"""
Preprocessing API Routes Module (Deprecated)

This module is deprecated. Please use the following endpoints in api/routes.py:
- POST /upload - Upload and process files
- GET /session/{session_id}/files - Get session file metadata

Deprecation date: 2026-03-09
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "preprocessing_routes.py is deprecated. Please use /upload and /session/{session_id}/files endpoints in api/routes.py",
    DeprecationWarning,
    stacklevel=2
)

# Keep old code for reference, no longer used
# Original endpoints:
# - POST /preprocessing/start
# - POST /preprocessing/{session_id}/upload
# - GET /preprocessing/{session_id}/status
# - GET /preprocessing/{session_id}/data/{data_id}
# - GET /preprocessing/{session_id}/metadata
# - DELETE /session/{session_id}

