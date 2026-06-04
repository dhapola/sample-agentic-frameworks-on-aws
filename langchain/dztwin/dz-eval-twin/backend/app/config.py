"""Application configuration settings"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "gen_ai_eval_platform"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # CORS Configuration
    # Comma-separated list of allowed origins, or use * for all origins
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # File Storage Configuration
    upload_dir: str = "uploads/datasets"
    max_file_size_mb: int = 10

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string. Returns ['*'] if wildcard is used."""
        origins = [origin.strip() for origin in self.cors_origins.split(",")]
        # If any origin is *, return just ['*']
        if "*" in origins:
            return ["*"]
        return origins


# Global settings instance
settings = Settings()
