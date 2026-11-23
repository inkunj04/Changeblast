"""Unit tests for Android and iOS platform adapters."""

from __future__ import annotations

from pathlib import Path

from changeblast.adapters.platform import AndroidPlatformAdapter, IOSPlatformAdapter
from changeblast.models.common import Platform, SymbolKind


class TestPlatformAdapters:
    """Validate Android and iOS platform coordination and symbol extraction."""

    def test_android_platform_adapter_delegation(self) -> None:
        adapter = AndroidPlatformAdapter()
        assert adapter.platform == Platform.ANDROID
        assert adapter.can_handle(Path("MainActivity.kt"))
        assert adapter.can_handle(Path("MainActivity.java"))
        assert not adapter.can_handle(Path("ContentView.swift"))

        # Test Kotlin parsing
        kt_code = b"class LoginActivity : Activity { fun onCreate() {} }"
        kt_symbols = adapter.parse_file(Path("LoginActivity.kt"), kt_code)
        assert len(kt_symbols) >= 1
        assert kt_symbols[0].name == "LoginActivity"

        # Test Java parsing
        jv_code = b"public class DataService { void fetchData() {} }"
        jv_symbols = adapter.parse_file(Path("DataService.java"), jv_code)
        assert len(jv_symbols) >= 1
        assert jv_symbols[0].name == "DataService"

    def test_ios_platform_adapter_delegation(self) -> None:
        adapter = IOSPlatformAdapter()
        assert adapter.platform == Platform.IOS
        assert adapter.can_handle(Path("AppView.swift"))
        assert not adapter.can_handle(Path("Main.kt"))

        swift_code = b'struct AppView: View { var body: some View { Text("Hi") } }'
        symbols = adapter.parse_file(Path("AppView.swift"), swift_code)
        assert len(symbols) >= 1
        assert symbols[0].name == "AppView"
        assert symbols[0].kind == SymbolKind.STRUCT
        assert symbols[0].is_entry_point is True
