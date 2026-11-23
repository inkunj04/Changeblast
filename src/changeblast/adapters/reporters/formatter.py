"""Concrete report formatter adapter rendering JSON, Markdown, and terminal summaries."""

from __future__ import annotations

from changeblast.models.common import RiskLevel
from changeblast.models.report import ImpactReport
from changeblast.ports.reporter import IReportFormatterAdapter


class ReportFormatter(IReportFormatterAdapter):
    """Formats ImpactReport objects into schema-compliant JSON, Markdown, or terminal summaries."""

    def format_json(self, report: ImpactReport, indent: int = 2) -> str:
        """Serialize report to formatted, schema-compliant JSON string."""
        return report.model_dump_json(indent=indent)

    def format_markdown(self, report: ImpactReport) -> str:
        """Render report into GitHub-flavored Markdown suitable for PR comments and docs."""
        lines: list[str] = []

        # 1. Header & Executive Summary
        risk = report.overall_risk
        risk_emoji = {
            RiskLevel.CRITICAL: "🚨",
            RiskLevel.HIGH: "⚠️",
            RiskLevel.MEDIUM: "⚡",
            RiskLevel.LOW: "✅",
        }.get(risk.level, "ℹ️")

        lines.append(f"# {risk_emoji} ChangeBlast Impact Report")
        lines.append("")
        lines.append(
            f"**Overall Risk**: `{risk.level.upper()}` ({risk.score:.1f}/100) &nbsp;|&nbsp; "
            f"**Confidence**: `{risk.confidence.upper()}` &nbsp;|&nbsp; "
            f"**Report ID**: `{report.report_id}`"
        )
        lines.append("")

        # 2. Summary Metrics Table
        sm = report.summary
        lines.append("## Summary Metrics")
        lines.append("")
        lines.append("| Metric | Count |")
        lines.append("| :--- | :--- |")
        lines.append(f"| **Files Changed** | {sm.total_files_changed} |")
        lines.append(f"| **Directly Modified Symbols** | {sm.directly_modified_symbols} |")
        lines.append(f"| **Direct Dependents (Depth 1)** | {sm.direct_impacts_count} |")
        lines.append(f"| **Transitive Dependents (Depth 2+)** | {sm.transitive_impacts_count} |")
        lines.append(f"| **Affected UI Components** | {sm.affected_ui_components_count} |")
        lines.append(f"| **Affected Modules** | {sm.affected_modules_count} |")
        lines.append(f"| **Recommended Tests** | {sm.suggested_tests_count} |")
        lines.append(f"| **Missing Test Coverage** | {sm.missing_test_coverage_count} |")
        lines.append("")

        # 3. Breaking Changes Signals
        if risk.breaking_change_signals:
            lines.append("### ⚠️ Potential Breaking Changes")
            lines.append("")
            for sig in risk.breaking_change_signals:
                lines.append(f"- **{sig}**")
            lines.append("")

        # 4. Risk Factors & Contributing Reasons
        lines.append("### Contributing Risk Factors")
        lines.append("")
        for reason in risk.reasons:
            lines.append(f"- {reason}")
        lines.append("")

        # 5. Directly Modified Symbols
        direct_findings = [f for f in report.findings if f.depth == 0]
        if direct_findings:
            lines.append("## Directly Modified Symbols")
            lines.append("")
            lines.append("| Symbol | Kind | File | Breaking? | Severity |")
            lines.append("| :--- | :--- | :--- | :---: | :---: |")
            for df in direct_findings:
                sym = df.target_symbol
                breaking_str = "Yes" if df.is_breaking else "No"
                lines.append(
                    f"| `{sym.name}` | `{sym.kind}` | `{sym.location.file_path}:{sym.location.start_line}` | {breaking_str} | `{df.severity.upper()}` |"
                )
            lines.append("")

        # 6. Transitive Blast Radius & Propagation Paths
        transitive_findings = [f for f in report.findings if f.depth > 0]
        if transitive_findings:
            lines.append("## Transitive Blast Radius")
            lines.append("")
            lines.append("| Target Component | Depth | Propagation Chain | Confidence |")
            lines.append("| :--- | :---: | :--- | :---: |")
            for tf in transitive_findings:
                path_str = " ➔ ".join(
                    f"`{p.split('//')[-1].split('#')[-1]}`" for p in tf.propagation_path
                )
                lines.append(
                    f"| `{tf.target_symbol.name}` | {tf.depth} | {path_str} | `{tf.confidence}` |"
                )
            lines.append("")

        # 7. Affected Modules
        if report.affected_modules:
            lines.append("## Affected Modules")
            lines.append("")
            for mod in report.affected_modules:
                lines.append(f"- `{mod}`")
            lines.append("")

        # 8. Regression Test Recommendations
        lines.append("## Recommended Regression Tests")
        lines.append("")
        if report.suggested_tests:
            for test in report.suggested_tests:
                lines.append(f"- [ ] `{test}`")
        else:
            lines.append("_No automated tests identified matching affected components._")
        lines.append("")

        # 9. Warnings & Limitations
        if report.warnings:
            lines.append("## 🔍 Analysis Warnings & Limitations")
            lines.append("")
            for w in report.warnings:
                remediation = f" *(Remediation: {w.remediation})*" if w.remediation else ""
                lines.append(f"- **[{w.category.upper()}]** {w.message}{remediation}")
            lines.append("")

        return "\n".join(lines)

    def format_summary(self, report: ImpactReport) -> str:
        """Render concise plain-text or ANSI terminal summary."""
        risk = report.overall_risk
        sm = report.summary

        lines = [
            f"ChangeBlast Analysis: {report.repository.root_path}",
            f"  Risk Level: {risk.level.upper()} ({risk.score:.1f}/100) [Confidence: {risk.confidence.upper()}]",
            f"  Files Changed: {sm.total_files_changed} | Directly Modified: {sm.directly_modified_symbols}",
            f"  Direct Dependents: {sm.direct_impacts_count} | Transitive Blast Radius: {sm.transitive_impacts_count}",
            f"  UI Components Impacted: {sm.affected_ui_components_count} | Affected Modules: {sm.affected_modules_count}",
            f"  Recommended Tests: {sm.suggested_tests_count} | Missing Coverage: {sm.missing_test_coverage_count}",
        ]

        if report.affected_modules:
            lines.append(f"  Modules: {', '.join(report.affected_modules)}")

        if risk.breaking_change_signals:
            lines.append("  Breaking Signals:")
            for b in risk.breaking_change_signals:
                lines.append(f"    - {b}")

        if report.suggested_tests:
            lines.append("  Recommended Tests:")
            for t in report.suggested_tests[:5]:
                lines.append(f"    - {t}")
            if len(report.suggested_tests) > 5:
                lines.append(f"    ... and {len(report.suggested_tests) - 5} more")

        return "\n".join(lines)
