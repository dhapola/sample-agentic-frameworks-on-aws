from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # AI Provider
    AI_PROVIDER: str = "bedrock"
    
    # AWS Bedrock
    AWS_REGION: str = "us-west-2"
    BEDROCK_MODEL_ID: str = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Google Gemini
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Azure OpenAI
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    
    # RAG
    RAG_ENABLED: bool = False
    QDRANT_URL: Optional[str] = None
    QDRANT_COLLECTION: str = "api_docs"
    RAG_TOP_K: int = 5
    
    # Server
    API_PORT: int = 3000
    CORS_ORIGINS: str = "*"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None  # If set, logs to file
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_LLM_REQUESTS: bool = False  # Enable detailed LLM request/response logging
    
    class Config:
        env_file = ".env"
        case_sensitive = True


_config = None

def get_config() -> Settings:
    global _config
    if _config is None:
        _config = Settings()
    return _config
