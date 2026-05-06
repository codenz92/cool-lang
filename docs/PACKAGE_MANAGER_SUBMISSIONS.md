# Package Manager Submissions

This checklist starts after the public GitHub Release assets exist. Do not
submit package-manager metadata from local `dist/` output or workflow artifacts.

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

## Homebrew

Source file:

```text
dist/channels/<version>/homebrew/cool.rb
```

Before opening a tap pull request:

- Confirm each macOS/Linux URL points at the public GitHub Release tag.
- Confirm every SHA-256 in the formula matches the hosted asset.
- Keep the formula smoke test as `system "#{bin}/cool", "help"`.
- Include the release record, hosted verification report, and distribution
  readiness report in the pull request notes.

## Winget

Source tree:

```text
dist/channels/<version>/winget/Codenz.Cool/<version>/
```

Before submission:

- Confirm `PackageVersion` equals the Cool release version.
- Confirm `InstallerType: zip` and `NestedInstallerType: portable` are present.
- Confirm `RelativeFilePath` points at `cool-<version>-windows-x86_64/bin/cool.exe`.
- Confirm the installer URL and hash match the hosted Windows zip asset.

## Debian And Apt

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

## Final Record

After package-manager submissions are opened or published, add their links and
any required manual edits to the versioned release record under
`docs/RELEASE_<version>.md`.
