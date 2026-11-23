# Static Analysis Boundaries & Disclosures

ChangeBlast uses deterministic Tree-sitter AST parsing and static call-graph analysis. Static analysis has inherent theoretical boundaries; disclosing these boundaries prevents false developer confidence.

## Inherent Static Analysis Boundaries

1. **Dynamic Reflection & Service Locators**:
   - Code that instantiates classes via `Class.forName("...")` or dynamic string lookups cannot be statically guaranteed.
   - Service locator lookups using dynamic keys can only be identified if the key literal is static.

2. **Dynamic URL and Deep Link Construction**:
   - Deep link routes constructed through complex string concatenation, remote configuration flags, or server-driven UI responses cannot be completely matched to static manifest filters.

3. **Operating System Memory Management & Process Death**:
   - Android process recreation under low memory and iOS watchdog termination (`0x8badf00d`) depend on hardware memory pressure and OS scheduler state at runtime. Static analysis detects potential lifecycle vulnerabilities, not runtime memory pressure.

4. **Server-Side Verification**:
   - In-app purchase verification, StoreKit 2 cryptoseals, and subscription entitlements have server-to-server webhook dependencies that execute out-of-process.

5. **Server-Driven UI**:
   - When screens are dynamically rendered from JSON payloads sent by an API, UI blast radius is dictated by the backend payload schema, not mobile source code alone.

## Presentation Rule
Always include the standard **Static Analysis Limitations** disclosure in full impact reports.
