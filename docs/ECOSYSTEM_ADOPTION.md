# Ecosystem Adoption

Phase 29 turns a published Cool release into an externally installable product.
Phase 30 adds a publication ledger and evidence gate so package-manager
submission, publication, adoption, and install proof stay under the same
validation discipline as release artifacts.

## Phase 29 Gate

Run the package submission and external install checks after package channels
are generated:

```bash
VERSION=1.1.0
bash scripts/package_submission_check.sh \
  --version "$VERSION" \
  --require-channel homebrew \
  --require-channel winget \
  --require-channel debian \
  --report "dist/validation/$VERSION/package-submission.json" \
  --write-checklist "dist/validation/$VERSION/PACKAGE_SUBMISSION_CHECKLIST.md"

bash scripts/external_install_check.sh \
  --version "$VERSION" \
  --require-platform linux-x86_64 \
  --require-platform macos-x86_64 \
  --require-platform macos-arm64 \
  --require-platform windows-x86_64 \
  --report "dist/validation/$VERSION/external-install.json" \
  --write-plan "dist/validation/$VERSION/EXTERNAL_INSTALL_PLAN.md"
```

Use `--run-hosted` on `external_install_check.sh` when public release assets or
a local `file://` mirror are available. That mode delegates to
`scripts/verify_hosted_release.sh` and can run an install smoke test.

Phase 30 adds a package publication evidence gate:

```bash
bash scripts/package_publication_check.sh \
  --version "$VERSION" \
  --report "dist/validation/$VERSION/package-publication.json" \
  --write-evidence "dist/validation/$VERSION/PACKAGE_PUBLICATION_EVIDENCE.md"
```

## Package-Manager Loop

The maintained loop for each public release is:

1. Publish the GitHub Release from the four-platform matrix.
2. Verify hosted assets, trust metadata, package-channel archive, and direct
   installer smoke.
3. Run distribution readiness and package submission checks against the
   generated channel tree.
4. Submit Homebrew, Winget, and Debian/apt metadata using immutable release
   URLs only.
5. Update `docs/PACKAGE_SUBMISSION_STATUS.json` with submission URLs,
   publication URLs, install commands, dates, and external install reports.
6. Run `package_publication_check.sh` for the current channel state.
7. Run external install checks once each package manager exposes the release.
8. Record final package-manager evidence in the versioned release record.

## Adoption Evidence

Each release should keep a short user path fresh:

- Install Cool from the public release or package manager.
- Run `cool help` and `cool examples/hello.cool`.
- Create a project from the first-30-minutes example.
- Run the project through interpreter, VM, static check, and native build paths.
- Package or document the result so a new user sees the native-first workflow.

`docs/FIRST_30_MINUTES.md` is the canonical walkthrough. The companion source
lives in `examples/first_30_minutes/`.

## Evidence Files

- `dist/validation/<version>/package-submission.json`
- `dist/validation/<version>/PACKAGE_SUBMISSION_CHECKLIST.md`
- `dist/validation/<version>/external-install.json`
- `dist/validation/<version>/EXTERNAL_INSTALL_PLAN.md`
- `dist/validation/<version>/package-publication.json`
- `dist/validation/<version>/PACKAGE_PUBLICATION_EVIDENCE.md`
- `docs/PACKAGE_SUBMISSION_STATUS.json`

Do not mark a channel as `published` until a user-visible install command has
been verified from the external package manager or mirror.
