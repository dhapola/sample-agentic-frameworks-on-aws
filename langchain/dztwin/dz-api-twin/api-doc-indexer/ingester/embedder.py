from abc import ABC, abstractmethod
from typing import List
from langchain_aws import BedrockEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from config import IngesterSettings


class BaseEmbedder(ABC):
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass
    
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        pass


class BedrockEmbedder(BaseEmbedder):
    def __init__(self, config: IngesterSettings):
        self.embeddings = BedrockEmbeddings(
            region_name=config.AWS_REGION,
            model_id=config.BEDROCK_EMBEDDING_MODEL_ID
        )
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embeddings.embed_documents(texts)
    
    def embed_query(self, text: str) -> List[float]:
        return self.embeddings.embed_query(text)


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, config: IngesterSettings):
        self.embeddings = OpenAIEmbeddings(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_EMBEDDING_MODEL
        )
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embeddings.embed_documents(texts)
    
    def embed_query(self, text: str) -> List[float]:
        return self.embeddings.embed_query(text)


class HuggingFaceEmbedder(BaseEmbedder):
    def __init__(self, config: IngesterSettings):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=config.HUGGINGFACE_MODEL
        )
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embeddings.embed_documents(texts)
    
    def embed_query(self, text: str) -> List[float]:
        return self.embeddings.embed_query(text)


def create_embedder(config: IngesterSettings) -> BaseEmbedder:
    embedder_map = {
        "bedrock": BedrockEmbedder,
        "openai": OpenAIEmbedder,
        "huggingface": HuggingFaceEmbedder
    }
    
    embedder_class = embedder_map.get(config.EMBEDDING_PROVIDER.lower())
    if not embedder_class:
        raise ValueError(f"Unknown embedding provider: {config.EMBEDDING_PROVIDER}")
    
    return embedder_class(config)
