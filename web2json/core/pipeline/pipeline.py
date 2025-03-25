"""
Pipeline architecture for web2json processing flow.

This module implements a flexible pipeline system for processing web content.
Each pipeline consists of a series of stages that transform the input data.
"""
from typing import List, Dict, Any, Optional, Type
import logging
from ..pipeline.stages.base import PipelineStage

class Pipeline:
    """Processing pipeline for web2json.
    
    A pipeline consists of a sequence of stages that are executed in order.
    Each stage takes the context (a dictionary of data) from the previous stage,
    processes it, and passes it to the next stage.
    """
    
    def __init__(self, stages: List[PipelineStage] = None):
        """Initialize the pipeline with a list of stages.
        
        Args:
            stages: List of pipeline stages to execute in sequence
        """
        self.stages = stages or []
        self.logger = logging.getLogger(__name__)
        
    def add_stage(self, stage: PipelineStage) -> 'Pipeline':
        """Add a stage to the pipeline.
        
        Args:
            stage: The stage to add
            
        Returns:
            The pipeline instance for method chaining
        """
        self.stages.append(stage)
        return self
        
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all pipeline stages on the context.
        
        Args:
            context: The initial context dictionary
            
        Returns:
            The processed context after all stages
            
        Raises:
            Exception: Any exception raised by a pipeline stage
        """
        current_context = context.copy()  # Create a copy to avoid modifying the input
        
        for stage in self.stages:
            stage_name = stage.__class__.__name__
            self.logger.debug(f"Executing pipeline stage: {stage_name}")
            
            try:
                current_context = stage.process(current_context)
            except Exception as e:
                self.logger.error(f"Error in pipeline stage {stage_name}: {str(e)}")
                # Add error information to the context
                current_context.setdefault('errors', []).append({
                    'stage': stage_name,
                    'error': str(e),
                    'type': type(e).__name__
                })
                raise
                
            self.logger.debug(f"Completed pipeline stage: {stage_name}")
            
        return current_context
        
    @classmethod
    def create_default(cls) -> 'Pipeline':
        """Create a pipeline with the default stages.
        
        Returns:
            A pipeline configured with the default stages
        """
        # Import here to avoid circular imports
        from ..pipeline.stages.fetch import FetchStage
        from ..pipeline.stages.parse import ParseStage
        from ..pipeline.stages.extract import ExtractStage
        from ..pipeline.stages.transform import TransformStage
        from ..pipeline.stages.export import ExportStage
        
        return cls([
            FetchStage(),
            ParseStage(),
            ExtractStage(),
            TransformStage(),
            ExportStage()
        ])
