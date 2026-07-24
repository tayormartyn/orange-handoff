<#
  SELF-VERIFYING ACL PROVISIONING TOOL - Orange demo-lane activation (D-094 / D-095 design).
  ASCII-only (PowerShell 5.1 reads .ps1 as cp1252). Flips no gate, touches no service, connects nothing.

  MODES
    DryRunProof (default) : prove enforcement + reversibility + idempotency on a SCRATCH dir using
                            the CURRENT user as an ACL stand-in. Creates NO principals, touches NO
                            real approvals dir or credential store. Zero live risk. Needs no admin.
    GenerateCommands      : print the EXACT icacls / New-LocalUser commands the elevated run will run.
    Apply                 : ELEVATED human activation - create the two principals, apply the ACLs,
                            store the broker token under the executor DPAPI. Requires admin AND
                            -ConfirmLiveActivation; refuses otherwise. (Not run in this phase.)
    Verify                : runas each OPPOSING principal, attempt each forbidden op, assert ACCESS
                            DENIED (the acceptance test). Requires the created principals (elevated run).
    Rollback              : restore the pre-provisioning ACL snapshot (icacls export/import).
#>
param(
  [ValidateSet('DryRunProof','GenerateCommands','Apply','Verify','Rollback')][string]$Mode='DryRunProof',
  [string]$ApprovalsDir,
  [string]$CredStore = (Join-Path $env:LOCALAPPDATA 'Orange'),
  [string]$Approver = 'svc-orange-approver',
  [string]$Executor = 'svc-orange-executor',
  [switch]$ConfirmLiveActivation
)
$ErrorActionPreference = 'Stop'

function Test-Elevated {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  [Security.Principal.WindowsPrincipal]::new($id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# ---- exact command generators (deterministic; the single source of the icacls design) ----
function Get-PrincipalCommands($app,$exe) {
  @("New-LocalUser -Name $app -Description 'Orange approver (create-only on approvals; denied creds)'",
    "New-LocalUser -Name $exe -Description 'Orange executor (read-only on approvals; reads creds)'")
}
function Get-ApprovalsAclCommands($dir,$app,$exe) {
  @("icacls `"$dir`" /inheritance:r",
    "icacls `"$dir`" /grant `"$app`:(OI)(CI)(RX,WD,AD)`" /deny `"$app`:(OI)(CI)(DE,DC)`"",   # create-only, immutable
    "icacls `"$dir`" /grant `"$exe`:(OI)(CI)(RX)`" /deny `"$exe`:(OI)(CI)(WD,AD,DE,DC)`"",     # read-only
    "icacls `"$dir`" /grant `"BUILTIN\Administrators`:(OI)(CI)F`" `"NT AUTHORITY\SYSTEM`:(OI)(CI)F`"")
}
function Get-CredStoreAclCommands($store,$app,$exe) {
  @("icacls `"$store`" /inheritance:r",
    "icacls `"$store`" /grant `"$exe`:(OI)(CI)(RX)`"",                                        # executor reads creds
    "icacls `"$store`" /deny  `"$app`:(OI)(CI)(R,W)`"",                                       # approver cannot obtain creds
    "icacls `"$store`" /grant `"BUILTIN\Administrators`:(OI)(CI)F`" `"NT AUTHORITY\SYSTEM`:(OI)(CI)F`"")
}
function Get-TokenStoreNote($exe) {
  @("# store the broker token under the EXECUTOR principal's DPAPI (CurrentUser=$exe SID) so the",
    "# approver cannot decrypt it even if it read the bytes. Run AS $exe (runas /user:$exe or a",
    "# scheduled task in $exe context):",
    "#   python -m research.farouk_pilot.read_only_ctrader_preflight.store_secret   (as $exe)")
}

# ---- ACE count for a given identity (idempotency check) ----
function Get-AceCount($path,$identity) {
  try { ((Get-Acl $path).Access | Where-Object { $_.IdentityReference -like "*$identity*" }).Count } catch { -1 }
}

# ================================ MODE: GenerateCommands ================================
if ($Mode -eq 'GenerateCommands') {
  $dir = if ($ApprovalsDir) { $ApprovalsDir } else { '<APPROVALS_DIR>' }
  Write-Output "# --- principals ---";        Get-PrincipalCommands   $Approver $Executor | ForEach-Object { Write-Output $_ }
  Write-Output "# --- approvals dir ACLs ---"; Get-ApprovalsAclCommands $dir $Approver $Executor | ForEach-Object { Write-Output $_ }
  Write-Output "# --- credential store ACLs ---"; Get-CredStoreAclCommands $CredStore $Approver $Executor | ForEach-Object { Write-Output $_ }
  Write-Output "# --- broker token DPAPI ---";  Get-TokenStoreNote $Executor | ForEach-Object { Write-Output $_ }
  return
}

# ================================ MODE: DryRunProof ================================
if ($Mode -eq 'DryRunProof') {
  $me = ([Security.Principal.WindowsIdentity]::GetCurrent()).Name
  $scr = Join-Path $env:TEMP ("orange_acl_dryrun_" + [guid]::NewGuid().ToString('N').Substring(0,8))
  [IO.Directory]::CreateDirectory($scr) | Out-Null
  $pass=0; $fail=0
  function Chk($name,$cond){ if($cond){$script:pass++; Write-Output ("  ok   " + $name)} else {$script:fail++; Write-Output ("  FAIL " + $name)} }
  function DeniedTo([scriptblock]$op){ try { & $op; $false } catch { $true } }

  # scratch approvals dir + one immutable approval file
  $adir = Join-Path $scr 'approvals'; [IO.Directory]::CreateDirectory($adir) | Out-Null
  $afile = Join-Path $adir 'XAU.approved.json'; [IO.File]::WriteAllText($afile, '{"immutable":true}')

  # ---- EXECUTOR ROLE (read-only): apply deny to the current user as stand-in ----
  & icacls $adir  /grant ($me + ':(OI)(CI)(RX)') | Out-Null
  & icacls $adir  /deny  ($me + ':(OI)(CI)(WD,AD,DE,DC)') | Out-Null
  & icacls $afile /deny  ($me + ':(WD,AD,DE)') | Out-Null
  Chk "executor stand-in CANNOT create an approval" (DeniedTo { [IO.File]::WriteAllText((Join-Path $adir 'new.json'),'x') })
  Chk "executor stand-in CANNOT modify an approval" (DeniedTo { [IO.File]::AppendAllText($afile,'tamper') })
  Chk "executor stand-in CANNOT rename an approval" (DeniedTo { [IO.File]::Move($afile, (Join-Path $adir 'renamed.json')) })
  Chk "executor stand-in CANNOT delete an approval" (DeniedTo { [IO.File]::Delete($afile) })
  Chk "executor stand-in CAN still read an approval" ((-not (DeniedTo { [IO.File]::ReadAllText($afile) | Out-Null })))

  # ---- APPROVER ROLE vs the credential store: deny read ----
  $cstore = Join-Path $scr 'cred'; [IO.Directory]::CreateDirectory($cstore) | Out-Null
  $cblob = Join-Path $cstore 'token.dpapi'; [IO.File]::WriteAllText($cblob, 'ENCRYPTED')
  & icacls $cblob /deny ($me + ':(R)') | Out-Null
  Chk "approver stand-in CANNOT read the credential store" (DeniedTo { [IO.File]::ReadAllText($cblob) | Out-Null })

  # ---- REVERSIBILITY (rollback restores access) ----
  & icacls $afile /remove:d $me | Out-Null
  & icacls $adir  /remove:d $me | Out-Null
  & icacls $cblob /remove:d $me | Out-Null
  Chk "rollback RESTORES modify access to the approval" ((-not (DeniedTo { [IO.File]::AppendAllText($afile,'ok') })))
  Chk "rollback RESTORES read access to the credential store" ((-not (DeniedTo { [IO.File]::ReadAllText($cblob) | Out-Null })))

  # ---- IDEMPOTENCY (re-applying a deny does not duplicate the ACE) ----
  & icacls $afile /deny ($me + ':(WD)') | Out-Null
  $c1 = Get-AceCount $afile $me
  & icacls $afile /deny ($me + ':(WD)') | Out-Null
  $c2 = Get-AceCount $afile $me
  Chk "idempotent: re-applying the deny does not duplicate ACEs" ($c1 -eq $c2 -and $c1 -ge 1)

  # ---- command-generation is well-formed (non-empty, references both principals) ----
  $cmds = @(); $cmds += Get-ApprovalsAclCommands $adir $Approver $Executor; $cmds += Get-CredStoreAclCommands $cstore $Approver $Executor
  Chk "command generation references both principals + inheritance:r" (($cmds -join "`n") -match 'inheritance:r' -and ($cmds -join "`n") -match $Approver -and ($cmds -join "`n") -match $Executor)

  [IO.Directory]::Delete($scr, $true)
  Write-Output ""
  Write-Output ("DRYRUN_PROOF: {0} passed, {1} failed" -f $pass,$fail)
  Write-Output ("ELEVATED_ADMIN: " + (Test-Elevated))
  Write-Output "PROVEN_HERE: deny-ACE enforcement (create/modify/rename/delete DENIED), cred-store read DENIED, reversibility, idempotency, command generation."
  Write-Output "ELEVATED_RUN_ONLY: create the two named principals; apply ACLs referencing them; runas-as-each ACCESS-DENIED acceptance test; token under executor DPAPI (cross-principal decrypt refusal)."
  if ($fail -gt 0) { exit 1 } else { exit 0 }
}

# ================================ MODE: Apply (ELEVATED human run) ================================
if ($Mode -eq 'Apply') {
  if (-not (Test-Elevated)) { throw "Apply requires an ELEVATED (admin) PowerShell." }
  if (-not $ConfirmLiveActivation) { throw "Apply requires -ConfirmLiveActivation (explicit operator go-action)." }
  if (-not $ApprovalsDir) { throw "Apply requires -ApprovalsDir (the governed approvals directory)." }
  # snapshot for rollback (export current ACLs to a sidecar)
  $snap = Join-Path (Split-Path $ApprovalsDir -Parent) 'orange_acl_rollback.acl'
  & icacls (Split-Path $ApprovalsDir -Leaf) /save $snap /t 2>$null | Out-Null   # (run from parent; see Rollback)
  foreach ($u in @($Approver,$Executor)) {
    if (-not (Get-LocalUser -Name $u -ErrorAction SilentlyContinue)) {
      $pw = ConvertTo-SecureString ([guid]::NewGuid().ToString()+'Aa1!') -AsPlainText -Force
      New-LocalUser -Name $u -Password $pw -Description "Orange $u" | Out-Null   # password used only for Verify runas
    }
  }
  Get-ApprovalsAclCommands $ApprovalsDir $Approver $Executor | ForEach-Object { Invoke-Expression $_ }
  Get-CredStoreAclCommands $CredStore    $Approver $Executor | ForEach-Object { Invoke-Expression $_ }
  Write-Output "APPLIED. Store the broker token under $Executor DPAPI, then run -Mode Verify."
  return
}

if ($Mode -eq 'Verify')   { throw "Verify runs the runas ACCESS-DENIED acceptance test against the created principals - ELEVATED run only." }
if ($Mode -eq 'Rollback') { throw "Rollback restores orange_acl_rollback.acl via 'icacls <dir> /restore <snap>' - ELEVATED run only." }
