from typing import List
from google import genai
from google.genai import types
from app.ai.interfaces.embeddings import EmbeddingProvider
from app.core.config import get_settings
from app.ai.config import ai_config

class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or ai_config.DEFAULT_EMBEDDING_MODEL
        settings = get_settings()
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in configuration.")
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def embed_text(self, text: str) -> List[float]:
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=ai_config.EMBEDDING_DIMENSIONS)
        )
        return response.embeddings[0].values

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        # In actual production, we might want to chunk texts into smaller batches 
        # depending on API limits, but we'll use a straightforward implementation here.
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=texts,
            config=types.EmbedContentConfig(output_dimensionality=ai_config.EMBEDDING_DIMENSIONS)
        )
        return [e.values for e in response.embeddings]
