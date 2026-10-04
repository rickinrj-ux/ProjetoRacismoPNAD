# Fila do E2.16 (03/10/2026): GLMM dos 4 grupos raça×gênero por grande grupo CBO.
# Espera a fila_e2 terminar (FIM_FILA) — os dois juntos disputariam a memória.
$root = "C:\Users\user\Documents\ProjetoRacismoPNAD"
$st   = "$root\outputs\logs\fila_e216_status.log"
$rs   = "C:\Program Files\R\R-4.6.0\bin\Rscript.exe"
Set-Location $root
Add-Content $st "$(Get-Date -Format s) ESPERANDO fila_e2"
while (-not ((Test-Path "$root\outputs\logs\fila_e2_status.log") -and
             (Select-String -Path "$root\outputs\logs\fila_e2_status.log" -Pattern "FIM_FILA" -Quiet))) {
    Start-Sleep -Seconds 120
}
Add-Content $st "$(Get-Date -Format s) INICIO grupo_rg_por_cbo"
cmd /c "`"$rs`" scripts/R/run_grupo_rg_por_cbo.R > `"$root\outputs\logs\grupo_rg_por_cbo.log`" 2>&1"
$res = if ($LASTEXITCODE -eq 0) { "OK" } else { "FALHOU(rc=$LASTEXITCODE)" }
Add-Content $st "$(Get-Date -Format s) $res grupo_rg_por_cbo"
Add-Content $st "$(Get-Date -Format s) FIM_FILA"
