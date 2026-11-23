# ChangeBlast: Security Policy & Threat Model

ChangeBlast is designed from the ground up as a **zero-trust, read-only static analysis system**. Because developer tools run in environments with privileged access to source code and credentials, ChangeBlast enforces strict architectural security boundaries.

---

## 1. Threat Model (STRIDE Methodology)

We apply Microsoft's STRIDE threat model specifically to local AST analysis, Git interactions, and AI tool integration:

| Threat Category | Potential Attack Vector | Architectural Mitigation in ChangeBlast |
| :--- | :--- | :--- |
| **Spoofing** | Malicious Git ref injected to analyze arbitrary branches or malicious commits | The CLI validates all Git ref arguments against a strict alphanumeric regex (`^[a-zA-Z0-9_\-\./~^]+$`). Ref values are never passed to an OS shell. |
| **Tampering** | Tool inadvertently or maliciously modifying user source code, build scripts, or git history | **Read-Only Invariant**: The engine contains zero file-write, file-delete, or file-creation logic outside of writing output to standard streams or user-specified output paths. It never runs git commands that modify state (`commit`, `checkout`, `reset`, `push`). |
| **Repudiation** | Ambiguity in which symbols or files were analyzed during an audit | Every `AnalysisReport` embeds a cryptographic hash of the commit/tree analyzed, precise timestamps, and full file/line coordinate trails. |
| **Information Disclosure** | Source code, intellectual property, or embedded secrets leaked to external servers | **Zero External Network Calls**: The Python analysis engine creates zero network sockets, makes zero HTTP/gRPC calls, and contains no telemetry or remote AI API calls. Code stays 100% on the developer's machine. |
| **Denial of Service** | Pathological ASTs, recursive macros, cyclic inheritance, or giant diffs exhausting CPU/memory | 1. Tree-sitter runs in native C with bounded memory.<br>2. Graph traversal enforces a hard maximum recursion depth (`max_depth = 10` default).<br>3. Visited-node sets prevent infinite cycles in mutually recursive symbols. |
| **Elevation of Privilege** | Malicious repo containing crafted filenames, `.git` hooks, or symlink escapes triggering arbitrary code execution | 1. No `shell=True` in subprocess calls.<br>2. No execution of project build tools (`gradle`, `gradlew`, `xcodebuild`, `pod`).<br>3. Path resolution validates that all target paths resolve strictly within the project repository root. |

---

## 2. Core Security Invariants

### 2.1 Strictly Read-Only Execution
- ChangeBlast never executes user code, tests, or build scripts.
- ChangeBlast never writes to, modifies, or deletes any file in the analyzed repository.
- Subprocess invocations are limited strictly to read-only Git query commands:
  - `git diff --unified=0 ...`
  - `git status --porcelain`
  - `git rev-parse ...`
  - `git show ...`

### 2.2 Subprocess Sandboxing & Injection Prevention
- Shell injection is eliminated by using array-based argument vectors exclusively:
  ```python
  # ALLOWED:
  subprocess.run(
      ["git", "diff", "--unified=0", base_ref, target_ref], check=True, capture_output=True
  )

  # STRICTLY FORBIDDEN:
  subprocess.run(f"git diff {base_ref} {target_ref}", shell=True)  # NEVER PERMITTED
  ```
- All user-supplied ref arguments undergo strict validation before passing to Git.

### 2.3 Filesystem Boundary & Path Traversal Protections
- Symlinks are resolved using `os.path.realpath`.
- ChangeBlast enforces that every resolved file path sits strictly below the Git repository root:
  ```python
  def validate_path_within_root(target_path: Path, repo_root: Path) -> Path:
      resolved_target = target_path.resolve()
      resolved_root = repo_root.resolve()
      if not resolved_target.is_relative_to(resolved_root):
          raise SecurityException(f"Path traversal detected: {target_path} escapes repository root.")
      return resolved_target
  ```

### 2.4 Zero External AI Dependency
- The Python analysis engine operates completely offline.
- No OpenAI, Anthropic, Gemini, or third-party API keys are required or supported within the engine.
- AI reasoning is delegated solely to the Claude Code client environment, which interacts with ChangeBlast strictly via standard CLI input/output.

---

## 3. Supply Chain Security

1. **Deterministic Pinning**: All production dependencies and transitive dependencies are pinned in `uv.lock`.
2. **Automated Vulnerability Auditing**: CI runs `pip-audit` on every pull request to identify known CVEs in dependencies.
3. **Restricted Script Execution**: Pre-commit hooks and package installations forbid execution of untrusted remote scripts.

---

## 4. Vulnerability Disclosure Policy

If you discover a security vulnerability in ChangeBlast, please report it privately:
- **Email**: `security@changeblast.org` (or create a private GitHub Security Advisory)
- Please include:
  - Description of the vulnerability.
  - Minimal reproducible example or proof-of-concept repository.
  - Potential impact assessment.
- We will acknowledge receipt within 48 hours and provide a fix timeline. Please do not open public issues for undisclosed security vulnerabilities.
