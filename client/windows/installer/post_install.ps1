param([switch]$InstallModel)
$ErrorActionPreference = "Stop"
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $InstallDir) { $InstallDir = "C:\Program Files\ISABEL" }
Write-Host "ISABEL AI - Pos-instalacao v1.0.2" -ForegroundColor Cyan
$ModelsDir = Join-Path $InstallDir "models"
$ConfigDir = Join-Path $InstallDir "config"
New-Item -ItemType Directory -Force -Path $ModelsDir, $ConfigDir | Out-Null
$EnvFile = Join-Path $ConfigDir "default.env"
if (Test-Path $EnvFile) {
  $content = Get-Content $EnvFile -Raw
  if ($content -match "ISABEL_MACHINE_ID=\s*$") {
    $machineId = "$env:COMPUTERNAME-$([guid]::NewGuid().ToString().Substring(0,8))"
    $content = $content -replace "ISABEL_MACHINE_ID=", "ISABEL_MACHINE_ID=$machineId"
    Set-Content -Path $EnvFile -Value $content -Encoding UTF8
    Write-Host "[OK] Machine ID: $machineId" -ForegroundColor Green
  }
}
Write-Host "Edite config\default.env com Cloudflare Service Token e ISABEL_SERVER_WSS" -ForegroundColor Yellow
