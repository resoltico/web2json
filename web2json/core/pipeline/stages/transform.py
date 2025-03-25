"""
Transform stage for the web2json pipeline.

This stage transforms extracted content into the final document structure.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import PipelineStage
from ....exceptions import TransformError

class DocumentTransformer:
    """Transformer for creating the final document structure."""
    
    def create_document(self, 
                        title: str, 
                        content: List[Dict[str, Any]], 
                        url: str,
                        preserve_styles: bool = False,
                        meta_tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create the final document structure.
        
        Args:
            title: Document title
            content: Extracted content items
            url: Source URL
            preserve_styles: Whether styles were preserved
            meta_tags: Metadata from HTML meta tags
            
        Returns:
            Structured document
        """
        # Create metadata section
        metadata = {
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": url,
            "preserve_styles": preserve_styles
        }
        
        # Add metadata from meta tags if available
        if meta_tags:
            metadata["meta"] = meta_tags
        
        # Format and clean content items
        formatted_content = self.format_content(content)
        
        # Create the document
        document = {
            "title": title,
            "content": formatted_content,
            "metadata": metadata
        }
        
        return document
    
    def format_content(self, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format and clean content items.
        
        Args:
            content: Raw content items
            
        Returns:
            Formatted content items
        """
        # Remove None values and empty content
        formatted = []
        
        for item in content:
            if not item:
                continue
                
            # Remove None values from item
            cleaned_item = {k: v for k, v in item.items() if v is not None}
            
            # Handle nested content
            if 'content' in cleaned_item and isinstance(cleaned_item['content'], list):
                cleaned_item['content'] = self.format_content(cleaned_item['content'])
                
            # Handle nested items in lists
            if 'items' in cleaned_item and isinstance(cleaned_item['items'], list):
                cleaned_item['items'] = [
                    {k: v for k, v in i.items() if v is not None}
                    for i in cleaned_item['items']
                    if i
                ]
            
            formatted.append(cleaned_item)
            
        return formatted

class TransformStage(PipelineStage):
    """Pipeline stage for transforming content into the final structure.
    
    This stage takes extracted content from the context, transforms it
    into the final document structure, and adds it to the context for
    the next stage.
    """
    
    def __init__(self, document_transformer: Optional[DocumentTransformer] = None):
        """Initialize the transform stage.
        
        Args:
            document_transformer: Document transformer to use
        """
        super().__init__()
        self.document_transformer = document_transformer or DocumentTransformer()
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the context by transforming content.
        
        Args:
            context: Pipeline context containing 'content', 'title', and 'url'
            
        Returns:
            Updated context with 'document'
            
        Raises:
            ValueError: If required keys are missing from context
            TransformError: If transformation fails
        """
        self.validate_context(context, ['content', 'title', 'url'])
        
        self.logger.info("Transforming content into final document structure")
        
        try:
            # Get required data from context
            title = context['title']
            content = context['content']
            url = context['url']
            preserve_styles = context.get('preserve_styles', False)
            meta_tags = context.get('meta_tags')
            
            # Create the document
            document = self.document_transformer.create_document(
                title=title,
                content=content,
                url=url,
                preserve_styles=preserve_styles,
                meta_tags=meta_tags
            )
            
            # Update the context
            context['document'] = document
            
            self.logger.info("Successfully transformed content into document structure")
            return context
            
        except Exception as e:
            self.logger.error(f"Error transforming content: {str(e)}")
            raise TransformError(f"Failed to transform content: {str(e)}")
