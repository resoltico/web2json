"""
Document model module for web2json.

This module defines the Pydantic models for documents.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import logging
import json

from pydantic import BaseModel, Field, field_validator, model_validator

from web2json.models.content import ContentItem
from web2json.utils.errors import ExportError


class Metadata(BaseModel):
    """Document metadata model."""
    
    url: str = Field(..., description="Source URL")
    fetched_at: str = Field(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="Timestamp when the document was fetched"
    )
    preserve_styles: bool = Field(False, description="Whether HTML styles are preserved")
    meta: Optional[Dict[str, str]] = Field(None, description="Metadata from HTML meta tags")

    @classmethod
    def create(cls, url: str, preserve_styles: bool = False) -> "Metadata":
        """Create metadata with current timestamp."""
        return cls(
            url=url,
            fetched_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            preserve_styles=preserve_styles
        )


class Document(BaseModel):
    """Main document model."""
    
    title: str = Field(..., description="Document title")
    content: List[ContentItem] = Field(default_factory=list, description="Document content")
    metadata: Metadata = Field(..., description="Document metadata")
    
    @model_validator(mode="before")
    @classmethod
    def create_metadata_from_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata from dictionary when loading from JSON."""
        # If we have metadata dictionary in input, convert to Metadata object
        if isinstance(data, dict) and "metadata" in data and isinstance(data["metadata"], dict):
            metadata_dict = data["metadata"]
            
            # If 'meta' is missing, add it as None
            if "meta" not in metadata_dict:
                metadata_dict["meta"] = None
                
            # Create metadata directly - removed redundant condition check
            data["metadata"] = Metadata(**metadata_dict)
        
        return data
    
    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        """Validate that title is not empty."""
        if not v or not v.strip():
            return "No Title"
        return v
    
    def model_dump_json(self, **kwargs) -> str:
        """Convert the model to a JSON string.
        
        Args:
            **kwargs: Arguments to pass to json.dumps
            
        Returns:
            JSON string representation of the model
            
        Raises:
            ExportError: If serialization fails
        """
        logger = logging.getLogger(__name__)
        
        try:
            # Get default options if not provided
            kwargs.setdefault("indent", 2)
            kwargs.setdefault("ensure_ascii", False)
            
            # Dump to dict first
            data = self.model_dump(mode="json")
            
            # Convert to JSON
            return json.dumps(data, **kwargs)
        except Exception as e:
            logger.error(f"Failed to serialize document to JSON: {str(e)}")
            raise ExportError(f"Failed to serialize document to JSON: {str(e)}")