---
name: Release checklist
about: Track a Cool public release from candidate build through hosted verification.
title: "Release vX.Y.Z"
labels: release
assignees: ""
---

## Release

- Version:
- Tag:
- Release owner:
- Target date:

## Pre-Release Gate

- [ ] `bash scripts/release_gate.sh`
- [ ] `bash scripts/release_launch_check.sh --version <version> --require-unreleased-tag --report dist/validation/<version>/release-launch.json --write-checklist dist/validation/<version>/RELEASE_LAUNCH_CHECKLIST.md`
- [ ] `bash scripts/conformance_suite.sh --report dist/validation/<version>/conformance-validation.json`
- [ ] `bash scripts/release_candidate.sh --require-clean --version <version>`
- [ ] `bash scripts/promote_release.sh --version <version>`
- [ ] `bash scripts/package_channels.sh generate --version <version>`
- [ ] `bash scripts/distribution_readiness.sh --version <version> --report dist/validation/<version>/distribution-readiness.json --write-checklist dist/validation/<version>/DISTRIBUTION_CHECKLIST.md`
- [ ] `bash scripts/validate_release.sh --version <version> --require-trust --require-channels --install-smoke`

## Matrix And Publishing

- [ ] Dispatch `Release Matrix` for the version or push `v<version>`.
- [ ] Confirm Linux, macOS Intel, macOS Arm, and Windows artifacts are present.
- [ ] Confirm `release-validation.json` passed and was uploaded.
- [ ] Confirm package-channel archive is uploaded.
- [ ] Confirm `distribution-readiness.json` passed and package submission checklist was uploaded.
- [ ] Publish or promote the GitHub Release from draft.

## Post-Release Verification

- [ ] `Hosted Release Verify` workflow passed.
- [ ] `bash scripts/verify_hosted_release.sh --version <version> --platform multi --require-trust --check-channel-archive --install-smoke --install-smoke-platform linux-x86_64`
- [ ] Install docs and support matrix still match the uploaded assets.
- [ ] Release notes include hashes, trust metadata, and package-channel instructions.
- [ ] `docs/RELEASE_<version>.md` includes final workflow links, hosted verification evidence, installer audit, and package-manager submission status.

## Rollback / Follow-Up

- [ ] If verification fails, mark the release as draft or delete the broken assets.
- [ ] Open a hotfix issue if the tag must be superseded.
- [ ] Record final links to the release, validation report, and hosted verification report.
