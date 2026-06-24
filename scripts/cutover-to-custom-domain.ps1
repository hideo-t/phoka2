<#
.SYNOPSIS
  Cutover helper: switch all absolute github.io/phoka2 references to the custom domain,
  fix the malformed "phoka<word>" og:url bugs, and write the CNAME file.

.DESCRIPTION
  Run in DryRun first (default) to preview. Run with -DryRun:$false at cutover.
  Files are read/written as UTF-8 without BOM to preserve Japanese text.

  Only run this AT cutover (once DNS points to GitHub Pages). Running earlier breaks
  the github.io/phoka2 staging URL.

.EXAMPLE
  pwsh ./scripts/cutover-to-custom-domain.ps1                 # preview (no writes)
  pwsh ./scripts/cutover-to-custom-domain.ps1 -DryRun:$false  # apply
  pwsh ./scripts/cutover-to-custom-domain.ps1 -Domain parkhomes-okinawa.com -DryRun:$false
#>
param(
  [string]$Domain = "www.parkhomes-okinawa.com",
  [bool]$DryRun = $true
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# Ordered replacements. phoka2 first, then the malformed bare "phoka" (no "2") prefix,
# which turns .../phokaabout/ -> .../about/ , .../phokalogin/ -> .../login/ , etc.
$rules = @(
  @{ from = "https://hideo-t.github.io/phoka2/"; to = "https://$Domain/" },
  @{ from = "https://hideo-t.github.io/phoka2";  to = "https://$Domain"  },
  @{ from = "https://hideo-t.github.io/phoka";   to = "https://$Domain/" }
)

$targets = Get-ChildItem -Path $repo -Recurse -File -Include *.html,*.xml,*.txt |
  Where-Object { $_.FullName -notmatch "\\\.git\\" -and $_.FullName -notmatch "\\\.omc\\" }

$totalFiles = 0
$totalHits  = 0
$expected   = 0   # leftover refs that are INTENTIONAL (the QAparkhome AI-consultation app) - leave alone
$unexpected = 0   # leftover github.io refs the rules did NOT catch - these need manual attention (want 0)

foreach ($f in $targets) {
  $text = [System.IO.File]::ReadAllText($f.FullName, $utf8NoBom)
  $hits = 0
  foreach ($r in $rules) {
    $count = ([regex]::Matches($text, [regex]::Escape($r.from))).Count
    if ($count -gt 0) {
      $hits += $count
      $text = $text.Replace($r.from, $r.to)
    }
  }
  # classify leftover github.io refs in the post-replacement text
  $expected   += ([regex]::Matches($text, "hideo-t\.github\.io/QAparkhome")).Count
  $unexpected += ([regex]::Matches($text, "hideo-t\.github\.io")).Count - ([regex]::Matches($text, "hideo-t\.github\.io/QAparkhome")).Count
  if ($hits -gt 0) {
    $totalFiles++
    $totalHits += $hits
    $rel = $f.FullName.Substring($repo.Length + 1)
    Write-Host ("{0,4}  {1}" -f $hits, $rel)
    if (-not $DryRun) {
      [System.IO.File]::WriteAllText($f.FullName, $text, $utf8NoBom)
    }
  }
}

# CNAME file (tells GitHub Pages the custom domain)
$cnamePath = Join-Path $repo "CNAME"
if ($DryRun) {
  Write-Host ""
  Write-Host "[DRY RUN] would write CNAME -> $Domain"
} else {
  [System.IO.File]::WriteAllText($cnamePath, "$Domain`n", $utf8NoBom)
  Write-Host ""
  Write-Host "wrote CNAME -> $Domain"
}

Write-Host ""
Write-Host ("Domain      : {0}" -f $Domain)
Write-Host ("Mode        : {0}" -f $(if ($DryRun) { "DRY RUN (no files changed)" } else { "APPLIED" }))
Write-Host ("Files hit   : {0}" -f $totalFiles)
Write-Host ("Occurrences : {0}" -f $totalHits)
Write-Host ("Leftover (expected, QAparkhome AI app - left intact): {0}" -f $expected)
Write-Host ("Leftover (UNEXPECTED - need manual review, want 0)  : {0}" -f $unexpected)
if ($unexpected -gt 0) {
  Write-Host "  WARNING: unexpected github.io refs remain. Review before pushing." -ForegroundColor Yellow
}
if ($DryRun) {
  Write-Host ""
  Write-Host "Re-run with -DryRun:`$false to apply, then commit & push."
}
