"""Report formatting and presentation adapter port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from changeblast.models.report import ImpactReport


class IReportFormatterAdapter(ABC):
    """Abstract interface for rendering impact reports into output formats."""

    @abstractmethod
    def format_json(self, report: ImpactReport, indent: int = 2) -> str:
        """Serialize report to formatted, schema-compliant JSON string."""
        ...

    @abstractmethod
    def format_markdown(self, report: ImpactReport) -> str:
        """Render report into GitHub-flavored Markdown suitable for PR comments and docs."""
        ...

    @abstractmethod
    def format_summary(self, report: ImpactReport) -> str:
        """Render concise plain-text or ANSI terminal summary."""
        ...
