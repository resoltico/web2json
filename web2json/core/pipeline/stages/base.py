"""
Base class for pipeline stages.

This module defines the abstract base class for pipeline stages
used in the web2json processing pipeline.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

class PipelineStage(ABC):
    """Abstract base class for pipeline stages.
    
    A pipeline stage processes the context data and returns
    the updated context for the next stage.
    """
    
    def __init__(self):
        """Initialize the pipeline stage."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the context and return the updated context.
        
        Args:
            context: The current pipeline context
            
        Returns:
            The updated context for the next stage
            
        Raises:
            Exception: If processing fails
        """
        pass
    
    def validate_context(self, context: Dict[str, Any], required_keys: Optional[list] = None) -> bool:
        """Validate that the context contains required keys.
        
        Args:
            context: The context to validate
            required_keys: List of keys that must be present in the context
            
        Returns:
            True if the context is valid
            
        Raises:
            ValueError: If a required key is missing
        """
        if required_keys:
            for key in required_keys:
                if key not in context:
                    raise ValueError(f"Missing required key in context: {key}")
        return True
