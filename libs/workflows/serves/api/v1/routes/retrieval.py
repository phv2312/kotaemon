import asyncio
import logging
import time
from concurrent.futures import Executor

from fastapi import APIRouter, Depends
from workflows.interface import IWorkflow

from kotaemon.base.schema import RetrievedDocument

from ..deps import get_executor, get_workflow
from ..models import RetrievedRequest, RetrievedResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/retrieve", response_model=list[RetrievedResponse])
async def retrieve(
    payload: RetrievedRequest,
    workflow: IWorkflow = Depends(get_workflow),
    executor: Executor = Depends(get_executor),
) -> list[RetrievedResponse]:
    logger.info("Started retrieving with payload: %s", payload.model_dump())
    loop = asyncio.get_event_loop()

    start_time = time.perf_counter()
    results: list[RetrievedDocument] = await loop.run_in_executor(
        executor, workflow.retrieve, payload.message, payload.file_ids
    )
    logger.info(
        "Retrieved %d chunks in %.3f", len(results), time.perf_counter() - start_time
    )

    return [RetrievedResponse.model_validate(result.dict()) for result in results]
