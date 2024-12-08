from concurrent.futures import Executor, ThreadPoolExecutor
from functools import lru_cache
from kotaemon_workflows.workflows.interface import IWorkflow
from kotaemon_workflows.workflows.simple_workflow import SimpleWorkflow


def get_workflow() -> IWorkflow:
    return SimpleWorkflow()


@lru_cache
def get_executor(max_workers: int = 3) -> Executor:
    return ThreadPoolExecutor(max_workers=max_workers)
