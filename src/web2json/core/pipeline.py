"""
Pipeline architecture for web2json processing flow.

This module implements a flexible pipeline system for processing web content.
Each pipeline consists of a series of stages that transform the input data.
"""
import asyncio
import logging
import gc
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, List, Protocol, Optional, TypeVar, Callable, Awaitable, Union, AsyncGenerator

from web2json.core.fetch import fetch_url
from web2json.core.parse import parse_html
from web2json.core.extract import extract_content
from web2json.core.export import export_document
from web2json.models.document import Document
from web2json.utils.filesystem import generate_filename
from web2json.utils.errors import Web2JsonError, FetchError
from web2json.utils.memory import clear_reference, optimize_memory_settings, memory_status

# Type definitions
T = TypeVar('T')
Context = Dict[str, Any]

# Default timeout in seconds for async operations
DEFAULT_TIMEOUT = 60


@asynccontextmanager
async def get_thread_pool(thread_name_prefix: str = "web2json_worker") -> AsyncGenerator[ThreadPoolExecutor, None]:
    """
    Context manager for thread pool management.
    
    This ensures proper cleanup of thread pool resources regardless of execution path.
    
    Args:
        thread_name_prefix: Prefix for worker thread names
        
    Yields:
        ThreadPoolExecutor instance
    """
    logger = logging.getLogger(__name__)
    
    # Get optimal worker count based on system resources
    # Using fewer threads than CPUs to avoid context switching overhead
    max_workers = max(2, min(32, (os.cpu_count() or 4) - 1))
    
    logger.debug(f"Creating thread pool with {max_workers} workers")
    
    # Create the thread pool
    executor = ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix=thread_name_prefix
    )
    
    try:
        # Yield the executor for use
        yield executor
    finally:
        # Ensure the executor is properly shut down during cleanup
        # Setting wait=True ensures all pending tasks complete before shutdown
        logger.debug("Shutting down thread pool...")
        executor.shutdown(wait=True)
        logger.debug("Thread pool shutdown complete")


class PipelineStage(Protocol):
    """Protocol defining a pipeline stage."""
    
    async def process(self, context: Context) -> Context:
        """Process the context and return the updated context."""
        ...


async def run_pipeline(stages: List[PipelineStage], initial_context: Context) -> Context:
    """Run a pipeline with the provided stages and initial context.
    
    Args:
        stages: List of pipeline stages to execute
        initial_context: Initial context dictionary
        
    Returns:
        Final context after all stages have processed
    """
    logger = logging.getLogger(__name__)
    
    # Configure garbage collection for optimal performance
    optimize_memory_settings()
    
    current_context = initial_context.copy()
    
    for i, stage in enumerate(stages):
        stage_name = stage.__class__.__name__
        logger.debug(f"Executing pipeline stage {i+1}/{len(stages)}: {stage_name}")
        
        try:
            # Process the stage with timeout protection
            task = asyncio.create_task(stage.process(current_context))
            timeout = current_context.get("timeout", DEFAULT_TIMEOUT)
            
            try:
                # Wait for the stage to complete with a timeout
                current_context = await asyncio.wait_for(task, timeout=timeout)
                
                # Log memory status after each stage (if in debug mode)
                if logger.isEnabledFor(logging.DEBUG):
                    mem_status = memory_status()
                    logger.debug(f"Memory after {stage_name}: {mem_status}")
                
            except asyncio.TimeoutError:
                # Cancel the task if it times out
                task.cancel()
                logger.error(f"Stage {stage_name} timed out after {timeout} seconds")
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                # Add error information to the context
                current_context.setdefault("errors", []).append({
                    "stage": stage_name,
                    "error": f"Operation timed out after {timeout} seconds",
                    "type": "TimeoutError"
                })
                
                # Raise a timeout error
                raise TimeoutError(f"Stage {stage_name} timed out after {timeout} seconds")
                
        except Exception as e:
            logger.error(f"Error in pipeline stage {stage_name}: {str(e)}")
            # Add error information to the context
            current_context.setdefault("errors", []).append({
                "stage": stage_name,
                "error": str(e),
                "type": type(e).__name__
            })
            # Re-raise the exception
            raise
    
    return current_context


async def run_in_thread(func, *args, executor=None, **kwargs):
    """Run a CPU-bound function in a thread pool.
    
    This helps avoid blocking the event loop with CPU-intensive operations.
    
    Args:
        func: Function to run
        *args: Positional arguments to pass to the function
        executor: ThreadPoolExecutor to use (if None, one will be created)
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Result of the function
    """
    loop = asyncio.get_running_loop()
    
    if executor is None:
        # Create a one-time use executor if none provided
        async with get_thread_pool() as temp_executor:
            return await loop.run_in_executor(
                temp_executor,
                lambda: func(*args, **kwargs)
            )
    else:
        # Use the provided executor
        return await loop.run_in_executor(
            executor,
            lambda: func(*args, **kwargs)
        )


class FetchStage:
    """Pipeline stage for fetching web content."""
    
    async def process(self, context: Context) -> Context:
        """Process context by fetching web content."""
        url = context["url"]
        logger = logging.getLogger(__name__)
        logger.info(f"Fetching content from URL: {url}")
        
        start_time = time.time()
        try:
            html_content = await fetch_url(url)
            elapsed = time.time() - start_time
            logger.debug(f"Fetch completed in {elapsed:.2f} seconds")
            
            context["html_content"] = html_content
            context["content_length"] = len(html_content)
            context["fetch_time"] = elapsed
            
        except FetchError as e:
            logger.error(f"Fetch error for {url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during fetch for {url}: {str(e)}")
            raise FetchError(f"Unexpected error during fetch: {str(e)}")
        
        return context


class ParseStage:
    """Pipeline stage for parsing HTML content."""
    
    def __init__(self, executor=None):
        self.executor = executor
    
    async def process(self, context: Context) -> Context:
        """Process context by parsing HTML content."""
        html_content = context["html_content"]
        logger = logging.getLogger(__name__)
        logger.info("Parsing HTML content")
        
        start_time = time.time()
        
        # Use specialized function for running in thread pool
        # This avoids blocking the event loop with CPU-intensive parsing
        try:
            soup, title, meta_tags = await run_in_thread(
                parse_html, html_content, executor=self.executor
            )
            elapsed = time.time() - start_time
            logger.debug(f"Parse completed in {elapsed:.2f} seconds")
            
            # Clear HTML content from memory as it's no longer needed
            clear_reference(context, "html_content")
            
            context["soup"] = soup
            context["title"] = title
            context["meta_tags"] = meta_tags
            context["parse_time"] = elapsed
            
        except Exception as e:
            logger.error(f"Error parsing HTML content: {str(e)}")
            # Ensure we clean up memory even on error
            clear_reference(context, "html_content")
            raise
        
        return context


class ExtractStage:
    """Pipeline stage for extracting structured content."""
    
    def __init__(self, executor=None):
        self.executor = executor
    
    async def process(self, context: Context) -> Context:
        """Process context by extracting structured content."""
        soup = context["soup"]
        preserve_styles = context.get("preserve_styles", False)
        logger = logging.getLogger(__name__)
        logger.info("Extracting structured content")
        
        start_time = time.time()
        
        # Use dedicated thread pool for CPU-intensive extraction
        try:
            content = await run_in_thread(
                extract_content, soup, preserve_styles, executor=self.executor
            )
            elapsed = time.time() - start_time
            logger.debug(f"Extract completed in {elapsed:.2f} seconds")
            
            # Clear soup object from memory as it's no longer needed
            clear_reference(context, "soup")
            
            context["content"] = content
            context["extract_time"] = elapsed
            
        except Exception as e:
            logger.error(f"Error extracting content: {str(e)}")
            # Ensure we clean up memory even on error
            clear_reference(context, "soup")
            raise
        
        return context


class TransformStage:
    """Pipeline stage for transforming content into a document."""
    
    async def process(self, context: Context) -> Context:
        """Process context by transforming content into a document."""
        logger = logging.getLogger(__name__)
        logger.info("Creating document")
        
        start_time = time.time()
        
        try:
            # Create document from context
            document = Document(
                title=context["title"],
                content=context["content"],
                metadata={
                    "url": context["url"],
                    "preserve_styles": context.get("preserve_styles", False),
                    "meta": context.get("meta_tags", {})
                }
            )
            elapsed = time.time() - start_time
            logger.debug(f"Transform completed in {elapsed:.2f} seconds")
            
            # Clear content list from memory as it's now in the document
            clear_reference(context, "content")
            clear_reference(context, "meta_tags")
            
            context["document"] = document
            context["transform_time"] = elapsed
            
        except Exception as e:
            logger.error(f"Error transforming content into document: {str(e)}")
            # Ensure we clean up memory even on error
            clear_reference(context, "content")
            clear_reference(context, "meta_tags")
            raise
        
        return context


class ExportStage:
    """Pipeline stage for exporting the document."""
    
    def __init__(self, executor=None):
        self.executor = executor
    
    async def process(self, context: Context) -> Context:
        """Process context by exporting the document."""
        document = context["document"]
        logger = logging.getLogger(__name__)
        
        start_time = time.time()
        
        try:
            # Check if output path is provided
            if "output_path" in context and context["output_path"]:
                output_path = context["output_path"]
                logger.info(f"Exporting document to {output_path}")
            else:
                # Generate filename based on URL
                output_dir = context["output_dir"]
                url = context["url"]
                dir_path, filename = generate_filename(url, output_dir)
                output_path = dir_path / filename
                logger.info(f"Exporting document to {output_path}")
                
            # Export document using the thread pool for I/O operations
            await run_in_thread(
                export_document, document, output_path, executor=self.executor
            )
            elapsed = time.time() - start_time
            logger.debug(f"Export completed in {elapsed:.2f} seconds")
            
            context["output_path"] = output_path
            context["export_time"] = elapsed
            
            # Perform final garbage collection
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error exporting document: {str(e)}")
            # Attempt garbage collection even on error
            gc.collect()
            raise
        
        return context


async def process_url(
    url: str,
    output_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    preserve_styles: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Process a single URL through the pipeline.
    
    Args:
        url: URL to process
        output_path: Optional specific output path
        output_dir: Directory to save output (if output_path not provided)
        preserve_styles: Whether to preserve HTML styles
        timeout: Timeout in seconds for each stage
        
    Returns:
        Dictionary with processing results
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Processing URL: {url}")
    
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
                }
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
    timeout: int = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
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
    async def process_with_semaphore(semaphore, executor, url: str) -> Dict[str, Any]:
        """Process a URL with semaphore for concurrency control."""
        start_time = time.time()
        
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
                    "processing_time": total_time
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
    
    async with get_thread_pool() as executor:
        # Create tasks for all URLs with proper resource management
        tasks = [process_with_semaphore(semaphore, executor, url) for url in urls]
        
        # Wait for all tasks to complete with per-URL timeout protection
        results = []
        
        for task in asyncio.as_completed(tasks):
            try:
                # Each URL has its own timeout protection within process_with_semaphore
                result = await task
                results.append(result)
                
                # Log progress
                completed = len(results)
                if completed % 5 == 0 or completed == len(urls):
                    logger.info(f"Progress: {completed}/{len(urls)} URLs processed")
                    
            except Exception as e:
                # Handle any unexpected errors from task execution
                logger.error(f"Unexpected error in task execution: {str(e)}")
                results.append({
                    "success": False,
                    "url": "unknown",  # We don't know which URL caused the error
                    "error": f"Task execution error: {str(e)}"
                })
    
    # Verify all URLs are accounted for in results
    processed_urls = {result.get("url") for result in results if "url" in result}
    for url in urls:
        if url not in processed_urls:
            logger.warning(f"No result found for URL: {url}, adding error entry")
            results.append({
                "success": False,
                "url": url,
                "error": "URL processing was skipped or failed without error information"
            })
    
    # Final garbage collection
    gc.collect()
    
    return results