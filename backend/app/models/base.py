from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def MetaJSON():
    """JSON column type that uses JSONB on PostgreSQL and plain JSON elsewhere.

    Kept portable so tests can run against in-memory SQLite without changes.
    """
    return JSON().with_variant(JSONB(), "postgresql")
