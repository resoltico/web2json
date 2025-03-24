"""
JSON conversion and structured data handling functionality.
"""
import json
import logging
import os
from typing import Dict, Optional, Union, Any
from pathlib import Path
from ..utils.file_handler import validate_output_path
from ..exceptions import ConversionError
from ..config import DEFAULT_ENCODING

class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling special data types."""
    def default(self, obj: Any) -> Any:
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)

def validate_json_data(data: Dict) -> bool:
    """
    Validate data structure before conversion.
    
    Args:
        data: Dictionary to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = {'title', 'content', 'metadata'}
    try:
        # Check required top-level fields
        if not all(field in data for field in required_fields):
            logging.error("Missing required fields in data structure")
            return False
            
        # Validate metadata
        metadata = data.get('metadata', {})
        if not isinstance(metadata, dict):
            logging.error("Metadata must be a dictionary")
            return False
            
        required_metadata = {'fetched_at', 'url'}
        if not all(field in metadata for field in required_metadata):
            logging.error("Missing required metadata fields")
            return False
            
        # Validate content structure
        content = data.get('content', [])
        if not isinstance(content, list):
            logging.error("Content must be a list")
            return False
            
        return True
        
    except Exception as e:
        logging.error(f"Error validating JSON data: {str(e)}")
        return False

def format_json_data(data: Dict) -> Dict:
    """
    Format and clean data before saving.
    
    Args:
        data: Dictionary to format
        
    Returns:
        Dict: Formatted data
    """
    try:
        # Remove empty fields
        formatted = {k: v for k, v in data.items() if v is not None}
        
        # Format metadata
        if 'metadata' in formatted:
            formatted['metadata'] = {
                k: v for k, v in formatted['metadata'].items()
                if v is not None
            }
            
        # Format content
        if 'content' in formatted:
            formatted['content'] = [
                {k: v for k, v in item.items() if v is not None}
                for item in formatted['content']
                if item
            ]
            
        return formatted
        
    except Exception as e:
        logging.error(f"Error formatting JSON data: {str(e)}")
        raise ConversionError(f"Failed to format data: {str(e)}")

def save_json(data: Dict, dir_path: str, filename: str, indent: int = 2) -> bool:
    """
    Save structured data as JSON file.
    
    Args:
        data: Dictionary to save
        dir_path: Target directory path
        filename: Target filename
        indent: JSON indentation level
        
    Returns:
        bool: True if save successful
    """
    try:
        if not validate_json_data(data):
            return False
            
        formatted_data = format_json_data(data)
        
        # Validate and prepare output path
        filepath = validate_output_path(dir_path, filename)
        if not filepath:
            return False
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Write JSON file
        with open(filepath, "w", encoding=DEFAULT_ENCODING) as f:
            json.dump(
                formatted_data,
                f,
                indent=indent,
                ensure_ascii=False,
                cls=JSONEncoder
            )
            
        logging.info(f"Successfully saved: {filepath}")
        return True
        
    except Exception as e:
        logging.error(f"Error saving JSON file: {str(e)}")
        return False

def load_json(filepath: Union[str, Path]) -> Optional[Dict]:
    """
    Load JSON file with error handling.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Optional[Dict]: Loaded data if successful
    """
    try:
        with open(filepath, 'r', encoding=DEFAULT_ENCODING) as f:
            data = json.load(f)
            
        if validate_json_data(data):
            return data
            
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in file {filepath}: {str(e)}")
    except Exception as e:
        logging.error(f"Error loading JSON file {filepath}: {str(e)}")
        
    return None