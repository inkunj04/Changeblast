"""Domain exceptions and error hierarchy for ChangeBlast.

All errors raised by ChangeBlast derive from ChangeBlastError to ensure
predictable error handling and clean exit codes across CLI and library consumers.
"""

from __future__ import annotations

from typing import Any


class ChangeBlastError(Exception):
    """Base exception for all errors raised within ChangeBlast."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception details to a structured dictionary."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class ConfigurationError(ChangeBlastError):
    """Raised when application or environment configuration is invalid."""


class SecurityBoundaryViolationError(ChangeBlastError):
    """Raised when an operation attempts to breach security boundaries.

    Examples: Path traversal outside repository root, symlink loop,
    unauthorized subprocess injection.
    """


class VCSException(ChangeBlastError):
    """Base exception for version control and git operations."""


class GitRepositoryNotFoundError(VCSException):
    """Raised when a directory is not a valid git repository."""


class GitReferenceNotFoundError(VCSException):
    """Raised when a specified git reference or commit SHA cannot be resolved."""


class ParsingError(ChangeBlastError):
    """Raised when source code parsing encounters a fatal error."""


class UnsupportedLanguageError(ParsingError):
    """Raised when a file extension or language is not supported by ChangeBlast."""


class GraphError(ChangeBlastError):
    """Base exception for dependency graph operations."""


class CyclicDependencyError(GraphError):
    """Raised when a cyclic dependency halts traversal unexpectedly."""


class SchemaValidationError(ChangeBlastError):
    """Raised when a data payload fails schema validation or version checks."""


class CliArgumentError(ChangeBlastError):
    """Raised when CLI arguments fail validation."""
