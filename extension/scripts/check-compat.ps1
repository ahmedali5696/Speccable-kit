# Speccable-kit: report Impeccable capability/version from public surfaces.
# Public contract: output "IMPECCABLE=<present|missing>|VERSION=<ver|unknown>|DETECTOR=<present|missing|degraded>|SUPPORTED=<supported|unsupported|unknown|missing>|LAYOUT=<selected root|none>".
# Reads only public, documented surfaces: the installed skill's SKILL.md frontmatter
# version and the presence of the documented detect script. Never inspects internals.
#
# The set and order of layouts are defined ONCE in the sibling data file
# impeccable-layouts.json. The detector executor (validate-detector.mjs) reads the SAME
# file, so capability discovery and detector invocation can never disagree about where
# Impeccable lives or which installation is authoritative.
#
# Version *measurement* (VERSION) and supported-range *evaluation* (SUPPORTED) are distinct.
# SUPPORTED applies the approved range `>= 4.1 < 5.0` to the measured SKILL.md version and
# fails closed: a present-but-malformed or unreadable version is never reported as supported.
# The *gate* makes the routing decision; this script only reports a deterministic yes/no/unknown.
param(
    [string]$ProjectRoot = (Get-Location)
)

$ErrorActionPreference = "Stop"

# The shared layout definition lives next to this script (in both the source tree and the
# installed copy under .specify/extensions/speccable/scripts/).
$layoutsFile = Join-Path $PSScriptRoot "impeccable-layouts.json"
$layouts = @()
$detEntry = "scripts/detect.mjs"
$skillFile = "SKILL.md"
if (Test-Path -LiteralPath $layoutsFile) {
    $data = Get-Content -LiteralPath $layoutsFile -Raw | ConvertFrom-Json
    $layouts = @($data.order)
    $detEntry = $data.detectorEntryPoint
    $skillFile = $data.skillFile
}

$found = $false
$version = "unknown"
$detector = "missing"
$selectedLayout = "none"

foreach ($relRoot in $layouts) {
    $root = Join-Path $ProjectRoot $relRoot
    $skill = Join-Path $root $skillFile
    if (Test-Path -LiteralPath $skill) {
        $found = $true
        $selectedLayout = $relRoot
        $line = Select-String -LiteralPath $skill -Pattern '^\s*version\s*:\s*(.+)$' -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $line -and $line.Matches.Count -gt 0) {
            $version = $line.Matches[0].Groups[1].Value.Trim()
        }
        # Detector capability is the documented detect script.
        $detectScript = Join-Path $root $detEntry
        if (Test-Path -LiteralPath $detectScript) { $detector = "present" }
        break
    }
}

$present = if ($found) { "present" } else { "missing" }

# --- Deterministic supported-range evaluation (>= 4.1 < 5.0) ---
# Independent of the UI Impact value; a non-UI feature never requires Impeccable, and the
# gate decides whether this capability matters for the routed feature.
if (-not $found) {
    $supported = "missing"
} else {
    # Extract the leading numeric "major.minor[.patch]" from the version string
    # (an optional leading "v" is tolerated, e.g. "v4.1.1").
    $m = [regex]::Match($version, '^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?')
    $major = $null
    $minor = $null
    if ($m.Success -and $m.Groups[1].Success -and $m.Groups[1].Value -ne "") {
        $major = [int]$m.Groups[1].Value
        if ($m.Groups[2].Success -and $m.Groups[2].Value -ne "") {
            $minor = [int]$m.Groups[2].Value
        }
    }
    if ($null -eq $major) {
        # Malformed / unreadable version with Impeccable present: fail closed, never supported.
        $supported = "unsupported"
    } elseif ($major -eq 4) {
        if ($null -eq $minor) {
            # Bare "4" / "4.x": a 4-series version with no decipherable minor. The approved
            # range treats the 4.x line as supported (only an explicit 4.0 is below the floor).
            $supported = "supported"
        } elseif ($minor -ge 1) {
            $supported = "supported"
        } else {
            # 4.0.x is below the >= 4.1 floor.
            $supported = "unsupported"
        }
    } else {
        # Any non-4 major (3.x, 5.x, 6.x) is outside [4.1, 5.0).
        $supported = "unsupported"
    }
}

Write-Output "IMPECCABLE=$present|VERSION=$version|DETECTOR=$detector|SUPPORTED=$supported|LAYOUT=$selectedLayout"
exit 0
