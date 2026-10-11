from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.auth.dependencies import require_admin
from app.config.settings import settings
from app.services.market_data_sync_service import MarketDataSyncService

router = APIRouter(
    prefix="/market-data",
    tags=["Market Data"],
    dependencies=[Depends(require_admin)],
)

REQUIRED_COLUMNS = {
    "datetime",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    return df


def _resolve_symbol(df: pd.DataFrame) -> str:

    full_symbol = str(df.iloc[0]["symbol"]).strip()

    if ":" in full_symbol:
        return full_symbol.split(":", 1)[1]

    return full_symbol


# Every file we've seen is internally consistent (always one format
# throughout), but not every file uses the SAME format as every
# other -- most are ISO ("2025-01-06"), at least one is
# day-first ("06-01-2025"). Detected per-file from its first value
# rather than assumed, and used only to sort correctly; the
# datetime column itself is written back out unparsed, in whatever
# format it arrived in, so this never changes a file's own format.
_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y")


def _parsed_datetime_for_sorting(column: pd.Series) -> pd.Series:

    sample = next(
        (value for value in column if pd.notna(value) and str(value).strip()),
        None,
    )

    for fmt in _DATE_FORMATS:
        if sample is not None:
            try:
                datetime.strptime(str(sample).strip(), fmt)
            except ValueError:
                continue
        try:
            return pd.to_datetime(column, format=fmt)
        except (ValueError, TypeError):
            continue

    # Unrecognised format -- fall back to pandas' best-effort
    # inference rather than failing the whole upload outright.
    return pd.to_datetime(column, errors="coerce")


@router.post("/upload")
async def upload_candles(
    files: list[UploadFile] = File(...),
) -> dict:
    """
    Upload one or more daily candle CSV files (same format as the
    existing data/candles files: datetime, symbol, open, high, low,
    close, volume).

    New rows are merged into that symbol's existing file (deduped by
    date, newest wins) rather than overwriting it — so this works
    whether you upload a fresh full-history export or just today's
    new row per symbol.

    Run POST /market-data/sync afterwards to process the uploaded
    data into features the scanner can use.
    """

    data_directory = Path(settings.DATA_DIRECTORY)
    data_directory.mkdir(parents=True, exist_ok=True)

    saved: list[dict] = []
    errors: list[dict] = []

    for file in files:

        if not (file.filename or "").lower().endswith(".csv"):
            errors.append(
                {
                    "file": file.filename,
                    "error": "Not a CSV file.",
                }
            )
            continue

        contents = await file.read()

        try:
            uploaded_df = pd.read_csv(BytesIO(contents))
        except Exception as exc:
            errors.append(
                {
                    "file": file.filename,
                    "error": f"Could not parse CSV: {exc}",
                }
            )
            continue

        if uploaded_df.empty:
            errors.append(
                {
                    "file": file.filename,
                    "error": "File has no data rows.",
                }
            )
            continue

        uploaded_df = _normalize_columns(uploaded_df)

        missing = REQUIRED_COLUMNS - set(uploaded_df.columns)

        if missing:
            errors.append(
                {
                    "file": file.filename,
                    "error": f"Missing required columns: {', '.join(sorted(missing))}",
                }
            )
            continue

        symbol = _resolve_symbol(uploaded_df)

        if not symbol:
            errors.append(
                {
                    "file": file.filename,
                    "error": "Could not determine symbol from file contents.",
                }
            )
            continue

        destination = data_directory / f"{symbol}.csv"

        if destination.exists():

            existing_df = _normalize_columns(
                pd.read_csv(destination),
            )

            combined_df = pd.concat(
                [existing_df, uploaded_df],
                ignore_index=True,
            )

        else:

            combined_df = uploaded_df

        combined_df = combined_df.drop_duplicates(
            subset=["datetime"],
            keep="last",
        )

        # Sort by the ACTUAL date, not the datetime column's raw
        # text -- a plain string sort silently breaks chronological
        # order for any file not in ISO (YYYY-MM-DD) format, e.g.
        # day-first dates like "06-01-2025" sort incorrectly as
        # text. Getting this wrong corrupts every indicator computed
        # downstream for that symbol, since they all depend on row
        # order being truly chronological.
        combined_df = (
            combined_df
            .assign(
                _sort_key=_parsed_datetime_for_sorting(combined_df["datetime"]),
            )
            .sort_values("_sort_key")
            .drop(columns="_sort_key")
        )

        combined_df.to_csv(destination, index=False)

        saved.append(
            {
                "file": file.filename,
                "symbol": symbol,
                "rows_in_upload": len(uploaded_df),
                "total_rows": len(combined_df),
            }
        )

    return {
        "saved": saved,
        "errors": errors,
    }


@router.post("/sync")
def sync_market_data(
    force_full_resync: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    """
    Process every CSV in the data directory: register any new
    instruments, recompute indicators/features, and refresh the
    scanner's snapshot data.

    Run this after uploading new CSVs.

    Set force_full_resync=true to recompute every instrument's full
    history from scratch, ignoring what's already stored. Needed
    once after adding a new indicator type, so historical dates get
    backfilled with it -- the normal incremental sync only looks at
    new candle data and would otherwise skip instruments that have
    no new rows to process.
    """

    service = MarketDataSyncService(
        session=db,
        data_directory=settings.DATA_DIRECTORY,
    )

    try:
        service.sync(force_full_resync=force_full_resync)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {exc}",
        )

    return {"status": "completed"}