# Release Validation

Cool release validation is the final pre-publish audit for promoted release
assets, trust metadata, installer behavior, and package-channel files. It is
designed to run locally, in pull-request CI, in the release matrix aggregate job,
and immediately before GitHub Release publishing.

## Validate A Promoted Release

```bash
bash scripts/validate_release.sh \
  --version 1.0.0 \
  --platform macos-arm64 \
  --require-trust \
  --require-channels \
  --install-smoke
```

The validator checks:

- `release.json`, `latest.json`, and `SHA256SUMS`
- promoted tarball and zip hashes, sizes, payload roots, manifests, and payload checksums
- packaged docs, conformance cases, and maintainer scripts needed to audit a release artifact offline
- platform sidecars: `*.manifest.json`, `*.checksums.txt`, and `*.RC_NOTES.md`
- trust files when `--require-trust` is present: SBOM, provenance, `trust.json`, and `TRUST_SHA256SUMS`
- channel files when `--require-channels` is present: `channels.json`, `CHANNEL_SHA256SUMS`, Homebrew, Winget, Debian/apt metadata, and the channel tarball
- distribution readiness reports when workflows run `scripts/distribution_readiness.sh`
- optional installer execution with archive metadata verification

Use `--verify-key <public-key.pem>` to verify detached OpenSSL signatures when
the release was signed.

## Required Platforms

For a full matrix release, require all public platforms:

```bash
bash scripts/validate_release.sh \
  --version 1.0.0 \
  --platform multi \
  --require-trust \
  --require-channels \
  --require-platform linux-x86_64 \
  --require-platform macos-x86_64 \
  --require-platform macos-arm64 \
  --require-platform windows-x86_64
```

On the Linux aggregate release job, add an installer smoke test against the Linux
asset:

```bash
bash scripts/validate_release.sh \
  --version 1.0.0 \
  --platform multi \
  --require-trust \
  --require-channels \
  --install-smoke \
  --install-smoke-platform linux-x86_64
```

## Validation Reports

Validation can emit a machine-readable report:

```bash
bash scripts/validate_release.sh \
  --version 1.0.0 \
  --require-trust \
  --require-channels \
  --report dist/validation/1.0.0/release-validation.json
```

The report records the release platform, platforms discovered, archive count,
checksum counts, channel counts, and installer smoke target.

The Phase 26 conformance suite can emit a separate compatibility report:

```bash
bash scripts/conformance_suite.sh \
  --report dist/validation/1.0.0/conformance-validation.json
```

The Phase 27 distribution readiness audit can emit package-index evidence:

```bash
bash scripts/distribution_readiness.sh \
  --version 1.0.0 \
  --require-platform linux-x86_64 \
  --require-platform macos-x86_64 \
  --require-platform macos-arm64 \
  --require-platform windows-x86_64 \
  --report dist/validation/1.0.0/distribution-readiness.json \
  --write-checklist dist/validation/1.0.0/DISTRIBUTION_CHECKLIST.md
```

## Hosted Release Verification

After assets are uploaded to a public GitHub Release or mirror, verify the
hosted URLs rather than local `dist/` files:

```bash
bash scripts/verify_hosted_release.sh \
  --version 1.0.0 \
  --platform multi \
  --require-trust \
  --check-channel-archive \
  --require-platform linux-x86_64 \
  --require-platform macos-x86_64 \
  --require-platform macos-arm64 \
  --require-platform windows-x86_64 \
  --install-smoke \
  --install-smoke-platform linux-x86_64
```

The hosted verifier downloads `release.json`, `latest.json`, `SHA256SUMS`,
release assets, trust metadata, and the package-channel archive from the release
URL, then checks hashes, sizes, archive layout, payload checksums, trust records,
channel checksums, and optional installer behavior.

Use `--base-url <url>` for mirrors. The URL should be the release download base
that contains tag directories, for example:

```text
https://github.com/codenz92/cool-lang/releases/download
```

## Synthetic Matrix Smoke Test

When a real four-platform matrix is too expensive for every pull request, run a
synthetic matrix smoke test from one promoted host release:

```bash
bash scripts/smoke_matrix_release.sh --version 1.0.0
```

The smoke driver repacks the host payload into Linux, macOS Intel, macOS Arm, and
Windows x64-shaped artifacts, assembles them with `assemble_matrix_release.sh`,
generates trust metadata, generates package channels with all required-platform
checks, and runs `validate_release.sh` against the resulting multi-platform
release. This does not replace a real tagged matrix release, but it catches
metadata, channel, checksum, archive-layout, and packaging regressions before the
tag is cut.

## Release Checklist

1. `bash scripts/release_gate.sh`
2. `bash scripts/conformance_suite.sh --report dist/validation/<version>/conformance-validation.json`
3. `cool apps/release_audit.cool --strict`
4. `bash scripts/release_candidate.sh --require-clean`
5. `bash scripts/promote_release.sh --version <version>`
6. `bash scripts/package_channels.sh generate --version <version>`
7. `bash scripts/distribution_readiness.sh --version <version> --report dist/validation/<version>/distribution-readiness.json`
8. `bash scripts/validate_release.sh --version <version> --require-trust --require-channels --install-smoke`
9. For a real release, dispatch `Release Matrix` or push tag `v<version>` and confirm the aggregate validation report passes.
10. After the release is public, run `Hosted Release Verify` or `scripts/verify_hosted_release.sh` against the hosted assets.
