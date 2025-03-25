"""
Export stage for the web2json pipeline.

This stage exports the document to a file or returns it as a dictionary.
"""
from typing import Dict, Any, Optional, Union
import json
import os
import logging
from pathlib import Path
from .base import PipelineStage
from ....exceptions import ExportError

class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling special data types."""
    def default(self, obj: Any) -> Any:
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)

class DocumentExporter:
    """Exporter for saving documents to files."""
    
    def __init__(self, indent: int = 2, encoding: str = 'utf-8'):
        """Initialize the document exporter.
        
        Args:
            indent: JSON indentation level
            encoding: File encoding
        """
        self.indent = indent
        self.encoding = encoding
        self.logger = logging.getLogger(__name__)
    
    def export_to_file(self, document: Dict[str, Any], filepath: Union[str, Path]) -> bool:
        """Export document to a file.
        
        Args:
            document: Document to export
            filepath: Path to export to
            
        Returns:
            True if export was successful
            
        Raises:
            ExportError: If export fails
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Write to file
            with open(filepath, 'w', encoding=self.encoding) as f:
                json.dump(
                    document,
                    f,
                    indent=self.indent,
                    ensure_ascii=False,
                    cls=JSONEncoder
                )
                
            self.logger.info(f"Document exported to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting document: {str(e)}")
            raise ExportError(f"Failed to export document: {str(e)}")
    
    def validate_document(self, document: Dict[str, Any]) -> bool:
        """Validate document structure.
        
        Args:
            document: Document to validate
            
        Returns:
            True if document is valid
            
        Raises:
            ValueError: If document is invalid
        """
        required_keys = {'title', 'content', 'metadata'}
        
        # Check required top-level fields
        if not all(key in document for key in required_keys):
            missing = required_keys - set(document.keys())
            raise ValueError(f"Missing required fields in document: {missing}")
            
        # Validate metadata
        metadata = document.get('metadata', {})
        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be a dictionary")
            
        required_metadata = {'fetched_at', 'url'}
        if not all(key in metadata for key in required_metadata):
            missing = required_metadata - set(metadata.keys())
            raise ValueError(f"Missing required metadata fields: {missing}")
            
        # Validate content structure
        content = document.get('content', [])
        if not isinstance(content, list):
            raise ValueError("Content must be a list")
            
        return True

class ExportStage(PipelineStage):
    """Pipeline stage for exporting documents.
    
    This stage takes the document from the context and either
    exports it to a file or keeps it in the context.
    """
    
    def __init__(self, document_exporter: Optional[DocumentExporter] = None):
        """Initialize the export stage.
        
        Args:
            document_exporter: Document exporter to use
        """
        super().__init__()
        self.document_exporter = document_exporter or DocumentExporter()
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the context by exporting the document.
        
        Args:
            context: Pipeline context containing 'document'
            
        Returns:
            Updated context
            
        Raises:
            ValueError: If document is missing from context
            ExportError: If export fails
        """
        self.validate_context(context, ['document'])
        
        document = context['document']
        
        try:
            # Validate document
            self.document_exporter.validate_document(document)
            
            # Export to file if output_path is provided
            if 'output_path' in context and context['output_path']:
                output_path = context['output_path']
                self.logger.info(f"Exporting document to {output_path}")
                self.document_exporter.export_to_file(document, output_path)
                context['exported'] = True
                context['export_path'] = output_path
            else:
                self.logger.info("No output path provided, skipping export")
                context['exported'] = False
            
            return context
            
        except ValueError as e:
            self.logger.error(f"Invalid document structure: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error in export stage: {str(e)}")
            raise ExportError(f"Failed to export document: {str(e)}")
