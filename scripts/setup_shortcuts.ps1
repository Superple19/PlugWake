$ScriptDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Desktop = [Environment]::GetFolderPath("Desktop")

function New-BatShortcut($Name, $Target, $IconPath, $IconIndex) {
  $ShortcutPath = Join-Path $Desktop "$Name.lnk"
  $Shell = New-Object -ComObject WScript.Shell
  $Shortcut = $Shell.CreateShortcut($ShortcutPath)

  $Shortcut.TargetPath = $Target
  $Shortcut.WorkingDirectory = $ScriptDir
  $Shortcut.IconLocation = "$IconPath,$IconIndex"
  $Shortcut.Save()

  Write-Host "Created: $ShortcutPath"
}

New-BatShortcut `
  -Name "Remote On" `
  -Target (Join-Path $ScriptDir "power_on_pc.bat") `
  -IconPath (Join-Path $ScriptDir "assets\icons\power-on-v2.ico") `
  -IconIndex 0

New-BatShortcut `
  -Name "Remote Off" `
  -Target (Join-Path $ScriptDir "power_off_pc.bat") `
  -IconPath (Join-Path $ScriptDir "assets\icons\power-off-v2.ico") `
  -IconIndex 0
