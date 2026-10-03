# Reestimação completa após a correção da escolaridade (VD3004). Roda DEPOIS de fila_educ.ps1.
# Lançar destacado:  Start-Process powershell -ArgumentList '-File','tcc\scripts\fila_reestima.ps1' -WindowStyle Hidden
# Retomar de um passo:  ... -File tcc\scripts\fila_reestima.ps1 -Desde <nome>
param([string]$Desde = "")
$root = "C:\Users\user\Documents\ProjetoRacismoPNAD"
$st   = "$root\outputs\logs\fila_reestima_status.log"
$py   = "C:\Users\user\AppData\Local\spyder-6\python.exe"
$rs   = "C:\Program Files\R\R-4.6.0\bin\Rscript.exe"
$bk   = "$root\outputs\_backup_pre_educ"
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"

# ── 0. Backup e limpeza dos caches/checkpoints que devolveriam resultados antigos ──
# (o N das amostras não muda com a correção: o GLMM e a série "retomariam" do csv velho)
if (-not $Desde) {
    New-Item -ItemType Directory -Force $bk | Out-Null
    Copy-Item "$root\outputs\tables\*.csv" $bk -Force
    Copy-Item "$root\outputs\tables\*.tex" $bk -Force
    foreach ($a in @("glmm_glassceil_glmer.csv", "glmm_glassceil_glmer_coefs.csv",
                     "validacao_temporal.novo.csv", "sensib_educ_missing.csv")) {
        if (Test-Path "$root\outputs\tables\$a") { Move-Item "$root\outputs\tables\$a" "$bk\$a" -Force }
    }
    if (Test-Path "$root\outputs\tables\rif_checkpoints") {
        Move-Item "$root\outputs\tables\rif_checkpoints" "$bk\rif_checkpoints" -Force
    }
    if (Test-Path "$root\outputs\_cache\hlm_stepup") {
        Move-Item "$root\outputs\_cache\hlm_stepup" "$bk\cache_hlm_stepup" -Force
    }
    Add-Content $st "$(Get-Date -Format s) OK backup e limpeza de caches"
}

function Linhas($p) { if (Test-Path $p) { @(Import-Csv $p).Count } else { 0 } }

$passos = @(
    # HLM: um degrau por processo (os seis juntos estouram a memória), depois a montagem
    @("hlm_M0",       "python -u scripts/analise/run_hlm_stepup.py --fit M0"),
    @("hlm_M0_REML",  "python -u scripts/analise/run_hlm_stepup.py --fit M0_REML"),
    @("hlm_M1",       "python -u scripts/analise/run_hlm_stepup.py --fit M1"),
    @("hlm_M2",       "python -u scripts/analise/run_hlm_stepup.py --fit M2"),
    @("hlm_M3",       "python -u scripts/analise/run_hlm_stepup.py --fit M3"),
    @("hlm_M4",       "python -u scripts/analise/run_hlm_stepup.py --fit M4"),
    @("hlm_M3_RS",    "python -u scripts/analise/run_hlm_stepup.py --fit M3_RS"),
    @("hlm_monta",    "python -u scripts/analise/run_hlm_stepup.py"),
    @("glmm",         "GLMM"),                                    # laço próprio abaixo
    @("rif_inter_se", "python -u scripts/analise/run_se_rif_interseccional.py"),
    @("rif_decomp",   "python -u scripts/analise/run_rif_decomp.py"),
    @("ob_qr",        "python -u scripts/analise/run_ob_qr_melhorias.py"),
    @("qr_so_area",   "python -u scripts/analise/run_regressao_quantilica.py --so-area"),
    @("hlm_serie",    "python -u scripts/analise/run_hlm_serie_completa.py"),
    @("oaxaca",       "python -u scripts/analise/run_oaxaca_blinder.py"),
    @("glmm_logit_fe","python -u scripts/analise/run_glmm_glassceil.py"),
    @("konfound",     "python -u scripts/analise/run_konfound_evalues.py"),
    @("ml_cv",        "python -u scripts/analise/run_ml_cv.py"),
    @("vif",          "python -u scripts/analise/run_vif_multicolinearidade.py"),
    @("gini",         "python -u scripts/analise/run_gini_raca.py"),
    @("hlm3_M0",      "`"$rs`" scripts/R/hlm_tres_niveis.R M0"),
    @("hlm3_M2",      "`"$rs`" scripts/R/hlm_tres_niveis.R M2"),
    @("grupo_rg_topo","`"$rs`" scripts/R/run_grupo_rg_topo.R"),
    @("serie_m3",     "SERIE"),                                   # laço próprio abaixo
    @("tendencia",    "python -u scripts/analise/run_tendencia_temporal.py"),
    @("ml_shap",      "python -u scripts/analise/run_ml_shap.py")
)
$pular = [bool]$Desde
foreach ($p in $passos) {
    if ($pular -and $p[0] -ne $Desde) { continue }
    $pular = $false
    $nome = $p[0]; $log = "$root\outputs\logs\reestima_$nome.log"
    Add-Content $st "$(Get-Date -Format s) INICIO $nome"
    $rc = 0
    if ($p[1] -eq "GLMM") {          # 12 modelos, um por processo, retomando pelo csv
        $csv = "$root\outputs\tables\glmm_glassceil_glmer.csv"
        for ($i = 1; $i -le 15 -and (Linhas $csv) -lt 12; $i++) {
            $antes = Linhas $csv
            cmd /c "`"$rs`" scripts/R/glmm_glassceil.R --one >> `"$log`" 2>&1"
            if ((Linhas $csv) -le $antes) { $rc = 1; break }
        }
    } elseif ($p[1] -eq "SERIE") {   # 10 anos, um por processo; a última chamada consolida
        $csv = "$root\outputs\tables\validacao_temporal.novo.csv"
        for ($i = 1; $i -le 13 -and (Linhas $csv) -lt 10; $i++) {
            $antes = Linhas $csv
            cmd /c "python -u scripts/analise/run_m3_serie_sensib.py --serie --um >> `"$log`" 2>&1"
            if ((Linhas $csv) -le $antes) { $rc = 1; break }
        }
        if ($rc -eq 0) { cmd /c "python -u scripts/analise/run_m3_serie_sensib.py --serie --um >> `"$log`" 2>&1" }
    } else {
        cmd /c "$($p[1]) > `"$log`" 2>&1"
        $rc = $LASTEXITCODE
    }
    $res = if ($rc -eq 0) { "OK" } else { "FALHOU(rc=$rc)" }
    Add-Content $st "$(Get-Date -Format s) $res $nome"
}
Add-Content $st "$(Get-Date -Format s) FIM_FILA"
