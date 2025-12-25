"""Data models for the Model Manager application."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class UpdateStatus(Enum):
    """Status of model update check."""

    CHECKING = "checking"
    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ModelInfo:
    """Information about a model from HuggingFace."""

    repo_id: str
    author: str
    name: str
    downloads: int = 0
    likes: int = 0
    last_modified: Optional[datetime] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)
    available_files: List[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Get a display-friendly name."""
        return self.repo_id.split("/")[-1]


@dataclass
class LocalModel:
    """Information about a locally downloaded model."""

    repo_id: str
    path: str
    files: List[str] = field(default_factory=list)
    total_size: int = 0
    download_date: Optional[datetime] = None
    commit_sha: Optional[str] = None
    update_status: UpdateStatus = UpdateStatus.UNKNOWN

    @property
    def display_name(self) -> str:
        """Get a display-friendly name."""
        return self.repo_id.split("/")[-1]

    @property
    def author(self) -> str:
        """Get the author from repo_id."""
        return self.repo_id.split("/")[0] if "/" in self.repo_id else "unknown"


@dataclass
class DownloadProgress:
    """Progress information for an ongoing download."""

    repo_id: str
    current_file: str
    current_file_index: int
    total_files: int
    current_file_downloaded: int
    current_file_total: int
    overall_downloaded: int
    overall_total: int
    speed: float = 0.0  # bytes per second
    eta: int = 0  # seconds

    @property
    def current_file_progress(self) -> float:
        """Get current file progress as percentage (0-100)."""
        if self.current_file_total == 0:
            return 0.0
        return (self.current_file_downloaded / self.current_file_total) * 100

    @property
    def overall_progress(self) -> float:
        """Get overall progress as percentage (0-100)."""
        if self.overall_total == 0:
            return 0.0
        return (self.overall_downloaded / self.overall_total) * 100

    @property
    def files_completed(self) -> int:
        """Get number of completed files."""
        return self.current_file_index


@dataclass
class QuantGroup:
    """A group of GGUF files representing a single quantization."""

    name: str  # Base name without multipart suffix
    files: List[str] = field(default_factory=list)
    total_size: int = 0

    @property
    def is_multipart(self) -> bool:
        """Check if this is a multipart model."""
        return len(self.files) > 1

    @property
    def display_name(self) -> str:
        """Get display name with file count if multipart."""
        if self.is_multipart:
            return f"{self.name} ({len(self.files)} files)"
        return self.name
