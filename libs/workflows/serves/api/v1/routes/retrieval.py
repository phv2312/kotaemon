from fastapi import APIRouter, Depends
from serves.api.v1.deps import get_workflow
from workflows.interface import IWorkflow

from kotaemon.base.schema import RetrievedDocument

from ..models import RetrievedRequest, RetrievedResponse

router = APIRouter()


@router.post("/retrieve", response_model=list[RetrievedResponse])
def retrieve(
    payload: RetrievedRequest,
    workflow: IWorkflow = Depends(get_workflow),
) -> list[RetrievedResponse]:
    results: list[RetrievedDocument] = workflow.retrieve(
        text=payload.message, file_ids=payload.file_ids
    )

    return [RetrievedResponse.model_validate(result.dict()) for result in results]
