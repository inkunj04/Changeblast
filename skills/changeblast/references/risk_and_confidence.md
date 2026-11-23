# Severity vs. Confidence Rules

ChangeBlast enforces an absolute architectural separation between **Risk Severity** (impact blast radius) and **Evidence Confidence** (certainty of static proof).

## Risk Severity (Impact Dimension)

Severity measures what could break if the changed component behaves abnormally:

* **CRITICAL**:
  - Direct modifications to In-App Billing or StoreKit purchase verification.
  - Manifest or Info.plist configuration changes that alter app-wide security or permissions.
  - Core database schema modifications without automated migration scripts.
  - Deleted public symbols called by downstream modules (breaking API change).
* **HIGH**:
  - Modified UI entry points (Activities, Fragments, ViewControllers, SwiftUI Views).
  - Modified dependency injection root modules (Hilt, Swinject).
  - Changes with large transitive blast radius (> 5 downstream components).
* **MEDIUM**:
  - Internal business logic modifications with 1-4 downstream dependents.
  - Non-breaking signature alterations in internal helper classes.
* **LOW**:
  - Localized leaf functions with zero downstream dependents.
  - Pure cosmetic modifications or comment/documentation changes.

---

## Evidence Confidence (Certainty Dimension)

Confidence measures how provable the relationship is using static Tree-sitter AST analysis:

* **VERIFIED**:
  - Direct import and explicit type reference in the same file.
  - Explicit method invocation on an instantiated type matching AST signatures.
  - Manifest `<activity android:name="...">` matching declared class in source tree.
* **STRONG_INFERENCE**:
  - Matched identical API route literal in both client and backend annotations.
  - Navigation route string matching destination coordinator binding.
  - Module dependency declared in Gradle `dependencies { implementation(project(":core")) }`.
* **POSSIBLE**:
  - Name-based heuristic correlation without verified call-graph edge.
  - Indirect notification or broad event bus dispatch.
* **UNKNOWN**:
  - Unresolved dynamic invocation, reflection, or unparseable syntax node.

---

## Separation Principle

> **Crucial Rule**: Never downgrade severity because confidence is incomplete, and never upgrade confidence because severity is high.
>
> *Example*: If an In-App Billing callback is modified, its Severity is **CRITICAL**. If invoked via an abstract interface, its Confidence may be **STRONG_INFERENCE**. Both must be reported accurately.
