"""Custom exception classes for Model Manager."""


class ModelManagerException(Exception):
    """Base exception for Model Manager."""

    pass


class DownloadError(ModelManagerException):
    """Exception raised when a download fails."""

    pass


class UpdateCheckError(ModelManagerException):
    """Exception raised when update check fails."""

    pass


class NetworkError(ModelManagerException):
    """Exception raised for network-related errors."""

    pass


class StorageError(ModelManagerException):
    """Exception raised for storage-related errors."""

    pass


class ValidationError(ModelManagerException):
    """Exception raised for validation errors."""

    pass


class HuggingFaceError(ModelManagerException):
    """Exception raised for HuggingFace API errors."""

    pass
