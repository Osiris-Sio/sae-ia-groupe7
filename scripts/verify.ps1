# Execution du script de verification Python pre-commit
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root

py -3.11 "$PSScriptRoot\verify.py"
exit $LASTEXITCODE
