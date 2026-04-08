"""
Chunking Settings API - Endpoints for document chunking configuration.

Provides /settings/chunking endpoints for configuring:
- Parent chunk size and overlap
- Child chunk size and overlap
- Chunking strategy
- Batch size for embedding
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

router = APIRouter(prefix="/settings/chunking", tags=["Chunking Settings"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ParentChunkSettings(BaseModel):
    """Parent chunk configuration (used for context retrieval)."""
    chunk_size: int = Field(default=800, ge=100, le=4000, description="Parent chunk size in characters")
    chunk_overlap: int = Field(default=150, ge=0, le=500, description="Overlap between parent chunks")


class ChildChunkSettings(BaseModel):
    """Child chunk configuration (used for dense retrieval)."""
    chunk_size: int = Field(default=200, ge=50, le=1000, description="Child chunk size in characters")
    chunk_overlap: int = Field(default=50, ge=0, le=200, description="Overlap between child chunks")


class ChunkingSettingsRequest(BaseModel):
    """Chunking settings update request."""
    parent_chunk_size: Optional[int] = Field(None, ge=100, le=4000, description="Parent chunk size")
    parent_chunk_overlap: Optional[int] = Field(None, ge=0, le=500, description="Parent chunk overlap")
    child_chunk_size: Optional[int] = Field(None, ge=50, le=1000, description="Child chunk size")
    child_chunk_overlap: Optional[int] = Field(None, ge=0, le=200, description="Child chunk overlap")
    batch_size: Optional[int] = Field(None, ge=1, le=1000, description="Embedding batch size")
    strategy: Optional[str] = Field(None, description="Chunking strategy: recursive, semantic, sentence")


class ChunkingSettingsResponse(BaseModel):
    """Chunking settings response."""
    parent_chunk_size: int = Field(default=800, description="Parent chunk size")
    parent_chunk_overlap: int = Field(default=150, description="Parent chunk overlap")
    child_chunk_size: int = Field(default=200, description="Child chunk size")
    child_chunk_overlap: int = Field(default=50, description="Child chunk overlap")
    batch_size: int = Field(default=500, description="Embedding batch size")
    strategy: str = Field(default="recursive", description="Chunking strategy")


# =============================================================================
# Strategy Catalog
# =============================================================================

CHUNKING_STRATEGIES = [
    {
        "name": "recursive",
        "display_name": "Recursive Character",
        "description": "Recursively splits text by separators (paragraphs, sentences, words)",
        "best_for": "General purpose text documents",
        "is_default": True
    },
    {
        "name": "semantic",
        "display_name": "Semantic",
        "description": "Splits based on semantic meaning using embeddings",
        "best_for": "Documents where meaning boundaries matter",
        "is_default": False
    },
    {
        "name": "sentence",
        "display_name": "Sentence-based",
        "description": "Splits at sentence boundaries only",
        "best_for": "Q&A documents, structured content",
        "is_default": False
    },
    {
        "name": "token",
        "display_name": "Token-based",
        "description": "Splits based on token count for specific models",
        "best_for": "When exact token limits are critical",
        "is_default": False
    },
]


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "",
    response_model=ChunkingSettingsResponse,
    summary="Get chunking settings",
    description="Get current document chunking configuration."
)
async def get_chunking_settings(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> ChunkingSettingsResponse:
    """Get current chunking settings."""
    service = SettingsService(db)
    settings = await service.get_chunking_settings()
    return ChunkingSettingsResponse(**settings)


@router.put(
    "",
    response_model=ChunkingSettingsResponse,
    summary="Update chunking settings",
    description="Update document chunking configuration. Requires Admin role."
)
async def update_chunking_settings(
    request: ChunkingSettingsRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
) -> ChunkingSettingsResponse:
    """Update chunking settings."""
    service = SettingsService(db)
    
    try:
        # Build update dict from non-None fields
        update_data = {}
        if request.parent_chunk_size is not None:
            update_data["parent_chunk_size"] = request.parent_chunk_size
        if request.parent_chunk_overlap is not None:
            update_data["parent_chunk_overlap"] = request.parent_chunk_overlap
        if request.child_chunk_size is not None:
            update_data["child_chunk_size"] = request.child_chunk_size
        if request.child_chunk_overlap is not None:
            update_data["child_chunk_overlap"] = request.child_chunk_overlap
        if request.batch_size is not None:
            update_data["batch_size"] = request.batch_size
        if request.strategy is not None:
            # Validate strategy
            valid_strategies = [s["name"] for s in CHUNKING_STRATEGIES]
            if request.strategy not in valid_strategies:
                raise ValueError(f"Invalid strategy. Must be one of: {valid_strategies}")
            update_data["strategy"] = request.strategy
        
        # Validate overlap is less than chunk size
        settings = await service.get_chunking_settings()
        parent_size = update_data.get("parent_chunk_size", settings["parent_chunk_size"])
        parent_overlap = update_data.get("parent_chunk_overlap", settings["parent_chunk_overlap"])
        child_size = update_data.get("child_chunk_size", settings["child_chunk_size"])
        child_overlap = update_data.get("child_chunk_overlap", settings["child_chunk_overlap"])
        
        if parent_overlap >= parent_size:
            raise ValueError("Parent chunk overlap must be less than parent chunk size")
        if child_overlap >= child_size:
            raise ValueError("Child chunk overlap must be less than child chunk size")
        
        settings = await service.update_chunking_settings(
            update_data,
            updated_by=str(current_user.id)
        )
        
        logger.info(f"Chunking settings updated by {current_user.email}")
        return ChunkingSettingsResponse(**settings)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating chunking settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/strategies",
    response_model=List[Dict[str, Any]],
    summary="List chunking strategies",
    description="Get list of available chunking strategies."
)
async def list_chunking_strategies(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """List available chunking strategies."""
    service = SettingsService(db)
    current_settings = await service.get_chunking_settings()
    active_strategy = current_settings.get("strategy", "recursive")
    
    strategies = []
    for s in CHUNKING_STRATEGIES:
        strategies.append({
            **s,
            "is_active": (s["name"] == active_strategy)
        })
    
    return strategies


@router.get(
    "/defaults",
    response_model=ChunkingSettingsResponse,
    summary="Get default chunking settings",
    description="Get the default chunking configuration values."
)
async def get_default_chunking_settings(
    current_user: User = Depends(get_current_user)
) -> ChunkingSettingsResponse:
    """Get default chunking settings."""
    return ChunkingSettingsResponse()


@router.get(
    "/recommendations",
    summary="Get chunking recommendations",
    description="Get recommended chunking settings based on embedding model."
)
async def get_chunking_recommendations(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get chunking recommendations based on active embedding model."""
    from app.modules.ai_models.service import AIModelService
    
    ai_service = AIModelService(db)
    defaults = await ai_service.get_defaults()
    
    # Default recommendations
    recommendations = {
        "parent_chunk_size": 800,
        "parent_chunk_overlap": 150,
        "child_chunk_size": 200,
        "child_chunk_overlap": 50,
        "batch_size": 500,
        "strategy": "recursive",
        "reasoning": "Default settings for general purpose use"
    }
    
    if defaults.embedding:
        model = defaults.embedding
        
        # Adjust based on model's max_input_tokens/context_length
        max_tokens = model.max_input_tokens or model.context_length or 512
        
        if max_tokens >= 8192:
            # Long context models can use larger chunks
            recommendations.update({
                "parent_chunk_size": 1500,
                "parent_chunk_overlap": 200,
                "child_chunk_size": 400,
                "child_chunk_overlap": 100,
                "reasoning": f"Optimized for {model.display_name} with {max_tokens} token context"
            })
        elif max_tokens >= 2048:
            recommendations.update({
                "parent_chunk_size": 1000,
                "parent_chunk_overlap": 150,
                "child_chunk_size": 300,
                "child_chunk_overlap": 75,
                "reasoning": f"Optimized for {model.display_name} with {max_tokens} token context"
            })
        else:
            recommendations.update({
                "reasoning": f"Default settings for {model.display_name} with {max_tokens} token context"
            })
        
        # Use model's recommended chunk size if available
        if model.recommended_chunk_size:
            recommendations["child_chunk_size"] = model.recommended_chunk_size
            recommendations["reasoning"] += f" (model recommends {model.recommended_chunk_size} chunk size)"
    
    return recommendations
