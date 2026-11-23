"""Unit tests for Tree-sitter AST parser adapters across Kotlin, Java, and Swift."""

from __future__ import annotations

from pathlib import Path

from changeblast.adapters.parsers import (
    JavaParserAdapter,
    KotlinParserAdapter,
    SwiftParserAdapter,
)
from changeblast.models.common import EdgeKind, Language, SymbolKind


class TestTreeSitterParsers:
    """Validate AST symbol and edge extraction across all 3 mobile languages."""

    # ------------------ KOTLIN ------------------

    def test_kotlin_symbol_and_edge_extraction(self) -> None:
        parser = KotlinParserAdapter()
        assert parser.language == Language.KOTLIN
        assert parser.can_parse(Path("Main.kt"))

        code = b"""
        package com.example.app

        import androidx.compose.runtime.Composable
        import com.example.network.ApiService

        interface UserContract {
            fun getUser(): String
        }

        @Composable
        fun UserScreen(name: String) {
            println(name)
        }

        class AuthManager(private val api: ApiService) : UserContract, BaseService {
            val timeout: Int = 30

            override fun getUser(): String {
                val data = api.fetch()
                UserScreen(data)
                return data
            }
        }
        """
        symbols = parser.parse_symbols(Path("AuthManager.kt"), code)
        edges = parser.extract_dependencies(Path("AuthManager.kt"), code)

        sym_names = {s.name: s for s in symbols}
        assert "UserContract" in sym_names
        assert sym_names["UserContract"].kind == SymbolKind.INTERFACE

        assert "UserScreen" in sym_names
        assert sym_names["UserScreen"].is_entry_point is True

        assert "AuthManager" in sym_names
        assert sym_names["AuthManager"].kind == SymbolKind.CLASS

        assert "getUser" in sym_names
        assert sym_names["getUser"].kind == SymbolKind.METHOD
        assert sym_names["getUser"].container_id == "kt://com.example.app.AuthManager"

        # Check edge extraction
        edge_kinds = {e.edge_kind for e in edges}
        assert EdgeKind.IMPORTS in edge_kinds
        assert EdgeKind.EXTENDS in edge_kinds or EdgeKind.IMPLEMENTS in edge_kinds
        assert EdgeKind.CALLS in edge_kinds

        # Check call sites
        call_targets = {e.target_symbol_id for e in edges if e.edge_kind == EdgeKind.CALLS}
        assert any("fetch" in t for t in call_targets)
        assert any("UserScreen" in t for t in call_targets)

    def test_kotlin_malformed_syntax_graceful_handling(self) -> None:
        """Parser must not crash on broken or incomplete code."""
        parser = KotlinParserAdapter()
        broken_code = b"class Broken { fun incomplete( val x = ;;; {{ "
        symbols = parser.parse_symbols(Path("Broken.kt"), broken_code)
        assert len(symbols) >= 1
        assert symbols[0].name == "Broken"

    # ------------------ JAVA ------------------

    def test_java_symbol_and_edge_extraction(self) -> None:
        parser = JavaParserAdapter()
        assert parser.language == Language.JAVA
        assert parser.can_parse(Path("MainActivity.java"))

        code = b"""
        package com.example.android;

        import java.util.List;
        import android.app.Activity;

        public class MainActivity extends Activity implements Runnable {
            private String token = "secret";

            public MainActivity() {}

            @Override
            public void run() {
                helper.executeTask(token);
                new WorkerThread();
            }
        }
        """
        symbols = parser.parse_symbols(Path("MainActivity.java"), code)
        edges = parser.extract_dependencies(Path("MainActivity.java"), code)

        classes = [s for s in symbols if s.kind == SymbolKind.CLASS]
        assert len(classes) >= 1
        main_act = classes[0]
        assert main_act.name == "MainActivity"
        assert main_act.kind == SymbolKind.CLASS
        assert main_act.is_entry_point is True  # Activity recognized as entry point

        methods = {s.name: s for s in symbols if s.kind == SymbolKind.METHOD}
        assert "run" in methods
        assert methods["run"].kind == SymbolKind.METHOD

        edge_targets = {e.target_symbol_id: e for e in edges}
        assert any("Activity" in t for t in edge_targets)
        assert any("Runnable" in t for t in edge_targets)
        assert any("executeTask" in t for t in edge_targets)
        assert any("WorkerThread" in t for t in edge_targets)

    def test_java_malformed_syntax_graceful_handling(self) -> None:
        parser = JavaParserAdapter()
        broken_code = b"public class Broken { void method(int a "
        symbols = parser.parse_symbols(Path("Broken.java"), broken_code)
        assert len(symbols) >= 1
        assert symbols[0].name == "Broken"

    # ------------------ SWIFT ------------------

    def test_swift_symbol_and_edge_extraction(self) -> None:
        parser = SwiftParserAdapter()
        assert parser.language == Language.SWIFT
        assert parser.can_parse(Path("App.swift"))

        code = b"""
        import SwiftUI

        protocol UserProvider {
            func fetchUser() async -> String
        }

        struct UserProfileView: View {
            @State var username: String = "Alice"
            let provider: UserProvider

            var body: some View {
                Text(username)
            }

            func reload() async {
                let name = await provider.fetchUser()
                print(name)
            }
        }
        """
        symbols = parser.parse_symbols(Path("UserProfileView.swift"), code)
        edges = parser.extract_dependencies(Path("UserProfileView.swift"), code)

        sym_names = {s.name: s for s in symbols}
        assert "UserProvider" in sym_names
        assert sym_names["UserProvider"].kind == SymbolKind.INTERFACE

        assert "UserProfileView" in sym_names
        view_sym = sym_names["UserProfileView"]
        assert view_sym.kind == SymbolKind.STRUCT
        assert view_sym.is_entry_point is True  # Conforms to View

        assert "reload" in sym_names
        assert sym_names["reload"].kind == SymbolKind.METHOD

        edge_targets = {e.target_symbol_id: e for e in edges}
        assert any("UserProvider" in t for t in edge_targets)
        assert any("fetchUser" in t for t in edge_targets)

    def test_swift_malformed_syntax_graceful_handling(self) -> None:
        parser = SwiftParserAdapter()
        broken_code = b"struct Broken: View { var x: Int = "
        symbols = parser.parse_symbols(Path("Broken.swift"), broken_code)
        assert len(symbols) >= 1
        assert symbols[0].name == "Broken"
