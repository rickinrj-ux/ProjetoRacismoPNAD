"""
interseccionalidade.py
======================
Interseccionalidade formalizada: raça × gênero × escolaridade.

Abordagem:
    1. HLM com termos de interação explícitos raça×gênero, raça×educação
       e a tripla raça×gênero×educação_superior.
    2. Estimação dos efeitos marginais esperados (EME) para 8 grupos
       definidos pela combinação {negro/branco} × {homem/mulher} × {superior/não}.
    3. Teste do "duplo disadvantage" de mulheres negras:
       EME(mulher negra) < EME(mulher branca) + EME(negro homem)?

Hipóteses:
    H1: O efeito de ser negro é heterogêneo por gênero (interação raça×gênero).
    H2: O retorno à educação superior é menor para negros (interação raça×educ).
    H3: Mulheres negras enfrentam penalidade adicional além da soma dos
        efeitos de gênero e raça isolados (efeito interseccional puro).

Referências:
    Crenshaw, K. (1989). Demarginalizing the intersection of race and sex.
        U. Chi. Legal F., 139.
    Bauer, G. R. (2014). Incorporating intersectionality theory into
        population health research. Social Science & Medicine, 110, 10-17.
    McCall, L. (2005). The complexity of intersectionality. Signs, 30(3).
"""

import logging
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

logger = logging.getLogger(__name__)

ROOT          = Path(__file__).parent.parent
FEATURES_PATH = ROOT / "data" / "processed" / "features.parquet"
OUT_FIG       = ROOT / "outputs" / "figures"
OUT_TAB       = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)

# Variáveis necessárias no features.parquet
MODEL_VARS = [
    "log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_ord", "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "UPA", "UF",
]

# Grupos interseccionais (race × sex × education)
GRUPOS_LABELS = {
    (0, 0, 0): "Homem Branco Sem Superior",
    (0, 0, 1): "Homem Branco Com Superior",
    (0, 1, 0): "Mulher Branca Sem Superior",
    (0, 1, 1): "Mulher Branca Com Superior",
    (1, 0, 0): "Homem Negro Sem Superior",
    (1, 0, 1): "Homem Negro Com Superior",
    (1, 1, 0): "Mulher Negra Sem Superior",
    (1, 1, 1): "Mulher Negra Com Superior",
}


# ── Carregamento e criação de interações ──────────────────────────────────────

def carregar_e_preparar(sample_frac: Optional[float] = None) -> pd.DataFrame:
    """
    Carrega features e cria variáveis de interação raça × gênero × educação.

    As interações são criadas como colunas explícitas (não via formula string)
    para facilitar a extração dos EMEs por grupo e garantir interpretabilidade
    no contexto do TCC.
    """
    df = pd.read_parquet(FEATURES_PATH)
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    df = df.dropna(subset=MODEL_VARS).reset_index(drop=True)

    upa_cnt = df["UPA"].value_counts()
    df = df[df["UPA"].isin(upa_cnt[upa_cnt >= 10].index)].reset_index(drop=True)

    df["UPA_str"] = df["UPA"].astype(str)
    df["UF_str"]  = df["UF"].astype(str)
    df["log_renda"] = df["log_renda"].astype(float)

    # ── Variáveis de interação de 1ª e 2ª ordem ──────────────────────────
    # negro × sexo_fem: captura o disadvantage específico de mulheres negras
    df["negro_x_mulher"] = df["negro"] * df["sexo_fem"]

    # negro × educação superior: testa se negros têm menor retorno ao diploma
    df["negro_x_superior"] = df["negro"] * df["educ_superior_completo"]

    # mulher × educação superior: testa o retorno de gênero ao diploma
    df["mulher_x_superior"] = df["sexo_fem"] * df["educ_superior_completo"]

    # Interação tripla: identifica o efeito interseccional puro
    # (diferente da soma dos efeitos de 1ª ordem)
    df["negro_x_mulher_x_superior"] = (
        df["negro"] * df["sexo_fem"] * df["educ_superior_completo"]
    )

    # Variável de grupo interseccional para os EMEs
    df["grupo_id"] = list(zip(
        df["negro"].astype(int),
        df["sexo_fem"].astype(int),
        df["educ_superior_completo"].astype(int),
    ))

    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)

    logger.info(f"Dataset interseccionalidade: {len(df):,} obs.")
    return df


# ── Modelos HLM ──────────────────────────────────────────────────────────────

def ajustar_hlm_base(df: pd.DataFrame) -> object:
    """
    HLM de referência sem interações — estabelece gap bruto por raça e gênero.
    Usado para comparação com o modelo interseccional.
    """
    formula = (
        "log_renda ~ negro + sexo_fem + idade_c + idade_sq"
        " + educ_fund_completo + educ_medio_completo"
        " + educ_superior_completo + educ_pos_graduacao"
        " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
    )
    logger.info("Ajustando HLM base (sem interações)...")
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        model  = smf.mixedlm(formula, data=df, groups=df["UF_str"])
        result = model.fit(method="powell", maxiter=500, reml=True)
    b_negro = result.params.get("negro", np.nan)
    b_mulher = result.params.get("sexo_fem", np.nan)
    logger.info(f"  HLM base: β_negro={b_negro:.4f}, β_mulher={b_mulher:.4f}")
    return result


def ajustar_hlm_interseccional(df: pd.DataFrame) -> object:
    """
    HLM com interações raça × gênero × educação superior.

    O coeficiente de 'negro_x_mulher' testa H1: se o efeito de ser negro
    difere entre homens e mulheres.

    O coeficiente de 'negro_x_mulher_x_superior' testa H3: se mulheres negras
    com ensino superior têm penalidade adicional além da soma dos efeitos
    individuais (efeito interseccional puro de Crenshaw, 1989).
    """
    formula = (
        "log_renda ~ negro + sexo_fem + educ_superior_completo"
        " + negro_x_mulher + negro_x_superior + mulher_x_superior"
        " + negro_x_mulher_x_superior"
        " + idade_c + idade_sq + educ_fund_completo + educ_medio_completo"
        " + educ_pos_graduacao"
        " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
    )
    logger.info("Ajustando HLM interseccional (com interações triplas)...")
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        model  = smf.mixedlm(formula, data=df, groups=df["UF_str"])
        result = model.fit(method="powell", maxiter=500, reml=True)

    # Log dos coeficientes-chave
    for var in ["negro", "sexo_fem", "negro_x_mulher", "negro_x_superior",
                "negro_x_mulher_x_superior"]:
        b  = result.params.get(var, np.nan)
        pv = result.pvalues.get(var, np.nan)
        stars = "***" if pv < 0.001 else "**" if pv < 0.01 else "*" if pv < 0.05 else "ns"
        logger.info(f"  {var:<35s}: {b:.4f}{stars}")
    return result


# ── Efeitos Marginais Esperados por Grupo ─────────────────────────────────────

def calcular_eme_por_grupo(
    result_base: object,
    result_inter: object,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula o Efeito Marginal Esperado (EME) de log-renda para cada grupo
    interseccional usando predição contrafactual:

        EME(grupo) = Ŷ(negro=n, mulher=m, superior=s, X̄)
        onde X̄ são as médias das covariáveis de controle.

    Permite comparar: quanto ganha em média cada subgrupo,
    holding constant outras características.
    """
    # Perfil de referência (médias das covariáveis de controle)
    ctrl = {
        "idade_c":              df["idade_c"].mean(),
        "idade_sq":             df["idade_sq"].mean(),
        "educ_fund_completo":   df["educ_fund_completo"].mean(),
        "educ_medio_completo":  df["educ_medio_completo"].mean(),
        "educ_pos_graduacao":   df["educ_pos_graduacao"].mean(),
        "pct_negro_upa_z":      0.0,
        "tx_desemprego_upa_z":  0.0,
        "media_educ_upa_z":     0.0,
    }

    rows = []
    for (neg, mul, sup), label in GRUPOS_LABELS.items():
        # Predição contrafactual com modelo interseccional
        p = ctrl.copy()
        p.update({
            "negro":                     neg,
            "sexo_fem":                  mul,
            "educ_superior_completo":    sup,
            "negro_x_mulher":            neg * mul,
            "negro_x_superior":          neg * sup,
            "mulher_x_superior":         mul * sup,
            "negro_x_mulher_x_superior": neg * mul * sup,
        })
        xb = sum(
            result_inter.params.get(v, 0) * val
            for v, val in p.items()
            if v in result_inter.params
        ) + result_inter.params.get("Intercept", 0)

        # Média observada no dataset para validação
        mask = (
            (df["negro"] == neg) &
            (df["sexo_fem"] == mul) &
            (df["educ_superior_completo"] == sup)
        )
        n_grupo = mask.sum()
        log_renda_obs = df.loc[mask, "log_renda"].mean() if n_grupo > 0 else np.nan

        rows.append({
            "grupo":           label,
            "negro":           neg,
            "mulher":          mul,
            "superior":        sup,
            "n_obs":           n_grupo,
            "log_renda_pred":  xb,
            "log_renda_obs":   log_renda_obs,
            "renda_pred_exp":  np.exp(xb),
        })

    df_eme = pd.DataFrame(rows).sort_values("log_renda_pred", ascending=False)
    return df_eme


def tabela_coeficientes_interseccional(result_base, result_inter) -> pd.DataFrame:
    """Tabela comparativa HLM base vs. HLM interseccional."""
    vars_key = [
        "Intercept", "negro", "sexo_fem", "educ_superior_completo",
        "negro_x_mulher", "negro_x_superior", "mulher_x_superior",
        "negro_x_mulher_x_superior",
        "idade_c", "educ_fund_completo", "educ_medio_completo",
        "educ_pos_graduacao", "pct_negro_upa_z",
    ]
    rows = []
    for var in vars_key:
        row = {"Variável": var}
        for label, res in [("Base", result_base), ("Interseccional", result_inter)]:
            if var in res.params:
                b  = res.params[var]
                se = res.bse[var]
                pv = res.pvalues[var]
                st = "***" if pv < 0.001 else "**" if pv < 0.01 else "*" if pv < 0.05 else ""
                row[label] = f"{b:.4f}{st} ({se:.4f})"
            else:
                row[label] = "—"
        rows.append(row)
    return pd.DataFrame(rows)


# ── Visualizações ─────────────────────────────────────────────────────────────

def plotar_eme_grupos(df_eme: pd.DataFrame) -> None:
    """Gráfico de barras dos EMEs por grupo interseccional."""
    df_plot = df_eme.sort_values("log_renda_pred", ascending=True).copy()

    # Cores: negros = vermelho, brancos = azul; escuro = mulher
    def _cor(row):
        if row["negro"] == 1 and row["mulher"] == 1:
            return "#c0392b"
        elif row["negro"] == 1:
            return "#e74c3c"
        elif row["mulher"] == 1:
            return "#2980b9"
        return "#3498db"

    cores = [_cor(r) for _, r in df_plot.iterrows()]

    fig, ax = plt.subplots(figsize=(9, 6))
    bars = ax.barh(
        df_plot["grupo"], df_plot["log_renda_pred"],
        color=cores, edgecolor="black", linewidth=0.5,
    )
    ax.set_xlabel("Log-renda predita (EME)", fontsize=11)
    ax.set_title(
        "Efeito Marginal Esperado por Grupo Interseccional\n"
        "Vermelho = Negro  ·  Azul = Branco  ·  Escuro = Mulher",
        fontsize=11,
    )
    for bar, (_, row) in zip(bars, df_plot.iterrows()):
        ax.text(
            bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
            f"exp={row['renda_pred_exp']:.0f}",
            va="center", fontsize=8,
        )
    plt.tight_layout()
    fig.savefig(OUT_FIG / "interseccional_eme_grupos.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: interseccional_eme_grupos.png")


def plotar_interacoes_coeficientes(result_inter) -> None:
    """Visualiza os termos de interação e seus IC95%."""
    termos = {
        "negro": "Negro (homem, sem superior)",
        "sexo_fem": "Mulher (branca, sem superior)",
        "negro_x_mulher": "Negro × Mulher",
        "negro_x_superior": "Negro × Superior",
        "mulher_x_superior": "Mulher × Superior",
        "negro_x_mulher_x_superior": "Negro × Mulher × Superior\n(interação tripla)",
    }
    labels, coefs, ic_l, ic_h = [], [], [], []
    for var, label in termos.items():
        if var in result_inter.params:
            b  = result_inter.params[var]
            se = result_inter.bse[var]
            labels.append(label)
            coefs.append(b)
            ic_l.append(b - 1.96 * se)
            ic_h.append(b + 1.96 * se)

    fig, ax = plt.subplots(figsize=(8, 5))
    y_pos = np.arange(len(labels))
    cores = ["#c0392b" if c < 0 else "#27ae60" for c in coefs]
    ax.barh(
        y_pos, coefs,
        xerr=[np.array(coefs) - np.array(ic_l), np.array(ic_h) - np.array(coefs)],
        color=cores, edgecolor="black", linewidth=0.5, capsize=4,
    )
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Coeficiente β (log-renda)  ·  IC 95%", fontsize=11)
    ax.set_title("Termos de Interação — HLM Interseccional\nVermelho = Efeito negativo", fontsize=11)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "interseccional_coeficientes.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: interseccional_coeficientes.png")


# ── Pipeline principal ────────────────────────────────────────────────────────

def run_interseccionalidade(sample_frac: Optional[float] = None) -> Dict:
    """
    Pipeline completo de análise interseccional.

    Returns:
        dict com modelos ajustados, EMEs por grupo e tabelas de coeficientes.
    """
    df = carregar_e_preparar(sample_frac=sample_frac)

    result_base  = ajustar_hlm_base(df)
    result_inter = ajustar_hlm_interseccional(df)

    # Efeitos marginais esperados por grupo
    df_eme = calcular_eme_por_grupo(result_base, result_inter, df)
    df_eme.to_csv(OUT_TAB / "interseccional_eme.csv", index=False)

    # Tabela comparativa de coeficientes
    tab_coef = tabela_coeficientes_interseccional(result_base, result_inter)
    tab_coef.to_csv(OUT_TAB / "interseccional_coeficientes.csv", index=False)
    (OUT_TAB / "interseccional_coeficientes.tex").write_text(
        tab_coef.to_latex(
            index=False, escape=False,
            caption=(
                "HLM Base e Interseccional — Efeitos de Raça × Gênero × Educação. "
                "PNAD Contínua. *** p<0,001; ** p<0,01; * p<0,05."
            ),
            label="tab:interseccional",
        ),
        encoding="utf-8",
    )

    plotar_eme_grupos(df_eme)
    plotar_interacoes_coeficientes(result_inter)

    # ── Teste do "duplo disadvantage" de Crenshaw ──────────────────────
    p = result_inter.params
    b_negro      = p.get("negro", 0)
    b_mulher     = p.get("sexo_fem", 0)
    b_nx_m       = p.get("negro_x_mulher", 0)
    efeito_aditivo    = b_negro + b_mulher
    efeito_intersec   = b_negro + b_mulher + b_nx_m
    penalidade_extra  = b_nx_m

    print("\n── SUMÁRIO: Interseccionalidade ──")
    print(f"β_negro (homem, sem superior)  : {b_negro:.4f}  →  gap {(np.exp(b_negro)-1)*100:.1f}%")
    print(f"β_mulher (branca, sem superior): {b_mulher:.4f}  →  gap {(np.exp(b_mulher)-1)*100:.1f}%")
    print(f"β_negro×mulher (interação)     : {b_nx_m:.4f}")
    print(f"Efeito aditivo mulher negra    : {efeito_aditivo:.4f}  →  {(np.exp(efeito_aditivo)-1)*100:.1f}%")
    print(f"Efeito interseccional real     : {efeito_intersec:.4f}  →  {(np.exp(efeito_intersec)-1)*100:.1f}%")
    print(f"Penalidade extra interseccional: {penalidade_extra:.4f}  →  {(np.exp(penalidade_extra)-1)*100:.1f}%")
    print(f"\n{'duplo disadvantage confirmado' if b_nx_m < 0 else 'sem penalidade adicional'} (β_nx_m {'<' if b_nx_m < 0 else '>='} 0)")
    print("\nEMEs por grupo (top 8):")
    print(df_eme[["grupo", "n_obs", "log_renda_pred", "renda_pred_exp"]].to_string(index=False))

    return {
        "result_base": result_base,
        "result_inter": result_inter,
        "eme": df_eme,
        "coeficientes": tab_coef,
    }
