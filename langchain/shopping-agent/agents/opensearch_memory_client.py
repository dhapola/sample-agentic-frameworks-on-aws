"""
OpenSearch Agentic Memory Client

Wrapper for OpenSearch agentic memory APIs to manage customer preferences.
Uses native OpenSearch memory containers for durable, searchable storage.

Reference: https://docs.opensearch.org/latest/ml-commons-plugin/agentic-memory/
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from opensearchpy import OpenSearch

from agents.opensearch_client import get_opensearch_client
from agents.memory_cache import get_customer_memory_cache


class OpenSearchMemoryClient:
    """
    Client for managing customer preferences using OpenSearch agentic memory.

    This client provides a simple interface to store and retrieve customer
    preferences using OpenSearch's native agentic memory containers.
    """

    def __init__(self, memory_container_id: str = None, client: OpenSearch = None):
        """
        Initialize the memory client.

        Args:
            memory_container_id: ID of the memory container (from OPENSEARCH_MEMORY_CONTAINER_ID)
            client: OpenSearch client instance (optional, will create if not provided)
        """
        self.client = client or get_opensearch_client()
        self.memory_container_id = memory_container_id or os.getenv('OPENSEARCH_MEMORY_CONTAINER_ID')
        self.cache = get_customer_memory_cache()

        if not self.memory_container_id:
            raise ValueError(
                "Memory container ID not provided. "
                "Set OPENSEARCH_MEMORY_CONTAINER_ID in .env or pass as parameter. "
                "Run scripts/setup_opensearch_memory_container.py to create a container."
            )

    def add_customer_memory(
        self,
        customer_id: str,
        preferences: Dict[str, Any],
        session_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Add or update customer preferences in the memory container.

        Args:
            customer_id: Unique customer identifier
            preferences: Customer preference data (e.g., UserProfile dict)
            session_id: Optional session identifier
            tags: Optional metadata tags for the memory

        Returns:
            str: Memory ID from OpenSearch

        Example:
            >>> client = OpenSearchMemoryClient()
            >>> preferences = {
            ...     "customer_id": "user123",
            ...     "music_preferences": ["rock", "jazz", "classical"]
            ... }
            >>> memory_id = client.add_customer_memory("user123", preferences)
        """
        # Format preferences as conversational messages for agentic memory
        # OpenSearch expects messages in a conversational format
        preference_text = self._format_preferences_as_text(preferences)

        memory_data = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Customer ID: {customer_id}. Update my preferences."
                        }
                    ]
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": preference_text
                        }
                    ]
                }
            ],
            "namespace": {"customer_id": customer_id},
            "tags": tags or {"type": "user_preferences"},
            # Store preferences in document-level metadata field
            "metadata": {
                "preferences": preferences,
                "updated_at": datetime.utcnow().isoformat()
            }
        }

        # Add session ID if provided
        if session_id:
            memory_data["namespace"]["session_id"] = session_id

        try:
            response = self.client.transport.perform_request(
                'POST',
                f'/_plugins/_ml/memory_containers/{self.memory_container_id}/memories',
                body=memory_data
            )

            # OpenSearch returns 'working_memory_id' not 'memory_id'
            memory_id = response.get('working_memory_id') or response.get('memory_id')
            if not memory_id:
                raise ValueError(f"No memory_id or working_memory_id returned from OpenSearch. Response: {response}")

            # Invalidate cache since preferences were updated
            self.cache.invalidate(customer_id)
            print(f"[MemoryCache] Invalidated cache for customer_id={customer_id}")

            return memory_id

        except Exception as e:
            raise RuntimeError(f"Failed to add customer memory: {e}") from e

    def get_customer_memory(
        self,
        customer_id: str,
        session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve customer preferences from the memory container.
        Uses in-memory cache with TTL to reduce OpenSearch query latency.

        Args:
            customer_id: Unique customer identifier
            session_id: Optional session identifier

        Returns:
            Dict containing customer preferences, or None if not found

        Example:
            >>> client = OpenSearchMemoryClient()
            >>> memory = client.get_customer_memory("user123")
            >>> if memory:
            ...     print(memory['preferences']['music_preferences'])
        """
        # Check cache first (only for non-session-specific queries)
        cache_key = f"{customer_id}:{session_id}" if session_id else customer_id

        if not session_id:  # Only cache non-session-specific queries
            cached_memory = self.cache.get(cache_key)
            if cached_memory is not None:
                print(f"[MemoryCache] Hit for customer_id={customer_id}")
                return cached_memory
            else:
                print(f"[MemoryCache] Miss for customer_id={customer_id}")

        try:
            # Query the underlying system index directly
            # Memories are stored in .plugins-ml-am-{index_prefix}-memory-working
            index_name = ".plugins-ml-am-default-memory-working"

            # Search for customer's memory in the container
            # Note: namespace is a flat_object type - term query works for exact matching
            search_query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "term": {
                                    "namespace.customer_id": customer_id
                                }
                            },
                            {
                                "term": {
                                    "memory_container_id": self.memory_container_id
                                }
                            }
                        ]
                    }
                },
                "sort": [
                    {"last_updated_time": {"order": "desc"}}
                ],
                "size": 1  # Get most recent memory
            }

            # Add session filter if provided
            if session_id:
                search_query["query"]["bool"]["must"].append({
                    "term": {"namespace.session_id": session_id}
                })

            response = self.client.search(
                index=index_name,
                body=search_query
            )

            hits = response.get('hits', {}).get('hits', [])
            if not hits:
                return None

            # Extract the most recent memory
            memory_doc = hits[0]['_source']

            # Extract preferences from document-level metadata
            metadata = memory_doc.get('metadata', {})
            if 'preferences' in metadata:
                preferences = metadata['preferences']

                # flat_object type may serialize dict as JSON string, so parse if needed
                if isinstance(preferences, str):
                    import json
                    preferences = json.loads(preferences)

                result = {
                    'preferences': preferences,
                    'updated_at': memory_doc.get('last_updated_time'),
                    'memory_id': hits[0]['_id'],
                    'namespace': memory_doc.get('namespace', {})
                }

                # Cache the result (only for non-session-specific queries)
                if not session_id:
                    self.cache.set(cache_key, result)

                return result

            return None

        except Exception as e:
            # Log the error but return None to allow graceful degradation
            print(f"Warning: Failed to retrieve customer memory: {e}")
            return None

    def search_customer_memories(
        self,
        query_text: str,
        customer_id: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search customer memories using semantic search.

        Args:
            query_text: Text to search for (uses embedding model for semantic search)
            customer_id: Optional filter by specific customer
            max_results: Maximum number of results to return

        Returns:
            List of matching memory documents with relevance scores

        Example:
            >>> client = OpenSearchMemoryClient()
            >>> results = client.search_customer_memories("customers who like jazz")
        """
        search_query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "neural": {
                                "memory_embedding": {
                                    "query_text": query_text,
                                    "model_id": os.getenv('OPENSEARCH_MODEL_ID'),
                                    "k": max_results
                                }
                            }
                        }
                    ]
                }
            },
            "size": max_results
        }

        # Filter by customer if provided
        if customer_id:
            search_query["query"]["bool"]["filter"] = [
                {"term": {"namespace.customer_id": customer_id}}
            ]

        try:
            response = self.client.transport.perform_request(
                'GET',
                f'/_plugins/_ml/memory_containers/{self.memory_container_id}/memories/_search',
                body=search_query
            )

            results = []
            for hit in response.get('hits', {}).get('hits', []):
                results.append({
                    'memory_id': hit['_id'],
                    'score': hit['_score'],
                    'data': hit['_source']
                })

            return results

        except Exception as e:
            print(f"Warning: Failed to search memories: {e}")
            return []

    def delete_customer_memory(
        self,
        customer_id: str,
        memory_id: str = None
    ) -> bool:
        """
        Delete customer memories.

        Args:
            customer_id: Customer identifier
            memory_id: Specific memory ID to delete (if None, deletes all for customer)

        Returns:
            bool: True if deletion was successful
        """
        try:
            if memory_id:
                # Delete specific memory
                self.client.transport.perform_request(
                    'DELETE',
                    f'/_plugins/_ml/memory_containers/{self.memory_container_id}/memories/{memory_id}'
                )
            else:
                # Delete all memories for customer (search and delete)
                # Note: OpenSearch agentic memory doesn't have bulk delete by namespace,
                # so we need to search first then delete individually
                search_query = {
                    "query": {
                        "term": {"namespace.customer_id": customer_id}
                    },
                    "size": 100  # Adjust if customer has more than 100 memories
                }

                response = self.client.transport.perform_request(
                    'GET',
                    f'/_plugins/_ml/memory_containers/{self.memory_container_id}/memories/_search',
                    body=search_query
                )

                for hit in response.get('hits', {}).get('hits', []):
                    memory_id = hit['_id']
                    self.client.transport.perform_request(
                        'DELETE',
                        f'/_plugins/_ml/memory_containers/{self.memory_container_id}/memories/{memory_id}'
                    )

            return True

        except Exception as e:
            print(f"Warning: Failed to delete customer memory: {e}")
            return False

    def _format_preferences_as_text(self, preferences: Dict[str, Any]) -> str:
        """
        Convert preferences dictionary to natural language text.

        This helps with semantic search and LLM processing of memories.

        Args:
            preferences: Preference data dictionary

        Returns:
            str: Natural language representation of preferences
        """
        if 'music_preferences' in preferences:
            music_prefs = preferences['music_preferences']
            if isinstance(music_prefs, list):
                prefs_text = ', '.join(music_prefs)
            else:
                prefs_text = str(music_prefs)

            return f"Customer preferences updated. Music preferences: {prefs_text}."

        # Generic fallback
        parts = []
        for key, value in preferences.items():
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            parts.append(f"{key}: {value}")

        return "Customer preferences: " + "; ".join(parts) + "."


# Convenience function for backward compatibility
def get_memory_client(memory_container_id: str = None) -> OpenSearchMemoryClient:
    """
    Get an instance of the OpenSearch memory client.

    Args:
        memory_container_id: Optional container ID (uses env var if not provided)

    Returns:
        OpenSearchMemoryClient instance
    """
    return OpenSearchMemoryClient(memory_container_id=memory_container_id)
