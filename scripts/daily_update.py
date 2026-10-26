"""
The daily pipeline in one script:

    1. download today's NSE bhavcopy
    2. append it to your local candle CSVs (data/candles/)
    3. push the newest rows of every candle file to the DEPLOYED
       backend, so the backend's own copy on its Railway Volume
       stays current

The backend then recomputes indicators and evaluates alerts on its
own schedule (see "Backend schedule" below) -- this script does not
wait for that. Run it once a day, automatically, via Windows Task
Scheduler (setup notes below), or by hand:

    python scripts/daily_update.py                    # today
    python scripts/daily_update.py --date 2026-09-28  # a specific day
    python scripts/daily_update.py --dry-run          # download + preview the append only

Needs scripts/.env.daily_update (kept out of git by the .env.* rule)
with three lines:

    SIP_API_URL=https://sipguru.up.railway.app
    SIP_ADMIN_EMAIL=an-admin-account@example.com
    SIP_ADMIN_PASSWORD=its-password

How the push works: for every candle file it sends the header plus
the last few rows (default 5, --push-rows) -- not the whole file. The
backend merges them in by date, so sending rows it already has is
harmless, and a day that failed to push yesterday is repaired by
today's run automatically. About 1-2 MB in total instead of the
~760 MB the full files weigh.

After a long gap (say you haven't run this for two weeks): first catch
your local files up by hand -- download_bhavcopies.py over the missing
dates into a NEW folder, then append_bhavcopy.py on that folder (dry
run first) -- and then send the missing days to the backend with:

    python scripts/daily_update.py --push-only --push-rows 40

--push-rows must be at least the number of trading days you missed.
The normal 5-row push only covers a few days and would leave a hole on
the backend.

Safe to run again after a failure: download, append and push are all
idempotent, so just re-run the same command.

---- Backend schedule (set these as variables on the Railway service) ----
The backend's built-in scheduler does the sync and then the alerts:

    SYNC_SCHEDULE_ENABLED=true
    SYNC_SCHEDULE_TIMEZONE=Asia/Kolkata
    SYNC_SCHEDULE_HOUR=21
    SYNC_SCHEDULE_MINUTE=0
    ALERT_SCHEDULE_DELAY_MINUTES=60

Pick a sync time comfortably AFTER this script normally finishes
(e.g. script at 19:30, sync at 21:00). If the sync starts before the
push finishes it just misses that day and picks it up the next day --
nothing breaks, alerts are simply a day late. Use ONE worker process
only (the Dockerfile already does), otherwise the scheduled job runs
once per worker.

Why the script doesn't trigger the sync itself: Railway's public URL
cuts HTTP requests off after a few minutes, and a daily sync can run
longer than that. --trigger-sync exists for running it on demand; if
Railway cuts the request off it logs a warning, because the sync
normally keeps running on the server regardless.

---- Windows Task Scheduler ----
1. Task Scheduler -> Create Task (not "Basic Task").
2. Triggers -> New -> Daily, at a time after NSE publishes the file
   (evenings; 19:30 or later is a safe choice).
3. Actions -> New -> Start a program:
     Program/script:  C:\\SIP\\sip-core\\.venv\\Scripts\\python.exe
     Arguments:       scripts\\daily_update.py
     Start in:        C:\\SIP\\sip-core
   "Start in" matters: it makes data\\candles, logs\\ and
   scripts\\.env.daily_update resolve correctly.
4. Conditions: untick "Start the task only if the computer is on AC
   power" on a laptop.
5. Right-click the task -> Run once by hand and read
   logs\\daily_update_<date>.log before trusting it overnight.

Everything is logged to logs/daily_update_YYYY-MM-DD.log as well as
the console.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / "scripts" / ".env.daily_update"
BHAVCOPY_DIR = PROJECT_ROOT / "data" / "bhavcopy_daily"
CANDLES_DIR = PROJECT_ROOT / "data" / "candles"
LOG_DIR = PROJECT_ROOT / "logs"


class Logger:
    """Writes every message to both stdout and today's log file."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(path, "a", encoding="utf-8")

    def __call__(self, message: str = "") -> None:
        stamped = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        print(stamped)
        self._file.write(stamped + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()


def load_credentials(log) -> dict[str, str] | None:
    if not CREDENTIALS_FILE.exists():
        log(f"ERROR: missing credentials file at {CREDENTIALS_FILE}")
        log("Create it with SIP_API_URL / SIP_ADMIN_EMAIL / SIP_ADMIN_PASSWORD -- see the top of this script.")
        return None

    values: dict[str, str] = {}
    for line in CREDENTIALS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()

    missing = [
        k for k in ("SIP_API_URL", "SIP_ADMIN_EMAIL", "SIP_ADMIN_PASSWORD")
        if not values.get(k)
    ]
    if missing:
        log(f"ERROR: {CREDENTIALS_FILE} is missing: {', '.join(missing)}")
        return None

    return values


def run_download(target_date: date, log) -> Path | None:
    """Runs download_bhavcopies.py for a single day. Returns the
    downloaded file's path, or None if there's nothing to append
    (weekend/holiday) or the download genuinely failed.
    """

    date_str = target_date.isoformat()
    log(f"Downloading bhavcopy for {date_str}...")

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "download_bhavcopies.py"),
            date_str,
            date_str,
            "--out",
            str(BHAVCOPY_DIR),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    log(result.stdout.strip())
    if result.stderr.strip():
        log("stderr: " + result.stderr.strip())

    # download_bhavcopies.py prints its summary as f"  {category:<11}: {count}".
    if f"{'weekend':<11}: 1" in result.stdout or f"{'holiday':<11}: 1" in result.stdout:
        log(f"{date_str} is not a trading day -- nothing to do today.")
        return None

    if result.returncode != 0:
        log(f"Download failed (exit code {result.returncode}).")
        return None

    filename = f"sec_bhavdata_full_{target_date.strftime('%d%m%Y')}.csv"
    downloaded = BHAVCOPY_DIR / filename

    if not downloaded.exists():
        log(f"Download reported success but {downloaded} isn't there -- treating as failed.")
        return None

    return downloaded


def run_append(bhavcopy_path: Path, dry_run: bool, log) -> bool:
    log(f"Appending {bhavcopy_path.name} to candle files{' (dry run)' if dry_run else ''}...")

    args = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "append_bhavcopy.py"),
        str(bhavcopy_path),
    ]
    if dry_run:
        args.append("--dry-run")

    result = subprocess.run(
        args, cwd=PROJECT_ROOT, capture_output=True, text=True,
    )

    log(result.stdout.strip())
    if result.stderr.strip():
        log("stderr: " + result.stderr.strip())

    if result.returncode == 2:
        log("Append refused to run because of a date gap -- this shouldn't happen on a")
        log("normal day-to-day run. Check whether a previous day's update was missed.")
        return False

    if result.returncode != 0:
        log(f"Append failed (exit code {result.returncode}).")
        return False

    return True


def login(base_url: str, credentials: dict[str, str], log) -> str | None:
    log(f"Logging in to {base_url}...")
    try:
        response = requests.post(
            f"{base_url}/auth/login",
            json={
                "email": credentials["SIP_ADMIN_EMAIL"],
                "password": credentials["SIP_ADMIN_PASSWORD"],
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.RequestException as exc:
        log(f"Login failed: {exc}")
        return None
    except (KeyError, ValueError):
        log("Login response didn't look right.")
        return None


def read_recent_rows(path: Path, count: int) -> bytes | None:
    """The header line plus the last `count` data rows of a candle
    file, byte for byte as they appear in it (so the date format,
    symbol text and line endings the backend sees are the file's
    own). Returns None for a file with no data rows.
    """

    with open(path, "rb") as handle:
        header = handle.readline()
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(max(0, size - 8192))
        tail = handle.read()

    lines = [
        line
        for line in tail.splitlines(keepends=True)
        if line.strip() and line != header
    ]

    if not lines:
        return None

    eol = b"\r\n" if header.endswith(b"\r\n") else b"\n"
    recent = lines[-count:]

    if not recent[-1].endswith((b"\n", b"\r")):
        recent[-1] += eol

    if not header.endswith((b"\n", b"\r")):
        header += eol

    return header + b"".join(recent)


def push_recent_rows(
    credentials: dict[str, str],
    candles_dir: Path,
    rows: int,
    batch_size: int,
    log,
    retries: int = 3,
    delay: float = 3.0,
) -> bool:
    """Sends the newest rows of every candle file to the deployed
    backend's /market-data/upload. Returns False if any batch
    couldn't be delivered, so the caller can stop and report it.
    """

    base_url = credentials["SIP_API_URL"].rstrip("/")
    token = login(base_url, credentials, log)
    if token is None:
        return False

    payloads: list[tuple[str, bytes]] = []
    for path in sorted(candles_dir.glob("*.csv")):
        data = read_recent_rows(path, rows)
        if data is not None:
            payloads.append((path.name, data))

    if not payloads:
        log(f"No candle files with data found in {candles_dir}.")
        return False

    total_kb = sum(len(data) for _, data in payloads) / 1000
    batches = [payloads[i : i + batch_size] for i in range(0, len(payloads), batch_size)]
    log(f"Pushing the last {rows} rows of {len(payloads)} files ({total_kb:.0f} KB) in {len(batches)} batches...")

    failed_batches: list[int] = []
    server_errors: list[object] = []

    for number, batch in enumerate(batches, 1):
        delivered = False
        last_error = "unknown error"

        for attempt in range(1, retries + 1):
            try:
                response = requests.post(
                    f"{base_url}/market-data/upload",
                    headers={"Authorization": f"Bearer {token}"},
                    files=[("files", (name, data, "text/csv")) for name, data in batch],
                    timeout=300,
                )
            except requests.RequestException as exc:
                last_error = str(exc)
            else:
                if response.status_code == 200:
                    try:
                        server_errors.extend(response.json().get("errors") or [])
                    except ValueError:
                        pass
                    delivered = True
                    break
                last_error = f"HTTP {response.status_code}: {response.text[:300]}"

            if attempt < retries:
                log(f"  batch {number}/{len(batches)} attempt {attempt}/{retries} failed ({last_error}) -- retrying...")
                time.sleep(delay * attempt)

        if not delivered:
            log(f"  batch {number}/{len(batches)} failed after {retries} attempts: {last_error}")
            failed_batches.append(number)

    if server_errors:
        log(f"WARNING: the server reported problems with {len(server_errors)} file(s): {server_errors[:5]}")

    if failed_batches:
        log(f"Push incomplete: {len(failed_batches)} of {len(batches)} batches failed.")
        return False

    log("Push complete.")
    return True


def trigger_sync(credentials: dict[str, str], log) -> bool:
    """Optional: asks the backend to run an incremental sync now.

    Railway's public URL cuts requests off after a few minutes, and a
    sync can take longer -- so a gateway timeout is reported as a
    warning, not a failure: the server normally carries on with the
    sync regardless.
    """

    base_url = credentials["SIP_API_URL"].rstrip("/")
    token = login(base_url, credentials, log)
    if token is None:
        return False

    log("Triggering /market-data/sync (incremental)...")
    try:
        response = requests.post(
            f"{base_url}/market-data/sync",
            params={"force_full_resync": "false"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=20 * 60,
        )
    except requests.Timeout:
        log("WARNING: no response before the client timeout. The sync most likely")
        log("continues on the server -- look for 'Build Complete' in the Railway logs.")
        return True
    except requests.RequestException as exc:
        log(f"Sync request failed: {exc}")
        return False

    if response.status_code in (502, 503, 504):
        log(f"WARNING: HTTP {response.status_code} -- Railway's gateway cut the request off.")
        log("The sync most likely continues on the server -- look for 'Build Complete' in the Railway logs.")
        return True

    if response.status_code != 200:
        log(f"Sync failed: HTTP {response.status_code} -- {response.text[:1000]}")
        return False

    log("Sync completed.")
    log(response.text[:1000])
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--date", help="YYYY-MM-DD, default: today")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="download and preview the append only; nothing is written, pushed or synced",
    )
    parser.add_argument("--push-rows", type=int, default=5, help="how many of each file's newest rows to push")
    parser.add_argument("--batch-size", type=int, default=100, help="files per upload request")
    parser.add_argument(
        "--push-only",
        action="store_true",
        help="skip the download and append; just push each file's newest rows "
             "(use after catching up your local files by hand -- see below)",
    )
    parser.add_argument(
        "--trigger-sync",
        action="store_true",
        help="after pushing, ask the backend to sync right now instead of waiting for its own schedule",
    )
    args = parser.parse_args()

    if args.dry_run and args.push_only:
        parser.error("--dry-run and --push-only can't be combined: there is nothing to preview")

    target_date = date.fromisoformat(args.date) if args.date else date.today()

    log = Logger(LOG_DIR / f"daily_update_{target_date.isoformat()}.log")
    log(f"===== Daily update for {target_date.isoformat()} =====")

    try:
        # A push-only run has no trading day to check, so it works on weekends too.
        if not args.push_only and target_date.weekday() >= 5:
            log(f"{target_date} is a {target_date.strftime('%A')} -- market closed, nothing to do.")
            return 0

        if args.dry_run:
            credentials = None
            log("Dry run: no credentials needed, nothing will be written or pushed.")
        else:
            credentials = load_credentials(log)
            if credentials is None:
                return 1

        if args.push_only:
            log("Push only: skipping the download and append.")
        else:
            bhavcopy_path = run_download(target_date, log)
            if bhavcopy_path is None:
                return 0  # holiday / no file -- not a failure

            if not run_append(bhavcopy_path, args.dry_run, log):
                return 1

            if args.dry_run:
                log("Dry run complete.")
                return 0

        if not push_recent_rows(credentials, CANDLES_DIR, args.push_rows, args.batch_size, log):
            return 1

        if args.trigger_sync:
            if not trigger_sync(credentials, log):
                return 1
        else:
            log("The backend will sync and run alerts on its own schedule.")

        log("Daily update completed successfully.")
        return 0

    finally:
        log("")
        log.close()


if __name__ == "__main__":
    sys.exit(main())