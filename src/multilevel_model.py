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
                    + ε_{ijk},    ε ~ N(0, σ²)

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
        "educ_fund_completo", "educ_medio_completo",
        "educ_superior_completo", "educ_pos_graduacao",
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
    return HLMResults(
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

    if save:
        save_outputs(models, results_table, decomposition, lrt_results)

    print_discussion_summary(models)
    return models


if __name__ == "__main__":
    # Para testes de convergência antes do ajuste completo:
    # models = run_models(sample_frac=0.05, save=False)
    models = run_models(sample_frac=None, save=True)
