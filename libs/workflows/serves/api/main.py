from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .settings import settings
from .v1.main import api_router as api_router_v1  # noqa: E402

app = FastAPI(
    title=settings.title,
    version=settings.version,
    docs_url=settings.docs_path,
    redoc_url=settings.redoc_path,
    openapi_url=settings.openapi_path,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router_v1, prefix=f"/{settings.api_version}")
