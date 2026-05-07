# Package Submission Review

Phase 31 prepares package-manager reviews without claiming they have happened.
It generates channel-specific submission packets, validates review-tracking
fields in `docs/PACKAGE_SUBMISSION_STATUS.json`, and records the exact next
action for each package manager.

## Phase 31 Gate

Generate submission packets after package channels are generated:

```bash
VERSION=1.1.0
bash scripts/package_submission_packet.sh \
  --version "$VERSION" \
  --require-channel homebrew \
  --require-channel winget \
  --require-channel debian \
  --report "dist/validation/$VERSION/package-submission-packet.json" \
  --write-checklist "dist/validation/$VERSION/PACKAGE_SUBMISSION_PACKET_CHECKLIST.md"
```

The packet root defaults to `dist/submissions/<version>/`. A full matrix release
should produce:

- `dist/submissions/<version>/homebrew/Formula/cool.rb`
- `dist/submissions/<version>/winget/manifests/c/Codenz/Cool/<version>/`
- `dist/submissions/<version>/debian/apt/`
- per-channel `SUBMISSION.md` and pull-request body templates
- `packet_manifest.json`

Before package channels exist, use ledger-only mode in release gates:

```bash
bash scripts/package_submission_packet.sh --version "$VERSION" --ledger-only
```

## Review Status Ledger

`docs/PACKAGE_SUBMISSION_STATUS.json` uses schema version 3. Each channel tracks:

- `submission_packet` - generated packet directory.
- `submission_branch` - fork or branch name once a review is opened.
- `review_url` - package-index pull request, issue, mirror, or downstream review
  URL.
- `review_status` - one of `not_submitted`, `open`, `changes_requested`,
  `approved`, `merged`, `rejected`, `blocked`, or `deferred`.
- `review_labels` - package-index labels or moderator state.
- `last_checked_at` - UTC date/time of the latest review state check.
- `next_action` - concrete maintainer action needed before the next status
  transition.

Do not move a channel from `ready` to `submitted` until `review_url` and
`submitted_at` are recorded.

## Homebrew Packet

Official references:

- https://docs.brew.sh/Formula-Cookbook
- https://docs.brew.sh/Acceptable-Formulae
- https://docs.brew.sh/How-To-Open-a-Homebrew-Pull-Request

The generated packet contains a `Formula/cool.rb` copy and review notes. Before
opening a tap or `homebrew/core` pull request, run:

```bash
brew audit --new --formula Formula/cool.rb
brew audit --strict --online --formula Formula/cool.rb
brew install --formula Formula/cool.rb
cool help
```

Homebrew review may require a project tap before `homebrew/core` is appropriate.
Record that decision in `next_action` rather than forcing a status change.

## Winget Packet

Official references:

- https://learn.microsoft.com/en-us/windows/package-manager/package/manifest
- https://learn.microsoft.com/en-us/windows/package-manager/package/repository
- https://learn.microsoft.com/en-us/windows/package-manager/package/windows-package-manager-policies

The generated packet copies manifests into the `winget-pkgs` repository layout:

```text
manifests/c/Codenz/Cool/<version>/
```

Before opening a pull request:

```powershell
winget validate manifests/c/Codenz/Cool/<version>
powershell .\Tools\SandboxTest.ps1 manifests/c/Codenz/Cool/<version>
```

After opening a review, record the `microsoft/winget-pkgs` pull request URL and
bot/moderator labels in `review_labels`.

## Debian And Apt Packet

Official references:

- https://www.debian.org/doc/debian-policy/
- https://www.debian.org/doc/debian-policy/ch-controlfields.html
- https://wiki.debian.org/DebianRepository/Format

The generated Debian packet is a project apt mirror packet, not an official
Debian archive upload. Official Debian inclusion requires source packaging,
maintainer sponsorship, and a policy review outside this generated binary
mirror.

Before publishing a project mirror:

```bash
dpkg-deb --info apt/pool/main/c/cool/cool_<version>_amd64.deb
gzip -dc apt/dists/stable/main/binary-amd64/Packages.gz | grep -A8 '^Package: cool$'
```

If the chosen path is downstream Debian packaging instead of a project mirror,
record the downstream issue, merge request, or sponsor review URL in
`review_url`.
