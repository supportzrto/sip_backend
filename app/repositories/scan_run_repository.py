from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.scan_result import ScanResult as ScanResultModel
from app.models.scan_run import ScanRun
from app.repositories.base_repository import BaseRepository


class ScanRunRepository(BaseRepository):

    def create_run(
        self,
        strategy: str,
        stocks_scanned: int,
        matches_found: int,
        started_at: datetime,
        completed_at: datetime,
        results: list[ScanResultModel],
        user_id: int | None = None,
    ) -> ScanRun:
        """
        Persist a completed scan run along with its matched results.
        """

        scan_run = ScanRun(
            user_id=user_id,
            strategy=strategy,
            stocks_scanned=stocks_scanned,
            matches_found=matches_found,
            started_at=started_at,
            completed_at=completed_at,
            results=results,
        )

        self.add(scan_run)
        self.commit()
        self.db.refresh(scan_run)

        return scan_run

    def _filtered_statement(
        self,
        strategy: str | None,
        symbol: str | None,
        started_after: datetime | None,
        started_before: datetime | None,
        user_id: int | None = None,
    ):

        statement = select(ScanRun)

        # user_id=None means "don't scope by owner" (used for admins
        # viewing everyone's runs) -- it is NOT the same as filtering
        # for rows where ScanRun.user_id IS NULL.
        if user_id is not None:
            statement = statement.where(
                ScanRun.user_id == user_id,
            )

        if symbol is not None:
            statement = statement.join(
                ScanResultModel,
                ScanResultModel.scan_run_id == ScanRun.id,
            ).where(
                ScanResultModel.symbol == symbol,
            )

        if strategy is not None:
            statement = statement.where(
                ScanRun.strategy == strategy,
            )

        if started_after is not None:
            statement = statement.where(
                ScanRun.started_at >= started_after,
            )

        if started_before is not None:
            statement = statement.where(
                ScanRun.started_at <= started_before,
            )

        return statement

    def get_recent_runs(
        self,
        limit: int = 20,
        offset: int = 0,
        strategy: str | None = None,
        symbol: str | None = None,
        started_after: datetime | None = None,
        started_before: datetime | None = None,
        user_id: int | None = None,
    ) -> list[ScanRun]:

        statement = self._filtered_statement(
            strategy=strategy,
            symbol=symbol,
            started_after=started_after,
            started_before=started_before,
            user_id=user_id,
        )

        statement = (
            statement
            .distinct()
            .order_by(ScanRun.started_at.desc())
            .offset(offset)
            .limit(limit)
        )

        return list(self.db.scalars(statement).all())

    def count_runs(
        self,
        strategy: str | None = None,
        symbol: str | None = None,
        started_after: datetime | None = None,
        started_before: datetime | None = None,
        user_id: int | None = None,
    ) -> int:
        """
        Total number of runs matching the same filters as
        get_recent_runs(), ignoring limit/offset. Used to build
        pagination metadata (e.g. total pages).
        """

        subquery = self._filtered_statement(
            strategy=strategy,
            symbol=symbol,
            started_after=started_after,
            started_before=started_before,
            user_id=user_id,
        ).subquery()

        statement = select(
            func.count(func.distinct(subquery.c.id)),
        )

        return self.db.scalar(statement) or 0

    def get_run_with_results(
        self,
        run_id: int,
        user_id: int | None = None,
    ) -> ScanRun | None:
        """
        user_id=None returns the run regardless of owner (for
        admins). Pass the requesting user's id to additionally
        require they own the run -- a mismatch returns None, which
        the caller should treat the same as "not found" rather than
        revealing that a run with that id exists for someone else.
        """

        statement = (
            select(ScanRun)
            .where(ScanRun.id == run_id)
            .options(selectinload(ScanRun.results))
        )

        if user_id is not None:
            statement = statement.where(
                ScanRun.user_id == user_id,
            )

        return self.db.scalar(statement)