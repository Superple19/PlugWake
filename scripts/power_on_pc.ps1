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

$HaUrl = $env:HA_URL
$Token = $env:HA_TOKEN
$PlugEntity = $env:PLUG_ENTITY
$WattEntity = $env:WATT_ENTITY
$ThresholdW = if ($env:POWER_THRESHOLD_W) { [double]$env:POWER_THRESHOLD_W } else { 5 }
$RdpHost = $env:RDP_HOST
$RdpPort = 3389
$RdpWaitSeconds = if ($env:RDP_WAIT_SECONDS) { [int]$env:RDP_WAIT_SECONDS } else { 180 }
$LowPowerConfirmations = if ($env:POWER_ON_LOW_CONFIRMATIONS) { [int]$env:POWER_ON_LOW_CONFIRMATIONS } else { 3 }

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

function Test-HaConnection {
  $Uri = [uri]$HaUrl
  $Port = if ($Uri.Port -gt 0) { $Uri.Port } else { 80 }

  Test-TcpPort $Uri.Host $Port 3000
}

function Test-TcpPort($HostName, $Port, $TimeoutMs) {
  $Client = [System.Net.Sockets.TcpClient]::new()

  try {
    $Connect = $Client.BeginConnect($HostName, $Port, $null, $null)

    if (-not $Connect.AsyncWaitHandle.WaitOne($TimeoutMs)) {
      return $false
    }

    $Client.EndConnect($Connect)
    return $true
  } catch {
    return $false
  } finally {
    $Client.Close()
  }
}

function Start-Rdp {
  $ExistingRdp = Get-CimInstance Win32_Process -Filter "name = 'mstsc.exe'" |
    Where-Object { $_.CommandLine -like "*$RdpHost*" }

  if ($ExistingRdp) {
    Log "RDP is already open for $RdpHost."
    return
  }

  Log "Waiting for $RdpHost to come online."
  $Deadline = (Get-Date).AddSeconds($RdpWaitSeconds)
  $Attempt = 1

  while ((Get-Date) -lt $Deadline) {
    if (Test-TcpPort $RdpHost $RdpPort 3000) {
      Log "$RdpHost is online. Opening RDP."
      Start-Process "mstsc.exe" -ArgumentList "/v:$RdpHost", "/f"
      return
    }

    Log "$RdpHost is not ready yet. Retrying in 5 seconds. Attempt $Attempt."
    $Attempt++
    Start-Sleep -Seconds 5
  }

  Log "$RdpHost did not come online within $RdpWaitSeconds seconds"
}

function Test-TailscaleConnection {
  if (-not (Get-Command tailscale -ErrorAction SilentlyContinue)) {
    return $null
  }

  $Status = (& tailscale status 2>$null) -join "`n"

  if ($LASTEXITCODE -ne 0 -or $Status -match "Tailscale is stopped|Logged out|not connected") {
    return $false
  }

  return $true
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

  if ([string]::IsNullOrWhiteSpace($HaUrl) -or [string]::IsNullOrWhiteSpace($PlugEntity) -or [string]::IsNullOrWhiteSpace($WattEntity) -or [string]::IsNullOrWhiteSpace($RdpHost)) {
    Log "Set HA_URL, PLUG_ENTITY, WATT_ENTITY, and RDP_HOST in .env"
    exit
  }

  Log "Checking Tailscale on this laptop"
  $TailscaleOk = Test-TailscaleConnection

  if ($TailscaleOk -eq $false) {
    Log "Tailscale is not connected"
    Start-Sleep -Seconds 3
    exit
  }

  if ($TailscaleOk -eq $null) {
    Log "Tailscale CLI was not found. Skipping direct Tailscale check."
  }

  Log "Checking Home Assistant: $HaUrl"

  if (-not (Test-HaConnection)) {
    Log "Home Assistant is not reachable"
    Start-Sleep -Seconds 3
    exit
  }

  Log "Reading plug state: $PlugEntity"
  $Plug = Get-HaState $PlugEntity
  Log "Reading power sensor: $WattEntity"
  $Watt = Get-Watt
  Log "Plug=$($Plug.state), Power=$Watt W"

  if ($Plug.state -eq "off") {
    Log "Decision: plug is off, so turning it on."
    Set-Plug "on"
    Start-Rdp
    Start-Sleep -Seconds 3
    exit
  }

  if ($Watt -ge $ThresholdW) {
    Log "Decision: power is at or above $ThresholdW W, so PC is already on."
    Start-Rdp
    Start-Sleep -Seconds 3
    exit
  }

  Log "Decision: plug is on but power is below $ThresholdW W. Watching for sustained low power."

  if (Test-TcpPort $RdpHost $RdpPort 3000) {
    Log "$RdpHost is online despite low power. Treating PC as already on."
    Start-Rdp
    Start-Sleep -Seconds 3
    exit
  }

  $LowPowerCount = 1
  Log "Low power confirmation $LowPowerCount/$LowPowerConfirmations."

  while ($LowPowerCount -lt $LowPowerConfirmations) {
    Start-Sleep -Seconds 5
    $Watt = Get-Watt
    Log "Power=$Watt W"

    if ($Watt -lt $ThresholdW) {
      $LowPowerCount++
      Log "Low power confirmation $LowPowerCount/$LowPowerConfirmations."
    } else {
      $LowPowerCount = 0
      Log "Power recovered. PC is already on."
      break
    }
  }

  if ($LowPowerCount -ge $LowPowerConfirmations) {
    Log "Decision: power stayed below $ThresholdW W, so power cycling plug."
    Set-Plug "off"
    Start-Sleep -Seconds 3
    Set-Plug "on"
    Start-Rdp
  } else {
    Start-Rdp
  }
} catch {
  Log "Error: $($_.Exception.Message)"
  if ($_.Exception.Response -and $_.Exception.Response.StatusCode.value__ -eq 401) {
    Log "Home Assistant authentication failed. Check the access token."
  } else {
    Log "Failed to check power state"
  }
}

Start-Sleep -Seconds 3
