"""Unit tests for platform adapter port interfaces."""

from __future__ import annotations

from pathlib import Path

import pytest

from changeblast.models import DependencyEdge, Language, SourceSymbol
from changeblast.ports import (
    IDependencyGraphAdapter,
    ILanguageParserAdapter,
    IReportFormatterAdapter,
    IVcsAdapter,
)


class TestPortContracts:
    """Verify that port interfaces cannot be instantiated directly without implementations."""

    def test_vcs_adapter_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            IVcsAdapter()  # type: ignore[abstract]

    def test_language_parser_adapter_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            ILanguageParserAdapter()  # type: ignore[abstract]

    def test_dependency_graph_adapter_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            IDependencyGraphAdapter()  # type: ignore[abstract]

    def test_report_formatter_adapter_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            IReportFormatterAdapter()  # type: ignore[abstract]

    def test_concrete_mock_parser_implementation(self, sample_symbol: SourceSymbol) -> None:
        """Verify that concrete implementation satisfying the port contract functions properly."""

        class MockKotlinParser(ILanguageParserAdapter):
            @property
            def language(self) -> Language:
                return Language.KOTLIN

            def can_parse(self, file_path: Path) -> bool:
                return file_path.suffix in {".kt", ".kts"}

            def parse_symbols(self, file_path: Path, content: bytes) -> list[SourceSymbol]:
                return [sample_symbol]

            def extract_dependencies(self, file_path: Path, content: bytes) -> list[DependencyEdge]:
                return []

        parser = MockKotlinParser()
        assert parser.language == Language.KOTLIN
        assert parser.can_parse(Path("Main.kt"))
        assert not parser.can_parse(Path("Main.swift"))
        symbols = parser.parse_symbols(Path("Main.kt"), b"")
        assert len(symbols) == 1
        assert symbols[0].name == sample_symbol.name
