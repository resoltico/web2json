"""
Memory management utilities for web2json.

This module provides functions for managing memory usage during processing.
"""
import gc
import logging
import sys
import inspect
import types
import random
from typing import Any, Dict, Optional, Set, List, Tuple
from collections import deque

# Size threshold for triggering garbage collection (in bytes)
# Objects larger than this will trigger collection when cleared
GC_SIZE_THRESHOLD = 1_000_000  # 1MB

# Maximum depth for recursive size calculation
MAX_RECURSION_DEPTH = 20

# Limit on number of objects to measure to prevent excessive CPU use
MAX_OBJECTS_TO_MEASURE = 10000

# Number of random samples to take for large dictionaries
DICT_SAMPLE_SIZE = 100


def get_object_size(obj: Any, seen: Optional[Set[int]] = None, depth: int = 0) -> int:
    """Estimate the memory size of an object recursively.
    
    This improved function handles circular references and provides a more
    accurate estimation for container objects by recursively measuring their contents.
    It uses statistical sampling for large dictionaries to improve accuracy.
    
    Args:
        obj: Object to measure
        seen: Set of object IDs already measured (to handle circular references)
        depth: Current recursion depth
        
    Returns:
        Approximate size in bytes
    """
    # Initialize the set of seen objects if this is the first call
    if seen is None:
        seen = set()
    
    # Check for circular references or excessive recursion
    obj_id = id(obj)
    if obj_id in seen or depth > MAX_RECURSION_DEPTH:
        return 0
    
    # Mark this object as seen
    seen.add(obj_id)
    
    try:
        # Get the basic size of the object
        size = sys.getsizeof(obj)
        
        # Handle various container types
        if isinstance(obj, (str, bytes, bytearray)):
            # Strings and bytes are already fully accounted for by getsizeof
            pass
        
        elif isinstance(obj, (list, tuple, set, frozenset, deque)):
            # For sequence containers, add the size of their items
            if len(obj) <= MAX_OBJECTS_TO_MEASURE:
                # For smaller containers, measure all items
                size += sum(get_object_size(item, seen, depth + 1) for item in obj)
            else:
                # For larger containers, use statistical sampling
                samples = random.sample(list(obj), min(DICT_SAMPLE_SIZE, len(obj)))
                avg_item_size = sum(get_object_size(item, seen, depth + 1) for item in samples) / len(samples)
                size += int(avg_item_size * len(obj))
            
        elif isinstance(obj, dict):
            # For dictionaries, use an improved approach with statistical sampling
            items = list(obj.items())
            if len(items) <= MAX_OBJECTS_TO_MEASURE:
                # For smaller dictionaries, measure all items
                size += sum(
                    get_object_size(k, seen, depth + 1) + get_object_size(v, seen, depth + 1)
                    for k, v in items
                )
            else:
                # For larger dictionaries, take a random sample of items
                # This helps ensure we get a more representative sample
                samples = random.sample(items, min(DICT_SAMPLE_SIZE, len(items)))
                
                # Calculate the average size of sampled items
                avg_item_size = sum(
                    get_object_size(k, seen, depth + 1) + get_object_size(v, seen, depth + 1)
                    for k, v in samples
                ) / len(samples)
                
                # Estimate total size based on average
                size += int(avg_item_size * len(items))
        
        elif hasattr(obj, '__dict__') and not isinstance(obj, (type, types.ModuleType, types.FunctionType)):
            # For objects with a __dict__ (not classes, modules, or functions), include their attributes
            size += get_object_size(obj.__dict__, seen, depth + 1)
            
        elif hasattr(obj, '__slots__'):
            # For objects with __slots__, measure the slot values
            for slot_name in obj.__slots__:
                if hasattr(obj, slot_name):
                    size += get_object_size(getattr(obj, slot_name), seen, depth + 1)
        
    except (TypeError, AttributeError, OverflowError):
        # For objects that don't support getsizeof or other errors
        logging.debug(f"Could not precisely measure size of {type(obj).__name__}")
        # Use a reasonable default size
        return 1000  # 1KB
    
    return size


def clear_reference(context: Dict[str, Any], key: str, force_gc: bool = False) -> None:
    """Clear a reference from a dictionary and optionally collect garbage.
    
    Args:
        context: Dictionary containing the reference
        key: Key to clear
        force_gc: Whether to force garbage collection regardless of object size
    """
    logger = logging.getLogger(__name__)
    
    if key in context and context[key] is not None:
        # Check if object is large enough to warrant measuring
        # This avoids wasting CPU time on small objects
        if force_gc or sys.getsizeof(context[key]) > 1000:
            # Only measure detailed size for potentially large objects
            obj_size = get_object_size(context[key])
        else:
            obj_size = sys.getsizeof(context[key])
            
        # Remove reference to allow garbage collection
        context[key] = None
        
        # Collect garbage if object was large or forced
        if force_gc or obj_size > GC_SIZE_THRESHOLD:
            logger.debug(f"Collecting garbage after clearing {key} ({obj_size} bytes)")
            gc.collect()
        else:
            logger.debug(f"Cleared {key} without garbage collection ({obj_size} bytes)")


def clear_memory_aggressively() -> Dict[str, Any]:
    """Perform aggressive memory cleanup.
    
    Useful after processing very large documents.
    
    Returns:
        Dictionary with garbage collection statistics
    """
    # Run garbage collection multiple times to ensure all cycles are cleaned
    stats = {}
    for i in range(3):
        collected = gc.collect(i)
        stats[f"gen{i}_collected"] = collected
    
    # Get memory status after collection
    stats.update(memory_status())
    
    return stats


def memory_status() -> Dict[str, Any]:
    """Get current memory status information.
    
    Returns:
        Dictionary with memory statistics
    """
    gc_counts = gc.get_count()
    
    # Get summary of objects being tracked
    objects_summary = {}
    if gc.get_debug() & gc.DEBUG_SAVEALL:
        # Only collect type info if detailed garbage collection is enabled
        garbage = gc.garbage
        objects_by_type = {}
        
        for obj in garbage[:1000]:  # Limit to 1000 objects to avoid excessive processing
            obj_type = type(obj).__name__
            objects_by_type[obj_type] = objects_by_type.get(obj_type, 0) + 1
        
        objects_summary = {
            "total_garbage": len(garbage),
            "types": objects_by_type
        }
    
    return {
        "gc_counts": {
            "generation0": gc_counts[0],
            "generation1": gc_counts[1],
            "generation2": gc_counts[2]
        },
        "gc_enabled": gc.isenabled(),
        "gc_thresholds": gc.get_threshold(),
        "gc_objects": len(gc.get_objects()),
        "gc_garbage_summary": objects_summary
    }


def optimize_memory_settings() -> None:
    """Configure garbage collector for optimal performance based on workload.
    
    This function adjusts GC settings based on expected memory usage patterns.
    """
    # Ensure garbage collection is enabled
    gc.enable()
    
    # Set threshold for generation 0 (young objects)
    # Lower threshold means GC runs more frequently for new objects
    # This is good for web scraping where we create many temporary objects
    
    # Set threshold for generations 1 and 2 (older objects)
    # Higher threshold means GC runs less frequently for old objects
    # This reduces overhead for long-lived objects
    
    # Custom thresholds tuned for web scraping workload
    # Format: (threshold0, threshold1, threshold2)
    gc.set_threshold(700, 10, 10)
    
    # Don't enable DEBUG_SAVEALL in production as it prevents cleanup
    # gc.set_debug(gc.DEBUG_SAVEALL)
    
    # Log current settings
    logger = logging.getLogger(__name__)
    logger.debug(f"Memory optimization applied: {memory_status()}")
    
    # Run initial collection
    gc.collect()