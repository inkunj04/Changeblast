# ChangeBlast JSON Output Schema & Interpretation

The Python engine outputs strict JSON matching JSON Schema Draft 2020-12 (schema version `1.0.0`).

## Top-Level Schema Keys

```json
{
  "schema_version": "1.0.0",
  "report_id": "rpt_...",
  "generated_at": "2026-...",
  "repository": { ... },
  "changeset": { ... },
  "summary": { ... },
  "overall_risk": { ... },
  "findings": [ ... ],
  "suggested_tests": [ ... ],
  "affected_modules": [ ... ],
  "missing_test_coverage": [ ... ],
  "cross_platform_correlations": [ ... ],
  "warnings": [ ... ],
  "static_analysis_limitations": [ ... ]
}
```

## Field Explanations

1. **`summary`**:
   - `total_files_changed`: Total files in changeset.
   - `directly_modified_symbols`: Total symbols whose lines intersect diff hunks.
   - `direct_impacts_count`: Total components directly calling modified symbols.
   - `transitive_impacts_count`: Total downstream components reached transitively.
   - `affected_ui_components_count`: UI entry points in the blast radius.
   - `missing_test_coverage_count`: Impacted production symbols lacking test edges.

2. **`overall_risk`**:
   - `level`: `"critical"` | `"high"` | `"medium"` | `"low"`
   - `confidence`: `"verified"` | `"strong_inference"` | `"possible"` | `"unknown"`
   - `score`: Numeric risk score between `0.0` and `100.0`.
   - `reasons`: Bulleted justification for the rating.
   - `breaking_change_signals`: Explicit breaking change alerts.

3. **`findings[]`**:
   - `target_symbol`: The modified or affected symbol model.
   - `platform`: `"android"` | `"ios"` | `"cross_platform"`.
   - `mobile_domain`: Architectural domain (e.g. `"lifecycle"`, `"billing_subscriptions"`).
   - `severity`: Finding risk level.
   - `confidence`: Finding confidence rating.
   - `potential_consequence`: Concrete mobile runtime failure mode.
   - `affected_dependents`: Downstream symbols reached in the blast radius.
   - `suggested_tests`: Targeted test files to execute for this component.

4. **`cross_platform_correlations[]`**:
   - `feature_name`: Shared feature domain.
   - `android_symbol_id`: Android symbol identifier.
   - `ios_symbol_id`: iOS symbol identifier.
   - `correlation_type`: `"api_contract"` | `"screen_flow"` | `"feature_mapping"`.
   - `notes`: Behavioral divergence disclosure warning.
