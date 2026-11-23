"""Platform adapter ports (Clean Architecture interfaces) for ChangeBlast."""

from changeblast.ports.graph import IDependencyGraphAdapter
from changeblast.ports.parser import ILanguageParserAdapter
from changeblast.ports.reporter import IReportFormatterAdapter
from changeblast.ports.vcs import IVcsAdapter

__all__ = [
    "IDependencyGraphAdapter",
    "ILanguageParserAdapter",
    "IReportFormatterAdapter",
    "IVcsAdapter",
]
