from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from config import IngesterSettings


class VectorStore:
    def __init__(self, config: IngesterSettings):
        self.config = config
        self.collection_name = config.QDRANT_COLLECTION_NAME
        
        if config.QDRANT_USE_EMBEDDED:
            self.client = QdrantClient(path="./qdrant_storage")
        else:
            self.client = QdrantClient(
                url=config.QDRANT_URL,
                api_key=config.QDRANT_API_KEY
            )
    
    def delete_collection(self):
        """Delete collection if exists"""
        if self.collection_exists():
            self.client.delete_collection(self.collection_name)
    
    def create_collection(self, dimension: int):
        """Create collection"""
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=dimension,
                distance=Distance.COSINE
            )
        )
    
    def add_documents(self, documents: List[Dict], vectors: List[List[float]]):
        """Add documents with their embeddings (legacy method with auto-generated IDs)"""
        points = []
        for i, (doc, vector) in enumerate(zip(documents, vectors)):
            # Generate unique ID based on content hash
            unique_id = hash(f"{doc['url']}:{doc['content'][:100]}") & 0x7FFFFFFFFFFFFFFF
            point = PointStruct(
                id=unique_id,
                vector=vector,
                payload={
                    "url": doc["url"],
                    "title": doc["title"],
                    "content": doc["content"],
                    "depth": doc.get("depth", 0)
                }
            )
            points.append(point)
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    def add_documents_with_ids(self, documents: List[Dict], vectors: List[List[float]]):
        """Add documents with their embeddings using hash-based IDs"""
        import hashlib
        points = []
        for doc, vector in zip(documents, vectors):
            # Generate deterministic ID from URL and content
            unique_str = f"{doc['url']}:{doc['content'][:100]}"
            unique_id = int(hashlib.md5(unique_str.encode()).hexdigest()[:16], 16)
            
            point = PointStruct(
                id=unique_id,
                vector=vector,
                payload={
                    "url": doc["url"],
                    "title": doc["title"],
                    "content": doc["content"],
                    "depth": doc.get("depth", 0)
                }
            )
            points.append(point)
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    def search(self, query_vector: List[float], limit: int = 5) -> List[Dict]:
        """Search for similar documents"""
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True
        )
        
        return [
            {
                "score": result.score,
                "url": result.payload["url"],
                "title": result.payload["title"],
                "content": result.payload["content"]
            }
            for result in results.points
        ]
    
    def collection_exists(self) -> bool:
        """Check if collection exists"""
        collections = self.client.get_collections().collections
        return self.collection_name in [c.name for c in collections]
    
    def get_collection_info(self):
        """Get collection information"""
        return self.client.get_collection(self.collection_name)
    
    def close(self):
        """Close the Qdrant client properly"""
        try:
            if hasattr(self.client, 'close'):
                self.client.close()
        except Exception:
            pass
