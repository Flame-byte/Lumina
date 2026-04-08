"""
Session Management Service Module

Provides session lifecycle management functionality
"""

import uuid
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from database.connection import (
    SessionDatabase,
    create_session_directory,
    BASE_SESSIONS_DIR
)
from preprocessing import Preprocessor


class SessionService:
    """
    Session management service

    Responsible for creating, querying, and deleting sessions
    """

    @staticmethod
    def create_session(session_id: str = None, title: str = None) -> dict:
        """
        Create a new session

        Args:
            session_id: Optional session ID, auto-generated if not provided
            title: Session title, auto-generated as "New Session n" format if not provided

        Returns:
            Session info dictionary
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        # Auto-generate "New Session n" format if title not provided
        if title is None:
            # Query current session count
            existing_sessions = SessionService.list_sessions(limit=1000)
            session_number = len(existing_sessions) + 1
            title = f"New Session {session_number}"

        # Create session directory
        create_session_directory(session_id)

        # Create database record
        db = SessionDatabase(session_id)
        session_info = db.create_session(title=title)

        return session_info

    @staticmethod
    def get_session_info(session_id: str) -> Optional[dict]:
        """
        Get session info

        Args:
            session_id: Session ID

        Returns:
            Session info dictionary, None if not exists
        """
        db_path = BASE_SESSIONS_DIR / session_id / "session.db"
        if not db_path.exists():
            return None

        db = SessionDatabase(session_id)
        # Query session record
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_session_status(session_id: str, status: str) -> bool:
        """
        Update session status

        Args:
            session_id: Session ID
            status: New status

        Returns:
            Whether successful
        """
        db = SessionDatabase(session_id)
        return db.update_session_status(status)

    @staticmethod
    def delete_session(session_id: str) -> dict:
        """
        Delete session and all its data

        Args:
            session_id: Session ID

        Returns:
            Delete result dictionary
        """
        import shutil
        import time

        db = None
        try:
            # Delete database record and get deletion count
            db = SessionDatabase(session_id)
            deleted_count = db.delete_session()
        finally:
            # Ensure database connection is closed
            if db:
                db.close()

        # Wait a short time to ensure SQLite releases file lock
        time.sleep(0.1)

        # Delete filesystem directory (with retry mechanism)
        session_dir = BASE_SESSIONS_DIR / session_id
        if session_dir.exists():
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    shutil.rmtree(session_dir)
                    break
                except OSError as e:
                    if e.winerror == 32 and attempt < max_retries - 1:
                        # File is occupied, wait and retry
                        time.sleep(0.5 * (attempt + 1))
                    else:
                        # Other errors or retry exhausted, raise exception
                        raise

        return {
            "status": "deleted",
            "session_id": session_id,
            "deleted_items": deleted_count
        }

    @staticmethod
    def list_sessions(limit: int = 100) -> List[dict]:
        """
        List all sessions

        Args:
            limit: Maximum number of returns

        Returns:
            List of session info
        """
        sessions = []

        # Iterate through sessions directory
        if not BASE_SESSIONS_DIR.exists():
            return sessions

        for session_dir in BASE_SESSIONS_DIR.iterdir():
            if not session_dir.is_dir():
                continue

            session_id = session_dir.name
            db_path = session_dir / "session.db"

            if not db_path.exists():
                continue

            try:
                db = SessionDatabase(session_id)
                with db.get_cursor() as cursor:
                    cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,))
                    for row in cursor.fetchall():
                        sessions.append(dict(row))
            except Exception:
                continue

            if len(sessions) >= limit:
                break

        return sessions

    @staticmethod
    def process_files(
        session_id: str,
        file_paths: List[str]
    ) -> List[dict]:
        """
        Process files and store to database

        Args:
            session_id: Session ID
            file_paths: List of file paths

        Returns:
            List of processed data
        """
        import uuid
        import json
        from preprocessing import Preprocessor

        db = SessionDatabase(session_id)
        preprocessor = Preprocessor()

        # Process files
        processed_files = preprocessor.process(file_paths)

        # Get storage directory
        from database.connection import get_session_data_path
        storage_base = get_session_data_path(session_id)

        processed_items = []

        for file_data in processed_files:
            data_id = str(uuid.uuid4())
            # Get filename from multiple possible fields
            original_filename = (
                file_data.get("filename") or
                file_data.get("metadata", {}).get("file_name") or
                file_data.get("source_file") or
                "unknown"
            )
            # Only get filename if it's a full path
            if original_filename and ("/" in original_filename or "\\" in original_filename):
                original_filename = Path(original_filename).name

            file_type = file_data.get("type", "unknown")
            processed_type = file_data.get("processed_type", "unknown")
            content = file_data.get("content")
            metadata = file_data.get("metadata", {})

            storage_path = None

            # Process storage path (for binary data like images)
            if processed_type in ["image", "mixed"]:
                if isinstance(content, dict) and "images" in content:
                    # Move images to storage directory
                    images_dir = storage_base / "images"
                    images_dir.mkdir(parents=True, exist_ok=True)

                    stored_image_paths = []
                    for img_path in content.get("images", []):
                        img_path_obj = Path(img_path)
                        if img_path_obj.exists():
                            # Copy image to storage directory
                            dest_path = images_dir / img_path_obj.name
                            import shutil
                            shutil.copy2(img_path, str(dest_path))
                            stored_image_paths.append(str(dest_path))

                    content["images"] = stored_image_paths
                    storage_path = str(images_dir)

                elif processed_type == "image" and isinstance(content, str):
                    # Single image
                    images_dir = storage_base / "images"
                    images_dir.mkdir(parents=True, exist_ok=True)

                    img_path_obj = Path(content)
                    if img_path_obj.exists():
                        dest_path = images_dir / img_path_obj.name
                        import shutil
                        shutil.copy2(content, str(dest_path))
                        storage_path = str(dest_path)
                        content = f"Image stored at: {storage_path}"

            # For structured data, serialize content to JSON
            if processed_type == "structured_data" and isinstance(content, (dict, list)):
                content = json.dumps(content, ensure_ascii=False)

            # Add data to database
            item = db.add_processed_data(
                data_id=data_id,
                original_filename=original_filename,
                file_type=file_type,
                processed_type=processed_type,
                content=content,
                metadata=metadata,
                storage_path=storage_path
            )

            processed_items.append(item)

        return processed_items

    @staticmethod
    def get_processed_data(session_id: str) -> List[dict]:
        """
        Get all processed data for the session

        Args:
            session_id: Session ID

        Returns:
            List of data
        """
        db = SessionDatabase(session_id)
        return db.get_processed_data()

    @staticmethod
    def get_file_metadata(session_id: str) -> List[dict]:
        """
        Get list of file metadata

        Args:
            session_id: Session ID

        Returns:
            List of file metadata
        """
        db = SessionDatabase(session_id)
        return db.get_file_metadata()
