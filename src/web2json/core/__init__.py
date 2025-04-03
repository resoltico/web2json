"""
Core functionality package for web2json.

This package provides the core functionality for converting web pages to JSON.
"""
# Main pipeline functions
from web2json.core.pipeline import (
    process_url, 
    bulk_process_urls, 
    get_thread_pool_sync
)

# Core modules
from web2json.core.fetch import fetch_url
from web2json.core.parse import parse_html
from web2json.core.export import export_document

# Pipeline stages
from web2json.core.pipeline_stages import (
    run_pipeline,
    PipelineStage,
    FetchStage,
    ParseStage,
    ExtractStage,
    TransformStage,
    ExportStage
)

# Pipeline stage utilities
from web2json.core.pipeline_stages.base import (
    run_in_thread,
    get_thread_pool
)

# Content extractors
from web2json.core.extractors import (
    extract_headings,
    extract_paragraphs,
    extract_lists,
    extract_code_block,
    extract_content_hierarchically
)

__all__ = [
    # Main pipeline functions
    'process_url',
    'bulk_process_urls',
    'get_thread_pool_sync',
    
    # Core modules
    'fetch_url',
    'parse_html',
    'export_document',
    
    # Pipeline stages
    'run_pipeline',
    'PipelineStage',
    'FetchStage',
    'ParseStage',
    'ExtractStage',
    'TransformStage',
    'ExportStage',
    
    # Pipeline stage utilities
    'run_in_thread',
    'get_thread_pool',
    
    # Content extractors
    'extract_headings',
    'extract_paragraphs',
    'extract_lists',
    'extract_code_block',
    'extract_content_hierarchically'
]