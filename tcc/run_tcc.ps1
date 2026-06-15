<#
    run_tcc.ps1 — Launcher curado da versão ENXUTA do TCC (núcleo de 4 + robustez).
    Roda APENAS os métodos do escopo do TCC, na ordem. Ver tcc/MANIFESTO_METODOS.md.

    A versão estendida (todos os métodos) está no branch `mestrado-extenso`.

    Uso:
        ./tcc/run_tcc.ps1            # roda núcleo + robustez
        ./tcc/run_tcc.ps1 -NucleoSo # roda só o núcleo de 4
#>
param(
    [switch]$NucleoSo
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

Invoke-Etapa $Nucleo "NÚCLEO (corpo do TCC)"
if (-not $NucleoSo) {
    Invoke-Etapa $Robustez "ROBUSTEZ (apêndice)"
}
Write-Host "`nConcluído. Tabelas em outputs/tables/, figuras em outputs/figures/." -ForegroundColor Cyan
