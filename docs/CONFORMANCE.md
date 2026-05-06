# Conformance Suite

The conformance suite is the Phase 26 compatibility contract for Cool 1.x. It
does not replace the full Rust test suite. It gives maintainers and downstream
packagers a compact, stable set of programs that must keep behaving the same
across supported runtimes.

## Run

```bash
bash scripts/conformance_suite.sh
```

Useful options:

- `--skip-native` runs only the interpreter and bytecode VM runtime modes.
- `--mode interpreter|vm|native` can be repeated to select exact modes.
- `--case <name>` can be repeated to run selected runtime or check cases.
- `--runtime-only` skips static-check cases.
- `--checks-only` skips runtime cases.
- `--report <path>` writes a JSON report for CI or release evidence.
- `--list` prints the manifest case names.

The runner uses `$COOL_BIN` when set. Otherwise it uses `target/debug/cool` and
builds it if needed.

## Manifest

`conformance/manifest.json` has two case classes:

- `runtime_cases` run `.cool` programs through selected runtime modes and
  compare exact stdout against `expected_stdout`.
- `check_cases` run `cool check`, optionally with `--strict`, and assert the
  expected pass/fail status plus required diagnostic text.

Runtime cases are intentionally deterministic and avoid network, wall-clock,
terminal, or filesystem state. Native cases are copied into a temporary
directory before compilation so the suite does not leave binaries in the source
tree.

## Current Coverage

- `core-language` covers closures, lambda capture behavior, inheritance,
  comprehensions, and `try` / `except` / `finally`.
- `typed-language` covers traits, generic structs, generic functions, enums,
  and `match`.
- `stdlib-data` covers stable data-oriented stdlib helpers such as `base64`,
  `bytes`, `json`, `path`, `option`, and `result`.
- `strict-typed-api` verifies strict static checking accepts a fully annotated
  public API.
- `non-exhaustive-match` verifies static checking rejects non-exhaustive enum
  matches.

## Adding Cases

Add a case when a behavior becomes part of the compatibility promise or when a
regression escapes the larger test suite. Keep cases small, deterministic, and
focused on user-observable behavior. Prefer one new conformance case over a
large scenario that is hard to diagnose.

For runtime cases, include exact stdout in the manifest. For diagnostic cases,
assert stable diagnostic identifiers or high-signal phrases rather than whole
multi-line error messages.
