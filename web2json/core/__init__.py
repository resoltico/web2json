"""
Core functionality package for web2json.
"""
from .url_processor import validate_url, fetch_page
from .html_parser import parse_content, get_element_text
from .json_converter import save_json, load_json

__all__ = [
    'validate_url',
    'fetch_page',
    'parse_content',
    'get_element_text',
    'save_json',
    'load_json'
]