"""Cross-platform feature correlation engine with behavioral divergence disclosure."""

from __future__ import annotations

import re
from collections.abc import Sequence

from changeblast.models.common import ConfidenceLevel, EvidenceType
from changeblast.models.evidence import EvidenceReference
from changeblast.models.finding import CrossPlatformCorrelation, ImpactFinding
from changeblast.models.symbol import SourceSymbol


class CrossPlatformCorrelator:
    """Correlates corresponding features between native Android and iOS components

    backed by verifiable evidence, while explicitly disclosing behavioral divergence.
    """

    DIVERGENCE_DISCLOSURE = (
        "BEHAVIORAL DIVERGENCE WARNING: Android and iOS implementations differ fundamentally "
        "in lifecycle management, concurrency dispatch, and OS platform contracts. "
        "Never assume identically named components behave identically. "
        "Verify both platforms with dedicated native tests."
    )

    def correlate(
        self,
        android_findings: Sequence[ImpactFinding],
        ios_findings: Sequence[ImpactFinding],
    ) -> list[CrossPlatformCorrelation]:
        """Identify potentially corresponding features between Android and iOS findings."""
        if not android_findings or not ios_findings:
            return []

        correlations: list[CrossPlatformCorrelation] = []
        seen_pairs: set[tuple[str, str]] = set()

        for a_finding in android_findings:
            a_sym = a_finding.target_symbol
            a_stem = self._clean_stem(a_sym.name)
            a_features = set(a_finding.related_features)

            for i_finding in ios_findings:
                i_sym = i_finding.target_symbol
                i_stem = self._clean_stem(i_sym.name)
                i_features = set(i_finding.related_features)
                pair = (a_sym.id, i_sym.id)

                if pair in seen_pairs:
                    continue

                # 1. API Contract Matching
                shared_api = self._extract_shared_api(a_sym, i_sym)
                if shared_api:
                    seen_pairs.add(pair)
                    ev = [
                        EvidenceReference(
                            evidence_type=EvidenceType.API_CONTRACT,
                            location=a_sym.location,
                            description=f"Android and iOS components reference matching API contract endpoint '{shared_api}'",
                        )
                    ]
                    correlations.append(
                        CrossPlatformCorrelation(
                            feature_name=shared_api.strip("/").replace("/", "_"),
                            android_symbol_id=a_sym.id,
                            ios_symbol_id=i_sym.id,
                            correlation_type="api_contract",
                            evidence=ev,
                            confidence=ConfidenceLevel.VERIFIED,
                            notes=f"Correlated via explicit API endpoint contract '{shared_api}'. {self.DIVERGENCE_DISCLOSURE}",
                        )
                    )
                    continue

                # 2. Screen Flow Matching
                if (
                    a_stem
                    and i_stem
                    and a_stem.lower() == i_stem.lower()
                    and (a_finding.is_ui_affected or i_finding.is_ui_affected)
                ):
                    seen_pairs.add(pair)
                    ev = [
                        EvidenceReference(
                            evidence_type=EvidenceType.UI_NAVIGATION,
                            location=a_sym.location,
                            description=f"Matching UI screen flow identifier '{a_stem}' across Android and iOS",
                        )
                    ]
                    correlations.append(
                        CrossPlatformCorrelation(
                            feature_name=a_stem,
                            android_symbol_id=a_sym.id,
                            ios_symbol_id=i_sym.id,
                            correlation_type="screen_flow",
                            evidence=ev,
                            confidence=ConfidenceLevel.STRONG_INFERENCE,
                            notes=f"Corresponding screen flow detected for '{a_stem}'. {self.DIVERGENCE_DISCLOSURE}",
                        )
                    )
                    continue

                # 3. Feature Mapping
                shared_features = a_features & i_features
                if shared_features:
                    feat = sorted(list(shared_features))[0]
                    seen_pairs.add(pair)
                    ev = [
                        EvidenceReference(
                            evidence_type=EvidenceType.FEATURE_MAPPING,
                            location=a_sym.location,
                            description=f"Both components reside within shared architectural feature domain '{feat}'",
                        )
                    ]
                    correlations.append(
                        CrossPlatformCorrelation(
                            feature_name=feat,
                            android_symbol_id=a_sym.id,
                            ios_symbol_id=i_sym.id,
                            correlation_type="feature_mapping",
                            evidence=ev,
                            confidence=ConfidenceLevel.STRONG_INFERENCE,
                            notes=f"Attributed to shared architectural domain '{feat}'. {self.DIVERGENCE_DISCLOSURE}",
                        )
                    )
                    continue

                # 4. Shared Behavior / Domain Model Matching
                if a_stem and i_stem and a_stem.lower() == i_stem.lower():
                    seen_pairs.add(pair)
                    ev = [
                        EvidenceReference(
                            evidence_type=EvidenceType.TYPE_REFERENCE,
                            location=a_sym.location,
                            description=f"Matching domain model stem '{a_stem}'",
                        )
                    ]
                    correlations.append(
                        CrossPlatformCorrelation(
                            feature_name=a_stem,
                            android_symbol_id=a_sym.id,
                            ios_symbol_id=i_sym.id,
                            correlation_type="shared_behavior",
                            evidence=ev,
                            confidence=ConfidenceLevel.POSSIBLE,
                            notes=f"Domain model nominal correspondence '{a_stem}'. {self.DIVERGENCE_DISCLOSURE}",
                        )
                    )

        return sorted(correlations, key=lambda c: (c.confidence, c.feature_name))

    def _clean_stem(self, name: str) -> str:
        """Strip mobile framework suffixes to isolate semantic feature stems."""
        suffixes = (
            "Activity",
            "Fragment",
            "ViewController",
            "Screen",
            "View",
            "ViewModel",
            "Service",
            "Controller",
            "Coordinator",
            "Router",
            "Adapter",
            "Dao",
            "Entity",
            "Manager",
            "Client",
        )
        cleaned = name
        for s in suffixes:
            if cleaned.endswith(s) and len(cleaned) > len(s):
                cleaned = cleaned[: -len(s)]
                break
        return cleaned

    def _extract_shared_api(self, sym1: SourceSymbol, sym2: SourceSymbol) -> str | None:
        """Detect identical API path literals referenced in annotations or signatures."""
        api_pattern = re.compile(r'["\'](/(?:api/|v[0-9]+/|[a-zA-Z0-9_-]+/)[a-zA-Z0-9_/-]+)["\']')

        sig1 = (sym1.signature or "") + " " + " ".join(sym1.annotations)
        sig2 = (sym2.signature or "") + " " + " ".join(sym2.annotations)

        m1: set[str] = set(api_pattern.findall(sig1))
        m2: set[str] = set(api_pattern.findall(sig2))

        shared = m1 & m2
        if shared:
            return str(sorted(shared)[0])
        return None
