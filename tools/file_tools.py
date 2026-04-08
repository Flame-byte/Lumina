"""
File Operation Tools Module

Encapsulated using LangChain args_schema pattern
Supports security restrictions: directory whitelist, file extension restrictions
"""

import os
import yaml
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field
from langchain_core.tools import tool


class FileToolsConfig:
    """File Tools Configuration Class (Singleton Pattern)"""

    _instance = None
    _initialized = False

    def __new__(cls, config_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: str = None):
        if FileToolsConfig._initialized:
            return

        # Default configuration path
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        self.config_path = Path(config_path)
        self._config = {}
        self._read_allowed_dirs: List[Path] = []
        self._write_allowed_dirs: List[Path] = []
        self._allowed_extensions: List[str] = []

        self._load_config()
        FileToolsConfig._initialized = True

    def _load_config(self):
        """Load configuration file"""
        if not self.config_path.exists():
            # Use default configuration
            self._read_allowed_dirs = [Path("./").resolve()]
            self._write_allowed_dirs = [Path("./output/").resolve()]
            self._allowed_extensions = [".txt", ".md"]
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}

        file_tools_config = self._config.get("file_tools", {})

        # Load read whitelist directories
        read_dirs = file_tools_config.get("read_allowed_directories", ["./"])
        self._read_allowed_dirs = [self._resolve_path(p) for p in read_dirs]

        # Load write whitelist directories
        write_dirs = file_tools_config.get("write_allowed_directories", ["./output/"])
        self._write_allowed_dirs = [self._resolve_path(p) for p in write_dirs]

        # Load allowed file extensions
        self._allowed_extensions = file_tools_config.get(
            "allowed_extensions", [".txt", ".md"]
        )

    def _resolve_path(self, path_str: str) -> Path:
        """Resolve path to absolute path"""
        path = Path(path_str)
        if not path.is_absolute():
            # Relative to project root
            project_root = Path(__file__).parent.parent
            path = project_root / path
        return path.resolve()

    def is_allowed_read_path(self, file_path: str) -> bool:
        """Check if file path is within the read whitelist"""
        path = Path(file_path)
        if not path.is_absolute():
            project_root = Path(__file__).parent.parent
            path = project_root / file_path

        try:
            resolved_path = path.resolve()
        except (OSError, RuntimeError):
            return False

        for allowed_dir in self._read_allowed_dirs:
            try:
                resolved_path.relative_to(allowed_dir)
                return True
            except ValueError:
                continue

        return False

    def is_allowed_write_path(self, file_path: str) -> bool:
        """Check if file path is within the write whitelist"""
        path = Path(file_path)
        if not path.is_absolute():
            project_root = Path(__file__).parent.parent
            path = project_root / file_path

        try:
            resolved_path = path.resolve()
        except (OSError, RuntimeError):
            return False

        for allowed_dir in self._write_allowed_dirs:
            try:
                resolved_path.relative_to(allowed_dir)
                return True
            except ValueError:
                continue

        return False

    def is_allowed_extension(self, file_path: str) -> bool:
        """Check if file extension is allowed"""
        path = Path(file_path)
        ext = path.suffix.lower()
        return ext in self._allowed_extensions

    def is_allowed_directory(self, dir_path: str) -> bool:
        """Check if directory is within the whitelist"""
        path = Path(dir_path)
        if not path.is_absolute():
            project_root = Path(__file__).parent.parent
            path = project_root / dir_path

        try:
            resolved_path = path.resolve()
        except (OSError, RuntimeError):
            return False

        for allowed_dir in self._read_allowed_dirs:
            try:
                resolved_path.relative_to(allowed_dir)
                return True
            except ValueError:
                continue

        return False

    @property
    def read_allowed_directories(self) -> List[Path]:
        """Get list of allowed read directories"""
        return self._read_allowed_dirs.copy()

    @property
    def write_allowed_directories(self) -> List[Path]:
        """Get list of allowed write directories"""
        return self._write_allowed_dirs.copy()

    @property
    def allowed_extensions(self) -> List[str]:
        """Get list of allowed file extensions"""
        return self._allowed_extensions.copy()


# Get configuration singleton
_config = FileToolsConfig()


class ReadFileQuery(BaseModel):
    """Read file query parameters"""
    file_path: str = Field(description="File path to read")


class WriteFileQuery(BaseModel):
    """Write file query parameters"""
    file_path: str = Field(description="File path to write")
    content: str = Field(description="Content to write")


class ListDirectoryQuery(BaseModel):
    """List directory query parameters"""
    dir_path: str = Field(description="Directory path to list")


@tool(args_schema=ReadFileQuery)
def read_file(file_path: str) -> str:
    """
    Read file content

    Security restrictions:
    - Only read files within whitelist directories
    - Only support .txt and .md extensions
    """
    # 1. Check file extension
    if not _config.is_allowed_extension(file_path):
        return f"Error: Unsupported file type. Only the following extensions are supported: {_config.allowed_extensions}"

    # 2. Check if path is within read whitelist
    if not _config.is_allowed_read_path(file_path):
        allowed_dirs = [str(p) for p in _config.read_allowed_directories]
        return f"Error: File path is not within the allowed read directories. Allowed directories: {allowed_dirs}"

    # 3. Read file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {file_path}"
    except PermissionError:
        return f"Error: No read permission: {file_path}"
    except UnicodeDecodeError:
        return f"Error: File encoding error, please ensure the file is UTF-8 encoded: {file_path}"
    except Exception as e:
        return f"Failed to read file: {str(e)}"


@tool(args_schema=WriteFileQuery)
def write_file(file_path: str, content: str) -> str:
    """
    Write file content (overwrite mode)

    Security restrictions:
    - Only write files within whitelist directories
    - Only support .txt and .md extensions
    - Overwrite mode
    """
    # 1. Check file extension
    if not _config.is_allowed_extension(file_path):
        return f"Error: Unsupported file type. Only the following extensions are supported: {_config.allowed_extensions}"

    # 2. Check if path is within write whitelist
    if not _config.is_allowed_write_path(file_path):
        allowed_dirs = [str(p) for p in _config.write_allowed_directories]
        return f"Error: File path is not within the allowed write directories. Allowed directories: {allowed_dirs}"

    # 3. Write file
    try:
        import os
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"File successfully written: {file_path}"
    except PermissionError:
        return f"Error: No write permission: {file_path}"
    except Exception as e:
        return f"Failed to write file: {str(e)}"


@tool(args_schema=ListDirectoryQuery)
def list_directory(dir_path: str) -> str:
    """
    List directory contents

    Security restrictions:
    - Only list directories within whitelist
    """
    # 1. Check if directory is within whitelist
    if not _config.is_allowed_directory(dir_path):
        allowed_dirs = [str(p) for p in _config.read_allowed_directories]
        return f"Error: Directory is not within the allowed list. Allowed directories: {allowed_dirs}"

    # 2. List directory contents
    try:
        import os
        items = os.listdir(dir_path)
        # Add type markers
        result = []
        for item in items:
            full_path = os.path.join(dir_path, item)
            if os.path.isdir(full_path):
                result.append(f"[DIR]  {item}")
            else:
                result.append(f"[FILE] {item}")
        return "\n".join(result)
    except FileNotFoundError:
        return f"Error: Directory not found: {dir_path}"
    except PermissionError:
        return f"Error: No access permission: {dir_path}"
    except Exception as e:
        return f"Failed to list directory: {str(e)}"


def build_file_read_tool():
    """Build file read tool"""
    return read_file


def build_file_write_tool():
    """Build file write tool"""
    return write_file


def build_file_list_tool():
    """Build file list tool"""
    return list_directory
