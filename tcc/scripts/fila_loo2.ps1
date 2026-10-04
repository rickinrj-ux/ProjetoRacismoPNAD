# Segunda fila da reestimação leave-one-out: insumos do núcleo que ficaram de fora da
# primeira fila (usam as médias de contexto ou dependem de quem usa), os geradores de
# tabela que o run_tcc.ps1 não chama, e a regeneração do documento (item 11-12 da retomada).
# Lançar destacado:  Start-Process powershell -ArgumentList '-File','tcc\scripts\fila_loo2.ps1' -WindowStyle Hidden
param([string]$Desde = "")   # retomar a partir deste passo (ex.: -Desde relatorio)
$root = "C:\Users\user\Documents\ProjetoRacismoPNAD"
$st   = "$root\outputs\logs\fila_loo2_status.log"
$py   = "C:\Users\user\AppData\Local\spyder-6\python.exe"   # o mesmo do run_tcc.ps1
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
$passos = @(
    # análises: OLS-FE em série, Oaxaca, logit FE-UF (robustez do GLMM), E-value/Konfound
    @("hlm_serie_completa", "python -u scripts/analise/run_hlm_serie_completa.py"),
    @("oaxaca_blinder",     "python -u scripts/analise/run_oaxaca_blinder.py"),
    @("glmm_logit_fe",      "python -u scripts/analise/run_glmm_glassceil.py"),
    @("konfound_evalues",   "python -u scripts/analise/run_konfound_evalues.py"),
    # RIF pontual: tem checkpoint por quantil em outputs/tables/rif_checkpoints (esvaziar antes!)
    @("rif_decomp",         "python -u scripts/analise/run_rif_decomp.py"),
    # geradores fora do run_tcc.ps1
    # tab1/tab2 (MED_BR, GAP_MEDIANA… do params) e fig1; composição (csv e figuras do deck).
    # Leem renda_bruta, que passou a ser deflacionada — não podem ficar de fora
    @("tabelas_compl",      "`"$py`" -u scripts/geradores/gerar_tabelas_complementares.py"),
    @("composicao",         "`"$py`" -u scripts/analise/run_composicao_ocupacional.py"),
    @("descritivos_base",   "`"$py`" -u tcc/scripts/gerar_descritivos_base.py"),
    @("tab_balanceamento",  "`"$py`" -u tcc/scripts/gerar_tabela_balanceamento.py"),
    @("tab_cv",             "`"$py`" -u tcc/scripts/gerar_tabela_cv.py"),
    @("tab_rif",            "`"$py`" -u tcc/scripts/corrigir_tabela_rif.py"),
    @("figuras_nucleo",     "`"$py`" -u tcc/scripts/gerar_figuras_nucleo.py"),
    @("fig_interseccional", "`"$py`" -u tcc/scripts/gerar_figura_interseccional.py"),
    @("fig_rs_blups",       "`"$py`" -u tcc/scripts/gerar_figura_rs_blups.py"),
    @("tab_robustez",       "`"$py`" -u tcc/scripts/gerar_tabela_robustez.py"),
    # documento: tabelas-síntese -> relatorio_tcc.tex -> enxuto -> normas -> PDF/docx -> conferência
    @("relatorio",          "powershell -NoProfile -ExecutionPolicy Bypass -File tcc/run_tcc.ps1 -Relatorio"),
    # o run_tcc.ps1 não compila o LaTeX: compila-se aqui e repete-se o que copia o PDF
    @("compilar_pdfs",      "pdflatex -interaction=nonstopmode relatorio_tcc_enxuto.tex & bibtex relatorio_tcc_enxuto & pdflatex -interaction=nonstopmode relatorio_tcc_enxuto.tex & pdflatex -interaction=nonstopmode relatorio_tcc_enxuto.tex & pdflatex -interaction=nonstopmode tcc_normas.tex & bibtex tcc_normas & pdflatex -interaction=nonstopmode tcc_normas.tex & pdflatex -interaction=nonstopmode tcc_normas.tex"),
    @("word_enxuto",        "`"$py`" -u tcc/scripts/gerar_word_enxuto.py"),
    @("normas_docx",        "`"$py`" -u tcc/scripts/gerar_tcc_normas_docx.py"),
    @("formatar_docx",      "`"$py`" -u tcc/scripts/formatar_docx_normas.py"),
    @("conferir_anexos",    "`"$py`" -u tcc/scripts/conferir_anexos_normas.py"),
    @("defesa_pptx",        "`"$py`" -u scripts/geradores/gerar_apresentacao_pptx.py"),
    @("validate",           "`"$py`" -u validate_consistency.py"),
    @("narrativa_social",   "`"$py`" -u tcc/scripts/gerar_narrativa_social.py"),
    # portões anti-fóssil: número digitado nos geradores / número sem fonte nos entregáveis
    @("caca_fosseis",       "`"$py`" -u tcc/scripts/caca_fosseis.py --vivos"),
    @("conferir_numeros",   "`"$py`" -u tcc/scripts/conferir_numeros_entregaveis.py --detalhe")
)
$pular = [bool]$Desde
foreach ($p in $passos) {
    if ($pular -and $p[0] -ne $Desde) { continue }
    $pular = $false
    $nome = $p[0]; $log = "$root\outputs\logs\loo2_$nome.log"
    Add-Content $st "$(Get-Date -Format s) INICIO $nome"
    cmd /c "$($p[1]) > `"$log`" 2>&1"
    $rc = $LASTEXITCODE
    $res = if ($rc -eq 0) { "OK" } else { "FALHOU(rc=$rc)" }
    Add-Content $st "$(Get-Date -Format s) $res $nome"
}
Add-Content $st "$(Get-Date -Format s) FIM_FILA"
