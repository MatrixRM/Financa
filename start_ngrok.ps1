# Script para Iniciar Servidor com ngrok
# start_ngrok.ps1

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   INICIANDO SERVIDOR COM NGROK" -ForegroundColor Cyan
Write-Host "   Para acessar biometria no celular" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se ngrok está instalado
if (-not (Test-Path ".\ngrok.exe")) {
    Write-Host "[ERRO] ngrok.exe nao encontrado!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Como instalar:" -ForegroundColor Yellow
    Write-Host "1. Acesse: https://ngrok.com/download" -ForegroundColor White
    Write-Host "2. Baixe o ngrok para Windows" -ForegroundColor White
    Write-Host "3. Extraia o arquivo ngrok.exe nesta pasta:" -ForegroundColor White
    Write-Host "   C:\Users\rober\Desktop\Financa\" -ForegroundColor White
    Write-Host ""
    Write-Host "Ou use o comando:" -ForegroundColor Yellow
    Write-Host "   choco install ngrok" -ForegroundColor White
    Write-Host ""
    Read-Host "Pressione Enter para sair"
    exit
}

Write-Host "[OK] ngrok encontrado!" -ForegroundColor Green
Write-Host ""

# Iniciar Django em background
Write-Host "[*] Iniciando servidor Django..." -ForegroundColor Blue
$djangoJob = Start-Job -ScriptBlock {
    Set-Location "C:\Users\rober\Desktop\Financa"
    python manage.py runserver 0.0.0.0:8000
}

Write-Host "[*] Aguardando Django inicializar (5 segundos)..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Verificar se Django iniciou
$jobOutput = Receive-Job -Job $djangoJob -Keep
if ($jobOutput -match "error|exception") {
    Write-Host ""
    Write-Host "[ERRO] Falha ao iniciar Django!" -ForegroundColor Red
    Write-Host $jobOutput
    Stop-Job $djangoJob
    Remove-Job $djangoJob
    Read-Host "Pressione Enter para sair"
    exit
}

Write-Host "[OK] Django rodando em http://localhost:8000" -ForegroundColor Green
Write-Host ""

# Iniciar ngrok
Write-Host "========================================================" -ForegroundColor Magenta
Write-Host "   INICIANDO NGROK" -ForegroundColor Magenta
Write-Host "========================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "[!] Copie a URL HTTPS que aparecera abaixo" -ForegroundColor Yellow
Write-Host "[!] Use essa URL no seu celular" -ForegroundColor Yellow
Write-Host ""
Write-Host "[IMPORTANTE] Adicione a URL no settings.py:" -ForegroundColor Cyan
Write-Host "   CSRF_TRUSTED_ORIGINS.append('https://sua-url.ngrok.io')" -ForegroundColor White
Write-Host ""
Write-Host "[*] Para parar: Pressione Ctrl+C" -ForegroundColor Red
Write-Host ""
Write-Host "========================================================" -ForegroundColor Gray
Write-Host ""

# Iniciar ngrok (em primeiro plano)
try {
    .\ngrok http 8000
} finally {
    # Limpar quando ngrok for fechado
    Write-Host ""
    Write-Host "[*] Parando servidor Django..." -ForegroundColor Yellow
    Stop-Job $djangoJob -ErrorAction SilentlyContinue
    Remove-Job $djangoJob -ErrorAction SilentlyContinue
    Write-Host "[OK] Servidor parado!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ate logo!" -ForegroundColor Cyan
    Write-Host ""
}
