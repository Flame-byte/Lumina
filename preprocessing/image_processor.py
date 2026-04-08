"""
Image Processing Module

Responsible for processing image files and generating metadata and thumbnails
"""
import os
from PIL import Image
from typing import Dict, Any
import tempfile


class ImageProcessor:
    def __init__(self, processed_data_dir: str = None):
        self.processed_data_dir = processed_data_dir or tempfile.gettempdir()

    def process(self, file_path: str) -> Dict[str, Any]:
        """
        Process image file

        Args:
            file_path: Image file path

        Returns:
            Dict: Dictionary containing processed image path, metadata, and thumbnail path
        """
        # Validate image file
        if not self._validate_image(file_path):
            raise ValueError(f"Invalid image file: {file_path}")

        # Open image and extract metadata
        with Image.open(file_path) as img:
            # Get basic image information
            width, height = img.size
            format = img.format
            mode = img.mode

            # Extract EXIF data (if exists)
            exif_data = img.info.get('exif', None)

        # Generate thumbnail
        thumbnail_path = self._generate_thumbnail(file_path)

        # Generate metadata
        metadata = self._extract_metadata(file_path, width, height, format, mode, exif_data)

        return {
            "type": "image",
            "content": file_path,  # Original image path
            "metadata": metadata,
            "source_file": file_path,
            "thumbnail_path": thumbnail_path
        }

    def _validate_image(self, file_path: str) -> bool:
        """
        Validate image file

        Args:
            file_path: File path

        Returns:
            bool: Whether the file is a valid image
        """
        try:
            with Image.open(file_path) as img:
                img.verify()  # Verify image integrity
            return True
        except:
            return False

    def _generate_thumbnail(self, file_path: str, size: tuple = (128, 128)) -> str:
        """
        Generate image thumbnail

        Args:
            file_path: Original image path
            size: Thumbnail size, default is 128x128

        Returns:
            str: Thumbnail save path
        """
        with Image.open(file_path) as img:
            # Convert to RGB mode for compatibility
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            # Generate thumbnail
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # Generate thumbnail filename
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            thumbnail_filename = f"thumb_{base_name}.jpg"

            # Save thumbnail to the specified processed data directory
            thumbnail_path = os.path.join(self.processed_data_dir, thumbnail_filename)
            img.save(thumbnail_path, "JPEG", quality=85)

        return thumbnail_path

    def _extract_metadata(self, file_path: str, width: int, height: int,
                         format: str, mode: str, exif_data: Any) -> Dict[str, Any]:
        """
        Extract image metadata

        Args:
            file_path: File path
            width: Image width
            height: Image height
            format: Image format
            mode: Color mode
            exif_data: EXIF data

        Returns:
            Dict: Metadata dictionary
        """
        return {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "width": width,
            "height": height,
            "dimensions": f"{width}x{height}",
            "format": format,
            "color_mode": mode,
            "file_extension": os.path.splitext(file_path)[1],
            "file_name": os.path.basename(file_path),
            "exif_data": exif_data
        }
