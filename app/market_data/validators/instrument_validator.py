from app.market_data.schemas import HistoricalInstrument


class InstrumentValidator:

    @staticmethod
    def validate(instrument: HistoricalInstrument) -> None:

        if not instrument.symbol.strip():
            raise ValueError("Instrument symbol cannot be empty.")

        if not instrument.company_name.strip():
            raise ValueError(
                f"{instrument.symbol}: Company name cannot be empty."
            )

        if not instrument.exchange.strip():
            raise ValueError(
                f"{instrument.symbol}: Exchange cannot be empty."
            )

        if not instrument.instrument_type.strip():
            raise ValueError(
                f"{instrument.symbol}: Instrument type cannot be empty."
            )

        if not instrument.provider.strip():
            raise ValueError(
                f"{instrument.symbol}: Provider cannot be empty."
            )