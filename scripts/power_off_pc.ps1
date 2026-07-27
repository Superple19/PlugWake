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

$HaUrl = "http://ha.example.local:8123"
$Token = $env:HA_TOKEN
$PlugEntity = "switch.smart_plug"
$WattEntity = "sensor.smart_plug_power"
$ThresholdW = 5
$SshTarget = if ($env:PC_SSH_TARGET) { $env:PC_SSH_TARGET } else { "target-pc" }
$ShutdownWaitSeconds = 300
$LowPowerConfirmations = 4

$Headers = @{
  Authorization = "Bearer $Token"
  "Content-Type" = "application/json"
}

function Log($Text) {
  Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Text"
}

function Get-HaState($EntityId) {
  Invoke-RestMethod -Headers $Headers -Uri "$HaUrl/api/states/$EntityId"
}

function Get-Watt {
  $State = (Get-HaState $WattEntity).state
  [double]$Watt = 0

  if (-not [double]::TryParse($State, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$Watt)) {
    throw "Invalid power sensor state: $State"
  }

  $Watt
}

function Set-Plug($State) {
  $Service = if ($State -eq "on") { "turn_on" } else { "turn_off" }
  $Body = @{ entity_id = $PlugEntity } | ConvertTo-Json

  Invoke-RestMethod `
    -Method Post `
    -Headers $Headers `
    -Uri "$HaUrl/api/services/switch/$Service" `
    -Body $Body | Out-Null
}

try {
  if ([string]::IsNullOrWhiteSpace($Token)) {
    Log "Home Assistant token is not configured"
    exit
  }

  Log "Reading plug state: $PlugEntity"
  $Plug = Get-HaState $PlugEntity
  Log "Reading power sensor: $WattEntity"
  $Watt = Get-Watt
  Log "Plug=$($Plug.state), Power=$Watt W"

  if ($Plug.state -eq "off") {
    Log "Decision: plug is already off."
    exit
  }

  if ($Watt -ge $ThresholdW) {
    if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
      Log "SSH command was not found"
      exit
    }

    Log "Decision: PC appears to be running. Sending shutdown over SSH to $SshTarget."
    & ssh $SshTarget "shutdown /s /t 0"

    if ($LASTEXITCODE -ne 0) {
      Log "SSH shutdown failed"
      exit
    }

    Log "SSH shutdown sent. Waiting for power to drop below $ThresholdW W."
    $Deadline = (Get-Date).AddSeconds($ShutdownWaitSeconds)
    $LowPowerCount = 0

    while ((Get-Date) -lt $Deadline) {
      Start-Sleep -Seconds 5
      $Watt = Get-Watt
      Log "Power=$Watt W"

      if ($Watt -lt $ThresholdW) {
        $LowPowerCount++
        Log "Low power confirmation $LowPowerCount/$LowPowerConfirmations."

        if ($LowPowerCount -ge $LowPowerConfirmations) {
          Log "Power stayed below $ThresholdW W."
          break
        }
      } else {
        $LowPowerCount = 0
      }
    }

    if ($LowPowerCount -lt $LowPowerConfirmations) {
      Log "Timed out waiting for shutdown. Not cutting power."
      exit
    }
  }

  Log "Decision: power is below $ThresholdW W, so turning plug off."
  Set-Plug "off"
} catch {
  Log "Error: $($_.Exception.Message)"
  Log "Failed to turn off PC plug."
}
