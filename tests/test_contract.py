# Speccable-kit contract tests.
#
# Run: python tests/test_contract.py
# Requires: Python 3.11+, PowerShell (for the .ps1 scripts), and the extension
# source under extension/ (this repo).
#
# These tests exercise the deterministic contract surface: the UI Impact
# reader/classifier script, the compatibility check script, the tolerant
# detector-output parser, the extension manifest structure, the hook
# declarations, and the architectural boundary invariants.

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - optional dev dependency
    yaml = None

HAS_YAML = yaml is not None

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REAL_FINDING = {
    "antipattern": "overused-font",
    "name": "Overused font",
    "description": "Inter ... no longer distinctive.",
    "severity": "warning",
    "category": "slop",
    "file": "C:\\proj\\index.html",
    "line": 3,
    "snippet": "font-family: Inter",
}

# ---------------------------------------------------------------------------
# Tolerant detector parser (the contract under test)
# ---------------------------------------------------------------------------
# The detector JSON schema is not an immutable semantic API. This parser
# enforces the tolerance rules: ignore unknown fields, tolerate unknown
# severity/category values, preserve useful info when optional fields are
# missing, never crash on extra fields, and fail explicitly (NOT_RUN) only when
# the result is structurally unusable.

VALID_STATUSES = {"PASS", "FAIL", "NOT_RUN"}


def parse_detector_output(stdout: str) -> tuple[str, list[dict], str]:
    """Return (status, findings, reason).

    status is one of PASS/FAIL/NOT_RUN. NOT_RUN is used for unusable output and
    is never equal to PASS.
    """
    if stdout is None or (isinstance(stdout, str) and not stdout.strip()):
        return "NOT_RUN", [], "malformed-output"
    try:
        data = json.loads(stdout)
    except (ValueError, TypeError):
        return "NOT_RUN", [], "malformed-output"
    if not isinstance(data, list):
        return "NOT_RUN", [], "malformed-output"
    findings = []
    for item in data:
        if not isinstance(item, dict):
            # Tolerate stray non-object array elements? No: a non-object element
            # makes the overall result structurally unreliable, but we can skip
            # it rather than crash. The contract says avoid crashes caused by
            # additional fields; a non-dict entry is not a valid finding, so we
            # skip it and still treat the rest as usable.
            continue
        # Preserve useful info when optional fields are missing; ignore unknowns.
        findings.append(item)
    if findings:
        # Advisory-only findings do not represent FAIL.
        primary = [f for f in findings if not f.get("advisory")]
        if primary:
            return "FAIL", findings, "findings"
        return "PASS", findings, "clean"
    return "PASS", [], "clean"


# ---------------------------------------------------------------------------
# Shim for invoking UI-impact / check-compat PowerShell scripts
# ---------------------------------------------------------------------------

def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _powershell_cmd() -> str:
    """Return the PowerShell executable to use.

    On Windows that is the bundled `powershell` (5.1). Elsewhere we require PowerShell Core
    and fall back to `pwsh` if `powershell` is not on PATH, so the same suite can exercise the
    .ps1 scripts on non-Windows CI. Resolution is manual and conservative: if neither is on
    PATH the subprocess call will fail and the test reports the error honestly.
    """
    if os.name == "nt":
        return shutil.which("powershell") or "powershell"
    return shutil.which("pwsh") or shutil.which("powershell") or "pwsh"


def run_ps(script_rel: Path, args: list[str]) -> str:
    script = repo_root() / script_rel
    cmd = [
        _powershell_cmd(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        *args,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.stdout.strip()


def parse_kv(line: str) -> dict[str, str]:
    out = {}
    for part in line.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestUiImpactScript(unittest.TestCase):
    """Contract tests for the UI Impact reader/classifier script."""

    def write_spec(self, content: str) -> str:
        d = tempfile.mkdtemp()
        p = Path(d) / "spec.md"
        p.write_text(content, encoding="utf-8")
        return str(p)

    def read(self, content: str) -> dict[str, str]:
        line = run_ps(Path("extension/scripts/ui-impact.ps1"), ["-SpecFile", self.write_spec(content)])
        return parse_kv(line)

    def test_valid_none(self):
        r = self.read("# F\n\n**UI Impact**: none\n")
        self.assertEqual(r["UI_IMPACT"], "none")
        self.assertEqual(r["MATCH"], "preserved")

    def test_valid_direct(self):
        r = self.read("# F\n\n**UI Impact**: direct\n")
        self.assertEqual(r["UI_IMPACT"], "direct")

    def test_missing_marker(self):
        r = self.read("# F\n\nNo impact marker here.\n")
        self.assertEqual(r["UI_IMPACT"], "unclassified")
        self.assertEqual(r["MATCH"], "none")

    def test_invalid_value(self):
        r = self.read("# F\n\n**UI Impact**: maybe\n")
        self.assertEqual(r["UI_IMPACT"], "invalid")
        self.assertEqual(r["MATCH"], "mismatch")

    def test_empty_value_is_invalid_not_unclassified(self):
        r = self.read("# F\n\n**UI Impact**:\n")
        self.assertEqual(r["UI_IMPACT"], "invalid")
        self.assertEqual(r["MATCH"], "empty")

    def test_duplicate_marker(self):
        r = self.read("# F\n\n**UI Impact**: direct\n**UI Impact**: none\n")
        self.assertEqual(r["UI_IMPACT"], "invalid")
        self.assertEqual(r["MATCH"], "duplicate")

    def test_case_insensitive_value(self):
        r = self.read("# F\n\n**UI Impact**: DIRECT\n")
        self.assertEqual(r["UI_IMPACT"], "direct")

    def test_marker_inside_fenced_markdown_ignored(self):
        # AR-004: a marker inside a fenced code block is example text, not metadata.
        r = self.read("# F\n\n```markdown\n**UI Impact**: direct\n```\n")
        self.assertEqual(r["UI_IMPACT"], "unclassified")
        self.assertEqual(r["MATCH"], "none")

    def test_marker_inside_multiple_fences_ignored(self):
        r = self.read("# F\n```\na\n```\nbody\n```\nb\n```\n\n**UI Impact**: none\n")
        self.assertEqual(r["UI_IMPACT"], "none")
        self.assertEqual(r["MATCH"], "preserved")

    def test_fenced_example_plus_real_marker_real_wins(self):
        r = self.read("# F\n```\n**UI Impact**: direct\n```\n\n**UI Impact**: none\n")
        self.assertEqual(r["UI_IMPACT"], "none")
        self.assertEqual(r["MATCH"], "preserved")

    def test_duplicate_real_markers_outside_fence_invalid(self):
        r = self.read("# F\n\n**UI Impact**: direct\n**UI Impact**: direct\n")
        self.assertEqual(r["UI_IMPACT"], "invalid")
        self.assertEqual(r["MATCH"], "duplicate")

    def test_fenced_only_marker_then_real_duplicate_counts_real(self):
        # Two real markers outside fences -> duplicate, even with examples inside fences.
        r = self.read("# F\n```\n**UI Impact**: none\n```\n**UI Impact**: direct\n**UI Impact**: none\n")
        self.assertEqual(r["UI_IMPACT"], "invalid")
        self.assertEqual(r["MATCH"], "duplicate")

    def test_spec_not_found(self):
        line = run_ps(Path("extension/scripts/ui-impact.ps1"), ["-SpecFile", "C:/nonexistent/x.js"])
        r = parse_kv(line)
        self.assertEqual(r["UI_IMPACT"], "unclassified")
        self.assertEqual(r["ERROR"], "spec-not-found")


class TestCheckCompatScript(unittest.TestCase):
    """Contract tests for the compatibility script, including SUPPORTED range evaluation and
    the shared multi-layout resolver (.agent / .agents / .claude)."""

    def write_impeccable(self, root, version, layout=".agent", with_detector=True):
        """Write a skill layout under root with the given SKILL.md version.
        layout is a relative root under root, e.g. ".agent/skills/impeccable"."""
        d = Path(root) / Path(layout)
        (d / "scripts").mkdir(parents=True)
        (d / "SKILL.md").write_text(f"name: impeccable\nversion: {version}\n", encoding="utf-8")
        if with_detector:
            (d / "scripts" / "detect.mjs").write_text("", encoding="utf-8")

    def run_compat(self, project_root):
        line = run_ps(
            Path("extension/scripts/check-compat.ps1"),
            ["-ProjectRoot", project_root],
        )
        return parse_kv(line)

    def test_reports_repo_impeccable(self):
        # In this repo Impeccable is installed; capability must be reported present.
        r = self.run_compat(str(repo_root()))
        self.assertEqual(r["IMPECCABLE"], "present")
        self.assertEqual(r["DETECTOR"], "present")
        # The repo's skill version must be a supported 4.x on (>=4.1 <5.0).
        ver = r["VERSION"]
        self.assertTrue(re.match(r"^4\.(?!0\.)", ver), f"unexpected version {ver}")
        self.assertEqual(r["SUPPORTED"], "supported")

    def test_missing_impeccable_reports_missing(self):
        d = tempfile.mkdtemp()
        r = self.run_compat(d)
        self.assertEqual(r["IMPECCABLE"], "missing")
        self.assertEqual(r["SUPPORTED"], "missing")
        self.assertEqual(r["DETECTOR"], "missing")
        self.assertEqual(r["LAYOUT"], "none")

    # --- F1 layout discovery (shared resolver) ---
    def test_layout_agent_only_detected(self):
        d = tempfile.mkdtemp()
        self.write_impeccable(d, "4.1.1", layout=".agent/skills/impeccable")
        r = self.run_compat(d)
        self.assertEqual(r["IMPECCABLE"], "present")
        self.assertEqual(r["LAYOUT"], ".agent/skills/impeccable")

    def test_layout_agents_only_detected(self):
        d = tempfile.mkdtemp()
        self.write_impeccable(d, "4.1.1", layout=".agents/skills/impeccable")
        r = self.run_compat(d)
        self.assertEqual(r["IMPECCABLE"], "present")
        self.assertEqual(r["LAYOUT"], ".agents/skills/impeccable")

    def test_layout_claude_only_detected(self):
        d = tempfile.mkdtemp()
        self.write_impeccable(d, "4.1.1", layout=".claude/skills/impeccable")
        r = self.run_compat(d)
        self.assertEqual(r["IMPECCABLE"], "present")
        self.assertEqual(r["LAYOUT"], ".claude/skills/impeccable")
        self.assertEqual(r["SUPPORTED"], "supported")

    def test_layout_preference_agent_over_agents(self):
        d = tempfile.mkdtemp()
        self.write_impeccable(d, "4.1.1", layout=".agent/skills/impeccable")
        self.write_impeccable(d, "4.1.1", layout=".agents/skills/impeccable")
        self.assertEqual(self.run_compat(d)["LAYOUT"], ".agent/skills/impeccable")

    def test_layout_preference_agent_over_claude(self):
        d = tempfile.mkdtemp()
        self.write_impeccable(d, "4.1.1", layout=".agent/skills/impeccable")
        self.write_impeccable(d, "4.1.1", layout=".claude/skills/impeccable")
        self.assertEqual(self.run_compat(d)["LAYOUT"], ".agent/skills/impeccable")

    def test_layout_preference_agents_over_claude(self):
        d = tempfile.mkdtemp()
        self.write_impeccable(d, "4.1.1", layout=".agents/skills/impeccable")
        self.write_impeccable(d, "4.1.1", layout=".claude/skills/impeccable")
        self.assertEqual(self.run_compat(d)["LAYOUT"], ".agents/skills/impeccable")

    def test_layout_all_three_prefers_agent(self):
        d = tempfile.mkdtemp()
        for lay in (".agent/skills/impeccable", ".agents/skills/impeccable", ".claude/skills/impeccable"):
            self.write_impeccable(d, "4.1.1", layout=lay)
        self.assertEqual(self.run_compat(d)["LAYOUT"], ".agent/skills/impeccable")

    def _assert_supported(self, version, expected):
        d = tempfile.mkdtemp()
        self.write_impeccable(d, version, layout=".claude/skills/impeccable")
        r = self.run_compat(d)
        self.assertEqual(r["SUPPORTED"], expected, f"version {version!r}")
        return r

    def test_supported_4_1_x(self):
        self._assert_supported("4.1.1", "supported")

    def test_supported_4_x_line(self):
        # A 4-series version with no decipherable minor is treated as supported (4.x).
        self._assert_supported("4", "supported")
        self._assert_supported("4.x", "supported")

    def test_unsupported_4_0_x(self):
        self._assert_supported("4.0.3", "unsupported")

    def test_unsupported_5_x_and_above(self):
        self._assert_supported("5.0.0", "unsupported")
        self._assert_supported("5.1", "unsupported")

    def test_unsupported_below_4(self):
        self._assert_supported("3.9", "unsupported")

    def test_malformed_version_fails_closed(self):
        # Present-but-malformed must never be reported supported.
        self._assert_supported("malformed", "unsupported")
        self._assert_supported("", "unsupported")

    def test_v_prefix_tolerated(self):
        r = self._assert_supported("v4.1.1", "supported")
        self.assertEqual(r["SUPPORTED"], "supported")


class TestDetectorParser(unittest.TestCase):
    """Tolerant parser contract: unknown fields/values tolerated, no false PASS."""

    def test_clean_output_pass(self):
        status, _, reason = parse_detector_output("[]")
        self.assertEqual(status, "PASS")

    def test_finding_fail(self):
        status, findings, reason = parse_detector_output(json.dumps([REAL_FINDING]))
        self.assertEqual(status, "FAIL")
        self.assertGreaterEqual(len(findings), 1)

    def test_empty_output_not_run(self):
        status, _, _ = parse_detector_output("")
        self.assertEqual(status, "NOT_RUN")
        self.assertNotEqual(status, "PASS")

    def test_malformed_json_not_run(self):
        status, _, reason = parse_detector_output("not json {{{")
        self.assertEqual(status, "NOT_RUN")

    def test_non_array_not_run(self):
        status, _, _ = parse_detector_output('{"findings": []}')
        self.assertEqual(status, "NOT_RUN")

    def test_unknown_fields_tolerated(self):
        f = dict(REAL_FINDING)
        f["brand_new_field_x"] = "whatever"
        f["severity"] = "catastrophic-new-severity"
        f["category"] = "brand-new-category"
        status, findings, _ = parse_detector_output(json.dumps([f]))
        self.assertEqual(status, "FAIL")
        self.assertEqual(findings[0]["antipattern"], "overused-font")

    def test_missing_optional_fields_preserved(self):
        f = {"antipattern": "cramped-padding", "file": "src/ui.js"}
        status, findings, _ = parse_detector_output(json.dumps([f]))
        self.assertEqual(status, "FAIL")
        self.assertEqual(findings[0]["file"], "src/ui.js")

    def test_advisory_only_is_not_fail(self):
        f = dict(REAL_FINDING)
        f["advisory"] = True
        status, _, _ = parse_detector_output(json.dumps([f]))
        self.assertEqual(status, "PASS")


class TestManifest(unittest.TestCase):
    """Manifest structure conforms to the verified Spec Kit 1.0.x schema."""

    @unittest.skipUnless(HAS_YAML, "PyYAML required for YAML manifest assertions")
    def setUp(self):
        self.manifest = repo_root() / "extension" / "extension.yml"
        with open(self.manifest, encoding="utf-8") as fh:
            self.data = yaml.safe_load(fh)

    @unittest.skipUnless(HAS_YAML, "PyYAML required")
    def test_required_fields(self):
        for f in ("schema_version", "extension", "requires", "provides"):
            self.assertIn(f, self.data)
        self.assertEqual(self.data["schema_version"], "1.0")

    @unittest.skipUnless(HAS_YAML, "PyYAML required")
    def test_extension_metadata(self):
        ext = self.data["extension"]
        for f in ("id", "name", "version", "description"):
            self.assertIsInstance(ext[f], str)
        self.assertRegex(ext["id"], r"^[a-z0-9-]+$")

    @unittest.skipUnless(HAS_YAML, "PyYAML required")
    def test_allows_public_command_namespace(self):
        # Commands must be namespace speccable and match the <id>.
        ext_id = self.data["extension"]["id"]
        commands = self.data["provides"]["commands"]
        self.assertGreaterEqual(len(commands), 1)
        for cmd in commands:
            name = cmd["name"]
            self.assertRegex(name, r"^speckit\.[a-z0-9-]+\.[a-z0-9-]+$")
            self.assertTrue(name.startswith(f"speckit.{ext_id}."))
            self.assertIn("file", cmd)

    @unittest.skipUnless(HAS_YAML, "PyYAML required")
    def test_requires_speckit_version_met(self):
        req = self.data["requires"]["speckit_version"]
        self.assertIn("1.0", req)  # baseline >= 1.0.1 satisfied by this form

    @unittest.skipUnless(HAS_YAML, "PyYAML required")
    def test_extension_only_no_preset_shape(self):
        # v1 must not ship a preset or override core templates.
        self.assertNotIn("preset", self.data)
        self.assertNotIn("templates", self.data.get("provides", {}))


class TestHooks(unittest.TestCase):
    """Required hooks exist and are condition-free."""

    @unittest.skipUnless(HAS_YAML, "PyYAML required")
    def setUp(self):
        with open(repo_root() / "extension" / "extension.yml", encoding="utf-8") as fh:
            self.data = yaml.safe_load(fh)
        self.hooks = self.data.get("hooks", {})

    @unittest.skipUnless(HAS_YAML, "PyYAML required")
    def test_required_hooks_exist(self):
        for event in ("after_specify", "before_plan", "after_implement"):
            self.assertIn(event, self.hooks)

    @unittest.skipUnless(HAS_YAML, "PyYAML required")
    def test_hooks_condition_free(self):
        # Condition-free at the declaration level: no condition field of any value.
        for event, cfg in self.hooks.items():
            entries = cfg if isinstance(cfg, list) else [cfg]
            for e in entries:
                self.assertNotIn("condition", e)

    @unittest.skipUnless(HAS_YAML, "PyYAML required")
    def test_authoritative_gate_is_before_plan_mandatory(self):
        cfg = self.hooks["before_plan"]
        entries = cfg if isinstance(cfg, list) else [cfg]
        self.assertTrue(all(e.get("optional") is False for e in entries))
        self.assertTrue(all("speckit.speccable.ui-gate" in e.get("command", "") for e in entries))

    @unittest.skipUnless(HAS_YAML, "PyYAML required")
    def test_after_specify_eager_but_optional(self):
        cfg = self.hooks["after_specify"]
        entries = cfg if isinstance(cfg, list) else [cfg]
        self.assertTrue(all(e.get("optional", True) is True for e in entries))

    @unittest.skipUnless(HAS_YAML, "PyYAML required")
    def test_after_implement_mandatory(self):
        cfg = self.hooks["after_implement"]
        entries = cfg if isinstance(cfg, list) else [cfg]
        self.assertTrue(all(e.get("optional") is False for e in entries))
        self.assertTrue(all("ui-validate" in e.get("command", "") for e in entries))


class TestBoundaries(unittest.TestCase):
    """Architectural invariants: no core fork, no vendoring, no .impeccable writes."""

    def test_no_core_template_fork(self):
        # Speccable must not ship replacements for core templates.
        for pattern in ("spec-template", "plan-template", "tasks-template"):
            hits = list((repo_root() / "extension").rglob(pattern + "*"))
            self.assertEqual(hits, [], f"found core template fork: {pattern}")

    def test_extension_does_not_vendor_impeccable(self):
        # The extension tree must not contain Impeccable's source.
        ext = (repo_root() / "extension").rglob("*")
        for p in ext:
            rel = p.relative_to(repo_root() / "extension").as_posix().lower()
            self.assertNotIn("impeccable/scripts", rel)
            self.assertNotIn(".impeccable", rel)

    @unittest.skipUnless(HAS_YAML, "PyYAML required")
    def test_runtime_hooks_registered_condition_free(self):
        # After install, .specify/extensions.yml keeps hooks condition-free.
        reg = repo_root() / ".specify" / "extensions.yml"
        if not reg.exists():
            self.skipTest("extension not installed (registry absent)")
        with open(reg, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        for event, entries in (data.get("hooks") or {}).items():
            for e in entries:
                if e.get("extension") == "speccable":
                    self.assertIn("condition", e)  # key present (null) is fine
                    self.assertIsNone(e["condition"])

    @unittest.skipUnless(HAS_YAML, "PyYAML required to read hooks registry")
    def test_native_install_validation(self):
        """The authoritative check: 'specify extension add' validates + installs."""
        specify = shutil.which("specify")
        if not specify:
            self.skipTest("specify CLI not available")
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp)
            # Scaffold a minimal spec-kit project so 'extension add' has a valid
            # target (integration state, init options, gitignore).
            sp = proj / ".specify"
            sp.mkdir(parents=True)
            root = repo_root()
            (sp / "init-options.json").write_text(
                (root / ".specify" / "init-options.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (sp / "integration.json").write_text(
                (root / ".specify" / "integration.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (sp / ".gitignore").write_text("", encoding="utf-8")
            proc = subprocess.run(
                [specify, "extension", "add", str(root / "extension"), "--dev"],
                cwd=tmp,
                capture_output=True,
                text=True,
                input="",
            )
            combined = (proc.stdout + proc.stderr).lower()
            self.assertEqual(proc.returncode, 0, f"install failed: {combined}")
            # Commands materialize as skills in .zcode/skills/ for this project.
            for skill in ("speckit-speccable-ui-gate", "speckit-speccable-ui-validate"):
                self.assertTrue(
                    (proj / ".zcode" / "skills" / skill / "SKILL.md").exists(),
                    f"skill not materialized: {skill}",
                )
            # Hooks are registered condition-free in the runtime registry.
            reg = sp / "extensions.yml"
            self.assertTrue(reg.exists())
            with open(reg, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            for event in ("after_specify", "before_plan", "after_implement"):
                entries = (data.get("hooks") or {}).get(event)
                self.assertTrue(entries, f"hook missing for {event}")
                for e in entries:
                    if e.get("extension") == "speccable":
                        self.assertIsNone(e.get("condition"))


# ---------------------------------------------------------------------------
# Prose-contract tests (AR-003)
#
# These are NOT an attempt to pretend the Markdown command files are executable
# unit-test modules. They read the actual shipped command files and assert that
# the critical agent-facing behavioral contract is present in the text, so a
# future edit cannot silently drop a load-bearing guarantee (a "never default to
# none", a "BLOCK", a "NOT_RUN != PASS", a boundary prohibition) without the
# suite failing. They provide regression protection for the command contract,
# not engine-level execution guarantees.
# ---------------------------------------------------------------------------

class TestProseContract(unittest.TestCase):
    """Read the shipped command files and assert the behavioral contract is present."""

    @classmethod
    def setUpClass(cls):
        cmd_dir = repo_root() / "extension" / "commands"
        cls.gate = (cmd_dir / "speckit.speccable.ui-gate.md").read_text(encoding="utf-8")
        cls.validate = (cmd_dir / "speckit.speccable.ui-validate.md").read_text(encoding="utf-8")
        cls.design = (cmd_dir / "speckit.speccable.ui-design.md").read_text(encoding="utf-8")
        cls.compat = (repo_root() / "extension" / "scripts" / "check-compat.ps1").read_text(encoding="utf-8")
        cls.impact = (repo_root() / "extension" / "scripts" / "ui-impact.ps1").read_text(encoding="utf-8")

    # --- UI gate: no silent 'none', classification failure blocks ---
    def test_gate_never_silently_defaults_missing_to_none(self):
        self.assertIn("Never silently default a missing/invalid value to `none`", self.gate)

    def test_gate_invalid_does_not_silently_become_none(self):
        # Missing and invalid values both go through classification (Step 2), not to none.
        for line in ("`UI_IMPACT=unclassified`", "`UI_IMPACT=invalid`"):
            self.assertIn(line, self.gate)

    def test_gate_unresolved_classification_blocks(self):
        self.assertIn("fail explicitly", self.gate)
        self.assertIn("stop and report `BLOCK`", self.gate)

    def test_gate_preserves_valid_human_none(self):
        self.assertIn("`UI_IMPACT=none|direct` with `MATCH=preserved`", self.gate)
        self.assertIn("Preserve it verbatim", self.gate)

    def test_gate_preserves_valid_human_direct(self):
        self.assertIn("valid human-authored value", self.gate)

    # --- Routing ---
    def test_routing_before_plan_authoritative(self):
        self.assertIn("sole authoritative routing point", self.gate)
        self.assertIn("`before_plan` (authoritative)", self.gate)

    def test_routing_none_is_native(self):
        self.assertIn("`ROUTE = native`", self.gate)
        self.assertIn("continue the native Spec Kit workflow", self.gate)

    def test_routing_direct_requires_impeccable_capability(self):
        self.assertIn("Verify Impeccable capability", self.gate)
        self.assertIn("check-compat.ps1", self.gate)

    def test_routing_direct_requires_design_source(self):
        self.assertIn("Verify design source of truth", self.gate)

    def test_routing_missing_impeccable_blocks(self):
        self.assertIn("`IMPECCABLE=missing`) → **BLOCK**", self.gate)
        self.assertIn("does not auto-install it", self.gate)

    def test_routing_missing_design_source_blocks(self):
        self.assertIn("design source missing → `BLOCK`", self.gate)

    # --- Version range enforcement is fail-closed in the script (AR-002) ---
    def test_compat_reports_supported_field(self):
        self.assertIn("SUPPORTED=", self.compat)

    def test_compat_fails_closed_on_unreadable_version(self):
        # Present but malformed/unreadable must never be reported supported.
        self.assertIn("fail closed", self.compat)

    def test_gate_uses_supported_not_version_guess(self):
        self.assertIn("SUPPORTED=", self.gate)

    # --- Validation: NOT_RUN != PASS, no player promotion, findings -> tasks ---
    def test_validate_not_run_distinct_from_pass(self):
        self.assertIn("NOT_RUN ≠ PASS", self.validate)
        self.assertIn("never `PASS`", self.validate)

    def test_validate_detector_failure_not_pass(self):
        # Any inability to establish a valid result must be NOT_RUN, never PASS.
        self.assertIn("NOT_RUN", self.validate)
        # The cardinal rule is spelled out, not silently omitted.
        self.assertIn("never `PASS`", self.validate)

    def test_validate_primary_findings_fail(self):
        # The report surface carries the FAIL status and primary-finding count.
        self.assertIn("UI_VALIDATE_STATUS=<NOT_RUN|PASS|FAIL>", self.validate)
        self.assertIn("PRIMARY_FINDINGS=", self.validate)

    def test_validate_advisory_only_not_primary_fail(self):
        self.assertIn("advisoryOnly", self.validate)
        self.assertIn("primaryFindingsCount", self.validate)

    def test_validate_routes_findings_to_tasks(self):
        self.assertIn("tasks.md", self.validate)
        self.assertIn("`$TASKS_FILE`", self.validate)

    def test_validate_deterministic_distinct_from_critique(self):
        self.assertIn("deliberately distinct from agent-judgment layers", self.validate)
        self.assertIn("critique", self.validate)

    # --- AR-001: validator resolves all documented detector layouts, not hardcoded one ---
    def test_validate_resolves_all_documented_layouts(self):
        self.assertIn("`.agent`", self.validate)
        self.assertIn("`.agents`", self.validate)
        self.assertIn("`.claude`", self.validate)
        # The command delegates layout discovery to the shared validator; it does
        # not hardcode a single layout in the command text.
        self.assertIn("validate-detector.mjs", self.validate)
        self.assertIn("single shared data file", self.validate)

    def test_validate_missing_detector_is_not_run_not_pass(self):
        self.assertNotIn("missing detector is PASS", self.validate.lower())
        self.assertIn("NOT_RUN", self.validate)

    # --- AR-004: fenced code is excluded from UI Impact metadata ---
    def test_impact_skips_fenced_code_blocks(self):
        self.assertIn("fenced code blocks", self.impact)
        self.assertIn("are treated as examples and are ignored", self.impact)

    # --- AR-005: deterministic tasks insertion + dedup ---
    def test_validate_uses_stable_section_heading(self):
        self.assertIn("## UI Validation Follow-ups", self.validate)

    def test_validate_deduplicates_findings(self):
        self.assertIn("deduplicated", self.validate)

    def test_validate_never_touches_user_tasks(self):
        self.assertIn("converge channel", self.validate)
        self.assertIn("never replace the convergence engine", self.validate)
        self.assertIn("never modify `/speckit-converge`", self.validate)

    def test_validate_failed_run_cannot_corrupt_tasks(self):
        # Only the validator writes tasks (deduplicated, under its section);
        # a failed/non-deterministic run never writes. The command states this
        # delegation explicitly rather than containing a second writer.
        self.assertIn("single source of truth", self.validate)
        self.assertIn("does **not** reimplement", self.validate)

    # --- Boundary: no fabrication, no namespace writes, no auto-install (AR-003) ---
    def test_design_no_fabricated_surface_brief_path(self):
        self.assertIn("Never fabricates a Surface Brief filesystem path", self.design)

    def test_design_no_writes_inside_impeccable_namespace(self):
        self.assertIn("Never writes inside Impeccable's namespace", self.design)

    def test_design_no_auto_install(self):
        self.assertIn("Never auto-installs Impeccable", self.design)

    def test_gate_no_auto_install(self):
        self.assertIn("does not auto-install", self.gate)


# ---------------------------------------------------------------------------
# Executable deterministic validator (F2)
#
# These tests EXECUTE the shipped `validate-detector.mjs` against a scratch fake
# detector rather than testing a reimplementation. Layout discovery, detector
# execution, parsing, PASS/FAIL/NOT_RUN classification, DEGRADED detection, and
# findings -> tasks.md insertion are all covered through the real artifact.
# ---------------------------------------------------------------------------

FAKE_DETECTOR = """\
import { readFileSync } from 'node:fs';
const mode = (process.env.DETECT_MODE || 'clean');
let out = '', code = 0, err = '';
if (mode === 'clean') { out = '[]'; }
else if (mode === 'findings') {
  out = JSON.stringify([{antipattern:'overused-font',name:'Overused font',description:'Inter not distinctive',severity:'warning',category:'slop',file:'C:/proj/index.html',line:3,snippet:'font-family: Inter'}]);
  code = 2;
} else if (mode === 'findings2') {
  out = JSON.stringify([
    {antipattern:'cramped-padding',file:'src/ui.js',line:7,description:'tight'},
    {antipattern:'overused-font',file:'C:/proj/index.html',line:3,description:'dup'}
  ]);
  code = 2;
} else if (mode === 'advisory') { out = JSON.stringify([{antipattern:'x',advisory:true}]); }
else if (mode === 'mixed') {
  out = JSON.stringify([
    {antipattern:'overused-font',name:'Overused font',description:'Inter not distinctive',severity:'warning',category:'slop',file:'C:/proj/index.html',line:3},
    {antipattern:'nice-to-have-note',description:'suggestion only',advisory:true}
  ]);
  code = 2;
}
else if (mode === 'malformed') { out = 'not json {{'; }
else if (mode === 'object') { out = '{"findings":[]}'; }
else if (mode === 'empty') { out = ''; }
else if (mode === 'unknown_fields') {
  out = JSON.stringify([{antipattern:'o',severity:'catastrophic-new',category:'new-cat',brand_new_field:true}]);
  code = 2;
} else if (mode === 'missing_optional') { out = JSON.stringify([{antipattern:'cramped-padding',file:'src/ui.js'}]); }
else if (mode === 'degraded') { out = '[]'; err = 'HTML parser modules unavailable ... findings are an undercount'; }
else if (mode === 'sleep') { const _b = new SharedArrayBuffer(4); const _a = new Int32Array(_b); Atomics.wait(_a, 0, 0, 5000); out='[]'; }
else if (mode === 'crash') { process.exit(9); }
else if (mode === 'nonobject_arr') { out = JSON.stringify([1, 'two', null]); }
process.stdout.write(out);
if (err) process.stderr.write(err);
process.exit(code);
"""


def run_validator(project_root, target, tasks=None, timeout=None, env_extra=None):
    """Execute the real shipped validator. Returns (json_obj, stdout)."""
    cmd = ["node", str(repo_root() / "extension" / "scripts" / "validate-detector.mjs"),
           "--project", str(project_root), "--target", str(target)]
    if tasks:
        cmd += ["--tasks", str(tasks)]
    if timeout:
        cmd += ["--timeout", str(timeout)]
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    out = proc.stdout.strip()
    return (json.loads(out) if out else None), out


class TestValidateDetectorExecutable(unittest.TestCase):
    """F2: the deterministic validator is executable and its behavior is correct."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.layout = Path(self.tmp) / ".claude" / "skills" / "impeccable"
        (self.layout / "scripts").mkdir(parents=True)
        (self.layout / "SKILL.md").write_text("name: impeccable\nversion: 4.1.1\n", encoding="utf-8")
        (self.layout / "scripts" / "detect.mjs").write_text(FAKE_DETECTOR, encoding="utf-8")
        self.tasks = Path(self.tmp) / "tasks.md"
        self.tasks.write_text("# Tasks\n\n- [ ] user authored\n", encoding="utf-8")

    def validator(self, mode, tasks=None, extra=None, timeout=None):
        env = {"DETECT_MODE": mode}
        if extra:
            env.update(extra)
        return run_validator(self.tmp, self.tmp, tasks=tasks, timeout=timeout, env_extra=env)

    # --- Parsing ---
    def test_clean_empty_array_pass(self):
        obj, _ = self.validator("clean")
        self.assertEqual(obj["status"], "PASS")
        self.assertEqual(obj["reason"], "clean")
        self.assertEqual(obj["findingsCount"], 0)

    def test_primary_finding_fail(self):
        obj, _ = self.validator("findings")
        self.assertEqual(obj["status"], "FAIL")
        self.assertEqual(obj["primaryFindingsCount"], 1)

    def test_advisory_only_is_pass_not_fail(self):
        obj, _ = self.validator("advisory")
        self.assertEqual(obj["status"], "PASS")
        self.assertEqual(obj["advisoryOnly"], True)
        self.assertEqual(obj["primaryFindingsCount"], 0)

    def test_mixed_primary_and_advisory_fail_closes_on_primary(self):
        # V-03: a run carrying BOTH a primary finding and an advisory note must FAIL on the
        # primary, keep the advisory non-blocking, and surface ONLY the primary into tasks.md.
        obj, _ = self.validator("mixed", tasks=self.tasks)
        self.assertEqual(obj["status"], "FAIL")
        self.assertEqual(obj["reason"], "findings")
        self.assertEqual(obj["findingsCount"], 2)
        self.assertEqual(obj["primaryFindingsCount"], 1)
        self.assertEqual(obj["advisoryOnly"], False)
        text = self.tasks.read_text(encoding="utf-8")
        # Primary finding is materialized ...
        self.assertIn("overused-font", text)
        self.assertIn("## UI Validation Follow-ups", text)
        # ... the advisory note is NOT materialized as a task.
        self.assertNotIn("nice-to-have-note", text)

    def test_unknown_fields_tolerated_fail(self):
        obj, _ = self.validator("unknown_fields")
        self.assertEqual(obj["status"], "FAIL")
        self.assertEqual(obj["primaryFindingsCount"], 1)

    def test_missing_optional_fields_tolerated_fail(self):
        obj, _ = self.validator("missing_optional")
        self.assertEqual(obj["status"], "FAIL")

    def test_malformed_json_not_run(self):
        obj, _ = self.validator("malformed")
        self.assertEqual(obj["status"], "NOT_RUN")
        self.assertEqual(obj["reason"], "malformed-output")

    def test_non_array_json_not_run(self):
        obj, _ = self.validator("object")
        self.assertEqual(obj["status"], "NOT_RUN")
        self.assertEqual(obj["reason"], "non-array")

    def test_empty_output_not_run(self):
        obj, _ = self.validator("empty")
        self.assertEqual(obj["status"], "NOT_RUN")
        self.assertNotEqual(obj["status"], "PASS")

    def test_non_object_array_elements_skipped_not_crash(self):
        # Non-object elements are skipped (not a valid finding) without crashing -> PASS/clean.
        obj, _ = self.validator("nonobject_arr")
        self.assertEqual(obj["status"], "PASS")

    def test_crash_exit_never_pass(self):
        obj, _ = self.validator("crash")
        self.assertEqual(obj["status"], "NOT_RUN")

    # --- Execution / exit codes ---
    def test_execution_failure_exit_9_not_run(self):
        obj, _ = self.validator("crash")
        self.assertEqual(obj["status"], "NOT_RUN")

    def test_timeout_not_run(self):
        obj, _ = self.validator("sleep", timeout=100)
        self.assertEqual(obj["status"], "NOT_RUN")
        self.assertEqual(obj["reason"], "timeout")

    # --- Degraded ---
    def test_degraded_clean_is_pass_with_degraded_flag(self):
        obj, _ = self.validator("degraded")
        self.assertEqual(obj["status"], "PASS")
        self.assertEqual(obj["degraded"], 1)
        self.assertEqual(obj["DEGRADED"], 1)
        self.assertTrue(obj["degradedNotice"])

    # --- Layout resolution through the validator (F1 consistency) ---
    def test_layout_resolution_through_validator(self):
        obj, _ = self.validator("clean")
        self.assertEqual(obj["layout"], ".claude/skills/impeccable")
        self.assertTrue(obj["detectorPath"])

    def test_no_impeccable_is_not_run(self):
        d = tempfile.mkdtemp()
        obj, _ = run_validator(d, d)
        self.assertEqual(obj["status"], "NOT_RUN")
        self.assertEqual(obj["reason"], "exec-unavailable")
        self.assertEqual(obj["layout"], "none")

    def test_missing_detector_script_is_not_run(self):
        d = tempfile.mkdtemp()
        lay = Path(d) / ".claude" / "skills" / "impeccable"
        (lay / "scripts").mkdir(parents=True)
        (lay / "SKILL.md").write_text("version: 4.1.1\n", encoding="utf-8")
        # no detect.mjs
        obj, _ = run_validator(d, d)
        self.assertEqual(obj["status"], "NOT_RUN")
        self.assertEqual(obj["reason"], "exec-unavailable")

    # --- Findings -> tasks.md ---
    def test_fail_writes_tasks_under_section(self):
        self.validator("findings", tasks=self.tasks)
        text = self.tasks.read_text(encoding="utf-8")
        self.assertIn("## UI Validation Follow-ups", text)
        self.assertIn("overused-font", text)
        self.assertIn("C:/proj/index.html:3", text)

    def test_deduplication_no_duplicate_on_repeat(self):
        self.validator("findings", tasks=self.tasks)
        first = self.tasks.read_text(encoding="utf-8").count("overused-font")
        # A repeated FAIL run must not re-add an identical finding.
        self.validator("findings", tasks=self.tasks)
        text = self.tasks.read_text(encoding="utf-8")
        self.assertEqual(text.count("overused-font"), first)

    def test_distinct_findings_both_added(self):
        self.validator("findings2", tasks=self.tasks)
        text = self.tasks.read_text(encoding="utf-8")
        self.assertIn("cramped-padding", text)
        self.assertIn("overused-font", text)

    def test_pass_does_not_mutate_tasks(self):
        before = self.tasks.read_text(encoding="utf-8")
        self.validator("clean", tasks=self.tasks)
        self.assertEqual(self.tasks.read_text(encoding="utf-8"), before)

    def test_not_run_does_not_mutate_tasks(self):
        before = self.tasks.read_text(encoding="utf-8")
        self.validator("malformed", tasks=self.tasks)
        self.assertEqual(self.tasks.read_text(encoding="utf-8"), before)

    def test_failed_execution_does_not_mutate_tasks(self):
        before = self.tasks.read_text(encoding="utf-8")
        self.validator("crash", tasks=self.tasks)
        self.assertEqual(self.tasks.read_text(encoding="utf-8"), before)

    def test_existing_user_tasks_preserved(self):
        self.validator("findings", tasks=self.tasks)
        text = self.tasks.read_text(encoding="utf-8")
        self.assertIn("user authored", text)

    def test_write_preserves_crlf_line_endings(self):
        # V-02: a CRLF tasks.md must remain entirely CRLF after the validator appends
        # its section -- no LF gets mixed in, and the user's authored lines are untouched.
        self.tasks.write_bytes(b"# Tasks\r\n\r\n- [ ] user authored\r\n")
        self.validator("findings", tasks=self.tasks)
        data = self.tasks.read_bytes()
        self.assertIn(b"## UI Validation Follow-ups", data)
        self.assertEqual(data.count(b"\r\n"), data.count(b"\n"), "every newline is CRLF")
        self.assertGreater(data.count(b"\r\n"), 0)
        self.assertIn(b"- [ ] user authored\r\n", data)

    def test_write_preserves_lf_line_endings(self):
        # V-02: an LF tasks.md must remain entirely LF -- no CRLF is introduced.
        self.tasks.write_bytes(b"# Tasks\n\n- [ ] user authored\n")
        self.validator("findings", tasks=self.tasks)
        data = self.tasks.read_bytes()
        self.assertIn(b"## UI Validation Follow-ups", data)
        self.assertEqual(data.count(b"\r\n"), 0, "no CRLF introduced into an LF file")
        self.assertIn(b"- [ ] user authored\n", data)


class TestLayoutConsistency(unittest.TestCase):
    """F1: the capability resolver (check-compat.ps1) and the detector executor
    (validate-detector.mjs) must select the SAME installation via the SAME shared layout
    definition. This proves they never disagree."""

    def _layout_dir(self, root, layout):
        d = Path(root) / Path(layout)
        (d / "scripts").mkdir(parents=True)
        (d / "SKILL.md").write_text("name: impeccable\nversion: 4.1.1\n", encoding="utf-8")
        (d / "scripts" / "detect.mjs").write_text(FAKE_DETECTOR, encoding="utf-8")

    def _assert_agree(self, layouts):
        d = tempfile.mkdtemp()
        for lay in layouts:
            self._layout_dir(d, lay)
        # compat side
        compat = parse_kv(run_ps(
            Path("extension/scripts/check-compat.ps1"), ["-ProjectRoot", d]))
        # validator side
        obj, _ = run_validator(d, d)
        self.assertEqual(compat["LAYOUT"], obj["layout"],
                         f"compat {compat['LAYOUT']} != validator {obj['layout']} for {layouts}")

    def test_only_agent_agree(self):
        self._assert_agree([".agent/skills/impeccable"])

    def test_only_agents_agree(self):
        self._assert_agree([".agents/skills/impeccable"])

    def test_only_claude_agree(self):
        self._assert_agree([".claude/skills/impeccable"])

    def test_all_three_agree_prefer_agent(self):
        self._assert_agree([".agent/skills/impeccable", ".agents/skills/impeccable", ".claude/skills/impeccable"])

    def test_agents_and_claude_agree(self):
        self._assert_agree([".agents/skills/impeccable", ".claude/skills/impeccable"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
