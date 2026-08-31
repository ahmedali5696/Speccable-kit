#!/usr/bin/env python3
"""Clean-room validation evidence harness.

Installs the shipped extension into fresh isolated temp Spec Kit projects via the
real native CLI (`specify extension add`), then exercises the real installed
artifacts (check-compat.ps1, validate-detector.mjs) across the documented layout
matrix. Output is a machine-parseable evidence log used by the acceptance report.

Run: python tests/run_cleanroom.py
Requires: Python 3.11+, Windows PowerShell, the `specify` CLI on PATH.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXT = REPO / "extension"
DETECTOR = """\
import { readFileSync } from 'node:fs';
import path from 'node:path';
const mode = (process.env.DETECT_MODE || 'clean');
let out = [], code = 0, err = '';
if (mode === 'findings') {
  out = [{antipattern:'overused-font',name:'Overused font',description:'Inter everywhere',severity:'warning',category:'slop',file:path.resolve('index.html'),line:3}];
  code = 2;
} else if (mode === 'advisory') { out = [{antipattern:'x',advisory:true}]; }
else if (mode === 'malformed') { process.stdout.write('not json'); process.exit(0); }
else if (mode === 'sleep') { const _b = new SharedArrayBuffer(4); const _a = new Int32Array(_b); Atomics.wait(_a, 0, 0, 5000); }
else if (mode === 'degraded') { err = 'HTML parser modules unavailable - findings are an undercount'; }
process.stdout.write(JSON.stringify(out));
if (err) process.stderr.write(err);
process.exit(code);
"""


def powershell(script: Path, args) -> str:
    if os.name == "nt":
        ps = shutil.which("powershell") or "powershell"
    else:
        ps = shutil.which("pwsh") or shutil.which("powershell") or "pwsh"
    proc = subprocess.run(
        [ps, "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(script), *args],
        capture_output=True, text=True)
    return proc.stdout.strip()


def install_extension(proj: Path) -> None:
    (proj / ".specify").mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / ".specify" / "init-options.json", proj / ".specify")
    shutil.copy(REPO / ".specify" / "integration.json", proj / ".specify")
    (proj / ".specify" / ".gitignore").write_text("", encoding="utf-8")
    proc = subprocess.run(["specify", "extension", "add", str(EXT), "--dev"],
                          cwd=str(proj), capture_output=True, text=True, input="")
    if proc.returncode != 0:
        raise RuntimeError(f"install failed: {(proc.stdout + proc.stderr)[-500:]}")


def write_impeccable(proj: Path, layout: str, version: str, with_detector=True):
    d = proj / layout
    (d / "scripts").mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"name: impeccable\nversion: {version}\n", encoding="utf-8")
    if with_detector:
        (d / "scripts" / "detect.mjs").write_text(DETECTOR, encoding="utf-8")


def check_compat(proj: Path) -> dict:
    line = powershell(EXT / "scripts" / "check-compat.ps1", ["-ProjectRoot", str(proj)])
    return dict(kv.split("=", 1) for kv in line.split("|"))


def validate(proj: Path, mode="clean", timeout_ms=None) -> dict:
    v = proj / ".specify" / "extensions" / "speccable" / "scripts" / "validate-detector.mjs"
    cmd = ["node", str(v), "--project", str(proj), "--target", str(proj)]
    if timeout_ms:
        cmd += ["--timeout", str(timeout_ms)]
    env = dict(os.environ, DETECT_MODE=mode)
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(proj))
    try:
        obj = json.loads(proc.stdout.strip())
    except Exception:
        obj = {"parse_error": proc.stdout.strip()[:200], "rc": proc.returncode}
    return obj


def main():
    results = {}
    # Section 17 / baseline: clean-room install artifact proof.
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        install_extension(proj)
        results["install"] = {
            "scripts": sorted(p.name for p in
                (proj / ".specify/extensions/speccable/scripts").iterdir()),
            "skills": sorted(p.name for p in (proj / ".zcode/skills").iterdir()),
        }

    # Layout matrix (Scenarios A-K / F1).
    layout_cases = [
        ("missing", None, None),
        ("agent-supported", ".agent/skills/impeccable", "4.1.1"),
        ("agents-supported", ".agents/skills/impeccable", "4.1.1"),
        ("claude-supported", ".claude/skills/impeccable", "4.1.1"),
        ("claude-unsupported-major", ".claude/skills/impeccable", "5.0.0"),
        ("claude-malformed-version", ".claude/skills/impeccable", "nonsense"),
        ("claude-no-detector", ".claude/skills/impeccable", "4.1.1", False),
        ("agent-preferred-over-claude",
         (".agent/skills/impeccable", ".claude/skills/impeccable"), "4.1.1"),
    ]
    for name, layout, version, *extra in layout_cases:
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td)
            install_extension(proj)
            if layout is not None:
                if isinstance(layout, tuple):
                    for lay in layout:
                        write_impeccable(proj, lay, version, *(extra or [True,]))
                else:
                    write_impeccable(proj, layout, version, *(extra or [True]))
            comp = check_compat(proj)
            val = validate(proj)
            results[name] = {"compat": comp, "validator": {k: val.get(k) for k in
                ("status", "reason", "layout", "DEGRADED", "primaryFindingsCount")}}

    # Detector execution modes (F2).
    mode_cases = [
        ("clean", "clean"),
        ("findings", "findings"),
        ("advisory", "advisory"),
        ("malformed", "malformed"),
        ("degraded", "degraded"),
    ]
    results["detector_modes"] = {}
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        install_extension(proj)
        write_impeccable(proj, ".claude/skills/impeccable", "4.1.1")
        for label, mode in mode_cases:
            results["detector_modes"][label] = validate(proj, mode)
        # timeout -> NOT_RUN
        results["detector_modes"]["timeout"] = validate(proj, "sleep", timeout_ms=100)

    print("CLEANROOM_EVIDENCE_BEGIN")
    print(json.dumps(results, indent=2))
    print("CLEANROOM_EVIDENCE_END")


if __name__ == "__main__":
    main()
