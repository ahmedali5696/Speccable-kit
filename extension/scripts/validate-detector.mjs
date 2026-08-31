#!/usr/bin/env node
// Speccable-kit: executable deterministic validation for the Impeccable detector.
//
// This is the SINGLE source of truth for deterministic validation behavior. The
// ui-validate *command* (a Spec Kit markdown skill) invokes this program and presents
// its result; it does NOT reimplement detector parsing, classification, or tasks.md
// insertion. Keeping the logic here makes it executable and independently testable.
//
// Contract (stdout is one JSON object):
//   {
//     "status": "PASS" | "FAIL" | "NOT_RUN",
//     "reason": "clean" | "findings" | "no-ui" | "exec-unavailable" | "timeout"
//               | "malformed-output" | "non-array" | "empty-output" | "layout-unavailable",
//     "findingsCount": <int>,           // total findings parsed from the array
//     "primaryFindingsCount": <int>,    // non-advisory findings (a FAIL driver)
//     "advisoryOnly": <bool>,
//     "degraded": <0|1>,                // detector reported degraded/undercounted analysis
//     "degradedNotice": "<stderr excerpt>" | "",
//     "layout": "<selected root>" | "none",
//     "detectorPath": "<abs detect.mjs>" | "",
//     "DEGRADED": <0|1>                 // alias for the parsable report line
//   }
//
// Exit code: 0 on a successful deterministic run (PASS/FAIL/NOT_RUN all exit 0 so the
// agent can read the reason), nonzero only on a hard internal failure.
//
// Invocation:
//   node validate-detector.mjs --project <root> --target <target>
//         [--tasks <tasks.md path>] [--timeout <ms>]
//
// NOTE: layout discovery order and the detector entry point live in the shared data file
// impeccable-layouts.json, the SAME file check-compat.ps1 reads. They can never disagree
// about where Impeccable exists.

import { execFile } from 'node:child_process';
import { readFile, writeFile, access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LAYOUTS_FILE = path.join(__dirname, 'impeccable-layouts.json');
const TASKS_SECTION = '## UI Validation Follow-ups';

// Default timeout for the detector subprocess (ms). The Spec Kit execution environment is
// a normal Node-capable shell; a detector scan should not hang the workflow.
const DEFAULT_TIMEOUT = 120000;

function fail(msg) {
  console.error(`validate-detector: ${msg}`);
  process.exit(2);
}

// ---------------------------------------------------------------------------
// Layout resolution (shared with check-compat.ps1 via the same JSON file)
// ---------------------------------------------------------------------------
async function resolveLayouts() {
  let data;
  try {
    data = JSON.parse(await readFile(LAYOUTS_FILE, 'utf8'));
  } catch (err) {
    fail(`cannot read layout definition ${LAYOUTS_FILE}: ${err.message}`);
  }
  return {
    order: data.order || [],
    detectorEntry: data.detectorEntryPoint || 'scripts/detect.mjs',
    skillFile: data.skillFile || 'SKILL.md',
  };
}

async function exists(p) {
  try { await access(p); return true; } catch { return false; }
}

// Returns { layout, root, skill, detectorPath } for the first layout present, or null.
async function findImpeccable(projectRoot, layoutDef) {
  for (const rel of layoutDef.order) {
    const root = path.join(projectRoot, ...rel.split('/'));
    const skill = path.join(root, layoutDef.skillFile);
    if (await exists(skill)) {
      const detectorPath = path.join(root, ...layoutDef.detectorEntry.split('/'));
      return { layout: rel, root, skill, detectorPath, detectorPresent: await exists(detectorPath) };
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Detector execution + degradation detection
// ---------------------------------------------------------------------------
function runDetector(detectorPath, target, timeoutMs) {
  return new Promise((resolve) => {
    execFile(
      process.execPath, // node
      [detectorPath, 'detect', '--json', target],
      { timeout: timeoutMs, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 },
      (error, stdout, stderr) => {
        const exit = error && typeof error.code === 'number' ? error.code
          : (error ? null : 0);
        const timedOut = !!(error && (error.killed || /ETIMEDOUT|timed.*out/i.test(error.message || '')));
        resolve({ exit, timedOut, stdout: stdout || '', stderr: stderr || '' });
      }
    );
  });
}

// A degraded notice means the scan is an undercount and must not be presented as a fully
// clean unconditional PASS. Markers are the ones the real detector emits on stderr when its
// optional analyzer modules are unavailable.
const DEGRADED_RE = /degraded|falling\s*back|undercount|parser modules? unavailable|not\s+available/i;

function detectDegraded(stderr) {
  const m = DEGRADED_RE.exec(stderr);
  if (!m) return { degraded: 0, notice: '' };
  const start = Math.max(0, m.index - 60);
  const excerpt = stderr.slice(start, m.index + m[0].length + 120).replace(/\s+/g, ' ').trim();
  return { degraded: 1, notice: excerpt };
}

// ---------------------------------------------------------------------------
// Tolerant JSON parsing + classification
// ---------------------------------------------------------------------------
function classify(stdout, degraded) {
  // NOT_RUN cases: unusable output is never PASS.
  if (stdout == null || !stdout.trim()) {
    return { status: 'NOT_RUN', reason: 'empty-output', findings: [], degraded };
  }
  let data;
  try {
    data = JSON.parse(stdout);
  } catch {
    return { status: 'NOT_RUN', reason: 'malformed-output', findings: [], degraded };
  }
  if (!Array.isArray(data)) {
    return { status: 'NOT_RUN', reason: 'non-array', findings: [], degraded };
  }

  // Tolerant parse: ignore unknown fields, tolerate unknown values, never crash on extra
  // fields, preserve info when optional fields are missing. A non-object array element is
  // skipped (not a valid finding) rather than crashing the whole run.
  const findings = [];
  for (const item of data) {
    if (item === null || typeof item !== 'object' || Array.isArray(item)) continue;
    const f = {};
    for (const k of Object.keys(item)) f[k] = item[k];
    findings.push(f);
  }

  // Advisory-only findings (advisory === true) never drive FAIL; they are non-blocking notes.
  const primaryFindings = findings.filter((f) => !(typeof f.advisory === 'boolean' ? f.advisory : f.advisory === true));

  if (primaryFindings.length > 0) {
    return { status: 'FAIL', reason: 'findings', findings, primaryCount: primaryFindings.length, degraded };
  }
  // Valid array; possibly advisory-only notes (not failures).
  return { status: 'PASS', reason: 'clean', findings, primaryCount: 0, degraded };
}

// ---------------------------------------------------------------------------
// Findings -> tasks.md (deterministic insertion + dedup)
// ---------------------------------------------------------------------------
function signatureOf(f) {
  const file = (f && f.file) ? String(f.file).replace(/\\/g, '/') : '';
  const line = (f && f.line != null) ? String(f.line) : '';
  return `sig:${f && f.antipattern ? String(f.antipattern) : ''}|${file}|${line}`;
}

// Returns { tasksPath tolerance note } — never mutates on PASS/NOT_RUN; only FAIL writes.
async function writeTasks(tasksPath, primaryFindings) {
  if (!tasksPath || primaryFindings.length === 0) return;
  const text = await readFile(tasksPath, 'utf8').catch(() => '');

  // Preserve the file's existing line-ending style so an insertion does not silently mix
  // LF with CRLF inside one tasks.md. If the file already uses CRLF we append with CRLF; a
  // file with no line endings (`\r\n` absent) defaults to LF. Rejoining the split user
  // content with the same EOL keeps user-authored lines byte-for-byte identical.
  const eol = text.includes('\r\n') ? '\r\n' : '\n';

  const lines = text.split(/\r?\n/);
  const hasSection = lines.some((l) => l.trim() === TASKS_SECTION);

  const newBlocks = [];
  for (const f of primaryFindings) {
    const sig = signatureOf(f);
    if (text.includes(sig)) continue; // already surfaced -> dedup
    const antipattern = (f && (f.antipattern || f.name || f.id)) || 'ui-finding';
    const where = f && f.file ? String(f.file).replace(/\\/g, '/') + (f.line != null ? `:${f.line}` : '') : 'unknown';
    const why = (f && f.description) || 'A detector finding was reported for this UI surface.';
    newBlocks.push(
      `- [ ] UI validation follow-up: ${antipattern}${eol}` +
      `  - Location: \`${where}\`${eol}` +
      `  - Why: ${why}${eol}` +
      `  - Acceptance: must not re-trigger this detector finding.${eol}` +
      `  - ${sig}`
    );
  }
  if (newBlocks.length === 0) return;

  let out;
  if (!hasSection) {
    // Create the section at EOF (using the file's line-ending style).
    const body = text.trim().length ? text.replace(/\r?\n?$/, '') + eol + eol : '';
    out = body + TASKS_SECTION + eol + eol + newBlocks.join(eol + eol) + eol;
  } else {
    // Append within the existing section: locate the heading, then insert before the next
    // heading or at EOF.
    const idx = lines.findIndex((l) => l.trim() === TASKS_SECTION);
    let end = lines.length;
    for (let i = idx + 1; i < lines.length; i++) {
      if (/^#{1,6}\s/.test(lines[i]) && lines[i].trim() !== TASKS_SECTION) { end = i; break; }
    }
    const prefix = lines.slice(0, end).join(eol);
    const suffix = lines.slice(end).join(eol);
    out = (prefix.endsWith(eol) ? prefix : prefix + eol) + newBlocks.join(eol + eol) + eol
      + (suffix ? eol + suffix : '');
  }
  await writeFile(tasksPath, out, 'utf8');
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------
function parseArgs(argv) {
  const args = { project: null, target: null, tasks: null, timeout: DEFAULT_TIMEOUT };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--project') args.project = argv[++i];
    else if (a === '--target') args.target = argv[++i];
    else if (a === '--tasks') args.tasks = argv[++i];
    else if (a === '--timeout') args.timeout = parseInt(argv[++i], 10) || DEFAULT_TIMEOUT;
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.project || !args.target) {
    fail('--project <root> and --target <target> are required');
  }
  const projectRoot = path.resolve(args.project);

  const layoutDef = await resolveLayouts();
  const found = await findImpeccable(projectRoot, layoutDef);

  const result = {
    status: 'NOT_RUN',
    reason: 'layout-unavailable',
    findingsCount: 0,
    primaryFindingsCount: 0,
    advisoryOnly: false,
    degraded: 0,
    degradedNotice: '',
    layout: 'none',
    detectorPath: '',
    DEGRADED: 0,
  };

  if (!found || !found.detectorPresent) {
    result.reason = 'exec-unavailable';
    result.layout = found ? found.layout : 'none';
    result.detectorPath = found ? found.detectorPath : '';
    // No tasks write on NOT_RUN.
    process.stdout.write(JSON.stringify(result));
    return;
  }

  const { exit, timedOut, stdout, stderr } = await runDetector(found.detectorPath, args.target, args.timeout);
  const { degraded, notice } = detectDegraded(stderr);
  result.layout = found.layout;
  result.detectorPath = found.detectorPath;
  result.degraded = degraded;
  result.DEGRADED = degraded;
  result.degradedNotice = notice;

  if (timedOut) {
    result.status = 'NOT_RUN';
    result.reason = 'timeout';
    result.degraded = degraded; result.DEGRADED = degraded;
    process.stdout.write(JSON.stringify(result));
    return;
  }

  // Execution failure with no usable stdout: NOT_RUN, never PASS.
  const cls = classify(stdout, degraded);
  result.findingsCount = cls.findings.length;
  result.primaryFindingsCount = cls.primaryCount;
  result.advisoryOnly = cls.status === 'PASS' && cls.findings.length > 0;
  result.degraded = degraded; result.DEGRADED = degraded;

  if (cls.status === 'PASS') {
    result.status = 'PASS';
    result.reason = 'clean';
  } else if (cls.status === 'FAIL') {
    result.status = 'FAIL';
    result.reason = 'findings';
  } else {
    result.status = 'NOT_RUN';
    result.reason = cls.reason;
  }

  // Only a FAIL with parseable primary findings writes tasks. PASS/NOT_RUN add nothing.
  if (result.status === 'FAIL' && args.tasks) {
    const primary = cls.findings.filter((f) => !(typeof f.advisory === 'boolean' ? f.advisory : f.advisory === true));
    await writeTasks(args.tasks, primary);
  }

  process.stdout.write(JSON.stringify(result));
}

main().catch((err) => { console.error(`validate-detector: ${err && err.stack || err}`); process.exit(2); });
