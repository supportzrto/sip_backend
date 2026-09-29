from sqlalchemy.orm import Session


class BaseRepository:
    """
    Base repository for all database repositories.
    """

    def __init__(self, db: Session):
        self.db = db

    def add(self, entity):
        self.db.add(entity)

    def add_many(self, entities):
        self.db.add_all(entities)

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()