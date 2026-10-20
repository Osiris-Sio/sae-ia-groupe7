<#
.SYNOPSIS
    Installe le hook Git pre-commit pour exécuter scripts/verify.ps1 automatiquement.
.DESCRIPTION
    Crée le fichier .git/hooks/pre-commit qui appelle scripts/verify.ps1
    avant chaque 'git commit'. Si une vérification échoue, le commit est bloqué.
.EXAMPLE
    .\scripts\install_hook.ps1
#>

$ErrorActionPreference = "Stop"
$gitDir = "$PSScriptRoot\..\.git"

if (-not (Test-Path $gitDir)) {
    Write-Host "❌ Dossier .git introuvable à la racine du projet." -ForegroundColor Red
    exit 1
}

$hooksDir = "$gitDir\hooks"
if (-not (Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
}

$hookPath = "$hooksDir\pre-commit"
$hookContent = @'
#!/bin/sh
powershell.exe -ExecutionPolicy Bypass -File "$(git rev-parse --show-toplevel)/scripts/verify.ps1"
exit $?
'@

Set-Content -Path $hookPath -Value $hookContent -Encoding utf8
Write-Host "✅ Hook Git pre-commit installé avec succès dans .git/hooks/pre-commit !" -ForegroundColor Green
Write-Host "Le script scripts/verify.ps1 sera désormais exécuté automatiquement avant chaque 'git commit'." -ForegroundColor Cyan
