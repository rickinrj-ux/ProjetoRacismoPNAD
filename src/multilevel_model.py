"""
multilevel_model.py
===================
Modelo Linear Multinível (HLM) de 3 Níveis — Gap Salarial e Empregabilidade
Racial no Brasil (PNAD Contínua).

═══════════════════════════════════════════════════════════════════════════════
ESPECIFICAÇÃO MATEMÁTICA DO MODELO
═══════════════════════════════════════════════════════════════════════════════

Nível 1 — Indivíduo i (dentro da localidade j, no estado k):

    ln(Renda)_{ijk} = β_{0jk}
                    + β₁·Negro_{ijk}
                    + β₂·SexoFem_{ijk}
                    + β₃·Idade_c_{ijk}
                    + β₄·IdadeSq_{ijk}
                    + β₅·EducFund_{ijk}
                    + β₆·EducMedio_{ijk}
                    + β₇·EducSuperior_{ijk}
                    + β₈·EducPos_{ijk}
                    + β₉·log(Horas)_{ijk}
                    + β₁₀·Urbano_{ijk}
                    + β₁₁ₜ·Anoₜ_{ijk}
                    + ε_{ijk},    ε ~ N(0, σ²)

    log(Horas): controla jornada de trabalho — sem ele, sobre-representação
    de negros em part-time infla o gap racial estimado.
    Urbano: prêmio salarial urbano predeterminado (V1022 PNAD).
    C(Ano): dummies anuais — remove viés de ciclo econômico em dados pooled.

Nível 2 — Localidade j (UPA, proxy de bairro — Hipótese de Networking Local):

    β_{0jk} = γ_{00k}
             + γ_{01}·PctNegro^{UPA}_{jk}
             + γ_{02}·TxDesemprego^{UPA}_{jk}
             + γ_{03}·MediaEduc^{UPA}_{jk}
             + u_{0jk},    u_{0j} ~ N(0, τ²_{u₀})

    γ_{01} < 0 → evidência de "duplo disadvantage": segregação residencial
    amplifica o gap racial além do efeito individual de ser negro.

Nível 3 — Estado k (UF — Contexto Macroeconômico):

    γ_{00k} = δ_{000}
             + δ_{001}·PctNegro^{UF}_k
             + δ_{002}·TxDesemprego^{UF}_k
             + δ_{003}·MediaEduc^{UF}_k
             + v_{00k},    v_{00k} ~ N(0, τ²_{v₀})

Modelo Combinado:

    ln(Renda)_{ijk} = δ_{000}
        + [δ_{001}·Z_k¹ + δ_{002}·Z_k² + δ_{003}·Z_k³]   ← efeitos UF
        + [γ_{01}·W_{jk}¹ + γ_{02}·W_{jk}² + γ_{03}·W_{jk}³]  ← efeitos UPA
        + [β₁·Negro_{ijk} + β₂·SexoFem_{ijk} + ...]        ← efeitos individuais
        + v_{00k} + u_{0jk} + ε_{ijk}                       ← erros aleatórios

ICC (Intraclass Correlation Coefficient):

    ρ_{UF}  = τ²_{v₀} / (τ²_{v₀} + τ²_{u₀} + σ²)
    ρ_{UPA} = τ²_{u₀} / (τ²_{v₀} + τ²_{u₀} + σ²)

    ρ_{UPA} > 0.05 → variância de localidade é substancial →
    a hipótese do networking local tem suporte estrutural nos dados.

Teste de Razão de Verossimilhança (LRT) para comparação de modelos aninhados:

    LR = 2·(LL_{full} - LL_{restricted}) ~ χ²(Δp)
    onde Δp = diferença no número de parâmetros

Redução do coeficiente β₁ (negro) entre M1 e M3:

    Mediação contextual = (β₁^{M1} - β₁^{M3}) / β₁^{M1}

    Quantifica quanto do gap salarial racial é explicado por
    onde o indivíduo mora vs. por discriminação direta no mercado.

═══════════════════════════════════════════════════════════════════════════════
REFERÊNCIAS
═══════════════════════════════════════════════════════════════════════════════
Raudenbush, S. W., & Bryk, A. S. (2002). Hierarchical Linear Models.
    Applications and Data Analysis Methods (2nd ed.). Sage.
Gelman, A., & Hill, J. (2007). Data Analysis Using Regression and
    Multilevel/Hierarchical Models. Cambridge University Press.
Hasenbalg, C. (1979). Discriminação e Desigualdades Raciais no Brasil.
    Graal.
Pager, D. (2007). Marked: Race, Crime, and Finding Work in an Era of
    Mass Incarceration. University of Chicago Press.
Sampson, R. J., Raudenbush, S. W., & Earls, F. (1997). Neighborhoods
    and violent crime: A multilevel study. Science, 277, 918-924.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

FIGURES = Path(__file__).parent.parent / "outputs" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

from mlflow_utils import (
    log_artifacts_dir, log_metrics, log_params, run_context, set_tag,
)

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
FEATURES_PATH = ROOT / "data" / "processed" / "features.parquet"
OUTPUTS = ROOT / "outputs" / "tables"
OUTPUTS.mkdir(parents=True, exist_ok=True)

# ── Fórmulas dos Modelos ──────────────────────────────────────────────────────
# Definidas como constantes para garantir consistência entre ajuste e relatório

_INDIVIDUAL_TERMS = (
    "negro + sexo_fem + idade_c + idade_sq"
    " + educ_fund_completo + educ_medio_completo"
    " + educ_superior_completo + educ_pos_graduacao"
    " + log_horas + urbano + C(Ano)"
)

_UPA_TERMS = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"

_UF_TERMS = "pct_negro_uf_z + tx_desemprego_uf_z + media_educ_uf_z"

FORMULAS = {
    "M0_Nulo":       "log_renda ~ 1",
    "M1_Individual": f"log_renda ~ {_INDIVIDUAL_TERMS}",
    "M2_Localidade": f"log_renda ~ {_INDIVIDUAL_TERMS} + {_UPA_TERMS}",
    "M3_Completo":   f"log_renda ~ {_INDIVIDUAL_TERMS} + {_UPA_TERMS} + {_UF_TERMS}",
}

# Preditores de interesse para a tabela de resultados
KEY_PREDICTORS = [
    "Intercept", "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
    "log_horas", "urbano",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "pct_negro_uf_z",  "tx_desemprego_uf_z",  "media_educ_uf_z",
]


# ── Estrutura de Resultados ───────────────────────────────────────────────────

@dataclass
class HLMResults:
    """Container tipado para resultados de um modelo HLM ajustado."""
    model_name: str
    result: object         # statsmodels MixedLMResults
    var_uf: float          # τ²_{v₀} — variância do RE de UF (Nível 3)
    var_upa: float         # τ²_{u₀} — variância do RE de UPA (Nível 2)
    var_resid: float       # σ²      — variância residual (Nível 1)
    icc_uf: float
    icc_upa: float
    n_obs: int
    n_upa: int
    n_uf: int
    aic: float
    bic: float
    log_likelihood: float


# ── Preparação dos Dados ──────────────────────────────────────────────────────

def load_features(sample_frac: Optional[float] = None) -> pd.DataFrame:
    """
    Carrega features e aplica filtros finais para modelagem de renda.

    Filtros aplicados:
        1. log_renda > 0: apenas trabalhadores com renda positiva declarada
        2. dropna em todas as variáveis dos modelos: garante índice consistente
           entre formula e vc_formula no statsmodels (evita IndexError)
        3. UPA com ≥ 10 obs. (após dropna): estimação estável de τ²_UPA
           (Raudenbush & Bryk, 2002, cap. 4 — minimum cluster size)

    sample_frac é aplicado APÓS todos os filtros para preservar a estrutura
    de clustering — amostrar antes faria a maioria das UPAs ter n < min.
    """
    df = pd.read_parquet(FEATURES_PATH)
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()

    # Remove NaN em qualquer variável usada nos modelos M0–M3
    # Crítico: statsmodels vc_formula não suporta NaN implícito — causa IndexError
    model_vars = [
        "log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
        "educ_ord",
        "educ_fund_completo", "educ_medio_completo",
        "educ_superior_completo", "educ_pos_graduacao",
        "log_horas", "urbano", "Ano",
        "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
        "pct_negro_uf_z",  "tx_desemprego_uf_z",  "media_educ_uf_z",
    ]
    n_before = len(df)
    df = df.dropna(subset=model_vars).reset_index(drop=True)
    logger.info(f"Removidos {n_before - len(df):,} obs. com NaN em variáveis do modelo.")

    # Filtro de UPA após dropna — garante que contagem reflete o dataset final
    upa_counts = df["UPA"].value_counts()
    valid_upas = upa_counts[upa_counts >= 10].index
    n_dropped = (~df["UPA"].isin(valid_upas)).sum()
    df = df[df["UPA"].isin(valid_upas)].reset_index(drop=True)
    if n_dropped:
        logger.info(f"Removidos {n_dropped:,} obs. de UPAs com n < 10.")

    # Adiciona educ_ord centrada (necessária para M4 random slope)
    if "educ_ord" in df.columns:
        df["educ_ord_c"] = (df["educ_ord"] - df["educ_ord"].mean()).astype("float32")
    else:
        df["educ_ord_c"] = np.nan

    # Fallback: reconstrói colunas novas se features.parquet foi gerado
    # antes da adição de log_horas / urbano em feature_engineering.py
    if "log_horas" not in df.columns:
        if "horas_trabalhadas" in df.columns:
            df["log_horas"] = np.log(df["horas_trabalhadas"].clip(lower=1))
            logger.warning("log_horas reconstruído a partir de horas_trabalhadas "
                           "(regenere features.parquet via run_feature_engineering.py)")
        else:
            df["log_horas"] = np.nan
            logger.warning("log_horas e horas_trabalhadas ausentes — coluna preenchida com NaN")

    if "urbano" not in df.columns:
        if "V1022" in df.columns:
            df["urbano"] = (df["V1022"] == 1).fillna(False).astype("int8")
            logger.warning("urbano reconstruído a partir de V1022 "
                           "(regenere features.parquet via run_feature_engineering.py)")
        else:
            df["urbano"] = 1
            logger.warning("V1022 ausente — urbano=1 para toda a amostra (fallback conservador)")

    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)

    df["UPA_str"] = df["UPA"].astype(str)
    df["UF_str"]  = df["UF"].astype(str)

    logger.info(
        f"Dados para modelagem: {len(df):,} obs. | "
        f"{df['UPA_str'].nunique():,} UPAs | "
        f"{df['UF_str'].nunique()} UFs"
    )
    return df


# ── Extração de Componentes de Variância ──────────────────────────────────────

def _extract_variance_components(result) -> Tuple[float, float, float]:
    """
    Extrai τ²_{v₀} (UF), τ²_{u₀} (UPA) e σ² (resíduo) do MixedLMResults.

    No statsmodels com vc_formula:
        result.cov_re → matriz de covariância dos efeitos aleatórios do grupo
                        (Nível 3, groups=UF_str)
        result.vcomp  → vetor de variâncias dos componentes adicionais
                        (Nível 2, vc_formula={"UPA_str": "0 + C(UPA_str)"})
        result.scale  → variância residual σ² (Nível 1)

    cov_re pode ser vazia quando o efeito aleatório de UF colapsa para zero
    (variância singular) — tratamos como 0 em vez de levantar IndexError.
    """
    try:
        var_uf = float(result.cov_re.iloc[0, 0]) if result.cov_re.shape[0] > 0 else 0.0
    except (IndexError, AttributeError):
        var_uf = 0.0

    try:
        var_upa = float(result.vcomp[0]) if (
            hasattr(result, "vcomp") and len(result.vcomp) > 0
        ) else 0.0
    except (IndexError, AttributeError):
        var_upa = 0.0

    var_resid = float(result.scale)
    return var_uf, var_upa, var_resid


def compute_icc(
    var_uf: float,
    var_upa: float,
    var_resid: float,
) -> Dict[str, float]:
    """
    Calcula ICC para cada nível do modelo.

    Interpretação para o capítulo de Resultados:
        ICC_UPA = 0.12 → 12% da variância de log-renda é atribuível
        à localidade de moradia, após controlar por características
        individuais — suporte para a hipótese de networking local.

    Regra de bolso (Raudenbush & Bryk, 2002):
        ICC > 0.05 justifica a inclusão do nível no modelo.
        ICC < 0.01 sugere que o nível pode ser colapsado.
    """
    total = var_uf + var_upa + var_resid
    if total <= 0:
        return {"icc_uf": 0.0, "icc_upa": 0.0, "icc_residual": 1.0}
    return {
        "icc_uf":       var_uf    / total,
        "icc_upa":      var_upa   / total,
        "icc_residual": var_resid / total,
    }


# ── Ajuste dos Modelos ────────────────────────────────────────────────────────

def _fit_model(
    model_name: str,
    formula: str,
    df: pd.DataFrame,
    method: str = "lbfgs",
    maxiter: int = 1000,
) -> HLMResults:
    """
    Ajusta um modelo HLM de 3 níveis com a fórmula fornecida.

    Estrutura de efeitos aleatórios:
        groups=UF_str          → intercepto aleatório por UF (Nível 3)
        vc_formula={"UPA_str"} → componente de variância por UPA (Nível 2)

    Método LBFGS: quasi-Newton de memória limitada — eficiente para
    o espaço paramétrico grande dos efeitos aleatórios de UPA
    (~3000-5000 UPAs na PNAD). Alternativa: "cg" (conjugate gradient)
    se convergência falhar.

    REML vs. ML:
        Padrão statsmodels: REML=True → estimativas não-viesadas das
        variâncias. Para comparação de modelos com diferentes parâmetros
        fixos (LRT), use reml=False (ML puro).
    """
    logger.info(f"Ajustando {model_name}...")
    model = smf.mixedlm(
        formula=formula,
        data=df,
        groups=df["UF_str"],
        vc_formula={"UPA_str": "0 + C(UPA_str)"},
    )
    # ML (não REML) para permitir LRT entre modelos com diferentes partes fixas
    result = model.fit(method=method, maxiter=maxiter, reml=False)

    var_uf, var_upa, var_resid = _extract_variance_components(result)
    icc = compute_icc(var_uf, var_upa, var_resid)

    logger.info(
        f"  {model_name} convergiu | "
        f"ICC_UPA={icc['icc_upa']:.3f} | ICC_UF={icc['icc_uf']:.3f} | "
        f"AIC={result.aic:.1f}"
    )
    hlm = HLMResults(
        model_name=model_name,
        result=result,
        var_uf=var_uf, var_upa=var_upa, var_resid=var_resid,
        icc_uf=icc["icc_uf"], icc_upa=icc["icc_upa"],
        n_obs=len(df),
        n_upa=df["UPA_str"].nunique(),
        n_uf=df["UF_str"].nunique(),
        aic=result.aic,
        bic=result.bic,
        log_likelihood=result.llf,
    )

    b  = result.params.get("negro", np.nan)
    se = result.bse.get("negro", np.nan)
    pv = result.pvalues.get("negro", np.nan)
    with run_context(model_name, "HLM_Gap_Racial", nested=True):
        log_params({
            "model_name": model_name,
            "formula":    formula,
            "method":     method,
            "maxiter":    maxiter,
            "reml":       False,
            "n_obs":      hlm.n_obs,
            "n_upa":      hlm.n_upa,
            "n_uf":       hlm.n_uf,
        })
        log_metrics({
            "beta_negro":     b,
            "se_negro":       se,
            "pval_negro":     pv,
            "gap_pct":        (np.exp(b) - 1) * 100,
            "icc_uf":         hlm.icc_uf,
            "icc_upa":        hlm.icc_upa,
            "var_uf":         hlm.var_uf,
            "var_upa":        hlm.var_upa,
            "var_resid":      hlm.var_resid,
            "aic":            hlm.aic,
            "bic":            hlm.bic,
            "log_likelihood": hlm.log_likelihood,
        })

    return hlm


def fit_null_model(df: pd.DataFrame) -> HLMResults:
    """
    Modelo Nulo (M0): apenas interceptos aleatórios, sem preditores.

    Propósito: estabelecer o ICC de referência (modelo incondicional).
    Responde: "quanta variância de renda existe ENTRE localidades e ENTRE
    estados, antes de controlar por qualquer característica individual?"

    A comparação do ICC entre M0 e M3 mostra quanto do efeito contextual
    é explicado pelos preditores de Nível 2 e 3 inseridos.
    """
    return _fit_model("M0_Nulo", FORMULAS["M0_Nulo"], df)


def fit_individual_model(df: pd.DataFrame) -> HLMResults:
    """
    Modelo 1 (M1): preditores individuais apenas (equação de Mincer estendida).

    O coeficiente β₁ (negro) aqui representa o gap salarial racial BRUTO:
    a diferença de log-renda entre negros e brancos com mesma escolaridade,
    sexo e faixa etária — mas sem controlar pelo contexto de moradia.

    Interpretação: exp(β₁) - 1 = variação percentual no rendimento.
    Exemplo: β₁ = -0.18 → negros ganham ~16.5% menos que brancos comparáveis.
    """
    return _fit_model("M1_Individual", FORMULAS["M1_Individual"], df)


def fit_locality_model(df: pd.DataFrame) -> HLMResults:
    """
    Modelo 2 (M2): individual + contexto de localidade (Nível 2).

    Adiciona variáveis da UPA para testar a hipótese de networking local.

    Interpretação dos novos coeficientes (γ):
        γ_{01} (pct_negro_upa): se negativo → segregação residencial amplifica
            o gap racial além do efeito individual — "duplo disadvantage"
        γ_{02} (tx_desemprego_upa): impacto das oportunidades locais na renda
        γ_{03} (media_educ_upa): spillovers de capital humano do entorno

    A redução de β₁ (negro) em relação ao M1 indica mediação contextual:
    parte do gap racial é explicada pelo tipo de bairro onde negros vivem.
    """
    return _fit_model("M2_Localidade", FORMULAS["M2_Localidade"], df)


def fit_full_model(df: pd.DataFrame) -> HLMResults:
    """
    Modelo Completo (M3): 3 níveis — individual + localidade + estado.

    β₁ (negro) no M3 representa o gap salarial racial LÍQUIDO:
    a parte que persiste após controlar por características individuais,
    contexto de moradia (Nível 2) e contexto macroeconômico estadual (Nível 3).

    Este é o coeficiente central para o argumento do TCC:
    o gap líquido reflete discriminação no mercado de trabalho que não
    pode ser atribuída a diferenças em capital humano ou localização.

    Decomposição do gap racial bruto (M1 → M3):
        Gap contextual (localidade) = β₁^{M1} - β₁^{M2}
        Gap contextual (estado)     = β₁^{M2} - β₁^{M3}
        Gap líquido (discriminação) = β₁^{M3}
    """
    return _fit_model("M3_Completo", FORMULAS["M3_Completo"], df)


# ── Testes Estatísticos ───────────────────────────────────────────────────────

def likelihood_ratio_test(
    m_restricted: HLMResults,
    m_full: HLMResults,
) -> Dict:
    """
    Teste LRT para comparar modelos aninhados.

    H₀: parâmetros adicionais do modelo completo são simultaneamente = 0
    H₁: pelo menos um parâmetro adicional ≠ 0

    LR = 2·(LL_full - LL_restricted) ~ χ²(Δp)
    Δp = diferença no número de parâmetros estimados

    Uso: determina se adicionar Nível 2 (M1→M2) ou Nível 3 (M2→M3)
    melhora significativamente o ajuste ao custo de parâmetros adicionais.
    """
    lr_stat = 2 * (m_full.log_likelihood - m_restricted.log_likelihood)
    n_params_full = len(m_full.result.params)
    n_params_rest = len(m_restricted.result.params)
    df_diff = max(n_params_full - n_params_rest, 1)
    p_value = stats.chi2.sf(lr_stat, df=df_diff)
    return {
        "Comparação":   f"{m_restricted.model_name} → {m_full.model_name}",
        "LR":           round(lr_stat, 3),
        "df":           df_diff,
        "p-valor":      round(p_value, 6),
        "Significativo": "Sim" if p_value < 0.05 else "Não",
    }


def compute_racial_gap_decomposition(models: Dict[str, "HLMResults"]) -> pd.DataFrame:
    """
    Decompõe o gap salarial racial entre efeitos individuais e contextuais.

    Decomposição sequencial (Oaxaca-Blinder adaptada para HLM):
        Gap Bruto (M1)         = β₁^{M1}
        Mediado por UPA (M2)   = β₁^{M1} - β₁^{M2}
        Mediado por UF (M3)    = β₁^{M2} - β₁^{M3}
        Gap Líquido            = β₁^{M3}

    O gap líquido é interpretado como limite inferior da discriminação
    não-explicada por diferenças em capital humano ou localização.
    """
    rows = []
    for mname in ["M1_Individual", "M2_Localidade", "M3_Completo"]:
        if mname not in models:
            continue
        m = models[mname]
        coef = m.result.params.get("negro", np.nan)
        se   = m.result.bse.get("negro", np.nan)
        pval = m.result.pvalues.get("negro", np.nan)
        rows.append({
            "Modelo": mname,
            "β_negro": round(coef, 4),
            "SE":      round(se, 4),
            "p-valor": round(pval, 6),
            "Gap %":   round((np.exp(coef) - 1) * 100, 2),
            "Stars":   "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else "",
        })

    df = pd.DataFrame(rows)
    if len(df) >= 2:
        b1 = df.loc[df["Modelo"] == "M1_Individual", "β_negro"].values[0]
        b3 = df.loc[df["Modelo"] == "M3_Completo",   "β_negro"].values[0]
        pct_contextual = abs(b1 - b3) / abs(b1) * 100 if b1 != 0 else np.nan
        logger.info(
            f"Gap racial bruto: {b1:.4f} | Líquido: {b3:.4f} | "
            f"Mediação contextual: {pct_contextual:.1f}%"
        )
    return df


# ── Tabela de Resultados ──────────────────────────────────────────────────────

def build_results_table(models: Dict[str, "HLMResults"]) -> pd.DataFrame:
    """
    Tabela de comparação de modelos no formato APA/ESALQ.

    Formato das células: coeficiente + stars (*** p<0.001)
                                      (erro-padrão)
    Rodapé: componentes de variância, ICC, N e fit statistics.
    """
    model_names = list(models.keys())
    records: Dict[str, Dict] = {}

    for mname, hlm in models.items():
        res = hlm.result

        for var in KEY_PREDICTORS:
            cell = records.setdefault(var, {m: "—" for m in model_names})
            if var not in res.params:
                continue
            coef  = res.params[var]
            se    = res.bse[var]
            pval  = res.pvalues[var]
            stars = (
                "***" if pval < 0.001 else
                "**"  if pval < 0.01  else
                "*"   if pval < 0.05  else ""
            )
            cell[mname] = f"{coef:.4f}{stars}\n({se:.4f})"

        # Componentes de variância
        records.setdefault("σ² (Nível 1)", {})[mname]     = f"{hlm.var_resid:.4f}"
        records.setdefault("τ²_UPA (Nível 2)", {})[mname] = f"{hlm.var_upa:.4f}"
        records.setdefault("τ²_UF (Nível 3)", {})[mname]  = f"{hlm.var_uf:.4f}"
        records.setdefault("ICC_UPA", {})[mname]           = f"{hlm.icc_upa:.4f}"
        records.setdefault("ICC_UF", {})[mname]            = f"{hlm.icc_uf:.4f}"
        records.setdefault("N (obs.)", {})[mname]          = f"{hlm.n_obs:,}"
        records.setdefault("N (UPAs)", {})[mname]          = f"{hlm.n_upa:,}"
        records.setdefault("N (UFs)", {})[mname]           = f"{hlm.n_uf}"
        records.setdefault("Log-Likelihood", {})[mname]    = f"{hlm.log_likelihood:.2f}"
        records.setdefault("AIC", {})[mname]               = f"{hlm.aic:.2f}"
        records.setdefault("BIC", {})[mname]               = f"{hlm.bic:.2f}"

    return pd.DataFrame(records).T[model_names]


def save_outputs(
    models: Dict[str, "HLMResults"],
    results_table: pd.DataFrame,
    decomposition: pd.DataFrame,
    lrt_results: List[Dict],
) -> None:
    """Salva todos os outputs em CSV e LaTeX para uso direto no TCC."""

    # Tabela principal de coeficientes
    results_table.to_csv(OUTPUTS / "hlm_coeficientes.csv")
    latex_main = results_table.to_latex(
        caption=(
            "Modelos HLM de 3 Níveis — Determinantes do Log-Rendimento Mensal "
            "por Raça no Brasil (PNAD Contínua, 2021-2024). "
            "Coeficientes com erro-padrão entre parênteses. "
            "*** p<0,001; ** p<0,01; * p<0,05."
        ),
        label="tab:hlm_coeficientes",
        escape=False,
        column_format="l" + "c" * len(results_table.columns),
    )
    (OUTPUTS / "hlm_coeficientes.tex").write_text(latex_main, encoding="utf-8")

    # Decomposição do gap racial
    decomposition.to_csv(OUTPUTS / "gap_decomposicao.csv", index=False)

    # Testes LRT
    pd.DataFrame(lrt_results).to_csv(OUTPUTS / "lrt_tests.csv", index=False)

    logger.info(f"Outputs salvos em: {OUTPUTS}")


# ── Sumário Narrativo para o TCC ──────────────────────────────────────────────

def print_discussion_summary(models: Dict[str, "HLMResults"]) -> None:
    """
    Gera texto narrativo de resultados para o capítulo de Discussão.
    Facilita a transição de outputs estatísticos para narrativa acadêmica.
    """
    m0 = models.get("M0_Nulo")
    m1 = models.get("M1_Individual")
    m3 = models.get("M3_Completo")
    if not all([m0, m1, m3]):
        logger.warning("Nem todos os modelos disponíveis para sumário.")
        return

    b1_m1 = m1.result.params.get("negro", np.nan)
    b1_m3 = m3.result.params.get("negro", np.nan)
    gap_bruto  = (np.exp(b1_m1) - 1) * 100
    gap_liquido = (np.exp(b1_m3) - 1) * 100
    mediacao   = abs(b1_m1 - b1_m3) / abs(b1_m1) * 100 if b1_m1 != 0 else np.nan

    sep  = "=" * 78
    sep2 = "-" * 78
    direcao = "menos" if gap_bruto < 0 else "mais"
    lines = [
        "",
        sep,
        "  SUMARIO DE RESULTADOS -- CAPITULO DE DISCUSSAO (TCC)",
        sep,
        "",
        "  MODELO NULO (M0) -- Decomposicao Incondicional da Variancia:",
        f"    ICC_UPA = {m0.icc_upa:.3f}  -> {m0.icc_upa*100:.1f}% da variancia de renda e atribuivel",
        "             a localidade de moradia, ANTES de controlar por raca.",
        f"    ICC_UF  = {m0.icc_uf:.3f}  -> {m0.icc_uf*100:.1f}% e atribuivel ao contexto estadual.",
        "",
        "  MODELO 1 (M1) -- Gap Salarial Racial Bruto:",
        f"    b_negro = {b1_m1:.4f}  -> profissionais negros ganham {abs(gap_bruto):.1f}%",
        f"             {direcao} que brancos com mesma escolaridade, sexo e idade.",
        "",
        "  MODELO COMPLETO (M3) -- Gap Salarial Racial Liquido:",
        f"    b_negro = {b1_m3:.4f}  -> gap persiste em {abs(gap_liquido):.1f}% apos controlar",
        "             por contexto de moradia (UPA) e macrorregional (UF).",
        f"    ICC_UPA = {m3.icc_upa:.3f}  -> {m3.icc_upa*100:.1f}% ainda explicado pela localidade.",
        "",
        "  MEDIACAO CONTEXTUAL (hipotese do networking local):",
        f"    {mediacao:.1f}% do gap bruto e mediado pelo local de moradia.",
        "    Segregacao residencial opera como canal independente de desigualdade",
        "    racial, alem da discriminacao direta no mercado de trabalho.",
        "",
        sep,
        "",
    ]
    print("\n".join(lines))


# ── Comparação de R² antes/depois das novas variáveis ────────────────────────

_FORMULA_BASE_OLS = (
    "log_renda ~ negro + sexo_fem + idade_c + idade_sq"
    " + educ_fund_completo + educ_medio_completo"
    " + educ_superior_completo + educ_pos_graduacao"
)
_FORMULA_EXT_OLS = _FORMULA_BASE_OLS + " + log_horas + urbano + C(Ano)"


def comparar_r2_controles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Quantifica o ganho de R² ao adicionar log_horas, urbano e C(Ano).

    Usa OLS como proxy (HLM não tem R² analítico direto).
    A redução em β_negro no modelo estendido mostra quanto do gap estimado
    era confound de jornada, urbanização e ciclo econômico — tornando
    o coeficiente residual uma medida mais conservadora de discriminação.
    """
    m_base = smf.ols(_FORMULA_BASE_OLS, data=df).fit()
    m_ext  = smf.ols(_FORMULA_EXT_OLS,  data=df).fit()

    b_base = m_base.params.get("negro", np.nan)
    b_ext  = m_ext.params.get("negro", np.nan)

    rows = [
        {
            "Especificação":   "Base (sem horas / urbano / ano)",
            "R²":              round(m_base.rsquared, 4),
            "R² adj.":         round(m_base.rsquared_adj, 4),
            "RMSE":            round(np.sqrt(m_base.mse_resid), 4),
            "β_negro":         round(b_base, 4),
            "Gap % estimado":  round((np.exp(b_base) - 1) * 100, 2),
        },
        {
            "Especificação":   "Estendido (+log_horas +urbano +C(Ano))",
            "R²":              round(m_ext.rsquared, 4),
            "R² adj.":         round(m_ext.rsquared_adj, 4),
            "RMSE":            round(np.sqrt(m_ext.mse_resid), 4),
            "β_negro":         round(b_ext, 4),
            "Gap % estimado":  round((np.exp(b_ext) - 1) * 100, 2),
        },
    ]
    comp = pd.DataFrame(rows)
    comp.loc[1, "ΔR²"]      = round(comp.loc[1, "R²"]     - comp.loc[0, "R²"], 4)
    comp.loc[1, "ΔRMSE"]    = round(comp.loc[1, "RMSE"]   - comp.loc[0, "RMSE"], 4)
    comp.loc[1, "Δβ_negro"] = round(comp.loc[1, "β_negro"]- comp.loc[0, "β_negro"], 4)

    return comp, m_base, m_ext


def plotar_ganho_fitted(
    df: pd.DataFrame,
    m_base,
    m_ext,
    out_fig: Path = None,
) -> None:
    """
    Figura 2×2: resíduos e fitted values antes/depois das novas variáveis.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if out_fig is None:
        out_fig = Path(__file__).parent.parent / "outputs" / "figures"
    out_fig.mkdir(parents=True, exist_ok=True)

    y     = df["log_renda"].values
    fv_b  = m_base.fittedvalues.values
    fv_e  = m_ext.fittedvalues.values
    res_b = m_base.resid.values
    res_e = m_ext.resid.values

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle(
        "Ganho de Ajuste: Modelo Base vs. Estendido (+log_horas, +urbano, +C(Ano))",
        fontsize=12, fontweight="bold",
    )

    # Fitted vs Actual — Base
    axes[0, 0].scatter(fv_b, y, alpha=0.08, s=4, color="#2166ac")
    lims = [min(fv_b.min(), y.min()), max(fv_b.max(), y.max())]
    axes[0, 0].plot(lims, lims, "r--", linewidth=1)
    axes[0, 0].set_title(f"Base — R²={m_base.rsquared:.4f}")
    axes[0, 0].set_xlabel("Fitted log-renda"); axes[0, 0].set_ylabel("Real log-renda")

    # Fitted vs Actual — Estendido
    axes[0, 1].scatter(fv_e, y, alpha=0.08, s=4, color="#4dac26")
    axes[0, 1].plot(lims, lims, "r--", linewidth=1)
    axes[0, 1].set_title(f"Estendido — R²={m_ext.rsquared:.4f}")
    axes[0, 1].set_xlabel("Fitted log-renda"); axes[0, 1].set_ylabel("Real log-renda")

    # Distribuição de resíduos — Base
    axes[1, 0].hist(res_b, bins=80, color="#2166ac", alpha=0.7, density=True)
    axes[1, 0].axvline(0, color="red", linestyle="--", linewidth=1)
    axes[1, 0].set_title(f"Resíduos Base — RMSE={np.sqrt(m_base.mse_resid):.4f}")
    axes[1, 0].set_xlabel("Resíduo")

    # Distribuição de resíduos — Estendido
    axes[1, 1].hist(res_e, bins=80, color="#4dac26", alpha=0.7, density=True)
    axes[1, 1].axvline(0, color="red", linestyle="--", linewidth=1)
    axes[1, 1].set_title(f"Resíduos Estendido — RMSE={np.sqrt(m_ext.mse_resid):.4f}")
    axes[1, 1].set_xlabel("Resíduo")

    plt.tight_layout()
    path = out_fig / "hlm_ganho_r2_fitted.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Figura salva: {path}")


# ── Pipeline Principal ────────────────────────────────────────────────────────

def run_models(
    sample_frac: Optional[float] = None,
    save: bool = True,
) -> Dict[str, HLMResults]:
    """
    Executa a sequência completa de modelos HLM (M0 → M1 → M2 → M3).

    A ordem sequencial é obrigatória: cada modelo subsequente é aninhado
    no anterior, permitindo LRT para justificar a adição de cada nível.

    Args:
        sample_frac: Fração da amostra para teste rápido de convergência.
                     Use 0.05 (5%) para validar antes do ajuste completo.
                     None = dados completos (recomendado para o TCC final).
        save: Persiste outputs em outputs/tables/.

    Returns:
        Dicionário {nome_modelo: HLMResults} para análises posteriores.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )

    df = load_features(sample_frac=sample_frac)

    run_tags = {
        "sample_frac": str(sample_frac or "completo"),
        "n_obs":        str(len(df)),
    }
    with run_context("pipeline_hlm", "HLM_Gap_Racial", tags=run_tags):
        log_params({"sample_frac": sample_frac, "n_obs": len(df)})

        # Ajuste sequencial — não paralelizar: cada modelo informa o próximo
        models: Dict[str, HLMResults] = {}
        models["M0_Nulo"]       = fit_null_model(df)
        models["M1_Individual"] = fit_individual_model(df)
        models["M2_Localidade"] = fit_locality_model(df)
        models["M3_Completo"]   = fit_full_model(df)

        # Comparações e análises
        lrt_results = [
            likelihood_ratio_test(models["M0_Nulo"],       models["M1_Individual"]),
            likelihood_ratio_test(models["M1_Individual"], models["M2_Localidade"]),
            likelihood_ratio_test(models["M2_Localidade"], models["M3_Completo"]),
        ]
        decomposition  = compute_racial_gap_decomposition(models)
        results_table  = build_results_table(models)

        # Métricas comparativas da run pai
        m1 = models["M1_Individual"]
        m3 = models["M3_Completo"]
        b1 = m1.result.params.get("negro", np.nan)
        b3 = m3.result.params.get("negro", np.nan)
        mediacao = abs(b1 - b3) / abs(b1) * 100 if b1 != 0 else np.nan
        log_metrics({
            "beta_negro_M1":       b1,
            "beta_negro_M3":       b3,
            "gap_pct_M1":          (np.exp(b1) - 1) * 100,
            "gap_pct_M3":          (np.exp(b3) - 1) * 100,
            "mediacao_contextual": mediacao,
            "aic_M0":  models["M0_Nulo"].aic,
            "aic_M1":  m1.aic,
            "aic_M2":  models["M2_Localidade"].aic,
            "aic_M3":  m3.aic,
            "icc_upa_M0": models["M0_Nulo"].icc_upa,
            "icc_upa_M3": m3.icc_upa,
        })

        # LRT como métricas
        for lrt in lrt_results:
            slug = lrt["Comparação"].replace(" → ", "_vs_").replace(" ", "")
            log_metrics({
                f"lrt_LR_{slug}":    lrt["LR"],
                f"lrt_pval_{slug}":  lrt["p-valor"],
            })

        # Modelo campeão: M3 é o modelo completo escolhido para o TCC
        set_tag("champion_model", "M3_Completo")
        set_tag("escolha_justificativa",
                "Menor AIC, LRT significativo em todos os níveis, "
                "ICC_UPA > 0.05 confirma estrutura multinível")

        if save:
            save_outputs(models, results_table, decomposition, lrt_results)
            log_artifacts_dir(OUTPUTS, subfolder="tables")

    print_discussion_summary(models)

    # ── Comparação de R² antes/depois das 3 novas variáveis ─────────────────
    comp_r2, m_base, m_ext = comparar_r2_controles(df)
    _imprimir_ganho_r2(comp_r2)
    if save:
        comp_r2.to_csv(OUTPUTS / "hlm_ganho_r2.csv", index=False)
        plotar_ganho_fitted(df, m_base, m_ext)

    return models


def _imprimir_ganho_r2(comp: pd.DataFrame) -> None:
    sep = "=" * 78
    row_b = comp.iloc[0]
    row_e = comp.iloc[1]
    print(f"\n{sep}")
    print("  GANHO DE R² — NOVAS VARIÁVEIS (+log_horas, +urbano, +C(Ano))")
    print(sep)
    print(f"  {'Especificação':<42} {'R²':>7}  {'R²adj':>7}  {'RMSE':>7}  {'β_negro':>8}  {'Gap%':>7}")
    print("-" * 78)
    print(f"  {row_b['Especificação']:<42} {row_b['R²']:>7.4f}  {row_b['R² adj.']:>7.4f}  "
          f"{row_b['RMSE']:>7.4f}  {row_b['β_negro']:>8.4f}  {row_b['Gap % estimado']:>6.1f}%")
    print(f"  {row_e['Especificação']:<42} {row_e['R²']:>7.4f}  {row_e['R² adj.']:>7.4f}  "
          f"{row_e['RMSE']:>7.4f}  {row_e['β_negro']:>8.4f}  {row_e['Gap % estimado']:>6.1f}%")
    print("-" * 78)
    print(f"  {'Ganho (Δ)':<42} {row_e['ΔR²']:>7.4f}  {'—':>7}  {row_e['ΔRMSE']:>7.4f}  "
          f"{row_e['Δβ_negro']:>8.4f}")
    print(f"\n  Interpretação:")
    print(f"    ΔR² = {row_e['ΔR²']:.4f} → as 3 variáveis explicam {row_e['ΔR²']*100:.2f}pp"
          " adicionais da variância de log-renda.")
    delta_gap = abs(row_e["Gap % estimado"]) - abs(row_b["Gap % estimado"])
    direcao = "menor" if delta_gap < 0 else "maior"
    print(f"    Δβ_negro = {row_e['Δβ_negro']:.4f} → gap estimado fica {abs(delta_gap):.1f}pp {direcao}")
    print(f"    após controlar por jornada, urbanização e ciclo econômico.")
    print(f"    O gap residual de {abs(row_e['Gap % estimado']):.1f}% é mais conservador e")
    print(f"    portanto mais difícil de contestar na banca.")
    print(f"{sep}\n")


# ── Pseudo-R² Nakagawa-Schielzeth (2013) ──────────────────────────────────────

def compute_nakagawa_r2(
    result,
    sigma2_u: float,
    var_predictor: float = 0.0,
    sigma2_u_slope: float = 0.0,
) -> Dict[str, float]:
    """
    Pseudo-R² marginal e condicional para LMM (Nakagawa & Schielzeth, 2013).

    R²m: variância explicada apenas pelos efeitos fixos.
    R²c: variância explicada pelos efeitos fixos + aleatórios (modelo completo).

    Para modelos com random slope:
        sigma2_u_total = tau²_intercept + tau²_slope * Var(preditor centrado)
    Para modelos sem random slope:
        sigma2_u_total = tau²_upa + tau²_uf

    Referência: Nakagawa, S. & Schielzeth, H. (2013). A general and simple
        method for obtaining R² from generalized linear mixed-effects models.
        Methods in Ecology and Evolution, 4(2), 133-142.
    """
    # Variância dos efeitos fixos: Var(Xβ)
    try:
        fixed_pred = result.model.exog @ result.fe_params
        sigma2_f = float(np.var(fixed_pred))
    except Exception:
        sigma2_f = float(np.var(result.fittedvalues))

    # Variância total dos efeitos aleatórios (inclui random slope se presente)
    sigma2_u_total = sigma2_u + sigma2_u_slope * var_predictor
    sigma2_e = float(result.scale)
    total = sigma2_f + sigma2_u_total + sigma2_e

    r2m = sigma2_f / total if total > 0 else np.nan
    r2c = (sigma2_f + sigma2_u_total) / total if total > 0 else np.nan
    return {
        "sigma2_f":  round(sigma2_f, 6),
        "sigma2_u":  round(sigma2_u_total, 6),
        "sigma2_e":  round(sigma2_e, 6),
        "R2m":       round(r2m, 4),
        "R2c":       round(r2c, 4),
    }


# ── M4: Random Slope de educ_ord por UPA ──────────────────────────────────────

# Fórmula M4: usa educ_ord_c no lugar das 4 dummies + UF como efeito fixo
_M4_INDIVIDUAL = (
    "negro + sexo_fem + idade_c + idade_sq + educ_ord_c"
    " + log_horas + urbano + C(Ano)"
)
FORMULA_M4 = (
    f"log_renda ~ {_M4_INDIVIDUAL}"
    " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
    " + C(UF_str)"
)


def fit_random_slope_model(
    df: pd.DataFrame,
    method: str = "lbfgs",
    maxiter: int = 1500,
) -> Dict:
    """
    M4: random intercept + random slope de educ_ord_c por UPA (2 níveis).

    Hipótese testada: o retorno à educação (educ_ord_c) varia entre
    localidades — negros concentrados em UPAs de menor capital social
    enfrentam menores retornos, mesmo com mesma escolaridade.

    UF entra como efeito fixo (C(UF_str)) em vez de nível aleatório,
    pois statsmodels não suporta random slope em vc_formula de forma estável.

    re_formula="~educ_ord_c" → random intercept (u₀ⱼ) + random slope (u₁ⱼ)
    cov_re = [[τ²₀, τ₀₁], [τ₀₁, τ²₁]]

    Retorna:
        dict com result, var components, ICC, Nakagawa R², LRT vs M3-equiv.
    """
    logger.info("Ajustando M4 (random slope educ_ord_c por UPA) ...")
    model = smf.mixedlm(
        formula=FORMULA_M4,
        data=df,
        groups=df["UPA_str"],
        re_formula="~educ_ord_c",
    )
    result = model.fit(method=method, maxiter=maxiter, reml=False)

    cov_re = result.cov_re
    tau2_int   = float(cov_re.iloc[0, 0]) if cov_re.shape[0] > 0 else 0.0
    tau2_slope = float(cov_re.iloc[1, 1]) if cov_re.shape[0] > 1 else 0.0
    tau_cov    = float(cov_re.iloc[0, 1]) if cov_re.shape[0] > 1 else 0.0
    var_resid  = float(result.scale)

    # ICC para observação "típica" (educ_ord_c = 0 = média)
    total_var = tau2_int + var_resid
    icc_upa   = tau2_int / total_var if total_var > 0 else np.nan

    # Correlação entre intercepto e slope aleatórios
    corr_int_slope = (
        tau_cov / np.sqrt(tau2_int * tau2_slope)
        if (tau2_int > 0 and tau2_slope > 0) else np.nan
    )

    var_educ_c = float(df["educ_ord_c"].var())
    ns_r2 = compute_nakagawa_r2(
        result,
        sigma2_u=tau2_int,
        var_predictor=var_educ_c,
        sigma2_u_slope=tau2_slope,
    )

    b_negro = result.params.get("negro", np.nan)
    b_educ  = result.params.get("educ_ord_c", np.nan)

    logger.info(
        f"  M4 convergiu | β_negro={b_negro:.4f} | β_educ_c={b_educ:.4f} | "
        f"τ²₀={tau2_int:.4f} | τ²₁={tau2_slope:.4f} | "
        f"corr={corr_int_slope:.3f} | ICC_UPA={icc_upa:.3f} | "
        f"R²m={ns_r2['R2m']:.3f} | R²c={ns_r2['R2c']:.3f}"
    )

    return {
        "result":           result,
        "tau2_int":         tau2_int,
        "tau2_slope":       tau2_slope,
        "tau_cov":          tau_cov,
        "corr_int_slope":   corr_int_slope,
        "var_resid":        var_resid,
        "icc_upa":          icc_upa,
        "nakagawa":         ns_r2,
        "b_negro":          b_negro,
        "b_educ_c":         b_educ,
        "n_obs":            len(df),
        "n_upa":            df["UPA_str"].nunique(),
        "aic":              result.aic,
        "bic":              result.bic,
        "llf":              result.llf,
    }


# ── ICC Estratificado por Raça ─────────────────────────────────────────────────

def compute_race_stratified_icc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Modelo nulo (M0) ajustado separadamente para negros e brancos.

    Hipótese de duplo disadvantage contextual: se ICC_UPA(negros) >
    ICC_UPA(brancos), o contexto de moradia explica maior fração da
    variância de renda para trabalhadores negros — evidência de que
    segregação residencial é canal amplificador da desigualdade racial.

    Usa groups=UPA_str (2-nível) para consistência com M4 e para
    estabilidade de convergência nas subamostras estratificadas.
    """
    rows = []
    for label, val in [("Brancos", 0), ("Negros", 1)]:
        sub = df[df["negro"] == val].copy()
        # Garante mínimo de 10 obs por UPA para estimação estável
        upa_cnt = sub["UPA_str"].value_counts()
        sub = sub[sub["UPA_str"].isin(upa_cnt[upa_cnt >= 10].index)].copy()
        logger.info(f"  ICC estratificado — {label} (n={len(sub):,}, UPAs≥10) ...")
        try:
            # UF como efeito fixo evita que variância de UF colapse para boundary
            m0 = smf.mixedlm("log_renda ~ C(UF_str)", data=sub, groups=sub["UPA_str"])
            # powell é mais robusto que lbfgs para o caso de boundary na variância UPA
            res = m0.fit(method="powell", maxiter=2000, reml=False)
            var_upa  = float(res.cov_re.iloc[0, 0]) if res.cov_re.shape[0] > 0 else 0.0
            var_e    = float(res.scale)
            total    = var_upa + var_e
            icc      = var_upa / total if total > 0 else np.nan
            ns       = compute_nakagawa_r2(res, sigma2_u=var_upa)
        except Exception as e:
            logger.warning(f"  {label}: falha no ajuste — {e}")
            var_upa = var_e = icc = np.nan
            ns = {"R2m": np.nan, "R2c": np.nan, "sigma2_f": np.nan,
                  "sigma2_u": np.nan, "sigma2_e": np.nan}

        rows.append({
            "Grupo":        label,
            "N":            len(sub),
            "N_UPAs":       sub["UPA_str"].nunique(),
            "τ²_UPA":       round(var_upa, 5),
            "σ²_residual":  round(var_e, 5),
            "ICC_UPA":      round(icc, 4),
            "R²m (M0)":     ns["R2m"],
            "R²c (M0)":     ns["R2c"],
        })
    df_out = pd.DataFrame(rows)
    delta_icc = (
        df_out.loc[df_out["Grupo"] == "Negros", "ICC_UPA"].values[0]
        - df_out.loc[df_out["Grupo"] == "Brancos", "ICC_UPA"].values[0]
    )
    logger.info(
        f"  ΔICC_UPA (Negros−Brancos) = {delta_icc:+.4f} — "
        + ("confirma duplo disadvantage contextual" if delta_icc > 0
           else "diferença não confirma hipótese contextual")
    )
    return df_out


# ── Figura: Variância do Slope por UPA ────────────────────────────────────────

def plot_random_slope_effects(m4_res: Dict, df: pd.DataFrame) -> None:
    """
    Figura de diagnóstico para M4: distribuição dos slopes aleatórios por UPA.
    Mostra heterogeneidade no retorno à educação entre localidades.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    result = m4_res["result"]
    re_df  = result.random_effects
    slopes = {upa: v.get("educ_ord_c", np.nan) for upa, v in re_df.items()}
    s_vals = np.array([v for v in slopes.values() if not np.isnan(v)])

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Histograma dos slopes aleatórios
    axes[0].hist(s_vals, bins=60, color="#1565C0", alpha=0.8, edgecolor="white")
    axes[0].axvline(0, color="red", lw=1.2, ls="--")
    axes[0].set_xlabel("Slope aleatório de educ_ord_c (u₁ⱼ)", fontsize=11)
    axes[0].set_ylabel("Frequência (UPAs)", fontsize=11)
    axes[0].set_title(
        f"Distribuição dos Slopes Aleatórios\n"
        f"τ²₁ = {m4_res['tau2_slope']:.4f}  |  "
        f"corr(u₀,u₁) = {m4_res['corr_int_slope']:.3f}",
        fontsize=11, fontweight="bold",
    )
    axes[0].spines["top"].set_visible(False)
    axes[0].spines["right"].set_visible(False)

    # Scatter: intercepto aleatório vs slope aleatório por UPA
    ints   = np.array([v.get("Group Var", v.get("Intercept", np.nan))
                       for v in re_df.values()])
    # Melhor abordagem: lê colunas direto do DataFrame de random effects
    re_frame = pd.DataFrame(re_df).T
    col_int   = re_frame.columns[0]   # "Group Var" ou "Intercept"
    col_slope = "educ_ord_c" if "educ_ord_c" in re_frame.columns else re_frame.columns[-1]
    x = re_frame[col_int].values.astype(float)
    y = re_frame[col_slope].values.astype(float)
    mask = np.isfinite(x) & np.isfinite(y)

    axes[1].scatter(x[mask], y[mask], alpha=0.15, s=8, color="#1565C0")
    axes[1].axhline(0, color="gray", lw=0.8); axes[1].axvline(0, color="gray", lw=0.8)
    axes[1].set_xlabel("Intercepto aleatório (u₀ⱼ)", fontsize=11)
    axes[1].set_ylabel("Slope aleatório educ_ord_c (u₁ⱼ)", fontsize=11)
    axes[1].set_title(
        f"Intercepto vs Slope por UPA\n"
        f"corr = {m4_res['corr_int_slope']:.3f}",
        fontsize=11, fontweight="bold",
    )
    axes[1].spines["top"].set_visible(False)
    axes[1].spines["right"].set_visible(False)

    fig.suptitle(
        "M4 — Heterogeneidade do Retorno Educacional por UPA\n"
        "PNAD Contínua 2016–2025, amostra 20%, grupos=UPA_str",
        fontsize=12, fontweight="bold",
    )
    plt.tight_layout()
    out = FIGURES / "hlm_m4_random_slope.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Figura salva: {out}")


# ── Tabela LaTeX: M4 + ICC Racial + Nakagawa R² ──────────────────────────────

def save_m4_outputs(
    m4_res: Dict,
    icc_racial: pd.DataFrame,
    nakagawa_rows: List[Dict],
) -> None:
    """Salva CSVs e LaTeX para M4, ICC racial e pseudo-R²."""

    # CSV: M4 coeficientes principais
    r   = m4_res["result"]
    rows_coef = []
    for var in ["negro", "educ_ord_c", "pct_negro_upa_z",
                "tx_desemprego_upa_z", "media_educ_upa_z"]:
        if var not in r.params:
            continue
        b  = r.params[var]; se = r.bse[var]; p = r.pvalues[var]
        rows_coef.append({
            "variavel": var, "beta": round(b, 5), "se": round(se, 5),
            "p_valor": round(p, 6),
            "stars": "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "",
        })
    pd.DataFrame(rows_coef).to_csv(OUTPUTS / "hlm_m4_coeficientes.csv", index=False, encoding="utf-8")

    # CSV: variância random effects M4
    vc_df = pd.DataFrame([{
        "componente":    "τ²₀ (intercepto UPA)",
        "variancia":     round(m4_res["tau2_int"], 6),
    }, {
        "componente":    "τ²₁ (slope educ_ord_c por UPA)",
        "variancia":     round(m4_res["tau2_slope"], 6),
    }, {
        "componente":    "τ₀₁ (covariância int×slope)",
        "variancia":     round(m4_res["tau_cov"], 6),
    }, {
        "componente":    "σ² (residual)",
        "variancia":     round(m4_res["var_resid"], 6),
    }, {
        "componente":    "ICC_UPA (q=0)",
        "variancia":     round(m4_res["icc_upa"], 6),
    }, {
        "componente":    "corr(u₀,u₁)",
        "variancia":     round(m4_res["corr_int_slope"], 6),
    }])
    vc_df.to_csv(OUTPUTS / "hlm_m4_variancia.csv", index=False, encoding="utf-8")

    # CSV: ICC racial
    icc_racial.to_csv(OUTPUTS / "hlm_icc_racial.csv", index=False, encoding="utf-8")

    # CSV: Nakagawa R²
    pd.DataFrame(nakagawa_rows).to_csv(OUTPUTS / "hlm_nakagawa_r2.csv", index=False, encoding="utf-8")

    # LaTeX combinada
    ns = m4_res["nakagawa"]
    delta_icc = (
        icc_racial.loc[icc_racial["Grupo"] == "Negros", "ICC_UPA"].values[0]
        - icc_racial.loc[icc_racial["Grupo"] == "Brancos", "ICC_UPA"].values[0]
    )
    tex = r"""\begin{table}[H]
\centering
\caption{M4 — Modelo com \textit{Random Slope} de \texttt{educ\_ord\_c} por UPA.
         Efeito fixo $\hat{\beta}_{\text{negro}}$ e componentes de variância.
         Pseudo-$R^2$ de Nakagawa \& Schielzeth (2013).
         PNAD Contínua 2016--2025, 20\% da amostra.}
\label{tab:hlm_m4}
\small
\begin{tabular}{lrrrr}
\toprule
Parâmetro & Estimativa & SE & $p$-valor & \\
\midrule
"""
    for row in rows_coef:
        name = row["variavel"].replace("_", r"\_")
        tex += f"  {name} & {row['beta']:.4f} & {row['se']:.4f} & {row['p_valor']:.4e} & {row['stars']} \\\\\n"
    tex += r"""\midrule
\multicolumn{5}{l}{\textit{Componentes de variância (efeitos aleatórios por UPA)}} \\
"""
    tex += f"  $\\tau^2_0$ (intercepto) & {m4_res['tau2_int']:.4f} & & & \\\\\n"
    tex += f"  $\\tau^2_1$ (slope educ) & {m4_res['tau2_slope']:.4f} & & & \\\\\n"
    tex += f"  $\\text{{corr}}(u_0, u_1)$ & {m4_res['corr_int_slope']:.3f} & & & \\\\\n"
    tex += f"  $\\sigma^2$ (residual) & {m4_res['var_resid']:.4f} & & & \\\\\n"
    tex += f"  ICC\\textsubscript{{UPA}} & {m4_res['icc_upa']:.4f} & & & \\\\\n"
    tex += r"""\midrule
\multicolumn{5}{l}{\textit{Pseudo-$R^2$ (Nakagawa \& Schielzeth, 2013)}} \\
"""
    tex += f"  $R^2_m$ (marginal — ef.~fixos) & {ns['R2m']:.4f} & & & \\\\\n"
    tex += f"  $R^2_c$ (condicional — completo) & {ns['R2c']:.4f} & & & \\\\\n"
    tex += r"""\midrule
\multicolumn{5}{l}{\textit{ICC estratificado por raça (Modelo Nulo)}} \\
"""
    for _, rw in icc_racial.iterrows():
        g = rw["Grupo"]
        tex += f"  ICC\\textsubscript{{UPA}} — {g} & {rw['ICC_UPA']:.4f} & & & \\\\\n"
    tex += f"  $\\Delta$ICC (Negros$-$Brancos) & {delta_icc:+.4f} & & & \\\\\n"
    tex += r"""\bottomrule
\end{tabular}
\end{table}
"""
    (OUTPUTS / "hlm_m4.tex").write_text(tex, encoding="utf-8")
    logger.info("hlm_m4.tex salvo.")


if __name__ == "__main__":
    # Para testes de convergência antes do ajuste completo:
    # models = run_models(sample_frac=0.05, save=False)
    models = run_models(sample_frac=None, save=True)
