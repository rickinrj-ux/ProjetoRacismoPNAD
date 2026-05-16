"""
mobilidade_intergeracional.py
==============================
Estimação de mobilidade intergeracional de renda por raça.

Estratégia com PNAD Contínua (dados transversais):
    Proxy de educação parental = nível de instrução do chefe do domicílio (V3009A)
    para moradores filhos (V2005 ∈ {4, 5, 6}) com 18-40 anos.

    Limitação reconhecida: proxy cross-sectional não capta causalidade vertical
    real. Ainda assim, segue prática estabelecida (Chetty et al., 2014;
    Bittencourt & Lemos, 2020) para países sem dados administrativos longitudinais.

Modelos:
    1. IGM-OLS: log(renda_filho) ~ educ_chefe + negro + negro×educ_chefe + controles
       → o coeficiente negro×educ_chefe testa se negros têm menor retorno
         à educação parental (menor transmissão intergeracional de vantagem).

    2. IGM-HLM: adiciona RE por UF para controlar heterogeneidade estadual
       no mercado de trabalho que afeta a mobilidade independentemente da família.

    3. Elasticidade educacional por raça: β(educ_chefe) e β(educ_chefe) + β(interação)
       quantificam a mobilidade relativa de negros vs. brancos.

Referências:
    Chetty, R. et al. (2014). Is the United States still a land of opportunity?
        American Economic Review P&P, 104(5), 141-147.
    Bittencourt, M., & Lemos, B. (2020). Mobilidade social e raça no Brasil.
        Texto para Discussão IPEA, 2576.
    Soares, F. V. (2004). O que a educação dos pais explica sobre as
        diferenças de renda. Pesquisa e Planejamento Econômico, 34(1).
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
import pyarrow.dataset as ds
import statsmodels.formula.api as smf

logger = logging.getLogger(__name__)

ROOT           = Path(__file__).parent.parent
DATA_PROCESSED = ROOT / "data" / "processed"
OUT_FIG        = ROOT / "outputs" / "figures"
OUT_TAB        = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)

# V2005: posição no domicílio — filhos/enteados elegíveis para o proxy parental
FILHO_CODES  = {4, 5, 6}   # 4=filho do chefe+cônjuge, 5=filho só do chefe, 6=enteado
CHEFE_CODE   = 1            # 1=pessoa responsável (proxy "pai/mãe")

# V2010: codigos de raça (replicados de feature_engineering.py)
RACE_NEGRO  = {2, 4}
RACE_BRANCO = {1}

# Faixa etária dos "filhos" analisados
IDADE_MIN, IDADE_MAX = 18, 40

# Ordinal de instrução (replicado de feature_engineering.py)
EDUC_ORDINAL = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7}


# ── Construção do dataset geracional ─────────────────────────────────────────

def _ler_raw_anos(anos: Optional[List[int]] = None) -> pd.DataFrame:
    """Lê os parquets processados (dados brutos com todas as variáveis PNAD)."""
    if anos:
        paths = [
            str(DATA_PROCESSED / f"ano={y}" / f"trimestre={q}" / "data.parquet")
            for y in anos for q in range(1, 5)
            if (DATA_PROCESSED / f"ano={y}" / f"trimestre={q}" / "data.parquet").exists()
        ]
    else:
        paths = sorted(str(p) for p in DATA_PROCESSED.glob("ano=*/trimestre=*/data.parquet"))

    if not paths:
        raise FileNotFoundError(
            f"Nenhum parquet encontrado em {DATA_PROCESSED}. "
            "Execute run_pipeline.py primeiro."
        )
    logger.info(f"Lendo {len(paths)} arquivo(s) parquet para mobilidade...")
    dataset = ds.dataset(paths, format="parquet")
    df = dataset.to_table().to_pandas()
    logger.info(f"  Total bruto: {len(df):,} registros.")
    return df


def construir_dataset_geracional(
    anos: Optional[List[int]] = None,
    sample_frac: Optional[float] = None,
) -> pd.DataFrame:
    """
    Constrói dataset vinculando filhos (18-40 anos) ao nível de instrução
    do chefe do domicílio (proxy de educação parental).

    Chave de domicílio: UPA + V1008 (identificador único na PNAD Contínua).

    Returns DataFrame com colunas:
        negro, log_renda_filho, educ_chefe_ord, educ_filho_ord,
        sexo_fem, idade, UF
    """
    df_raw = _ler_raw_anos(anos)

    # ── Variáveis necessárias ─────────────────────────────────────────────
    vars_need = ["V2005", "V2009", "V2010", "V3009A", "VD4020", "V2007", "UF", "UPA", "V1008"]
    missing   = [v for v in vars_need if v not in df_raw.columns]
    if missing:
        raise KeyError(
            f"Variáveis não encontradas nos parquets: {missing}. "
            "Verifique se TARGET_VARIABLES em data_ingestion.py inclui essas colunas."
        )

    df = df_raw[vars_need + (["Ano"] if "Ano" in df_raw.columns else [])].copy()

    # ── Converte tipos ────────────────────────────────────────────────────
    for col in ["V2005", "V2009", "V2010", "V3009A"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["VD4020"] = pd.to_numeric(df["VD4020"], errors="coerce")
    df["V2007"]  = pd.to_numeric(df["V2007"], errors="coerce")
    df["UF"]     = pd.to_numeric(df["UF"], errors="coerce")

    df["chave_dom"] = df["UPA"].astype(str) + "_" + df["V1008"].astype(str)

    # ── Subset: chefes de domicílio ───────────────────────────────────────
    chefes = (
        df[df["V2005"] == CHEFE_CODE]
        [["chave_dom", "V3009A"]]
        .rename(columns={"V3009A": "educ_chefe"})
        .dropna(subset=["educ_chefe"])
        .drop_duplicates("chave_dom")
    )
    chefes["educ_chefe_ord"] = chefes["educ_chefe"].map(EDUC_ORDINAL)

    # ── Subset: filhos/enteados na faixa etária ───────────────────────────
    mask_filho = (
        df["V2005"].isin(FILHO_CODES) &
        df["V2009"].between(IDADE_MIN, IDADE_MAX) &
        df["VD4020"].notna() & (df["VD4020"] > 0) &
        df["V2010"].notna() &
        df["V3009A"].notna()
    )
    filhos = df[mask_filho].copy()
    filhos["negro"]   = np.where(filhos["V2010"].isin(RACE_NEGRO), 1,
                        np.where(filhos["V2010"].isin(RACE_BRANCO), 0, np.nan))
    filhos            = filhos.dropna(subset=["negro"])
    filhos["log_renda_filho"] = np.log1p(filhos["VD4020"])
    filhos["educ_filho_ord"]  = filhos["V3009A"].map(EDUC_ORDINAL)
    filhos["sexo_fem"]        = (filhos["V2007"] == 2).astype(int)
    filhos["idade"]           = filhos["V2009"]
    filhos["idade_c"]         = filhos["idade"] - filhos["idade"].mean()

    # ── Merge: filho ← educ do chefe ─────────────────────────────────────
    df_ger = filhos.merge(chefes[["chave_dom", "educ_chefe_ord"]], on="chave_dom", how="inner")
    df_ger = df_ger.dropna(subset=["educ_chefe_ord", "log_renda_filho"]).reset_index(drop=True)
    df_ger["UF_str"] = df_ger["UF"].astype(str)

    logger.info(
        f"Dataset geracional: {len(df_ger):,} filhos vinculados | "
        f"negro={df_ger['negro'].mean():.2%}"
    )

    if sample_frac:
        df_ger = df_ger.sample(frac=sample_frac, random_state=42).reset_index(drop=True)

    return df_ger


# ── Modelos IGM ───────────────────────────────────────────────────────────────

def ajustar_igm_ols(df: pd.DataFrame) -> object:
    """
    OLS de mobilidade intergeracional com interação raça × educação parental.

    Interpretação do coeficiente negro×educ_chefe_ord:
        < 0 → negros têm menor retorno à educação parental → menor mobilidade
        ≈ 0 → mobilidade similar entre raças (educ. parental conta igualmente)
        > 0 → negros se beneficiam mais da educação parental (improvável no Brasil)
    """
    formula = (
        "log_renda_filho ~ educ_chefe_ord * negro"
        " + educ_filho_ord + sexo_fem + idade_c + C(UF_str)"
    )
    logger.info("Ajustando IGM-OLS (interacao raca x educ. parental)...")
    cols = ["log_renda_filho", "educ_chefe_ord", "negro",
            "educ_filho_ord", "sexo_fem", "idade_c", "UF_str"]
    df = df[cols].dropna().reset_index(drop=True)
    result = smf.ols(formula, data=df).fit(
        cov_type="cluster", cov_kwds={"groups": df["UF_str"].values}
    )
    b_educ   = result.params.get("educ_chefe_ord", np.nan)
    b_inter  = result.params.get("educ_chefe_ord:negro", np.nan)
    b_negro  = result.params.get("negro", np.nan)
    logger.info(
        f"  β_educ_parental = {b_educ:.4f} | "
        f"β_negro = {b_negro:.4f} | "
        f"β_educ×negro = {b_inter:.4f}"
    )
    return result


def ajustar_igm_hlm(df: pd.DataFrame) -> object:
    """
    HLM de mobilidade intergeracional: RE por UF controla heterogeneidade
    estadual no mercado de trabalho que afeta mobilidade independentemente
    da família (ex.: mercado de trabalho mais rígido no Norte/Nordeste).
    """
    formula = (
        "log_renda_filho ~ educ_chefe_ord + negro"
        " + educ_chefe_ord:negro"
        " + educ_filho_ord + sexo_fem + idade_c"
    )
    logger.info("Ajustando IGM-HLM (RE por UF)...")
    cols = ["log_renda_filho", "educ_chefe_ord", "negro",
            "educ_filho_ord", "sexo_fem", "idade_c", "UF_str"]
    df = df[cols].dropna().reset_index(drop=True)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        model  = smf.mixedlm(formula, data=df, groups=df["UF_str"])
        result = model.fit(method="powell", maxiter=500, reml=True)

    b_educ  = result.params.get("educ_chefe_ord", np.nan)
    b_inter = result.params.get("educ_chefe_ord:negro", np.nan)
    b_negro = result.params.get("negro", np.nan)
    logger.info(
        f"  HLM-IGM: β_educ={b_educ:.4f} | β_negro={b_negro:.4f} | "
        f"β_educ×negro={b_inter:.4f} | AIC={result.aic:.1f}"
    )
    return result


def calcular_elasticidade(result_ols, result_hlm, df: pd.DataFrame) -> pd.DataFrame:
    """
    Elasticidade educacional intergeracional por raça:

        Elasticidade_branco = β_educ_parental
        Elasticidade_negro  = β_educ_parental + β_educ×negro

    Interpretação: quanto 1 ponto a mais de educação parental (escala 0-7)
    se traduz em log-renda adicional para filhos, por raça.
    """
    rows = []
    for label, res in [("OLS-UF-FE", result_ols), ("HLM-RE-UF", result_hlm)]:
        b_educ  = res.params.get("educ_chefe_ord", np.nan)
        b_inter = res.params.get("educ_chefe_ord:negro", np.nan)
        se_educ = res.bse.get("educ_chefe_ord", np.nan)
        se_int  = res.bse.get("educ_chefe_ord:negro", np.nan)

        e_branco = b_educ
        e_negro  = b_educ + (b_inter if not np.isnan(b_inter) else 0)
        # SE pela regra delta (soma de variâncias, correlação ignorada como limite superior)
        se_negro_approx = np.sqrt(se_educ**2 + (se_int**2 if not np.isnan(se_int) else 0))

        rows.append({
            "Modelo":              label,
            "Elast_Branco":        round(e_branco, 4),
            "SE_Branco":           round(se_educ, 4),
            "Elast_Negro":         round(e_negro, 4),
            "SE_Negro_approx":     round(se_negro_approx, 4),
            "Diferenca":           round(e_branco - e_negro, 4),
            "Mobilidade_relativa": round(e_negro / e_branco, 4) if e_branco != 0 else np.nan,
        })
    return pd.DataFrame(rows)


# ── Visualizações ─────────────────────────────────────────────────────────────

def plotar_mobilidade(df: pd.DataFrame, result_ols) -> None:
    """
    Scatter de log-renda dos filhos vs. educação do chefe, por raça.
    Linhas de regressão mostram diferença na inclinação (mobilidade).
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    for (neg, cor, label) in [(0, "#3498db", "Branco"), (1, "#c0392b", "Negro")]:
        sub = df[df["negro"] == neg].sample(min(5000, (df["negro"] == neg).sum()), random_state=42)
        ax.scatter(sub["educ_chefe_ord"], sub["log_renda_filho"],
                   alpha=0.08, color=cor, s=6, rasterized=True)
        # Linha de tendência via regressão simples no subgrupo
        xs = np.linspace(0, 7, 100)
        b0 = (result_ols.params.get("Intercept", 0)
              + result_ols.params.get("negro", 0) * neg)
        b1 = (result_ols.params.get("educ_chefe_ord", 0)
              + result_ols.params.get("educ_chefe_ord:negro", 0) * neg)
        ax.plot(xs, b0 + b1 * xs, color=cor, linewidth=2, label=label)

    ax.set_xlabel("Escolaridade do chefe de domicílio (proxy parental, 0-7)", fontsize=10)
    ax.set_ylabel("Log-renda do filho(a)", fontsize=10)
    ax.set_title(
        "Mobilidade Intergeracional por Raça\n"
        "Inclinação = elasticidade educacional intergeracional",
        fontsize=11,
    )
    ax.legend(fontsize=10)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "mobilidade_scatter.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: mobilidade_scatter.png")


def plotar_elasticidade(df_elast: pd.DataFrame) -> None:
    """Gráfico comparativo de elasticidade intergeracional por raça e modelo."""
    fig, ax = plt.subplots(figsize=(7, 4))
    x   = np.arange(len(df_elast))
    w   = 0.35
    ax.bar(x - w/2, df_elast["Elast_Branco"], width=w,
           label="Branco", color="#3498db", edgecolor="black", linewidth=0.5)
    ax.bar(x + w/2, df_elast["Elast_Negro"], width=w,
           label="Negro", color="#c0392b", edgecolor="black", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(df_elast["Modelo"], fontsize=10)
    ax.set_ylabel("Elasticidade educacional intergeracional", fontsize=10)
    ax.set_title(
        "Retorno da Educação Parental no Rendimento dos Filhos\n"
        "por Raça — Mobilidade Intergeracional",
        fontsize=11,
    )
    ax.legend(fontsize=10)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "mobilidade_elasticidade.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: mobilidade_elasticidade.png")


# ── Pipeline principal ────────────────────────────────────────────────────────

def run_mobilidade(
    anos: Optional[List[int]] = None,
    sample_frac: Optional[float] = None,
) -> Dict:
    """
    Pipeline de mobilidade intergeracional.

    Args:
        anos: Lista de anos PNAD a incluir. None = todos disponíveis.
        sample_frac: Fração da amostra para desenvolvimento.

    Returns:
        dict com modelos IGM, elasticidades e dataset geracional.
    """
    df_ger = construir_dataset_geracional(anos=anos, sample_frac=sample_frac)

    result_ols = ajustar_igm_ols(df_ger)
    result_hlm = ajustar_igm_hlm(df_ger)
    df_elast   = calcular_elasticidade(result_ols, result_hlm, df_ger)

    # Outputs
    df_elast.to_csv(OUT_TAB / "mobilidade_elasticidade.csv", index=False)
    plotar_mobilidade(df_ger, result_ols)
    plotar_elasticidade(df_elast)

    # Sumário
    print("\n── SUMÁRIO: Mobilidade Intergeracional ──")
    print(f"Filhos vinculados: {len(df_ger):,} | % negro: {df_ger['negro'].mean():.1%}")
    print("\nElasticidade educacional intergeracional por raça:")
    print(df_elast.to_string(index=False))

    b_inter = result_hlm.params.get("educ_chefe_ord:negro", np.nan)
    direcao = "menor" if b_inter < 0 else "maior ou igual"
    print(f"\nNegros têm mobilidade {direcao} que brancos (β_interação = {b_inter:.4f}).")

    return {
        "dataset":    df_ger,
        "result_ols": result_ols,
        "result_hlm": result_hlm,
        "elasticidade": df_elast,
    }
