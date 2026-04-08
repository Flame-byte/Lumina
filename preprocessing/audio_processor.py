"""
Audio Processing Module

Responsible for converting audio files to text
"""
import os
import tempfile
from typing import Dict, Any
from openai import OpenAI


class AudioProcessor:
    # def __init__(self, processed_data_dir: str = None):
    #     # Initialize FastFlowLM client
    #     self.client = OpenAI(
    #         base_url="http://localhost:52625/v1",  # FastFlowLM local API endpoint
    #         api_key="flm"                          # Placeholder key
    #     )
    def __init__(self, processed_data_dir: str = None, base_url: str = "http://localhost:52625/v1"):
        # Initialize FastFlowLM client
        self.client = OpenAI(
            base_url=base_url,  # FastFlowLM local API endpoint
            api_key="flm"                          # Placeholder key
        )

        # Try to import pydub, set flag if fails
        try:
            from pydub import AudioSegment
            self.AudioSegment = AudioSegment
            self.pydub_available = True
        except ImportError:
            self.AudioSegment = None
            self.pydub_available = False

        # Set processed data directory, default to system temp directory
        self.processed_data_dir = processed_data_dir or tempfile.gettempdir()

    def process(self, file_path: str) -> Dict[str, Any]:
        """
        Process audio file, convert it to text

        Args:
            file_path: Audio file path

        Returns:
            Dict: Dictionary containing converted text and metadata
        """
        # Validate audio file
        if not self._validate_audio_file(file_path):
            raise ValueError(f"Invalid audio file: {file_path}")

        # If pydub is not available, raise exception
        if not self.pydub_available:
            raise ImportError("pydub is not available. Please install pydub and its dependencies.")

        # Convert audio format to FastFlowLM supported format (such as MP3)
        converted_file_path = self._convert_audio_format(file_path)

        try:
            # Use FastFlowLM's whisper model for speech-to-text
            with open(converted_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-v3",
                    file=audio_file
                )

            # Get converted text
            text_content = transcript.text

            # Extract metadata
            metadata = self._extract_metadata(file_path, text_content)

            return {
                "type": "text",
                "content": text_content,
                "metadata": metadata,
                "source_file": file_path
            }
        finally:
            # Clean up temporary conversion file
            if converted_file_path != file_path and os.path.exists(converted_file_path):
                os.remove(converted_file_path)

    def _validate_audio_file(self, file_path: str) -> bool:
        """
        Validate audio file

        Args:
            file_path: File path

        Returns:
            bool: Whether the file is valid
        """
        if not os.path.exists(file_path):
            return False

        # Check if file extension is a supported audio format
        _, ext = os.path.splitext(file_path)
        supported_formats = {'.mp3', '.mp4', '.m4a', '.wav', '.mpga', '.mpeg', '.webm', '.mp4a'}

        if ext.lower() not in supported_formats:
            return False

        # If pydub is not available, only check file existence and size
        if not self.pydub_available:
            return os.path.getsize(file_path) > 0

        # Try to load audio file to verify its integrity
        try:
            audio = self.AudioSegment.from_file(file_path)
            return len(audio) > 0  # Ensure audio has content
        except:
            return False

    def _convert_audio_format(self, file_path: str) -> str:
        """
        Convert audio format to FastFlowLM supported format (MP3)

        Args:
            file_path: Original audio file path

        Returns:
            str: Converted audio file path
        """
        if not self.pydub_available:
            raise ImportError("pydub is not available. Please install pydub and its dependencies.")

        _, ext = os.path.splitext(file_path)

        # If already in supported format, return original path
        if ext.lower() in {'.mp3', '.mp4', '.m4a', '.wav', '.m4p'}:
            return file_path

        # Otherwise convert to MP3 format
        audio = self.AudioSegment.from_file(file_path)

        # Generate temporary file path, save to the specified processed data directory
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        converted_file_path = os.path.join(self.processed_data_dir, f"{base_name}_converted.mp3")

        # Export to MP3 format
        audio.export(converted_file_path, format="mp3")

        return converted_file_path

    def _extract_metadata(self, file_path: str, text_content: str) -> Dict[str, Any]:
        """
        Extract audio file metadata

        Args:
            file_path: File path
            text_content: Converted text content

        Returns:
            Dict: Metadata dictionary
        """
        if not self.pydub_available:
            # If pydub is not available, return basic metadata
            return {
                "file_path": file_path,
                "file_size": os.path.getsize(file_path),
                "file_extension": os.path.splitext(file_path)[1],
                "file_name": os.path.basename(file_path),
                "transcript_length": len(text_content),
                "transcript_word_count": len(text_content.split()),
                "note": "Detailed audio metadata unavailable due to missing pydub dependency"
            }

        # Get audio file information
        audio = self.AudioSegment.from_file(file_path)
        duration = len(audio) / 1000.0  # Convert to seconds

        return {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "duration": duration,  # Audio duration (seconds)
            "sample_rate": audio.frame_rate,
            "channels": audio.channels,
            "bit_depth": audio.sample_width * 8,
            "file_extension": os.path.splitext(file_path)[1],
            "file_name": os.path.basename(file_path),
            "transcript_length": len(text_content),
            "transcript_word_count": len(text_content.split())
        }
