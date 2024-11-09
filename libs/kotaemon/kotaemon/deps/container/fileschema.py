from functools import lru_cache

import flowsettings
from kotaemon.schemas.file import FileGroup, Index, Source
from kotaemon.schemas.utils.db import get_engine


class FileSchema:
    @staticmethod
    @lru_cache
    def Source(
        collection_idx: int,
        private: bool,
        database_path: str | None = None,
    ) -> type[Source]:
        database_path = database_path or flowsettings.KH_DATABASE
        source = Source.from_index(collection_idx, private)
        source.metadata.create_all(get_engine(database_path))
        return source

    @staticmethod
    @lru_cache
    def Index(collection_idx: int, database_path: str | None = None) -> type[Index]:
        database_path = database_path or flowsettings.KH_DATABASE
        index = Index.from_index(collection_idx)
        index.metadata.create_all(get_engine(database_path))
        return index

    @staticmethod
    def filegroup(
        collection_idx: int, database_path: str | None = None
    ) -> type[FileGroup]:
        database_path = database_path or flowsettings.KH_DATABASE
        filegroup = FileGroup.from_index(collection_idx)
        filegroup.metadata.create_all(get_engine(database_path))
        return filegroup
