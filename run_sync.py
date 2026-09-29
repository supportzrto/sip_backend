"""
One-off script to run the full market data sync.

force_full_resync=True is required here: it ignores each
instrument's "already processed" status and recomputes every
indicator from scratch. Needed once after adding new indicator
types (like the breakout strategy's HIGHEST252/LOWEST252/
VOLUME_SURGE20) to an environment that already had data synced
before those indicators existed -- the normal fast incremental sync
only looks at whether there's new candle data, not whether new
indicator types need backfilling, so it would otherwise skip
everything and silently leave those fields empty.

Usage: python run_sync.py
"""
import time

from app.database.session import SessionLocal
from app.services.market_data_sync_service import MarketDataSyncService
from app.config.settings import settings

start = time.time()

db = SessionLocal()

try:
    service = MarketDataSyncService(
        session=db,
        data_directory=settings.DATA_DIRECTORY,
    )

    service.sync(force_full_resync=True)
    db.commit()
    print(f"\n\nSYNC COMPLETE in {time.time() - start:.1f} sec ({(time.time() - start) / 60:.1f} min)")

except Exception:
    db.rollback()
    print("\n\nSYNC FAILED - see traceback above")
    raise

finally:
    db.close()
        




