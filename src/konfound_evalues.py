"""
konfound_evalues.py
===================
Análise de sensibilidade a variáveis omitidas para os modelos primários do TCC:

  • Konfound (Frank et al., 2013) para HLM M1–M4
    Opera diretamente no t-estatístico do próprio modelo hierárquico,
    sem exigir decomposição de R² linear. Calcula:
      - pkonfound: % do efeito que precisaria ser confundido para invalidar
        a inferência (|t_obs| → t_crit).
      - ITCV: correlação parcial mínima entre confundidor e tratamento e
        resultado para invalidar a inferência.

  • E-values (VanderWeele & Ding, 2017) para GLMM
    Agnóstico ao link function e ao R² de modelos mistos. Para OR < 1:
      E = (1/OR) + √[(1/OR)(1/OR − 1)]
    Interpreta-se como: um confundidor precisaria ter associação ≥ E com
    raça E com a probabilidade de ocupar cargo qualificado.

  • Oster bounds (OLS auxiliar, posicionamento comparativo)
    Válidos apenas para os modelos OLS auxiliares da decomposição OB.
    Incluídos aqui para contraste metodológico explícito.

Referências:
    Frank, K. A., Maroulis, S., Duong, M., & Kelcey, B. (2013).
        What would it take to change an inference? Using Rubin's causal
        model in education research. Educational Evaluation and Policy
        Analysis, 35(4), 437–460.
    VanderWeele, T. J., & Ding, P. (2017). Sensitivity analysis in
        observational research: Introducing the E-value. Annals of
        Internal Medicine, 167(4), 268–274.
    Oster, E. (2019). Unobservable selection and coefficient stability.
        Journal of Business & Economic Statistics, 37(2), 187–204.
"""

import logging
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ROOT    = Path(__file__).parent.parent
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TAB = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)

T_CRIT = 1.96  # bilateral α = 0.05, n grande


# ── Konfound (Frank et al., 2013) ──────────────────────────────────────────────

def pkonfound(t_obs: float, t_crit: float = T_CRIT) -> float:
    """
    Percentual do efeito que precisaria ser 'confundido' para invalidar a
    inferência — i.e., reduzir |t_obs| até t_crit.

    pkonfound = (|t_obs| − t_crit) / |t_obs| × 100

    Interpretação: se pkonfound = 98%, seria necessário que 98% do sinal
    observado fosse explicável por viés de seleção para que a inferência
    fosse invalidada.
    """
    return 100 * (abs(t_obs) - t_crit) / abs(t_obs)


def itcv(t_obs: float, n: int, k: int = 5) -> float:
    """
    Impact Threshold of a Confounding Variable.

    Mínimo |r_confundidor_X| × |r_confundidor_Y| necessário para invalidar
    a inferência. Baseado na correlação parcial entre negro e log_renda.

    r_xy = t / √(t² + df)   onde df = n − k − 1
    ITCV = r_xy² (correlação parcial ao quadrado, threshold de invalidação)
    """
    df = n - k - 1
    r_xy = t_obs / np.sqrt(t_obs**2 + df)
    return float(r_xy**2)


def tabela_konfound_hlm(hlm_data: List[Dict]) -> pd.DataFrame:
    """
    Gera tabela Konfound para série HLM M1–M4.

    hlm_data: lista de dicts com {modelo, beta, se, n, descricao}
    """
    rows = []
    for m in hlm_data:
        t = m["beta"] / m["se"]
        pk = pkonfound(t)
        iv = itcv(t, m["n"])
        rows.append({
            "Modelo":       m["modelo"],
            "Descrição":    m["descricao"],
            "β_negro":      round(m["beta"], 4),
            "SE":           round(m["se"], 4),
            "t":            round(t, 1),
            "Gap (%)":      round((np.exp(m["beta"]) - 1) * 100, 1),
            "pkonfound (%)": round(pk, 1),
            "ITCV":         round(iv, 5),
            "n":            m["n"],
        })
    return pd.DataFrame(rows)


# ── E-values (VanderWeele & Ding, 2017) ───────────────────────────────────────

def evalue_or(or_val: float) -> float:
    """
    E-value para Odds Ratio.

    Para OR < 1, inverte para OR* = 1/OR antes de aplicar a fórmula.
    E = OR* + √[OR*(OR* − 1)]

    Interpretação: qualquer confounder precisaria ter associação ≥ E
    com raça E com o desfecho para explicar completamente o OR observado.
    """
    if or_val < 1:
        or_val = 1 / or_val
    return float(or_val + np.sqrt(or_val * (or_val - 1)))


def tabela_evalues_glmm(glmm_path: Path) -> pd.DataFrame:
    """Calcula E-values para todos os ORs em glmm_glassceil_full.csv."""
    df_glmm = pd.read_csv(glmm_path)

    rows = []
    for _, row in df_glmm.iterrows():
        or_val  = row["OR_negro"]
        or_lo   = row["CI95_lo"]
        or_hi   = row["CI95_hi"]
        ev      = evalue_or(or_val)
        ev_ci   = evalue_or(or_hi)  # CI bound mais próximo de 1 → E-value mais conservador

        rows.append({
            "Desfecho":     row["desfecho"],
            "Modelo":       row["modelo"],
            "OR":           round(or_val, 4),
            "IC 95% lo":    round(or_lo, 4),
            "IC 95% hi":    round(or_hi, 4),
            "E-value (OR)": round(ev, 3),
            "E-value (CI)": round(ev_ci, 3),
            "Interpretação": (
                f"Confounder precisaria ter ≥{ev:.2f}× associação "
                f"com raça E com {row['desfecho']} para zerar o efeito"
            ),
        })
    return pd.DataFrame(rows)


# ── Tabela comparativa metodológica ───────────────────────────────────────────

def tabela_comparativa_metodologias(
    tab_konfound: pd.DataFrame,
    tab_evalues: pd.DataFrame,
    tab_oster: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Consolida os três métodos em uma tabela única para o TCC,
    com coluna explícita sobre aplicabilidade ao modelo primário.
    """
    rows = []

    # Konfound HLM
    for _, r in tab_konfound.iterrows():
        rows.append({
            "Método":                    "Konfound (Frank et al., 2013)",
            "Modelo":                    f"HLM {r['Modelo']}",
            "Estatística central":       f"t = {r['t']:.1f}",
            "Resultado robustez":        f"pkonfound = {r['pkonfound (%)']:.1f}%",
            "Aplica ao modelo primário": "✓ Sim",
            "Nota":                      "Usa t do próprio HLM; agnóstico ao R²",
        })

    # E-values GLMM — apenas ocp_qualif M2 e M1 para concisão
    for _, r in tab_evalues[tab_evalues["Desfecho"] == "ocp_qualif"].iterrows():
        rows.append({
            "Método":                    "E-value (VanderWeele & Ding, 2017)",
            "Modelo":                    f"GLMM {r['Modelo']} ({r['Desfecho']})",
            "Estatística central":       f"OR = {r['OR']:.4f}",
            "Resultado robustez":        f"E = {r['E-value (OR)']:.3f} (CI: {r['E-value (CI)']:.3f})",
            "Aplica ao modelo primário": "✓ Sim",
            "Nota":                      "Usa OR; agnóstico ao link function e R² misto",
        })

    # Oster OLS (se disponível)
    if tab_oster is not None:
        for _, r in tab_oster.iterrows():
            rows.append({
                "Método":                    "Oster bounds (Oster, 2019)",
                "Modelo":                    f"OLS {r['Modelo restrito']}",
                "Estatística central":       f"R² = {r['R̃²']}",
                "Resultado robustez":        f"δ* = {r['δ*']}; β*(δ=1) = {r['β*(δ=1)']}",
                "Aplica ao modelo primário": "✗ Não (OLS auxiliar)",
                "Nota":                      "Válido para OB; não aplica ao HLM (ICC>5%)",
            })

    return pd.DataFrame(rows)


# ── Figura comparativa ─────────────────────────────────────────────────────────

def plotar_sensibilidade_comparativa(
    tab_konfound: pd.DataFrame,
    tab_evalues: pd.DataFrame,
) -> None:
    """
    Dois painéis lado a lado:
    (1) pkonfound por modelo HLM (barra horizontal, linha de referência 95%)
    (2) E-values por desfecho GLMM (barra vertical, linha de referência E=1)
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Painel 1 — Konfound HLM
    labels_hlm = tab_konfound["Modelo"].tolist()
    pk_vals    = tab_konfound["pkonfound (%)"].tolist()
    cores_hlm  = ["#27ae60" if v >= 95 else "#f39c12" for v in pk_vals]
    y_pos = np.arange(len(labels_hlm))
    ax1.barh(y_pos, pk_vals, color=cores_hlm, alpha=0.85, edgecolor="black", linewidth=0.5)
    ax1.axvline(95, color="#c0392b", linewidth=1.2, linestyle="--", label="95% (referência)")
    ax1.axvline(99, color="#7f8c8d", linewidth=0.8, linestyle=":", label="99%")
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(labels_hlm)
    ax1.set_xlabel("pkonfound (%)")
    ax1.set_xlim(0, 105)
    ax1.set_title(
        "Konfound (Frank et al., 2013)\nHLM: % do efeito que precisaria ser confundido",
        fontsize=10,
    )
    ax1.legend(fontsize=8)
    for yi, pk in zip(y_pos, pk_vals):
        ax1.text(pk + 0.5, yi, f"{pk:.1f}%", va="center", fontsize=9, fontweight="bold")

    # Painel 2 — E-values GLMM
    df_ev_plot = tab_evalues[tab_evalues["Desfecho"].isin(["ocp_qualif", "y_top20", "y_top10"])]
    labels_glmm = [f"{r['Desfecho']}\n{r['Modelo']}" for _, r in df_ev_plot.iterrows()]
    ev_vals     = df_ev_plot["E-value (OR)"].tolist()
    ev_ci_vals  = df_ev_plot["E-value (CI)"].tolist()
    x_pos = np.arange(len(labels_glmm))
    ax2.bar(x_pos - 0.2, ev_vals,    0.35, color="#3498db", alpha=0.85, label="E-value (OR)")
    ax2.bar(x_pos + 0.2, ev_ci_vals, 0.35, color="#85c1e9", alpha=0.85, label="E-value (IC hi)")
    ax2.axhline(2.0, color="#c0392b", linewidth=1.2, linestyle="--", label="E = 2 (referência comum)")
    ax2.axhline(1.0, color="black",   linewidth=0.8, linestyle=":")
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(labels_glmm, fontsize=8)
    ax2.set_ylabel("E-value")
    ax2.set_title(
        "E-values (VanderWeele & Ding, 2017)\nGLMM: associação mínima do confounder para zerar OR",
        fontsize=10,
    )
    ax2.legend(fontsize=8)
    for xi, ev in zip(x_pos, ev_vals):
        ax2.text(xi - 0.2, ev + 0.03, f"{ev:.2f}", ha="center", fontsize=8)

    plt.suptitle(
        "Sensibilidade a Variáveis Omitidas — Modelos Primários do TCC\n"
        "Konfound para HLM  ·  E-values para GLMM  ·  PNAD Contínua 2016–2025",
        fontsize=11,
    )
    plt.tight_layout()
    fig.savefig(OUT_FIG / "sensibilidade_konfound_evalues.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: sensibilidade_konfound_evalues.png")


# ── Pipeline principal ─────────────────────────────────────────────────────────

def run_konfound_evalues() -> Dict:
    """
    Executa Konfound (HLM) e E-values (GLMM) sem re-estimar modelos —
    usa os coeficientes e SEs já salvos em outputs/tables/.
    """
    # ── Dados HLM (hlm_serie_completo.csv) — população completa ──────────────
    # N=7,689,426 | 40,295 UPAs | 27 UFs | REML+Powell | run_hlm_serie_completa.py
    hlm_data = [
        {"modelo": "M1", "descricao": "Individual (dem. + educ. + horas)",
         "beta": -0.2148, "se": 0.0006, "n": 7_689_426},
        {"modelo": "M2", "descricao": "Localidade (+contexto UPA)",
         "beta": -0.1021, "se": 0.0006, "n": 7_689_426},
        {"modelo": "M3", "descricao": "Completo (+contexto UF)",
         "beta": -0.1021, "se": 0.0006, "n": 7_689_426},
        {"modelo": "M4", "descricao": "Ocupação (controles CBO)",
         "beta": -0.0644, "se": 0.0005, "n": 7_689_426},
    ]

    # Comparativo OLS (mesmos modelos, SEs clusterizados por UF)
    ols_data = [
        {"modelo": "M1_OLS", "descricao": "Individual (OLS, SE clusterizado)",
         "beta": -0.2148, "se": 0.0093, "n": 7_689_426},
        {"modelo": "M2_OLS", "descricao": "Localidade (OLS)",
         "beta": -0.1021, "se": 0.0034, "n": 7_689_426},
        {"modelo": "M3_OLS", "descricao": "Completo (OLS)",
         "beta": -0.1021, "se": 0.0034, "n": 7_689_426},
        {"modelo": "M4_OLS", "descricao": "Ocupação (OLS)",
         "beta": -0.0644, "se": 0.0037, "n": 7_689_426},
    ]

    tab_hlm = tabela_konfound_hlm(hlm_data)
    tab_ols = tabela_konfound_hlm(ols_data)

    # ── E-values GLMM ─────────────────────────────────────────────────────────
    glmm_path = ROOT / "outputs" / "tables" / "glmm_glassceil_full.csv"
    tab_ev = tabela_evalues_glmm(glmm_path)

    # ── Oster bounds (lê resultado existente se disponível) ────────────────────
    oster_path = ROOT / "outputs" / "tables" / "oster_bounds.csv"
    tab_oster = pd.read_csv(oster_path) if oster_path.exists() else None

    # ── Tabela comparativa HLM vs OLS (Konfound) ──────────────────────────────
    tab_hlm_vs_ols = pd.DataFrame({
        "Modelo":             [m["modelo"] for m in hlm_data[:4]],
        "β_negro":            [m["beta"] for m in hlm_data[:4]],
        "SE (HLM)":           [m["se"] for m in hlm_data[:4]],
        "t (HLM)":            [round(m["beta"]/m["se"], 1) for m in hlm_data[:4]],
        "pkonfound HLM (%)":  [round(pkonfound(m["beta"]/m["se"]), 1) for m in hlm_data[:4]],
        "SE (OLS)":           [m["se"] for m in ols_data],
        "t (OLS)":            [round(m["beta"]/m["se"], 1) for m in ols_data],
        "pkonfound OLS (%)":  [round(pkonfound(m["beta"]/m["se"]), 1) for m in ols_data],
        "Δ pkonfound (pp)":   [
            round(pkonfound(h["beta"]/h["se"]) - pkonfound(o["beta"]/o["se"]), 1)
            for h, o in zip(hlm_data[:4], ols_data)
        ],
    })

    # ── Tabela consolidada dos três métodos ────────────────────────────────────
    tab_comp = tabela_comparativa_metodologias(tab_hlm, tab_ev, tab_oster)

    # ── Salvar ─────────────────────────────────────────────────────────────────
    tab_hlm.to_csv(OUT_TAB / "konfound_hlm.csv", index=False)
    tab_ev.to_csv(OUT_TAB / "evalues_glmm.csv", index=False)
    tab_hlm_vs_ols.to_csv(OUT_TAB / "konfound_hlm_vs_ols.csv", index=False)
    tab_comp.to_csv(OUT_TAB / "sensibilidade_comparativa.csv", index=False)

    # LaTeX — tabela HLM vs OLS
    (OUT_TAB / "konfound_hlm_vs_ols.tex").write_text(
        tab_hlm_vs_ols.to_latex(
            index=False, escape=False,
            caption=(
                r"Konfound (Frank et al., 2013): pkonfound para HLM e OLS por modelo. "
                r"Δ pkonfound mostra a subestimação sistemática da robustez pelo OLS "
                r"quando aplicado a dados com estrutura multinível (ICC $>$ 5\%). "
                r"PNAD Contínua 2016--2025."
            ),
            label="tab:konfound_hlm_vs_ols",
        ),
        encoding="utf-8",
    )

    # LaTeX — E-values
    tab_ev_latex = tab_ev[["Desfecho", "Modelo", "OR", "IC 95% lo", "IC 95% hi",
                             "E-value (OR)", "E-value (CI)"]].copy()
    (OUT_TAB / "evalues_glmm.tex").write_text(
        tab_ev_latex.to_latex(
            index=False, escape=False,
            caption=(
                r"E-values (VanderWeele \& Ding, 2017) para GLMM Logístico Multinível. "
                r"E-value (OR): associação mínima do confounder com raça e desfecho "
                r"para zerar o OR observado. "
                r"E-value (CI): bound conservador usando IC$_{95\%}$ superior. "
                r"PNAD Contínua 2016--2025."
            ),
            label="tab:evalues_glmm",
        ),
        encoding="utf-8",
    )

    plotar_sensibilidade_comparativa(tab_hlm, tab_ev)

    # ── Sumário ────────────────────────────────────────────────────────────────
    print("\n── SUMÁRIO: Sensibilidade a Variáveis Omitidas ──")
    print("\n[1] Konfound HLM vs OLS (antes × depois):")
    print(tab_hlm_vs_ols[["Modelo", "t (HLM)", "pkonfound HLM (%)",
                            "t (OLS)", "pkonfound OLS (%)", "Δ pkonfound (pp)"]].
          to_string(index=False))

    print("\n[2] E-values GLMM (ocp_qualif):")
    print(tab_ev[tab_ev["Desfecho"] == "ocp_qualif"][
        ["Modelo", "OR", "E-value (OR)", "E-value (CI)"]].to_string(index=False))

    return {
        "konfound_hlm":     tab_hlm,
        "konfound_ols":     tab_ols,
        "hlm_vs_ols":       tab_hlm_vs_ols,
        "evalues_glmm":     tab_ev,
        "comparativa":      tab_comp,
    }
