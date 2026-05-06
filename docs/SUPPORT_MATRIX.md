# Support Matrix

Cool publishes release archives and package-channel metadata for the platforms
below. A platform is public only when it is produced by the release matrix,
listed in `release.json`, present in `channels.json`, and covered by hosted
release verification.

## Public Platforms

| Platform | Runner | Archive formats | Installer default | Status |
| --- | --- | --- | --- | --- |
| `linux-x86_64` | `ubuntu-22.04` | `.tar.gz`, `.zip` | `.tar.gz` | Supported |
| `macos-x86_64` | `macos-15-intel` | `.tar.gz`, `.zip` | `.tar.gz` | Supported |
| `macos-arm64` | `macos-14` | `.tar.gz`, `.zip` | `.tar.gz` | Supported |
| `windows-x86_64` | `windows-2022` | `.tar.gz`, `.zip` | `.zip` | Supported |

## Package Channels

| Channel | Source asset | Generated when | Verification |
| --- | --- | --- | --- |
| Homebrew formula | macOS/Linux `.tar.gz` assets | At least one macOS or Linux tarball exists | `validate_release.sh --require-channels` |
| Winget manifests | Windows `.zip` asset | `windows-x86_64` zip exists | `validate_release.sh --require-channels` |
| Debian/apt metadata | Linux x86_64 `.tar.gz` asset | `linux-x86_64` tarball exists | `validate_release.sh --require-channels` |
| Channel archive | Full `dist/channels/<version>/` tree | Every release channel generation | `verify_hosted_release.sh --check-channel-archive` |
| Package submission evidence | Generated channel tree | After hosted verification | `package_submission_check.sh` and `external_install_check.sh` |
| Package publication evidence | Status ledger and external install reports | After submission or publication changes | `package_publication_check.sh` |

## Verification Coverage

Release validation checks local promoted artifacts before upload. Hosted release
verification downloads the final assets from GitHub Releases or a mirror and
checks the same public contract from the user's point of view:

- Phase 26 conformance cases for stable runtime parity and static diagnostics.
- Phase 27 distribution readiness for package-manager submission metadata.
- Phase 28 launch checks for version, tag, changelog, release evidence, and
  package-manager submission gates.
- Phase 29 package submission and external install checks for package-manager
  readiness and post-submit evidence.
- Phase 30 package publication checks for submitted/published status, install
  commands, and external evidence links.
- `release.json`, `latest.json`, and `SHA256SUMS` hashes and sizes.
- Platform tarball and zip payload roots, manifests, payload checksums, docs, and release scripts.
- SBOM, provenance, `trust.json`, and `TRUST_SHA256SUMS` when trust is required.
- Package-channel archive layout and internal channel checksums.
- Optional install smoke test using the hosted URL for HTTP(S) releases.

## Support Policy

- A supported platform must keep passing the release matrix before it can be
  listed as supported.
- A supported hosted runtime mode must keep passing the conformance suite for
  the stable surface it implements.
- If a platform cannot be built or verified, remove it from the required-platform
  list before publishing and document the gap in release notes.
- Do not publish a release with mismatched archive names, hashes, package-channel
  entries, or trust metadata.
- Do not submit package-index updates until distribution readiness and hosted
  verification pass.
- Do not mark package-manager channels as published until
  `package_publication_check.sh` can verify the publication evidence.
- Prefer a patch release over replacing assets after a public release has been
  announced or downloaded.
