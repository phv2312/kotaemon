
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.settings import settings

from app.api.v1.main import api_router as api_router_v1  # noqa: E402


app = FastAPI(
    title=settings.TITLE,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# Set all CORS enabled origins
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router_v1, prefix=settings.API_V1_PREFIX)
