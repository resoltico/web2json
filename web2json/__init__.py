"""
web2json - Web page to structured JSON converter
Copyright (c) 2025 Ervins Strauhmanis
Licensed under the MIT License
"""

# Import only the version from config to avoid loading dependencies too early
from .config import VERSION

__version__ = VERSION
__author__ = "Ervins Strauhmanis"
__license__ = "MIT"

# Define __all__ to specify public API but don't import everything eagerly
__all__ = [
    'validate_url',
    'fetch_page',
    'parse_content',
    'get_element_text',
    'save_json',
    'load_json',
    'expand_path',
    'is_safe_path',
    'sanitize_filename',
    'validate_output_path',
    'generate_filename',
    'setup_logging',
    'ContentSchema',
    'MetadataSchema'
]

# Import lazily when attributes are actually accessed
def __getattr__(name):
    if name in ['validate_url', 'fetch_page', 'parse_content', 'get_element_text', 'save_json', 'load_json']:
        from .core import validate_url, fetch_page, parse_content, get_element_text, save_json, load_json
        return locals()[name]
    elif name in ['expand_path', 'is_safe_path', 'sanitize_filename', 'validate_output_path', 'generate_filename', 'setup_logging']:
        from .utils import expand_path, is_safe_path, sanitize_filename, validate_output_path, generate_filename, setup_logging
        return locals()[name]
    elif name in ['ContentSchema', 'MetadataSchema']:
        from .data import ContentSchema, MetadataSchema
        return locals()[name]
    else:
        raise AttributeError(f"module 'web2json' has no attribute '{name}'")