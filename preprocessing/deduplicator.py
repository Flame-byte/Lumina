"""
File Deduplication Module

Responsible for detecting duplicate files and reusing cached results
"""
import hashlib
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class Deduplicator:
    def __init__(self, cache_expiry_hours: int = 24):
        """
        Initialize deduplicator

        Args:
            cache_expiry_hours: Cache expiry time (hours)
        """
        self.cache = {}
        self.cache_expiry_hours = cache_expiry_hours

    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate file hash

        Args:
            file_path: File path

        Returns:
            str: SHA-256 hash of the file
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def is_duplicate(self, file_path: str) -> bool:
        """
        Check if file is a duplicate

        Args:
            file_path: File path

        Returns:
            bool: Whether the file is a duplicate
        """
        if not os.path.exists(file_path):
            return False

        file_hash = self._calculate_file_hash(file_path)

        # Check if hash exists in cache
        if file_hash in self.cache:
            cached_item = self.cache[file_hash]

            # Check if cache is expired
            if datetime.now() - cached_item['timestamp'] < timedelta(hours=self.cache_expiry_hours):
                return True

        return False

    def cache_result(self, file_path: str, result: Dict[str, Any]) -> None:
        """
        Cache processing result

        Args:
            file_path: File path
            result: Processing result
        """
        if not os.path.exists(file_path):
            return

        file_hash = self._calculate_file_hash(file_path)

        self.cache[file_hash] = {
            'result': result,
            'timestamp': datetime.now(),
            'file_path': file_path
        }

    def get_cached_result(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get cached processing result

        Args:
            file_path: File path

        Returns:
            Optional[Dict]: Cached processing result, None if not exists
        """
        if not os.path.exists(file_path):
            return None

        file_hash = self._calculate_file_hash(file_path)

        if file_hash in self.cache:
            cached_item = self.cache[file_hash]

            # Check if cache is expired
            if datetime.now() - cached_item['timestamp'] < timedelta(hours=self.cache_expiry_hours):
                return cached_item['result']

        return None

    def cleanup_cache(self) -> None:
        """
        Clean up expired cache items
        """
        current_time = datetime.now()
        expired_hashes = []

        for file_hash, cached_item in self.cache.items():
            if current_time - cached_item['timestamp'] >= timedelta(hours=self.cache_expiry_hours):
                expired_hashes.append(file_hash)

        for file_hash in expired_hashes:
            del self.cache[file_hash]
