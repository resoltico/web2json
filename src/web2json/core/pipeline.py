"""
Main pipeline module for web2json.

This module provides high-level functions for processing URLs through the pipeline.
"""
import asyncio
import gc
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from web2json.core.pipeline_stages import (
    run_pipeline,
    FetchStage,
    ParseStage,
    ExtractStage,
    TransformStage,
    ExportStage
)
from web2json.core.pipeline_stages.base import get_thread_pool
from web2json.utils.errors import Web2JsonError
from web2json.utils.memory import optimize_memory_settings, clear_reference
from web2json.utils.url import validate_url

# Type alias
Result = Dict[str, Any]


async def process_url(
    url: str,
    output_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    preserve_styles: bool = False,
    timeout: int = 60,
) -> Result:
    """Process a single URL through the pipeline.
    
    Args:
        url: URL to process
        output_path: Optional specific output path for the document
        output_dir: Directory to save output (if output_path not provided)
        preserve_styles: Whether to preserve HTML styles in content
        timeout: Timeout in seconds for each stage
        
    Returns:
        Dictionary with processing results
        
    Raises:
        Web2JsonError: If processing fails
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Processing URL: {url}")
    
    # Validate the URL
    if not validate_url(url):
        return {
            "success": False,
            "url": url,
            "error": "Invalid URL format"
        }
    
    # Use a context manager to ensure proper thread pool shutdown
    async with get_thread_pool() as executor:
        # Create pipeline stages with shared executor
        stages = [
            FetchStage(),
            ParseStage(executor=executor),
            ExtractStage(executor=executor),
            TransformStage(),
            ExportStage(executor=executor),
        ]
        
        # Prepare initial context
        context = {
            "url": url,
            "preserve_styles": preserve_styles,
            "timeout": timeout,
            "start_time": time.time(),
        }
        
        if output_path:
            context["output_path"] = output_path
        
        if output_dir:
            context["output_dir"] = output_dir
        
        try:
            # Process through pipeline
            result = await run_pipeline(stages, context)
            
            # Calculate total processing time
            total_time = time.time() - context["start_time"]
            
            # Clear document from memory after export
            clear_reference(result, "document", force_gc=True)
            
            # Prepare success result
            return {
                "success": True,
                "url": url,
                "output_path": result["output_path"],
                "processing_time": total_time,
                "stages": {
                    "fetch": result.get("fetch_time"),
                    "parse": result.get("parse_time"),
                    "extract": result.get("extract_time"),
                    "transform": result.get("transform_time"),
                    "export": result.get("export_time"),
                },
                "content_stats": result.get("content_stats", {})
            }
            
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout processing {url}: {e}")
            # Force garbage collection after error
            gc.collect()
            return {
                "success": False,
                "url": url,
                "error": f"Operation timed out after {timeout} seconds"
            }
            
        except Web2JsonError as e:
            logger.error(f"Error processing {url}: {e}")
            # Force garbage collection after error
            gc.collect()
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }
            
        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {e}")
            # Force garbage collection after error
            gc.collect()
            return {
                "success": False,
                "url": url,
                "error": f"Unexpected error: {e}"
            }


async def bulk_process_urls(
    urls: List[str],
    output_dir: Path,
    preserve_styles: bool = False,
    max_concurrency: int = 5,
    timeout: int = 60,
) -> List[Result]:
    """Process multiple URLs in parallel.
    
    Args:
        urls: List of URLs to process
        output_dir: Directory to save outputs
        preserve_styles: Whether to preserve HTML styles
        max_concurrency: Maximum number of concurrent requests
        timeout: Timeout in seconds for each stage
        
    Returns:
        List of processing results for each URL
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Processing {len(urls)} URLs with concurrency {max_concurrency}")
    
    # Configure garbage collection for optimal performance
    optimize_memory_settings()
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process URLs with bounded concurrency and proper resource management
    async def process_with_semaphore(semaphore, executor, url: str) -> Result:
        """Process a URL with semaphore for concurrency control."""
        start_time = time.time()
        
        # Skip invalid URLs
        if not validate_url(url):
            return {
                "success": False,
                "url": url,
                "error": "Invalid URL format"
            }
        
        # Use semaphore to limit concurrency
        async with semaphore:
            logger.debug(f"Starting processing of {url}")
            
            # Create pipeline stages with shared executor
            stages = [
                FetchStage(),
                ParseStage(executor=executor),
                ExtractStage(executor=executor),
                TransformStage(),
                ExportStage(executor=executor),
            ]
            
            # Prepare initial context
            context = {
                "url": url,
                "preserve_styles": preserve_styles,
                "output_dir": output_dir,
                "timeout": timeout,
                "start_time": start_time,
            }
            
            try:
                # Process through pipeline
                result = await run_pipeline(stages, context)
                
                # Calculate total processing time
                total_time = time.time() - start_time
                
                # Clear document from memory after export
                clear_reference(context, "document", force_gc=True)
                
                return {
                    "success": True,
                    "url": url,
                    "output_path": result["output_path"],
                    "processing_time": total_time,
                    "content_stats": result.get("content_stats", {})
                }
                
            except asyncio.TimeoutError as e:
                logger.error(f"Timeout processing {url}: {e}")
                # Force garbage collection after error
                gc.collect()
                return {
                    "success": False,
                    "url": url,
                    "error": f"Operation timed out after {timeout} seconds"
                }
                
            except Web2JsonError as e:
                logger.error(f"Error processing {url}: {e}")
                # Force garbage collection after error
                gc.collect()
                return {
                    "success": False,
                    "url": url,
                    "error": str(e)
                }
                
            except Exception as e:
                logger.error(f"Unexpected error processing {url}: {e}")
                # Force garbage collection after error
                gc.collect()
                return {
                    "success": False,
                    "url": url,
                    "error": f"Unexpected error: {e}"
                }
    
    # Use a single thread pool for all URLs and create a semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrency)
    
    # Process URLs with proper error handling
    async with get_thread_pool() as executor:
        # Create tasks for all URLs with proper resource management
        tasks = [process_with_semaphore(semaphore, executor, url) for url in urls]
        
        # Wait for all tasks to complete 
        results = []
        
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                results.append(result)
                
                # Log progress
                completed = len(results)
                if completed % 5 == 0 or completed == len(urls):
                    success_count = sum(1 for r in results if r.get("success", False))
                    logger.info(f"Progress: {completed}/{len(urls)} URLs processed ({success_count} successful)")
                    
            except Exception as e:
                # Handle any unexpected errors from task execution
                logger.error(f"Unexpected error in task execution: {str(e)}")
                results.append({
                    "success": False,
                    "url": "unknown",
                    "error": f"Task execution error: {str(e)}"
                })
    
    # Verify all URLs are accounted for in results
    processed_urls = {result.get("url") for result in results if "url" in result}
    missing_urls = set(urls) - processed_urls
    
    for url in missing_urls:
        logger.warning(f"No result found for URL: {url}, adding error entry")
        results.append({
            "success": False,
            "url": url,
            "error": "URL processing was skipped or failed without error information"
        })
    
    # Final garbage collection
    gc.collect()
    
    return results


def get_thread_pool_sync(max_workers=None, thread_name_prefix="web2json_worker"):
    """Create a thread pool for synchronous use.
    
    Args:
        max_workers: Maximum number of worker threads
        thread_name_prefix: Prefix for thread names
        
    Returns:
        ThreadPoolExecutor instance
    """
    import concurrent.futures
    
    # Get optimal worker count based on system resources
    if max_workers is None:
        # Use 75% of available CPUs to avoid overloading the system
        max_workers = max(2, min(32, int((os.cpu_count() or 4) * 0.75)))
    
    return concurrent.futures.ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix=thread_name_prefix
    )


def get_version() -> str:
    """Get the current version of web2json.
    
    Returns:
        Version string
    """
    try:
        return sys.modules["web2json"].__version__
    except (KeyError, AttributeError):
        # Fallback to manual import
        from web2json import __version__
        return __version__
