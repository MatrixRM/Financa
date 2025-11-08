# Script de Restauração do PostgreSQL
# Execute: .\restore_postgresql.ps1 -BackupFile "backups\financa_backup_20251027_123456.sql"

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "    Restauração PostgreSQL - Financa DB    " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se arquivo existe
if (-not (Test-Path $BackupFile)) {
    Write-Host "❌ Arquivo de backup não encontrado: $BackupFile" -ForegroundColor Red
    exit 1
}

# Carregar variáveis do .env
if (-not (Test-Path ".env")) {
    Write-Host "❌ Arquivo .env não encontrado!" -ForegroundColor Red
    exit 1
}

$envVars = @{}
Get-Content ".env" | ForEach-Object {
    if ($_ -match "^\s*([^#][^=]*?)\s*=\s*(.+?)\s*$") {
        $envVars[$matches[1]] = $matches[2]
    }
}

$DB_NAME = $envVars["DB_NAME"]
$DB_USER = $envVars["DB_USER"]
$DB_PASSWORD = $envVars["DB_PASSWORD"]
$DB_HOST = $envVars["DB_HOST"]
$DB_PORT = $envVars["DB_PORT"]

Write-Host "Banco: $DB_NAME" -ForegroundColor Yellow
Write-Host "Usuário: $DB_USER" -ForegroundColor Yellow
Write-Host "Arquivo: $BackupFile" -ForegroundColor Yellow
Write-Host ""

# Confirmar
$confirm = Read-Host "⚠️  ATENÇÃO: Isso irá SOBRESCREVER todos os dados atuais! Digite 'SIM' para continuar"
if ($confirm -ne "SIM") {
    Write-Host "Operação cancelada." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Restaurando backup..." -ForegroundColor Yellow

# Executar psql
$env:PGPASSWORD = $DB_PASSWORD
try {
    psql -U $DB_USER -h $DB_HOST -p $DB_PORT -d $DB_NAME -f $BackupFile

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Backup restaurado com sucesso!" -ForegroundColor Green
    } else {
        Write-Host "❌ Erro ao restaurar backup" -ForegroundColor Red
        exit 1
    }
} finally {
    $env:PGPASSWORD = $null
}

Write-Host ""
Write-Host "Reinicie o servidor Django:" -ForegroundColor Yellow
Write-Host "  python manage.py runserver" -ForegroundColor Gray
Write-Host ""
