# Cool 1.1.0 Release Record

Release date: 2026-05-06

Release state: prepared for public release; hosted evidence is pending the
tag-triggered four-platform Release Matrix and hosted verification.

## Release Scope

- Phase 26 compatibility and conformance workflow.
- Phase 27 distribution readiness, structured documentation, and Cool-written
  release audit dogfooding.
- Phase 28 public 1.1.0 launch preparation, package-manager submission
  checklist, launch identity validation, version alignment, and release evidence
  wiring.

## Prepared Artifact

- Git tag: `v1.1.0`
- Previous public release: `v1.0.0`
- Expected GitHub Release: https://github.com/codenz92/cool-lang/releases/tag/v1.1.0
- Release state: prepared, not yet marked as hosted-verified in this record
- Required public platforms: `linux-x86_64`, `macos-x86_64`, `macos-arm64`,
  `windows-x86_64`

## Launch Evidence To Record

| Check | Result | Evidence |
| ----- | ------ | -------- |
| Release launch check | Pending final tag workflow | `dist/validation/1.1.0/release-launch.json` |
| Branch release gate | Pending final launch commit | GitHub Actions run URL |
| Branch release validation | Pending final launch commit | GitHub Actions run URL |
| Publishing release matrix | Pending `v1.1.0` tag | GitHub Actions run URL |
| Distribution readiness | Pending matrix assembly | `dist/validation/1.1.0/distribution-readiness.json` |
| Package submission checklist | Pending matrix assembly | `dist/validation/1.1.0/DISTRIBUTION_CHECKLIST.md` |
| Hosted public release verification | Pending public upload | `dist/hosted-validation/1.1.0/hosted-release-validation.json` |
| Public installer audit | Pending public upload | `install.sh --version 1.1.0 --verify-metadata` |

## Launch Commands

```bash
VERSION=1.1.0
bash scripts/release_gate.sh
bash scripts/release_launch_check.sh \
  --version "$VERSION" \
  --require-unreleased-tag \
  --require-newer-than-latest-tag \
  --report "dist/validation/$VERSION/release-launch.json" \
  --write-checklist "dist/validation/$VERSION/RELEASE_LAUNCH_CHECKLIST.md"
```

For public publishing, use the `Release Matrix` workflow or push the annotated
tag after the final launch commit is on `master`:

```bash
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

Tag pushes publish a non-draft GitHub Release through the matrix workflow.
Record the final workflow URLs, hosted verification report, package-channel
archive hash, and package-manager submission links here after the public release
has passed hosted verification.
