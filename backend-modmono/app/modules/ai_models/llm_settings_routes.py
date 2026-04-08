"""
LLM Settings API - Endpoints for LLM configuration.

Provides /settings/llm endpoints for configuring:
- LLM provider selection (OpenAI, Azure, Anthropic, etc.)
- Model parameters (temperature, max_tokens)
- Provider-specific configuration
"""
from typing import Dict, Any, Optional, List, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_db_session
from app.core.auth.permissions import get_current_user, require_admin
from app.core.utils.logging import get_logger
from app.modules.users.schemas import User
from app.modules.ai_models.service import AIModelService
from app.modules.ai_models.settings_service import SettingsService

logger = get_logger(__name__)

router = APIRouter(prefix="/settings/llm", tags=["LLM Settings"])


# =============================================================================
# Request/Response Models
# =============================================================================

class LLMProviderConfig(BaseModel):
    """LLM provider configuration."""
    provider: Literal["openai", "azure", "anthropic", "ollama", "huggingface", "local"] = Field(
        default="openai",
        description="LLM provider type"
    )
    model_name: str = Field(default="gpt-4o", description="Model name/identifier")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=4096, ge=1, le=128000, description="Maximum output tokens")
    api_key_configured: bool = Field(default=True, description="Whether API key is configured")


class LLMSettingsRequest(BaseModel):
    """LLM settings update request."""
    provider: Optional[Literal["openai", "azure", "anthropic", "ollama", "huggingface", "local"]] = None
    config: Optional[Dict[str, Any]] = Field(default=None, description="Provider-specific configuration")
    reason: Optional[str] = Field(default=None, description="Reason for the change")


class LLMSettingsResponse(BaseModel):
    """LLM settings response."""
    provider: str
    config: Dict[str, Any]
    is_healthy: bool = True


class LLMProviderInfo(BaseModel):
    """Information about an LLM provider."""
    name: str
    display_name: str
    description: str
    requires_api_key: bool
    requires_endpoint: bool = False
    is_active: bool
    default_config: Dict[str, Any]
    models: List[str]


class LLMValidationRequest(BaseModel):
    """Request to validate LLM configuration."""
    provider: str = Field(..., description="Provider type to validate")
    config: Dict[str, Any] = Field(..., description="Configuration to validate")


# =============================================================================
# Provider Catalog
# =============================================================================

LLM_PROVIDERS = [
    {
        "name": "openai",
        "display_name": "OpenAI",
        "description": "OpenAI GPT models (GPT-4, GPT-3.5)",
        "requires_api_key": True,
        "requires_endpoint": False,
        "default_config": {
            "model_name": "gpt-4o",
            "temperature": 0.0,
            "max_tokens": 4096
        },
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o1-preview", "o1-mini"]
    },
    {
        "name": "azure",
        "display_name": "Azure OpenAI",
        "description": "Azure-hosted OpenAI models",
        "requires_api_key": True,
        "requires_endpoint": True,
        "default_config": {
            "deployment_name": "",
            "api_version": "2024-02-01",
            "temperature": 0.0,
            "max_tokens": 4096
        },
        "models": []
    },
    {
        "name": "anthropic",
        "display_name": "Anthropic Claude",
        "description": "Anthropic Claude models (Claude 3.5, Claude 3)",
        "requires_api_key": True,
        "requires_endpoint": False,
        "default_config": {
            "model_name": "claude-3-5-sonnet-20241022",
            "temperature": 0.0,
            "max_tokens": 4096
        },
        "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
    },
    {
        "name": "ollama",
        "display_name": "Ollama (Local)",
        "description": "Locally running models via Ollama",
        "requires_api_key": False,
        "requires_endpoint": True,
        "default_config": {
            "model_name": "llama3.1",
            "base_url": "http://localhost:11434",
            "temperature": 0.0,
            "max_tokens": 4096
        },
        "models": ["llama3.1", "llama3.1:70b", "mistral", "mixtral", "codellama", "phi3"]
    },
]


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "",
    response_model=LLMSettingsResponse,
    summary="Get LLM settings",
    description="Get current LLM provider configuration."
)
async def get_llm_settings(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> LLMSettingsResponse:
    """Get current LLM settings."""
    service = SettingsService(db)
    settings = await service.get_llm_settings()
    return LLMSettingsResponse(**settings)


@router.put(
    "",
    response_model=LLMSettingsResponse,
    summary="Update LLM settings",
    description="Update LLM provider configuration. Requires Admin role."
)
async def update_llm_settings(
    request: LLMSettingsRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
) -> LLMSettingsResponse:
    """Update LLM settings."""
    service = SettingsService(db)
    
    try:
        update_data = {}
        if request.provider:
            update_data["provider"] = request.provider
        if request.config:
            update_data["config"] = request.config
        
        settings = await service.update_llm_settings(
            update_data,
            updated_by=str(current_user.id)
        )
        
        logger.info(f"LLM settings updated by {current_user.email}")
        return LLMSettingsResponse(**settings)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating LLM settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/providers",
    response_model=List[LLMProviderInfo],
    summary="List LLM providers",
    description="Get list of available LLM providers."
)
async def list_llm_providers(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> List[LLMProviderInfo]:
    """List available LLM providers."""
    service = SettingsService(db)
    current_settings = await service.get_llm_settings()
    active_provider = current_settings.get("provider", "openai")
    
    providers = []
    for p in LLM_PROVIDERS:
        providers.append(LLMProviderInfo(
            name=p["name"],
            display_name=p["display_name"],
            description=p["description"],
            requires_api_key=p["requires_api_key"],
            requires_endpoint=p.get("requires_endpoint", False),
            is_active=(p["name"] == active_provider),
            default_config=p["default_config"],
            models=p["models"]
        ))
    
    return providers


@router.post(
    "/validate",
    summary="Validate LLM configuration",
    description="Test LLM configuration without saving."
)
async def validate_llm_config(
    request: LLMValidationRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Validate LLM provider configuration."""
    # Find provider in catalog
    provider_info = None
    for p in LLM_PROVIDERS:
        if p["name"] == request.provider:
            provider_info = p
            break
    
    if not provider_info:
        return {
            "success": False,
            "provider": request.provider,
            "error": f"Unknown provider: {request.provider}"
        }
    
    # Check if API key is required and provided
    if provider_info["requires_api_key"]:
        import os
        api_key = request.config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {
                "success": False,
                "provider": request.provider,
                "error": "API key is required but not configured"
            }
    
    # Basic validation passed
    return {
        "success": True,
        "provider": request.provider,
        "message": "Configuration appears valid"
    }


@router.get(
    "/health",
    summary="Check LLM health",
    description="Check health of active LLM provider."
)
async def check_llm_health(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check LLM provider health."""
    service = SettingsService(db)
    settings = await service.get_llm_settings()
    
    # Simple health check - verify API key is configured
    import os
    api_key_configured = bool(os.environ.get("OPENAI_API_KEY"))
    
    return {
        "healthy": api_key_configured,
        "provider": settings.get("provider", "openai"),
        "message": "API key configured" if api_key_configured else "API key not configured"
    }


@router.get(
    "/models",
    response_model=List[Dict[str, Any]],
    summary="List LLM models",
    description="List all registered LLM models."
)
async def list_llm_models(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """List all registered LLM models from the AI Models registry."""
    service = AIModelService(db)
    result = await service.list_models(model_type="llm")
    
    models = []
    for model in result.models:
        models.append({
            "id": model.id,
            "model_name": model.model_id,
            "display_name": model.display_name,
            "provider": model.provider_name,
            "is_active": model.is_default,
            "context_length": model.context_length,
            "deployment_type": model.deployment_type,
            "is_ready": model.is_ready,
        })
    
    return models
