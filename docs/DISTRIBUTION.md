# Distribution

Phase 27 makes package-channel publication a maintained workflow instead of a
manual follow-up after GitHub Release upload. Phase 28 adds a launch check and
package-manager submission checklist before metadata goes to public indexes.
Phase 29 adds package submission and external install checks after channels are
generated.

## Release Asset Contract

Public distribution starts from the immutable GitHub Release assets produced by
the release matrix:

- `cool-<version>-linux-x86_64.tar.gz`
- `cool-<version>-macos-x86_64.tar.gz`
- `cool-<version>-macos-arm64.tar.gz`
- `cool-<version>-windows-x86_64.zip`
- `release.json`, `latest.json`, `SHA256SUMS`, trust metadata, validation
  reports, installer, and package-channel archive

Do not submit package-manager metadata that points at local files, workflow
artifacts, or mutable URLs.

## Generate Channels

After release assets are promoted or assembled:

```bash
bash scripts/package_channels.sh generate \
  --version 1.1.0 \
  --require-platform linux-x86_64 \
  --require-platform macos-x86_64 \
  --require-platform macos-arm64 \
  --require-platform windows-x86_64
```

## Audit Distribution Readiness

Run the Phase 27 readiness audit and Phase 28 launch check before package-index
submission:

```bash
bash scripts/release_launch_check.sh \
  --version 1.1.0 \
  --report dist/distribution/1.1.0/release-launch.json \
  --write-checklist dist/distribution/1.1.0/RELEASE_LAUNCH_CHECKLIST.md
bash scripts/distribution_readiness.sh \
  --version 1.1.0 \
  --require-platform linux-x86_64 \
  --require-platform macos-x86_64 \
  --require-platform macos-arm64 \
  --require-platform windows-x86_64 \
  --report dist/distribution/1.1.0/distribution-readiness.json \
  --write-checklist dist/distribution/1.1.0/DISTRIBUTION_CHECKLIST.md
```

The audit checks release archive names and hashes, package-channel asset URLs,
Homebrew formula references, Winget portable manifests, Debian/apt metadata,
and required-platform coverage.

## Audit Package Submission Metadata

After package channels are generated, run the Phase 29 package submission gate:

```bash
bash scripts/package_submission_check.sh \
  --version 1.1.0 \
  --require-channel homebrew \
  --require-channel winget \
  --require-channel debian \
  --report dist/validation/1.1.0/package-submission.json \
  --write-checklist dist/validation/1.1.0/PACKAGE_SUBMISSION_CHECKLIST.md
```

This validates the generated Homebrew formula, Winget portable manifests,
Debian/apt package/index metadata, official submission checklist references, and
`docs/PACKAGE_SUBMISSION_STATUS.json`.

## Hosted Verification

After uploading release assets, verify the hosted package-channel archive:

```bash
bash scripts/verify_hosted_release.sh \
  --version 1.1.0 \
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

## Package-Index Targets

- Homebrew: submit `dist/channels/<version>/homebrew/cool.rb` or use it as the
  source for a tap update.
- Winget: submit the manifests under
  `dist/channels/<version>/winget/Codenz.Cool/<version>/`.
- Debian/apt: publish the generated apt tree or use the generated `.deb` and
  `Packages` index as packaging input.

If a package index requires a different layout, add that layout to
`scripts/package_channels.py`, add validation to `scripts/validate_release.py`
or `scripts/distribution_readiness.py`, and document the new contract here.
See `docs/PACKAGE_MANAGER_SUBMISSIONS.md` for the public Homebrew, Winget, and
Debian/apt submission checklist. See `docs/ECOSYSTEM_ADOPTION.md` for the
post-submit external install loop.
