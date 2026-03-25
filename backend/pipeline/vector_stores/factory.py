from backend.core.logging import get_logger
from backend.pipeline.vector_stores.base import BaseVectorStore
from backend.pipeline.vector_stores.chroma import ChromaStore
from backend.pipeline.vector_stores.qdrant import QdrantStore

logger = get_logger(__name__)

class VectorStoreFactory:
    """Factory correctly initializes the appropriate Vector Database client based on Configuration."""
    
    @staticmethod
    def get_provider(provider_type: str, collection_name: str) -> BaseVectorStore:
        provider_type = provider_type.lower().strip()
        
        if provider_type == "chroma":
            logger.debug(f"Initializing Chroma Vector Store for collection {collection_name}")
            return ChromaStore(collection_name=collection_name)
            
        elif provider_type == "qdrant":
            logger.debug(f"Initializing Qdrant Vector Store for collection {collection_name}")
            return QdrantStore(collection_name=collection_name)
            
        else:
            logger.warning(f"Unknown vector DB provider '{provider_type}'. Defaulting to Qdrant.")
            return QdrantStore(collection_name=collection_name)
    
    @staticmethod
    def get_provider_for_agent(agent_id: str, provider_type: str = "qdrant") -> BaseVectorStore:  # agent_id is UUID
        """
        Get a vector store configured for a specific agent.
        
        Uses the agent's embedding configuration to determine the collection name,
        ensuring each agent has its own isolated vector space.
        
        Args:
            agent_id: The agent ID to get the vector store for
            provider_type: The vector store provider (default: qdrant)
            
        Returns:
            A BaseVectorStore instance with the agent-specific collection
        """
        from backend.services.agent_embedding_service import get_agent_embedding_service
        
        agent_embedding_svc = get_agent_embedding_service()
        collection_name = agent_embedding_svc.get_collection_name_for_agent(agent_id)
        
        logger.debug(f"Getting vector store for agent {agent_id}, collection: {collection_name}")
        return VectorStoreFactory.get_provider(provider_type, collection_name)
    
    @staticmethod
    def get_collection_name_for_agent(agent_id: str) -> str:  # agent_id is UUID
        """
        Get the collection name for a specific agent.
        
        Convenience method for code that needs just the collection name.
        """
        from backend.services.agent_embedding_service import get_agent_embedding_service
        return get_agent_embedding_service().get_collection_name_for_agent(agent_id)
