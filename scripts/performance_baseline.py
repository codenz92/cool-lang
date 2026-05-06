#!/usr/bin/env python3
import argparse
import json
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(message):
    raise SystemExit(f"performance baseline: {message}")


def read_cargo_value(key):
    text = (ROOT / "Cargo.toml").read_text(encoding="utf-8")
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\"([^\"]+)\"", text)
    if not match:
        fail(f"could not read {key} from Cargo.toml")
    return match.group(1)


def git_value(*args):
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def display_path(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_duration(raw):
    return raw.strip()


def parse_summary(output):
    rows = []
    in_summary = False
    pattern = re.compile(
        r"^(?P<workload>[a-zA-Z0-9_]+)\s+"
        r"(?P<cool_mean>[0-9.]+(?:ms|s))\s+"
        r"(?P<rust_mean>[0-9.]+(?:ms|s))\s+"
        r"(?P<cool_compile>[0-9.]+(?:ms|s))\s+"
        r"(?P<rust_compile>[0-9.]+(?:ms|s))\s+"
        r"(?P<ratio>[0-9.]+)x$"
    )
    for line in output.splitlines():
        if line.strip() == "Summary":
            in_summary = True
            continue
        if not in_summary:
            continue
        match = pattern.match(line.strip())
        if not match:
            continue
        row = match.groupdict()
        row["ratio"] = float(row["ratio"])
        for key in ("cool_mean", "rust_mean", "cool_compile", "rust_compile"):
            row[key] = normalize_duration(row[key])
        rows.append(row)
    return rows


def parse_args():
    parser = argparse.ArgumentParser(description="Record a reproducible maintainer performance baseline.")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--filter")
    parser.add_argument("--output-dir")
    parser.add_argument("--report-name", default="benchmark-baseline")
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--keep-build", action="store_true", help="Keep benchmarks/build after the run for inspection.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.runs < 1:
        fail("--runs must be at least 1")
    if args.warmups < 0:
        fail("--warmups must be 0 or greater")

    version = read_cargo_value("version")
    output_dir = Path(args.output_dir) if args.output_dir else ROOT / "dist" / "performance" / version
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / f"{args.report_name}.txt"
    report_path = output_dir / f"{args.report_name}.json"

    command = [
        "cargo",
        "run",
        "--release",
        "--bin",
        "bench_compare",
        "--",
        "--runs",
        str(args.runs),
        "--warmups",
        str(args.warmups),
    ]
    if args.filter:
        command.extend(["--filter", args.filter])

    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=args.timeout,
            check=False,
        )
    finally:
        if not args.keep_build:
            shutil.rmtree(ROOT / "benchmarks" / "build", ignore_errors=True)
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path = None
    if completed.stderr:
        stderr_path = output_dir / f"{args.report_name}.stderr.txt"
        stderr_path.write_text(completed.stderr, encoding="utf-8")

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package": {"name": "cool", "version": version},
        "git": {
            "commit": git_value("rev-parse", "HEAD"),
            "dirty": bool(git_value("status", "--short")),
        },
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "command": command,
        "runs": args.runs,
        "warmups": args.warmups,
        "filter": args.filter,
        "status": {
            "returncode": completed.returncode,
            "ok": completed.returncode == 0,
        },
        "stdout": display_path(stdout_path),
        "stderr": display_path(stderr_path) if stderr_path else None,
        "summary": parse_summary(completed.stdout),
    }
    write_json(report_path, report)

    if completed.returncode != 0:
        fail(f"benchmark command failed with exit code {completed.returncode}; see {display_path(stdout_path)}")

    print("performance baseline: ok")
    print(f"  Output -> {display_path(stdout_path)}")
    print(f"  Report -> {display_path(report_path)}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.TimeoutExpired as exc:
        fail(f"benchmark command timed out after {exc.timeout}s")
