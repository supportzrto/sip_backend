"""
Download NSE's daily "Full Bhavcopy and Security Deliverable" files
(sec_bhavdata_full_DDMMYYYY.csv) for a date range, so the whole batch
can then be fed into scripts/append_bhavcopy.py in one pass.

Usage (start small first -- see the note below):

    python scripts/download_bhavcopies.py 2025-01-06 2025-01-10 --out data/bhavcopy_backfill

    # If that works, do the real range:
    python scripts/download_bhavcopies.py 2025-01-04 2026-09-27 --out data/bhavcopy_backfill

IMPORTANT -- try a small range (a week) before the full ~21-month
backfill. This script could not be tested against NSE's live server
from where it was written (that network wasn't reachable from there),
so it's built from the documented URL pattern and the defenses public
NSE-downloader tools typically need, but hasn't been proven end to
end. A small range tells you quickly whether it works at all, rather
than finding out 300 requests in.

If every request fails with 403 Forbidden: NSE is blocking the
request as non-browser traffic despite the User-Agent below. The
usual next step is warming up a session by first requesting nseindia.com's
homepage (to pick up cookies) before hitting archives.nseindia.com --
tell me if you hit this and I'll add it.

Notes:
- Saturdays and Sundays are skipped automatically (NSE is closed).
- A 404 for a weekday usually means an exchange holiday, not a bug --
  reported in the summary, not treated as a failure.
- Transient network errors are retried a few times with backoff
  before that date is given up on and the script moves to the next.
- Safe to re-run: a file already downloaded (non-empty, on disk) is
  skipped, so an interrupted run can just be restarted with the same
  command.
- A short delay between requests is built in by default -- please
  don't remove it. These are free public files, but hammering NSE's
  servers with hundreds of back-to-back requests is a good way to get
  your IP temporarily blocked, which would break this for longer than
  the delay ever costs you.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

URL_TEMPLATE = "https://archives.nseindia.com/products/content/sec_bhavdata_full_{}.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/csv,application/csv,*/*",
    "Referer": "https://www.nseindia.com/",
}

# A real bhavcopy for the full market is hundreds of KB. Anything
# tiny returned with a 200 status is almost always an HTML error/
# rate-limit page, not real data -- catching that here stops a
# handful of garbage bytes from silently being fed into the backfill.
MIN_VALID_BYTES = 5_000


def daterange(start: date, end: date):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def download_one(
    session: requests.Session,
    day: date,
    out_dir: Path,
    retries: int,
    delay: float,
) -> tuple[str, str]:
    """Returns (category, detail). category is one of:
    weekend, already, downloaded, holiday, failed
    """

    if day.weekday() >= 5:
        return "weekend", ""

    filename = f"sec_bhavdata_full_{day.strftime('%d%m%Y')}.csv"
    dest = out_dir / filename

    if dest.exists() and dest.stat().st_size >= MIN_VALID_BYTES:
        return "already", str(dest)

    url = URL_TEMPLATE.format(day.strftime("%d%m%Y"))
    last_error = "unknown error"

    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, headers=HEADERS, timeout=20)

            if response.status_code == 404:
                return "holiday", ""

            response.raise_for_status()

            if len(response.content) < MIN_VALID_BYTES:
                last_error = (
                    f"response was only {len(response.content)} bytes "
                    f"-- likely a rate-limit or error page, not real data"
                )
                time.sleep(delay * attempt)
                continue

            dest.write_bytes(response.content)
            return "downloaded", str(dest)

        except requests.RequestException as exc:
            last_error = str(exc)
            time.sleep(delay * attempt)

    return "failed", last_error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("start", help="YYYY-MM-DD, inclusive")
    parser.add_argument("end", help="YYYY-MM-DD, inclusive")
    parser.add_argument("--out", default="data/bhavcopy_backfill")
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="seconds to wait between requests (be polite to NSE's servers)",
    )
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    if start > end:
        print("start date must not be after end date")
        return 1

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    days = list(daterange(start, end))
    print(f"Checking {len(days)} calendar days from {start} to {end}...")
    print(f"Saving into: {out_dir.resolve()}")
    print()

    session = requests.Session()
    by_category: dict[str, list[date]] = {}
    failures: list[tuple[date, str]] = []

    for i, day in enumerate(days, 1):
        category, detail = download_one(
            session, day, out_dir, retries=args.retries, delay=args.delay,
        )
        by_category.setdefault(category, []).append(day)

        print(f"[{i}/{len(days)}] {day} ({day.strftime('%a')}): {category}")

        if category == "failed":
            failures.append((day, detail))

        # Only actual network requests need the courtesy delay --
        # weekends and already-downloaded files are free.
        if category in ("downloaded", "holiday", "failed"):
            time.sleep(args.delay)

    print()
    print("Summary:")
    for category in ("downloaded", "already", "weekend", "holiday", "failed"):
        print(f"  {category:<11}: {len(by_category.get(category, []))}")

    if failures:
        print()
        print("Failed dates (re-run the same command -- everything else already")
        print("downloaded will be skipped, so this only retries what's missing):")
        for day, detail in failures:
            print(f"  {day}: {detail}")
        return 1

    print()
    print("Next step: run scripts/append_bhavcopy.py against this folder, e.g.")
    print(f"  python scripts/append_bhavcopy.py {out_dir} --dry-run")

    return 0


if __name__ == "__main__":
    sys.exit(main())