<#
  ORANGE_START_SERVICES.ps1 - documented, single-instance-guarded launcher for the ORANGE
  read-only services. Machine-proven commands + working directories (established 2026-07-22
  from each service's instance-lock LOCATION and its running command line).

  WHY the working directory matters: each service resolves its instance lock and cursor at
  dirname(abspath(__file__)), which equals the CWD when launched by RELATIVE filename from
  the file's own directory. A wrong CWD => wrong lock/cursor paths => duplicate instance or
  lost cursor (the exact class of failure this launcher exists to prevent).

  PROVEN working directories (lock file found at that path, holding the live PID):
    wire     -> follower_assistant\                    (live_wire.instance.lock, PID 30612)
    watcher  -> follower_assistant\evidence_layer\     (evidence_watcher.instance.lock, PID 3348)
    observer -> follower_assistant\intake_reliability\ (intake_observer.instance.lock, PID 8068)
    listener -> repo root C:\Users\Marty\signal-terminal (no lock; HIGH-confidence recipe, used 2026-07-22)

  USAGE:
    .\ORANGE_START_SERVICES.ps1 -DryRun               # print exact command + guard decision per service; START NOTHING
    .\ORANGE_START_SERVICES.ps1 -Only wire,listener   # start only named services (each guarded)
    .\ORANGE_START_SERVICES.ps1                        # start all (guarded; REFUSES any already-running service)

  Each service is launched DETACHED (Start-Process = independent, session-surviving) with
  DATED stdout/stderr redirection into that service's own logs\ directory.
#>
param(
  [switch]$DryRun,
  [string[]]$Only
)
$ErrorActionPreference = 'Stop'
# -File passes "-Only a,b" as ONE string element; split so a comma-separated list works.
if($Only){ $Only = @($Only -join ',' -split ',' | Where-Object { $_ }) }
$PY   = 'C:\Python314\python.exe'
$ROOT = 'C:\Users\Marty\signal-terminal'
$FA   = Join-Path $ROOT 'research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\farouk_plus\follower_assistant'

$SERVICES = @(
  @{ name='wire';     args=@('-u','live_wire.py','--watch');
     workdir=$FA;                                    logdir=(Join-Path $FA 'logs');
     lock=(Join-Path $FA 'live_wire.instance.lock'); marker='live_wire\.py' },
  @{ name='watcher';  args=@('-u','evidence_watcher.py','--watch');
     workdir=(Join-Path $FA 'evidence_layer');       logdir=(Join-Path $FA 'evidence_layer\logs');
     lock=(Join-Path $FA 'evidence_layer\evidence_watcher.instance.lock'); marker='evidence_watcher\.py' },
  @{ name='observer'; args=@('-u','intake_observer.py','--watch');
     workdir=(Join-Path $FA 'intake_reliability');   logdir=(Join-Path $FA 'intake_reliability\logs');
     lock=(Join-Path $FA 'intake_reliability\intake_observer.instance.lock'); marker='intake_observer\.py' },
  @{ name='listener'; args=@('-u','module_a_telegram.py');
     workdir=$ROOT;                                  logdir=(Join-Path $ROOT 'data\listener_logs');
     lock=$null; marker='module_a_telegram\.py' }
)

function Get-RunningPids([string]$marker){
  ,@(Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
     Where-Object { $_.CommandLine -match $marker } | ForEach-Object { $_.ProcessId })
}
function Test-PidAlive($processId){
  if(-not $processId){ return $false }
  return $null -ne (Get-Process -Id ([int]$processId) -ErrorAction SilentlyContinue)
}

function Invoke-OrangeService($svc){
  $name = $svc.name

  # ---- SINGLE-INSTANCE GUARD (the safety that makes restarts safe) ----
  $running = Get-RunningPids $svc.marker
  $lockPid = $null
  if($svc.lock -and (Test-Path $svc.lock)){ $lockPid = (Get-Content $svc.lock -ErrorAction SilentlyContinue | Select-Object -First 1) }
  $decision = 'CLEAR'; $why = ''
  if($running.Count -ge 1){ $decision='REFUSE'; $why = ("already running (PID {0})" -f ($running -join ',')) }
  elseif($lockPid -and (Test-PidAlive $lockPid)){ $decision='REFUSE'; $why = ("instance lock held by live PID {0}" -f $lockPid) }
  elseif($lockPid){ $decision='STALE_LOCK'; $why = ("lock holds DEAD PID {0}: prove-dead + clean before start" -f $lockPid) }

  $ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
  $out = Join-Path $svc.logdir ("{0}_{1}.out.log" -f $name,$ts)
  $err = Join-Path $svc.logdir ("{0}_{1}.err.log" -f $name,$ts)

  if($DryRun){
    Write-Host ("  [{0}] exact command that WOULD run:" -f $name) -ForegroundColor Cyan
    Write-Host ("      {0} {1}" -f $PY, ($svc.args -join ' '))
    Write-Host ("      WorkingDirectory: {0}" -f $svc.workdir)
    Write-Host ("      RedirectOut/Err : {0}  (and {1}.err.log)" -f $out, $ts)
    if($decision -eq 'REFUSE'){ Write-Host ("      GUARD => REFUSE: {0}" -f $why) -ForegroundColor Yellow }
    elseif($decision -eq 'STALE_LOCK'){ Write-Host ("      GUARD => STALE LOCK: {0}" -f $why) -ForegroundColor Yellow }
    else { Write-Host "      GUARD => would START (clear: no running process, no live lock)" -ForegroundColor Green }
    return
  }

  # ---- LIVE ----
  if($decision -eq 'REFUSE'){ Write-Host ("  REFUSE {0}: {1}; not starting a duplicate" -f $name,$why) -ForegroundColor Yellow; return }
  if($decision -eq 'STALE_LOCK'){ Write-Host ("  BLOCK {0}: {1}" -f $name,$why) -ForegroundColor Yellow; return }
  if(-not (Test-Path $svc.logdir)){ New-Item -ItemType Directory -Path $svc.logdir -Force | Out-Null }
  # -PassThru returns the Process object immediately (no wait); we then SELF-VERIFY the pid is
  # alive and REPORT it, so the launcher never needs external verification. Write-Output (success
  # stream) so a caller that pipes/closes stdout early cannot stall the report.
  $proc = Start-Process -FilePath $PY -ArgumentList $svc.args -WorkingDirectory $svc.workdir `
    -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
  Start-Sleep -Milliseconds 700
  $alive = $null -ne (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)
  if($alive){ Write-Output ("  STARTED {0}  pid={1}  alive=TRUE  (workdir {2}; logs {3})" -f $name,$proc.Id,$svc.workdir,$out) }
  else      { Write-Output ("  FAILED  {0}  pid={1} exited immediately - inspect {2}" -f $name,$proc.Id,$err) }
}

$targets = if($Only){ $SERVICES | Where-Object { $Only -contains $_.name } } else { $SERVICES }
$modeStr = if($DryRun){ 'DRY-RUN (nothing started)' } else { 'LIVE' }
Write-Host ("ORANGE_START_SERVICES  mode={0}  targets={1}" -f $modeStr, (($targets | ForEach-Object { $_.name }) -join ', '))
Write-Host ('-' * 70)
foreach($s in $targets){ Invoke-OrangeService $s }
