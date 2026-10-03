"""
run_hlm_stepup.py
=================
HLM de DOIS níveis — indivíduo (nível 1) aninhado em UPA (nível 2, proxy de bairro) —
com efeitos fixos de UF, estimado pela *multilevel step-up strategy* (Raudenbush & Bryk,
2002; Fávero & Belfiore, cap. 15) sobre a população completa da PNAD Contínua 2016-2025.

Por que esta especificação (TODO_revisao, bloco 3, opção a):
  - o texto do TCC descrevia "três níveis com UPA como interceptos fixos", que não era o
    que run_hlm_serie_completa.py estimava (intercepto aleatório de UF + covariáveis de
    UPA). Aqui o nível 2 É a UPA — o nível substantivo da tese (segregação de bairro) —,
    o que permite reportar tau²_UPA, ICC_UPA e a variância entre bairros explicada pelas
    covariáveis contextuais. A UF (27 unidades) entra como efeitos fixos: absorve o
    contexto estadual sem exigir um terceiro nível com poucos grupos (MHE-82).

Degraus (todos por ML, para que os testes de razão de verossimilhança entre modelos
aninhados sejam válidos; com N = 7,7 M, REML e ML coincidem — verificado no M0):
    M0  nulo:            log_renda ~ 1 + (1 | UPA)                         -> ICC_UPA
    M1  individual:      + Mincer (negro, sexo, idade, educação, horas, urbano, ano)
    M2  contexto UPA:    + %negro, desemprego, educação média da UPA (z)   -> mediação
    M3  UF:              + C(UF)                                            -> gap líquido
    M4  ocupação:        + formalidade + grupo CBO (bad controls: limite inferior)
    M3-RS random slope:  M3 + (1 + negro | UPA)   -> LR test: a penalidade varia entre bairros?

Saídas (outputs/tables): hlm_stepup_coefs.csv (longo), hlm_stepup_fit.csv (LL/AIC/BIC/LR),
hlm_stepup_varcomp.csv, gap_decomposicao_stepup.csv, hlm_stepup_konfound.csv,
hlm_stepup.tex (tabela do relatório); outputs/figures/hlm_efeitos_uf_blup_upa.png.
Memória: cada resultado do statsmodels é reduzido a um objeto leve logo após o ajuste.
"""

# --- bootstrap raiz do projeto ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys, gc, time, logging, warnings, argparse
import pickle
from pathlib import Path
sys.path.insert(0, "src")

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
Path("outputs/_logs").mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    handlers=[logging.FileHandler("outputs/_logs/hlm_stepup.log", encoding="utf-8"),
                              logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)
from mlflow_utils import run_context, log_params, log_metrics, log_artifacts_dir
from params import fmt, fmtN

SAMPLE_FRAC = None            # None = população completa (regra do projeto: só amostrar com confirmação)
FEATURES_PATH = Path("data/processed/features.parquet")
TABLES  = Path("outputs/tables");  TABLES.mkdir(parents=True, exist_ok=True)
FIGURES = Path("outputs/figures"); FIGURES.mkdir(parents=True, exist_ok=True)

_IND = ("negro + sexo_fem + idade_c + idade_sq"
        " + educ_fund_completo + educ_medio_completo + educ_superior_completo"
        " + educ_pos_graduacao + log_horas + urbano + C(Ano)")
_UPA = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
_OCC = ("emprego_formal + conta_propria + trab_domestico"
        " + ocp_dirigente + ocp_profissional + ocp_tecnico + ocp_administrativo"
        " + ocp_servicos + ocp_agro + ocp_operario + ocp_operador + ocp_ffaa")
FORMULAS = {
    "M0": "log_renda ~ 1",
    "M1": f"log_renda ~ {_IND}",
    "M2": f"log_renda ~ {_IND} + {_UPA}",
    "M3": f"log_renda ~ {_IND} + {_UPA} + C(UF_str)",
    "M4": f"log_renda ~ {_IND} + {_UPA} + C(UF_str) + {_OCC}",
}
ROTULOS = {"M0": "M0 nulo", "M1": "M1 individual", "M2": "M2 + contexto UPA",
           "M3": "M3 + UF (efeitos fixos)", "M4": "M4 + ocupação"}
MODEL_VARS = ["log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
              "educ_fund_completo", "educ_medio_completo", "educ_superior_completo",
              "educ_pos_graduacao", "log_horas", "urbano", "Ano",
              "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
              "emprego_formal", "conta_propria", "trab_domestico",
              "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
              "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa",
              "UPA", "UF"]
KEY_VARS = ["Intercept", "negro", "sexo_fem", "idade_c", "idade_sq",
            "educ_fund_completo", "educ_medio_completo", "educ_superior_completo",
            "educ_pos_graduacao", "log_horas", "urbano",
            "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
            "emprego_formal", "conta_propria", "trab_domestico",
            "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
            "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa"]
LABELS = {
    "Intercept": "Intercepto", "negro": r"\textbf{Raça (negro)}", "sexo_fem": "Sexo feminino",
    "idade_c": "Idade (centrada)", "idade_sq": "Idade$^2$",
    "educ_fund_completo": "Educ.: fundamental completo", "educ_medio_completo": "Educ.: médio completo",
    "educ_superior_completo": "Educ.: superior completo", "educ_pos_graduacao": "Educ.: pós-graduação",
    "educ_missing": "Educ.: não registrada", "log_horas": "log(horas)", "urbano": "Urbano",
    "pct_negro_upa_z": r"\% negro na UPA ($z$)", "tx_desemprego_upa_z": "Desemprego na UPA ($z$)",
    "media_educ_upa_z": "Educ. média na UPA ($z$)",
    "emprego_formal": "Emprego formal", "conta_propria": "Conta própria", "trab_domestico": "Trab. doméstico",
    "ocp_dirigente": "CBO: dirigente", "ocp_profissional": "CBO: profissional", "ocp_tecnico": "CBO: técnico",
    "ocp_administrativo": "CBO: administrativo", "ocp_servicos": "CBO: serviços", "ocp_agro": "CBO: agropecuária",
    "ocp_operario": "CBO: operário", "ocp_operador": "CBO: operador", "ocp_ffaa": "CBO: FFAA",
}


# ── Dados ──────────────────────────────────────────────────────────────────────
def load_data(sample_frac=None):
    logger.info(f"Carregando {FEATURES_PATH} ...")
    df = pd.read_parquet(FEATURES_PATH, columns=[c for c in MODEL_VARS if c not in ("educ_missing",)]
                         + ["educ_cat"])
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    df["educ_missing"] = df["educ_cat"].isna().astype("int8")
    n0 = len(df)
    df = df.dropna(subset=[c for c in MODEL_VARS if c != "educ_missing"]).reset_index(drop=True)
    logger.info(f"  renda>0 e completos: {len(df):,} (removidos {n0-len(df):,})")
    upa_counts = df["UPA"].value_counts()
    df = df[df["UPA"].isin(upa_counts[upa_counts >= 10].index)].reset_index(drop=True)
    if sample_frac:
        # teste: amostra de UPAs inteiras (preserva a estrutura de grupos; amostrar linhas
        # deixaria ~2 obs por UPA e degeneraria tau2)
        rng = np.random.default_rng(42)
        upas = df["UPA"].unique()
        keep = rng.choice(upas, size=max(int(len(upas) * sample_frac), 50), replace=False)
        df = df[df["UPA"].isin(keep)].reset_index(drop=True)
        logger.info(f"  AMOSTRA de {sample_frac:.1%} das UPAs: {len(df):,} obs.")
    df["UPA_str"] = df["UPA"].astype(str)
    df["UF_str"] = df["UF"].astype(str)
    df["log_renda"] = df["log_renda"].astype(float)
    logger.info(f"Dataset: {len(df):,} obs | {df['UPA_str'].nunique():,} UPAs | {df['UF_str'].nunique()} UFs")
    return df


# ── Ajuste ─────────────────────────────────────────────────────────────────────
class Light:
    pass


# Cache em disco: cada degrau é ajustado num processo próprio (ver --fit), senão
# os seis modelos juntos estouram a memória em 7,7 milhões de observações.
CACHE = Path("outputs/_cache/hlm_stepup")   # o script já faz chdir para a raiz


def _cache_path(name: str) -> Path:
    return CACHE / f"{name}.pkl"


def cache_save(name: str, L: "Light") -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    with _cache_path(name).open("wb") as fh:
        pickle.dump(L, fh, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info(f"[{name}] cache gravado em {_cache_path(name)}")


def cache_load(name: str):
    p = _cache_path(name)
    if not p.exists():
        return None
    try:
        with p.open("rb") as fh:
            L = pickle.load(fh)
        logger.info(f"[{name}] reaproveitado do cache (llf={L.llf:,.0f}, conv={L.converged})")
        return L
    except Exception as e:
        logger.warning(f"[{name}] cache ilegível ({e}); será reajustado")
        return None


def fit_mixed(name, formula, df, re_formula=None, reml=False, keep_re=False):
    """MixedLM com groups=UPA. Devolve objeto leve: params/bse/pvalues (Series),
    llf, aic, bic, k_fe, n, tau2 (intercepto), tau2_slope, cov01, sigma2, icc,
    converged, e (opcional) BLUPs."""
    t0 = time.time()
    logger.info(f"[{name}] ajustando {'REML' if reml else 'ML'}"
                f"{' + random slope ' + re_formula if re_formula else ''} ...")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        model = smf.mixedlm(formula, data=df, groups=df["UPA_str"], re_formula=re_formula)
        # lbfgs (statsmodels 0.14.6 + scipy atual) para na fronteira tau2=0 com llf=inf;
        # bfgs converge no mesmo otimo que powell/cg e e ~2x mais rapido.
        try:
            res = model.fit(method="bfgs", maxiter=2000, reml=reml)
        except np.linalg.LinAlgError:
            logger.warning(f"[{name}] bfgs singular — tentando powell")
            res = model.fit(method="powell", maxiter=3000, reml=reml)
        # bfgs parava no M3 com converged=False: o efeito fixo ficava estável
        # (variação de 0,03%), mas tau2 saía 12% acima do otimo. powell, sem
        # gradiente, fecha; fica o ajuste de maior verossimilhanca.
        if not getattr(res, "converged", True):
            logger.warning(f"[{name}] bfgs nao convergiu — refazendo com powell")
            try:
                alt = model.fit(method="powell", maxiter=3000, reml=reml)
                if float(alt.llf) > float(res.llf):
                    logger.info(f"[{name}] powell melhor: llf {float(res.llf):.1f} -> "
                                f"{float(alt.llf):.1f} (converged={alt.converged})")
                    res = alt
            except Exception as e:                       # pragma: no cover
                logger.warning(f"[{name}] powell falhou ({e}); mantendo bfgs")
        msgs = [str(x.message) for x in w]
    L = Light()
    names = list(res.params.index)
    fe = [n_ for n_ in names if n_ in res.fe_params.index]
    L.params = res.fe_params.copy()
    L.bse = res.bse.loc[fe].copy()
    L.pvalues = res.pvalues.loc[fe].copy()
    L.conf = res.conf_int().loc[fe].copy()
    L.n = int(res.nobs)
    L.llf = float(res.llf)
    L.k_fe = len(fe)
    L.k_re = int(res.cov_re.shape[0] * (res.cov_re.shape[0] + 1) / 2) + 1   # var/cov + sigma2
    k = L.k_fe + L.k_re
    L.aic = -2 * L.llf + 2 * k
    L.bic = -2 * L.llf + np.log(L.n) * k
    L.sigma2 = float(res.scale)
    cov_re = np.asarray(res.cov_re)
    L.tau2 = float(cov_re[0, 0])
    L.tau2_slope = float(cov_re[1, 1]) if cov_re.shape[0] > 1 else np.nan
    L.cov01 = float(cov_re[0, 1]) if cov_re.shape[0] > 1 else np.nan
    L.icc = L.tau2 / (L.tau2 + L.sigma2)
    L.converged = bool(res.converged)
    L.warnings = "; ".join(m for m in msgs if "singular" in m.lower() or "boundary" in m.lower())[:200]
    if keep_re:
        L.blups = pd.Series({g: float(v.iloc[0]) for g, v in res.random_effects.items()})
    del res, model
    gc.collect()
    logger.info(f"[{name}] OK em {time.time()-t0:.0f}s | b_negro={L.params.get('negro', np.nan):.4f} "
                f"(SE {L.bse.get('negro', np.nan):.4f}) | tau2_UPA={L.tau2:.4f} | sigma2={L.sigma2:.4f} "
                f"| ICC={L.icc:.4f} | llf={L.llf:,.0f} | conv={L.converged} {L.warnings}")
    return L


def lr_test(r0, r1, df_):
    lr = 2 * (r1.llf - r0.llf)
    return lr, stats.chi2.sf(lr, df_)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=float, default=SAMPLE_FRAC, help="só para teste; padrão = população")
    ap.add_argument("--replot", action="store_true", help="só refaz a figura a partir dos csv")
    ap.add_argument("--fit", default="", metavar="MODELO",
                    help="ajusta só esse degrau (M0, M0_REML, M1..M4, M3_RS), grava no cache e sai")
    ap.add_argument("--force", action="store_true", help="ignora o cache e reajusta tudo")
    args = ap.parse_args()
    if args.replot:
        replot(); return
    t_total = time.time()

    # modo "um modelo por processo": ajusta, grava no cache e sai
    if args.fit:
        nome = args.fit
        df = load_data(args.sample)
        kw = {}
        if nome == "M0_REML":
            L = fit_mixed(nome, FORMULAS["M0"], df, reml=True)
        elif nome == "M3_RS":
            L = fit_mixed(nome, FORMULAS["M3"], df, re_formula="~negro")
        else:
            L = fit_mixed(nome, FORMULAS[nome], df, keep_re=(nome == "M3"))
        cache_save(nome, L)
        logger.info(f"[{nome}] CONCLUIDO em {(time.time()-t_total)/60:.1f} min")
        return

    df = load_data(args.sample)
    n_upa, n_uf = df["UPA_str"].nunique(), df["UF_str"].nunique()

    with run_context("HLM_StepUp_UPA", "HLM_Gap_Racial", tags={"n_obs": str(len(df))}):
        log_params({"sample_frac": args.sample, "groups": "UPA", "method": "bfgs", "ml": True})
        R = {}

        def _obter(nome, *a, **kw):
            """Usa o cache do processo dedicado quando existir (ver --fit)."""
            if not args.force:
                L = cache_load(nome)
                if L is not None:
                    return L
            L = fit_mixed(nome, *a, **kw)
            cache_save(nome, L)
            return L

        R["M0"] = _obter("M0", FORMULAS["M0"], df)
        R["M0_REML"] = _obter("M0_REML", FORMULAS["M0"], df, reml=True)
        for m in ("M1", "M2", "M3", "M4"):
            R[m] = _obter(m, FORMULAS[m], df, keep_re=(m == "M3"))
        R["M3_RS"] = _obter("M3_RS", FORMULAS["M3"], df, re_formula="~negro")

        # ── Ajuste e LR tests ──
        fit_rows, seq = [], ["M0", "M1", "M2", "M3", "M4"]
        for i, m in enumerate(seq):
            r = R[m]
            row = {"modelo": m, "rotulo": ROTULOS[m], "n": r.n, "k_fe": r.k_fe, "k_re": r.k_re,
                   "llf": r.llf, "deviance": -2 * r.llf, "aic": r.aic, "bic": r.bic,
                   "tau2_upa": r.tau2, "sigma2": r.sigma2, "icc_upa": r.icc, "converged": r.converged}
            if i > 0:
                prev = R[seq[i - 1]]
                lr, p = lr_test(prev, r, r.k_fe - prev.k_fe)
                row.update({"lr_vs_anterior": lr, "df_lr": r.k_fe - prev.k_fe, "p_lr": p})
                # variância entre UPAs explicada pelo degrau (Raudenbush & Bryk: pseudo-R2 nível 2)
                row["pct_tau2_explicada_vs_M0"] = (R["M0"].tau2 - r.tau2) / R["M0"].tau2 * 100
                row["pct_sigma2_explicada_vs_M0"] = (R["M0"].sigma2 - r.sigma2) / R["M0"].sigma2 * 100
            fit_rows.append(row)
        rs = R["M3_RS"]
        lr_rs, p_rs = lr_test(R["M3"], rs, 2)
        fit_rows.append({"modelo": "M3_RS", "rotulo": "M3 + inclinação aleatória de negro por UPA",
                         "n": rs.n, "k_fe": rs.k_fe, "k_re": rs.k_re, "llf": rs.llf, "deviance": -2 * rs.llf,
                         "aic": rs.aic, "bic": rs.bic, "tau2_upa": rs.tau2, "sigma2": rs.sigma2,
                         "icc_upa": rs.icc, "converged": rs.converged,
                         "lr_vs_anterior": lr_rs, "df_lr": 2, "p_lr": p_rs,
                         "tau2_slope_negro": rs.tau2_slope, "cov_int_slope": rs.cov01,
                         "sd_slope_negro": np.sqrt(max(rs.tau2_slope, 0))})
        fit_df = pd.DataFrame(fit_rows)
        fit_df.to_csv(TABLES / "hlm_stepup_fit.csv", index=False)

        # REML vs ML no M0 (declaração no texto)
        pd.DataFrame([{"componente": "tau2_upa", "ML": R["M0"].tau2, "REML": R["M0_REML"].tau2},
                      {"componente": "sigma2", "ML": R["M0"].sigma2, "REML": R["M0_REML"].sigma2},
                      {"componente": "icc_upa", "ML": R["M0"].icc, "REML": R["M0_REML"].icc}]
                     ).to_csv(TABLES / "hlm_stepup_varcomp.csv", index=False)

        # ── Coeficientes (longo) ──
        rows = []
        for m in seq + ["M3_RS"]:
            r = R[m]
            for v in r.params.index:
                if v.startswith("C(") and v not in KEY_VARS:
                    continue
                rows.append({"modelo": m, "variavel": v, "coef": r.params[v], "se": r.bse[v],
                             "p": r.pvalues[v], "ci_lo": r.conf.loc[v, 0], "ci_hi": r.conf.loc[v, 1]})
        coef_df = pd.DataFrame(rows)
        coef_df.to_csv(TABLES / "hlm_stepup_coefs.csv", index=False)

        # ── Decomposição do gap ──
        b = {m: R[m].params.get("negro", np.nan) for m in seq[1:]}
        gap_rows = []
        for m in seq[1:]:
            gap_rows.append({"Modelo": m, "rotulo": ROTULOS[m], "b_negro": b[m], "se": R[m].bse["negro"],
                             "ci_lo": R[m].conf.loc["negro", 0], "ci_hi": R[m].conf.loc["negro", 1],
                             "Gap%": (np.exp(b[m]) - 1) * 100,
                             "Mediacao_acum%": (abs(b["M1"]) - abs(b[m])) / abs(b["M1"]) * 100})
        gap_df = pd.DataFrame(gap_rows)
        gap_df.to_csv(TABLES / "gap_decomposicao_stepup.csv", index=False)

        # ── Konfound (Frank et al., 2013) com o SE do modelo (UPA aleatório) ──
        kf = []
        for m in seq[1:]:
            t = R[m].params["negro"] / R[m].bse["negro"]
            dfres = R[m].n - R[m].k_fe
            t_crit = stats.t.ppf(0.975, dfres)
            r_xy = t / np.sqrt(t ** 2 + dfres)
            r_crit = t_crit / np.sqrt(t_crit ** 2 + dfres)
            kf.append({"modelo": m, "b_negro": R[m].params["negro"], "se": R[m].bse["negro"], "t": t,
                       "pct_vies_para_invalidar": (1 - t_crit / abs(t)) * 100,
                       "r_parcial": r_xy, "itcv": abs(r_xy) - r_crit})
        pd.DataFrame(kf).to_csv(TABLES / "hlm_stepup_konfound.csv", index=False)

        log_metrics({"icc_upa_m0": R["M0"].icc, "beta_negro_m1": b["M1"], "beta_negro_m3": b["M3"],
                     "beta_negro_m4": b["M4"], "lr_rs": lr_rs, "tau2_slope_negro": rs.tau2_slope})

        # ── Figura: efeitos fixos de UF (M3) + distribuição dos BLUPs de UPA ──
        uf_rows = [(v.split("[T.")[1].rstrip("]"), R["M3"].params[v], R["M3"].conf.loc[v, 0], R["M3"].conf.loc[v, 1])
                   for v in R["M3"].params.index if v.startswith("C(UF_str)[T.")]
        uf_df = pd.DataFrame(uf_rows, columns=["UF", "coef", "lo", "hi"]).sort_values("coef")
        uf_df.to_csv(TABLES / "hlm_stepup_efeitos_uf.csv", index=False)
        blups = R["M3"].blups
        pd.DataFrame({"UPA": blups.index, "u0j": blups.values}).to_csv(TABLES / "hlm_stepup_blups_upa.csv", index=False)

        plot_figura(uf_df, blups, R["M3"].tau2)

        # ── Tabela LaTeX ──
        write_tex(R, seq, fit_df, gap_df, n_upa, n_uf, lr_rs, p_rs)
        log_artifacts_dir(TABLES, subfolder="tables")
        logger.info(f"CONCLUIDO em {(time.time()-t_total)/60:.1f} min")


UF_NOMES = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
            "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA",
            "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS",
            "50": "MS", "51": "MT", "52": "GO", "53": "DF"}


def plot_figura(uf_df, blups, tau2, ref_uf="11"):
    """Efeitos fixos de UF (M3, IC 95%) + distribuição dos BLUPs de UPA. Cinza + 1 cor."""
    uf_df = uf_df.copy()
    uf_df["UF"] = uf_df["UF"].astype(str).map(lambda c: UF_NOMES.get(c, c))
    uf_df = uf_df.sort_values("coef")
    sd = float(np.sqrt(tau2))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.4), gridspec_kw={"width_ratios": [1.1, 1]})
    ax1.errorbar(uf_df["coef"], range(len(uf_df)),
                 xerr=[uf_df["coef"] - uf_df["lo"], uf_df["hi"] - uf_df["coef"]],
                 fmt="o", color="#616161", ecolor="#BDBDBD", ms=4, capsize=2)
    ax1.set_yticks(range(len(uf_df))); ax1.set_yticklabels(uf_df["UF"], fontsize=8)
    ax1.axvline(0, color="#212121", lw=0.8)
    ax1.set_xlabel(f"Efeito fixo da UF no log-rendimento (M3), IC 95% — referência: {UF_NOMES.get(ref_uf, ref_uf)}")
    ax1.set_title("Estados: 26 efeitos fixos", fontsize=10, color="#424242")
    ax2.hist(blups.values, bins=60, color="#9E9E9E", edgecolor="white")
    ax2.axvline(0, color="#212121", lw=0.8)
    ax2.axvspan(-1.96 * sd, 1.96 * sd, color="#1565C0", alpha=0.08)
    ax2.set_xlabel(r"BLUP do intercepto da UPA ($u_{0j}$), M3 — faixa azul: $\pm1{,}96$ DP")
    ax2.set_title(f"Bairros: {len(blups):,} interceptos aleatórios — DP = {sd:.3f} "
                  f"(≈ ±{(np.exp(1.96 * sd) - 1) * 100:.0f}% de renda)".replace(",", "."),
                  fontsize=10, color="#424242")
    for ax in (ax1, ax2):
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.suptitle("Onde se mora importa: a variação entre bairros supera a variação entre estados",
                 fontsize=12, fontweight="bold", color="#212121")
    plt.tight_layout()
    plt.savefig(FIGURES / "hlm_efeitos_uf_blup_upa.png", dpi=150, bbox_inches="tight")
    plt.close()


def replot():
    """Refaz só a figura a partir dos csv salvos (sem reestimar)."""
    uf_df = pd.read_csv(TABLES / "hlm_stepup_efeitos_uf.csv", dtype={"UF": str})
    blups = pd.read_csv(TABLES / "hlm_stepup_blups_upa.csv")["u0j"]
    fit = pd.read_csv(TABLES / "hlm_stepup_fit.csv").set_index("modelo")
    plot_figura(uf_df, blups, float(fit.loc["M3", "tau2_upa"]))
    logger.info("Figura refeita: outputs/figures/hlm_efeitos_uf_blup_upa.png")


def write_tex(R, seq, fit_df, gap_df, n_upa, n_uf, lr_rs, p_rs):
    def cell(r, v):
        if v not in r.params.index:
            return "---"
        c, s = r.params[v], r.bse[v]
        s_txt = f"{s:.4f}" if s >= 0.00005 else f"{s:.1e}"
        return f"{fmt(c, 4)} ({s_txt.replace('.', ',')})"
    cols = seq
    L = []
    L.append(r"\begin{table}[htbp]")
    L.append(r"\centering")
    L.append(r"\caption{HLM de dois níveis (indivíduo em UPA) com efeitos fixos de UF --- estratégia "
             r"\emph{step-up}, PNAD Contínua 2016--2025, população completa "
             rf"($N = {fmtN(R['M0'].n)}$; {fmtN(n_upa)}~UPAs; {n_uf}~UFs). "
             r"Coeficientes com erro-padrão do modelo entre parênteses (a correlação intra-UPA já está "
             r"no efeito aleatório). Estimação por máxima verossimilhança (ML), para os testes LR entre "
             r"degraus; REML coincide. Com $N$ desta ordem quase todo coeficiente é significante; "
             r"a inferência relevante está nos intervalos de confiança, não nos asteriscos "
             r"\cite[cap.~8]{angrist2009}.}")
    L.append(r"\label{tab:hlm_resultados}")
    L.append(r"\resizebox{\textwidth}{!}{%")
    L.append(r"\begin{tabular}{l" + "c" * len(cols) + "}")
    L.append(r"\toprule")
    hdr = " & ".join([r"\textbf{Variável}"] + [r"\textbf{" + c + "}" for c in cols])
    L += [hdr + r" \\", r"\midrule"]
    grupos = [("", ["Intercept", "negro", "sexo_fem", "idade_c", "idade_sq"]),
              (r"\textit{Escolaridade (ref.: fundamental incompleto)}",
               ["educ_fund_completo", "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao"]),
              (r"\textit{Inserção}", ["log_horas", "urbano"]),
              (r"\textit{Contexto de bairro --- nível 2 (UPA)}", ["pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z"]),
              (r"\textit{Ocupação e vínculo (M4; \emph{bad controls})}",
               ["emprego_formal", "conta_propria", "trab_domestico", "ocp_dirigente", "ocp_profissional",
                "ocp_tecnico", "ocp_administrativo", "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa"])]
    for titulo, vs in grupos:
        if titulo:
            L.append(r"\addlinespace[3pt]")
            L.append(r"\multicolumn{" + str(len(cols) + 1) + "}{l}{" + titulo + r"} \\")
        for v in vs:
            L.append(" & ".join([LABELS[v]] + [cell(R[c], v) for c in cols]) + r" \\")
    # IC do negro
    L.append(r"\addlinespace[2pt]")
    ic = ["IC 95\\% de $\\beta_{\\text{negro}}$"]
    for c in cols:
        r = R[c]
        ic.append("---" if "negro" not in r.params.index else
                  f"[{fmt(r.conf.loc['negro', 0], 4)}; {fmt(r.conf.loc['negro', 1], 4)}]")
    L.append(" & ".join(ic) + r" \\")
    gapl = ["Gap (\\%) $= e^{\\beta}-1$"]
    for c in cols:
        r = R[c]
        gapl.append("---" if "negro" not in r.params.index else fmt((np.exp(r.params["negro"]) - 1) * 100, 1))
    L.append(" & ".join(gapl) + r" \\")
    L.append(r"Efeitos fixos de UF & não & não & não & sim & sim \\")
    # componentes de variância e ajuste
    L.append(r"\addlinespace[2pt] \midrule")
    L.append(r"\multicolumn{" + str(len(cols) + 1) + r"}{l}{\textit{Componentes de variância e ajuste}} \\")
    L.append(" & ".join([r"$\hat\tau^2_{\text{UPA}}$ (nível 2)"] + [fmt(R[c].tau2, 4) for c in cols]) + r" \\")
    L.append(" & ".join([r"$\hat\sigma^2$ (nível 1)"] + [fmt(R[c].sigma2, 4) for c in cols]) + r" \\")
    L.append(" & ".join([r"ICC$_{\text{UPA}}$"] + [fmt(R[c].icc, 3) for c in cols]) + r" \\")
    f = fit_df.set_index("modelo")
    L.append(" & ".join([r"$\tau^2$ explicada vs.\ M0 (\%)"] +
                        ["---" if c == "M0" else fmt(f.loc[c, "pct_tau2_explicada_vs_M0"], 1) for c in cols]) + r" \\")
    L.append(" & ".join([r"$-2\,$LL (deviance)"] + [fmtN(int(round(f.loc[c, "deviance"]))) for c in cols]) + r" \\")
    L.append(" & ".join(["AIC"] + [fmtN(int(round(f.loc[c, "aic"]))) for c in cols]) + r" \\")
    L.append(" & ".join(["BIC"] + [fmtN(int(round(f.loc[c, "bic"]))) for c in cols]) + r" \\")
    L.append(" & ".join([r"LR vs.\ degrau anterior ($\chi^2$, g.l.)"] +
                        ["---" if c == "M0" else f"{fmtN(int(round(f.loc[c, 'lr_vs_anterior'])))} ({int(f.loc[c, 'df_lr'])})"
                         for c in cols]) + r" \\")
    L.append(" & ".join([r"$p$ do LR"] + ["---" if c == "M0" else ("$<0{,}001$" if f.loc[c, "p_lr"] < 0.001 else fmt(f.loc[c, "p_lr"], 3))
                                           for c in cols]) + r" \\")
    L.append(r"\bottomrule")
    L.append(r"\end{tabular}}")
    rs = R["M3_RS"]
    L.append("")
    L.append(r"\noindent\footnotesize\emph{Inclinação aleatória de \texttt{negro} por UPA (M3 + $u_{1j}$):} "
             rf"$\hat\tau^2_{{1}} = {fmt(rs.tau2_slope, 4)}$ (DP $= {fmt(np.sqrt(max(rs.tau2_slope,0)), 3)}$ em log-pontos), "
             rf"cov$(u_0,u_1) = {fmt(rs.cov01, 4)}$; LR $= {fmtN(int(round(lr_rs)))}$ (2 g.l.), "
             + ("$p<0{,}001$" if p_rs < 0.001 else f"$p = {fmt(p_rs, 3)}$") +
             rf": a penalidade racial varia entre bairros; $\hat\beta_{{\text{{negro}}}}$ médio $= {fmt(rs.params['negro'], 4)}$.")
    L.append(r"\normalsize")
    L.append(r"\end{table}")
    (TABLES / "hlm_stepup.tex").write_text("\n".join(L) + "\n", encoding="utf-8")
    logger.info(f"Tabela LaTeX: {TABLES / 'hlm_stepup.tex'}")


if __name__ == "__main__":
    main()
