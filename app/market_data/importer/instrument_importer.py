from app.market_data.providers.base import MarketDataProvider
from app.market_data.validators.instrument_validator import (
    InstrumentValidator,
)
from app.models.instrument import Instrument
from app.repositories.instrument_repository import (
    InstrumentRepository,
)


class InstrumentImporter:
    """
    Imports instruments from a MarketDataProvider into the database.
    """

    def __init__(
        self,
        provider: MarketDataProvider,
        repository: InstrumentRepository,
    ):
        self.provider = provider
        self.repository = repository

    def import_instruments(self) -> int:
        """
        Import all instruments from the provider.

        Returns:
            int: Number of newly imported instruments.
        """

        imported_models: list[Instrument] = []

        # Load all existing symbols once
        existing_symbols = self.repository.get_all_symbols()

        # Fetch instruments from provider
        instruments = self.provider.fetch_instruments()

        for instrument in instruments:

            InstrumentValidator.validate(instrument)

            if instrument.symbol in existing_symbols:
                continue

            imported_models.append(
                Instrument(
                    symbol=instrument.symbol,
                    company_name=instrument.company_name,
                    exchange=instrument.exchange,
                    instrument_type=instrument.instrument_type,
                    isin=instrument.isin,
                    provider=instrument.provider,
                    provider_token=instrument.provider_token,
                    is_active=instrument.is_active,
                )
            )

        if imported_models:
            self.repository.save_many(imported_models)
            self.repository.commit()

        return len(imported_models)