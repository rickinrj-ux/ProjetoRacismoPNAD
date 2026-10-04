# Fila Python do módulo de heterogeneidade (04/10/2026): espera o logit ponderado terminar
$root = "C:\Users\user\Documents\ProjetoRacismoPNAD"
$st   = "$root\outputs\logs\fila_het_py_status.log"
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
Add-Content $st "$(Get-Date -Format s) ESPERANDO logit ponderado"
while (-not (Select-String -Path "$root\outputs\logs\robustez_glmm.log" -Pattern "FIM rc=" -Quiet)) { Start-Sleep -Seconds 60 }
$passos = @(
    @("hlm_cor3", "--hlm cor3"), @("hlm_idade", "--hlm idade"),
    @("hlm_setor0", "--hlm setor0"), @("hlm_setor1", "--hlm setor1"),
    @("qr_cor", "--qr"), @("rif_cor", "--rif")
)
foreach ($p in $passos) {
    $nome = $p[0]; $log = "$root\outputs\logs\het_py_$nome.log"
    Add-Content $st "$(Get-Date -Format s) INICIO $nome"
    cmd /c "python -u scripts/analise/run_heterogeneidade.py $($p[1]) > `"$log`" 2>&1"
    $res = if ($LASTEXITCODE -eq 0) { "OK" } else { "FALHOU(rc=$LASTEXITCODE)" }
    Add-Content $st "$(Get-Date -Format s) $res $nome"
}
Add-Content $st "$(Get-Date -Format s) FIM_FILA"
