from fastapi import APIRouter

from .routes import indexing, retrieval

api_router = APIRouter()
api_router.include_router(indexing.router, prefix="/indexing", tags=["indexing"])
api_router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
