# Fila R do módulo de heterogeneidade (04/10/2026): 10 GLMMs, um por processo
$root = "C:\Users\user\Documents\ProjetoRacismoPNAD"
$st   = "$root\outputs\logs\fila_het_r_status.log"
$rs   = "C:\Program Files\R\R-4.6.0\bin\Rscript.exe"
Set-Location $root
$passos = @(
    @("cor3_ocp",   "cor3 ocp_qualif"), @("cor3_t20", "cor3 y_top20"), @("cor3_t10", "cor3 y_top10"),
    @("setor0_ocp", "setor ocp_qualif 0"), @("setor1_ocp", "setor ocp_qualif 1"),
    @("setor0_t20", "setor y_top20 0"), @("setor1_t20", "setor y_top20 1"),
    @("setor0_t10", "setor y_top10 0"), @("setor1_t10", "setor y_top10 1"),
    @("topuf",      "topuf y_top10_uf")
)
foreach ($p in $passos) {
    $nome = $p[0]; $log = "$root\outputs\logs\het_r_$nome.log"
    Add-Content $st "$(Get-Date -Format s) INICIO $nome"
    cmd /c "`"$rs`" scripts/R/run_glmm_heterogeneidade.R $($p[1]) > `"$log`" 2>&1"
    $res = if ($LASTEXITCODE -eq 0) { "OK" } else { "FALHOU(rc=$LASTEXITCODE)" }
    Add-Content $st "$(Get-Date -Format s) $res $nome"
}
Add-Content $st "$(Get-Date -Format s) FIM_FILA"
