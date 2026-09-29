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

        combined_df = (
            combined_df
            .drop_duplicates(
                subset=["datetime"],
                keep="last",
            )
            .sort_values("datetime")
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