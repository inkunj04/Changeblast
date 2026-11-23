# Investigation Report Template

Use this template when rendering `/changeblast investigate <symbol>`:

```markdown
# 🔍 ChangeBlast Symbol Investigation: `{{SYMBOL_NAME}}`

## Component Coordinates
- **Qualified Name**: `{{QUALIFIED_NAME}}`
- **Kind**: `{{SYMBOL_KIND}}`
- **File**: `{{FILE_PATH}}:{{START_LINE}}-{{END_LINE}}`
- **Mobile Domain**: `{{MOBILE_DOMAIN}}`
- **Platform**: `{{PLATFORM}}`

## Call Hierarchy & Transitive Blast Radius
```text
{{SYMBOL_NAME}} (Target)
{{#each CALLER_CHAIN}}
└── {{CALLER_NAME}} ({{CALLER_KIND}} in {{CALLER_FILE}})
{{/each}}
```

## Potential Runtime Failure Modes
{{POTENTIAL_CONSEQUENCE}}

## Connected Entry Points
- UI Screens / Entry Points: `{{CONNECTED_ENTRY_POINTS}}`
- Downstream Dependents Reached: `{{DEPENDENTS_COUNT}}`

## Targeted Test Recommendations
- [ ] `{{RECOMMENDED_TEST_1}}`
- [ ] `{{RECOMMENDED_TEST_2}}`
```
