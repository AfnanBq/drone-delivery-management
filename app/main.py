import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.api.api import api_router_v1

from .core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


# Lifespan (startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{settings.PROJECT_NAME} starting...")
    yield
    logger.info(f"{settings.PROJECT_NAME} shutting down...")


# FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

app.include_router(api_router_v1, prefix=settings.API_V1_STR)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    return response


@app.get("/health")
def health():
    logger.info("Health check requested")
    return {"status": "ok"}
