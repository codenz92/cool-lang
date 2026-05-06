#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://github.com/codenz92/cool-lang/releases/download"


def fail(message):
    raise SystemExit(f"distribution readiness: {message}")


def display_path(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_cargo_value(key):
    text = (ROOT / "Cargo.toml").read_text(encoding="utf-8")
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\"([^\"]+)\"", text)
    if not match:
        fail(f"could not read {key} from Cargo.toml")
    return match.group(1)


def sha256_path(path):
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_sha256sums(path):
    entries = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            fail(f"invalid checksum line in {path}: {line_no}")
        digest, rel = parts
        rel = rel.strip().lstrip("*")
        entries[rel] = digest.lower()
    return entries


def add_check(checks, name, ok, detail="", severity="blocker"):
    checks.append({
        "name": name,
        "ok": bool(ok),
        "severity": severity,
        "detail": detail,
    })


def require_file(checks, path, label):
    ok = path.is_file()
    add_check(checks, label, ok, display_path(path) if ok else f"missing {display_path(path)}")
    return ok


def expected_asset_url(base_url, tag, filename):
    return f"{base_url.rstrip('/')}/{tag}/{filename}"


def release_assets(release_json, package_name, version):
    assets = {}
    pattern = re.compile(rf"^{re.escape(package_name)}-{re.escape(version)}-(.+)\.(tar\.gz|zip)$")
    for asset in release_json.get("assets", []):
        filename = asset.get("filename") or asset.get("path") or ""
        platform_name = asset.get("platform")
        kind = asset.get("kind")
        if not platform_name or not kind:
            match = pattern.match(filename)
            if not match:
                continue
            platform_name, ext = match.groups()
            kind = "tar.gz" if ext == "tar.gz" else "zip"
        enriched = dict(asset)
        enriched["filename"] = filename
        enriched["platform"] = platform_name
        enriched["kind"] = kind
        assets.setdefault(platform_name, {})[kind] = enriched
    return assets


def channels_assets(channels_json):
    assets = {}
    for record in channels_json.get("platforms", []):
        platform_name = record.get("platform")
        if platform_name:
            assets[platform_name] = record.get("assets", {})
    return assets


def validate_release_files(checks, release_dir, package_name, version, release_json, required_platforms):
    sums_path = release_dir / "SHA256SUMS"
    if not require_file(checks, sums_path, "release SHA256SUMS exists"):
        return {}
    sums = parse_sha256sums(sums_path)
    assets = release_assets(release_json, package_name, version)
    for platform_name in required_platforms:
        add_check(
            checks,
            f"release includes required platform {platform_name}",
            platform_name in assets,
            "release.json platform list",
        )
    for platform_name, kinds in sorted(assets.items()):
        for kind, asset in sorted(kinds.items()):
            filename = asset.get("filename", "")
            asset_path = release_dir / filename
            expected_name = f"{package_name}-{version}-{platform_name}.{kind}"
            add_check(
                checks,
                f"{platform_name} {kind} archive name is stable",
                filename == expected_name,
                f"{filename} expected {expected_name}",
            )
            if require_file(checks, asset_path, f"{platform_name} {kind} archive exists"):
                actual = sha256_path(asset_path)
                add_check(
                    checks,
                    f"{platform_name} {kind} archive hash matches release.json",
                    actual == asset.get("sha256"),
                    filename,
                )
                add_check(
                    checks,
                    f"{platform_name} {kind} archive hash is in SHA256SUMS",
                    sums.get(filename) == actual,
                    filename,
                )
    return assets


def validate_channels(checks, channel_root, channels_json, base_url, tag, release_assets_by_platform, required_platforms):
    channel_assets = channels_assets(channels_json)
    for platform_name in required_platforms:
        add_check(
            checks,
            f"channels include required platform {platform_name}",
            platform_name in channel_assets,
            "channels.json platform list",
        )

    for platform_name, kinds in sorted(channel_assets.items()):
        release_kinds = release_assets_by_platform.get(platform_name, {})
        for kind, channel_asset in sorted(kinds.items()):
            release_asset = release_kinds.get(kind)
            filename = channel_asset.get("filename")
            add_check(
                checks,
                f"{platform_name} {kind} channel asset matches release asset",
                release_asset is not None and filename == release_asset.get("filename"),
                filename or "",
            )
            add_check(
                checks,
                f"{platform_name} {kind} channel hash matches release asset",
                release_asset is not None and channel_asset.get("sha256") == release_asset.get("sha256"),
                filename or "",
            )
            add_check(
                checks,
                f"{platform_name} {kind} channel URL is immutable release asset",
                channel_asset.get("url") == expected_asset_url(base_url, tag, filename),
                channel_asset.get("url", ""),
            )

    formula_path = channel_root / "homebrew" / "cool.rb"
    if require_file(checks, formula_path, "Homebrew formula exists"):
        text = formula_path.read_text(encoding="utf-8")
        add_check(checks, "Homebrew formula has install test", 'system "#{bin}/cool", "help"' in text)
        for platform_name in ("macos-arm64", "macos-x86_64", "linux-x86_64"):
            asset = release_assets_by_platform.get(platform_name, {}).get("tar.gz")
            if asset:
                add_check(
                    checks,
                    f"Homebrew formula references {platform_name}",
                    expected_asset_url(base_url, tag, asset["filename"]) in text and asset["sha256"] in text,
                    asset["filename"],
                )

    windows_zip = release_assets_by_platform.get("windows-x86_64", {}).get("zip")
    winget_root = channels_json.get("channels", {}).get("winget")
    if windows_zip:
        add_check(checks, "Winget channel path is recorded", winget_root is not None, str(winget_root))
        if winget_root:
            installer_path = channel_root / winget_root / "Codenz.Cool.installer.yaml"
            if require_file(checks, installer_path, "Winget installer manifest exists"):
                text = installer_path.read_text(encoding="utf-8")
                add_check(
                    checks,
                    "Winget manifest references Windows zip URL",
                    expected_asset_url(base_url, tag, windows_zip["filename"]) in text,
                    windows_zip["filename"],
                )
                add_check(
                    checks,
                    "Winget manifest references Windows zip hash",
                    windows_zip["sha256"].upper() in text,
                    windows_zip["filename"],
                )

    linux_tar = release_assets_by_platform.get("linux-x86_64", {}).get("tar.gz")
    debian_package = channels_json.get("channels", {}).get("debian_package")
    debian_index = channels_json.get("channels", {}).get("debian_packages_index")
    if linux_tar:
        add_check(checks, "Debian package path is recorded", debian_package is not None, str(debian_package))
        add_check(checks, "Debian Packages index path is recorded", debian_index is not None, str(debian_index))
        if debian_package:
            require_file(checks, channel_root / debian_package, "Debian package exists")
        if debian_index and require_file(checks, channel_root / debian_index, "Debian Packages index exists"):
            text = (channel_root / debian_index).read_text(encoding="utf-8")
            add_check(checks, "Debian Packages index includes SHA256", "SHA256:" in text)


def write_checklist(path, report):
    lines = [
        f"# Distribution Checklist For Cool {report['package']['version']}",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Required Before Package-Index Submission",
        "",
    ]
    for check in report["checks"]:
        mark = "x" if check["ok"] else " "
        lines.append(f"- [{mark}] {check['name']}")
    lines += [
        "",
        "## Submission Targets",
        "",
        "- Homebrew: submit or update the formula from `dist/channels/<version>/homebrew/cool.rb`.",
        "- Winget: submit manifests from `dist/channels/<version>/winget/Codenz.Cool/<version>/` when a Windows zip exists.",
        "- Debian/apt: publish the generated apt tree or use it as packaging input when a Linux x86_64 tarball exists.",
        "",
        "Use hosted GitHub Release URLs and rerun hosted verification before submitting public package-manager updates.",
        "",
    ]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Audit Cool release assets for public package-channel distribution readiness.")
    parser.add_argument("--version")
    parser.add_argument("--dist-dir", default=str(ROOT / "dist"))
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--tag")
    parser.add_argument("--require-platform", action="append", default=[])
    parser.add_argument("--report")
    parser.add_argument("--write-checklist")
    return parser.parse_args()


def main():
    args = parse_args()
    version = args.version or read_cargo_value("version")
    package_name = read_cargo_value("name")
    tag = args.tag or f"v{version}"
    dist_dir = Path(args.dist_dir).resolve()
    release_dir = dist_dir / "releases" / version
    channel_root = dist_dir / "channels" / version
    release_json_path = release_dir / "release.json"
    channels_json_path = channel_root / "channels.json"
    checks = []

    require_file(checks, release_json_path, "release.json exists")
    require_file(checks, channels_json_path, "channels.json exists")
    if not release_json_path.is_file() or not channels_json_path.is_file():
        fail("release.json and channels.json are required")

    release_json = load_json(release_json_path)
    channels_json = load_json(channels_json_path)
    release_platform = release_json.get("release", {}).get("platform")
    required_platforms = args.require_platform
    if not required_platforms and release_platform not in (None, "", "multi"):
        required_platforms = [release_platform]

    add_check(checks, "release package name matches Cargo.toml", release_json.get("package", {}).get("name") == package_name)
    add_check(checks, "release version matches requested version", release_json.get("package", {}).get("version") == version)
    add_check(checks, "channels package name matches Cargo.toml", channels_json.get("package", {}).get("name") == package_name)
    add_check(checks, "channels version matches requested version", channels_json.get("package", {}).get("version") == version)
    add_check(checks, "channels base URL matches expected host", channels_json.get("release", {}).get("base_url") == args.base_url)
    add_check(checks, "channels tag matches expected tag", channels_json.get("release", {}).get("tag") == tag)

    release_assets_by_platform = validate_release_files(
        checks,
        release_dir,
        package_name,
        version,
        release_json,
        required_platforms,
    )
    validate_channels(checks, channel_root, channels_json, args.base_url, tag, release_assets_by_platform, required_platforms)

    blockers = [check for check in checks if not check["ok"] and check["severity"] == "blocker"]
    warnings = [check for check in checks if not check["ok"] and check["severity"] != "blocker"]
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package": {"name": package_name, "version": version},
        "release": {
            "path": display_path(release_dir),
            "platform": release_platform,
            "required_platforms": required_platforms,
            "tag": tag,
            "base_url": args.base_url,
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

    if args.report:
        write_json(args.report, report)
    if args.write_checklist:
        write_checklist(args.write_checklist, report)

    if blockers:
        for check in blockers:
            print(f"BLOCKER {check['name']}: {check['detail']}", flush=True)
        fail(f"{len(blockers)} blocker(s) found")

    print("distribution readiness: ok")
    print(f"  Version -> {version}")
    print(f"  Checks  -> {report['summary']['passed']}/{report['summary']['checks']} passed")
    if args.report:
        print(f"  Report  -> {display_path(Path(args.report).resolve())}")
    if args.write_checklist:
        print(f"  List    -> {display_path(Path(args.write_checklist).resolve())}")


if __name__ == "__main__":
    main()
