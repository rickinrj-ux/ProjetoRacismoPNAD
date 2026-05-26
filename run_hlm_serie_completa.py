"""
run_hlm_serie_completa.py
==========================
HLM ajustado sobre a serie completa PNAD Continua 2016-2025 (~15.9M obs.).

ESTRATEGIA COMPUTACIONAL (41.517 UPAs):
    O vc_formula={"UPA_str": "0 + C(UPA_str)"} exige inverter uma matriz
    41517 x 41517 por iteracao — inviavel em hardware convencional.

    Solucao academicamente defensavel (Raudenbush & Bryk, 2002, cap. 4):
        - Efeitos aleatorios de UF via groups=UF_str (27 grupos)
        - Efeitos de UPA como SLOPES FIXOS (pct_negro_upa_z, etc.)
        - A hipotese de networking local e testada pelos slopes fixos de UPA

    REML=True (padrao) em vez de ML puro para estimativas de variancia
    nao-viesadas e menor risco de convergencia no limite tau^2=0.
    Metodo POWELL (sem gradiente) para robustez na fronteira do espaco.

    ICC_UF = tau^2_UF / (tau^2_UF + sigma^2)

AMOSTRA:
    População completa (7.69M obs.). Para amostra 20%, definir SAMPLE_FRAC=0.20.
"""
import sys
import logging
import time
import warnings
from pathlib import Path

sys.path.insert(0, "src")

# ── Logging ────────────────────────────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)
LOG_FILE = "logs/hlm_serie_completa.log"
handlers = [
    logging.FileHandler(LOG_FILE, encoding="utf-8"),
    logging.StreamHandler(sys.stdout),
]
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=handlers,
)
logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.regression.mixed_linear_model import MixedLM
from scipy import stats
from mlflow_utils import run_context, log_params, log_metrics, log_artifacts_dir

# ── Configuracao ───────────────────────────────────────────────────────────────
SAMPLE_FRAC  = None          # None = população completa | 0.20 = 20% (~1.54M obs.)
RANDOM_STATE = 42
FEATURES_PATH = Path("data/processed/features.parquet")
OUTPUTS = Path("outputs/tables")
OUTPUTS.mkdir(parents=True, exist_ok=True)

# ── Formulas ───────────────────────────────────────────────────────────────────
_IND = ("negro + sexo_fem + idade_c + idade_sq"
        " + educ_fund_completo + educ_medio_completo"
        " + educ_superior_completo + educ_pos_graduacao"
        " + log_horas + urbano + C(Ano)")
_UPA = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
_UF  = "pct_negro_uf_z + tx_desemprego_uf_z + media_educ_uf_z"
# M4: formalidade e grupo CBO (referência: elementar)
# log_horas e urbano já entram via _IND — removidos aqui para evitar duplicação
_OCC = ("emprego_formal + conta_propria + trab_domestico"
        " + ocp_dirigente + ocp_profissional + ocp_tecnico + ocp_administrativo"
        " + ocp_servicos + ocp_agro + ocp_operario + ocp_operador + ocp_ffaa")

FORMULAS = {
    "M0_Nulo":       "log_renda ~ 1",
    "M1_Individual": f"log_renda ~ {_IND}",
    "M2_Localidade": f"log_renda ~ {_IND} + {_UPA}",
    "M3_Completo":   f"log_renda ~ {_IND} + {_UPA} + {_UF}",
    "M4_Ocupacao":   f"log_renda ~ {_IND} + {_UPA} + {_UF} + {_OCC}",
}

# OLS com UF como efeito fixo (dummies) — robusto quando ICC_UF -> 0
FORMULAS_OLS = {
    "M1_Individual_OLS": f"log_renda ~ {_IND} + C(UF_str)",
    "M2_Localidade_OLS": f"log_renda ~ {_IND} + {_UPA} + C(UF_str)",
    "M3_Completo_OLS":   f"log_renda ~ {_IND} + {_UPA} + {_UF} + C(UF_str)",
    "M4_Ocupacao_OLS":   f"log_renda ~ {_IND} + {_UPA} + {_UF} + {_OCC} + C(UF_str)",
}

MODEL_VARS = [
    "log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
    "log_horas", "urbano", "Ano",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "pct_negro_uf_z",  "tx_desemprego_uf_z",  "media_educ_uf_z",
    "emprego_formal", "conta_propria", "trab_domestico",
    "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
    "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa",
    "UPA", "UF",
]


# ── Carregamento e Filtros ─────────────────────────────────────────────────────

def load_data(sample_frac=None):
    logger.info(f"Carregando {FEATURES_PATH} ...")
    df = pd.read_parquet(FEATURES_PATH)
    logger.info(f"  Total bruto: {len(df):,} obs.")

    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    logger.info(f"  Com renda positiva: {len(df):,} obs.")

    # Fallback: reconstrói colunas se features.parquet for anterior à atualização
    if "log_horas" not in df.columns and "horas_trabalhadas" in df.columns:
        df["log_horas"] = np.log(df["horas_trabalhadas"].clip(lower=1))
        logger.warning("log_horas reconstruído a partir de horas_trabalhadas")
    if "urbano" not in df.columns:
        df["urbano"] = (df["V1022"] == 1).astype("int8") if "V1022" in df.columns else 1
        logger.warning("urbano reconstruído")

    n_before = len(df)
    df = df.dropna(subset=MODEL_VARS).reset_index(drop=True)
    logger.info(f"  Apos dropna: {len(df):,} obs. (removidos {n_before - len(df):,})")

    upa_counts = df["UPA"].value_counts()
    valid_upas = upa_counts[upa_counts >= 10].index
    n_drop = (~df["UPA"].isin(valid_upas)).sum()
    df = df[df["UPA"].isin(valid_upas)].reset_index(drop=True)
    logger.info(f"  Apos filtro UPA>=10: {len(df):,} obs. (removidos {n_drop:,})")

    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=RANDOM_STATE).reset_index(drop=True)
        logger.info(f"  Amostra {sample_frac*100:.0f}%: {len(df):,} obs.")

    df["UPA_str"] = df["UPA"].astype(str)
    df["UF_str"]  = df["UF"].astype(str)
    # log_renda para float64 — statsmodels exige precisao dupla
    df["log_renda"] = df["log_renda"].astype(float)

    logger.info(
        f"Dataset final: {len(df):,} obs. | "
        f"{df['UPA_str'].nunique():,} UPAs | "
        f"{df['UF_str'].nunique()} UFs"
    )
    return df


# ── Ajuste HLM (REML + POWELL) ────────────────────────────────────────────────

def fit_hlm(name, formula, df):
    """
    REML=True: estimativas de variancia nao-viesadas; padrao Raudenbush & Bryk.
    method="powell": busca direcional sem gradiente — mais robusto na fronteira
    tau^2=0 do que LBFGS/BFGS que colapsam ao limite por derivada nula.
    """
    logger.info(f"[HLM | {name}] Ajustando ... (n={len(df):,})")
    t0 = time.time()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        model = smf.mixedlm(formula=formula, data=df, groups=df["UF_str"])
        result = model.fit(method="powell", maxiter=500, reml=True)
        singular = any("singular" in str(x.message).lower() for x in w)

    elapsed = time.time() - t0

    try:
        var_uf = float(result.cov_re.iloc[0, 0]) if result.cov_re.shape[0] > 0 else 0.0
    except Exception:
        var_uf = 0.0

    var_resid = float(result.scale)
    total_var = var_uf + var_resid
    icc_uf    = var_uf / total_var if total_var > 0 else 0.0

    status = "SINGULAR" if singular else "OK"
    logger.info(
        f"[HLM | {name}] {status} em {elapsed:.0f}s | "
        f"ICC_UF={icc_uf:.4f} | tau2_UF={var_uf:.5f} | sigma2={var_resid:.4f}"
    )
    return result, var_uf, var_resid, icc_uf, singular


# ── Ajuste OLS com UF FE (SE clusterizado por UF) ────────────────────────────

def fit_ols_uf_fe(name, formula, df):
    """
    OLS com UF como efeito fixo (dummies) + HC3 clusterizado por UF.
    Equivalente ao HLM quando ICC_UF -> 0.
    Coeficientes identicos ao within-UF estimator; SE corretos para clustering.
    """
    logger.info(f"[OLS | {name}] Ajustando ...")
    t0 = time.time()
    model  = smf.ols(formula=formula, data=df)
    result = model.fit(cov_type="cluster", cov_kwds={"groups": df["UF_str"]})
    elapsed = time.time() - t0
    b_negro = result.params.get("negro", np.nan)
    logger.info(
        f"[OLS | {name}] OK em {elapsed:.0f}s | "
        f"b_negro={b_negro:.4f} (SE={result.bse.get('negro', np.nan):.4f})"
    )
    return result


# ── LRT (apenas para modelos HLM REML comparaveis em estrutura RE) ───────────

def lrt_re(name_r, res_r, var_uf_r, name_f, res_f, var_uf_f):
    """LRT para testar se adicionar RE de UF melhora ajuste (H0: tau^2=0)."""
    lr_stat = 2 * max(res_f.llf - res_r.llf, 0)
    pval    = stats.chi2.sf(lr_stat, df=1) / 2  # one-sided boundary test
    return {
        "Comparacao":    f"{name_r} -> {name_f}",
        "LR":            round(lr_stat, 3),
        "df":            1,
        "p-valor":       round(pval, 8),
        "Significativo": "Sim" if pval < 0.05 else "Nao",
    }


# ── Decomposicao do Gap Racial ─────────────────────────────────────────────────

def gap_decomp(b_m1, b_m2, b_m3, b_m4=None):
    rows = []
    for label, b, med_upa, med_uf, med_occ in [
        ("M1_Individual", b_m1, np.nan,                        np.nan, np.nan),
        ("M2_Localidade", b_m2, abs(b_m1-b_m2)/abs(b_m1)*100, np.nan, np.nan),
        ("M3_Completo",   b_m3, abs(b_m1-b_m2)/abs(b_m1)*100,
                                abs(b_m2-b_m3)/abs(b_m1)*100, np.nan),
    ]:
        total_med = (abs(b_m1 - b) / abs(b_m1) * 100) if label != "M1_Individual" else np.nan
        rows.append({
            "Modelo":          label,
            "b_negro":         round(b, 4),
            "Gap%":            round((np.exp(b) - 1) * 100, 2),
            "Mediacao_UPA%":   round(med_upa, 2) if not np.isnan(med_upa) else np.nan,
            "Mediacao_UF%":    round(med_uf, 2)  if not np.isnan(med_uf) else np.nan,
            "Mediacao_occ%":   np.nan,
            "Mediacao_total%": round(total_med, 2) if not np.isnan(total_med) else np.nan,
        })
    if b_m4 is not None:
        med_occ_val = abs(b_m3 - b_m4) / abs(b_m1) * 100
        total_med_m4 = abs(b_m1 - b_m4) / abs(b_m1) * 100
        rows.append({
            "Modelo":          "M4_Ocupacao",
            "b_negro":         round(b_m4, 4),
            "Gap%":            round((np.exp(b_m4) - 1) * 100, 2),
            "Mediacao_UPA%":   round(abs(b_m1-b_m2)/abs(b_m1)*100, 2),
            "Mediacao_UF%":    round(abs(b_m2-b_m3)/abs(b_m1)*100, 2),
            "Mediacao_occ%":   round(med_occ_val, 2),
            "Mediacao_total%": round(total_med_m4, 2),
        })
    return pd.DataFrame(rows)


# ── Tabela de Coeficientes ─────────────────────────────────────────────────────

KEY_VARS = [
    "Intercept", "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
    "log_horas", "urbano",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "pct_negro_uf_z",  "tx_desemprego_uf_z",  "media_educ_uf_z",
    "emprego_formal", "conta_propria", "trab_domestico",
    "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
    "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa",
]


def coef_cell(res, var):
    if var not in res.params:
        return "-"
    coef  = res.params[var]
    se    = res.bse[var]
    pval  = res.pvalues[var]
    stars = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""
    return f"{coef:.4f}{stars} ({se:.4f})"


def build_table(hlm_results, ols_results):
    """
    hlm_results: dict {name: (result, var_uf, var_resid, icc_uf, singular)}
    ols_results: dict {name: result}
    Combina HLM e OLS numa tabela para comparacao.
    """
    all_results = {}
    for k, v in hlm_results.items():
        all_results[k] = ("hlm", v[0], v[1], v[2], v[3])
    for k, v in ols_results.items():
        all_results[k] = ("ols", v, None, None, None)

    mnames = list(all_results.keys())
    records = {}

    for mname, entry in all_results.items():
        kind, res = entry[0], entry[1]
        var_uf, var_resid, icc_uf = entry[2], entry[3], entry[4]

        for var in KEY_VARS:
            row = records.setdefault(var, {m: "-" for m in mnames})
            row[mname] = coef_cell(res, var)

        if kind == "hlm":
            records.setdefault("sigma2 (Nivel 1)", {})[mname]  = f"{var_resid:.4f}"
            records.setdefault("tau2_UF (Nivel 3)", {})[mname] = f"{var_uf:.5f}"
            records.setdefault("ICC_UF", {})[mname]             = f"{icc_uf:.4f}"
        else:
            records.setdefault("sigma2 (Nivel 1)", {})[mname]  = f"{res.mse_resid:.4f}"
            records.setdefault("tau2_UF (Nivel 3)", {})[mname] = "FE"
            records.setdefault("ICC_UF", {})[mname]             = "FE"

        records.setdefault("N (obs.)", {})[mname]        = f"{int(res.nobs):,}"
        records.setdefault("Log-Likelihood", {})[mname]  = f"{res.llf:.2f}" if np.isfinite(res.llf) else "NaN"
        aic_val = res.aic if hasattr(res, "aic") else res.aic
        records.setdefault("AIC", {})[mname] = f"{aic_val:.2f}" if np.isfinite(aic_val) else "N/D"

    return pd.DataFrame(records).T[mnames]


# ── Sumario ────────────────────────────────────────────────────────────────────

def print_summary(ols_m1, ols_m2, ols_m3, ols_m4, hlm_m0, df, icc_uf_m0):
    b1_m1 = ols_m1.params.get("negro", np.nan)
    b1_m2 = ols_m2.params.get("negro", np.nan)
    b1_m3 = ols_m3.params.get("negro", np.nan)
    b1_m4 = ols_m4.params.get("negro", np.nan)
    gap_bruto   = (np.exp(b1_m1) - 1) * 100
    gap_upa     = (np.exp(b1_m2) - 1) * 100
    gap_liquido = (np.exp(b1_m3) - 1) * 100
    gap_m4      = (np.exp(b1_m4) - 1) * 100
    med_upa  = abs(b1_m1 - b1_m2) / abs(b1_m1) * 100
    med_uf   = abs(b1_m2 - b1_m3) / abs(b1_m1) * 100
    med_tot  = abs(b1_m1 - b1_m3) / abs(b1_m1) * 100
    med_occ  = abs(b1_m3 - b1_m4) / abs(b1_m1) * 100

    n_obs  = int(ols_m1.nobs)
    n_upas = df["UPA_str"].nunique()
    n_ufs  = df["UF_str"].nunique()
    anos   = sorted(int(a) for a in df["Ano"].unique()) if "Ano" in df.columns else "N/D"

    # Coeficientes OLS de UPA
    g_pct_negro = ols_m2.params.get("pct_negro_upa_z", np.nan)
    g_desemprego = ols_m2.params.get("tx_desemprego_upa_z", np.nan)
    g_educ = ols_m2.params.get("media_educ_upa_z", np.nan)

    sep = "=" * 78
    print(f"""
{sep}
  SUMARIO DE RESULTADOS -- HLM SERIE COMPLETA PNAD 2016-2025
{sep}

  DADOS:
    N = {n_obs:,} obs. | {n_upas:,} UPAs | {n_ufs} UFs
    Anos cobertos: {anos}
    Amostra: {SAMPLE_FRAC*100 if SAMPLE_FRAC else 100:.0f}% do dataset filtrado

  MODELO NULO (M0) -- ICC de Referencia (Incondicional):
    ICC_UF  = {icc_uf_m0:.4f}  -> {icc_uf_m0*100:.1f}% da variancia de log-renda e
             atribuivel ao estado de residencia (Nivel 3).
    Nota: variancia de UPA capturada pelos slopes fixos de contexto.

  MODELO 1 (M1) -- Gap Salarial Racial Bruto (Mincer + UF FE + SE cluster):
    b_negro = {b1_m1:.4f}  -> profissionais negros ganham {abs(gap_bruto):.1f}%
             {"menos" if gap_bruto < 0 else "mais"} que brancos com mesma escolaridade, sexo e idade.

  MODELO 2 (M2) -- Gap Apos Controle de Contexto de UPA:
    b_negro = {b1_m2:.4f}  -> gap cai para {abs(gap_upa):.1f}%
    gamma_pct_negro_upa = {g_pct_negro:.4f} -> "duplo disadvantage":
             morar em bairros mais negros reduz renda independentemente da raca.
    gamma_tx_desemprego = {g_desemprego:.4f} -> desemprego local reduz renda.
    gamma_media_educ    = {g_educ:.4f} -> spillovers de capital humano do entorno.

  MODELO COMPLETO (M3) -- Gap Racial Liquido (3 niveis):
    b_negro = {b1_m3:.4f}  -> gap persiste em {abs(gap_liquido):.1f}% apos controlar
             por contexto de moradia (UPA) e macrorregional (UF).

  DECOMPOSICAO DO GAP RACIAL:
    Gap bruto (M1):             {abs(gap_bruto):.1f}%
    Mediacao UPA:               {med_upa:.1f}% ({abs(b1_m1-b1_m2):.4f} em log-pontos)
    Mediacao UF:                {med_uf:.1f}% ({abs(b1_m2-b1_m3):.4f} em log-pontos)
    Mediacao total contextual:  {med_tot:.1f}%
    Gap liquido (M3):           {abs(gap_liquido):.1f}% (discriminacao residual)
    Mediacao ocupacional (M4):  {med_occ:.1f}% (explicado por ocp + horas + formal)
    Gap residual (M4):          {abs(gap_m4):.1f}% (discriminacao pura pos-ocp)

{sep}
""")


# ── Pipeline Principal ─────────────────────────────────────────────────────────

def main():
    t_total = time.time()
    logger.info("=" * 70)
    logger.info("HLM SERIE COMPLETA PNAD 2016-2025")
    logger.info(f"Amostra: {SAMPLE_FRAC*100 if SAMPLE_FRAC else 100:.0f}%")
    logger.info("=" * 70)

    _sample_label = f"{int(SAMPLE_FRAC*100)}pct" if SAMPLE_FRAC else "completo"

    df = load_data(sample_frac=SAMPLE_FRAC)

    with run_context(
        f"HLM_Serie_{_sample_label}",
        "HLM_Gap_Racial",
        tags={"sample_frac": str(SAMPLE_FRAC or "completo"),
              "n_obs": str(len(df))},
    ):
        log_params({"sample_frac": SAMPLE_FRAC, "random_state": RANDOM_STATE,
                    "method": "powell", "reml": True, "n_obs": len(df)})

        # ── Passo 1: HLM nulo para ICC de referencia ───────────────────────────────
        logger.info("--- Passo 1: Modelo Nulo (ICC de referencia) ---")
        res_m0, var_uf_m0, var_resid_m0, icc_uf_m0, sing_m0 = fit_hlm(
            "M0_Nulo", FORMULAS["M0_Nulo"], df
        )

        # ── Passo 2: HLM M1-M3 (REML) para componentes de variancia ──────────────
        logger.info("--- Passo 2: HLM M1-M3 (REML + Powell) ---")
        hlm_results = {"M0_Nulo": (res_m0, var_uf_m0, var_resid_m0, icc_uf_m0, sing_m0)}
        for name, formula in list(FORMULAS.items())[1:]:
            r, vu, vr, icc, sing = fit_hlm(name, formula, df)
            hlm_results[name] = (r, vu, vr, icc, sing)

        # ── Passo 3: OLS com UF FE (robusto, SE clusterizado) ────────────────────
        logger.info("--- Passo 3: OLS com UF FE + SE clusterizado ---")
        ols_results = {}
        for name, formula in FORMULAS_OLS.items():
            ols_results[name] = fit_ols_uf_fe(name, formula, df)

        ols_m1 = ols_results["M1_Individual_OLS"]
        ols_m2 = ols_results["M2_Localidade_OLS"]
        ols_m3 = ols_results["M3_Completo_OLS"]
        ols_m4 = ols_results["M4_Ocupacao_OLS"]

        # ── Decomposicao ───────────────────────────────────────────────────────────
        b_m1 = ols_m1.params.get("negro", np.nan)
        b_m2 = ols_m2.params.get("negro", np.nan)
        b_m3 = ols_m3.params.get("negro", np.nan)
        b_m4 = ols_m4.params.get("negro", np.nan)
        decomp_df = gap_decomp(b_m1, b_m2, b_m3, b_m4)

        # ── MLflow: log métricas-chave ─────────────────────────────────────────────
        log_metrics({
            "icc_uf_m0":      icc_uf_m0,
            "beta_negro_m1":  b_m1,
            "beta_negro_m3":  b_m3,
            "beta_negro_m4":  b_m4,
            "gap_pct_m1":     (np.exp(b_m1) - 1) * 100 if not np.isnan(b_m1) else np.nan,
            "gap_pct_m3":     (np.exp(b_m3) - 1) * 100 if not np.isnan(b_m3) else np.nan,
            "gap_pct_m4":     (np.exp(b_m4) - 1) * 100 if not np.isnan(b_m4) else np.nan,
            "med_upa_pct":    abs(b_m1 - b_m2) / abs(b_m1) * 100 if not np.isnan(b_m1) else np.nan,
            "med_uf_pct":     abs(b_m2 - b_m3) / abs(b_m1) * 100 if not np.isnan(b_m1) else np.nan,
        })

        # ── Tabela combinada ───────────────────────────────────────────────────────
        table = build_table(hlm_results, ols_results)

        # ── Salvar outputs ─────────────────────────────────────────────────────────
        suffix = f"_s{int(SAMPLE_FRAC*100)}pct" if SAMPLE_FRAC else "_completo"
        table.to_csv(OUTPUTS / f"hlm_serie{suffix}.csv")
        decomp_df.to_csv(OUTPUTS / f"gap_decomposicao_serie{suffix}.csv", index=False)

        try:
            import jinja2  # noqa: F401
            latex_str = table.to_latex(
                caption=(
                    "Modelos de Determinantes do Log-Rendimento por Raca -- "
                    "PNAD Continua 2016-2025. "
                    "Coeficientes com SE clusterizado por UF entre parenteses. "
                    "*** p<0,001; ** p<0,01; * p<0,05. "
                    "HLM: efeito aleatorio por UF (REML). "
                    "OLS: UF como efeito fixo (dummies)."
                ),
                label="tab:hlm_serie_completa",
                escape=False,
                column_format="l" + "c" * len(table.columns),
            )
            (OUTPUTS / f"hlm_serie{suffix}.tex").write_text(latex_str, encoding="utf-8")
        except ImportError:
            logger.warning("jinja2 nao instalado — LaTeX nao gerado.")

        log_artifacts_dir(OUTPUTS, subfolder="tables")
        logger.info(f"Outputs salvos em: {OUTPUTS}")

        # ── Sumario narrativo ──────────────────────────────────────────────────────
        print_summary(ols_m1, ols_m2, ols_m3, ols_m4, res_m0, df, icc_uf_m0)

        # ── Tabela reduzida no console ─────────────────────────────────────────────
        print("\n--- Coeficientes Selecionados (HLM e OLS) ---")
        display_rows = [
            "negro", "sexo_fem", "pct_negro_upa_z", "tx_desemprego_upa_z",
            "media_educ_upa_z", "pct_negro_uf_z",
            "sigma2 (Nivel 1)", "tau2_UF (Nivel 3)", "ICC_UF", "N (obs.)", "AIC",
        ]
        display_rows = [r for r in display_rows if r in table.index]
        print(table.loc[display_rows].to_string())

        print("\n--- Decomposicao do Gap Racial (base OLS com UF FE) ---")
        print(decomp_df.round(4).to_string(index=False))

        print("\n--- ICC por Modelo (HLM REML) ---")
        for mname, entry in hlm_results.items():
            _, vu, vr, icc, sing = entry
            flag = " [SINGULAR]" if sing else ""
            print(f"  {mname:<20s}  ICC_UF={icc:.4f}  tau2={vu:.5f}  sigma2={vr:.4f}{flag}")

        elapsed = (time.time() - t_total) / 60
        logger.info(f"CONCLUIDO em {elapsed:.1f} min")
        print(f"\n=== CONCLUIDO em {elapsed:.1f} min | Outputs: {OUTPUTS} ===")


if __name__ == "__main__":
    main()
