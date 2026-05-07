# Cool 1.1.0 Release Record

Release date: 2026-05-06

Release state: published, latest, public, hosted-verified.

## Release Scope

- Phase 26 compatibility and conformance workflow.
- Phase 27 distribution readiness, structured documentation, and Cool-written
  release audit dogfooding.
- Phase 28 public 1.1.0 launch preparation, package-manager submission
  checklist, launch identity validation, version alignment, and release evidence
  wiring.

## Published Artifact

- Git tag: `v1.1.0`
- Tag object: `444818a95512526cf669dbb1997f5007d3140fbc`
- Target commit: `d7d10eaee1b65cb9896313055bbd9704fd878e1c`
- Previous public release: `v1.0.0`
- GitHub Release: https://github.com/codenz92/cool-lang/releases/tag/v1.1.0
- Release state: public, latest, non-draft, non-prerelease.
- Promoted: `2026-05-06T22:27:53Z`
- Required public platforms: `linux-x86_64`, `macos-x86_64`, `macos-arm64`,
  `windows-x86_64`

## Release Execution Evidence

| Check | Result | Evidence |
| ----- | ------ | -------- |
| Branch release gate | Passed | https://github.com/codenz92/cool-lang/actions/runs/25463902124 |
| Branch release validation | Passed | https://github.com/codenz92/cool-lang/actions/runs/25463902118 |
| Branch conformance suite | Passed | https://github.com/codenz92/cool-lang/actions/runs/25463902100 |
| Tag release candidate workflow | Passed | https://github.com/codenz92/cool-lang/actions/runs/25463905281 |
| Tag release promotion workflow | Passed | https://github.com/codenz92/cool-lang/actions/runs/25463905272 |
| Publishing release matrix | Passed | https://github.com/codenz92/cool-lang/actions/runs/25463905288 |
| Distribution readiness | Passed | `dist/validation/1.1.0/distribution-readiness.json` |
| Package submission checklist | Passed | `dist/validation/1.1.0/DISTRIBUTION_CHECKLIST.md` |
| Hosted public release verification | Passed | `/tmp/cool-1.1.0-public-hosted-release-validation.json` |
| Public installer audit | Passed | `verify_hosted_release.sh --install-smoke --install-smoke-platform macos-arm64` |

## Package-Manager Follow-Up

Phase 29 records package-manager submission readiness separately from the
release upload. Phase 30 records publication status and install evidence as
those package-manager submissions move through review:

- Status file: `docs/PACKAGE_SUBMISSION_STATUS.json`
- Submission gate: `scripts/package_submission_check.sh --version 1.1.0`
- External install plan: `scripts/external_install_check.sh --version 1.1.0`
- Publication gate: `scripts/package_publication_check.sh --version 1.1.0`
- Submission packet gate: `scripts/package_submission_packet.sh --version 1.1.0`
- Current channel state: Homebrew, Winget, and Debian/apt are `ready` pending
  public package-index submission links.

## Hosted Verification

The public hosted verifier checked the release at
`https://github.com/codenz92/cool-lang/releases/download/v1.1.0`, including:

- 8 platform archives across `linux-x86_64`, `macos-x86_64`, `macos-arm64`,
  and `windows-x86_64`.
- 37 trust checksum entries and 31 hosted release checksum entries.
- Package-channel archive `cool-1.1.0-package-channels.tar.gz`.
- macOS Arm install smoke from the published `cool-1.1.0-macos-arm64.tar.gz`
  archive.

## Launch Corrections

Two Windows release-gate issues were found in tag-triggered matrix validation
before the final published release:

- `51c3736` resolves Windows release-gate binary path selection by using
  `cool.exe` on Windows shells.
- `d7d10ea` skips native conformance in the release gate when hosted native
  binary validation is disabled for the platform.

The final `v1.1.0` tag points at `d7d10ea`.

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

For future public publishing, use the `Release Matrix` workflow or push the
annotated tag after the final launch commit is on `master`:

```bash
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

Tag pushes publish a non-draft GitHub Release through the matrix workflow.
