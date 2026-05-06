# Post-1.0 Adoption

Phase 26 moves Cool from "released" to "adoptable". The priority is not a new
language feature tranche; it is making installation, documentation,
compatibility, and performance evidence repeatable.

## Maintainer Checklist

For each post-1.0 release:

1. Keep the changelog focused on user-visible changes, compatibility fixes, and
   migration notes.
2. Run the release gate and conformance suite.
3. Publish the matrix release only after validation and hosted verification pass.
4. Regenerate package channels and verify the hosted channel archive.
5. Run distribution readiness and keep its JSON report/checklist with release evidence.
6. Run `apps/release_audit.cool --strict` before release.
7. Record any supported-platform or compatibility-policy exception in release
   notes.
8. Capture a performance baseline when native backend or runtime changes may
   affect benchmark behavior.

## Package Channels

Cool already generates channel artifacts for Homebrew, Winget, and Debian/apt.
Before proposing those artifacts to public package indexes, validate the hosted
release URL and channel archive:

```bash
bash scripts/verify_hosted_release.sh \
  --version 1.0.0 \
  --platform multi \
  --require-trust \
  --check-channel-archive \
  --require-platform linux-x86_64 \
  --require-platform macos-x86_64 \
  --require-platform macos-arm64 \
  --require-platform windows-x86_64
```

Package-index submissions should point at immutable GitHub Release assets, not
local `dist/` files. If an index requires a different archive shape, add that
shape to `scripts/package_channels.py` and validate it in
`scripts/validate_release.py` before publishing.

Phase 27 adds a package-index readiness audit:

```bash
bash scripts/distribution_readiness.sh \
  --version 1.0.0 \
  --require-platform linux-x86_64 \
  --require-platform macos-x86_64 \
  --require-platform macos-arm64 \
  --require-platform windows-x86_64 \
  --report dist/distribution/1.0.0/distribution-readiness.json \
  --write-checklist dist/distribution/1.0.0/DISTRIBUTION_CHECKLIST.md
```

## Documentation

The top-level README remains the broad feature tour. New long-form docs should
live under `docs/` and be linked from `docs/README.md`.

Prefer focused pages:

- Install and package manager workflows.
- Language reference and compatibility notes.
- Native compiler, FFI, and systems interop.
- Standard library module families.
- Release, validation, trust, and support operations.

The current structured entry points are `docs/LANGUAGE_REFERENCE.md`,
`docs/NATIVE_COMPILER.md`, `docs/STDLIB_OVERVIEW.md`, `docs/DISTRIBUTION.md`,
and `docs/DOGFOODING.md`.

## Performance Baselines

Use the benchmark baseline wrapper when native backend, runtime, allocator, or
stdlib changes could affect performance:

```bash
bash scripts/performance_baseline.sh --runs 5 --warmups 1
```

The wrapper records the raw `bench_compare` output and a JSON metadata report
under `dist/performance/<version>/` by default. For quick local smoke testing:

```bash
bash scripts/performance_baseline.sh --filter integer_loop --runs 1 --warmups 0 --output-dir /tmp/cool-perf
```

Do not treat one host result as a global performance claim. Use it as a
regression signal tied to the commit, host, compiler, and workload set in the
JSON report.
