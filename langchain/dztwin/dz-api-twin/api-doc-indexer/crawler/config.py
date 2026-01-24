from pydantic_settings import BaseSettings
from typing import Optional


class CrawlerSettings(BaseSettings):
    API_DOC_URL: str
    API_DOC_STORAGE_PATH: str = "./data"
    API_DOC_MAX_DEPTH: int = 3
    API_DOC_CRAWL_DELAY: float = 1.0
    API_DOC_MAX_PAGES: int = 100
    API_DOC_VERBOSE: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


config = CrawlerSettings()
