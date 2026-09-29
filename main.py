from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.api.router import api_router
from app.auth.router import router as auth_router
from app.core.exception_handlers import register_exception_handlers
from app.core.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for SIP",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(auth_router)

@app.get("/")
def root():
    return {
        "application": settings.APP_NAME,
        "status": "running",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }