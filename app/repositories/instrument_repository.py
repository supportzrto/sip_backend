from sqlalchemy import select

from app.models.instrument import Instrument
from app.repositories.base_repository import BaseRepository


class InstrumentRepository(BaseRepository):

    def get_by_symbol(
        self,
        symbol: str,
    ) -> Instrument | None:

        statement = (
            select(Instrument)
            .where(Instrument.symbol == symbol)
        )

        return self.db.scalar(statement)

    def save_many(
        self,
        instruments: list[Instrument],
    ) -> None:

        self.add_many(instruments)
        # self.commit()

    def get_all_symbols(self) -> set[str]:

        statement = select(Instrument.symbol)

        return set(
            self.db.scalars(statement).all()
        )
    
    def get_all(self) -> list[Instrument]:

        statement = (select(Instrument).order_by(Instrument.symbol))

        return list(
            self.db.scalars(statement).all()
        )