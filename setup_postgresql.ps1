# Script de Setup do PostgreSQL para Controle de Despesas
# Execute como administrador: .\setup_postgresql.ps1

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Setup PostgreSQL - Controle de Despesas  " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se PostgreSQL está instalado
Write-Host "1. Verificando instalação do PostgreSQL..." -ForegroundColor Yellow
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue

if (-not $psqlPath) {
    Write-Host "❌ PostgreSQL não encontrado!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Por favor, instale o PostgreSQL:" -ForegroundColor Yellow
    Write-Host "  1. Baixar: https://www.postgresql.org/download/windows/" -ForegroundColor White
    Write-Host "  2. Ou via Chocolatey: choco install postgresql" -ForegroundColor White
    Write-Host "  3. Ou via Scoop: scoop install postgresql" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "✅ PostgreSQL encontrado: $($psqlPath.Source)" -ForegroundColor Green
Write-Host ""

# Configurações
$DB_NAME = "financa_db"
$DB_USER = "financa_user"
$DB_PASSWORD = Read-Host "Digite a senha para o usuário 'financa_user'" -AsSecureString
$DB_PASSWORD_TEXT = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($DB_PASSWORD))

$POSTGRES_PASSWORD = Read-Host "Digite a senha do usuário 'postgres'" -AsSecureString
$POSTGRES_PASSWORD_TEXT = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($POSTGRES_PASSWORD))

Write-Host ""
Write-Host "2. Criando banco de dados '$DB_NAME'..." -ForegroundColor Yellow

# Criar arquivo SQL temporário
$sqlScript = @"
-- Criar banco de dados
CREATE DATABASE $DB_NAME
    WITH 
    ENCODING = 'UTF8'
    LC_COLLATE = 'Portuguese_Brazil.1252'
    LC_CTYPE = 'Portuguese_Brazil.1252'
    TEMPLATE = template0;

-- Criar usuário
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD_TEXT';

-- Dar permissões
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Conectar ao banco e dar permissões no schema
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
"@

$sqlFile = "temp_setup.sql"
$sqlScript | Out-File -FilePath $sqlFile -Encoding UTF8

# Executar SQL
$env:PGPASSWORD = $POSTGRES_PASSWORD_TEXT
try {
    psql -U postgres -f $sqlFile 2>&1 | ForEach-Object {
        if ($_ -match "ERROR") {
            Write-Host "⚠️  $_" -ForegroundColor Yellow
        } else {
            Write-Host "   $_" -ForegroundColor Gray
        }
    }
    Write-Host "✅ Banco de dados criado com sucesso!" -ForegroundColor Green
} catch {
    Write-Host "❌ Erro ao criar banco: $_" -ForegroundColor Red
    Remove-Item $sqlFile -ErrorAction SilentlyContinue
    exit 1
} finally {
    Remove-Item $sqlFile -ErrorAction SilentlyContinue
    $env:PGPASSWORD = $null
}

Write-Host ""
Write-Host "3. Criando arquivo .env..." -ForegroundColor Yellow

$envContent = @"
# Django Settings
SECRET_KEY=django-insecure-$(New-Guid)-change-in-production
DEBUG=True

# PostgreSQL Database
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD_TEXT
DB_HOST=localhost
DB_PORT=5432
"@

if (Test-Path ".env") {
    Write-Host "⚠️  Arquivo .env já existe. Criando backup..." -ForegroundColor Yellow
    Copy-Item ".env" ".env.backup" -Force
    Write-Host "   Backup salvo em: .env.backup" -ForegroundColor Gray
}

$envContent | Out-File -FilePath ".env" -Encoding UTF8 -Force
Write-Host "✅ Arquivo .env criado!" -ForegroundColor Green
Write-Host ""

Write-Host "4. Aplicando migrações do Django..." -ForegroundColor Yellow
Write-Host ""

# Ativar ambiente virtual se existir
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "   Ativando ambiente virtual..." -ForegroundColor Gray
    & "venv\Scripts\Activate.ps1"
}

# Aplicar migrações
Write-Host "   Executando: python manage.py migrate" -ForegroundColor Gray
python manage.py migrate

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Migrações aplicadas com sucesso!" -ForegroundColor Green
} else {
    Write-Host "❌ Erro ao aplicar migrações" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "           Setup Concluído! 🎉             " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Próximos passos:" -ForegroundColor Yellow
Write-Host "  1. Criar superusuário:" -ForegroundColor White
Write-Host "     python manage.py createsuperuser" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Rodar o servidor:" -ForegroundColor White
Write-Host "     python manage.py runserver" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Acessar:" -ForegroundColor White
Write-Host "     http://127.0.0.1:8000" -ForegroundColor Gray
Write-Host ""
Write-Host "Credenciais do banco:" -ForegroundColor Yellow
Write-Host "  Banco: $DB_NAME" -ForegroundColor White
Write-Host "  Usuário: $DB_USER" -ForegroundColor White
Write-Host "  Host: localhost:5432" -ForegroundColor White
Write-Host ""
Write-Host "Para conectar via pgAdmin ou psql:" -ForegroundColor Yellow
Write-Host "  psql -U $DB_USER -d $DB_NAME -h localhost" -ForegroundColor Gray
Write-Host ""
