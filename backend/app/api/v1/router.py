from fastapi import APIRouter
from app.api.v1 import health
from app.api.v1 import auth
from app.api.v1 import integrations
from app.api.v1 import documents
from app.api.v1 import conversations
api_router = APIRouter()

# Include routers under the v1 API
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])

from app.api.v1 import metrics
api_router.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])
