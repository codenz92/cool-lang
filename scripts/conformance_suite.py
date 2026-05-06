#!/usr/bin/env python3
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALID_MODES = ("interpreter", "vm", "native")


def fail(message):
    raise SystemExit(f"conformance suite: {message}")


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
    prefix = f'{key} = "'
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix) and stripped.endswith('"'):
            return stripped[len(prefix):-1]
    fail(f"could not read {key} from Cargo.toml")


def default_cool_bin():
    env_bin = os.environ.get("COOL_BIN")
    if env_bin:
        return Path(env_bin)
    name = "cool.exe" if platform.system().lower().startswith("win") else "cool"
    return ROOT / "target" / "debug" / name


def ensure_cool_bin(path):
    path = Path(path)
    if path.is_file():
        return path
    subprocess.run(["cargo", "build", "--bin", "cool"], cwd=ROOT, check=True)
    if not path.is_file():
        fail(f"cool binary not found after build: {path}")
    return path


def normalize_text(raw):
    return raw.decode("utf-8", errors="replace").replace("\r\n", "\n")


def run_command(args, timeout, cwd=ROOT):
    try:
        output = subprocess.run(
            [str(arg) for arg in args],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "returncode": None,
            "stdout": normalize_text(exc.stdout or b""),
            "stderr": normalize_text(exc.stderr or b""),
            "command": [str(arg) for arg in args],
        }

    return {
        "status": "completed",
        "returncode": output.returncode,
        "stdout": normalize_text(output.stdout),
        "stderr": normalize_text(output.stderr),
        "command": [str(arg) for arg in args],
    }


def runtime_command(cool_bin, mode, source):
    if mode == "interpreter":
        return [cool_bin, source]
    if mode == "vm":
        return [cool_bin, "--vm", source]
    fail(f"unknown runtime mode: {mode}")


def copy_native_source(source, case_name, work_root):
    case_dir = work_root / case_name
    case_dir.mkdir(parents=True, exist_ok=True)
    target = case_dir / source.name
    shutil.copy2(source, target)
    return target


def run_native_case(cool_bin, source, case_name, timeout, work_root):
    native_source = copy_native_source(source, case_name, work_root)
    build = run_command([cool_bin, "build", "--emit", "binary", native_source], timeout)
    binary = native_source.with_suffix("")
    if platform.system().lower().startswith("win"):
        binary = binary.with_suffix(".exe")
    if build["status"] != "completed" or build["returncode"] != 0:
        build["phase"] = "build"
        return build
    run = run_command([binary], timeout, cwd=native_source.parent)
    run["build_stdout"] = build["stdout"]
    run["build_stderr"] = build["stderr"]
    return run


def validate_runtime_case(case, cool_bin, modes, timeout, work_root):
    name = case["name"]
    source = ROOT / case["path"]
    if not source.is_file():
        fail(f"runtime case source missing: {case['path']}")
    expected_stdout = case.get("expected_stdout")
    if expected_stdout is None:
        fail(f"runtime case {name} is missing expected_stdout")

    case_modes = [mode for mode in case.get("modes", modes) if mode in modes]
    if not case_modes:
        fail(f"runtime case {name} has no selected modes")

    results = {}
    baseline_stdout = None
    errors = []
    for mode in case_modes:
        if mode == "native":
            result = run_native_case(cool_bin, source, name, timeout, work_root)
        else:
            result = run_command(runtime_command(cool_bin, mode, source), timeout)
        results[mode] = result

        if result["status"] != "completed":
            errors.append(f"{name} [{mode}] timed out")
            continue
        if result["returncode"] != 0:
            errors.append(f"{name} [{mode}] exited with {result['returncode']}\n{result['stderr']}")
            continue
        if result["stdout"] != expected_stdout:
            errors.append(
                f"{name} [{mode}] stdout mismatch\nexpected:\n{expected_stdout}actual:\n{result['stdout']}"
            )
            continue
        if baseline_stdout is None:
            baseline_stdout = result["stdout"]
        elif result["stdout"] != baseline_stdout:
            errors.append(f"{name} [{mode}] diverged from earlier runtime output")

    return {
        "name": name,
        "path": case["path"],
        "kind": "runtime",
        "modes": case_modes,
        "passed": not errors,
        "errors": errors,
        "results": results,
    }


def check_command(cool_bin, case):
    command = [cool_bin, "check"]
    if case.get("strict", False):
        command.append("--strict")
    command.append(ROOT / case["path"])
    return command


def contains_all(text, needles):
    return [needle for needle in needles or [] if needle not in text]


def validate_check_case(case, cool_bin, timeout):
    name = case["name"]
    source = ROOT / case["path"]
    if not source.is_file():
        fail(f"check case source missing: {case['path']}")

    result = run_command(check_command(cool_bin, case), timeout)
    expected_status = case.get("expected_status", "pass")
    errors = []

    if result["status"] != "completed":
        errors.append(f"{name} timed out")
    elif expected_status == "pass" and result["returncode"] != 0:
        errors.append(f"{name} expected check pass, got exit {result['returncode']}\n{result['stderr']}")
    elif expected_status == "fail" and result["returncode"] == 0:
        errors.append(f"{name} expected check failure, got success")
    elif expected_status not in ("pass", "fail"):
        errors.append(f"{name} has invalid expected_status {expected_status!r}")

    missing_stdout = contains_all(result.get("stdout", ""), case.get("stdout_contains"))
    missing_stderr = contains_all(result.get("stderr", ""), case.get("stderr_contains"))
    if missing_stdout:
        errors.append(f"{name} stdout missing expected text: {', '.join(missing_stdout)}")
    if missing_stderr:
        errors.append(f"{name} stderr missing expected text: {', '.join(missing_stderr)}")

    return {
        "name": name,
        "path": case["path"],
        "kind": "check",
        "passed": not errors,
        "errors": errors,
        "result": result,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Run Cool's post-1.0 compatibility conformance suite.")
    parser.add_argument("--manifest", default=str(ROOT / "conformance" / "manifest.json"))
    parser.add_argument("--cool-bin", default=str(default_cool_bin()))
    parser.add_argument("--mode", action="append", choices=VALID_MODES)
    parser.add_argument("--skip-native", action="store_true")
    parser.add_argument("--case", action="append", dest="cases", help="Run one named runtime or check case.")
    parser.add_argument("--runtime-only", action="store_true")
    parser.add_argument("--checks-only", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--report")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--keep-temp", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.runtime_only and args.checks_only:
        fail("choose either --runtime-only or --checks-only, not both")

    manifest_path = Path(args.manifest)
    manifest = load_json(manifest_path)
    runtime_cases = manifest.get("runtime_cases", [])
    check_cases = manifest.get("check_cases", [])

    if args.list:
        for case in runtime_cases:
            print(f"runtime {case['name']}: {case['path']}")
        for case in check_cases:
            print(f"check   {case['name']}: {case['path']}")
        return

    modes = args.mode or manifest.get("runtime_modes", list(VALID_MODES))
    modes = [mode for mode in modes if mode in VALID_MODES]
    if args.skip_native:
        modes = [mode for mode in modes if mode != "native"]
    if not modes and not args.checks_only:
        fail("no runtime modes selected")

    if args.cases:
        wanted = set(args.cases)
        known = {case.get("name") for case in runtime_cases} | {case.get("name") for case in check_cases}
        missing = sorted(wanted - known)
        if missing:
            fail("unknown case(s): " + ", ".join(missing))
        runtime_cases = [case for case in runtime_cases if case.get("name") in wanted]
        check_cases = [case for case in check_cases if case.get("name") in wanted]
    if args.runtime_only:
        check_cases = []
    if args.checks_only:
        runtime_cases = []
    if not runtime_cases and not check_cases:
        fail("no cases selected")

    cool_bin = ensure_cool_bin(args.cool_bin).resolve()
    temp_dir = tempfile.TemporaryDirectory(prefix="cool-conformance.")
    work_root = Path(temp_dir.name)
    try:
        results = []
        for case in runtime_cases:
            print(f"==> runtime {case['name']} [{', '.join(modes)}]")
            results.append(validate_runtime_case(case, cool_bin, modes, args.timeout, work_root))
        for case in check_cases:
            print(f"==> check {case['name']}")
            results.append(validate_check_case(case, cool_bin, args.timeout))

        failures = [result for result in results if not result["passed"]]
        report = {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "package": {"name": "cool", "version": read_cargo_value("version")},
            "manifest": display_path(manifest_path),
            "cool_bin": str(cool_bin),
            "runtime_modes": modes,
            "summary": {
                "case_count": len(results),
                "passed": len(results) - len(failures),
                "failed": len(failures),
            },
            "cases": results,
        }
        if args.report:
            write_json(args.report, report)

        if failures:
            for result in failures:
                for error in result["errors"]:
                    print(error, file=sys.stderr)
            fail(f"{len(failures)} case(s) failed")

        print(f"conformance suite: ok ({len(results)} case(s))")
        if args.report:
            print(f"  Report -> {display_path(Path(args.report).resolve())}")
    finally:
        if args.keep_temp:
            print(f"  Temp   -> {work_root}")
        else:
            temp_dir.cleanup()


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        fail(f"command failed with exit code {exc.returncode}: {' '.join(map(str, exc.cmd))}")
