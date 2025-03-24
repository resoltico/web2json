"""
HTML parsing and content extraction functionality.
"""
import logging
from typing import Dict, List, Any
from bs4 import BeautifulSoup, NavigableString
from datetime import datetime
from ..config import STYLE_TAGS, STRUCTURAL_TAGS

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

def extract_heading_level(element: Any) -> int:
    """Extract numeric heading level from h1-h6 tags."""
    try:
        return int(element.name[1])
    except (IndexError, ValueError):
        logging.warning(f"Invalid heading element: {element.name}")
        return 1

def parse_content(html: str, url: str, preserve_styles: bool = False) -> Dict:
    """Parse and structure content from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    
    # Handle malformed HTML better for title extraction
    title_elem = soup.find("h1")
    if title_elem:
        # Get only the direct text of h1, not its descendants
        title = ''.join(
            text for text in title_elem.contents 
            if isinstance(text, NavigableString)
        ).strip()
    else:
        title_meta = soup.find("meta", property="og:title")
        title = title_meta.get("content", "No Title") if title_meta else "No Title"
    
    content = []
    current_section = None
    
    for element in soup.find_all(STRUCTURAL_TAGS):
        if element.find_parent(['ul', 'ol']):
            continue
            
        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = extract_heading_level(element)
            heading_data = {
                "type": "heading",
                "level": level,
                "text": get_element_text(element, preserve_styles)
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
                "text": get_element_text(element, preserve_styles)
            }
            content.append(para_data)
                
        elif element.name in ["ul", "ol"]:
            list_type = "ordered" if element.name == "ol" else "unordered"
            list_data = {
                "type": "list",
                "list_type": list_type,
                "level": 1,
                "items": extract_list_items(element, preserve_styles)
            }
            content.append(list_data)
                
        elif element.name == "blockquote":
            quote_data = {
                "type": "blockquote",
                "text": get_element_text(element, preserve_styles)
            }
            content.append(quote_data)
    
    if current_section:
        content.append(current_section)
    
    return {
        "title": title,
        "content": content,
        "metadata": {
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": url,
            "preserve_styles": preserve_styles
        }
    }