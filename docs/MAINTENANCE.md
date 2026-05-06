# Maintenance

This page defines the post-`1.1.0` maintenance loop for Cool `1.1.x` releases.

## Patch Release Policy

Use a `1.1.x` hotfix when a change is narrowly scoped to:

- Broken release, installer, package-manager, or hosted artifact metadata.
- Regression in documented stable 1.x behavior.
- Supported-platform build or runtime failure.
- Security, trust metadata, or checksum correction.

Do not use a patch release for new language syntax, new stdlib families, or
large behavior changes. Those belong in the next minor release.

## Hotfix Gate

Every hotfix must pass:

```bash
bash scripts/release_gate.sh
bash scripts/release_launch_check.sh --version <version>
bash scripts/package_submission_check.sh --version <version>
bash scripts/external_install_check.sh --version <version>
```

When public assets exist, rerun hosted verification with `--run-hosted` through
`scripts/external_install_check.sh` or directly through
`scripts/verify_hosted_release.sh`.

## Package-channel Rollback

The package-channel rollback path is metadata-only unless the release archive itself is
bad.

1. If a package-manager submission is wrong but GitHub Release assets are good,
   update the package-manager metadata and keep the immutable release assets.
2. If an uploaded release asset is wrong, publish a new patch version. Do not
   mutate an existing public asset after package managers have consumed its URL
   and SHA-256.
3. Mark the affected channel as `blocked` in
   `docs/PACKAGE_SUBMISSION_STATUS.json` with a short note.
4. Open a hotfix issue and link package-manager pull requests or mirror changes.

## Compatibility Exceptions

Any intentional compatibility exception must name:

- Affected version and runtime profile.
- User-visible behavior.
- Migration path.
- Conformance test or release validation evidence.

Record the exception in the changelog and release record before publishing.
