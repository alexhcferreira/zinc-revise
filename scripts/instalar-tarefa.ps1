# Registra a tarefa "ZincRevise" no Agendador de Tarefas: sobe o servidor ao fazer logon,
# com o MESMO usuário em que o Claude Code está logado (o login do Claude Code é por usuário).
# Depois libera a porta 8443 só na tailnet (sem Funnel).
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$script = Join-Path $raiz "scripts\iniciar.ps1"

$acao = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`"" `
  -WorkingDirectory $raiz
$gatilho = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$config = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName "ZincRevise" -Action $acao -Trigger $gatilho -Settings $config `
  -Principal $principal -Description "Servidor do ZincRevise em 127.0.0.1:3001" -Force | Out-Null
Write-Host "Tarefa 'ZincRevise' registrada. Ela sobe o servidor no próximo logon."

# Porta 8443 só na tailnet. O Funnel da porta 443 (outros sites) não é alterado.
tailscale serve --bg --https=8443 http://127.0.0.1:3001
Write-Host "Acesse em https://$((tailscale status --json | ConvertFrom-Json).Self.DNSName.TrimEnd('.')):8443"
