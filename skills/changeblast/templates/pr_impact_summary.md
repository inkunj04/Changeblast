# PR Impact Summary Template

Use this markdown template when rendering `/changeblast pr`:

```markdown
## ⚠️ ChangeBlast Mobile Impact Summary

| Metric | Assessment |
| :--- | :--- |
| **Overall Risk** | `{{OVERALL_RISK_LEVEL}}` (Score: {{RISK_SCORE}}/100) |
| **Evidence Confidence** | `{{CONFIDENCE_LEVEL}}` |
| **Files Changed** | {{TOTAL_FILES}} (+{{ADDITIONS}} / -{{DELETIONS}}) |
| **Directly Modified Symbols** | {{MODIFIED_SYMBOLS_COUNT}} |
| **Impacted UI Entry Points** | {{UI_ENTRY_POINTS_COUNT}} |
| **Transitive Blast Radius** | {{TRANSITIVE_DEPENDENTS_COUNT}} components |

### 🚨 Architectural & Domain Failure Risks

| Platform | Component | Domain | Severity | Potential Consequence |
| :--- | :--- | :--- | :---: | :--- |
| `{{PLATFORM}}` | `{{COMPONENT}}` | `{{DOMAIN}}` | `{{SEVERITY}}` | {{CONSEQUENCE}} |

### 🔄 Cross-Platform Feature Parity

{{#if CROSS_PLATFORM_CORRELATIONS}}
| Feature | Android Component | iOS Component | Basis | Confidence |
| :--- | :--- | :--- | :--- | :---: |
| **{{FEATURE}}** | `{{ANDROID_COMP}}` | `{{IOS_COMP}}` | `{{BASIS}}` | `{{CONFIDENCE}}` |

> **⚠️ Divergence Warning**: Android and iOS implementations differ in lifecycle dispatch and concurrency models. Never assume identically named components share implementation parity.
{{else}}
_No cross-platform feature correlations detected in this diff._
{{/if}}

### ✅ Recommended Targeted Regression Checklist

Before merging, verify the following affected test suites:
- [ ] `{{SUGGESTED_TEST_1}}`
- [ ] `{{SUGGESTED_TEST_2}}`

{{#if MISSING_TESTS}}
### ⚠️ Missing Test Coverage Warnings
The following modified components lack automated test coverage:
- `{{UNTESTED_SYMBOL}}`
{{/if}}

---
<sub>Report generated deterministically by **ChangeBlast** (100% read-only static analysis).</sub>
```
