"""
Base pipeline stage module for web2json.

This module defines the base PipelineStage protocol and related utilities.
"""
import asyncio
import gc
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Protocol, Optional, TypeVar, Callable, Awaitable, Union, AsyncGenerator

from web2json.utils.errors import Web2JsonError
from web2json.utils.memory import clear_reference, optimize_memory_settings, memory_status

# Type definitions
T = TypeVar('T')
Context = Dict[str, Any]

# Default timeout in seconds for async operations
DEFAULT_TIMEOUT = 60


class PipelineStage(Protocol):
    """Protocol defining a pipeline stage."""
    
    async def process(self, context: Context) -> Context:
        """Process the context and return the updated context."""
        ...


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


async def run_pipeline(stages: List[PipelineStage], initial_context: Context) -> Context:
    """Run a pipeline with the provided stages and initial context.
    
    Args:
        stages: List of pipeline stages to execute
        initial_context: Initial context dictionary
        
    Returns:
        Final context after all stages have processed
        
    Raises:
        Exception: If any stage fails
    """
    logger = logging.getLogger(__name__)
    
    # Configure garbage collection for optimal performance
    optimize_memory_settings()
    
    current_context = initial_context.copy()
    
    # Store timing information
    current_context.setdefault("timings", {})
    
    for i, stage in enumerate(stages):
        stage_name = stage.__class__.__name__
        logger.debug(f"Executing pipeline stage {i+1}/{len(stages)}: {stage_name}")
        
        stage_start_time = time.time()
        
        try:
            # Process the stage with timeout protection
            task = asyncio.create_task(stage.process(current_context))
            timeout = current_context.get("timeout", DEFAULT_TIMEOUT)
            
            try:
                # Wait for the stage to complete with a timeout
                current_context = await asyncio.wait_for(task, timeout=timeout)
                
                # Record stage timing
                stage_time = time.time() - stage_start_time
                current_context["timings"][stage_name] = stage_time
                
                # Log completion and timing
                logger.debug(f"Stage {stage_name} completed in {stage_time:.2f} seconds")
                
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
    
    # Calculate total processing time
    if "start_time" in current_context:
        total_time = time.time() - current_context["start_time"]
        current_context["total_time"] = total_time
        logger.info(f"Total pipeline execution time: {total_time:.2f} seconds")
    
    return current_context
