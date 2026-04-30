"""
Device Detection Utilities — Auto-detect best available compute device.

Provides a unified function for detecting and selecting the optimal device
(CUDA, MPS, or CPU) for inference tasks like embeddings.
"""
from app.core.utils.logging import get_logger

logger = get_logger(__name__)

# Cache the detected device to avoid repeated detection
_cached_device: str | None = None


def get_best_device(force_refresh: bool = False) -> str:
    """
    Determine the best available device for inference.
    
    Detection order: CUDA (NVIDIA GPU) > MPS (Apple Metal) > CPU
    
    Args:
        force_refresh: If True, re-detect device instead of using cache
        
    Returns:
        Device string: "cuda", "mps", or "cpu"
    """
    global _cached_device
    
    if _cached_device is not None and not force_refresh:
        return _cached_device
    
    import torch
    
    # Check for CUDA (NVIDIA GPU)
    if torch.cuda.is_available():
        logger.info("CUDA detected, using GPU for inference")
        _cached_device = "cuda"
        return _cached_device
    
    # Check for MPS (Apple Metal/Silicon)
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        try:
            # Verify MPS is functional with a simple tensor operation
            test_tensor = torch.zeros(1, device="mps")
            del test_tensor
            logger.info("MPS (Apple Metal) detected, using GPU acceleration for inference")
            _cached_device = "mps"
            return _cached_device
        except Exception as e:
            logger.warning(f"MPS available but not functional: {e}")
    
    # Fallback to CPU
    logger.info("No GPU detected, using CPU for inference")
    _cached_device = "cpu"
    return _cached_device


def get_device_info() -> dict:
    """
    Get detailed information about the detected device.
    
    Returns:
        Dictionary with device info including type, name, and memory (if applicable)
    """
    import torch
    
    device = get_best_device()
    info = {
        "device": device,
        "torch_version": torch.__version__,
    }
    
    if device == "cuda":
        info["device_name"] = torch.cuda.get_device_name(0)
        info["device_count"] = torch.cuda.device_count()
        info["memory_allocated_mb"] = torch.cuda.memory_allocated() / (1024 * 1024)
        info["memory_total_mb"] = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
    elif device == "mps":
        info["device_name"] = "Apple Metal (MPS)"
        if hasattr(torch.mps, 'current_allocated_memory'):
            info["memory_allocated_mb"] = torch.mps.current_allocated_memory() / (1024 * 1024)
    else:
        info["device_name"] = "CPU"
    
    return info
