# Risk Disclosure Template

Use this template when breaking changes, critical severity domains, or architectural divergence risks are detected:

```markdown
## 🚨 ChangeBlast Risk Disclosure

> **Risk Level**: `CRITICAL`  
> **Confidence**: `{{CONFIDENCE_LEVEL}}`

### Critical Failure Mode Warning
{{POTENTIAL_CONSEQUENCE}}

### Affected Component
- **Symbol**: `{{SYMBOL_NAME}}` ({{SYMBOL_KIND}})
- **File**: `{{FILE_PATH}}:{{START_LINE}}-{{END_LINE}}`
- **Mobile Domain**: `{{MOBILE_DOMAIN}}`
- **Platform**: `{{PLATFORM}}`

### Root Cause & Evidence
{{EVIDENCE_EXPLANATION}}

### Required Actions Before Merging
1. Review lifecycle / entitlement handling in `{{FILE_PATH}}`.
2. Execute targeted regression test: `{{SUGGESTED_TEST}}`.
3. Check corresponding platform for unintended divergence: `{{CORRESPONDING_COMPONENT}}`.
```
