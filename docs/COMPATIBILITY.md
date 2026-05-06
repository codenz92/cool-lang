# Compatibility Policy

Cool 1.0 commits to compatibility for the stable language surface, runtime
semantics, release archives, and public platform contract. Phase 26 turns that
commitment into an executable policy: release-critical changes must pass the
conformance suite in addition to the release gate.

## Stable Surface

The stable 1.x surface includes:

- Core syntax and semantics documented in `README.md` and exercised by
  `conformance/runtime/`.
- Interpreter and bytecode VM execution for stable hosted language features.
- Hosted LLVM native execution for the overlapping stable language and stdlib
  surface.
- `cool check`, `cool build`, `cool test`, `cool bench`, `cool fmt`,
  `cool pkg`, `cool new`, `cool install`, `cool publish`, `cool bundle`, and
  release tooling documented in the README and release docs.
- Public release archive layout and install behavior validated by
  `scripts/validate_release.sh` and `scripts/verify_hosted_release.sh`.
- Public platforms listed in `docs/SUPPORT_MATRIX.md`.

Freestanding, no-libc, inline assembly, raw memory, port I/O, and linker-script
flows are stable where they are covered by tests and release-gate checks, but
their host and target availability is narrower than the hosted runtime surface.

## Runtime Parity

Backend parity is a compatibility feature. For a stable hosted feature, the
tree-walk interpreter, bytecode VM, and hosted native backend must produce the
same observable output and error behavior unless documentation explicitly marks
a runtime as unsupported.

The conformance suite is the smallest required parity contract. The broader
Rust integration and LLVM backend suites remain the deeper regression net.

## Semantic Versioning

- Patch releases, such as `1.0.1`, fix bugs, diagnostics, packaging, docs, and
  compatibility gaps without intentionally breaking valid 1.0 programs.
- Minor releases, such as `1.1.0`, may add syntax, commands, modules, flags, or
  platforms while preserving the stable 1.x surface.
- Major releases may remove deprecated behavior or change core semantics.

If a severe security or correctness issue requires breaking behavior in a patch
or minor release, document the exception in the changelog and release notes,
include a migration note, and add a conformance or regression test for the new
contract.

## Deprecation Rules

Deprecations must be visible before removal:

- Add documentation that names the replacement.
- Add a warning when the affected code path is easy to detect.
- Keep the behavior through at least one minor release unless the behavior is
  unsafe or impossible to support.
- Add release notes when the warning is introduced and when removal happens.

## Release Requirement

Before a public release:

```bash
bash scripts/release_gate.sh
bash scripts/conformance_suite.sh
```

For fast local work that does not touch native lowering, use:

```bash
bash scripts/conformance_suite.sh --skip-native
```

`release_gate.sh` runs the conformance suite by default. Skipping native
conformance is acceptable only for local diagnosis or hosts without LLVM native
support; it is not acceptable for a public release.
