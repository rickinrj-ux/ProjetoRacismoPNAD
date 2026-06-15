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
$Root   = Split-Path -Parent $PSScriptRoot
$Analise = Join-Path $Root "scripts\analise"

# Núcleo de 4 — corpo do TCC (ordem de dependência: features -> métodos)
$Nucleo = @(
    "run_hlm_serie_completa.py",   # 1. HLM 3 níveis
    "run_hlm_m4.py",               #    HLM M4 (gap residual)
    "run_oaxaca_blinder.py",       # 2. Oaxaca-Blinder
    "run_regressao_quantilica.py", # 3. Quantílica
    "run_rif_decomp.py",           #    RIF-OB (decomposição por quantil)
    "run_glmm_glassceil.py",       # 4. GLMM logístico (teto de vidro)
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
    # 1. tabela-síntese do GLMM (núcleo)
    Write-Host "  -> tcc/scripts/gerar_tabela_glmm.py" -ForegroundColor Green
    & $Python (Join-Path $PSScriptRoot "scripts\gerar_tabela_glmm.py")
    # 2. relatório completo (fonte) — necessário para o pós-processador
    Write-Host "  -> scripts/geradores/gerar_relatorio_tcc.py" -ForegroundColor Green
    & $Python (Join-Path $Root "scripts\geradores\gerar_relatorio_tcc.py")
    # 3. pós-processa -> relatorio_tcc_enxuto.tex
    Write-Host "  -> tcc/scripts/gerar_relatorio_enxuto.py" -ForegroundColor Green
    & $Python (Join-Path $PSScriptRoot "scripts\gerar_relatorio_enxuto.py")
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
