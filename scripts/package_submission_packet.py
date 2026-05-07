#!/usr/bin/env python3
import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHANNELS = {
    "homebrew": {
        "label": "Homebrew",
        "status_key": "homebrew",
        "official_refs": [
            "https://docs.brew.sh/Formula-Cookbook",
            "https://docs.brew.sh/Acceptable-Formulae",
            "https://docs.brew.sh/How-To-Open-a-Homebrew-Pull-Request",
        ],
    },
    "winget": {
        "label": "Winget",
        "status_key": "winget",
        "official_refs": [
            "https://learn.microsoft.com/en-us/windows/package-manager/package/manifest",
            "https://learn.microsoft.com/en-us/windows/package-manager/package/repository",
            "https://learn.microsoft.com/en-us/windows/package-manager/package/windows-package-manager-policies",
        ],
    },
    "debian": {
        "label": "Debian/apt",
        "status_key": "debian",
        "official_refs": [
            "https://www.debian.org/doc/debian-policy/",
            "https://www.debian.org/doc/debian-policy/ch-controlfields.html",
            "https://wiki.debian.org/DebianRepository/Format",
        ],
    },
}
VALID_PACKAGE_STATUSES = {"ready", "submitted", "published", "blocked", "deferred"}
VALID_REVIEW_STATUSES = {
    "not_submitted",
    "open",
    "changes_requested",
    "approved",
    "merged",
    "rejected",
    "blocked",
    "deferred",
}


def fail(message):
    raise SystemExit(f"package submission packet: {message}")


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def display_path(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_cargo_value(key):
    text = read_text(ROOT / "Cargo.toml")
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\"([^\"]+)\"", text)
    if not match:
        fail(f"could not read {key} from Cargo.toml")
    return match.group(1)


def add_check(checks, name, ok, detail="", severity="blocker"):
    checks.append({
        "name": name,
        "ok": bool(ok),
        "severity": severity,
        "detail": str(detail),
    })


def require_file(checks, path, name):
    ok = Path(path).is_file()
    add_check(checks, name, ok, display_path(path) if ok else f"missing {display_path(path)}")
    return ok


def require_path(checks, path, name):
    ok = Path(path).exists()
    add_check(checks, name, ok, display_path(path) if ok else f"missing {display_path(path)}")
    return ok


def copy_file(src, dst):
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_tree(src, dst):
    dst = Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def winget_submission_path(package_identifier, version):
    parts = package_identifier.split(".")
    publisher = parts[0] if parts else "Unknown"
    package = parts[1] if len(parts) > 1 else publisher
    letter = publisher[:1].lower() or "unknown"
    return Path("manifests") / letter / publisher / package / version


def channel_assets(channels_json):
    assets = {}
    for record in channels_json.get("platforms", []):
        platform_name = record.get("platform")
        if platform_name:
            assets[platform_name] = record.get("assets", {})
    return assets


def validate_docs(checks):
    docs = [
        ROOT / "docs/PACKAGE_SUBMISSION_REVIEW.md",
        ROOT / "docs/PACKAGE_MANAGER_SUBMISSIONS.md",
        ROOT / "docs/PACKAGE_PUBLICATION.md",
        ROOT / "docs/PACKAGE_SUBMISSION_STATUS.json",
    ]
    for doc in docs:
        require_file(checks, doc, f"{display_path(doc)} exists")
    review_doc = ROOT / "docs/PACKAGE_SUBMISSION_REVIEW.md"
    if review_doc.is_file():
        text = read_text(review_doc)
        for needle in [
            "Phase 31",
            "package_submission_packet.sh",
            "submission packet",
            "review_status",
            "https://docs.brew.sh/How-To-Open-a-Homebrew-Pull-Request",
            "https://learn.microsoft.com/en-us/windows/package-manager/package/repository",
            "https://wiki.debian.org/DebianRepository/Format",
        ]:
            add_check(checks, f"submission review docs include {needle}", needle in text, display_path(review_doc))


def validate_status(checks, status_path, package_name, version):
    status = {}
    if not require_file(checks, status_path, "package submission status file exists"):
        return status
    status = load_json(status_path)
    add_check(checks, "submission status schema version supports Phase 31", status.get("schema_version") == 3, status.get("schema_version"))
    package = status.get("package", {})
    add_check(checks, "submission status package name matches", package.get("name") == package_name, package.get("name", ""))
    add_check(checks, "submission status current release matches", package.get("current_release") == version, package.get("current_release", ""))
    policy = status.get("policy", {})
    add_check(checks, "submission policy records review statuses", set(policy.get("accepted_review_statuses", [])) >= VALID_REVIEW_STATUSES, policy.get("accepted_review_statuses", []))
    for channel in CHANNELS:
        record = status.get("channels", {}).get(channel, {})
        add_check(checks, f"{channel} status record exists", isinstance(record, dict) and bool(record), channel)
        add_check(checks, f"{channel} package status is valid", record.get("status") in VALID_PACKAGE_STATUSES, record.get("status", ""))
        add_check(checks, f"{channel} review status is valid", record.get("review_status") in VALID_REVIEW_STATUSES, record.get("review_status", ""))
        add_check(checks, f"{channel} submission packet path is recorded", bool(record.get("submission_packet")), record.get("submission_packet", ""))
        add_check(checks, f"{channel} next action is recorded", bool(record.get("next_action")), record.get("next_action", ""))
        add_check(checks, f"{channel} review labels are tracked", isinstance(record.get("review_labels"), list), record.get("review_labels", ""))
        if record.get("status") in {"submitted", "published"} or record.get("review_status") not in {"not_submitted", "deferred"}:
            add_check(checks, f"{channel} review URL is recorded after submission", bool(record.get("review_url")), record)
            add_check(checks, f"{channel} submitted_at is recorded after submission", bool(record.get("submitted_at")), record)
    return status


def write_homebrew_packet(version, channel_root, channels_json, output_root, checks):
    formula_rel = channels_json.get("channels", {}).get("homebrew_formula") or "homebrew/cool.rb"
    formula = channel_root / formula_rel
    if not require_file(checks, formula, "Homebrew formula exists for submission packet"):
        return None
    packet = output_root / "homebrew"
    formula_out = packet / "Formula" / "cool.rb"
    copy_file(formula, formula_out)
    write_text(packet / "PR_BODY.md", f"""## Cool {version} Homebrew Formula

Generated from `dist/channels/{version}/homebrew/cool.rb`.

Validation evidence:

- Release launch check
- Hosted release verification
- Distribution readiness
- Package submission check
- Package publication check

Install smoke:

```bash
brew audit --new --formula Formula/cool.rb
brew audit --strict --online --formula Formula/cool.rb
brew install --formula Formula/cool.rb
cool help
```
""")
    write_text(packet / "SUBMISSION.md", f"""# Homebrew Submission Packet For Cool {version}

Official references:

- https://docs.brew.sh/Formula-Cookbook
- https://docs.brew.sh/Acceptable-Formulae
- https://docs.brew.sh/How-To-Open-a-Homebrew-Pull-Request

Packet contents:

- `Formula/cool.rb`
- `PR_BODY.md`

Before opening a pull request or tap update:

```bash
brew audit --new --formula Formula/cool.rb
brew audit --strict --online --formula Formula/cool.rb
brew install --formula Formula/cool.rb
cool help
```

After opening the review, update `docs/PACKAGE_SUBMISSION_STATUS.json`:

- `status`: `submitted`
- `review_status`: `open`
- `submission_url` and `review_url`: pull request URL
- `submitted_at`: UTC date
""")
    add_check(checks, "Homebrew submission packet formula copied", formula_out.is_file(), display_path(formula_out))
    return {
        "channel": "homebrew",
        "path": display_path(packet),
        "primary_file": display_path(formula_out),
        "review_command": "brew audit --new --formula Formula/cool.rb",
    }


def write_winget_packet(version, channel_root, channels_json, output_root, checks):
    winget_rel = channels_json.get("channels", {}).get("winget")
    if not winget_rel:
        add_check(checks, "Winget channel exists for submission packet", False, "channels.json has no winget path")
        return None
    winget_root = channel_root / winget_rel
    if not require_path(checks, winget_root, "Winget manifest tree exists for submission packet"):
        return None
    version_manifest = winget_root / "Codenz.Cool.yaml"
    package_identifier = "Codenz.Cool"
    if version_manifest.is_file():
        match = re.search(r"(?m)^PackageIdentifier:\s*(.+?)\s*$", read_text(version_manifest))
        if match:
            package_identifier = match.group(1).strip().strip('"')
    target_rel = winget_submission_path(package_identifier, version)
    packet = output_root / "winget"
    target = packet / target_rel
    copy_tree(winget_root, target)
    write_text(packet / "PR_BODY.md", f"""## Cool {version} Winget Manifests

Generated from `dist/channels/{version}/winget/Codenz.Cool/{version}`.

Validation evidence:

- Hosted release verification for the Windows zip URL and SHA-256
- Package submission check
- Package publication check

Install smoke:

```powershell
winget validate {target_rel.as_posix()}
winget install --manifest {target_rel.as_posix()} --accept-source-agreements --accept-package-agreements
cool help
```
""")
    write_text(packet / "SUBMISSION.md", f"""# Winget Submission Packet For Cool {version}

Official references:

- https://learn.microsoft.com/en-us/windows/package-manager/package/manifest
- https://learn.microsoft.com/en-us/windows/package-manager/package/repository
- https://learn.microsoft.com/en-us/windows/package-manager/package/windows-package-manager-policies

Copy `{target_rel.as_posix()}` into a branch or fork of
`https://github.com/microsoft/winget-pkgs`.

Before opening a pull request:

```powershell
winget validate {target_rel.as_posix()}
powershell .\\Tools\\SandboxTest.ps1 {target_rel.as_posix()}
```

After opening the review, update `docs/PACKAGE_SUBMISSION_STATUS.json`:

- `status`: `submitted`
- `review_status`: `open`
- `submission_url` and `review_url`: pull request URL
- `submitted_at`: UTC date
""")
    add_check(checks, "Winget submission packet manifests copied", target.is_dir(), display_path(target))
    return {
        "channel": "winget",
        "path": display_path(packet),
        "primary_file": display_path(target),
        "review_command": f"winget validate {target_rel.as_posix()}",
    }


def write_debian_packet(version, channel_root, channels_json, output_root, checks):
    apt_root = channel_root / "apt"
    deb_rel = channels_json.get("channels", {}).get("debian_package")
    index_rel = channels_json.get("channels", {}).get("debian_packages_index")
    if not deb_rel or not index_rel:
        add_check(checks, "Debian channel exists for submission packet", False, "channels.json has no Debian package/index")
        return None
    if not require_path(checks, apt_root, "Debian apt tree exists for submission packet"):
        return None
    packet = output_root / "debian"
    target = packet / "apt"
    copy_tree(apt_root, target)
    write_text(packet / "SOURCES_LIST.example", "deb [trusted=yes] https://example.com/cool/apt stable main\n")
    write_text(packet / "SUBMISSION.md", f"""# Debian/Apt Submission Packet For Cool {version}

Official references:

- https://www.debian.org/doc/debian-policy/
- https://www.debian.org/doc/debian-policy/ch-controlfields.html
- https://wiki.debian.org/DebianRepository/Format

Packet contents:

- `apt/` generated repository tree
- `SOURCES_LIST.example`

This packet is suitable for a project-hosted apt mirror or as downstream
packaging input. Official Debian archive inclusion requires source packaging,
maintainer sponsorship, and policy review outside this generated binary mirror.

Before publishing a mirror:

```bash
dpkg-deb --info apt/pool/main/c/cool/cool_{version}_amd64.deb
gzip -dc apt/dists/stable/main/binary-amd64/Packages.gz | grep -A8 '^Package: cool$'
```

After a mirror or downstream review exists, update
`docs/PACKAGE_SUBMISSION_STATUS.json` with `submission_url`, `review_url`, and
`submitted_at`.
""")
    add_check(checks, "Debian submission packet apt tree copied", target.is_dir(), display_path(target))
    return {
        "channel": "debian",
        "path": display_path(packet),
        "primary_file": display_path(target),
        "review_command": f"dpkg-deb --info apt/pool/main/c/cool/cool_{version}_amd64.deb",
    }


def write_root_readme(output_root, version, packets):
    lines = [
        f"# Cool {version} Package Submission Packets",
        "",
        "Generated packet directories:",
        "",
    ]
    for packet in packets:
        lines.append(f"- `{packet['channel']}`: `{packet['path']}`")
    lines += [
        "",
        "Do not mark a channel as submitted until the package-index pull request,",
        "review, or mirror URL exists and has been recorded in",
        "`docs/PACKAGE_SUBMISSION_STATUS.json`.",
    ]
    write_text(output_root / "README.md", "\n".join(lines) + "\n")


def write_checklist(path, report):
    lines = [
        f"# Package Submission Packet Checklist For Cool {report['package']['version']}",
        "",
        f"Generated: {report['generated_at']}",
        f"Packet root: `{report['packet_root']}`",
        "",
        "## Automated Checks",
        "",
    ]
    for check in report["checks"]:
        mark = "x" if check["ok"] else " "
        lines.append(f"- [{mark}] {check['name']}")
    lines += [
        "",
        "## Packet Outputs",
        "",
    ]
    for packet in report["packets"]:
        lines.append(f"- `{packet['channel']}`: `{packet['path']}`")
    write_text(path, "\n".join(lines) + "\n")


def validate(args):
    package_name = read_cargo_value("name")
    version = args.version or read_cargo_value("version")
    checks = []
    validate_docs(checks)
    status = validate_status(checks, Path(args.status_file).resolve(), package_name, version)

    output_root = Path(args.output_dir).resolve() if args.output_dir else Path(args.dist_dir).resolve() / "submissions" / version
    packets = []
    channels_json = {}
    channel_root = Path(args.channel_root).resolve() if args.channel_root else Path(args.dist_dir).resolve() / "channels" / version

    if args.ledger_only:
        add_check(checks, "submission packet generation skipped by ledger-only mode", True, "ledger-only", "info")
    else:
        channels_path = channel_root / "channels.json"
        if require_file(checks, channels_path, "channels.json exists for submission packet generation"):
            channels_json = load_json(channels_path)
            package = channels_json.get("package", {})
            add_check(checks, "channels package name matches", package.get("name") == package_name, package.get("name", ""))
            add_check(checks, "channels package version matches", package.get("version") == version, package.get("version", ""))
            if output_root.exists() and not args.keep:
                shutil.rmtree(output_root)
            output_root.mkdir(parents=True, exist_ok=True)
            required = set(args.require_channel)
            writers = {
                "homebrew": write_homebrew_packet,
                "winget": write_winget_packet,
                "debian": write_debian_packet,
            }
            present = []
            channels = channels_json.get("channels", {})
            if channels.get("homebrew_formula"):
                present.append("homebrew")
            if channels.get("winget"):
                present.append("winget")
            if channels.get("debian_package") or channels.get("debian_packages_index"):
                present.append("debian")
            for channel in sorted(set(present) | required):
                packet = writers[channel](version, channel_root, channels_json, output_root, checks)
                if packet:
                    packets.append(packet)
            write_root_readme(output_root, version, packets)
            write_json(output_root / "packet_manifest.json", {
                "schema_version": 1,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "package": {"name": package_name, "version": version},
                "channel_root": display_path(channel_root),
                "packets": packets,
            })
            add_check(checks, "submission packet manifest written", (output_root / "packet_manifest.json").is_file(), display_path(output_root / "packet_manifest.json"))

    blockers = [check for check in checks if not check["ok"] and check["severity"] == "blocker"]
    warnings = [check for check in checks if not check["ok"] and check["severity"] != "blocker"]
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package": {"name": package_name, "version": version},
        "status_schema_version": status.get("schema_version") if isinstance(status, dict) else None,
        "channel_root": display_path(channel_root),
        "packet_root": display_path(output_root),
        "ledger_only": bool(args.ledger_only),
        "packets": packets,
        "summary": {
            "checks": len(checks),
            "passed": len([check for check in checks if check["ok"]]),
            "blockers": len(blockers),
            "warnings": len(warnings),
            "ready": len(blockers) == 0,
        },
        "checks": checks,
    }
    return report, blockers


def main():
    parser = argparse.ArgumentParser(description="Generate and validate package-manager submission packets for Cool.")
    parser.add_argument("--version")
    parser.add_argument("--dist-dir", default=str(ROOT / "dist"))
    parser.add_argument("--channel-root")
    parser.add_argument("--output-dir")
    parser.add_argument("--status-file", default=str(ROOT / "docs/PACKAGE_SUBMISSION_STATUS.json"))
    parser.add_argument("--require-channel", action="append", choices=sorted(CHANNELS), default=[])
    parser.add_argument("--ledger-only", action="store_true")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--report")
    parser.add_argument("--write-checklist")
    args = parser.parse_args()

    report, blockers = validate(args)
    if args.report:
        write_json(args.report, report)
    if args.write_checklist:
        write_checklist(args.write_checklist, report)
    if blockers:
        for check in blockers:
            print(f"BLOCKER {check['name']}: {check.get('detail', '')}")
        fail(f"{len(blockers)} blocker(s) found")

    print("package submission packet: ok")
    print(f"  Version -> {report['package']['version']}")
    print(f"  Checks  -> {report['summary']['passed']}/{report['summary']['checks']} passed")
    if report["ledger_only"]:
        print("  Mode    -> ledger-only")
    else:
        print(f"  Packets -> {report['packet_root']}")
    if args.report:
        print(f"  Report  -> {args.report}")
    if args.write_checklist:
        print(f"  List    -> {args.write_checklist}")


if __name__ == "__main__":
    main()
