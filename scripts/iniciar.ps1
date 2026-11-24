# Sobe o ZincRevise em 127.0.0.1:3001 (só local). O acesso de fora é pelo Tailscale Funnel.
# Chamado pela tarefa agendada no logon e a cada 5 minutos (ver instalar-tarefa.ps1).
# Se o servidor cair por qualquer motivo, este script o religa sozinho.
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
New-Item -ItemType Directory -Force (Join-Path $raiz "data") | Out-Null
$log = Join-Path $raiz "data\servidor.log"
$python = Join-Path $raiz ".venv\Scripts\python.exe"

function Test-PortaOcupada {
    $null -ne (Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue)
}

# Já está rodando (outra cópia deste script ou um servidor aberto à mão): não faz nada.
if (Test-PortaOcupada) { exit 0 }

# Nunca herdar uma API key do ambiente: no modo assinatura ela faria o Claude Code cobrar como API.
Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue

while ($true) {
    Add-Content -Path $log -Value "=== $(Get-Date -Format s) iniciando servidor" -Encoding utf8
    # O uvicorn escreve o log no stderr. O Windows PowerShell 5.1 trata stderr de programa externo
    # como erro, então o redirecionamento fica a cargo do cmd.
    cmd /c "`"$python`" -m uvicorn app.main:app --host 127.0.0.1 --port 3001 >> `"$log`" 2>&1"
    Add-Content -Path $log -Value "=== $(Get-Date -Format s) servidor parou (código $LASTEXITCODE); religando em 5 s" -Encoding utf8
    Start-Sleep -Seconds 5
    if (Test-PortaOcupada) { exit 0 }
}
