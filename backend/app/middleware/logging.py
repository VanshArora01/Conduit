import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log the start, duration, and status code of incoming HTTP requests.
    Relies on the RequestIDMiddleware to trace requests efficiently.
    """
    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.info(f"Request started: {request.method} {request.url.path} - ID: {request_id}")
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            logger.info(f"Request completed: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {process_time:.2f}ms - ID: {request_id}")
            return response
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(f"Request failed: {request.method} {request.url.path} - Error: {str(e)} - Duration: {process_time:.2f}ms - ID: {request_id}")
            raise
