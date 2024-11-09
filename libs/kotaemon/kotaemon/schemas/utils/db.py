from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


@lru_cache
def get_engine(database: str) -> Engine:
    return create_engine(database, echo=True)
