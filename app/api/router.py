from fastapi import APIRouter

from app.api.alerts import router as alerts_router
from app.api.market_data import router as market_data_router
from app.api.scanner import router as scanner_router
from app.api.strategies import router as strategies_router
from app.api.watchlists import router as watchlists_router

api_router = APIRouter()

api_router.include_router(scanner_router)
api_router.include_router(market_data_router)
api_router.include_router(watchlists_router)
api_router.include_router(strategies_router)
api_router.include_router(alerts_router)