# ORANGE_START_FABLE.ps1 — start Claude Code (Fable) in this repository.
# No MCP authentication required; contains no credentials.
$brain = Join-Path $PSScriptRoot "research\farouk_pilot\orange_brain"
Write-Host "ORANGE brain:    $(Join-Path $brain 'START_HERE.md')"
Write-Host "Operator brief:  $(Join-Path $brain 'operator_brief.md')"
Write-Host "Fable will load CLAUDE.md automatically and read the brain first."
Set-Location $PSScriptRoot
claude
