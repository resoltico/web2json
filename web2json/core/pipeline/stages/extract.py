"""
Extract stage for the web2json pipeline.

This stage extracts structured content from parsed HTML.
"""
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup, Tag, NavigableString
from .base import PipelineStage
from ....exceptions import ExtractError
from ....config import STRUCTURAL_TAGS, STYLE_TAGS

class ContentExtractor:
    """Content extractor for HTML elements."""
    
    def __init__(self, preserve_styles: bool = False):
        """Initialize the content extractor.
        
        Args:
            preserve_styles: Whether to preserve HTML style tags
        """
        self.preserve_styles = preserve_styles
    
    def get_element_text(self, element: Any) -> str:
        """Extract text from HTML element with style preservation.
        
        Args:
            element: HTML element to extract text from
            
        Returns:
            Extracted text
        """
        soup = BeautifulSoup(str(element), 'html.parser')
        
        # Always unwrap spans, regardless of preserve_styles
        for span in soup.find_all('span'):
            span.unwrap()
            
        if not self.preserve_styles:
            for tag in soup.find_all(True):
                tag.unwrap()
        else:
            for tag in soup.find_all(True):
                if tag.name not in STYLE_TAGS:
                    tag.unwrap()
        
        return ' '.join(str(soup).split())
    
    def get_list_text_content(self, li_element: Tag) -> str:
        """Get text content from list item, excluding nested lists.
        
        Args:
            li_element: List item element
            
        Returns:
            Text content of the list item
        """
        text_parts = []
        for element in li_element.children:
            if isinstance(element, NavigableString):
                text_parts.append(str(element))
            elif element.name not in ['ul', 'ol']:
                if self.preserve_styles and element.name in STYLE_TAGS:
                    text_parts.append(str(element))
                else:
                    text_parts.append(element.get_text())
        return ' '.join(' '.join(text_parts).split())
    
    def extract_list_items(self, list_element: Tag) -> List[Dict]:
        """Extract list items with nested list handling.
        
        Args:
            list_element: List element (ul or ol)
            
        Returns:
            List of extracted items
        """
        items = []
        
        for li in list_element.find_all("li", recursive=False):
            item_data = {"text": self.get_list_text_content(li)}
            
            nested_lists = []
            for child in li.children:
                if isinstance(child, NavigableString):
                    continue
                if child.name in ['ul', 'ol']:
                    nested_lists.append(child)
            
            if nested_lists:
                nested_list = nested_lists[0]
                nested_type = "ordered" if nested_list.name == "ol" else "unordered"
                nested_items = self.extract_list_items(nested_list)
                
                if nested_items:
                    item_data.update({
                        "type": "sublist",
                        "list_type": nested_type,
                        "items": nested_items
                    })
            
            items.append(item_data)
        
        return items
    
    def extract_heading_level(self, element: Tag) -> int:
        """Extract numeric heading level from h1-h6 tags.
        
        Args:
            element: Heading element
            
        Returns:
            Heading level (1-6)
        """
        try:
            return int(element.name[1])
        except (IndexError, ValueError):
            return 1
    
    def extract_content(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract structured content from parsed HTML.
        
        Args:
            soup: Parsed BeautifulSoup object
            
        Returns:
            List of structured content items
        """
        content = []
        current_section = None
        
        for element in soup.find_all(STRUCTURAL_TAGS):
            if element.find_parent(['ul', 'ol']):
                continue
                
            if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                level = self.extract_heading_level(element)
                heading_data = {
                    "type": "heading",
                    "level": level,
                    "text": self.get_element_text(element)
                }
                content.append(heading_data)
                
                if level == 1:
                    if current_section:
                        content.append(current_section)
                    current_section = {
                        "type": "section",
                        "level": level,
                        "content": []
                    }
                    
            elif element.name == "p":
                para_data = {
                    "type": "paragraph",
                    "text": self.get_element_text(element)
                }
                content.append(para_data)
                    
            elif element.name in ["ul", "ol"]:
                list_type = "ordered" if element.name == "ol" else "unordered"
                list_data = {
                    "type": "list",
                    "list_type": list_type,
                    "level": 1,
                    "items": self.extract_list_items(element)
                }
                content.append(list_data)
                    
            elif element.name == "blockquote":
                quote_data = {
                    "type": "blockquote",
                    "text": self.get_element_text(element)
                }
                content.append(quote_data)
        
        if current_section:
            content.append(current_section)
        
        return content

class ExtractStage(PipelineStage):
    """Pipeline stage for extracting structured content.
    
    This stage takes parsed HTML from the context, extracts structured
    content, and adds it to the context for the next stage.
    """
    
    def __init__(self, content_extractor: Optional[ContentExtractor] = None):
        """Initialize the extract stage.
        
        Args:
            content_extractor: Content extractor to use
        """
        super().__init__()
        self.content_extractor = content_extractor
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the context by extracting structured content.
        
        Args:
            context: Pipeline context containing 'soup'
            
        Returns:
            Updated context with 'content'
            
        Raises:
            ValueError: If soup is missing from context
            ExtractError: If extraction fails
        """
        self.validate_context(context, ['soup', 'url', 'title'])
        
        # Get preserve_styles from context if available, default to False
        preserve_styles = context.get('preserve_styles', False)
        
        # Create content extractor if not provided
        if self.content_extractor is None:
            self.content_extractor = ContentExtractor(preserve_styles=preserve_styles)
        
        soup = context['soup']
        self.logger.info("Extracting structured content")
        
        try:
            # Extract structured content
            content = self.content_extractor.extract_content(soup)
            context['content'] = content
            
            self.logger.info(f"Successfully extracted {len(content)} content items")
            return context
            
        except Exception as e:
            self.logger.error(f"Error extracting content: {str(e)}")
            raise ExtractError(f"Failed to extract content: {str(e)}")
