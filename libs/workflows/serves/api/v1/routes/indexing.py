import asyncio
import logging
import shutil
import time
from concurrent.futures import Executor
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from workflows.interface import IWorkflow

from ...settings import AppSettings
from ..deps import get_executor, get_settings, get_workflow
from ..models import IndexedResponse, IndexedStatus

router = APIRouter()
logger = logging.getLogger(__name__)


def index_single(
    filepath: Path,
    workflow: IWorkflow,
) -> IndexedResponse:
    indexed_ids, errors, _ = workflow.index([filepath])
    if len(indexed_ids) != 1:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing for {filepath.name} returned unexpected tuple",
        )

    if len(errors) > 0 and errors[0] is not None:
        # error
        return IndexedResponse(
            file=filepath.name,
            file_id=indexed_ids[0],
            status=IndexedStatus.FAILED,
            message=str(errors[0]),
        )

    # success
    return IndexedResponse(
        file=filepath.name,
        file_id=indexed_ids[0],
        status=IndexedStatus.SUCCESS,
    )


@router.post("/index", response_model=list[IndexedResponse])
async def indexing(
    files: list[UploadFile] = File(...),
    settings: AppSettings = Depends(get_settings),
    workflow: IWorkflow = Depends(get_workflow),
    executor: Executor = Depends(get_executor),
) -> list[IndexedResponse]:
    """Batch indexing API"""
    logger.info("Started indexing for %d file(s)", len(files))
    loop = asyncio.get_event_loop()
    responses: list[IndexedResponse] = []

    with TemporaryDirectory() as temp_dir:
        local_files: list[Path] = []

        start_time = time.perf_counter()
        for file in files:
            local_file = Path(temp_dir) / file.filename

            with local_file.open("wb") as file_content:
                shutil.copyfileobj(file.file, file_content)

            local_files.append(local_file)
        logger.info(
            "Saved %d files to temporary storage takes %.3f",
            len(local_files),
            time.perf_counter() - start_time,
        )

        num_files: int = len(local_files)
        batched_idxs = [
            (start_idx, min(start_idx + settings.batch_size, num_files))
            for start_idx in range(0, num_files, settings.batch_size)
        ]

        for start_idx, end_idx in batched_idxs:
            start_time = time.perf_counter()
            batched_files = local_files[start_idx:end_idx]
            batched_responses = await asyncio.gather(
                *[
                    loop.run_in_executor(
                        executor, index_single, indexing_file, workflow
                    )
                    for indexing_file in batched_files
                ]
            )
            responses.extend(batched_responses)
            logger.info(
                "Indexed for batch: [%d-%d] takes %.3f",
                start_idx,
                end_idx,
                time.perf_counter() - start_time,
            )

    return responses
