from sqlalchemy.orm import Session

from app.models.feature.value import FeatureValue
from app.repositories.feature_value_repository import (
    FeatureValueRepository,
)


class BatchWriter:
    """
    Persists FeatureValue objects in batches.

    Responsibilities
    ----------------
    - Buffer FeatureValue objects
    - Bulk insert into the database
    - Commit transactions
    - Track write statistics
    """

    def __init__(
        self,
        session: Session,
        repository: FeatureValueRepository,
        batch_size: int = 50_000,
    ) -> None:

        self.session = session
        self.repository = repository
        self.batch_size = batch_size

        self._buffer: list[FeatureValue] = []

        self._rows_written = 0
        self._flush_count = 0

    @property
    def rows_written(self) -> int:
        return self._rows_written

    @property
    def flush_count(self) -> int:
        return self._flush_count

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    def add(
        self,
        rows: list[FeatureValue],
    ) -> None:
        """
        Add rows to the internal buffer.
        """

        if not rows:
            return

        self._buffer.extend(rows)

        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(
        self,
    ) -> None:
        """
        Persist buffered rows.
        """

        if not self._buffer:
            return

        self.repository.bulk_upsert(
            self._buffer
        )

        self.session.commit()

        self._rows_written += len(self._buffer)
        self._flush_count += 1

        self._buffer.clear()

    def finish(
        self,
    ) -> int:
        """
        Flush any remaining rows and return
        the total number of rows written.
        """

        self.flush()

        return self._rows_written

    def reset(self) -> None:
        """
        Clear internal state.

        Useful for testing.
        """

        self._buffer.clear()
        self._rows_written = 0
        self._flush_count = 0