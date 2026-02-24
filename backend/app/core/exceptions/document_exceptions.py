"""
Custom exceptions for Document Service.
"""


class DocumentServiceError(Exception):
    """Base exception for document service errors."""

    pass


class UnsupportedFileTypeError(DocumentServiceError):
    """Raised when file type is not supported for parsing."""

    def __init__(self, content_type: str, filename: str):
        self.content_type = content_type
        self.filename = filename
        super().__init__(f"Unsupported file type: {content_type} (file: {filename})")


class ExtractionFailedError(DocumentServiceError):
    """Raised when text extraction fails for a document."""

    def __init__(self, doc_type: str, reason: str):
        self.doc_type = doc_type
        self.reason = reason
        super().__init__(f"Text extraction failed for {doc_type}: {reason}")


class QuotaExceededError(DocumentServiceError):
    """Raised when user document quota is exceeded."""

    def __init__(self, user_id: str, current: int, limit: int):
        self.user_id = user_id
        self.current = current
        self.limit = limit
        super().__init__(f"User {user_id} exceeded document quota: {current}/{limit} points")
