"""
Transform stage for web2json pipeline.

This module provides the transform stage for creating a document from extracted content.
"""
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Union, Type, Optional

from pydantic import BaseModel

from web2json.models.document import Document, Metadata
from web2json.models.content import (
    ContentItem, HeadingContent, ParagraphContent, ListContent, 
    BlockquoteContent, CodeContent, ImageContent, TableContent, SectionContent
)
from web2json.utils.errors import TransformError
from web2json.utils.memory import clear_reference

# Type alias
Context = Dict[str, Any]


class TransformStage:
    """Pipeline stage for transforming content into a document."""
    
    async def process(self, context: Context) -> Context:
        """Process context by transforming content into a document.
        
        Args:
            context: Processing context
            
        Returns:
            Updated context with document
            
        Raises:
            TransformError: If transformation fails
        """
        logger = logging.getLogger(__name__)
        logger.info("Creating document")
        
        try:
            start_time = time.time()
            
            # Convert content items to dictionaries if they're objects
            content_list = context.get("content", [])
            content_dicts = self._convert_content_to_dicts(content_list)
            
            # Create document metadata
            metadata = Metadata(
                url=context["url"],
                fetched_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                preserve_styles=context.get("preserve_styles", False),
                meta=context.get("meta_tags", {})
            )
            
            # Create document
            document = Document(
                title=context["title"],
                content=content_dicts,
                metadata=metadata
            )
            
            elapsed = time.time() - start_time
            logger.debug(f"Transform completed in {elapsed:.2f} seconds")
            
            # Clear content list from memory as it's now in the document
            clear_reference(context, "content")
            clear_reference(context, "meta_tags")
            
            # Store results in context
            context["document"] = document
            context["transform_time"] = elapsed
            
        except Exception as e:
            logger.error(f"Error transforming content into document: {str(e)}")
            # Ensure we clean up memory even on error
            clear_reference(context, "content")
            clear_reference(context, "meta_tags")
            raise TransformError(f"Failed to transform content into document: {str(e)}")
        
        return context
    
    def _get_content_model_class(self, item_type: str) -> Optional[Type[BaseModel]]:
        """Get the appropriate content model class based on type.
        
        Args:
            item_type: Content type string
            
        Returns:
            Corresponding model class or None if not found
        """
        type_to_class = {
            "heading": HeadingContent,
            "paragraph": ParagraphContent,
            "list": ListContent,
            "blockquote": BlockquoteContent,
            "code_block": CodeContent,
            "image": ImageContent,
            "table": TableContent,
            "section": SectionContent
        }
        
        return type_to_class.get(item_type)
    
    def _convert_content_to_dicts(self, content_items: List[Any]) -> List[Dict[str, Any]]:
        """Convert content items to dictionaries recursively.
        
        Handles different types of content objects and ensures they're properly converted
        to dictionaries that can be serialized by the Document model.
        
        Args:
            content_items: List of content items
            
        Returns:
            List of content items as dictionaries
        """
        result = []
        
        for item in content_items:
            if item is None:
                continue
                
            # Handle Pydantic models by using their serialization method
            if hasattr(item, 'model_dump'):
                # Convert Pydantic model to dict
                item_dict = item.model_dump()
                
                # Handle nested content in sections
                if item_dict.get('type') == 'section' and 'content' in item_dict:
                    item_dict['content'] = self._convert_content_to_dicts(item_dict['content'])
                    
                result.append(item_dict)
                
            elif isinstance(item, dict):
                # When the item is already a dict with a 'type' field
                item_copy = item.copy()
                
                if 'type' in item_copy:
                    # Handle nested content for sections
                    if item_copy['type'] == 'section' and 'content' in item_copy:
                        item_copy['content'] = self._convert_content_to_dicts(item_copy['content'])
                    
                    # Try to convert to correct model if needed
                    model_class = self._get_content_model_class(item_copy['type'])
                    if model_class:
                        try:
                            # Try to create a model instance and convert to dict
                            model_instance = model_class(**item_copy)
                            item_copy = model_instance.model_dump()
                        except Exception as e:
                            logging.debug(f"Could not convert dict to model: {str(e)}")
                            # Continue with original dictionary
                    
                result.append(item_copy)
                
            else:
                # Try to convert to dict for other object types
                try:
                    if hasattr(item, '__dict__'):
                        item_dict = vars(item)
                        
                        # Check if this object has a type attribute
                        if 'type' in item_dict:
                            # Handle nested content for sections
                            if item_dict['type'] == 'section' and 'content' in item_dict:
                                item_dict['content'] = self._convert_content_to_dicts(item_dict['content'])
                                
                            # Try to convert to correct model if needed
                            model_class = self._get_content_model_class(item_dict['type'])
                            if model_class:
                                try:
                                    # Create model instance to ensure validation
                                    model_instance = model_class(**item_dict)
                                    item_dict = model_instance.model_dump()
                                except Exception as e:
                                    logging.debug(f"Could not convert object to model: {str(e)}")
                        
                        result.append(item_dict)
                    else:
                        # Last resort - create a generic dict with available attributes
                        generic_dict = {"type": "unknown"}
                        
                        # Try to get common attributes
                        for attr in ['text', 'level', 'items', 'language', 'caption', 'list_type', 'type']:
                            if hasattr(item, attr):
                                generic_dict[attr] = getattr(item, attr)
                                
                        # If we found a type, try to use the appropriate model
                        if 'type' in generic_dict and generic_dict['type'] != 'unknown':
                            model_class = self._get_content_model_class(generic_dict['type'])
                            if model_class:
                                try:
                                    # Create model instance to ensure validation
                                    model_instance = model_class(**generic_dict)
                                    generic_dict = model_instance.model_dump()
                                except Exception as e:
                                    logging.debug(f"Could not convert generic dict to model: {str(e)}")
                        
                        result.append(generic_dict)
                        
                except Exception as e:
                    logging.warning(f"Could not convert item to dict: {str(e)}")
        
        return result
