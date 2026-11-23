"""Pytest configuration and synthetic fixtures for ChangeBlast tests."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from changeblast.models import (
    AnalysisWarning,
    ChangedFile,
    ChangeSet,
    ChangeType,
    DependencyEdge,
    DiffHunk,
    EdgeKind,
    EvidenceReference,
    EvidenceType,
    ImpactFinding,
    ImpactReport,
    Language,
    LineRange,
    Platform,
    RepositoryProfile,
    RiskAssessment,
    RiskLevel,
    SourceLocation,
    SourceSymbol,
    SummaryMetrics,
    SymbolKind,
    VcsMetadata,
    Visibility,
    WarningCategory,
)


@pytest.fixture
def sample_location() -> SourceLocation:
    """Fixture returning a standard SourceLocation."""
    return SourceLocation(
        file_path="app/src/main/kotlin/com/example/auth/AuthManager.kt",
        start_line=15,
        start_column=4,
        end_line=28,
        end_column=5,
    )


@pytest.fixture
def sample_symbol(sample_location: SourceLocation) -> SourceSymbol:
    """Fixture returning a representative SourceSymbol."""
    return SourceSymbol(
        id="kt://com.example.auth.AuthManager#authenticate",
        name="authenticate",
        qualified_name="com.example.auth.AuthManager.authenticate",
        kind=SymbolKind.FUNCTION,
        language=Language.KOTLIN,
        visibility=Visibility.PUBLIC,
        location=sample_location,
        container_id="kt://com.example.auth.AuthManager",
        signature="fun authenticate(username: String, token: String): AuthResult",
        annotations=["@WorkerThread"],
        is_entry_point=False,
        is_test=False,
    )


@pytest.fixture
def sample_edge(sample_location: SourceLocation) -> DependencyEdge:
    """Fixture returning a standard DependencyEdge."""
    return DependencyEdge(
        source_symbol_id="kt://com.example.ui.LoginViewModel#onLoginClicked",
        target_symbol_id="kt://com.example.auth.AuthManager#authenticate",
        edge_kind=EdgeKind.CALLS,
        location=sample_location,
        is_dynamic=False,
        weight=1.0,
    )


@pytest.fixture
def sample_evidence(sample_location: SourceLocation) -> EvidenceReference:
    """Fixture returning a verifiable EvidenceReference."""
    return EvidenceReference(
        evidence_type=EvidenceType.CALL_SITE,
        location=sample_location,
        description="LoginViewModel calls AuthManager.authenticate inside coroutine scope",
        snippet="val result = authManager.authenticate(user, pass)",
    )


@pytest.fixture
def sample_finding(
    sample_symbol: SourceSymbol,
    sample_evidence: EvidenceReference,
) -> ImpactFinding:
    """Fixture returning an ImpactFinding."""
    return ImpactFinding(
        finding_id="finding-auth-001",
        target_symbol=sample_symbol,
        root_changed_symbol_id="kt://com.example.auth.AuthManager#authenticate",
        depth=1,
        propagation_path=[
            "kt://com.example.auth.AuthManager#authenticate",
            "kt://com.example.ui.LoginViewModel#onLoginClicked",
        ],
        evidence=[sample_evidence],
        is_breaking=True,
        is_ui_affected=True,
        suggested_tests=["com.example.auth.AuthManagerTest"],
    )


@pytest.fixture
def sample_changeset() -> ChangeSet:
    """Fixture returning a populated ChangeSet."""
    return ChangeSet(
        base_ref="main",
        target_ref="feature/auth-v2",
        is_working_tree=False,
        changed_files=[
            ChangedFile(
                path="app/src/main/kotlin/com/example/auth/AuthManager.kt",
                change_type=ChangeType.MODIFIED,
                changed_line_ranges=[LineRange(start_line=15, end_line=30)],
                hunks=[
                    DiffHunk(
                        old_start=15,
                        old_length=12,
                        new_start=15,
                        new_length=15,
                        header="fun authenticate",
                    ),
                ],
            )
        ],
        total_additions=15,
        total_deletions=12,
    )


@pytest.fixture
def sample_profile() -> RepositoryProfile:
    """Fixture returning a standard RepositoryProfile."""
    return RepositoryProfile(
        root_path="/workspace/sample-mobile-app",
        platforms=[Platform.ANDROID],
        languages=[Language.KOTLIN, Language.JAVA],
        source_roots=["app/src/main/kotlin", "app/src/main/java"],
        test_roots=["app/src/test/kotlin"],
        build_files=["build.gradle.kts", "settings.gradle.kts"],
        vcs=VcsMetadata(
            vcs_type="git",
            branch="feature/auth-v2",
            commit_sha="a1b2c3d4e5f6",
            is_dirty=False,
        ),
    )


@pytest.fixture
def sample_report(
    sample_profile: RepositoryProfile,
    sample_changeset: ChangeSet,
    sample_finding: ImpactFinding,
) -> ImpactReport:
    """Fixture returning a complete ImpactReport."""
    return ImpactReport(
        report_id="report-20261123-001",
        timestamp="2026-11-23T12:00:00Z",
        repository=sample_profile,
        changeset=sample_changeset,
        summary=SummaryMetrics(
            total_files_changed=1,
            directly_modified_symbols=1,
            direct_impacts_count=1,
            transitive_impacts_count=0,
            affected_ui_components_count=1,
            suggested_tests_count=1,
        ),
        overall_risk=RiskAssessment(
            level=RiskLevel.HIGH,
            score=65.0,
            reasons=["Public API signature modified in AuthManager", "Impacts LoginViewModel"],
            breaking_change_signals=["Parameter token added to authenticate()"],
        ),
        findings=[sample_finding],
        warnings=[
            AnalysisWarning(
                warning_id="warn-001",
                category=WarningCategory.SYNTAX_ERROR_RECOVERY,
                message="Handled recoverable syntax discrepancy on line 42",
                file_path="app/src/main/kotlin/com/example/auth/AuthManager.kt",
                line_number=42,
            )
        ],
        suggested_tests=["com.example.auth.AuthManagerTest"],
    )


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Fixture creating a temporary directory for safe filesystem tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# Synthetic Mobile Code Snippets
SYNTHETIC_KOTLIN = """
package com.example.mobile

import androidx.compose.runtime.Composable
import androidx.lifecycle.ViewModel

interface UserRepository {
    fun fetchUser(id: String): User
}

class UserViewModel(private val repository: UserRepository) : ViewModel() {
    fun loadUserProfile(userId: String) {
        val user = repository.fetchUser(userId)
    }
}

@Composable
fun UserProfileScreen(viewModel: UserViewModel) {
    // Composable UI entry point
}
"""

SYNTHETIC_JAVA = """
package com.example.android;

import android.app.Activity;
import android.os.Bundle;

public class MainActivity extends Activity {
    private AuthService authService;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        authService = new AuthService();
        authService.startSession();
    }
}
"""

SYNTHETIC_SWIFT = """
import SwiftUI
import XCTest

protocol PaymentGateway {
    func processPayment(amount: Double) async throws -> Bool
}

@MainActor
final class CheckoutViewModel: ObservableObject {
    @Published var isProcessing: Bool = false
    private let gateway: PaymentGateway

    init(gateway: PaymentGateway) {
        self.gateway = gateway
    }

    func submitPayment(amount: Double) async {
        isProcessing = true
        _ = try? await gateway.processPayment(amount: amount)
        isProcessing = false
    }
}

struct CheckoutView: View {
    @StateObject var viewModel: CheckoutViewModel

    var body: some View {
        Text("Checkout")
    }
}
"""
