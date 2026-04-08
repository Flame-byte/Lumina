"""
Error Handling Module

Responsible for error handling, retry mechanism, and error reporting
"""
import time
import logging
from functools import wraps
from typing import Callable, Any, Dict, List


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Retry decorator

    Args:
        max_retries: Maximum number of retries
        delay: Initial delay time
        backoff: Delay time multiplier
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retries = 0
            current_delay = delay

            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        raise e

                    # Wait and retry
                    time.sleep(current_delay)
                    current_delay *= backoff

            return None
        return wrapper
    return decorator


def handle_network_error(file_path: str, exception: Exception) -> None:
    """
    Handle network request errors

    Args:
        file_path: File path
        exception: Exception object
    """
    logging.error(f"Network error processing {file_path}: {str(exception)}")
    # Here you can implement special handling logic for network errors
    # For example: use backup API endpoint, reduce request frequency, etc.


def handle_file_error(file_path: str, exception: Exception) -> None:
    """
    Handle file read errors

    Args:
        file_path: File path
        exception: Exception object
    """
    logging.error(f"File error processing {file_path}: {str(exception)}")
    # Try to read text file with different encodings
    if isinstance(exception, UnicodeDecodeError):
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read()
                logging.info(f"File {file_path} can be read with {encoding} encoding")
                break
            except:
                continue


def handle_api_error(file_path: str, exception: Exception) -> None:
    """
    Handle API call errors

    Args:
        file_path: File path
        exception: Exception object
    """
    logging.error(f"API error processing {file_path}: {str(exception)}")
    # Here you can implement special handling logic for API errors
    # For example: switch to backup API, reduce request frequency, etc.


def log_error(file_path: str, error_msg: str, error_type: str = "general") -> None:
    """
    Log error information

    Args:
        file_path: File path
        error_msg: Error message
        error_type: Error type
    """
    logging.error(f"[{error_type}] Error processing file {file_path}: {error_msg}")


def generate_error_report(errors: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Generate error report

    Args:
        errors: List of errors

    Returns:
        Dict: Error report
    """
    error_types = {}
    total_errors = len(errors)

    for error in errors:
        error_type = error.get('type', 'unknown')
        if error_type not in error_types:
            error_types[error_type] = 0
        error_types[error_type] += 1

    report = {
        "total_errors": total_errors,
        "error_types": error_types,
        "detailed_errors": errors,
        "timestamp": time.time()
    }

    return report


class ErrorHandler:
    def __init__(self):
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('preprocessing_errors.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def handle_error(self, file_path: str, exception: Exception, error_type: str = "general") -> None:
        """
        Unified error handling method

        Args:
            file_path: File path
            exception: Exception object
            error_type: Error type
        """
        error_msg = str(exception)
        self.logger.error(f"[{error_type}] Error processing file {file_path}: {error_msg}")

        # Call specific handler based on error type
        if error_type == "network":
            handle_network_error(file_path, exception)
        elif error_type == "file":
            handle_file_error(file_path, exception)
        elif error_type == "api":
            handle_api_error(file_path, exception)
        else:
            # Generic error handling
            self.logger.info(f"Executing generic error handling process...")
