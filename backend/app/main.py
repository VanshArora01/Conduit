from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.exceptions import add_exception_handlers
from app.api.v1.router import api_router
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.logging import LoggingMiddleware

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Why it exists: Provides a clean way to initialize resources (like database connections,
    caches, or loggers) at startup and dispose of them gracefully at shutdown without 
    relying on deprecated FastAPI events.
    """
    # Initialize logger and verify settings on startup
    setup_logging()
    settings = get_settings()
    
    logger.info(f"Starting application: {settings.APP_NAME}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Placeholder for database initialization if needed in the future
    # (Currently handled by dependencies for routes)
    
    yield  # Application is running
    
    logger.info("Application shutting down...")
    # Placeholder for disposing resources

def create_application() -> FastAPI:
    """
    Application factory to initialize the FastAPI application.
    Why it exists: It centralizes initialization logic, making testing easier by 
    allowing us to create test instances with different configurations. It prevents 
    global state pollution.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        lifespan=lifespan
    )

    # Register Middlewares (Order matters: outermost first)
    # RequestIDMiddleware should be first so all other middlewares have the ID
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Exception Handlers
    add_exception_handlers(app)

    # Register API Routers
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app

# The main application entry point for uvicorn
app = create_application()
