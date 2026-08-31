# Speccable-kit: read/classify the UI Impact value from a feature spec.
# Public contract: output one line "UI_IMPACT=<none|direct|unclassified|invalid>|MATCH=<...>|...".
# This is a narrowly-scoped helper for the ui-gate command; it does not perform routing.
#
# The marker is *document metadata*, not arbitrary example text. Lines inside Markdown
# fenced code blocks (``` ... ```) are treated as examples and are ignored, so a marker
# that appears only inside a fence is reported as missing (unclassified), while a real
# marker outside a fence is recognized. Existing rules are preserved: case-insensitive
# values, surrounding whitespace tolerance, CRLF support, empty -> invalid, duplicated
# real markers -> invalid, unknown value -> invalid.
param(
    [Parameter(Mandatory = $true)][string]$SpecFile
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SpecFile)) {
    Write-Output "UI_IMPACT=unclassified|ERROR=spec-not-found|FILE=$SpecFile"
    exit 1
}

$content = Get-Content -LiteralPath $SpecFile -Raw -ErrorAction Stop
if ($null -eq $content) { $content = "" }

# Normalize newlines so a single line-anchored pass works for both LF and CRLF.
$lines = ($content -replace "`r`n", "`n") -split "`n"

$markerLine = [regex]'^\s*\*\*UI\s+Impact\*\*\s*:\s*([^\r\n]*?)\s*$'
$fence = [regex]'^\s*```'
$inFence = $false
$values = New-Object System.Collections.Generic.List[string]

foreach ($line in $lines) {
    if ($fence.IsMatch($line)) {
        $inFence = -not $inFence
        continue
    }
    if ($inFence) { continue }
    $m = $markerLine.Match($line)
    if ($m.Success) {
        $values.Add($m.Groups[1].Value.Trim())
    }
}

if ($values.Count -eq 0) {
    Write-Output "UI_IMPACT=unclassified|MATCH=none|FILE=$SpecFile"
    exit 0
}

if ($values.Count -gt 1) {
    Write-Output "UI_IMPACT=invalid|MATCH=duplicate|FILE=$SpecFile"
    exit 0
}

$value = $values[0].ToLowerInvariant()

switch ($value) {
    "none"   { Write-Output "UI_IMPACT=none|MATCH=preserved|FILE=$SpecFile"; exit 0 }
    "direct" { Write-Output "UI_IMPACT=direct|MATCH=preserved|FILE=$SpecFile"; exit 0 }
    ""       { Write-Output "UI_IMPACT=invalid|MATCH=empty|FILE=$SpecFile"; exit 0 }
    default  { Write-Output "UI_IMPACT=invalid|MATCH=mismatch|VALUE=$value|FILE=$SpecFile"; exit 0 }
}
