"""
validacao_cruzada.py
====================
Validação cruzada dos resultados principais por duas estratégias:

    1. Validação temporal (year-by-year):
       Estima β_negro em cada ano separadamente e verifica estabilidade
       do coeficiente ao longo do tempo. Coeficiente estável → achado robusto.
       Tendência sistemática → estrutura do gap racial mudou no período.

    2. Validação geográfica (k-fold por UF):
       Leave-one-state-out cross-validation: estima o modelo sem cada UF
       e avalia se os coeficientes mudam substantivamente → identifica UFs
       influentes (outliers geográficos) que distorcem o achado nacional.

    3. Comparação com estrutura esperada da RAIS:
       Framework para quando microdados RAIS estiverem disponíveis.
       A RAIS (empregados com carteira) é mais precisa que PNAD para
       renda formal — comparação valida o achado para trabalhadores formais.

Critérios de robustez:
    - Coeficiente negro < 0 em todos os anos → discriminação sistemática (não pontual)
    - Variação do coeficiente < 20% do valor médio → achado estável
    - Leave-one-out: nenhuma UF remove a significância → não é artefato regional

Referências:
    Angrist, J. D., & Pischke, J. S. (2009). Mostly Harmless Econometrics.
        Princeton University Press.
    Imbens, G. W., & Wooldridge, J. M. (2009). Recent developments in the
        econometrics of program evaluation. JEL, 47(1), 5-86.
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

MODEL_VARS = [
    "log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "UPA", "UF",
]
FORMULA = (
    "log_renda ~ negro + sexo_fem + idade_c + idade_sq"
    " + educ_fund_completo + educ_medio_completo"
    " + educ_superior_completo + educ_pos_graduacao"
    " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
)


# ── Carregamento ──────────────────────────────────────────────────────────────

def carregar_dados(sample_frac: Optional[float] = None) -> pd.DataFrame:
    """Carrega features com coluna de Ano para validação temporal."""
    df = pd.read_parquet(FEATURES_PATH)
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    df = df.dropna(subset=MODEL_VARS).reset_index(drop=True)

    if "UPA" in df.columns:
        cnt = df["UPA"].value_counts()
        df  = df[df["UPA"].isin(cnt[cnt >= 10].index)].reset_index(drop=True)

    df["UPA_str"] = df["UPA"].astype(str)
    df["UF_str"]  = df["UF"].astype(str)
    df["log_renda"] = df["log_renda"].astype(float)

    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)

    if "Ano" in df.columns:
        logger.info(f"Dataset: {len(df):,} obs. | Anos: {sorted(df['Ano'].unique().tolist())}")
    return df


def _ajustar_hlm_subset(df: pd.DataFrame, label: str) -> Optional[Dict]:
    """Ajusta HLM em subconjunto e retorna coeficientes-chave."""
    n_ufs = df["UF"].nunique()
    if len(df) < 500 or n_ufs < 2:
        return None
    try:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("ignore")
            model  = smf.mixedlm(FORMULA, data=df, groups=df["UF_str"])
            result = model.fit(method="powell", maxiter=400, reml=True)

        b  = result.params.get("negro", np.nan)
        se = result.bse.get("negro", np.nan)
        pv = result.pvalues.get("negro", np.nan)

        try:
            var_uf = float(result.cov_re.iloc[0, 0]) if result.cov_re.shape[0] > 0 else 0.0
        except Exception:
            var_uf = 0.0
        var_res = float(result.scale)
        icc_uf  = var_uf / (var_uf + var_res) if (var_uf + var_res) > 0 else 0.0

        return {
            "label":      label,
            "n_obs":      len(df),
            "n_ufs":      n_ufs,
            "beta_negro": b,
            "se_negro":   se,
            "pval":       pv,
            "gap_pct":    (np.exp(b) - 1) * 100,
            "icc_uf":     icc_uf,
            "aic":        result.aic,
        }
    except Exception as exc:
        logger.warning(f"{label}: falha HLM — {exc}")
        return None


# ── Validação temporal ────────────────────────────────────────────────────────

def validacao_temporal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Estima β_negro ano a ano.

    Estabilidade temporal dos coeficientes é evidência de que o achado
    não é artefato de um período específico (crise econômica, pandemia, etc.).
    Variação > 20% do coeficiente médio deve ser documentada e justificada.
    """
    if "Ano" not in df.columns:
        logger.error("Coluna 'Ano' não encontrada — validação temporal impossível.")
        return pd.DataFrame()

    anos = sorted(df["Ano"].unique())
    logger.info(f"Validação temporal: {len(anos)} anos ({anos[0]}-{anos[-1]})")

    rows = []
    for ano in anos:
        sub = df[df["Ano"] == ano].copy()
        res = _ajustar_hlm_subset(sub, str(ano))
        if res:
            res["periodo"] = ano
            rows.append(res)

    df_val = pd.DataFrame(rows)
    if not df_val.empty:
        media = df_val["beta_negro"].mean()
        cv    = df_val["beta_negro"].std() / abs(media) * 100 if media != 0 else np.nan
        logger.info(
            f"Temporal: média β_negro={media:.4f} | "
            f"CV={cv:.1f}% | "
            f"min={df_val['beta_negro'].min():.4f} | "
            f"max={df_val['beta_negro'].max():.4f}"
        )
    return df_val


# ── Leave-One-State-Out ───────────────────────────────────────────────────────

def validacao_leave_one_state_out(df: pd.DataFrame) -> pd.DataFrame:
    """
    Leave-One-State-Out: estima o modelo sem cada UF e verifica se o
    coeficiente muda substantivamente.

    UF que ao ser excluída altera β_negro em >10% é considerada influente
    e merece análise separada no TCC.
    """
    ufs = sorted(df["UF"].unique())
    logger.info(f"Leave-One-State-Out: {len(ufs)} UFs")

    # Modelo completo (referência)
    res_full = _ajustar_hlm_subset(df, "Completo")
    if res_full is None:
        logger.error("Modelo completo falhou — abortando LOSO.")
        return pd.DataFrame()

    b_full = res_full["beta_negro"]
    rows = [res_full]

    for uf in ufs:
        sub = df[df["UF"] != uf].copy()
        uf_str = str(int(uf))
        res = _ajustar_hlm_subset(sub, f"Sem UF {uf_str}")
        if res:
            res["uf_excluida"]   = int(uf)
            res["delta_beta"]    = res["beta_negro"] - b_full
            res["delta_pct"]     = abs(res["beta_negro"] - b_full) / abs(b_full) * 100
            res["influente"]     = res["delta_pct"] > 10
            rows.append(res)

    df_loso = pd.DataFrame(rows)
    n_influentes = df_loso.get("influente", pd.Series()).sum() if "influente" in df_loso.columns else 0
    logger.info(f"LOSO: {n_influentes} UFs influentes (delta > 10%)")
    return df_loso


# ── Validação amostral k-fold geográfico ─────────────────────────────────────

def validacao_kfold_geografico(df: pd.DataFrame, n_splits: int = 5) -> pd.DataFrame:
    """
    K-fold cross-validation geográfico: divide por clusters de UF.

    Avalia a generalização do modelo para regiões não vistas no treinamento.
    Métricas: RMSE e MAE de log-renda nos folds de teste.
    """
    from sklearn.model_selection import GroupKFold

    ufs   = df["UF"].values
    X_cols = [
        "negro", "sexo_fem", "idade_c", "idade_sq",
        "educ_fund_completo", "educ_medio_completo",
        "educ_superior_completo", "educ_pos_graduacao",
        "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    ]
    X_cols = [c for c in X_cols if c in df.columns]
    Y = df["log_renda"].values

    gkf  = GroupKFold(n_splits=n_splits)
    rows = []

    for fold, (train_idx, test_idx) in enumerate(gkf.split(df, groups=ufs)):
        df_train = df.iloc[train_idx].copy()
        df_test  = df.iloc[test_idx].copy()
        df_train["UF_str"] = df_train["UF"].astype(str)

        try:
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("ignore")
                model  = smf.mixedlm(FORMULA, data=df_train, groups=df_train["UF_str"])
                result = model.fit(method="powell", maxiter=300, reml=True)

            # Predição nos dados de teste
            b_neg  = result.params.get("negro", 0)
            b_fem  = result.params.get("sexo_fem", 0)
            intcpt = result.params.get("Intercept", 0)

            # Predição simplificada (parte fixa apenas)
            y_pred = (
                intcpt
                + sum(result.params.get(c, 0) * df_test[c].values
                      for c in X_cols if c in result.params)
            )
            rmse = np.sqrt(np.mean((Y[test_idx] - y_pred) ** 2))
            mae  = np.mean(np.abs(Y[test_idx] - y_pred))

            rows.append({
                "fold":       fold + 1,
                "n_train":    len(train_idx),
                "n_test":     len(test_idx),
                "ufs_train":  df_train["UF"].nunique(),
                "ufs_test":   df_test["UF"].nunique(),
                "beta_negro": b_neg,
                "rmse":       rmse,
                "mae":        mae,
            })
            logger.info(
                f"Fold {fold+1}: β_negro={b_neg:.4f} | "
                f"RMSE={rmse:.3f} | MAE={mae:.3f}"
            )
        except Exception as exc:
            logger.warning(f"Fold {fold+1}: falha — {exc}")

    return pd.DataFrame(rows)


# ── Framework RAIS ────────────────────────────────────────────────────────────

def framework_rais(rais_path: Optional[str] = None) -> None:
    """
    Framework de validação cruzada com RAIS (quando dados disponíveis).

    A RAIS cobre apenas empregados com registro formal — complementa a PNAD
    que inclui informais. Se os achados forem consistentes entre as bases,
    a discriminação salarial racial está documentada também no setor formal.

    Instrução de uso:
        1. Solicite acesso à RAIS no DATAMEC (acesso restrito via MTb).
        2. Filtre para os mesmos anos, UFs e faixa etária da PNAD.
        3. Construa variáveis equivalentes: log_renda, negro, educação, etc.
        4. Chame esta função com o path do parquet preparado.
    """
    if rais_path is None:
        logger.info(
            "Framework RAIS: dados não disponíveis. "
            "Para validação com RAIS:\n"
            "  1. Acesse: https://bi.mte.gov.br/bgcaged/login.php\n"
            "  2. Baixe microdados RAIS por UF (formato .txt fixo)\n"
            "  3. Prepare variáveis: rais_negro (raça=4), log_salário, "
            "     grau_instrução, CNAE, CBO\n"
            "  4. Salve em parquet e passe o path aqui."
        )
        return

    logger.info(f"Carregando RAIS: {rais_path}")
    df_rais = pd.read_parquet(rais_path)
    logger.info(f"  RAIS: {len(df_rais):,} vínculos formais")
    # Implementação completa pendente de dados RAIS


# ── Visualizações ─────────────────────────────────────────────────────────────

def plotar_estabilidade_temporal(df_val: pd.DataFrame) -> None:
    """Série temporal de β_negro com IC95% ano a ano."""
    if df_val.empty:
        return
    df_val = df_val.sort_values("periodo")

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(df_val["periodo"], df_val["beta_negro"],
            marker="o", color="#c0392b", linewidth=2, label="β_negro")
    ax.fill_between(
        df_val["periodo"],
        df_val["beta_negro"] - 1.96 * df_val["se_negro"],
        df_val["beta_negro"] + 1.96 * df_val["se_negro"],
        color="#c0392b", alpha=0.15, label="IC 95%",
    )
    ax.axhline(
        df_val["beta_negro"].mean(), color="gray",
        linestyle="--", linewidth=1, label="Média do período",
    )
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xlabel("Ano", fontsize=11)
    ax.set_ylabel("β_negro (log-renda)", fontsize=11)
    ax.set_title(
        "Estabilidade Temporal do Gap Salarial Racial\n"
        "HLM com RE por UF — PNAD Contínua",
        fontsize=11,
    )
    ax.legend(fontsize=9)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "validacao_temporal.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: validacao_temporal.png")


def plotar_loso(df_loso: pd.DataFrame) -> None:
    """Gráfico de sensibilidade do β_negro ao excluir cada UF."""
    if df_loso.empty or "uf_excluida" not in df_loso.columns:
        return
    df_plot = df_loso[df_loso["uf_excluida"].notna()].sort_values("delta_pct", ascending=False)

    fig, ax = plt.subplots(figsize=(9, 6))
    cores = ["#c0392b" if inf else "#3498db"
             for inf in df_plot.get("influente", pd.Series([False] * len(df_plot)))]
    ax.barh(
        df_plot["label"].str.replace("Sem ", ""), df_plot["delta_pct"],
        color=cores, edgecolor="black", linewidth=0.4,
    )
    ax.axvline(10, color="orange", linestyle="--", linewidth=1, label="Limiar influência 10%")
    ax.set_xlabel("Δβ_negro ao excluir UF (%)", fontsize=11)
    ax.set_title(
        "Sensibilidade do Gap Racial por UF Excluída\n"
        "(Leave-One-State-Out)  ·  Vermelho = influente",
        fontsize=11,
    )
    ax.legend(fontsize=9)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "validacao_loso.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: validacao_loso.png")


def plotar_kfold(df_kf: pd.DataFrame) -> None:
    """Boxplot dos β_negro e RMSE por fold."""
    if df_kf.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    axes[0].bar(df_kf["fold"], df_kf["beta_negro"],
                color="#c0392b", edgecolor="black", linewidth=0.5)
    axes[0].axhline(df_kf["beta_negro"].mean(), color="gray",
                    linestyle="--", linewidth=1, label="Média")
    axes[0].set_xlabel("Fold", fontsize=11)
    axes[0].set_ylabel("β_negro", fontsize=11)
    axes[0].set_title("β_negro por Fold Geográfico", fontsize=11)
    axes[0].legend(fontsize=9)

    axes[1].bar(df_kf["fold"], df_kf["rmse"],
                color="#8e44ad", edgecolor="black", linewidth=0.5)
    axes[1].set_xlabel("Fold", fontsize=11)
    axes[1].set_ylabel("RMSE (log-renda)", fontsize=11)
    axes[1].set_title("RMSE de Predição por Fold Geográfico", fontsize=11)

    plt.tight_layout()
    fig.savefig(OUT_FIG / "validacao_kfold.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: validacao_kfold.png")


# ── Pipeline principal ────────────────────────────────────────────────────────

def run_validacao(
    sample_frac: Optional[float] = None,
    rais_path: Optional[str] = None,
    n_kfold: int = 5,
) -> Dict:
    """
    Pipeline completo de validação cruzada.

    Args:
        sample_frac: Fração da amostra (None = dados completos).
        rais_path: Path para parquet da RAIS (opcional).
        n_kfold: Número de folds na validação geográfica.
    """
    df = carregar_dados(sample_frac=sample_frac)

    # Validação temporal
    df_temporal = validacao_temporal(df)
    if not df_temporal.empty:
        df_temporal.to_csv(OUT_TAB / "validacao_temporal.csv", index=False)
        plotar_estabilidade_temporal(df_temporal)

    # Leave-One-State-Out
    logger.info("Iniciando Leave-One-State-Out...")
    df_loso = validacao_leave_one_state_out(df)
    if not df_loso.empty:
        df_loso.to_csv(OUT_TAB / "validacao_loso.csv", index=False)
        plotar_loso(df_loso)

    # K-fold geográfico
    logger.info(f"Iniciando K-Fold geográfico (k={n_kfold})...")
    df_kfold = validacao_kfold_geografico(df, n_splits=n_kfold)
    if not df_kfold.empty:
        df_kfold.to_csv(OUT_TAB / "validacao_kfold.csv", index=False)
        plotar_kfold(df_kfold)

    # Framework RAIS
    framework_rais(rais_path=rais_path)

    # Sumário
    print("\n── SUMÁRIO: Validação Cruzada ──")
    if not df_temporal.empty:
        b_med = df_temporal["beta_negro"].mean()
        b_cv  = df_temporal["beta_negro"].std() / abs(b_med) * 100 if b_med != 0 else np.nan
        n_sig = (df_temporal["pval"] < 0.05).sum()
        print(f"\nValidação temporal ({len(df_temporal)} anos):")
        print(f"  β_negro médio = {b_med:.4f} | CV = {b_cv:.1f}%")
        print(f"  Significativo (p<0.05) em {n_sig}/{len(df_temporal)} anos")

    if not df_loso.empty and "influente" in df_loso.columns:
        n_inf = int(df_loso["influente"].sum())
        print(f"\nLOSO: {n_inf} UF(s) influente(s) (delta >10%)")

    if not df_kfold.empty:
        print(f"\nK-fold geográfico (k={n_kfold}):")
        print(f"  β_negro: média={df_kfold['beta_negro'].mean():.4f} | "
              f"DP={df_kfold['beta_negro'].std():.4f}")
        print(f"  RMSE: média={df_kfold['rmse'].mean():.3f}")

    return {
        "temporal": df_temporal,
        "loso":     df_loso,
        "kfold":    df_kfold,
    }
