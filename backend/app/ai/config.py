from pydantic_settings import BaseSettings

class AIConfig(BaseSettings):
    """
    Configuration for the AI Engine.
    """
    # Chunking
    DEFAULT_CHUNK_SIZE: int = 1024
    DEFAULT_CHUNK_OVERLAP: int = 128

    # LLM Settings
    DEFAULT_LLM_PROVIDER: str = "gemini"
    DEFAULT_LLM_MODEL: str = "gemini-2.0-flash"

    # Embeddings
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIMENSIONS: int = 768

    # Retrieval & RAG
    RETRIEVAL_TOP_K: int = 10
    SIMILARITY_THRESHOLD_HIGH: float = 0.75
    SIMILARITY_THRESHOLD_MEDIUM: float = 0.55
    SIMILARITY_THRESHOLD_LOW: float = 0.35
    MAX_CONTEXT_TOKENS: int = 3000
    MAX_OUTPUT_TOKENS: int = 500
    MAX_HISTORY_MESSAGES: int = 6
    MAX_CHUNKS: int = 5
    DEFAULT_ANSWER_LENGTH: str = "medium"  # short | medium | detailed
    STREAM_ENABLED: bool = True

    # Caching
    QUERY_CACHE_TTL_SECONDS: int = 300

    # Qdrant
    QDRANT_DEFAULT_COLLECTION: str = "conduit_documents"

    # Execution Framework
    DEBUG_AI: bool = True
    AI_DEBUG: bool = True
    MAX_RETRIES: int = 1
    TIMEOUT_PLANNER: int = 10
    TIMEOUT_EMBEDDING: int = 10
    TIMEOUT_RETRIEVAL: int = 5
    TIMEOUT_LLM: int = 60
    TIMEOUT_STREAMING: int = 90
    HEARTBEAT_INTERVAL: int = 3  # Set to 3 seconds for heartbeats

    # Milestone 10: Planner + Executor
    ENABLE_PLANNER: bool = True          # Set to False to disable the new Planner
    PLANNER_VERSION: str = "2.1.0"
    EXECUTOR_VERSION: str = "2.1.0"
    MAX_TOOL_RETRIES: int = 1            # Max retries per tool step

ai_config = AIConfig()
