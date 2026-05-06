#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PLATFORMS = [
    "linux-x86_64",
    "macos-x86_64",
    "macos-arm64",
    "windows-x86_64",
]


def fail(message):
    raise SystemExit(f"release launch check: {message}")


def display_path(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_cargo_value(key):
    text = read_text(ROOT / "Cargo.toml")
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\"([^\"]+)\"", text)
    if not match:
        fail(f"could not read {key} from Cargo.toml")
    return match.group(1)


def read_lock_package_version(package_name):
    text = read_text(ROOT / "Cargo.lock")
    for section in text.split("[[package]]"):
        if re.search(rf"(?m)^\s*name\s*=\s*\"{re.escape(package_name)}\"\s*$", section):
            match = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"\s*$', section)
            if match:
                return match.group(1)
    return None


def semver_tuple(version):
    match = re.fullmatch(r"([0-9]+)\.([0-9]+)\.([0-9]+)", version)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def git_output(*args):
    proc = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def local_release_tags():
    tags = []
    for line in git_output("tag", "--list", "v*").splitlines():
        name = line.strip()
        version = name[1:] if name.startswith("v") else name
        parsed = semver_tuple(version)
        if parsed is not None:
            tags.append((parsed, name, version))
    return sorted(tags)


def add_check(checks, name, ok, detail="", severity="blocker"):
    checks.append({
        "name": name,
        "ok": bool(ok),
        "severity": severity,
        "detail": detail,
    })


def require_file(checks, rel, label=None):
    path = ROOT / rel
    ok = path.is_file()
    add_check(checks, label or f"{rel} exists", ok, display_path(path) if ok else f"missing {rel}")
    return ok


def check_contains(checks, rel, needle, label=None):
    path = ROOT / rel
    if not path.is_file():
        add_check(checks, label or f"{rel} contains {needle}", False, f"missing {rel}")
        return
    text = read_text(path)
    add_check(checks, label or f"{rel} contains {needle}", needle in text, display_path(path))


def release_doc_name(version):
    return f"docs/RELEASE_{version.replace('.', '_')}.md"


def changelog_version_headings(version):
    text = read_text(ROOT / "CHANGELOG.md")
    return re.findall(rf"(?m)^## \[{re.escape(version)}\](?:\s|$)", text)


def validate(args):
    package_name = read_cargo_value("name")
    version = args.version or read_cargo_value("version")
    parsed_version = semver_tuple(version)
    tag = args.tag or f"v{version}"
    checks = []

    add_check(checks, "version is semantic X.Y.Z", parsed_version is not None, version)
    add_check(
        checks,
        "Cargo.toml package version matches launch version",
        read_cargo_value("version") == version,
        f"Cargo.toml version={read_cargo_value('version')} launch={version}",
    )
    lock_version = read_lock_package_version(package_name)
    add_check(
        checks,
        "Cargo.lock package version matches launch version",
        lock_version == version,
        f"Cargo.lock version={lock_version} launch={version}",
    )

    tags = local_release_tags()
    tag_names = {name for _, name, _ in tags}
    target_tag_exists = tag in tag_names
    if args.require_unreleased_tag:
        add_check(checks, "target public tag is not already present", not target_tag_exists, tag)
    else:
        add_check(checks, "target public tag state recorded", True, f"{tag} exists={target_tag_exists}", "info")
    if parsed_version is not None and tags:
        latest_tuple, latest_tag, latest_version = tags[-1]
        add_check(
            checks,
            "launch version is not behind latest local release tag",
            parsed_version >= latest_tuple,
            f"latest={latest_tag} launch={tag}",
        )
        if args.require_newer_than_latest_tag:
            add_check(
                checks,
                "launch version is newer than latest local release tag",
                parsed_version > latest_tuple,
                f"latest={latest_version} launch={version}",
            )

    headings = changelog_version_headings(version)
    add_check(
        checks,
        "CHANGELOG has exactly one heading for launch version",
        len(headings) == 1,
        f"found {len(headings)} heading(s) for {version}",
    )
    check_contains(checks, "CHANGELOG.md", "Phase 28", "CHANGELOG records Phase 28")
    check_contains(checks, "CHANGELOG.md", f"[{version}]: https://github.com/codenz92/cool-lang/releases/tag/{tag}", "CHANGELOG links launch tag")

    rel_doc = release_doc_name(version)
    if require_file(checks, rel_doc, f"{rel_doc} exists"):
        for needle in [
            tag,
            "Release state:",
            "Phase 28",
            "release-launch.json",
            "distribution-readiness.json",
            "hosted-release-validation.json",
        ]:
            check_contains(checks, rel_doc, needle, f"{rel_doc} records {needle}")

    if require_file(checks, "docs/PACKAGE_MANAGER_SUBMISSIONS.md"):
        for needle in ["Homebrew", "Winget", "Debian", "hosted verification"]:
            check_contains(checks, "docs/PACKAGE_MANAGER_SUBMISSIONS.md", needle, f"package submissions doc covers {needle}")

    for rel in [
        "scripts/release_launch_check.sh",
        "scripts/release_launch_check.py",
        "scripts/distribution_readiness.py",
        "scripts/validate_release.py",
        "scripts/release_candidate.sh",
        "apps/release_audit.cool",
        ".github/workflows/release-validation.yml",
        ".github/workflows/release-matrix.yml",
        ".github/workflows/published-release.yml",
    ]:
        require_file(checks, rel)

    for rel, needle, label in [
        ("scripts/release_gate.sh", "release_launch_check.sh", "release gate runs launch check"),
        ("scripts/release_candidate.sh", "release_launch_check.py", "release candidates package launch check"),
        ("scripts/release_candidate.sh", "RELEASE_*.md", "release candidates package release records"),
        ("scripts/validate_release.py", "PACKAGE_MANAGER_SUBMISSIONS.md", "release validation requires package submissions doc"),
        ("scripts/validate_release.py", "RELEASE_", "release validation requires versioned release record"),
        ("apps/release_audit.cool", "Phase 28", "release audit checks Phase 28 roadmap"),
        (".github/workflows/release-validation.yml", "release_launch_check.sh", "release validation workflow runs launch check"),
        (".github/workflows/release-matrix.yml", "release_launch_check.sh", "release matrix workflow runs launch check"),
        (".github/workflows/published-release.yml", "release_launch_check.sh", "published-release workflow runs launch check"),
        ("docs/RELEASE_RUNBOOK.md", "release_launch_check.sh", "runbook includes launch check"),
        ("docs/RELEASE_VALIDATION.md", "release_launch_check.sh", "release validation docs include launch check"),
        ("docs/README.md", "PACKAGE_MANAGER_SUBMISSIONS.md", "docs index links package submissions"),
        ("ROADMAP.md", "Phase 28", "roadmap records Phase 28"),
    ]:
        check_contains(checks, rel, needle, label)

    for platform_name in REQUIRED_PLATFORMS:
        check_contains(checks, "docs/RELEASE_RUNBOOK.md", platform_name, f"runbook mentions required platform {platform_name}")

    blockers = [check for check in checks if not check["ok"] and check["severity"] == "blocker"]
    warnings = [check for check in checks if not check["ok"] and check["severity"] != "blocker"]
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package": {"name": package_name, "version": version},
        "release": {
            "tag": tag,
            "target_tag_exists": target_tag_exists,
            "latest_local_tag": tags[-1][1] if tags else None,
            "required_platforms": REQUIRED_PLATFORMS,
        },
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


def write_checklist(path, report):
    version = report["package"]["version"]
    tag = report["release"]["tag"]
    lines = [
        f"# Release Launch Checklist For Cool {version}",
        "",
        f"Generated: {report['generated_at']}",
        f"Tag: `{tag}`",
        "",
        "## Automated Checks",
        "",
    ]
    for check in report["checks"]:
        mark = "x" if check["ok"] else " "
        lines.append(f"- [{mark}] {check['name']}")
    lines += [
        "",
        "## Launch Steps",
        "",
        f"- [ ] Confirm `bash scripts/release_gate.sh` passed on the launch commit.",
        f"- [ ] Run or dispatch the four-platform Release Matrix for `{tag}`.",
        "- [ ] Confirm release validation, distribution readiness, and package-channel archives were uploaded.",
        "- [ ] Run hosted release verification against public GitHub Release URLs.",
        f"- [ ] Update `docs/RELEASE_{version.replace('.', '_')}.md` with final workflow and hosted verification links.",
        "- [ ] Submit package-manager metadata only after hosted verification passes.",
        "",
    ]
    write_text(path, "\n".join(lines))


def parse_args():
    parser = argparse.ArgumentParser(description="Audit Cool public release launch identity and evidence wiring.")
    parser.add_argument("--version", help="Launch version without leading v. Defaults to Cargo.toml.")
    parser.add_argument("--tag", help="Launch tag. Defaults to v<version>.")
    parser.add_argument("--report", help="Write JSON launch-check evidence to this path.")
    parser.add_argument("--write-checklist", help="Write a Markdown launch checklist to this path.")
    parser.add_argument("--require-unreleased-tag", action="store_true", help="Fail if the target tag already exists locally.")
    parser.add_argument("--require-newer-than-latest-tag", action="store_true", help="Fail unless version is newer than every local v* tag.")
    return parser.parse_args()


def main():
    args = parse_args()
    report, blockers = validate(args)
    if args.report:
        write_json(args.report, report)
    if args.write_checklist:
        write_checklist(args.write_checklist, report)
    if blockers:
        for check in blockers:
            print(f"BLOCKER {check['name']}: {check['detail']}", flush=True)
        fail(f"{len(blockers)} blocker(s) found")
    print("release launch check: ok")
    print(f"  Version -> {report['package']['version']}")
    print(f"  Tag     -> {report['release']['tag']}")
    print(f"  Checks  -> {report['summary']['passed']}/{report['summary']['checks']} passed")
    if args.report:
        print(f"  Report  -> {display_path(args.report)}")
    if args.write_checklist:
        print(f"  List    -> {display_path(args.write_checklist)}")


if __name__ == "__main__":
    main()
