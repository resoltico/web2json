"""
Utility functions package for web2json.
"""
from web2json.utils.url import validate_url, normalize_url, extract_domain
from web2json.utils.filesystem import (
    generate_filename, 
    sanitize_filename,
    ensure_directory,
    expand_path,
    validate_output_path
)
from web2json.utils.errors import (
    Web2JsonError, 
    FetchError,
    ParseError,
    ExportError,
    Result
)
from web2json.utils.memory import (
    clear_reference,
    optimize_memory_settings,
    memory_status,
    get_object_size,
    clear_memory_aggressively
)

__all__ = [
    'validate_url',
    'normalize_url',
    'extract_domain',
    'generate_filename',
    'sanitize_filename',
    'ensure_directory',
    'expand_path',
    'validate_output_path',
    'Web2JsonError',
    'FetchError',
    'ParseError',
    'ExportError',
    'Result',
    'clear_reference',
    'optimize_memory_settings',
    'memory_status',
    'get_object_size',
    'clear_memory_aggressively'
]