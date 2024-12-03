import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.settings import settings

sys.path.append(
    str(Path(__file__).parents[3])
)  # Add root directory that flowsettings.py is located

from app.api.v1.main import api_router as api_router_v1  # noqa: E402


# TODO : Why need this function?
def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(
    title=settings.TITLE,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
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
