#!/usr/bin/env python3
import argparse
import gzip
import io
import json
import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://github.com/codenz92/cool-lang/releases/download"
VALID_STATUSES = {"ready", "submitted", "published", "blocked", "deferred"}
VALID_STATUS_SCHEMA_VERSIONS = {1, 2, 3}


def fail(message):
    raise SystemExit(f"package submission check: {message}")


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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


def check_contains(checks, path, needle, name):
    path = Path(path)
    if not require_file(checks, path, f"{display_path(path)} exists"):
        return
    text = read_text(path)
    add_check(checks, name, needle in text, f"{display_path(path)} needs {needle}")


def expected_url(base_url, tag, filename):
    return f"{base_url.rstrip('/')}/{tag}/{filename}"


def channel_assets(channels_json):
    assets = {}
    for platform in channels_json.get("platforms", []):
        name = platform.get("platform")
        if name:
            assets[name] = platform.get("assets", {})
    return assets


def yaml_value(text, key):
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", text)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def read_ar_members(path):
    data = Path(path).read_bytes()
    if not data.startswith(b"!<arch>\n"):
        fail(f"invalid Debian ar archive: {path}")
    offset = 8
    members = {}
    while offset < len(data):
        header = data[offset:offset + 60]
        if len(header) < 60:
            fail(f"truncated ar header in {path}")
        name = header[:16].decode("ascii", errors="replace").strip().rstrip("/")
        size_text = header[48:58].decode("ascii", errors="replace").strip()
        try:
            size = int(size_text)
        except ValueError:
            fail(f"invalid ar member size in {path}: {size_text}")
        offset += 60
        members[name] = data[offset:offset + size]
        offset += size
        if offset % 2:
            offset += 1
    return members


def deb_control_text(path):
    members = read_ar_members(path)
    control_data = members.get("control.tar.gz")
    if control_data is None:
        fail(f"Debian package missing control.tar.gz: {path}")
    with tarfile.open(fileobj=io.BytesIO(control_data), mode="r:gz") as archive:
        for member in archive.getmembers():
            if Path(member.name).name == "control":
                fh = archive.extractfile(member)
                if fh is None:
                    break
                return fh.read().decode("utf-8")
    fail(f"Debian package missing control file: {path}")


def validate_status_file(checks, status_file, package_name, version):
    if not require_file(checks, status_file, "package submission status file exists"):
        return {}
    data = load_json(status_file)
    add_check(checks, "submission status schema version is supported", data.get("schema_version") in VALID_STATUS_SCHEMA_VERSIONS)
    package = data.get("package", {})
    add_check(checks, "submission status package name matches", package.get("name") == package_name)
    add_check(checks, "submission status current release matches", package.get("current_release") == version)
    channels = data.get("channels", {})
    for channel in ("homebrew", "winget", "debian"):
        record = channels.get(channel, {})
        add_check(checks, f"{channel} submission status is recorded", bool(record), status_file)
        status = record.get("status")
        add_check(checks, f"{channel} submission status value is valid", status in VALID_STATUSES, str(status))
        add_check(checks, f"{channel} submission source path is recorded", bool(record.get("source")), str(record.get("source", "")))
        if status in ("submitted", "published"):
            add_check(
                checks,
                f"{channel} submitted/published status has evidence URL",
                bool(record.get("submission_url") or record.get("published_url")),
                str(record),
            )
        if data.get("schema_version") in (2, 3):
            for field in ("submitted_at", "published_at", "verified_at", "public_install_command", "external_install_report"):
                add_check(
                    checks,
                    f"{channel} publication evidence field is tracked: {field}",
                    field in record,
                    str(record.get(field, "")),
                )
    return data


def validate_docs(checks):
    submission_doc = ROOT / "docs/PACKAGE_MANAGER_SUBMISSIONS.md"
    ecosystem_doc = ROOT / "docs/ECOSYSTEM_ADOPTION.md"
    maintenance_doc = ROOT / "docs/MAINTENANCE.md"
    for path in (submission_doc, ecosystem_doc, maintenance_doc, ROOT / "docs/FIRST_30_MINUTES.md"):
        require_file(checks, path, f"{display_path(path)} exists")
    for needle in [
        "https://docs.brew.sh/Formula-Cookbook",
        "brew audit --strict --online",
        "https://learn.microsoft.com/en-us/windows/package-manager/package/manifest",
        "winget validate",
        "https://www.debian.org/doc/debian-policy/",
        "SHA256",
    ]:
        check_contains(checks, submission_doc, needle, f"submission docs include {needle}")
    for needle in ["Phase 29", "external install", "package-manager", "adoption"]:
        check_contains(checks, ecosystem_doc, needle, f"ecosystem docs include {needle}")
    for needle in ["1.1.x", "hotfix", "rollback", "package-channel"]:
        check_contains(checks, maintenance_doc, needle, f"maintenance docs include {needle}")


def validate_homebrew(checks, channel_root, channels_json, assets, base_url, tag, required):
    formula_rel = channels_json.get("channels", {}).get("homebrew_formula")
    formula_path = channel_root / formula_rel if formula_rel else channel_root / "homebrew/cool.rb"
    if not formula_path.is_file():
        add_check(checks, "Homebrew formula exists", not required, display_path(formula_path))
        return
    text = read_text(formula_path)
    for needle, label in [
        ("class Cool < Formula", "Homebrew formula defines Cool"),
        ('homepage "https://github.com/codenz92/cool-lang"', "Homebrew formula homepage is canonical"),
        ('license "MIT"', "Homebrew formula license is present"),
        ('system "#{bin}/cool", "help"', "Homebrew formula has install smoke test"),
    ]:
        add_check(checks, label, needle in text, display_path(formula_path))
    add_check(checks, "Homebrew formula avoids mutable latest URLs", "/latest/download/" not in text and "/releases/latest/" not in text)
    for platform_name in ("macos-arm64", "macos-x86_64", "linux-x86_64"):
        asset = assets.get(platform_name, {}).get("tar.gz")
        if not asset:
            continue
        url = expected_url(base_url, tag, asset["filename"])
        add_check(checks, f"Homebrew formula references {platform_name} URL", url in text, url)
        add_check(checks, f"Homebrew formula references {platform_name} SHA-256", asset["sha256"] in text, asset["filename"])


def validate_winget(checks, channel_root, channels_json, assets, base_url, tag, version, required):
    winget_rel = channels_json.get("channels", {}).get("winget")
    if not winget_rel:
        add_check(checks, "Winget channel exists", not required, "channels.json has no winget path")
        return
    winget_root = channel_root / winget_rel
    version_file = winget_root / "Codenz.Cool.yaml"
    locale_file = winget_root / "Codenz.Cool.locale.en-US.yaml"
    installer_file = winget_root / "Codenz.Cool.installer.yaml"
    for path, label in [
        (version_file, "Winget version manifest exists"),
        (locale_file, "Winget locale manifest exists"),
        (installer_file, "Winget installer manifest exists"),
    ]:
        require_file(checks, path, label)
    if not installer_file.is_file():
        return
    installer = read_text(installer_file)
    locale = read_text(locale_file) if locale_file.is_file() else ""
    version_manifest = read_text(version_file) if version_file.is_file() else ""
    windows_zip = assets.get("windows-x86_64", {}).get("zip")
    expected_manifest_version = "1.12.0"
    for text, label in [
        (version_manifest, "Winget version manifest"),
        (locale, "Winget locale manifest"),
        (installer, "Winget installer manifest"),
    ]:
        add_check(checks, f"{label} uses current manifest schema", f"ManifestVersion: {expected_manifest_version}" in text)
        add_check(checks, f"{label} package identifier is stable", "PackageIdentifier: Codenz.Cool" in text)
        add_check(checks, f"{label} package version matches", f"PackageVersion: {version}" in text)
    for needle, label in [
        ("InstallerType: zip", "Winget installer type is zip"),
        ("NestedInstallerType: portable", "Winget nested installer type is portable"),
        ("PortableCommandAlias: cool", "Winget portable command alias is cool"),
        (f"RelativeFilePath: cool-{version}-windows-x86_64/bin/cool.exe", "Winget nested binary path is stable"),
    ]:
        add_check(checks, label, needle in installer, display_path(installer_file))
    if windows_zip:
        url = expected_url(base_url, tag, windows_zip["filename"])
        add_check(checks, "Winget installer URL is immutable release asset", url in installer, url)
        add_check(checks, "Winget installer SHA-256 matches Windows zip", windows_zip["sha256"].upper() in installer, windows_zip["filename"])
    elif required:
        add_check(checks, "Winget Windows zip asset exists", False, "missing windows-x86_64 zip")


def validate_debian(checks, channel_root, channels_json, version, required):
    deb_rel = channels_json.get("channels", {}).get("debian_package")
    index_rel = channels_json.get("channels", {}).get("debian_packages_index")
    if not deb_rel or not index_rel:
        add_check(checks, "Debian channel exists", not required, "channels.json has no Debian package/index")
        return
    deb_path = channel_root / deb_rel
    index_path = channel_root / index_rel
    packages_gz = index_path.with_name("Packages.gz")
    if require_file(checks, deb_path, "Debian .deb package exists"):
        control = deb_control_text(deb_path)
        for needle, label in [
            ("Package: cool", "Debian control package name is cool"),
            (f"Version: {version}", "Debian control version matches"),
            ("Architecture: amd64", "Debian control architecture is amd64"),
            ("Maintainer:", "Debian control maintainer is present"),
            ("Description:", "Debian control description is present"),
            ("Homepage: https://github.com/codenz92/cool-lang", "Debian control homepage is canonical"),
        ]:
            add_check(checks, label, needle in control, deb_rel)
    index = None
    if require_file(checks, index_path, "Debian Packages index exists"):
        index = read_text(index_path)
        for needle, label in [
            ("Package: cool", "Debian index package name is cool"),
            (f"Version: {version}", "Debian index version matches"),
            ("Architecture: amd64", "Debian index architecture is amd64"),
            ("Filename:", "Debian index filename is present"),
            ("Size:", "Debian index size is present"),
            ("SHA256:", "Debian index SHA-256 is present"),
        ]:
            add_check(checks, label, needle in index, index_rel)
    if require_file(checks, packages_gz, "Debian Packages.gz index exists"):
        try:
            decoded = gzip.decompress(packages_gz.read_bytes()).decode("utf-8")
        except OSError as exc:
            add_check(checks, "Debian Packages.gz is valid gzip", False, str(exc))
        else:
            add_check(
                checks,
                "Debian Packages.gz matches Packages index",
                index is not None and decoded == index,
                display_path(packages_gz),
            )


def write_checklist(path, report):
    version = report["package"]["version"]
    lines = [
        f"# Package Submission Checklist For Cool {version}",
        "",
        f"Generated: {report['generated_at']}",
        f"Tag: `{report['release']['tag']}`",
        "",
        "## Automated Checks",
        "",
    ]
    for check in report["checks"]:
        mark = "x" if check["ok"] else " "
        lines.append(f"- [{mark}] {check['name']}")
    lines += [
        "",
        "## Manual Submission Commands",
        "",
        "- Homebrew: `brew audit --strict --online --formula dist/channels/<version>/homebrew/cool.rb` before opening the tap pull request.",
        "- Winget: `winget validate dist/channels/<version>/winget/Codenz.Cool/<version>` before submitting to `microsoft/winget-pkgs`.",
        "- Debian/apt: `dpkg-deb --info <deb>` and verify the generated `Packages` / `Packages.gz` pair before publishing a mirror.",
        "",
        "## Evidence To Record",
        "",
        "- Package-index pull request or publication URL.",
        "- Any manual metadata edits required by the index.",
        "- External install verification report after the package is visible to users.",
    ]
    write_text(path, "\n".join(lines) + "\n")


def validate(args):
    package_name = read_cargo_value("name")
    version = args.version or read_cargo_value("version")
    tag = args.tag or f"v{version}"
    base_url = args.base_url
    channel_root = Path(args.channel_root).resolve() if args.channel_root else Path(args.dist_dir).resolve() / "channels" / version
    channels_path = channel_root / "channels.json"
    checks = []

    validate_docs(checks)
    status = validate_status_file(checks, Path(args.status_file).resolve(), package_name, version)

    if require_file(checks, channels_path, "channels.json exists for package submission"):
        channels_json = load_json(channels_path)
        package = channels_json.get("package", {})
        add_check(checks, "channels package name matches", package.get("name") == package_name)
        add_check(checks, "channels package version matches", package.get("version") == version)
        release = channels_json.get("release", {})
        add_check(checks, "channels release tag matches", release.get("tag") == tag, str(release.get("tag")))
        add_check(checks, "channels base URL is immutable GitHub Release base", release.get("base_url") == base_url, str(release.get("base_url")))
        assets = channel_assets(channels_json)
        required = set(args.require_channel)
        validate_homebrew(checks, channel_root, channels_json, assets, base_url, tag, "homebrew" in required)
        validate_winget(checks, channel_root, channels_json, assets, base_url, tag, version, "winget" in required)
        validate_debian(checks, channel_root, channels_json, version, "debian" in required)
    else:
        channels_json = {}

    blockers = [check for check in checks if not check["ok"] and check["severity"] == "blocker"]
    warnings = [check for check in checks if not check["ok"] and check["severity"] != "blocker"]
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package": {"name": package_name, "version": version},
        "release": {"tag": tag, "base_url": base_url},
        "channel_root": display_path(channel_root),
        "status": status.get("channels", {}) if isinstance(status, dict) else {},
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
    parser = argparse.ArgumentParser(description="Validate Cool package-manager submission metadata from generated package channels.")
    parser.add_argument("--version")
    parser.add_argument("--tag")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--dist-dir", default=str(ROOT / "dist"))
    parser.add_argument("--channel-root")
    parser.add_argument("--status-file", default=str(ROOT / "docs/PACKAGE_SUBMISSION_STATUS.json"))
    parser.add_argument("--require-channel", action="append", choices=["homebrew", "winget", "debian"], default=[])
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

    print("package submission check: ok")
    print(f"  Version -> {report['package']['version']}")
    print(f"  Tag     -> {report['release']['tag']}")
    print(f"  Checks  -> {report['summary']['passed']}/{report['summary']['checks']} passed")
    if args.report:
        print(f"  Report  -> {args.report}")
    if args.write_checklist:
        print(f"  List    -> {args.write_checklist}")


if __name__ == "__main__":
    main()
