"""
Imports all SQLAlchemy models so they are registered with Base.metadata.
"""

from app.models.instrument import Instrument
from app.models.daily_candle import DailyCandle