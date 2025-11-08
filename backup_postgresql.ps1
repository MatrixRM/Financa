# Script de Backup do PostgreSQL
# Execute: .\backup_postgresql.ps1

param(
    [string]$BackupDir = ".\backups"
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "      Backup PostgreSQL - Financa DB       " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

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

if (-not $DB_NAME) {
    Write-Host "❌ Variáveis do banco não encontradas no .env" -ForegroundColor Red
    exit 1
}

# Criar diretório de backup
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

# Nome do arquivo de backup
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = Join-Path $BackupDir "financa_backup_$timestamp.sql"

Write-Host "Banco: $DB_NAME" -ForegroundColor Yellow
Write-Host "Usuário: $DB_USER" -ForegroundColor Yellow
Write-Host "Destino: $backupFile" -ForegroundColor Yellow
Write-Host ""

Write-Host "Criando backup..." -ForegroundColor Yellow

# Executar pg_dump
$env:PGPASSWORD = $DB_PASSWORD
try {
    pg_dump -U $DB_USER -h $DB_HOST -p $DB_PORT -d $DB_NAME -f $backupFile --clean --if-exists

    if ($LASTEXITCODE -eq 0) {
        $fileSize = (Get-Item $backupFile).Length / 1KB
        Write-Host "✅ Backup criado com sucesso!" -ForegroundColor Green
        Write-Host "   Arquivo: $backupFile" -ForegroundColor Gray
        Write-Host "   Tamanho: $([math]::Round($fileSize, 2)) KB" -ForegroundColor Gray
        
        # Manter apenas os últimos 10 backups
        $backups = Get-ChildItem $BackupDir -Filter "financa_backup_*.sql" | Sort-Object CreationTime -Descending
        if ($backups.Count -gt 10) {
            Write-Host ""
            Write-Host "Removendo backups antigos (mantendo últimos 10)..." -ForegroundColor Yellow
            $backups | Select-Object -Skip 10 | ForEach-Object {
                Remove-Item $_.FullName -Force
                Write-Host "   Removido: $($_.Name)" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "❌ Erro ao criar backup" -ForegroundColor Red
        exit 1
    }
} finally {
    $env:PGPASSWORD = $null
}

Write-Host ""
Write-Host "Para restaurar este backup:" -ForegroundColor Yellow
Write-Host "  psql -U $DB_USER -h $DB_HOST -d $DB_NAME -f $backupFile" -ForegroundColor Gray
Write-Host ""
