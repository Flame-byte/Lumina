"""
Excel Processing Module

Responsible for converting Excel files to structured format
"""
import os
import pandas as pd
from typing import Dict, Any
import json


class ExcelProcessor:
    def __init__(self):
        pass

    def process(self, file_path: str) -> Dict[str, Any]:
        """
        Process Excel file

        Args:
            file_path: Excel file path

        Returns:
            Dict: Dictionary containing structured data and metadata
        """
        # Read all worksheets from the Excel file
        excel_data = pd.read_excel(file_path, sheet_name=None)

        # Convert to structured format
        structured_data = {}
        for sheet_name, df in excel_data.items():
            # Convert to JSON format (preserve data structure)
            json_data = df.to_dict(orient='records')

            # Convert to Markdown format (for LLM reading)
            markdown_data = df.to_markdown(index=False) if hasattr(df, 'to_markdown') else str(df)

            structured_data[sheet_name] = {
                "json_data": json_data,
                "markdown_data": markdown_data
            }

        # Generate data summary
        data_summary = self._generate_data_summary(excel_data)

        # Extract metadata
        metadata = self._extract_metadata(file_path, excel_data, data_summary)

        return {
            "type": "structured_data",
            "content": structured_data,
            "metadata": metadata,
            "source_file": file_path
        }

    def _generate_data_summary(self, excel_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Generate Excel data summary

        Args:
            excel_data: Excel data dictionary

        Returns:
            Dict: Data summary
        """
        summary = {
            "total_sheets": len(excel_data),
            "sheets_info": {}
        }

        for sheet_name, df in excel_data.items():
            sheet_info = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
                "data_types": {str(col): str(dtype) for col, dtype in df.dtypes.items()},
                "null_counts": {str(col): int(df[col].isnull().sum()) for col in df.columns}
            }
            summary["sheets_info"][sheet_name] = sheet_info

        return summary

    def _extract_metadata(self, file_path: str, excel_data: Dict[str, pd.DataFrame],
                         data_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract Excel file metadata

        Args:
            file_path: File path
            excel_data: Excel data
            data_summary: Data summary

        Returns:
            Dict: Metadata dictionary
        """
        return {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "file_extension": os.path.splitext(file_path)[1],
            "file_name": os.path.basename(file_path),
            "total_sheets": len(excel_data),
            "total_rows": sum(len(df) for df in excel_data.values()),
            "total_columns": sum(len(df.columns) for df in excel_data.values()),
            "data_summary": data_summary
        }
