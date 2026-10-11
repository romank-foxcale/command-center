<#
.SYNOPSIS
  Sets up the Control Center kit on Windows: WSL2 + Ubuntu, then Nix and the kit inside WSL.

.DESCRIPTION
  Safe to re-run. Each step checks what is already there and skips it.
  Start it as a normal user: it asks for administrator rights only to install WSL.
  If Windows needs a reboot, it continues by itself after the next sign-in.
  At the end it adds cc-kit to PowerShell and offers to create the first Control Center.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File install\windows\install.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File install\windows\install.ps1 -Tools claude,codex,opencode
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File install\windows\install.ps1 -KitSource C:\path\to\command-center
#>
[CmdletBinding()]
param(
    [string]$Distro = "Ubuntu",
    [string]$KitRepo = "https://github.com/romank-foxcale/command-center.git",
    [string]$KitBranch = "main",
    # For testing: copy the kit from a local Windows folder instead of cloning it.
    [string]$KitSource = "",
    # Command-line AI tools to install inside WSL: claude, codex, opencode, or none.
    [string[]]$Tools = @("claude"),
    # Internal: the elevated copy of this script that only installs WSL.
    [switch]$WslOnly
)

$ErrorActionPreference = "Stop"
# Without this, wsl.exe prints UTF-16 text that PowerShell cannot compare.
$env:WSL_UTF8 = "1"

function Write-Step([string]$Message) { Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Note([string]$Message) { Write-Host "    $Message" }
function Write-Warn([string]$Message) { Write-Host "!!  $Message" -ForegroundColor Yellow }

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    (New-Object Security.Principal.WindowsPrincipal $identity).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Runs a native command, dropping its error output. PowerShell 5.1 turns any
# redirected stderr into a terminating error under ErrorActionPreference=Stop.
function Invoke-Quiet([scriptblock]$Block) {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $Block 2>$null } finally { $ErrorActionPreference = $previous }
}

function Get-Distros {
    $output = Invoke-Quiet { wsl.exe --list --quiet }
    if ($LASTEXITCODE -ne 0) { return @() }
    @($output | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

function Invoke-Wsl([string]$Command) {
    & wsl.exe -d $Distro -- bash -lc $Command
    if ($LASTEXITCODE -ne 0) { throw "WSL command failed ($LASTEXITCODE): $Command" }
}

# 1. Windows version: WSL2 needs Windows 10 build 19041+ or Windows 11.
Write-Step "Checking Windows"
$build = [Environment]::OSVersion.Version.Build
if ($build -lt 19041) {
    throw "Windows build $build is too old for WSL2. Update Windows first (build 19041 or newer)."
}
Write-Note "Windows build $build OK"

# 2. WSL itself and the Linux distribution.
Write-Step "Checking WSL2 and $Distro"

# A copy of this script that survives a reboot: the elevated WSL step and the resume after sign-in run it.
$persisted = Join-Path $env:LOCALAPPDATA "cc-kit\install.ps1"
if (-not $WslOnly) {
    New-Item -ItemType Directory -Force (Split-Path $persisted) | Out-Null
    if ($PSCommandPath -and ($PSCommandPath -ne $persisted)) {
        Copy-Item -Force $PSCommandPath $persisted
    } elseif (-not $PSCommandPath) {
        Invoke-RestMethod "https://raw.githubusercontent.com/romank-foxcale/command-center/$KitBranch/install/windows/install.ps1" -OutFile $persisted
    }
}
$rerun = "-ExecutionPolicy Bypass -File `"$persisted`" -Distro $Distro -KitRepo $KitRepo -KitBranch $KitBranch -Tools $($Tools -join ',')"
if ($KitSource) { $rerun += " -KitSource `"$KitSource`"" }

function Test-WslReady {
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { return $false }
    Invoke-Quiet { wsl.exe --status } | Out-Null
    ($LASTEXITCODE -eq 0) -and ((Get-Distros) -contains $Distro)
}

if (-not (Test-WslReady)) {
    if ($WslOnly -or (Test-Admin)) {
        Write-Note "Installing WSL2 with $Distro (this can take several minutes)"
        Write-Note "When $Distro asks for a UNIX username and password, create them: the username in lowercase,"
        Write-Note "the password stays invisible while you type. Then type 'exit' to come back here."
        # No --no-launch: on current WSL it can leave the distro unregistered.
        & wsl.exe --install -d $Distro
        if ($LASTEXITCODE -ne 0) { throw "wsl --install failed. See the message above." }
    } else {
        Write-Note "Installing WSL needs administrator rights: Windows asks for them now, in a second window."
        Start-Process powershell.exe -Verb RunAs -Wait -ArgumentList "$rerun -WslOnly"
    }
    if ($WslOnly) { exit 0 }
    if (-not (Test-WslReady)) {
        # WSL only works after a reboot: continue by itself after the next sign-in.
        Set-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce" "CcKitInstall" "powershell.exe -NoExit $rerun"
        Write-Warn "Restart Windows to finish installing WSL. After you sign in, this setup continues by itself."
        exit 0
    }
}
if ($WslOnly) { exit 0 }
& wsl.exe --set-default-version 2 | Out-Null

$version = (Invoke-Quiet { wsl.exe --list --verbose } | Where-Object { $_ -match "\b$([regex]::Escape($Distro))\b" }) -replace '.*\s(\d)\s*$', '$1'
if ($version -eq "1") {
    Write-Note "Converting $Distro from WSL1 to WSL2"
    & wsl.exe --set-version $Distro 2
}

# 3. The distro must have a normal user; Nix and the tools must not run as root.
$linuxUser = (Invoke-Quiet { wsl.exe -d $Distro -- whoami } | Select-Object -First 1)
if (-not $linuxUser -or $linuxUser.Trim() -eq "root") {
    Write-Warn "$Distro has no regular Linux user yet."
    Write-Note "Run 'wsl -d $Distro', create a user and password, type 'exit', and run this script again."
    exit 1
}
Write-Note "$Distro is ready (user: $($linuxUser.Trim()))"

# 4. Clone or update the kit inside the Linux filesystem, never under /mnt/c.
Write-Step "Getting the Control Center kit inside WSL (~/.cc-kit)"
Invoke-Wsl "command -v git >/dev/null || (sudo apt-get update && sudo apt-get install -y git)"
if ($KitSource) {
    # Copies the folder as-is, including uncommitted changes, replacing any previous kit.
    if (-not (Test-Path (Join-Path $KitSource "install\cc-kit"))) { throw "$KitSource is not a kit folder" }
    $linuxSource = (& wsl.exe -d $Distro -- wslpath -a ((Resolve-Path $KitSource).Path -replace '\\', '/')).Trim()
    Write-Note "Copying the kit from $KitSource"
    Invoke-Wsl "rm -rf ~/.cc-kit && cp -r '$linuxSource' ~/.cc-kit && git -C ~/.cc-kit config core.fileMode false"
} else {
    Invoke-Wsl ("if [ -d ~/.cc-kit/.git ]; then git -C ~/.cc-kit pull --ff-only; " +
        "else git clone --branch '$KitBranch' '$KitRepo' ~/.cc-kit; fi")
}

# 5. Everything else happens inside Linux. sudo will ask for the Linux password.
Write-Step "Running the Linux installer inside $Distro"
$toolArgument = if ($Tools.Count) { "--tools " + ($Tools -join ",") } else { "--tools none" }
# The first Control Center is offered at the end of this script instead, once cc-kit works from PowerShell.
$linuxInstall = "CC_KIT_NO_FIRST=1 ~/.cc-kit/install/install.sh $toolArgument"
& wsl.exe -d $Distro -- bash -lc $linuxInstall
if ($LASTEXITCODE -eq 10) {
    # install.sh turned on systemd, which only takes effect after WSL restarts.
    Write-Note "Restarting WSL to turn on systemd"
    & wsl.exe --shutdown
    & wsl.exe -d $Distro -- bash -lc $linuxInstall
}
if ($LASTEXITCODE -ne 0) { throw "The Linux installer failed. Read the message above, fix it, and run this script again." }

# 6. Windows-side editors: make sure they can open folders inside WSL.
Write-Step "Checking editors and AI apps on Windows"
if (Get-Command code -ErrorAction SilentlyContinue) {
    & code --install-extension ms-vscode-remote.remote-wsl --force | Out-Null
    Write-Note "VS Code: WSL extension installed"
} else {
    Write-Note "VS Code: not found (optional)"
}
if (Get-Command cursor -ErrorAction SilentlyContinue) {
    Invoke-Quiet { cursor --install-extension anysphere.remote-wsl --force } | Out-Null
    Write-Note "Cursor: WSL extension installed"
} else {
    Write-Note "Cursor: not found (optional)"
}
# Newer builds install as an app package; older ones as a per-user folder.
$claudeDesktop = [bool](Get-AppxPackage -Name "Claude" -ErrorAction SilentlyContinue) -or
    (Test-Path "$env:LOCALAPPDATA\AnthropicClaude")
Write-Note ("Claude desktop: " + $(if ($claudeDesktop) { "found" } else { "not found (optional)" }))

# 7. cc-kit from PowerShell and cmd: a launcher on the user's PATH that runs it inside WSL.
Write-Step "Adding the cc-kit command to Windows"
$binDir = Join-Path $env:LOCALAPPDATA "cc-kit\bin"
New-Item -ItemType Directory -Force $binDir | Out-Null
$launcher = @"
@echo off
rem Runs cc-kit inside WSL ($Distro), where the kit, Nix and the Control Centers live.
wsl.exe -d $Distro --cd ~ -e bash -lc "exec cc-kit \"`$@\"" cc-kit %*
exit /b %errorlevel%
"@
Set-Content -Path (Join-Path $binDir "cc-kit.cmd") -Value $launcher -Encoding Ascii
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not (($userPath -split ";") -contains $binDir)) {
    [Environment]::SetEnvironmentVariable("Path", (@($userPath, $binDir) | Where-Object { $_ }) -join ";", "User")
}
$env:Path = "$env:Path;$binDir"
Write-Note "cc-kit works in any new PowerShell or cmd window"

Write-Step "Done"
$existing = Invoke-Quiet { wsl.exe -d $Distro -- bash -lc "ls -d ~/Projects/*_CC 2>/dev/null" }
if (-not $existing) {
    Write-Note "Now create your first Control Center."
    Write-Note "Name it after the product or system it covers, in lowercase with dashes (for example: shop)."
    $name = Read-Host "    Name (Enter to skip)"
    if ($name) {
        & (Join-Path $binDir "cc-kit.cmd") new $name.Trim()
        exit 0
    }
}
Write-Note "Create a Control Center any time, in PowerShell:"
Write-Host  "      cc-kit new my-project"
Write-Note "It opens Claude and the agent walks you through the setup. More: GUIDE.md in the kit."
