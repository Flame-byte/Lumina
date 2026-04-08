"""
Database Connection Management Module

Responsible for creating and managing SQLite database connections
"""

import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager


# Base data directory
BASE_SESSIONS_DIR = Path("sessions")


def create_session_directory(session_id: str) -> Path:
    """
    Create session directory structure

    Args:
        session_id: Session ID

    Returns:
        Session directory path
    """
    session_dir = BASE_SESSIONS_DIR / session_id
    data_dir = session_dir / "data"

    # Create directory structure
    session_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    return session_dir


def get_session_db_path(session_id: str) -> Path:
    """
    Get session database file path

    Args:
        session_id: Session ID

    Returns:
        SQLite database file path
    """
    session_dir = create_session_directory(session_id)
    return session_dir / "session.db"


def get_session_data_path(session_id: str) -> Path:
    """
    Get session data storage directory path

    Args:
        session_id: Session ID

    Returns:
        Data storage directory path
    """
    session_dir = BASE_SESSIONS_DIR / session_id / "data"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


class SessionDatabase:
    """
    Session database management class

    Provides SQLite database connection and table initialization
    """

    def __init__(self, session_id: str):
        """
        Initialize database connection

        Args:
            session_id: Session ID
        """
        self.session_id = session_id
        self.db_path = get_session_db_path(session_id)
        self._conn: Optional[sqlite3.Connection] = None

        # Initialize database
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database table structure"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'active',
                title TEXT
            )
        """)

        # Create processed_data table (directly use session_id, no longer need preprocessing_sessions table)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_data (
                id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id),
                original_filename TEXT,
                file_type TEXT,
                processed_type TEXT,
                content TEXT,
                metadata TEXT,
                storage_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create message history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id),
                thread_id TEXT,
                role TEXT,
                content TEXT,
                tool_calls TEXT,
                tool_call_id TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create tool execution log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_execution_logs (
                id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id),
                tool_name TEXT,
                input_args TEXT,
                output_result TEXT,
                status TEXT,
                error_message TEXT,
                execution_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    @contextmanager
    def get_cursor(self):
        """Get cursor context manager"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    def create_session(self, title: str = None) -> dict:
        """
        Create session record

        Args:
            title: Session title

        Returns:
            Session info dictionary
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO sessions (id, title, status)
                VALUES (?, ?, 'active')
            """, (self.session_id, title))

            cursor.execute("SELECT * FROM sessions WHERE id = ?", (self.session_id,))
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else {}

    def add_processed_data(
        self,
        data_id: str,
        original_filename: str,
        file_type: str,
        processed_type: str,
        content: str = None,
        metadata: dict = None,
        storage_path: str = None
    ) -> dict:
        """
        Add processed data

        Args:
            data_id: Data ID
            original_filename: Original filename
            file_type: File type
            processed_type: Processed type
            content: Processed content
            metadata: Metadata
            storage_path: Storage path

        Returns:
            Added data info
        """
        import json

        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO processed_data
                (id, session_id, original_filename, file_type,
                 processed_type, content, metadata, storage_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data_id, self.session_id, original_filename, file_type,
                processed_type, content,
                json.dumps(metadata, ensure_ascii=False) if metadata else None,
                storage_path
            ))

            cursor.execute("SELECT * FROM processed_data WHERE id = ?", (data_id,))
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else {}

    def get_processed_data(self) -> list:
        """
        Get all processed data for the session

        Returns:
            List of data
        """
        import json

        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM processed_data
                WHERE session_id = ?
                ORDER BY created_at ASC
            """, (self.session_id,))

            rows = cursor.fetchall()
            result = []
            for row in rows:
                data = self._row_to_dict(row)
                # Parse JSON fields
                if data.get('metadata'):
                    try:
                        data['metadata'] = json.loads(data['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if data.get('content'):
                    try:
                        # Try to parse JSON content (for structured data)
                        data['content'] = json.loads(data['content'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                result.append(data)
            return result

    def get_file_metadata(self) -> list:
        """
        Get file metadata (without content)

        Returns:
            List of file metadata
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, original_filename, file_type, processed_type,
                       metadata, storage_path, created_at
                FROM processed_data
                WHERE session_id = ?
                ORDER BY created_at ASC
            """, (self.session_id,))

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_file_metadata_by_session(self) -> list:
        """
        Get file metadata list for session (query by session_id)

        Returns:
            List of file metadata
        """
        return self.get_file_metadata()

    def add_message(
        self,
        message_id: str,
        thread_id: str,
        role: str,
        content: str,
        tool_calls: list = None,
        tool_call_id: str = None,
        metadata: dict = None
    ) -> dict:
        """
        Add message to history

        Args:
            message_id: Message ID
            thread_id: Thread ID
            role: Role (human/ai/system/tool)
            content: Message content
            tool_calls: Tool calls list
            tool_call_id: Tool call ID
            metadata: Metadata (contains round info)

        Returns:
            Added message info
        """
        import json

        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO messages
                (id, session_id, thread_id, role, content, tool_calls, tool_call_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message_id, self.session_id, thread_id, role, content,
                json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
                tool_call_id,
                json.dumps(metadata, ensure_ascii=False) if metadata else None
            ))

            cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else {}

    def get_messages(self, thread_id: str = None, limit: int = 50) -> list:
        """
        Get message history

        Args:
            thread_id: Thread ID (optional, if not provided gets all messages for the session)
            limit: Maximum number of returns

        Returns:
            List of messages
        """
        import json

        with self.get_cursor() as cursor:
            if thread_id:
                cursor.execute("""
                    SELECT * FROM messages
                    WHERE session_id = ? AND thread_id = ?
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (self.session_id, thread_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM messages
                    WHERE session_id = ?
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (self.session_id, limit))

            rows = cursor.fetchall()
            result = []
            for row in rows:
                msg = self._row_to_dict(row)
                # Parse JSON fields
                if msg.get('tool_calls'):
                    try:
                        msg['tool_calls'] = json.loads(msg['tool_calls'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                # Parse metadata field
                if msg.get('metadata'):
                    try:
                        msg['metadata'] = json.loads(msg['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        msg['metadata'] = {}
                result.append(msg)
            return result

    def add_tool_execution_log(
        self,
        log_id: str,
        tool_name: str,
        input_args: dict,
        output_result: dict,
        status: str,
        error_message: str = None,
        execution_time_ms: int = None
    ) -> dict:
        """
        Add tool execution log

        Args:
            log_id: Log ID
            tool_name: Tool name
            input_args: Input parameters
            output_result: Output result
            status: Status (success/failed)
            error_message: Error message
            execution_time_ms: Execution time (milliseconds)

        Returns:
            Added log info
        """
        import json

        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO tool_execution_logs
                (id, session_id, tool_name, input_args, output_result,
                 status, error_message, execution_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, self.session_id, tool_name,
                json.dumps(input_args, ensure_ascii=False) if input_args else None,
                json.dumps(output_result, ensure_ascii=False) if output_result else None,
                status, error_message, execution_time_ms
            ))

            cursor.execute("SELECT * FROM tool_execution_logs WHERE id = ?", (log_id,))
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else {}

    def get_tool_execution_logs(self, limit: int = 100) -> list:
        """
        Get tool execution logs

        Args:
            limit: Maximum number of returns

        Returns:
            List of logs
        """
        import json

        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM tool_execution_logs
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (self.session_id, limit))

            rows = cursor.fetchall()
            result = []
            for row in rows:
                log = self._row_to_dict(row)
                # Parse JSON fields
                for field in ['input_args', 'output_result']:
                    if log.get(field):
                        try:
                            log[field] = json.loads(log[field])
                        except (json.JSONDecodeError, TypeError):
                            pass
                result.append(log)
            return result

    def update_session_status(self, status: str) -> bool:
        """
        Update session status

        Args:
            status: New status

        Returns:
            Whether successful
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE sessions SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, self.session_id))
            return cursor.rowcount > 0

    def delete_session(self) -> int:
        """
        Delete session and all related data

        Returns:
            Number of deleted data items
        """
        deleted_count = 0

        with self.get_cursor() as cursor:
            # Delete tool logs
            cursor.execute("""
                DELETE FROM tool_execution_logs WHERE session_id = ?
            """, (self.session_id,))
            deleted_count += cursor.rowcount

            # Delete messages
            cursor.execute("""
                DELETE FROM messages WHERE session_id = ?
            """, (self.session_id,))
            deleted_count += cursor.rowcount

            # Delete processed data
            cursor.execute("""
                DELETE FROM processed_data WHERE session_id = ?
            """, (self.session_id,))
            deleted_count += cursor.rowcount

            # Delete session record
            cursor.execute("""
                DELETE FROM sessions WHERE id = ?
            """, (self.session_id,))
            deleted_count += cursor.rowcount

        return deleted_count

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert SQLite Row to dictionary"""
        if row is None:
            return {}
        return dict(row)

    def close(self):
        """Close database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __del__(self):
        """Destructor, ensure connection is closed"""
        self.close()
