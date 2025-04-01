"""
Export module for web2json.

This module provides functionality for exporting documents to files.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Union

from web2json.models.document import Document
from web2json.utils.errors import ExportError
from web2json.utils.filesystem import validate_output_path, sanitize_filename


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling dates and special objects."""
    
    def default(self, obj: Any) -> Any:
        """Convert objects to JSON serializable types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        
        # For other types, just use the parent's implementation
        try:
            return super().default(obj)
        except TypeError:
            # If that fails, convert to string
            return str(obj)


def export_document(
    document: Union[Document, Dict[str, Any]],
    filepath: Union[str, Path],
    indent: int = 2,
    encoding: str = "utf-8",
) -> Path:
    """Export a document to a JSON file.
    
    Args:
        document: Document to export
        filepath: Path to save file to
        indent: JSON indentation level
        encoding: File encoding
        
    Returns:
        Path to saved file
        
    Raises:
        ExportError: If export fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Convert filepath to Path object
        original_path = Path(filepath)
        
        # Extract directory and filename
        dir_path = original_path.parent
        filename = original_path.name
        
        # Validate and sanitize output path
        path = validate_output_path(dir_path, filename)
        
        # If document is a Document object, convert to dict
        if isinstance(document, Document):
            try:
                # Use model_dump() from Pydantic to convert to dict
                data = document.model_dump(mode='json')
            except Exception as e:
                logger.error(f"Failed to convert document to dict: {str(e)}")
                raise ExportError(f"Failed to convert document to dict: {str(e)}")
        else:
            data = document
        
        # Serialize to JSON
        try:
            json_string = json.dumps(
                data,
                indent=indent,
                ensure_ascii=False,
                cls=CustomJSONEncoder
            )
        except Exception as e:
            logger.error(f"Failed to serialize document to JSON: {str(e)}")
            raise ExportError(f"Failed to serialize document to JSON: {str(e)}")
        
        # Write to file
        try:
            path.write_text(json_string, encoding=encoding)
        except Exception as e:
            logger.error(f"Failed to write document to file: {str(e)}")
            raise ExportError(f"Failed to write document to file: {str(e)}")
        
        logger.info(f"Document saved to {path}")
        return path
        
    except ExportError:
        # Re-raise ExportError as is
        raise
    except Exception as e:
        logger.error(f"Failed to save document: {str(e)}")
        raise ExportError(f"Failed to save document: {str(e)}")