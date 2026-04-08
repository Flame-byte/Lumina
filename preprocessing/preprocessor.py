"""
Preprocessing Main Module

Responsible for coordinating sub-modules to complete multimodal input preprocessing tasks
"""
import os
import tempfile
from typing import List, Dict, Any, Union, Optional
from .input_detector import detect_input_type, validate_input
from .text_processor import TextProcessor
from .image_processor import ImageProcessor
from .pdf_processor import PDFProcessor
from .excel_processor import ExcelProcessor
from .audio_processor import AudioProcessor
from .output_formatter import OutputFormatter
from .error_handler import handle_file_error
from .deduplicator import Deduplicator


class Preprocessor:
    def __init__(self, processed_data_dir: str = None, audio_base_url: str = "http://localhost:52625/v1"):
        self.processed_data_dir = processed_data_dir or tempfile.gettempdir()

        self.text_processor = TextProcessor()
        self.image_processor = ImageProcessor(processed_data_dir=self.processed_data_dir)
        self.pdf_processor = PDFProcessor(processed_data_dir=self.processed_data_dir)
        self.excel_processor = ExcelProcessor()
        self.audio_processor = AudioProcessor(processed_data_dir=self.processed_data_dir, base_url=audio_base_url)
        self.output_formatter = OutputFormatter()
        self.deduplicator = Deduplicator()

        # Processor mapping
        self.processor_map = {
            'text': self.text_processor,
            'image': self.image_processor,
            'pdf': self.pdf_processor,
            'excel': self.excel_processor,
            'audio': self.audio_processor
        }

    def process(self, inputs: Union[str, List[str]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Preprocessing main entry function

        Args:
            inputs: Input paths, can be a single path or a list of paths

        Returns:
            For single input: returns processing result dictionary
            For multiple inputs: returns processing result list
        """
        # Handle single file case
        if isinstance(inputs, str):
            return self._process_single_file(inputs)

        # Handle multiple files case
        processed_results = []
        for input_path in inputs:
            result = self._process_single_file(input_path)
            if result:
                processed_results.append(result)

        return processed_results

    def _process_single_file(self, input_path: str) -> Optional[Dict[str, Any]]:
        """
        Process single file

        Args:
            input_path: File path

        Returns:
            Processing result dictionary, returns None on failure
        """
        try:
            # Detect input type
            input_type = detect_input_type(input_path)

            # Validate input
            if not validate_input(input_path):
                return None

            # Check for duplicate file
            if self.deduplicator.is_duplicate(input_path):
                # If duplicate file, use cached result
                return self.deduplicator.get_cached_result(input_path)

            # Select processor based on type
            if input_type in self.processor_map:
                processor = self.processor_map[input_type]
                result = processor.process(input_path)

                # Set processed_type field
                result['processed_type'] = input_type

                # Cache result
                self.deduplicator.cache_result(input_path, result)

                return result
            else:
                return None

        except Exception as e:
            error_msg = f"Error processing {input_path}: {str(e)}"
            handle_file_error(input_path, e)
            return None
