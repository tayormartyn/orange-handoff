<#
  ACL DELTA (Chuck corrections 1 + 2) - companion to Provision-OrangeAcl.ps1. ASCII-only.
  Splits APPROVAL_INBOX (approver submits candidates) from IMMUTABLE_APPROVAL_STORE (sealed,
  executor read-only, approver NO authority, owner = trusted non-approver). Adds DPAPI
  bootstrap-vs-runtime credential ACLs, and PATH SAFETY. Flips no gate, touches no service,
  connects nothing.

  Modes:
    DeltaProof (default)  - scratch + current-user stand-in. Zero live risk. Needs no admin.
    ShowPaths             - print the three paths for Martyn to CONFIRM before any apply.
    GenerateDeltaCommands - print the exact icacls/setowner commands the elevated run will execute.
#>
param(
  [ValidateSet('DeltaProof','ShowPaths','GenerateDeltaCommands')][string]$Mode='DeltaProof',
  [string]$ApprovalInbox,
  [string]$ImmutableStore,
  [string]$CredentialStore = (Join-Path $env:LOCALAPPDATA 'Orange'),
  [string]$Approver='svc-orange-approver',
  [string]$Executor='svc-orange-executor',
  [string]$Sealer='svc-orange-sealer',
  [string]$Owner='svc-orange-sealer'
)
$ErrorActionPreference='Stop'

# ---------- PATH SAFETY: refuse repo roots, home, Windows/system dirs, empty/root ----------
function Test-PathSafe([string]$p){
  if ([string]::IsNullOrWhiteSpace($p)) { return $false }
  try { $full = [IO.Path]::GetFullPath($p) } catch { return $false }
  $full = $full.TrimEnd('\')
  if ($full -match '^[A-Za-z]:$') { return $false }                                   # drive root
  $roots = @($env:SystemRoot,'C:\Windows','C:\Program Files','C:\Program Files (x86)') | Where-Object { $_ }
  foreach($r in $roots){ $r=$r.TrimEnd('\'); if ($full -ieq $r -or $full -ilike ($r+'\*')) { return $false } }
  if ($env:USERPROFILE -and ($full -ieq $env:USERPROFILE.TrimEnd('\'))) { return $false }  # home ROOT (subdirs ok)
  if ($full -imatch '\\signal-terminal(\\|$)') { return $false }                      # repository tree
  return $true
}

# ---------- exact command generators for the elevated run ----------
function Get-InboxCommands($inbox,$app,$sealer,$exe){
  @("icacls `"$inbox`" /inheritance:r",
    "icacls `"$inbox`" /grant `"$app`:(OI)(CI)(RX,WD,AD)`"",                          # approver SUBMITS candidates
    "icacls `"$inbox`" /grant `"$sealer`:(OI)(CI)(RX)`"",                             # sealer reads to seal
    "icacls `"$inbox`" /deny  `"$exe`:(OI)(CI)(F)`"",                                 # executor ignores the inbox
    "icacls `"$inbox`" /grant `"BUILTIN\Administrators`:(OI)(CI)F`" `"NT AUTHORITY\SYSTEM`:(OI)(CI)F`"")
}
function Get-ImmutableStoreCommands($store,$app,$exe,$owner){
  @("icacls `"$store`" /inheritance:r",
    "icacls `"$store`" /setowner `"$owner`" /t",                                      # owner = trusted NON-approver
    "icacls `"$store`" /grant `"$exe`:(OI)(CI)(RX)`"",                                # executor READ-ONLY
    "icacls `"$store`" /deny  `"$app`:(OI)(CI)(F)`"",                                 # approver NO authority at all
    "icacls `"$store`" /grant `"BUILTIN\Administrators`:(OI)(CI)F`" `"NT AUTHORITY\SYSTEM`:(OI)(CI)F`"")
}
function Get-CredBootstrapCommands($store,$exe){
  @("# BOOTSTRAP (human-triggered, temporary): grant executor create/write for the blob",
    "icacls `"$store`" /grant `"$exe`:(OI)(CI)(RX,WD,AD)`"",
    "# run AS $exe with its profile loaded so DPAPI CurrentUser binds to ${exe} :",
    "#   runas /user:$exe /profile `"python -m research.farouk_pilot.read_only_ctrader_preflight.store_secret`"",
    "#   (prove decrypt succeeds under $exe), then LOCK DOWN:")
}
function Get-CredRuntimeCommands($store,$exe,$app){
  @("icacls `"$store`" /remove:g `"$exe`"",
    "icacls `"$store`" /grant  `"$exe`:(OI)(CI)(RX)`"",                               # runtime: executor READ-ONLY
    "icacls `"$store`" /deny   `"$app`:(OI)(CI)(R,W)`"",                              # approver cannot read/decrypt
    "icacls `"$store`" /grant  `"BUILTIN\Administrators`:(OI)(CI)F`" `"NT AUTHORITY\SYSTEM`:(OI)(CI)F`"")
}

if ($Mode -eq 'ShowPaths'){
  Write-Output "CONFIRM THESE PATHS BEFORE ANY APPLY (Martyn):"
  foreach($pair in @(@('APPROVAL_INBOX',$ApprovalInbox),@('IMMUTABLE_APPROVAL_STORE',$ImmutableStore),@('CREDENTIAL_STORE',$CredentialStore))){
    $safe = if ($pair[1]) { Test-PathSafe $pair[1] } else { '<unset>' }
    Write-Output ("  {0,-24} = {1}   [path-safe: {2}]" -f $pair[0], $pair[1], $safe)
  }
  return
}
if ($Mode -eq 'GenerateDeltaCommands'){
  $ib = if($ApprovalInbox){$ApprovalInbox}else{'<APPROVAL_INBOX>'}
  $st = if($ImmutableStore){$ImmutableStore}else{'<IMMUTABLE_APPROVAL_STORE>'}
  Write-Output "# --- APPROVAL_INBOX ---";           Get-InboxCommands $ib $Approver $Sealer $Executor | ForEach-Object { Write-Output $_ }
  Write-Output "# --- IMMUTABLE_APPROVAL_STORE ---";  Get-ImmutableStoreCommands $st $Approver $Executor $Owner | ForEach-Object { Write-Output $_ }
  Write-Output "# --- CREDENTIAL bootstrap ---";      Get-CredBootstrapCommands $CredentialStore $Executor | ForEach-Object { Write-Output $_ }
  Write-Output "# --- CREDENTIAL runtime ---";        Get-CredRuntimeCommands $CredentialStore $Executor $Approver | ForEach-Object { Write-Output $_ }
  return
}

# ================================ DeltaProof (scratch, stand-in) ================================
$me = ([Security.Principal.WindowsIdentity]::GetCurrent()).Name
$scr = Join-Path $env:TEMP ("orange_delta_"+[guid]::NewGuid().ToString('N').Substring(0,8))
[IO.Directory]::CreateDirectory($scr) | Out-Null
$pass=0;$fail=0
function Chk($n,$c){ if($c){$script:pass++;Write-Output ("  ok   "+$n)}else{$script:fail++;Write-Output ("  FAIL "+$n)} }
function Denied([scriptblock]$op){ try{ & $op; $false }catch{ $true } }

# ---- PATH SAFETY ----
Chk "path-safety refuses empty"          (-not (Test-PathSafe ''))
Chk "path-safety refuses a drive root"   (-not (Test-PathSafe 'C:\'))
Chk "path-safety refuses Windows dir"    (-not (Test-PathSafe $env:SystemRoot))
Chk "path-safety refuses a system subdir" (-not (Test-PathSafe (Join-Path $env:SystemRoot 'System32')))
Chk "path-safety refuses the home root"  (-not (Test-PathSafe $env:USERPROFILE))
Chk "path-safety refuses the repo tree"  (-not (Test-PathSafe 'C:\Users\Marty\signal-terminal\research'))
Chk "path-safety ACCEPTS a dedicated store dir" (Test-PathSafe (Join-Path $scr 'store'))

# ---- INBOX: approver stand-in CAN submit a candidate ----
$inbox = Join-Path $scr 'inbox'; [IO.Directory]::CreateDirectory($inbox) | Out-Null
& icacls $inbox /grant ($me+':(OI)(CI)(RX,WD,AD)') | Out-Null
Chk "approver stand-in CAN submit a candidate to the inbox" (-not (Denied { [IO.File]::WriteAllText((Join-Path $inbox 'cand.json'),'{}') }))

# ---- IMMUTABLE STORE: approver stand-in (deny F) cannot create/modify/rename/delete ----
$store = Join-Path $scr 'store'; [IO.Directory]::CreateDirectory($store) | Out-Null
$sealed = Join-Path $store 'XAU.sealed.json'; [IO.File]::WriteAllText($sealed,'{"sealed":true}')
& icacls $store  /deny ($me+':(OI)(CI)(F)') | Out-Null
& icacls $sealed /deny ($me+':(F)') | Out-Null
Chk "approver stand-in CANNOT create in the immutable store" (Denied { [IO.File]::WriteAllText((Join-Path $store 'x.json'),'x') })
Chk "approver stand-in CANNOT modify a sealed approval"      (Denied { [IO.File]::AppendAllText($sealed,'t') })
Chk "approver stand-in CANNOT rename a sealed approval"      (Denied { [IO.File]::Move($sealed,(Join-Path $store 'r.json')) })
Chk "approver stand-in CANNOT delete a sealed approval"      (Denied { [IO.File]::Delete($sealed) })
& icacls $store  /remove:d $me | Out-Null
& icacls $sealed /remove:d $me | Out-Null

# ---- IMMUTABLE STORE: executor stand-in reads, cannot mutate ----
$store2 = Join-Path $scr 'store2'; [IO.Directory]::CreateDirectory($store2) | Out-Null
$s2 = Join-Path $store2 'XAU.sealed.json'; [IO.File]::WriteAllText($s2,'{"sealed":true}')
& icacls $store2 /grant ($me+':(OI)(CI)(RX)') | Out-Null
& icacls $s2     /deny  ($me+':(WD,AD,DE)') | Out-Null
Chk "executor stand-in CAN read a sealed approval"    (-not (Denied { [IO.File]::ReadAllText($s2) | Out-Null }))
Chk "executor stand-in CANNOT modify a sealed approval" (Denied { [IO.File]::AppendAllText($s2,'t') })
& icacls $s2 /remove:d $me | Out-Null

# ---- CREDENTIAL bootstrap-vs-runtime ----
$cred = Join-Path $scr 'cred'; [IO.Directory]::CreateDirectory($cred) | Out-Null
$blob = Join-Path $cred 'token.dpapi'; [IO.File]::WriteAllText($blob,'ENC')
# bootstrap: executor stand-in granted write -> write succeeds
& icacls $blob /grant ($me+':(WD,AD)') | Out-Null
Chk "bootstrap: executor stand-in write SUCCEEDS during bootstrap" (-not (Denied { [IO.File]::AppendAllText($blob,'x') }))
# runtime lockdown: read-only (deny write) -> write denied, read OK
& icacls $blob /deny ($me+':(WD,AD)') | Out-Null
Chk "runtime: executor stand-in write DENIED after lockdown" (Denied { [IO.File]::AppendAllText($blob,'x') })
Chk "runtime: executor stand-in read STILL OK"               (-not (Denied { [IO.File]::ReadAllText($blob) | Out-Null }))
& icacls $blob /remove:d $me | Out-Null
# approver stand-in denied read -> cannot read/decrypt
$blob2 = Join-Path $cred 'approver_view.dpapi'; [IO.File]::WriteAllText($blob2,'ENC')
& icacls $blob2 /deny ($me+':(R)') | Out-Null
Chk "approver stand-in CANNOT read the credential blob (no decrypt)" (Denied { [IO.File]::ReadAllText($blob2) | Out-Null })
& icacls $blob2 /remove:d $me | Out-Null

# ---- ROLLBACK: DACL restored (deny removed -> access returns) ----
Chk "rollback: removing the deny restores modify access" (-not (Denied { [IO.File]::AppendAllText($blob2,'ok') }))

# ---- command generation references the split roles + owner-away-from-approver ----
$gen = (Get-ImmutableStoreCommands $store $Approver $Executor $Owner) -join "`n"
Chk "store commands set owner to a trusted NON-approver and deny the approver" ($gen -match ('setowner .*'+[regex]::Escape($Owner)) -and $gen -match ('deny .*'+[regex]::Escape($Approver)) -and $Owner -ne $Approver)

[IO.Directory]::Delete($scr,$true)
Write-Output ""
Write-Output ("DELTA_DRYRUN: {0} passed, {1} failed" -f $pass,$fail)
Write-Output ("ELEVATED_ADMIN: " + ([Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)))
Write-Output "PROVEN_HERE: path safety; inbox submit allowed; immutable-store approver create/modify/rename/delete DENIED; executor read-only; bootstrap-write-then-runtime-lockdown; approver cannot read credential blob; rollback; command generation (owner != approver)."
Write-Output "ELEVATED_RUN_ONLY: real principals; ownership transfer AWAY from approver so approver (non-owner) cannot change owner/DACL; runas store_secret UNDER svc-orange-executor (profile loaded) DPAPI same-user decrypt; cross-principal decrypt FAILS."
if ($fail -gt 0) { exit 1 } else { exit 0 }
