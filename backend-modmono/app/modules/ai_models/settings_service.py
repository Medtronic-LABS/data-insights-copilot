"""
Settings Service - Business logic for system settings.

Manages RAG, LLM, and Chunking settings.
In backend-modmono, these are stored as JSON in agent_configs table,
or we use sensible defaults when no agent is active.
"""
import json
from typing import Dict, Any, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Default Settings
# =============================================================================

DEFAULT_RAG_SETTINGS = {
    "retriever": {
        "top_k_initial": 50,
        "top_k_final": 10,
        "hybrid_weights": [0.75, 0.25],
        "rerank_enabled": True,
        "reranker_model": "BAAI/bge-reranker-base",
        "similarity_threshold": 0.5
    },
    "vector_store": {
        "store_type": "qdrant",
        "collection_prefix": "agent_"
    }
}

DEFAULT_LLM_SETTINGS = {
    "provider": "openai",
    "config": {
        "model_name": "gpt-4o",
        "temperature": 0.0,
        "max_tokens": 4096,
        "api_key_configured": True
    },
    "is_healthy": True
}

DEFAULT_CHUNKING_SETTINGS = {
    "parent_chunk_size": 800,
    "parent_chunk_overlap": 150,
    "child_chunk_size": 200,
    "child_chunk_overlap": 50,
    "batch_size": 500,
    "strategy": "recursive"
}


class SettingsService:
    """Service for managing system settings."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: Dict[str, Any] = {}
    
    async def get_rag_settings(self) -> Dict[str, Any]:
        """Get RAG settings."""
        settings = await self._get_active_config_settings("rag_config")
        if settings:
            return {**DEFAULT_RAG_SETTINGS, **settings}
        return DEFAULT_RAG_SETTINGS.copy()
    
    async def update_rag_settings(
        self,
        updates: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update RAG settings."""
        current = await self.get_rag_settings()
        if "retriever" in updates:
            current["retriever"] = {**current.get("retriever", {}), **updates["retriever"]}
        if "vector_store" in updates:
            current["vector_store"] = {**current.get("vector_store", {}), **updates["vector_store"]}
        await self._save_active_config_settings("rag_config", current)
        self._cache.pop("rag_config", None)
        return current
    
    async def get_llm_settings(self) -> Dict[str, Any]:
        """Get LLM settings."""
        settings = await self._get_active_config_settings("llm_config")
        if settings:
            result = DEFAULT_LLM_SETTINGS.copy()
            if "provider" in settings:
                result["provider"] = settings["provider"]
            if "config" in settings:
                result["config"] = {**result["config"], **settings["config"]}
            elif any(k in settings for k in ["model_name", "temperature", "max_tokens"]):
                result["config"] = {**result["config"], **settings}
            return result
        return DEFAULT_LLM_SETTINGS.copy()
    
    async def update_llm_settings(
        self,
        updates: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update LLM settings."""
        current = await self.get_llm_settings()
        if "provider" in updates:
            current["provider"] = updates["provider"]
        if "config" in updates:
            current["config"] = {**current.get("config", {}), **updates["config"]}
        await self._save_active_config_settings("llm_config", current)
        self._cache.pop("llm_config", None)
        return current
    
    async def get_chunking_settings(self) -> Dict[str, Any]:
        """Get chunking settings."""
        settings = await self._get_active_config_settings("chunking_config")
        if settings:
            return {**DEFAULT_CHUNKING_SETTINGS, **settings}
        return DEFAULT_CHUNKING_SETTINGS.copy()
    
    async def update_chunking_settings(
        self,
        updates: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update chunking settings."""
        current = await self.get_chunking_settings()
        for key in ["parent_chunk_size", "parent_chunk_overlap", 
                    "child_chunk_size", "child_chunk_overlap", 
                    "batch_size", "strategy"]:
            if key in updates:
                current[key] = updates[key]
        await self._save_active_config_settings("chunking_config", current)
        self._cache.pop("chunking_config", None)
        return current
    
    async def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """Get all settings grouped by category."""
        return {
            "rag": await self.get_rag_settings(),
            "llm": await self.get_llm_settings(),
            "chunking": await self.get_chunking_settings()
        }
    
    async def _get_active_config_settings(self, config_field: str) -> Optional[Dict[str, Any]]:
        """Get settings from the active agent config."""
        if config_field in self._cache:
            return self._cache[config_field]
        
        try:
            from app.modules.agents.models import AgentConfigModel
            
            result = await self.session.execute(
                select(AgentConfigModel).where(
                    AgentConfigModel.is_active == 1
                ).limit(1)
            )
            config = result.scalar_one_or_none()
            
            if config:
                config_value = getattr(config, config_field, None)
                if config_value:
                    settings = json.loads(config_value) if isinstance(config_value, str) else config_value
                    self._cache[config_field] = settings
                    return settings
            return None
        except Exception as e:
            logger.debug(f"Could not load settings from agent config: {e}")
            return None
    
    async def _save_active_config_settings(
        self,
        config_field: str,
        value: Dict[str, Any]
    ) -> None:
        """Save settings to the active agent config."""
        try:
            from app.modules.agents.models import AgentConfigModel
            
            result = await self.session.execute(
                select(AgentConfigModel).where(
                    AgentConfigModel.is_active == 1
                ).limit(1)
            )
            config = result.scalar_one_or_none()
            
            if config:
                value_json = json.dumps(value)
                setattr(config, config_field, value_json)
                config.updated_at = datetime.utcnow()
                await self.session.commit()
                logger.info(f"Settings saved for {config_field}")
            else:
                logger.warning(f"No active agent config found to save {config_field}")
        except Exception as e:
            logger.error(f"Error saving settings for {config_field}: {e}")
            await self.session.rollback()
            raise
    
    def clear_cache(self) -> None:
        """Clear the settings cache."""
        self._cache.clear()
