"""
Core functionality package for web2json.
"""
from web2json.core.pipeline import process_url, bulk_process_urls, run_in_thread, get_thread_pool
from web2json.core.fetch import fetch_url
from web2json.core.parse import parse_html
from web2json.core.extract import extract_content
from web2json.core.export import export_document

__all__ = [
    'process_url',
    'bulk_process_urls',
    'run_in_thread',
    'get_thread_pool',
    'fetch_url',
    'parse_html',
    'extract_content',
    'export_document'
]