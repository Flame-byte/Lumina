"""
PDF Processing Module

Responsible for identifying PDF type and handling text-based, image-based, and mixed PDFs
"""
import os
from typing import Dict, Any, List
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import tempfile


class PDFProcessor:
    def __init__(self, processed_data_dir: str = None):
        self.processed_data_dir = processed_data_dir or tempfile.gettempdir()

    def process(self, file_path: str) -> Dict[str, Any]:
        """
        Process PDF file

        Args:
            file_path: PDF file path

        Returns:
            Dict: Corresponding content and metadata based on PDF type
        """
        # Identify PDF type
        pdf_type = self._identify_pdf_type(file_path)

        if pdf_type == 'text':
            # Text-based PDF: Extract text content
            content = self._extract_text_from_pdf(file_path)
            metadata = self._extract_metadata(file_path, pdf_type, len(content))
            return {
                "type": "text",
                "content": content,
                "metadata": metadata,
                "source_file": file_path
            }
        elif pdf_type == 'image':
            # Image-based PDF: Convert to image files
            image_paths = self._convert_pdf_to_images(file_path)
            metadata = self._extract_metadata(file_path, pdf_type, len(image_paths))
            return {
                "type": "image",
                "content": image_paths,
                "metadata": metadata,
                "source_file": file_path
            }
        elif pdf_type == 'mixed':
            # Mixed PDF: Extract both text and images
            text_content = self._extract_text_from_pdf(file_path)
            image_paths = self._convert_pdf_to_images(file_path)
            metadata = self._extract_metadata(file_path, pdf_type, len(text_content) + len(image_paths))
            return {
                "type": "mixed",
                "content": {
                    "text": text_content,
                    "images": image_paths
                },
                "metadata": metadata,
                "source_file": file_path
            }
        else:
            raise ValueError(f"Unknown PDF type: {pdf_type}")

    def _identify_pdf_type(self, file_path: str) -> str:
        """
        Identify PDF type (text-based, image-based, or mixed)

        Args:
            file_path: PDF file path

        Returns:
            str: PDF type ('text', 'image', 'mixed')
        """
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PdfReader(f)
                total_pages = len(pdf_reader.pages)

                # Check first few pages to determine PDF type
                text_pages = 0
                image_pages = 0

                # Check up to first 5 pages
                check_pages = min(5, total_pages)

                for i in range(check_pages):
                    page = pdf_reader.pages[i]
                    text = page.extract_text()

                    # If page text length exceeds threshold, consider it a text page
                    if len(text.strip()) > 50:  # Threshold can be adjusted
                        text_pages += 1
                    else:
                        image_pages += 1

                # Determine type based on count of text and image pages
                if text_pages == check_pages:
                    return 'text'
                elif image_pages == check_pages:
                    return 'image'
                else:
                    return 'mixed'
        except Exception as e:
            # If PDF read fails, try to convert to images
            try:
                convert_from_path(file_path, first_page=1, last_page=1)
                return 'image'  # If can convert to image, consider it image-based PDF
            except:
                raise e

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text content from PDF

        Args:
            file_path: PDF file path

        Returns:
            str: Extracted text content
        """
        with open(file_path, 'rb') as f:
            pdf_reader = PdfReader(f)
            text_content = []

            for page in pdf_reader.pages:
                text = page.extract_text()
                text_content.append(text)

        return "\n".join(text_content)

    def _convert_pdf_to_images(self, file_path: str) -> List[str]:
        """
        Convert PDF to images

        Args:
            file_path: PDF file path

        Returns:
            List[str]: List of converted image paths
        """
        # Use pdf2image to convert PDF to images
        images = convert_from_path(file_path)

        # Save images to the specified processed data directory
        image_paths = []
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        for i, image in enumerate(images):
            # Generate image filename
            image_filename = f"{base_name}_page_{i+1}.png"
            image_path = os.path.join(self.processed_data_dir, image_filename)

            # Save image
            image.save(image_path, "PNG")
            image_paths.append(image_path)

        return image_paths

    def _extract_metadata(self, file_path: str, pdf_type: str, content_info: Any) -> Dict[str, Any]:
        """
        Extract PDF file metadata

        Args:
            file_path: File path
            pdf_type: PDF type
            content_info: Content related information (text length or image count)

        Returns:
            Dict: Metadata dictionary
        """
        with open(file_path, 'rb') as f:
            pdf_reader = PdfReader(f)
            total_pages = len(pdf_reader.pages)

            # Get PDF document information
            metadata = {
                "file_path": file_path,
                "file_size": os.path.getsize(file_path),
                "total_pages": total_pages,
                "pdf_type": pdf_type,
                "file_extension": os.path.splitext(file_path)[1],
                "file_name": os.path.basename(file_path),
                "creation_time": None,  # PyPDF2 may not be able to get creation time
                "modification_time": None
            }

            # Add document information (if exists)
            if pdf_reader.metadata:
                doc_info = pdf_reader.metadata
                metadata["title"] = getattr(doc_info, 'title', None)
                metadata["author"] = getattr(doc_info, 'author', None)
                metadata["subject"] = getattr(doc_info, 'subject', None)
                metadata["creator"] = getattr(doc_info, 'creator', None)
                metadata["producer"] = getattr(doc_info, 'producer', None)

        # Add specific information based on PDF type
        if pdf_type == 'text':
            metadata["text_length"] = content_info
        elif pdf_type == 'image':
            metadata["image_count"] = content_info
        elif pdf_type == 'mixed':
            metadata["mixed_content_info"] = content_info

        return metadata
