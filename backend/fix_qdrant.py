import asyncio
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from app.core.config import get_settings
from app.ai.config import ai_config

async def main():
    s = get_settings()
    c = AsyncQdrantClient(url=s.QDRANT_URL, api_key=s.QDRANT_API_KEY)
    await c.create_payload_index(
        collection_name=ai_config.QDRANT_DEFAULT_COLLECTION, 
        field_name='document_id', 
        field_schema=qmodels.PayloadSchemaType.KEYWORD
    )
    print('Done')

if __name__ == "__main__":
    asyncio.run(main())
