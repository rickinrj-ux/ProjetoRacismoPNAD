# Fila do E2 (03/10/2026): especificação (A) ≡ M3 em Oaxaca/QR/RIF (E2.5: + jornada, urbano,
# UF) e escada aninhada do HLM (E2.2: M1 com UF). Espera o ajuste do M1_UF terminar antes de
# começar — os dois juntos em 7,7 milhões de linhas disputariam a memória.
# Lançar destacado:  Start-Process powershell -ArgumentList '-File','tcc\scripts\fila_e2.ps1' -WindowStyle Hidden
param([string]$Desde = "")
$root = "C:\Users\user\Documents\ProjetoRacismoPNAD"
$st   = "$root\outputs\logs\fila_e2_status.log"
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"

Add-Content $st "$(Get-Date -Format s) ESPERANDO M1_UF"
while (-not (Select-String -Path "$root\outputs\logs\hlm_m1_uf.log" -Pattern "FIM rc=" -Quiet)) {
    Start-Sleep -Seconds 60
}
Add-Content $st "$(Get-Date -Format s) M1_UF: $((Get-Content "$root\outputs\logs\hlm_m1_uf.log" -Tail 1))"

$passos = @(
    @("m1_uf_export",  "python -u scripts/analise/exportar_m1_uf.py"),
    @("qr",            "python -u scripts/analise/run_regressao_quantilica.py"),
    @("ob_qr",         "python -u scripts/analise/run_ob_qr_melhorias.py"),
    # o RIF tem checkpoint por quantil: esvaziar antes, senão reaproveita a especificação velha
    @("rif_limpa",     "del /q outputs\tables\rif_checkpoints\rif_q*.csv"),
    @("rif_decomp",    "python -u scripts/analise/run_rif_decomp.py"),
    @("rif_inter_se",  "python -u scripts/analise/run_se_rif_interseccional.py"),
    # tabelas, figuras, relatório, PDFs, Word, decks, validate e portões anti-fóssil
    @("regeneracao",   "powershell -NoProfile -ExecutionPolicy Bypass -File tcc\scripts\fila_loo2.ps1 -Desde tabelas_compl")
)
$pular = [bool]$Desde
foreach ($p in $passos) {
    if ($pular -and $p[0] -ne $Desde) { continue }
    $pular = $false
    $nome = $p[0]; $log = "$root\outputs\logs\e2_$nome.log"
    Add-Content $st "$(Get-Date -Format s) INICIO $nome"
    cmd /c "$($p[1]) > `"$log`" 2>&1"
    $rc = $LASTEXITCODE
    $res = if ($rc -eq 0) { "OK" } else { "FALHOU(rc=$rc)" }
    Add-Content $st "$(Get-Date -Format s) $res $nome"
}
Add-Content $st "$(Get-Date -Format s) FIM_FILA"
