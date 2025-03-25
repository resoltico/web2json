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

# Define __all__ to specify public API
__all__ = [
    # Core pipeline
    'Pipeline',
    'PipelineStage',
    
    # Pipeline stages
    'FetchStage',
    'ParseStage',
    'ExtractStage',
    'TransformStage',
    'ExportStage',
    
    # Utility functions
    'process_url',
    'bulk_process_urls',
    'validate_url',
    
    # Legacy functions (for backward compatibility)
    'fetch_page',
    'parse_content',
    'get_element_text',
    'save_json',
    'load_json',
    'expand_path',
    'is_safe_path',
    'sanitize_filename',
    'validate_output_path',
    'generate_filename'
]

# Import lazily when attributes are actually accessed
def __getattr__(name):
    if name in ['Pipeline', 'PipelineStage', 'FetchStage', 'ParseStage', 'ExtractStage', 'TransformStage', 'ExportStage']:
        if name == 'Pipeline':
            from .core.pipeline import Pipeline
            return Pipeline
        else:
            from .core.pipeline.stages import (
                PipelineStage, FetchStage, ParseStage, ExtractStage, TransformStage, ExportStage
            )
            return locals()[name]
    
    elif name in ['process_url', 'bulk_process_urls', 'validate_url']:
        if name == 'validate_url':
            from .utils.url import validate_url
            return validate_url
        else:
            from .utils.pipeline_runner import process_url, bulk_process_urls
            return locals()[name]
    
    elif name in ['fetch_page', 'parse_content', 'get_element_text', 'save_json', 'load_json']:
        from .core import fetch_page, parse_content, get_element_text, save_json, load_json
        return locals()[name]
        
    elif name in ['expand_path', 'is_safe_path', 'sanitize_filename', 'validate_output_path', 'generate_filename']:
        from .utils.filesystem import expand_path, is_safe_path, sanitize_filename, validate_output_path, generate_filename
        return locals()[name]
        
    else:
        raise AttributeError(f"module 'web2json' has no attribute '{name}'")
