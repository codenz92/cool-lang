#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
VALID_STATUSES = {"ready", "submitted", "published", "blocked", "deferred"}
STATUS_RANK = {
    "ready": 0,
    "submitted": 1,
    "published": 2,
    "blocked": -1,
    "deferred": -1,
}
CHANNELS = {
    "homebrew": {
        "label": "Homebrew",
        "verification": "brew audit",
        "official_refs": [
            "https://docs.brew.sh/Formula-Cookbook",
            "https://docs.brew.sh/Acceptable-Formulae",
        ],
    },
    "winget": {
        "label": "Winget",
        "verification": "winget validate",
        "official_refs": [
            "https://learn.microsoft.com/en-us/windows/package-manager/package/manifest",
            "https://learn.microsoft.com/en-us/windows/package-manager/package/repository",
        ],
    },
    "debian": {
        "label": "Debian/apt",
        "verification": "dpkg-deb",
        "official_refs": [
            "https://www.debian.org/doc/debian-policy/",
            "https://www.debian.org/doc/debian-policy/ch-controlfields.html",
        ],
    },
}


def fail(message):
    raise SystemExit(f"package publication check: {message}")


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


def is_https_url(value):
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def is_date_or_datetime(value):
    if not isinstance(value, str) or not value:
        return False
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return True
    return bool(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value))


def public_install_command(record):
    return record.get("public_install_command") or record.get("install_command") or ""


def required_status_met(actual, required):
    if required == "submitted":
        return actual in {"submitted", "published"}
    if required == "published":
        return actual == "published"
    return actual == required


def parse_required_status(values):
    required = {}
    for value in values:
        if "=" not in value:
            fail(f"--require-status expects CHANNEL=STATUS, got {value}")
        channel, status = value.split("=", 1)
        channel = channel.strip()
        status = status.strip()
        if channel not in CHANNELS:
            fail(f"unknown publication channel: {channel}")
        if status not in VALID_STATUSES:
            fail(f"unknown publication status for {channel}: {status}")
        required[channel] = status
    return required


def channel_summary(record):
    return {
        "status": record.get("status"),
        "source": record.get("source", ""),
        "submission_url": record.get("submission_url", ""),
        "published_url": record.get("published_url", ""),
        "public_install_command": public_install_command(record),
        "external_install_report": record.get("external_install_report", ""),
        "blockers": record.get("blockers", []),
    }


def validate_docs(checks):
    publication_doc = ROOT / "docs/PACKAGE_PUBLICATION.md"
    status_file = ROOT / "docs/PACKAGE_SUBMISSION_STATUS.json"
    for path in [
        publication_doc,
        ROOT / "docs/ECOSYSTEM_ADOPTION.md",
        ROOT / "docs/PACKAGE_MANAGER_SUBMISSIONS.md",
        ROOT / "docs/MAINTENANCE.md",
        status_file,
    ]:
        require_file(checks, path, f"{display_path(path)} exists")
    for needle in [
        "Phase 30",
        "package publication",
        "submitted",
        "published",
        "external install",
        "package_publication_check.sh",
    ]:
        check_contains(checks, publication_doc, needle, f"publication docs include {needle}")
    for channel, meta in CHANNELS.items():
        for ref in meta["official_refs"]:
            check_contains(checks, publication_doc, ref, f"publication docs include {channel} official reference")


def validate_channel(checks, channel, record, policy, required_status, args):
    meta = CHANNELS[channel]
    label = meta["label"]
    status = record.get("status")
    add_check(checks, f"{label} status value is valid", status in VALID_STATUSES, str(status))
    add_check(checks, f"{label} source path is recorded", bool(record.get("source")), record.get("source", ""))
    add_check(checks, f"{label} verification command is recorded", bool(record.get("verification")), record.get("verification", ""))
    if record.get("verification"):
        add_check(
            checks,
            f"{label} verification command names expected tool",
            meta["verification"] in record.get("verification", ""),
            record.get("verification", ""),
        )
    if args.require_sources_exist and record.get("source"):
        source_path = ROOT / record["source"]
        add_check(checks, f"{label} source path exists", source_path.exists(), display_path(source_path))

    refs = policy.get("official_references", {}).get(channel, [])
    for ref in meta["official_refs"]:
        add_check(checks, f"{label} official reference is tracked", ref in refs, ref)

    if required_status:
        add_check(
            checks,
            f"{label} status satisfies required {required_status}",
            required_status_met(status, required_status),
            f"actual={status}",
        )

    if status in {"submitted", "published"}:
        add_check(checks, f"{label} submission URL is recorded", is_https_url(record.get("submission_url")), record.get("submission_url", ""))
        add_check(checks, f"{label} submitted_at is recorded", is_date_or_datetime(record.get("submitted_at")), record.get("submitted_at", ""))

    if status == "published":
        install_command = public_install_command(record)
        add_check(checks, f"{label} published URL is recorded", is_https_url(record.get("published_url")), record.get("published_url", ""))
        add_check(checks, f"{label} public install command is recorded", bool(install_command), install_command)
        add_check(checks, f"{label} published_at is recorded", is_date_or_datetime(record.get("published_at")), record.get("published_at", ""))
        add_check(checks, f"{label} verified_at is recorded", is_date_or_datetime(record.get("verified_at")), record.get("verified_at", ""))
        if args.require_external_evidence:
            add_check(
                checks,
                f"{label} external install report is recorded",
                bool(record.get("external_install_report")),
                record.get("external_install_report", ""),
            )

    if status in {"blocked", "deferred"}:
        blockers = record.get("blockers", [])
        add_check(checks, f"{label} blocker/deferred status has notes", bool(record.get("notes") or blockers), str(record))


def validate(args):
    package_name = read_cargo_value("name")
    version = args.version or read_cargo_value("version")
    checks = []

    validate_docs(checks)
    status_path = Path(args.status_file).resolve()
    status = {}
    if require_file(checks, status_path, "package publication status file exists"):
        status = load_json(status_path)
    schema_version = status.get("schema_version")
    add_check(checks, "publication status schema version supports Phase 30", schema_version in {2, 3}, str(schema_version))
    package = status.get("package", {})
    add_check(checks, "publication status package name matches", package.get("name") == package_name, package.get("name", ""))
    add_check(checks, "publication status current release matches", package.get("current_release") == version, package.get("current_release", ""))
    add_check(checks, "publication status updated_at is recorded", is_date_or_datetime(status.get("updated_at")), status.get("updated_at", ""))

    policy = status.get("policy", {})
    accepted = set(policy.get("accepted_statuses", []))
    add_check(checks, "publication policy records accepted statuses", VALID_STATUSES.issubset(accepted), sorted(accepted))
    add_check(checks, "publication policy requires immutable assets", policy.get("immutable_assets_required") is True)

    required = parse_required_status(args.require_status)
    for channel in args.require_published:
        required[channel] = "published"
    for channel in args.require_submitted:
        required[channel] = "submitted"
    if args.require_all_published:
        for channel in CHANNELS:
            required[channel] = "published"

    requested_channels = args.require_channel or list(CHANNELS)
    channels = status.get("channels", {})
    summaries = {}
    for channel in requested_channels:
        record = channels.get(channel)
        add_check(checks, f"{channel} publication record exists", isinstance(record, dict), channel)
        if isinstance(record, dict):
            validate_channel(checks, channel, record, policy, required.get(channel), args)
            summaries[channel] = channel_summary(record)
            if schema_version == 3:
                add_check(checks, f"{channel} review status is tracked", bool(record.get("review_status")), record.get("review_status", ""))
                add_check(checks, f"{channel} submission packet is tracked", bool(record.get("submission_packet")), record.get("submission_packet", ""))

    blockers = [check for check in checks if not check["ok"] and check["severity"] == "blocker"]
    warnings = [check for check in checks if not check["ok"] and check["severity"] != "blocker"]
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package": {"name": package_name, "version": version},
        "status_file": display_path(status_path),
        "status_schema_version": schema_version,
        "required_status": required,
        "channels": summaries,
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


def write_evidence(path, report):
    version = report["package"]["version"]
    lines = [
        f"# Package Publication Evidence For Cool {version}",
        "",
        f"Generated: {report['generated_at']}",
        f"Status file: `{report['status_file']}`",
        "",
        "## Channel Status",
        "",
        "| Channel | Status | Submission | Publication | Install | Evidence |",
        "| ------- | ------ | ---------- | ----------- | ------- | -------- |",
    ]
    for channel, record in report["channels"].items():
        lines.append(
            "| {channel} | {status} | {submission} | {published} | {install} | {evidence} |".format(
                channel=channel,
                status=record.get("status") or "",
                submission=record.get("submission_url") or "",
                published=record.get("published_url") or "",
                install=(record.get("public_install_command") or "").replace("|", "\\|"),
                evidence=record.get("external_install_report") or "",
            )
        )
    lines += [
        "",
        "## Automated Checks",
        "",
    ]
    for check in report["checks"]:
        mark = "x" if check["ok"] else " "
        lines.append(f"- [{mark}] {check['name']}")
    lines += [
        "",
        "## Evidence Rules",
        "",
        "- `ready` means the generated metadata passed local validation and has not been submitted.",
        "- `submitted` requires a package-index pull request, issue, or review URL plus `submitted_at`.",
        "- `published` requires a public package page, public install command, publication date, verification date, and external install report.",
        "- `blocked` or `deferred` requires a short note or blocker entry.",
    ]
    write_text(path, "\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Validate Cool package-manager publication status and evidence.")
    parser.add_argument("--version")
    parser.add_argument("--status-file", default=str(ROOT / "docs/PACKAGE_SUBMISSION_STATUS.json"))
    parser.add_argument("--require-channel", action="append", choices=sorted(CHANNELS), default=[])
    parser.add_argument("--require-status", action="append", default=[], metavar="CHANNEL=STATUS")
    parser.add_argument("--require-submitted", action="append", choices=sorted(CHANNELS), default=[])
    parser.add_argument("--require-published", action="append", choices=sorted(CHANNELS), default=[])
    parser.add_argument("--require-all-published", action="store_true")
    parser.add_argument("--require-external-evidence", action="store_true")
    parser.add_argument("--require-sources-exist", action="store_true")
    parser.add_argument("--report")
    parser.add_argument("--write-evidence")
    args = parser.parse_args()

    report, blockers = validate(args)
    if args.report:
        write_json(args.report, report)
    if args.write_evidence:
        write_evidence(args.write_evidence, report)
    if blockers:
        for check in blockers:
            print(f"BLOCKER {check['name']}: {check.get('detail', '')}")
        fail(f"{len(blockers)} blocker(s) found")

    print("package publication check: ok")
    print(f"  Version -> {report['package']['version']}")
    print(f"  Checks  -> {report['summary']['passed']}/{report['summary']['checks']} passed")
    if args.report:
        print(f"  Report  -> {args.report}")
    if args.write_evidence:
        print(f"  Evidence -> {args.write_evidence}")


if __name__ == "__main__":
    main()
