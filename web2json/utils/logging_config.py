"""
Logging configuration functionality.
"""
import logging
from typing import Optional

def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> None:
    """Configure logging settings."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    format_str = "%(asctime)s - %(levelname)s - %(message)s"
    
    handlers = []
    handlers.append(logging.StreamHandler())
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=log_level,
        format=format_str,
        handlers=handlers
    )