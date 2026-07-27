$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
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
$RdpHost = "target-pc"
$RdpPort = 3389
$RdpWaitSeconds = 180

$Headers = @{
  Authorization = "Bearer $Token"
  "Content-Type" = "application/json"
}

function Show-Message($Text) {
  (New-Object -ComObject WScript.Shell).Popup($Text, 5, "PC Power", 64) | Out-Null
}

function Log($Text) {
  Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Text"
}

function Get-HaState($EntityId) {
  Invoke-RestMethod -Headers $Headers -Uri "$HaUrl/api/states/$EntityId"
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
  Log "Waiting for RDP: $RdpHost`:$RdpPort"
  $Deadline = (Get-Date).AddSeconds($RdpWaitSeconds)
  $Attempt = 1

  while ((Get-Date) -lt $Deadline) {
    if (Test-TcpPort $RdpHost $RdpPort 3000) {
      Log "RDP is reachable. Opening mstsc."
      Start-Process "mstsc.exe" -ArgumentList "/v:$RdpHost", "/f"
      return
    }

    Log "RDP not reachable yet. Retrying in 5 seconds. Attempt $Attempt."
    $Attempt++
    Start-Sleep -Seconds 5
  }

  Log "RDP did not become reachable within $RdpWaitSeconds seconds"
  Show-Message "PC power action finished, but RDP is not reachable yet."
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
    Show-Message "Set HA_TOKEN in .env."
    exit
  }

  Log "Checking Tailscale on this laptop"
  $TailscaleOk = Test-TailscaleConnection

  if ($TailscaleOk -eq $false) {
    Log "Tailscale is not connected"
    Show-Message "Tailscale is not connected on this laptop."
    Start-Sleep -Seconds 3
    exit
  }

  if ($TailscaleOk -eq $null) {
    Log "Tailscale CLI was not found. Skipping direct Tailscale check."
  }

  Log "Checking Home Assistant: $HaUrl"

  if (-not (Test-HaConnection)) {
    Log "Home Assistant is not reachable"
    Show-Message "Cannot reach Home Assistant at $HaUrl."
    Start-Sleep -Seconds 3
    exit
  }

  Log "Reading plug state: $PlugEntity"
  $Plug = Get-HaState $PlugEntity
  Log "Reading power sensor: $WattEntity"
  $Watt = [double](Get-HaState $WattEntity).state
  Log "Plug=$($Plug.state), Power=$Watt W"

  if ($Plug.state -eq "off") {
    Log "Decision: plug is off, so turning it on."
    Set-Plug "on"
    Show-Message "PC power has been turned on"
    Start-Rdp
    Start-Sleep -Seconds 3
    exit
  }

  if ($Watt -ge $ThresholdW) {
    Log "Decision: power is at or above $ThresholdW W, so PC is already on."
    Show-Message "PC is already on ($Watt W)"
    Start-Rdp
    Start-Sleep -Seconds 3
    exit
  }

  Log "Decision: plug is on but power is below $ThresholdW W. Waiting 30 seconds."
  Start-Sleep -Seconds 30
  $Watt = [double](Get-HaState $WattEntity).state
  Log "Power after wait=$Watt W"

  if ($Watt -lt $ThresholdW) {
    Log "Decision: still below $ThresholdW W, so power cycling plug."
    Set-Plug "off"
    Start-Sleep -Seconds 3
    Set-Plug "on"
    Show-Message "PC boot has been started"
    Start-Rdp
  } else {
    Log "Decision: power rose to $Watt W, so PC is already on."
    Show-Message "PC is already on ($Watt W)"
    Start-Rdp
  }
} catch {
  Log "Error: $($_.Exception.Message)"
  if ($_.Exception.Response.StatusCode.value__ -eq 401) {
    Show-Message "Home Assistant authentication failed. Check the access token."
  } else {
    Show-Message "Failed to check power state"
  }
}

Start-Sleep -Seconds 3
