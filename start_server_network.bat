@echo off
chcp 65001 >nul
title Servidor Django - Acesso pela Rede Local

echo.
echo ============================================================
echo  🌐 SERVIDOR DJANGO - ACESSO PELA REDE LOCAL
echo ============================================================
echo.

REM Ativar ambiente virtual se existir
if exist "venv\Scripts\activate.bat" (
    echo 🔧 Ativando ambiente virtual...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo 🔧 Ativando ambiente virtual...
    call .venv\Scripts\activate.bat
) else (
    echo ⚠️  Ambiente virtual não encontrado. Continuando...
)

echo.
echo 🔍 Detectando seu IP na rede local...
echo.

REM Obter IP local
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do (
    set IP=%%a
    goto :found
)

:found
REM Remover espaços em branco
set IP=%IP: =%

echo 📱 ACESSO DE OUTROS DISPOSITIVOS:
echo    → http://%IP%:8000
echo.
echo 💻 ACESSO LOCAL:
echo    → http://localhost:8000
echo    → http://127.0.0.1:8000
echo.
echo 📋 INSTRUÇÕES:
echo    1. Certifique-se de que os dispositivos estão na mesma rede WiFi
echo    2. No seu celular/tablet, abra o navegador
echo    3. Digite o endereço: http://%IP%:8000
echo    4. Faça login normalmente
echo.
echo ⚠️  IMPORTANTE:
echo    - Seu firewall pode bloquear conexões externas
echo    - Se não funcionar, veja o arquivo GUIA_ACESSO_REDE.md
echo.
echo 🛑 Para parar o servidor: Pressione Ctrl+C
echo.
echo ============================================================
echo.
echo 🚀 Iniciando servidor Django...
echo.

REM Verificar se manage.py existe
if not exist "manage.py" (
    echo ❌ Erro: manage.py não encontrado!
    echo    Execute este script do diretório raiz do projeto.
    pause
    exit /b 1
)

REM Iniciar servidor
python manage.py runserver 0.0.0.0:8000

echo.
echo ✅ Servidor encerrado com sucesso!
pause
