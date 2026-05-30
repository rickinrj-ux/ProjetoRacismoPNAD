"""
run_vif_multicolinearidade.py
==============================
Calcula VIF (Variance Inflation Factor) para os preditores do modelo M4 do HLM,
investigando a multicolinearidade entre grupos CBO e formalidade de vínculo.

MOTIVAÇÃO:
    CBO groups e emprego_formal são potencialmente colineares:
    ocupações qualificadas (ocp_profissional, ocp_dirigente) tendem
    ao emprego formal; domésticas/conta_propria tendem ao informal.
    VIF > 10 indica colinearidade problemática.

METODOLOGIA:
    statsmodels.stats.outliers_influence.variance_inflation_factor
    sobre subsample estratificado de 200k observações (M4 sample).
"""
import sys
import logging
import warnings
from pathlib import Path

sys.path.insert(0, "src")
warnings.filterwarnings("ignore")

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/vif.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant

FEATURES_PATH = Path("data/processed/features.parquet")
OUTPUTS_TB    = Path("outputs/tables")
OUTPUTS_FIG   = Path("outputs/figures")
OUTPUTS_TB.mkdir(parents=True, exist_ok=True)

# Preditores do modelo M4 (individual + UPA + ocupacional)
M4_PREDICTORS = [
    # Individuais
    "negro", "sexo_fem", "log_horas", "urbano",
    "educ_fund_completo", "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
    # Contexto UPA
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    # Vínculo empregatício
    "emprego_formal", "conta_propria", "trab_domestico",
    # Grupos CBO
    "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
    "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa",
]

LABEL_MAP = {
    "negro": "Raça (negro)",
    "sexo_fem": "Gênero (feminino)",
    "log_horas": "Log horas trabalhadas",
    "urbano": "Área urbana",
    "educ_fund_completo": "Educ.: Fundamental",
    "educ_medio_completo": "Educ.: Médio",
    "educ_superior_completo": "Educ.: Superior",
    "educ_pos_graduacao": "Educ.: Pós-graduação",
    "pct_negro_upa_z": "% Negro na UPA (z)",
    "tx_desemprego_upa_z": "Desemprego UPA (z)",
    "media_educ_upa_z": "Educ. média UPA (z)",
    "emprego_formal": "Emprego formal (carteira)",
    "conta_propria": "Conta-própria",
    "trab_domestico": "Trabalho doméstico",
    "ocp_dirigente": "CBO: Dirigentes",
    "ocp_profissional": "CBO: Profissionais",
    "ocp_tecnico": "CBO: Técnicos",
    "ocp_administrativo": "CBO: Administrativo",
    "ocp_servicos": "CBO: Serviços/Vendas",
    "ocp_agro": "CBO: Agropecuária",
    "ocp_operario": "CBO: Operários",
    "ocp_operador": "CBO: Op. Máquinas",
    "ocp_ffaa": "CBO: FFAA/Polícia",
}

SUBSAMPLE_N = 200_000


def load_sample():
    logger.info(f"Carregando subsample N={SUBSAMPLE_N:,} para VIF ...")
    cols = M4_PREDICTORS + ["pea", "renda_bruta"]
    df = pd.read_parquet(FEATURES_PATH, columns=cols)
    df = df[(df["pea"] == 1) & (df["renda_bruta"] > 0)].dropna(subset=M4_PREDICTORS)
    df_sample = df.sample(n=min(SUBSAMPLE_N, len(df)), random_state=42)
    logger.info(f"  Sample: {len(df_sample):,} obs. com {len(M4_PREDICTORS)} preditores")
    return df_sample


def compute_vif(df_sample):
    logger.info("Calculando VIF ...")
    X = df_sample[M4_PREDICTORS].astype(float)
    X_const = add_constant(X, has_constant="add")

    vif_values = []
    for i, col in enumerate(X.columns):
        vif = variance_inflation_factor(X_const.values, i + 1)
        vif_values.append({"predictor": col, "label": LABEL_MAP.get(col, col), "VIF": round(vif, 2)})

    df_vif = pd.DataFrame(vif_values).sort_values("VIF", ascending=False).reset_index(drop=True)

    # Classificação
    df_vif["nivel"] = pd.cut(
        df_vif["VIF"],
        bins=[0, 2, 5, 10, float("inf")],
        labels=["Baixo (<2)", "Moderado (2–5)", "Alto (5–10)", "Crítico (>10)"]
    )

    df_vif.to_csv(OUTPUTS_TB / "vif_m4_preditores.csv", index=False, encoding="utf-8")
    logger.info("  vif_m4_preditores.csv salvo.")
    return df_vif


def plot_vif(df_vif):
    logger.info("Gerando figura VIF ...")
    fig, ax = plt.subplots(figsize=(10, 8))

    colors = {"Baixo (<2)": "#2ECC71", "Moderado (2–5)": "#F39C12",
              "Alto (5–10)": "#E74C3C", "Crítico (>10)": "#8B0000"}
    bar_colors = [colors.get(str(n), "#888") for n in df_vif["nivel"]]

    bars = ax.barh(df_vif["label"], df_vif["VIF"], color=bar_colors, alpha=0.85, edgecolor="white")
    ax.axvline(x=5,  color="#F39C12", linestyle="--", linewidth=1.2, label="Limiar moderado (5)")
    ax.axvline(x=10, color="#E74C3C", linestyle="--", linewidth=1.2, label="Limiar crítico (10)")

    for bar, vif_val in zip(bars, df_vif["VIF"]):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                f"{vif_val:.1f}", va="center", ha="left", fontsize=8)

    from matplotlib.patches import Patch
    legend_els = [Patch(facecolor=c, label=l) for l, c in colors.items()] + [
        plt.Line2D([0], [0], color="#F39C12", linestyle="--", label="Limiar moderado (5)"),
        plt.Line2D([0], [0], color="#E74C3C", linestyle="--", label="Limiar crítico (10)"),
    ]
    ax.legend(handles=legend_els, loc="lower right", fontsize=8)

    ax.set_xlabel("VIF (Variance Inflation Factor)", fontsize=10)
    ax.set_title("VIF dos Preditores — Modelo M4 (HLM)\nMulticolinearidade: CBO × Formalidade × Educação",
                 fontsize=11, pad=12)
    ax.invert_yaxis()
    plt.tight_layout()
    plt.savefig(OUTPUTS_FIG / "vif_m4_preditores.png", dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("  vif_m4_preditores.png salvo.")


def print_summary(df_vif):
    logger.info("\n=== RESUMO VIF ===")
    for _, row in df_vif.iterrows():
        flag = " ⚠" if row["VIF"] > 5 else ("  ✓" if row["VIF"] < 2 else "  ~")
        logger.info(f"  {row['label']:<35s}  VIF={row['VIF']:6.2f}  [{row['nivel']}]{flag}")
    critico = df_vif[df_vif["VIF"] > 10]
    alto    = df_vif[(df_vif["VIF"] > 5) & (df_vif["VIF"] <= 10)]
    logger.info(f"\n  Crítico (>10): {len(critico)} variáveis")
    logger.info(f"  Alto (5–10):   {len(alto)} variáveis")


def main():
    logger.info("=" * 60)
    logger.info("  VIF — Multicolinearidade Modelo M4")
    logger.info("=" * 60)
    df_sample = load_sample()
    df_vif    = compute_vif(df_sample)
    print_summary(df_vif)
    plot_vif(df_vif)
    logger.info("VIF concluído.")
    return df_vif


if __name__ == "__main__":
    main()
