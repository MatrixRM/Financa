# Script PowerShell para iniciar o servidor Django com acesso pela rede local
# Exibe automaticamente o IP da máquina para facilitar o acesso de outros dispositivos

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " 🌐 SERVIDOR DJANGO - ACESSO PELA REDE LOCAL" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Obter o IP local da máquina
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.254.*"} | Select-Object -First 1).IPAddress

if (-not $localIP) {
    Write-Host "⚠️  Não foi possível detectar o IP local automaticamente." -ForegroundColor Yellow
    $localIP = "SEU_IP_AQUI"
}

$port = 8000

# Exibir informações de acesso
Write-Host "📱 ACESSO DE OUTROS DISPOSITIVOS:" -ForegroundColor Green
Write-Host "   → http://$localIP`:$port" -ForegroundColor White
Write-Host ""
Write-Host "💻 ACESSO LOCAL:" -ForegroundColor Green
Write-Host "   → http://localhost:$port" -ForegroundColor White
Write-Host "   → http://127.0.0.1:$port" -ForegroundColor White
Write-Host ""
Write-Host "📋 INSTRUÇÕES:" -ForegroundColor Yellow
Write-Host "   1. Certifique-se de que os dispositivos estão na mesma rede WiFi"
Write-Host "   2. No seu celular/tablet, abra o navegador"
Write-Host "   3. Digite o endereço: http://$localIP`:$port"
Write-Host "   4. Faça login normalmente"
Write-Host ""
Write-Host "⚠️  IMPORTANTE:" -ForegroundColor Red
Write-Host "   - Seu firewall pode bloquear conexões externas"
Write-Host "   - Se não funcionar, execute este comando como Administrador:"
Write-Host "     netsh advfirewall firewall add rule name=`"Django Dev`" dir=in action=allow protocol=TCP localport=$port"
Write-Host ""
Write-Host "🛑 Para parar o servidor: Pressione Ctrl+C" -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se manage.py existe
if (-not (Test-Path "manage.py")) {
    Write-Host "❌ Erro: manage.py não encontrado!" -ForegroundColor Red
    Write-Host "   Execute este script do diretório raiz do projeto." -ForegroundColor Yellow
    Read-Host "Pressione Enter para sair"
    exit 1
}

# Verificar se o ambiente virtual está ativado
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️  Ambiente virtual não detectado. Tentando ativar..." -ForegroundColor Yellow
    
    if (Test-Path "venv\Scripts\Activate.ps1") {
        Write-Host "   Ativando venv..." -ForegroundColor Cyan
        & "venv\Scripts\Activate.ps1"
    } elseif (Test-Path ".venv\Scripts\Activate.ps1") {
        Write-Host "   Ativando .venv..." -ForegroundColor Cyan
        & ".venv\Scripts\Activate.ps1"
    } else {
        Write-Host "   ⚠️  Nenhum ambiente virtual encontrado. Continuando mesmo assim..." -ForegroundColor Yellow
    }
}

Write-Host "🚀 Iniciando servidor Django..." -ForegroundColor Green
Write-Host ""

# Iniciar o servidor
try {
    & python manage.py runserver "0.0.0.0:$port"
} catch {
    Write-Host ""
    Write-Host "❌ Erro ao iniciar o servidor: $_" -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
}

Write-Host ""
Write-Host "✅ Servidor encerrado com sucesso!" -ForegroundColor Green
