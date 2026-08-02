from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorDetails:
    code: str
    message: str
    status_code: int


class TimeRadioError(Exception):
    """Base exception for expected application failures."""

    def __init__(self, details: ErrorDetails) -> None:
        super().__init__(details.message)
        self.details = details


class ConfigurationError(TimeRadioError):
    """Raised when required runtime configuration is unavailable."""


class ExternalServiceError(TimeRadioError):
    """Raised when an external service request fails."""


class MediaProcessingError(TimeRadioError):
    """Raised when uploaded media cannot be normalized or decoded."""


class VoiceReferenceError(TimeRadioError):
    """Raised when a requested voice reference is unavailable."""

