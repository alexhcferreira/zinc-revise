# Sobe o ZincRevise em 127.0.0.1:3001 (só local). O acesso de fora é pelo `tailscale serve`.
# Chamado pela tarefa agendada no logon (ver instalar-tarefa.ps1).
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
New-Item -ItemType Directory -Force (Join-Path $raiz "data") | Out-Null
$log = Join-Path $raiz "data\servidor.log"
$python = Join-Path $raiz ".venv\Scripts\python.exe"
# Nunca herdar uma API key do ambiente: no modo assinatura ela faria o Claude Code cobrar como API.
Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
# O uvicorn escreve o log no stderr. O Windows PowerShell 5.1 trata stderr de programa externo
# como erro, então o redirecionamento fica a cargo do cmd.
cmd /c "`"$python`" -m uvicorn app.main:app --host 127.0.0.1 --port 3001 >> `"$log`" 2>&1"
