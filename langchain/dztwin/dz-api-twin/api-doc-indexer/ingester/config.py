from pydantic_settings import BaseSettings
from typing import Optional


class IngesterSettings(BaseSettings):
    # Embedding provider (bedrock, openai, cohere, huggingface)
    EMBEDDING_PROVIDER: str = "bedrock"
    EMBEDDING_DIMENSION: int = 1024
    
    # AWS Bedrock
    AWS_REGION: str = "us-west-2"
    BEDROCK_EMBEDDING_MODEL_ID: str = "amazon.titan-embed-text-v2:0"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # HuggingFace
    HUGGINGFACE_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Qdrant
    QDRANT_USE_EMBEDDED: bool = False
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "api_docs"
    
    # Data
    CRAWLER_DATA_PATH: str = "../crawler/data"
    BATCH_SIZE: int = 32
    
    # Performance
    MAX_CONCURRENT_BATCHES: int = 5  # Number of batches to process concurrently
    
    class Config:
        env_file = ".env"
        case_sensitive = True


config = IngesterSettings()
