"""
Request cancellation utilities for detecting client disconnection.

Provides checkpoint-based cancellation: check is_disconnected() before
expensive operations to avoid wasting resources on cancelled requests.
"""
from typing import Optional
from fastapi import Request

from backend.core.logging import get_logger

logger = get_logger(__name__)


class RequestCancelled(Exception):
    """Raised when client disconnects during request processing."""
    pass


async def check_cancelled(request: Optional[Request]) -> None:
    """
    Checkpoint: raise RequestCancelled if client has disconnected.
    
    Call this before expensive operations (LLM calls, DB queries, etc.)
    to avoid wasting resources on requests the client has abandoned.
    
    Args:
        request: FastAPI Request object. If None, does nothing (allows
                 calling process_query without cancellation support).
    
    Raises:
        RequestCancelled: If request.is_disconnected() returns True.
    
    Example:
        await check_cancelled(request)
        result = await expensive_llm_call()
    """
    if request is not None and await request.is_disconnected():
        logger.info("Client disconnected - cancelling request")
        raise RequestCancelled("Client disconnected")
