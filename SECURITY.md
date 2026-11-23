# ChangeBlast Security Policy

ChangeBlast is built with a zero-trust, read-only security model. As a developer intelligence tool operating inside source code repositories, ChangeBlast enforces strict architectural boundaries to protect developer environments, intellectual property, and system integrity.

---

## Supported Versions

Only the latest active minor release receives security updates.

| Version | Supported |
| :--- | :--- |
| `0.1.x` | Yes |
| `< 0.1.0` | No |

---

## Security Model & Invariants

ChangeBlast operates under verified architectural security guarantees:

1. **Strictly Read-Only Execution**: ChangeBlast never writes to, modifies, or deletes files in the analyzed repository. It does not alter Git working trees, staging areas, or commit history. Cryptographic SHA-256 tree hashing verifies zero mutation.
2. **Zero External Network Activity**: The Python analysis engine creates zero network sockets, makes zero HTTP/RPC requests, and sends no telemetry. Code never leaves your local workstation.
3. **No Arbitrary Build Script Execution**: ChangeBlast does not invoke Gradle, Xcodebuild, CocoaPods, or any repository build scripts. It performs pure static syntax parsing using Tree-sitter.
4. **Path Traversal & Symlink Sandboxing**: All file resolution enforces strict canonical boundaries within the repository root. Null-byte injection (`\0`) and escaping symlinks are rejected with `SecurityBoundaryViolationError`.
5. **Safe Subprocess Execution**: Subprocesses are invoked with explicit argument vectors (`shell=False`). No user input is evaluated by a shell interpreter.

---

## Reporting a Vulnerability

If you discover a security vulnerability in ChangeBlast, please report it responsibly:

* **Primary Route**: Open a private advisory report through GitHub's [Private Vulnerability Reporting](https://github.com/changeblast/changeblast/security/advisories/new) on the repository.
* **Alternative Route**: Email the core engineering team at `engineering@changeblast.org` with the subject line `[SECURITY] ChangeBlast Vulnerability Report`.

Please include:
* Description of the potential vulnerability and affected component.
* Minimal reproduction steps or proof-of-concept repository.
* Potential security impact (e.g., path traversal, memory exhaustion).

### Response Process
* **Acknowledgment**: Within 48 hours.
* **Assessment & Fix**: Security patches will be prepared in private branches and published as a patched release.
* **Public Disclosure**: Coordinated disclosure after a fix is available.
