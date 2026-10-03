# Correção da escolaridade (VD3004 no lugar da V3009A): backup, reextração dos ZIPs,
# reconstrução de features.parquet e checagem de sanidade. Nada é apagado: os arquivos
# anteriores ficam com o sufixo .pre_educ.
# Lançar destacado:  Start-Process powershell -ArgumentList '-File','tcc\scripts\fila_educ.ps1' -WindowStyle Hidden
$root = "C:\Users\user\Documents\ProjetoRacismoPNAD"
$st   = "$root\outputs\logs\fila_educ_status.log"
$py   = "C:\Users\user\AppData\Local\spyder-6\python.exe"
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"

Add-Content $st "$(Get-Date -Format s) INICIO backup"
Get-ChildItem "$root\data\processed" -Recurse -Filter "extras.parquet" | ForEach-Object {
    Move-Item $_.FullName ($_.FullName -replace "extras\.parquet$", "extras.pre_educ.parquet") -Force
}
if (-not (Test-Path "$root\data\processed\features.parquet.pre_educ")) {
    Copy-Item "$root\data\processed\features.parquet" "$root\data\processed\features.parquet.pre_educ"
}
Add-Content $st "$(Get-Date -Format s) OK backup"

$passos = @(
    @("enrich_raw",      "python -u scripts/analise/run_enrich_raw.py"),
    @("features",        "`"$py`" -u scripts/analise/run_features_completo.py"),
    @("checa_educ",      "`"$py`" -u tcc/scripts/checar_escolaridade.py")
)
foreach ($p in $passos) {
    $nome = $p[0]; $log = "$root\outputs\logs\educ_$nome.log"
    Add-Content $st "$(Get-Date -Format s) INICIO $nome"
    cmd /c "$($p[1]) > `"$log`" 2>&1"
    $res = if ($LASTEXITCODE -eq 0) { "OK" } else { "FALHOU(rc=$LASTEXITCODE)" }
    Add-Content $st "$(Get-Date -Format s) $res $nome"
    if ($res -ne "OK") { break }
}
Add-Content $st "$(Get-Date -Format s) FIM_FILA"
