"""
Output Formatting Module

Responsible for formatting processing results into standardized format acceptable by Agent
"""
import time
from typing import Dict, Any, List, Union


class OutputFormatter:
    def __init__(self):
        pass

    def format(self,
               user_prompt: str,
               processed_inputs: List[Dict[str, Any]],
               processing_errors: List[str] = None) -> Dict[str, Any]:
        """
        Format output result

        Args:
            user_prompt: Original user prompt
            processed_inputs: List of processed inputs
            processing_errors: List of processing errors

        Returns:
            Dict: Formatted output dictionary
        """
        if processing_errors is None:
            processing_errors = []

        # Calculate processing summary
        processing_summary = self._generate_processing_summary(
            processed_inputs,
            processing_errors
        )

        # Build output dictionary
        output = {
            "user_prompt": user_prompt,
            "processed_inputs": processed_inputs,
            "processing_summary": processing_summary
        }

        return output

    def _generate_processing_summary(self,
                                   processed_inputs: List[Dict[str, Any]],
                                   errors: List[str]) -> Dict[str, Any]:
        """
        Generate processing summary

        Args:
            processed_inputs: List of processed inputs
            errors: List of errors

        Returns:
            Dict: Processing summary
        """
        # Count various input types
        input_type_counts = {}
        total_content_length = 0

        for input_item in processed_inputs:
            input_type = input_item.get('type', 'unknown')
            if input_type not in input_type_counts:
                input_type_counts[input_type] = 0
            input_type_counts[input_type] += 1

            # Count content length
            content = input_item.get('content', '')
            if isinstance(content, str):
                total_content_length += len(content)
            elif isinstance(content, list):
                total_content_length += len(content)
            elif isinstance(content, dict):
                # For dict type, count length of all values
                for value in content.values():
                    if isinstance(value, str):
                        total_content_length += len(value)
                    elif isinstance(value, list):
                        total_content_length += len(value)

        summary = {
            "total_processed_inputs": len(processed_inputs),
            "input_type_distribution": input_type_counts,
            "total_content_length": total_content_length,
            "error_count": len(errors),
            "errors": errors,
            "processing_time": time.time(),  # Record processing timestamp
            "success_rate": len(processed_inputs) / (len(processed_inputs) + len(errors)) if (processed_inputs or errors) else 0
        }

        return summary

    def validate_output_format(self, output: Dict[str, Any]) -> bool:
        """
        Validate if output format meets requirements

        Args:
            output: Output dictionary

        Returns:
            bool: Whether the format is valid
        """
        required_keys = ["user_prompt", "processed_inputs", "processing_summary"]

        for key in required_keys:
            if key not in output:
                return False

        # Validate if processed_inputs is a list
        if not isinstance(output["processed_inputs"], list):
            return False

        # Validate if processing_summary is a dictionary
        if not isinstance(output["processing_summary"], dict):
            return False

        return True
