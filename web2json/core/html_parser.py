"""
HTML parsing and structure analysis functionality.
"""
import logging
from typing import Dict, List, Any
from bs4 import BeautifulSoup, NavigableString
from datetime import datetime
from ..config import STRUCTURAL_TAGS
from .content_extractor import get_element_text, extract_list_items

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