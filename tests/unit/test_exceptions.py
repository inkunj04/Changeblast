"""Unit tests for ChangeBlast exceptions and error handling hierarchy."""

from __future__ import annotations

from changeblast.exceptions import (
    ChangeBlastError,
    CliArgumentError,
    ConfigurationError,
    CyclicDependencyError,
    GitReferenceNotFoundError,
    GitRepositoryNotFoundError,
    GraphError,
    ParsingError,
    SchemaValidationError,
    SecurityBoundaryViolationError,
    UnsupportedLanguageError,
    VCSException,
)


class TestExceptions:
    """Verify exception hierarchy, messages, and dictionary serialization."""

    def test_exception_inheritance(self) -> None:
        """All specialized exceptions must derive from ChangeBlastError."""
        assert issubclass(ConfigurationError, ChangeBlastError)
        assert issubclass(SecurityBoundaryViolationError, ChangeBlastError)
        assert issubclass(VCSException, ChangeBlastError)
        assert issubclass(GitRepositoryNotFoundError, VCSException)
        assert issubclass(GitReferenceNotFoundError, VCSException)
        assert issubclass(ParsingError, ChangeBlastError)
        assert issubclass(UnsupportedLanguageError, ParsingError)
        assert issubclass(GraphError, ChangeBlastError)
        assert issubclass(CyclicDependencyError, GraphError)
        assert issubclass(SchemaValidationError, ChangeBlastError)
        assert issubclass(CliArgumentError, ChangeBlastError)

    def test_exception_to_dict_serialization(self) -> None:
        exc = SecurityBoundaryViolationError(
            "Directory traversal escape detected",
            details={"attempted_path": "../../../etc/passwd", "root": "/workspace"},
        )
        assert str(exc) == "Directory traversal escape detected"
        data = exc.to_dict()
        assert data["error_type"] == "SecurityBoundaryViolationError"
        assert data["message"] == "Directory traversal escape detected"
        assert data["details"]["attempted_path"] == "../../../etc/passwd"
