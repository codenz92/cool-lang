# Dogfooding

Cool should keep shipping real tools written in Cool. Dogfooding is how the
project finds rough edges in imports, stdlib APIs, error reporting, native
builds, packaging, and docs before users do.

## Maintained Dogfood Apps

- `apps/shell.cool` — interactive shell and app launcher.
- `apps/pulse.cool` / `apps/control.cool` — health-check automation and TUI
  dashboard.
- `examples/coolboard/` — small service-style project.
- `apps/release_audit.cool` - Phase 31 repo-health audit for distribution,
  conformance, launch checks, ecosystem adoption docs, release workflows,
  package submission checks, package publication checks, package submission
  packets, and package-channel readiness.

## Release Audit App

Run from the repository root:

```bash
./target/debug/cool apps/release_audit.cool --strict
./target/debug/cool apps/release_audit.cool --strict --json
```

The app is intentionally written in Cool and uses stable file, TOML, JSON, path,
and stdlib behavior. It fails when required Phase 26/27/28/29/30/31 docs,
conformance assets, launch checks, package submission/publication checks,
submission packet scripts, release scripts, or workflows are missing.

## Dogfood Rules

- A dogfood app should exercise a real maintainer or user workflow.
- It should run without external credentials.
- It should have at least one integration test.
- It should avoid depending on the network unless that is the explicit feature
  being tested.
- If the app exposes a release-critical workflow, wire it into the release gate.

## Adding A New App

Add the app under `apps/`, document the command in this file, and add a focused
integration test in `tests/integration.rs`. If the app becomes release-critical,
add it to `scripts/release_gate.sh`.
