"""
Text Processing Module

Responsible for processing various text files and normalizing them
"""
import os
import chardet
from typing import Dict, Any
from pathlib import Path


class TextProcessor:
    def __init__(self):
        pass

    def process(self, file_path: str) -> Dict[str, Any]:
        """
        Process text file

        Args:
            file_path: Text file path

        Returns:
            Dict: Dictionary containing processed text content and metadata
        """
        file_extension = Path(file_path).suffix.lower()

        # Select processing method based on file extension
        if file_extension in ['.docx', '.doc']:
            content = self._read_word_file(file_path)
            # For Word documents, use UTF-8 encoding
            encoding = 'utf-8'
        else:
            # Detect file encoding
            encoding = self._detect_encoding(file_path)

            # Read file content
            content = self._read_file(file_path, encoding)

        # Normalize content (preserve first-line indent, only handle large blank spaces between paragraphs)
        normalized_content = self._normalize_content(content)

        # Extract metadata
        metadata = self._extract_metadata(file_path, encoding, normalized_content)

        return {
            "type": "text",
            "content": normalized_content,
            "metadata": metadata,
            "source_file": file_path
        }

    def _detect_encoding(self, file_path: str) -> str:
        """
        Detect file encoding

        Args:
            file_path: File path

        Returns:
            str: Detected encoding format
        """
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding']

            # If detection fails, use default encoding
            if encoding is None:
                encoding = 'utf-8'

        return encoding

    def _read_file(self, file_path: str, encoding: str) -> str:
        """
        Read file content

        Args:
            file_path: File path
            encoding: File encoding

        Returns:
            str: File content
        """
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()
        return content

    def _read_word_file(self, file_path: str) -> str:
        """
        Read Word document content

        Args:
            file_path: Word document path

        Returns:
            str: Document content
        """
        from docx import Document

        doc = Document(file_path)
        paragraphs = []
        for paragraph in doc.paragraphs:
            paragraphs.append(paragraph.text)

        return '\n'.join(paragraphs)

    def _normalize_content(self, content: str) -> str:
        """
        Normalize text content, preserve first-line indent, only remove large blank spaces between paragraphs

        Args:
            content: Original text content

        Returns:
            str: Normalized text content
        """
        # Unify line breaks to \n
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        # Split by paragraphs (separated by one or more blank lines)
        paragraphs = content.split('\n\n')

        normalized_paragraphs = []
        for paragraph in paragraphs:
            # Preserve line breaks and indentation within paragraphs
            lines = paragraph.split('\n')
            normalized_lines = []

            for line in lines:
                # Only remove trailing whitespace, preserve leading indentation
                normalized_line = line.rstrip()
                if normalized_line:  # Only add non-empty lines
                    normalized_lines.append(normalized_line)

            # Reassemble paragraph
            if normalized_lines:  # Only add non-empty paragraphs
                normalized_paragraph = '\n'.join(normalized_lines)
                normalized_paragraphs.append(normalized_paragraph)

        # Join paragraphs with double line breaks, maintain paragraph structure
        normalized_content = '\n\n'.join(normalized_paragraphs)

        return normalized_content

    def _extract_metadata(self, file_path: str, encoding: str, content: str) -> Dict[str, Any]:
        """
        Extract text file metadata

        Args:
            file_path: File path
            encoding: File encoding
            content: File content

        Returns:
            Dict: Metadata dictionary
        """
        return {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "character_count": len(content),
            "line_count": len(content.split('\n')),
            "paragraph_count": len(content.split('\n\n')),  # Number of paragraphs
            "encoding": encoding,
            "file_extension": os.path.splitext(file_path)[1],
            "file_name": os.path.basename(file_path)
        }
