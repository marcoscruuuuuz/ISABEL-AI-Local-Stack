$ErrorActionPreference = "Stop"
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AgentExe = Join-Path $InstallDir "ISABEL-Agent.exe"
Write-Host "Registrando servico ISABEL Agent..." -ForegroundColor Cyan
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
  Write-Host "NSSM nao encontrado. Baixe de https://nssm.cc" -ForegroundColor Yellow
  Write-Host "nssm install ISABELAgent `"$AgentExe`"" -ForegroundColor White
  exit 0
}
& nssm install ISABELAgent $AgentExe
& nssm set ISABELAgent AppDirectory $InstallDir
& nssm set ISABELAgent DisplayName "ISABEL AI Agent"
& nssm set ISABELAgent Start SERVICE_AUTO_START
& nssm start ISABELAgent
Write-Host "[OK] Servico ISABELAgent instalado." -ForegroundColor Green
