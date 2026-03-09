"""
Unified Vector Store Service - Supports Qdrant (primary) and ChromaDB (fallback).
Uses VectorStoreFactory for production-ready, horizontally scalable vector operations.
"""
import os
import threading
from typing import Dict, Set, List, Optional, Any
import hashlib

from backend.core.logging import get_logger
from backend.pipeline.vector_stores.factory import VectorStoreFactory
from backend.pipeline.vector_stores.base import BaseVectorStore

logger = get_logger(__name__)


def get_vector_store_type() -> str:
    """Get the configured vector store type from settings."""
    try:
        from backend.services.settings_service import get_settings_service, SettingCategory
        settings_service = get_settings_service()
        vs_settings = settings_service.get_category_settings_raw(SettingCategory.VECTOR_STORE)
        return vs_settings.get('type', 'qdrant').strip('"')
    except Exception as e:
        logger.warning(f"Could not get vector store type from settings: {e}. Defaulting to qdrant.")
        return 'qdrant'


class VectorStoreManager:
    """
    Singleton manager for vector store instances.
    Provides caching and thread-safe access to vector stores.
    """
    _instances: Dict[str, BaseVectorStore] = {}
    _lock = threading.Lock()

    @classmethod
    def get_store(cls, collection_name: str, provider_type: Optional[str] = None) -> BaseVectorStore:
        """
        Get or create a vector store instance for the given collection.
        
        Args:
            collection_name: Name of the collection
            provider_type: Optional override for provider type (qdrant/chroma)
            
        Returns:
            BaseVectorStore instance
        """
        if provider_type is None:
            provider_type = get_vector_store_type()
            
        cache_key = f"{provider_type}:{collection_name}"
        
        with cls._lock:
            if cache_key not in cls._instances:
                logger.info(f"Creating new {provider_type} vector store for collection: {collection_name}")
                cls._instances[cache_key] = VectorStoreFactory.get_provider(
                    provider_type, 
                    collection_name=collection_name
                )
            return cls._instances[cache_key]
    
    @classmethod
    def clear_cache(cls, collection_name: Optional[str] = None):
        """Clear cached vector store instances."""
        with cls._lock:
            if collection_name:
                keys_to_remove = [k for k in cls._instances if k.endswith(f":{collection_name}")]
                for key in keys_to_remove:
                    del cls._instances[key]
                logger.info(f"Cleared vector store cache for collection: {collection_name}")
            else:
                cls._instances.clear()
                logger.info("Cleared all vector store caches")


def get_vector_store(collection_name: str, provider_type: Optional[str] = None) -> BaseVectorStore:
    """
    Get a vector store instance using the factory pattern.
    
    Args:
        collection_name: Name of the collection
        provider_type: Optional override (qdrant/chroma). Defaults to system setting.
        
    Returns:
        BaseVectorStore instance (QdrantStore or ChromaStore)
    """
    return VectorStoreManager.get_store(collection_name, provider_type)


async def get_vector_count(collection_name: str, provider_type: Optional[str] = None) -> tuple[int, bool]:
    """
    Get vector count from the configured vector store.
    
    Args:
        collection_name: Name of the collection
        provider_type: Optional override for provider type
        
    Returns:
        Tuple of (vector_count, collection_exists)
    """
    if provider_type is None:
        provider_type = get_vector_store_type()
    
    if provider_type == 'qdrant':
        return await _get_qdrant_vector_count(collection_name)
    else:
        return await _get_chroma_vector_count(collection_name)


async def _get_qdrant_vector_count(collection_name: str) -> tuple[int, bool]:
    """Get vector count from Qdrant."""
    try:
        import httpx
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{qdrant_url}/collections/{collection_name}")
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('result', {})
                points_count = result.get('points_count', 0)
                return points_count, True
            elif response.status_code == 404:
                return 0, False
            else:
                logger.warning(f"Qdrant returned status {response.status_code} for collection {collection_name}")
                return 0, False
    except Exception as e:
        logger.warning(f"Could not connect to Qdrant: {e}")
        return 0, False


async def _get_chroma_vector_count(collection_name: str) -> tuple[int, bool]:
    """Get vector count from ChromaDB."""
    try:
        import chromadb
        from chromadb.config import Settings
        
        chroma_path = os.getenv("CHROMA_PATH", "./data/chroma_db")
        
        # Also check indexes path
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        indexes_path = os.path.join(backend_dir, "data", "indexes", collection_name)
        
        search_paths = [
            os.path.join(chroma_path, collection_name),
            indexes_path,
            chroma_path
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                try:
                    client = chromadb.PersistentClient(
                        path=path, 
                        settings=Settings(anonymized_telemetry=False)
                    )
                    collection = client.get_collection(name=collection_name)
                    return collection.count(), True
                except ValueError:
                    continue
                except Exception:
                    continue
        
        return 0, False
    except Exception as e:
        logger.warning(f"Could not get ChromaDB count: {e}")
        return 0, False


def get_existing_chunk_ids(
    collection_name: str,
    provider_type: Optional[str] = None,
    batch_size: int = 10000
) -> Set[str]:
    """
    Get all existing document IDs from a vector store collection.
    
    Used for stateful job resuming - allows filtering out already-embedded
    documents before sending to the embedding model.
    
    Args:
        collection_name: Name of the collection to query
        provider_type: Optional provider type override
        batch_size: Number of IDs to fetch per batch (for large collections)
        
    Returns:
        Set of existing document IDs in the collection
    """
    if provider_type is None:
        provider_type = get_vector_store_type()
    
    try:
        if provider_type == 'qdrant':
            return _get_qdrant_chunk_ids(collection_name, batch_size)
        else:
            return _get_chroma_chunk_ids(collection_name, batch_size)
    except Exception as e:
        logger.warning(f"Failed to fetch existing chunk IDs: {e}")
        return set()


def _get_qdrant_chunk_ids(collection_name: str, batch_size: int) -> Set[str]:
    """Get all chunk IDs from Qdrant collection."""
    try:
        import requests
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        
        # First check if collection exists
        response = requests.get(f"{qdrant_url}/collections/{collection_name}", timeout=5)
        if response.status_code != 200:
            return set()
        
        data = response.json()
        total_points = data.get('result', {}).get('points_count', 0)
        
        if total_points == 0:
            return set()
        
        all_ids: Set[str] = set()
        offset = None
        
        while True:
            scroll_params = {
                "limit": batch_size,
                "with_payload": ["_original_id"],
                "with_vector": False
            }
            if offset:
                scroll_params["offset"] = offset
            
            response = requests.post(
                f"{qdrant_url}/collections/{collection_name}/points/scroll",
                json=scroll_params,
                timeout=30
            )
            
            if response.status_code != 200:
                break
            
            result = response.json().get('result', {})
            points = result.get('points', [])
            
            for point in points:
                payload = point.get('payload', {})
                original_id = payload.get('_original_id', str(point.get('id', '')))
                if original_id:
                    all_ids.add(original_id)
            
            offset = result.get('next_page_offset')
            if not offset or len(points) < batch_size:
                break
        
        return all_ids
        
    except Exception as e:
        logger.warning(f"Failed to fetch Qdrant chunk IDs: {e}")
        return set()


def _get_chroma_chunk_ids(collection_name: str, batch_size: int) -> Set[str]:
    """Get all chunk IDs from ChromaDB collection."""
    try:
        import chromadb
        from chromadb.config import Settings
        
        chroma_path = os.getenv("CHROMA_PATH", "./data/chroma_db")
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        indexes_path = os.path.join(backend_dir, "data", "indexes", collection_name)
        
        search_paths = [indexes_path, chroma_path]
        
        for path in search_paths:
            if not os.path.exists(path):
                continue
                
            try:
                client = chromadb.PersistentClient(
                    path=path, 
                    settings=Settings(anonymized_telemetry=False)
                )
                collection = client.get_collection(name=collection_name)
                
                count = collection.count()
                if count == 0:
                    return set()
                
                all_ids: Set[str] = set()
                offset = 0
                
                while offset < count:
                    result = collection.get(
                        limit=batch_size,
                        offset=offset,
                        include=[]
                    )
                    if result and result.get("ids"):
                        all_ids.update(result["ids"])
                    offset += batch_size
                
                return all_ids
                
            except ValueError:
                continue
        
        return set()
        
    except Exception as e:
        logger.warning(f"Failed to fetch ChromaDB chunk IDs: {e}")
        return set()


def filter_unembedded_chunks(
    documents: List,
    existing_ids: Set[str],
    id_generator: Optional[callable] = None
) -> tuple:
    """
    Filter documents to only include those not already embedded.
    
    Args:
        documents: List of documents to filter
        existing_ids: Set of IDs already in the vector store
        id_generator: Optional function to generate ID from document.
                      If None, uses default hash-based ID generation.
                      
    Returns:
        Tuple of (filtered_documents, filtered_indices, skipped_count)
        - filtered_documents: Documents that need embedding
        - filtered_indices: Original indices of filtered documents
        - skipped_count: Number of documents skipped (already embedded)
    """
    def default_id_generator(doc):
        """Generate chunk ID matching the embedding job logic."""
        content = getattr(doc, "page_content", getattr(doc, "content", ""))
        parent_id = doc.metadata.get("doc_id", "unknown") if hasattr(doc, "metadata") else "unknown"
        return hashlib.sha256(f"{content}{parent_id}".encode()).hexdigest()
    
    gen_id = id_generator or default_id_generator
    
    filtered_docs = []
    filtered_indices = []
    skipped = 0
    
    for idx, doc in enumerate(documents):
        doc_id = gen_id(doc)
        if doc_id not in existing_ids:
            filtered_docs.append(doc)
            filtered_indices.append(idx)
        else:
            skipped += 1
    
    return filtered_docs, filtered_indices, skipped


# Legacy compatibility - deprecated, use get_vector_store instead
def get_chroma_client(path: str):
    """
    DEPRECATED: Use get_vector_store() instead.
    This function is kept for backward compatibility only.
    """
    import chromadb
    from chromadb.config import Settings
    
    logger.warning("get_chroma_client() is deprecated. Use get_vector_store() for production workloads.")
    
    absolute_path = os.path.abspath(path)
    os.makedirs(absolute_path, exist_ok=True)
    return chromadb.PersistentClient(
        path=absolute_path, 
        settings=Settings(anonymized_telemetry=False)
    )


# Legacy class - deprecated
class ChromaClientManager:
    """DEPRECATED: Use VectorStoreManager instead."""
    _instances: Dict[str, Any] = {}
    _lock = threading.Lock()

    @classmethod
    def get_client(cls, path: str):
        """DEPRECATED: Use get_vector_store() instead."""
        import chromadb
        from chromadb.config import Settings
        
        logger.warning("ChromaClientManager is deprecated. Use VectorStoreManager for production workloads.")
        
        absolute_path = os.path.abspath(path)
        with cls._lock:
            if absolute_path not in cls._instances:
                os.makedirs(absolute_path, exist_ok=True)
                cls._instances[absolute_path] = chromadb.PersistentClient(
                    path=absolute_path, 
                    settings=Settings(anonymized_telemetry=False)
                )
            return cls._instances[absolute_path]
