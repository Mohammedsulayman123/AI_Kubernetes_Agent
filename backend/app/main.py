from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.health import router as health_router
from app.api.investigate import router as investigate_router
from app.api.kubeconfig import router as kubeconfig_router
from app.api.test_scenarios import router as test_scenarios_router
from app.api.resources import router as resources_router
from app.core.config import settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    logger.info("AI Kubernetes Agent backend starting")
    yield
    logger.info("AI Kubernetes Agent backend shutting down")


app = FastAPI(
    title="AI Kubernetes Agent",
    description="On-demand Kubernetes troubleshooting orchestrator",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(investigate_router)
app.include_router(kubeconfig_router)
app.include_router(test_scenarios_router)
app.include_router(resources_router)
