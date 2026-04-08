"""
RAG Settings API - Endpoints for RAG configuration.

Provides /settings/rag endpoints for configuring:
- Retriever settings (top_k, hybrid weights, reranking)
- Vector store settings
- General RAG pipeline configuration
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_db_session
from app.core.auth.permissions import get_current_user, require_admin
from app.core.utils.logging import get_logger
from app.modules.users.schemas import User
from app.modules.ai_models.settings_service import SettingsService

logger = get_logger(__name__)

router = APIRouter(prefix="/settings/rag", tags=["RAG Settings"])


# =============================================================================
# Request/Response Models
# =============================================================================

class RetrieverSettings(BaseModel):
    """Retriever configuration."""
    top_k_initial: int = Field(default=50, ge=1, le=200, description="Initial retrieval count")
    top_k_final: int = Field(default=10, ge=1, le=50, description="Final reranked count")
    hybrid_weights: List[float] = Field(
        default=[0.75, 0.25],
        description="Weights for dense and sparse retrieval [dense, sparse]"
    )
    rerank_enabled: bool = Field(default=True, description="Enable cross-encoder reranking")
    reranker_model: Optional[str] = Field(
        default="BAAI/bge-reranker-base",
        description="Reranker model name"
    )
    similarity_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold"
    )


class VectorStoreSettings(BaseModel):
    """Vector store configuration."""
    store_type: str = Field(default="qdrant", description="Vector store type: qdrant, chroma")
    collection_prefix: str = Field(default="agent_", description="Collection name prefix")


class RAGSettingsRequest(BaseModel):
    """RAG settings update request."""
    retriever: Optional[RetrieverSettings] = None
    vector_store: Optional[VectorStoreSettings] = None


class RAGSettingsResponse(BaseModel):
    """RAG settings response."""
    retriever: RetrieverSettings
    vector_store: VectorStoreSettings


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "",
    response_model=RAGSettingsResponse,
    summary="Get RAG settings",
    description="Get current RAG pipeline configuration."
)
async def get_rag_settings(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> RAGSettingsResponse:
    """Get current RAG settings."""
    service = SettingsService(db)
    settings = await service.get_rag_settings()
    return RAGSettingsResponse(**settings)


@router.put(
    "",
    response_model=RAGSettingsResponse,
    summary="Update RAG settings",
    description="Update RAG pipeline configuration. Requires Admin role."
)
async def update_rag_settings(
    request: RAGSettingsRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
) -> RAGSettingsResponse:
    """Update RAG settings."""
    service = SettingsService(db)
    
    try:
        update_data = {}
        if request.retriever:
            update_data["retriever"] = request.retriever.model_dump()
        if request.vector_store:
            update_data["vector_store"] = request.vector_store.model_dump()
        
        settings = await service.update_rag_settings(
            update_data,
            updated_by=str(current_user.id)
        )
        
        logger.info(f"RAG settings updated by {current_user.email}")
        return RAGSettingsResponse(**settings)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating RAG settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/defaults",
    response_model=RAGSettingsResponse,
    summary="Get default RAG settings",
    description="Get the default RAG configuration values."
)
async def get_default_rag_settings(
    current_user: User = Depends(get_current_user)
) -> RAGSettingsResponse:
    """Get default RAG settings."""
    return RAGSettingsResponse(
        retriever=RetrieverSettings(),
        vector_store=VectorStoreSettings()
    )
