# Laço destacado: um processo Rscript por modelo GLMM, até as 12 linhas do csv.
$root = "C:\Users\user\Documents\ProjetoRacismoPNAD"
$csv  = "$root\outputs\tables\glmm_glassceil_glmer.csv"
$log  = "$root\outputs\logs\glmm_loo_loop.log"
$rs   = "C:\Program Files\R\R-4.6.0\bin\Rscript.exe"
New-Item -ItemType Directory -Force "$root\outputs\logs" | Out-Null
Set-Location $root
function Linhas { if (Test-Path $csv) { (Import-Csv $csv).Count } else { 0 } }
for ($i = 1; $i -le 14; $i++) {
    $antes = Linhas
    if ($antes -ge 12) { break }
    Add-Content $log "=== $(Get-Date -Format s) iteração $i — $antes/12 modelos ==="
    & $rs "scripts/R/glmm_glassceil.R" "--one" *>> $log
    $depois = Linhas
    if ($depois -le $antes) { Add-Content $log "!!! sem progresso (código $LASTEXITCODE) — abortando"; break }
}
Add-Content $log "=== $(Get-Date -Format s) FIM — $(Linhas)/12 modelos ==="
