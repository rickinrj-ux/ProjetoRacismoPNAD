<#
    run_tcc.ps1 — Launcher curado da versão ENXUTA do TCC (núcleo de 4 + robustez).
    Roda APENAS os métodos do escopo do TCC, na ordem. Ver tcc/MANIFESTO_METODOS.md.

    A versão estendida (todos os métodos) está no branch `mestrado-extenso`.

    Uso:
        ./tcc/run_tcc.ps1             # roda núcleo + robustez
        ./tcc/run_tcc.ps1 -NucleoSo   # roda só o núcleo de 4
        ./tcc/run_tcc.ps1 -Relatorio  # (re)gera só o relatório enxuto
#>
param(
    [switch]$NucleoSo,
    [switch]$Relatorio
)

$ErrorActionPreference = "Stop"
$Python = "C:\Users\user\AppData\Local\spyder-6\python.exe"
$Rscript = "C:\Program Files\R\R-4.6.0\bin\Rscript.exe"
$Root   = Split-Path -Parent $PSScriptRoot
$Analise = Join-Path $Root "scripts\analise"

# Núcleo de 4 — corpo do TCC (ordem de dependência: features -> métodos)
$Nucleo = @(
    "run_hlm_serie_completa.py",   # 1a. OLS-FE de UF (SE conv/cluster-UPA/cluster-UF) + WLS; gap agregado
    "run_hlm_stepup.py",           # 1b. HLM 2 níveis (indivíduo em UPA, UF fixo): step-up M0-M4, RS, BLUPs
    "run_oaxaca_blinder.py",       # 2. Oaxaca-Blinder
    "run_regressao_quantilica.py", # 3. Quantílica
    "run_ob_qr_melhorias.py",      #    QR por sexo + KB test (bootstrap em blocos por UPA) -> qr_melhorias.tex
    "run_rif_decomp.py",           #    RIF-OB (decomposição por quantil)
    "run_glmm_glassceil.py",       # 4a. logit com efeitos fixos de UF + SE cluster-UPA (robustez)
    "R:scripts/R/glmm_glassceil.R", # 4b. GLMM de verdade (glmer, RE de UPA): fonte da tab:glmm_glassceil
    "run_composicao_ocupacional.py" # apoio descritivo do núcleo
)

# Robustez — apêndice enxuto
$Robustez = @(
    "run_ml_shap.py",                  # XGBoost + SHAP
    "run_konfound_evalues.py",         # E-value (GLMM) + Konfound (HLM)
    "run_interseccionalidade.py",      # OB 4 grupos (raça×gênero)
    "run_vif_multicolinearidade.py",   # diagnóstico de multicolinearidade
    "run_hlm_vs_ols_justificacao.py"   # justificação HLM vs OLS
)

function Invoke-Etapa([string[]]$Scripts, [string]$Titulo) {
    Write-Host "`n===== $Titulo =====" -ForegroundColor Cyan
    foreach ($s in $Scripts) {
        if ($s.StartsWith("R:")) {                     # script R (lme4::glmer)
            $rpath = Join-Path $Root ($s.Substring(2))
            Write-Host "  -> $($s.Substring(2)) [Rscript]" -ForegroundColor Green
            & $Rscript $rpath
            if ($LASTEXITCODE -ne 0) { throw "Falha em $s (exit $LASTEXITCODE)" }
            continue
        }
        $path = Join-Path $Analise $s
        if (-not (Test-Path $path)) {
            Write-Host "  [PULADO] não encontrado: $s" -ForegroundColor Yellow
            continue
        }
        Write-Host "  -> $s" -ForegroundColor Green
        & $Python $path
        if ($LASTEXITCODE -ne 0) { throw "Falha em $s (exit $LASTEXITCODE)" }
    }
}

function Build-Relatorio {
    Write-Host "`n===== RELATÓRIO ENXUTO =====" -ForegroundColor Cyan
    # 1. tabelas-síntese do núcleo (GLMM, Oaxaca em duas especificações, mediação, interseccional)
    foreach ($g in @("gerar_tabela_glmm.py", "gerar_tabela_oaxaca.py",
                     "gerar_tabela_mediacao.py", "gerar_tabela_interseccional.py")) {
        Write-Host "  -> tcc/scripts/$g" -ForegroundColor Green
        & $Python (Join-Path $PSScriptRoot "scripts\$g")
        if ($LASTEXITCODE -ne 0) { throw "Falha em $g (exit $LASTEXITCODE)" }
    }
    # 2. relatório completo (fonte) — necessário para o pós-processador
    Write-Host "  -> scripts/geradores/gerar_relatorio_tcc.py" -ForegroundColor Green
    & $Python (Join-Path $Root "scripts\geradores\gerar_relatorio_tcc.py")
    # 3. pós-processa -> relatorio_tcc_enxuto.tex
    Write-Host "  -> tcc/scripts/gerar_relatorio_enxuto.py" -ForegroundColor Green
    & $Python (Join-Path $PSScriptRoot "scripts\gerar_relatorio_enxuto.py")
    # 4. mesma fonte, saída Word (entregaveis/relatorio_tcc_enxuto.docx)
    Write-Host "  -> tcc/scripts/gerar_word_enxuto.py" -ForegroundColor Green
    & $Python (Join-Path $PSScriptRoot "scripts\gerar_word_enxuto.py")
    if ($LASTEXITCODE -ne 0) { Write-Host "  [AVISO] Word não gerado (pypandoc_binary ausente?)" -ForegroundColor Yellow }
    # 5. demais entregáveis — todos lêem os números via params_nucleo.py.
    # gerar_resultados_preliminares.py ficou de fora: o documento é de uma etapa
    # vencida (está em entregaveis/_arquivo/) e só precisa rodar se houver nova
    # submissão naquele modelo.
    foreach ($e in @("gerar_guia_estudo.py", "gerar_apresentacao_executiva.py")) {
        Write-Host "  -> tcc/scripts/$e" -ForegroundColor Green
        & $Python (Join-Path $PSScriptRoot "scripts\$e")
        if ($LASTEXITCODE -ne 0) { throw "Falha em $e (exit $LASTEXITCODE)" }
    }
}

if ($Relatorio) {
    Build-Relatorio
    Write-Host "`nRelatório enxuto: relatorio_tcc_enxuto.tex" -ForegroundColor Cyan
    return
}

Invoke-Etapa $Nucleo "NÚCLEO (corpo do TCC)"
if (-not $NucleoSo) {
    Invoke-Etapa $Robustez "ROBUSTEZ (apêndice)"
}
Build-Relatorio
Write-Host "`nConcluído. Tabelas em outputs/tables/, figuras em outputs/figures/." -ForegroundColor Cyan
Write-Host "Relatório enxuto: relatorio_tcc_enxuto.tex" -ForegroundColor Cyan
