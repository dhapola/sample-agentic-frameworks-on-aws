from typing import Optional, List
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_aws import BedrockEmbeddings
from config import Settings
from logger import logger


class RAGService:
    def __init__(self, config: Settings):
        self.config = config
        self.enabled = config.RAG_ENABLED
        self.client = None
        self.embeddings = None
        self.collection_name = None
        
        if self.enabled:
            try:
                self.client = QdrantClient(
                    url=config.QDRANT_URL,
                    api_key=config.QDRANT_API_KEY,
                    timeout=30.0
                ) if config.QDRANT_URL else QdrantClient(":memory:")
                self.embeddings = BedrockEmbeddings(
                    region_name=config.AWS_REGION,
                    model_id="amazon.titan-embed-text-v2:0"
                )
                self.collection_name = config.QDRANT_COLLECTION
                logger.info("RAG service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize RAG service: {e}", exc_info=True)
                logger.warning("RAG service disabled due to initialization error")
                self.enabled = False
    
    async def search(self, query: str, top_k: Optional[int] = None) -> Optional[str]:
        if not self.enabled:
            return None
        
        try:
            # Generate query embedding
            query_vector = self.embeddings.embed_query(query)
            
            # Search in Qdrant using query_points (new API)
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k or self.config.RAG_TOP_K,
                with_payload=True
            )
            
            if not results.points:
                if self.config.LOG_LLM_REQUESTS:
                    logger.info(f"RAG search returned no results for query: {query[:100]}...")
                return None
            
            # Log retrieved documents if enabled
            if self.config.LOG_LLM_REQUESTS:
                logger.info(f"RAG search query: {query}")
                logger.info(f"Retrieved {len(results.points)} documents:")
                for i, result in enumerate(results.points, 1):
                    url = result.payload.get("url", "N/A")
                    score = result.score
                    content_preview = result.payload.get("content", "")[:200]
                    logger.info(f"  Document {i}: score={score:.4f}, url={url}")
                    logger.debug(f"  Content preview: {content_preview}...")
            
            # Format context from results
            context_parts = []
            sources = []
            for i, result in enumerate(results.points, 1):
                content = result.payload.get("content", "")
                url = result.payload.get("url", "")
                title = result.payload.get("title", f"Document {i}")
                
                # Add content with source reference
                context_parts.append(f"[Source {i}: {title}]\n{content}")
                
                # Collect source for citation
                sources.append(f"Source {i}: {title} - {url}")
            
            # Combine context with sources list at the end
            context_text = "\n\n---\n\n".join(context_parts)
            sources_text = "\n".join(sources)
            
            return f"{context_text}\n\n---\n\nSOURCE URLS (include these in your response):\n{sources_text}"
        
        except Exception as e:
            logger.error(f"RAG search error: {e}", exc_info=True)
            return None
