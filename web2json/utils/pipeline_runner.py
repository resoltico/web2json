"""
Utility for running web2json pipelines.

This module provides helper functions for constructing and running pipelines.
"""
from typing import Dict, Any, Optional, Union
from pathlib import Path
import logging
from ..core.pipeline import Pipeline
from ..core.pipeline.stages import (
    FetchStage,
    ParseStage,
    ExtractStage,
    TransformStage,
    ExportStage
)
from ..exceptions import Web2JsonError

def process_url(url: str, 
                output_path: Optional[Union[str, Path]] = None, 
                preserve_styles: bool = False) -> Dict[str, Any]:
    """Process a URL through the pipeline.
    
    Args:
        url: URL to process
        output_path: Path to save the output (optional)
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        The final pipeline context
        
    Raises:
        Web2JsonError: If any pipeline stage fails
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Processing URL: {url}")
    
    # Create pipeline
    pipeline = Pipeline([
        FetchStage(),
        ParseStage(),
        ExtractStage(),
        TransformStage(),
        ExportStage()
    ])
    
    # Create initial context
    context = {
        'url': url,
        'preserve_styles': preserve_styles
    }
    
    # Add output path if provided
    if output_path:
        context['output_path'] = str(output_path)
    
    try:
        # Process through pipeline
        result = pipeline.process(context)
        
        if output_path:
            # If we were exporting, log success or failure
            if result.get('exported', False):
                logger.info(f"Successfully processed {url} to {result['export_path']}")
            else:
                logger.warning(f"Processed {url} but export failed")
        else:
            # If not exporting, just log success
            logger.info(f"Successfully processed {url}")
        
        return result
    except Web2JsonError as e:
        logger.error(f"Error processing {url}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing {url}: {e}")
        raise Web2JsonError(f"Unexpected error: {e}")

def bulk_process_urls(urls: list, 
                      output_dir: Union[str, Path],
                      preserve_styles: bool = False) -> Dict[str, int]:
    """Process multiple URLs and save outputs to a directory.
    
    Args:
        urls: List of URLs to process
        output_dir: Directory to save outputs
        preserve_styles: Whether to preserve HTML style tags
        
    Returns:
        Dict with counts of success and failure
    """
    from concurrent.futures import ThreadPoolExecutor
    from ..utils.filesystem import generate_filename
    import os
    
    logger = logging.getLogger(__name__)
    logger.info(f"Processing {len(urls)} URLs")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    success_count = 0
    failure_count = 0
    
    # Function to process a single URL
    def process_single_url(url: str) -> bool:
        try:
            # Generate filename for this URL
            dir_path, filename = generate_filename(url, output_dir)
            output_path = os.path.join(dir_path, filename)
            
            # Process URL
            process_url(url, output_path, preserve_styles)
            return True
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return False
    
    # Use ThreadPoolExecutor for concurrent processing
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_single_url, urls))
    
    # Count successes and failures
    success_count = sum(results)
    failure_count = len(urls) - success_count
    
    logger.info(f"Processed {len(urls)} URLs: {success_count} succeeded, {failure_count} failed")
    
    return {
        'total': len(urls),
        'success': success_count,
        'failure': failure_count
    }
