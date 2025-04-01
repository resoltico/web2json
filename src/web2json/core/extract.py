"""
Extract module for web2json.

This module provides functionality for extracting structured content from HTML.
"""
import logging
from typing import Dict, Any, List, Optional, Union

from bs4 import BeautifulSoup, Tag, NavigableString

from web2json.utils.errors import ExtractError

# Define which HTML tags are considered style tags
STYLE_TAGS = {
    "b", "strong", "i", "em", "sup", "sub", "u", "mark",
    "small", "s", "del", "ins", "abbr", "cite", "q", "dfn",
    "time", "code", "var", "samp", "kbd", "span"
}

# Define which HTML tags are considered structural elements
STRUCTURAL_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "blockquote", "ul", "ol", "dl",
    "table", "header", "footer", "main", "article", "section", "aside"
}


def extract_content(soup: BeautifulSoup, preserve_styles: bool = False) -> List[Dict[str, Any]]:
    """Extract structured content from a parsed HTML document.
    
    Args:
        soup: BeautifulSoup object representing the parsed HTML
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        List of structured content items
        
    Raises:
        ExtractError: If extraction fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        content = []
        
        # Use CSS selectors to extract content elements
        # Process headings (h1-h6)
        for heading in soup.select("h1, h2, h3, h4, h5, h6"):
            if not _is_nested_element(heading):
                level = int(heading.name[1])
                content.append({
                    "type": "heading",
                    "level": level,
                    "text": get_element_text(heading, preserve_styles)
                })
        
        # Process paragraphs
        for paragraph in soup.select("p"):
            if not _is_nested_element(paragraph):
                text = get_element_text(paragraph, preserve_styles)
                if text.strip():  # Only add non-empty paragraphs
                    content.append({
                        "type": "paragraph",
                        "text": text
                    })
        
        # Process blockquotes
        for blockquote in soup.select("blockquote"):
            if not _is_nested_element(blockquote):
                content.append({
                    "type": "blockquote",
                    "text": get_element_text(blockquote, preserve_styles)
                })
        
        # Process lists (ul, ol)
        for list_element in soup.select("ul, ol"):
            if not _is_nested_element(list_element):
                list_type = "ordered" if list_element.name == "ol" else "unordered"
                content.append({
                    "type": "list",
                    "list_type": list_type,
                    "items": extract_list_items(list_element, preserve_styles)
                })
        
        logger.info(f"Extracted {len(content)} content items")
        return content
        
    except Exception as e:
        logger.error(f"Error extracting content: {str(e)}")
        raise ExtractError(f"Failed to extract content: {str(e)}")


def _is_nested_element(element: Tag) -> bool:
    """Check if an element is nested inside another structural element."""
    parent = element.parent
    while parent and parent.name != "body" and parent.name != "html":
        if parent.name in ("ul", "ol", "li"):
            return True
        parent = parent.parent
    return False


def get_element_text(element: Union[Tag, str], preserve_styles: bool = False) -> str:
    """Extract text from HTML element with style preservation.
    
    Args:
        element: HTML element to extract text from
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        Extracted text
    """
    # If the element is already a string, return it
    if isinstance(element, str):
        return element
    
    # Create a copy of the element to avoid modifying the original
    soup = BeautifulSoup(str(element), 'html.parser')
    
    # Always unwrap spans, regardless of preserve_styles
    for span in soup.find_all('span'):
        span.unwrap()
    
    if not preserve_styles:
        # If not preserving styles, unwrap all tags
        for tag in soup.find_all(True):
            tag.unwrap()
    else:
        # If preserving styles, only unwrap non-style tags
        for tag in soup.find_all(True):
            if tag.name not in STYLE_TAGS:
                tag.unwrap()
    
    # Get text and normalize whitespace
    return ' '.join(str(soup).split())


def get_list_text_content(li_element: Tag, preserve_styles: bool = False) -> str:
    """Get text content from list item, excluding nested lists.
    
    Args:
        li_element: List item element
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        Text content of the list item
    """
    text_parts = []
    
    for element in li_element.children:
        if isinstance(element, NavigableString):
            text_parts.append(str(element))
        elif element.name not in ('ul', 'ol'):
            if preserve_styles and element.name in STYLE_TAGS:
                text_parts.append(str(element))
            else:
                text_parts.append(element.get_text())
    
    # Normalize whitespace
    return ' '.join(' '.join(text_parts).split())


def extract_list_items(list_element: Tag, preserve_styles: bool = False) -> List[Dict[str, Any]]:
    """Extract list items with nested list handling.
    
    Args:
        list_element: List element (ul or ol)
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        List of extracted items
    """
    items = []
    
    for li in list_element.find_all("li", recursive=False):
        item_data = {"text": get_list_text_content(li, preserve_styles)}
        
        # Check for nested lists
        nested_lists = []
        for child in li.children:
            if isinstance(child, NavigableString):
                continue
            if child.name in ['ul', 'ol']:
                nested_lists.append(child)
        
        # Process nested list if present
        if nested_lists:
            nested_list = nested_lists[0]  # Take the first nested list
            nested_type = "ordered" if nested_list.name == "ol" else "unordered"
            nested_items = extract_list_items(nested_list, preserve_styles)
            
            if nested_items:
                item_data.update({
                    "type": "sublist",
                    "list_type": nested_type,
                    "items": nested_items
                })
        
        items.append(item_data)
    
    return items
