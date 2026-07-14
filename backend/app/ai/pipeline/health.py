import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.ai.vectorstore.qdrant import QdrantVectorStore
from app.ai.llm.groq_provider import GroqProvider
from app.ai.config import ai_config

logger = logging.getLogger(__name__)

class ComponentHealth:
    @staticmethod
    async def check_database(db: AsyncSession) -> bool:
        try:
            await db.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"HealthCheck - Database failed: {e}")
            return False

    @staticmethod
    async def check_qdrant() -> bool:
        try:
            vector_store = QdrantVectorStore()
            await vector_store.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"HealthCheck - Qdrant failed: {e}")
            return False

    @staticmethod
    async def check_groq() -> bool:
        try:
            provider = GroqProvider()
            await provider.client.models.list()
            return True
        except Exception as e:
            logger.error(f"HealthCheck - Groq failed: {e}")
            return False

    @staticmethod
    async def check_embedding() -> bool:
        try:
            from app.ai.embeddings.huggingface import HuggingFaceEmbeddingProvider
            provider = HuggingFaceEmbeddingProvider()
            provider.embed_text("healthcheck")
            return True
        except Exception as e:
            logger.error(f"HealthCheck - Embedding failed: {e}")
            return False

    @classmethod
    async def run_all(cls, db: AsyncSession) -> dict:
        results = {}
        logger.info("Running pre-flight health checks...")
        
        db_ok = await cls.check_database(db)
        qdrant_ok = await cls.check_qdrant()
        groq_ok = await cls.check_groq()
        embedding_ok = await cls.check_embedding()
        
        results["Database"] = db_ok
        results["Qdrant"] = qdrant_ok
        results["Groq"] = groq_ok
        results["Embeddings"] = embedding_ok
        
        for comp, status in results.items():
            mark = "✓" if status else "✗"
            logger.info(f"{comp} {mark}")
            
        return results

