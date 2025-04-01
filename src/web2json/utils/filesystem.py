"""
File system utilities for web2json.

This module provides utilities for file system operations.
"""
import os
import sys
import re
import logging
import unicodedata
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Union, Set

from web2json.utils.errors import PathError

# Platform detection
IS_WINDOWS = platform.system() == "Windows"

# Default values
DEFAULT_OUTPUT_FOLDER = Path("fetched_jsons")

# Path length constraints
# For Windows, MAX_PATH is 260 by default, but can be longer with \\?\ prefix
# We'll use a more nuanced approach based on platform
MAX_FILENAME_LENGTH = 220 if IS_WINDOWS else 255
MAX_PATH_LENGTH = 50
WINDOWS_MAX_PATH = 260  # Windows API standard MAX_PATH

# Reserved filenames in Windows
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

# Invalid characters in filenames (cross-platform)
# Windows: < > : " / \ | ? * and ASCII control characters 0-31
# Unix: / and NUL
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1F]' if IS_WINDOWS else r'[/\x00]'

# Maximum URL component length for filename generation
MAX_URL_COMPONENT_LENGTH = 30


def expand_path(path: Union[str, Path]) -> Path:
    """Expand and normalize path.
    
    Args:
        path: Path to expand
        
    Returns:
        Expanded path
        
    Raises:
        PathError: If path expansion fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        if not path:
            raise ValueError("Path cannot be empty")
        
        path_str = str(path)
        expanded = os.path.expanduser(path_str)
        expanded = os.path.expandvars(expanded)
        normalized = os.path.normpath(expanded)
        
        # Handle long paths on Windows - always use absolute paths
        if IS_WINDOWS:
            abs_path = os.path.abspath(normalized)
            
            # Apply the \\?\ prefix for all Windows paths to consistently handle long paths
            if not abs_path.startswith("\\\\?\\"):
                # Check if path might exceed traditional Windows path limits
                if len(abs_path) > WINDOWS_MAX_PATH - 12:  # Allow some margin for additional components
                    logger.debug(f"Using long path format for potentially long path: {abs_path}")
                    return Path("\\\\?\\" + abs_path)
            
            # Already has the prefix, keep it
            if abs_path.startswith("\\\\?\\"):
                return Path(abs_path)
            
            # Path is safe and doesn't need special handling
            return Path(abs_path)
        else:
            # For non-Windows platforms, just return the normalized path
            return Path(normalized)
            
    except Exception as e:
        logger.error(f"Failed to expand path '{path}': {str(e)}")
        raise PathError(f"Failed to expand path '{path}': {str(e)}")


def is_safe_path(base_dir: Union[str, Path], path: Union[str, Path]) -> bool:
    """Check if path is within base directory.
    
    Args:
        base_dir: Base directory
        path: Path to check
        
    Returns:
        True if path is within base directory
    """
    try:
        if not path or not base_dir:
            return False
        
        # Normalize paths for consistent comparison
        base_abs = str(expand_path(base_dir))
        path_abs = str(expand_path(path))
        
        try:
            # Use commonpath for safer path comparison
            common = os.path.commonpath([base_abs, path_abs])
            return common == base_abs
        except ValueError:
            # ValueError occurs if paths are on different drives
            return False
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe OS processing.
    
    Handles:
    - Invalid characters
    - Reserved filenames on Windows
    - Unicode normalization
    - Excessive length
    - Leading/trailing whitespace and periods
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
    """
    logger = logging.getLogger(__name__)
    
    # Handle empty filenames
    if not filename or not filename.strip():
        logger.warning("Empty filename provided, using default")
        return "unnamed_file"
    
    # Remove leading/trailing whitespace
    name = filename.strip()
    
    # Normalize Unicode characters and convert to ASCII if possible
    try:
        name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    except UnicodeError:
        # If ASCII conversion fails, just use Unicode normalization
        name = unicodedata.normalize('NFKD', name)
    
    # Replace invalid characters with underscores
    name = re.sub(INVALID_FILENAME_CHARS, '_', name)
    
    # Handle Windows reserved names
    if IS_WINDOWS and name.upper() in WINDOWS_RESERVED_NAMES:
        name = f"_{name}_"
    
    # Handle devices on Windows (CON.txt, COM1.json, etc.)
    if IS_WINDOWS:
        name_parts = name.split('.')
        if name_parts[0].upper() in WINDOWS_RESERVED_NAMES:
            name_parts[0] = f"_{name_parts[0]}_"
            name = '.'.join(name_parts)
    
    # Replace dots in base name with underscores (except the last one for extension)
    if '.' in name[:-5]:  # Allow for extension like .json
        base, ext = os.path.splitext(name)
        base = base.replace('.', '_')
        name = f"{base}{ext}"
    
    # Replace multiple consecutive underscores with a single one
    name = re.sub(r'_{2,}', '_', name)
    
    # Remove leading/trailing periods to avoid hidden files on Unix
    name = name.strip('.')
    
    # Ensure we have a valid name
    if not name or name.isspace():
        logger.warning("Sanitization resulted in empty name, using default")
        return "unnamed_file"
    
    # Truncate if too long, but preserve extension
    if len(name) > MAX_FILENAME_LENGTH:
        base, ext = os.path.splitext(name)
        # Ensure extension is preserved but not too long
        if len(ext) > 10:  # If extension is unreasonably long
            ext = ext[:10]
        max_base_length = MAX_FILENAME_LENGTH - len(ext)
        base = base[:max_base_length]
        name = f"{base}{ext}"
        logger.warning(f"Filename truncated to {len(name)} characters")
    
    return name


def validate_output_path(dir_path: Union[str, Path], filename: str) -> Path:
    """Validate and prepare output path.
    
    Args:
        dir_path: Directory path
        filename: Filename
        
    Returns:
        Full validated path
        
    Raises:
        ValueError: If path is invalid
        PathError: If path creation fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Sanitize filename
        safe_filename = sanitize_filename(filename)
        if safe_filename != filename:
            logger.info(f"Filename sanitized: '{filename}' -> '{safe_filename}'")
        
        # Convert to Path objects
        dir_path_obj = Path(dir_path)
        
        # Expand path to handle ~, environment variables, etc.
        expanded_dir = expand_path(dir_path_obj)
        path_obj = expanded_dir / safe_filename
        
        # Check total path length
        path_str = str(path_obj)
        
        # Windows-specific path handling for long paths
        if IS_WINDOWS:
            # Check if path exceeds Windows standard MAX_PATH
            if len(path_str) > WINDOWS_MAX_PATH:
                logger.warning(f"Path exceeds Windows MAX_PATH ({WINDOWS_MAX_PATH}): {len(path_str)} characters")
                
                # Make sure path is absolute and has the \\?\ prefix
                path_abs = os.path.abspath(path_str)
                if not path_abs.startswith("\\\\?\\"):
                    path_str = "\\\\?\\" + path_abs
                    path_obj = Path(path_str)
                    logger.info("Using Windows long path format with \\\\?\\ prefix")
        
        # Create parent directory if it doesn't exist
        try:
            path_obj.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create directory: {str(e)}")
            raise PathError(f"Failed to create directory: {str(e)}")
            
        # Check write permissions
        if path_obj.parent.exists() and not os.access(path_obj.parent, os.W_OK):
            logger.error(f"No write permission for directory: {path_obj.parent}")
            raise PathError(f"No write permission for directory: {path_obj.parent}")
        
        return path_obj
    
    except ValueError as e:
        raise e
    except Exception as e:
        logger.error(f"Path validation error: {str(e)}")
        raise PathError(f"Path validation error: {str(e)}")


def generate_filename(url: str, output_dir: Union[str, Path]) -> Tuple[Path, str]:
    """Generate safe filename from URL.
    
    Args:
        url: Source URL
        output_dir: Output directory
        
    Returns:
        Tuple of (directory path, filename)
        
    Raises:
        PathError: If filename generation fails
    """
    logger = logging.getLogger(__name__)
    
    if not url or not output_dir:
        raise PathError("URL and output directory cannot be empty")
    
    try:
        # Convert output_dir to Path and expand
        output_path = expand_path(output_dir)
        
        # Parse URL for domain and path
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # Get domain, removing www. prefix if present
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        domain = domain.replace(".", "_")
        
        # Limit domain length
        if len(domain) > MAX_URL_COMPONENT_LENGTH:
            domain = domain[:MAX_URL_COMPONENT_LENGTH]
        
        # Get path, limiting length and removing common endings
        path = parsed.path.rstrip("/")
        if path:
            # Remove common file extensions that might be in the URL path
            path = re.sub(r'\.(html|htm|php|asp|aspx|jsp)$', '', path, flags=re.IGNORECASE)
            # Replace slashes with underscores
            path = path.replace("/", "_").strip("_")
            # Limit path component length
            if len(path) > MAX_URL_COMPONENT_LENGTH:
                path = path[:MAX_URL_COMPONENT_LENGTH]
        else:
            path = "home"
        
        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create base filename
        if path:
            filename = f"{domain}_{path}_{timestamp}"
        else:
            filename = f"{domain}_{timestamp}"
        
        # Sanitize the filename
        filename = sanitize_filename(filename)
        
        # Ensure filename length is valid (accounting for .json extension)
        max_base_length = MAX_FILENAME_LENGTH - 5  # Allow for .json extension
        if len(filename) > max_base_length:
            filename = filename[:max_base_length]
        
        # Add .json extension
        filename = f"{filename}.json"
        
        logger.debug(f"Generated filename: {filename} for URL: {url}")
        return output_path, filename
    
    except Exception as e:
        logger.error(f"Failed to generate filename: {str(e)}")
        raise PathError(f"Failed to generate filename: {str(e)}")


def ensure_directory(directory: Union[str, Path]) -> Path:
    """Ensure directory exists, creating it if necessary.
    
    Args:
        directory: Directory path
        
    Returns:
        Path object for the directory
        
    Raises:
        PathError: If directory creation fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Handle empty directory
        if not directory:
            raise PathError("Directory path cannot be empty")
        
        # Expand and normalize path
        path = expand_path(directory)
        
        # Check if path exists and is a directory
        if path.exists() and not path.is_dir():
            raise PathError(f"Path exists but is not a directory: {path}")
        
        # Create directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)
        
        # Check permissions
        if not os.access(path, os.W_OK):
            raise PathError(f"No write permission for directory: {path}")
        
        return path
    except PathError:
        # Re-raise PathError as is
        raise
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {str(e)}")
        raise PathError(f"Failed to create directory {directory}: {str(e)}")