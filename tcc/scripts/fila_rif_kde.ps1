# RIF com a densidade f(q) estimada na população completa (opção b do autor, 03/10/2026),
# depois a regeneração dos entregáveis a partir da tabela da RIF (fila_loo2 -Desde tab_rif).
# Os checkpoints antigos da RIF foram movidos para outputs/_backup_pre_kde antes.
# Lançar destacado:  Start-Process powershell -ArgumentList '-File','tcc\scripts\fila_rif_kde.ps1' -WindowStyle Hidden
$root = "C:\Users\user\Documents\ProjetoRacismoPNAD"
$st   = "$root\outputs\logs\fila_rif_kde_status.log"
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
$passos = @(
    @("rif_decomp",   "python -u scripts/analise/run_rif_decomp.py"),
    @("rif_inter_se", "python -u scripts/analise/run_se_rif_interseccional.py")
)
foreach ($p in $passos) {
    $nome = $p[0]; $log = "$root\outputs\logs\rifkde_$nome.log"
    Add-Content $st "$(Get-Date -Format s) INICIO $nome"
    cmd /c "$($p[1]) > `"$log`" 2>&1"
    $rc = $LASTEXITCODE
    Add-Content $st "$(Get-Date -Format s) $(if ($rc -eq 0) {'OK'} else {"FALHOU(rc=$rc)"}) $nome"
    if ($rc -ne 0) { Add-Content $st "$(Get-Date -Format s) FIM_FILA (interrompida)"; exit 1 }
}
Add-Content $st "$(Get-Date -Format s) INICIO regeneracao (fila_loo2 -Desde tab_rif)"
& powershell -NoProfile -ExecutionPolicy Bypass -File "$root\tcc\scripts\fila_loo2.ps1" -Desde tab_rif
Add-Content $st "$(Get-Date -Format s) FIM_FILA"
