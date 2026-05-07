# Package Manager Submissions

This checklist starts after the public GitHub Release assets exist. Do not
submit package-manager metadata from local `dist/` output or workflow artifacts.

Phase 29 adds two maintained gates on top of the Phase 27/28 release checks:

```bash
bash scripts/package_submission_check.sh --version 1.1.0
bash scripts/external_install_check.sh --version 1.1.0
```

Phase 30 adds the publication ledger gate:

```bash
bash scripts/package_publication_check.sh --version 1.1.0
```

Phase 31 adds submission packet generation and review tracking:

```bash
bash scripts/package_submission_packet.sh --version 1.1.0
```

Track channel state in `docs/PACKAGE_SUBMISSION_STATUS.json` and record final
links, install commands, dates, and evidence reports in the versioned release
record.

## Pre-Submission Gate

Run the launch, validation, distribution, and hosted checks for the release:

```bash
VERSION=1.1.0
bash scripts/release_launch_check.sh \
  --version "$VERSION" \
  --report "dist/validation/$VERSION/release-launch.json" \
  --write-checklist "dist/validation/$VERSION/RELEASE_LAUNCH_CHECKLIST.md"
bash scripts/distribution_readiness.sh \
  --version "$VERSION" \
  --require-platform linux-x86_64 \
  --require-platform macos-x86_64 \
  --require-platform macos-arm64 \
  --require-platform windows-x86_64 \
  --report "dist/validation/$VERSION/distribution-readiness.json" \
  --write-checklist "dist/validation/$VERSION/DISTRIBUTION_CHECKLIST.md"
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

Submission metadata must point at immutable URLs under:

```text
https://github.com/codenz92/cool-lang/releases/download/v<version>/
```

Every generated package-manager record must carry the hosted SHA256 or SHA-256
value for the exact immutable release asset it installs.

## Homebrew

Reference: https://docs.brew.sh/Formula-Cookbook

Source file:

```text
dist/channels/<version>/homebrew/cool.rb
```

Before opening a tap pull request:

- Confirm each macOS/Linux URL points at the public GitHub Release tag.
- Confirm every SHA-256 in the formula matches the hosted asset.
- Keep the formula smoke test as `system "#{bin}/cool", "help"`.
- Include the release record, hosted verification report, distribution
  readiness report, and package publication evidence report in the pull request
  notes.
- Before opening a pull request, run:

```bash
brew audit --strict --online --formula dist/channels/<version>/homebrew/cool.rb
brew install --formula dist/channels/<version>/homebrew/cool.rb
cool help
```

Generate the packet with `package_submission_packet.sh` and use
`dist/submissions/<version>/homebrew/PR_BODY.md` as the review starting point.
After publication, update the status ledger to `published`, record the public
install command and evidence report, then run
`package_publication_check.sh --require-published homebrew`.

## Winget

Reference: https://learn.microsoft.com/en-us/windows/package-manager/package/manifest

Source tree:

```text
dist/channels/<version>/winget/Codenz.Cool/<version>/
```

Before submission:

- Confirm `PackageVersion` equals the Cool release version.
- Confirm `InstallerType: zip` and `NestedInstallerType: portable` are present.
- Confirm `RelativeFilePath` points at `cool-<version>-windows-x86_64/bin/cool.exe`.
- Confirm the installer URL and hash match the hosted Windows zip asset.
- Before submission, run:

```powershell
winget validate dist/channels/<version>/winget/Codenz.Cool/<version>
winget install --manifest dist/channels/<version>/winget/Codenz.Cool/<version> --accept-source-agreements --accept-package-agreements
cool help
```

Generate the packet with `package_submission_packet.sh` and copy the generated
`manifests/c/Codenz/Cool/<version>/` tree into a `microsoft/winget-pkgs` fork or
branch.
After publication, verify `winget install Codenz.Cool` from a clean Windows
environment, record the output, and run
`package_publication_check.sh --require-published winget`.

## Debian And Apt

Reference: https://www.debian.org/doc/debian-policy/

Source tree:

```text
dist/channels/<version>/apt/
```

Before publishing or handing the output to downstream packaging:

- Confirm the `.deb`, `Packages`, and `Packages.gz` files came from the same
  generated channel tree.
- Confirm the `Packages` entry has the hosted package version and SHA-256.
- Host the apt tree on an immutable release mirror or use it as packaging input;
  do not point users at transient workflow downloads.
- Before publishing a mirror or handing the package to downstream maintainers,
  run:

```bash
dpkg-deb --info dist/channels/<version>/apt/pool/main/c/cool/cool_<version>_amd64.deb
gzip -dc dist/channels/<version>/apt/dists/stable/main/binary-amd64/Packages.gz | grep -A8 '^Package: cool$'
```

After publication or mirror update, record the public apt source URL and install
command, then run `package_publication_check.sh --require-published debian`.

## Final Record

After package-manager submissions are opened or published, add their links and
any required manual edits to the versioned release record under
`docs/RELEASE_<version>.md`.
Use `docs/PACKAGE_SUBMISSION_REVIEW.md` for review-state rules and packet
contents.
