"""Transparent rule-based risk evaluation engine."""

from __future__ import annotations

from collections.abc import Sequence

from changeblast.models.common import ConfidenceLevel, RiskLevel, SymbolKind
from changeblast.models.finding import ImpactFinding
from changeblast.models.report import RiskAssessment


class RiskEngine:
    """Calculates deterministic risk scores, severity levels, and confidence ratings.

    Strictly separates Severity and Confidence into distinct dimensions without
    inventing statistical failure probabilities.
    """

    def evaluate(
        self,
        findings: Sequence[ImpactFinding],
        affected_modules: Sequence[str],
        missing_test_count: int,
        is_monorepo: bool = False,
    ) -> RiskAssessment:
        """Evaluate findings and return a transparent, reproducible RiskAssessment."""
        if not findings:
            return RiskAssessment(
                level=RiskLevel.LOW,
                confidence=ConfidenceLevel.VERIFIED,
                score=0.0,
                reasons=[
                    "No source symbols were directly or transitively affected by the changes."
                ],
                breaking_change_signals=[],
            )

        score = 0.0
        reasons: list[str] = []
        breaking_signals: list[str] = []

        direct_findings = [f for f in findings if f.depth == 0]
        transitive_findings = [f for f in findings if f.depth > 0]
        ui_findings = [f for f in findings if f.is_ui_affected]
        breaking_findings = [f for f in findings if f.is_breaking]

        # 1. Direct Modifications Contribution
        direct_count = len(direct_findings)
        direct_pts = min(25.0, direct_count * 5.0)
        score += direct_pts
        reasons.append(
            f"Directly modified {direct_count} source symbol{'s' if direct_count != 1 else ''} (+{direct_pts:.1f} pts)"
        )

        # 2. Transitive Blast Radius Contribution
        transitive_count = len(transitive_findings)
        if transitive_count > 0:
            transitive_pts = min(30.0, transitive_count * 2.5)
            score += transitive_pts
            reasons.append(
                f"Transitive blast radius affects {transitive_count} downstream component{'s' if transitive_count != 1 else ''} (+{transitive_pts:.1f} pts)"
            )

        # 3. Breaking Changes Contribution
        if breaking_findings:
            breaking_pts = min(30.0, len(breaking_findings) * 15.0)
            score += breaking_pts
            for bf in breaking_findings:
                msg = f"Potential breaking change in '{bf.target_symbol.name}' ({bf.target_symbol.kind})"
                breaking_signals.append(msg)
            reasons.append(
                f"Identified {len(breaking_findings)} potential breaking change signal{'s' if len(breaking_findings) != 1 else ''} (+{breaking_pts:.1f} pts)"
            )

        # 4. User-Facing UI Impact Contribution
        if ui_findings:
            ui_pts = min(20.0, len(ui_findings) * 5.0)
            score += ui_pts
            reasons.append(
                f"Impact reaches {len(ui_findings)} user-facing UI component{'s' if len(ui_findings) != 1 else ''} or entry point{'s' if len(ui_findings) != 1 else ''} (+{ui_pts:.1f} pts)"
            )

        # 5. Cross-Module Blast Radius Contribution
        module_count = len(affected_modules)
        if module_count > 1:
            module_pts = min(15.0, (module_count - 1) * 5.0)
            score += module_pts
            reasons.append(
                f"Impact propagates across {module_count} distinct modules/targets (+{module_pts:.1f} pts)"
            )

        # 6. Missing Test Coverage Contribution
        if missing_test_count > 0:
            coverage_pts = min(15.0, missing_test_count * 3.0)
            score += coverage_pts
            reasons.append(
                f"No automated tests identified for {missing_test_count} impacted component{'s' if missing_test_count != 1 else ''} (+{coverage_pts:.1f} pts)"
            )

        # Cap score strictly between 0.0 and 100.0
        final_score = round(max(0.0, min(100.0, score)), 1)

        # Categorical Severity Classification
        # Rule-based decision hierarchy
        has_critical_breaking = any(
            bf.is_breaking
            and (
                bf.target_symbol.is_entry_point
                or bf.target_symbol.kind in {SymbolKind.INTERFACE, SymbolKind.CLASS}
            )
            for bf in breaking_findings
        )
        is_sensitive = any(
            any(
                k in f.target_symbol.name.lower()
                for k in ("auth", "security", "token", "payment", "crypto")
            )
            for f in direct_findings
        )

        if (
            any(f.severity == RiskLevel.CRITICAL for f in findings)
            or has_critical_breaking
            or final_score >= 70.0
            or (is_sensitive and len(findings) >= 5)
            or (module_count >= 3 and len(findings) >= 15)
        ):
            level = RiskLevel.CRITICAL
        elif (
            any(f.severity == RiskLevel.HIGH for f in findings)
            or final_score >= 40.0
            or len(ui_findings) >= 2
            or module_count >= 2
        ):
            level = RiskLevel.HIGH
        elif final_score >= 15.0 or transitive_count > 0:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        # Overall Confidence Classification
        # Lowest confidence among individual findings determines aggregate certainty
        order = {
            ConfidenceLevel.VERIFIED: 4,
            ConfidenceLevel.STRONG_INFERENCE: 3,
            ConfidenceLevel.POSSIBLE: 2,
            ConfidenceLevel.UNKNOWN: 1,
        }
        min_order = 4
        overall_confidence = ConfidenceLevel.VERIFIED
        for f in findings:
            c_val = order.get(f.confidence, 1)
            if c_val < min_order:
                min_order = c_val
                overall_confidence = f.confidence

        return RiskAssessment(
            level=level,
            confidence=overall_confidence,
            score=final_score,
            reasons=reasons,
            breaking_change_signals=breaking_signals,
        )
