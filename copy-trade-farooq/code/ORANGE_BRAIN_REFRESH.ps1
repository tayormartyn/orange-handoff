# ORANGE_BRAIN_REFRESH.ps1 — deterministic brain refresh (writes ONLY inside orange_brain/)
$brain = Join-Path $PSScriptRoot "research\farouk_pilot\orange_brain"
python (Join-Path $brain "brain_refresh.py")
Write-Host ""
Write-Host "Operator brief: $(Join-Path $brain 'operator_brief.md')"
try { Invoke-Item (Join-Path $brain "operator_brief.md") } catch { }
