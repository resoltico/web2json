"""
Core functionality package for web2json.
"""
from .pipeline import Pipeline
from .pipeline.stages import (
    PipelineStage,
    FetchStage,
    ParseStage,
    ExtractStage, 
    TransformStage,
    ExportStage
)

# For backward compatibility - these will be deprecated in future versions
# but are provided for transition to the pipeline architecture
from .pipeline.stages.fetch import HTTPClient

def validate_url(url: str) -> bool:
    """Validate URL format and scheme (compatibility function)."""
    # Import here to avoid circular imports
    from ..utils.url import validate_url as _validate_url
    return _validate_url(url)

def fetch_page(url: str) -> str:
    """Fetch webpage content with error handling (compatibility function)."""
    client = HTTPClient()
    try:
        return client.fetch(url)
    except Exception:
        return None

def parse_content(html: str, url: str, preserve_styles: bool = False) -> dict:
    """Parse and structure content from HTML (compatibility function)."""
    # Create and run a mini-pipeline
    from .pipeline.stages.parse import HTMLParser
    from .pipeline.stages.extract import ContentExtractor
    from .pipeline.stages.transform import DocumentTransformer
    
    parser = HTMLParser()
    extractor = ContentExtractor(preserve_styles=preserve_styles)
    transformer = DocumentTransformer()
    
    try:
        # Parse HTML
        soup = parser.parse(html)
        title = parser.extract_title(soup)
        
        # Extract content
        content = extractor.extract_content(soup)
        
        # Create document
        document = transformer.create_document(
            title=title,
            content=content,
            url=url,
            preserve_styles=preserve_styles
        )
        
        return document
    except Exception as e:
        import logging
        logging.error(f"Error parsing content: {str(e)}")
        # Return minimal document on error
        return {
            "title": "Error",
            "content": [],
            "metadata": {
                "fetched_at": "",
                "url": url,
                "preserve_styles": preserve_styles,
                "error": str(e)
            }
        }

def get_element_text(element: any, preserve_styles: bool = False) -> str:
    """Extract text from HTML element with style preservation (compatibility function)."""
    from .pipeline.stages.extract import ContentExtractor
    extractor = ContentExtractor(preserve_styles=preserve_styles)
    return extractor.get_element_text(element)

def save_json(data: dict, dir_path: str, filename: str, indent: int = 2) -> bool:
    """Save structured data as JSON file (compatibility function)."""
    from .pipeline.stages.export import DocumentExporter
    from pathlib import Path
    
    exporter = DocumentExporter(indent=indent)
    try:
        exporter.validate_document(data)
        filepath = Path(dir_path) / filename
        return exporter.export_to_file(data, filepath)
    except Exception:
        return False

def load_json(filepath: str) -> dict:
    """Load JSON file with error handling (compatibility function)."""
    import json
    from .pipeline.stages.export import DocumentExporter
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        exporter = DocumentExporter()
        if exporter.validate_document(data):
            return data
    except Exception:
        pass
        
    return None

__all__ = [
    'Pipeline',
    'PipelineStage',
    'FetchStage',
    'ParseStage',
    'ExtractStage',
    'TransformStage',
    'ExportStage',
    # Compatibility functions
    'validate_url',
    'fetch_page',
    'parse_content',
    'get_element_text',
    'save_json',
    'load_json'
]
