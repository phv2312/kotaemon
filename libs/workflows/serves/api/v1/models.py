from enum import Enum

from pydantic import BaseModel


class IndexedStatus(str, Enum):
    SUCCESS = "Success"
    FAILED = "Failed"


class IndexedResponse(BaseModel):
    file: str
    file_id: str
    status: IndexedStatus
    message: str = ""


class RetrievedRequest(BaseModel):
    message: str
    file_ids: list[str] | None = None


class RetrievedMetadata(BaseModel):
    file_name: str
    file_id: str
    collection_name: str
    page_label: str = "1"


class RetrievedResponse(BaseModel):
    score: float
    text: str
    metadata: RetrievedMetadata
