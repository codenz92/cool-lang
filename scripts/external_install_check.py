#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://github.com/codenz92/cool-lang/releases/download"


def fail(message):
    raise SystemExit(f"external install check: {message}")


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
    import re

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


def tool_check(checks, tool, required):
    path = shutil.which(tool)
    add_check(
        checks,
        f"{tool} command availability",
        bool(path) or not required,
        path or "not found",
        "blocker" if required else "info",
    )
    return path


def channel_paths(channel_root, channels_json):
    channels = channels_json.get("channels", {})
    paths = {
        "homebrew_formula": channels.get("homebrew_formula"),
        "winget": channels.get("winget"),
        "debian_package": channels.get("debian_package"),
        "debian_packages_index": channels.get("debian_packages_index"),
    }
    return {key: (channel_root / value if value else None) for key, value in paths.items()}


def run_hosted_verifier(args, version, tag, checks):
    cmd = [
        "bash",
        "scripts/verify_hosted_release.sh",
        "--version",
        version,
        "--tag",
        tag,
        "--base-url",
        args.base_url,
        "--platform",
        args.platform,
        "--require-trust",
        "--check-channel-archive",
        "--report",
        args.hosted_report,
    ]
    for platform_name in args.require_platform:
        cmd += ["--require-platform", platform_name]
    if args.install_smoke:
        cmd += ["--install-smoke", "--install-smoke-platform", args.install_smoke_platform]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    add_check(
        checks,
        "hosted release verifier passes from external install check",
        proc.returncode == 0,
        (proc.stdout + proc.stderr).strip()[-1000:],
    )


def build_plan(version, tag, base_url, channel_root, paths):
    lines = [
        f"# External Install Verification Plan For Cool {version}",
        "",
        f"Tag: `{tag}`",
        f"Release assets: `{base_url.rstrip('/')}/{tag}/`",
        "",
        "## Direct Hosted Install",
        "",
        "```bash",
        f"bash install.sh --version {version} --verify-metadata",
        "```",
        "",
        "## Package Channels",
        "",
    ]
    formula = paths.get("homebrew_formula")
    if formula:
        lines += [
            "### Homebrew",
            "",
            "```bash",
            f"brew audit --strict --online --formula {display_path(formula)}",
            f"brew install --formula {display_path(formula)}",
            "cool help",
            "```",
            "",
        ]
    winget_root = paths.get("winget")
    if winget_root:
        lines += [
            "### Winget",
            "",
            "```powershell",
            f"winget validate {display_path(winget_root)}",
            f"winget install --manifest {display_path(winget_root)} --accept-source-agreements --accept-package-agreements",
            "cool help",
            "```",
            "",
        ]
    deb = paths.get("debian_package")
    index = paths.get("debian_packages_index")
    if deb and index:
        lines += [
            "### Debian/Apt",
            "",
            "```bash",
            f"dpkg-deb --info {display_path(deb)}",
            f"gzip -dc {display_path(index)}.gz | grep -A8 '^Package: cool$'",
            "sudo apt install ./<published-cool-deb>",
            "cool help",
            "```",
            "",
        ]
    lines += [
        "## Evidence",
        "",
        "- Record direct hosted install output.",
        "- Record package-manager validation output.",
        "- Record package-manager install output after each channel is public.",
    ]
    return "\n".join(lines) + "\n"


def validate(args):
    package_name = read_cargo_value("name")
    version = args.version or read_cargo_value("version")
    tag = args.tag or f"v{version}"
    channel_root = Path(args.channel_root).resolve() if args.channel_root else Path(args.dist_dir).resolve() / "channels" / version
    checks = []

    require_file(checks, ROOT / "install.sh", "root installer exists")
    for rel in ["docs/FIRST_30_MINUTES.md", "docs/ECOSYSTEM_ADOPTION.md", "docs/MAINTENANCE.md", "docs/PACKAGE_MANAGER_SUBMISSIONS.md"]:
        require_file(checks, ROOT / rel, f"{rel} exists")
    channels_path = channel_root / "channels.json"
    paths = {}
    if require_file(checks, channels_path, "channels.json exists for external install planning"):
        channels_json = load_json(channels_path)
        package = channels_json.get("package", {})
        add_check(checks, "channels package name matches", package.get("name") == package_name)
        add_check(checks, "channels package version matches", package.get("version") == version)
        paths = channel_paths(channel_root, channels_json)
        for key, path in paths.items():
            if path is not None:
                require_path(checks, path, f"{key} path exists")

    tool_check(checks, "brew", args.require_homebrew_tool)
    tool_check(checks, "winget", args.require_winget_tool)
    tool_check(checks, "dpkg-deb", args.require_debian_tool)

    if args.run_hosted:
        run_hosted_verifier(args, version, tag, checks)
    else:
        add_check(checks, "hosted verifier execution is explicitly planned", True, "use --run-hosted for public or mirror checks", "info")

    blockers = [check for check in checks if not check["ok"] and check["severity"] == "blocker"]
    warnings = [check for check in checks if not check["ok"] and check["severity"] != "blocker"]
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package": {"name": package_name, "version": version},
        "release": {"tag": tag, "base_url": args.base_url},
        "channel_root": display_path(channel_root),
        "install_plan": {
            "direct_hosted": f"bash install.sh --version {version} --verify-metadata",
            "homebrew_formula": display_path(paths["homebrew_formula"]) if paths.get("homebrew_formula") else None,
            "winget_manifest": display_path(paths["winget"]) if paths.get("winget") else None,
            "debian_package": display_path(paths["debian_package"]) if paths.get("debian_package") else None,
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
    plan = build_plan(version, tag, args.base_url, channel_root, paths)
    return report, blockers, plan


def main():
    parser = argparse.ArgumentParser(description="Validate and record external install verification plans for Cool package channels.")
    parser.add_argument("--version")
    parser.add_argument("--tag")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--platform", default="multi")
    parser.add_argument("--dist-dir", default=str(ROOT / "dist"))
    parser.add_argument("--channel-root")
    parser.add_argument("--require-platform", action="append", default=[])
    parser.add_argument("--report")
    parser.add_argument("--write-plan")
    parser.add_argument("--run-hosted", action="store_true")
    parser.add_argument("--hosted-report", default=str(ROOT / "dist/hosted-validation/external-install-hosted-release.json"))
    parser.add_argument("--install-smoke", action="store_true")
    parser.add_argument("--install-smoke-platform", default="linux-x86_64")
    parser.add_argument("--require-homebrew-tool", action="store_true")
    parser.add_argument("--require-winget-tool", action="store_true")
    parser.add_argument("--require-debian-tool", action="store_true")
    args = parser.parse_args()

    report, blockers, plan = validate(args)
    if args.report:
        write_json(args.report, report)
    if args.write_plan:
        write_text(args.write_plan, plan)
    if blockers:
        for check in blockers:
            print(f"BLOCKER {check['name']}: {check.get('detail', '')}")
        fail(f"{len(blockers)} blocker(s) found")

    print("external install check: ok")
    print(f"  Version -> {report['package']['version']}")
    print(f"  Tag     -> {report['release']['tag']}")
    print(f"  Checks  -> {report['summary']['passed']}/{report['summary']['checks']} passed")
    if args.report:
        print(f"  Report  -> {args.report}")
    if args.write_plan:
        print(f"  Plan    -> {args.write_plan}")


if __name__ == "__main__":
    main()
