# Workflow: Deep Symbol Investigation (`/changeblast investigate`)

Traces the dependency graph, callers, and runtime blast radius of a specific symbol, class, or method.

## Step-by-Step Execution

1. **Extract Target Symbol**:
   - The user specifies a symbol name or pattern: `/changeblast investigate CheckoutViewModel` or `/changeblast investigate acknowledgePurchase`.

2. **Execute Filtered Impact Analysis**:
   ```bash
   changeblast analyze --symbol <symbol-name> --format json
   ```

3. **Analyze Call Path & Dependents**:
   - Map from top-level UI entry points down to the target symbol.
   - Identify direct callers and transitive dependents.
   - Determine which mobile architectural domain is touched.
   - Evaluate concrete failure modes if this symbol returns invalid data, throws exceptions, or leaks state.

4. **Render Investigation Report**:
   Use [templates/investigation_report.md](file:///skills/changeblast/templates/investigation_report.md):
   - **Target Symbol Metadata**: Kind, File Path, Location, Annotations.
   - **Downstream Blast Radius**: All components affected if this symbol changes.
   - **Potential Consequence**: Concrete runtime risks (crashes, memory leaks, recomposition storms).
   - **Targeted Test Cases**: Specific unit and integration test strategies to isolate this symbol.
