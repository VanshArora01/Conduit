import logging
from fastapi import APIRouter
from typing import Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()

# In a real app we'd pull from Prometheus or a DB, but for now we'll just mock a response
# as the pipeline timings are returned per request.
@router.get("", response_model=Dict[str, Any])
async def get_metrics():
    return {
        "status": "online",
        "description": "Pipeline execution metrics are returned dynamically per request in the ChatQueryResponse or SSE stream under the 'timing' key."
    }
