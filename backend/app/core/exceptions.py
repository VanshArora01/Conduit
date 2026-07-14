from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class AppException(Exception):
    """
    Base exception class for all application-specific errors.
    Why it exists: Allows us to differentiate between expected business logic errors
    and unexpected system errors.
    """
    def __init__(self, message: str, status_code: int = 400, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

def add_exception_handlers(app: FastAPI):
    """
    Registers centralized exception handlers for the FastAPI application.
    Why it exists: To ensure all errors (both handled and unhandled) return a 
    consistent JSON structure to the client and are properly logged.
    """
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(f"AppException: {exc.message} - Status: {exc.status_code} - ID: {request_id}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        import traceback
        import sys
        trace = traceback.format_exc()
        with open("error_trace.txt", "a") as f:
            f.write(f"CRITICAL UNHANDLED EXCEPTION: {str(exc)} - ID: {request_id}\n{trace}\n")
        print(f"CRITICAL UNHANDLED EXCEPTION: {str(exc)} - ID: {request_id}\n{trace}", file=sys.stderr)
        logger.exception(f"Unhandled exception: {str(exc)} - ID: {request_id}\n{trace}")
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "Internal server error",
                "request_id": request_id
            },
        )
