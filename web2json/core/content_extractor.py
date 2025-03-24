"""
Content extraction functionality for HTML elements.
"""
import logging
from typing import Dict, List, Any
from bs4 import BeautifulSoup, NavigableString
from ..config import STYLE_TAGS

def get_element_text(element: Any, preserve_styles: bool = False) -> str:
    """Extract text from HTML element with style preservation."""
    soup = BeautifulSoup(str(element), 'html.parser')
    
    # Always unwrap spans, regardless of preserve_styles
    for span in soup.find_all('span'):
        span.unwrap()
        
    if not preserve_styles:
        for tag in soup.find_all(True):
            tag.unwrap()
    else:
        for tag in soup.find_all(True):
            if tag.name not in STYLE_TAGS:
                tag.unwrap()
    
    return ' '.join(str(soup).split())

def get_list_text_content(li_element: Any, preserve_styles: bool = False) -> str:
    """Get text content from list item, excluding nested lists."""
    text_parts = []
    for element in li_element.children:
        if isinstance(element, NavigableString):
            text_parts.append(str(element))
        elif element.name not in ['ul', 'ol']:
            if preserve_styles and element.name in STYLE_TAGS:
                text_parts.append(str(element))
            else:
                text_parts.append(element.get_text())
    return ' '.join(' '.join(text_parts).split())

def extract_list_items(list_element: Any, preserve_styles: bool = False) -> List[Dict]:
    """Extract list items with nested list handling."""
    items = []
    
    for li in list_element.find_all("li", recursive=False):
        item_data = {"text": get_list_text_content(li, preserve_styles)}
        
        nested_lists = []
        for child in li.children:
            if isinstance(child, NavigableString):
                continue
            if child.name in ['ul', 'ol']:
                nested_lists.append(child)
        
        if nested_lists:
            nested_list = nested_lists[0]
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