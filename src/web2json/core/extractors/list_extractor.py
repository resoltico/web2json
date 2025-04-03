"""
List extractor module for web2json.

This module provides functionality for extracting lists from HTML.
"""
import logging
from typing import List, Dict, Any

from bs4 import BeautifulSoup, Tag, NavigableString

from web2json.models.content import ListContent, ListItem
from web2json.utils.errors import ExtractError
from web2json.core.extractors.base import get_element_text


def extract_lists(soup: BeautifulSoup, preserve_styles: bool = False) -> List[ListContent]:
    """Extract lists from HTML content.
    
    Args:
        soup: BeautifulSoup object to extract lists from
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        List of ListContent objects
        
    Raises:
        ExtractError: If list extraction fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        lists = []
        
        # Process unordered lists
        for ul in soup.find_all("ul"):
            # Check if this list is nested inside another list
            if ul.parent.name in ("li", "ul", "ol"):
                continue  # Skip nested lists, they'll be handled by their parent
                
            list_content = ListContent(
                type="list",
                list_type="unordered",
                items=extract_list_items(ul, preserve_styles)
            )
            lists.append(list_content)
        
        # Process ordered lists
        for ol in soup.find_all("ol"):
            # Check if this list is nested inside another list
            if ol.parent.name in ("li", "ul", "ol"):
                continue  # Skip nested lists, they'll be handled by their parent
                
            list_content = ListContent(
                type="list",
                list_type="ordered",
                items=extract_list_items(ol, preserve_styles)
            )
            lists.append(list_content)
        
        logger.debug(f"Extracted {len(lists)} lists from document")
        return lists
        
    except Exception as e:
        logger.error(f"Error extracting lists: {str(e)}")
        raise ExtractError(f"Failed to extract lists: {str(e)}")


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
            # Add text node content
            text = str(element).strip()
            if text:
                text_parts.append(text)
        elif element.name not in ('ul', 'ol'):
            # Add element content if it's not a nested list
            if preserve_styles and element.name in {"b", "strong", "i", "em", "u", "code"}:
                # If preserving styles, add the element as-is
                text_parts.append(str(element))
            else:
                # Otherwise, just add the text content
                text = element.get_text().strip()
                if text:
                    text_parts.append(text)
    
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
        # Get the text content of this list item
        text = get_list_text_content(li, preserve_styles)
        
        # Create base item data
        item_data = {"text": text}
        
        # Check for nested lists
        nested_lists = []
        for child in li.children:
            if isinstance(child, Tag) and child.name in ['ul', 'ol']:
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


def detect_list_structure(element: Tag) -> Dict[str, Any]:
    """Detect the structure of a list.
    
    Args:
        element: Element that might contain a list
        
    Returns:
        Dictionary with list structure information
    """
    info = {
        "has_list": False,
        "type": None,
        "item_count": 0,
        "nested_lists": 0
    }
    
    # Check if this is a list element
    if element.name in ("ul", "ol"):
        info["has_list"] = True
        info["type"] = "ordered" if element.name == "ol" else "unordered"
        
        # Count items
        list_items = element.find_all("li", recursive=False)
        info["item_count"] = len(list_items)
        
        # Count nested lists
        nested_lists = 0
        for li in list_items:
            if li.find(["ul", "ol"]):
                nested_lists += 1
        
        info["nested_lists"] = nested_lists
    
    return info
