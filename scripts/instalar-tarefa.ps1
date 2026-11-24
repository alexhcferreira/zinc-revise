# Registra a tarefa "ZincRevise" no Agendador de Tarefas: sobe o servidor ao fazer logon,
# com o MESMO usuário em que o Claude Code está logado (o login do Claude Code é por usuário).
# Depois publica a porta 8443 na internet com o Tailscale Funnel.
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$script = Join-Path $raiz "scripts\iniciar.ps1"

$acao = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`"" `
  -WorkingDirectory $raiz
# No logon e, de garantia, a cada 5 minutos: se o servidor já estiver no ar, o script sai sem fazer nada.
$noLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$aCada5min = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$gatilho = @($noLogon, $aCada5min)
$config = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
  -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName "ZincRevise" -Action $acao -Trigger $gatilho -Settings $config `
  -Principal $principal -Description "Servidor do ZincRevise em 127.0.0.1:3001" -Force | Out-Null
Write-Host "Tarefa 'ZincRevise' registrada: sobe o servidor no logon e confere a cada 5 minutos."

# Porta 8443 aberta na internet (Funnel). A porta 443 (outros sites) não é alterada.
# Para voltar a ser só da tailnet: tailscale funnel --https=8443 off ; tailscale serve --bg --https=8443 http://127.0.0.1:3001
tailscale funnel --bg --https=8443 http://127.0.0.1:3001
Write-Host "Acesse em https://$((tailscale status --json | ConvertFrom-Json).Self.DNSName.TrimEnd('.')):8443"
