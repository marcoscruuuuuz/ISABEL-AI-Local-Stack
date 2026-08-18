param(
    [Parameter(Mandatory=$true)][string]$InstallKey,
    [string]$ServerApi = "https://ai.seudominio.com.br",
    [string]$InstallDir = "$env:ProgramFiles\ISABEL\agents"
)
$ErrorActionPreference = "Stop"
$MachineId = "$env:COMPUTERNAME-$([guid]::NewGuid().ToString().Substring(0,8))"
$Hostname = $env:COMPUTERNAME
Write-Host "ISABEL Fleet Agent - Claim" -ForegroundColor Cyan
$body = @{ install_key = $InstallKey; machine_id = $MachineId; hostname = $Hostname; version = "1.0.2" } | ConvertTo-Json
$resp = Invoke-RestMethod -Uri "$ServerApi/fleet/agents/claim" -Method POST -Body $body -ContentType "application/json"
Write-Host "Agente: $($resp.agent_name)" -ForegroundColor Green
$AgentDir = Join-Path $InstallDir $resp.agent_name
New-Item -ItemType Directory -Force -Path $AgentDir | Out-Null
$src = Join-Path $PSScriptRoot "fleet_agent.py"
if (Test-Path $src) { Copy-Item $src $AgentDir -Force }
$envContent = @"
ISABEL_VERSION=1.0.2
ISABEL_AGENT_ID=$($resp.agent_id)
ISABEL_AGENT_NAME=$($resp.agent_name)
ISABEL_AGENT_TOKEN=$($resp.agent_token)
ISABEL_SERVER_WSS=wss://$(([uri]$ServerApi).Host)/ws/fleet
ISABEL_API_URL=$ServerApi
ISABEL_LOCAL_URL=http://127.0.0.1:11434
ISABEL_ALLOW_PATHS=$($resp.allow_paths -join ';')
ISABEL_DENY_PATHS=$($resp.deny_paths -join ';')
"@
Set-Content -Path (Join-Path $AgentDir "agent.env") -Value $envContent -Encoding UTF8
Write-Host "Instalado em: $AgentDir" -ForegroundColor Green
Write-Host "Inicie: python fleet_agent.py (com agent.env carregado)"
