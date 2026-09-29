"""
Append NSE "Full Bhavcopy and Security Deliverable" files
(sec_bhavdata_full_DDMMYYYY.csv) to the per-symbol candle CSVs in
data/candles/.

Usage (from the project root, e.g. C:\\SIP\\sip-core):

    # Always look at a dry run first -- nothing is written.
    python scripts/append_bhavcopy.py path/to/sec_bhavdata_full_29092026.csv --dry-run

    # Then the real thing. A folder works too (every *.csv inside is
    # read, then applied in date order -- use this for the backfill).
    python scripts/append_bhavcopy.py path/to/folder_of_bhavcopies

    # Afterwards, run the incremental sync (force_full_resync=false).

Design notes
------------
* Only symbols that ALREADY have a file in the candles folder are
  updated, so your universe stays as it is. Bonds, ETFs, SME listings
  etc. in the bhavcopy are ignored unless you have a file for them.
* Nothing is rewritten: new rows are appended to the end of each file.
  The date format, symbol text (e.g. "NSE:ABB"), line endings and the
  index column are all copied from the file's own last row.
* Safe to re-run: a date that is already in a file is skipped.
* change (%) is computed close-to-close against the previous row in
  the file, and "last day change (%)" is the previous row's change --
  matching how the existing rows are built.
* Refuses to run if your files end long before the bhavcopy's date,
  because appending across a gap would make the indicators (252-day
  highs, RSI, moving averages) treat non-adjacent days as consecutive.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd

# Columns after the unnamed index column in the candle files.
EXPECTED_HEADER = [
    "datetime",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "change (%)",
    "last day change (%)",
]

BHAV_REQUIRED = [
    "SYMBOL",
    "DATE1",
    "OPEN_PRICE",
    "HIGH_PRICE",
    "LOW_PRICE",
    "CLOSE_PRICE",
    "TTL_TRD_QNTY",
]

# A one-day move at least this large is reported, because it is very
# often a split/bonus/demerger that the raw bhavcopy does not adjust.
SUSPICIOUS_MOVE_PCT = 30.0

# (regex, strptime format). The captured group 2 is any suffix after
# the date (e.g. " 00:00:00") and is copied verbatim to new rows.
_DATE_STYLES = [
    (re.compile(r"^(\d{4}-\d{2}-\d{2})(.*)$"), "%Y-%m-%d"),
    (re.compile(r"^(\d{2}-\d{2}-\d{4})(.*)$"), "%d-%m-%Y"),
    (re.compile(r"^(\d{2}/\d{2}/\d{4})(.*)$"), "%d/%m/%Y"),
]


@dataclass
class SymbolState:
    path: Path
    index: int
    day: date
    close: float
    change: str          # the last row's "change (%)" text
    symbol_field: str    # e.g. "NSE:3IINFOLTD", copied verbatim
    date_fmt: str
    date_suffix: str
    eol: str
    needs_leading_newline: bool
    new_lines: list[str] = field(default_factory=list)


def fmt_num(value: float, places: int) -> str:
    text = f"{value:.{places}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def parse_candle_date(text: str):
    """Returns (date, strptime_format, suffix) or None."""
    for pattern, fmt in _DATE_STYLES:
        match = pattern.match(text.strip())
        if match:
            try:
                return (
                    datetime.strptime(match.group(1), fmt).date(),
                    fmt,
                    match.group(2),
                )
            except ValueError:
                return None
    return None


def read_state(path: Path):
    """
    Reads just the header and last row of a candle file. Returns
    (SymbolState, None) or (None, reason_string).
    """
    with open(path, "rb") as handle:
        header_bytes = handle.readline()
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(max(0, size - 8192))
        tail = handle.read()

    header_text = header_bytes.decode("utf-8-sig", errors="replace")
    header = next(csv.reader([header_text.strip("\r\n")]), [])

    if [h.strip() for h in header[1:10]] != EXPECTED_HEADER:
        return None, "unexpected header"

    tail_text = tail.decode("utf-8", errors="replace")
    lines = [ln for ln in tail_text.splitlines() if ln.strip()]

    if not lines or lines[-1].strip("\r\n") == header_text.strip("\r\n"):
        return None, "no data rows"

    fields = next(csv.reader([lines[-1]]), [])
    if len(fields) < 8:
        return None, "last row is malformed"

    parsed = parse_candle_date(fields[1])
    if parsed is None:
        return None, f"unrecognised date format: {fields[1]!r}"

    day, date_fmt, suffix = parsed

    try:
        index = int(float(fields[0]))
        close = float(fields[6])
    except ValueError:
        return None, "last row has non-numeric index/close"

    change = fields[8] if len(fields) > 8 else ""
    eol = "\r\n" if header_bytes.endswith(b"\r\n") else "\n"

    return (
        SymbolState(
            path=path,
            index=index,
            day=day,
            close=close,
            change=change,
            symbol_field=fields[2],
            date_fmt=date_fmt,
            date_suffix=suffix,
            eol=eol,
            needs_leading_newline=not tail.endswith((b"\n", b"\r")),
        ),
        None,
    )


def load_bhavcopy(path: Path):
    df = pd.read_csv(path, dtype=str, skipinitialspace=True)
    df.columns = [c.strip() for c in df.columns]

    missing = [c for c in BHAV_REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}")

    for column in ("SYMBOL", "DATE1"):
        df[column] = df[column].str.strip()

    dates = df["DATE1"].dropna().unique()
    if len(dates) != 1:
        raise ValueError(f"{path.name}: expected one trade date, found {list(dates)}")

    trade_date = datetime.strptime(dates[0], "%d-%b-%Y").date()

    for column in ("OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE", "TTL_TRD_QNTY"):
        df[column] = pd.to_numeric(df[column], errors="coerce")

    valid = (
        df[["OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE", "TTL_TRD_QNTY"]]
        .notna()
        .all(axis=1)
        & (df["OPEN_PRICE"] > 0)
        & (df["HIGH_PRICE"] > 0)
        & (df["LOW_PRICE"] > 0)
        & (df["CLOSE_PRICE"] > 0)
        & (df["HIGH_PRICE"] >= df["LOW_PRICE"])
    )

    return trade_date, df[valid], int((~valid).sum())


def collect_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            paths.extend(sorted(p.glob("*.csv")))
        elif p.is_file():
            paths.append(p)
        else:
            raise FileNotFoundError(item)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("inputs", nargs="+", help="bhavcopy CSV file(s) or folder(s)")
    parser.add_argument("--candles-dir", default="data/candles")
    parser.add_argument("--dry-run", action="store_true", help="show what would happen, write nothing")
    parser.add_argument("--max-gap-days", type=int, default=7)
    parser.add_argument(
        "--allow-gap",
        action="store_true",
        help="append even if your files end long before the bhavcopy date",
    )
    args = parser.parse_args()

    candles_dir = Path(args.candles_dir)
    if not candles_dir.is_dir():
        print(f"Candles folder not found: {candles_dir.resolve()}")
        return 1

    # ---- load bhavcopies, oldest first, one per trade date ----
    loaded = {}
    dropped_rows = 0
    for path in collect_paths(args.inputs):
        trade_date, df, dropped = load_bhavcopy(path)
        dropped_rows += dropped
        if trade_date in loaded:
            print(f"Skipping {path.name}: trade date {trade_date} already loaded")
            continue
        loaded[trade_date] = df

    if not loaded:
        print("No bhavcopy files found.")
        return 1

    ordered_dates = sorted(loaded)
    print(f"Bhavcopy files: {len(ordered_dates)} ({ordered_dates[0]} to {ordered_dates[-1]})")

    # ---- read the last row of every candle file ----
    states: dict[str, SymbolState] = {}
    unreadable: list[tuple[str, str]] = []

    for csv_path in sorted(candles_dir.glob("*.csv")):
        state, reason = read_state(csv_path)
        if state is None:
            unreadable.append((csv_path.name, reason))
        else:
            states[csv_path.stem] = state

    print(f"Candle files readable: {len(states)}  (unreadable, left untouched: {len(unreadable)})")
    for name, reason in unreadable[:10]:
        print(f"  ! {name}: {reason}")

    if not states:
        return 1

    # ---- refuse to append across a big gap ----
    typical_last_day = Counter(s.day for s in states.values()).most_common(1)[0][0]
    gap_days = (ordered_dates[0] - typical_last_day).days

    if gap_days > args.max_gap_days and not args.allow_gap:
        print()
        print(f"STOPPED: most of your candle files end on {typical_last_day}, but the")
        print(f"earliest bhavcopy given is {ordered_dates[0]} -- {gap_days} days later.")
        print("Appending across that gap would make the indicators treat non-adjacent")
        print("days as consecutive. Backfill every trading day in between first")
        print("(pass them all in one run), or use --allow-gap if you really mean it.")
        return 2

    # ---- build new rows in memory ----
    appended = 0
    already_present = 0
    resumed_after_gap = 0
    not_in_universe: set[str] = set()
    flagged: list[tuple[float, str, date, float, float]] = []
    samples: list[tuple[str, str]] = []

    for trade_date in ordered_dates:
        for row in loaded[trade_date].itertuples(index=False):
            symbol = row.SYMBOL
            state = states.get(symbol)

            if state is None:
                not_in_universe.add(symbol)
                continue

            if trade_date <= state.day:
                already_present += 1
                continue

            if (trade_date - state.day).days > args.max_gap_days:
                resumed_after_gap += 1

            close = float(row.CLOSE_PRICE)
            change_pct = (close / state.close - 1.0) * 100.0 if state.close else 0.0

            if abs(change_pct) >= SUSPICIOUS_MOVE_PCT:
                flagged.append((abs(change_pct), symbol, trade_date, state.close, close))

            change_text = fmt_num(change_pct, 6)

            buffer = io.StringIO()
            csv.writer(buffer, lineterminator=state.eol).writerow(
                [
                    state.index + 1,
                    trade_date.strftime(state.date_fmt) + state.date_suffix,
                    state.symbol_field,
                    fmt_num(float(row.OPEN_PRICE), 4),
                    fmt_num(float(row.HIGH_PRICE), 4),
                    fmt_num(float(row.LOW_PRICE), 4),
                    fmt_num(close, 4),
                    int(row.TTL_TRD_QNTY),
                    change_text,
                    state.change,  # previous row's change (%)
                ]
            )

            line = buffer.getvalue()
            if len(samples) < 3 and not state.new_lines:
                samples.append((symbol, line.rstrip("\r\n")))

            state.new_lines.append(line)
            state.index += 1
            state.day = trade_date
            state.close = close
            state.change = change_text
            appended += 1

    # ---- write ----
    files_touched = 0
    if not args.dry_run:
        for state in states.values():
            if not state.new_lines:
                continue
            with open(state.path, "ab") as handle:
                if state.needs_leading_newline:
                    handle.write(state.eol.encode())
                handle.write("".join(state.new_lines).encode("utf-8"))
            files_touched += 1

    # ---- summary ----
    print()
    print("DRY RUN - nothing written" if args.dry_run else "Done")
    print(f"  rows appended                : {appended}")
    if not args.dry_run:
        print(f"  candle files updated         : {files_touched}")
    print(f"  already present (skipped)    : {already_present}")
    print(f"  bhavcopy symbols not in your candles folder (ignored): {len(not_in_universe)}")
    print(f"  bhavcopy rows dropped as invalid (zero/blank prices) : {dropped_rows}")
    print(f"  symbols appended after a >{args.max_gap_days}-day gap of their own : {resumed_after_gap}")

    if samples:
        print()
        print("Sample of what is being written (compare with your files):")
        for symbol, line in samples:
            print(f"  {symbol}.csv  <-  {line}")

    if flagged:
        flagged.sort(reverse=True)
        print()
        print(f"{len(flagged)} move(s) of {SUSPICIOUS_MOVE_PCT:.0f}% or more in one day - check for an")
        print("unadjusted split/bonus/demerger before trusting a signal on these:")
        for pct, symbol, day, prev_close, close in flagged[:25]:
            print(f"  {symbol:<14} {day}  {prev_close:>10.2f} -> {close:>10.2f}  ({close / prev_close - 1:+.1%})")
        if len(flagged) > 25:
            print(f"  ... and {len(flagged) - 25} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())