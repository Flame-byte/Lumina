"""
Input Type Detection Module

Responsible for identifying input file types and validating their effectiveness
"""
import os
import mimetypes
from pathlib import Path


def detect_input_type(file_path: str) -> str:
    """
    Detect input file type

    Args:
        file_path: File path

    Returns:
        str: File type ('text', 'image', 'pdf', 'excel', 'audio', 'unknown')
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File does not exist: {file_path}")

    # Get file extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    # Determine type based on extension
    text_extensions = {'.txt', '.md', '.html', '.htm', '.py', '.js', '.ts', '.json', '.xml', '.doc', '.docx'}
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
    pdf_extensions = {'.pdf'}
    excel_extensions = {'.xlsx', '.xls', '.csv'}  # CSV is only processed by Excel processor
    audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma'}

    if ext in text_extensions:
        if ext == '.csv':
            return 'excel'  # CSV is processed by Excel processor
        return 'text'
    elif ext in image_extensions:
        return 'image'
    elif ext in pdf_extensions:
        return 'pdf'
    elif ext in excel_extensions:
        return 'excel'
    elif ext in audio_extensions:
        return 'audio'
    else:
        # Use mimetypes as fallback
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            if mime_type.startswith('text/'):
                if ext == '.csv':
                    return 'excel'  # CSV is processed by Excel processor
                return 'text'
            elif mime_type.startswith('image/'):
                return 'image'
            elif mime_type == 'application/pdf':
                return 'pdf'
            elif mime_type in ['application/vnd.ms-excel',
                              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                              'text/csv']:
                return 'excel'
            elif mime_type.startswith('audio/'):
                return 'audio'

    return 'unknown'


def validate_input(file_path: str) -> bool:
    """
    Validate input file effectiveness

    Args:
        file_path: File path

    Returns:
        bool: Whether the file is valid
    """
    if not os.path.exists(file_path):
        return False

    if not os.path.isfile(file_path):
        return False

    # Check file size (limit to 100MB)
    file_size = os.path.getsize(file_path)
    if file_size > 100 * 1024 * 1024:  # 100MB
        return False

    # Check if file is readable
    try:
        with open(file_path, 'rb'):
            pass
        return True
    except:
        return False
