"""
File and path handling functionality.
"""
import os
import logging
import unicodedata
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime
from ..config import MAX_FILENAME_LENGTH, MAX_PATH_LENGTH
from ..exceptions import PathError

def expand_path(path: str) -> str:
   """Expand and normalize path."""
   try:
       expanded = os.path.expanduser(path)
       expanded = os.path.expandvars(expanded)
       return os.path.normpath(expanded)
   except Exception as e:
       raise PathError(f"Failed to expand path '{path}': {str(e)}")

def is_safe_path(base_dir: str, path: str) -> bool:
   """Check if path is within base directory."""
   try:
       base_abs = os.path.abspath(base_dir)
       path_abs = os.path.abspath(path)
       common = os.path.commonpath([base_abs, path_abs])
       return common == base_abs
   except Exception:
       return False

def sanitize_filename(filename: str) -> str:
   """Sanitize filename for safe OS processing."""
   # Handle empty filenames
   if not filename:
       return ""
   
   # Normalize path separators and handle unicode
   name = os.path.normpath(filename)
   name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
   
   # Handle the special case for ..hiddenfile
   if os.path.basename(name).startswith('..'):
       base = os.path.basename(name)[2:]  # Remove the leading ..
   else:
       # Split into path components and process each
       parts = [part for part in name.split(os.path.sep) if part and not part.startswith('.')]
       if not parts:
           return ""
       base = '_'.join(parts)
   
   # Split into base name and extension
   if '.' in base:
       name_base, ext = os.path.splitext(base)
   else:
       name_base, ext = base, ''
   
   # Replace dots with underscores in the base name
   name_base = name_base.replace('.', '_')
   
   # Handle special characters in the base name
   sanitized = ""
   prev_replaced = False
   
   for c in name_base:
       if c.isalnum():
           sanitized += c
           prev_replaced = False
       elif not prev_replaced:
           sanitized += '_'
           prev_replaced = True
   
   # Remove trailing underscore if present
   sanitized = sanitized.rstrip('_')
   
   # Return with extension if it exists
   return sanitized + ext if ext else sanitized

def validate_output_path(dir_path: str, filename: str) -> Optional[str]:
   """Validate and prepare output path."""
   try:
       path_obj = Path(dir_path) / filename
       
       if len(str(path_obj)) > MAX_FILENAME_LENGTH:
           logging.error(f"Path exceeds maximum length of {MAX_FILENAME_LENGTH}")
           raise ValueError(f"Path exceeds maximum length of {MAX_FILENAME_LENGTH}")
           
       if not path_obj.parent.exists():
           try:
               path_obj.parent.mkdir(parents=True, exist_ok=True)
           except Exception as e:
               logging.error(f"Failed to create directory: {str(e)}")
               raise Exception(f"Failed to create directory: {str(e)}")
       elif not os.access(path_obj.parent, os.W_OK):
           logging.error(f"No write permission for directory: {path_obj.parent}")
           raise Exception(f"No write permission for directory: {path_obj.parent}")
           
       return str(path_obj)
       
   except ValueError as e:
       raise e
   except Exception as e:
       logging.error(f"Path validation error: {str(e)}")
       raise e

def generate_filename(url: str, output_dir: str, custom_name: Optional[str] = None) -> Tuple[str, str]:
   """Generate safe filename from URL or custom name."""
   if not url or not output_dir:
       raise PathError("URL and output directory cannot be empty")
       
   try:
       base_dir = os.path.abspath(expand_path(output_dir))
       
       if custom_name:
           if not custom_name.strip():
               raise PathError("Custom name cannot be empty")
               
           if ".." in custom_name:
               raise PathError("Invalid path: potential directory traversal")
               
           if os.path.isabs(custom_name):
               custom_dir = os.path.dirname(custom_name)
               filename = os.path.basename(custom_name)
               if not is_safe_path(base_dir, custom_dir):
                   dir_path = base_dir
               else:
                   dir_path = custom_dir
           elif os.path.sep in custom_name:
               rel_dir = os.path.dirname(custom_name)
               filename = os.path.basename(custom_name)
               dir_path = os.path.join(base_dir, rel_dir)
           else:
               dir_path = base_dir
               filename = custom_name
               
           filename = filename.removesuffix('.json')
           filename = sanitize_filename(filename)
       else:
           dir_path = base_dir
           parsed = urlparse(url)
           domain = parsed.netloc.replace(".", "_")
           path = parsed.path.replace("/", "_").strip("_")[:MAX_PATH_LENGTH]
           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           filename = f"{domain}_{path}_{timestamp}"
       
       max_base_length = MAX_FILENAME_LENGTH - 5
       if len(filename) > max_base_length:
           filename = filename[:max_base_length]
       
       return dir_path, f"{filename}.json"
       
   except Exception as e:
       raise PathError(f"Failed to process output path: {str(e)}")