from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging
from app.db.session import get_db
from app.core.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health", summary="Health check endpoint", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Returns the health status of the application and verifies database connectivity.
    Why it exists: Used by load balancers and orchestrators (like Docker/Kubernetes) 
    to ensure the service and its dependencies are running correctly.
    """
    settings = get_settings()
    
    try:
        # Verify database connection
        await db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "database": "connected",
            "service": "conduit-api",
            "version": "0.1.0"
        }
    except Exception as e:
        # Log the error gracefully on the server without leaking stack traces to the client
        logger.error(f"Database health check failed: {str(e)}")
        
        # Return 503 Service Unavailable with the requested JSON structure
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "service": "conduit-api",
                "version": "0.1.0"
            }
        )

@router.get("/health/ai", summary="AI Engine components health check", status_code=status.HTTP_200_OK)
async def health_check_ai(db: AsyncSession = Depends(get_db)):
    """
    Checks health of Postgres, Qdrant, Groq, and Huggingface Embeddings.
    """
    from app.ai.pipeline.health import ComponentHealth
    
    results = await ComponentHealth.run_all(db)
    
    all_healthy = all(results.values())
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    response_content = {
        "status": "healthy" if all_healthy else "unhealthy",
        "details": {
            "postgres": "healthy" if results.get("Database") else "unhealthy",
            "qdrant": "healthy" if results.get("Qdrant") else "unhealthy",
            "groq": "healthy" if results.get("Groq") else "unhealthy",
            "embeddings": "healthy" if results.get("Embeddings") else "unhealthy"
        }
    }
    
    if all_healthy:
        return response_content
    else:
        return JSONResponse(status_code=status_code, content=response_content)

