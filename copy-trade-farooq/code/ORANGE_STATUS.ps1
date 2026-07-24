# ORANGE_STATUS.ps1 — read-only status (no live-state changes)
$brain = Join-Path $PSScriptRoot "research\farouk_pilot\orange_brain"
python (Join-Path $brain "brain_refresh.py") --status
python (Join-Path $brain "alert_lane_monitor.py")
python (Join-Path $brain "morphology_drift_canary.py")
