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

ERROS-PADRAO (Angrist & Pischke, cap. 8 — Moulton):
    Regressores que variam no nivel do grupo (contexto de UPA, dummies de UF)
    tem SE subestimado se as observacoes da mesma UPA forem tratadas como
    independentes. Para os modelos OLS-FE (mesmos coeficientes do HLM quando
    ICC_UF -> 0) reportam-se tres SEs a partir de um unico ajuste:
        - convencional (referencia);
        - cluster por UPA (41.517 clusters; SE principal do relatorio);
        - cluster por UF (27 clusters < 42: inferencia com t de G-1 g.l.,
          df_correction — Cameron, Gelbach & Miller, 2008).
    Saida: hlm_serie<sufixo>_se.csv (formato longo: variavel x modelo x tipo de SE).
    Os z-scores de UF (_UF) sao colineares com C(UF_str) e ficam FORA dos OLS-FE.

ROBUSTEZ COM PESO AMOSTRAL (V1028):
    M3 reestimado por WLS com o peso da PNAD e SE cluster-UPA
    (hlm_serie<sufixo>_ponderado.csv). Os demais modelos sao nao ponderados
    (regressao amostral), o que o texto deve declarar.

AMOSTRA:
    População completa (7.69M obs.). Para amostra 20%, definir SAMPLE_FRAC=0.20.
"""

# --- bootstrap raiz do projeto (reorg estrutura) ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys
import logging
import time
import warnings
from pathlib import Path

sys.path.insert(0, "src")

# ── Logging ────────────────────────────────────────────────────────────────────
Path("outputs/_logs").mkdir(exist_ok=True)
LOG_FILE = "outputs/_logs/hlm_serie_completa.log"
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
        " + educ_superior_completo + educ_pos_graduacao + educ_missing"
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

# OLS com UF como efeito fixo (dummies) — robusto quando ICC_UF -> 0.
# Os z-scores de UF (_UF) NAO entram: sao combinacao linear exata das dummies
# C(UF_str) (colinearidade perfeita -> intercepto ~5e7 na rodada anterior).
# M3_OLS = M2_OLS + efeitos fixos de UF ja absorvendo o contexto estadual.
FORMULAS_OLS = {
    "M1_Individual_OLS": f"log_renda ~ {_IND} + C(UF_str)",
    "M2_Localidade_OLS": f"log_renda ~ {_IND} + {_UPA} + C(UF_str)",
    "M3_Completo_OLS":   f"log_renda ~ {_IND} + {_UPA} + C(UF_str)",
    "M4_Ocupacao_OLS":   f"log_renda ~ {_IND} + {_UPA} + {_OCC} + C(UF_str)",
}

# Peso amostral da PNAD Continua (pessoa, com pos-estratificacao)
PESO_COL = "V1028"

MODEL_VARS = [
    "log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao", "educ_missing",
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

    # educ_missing: indicador de escolaridade nao registrada (educ_cat ausente em ~69%).
    # Sem este flag, os dummies de educacao (NA->0) contaminam a categoria-base e
    # invertem os sinais; com ele, a base = "ensino fundamental incompleto/sem instrucao
    # COM dado", e o grupo sem registro fica isolado num termo proprio.
    df["educ_missing"] = df["educ_cat"].isna().astype("int8") if "educ_cat" in df.columns else 0

    # Fallback: reconstrói colunas se features.parquet for anterior à atualização
    if "log_horas" not in df.columns and "horas_trabalhadas" in df.columns:
        df["log_horas"] = np.log(df["horas_trabalhadas"].clip(lower=1))
        logger.warning("log_horas reconstruído a partir de horas_trabalhadas")
    if "urbano" not in df.columns:
        df["urbano"] = (df["V1022"] == 1).astype("int8") if "V1022" in df.columns else 1
        logger.warning("urbano reconstruído")

    # Peso amostral (robustez ponderada); ausente -> 1 (nao ponderado) com aviso
    if PESO_COL in df.columns:
        df[PESO_COL] = pd.to_numeric(df[PESO_COL], errors="coerce")
        n_na_peso = int(df[PESO_COL].isna().sum())
        if n_na_peso:
            logger.warning(f"{PESO_COL} ausente em {n_na_peso:,} obs. — preenchido com a mediana")
            df[PESO_COL] = df[PESO_COL].fillna(df[PESO_COL].median())
    else:
        logger.warning(f"{PESO_COL} nao existe em features.parquet — WLS ponderado sera pulado")

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
    # Guarda só o que a tabela usa; o MixedLMResults retém a matriz de desenho
    # (7,7 M x k) e, com 5 modelos vivos, esgota a RAM antes do WLS.
    light = _light_result(result)
    del result, model
    return light, var_uf, var_resid, icc_uf, singular


class _Res:
    """Resultado leve (params/bse/pvalues por nome + escalares) — interface mínima
    usada por coef_cell/build_table/print_summary/lrt_re."""
    pass


def _light_result(res, bse=None, pvalues=None):
    names = list(res.params.index) if hasattr(res.params, "index") else list(res.model.exog_names)
    r = _Res()
    r.params    = pd.Series(np.asarray(res.params), index=names)
    r.bse       = pd.Series(np.asarray(bse if bse is not None else res.bse), index=names)
    r.pvalues   = pd.Series(np.asarray(pvalues if pvalues is not None else res.pvalues), index=names)
    r.nobs      = float(res.nobs)
    r.llf       = float(res.llf) if np.isfinite(getattr(res, "llf", np.nan)) else np.nan
    r.aic       = float(res.aic) if np.isfinite(getattr(res, "aic", np.nan)) else np.nan
    r.mse_resid = float(getattr(res, "mse_resid", np.nan)) if hasattr(res, "mse_resid") else np.nan
    return r


# ── Ajuste OLS com UF FE (SE convencional / cluster-UPA / cluster-UF) ─────────

def _cluster_meat(Xe, groups):
    """Σ_g s_g s_g', com s_g = Σ_{i∈g} x_i e_i  (soma por grupo via reduceat)."""
    order = np.argsort(groups, kind="stable")
    Xe_s, g_s = Xe[order], groups[order]
    starts = np.concatenate([[0], np.flatnonzero(np.diff(g_s)) + 1])
    S = np.add.reduceat(Xe_s, starts, axis=0)          # G x k
    return S.T @ S, len(starts)


def fit_ols_uf_fe(name, formula, df, weights=None):
    """
    OLS (ou WLS, se `weights`) com UF como efeito fixo (dummies), em FORMA FECHADA
    a partir de X'X e X'y — sem a SVD do statsmodels, que precisa de ~3x a matriz de
    desenho (7,7 M x k) em RAM e estourava a memória no M4/WLS.
    Equivalente ao HLM quando ICC_UF -> 0 (coeficientes identicos ao within-UF).

    Tres matrizes de covariancia:
      conv   - sigma^2 (X'X)^-1                          -> referencia (MHE-22: regra do maximo)
      cl_upa - sanduiche com blocos por UPA (G ~ 41.5k)  -> SE PRINCIPAL (Moulton, MHE-81)
      cl_uf  - sanduiche com blocos por UF (G = 27 < 42) -> p-valor com t(G-1) (MHE-82)
    Correcao de amostra finita igual a do statsmodels (use_correction=True):
      G/(G-1) * (N-1)/(N-k).  Com pesos w: X -> sqrt(w) X, y -> sqrt(w) y (WLS).
    Retorna (resultado_leve, dict_se) com coef e os tres SEs/p por variavel.
    """
    import patsy, gc
    logger.info(f"[{'WLS' if weights is not None else 'OLS'} | {name}] Ajustando ...")
    t0 = time.time()

    y, X = patsy.dmatrices(formula, df, NA_action="raise")   # DesignMatrix (ndarray)
    names = list(X.design_info.column_names)
    X = np.ascontiguousarray(X, dtype=np.float64)
    y = np.ascontiguousarray(y, dtype=np.float64).ravel()
    n, k = X.shape
    if weights is not None:
        sw = np.sqrt(np.asarray(weights, dtype=np.float64))
        X *= sw[:, None]
        y *= sw
        del sw

    XtX = X.T @ X
    Xty = X.T @ y
    XtX_inv = np.linalg.pinv(XtX)                       # pinv: tolera colinearidade residual
    beta = XtX_inv @ Xty
    e = y - X @ beta
    rss = float(e @ e)
    sigma2 = rss / (n - k)
    V_conv = sigma2 * XtX_inv
    del y

    X *= e[:, None]                                     # X <- X * e (in place; economiza 3,7 GB)
    out = {}
    for lab, gcol, use_t in (("cl_upa", "UPA_str", False), ("cl_uf", "UF_str", True)):
        g = pd.factorize(df[gcol])[0]
        meat, G = _cluster_meat(X, g)
        corr = (G / (G - 1)) * ((n - 1) / (n - k))
        V = corr * XtX_inv @ meat @ XtX_inv
        se_ = np.sqrt(np.clip(np.diag(V), 0, None))
        t = beta / se_
        p = (2 * stats.t.sf(np.abs(t), df=G - 1)) if use_t else (2 * stats.norm.sf(np.abs(t)))
        out[lab] = (se_, p)
    del X, e
    gc.collect()

    se_conv = np.sqrt(np.clip(np.diag(V_conv), 0, None))
    se = {}
    for i, v in enumerate(names):
        se[v] = {
            "coef":      float(beta[i]),
            "se_conv":   float(se_conv[i]),
            "se_cl_upa": float(out["cl_upa"][0][i]),
            "p_cl_upa":  float(out["cl_upa"][1][i]),
            "se_cl_uf":  float(out["cl_uf"][0][i]),
            "p_cl_uf_t": float(out["cl_uf"][1][i]),
        }

    llf = -0.5 * n * (np.log(2 * np.pi * rss / n) + 1)
    r = _Res()
    r.params    = pd.Series(beta, index=names)
    r.bse       = pd.Series(out["cl_upa"][0], index=names)
    r.pvalues   = pd.Series(out["cl_upa"][1], index=names)
    r.nobs      = float(n)
    r.llf       = float(llf)
    r.aic       = float(-2 * llf + 2 * k)
    r.mse_resid = float(sigma2)
    r.cov_type  = "cluster (UPA)"

    elapsed = time.time() - t0
    b = se.get("negro", {})
    logger.info(
        f"[OLS | {name}] OK em {elapsed:.0f}s | b_negro={b.get('coef', np.nan):.4f} | "
        f"SE conv={b.get('se_conv', np.nan):.4f} | cl-UPA={b.get('se_cl_upa', np.nan):.4f} | "
        f"cl-UF(t)={b.get('se_cl_uf', np.nan):.4f}"
    )
    return r, se


def se_long_table(se_por_modelo):
    """{modelo: {var: {...}}} -> DataFrame longo (modelo, variavel, coef, se_conv, ...)."""
    rows = []
    for mname, d in se_por_modelo.items():
        for var, v in d.items():
            if var.startswith("C(") and var not in KEY_VARS:
                continue                      # dummies de UF/Ano: fora da tabela longa
            rows.append({"modelo": mname, "variavel": var, **v,
                         "razao_upa_conv": v["se_cl_upa"] / v["se_conv"] if v["se_conv"] else np.nan,
                         "razao_uf_conv":  v["se_cl_uf"] / v["se_conv"] if v["se_conv"] else np.nan})
    return pd.DataFrame(rows)


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
    "educ_superior_completo", "educ_pos_graduacao", "educ_missing",
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

def print_summary(ols_m1, ols_m2, ols_m3, ols_m4, hlm_m0, df, icc_uf_m0, se3=None):
    se3 = se3 or {}
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
    SE(b_negro, M3): conv={se3.get('se_conv', float('nan')):.4f} | cluster-UPA={se3.get('se_cl_upa', float('nan')):.4f} | cluster-UF t(26)={se3.get('se_cl_uf', float('nan')):.4f}
    Moulton: ignorar a UPA subestima o SE por {se3.get('se_cl_upa', float('nan'))/max(se3.get('se_conv', float('nan')),1e-12):.1f}x.

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
        logger.info("--- Passo 3: OLS com UF FE + SE (conv / cluster-UPA / cluster-UF) ---")
        ols_results, se_por_modelo = {}, {}
        for name, formula in FORMULAS_OLS.items():
            ols_results[name], se_por_modelo[name] = fit_ols_uf_fe(name, formula, df)

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

        # Tabela longa de SEs (conv / cluster-UPA / cluster-UF) por variavel e modelo
        se_df = se_long_table(se_por_modelo)
        se_df.to_csv(OUTPUTS / f"hlm_serie{suffix}_se.csv", index=False)

        # ── Passo 3b: robustez ponderada (WLS com V1028) no M3 — DEPOIS de salvar tudo,
        #    porque o WLS duplica a matriz de desenho (exog + wexog) e pode esgotar a RAM.
        wls_m3 = None
        if PESO_COL in df.columns:
            logger.info("--- Passo 3b: M3 ponderado pelo peso amostral (WLS + cluster-UPA) ---")
            try:
                wls_m3, se_por_modelo["M3_Completo_WLS_V1028"] = fit_ols_uf_fe(
                    "M3_Completo_WLS_V1028", FORMULAS_OLS["M3_Completo_OLS"], df,
                    weights=df[PESO_COL].astype(float))
                se_long_table(se_por_modelo).to_csv(OUTPUTS / f"hlm_serie{suffix}_se.csv", index=False)
            except MemoryError:
                logger.error("WLS ponderado: MemoryError — pulado (rode isolado com mais RAM livre)")

        # Robustez ponderada: b_negro OLS vs WLS (V1028), SE cluster-UPA
        if wls_m3 is not None:
            b_ols, b_wls = se_por_modelo["M3_Completo_OLS"]["negro"], se_por_modelo["M3_Completo_WLS_V1028"]["negro"]
            pond = pd.DataFrame([
                {"Modelo": "M3_OLS (nao ponderado)", "b_negro": b_ols["coef"], "se_cl_upa": b_ols["se_cl_upa"],
                 "Gap%": (np.exp(b_ols["coef"]) - 1) * 100},
                {"Modelo": "M3_WLS (peso V1028)",   "b_negro": b_wls["coef"], "se_cl_upa": b_wls["se_cl_upa"],
                 "Gap%": (np.exp(b_wls["coef"]) - 1) * 100},
            ])
            pond["dif_pp"] = pond["Gap%"] - pond["Gap%"].iloc[0]
            pond.to_csv(OUTPUTS / f"hlm_serie{suffix}_ponderado.csv", index=False)
            log_metrics({"beta_negro_m3_wls": b_wls["coef"], "se_cl_upa_m3": b_ols["se_cl_upa"],
                         "se_cl_uf_m3": b_ols["se_cl_uf"]})

        try:
            import jinja2  # noqa: F401
            latex_str = table.to_latex(
                caption=(
                    "Modelos de Determinantes do Log-Rendimento por Raca -- "
                    "PNAD Continua 2016-2025. "
                    "Coeficientes com SE entre parenteses: HLM = SE do modelo; "
                    "OLS = SE clusterizado por UPA (ver hlm_serie_se.csv para conv./cluster-UF). "
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
        print_summary(ols_m1, ols_m2, ols_m3, ols_m4, res_m0, df, icc_uf_m0,
                      se3=se_por_modelo["M3_Completo_OLS"].get("negro"))

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
