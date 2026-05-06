# Package Publication

Phase 30 makes package publication a maintained workflow by moving
package-manager work from "metadata is ready" to "publication
state and install evidence are tracked". The maintained source of truth is
`docs/PACKAGE_SUBMISSION_STATUS.json`; every public package-manager action must
leave enough evidence for another maintainer to reproduce or audit the result.

## Phase 30 Gate

Run the publication gate after the Phase 29 package submission and external
install checks:

```bash
VERSION=1.1.0
bash scripts/package_publication_check.sh \
  --version "$VERSION" \
  --report "dist/validation/$VERSION/package-publication.json" \
  --write-evidence "dist/validation/$VERSION/PACKAGE_PUBLICATION_EVIDENCE.md"
```

By default the gate validates that the ledger is current, every channel has a
valid status, official submission references are recorded, and readiness
commands are present. It does not require public package-manager publication
while channels are still `ready`.

When a channel is submitted, require that state explicitly:

```bash
bash scripts/package_publication_check.sh \
  --version "$VERSION" \
  --require-status homebrew=submitted \
  --require-status winget=submitted \
  --report "dist/validation/$VERSION/package-publication-submitted.json"
```

When a channel is public, require publication and external install evidence:

```bash
bash scripts/package_publication_check.sh \
  --version "$VERSION" \
  --require-published homebrew \
  --require-external-evidence \
  --report "dist/validation/$VERSION/package-publication-homebrew.json"
```

Use `--require-all-published --require-external-evidence` only after every
package manager exposes the release to users.

## Status Ledger

Each channel in `docs/PACKAGE_SUBMISSION_STATUS.json` uses one of these states:

- `ready` — generated metadata passed local submission checks but has not been
  submitted externally.
- `submitted` — a package-index pull request, issue, or review is open and
  `submission_url` plus `submitted_at` are recorded.
- `published` — a user-visible package page or mirror exists, `published_url`,
  `public_install_command`, `published_at`, `verified_at`, and
  `external_install_report` are recorded, and the install command has been
  checked.
- `blocked` — publication cannot proceed; record a short blocker in `blockers`
  or `notes`.
- `deferred` — publication is intentionally postponed; record the reason in
  `notes`.

Do not mark a channel as `published` from a successful local manifest
validation alone. `published` means a user can install Cool through that
external package-manager path.

## Channel References

Use these official references when updating package metadata or reviewing
external feedback:

- Homebrew Formula Cookbook: https://docs.brew.sh/Formula-Cookbook
- Homebrew Acceptable Formulae: https://docs.brew.sh/Acceptable-Formulae
- Winget manifest docs:
  https://learn.microsoft.com/en-us/windows/package-manager/package/manifest
- Winget repository submission docs:
  https://learn.microsoft.com/en-us/windows/package-manager/package/repository
- Debian Policy Manual: https://www.debian.org/doc/debian-policy/
- Debian control fields:
  https://www.debian.org/doc/debian-policy/ch-controlfields.html

## Publication Loop

1. Publish or verify the GitHub Release assets and package-channel archive.
2. Run `package_submission_check.sh` and `external_install_check.sh`.
3. Submit Homebrew, Winget, and Debian/apt metadata using immutable release
   URLs and SHA-256 values only.
4. Update `docs/PACKAGE_SUBMISSION_STATUS.json` to `submitted` with the
   external URL and date.
5. When each package manager exposes the release, update the ledger to
   `published`, record the public install command, and run
   `external_install_check.sh` for the install path.
6. Run `package_publication_check.sh` with the matching required status and
   keep its JSON/Markdown outputs with release evidence.

## Evidence Rules

The publication report is useful only when it can answer three questions:

- Where was this package submitted or published?
- Which exact user command installs this version?
- Which validation report proves the command worked after publication?

For `1.1.x` hotfixes, keep the same package-manager entry and update only the
versioned source, URL, SHA-256, and evidence fields. If a package manager
requires a metadata-only correction, keep the immutable GitHub Release asset
and update only the package-manager metadata.
