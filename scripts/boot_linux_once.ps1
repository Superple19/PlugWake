$ScriptDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvFile = Join-Path $ScriptDir ".env"

if (Test-Path $EnvFile) {
  Get-Content $EnvFile | ForEach-Object {
    $Line = $_.Trim()

    if ($Line -eq "" -or $Line.StartsWith("#") -or -not $Line.Contains("=")) {
      return
    }

    $Name, $Value = $Line.Split("=", 2)
    [Environment]::SetEnvironmentVariable($Name.Trim(), $Value.Trim().Trim('"'), "Process")
  }
}

$LinuxBootId = $env:LINUX_BOOT_ID

function Log($Text) {
  Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Text"
}

function Test-Admin {
  $Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $Principal = [Security.Principal.WindowsPrincipal]::new($Identity)
  $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
  Log "Run this script as Administrator."
  exit 1
}

if ([string]::IsNullOrWhiteSpace($LinuxBootId)) {
  Log "Set LINUX_BOOT_ID in .env first."
  Log "Run this command to find it:"
  Log "bcdedit /enum firmware"
  exit 1
}

Log "Setting next boot to Linux entry: $LinuxBootId"
& bcdedit /bootsequence $LinuxBootId

if ($LASTEXITCODE -ne 0) {
  Log "Failed to set bootsequence."
  exit $LASTEXITCODE
}

Log "Next boot is set to Linux once."
Log "Restart Windows when ready."
