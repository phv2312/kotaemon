from typing import Sequence, TypeAlias

from sqlalchemy import select
from sqlalchemy.engine.row import Row
from sqlalchemy.orm import Session

import flowsettings
from kotaemon.schemas.file.source import Source

from ..utils.db import get_engine

SourceRecords: TypeAlias = Sequence[Row[tuple[Source]]]


class FileCRUD:
    def __init__(self, source: type[Source], database_path: str | None = None):
        database_path = database_path or flowsettings.KH_DATABASE
        self.source = source
        self.engine = get_engine(database_path)

    def list_docids(self) -> list[str]:
        with Session(self.engine) as session:
            records: SourceRecords = session.execute(select(self.source)).all()
            return [record[0].id for record in records]
