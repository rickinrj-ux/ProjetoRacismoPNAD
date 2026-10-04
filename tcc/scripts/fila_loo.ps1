# Fila da reestimação leave-one-out (itens 2-10 de tcc/revisoes/RETOMADA_reestimacao_loo.md).
# Lançar destacado:  Start-Process powershell -ArgumentList '-File','tcc\scripts\fila_loo.ps1' -WindowStyle Hidden
# Cada passo grava outputs/logs/loo_<nome>.log; o resumo vai em outputs/logs/fila_loo_status.log.
$root = "C:\Users\user\Documents\ProjetoRacismoPNAD"
$rs   = "C:\Program Files\R\R-4.6.0\bin\Rscript.exe"
$st   = "$root\outputs\logs\fila_loo_status.log"
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
$passos = @(
    @("rif_interseccional", "python -u scripts/analise/run_se_rif_interseccional.py"),
    @("ob_qr_melhorias",    "python -u scripts/analise/run_ob_qr_melhorias.py"),
    @("ml_cv",              "python -u scripts/analise/run_ml_cv.py"),
    @("vif",                "python -u scripts/analise/run_vif_multicolinearidade.py"),
    @("qr_so_area",         "python -u scripts/analise/run_regressao_quantilica.py --so-area"),
    @("gini_raca",          "python -u scripts/analise/run_gini_raca.py"),
    @("hlm3_M0",            "`"$rs`" scripts/R/hlm_tres_niveis.R M0"),
    @("hlm3_M2",            "`"$rs`" scripts/R/hlm_tres_niveis.R M2"),
    @("grupo_rg_topo",      "`"$rs`" scripts/R/run_grupo_rg_topo.R"),
    @("ml_shap",            "python -u scripts/analise/run_ml_shap.py")
)
foreach ($p in $passos) {
    $nome = $p[0]; $log = "$root\outputs\logs\loo_$nome.log"
    Add-Content $st "$(Get-Date -Format s) INICIO $nome"
    cmd /c "$($p[1]) > `"$log`" 2>&1"
    $rc = $LASTEXITCODE
    $res = if ($rc -eq 0) { "OK" } else { "FALHOU(rc=$rc)" }
    Add-Content $st "$(Get-Date -Format s) $res $nome"
}
Add-Content $st "$(Get-Date -Format s) FIM_FILA"
