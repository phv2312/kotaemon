from concurrent.futures import Executor, ThreadPoolExecutor
from functools import lru_cache

from workflows.interface import IWorkflow
from workflows.impl.simple import SimpleWorkflow
from ..settings import settings


def get_workflow() -> IWorkflow:
    return SimpleWorkflow()


@lru_cache
def get_executor() -> Executor:
    return ThreadPoolExecutor(max_workers=settings.num_thread_worker)
