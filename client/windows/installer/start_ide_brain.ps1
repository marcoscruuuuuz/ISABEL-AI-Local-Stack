param([string]$Runtime = "llama", [int]$Port = 11434)
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ModelsDir = Join-Path $InstallDir "models"
$ModelFile = Get-ChildItem -Path $ModelsDir -Filter "*.gguf" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $ModelFile) {
  Write-Host "Nenhum GGUF em $ModelsDir" -ForegroundColor Red
  exit 1
}
Write-Host "Modelo: $($ModelFile.FullName) | Porta: $Port" -ForegroundColor Cyan
$LlamaServer = Join-Path $InstallDir "runtime\llama-server.exe"
if (-not (Test-Path $LlamaServer)) {
  Write-Host "llama-server.exe nao encontrado" -ForegroundColor Red
  exit 1
}
& $LlamaServer -m $ModelFile.FullName --host 127.0.0.1 --port $Port -c 4096
