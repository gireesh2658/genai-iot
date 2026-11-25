"""
IoTSynth AI - FastAPI Application Entrypoint
"""

from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from backend.config import get_settings
from backend.exceptions import register_exception_handlers
from backend.routes.anomaly import router as anomaly_router
from backend.routes.ctgan import router as ctgan_router
from backend.routes.datasets import router as datasets_router
from backend.routes.evaluation import router as evaluation_router
from backend.routes.health import router as health_router
from backend.routes.system import router as system_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


@app.get(f"{settings.API_V1_STR}/openapi.json", include_in_schema=False)
def api_v1_openapi() -> Dict[str, Any]:
    return app.openapi()


@app.get(f"{settings.API_V1_STR}/docs", include_in_schema=False)
def api_v1_docs_redirect() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get(f"{settings.API_V1_STR}/redoc", include_in_schema=False)
def api_v1_redoc_redirect() -> RedirectResponse:
    return RedirectResponse(url="/redoc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

register_exception_handlers(app)

app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(ctgan_router, prefix=f"{settings.API_V1_STR}/ctgan")
app.include_router(datasets_router, prefix=f"{settings.API_V1_STR}/datasets")
app.include_router(evaluation_router, prefix=f"{settings.API_V1_STR}/evaluation")
app.include_router(anomaly_router, prefix=f"{settings.API_V1_STR}/anomaly")
app.include_router(system_router, prefix=f"{settings.API_V1_STR}/system")


@app.get("/", tags=["Root"])
def read_root() -> Dict[str, Any]:
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "api_v1": settings.API_V1_STR,
    }


@app.get("/health", tags=["Root"])
def health_check() -> Dict[str, str]:
    return {"status": "healthy"}
