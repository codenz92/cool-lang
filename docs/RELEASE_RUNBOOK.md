# Release Runbook

This runbook is the operator checklist for shipping a public Cool release. It
assumes the version in `Cargo.toml` is final and the release branch is clean.

## Roles And Inputs

- Release owner: one person owns the checklist and final publish decision.
- Version: semantic version without the leading `v`, for example `1.1.0`.
- Tag: `v<version>`.
- Signing key: optional OpenSSL private key exposed to CI as `COOL_RELEASE_SIGNING_KEY_B64`.
- Required public platforms: `linux-x86_64`, `macos-x86_64`, `macos-arm64`, `windows-x86_64`.

## Local Preflight

Run the release gate from a clean tree:

```bash
bash scripts/release_gate.sh
```

The release gate includes the conformance suite, Cool-written release audit,
Phase 28 launch-identity check, and Phase 30 publication ledger check. Phase 29
package submission and external install checks run after package channels are
generated. To capture separate
compatibility and launch reports for release evidence, run:

```bash
VERSION=1.1.0
bash scripts/conformance_suite.sh \
  --report "dist/validation/$VERSION/conformance-validation.json"
bash scripts/release_launch_check.sh \
  --version "$VERSION" \
  --require-unreleased-tag \
  --require-newer-than-latest-tag \
  --report "dist/validation/$VERSION/release-launch.json" \
  --write-checklist "dist/validation/$VERSION/RELEASE_LAUNCH_CHECKLIST.md"
```

Run the Cool-written release audit app:

```bash
./target/debug/cool apps/release_audit.cool --strict
```

Build and promote a local host candidate when you need a fast final sanity
check before using the full matrix:

```bash
bash scripts/release_candidate.sh --require-clean --version "$VERSION"
bash scripts/promote_release.sh --version "$VERSION"
bash scripts/package_channels.sh generate --version "$VERSION"
bash scripts/distribution_readiness.sh \
  --version "$VERSION" \
  --require-platform macos-arm64 \
  --report "dist/validation/$VERSION/distribution-readiness.json" \
  --write-checklist "dist/validation/$VERSION/DISTRIBUTION_CHECKLIST.md"
bash scripts/package_submission_check.sh \
  --version "$VERSION" \
  --report "dist/validation/$VERSION/package-submission.json" \
  --write-checklist "dist/validation/$VERSION/PACKAGE_SUBMISSION_CHECKLIST.md"
bash scripts/external_install_check.sh \
  --version "$VERSION" \
  --report "dist/validation/$VERSION/external-install.json" \
  --write-plan "dist/validation/$VERSION/EXTERNAL_INSTALL_PLAN.md"
bash scripts/package_publication_check.sh \
  --version "$VERSION" \
  --report "dist/validation/$VERSION/package-publication.json" \
  --write-evidence "dist/validation/$VERSION/PACKAGE_PUBLICATION_EVIDENCE.md"
bash scripts/validate_release.sh \
  --version "$VERSION" \
  --require-trust \
  --require-channels \
  --install-smoke
```

For a synthetic four-platform packaging check from the host artifact:

```bash
bash scripts/smoke_matrix_release.sh --version "$VERSION"
```

## Matrix Release

Use the `Release Matrix` workflow for public releases. It builds the four public
platforms, assembles one multi-platform release directory, generates trust
metadata, generates package-channel files, validates everything, and optionally
publishes the GitHub Release.

Manual dispatch inputs:

- `version`: release version without `v`.
- `publish`: set to `true` only when the matrix validation has passed.
- `draft`: keep `true` for the first upload unless the release is already approved.

Tag push flow:

```bash
git tag -a "v$VERSION" -m "Release v$VERSION"
git push origin "v$VERSION"
```

Tag pushes publish a non-draft release through the workflow. Use manual dispatch
with a draft when you want a final human review before public promotion.

## Published Release Verification

After the GitHub Release is public, run hosted verification against the uploaded
assets instead of local `dist/` files:

```bash
bash scripts/verify_hosted_release.sh \
  --version "$VERSION" \
  --platform multi \
  --require-trust \
  --check-channel-archive \
  --require-platform linux-x86_64 \
  --require-platform macos-x86_64 \
  --require-platform macos-arm64 \
  --require-platform windows-x86_64 \
  --install-smoke \
  --install-smoke-platform linux-x86_64 \
  --report "dist/hosted-validation/$VERSION/hosted-release-validation.json"
```

The `Hosted Release Verify` workflow runs the same check on `release.published`
events and can also be dispatched manually for mirrors or rechecks.

## Rollback

If hosted verification fails before announcement:

1. Convert the release back to draft, or delete the broken release if it cannot
   be repaired in place.
2. Do not move a public tag silently. If a tag was published with broken assets,
   create a patch release unless the release has not been consumed.
3. Fix the issue on `master`, rebuild the matrix, and rerun hosted verification.
4. Record the failed asset, failing verification command, and replacement release
   in a `Release hotfix` issue.

If a package-channel file is wrong but archives are correct, regenerate channels,
upload the replacement channel archive, and rerun hosted verification with
`--check-channel-archive`.

## Hotfix Release

For a code hotfix:

```bash
bash scripts/release_gate.sh
bash scripts/release_candidate.sh --require-clean --version 1.0.1
```

Then use the same matrix, trust, package-channel, and hosted verification steps
as a normal release. The hotfix issue should link the broken release, the fixed
release, and the verification report.

## Final Record

Before closing the release checklist, record:

- GitHub Release URL.
- `release-validation.json` workflow artifact.
- `release-launch.json` and `RELEASE_LAUNCH_CHECKLIST.md` artifacts.
- `conformance-validation.json` or `conformance-suite.json` workflow artifact.
- `distribution-readiness.json` and `DISTRIBUTION_CHECKLIST.md` artifacts.
- `package-submission.json` and `PACKAGE_SUBMISSION_CHECKLIST.md` artifacts.
- `external-install.json` and `EXTERNAL_INSTALL_PLAN.md` artifacts.
- `hosted-release-validation.json` workflow artifact.
- Package-channel archive name and hash.
- Homebrew, Winget, and Debian/apt submission links or explicit deferrals.
- Any manual deviations from this runbook.
