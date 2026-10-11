"""
One-time (or repeatable) bulk upload of every CSV in data/candles/
to the deployed backend's POST /market-data/upload -- this is what
actually gets your local market data onto the backend's Railway
Volume, since the deployed container has no access to your laptop's
disk.

Usage:

    python scripts/bulk_upload_candles.py --dry-run
    python scripts/bulk_upload_candles.py

Requires the same credentials file as scripts/daily_update.py:

    scripts/.env.daily_update

containing SIP_API_URL / SIP_ADMIN_EMAIL / SIP_ADMIN_PASSWORD. If
you haven't set that up yet, see daily_update.py's docstring.

Safe to interrupt and re-run: as each batch succeeds, its filenames
are recorded in scripts/.bulk_upload_checkpoint.json, and a re-run
skips anything already checkpointed instead of re-sending ~700MB of
data from scratch. Delete that checkpoint file if you ever want to
force a full re-upload of everything.

Files are sent in batches (default 25 per request, ~7MB typically)
rather than one request per file (2500+ round trips) or everything
in a single request (one dropped connection loses the whole run).
Given how often the Railway connection has dropped mid-operation
elsewhere in this project, each batch gets a few retries with
backoff before being recorded as failed and the script moves on to
the next one -- a single stubborn batch doesn't block the rest of
the run. Failed batches are listed at the end; just run the script
again afterward and it'll retry only what's missing.

After this completes, trigger a sync against the deployed backend:

    POST /market-data/sync?force_full_resync=false

This script only gets the raw CSVs onto the server -- it does not
itself recompute indicators, the sync step does that.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / "scripts" / ".env.daily_update"
CHECKPOINT_FILE = PROJECT_ROOT / "scripts" / ".bulk_upload_checkpoint.json"
DEFAULT_CANDLES_DIR = PROJECT_ROOT / "data" / "candles"


def load_credentials() -> dict[str, str] | None:
    if not CREDENTIALS_FILE.exists():
        print(f"ERROR: missing credentials file at {CREDENTIALS_FILE}")
        print("Create it with SIP_API_URL / SIP_ADMIN_EMAIL / SIP_ADMIN_PASSWORD")
        print("-- see the top of scripts/daily_update.py for the format.")
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
        print(f"ERROR: {CREDENTIALS_FILE} is missing: {', '.join(missing)}")
        return None

    return values


def login(base_url: str, email: str, password: str) -> str | None:
    try:
        response = requests.post(
            f"{base_url}/auth/login",
            json={"email": email, "password": password},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.RequestException as exc:
        print(f"Login failed: {exc}")
        return None
    except (KeyError, ValueError):
        print(f"Login response didn't look right: {response.text[:500]}")
        return None


def load_checkpoint() -> set[str]:
    if not CHECKPOINT_FILE.exists():
        return set()
    try:
        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        return set(data.get("uploaded_files", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_checkpoint(uploaded_files: set[str]) -> None:
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_FILE.write_text(
        json.dumps({"uploaded_files": sorted(uploaded_files)}, indent=2),
        encoding="utf-8",
    )


def chunked(items: list[Path], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def upload_batch(
    base_url: str,
    token: str,
    batch: list[Path],
    retries: int,
    delay: float,
) -> bool:
    """Uploads one batch, retrying on transient failure. Returns
    whether it ultimately succeeded.
    """

    last_error = "unknown error"

    for attempt in range(1, retries + 1):

        # Opened fresh each attempt -- a file object consumed by a
        # failed attempt can't be safely reused for a retry.
        handles = [open(path, "rb") for path in batch]
        try:
            files = [
                ("files", (path.name, handle, "text/csv"))
                for path, handle in zip(batch, handles)
            ]

            response = requests.post(
                f"{base_url}/market-data/upload",
                headers={"Authorization": f"Bearer {token}"},
                files=files,
                timeout=300,
            )

            if response.status_code != 200:
                last_error = f"HTTP {response.status_code}: {response.text[:500]}"
            else:
                body = response.json()
                if body.get("errors"):
                    # The endpoint itself reports some files as
                    # unreadable -- not a network failure, so don't
                    # retry, just surface it and move on.
                    print(f"  server reported per-file errors: {body['errors']}")
                return True

        except requests.RequestException as exc:
            last_error = str(exc)

        finally:
            for handle in handles:
                handle.close()

        if attempt < retries:
            print(f"  attempt {attempt}/{retries} failed ({last_error}) -- retrying...")
            time.sleep(delay * attempt)

    print(f"  batch failed after {retries} attempts: {last_error}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--candles-dir", default=str(DEFAULT_CANDLES_DIR))
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be uploaded, in how many batches, without sending anything",
    )
    args = parser.parse_args()

    candles_dir = Path(args.candles_dir)
    if not candles_dir.is_dir():
        print(f"Candles folder not found: {candles_dir.resolve()}")
        return 1

    all_files = sorted(candles_dir.glob("*.csv"))
    if not all_files:
        print(f"No CSV files found in {candles_dir.resolve()}")
        return 1

    checkpoint = load_checkpoint()
    pending = [f for f in all_files if f.name not in checkpoint]

    total_bytes = sum(f.stat().st_size for f in pending)
    print(f"Candle files total: {len(all_files)}")
    print(f"Already uploaded (checkpointed, will skip): {len(checkpoint & {f.name for f in all_files})}")
    print(f"Remaining to upload: {len(pending)} ({total_bytes / 1_000_000:.1f} MB)")

    if not pending:
        print("Nothing to do -- everything is already checkpointed.")
        print("(Delete scripts/.bulk_upload_checkpoint.json to force a full re-upload.)")
        return 0

    batches = list(chunked(pending, args.batch_size))
    print(f"Batches: {len(batches)} (batch size {args.batch_size})")

    if args.dry_run:
        print("\nDry run -- not uploading. Remove --dry-run to actually send these.")
        return 0

    credentials = load_credentials()
    if credentials is None:
        return 1

    base_url = credentials["SIP_API_URL"].rstrip("/")
    print(f"\nLogging in to {base_url}...")
    token = login(base_url, credentials["SIP_ADMIN_EMAIL"], credentials["SIP_ADMIN_PASSWORD"])
    if token is None:
        return 1

    succeeded = 0
    failed_batches: list[int] = []
    started_at = time.time()

    for i, batch in enumerate(batches, 1):
        names = ", ".join(p.name for p in batch[:3])
        suffix = f" (+{len(batch) - 3} more)" if len(batch) > 3 else ""
        print(f"[{i}/{len(batches)}] uploading {len(batch)} files: {names}{suffix}")

        if upload_batch(base_url, token, batch, args.retries, args.delay):
            succeeded += len(batch)
            checkpoint.update(p.name for p in batch)
            save_checkpoint(checkpoint)  # persist after every batch, not just at the end
        else:
            failed_batches.append(i)

        time.sleep(args.delay)  # be polite between batches regardless of outcome

    elapsed = time.time() - started_at
    print(f"\nDone in {elapsed / 60:.1f} minutes.")
    print(f"  uploaded this run : {succeeded} files")
    print(f"  total checkpointed: {len(checkpoint)} / {len(all_files)} files")

    if failed_batches:
        print(f"  failed batches    : {len(failed_batches)} (batch numbers: {failed_batches})")
        print("\nRun this exact command again -- successful files are skipped automatically,")
        print("so a re-run only retries what actually failed.")
        return 1

    print("\nAll files uploaded. Next step:")
    print(f"  curl -X POST '{base_url}/market-data/sync?force_full_resync=false' \\")
    print(f"       -H 'Authorization: Bearer <token>'")
    print("(or trigger it via /docs, same as before)")
    return 0


if __name__ == "__main__":
    sys.exit(main())