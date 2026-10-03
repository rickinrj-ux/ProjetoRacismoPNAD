"""
run_se_rif_interseccional.py
============================
Erros-padrão por BOOTSTRAP EM BLOCOS POR UPA para duas tabelas do núcleo que ainda os
reportavam (TODO_revisao, item 5.9):

  (a) RIF-OB por quantil (rif_ob_decomposicao.csv) — dotações e retornos em q10..q90;
  (b) Oaxaca-Blinder interseccional, 4 grupos raça x gênero (interseccional_ob4grupos.csv).

Método (Angrist & Pischke, cap. 8; Bickel & Sakov, 2008): reamostram-se UPAs inteiras com
reposição, porque as observações da mesma UPA são correlacionadas e as covariáveis de
contexto variam só no nível da UPA. Como a RIF exige reestimar a densidade e duas
regressões por quantil, cada réplica usa m = BOOT_FRAC x G UPAs ("m de n") e o
erro-padrão da população é obtido pela escala sqrt(m/G); reporta-se também o SE bruto
(conservador, sem escala).

Saídas: outputs/tables/rif_ob_se.csv e outputs/tables/interseccional_ob4grupos_se.csv
Uso: python scripts/analise/run_se_rif_interseccional.py [--boot 200] [--frac 0.05]
"""

# --- bootstrap raiz do projeto ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys, time, logging, argparse, warnings
from pathlib import Path
sys.path.insert(0, "src")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s",
                    datefmt="%H:%M:%S", handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

from rif_decomp import rif_ob_quantil, CONTROLES, QUANTIS_DEFAULT

# ── OB interseccional (4 grupos raça x gênero) na MESMA amostra do núcleo ─────
# O módulo src/interseccionalidade.py exige educ_ord (registrada em ~31% da PEA); aqui
# usam-se os dummies de conclusão + educ_missing, como no HLM/OB/QR/GLMM do núcleo.
OB4_FORMULA = ("log_renda ~ idade_c + idade_sq + educ_fund_completo + educ_medio_completo"
               " + educ_superior_completo + educ_pos_graduacao"
               " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z + C(Ano)")


def _ob_twofold(d_ref, d_trt):
    import statsmodels.formula.api as smf
    if len(d_ref) < 100 or len(d_trt) < 100:
        return None
    m_r = smf.ols(OB4_FORMULA, data=d_ref).fit()
    m_t = smf.ols(OB4_FORMULA, data=d_trt).fit()
    xb_r, xb_t = m_r.model.exog.mean(0), m_t.model.exog.mean(0)
    b_r, b_t = m_r.params.values, m_t.params.values
    gap = d_ref["log_renda"].mean() - d_trt["log_renda"].mean()
    end = (xb_r - xb_t) @ b_r
    ret = xb_t @ (b_r - b_t)
    pct = lambda x: x / gap * 100 if abs(gap) > 1e-8 else 0.0
    return {"gap": gap, "gap_pct": (np.exp(gap) - 1) * 100, "end": end, "end_pct": pct(end),
            "ret": ret, "ret_pct": pct(ret), "n_ref": len(d_ref), "n_n": len(d_trt)}


def decomposicao_ob_4grupos(df):
    ref = df[(df["negro"] == 0) & (df["sexo_fem"] == 0)]
    grupos = {"Mulher Branca": df[(df["negro"] == 0) & (df["sexo_fem"] == 1)],
              "Homem Negro":   df[(df["negro"] == 1) & (df["sexo_fem"] == 0)],
              "Mulher Negra":  df[(df["negro"] == 1) & (df["sexo_fem"] == 1)]}
    rows = []
    for nome, sub in grupos.items():
        r = _ob_twofold(ref, sub)
        if r:
            rows.append({"grupo": nome, **r})
    out = pd.DataFrame(rows)
    if len(out) == 3:
        g = out.set_index("grupo")["gap_pct"]
        extra = g["Mulher Negra"] - g["Mulher Branca"] - g["Homem Negro"]
        out["penalidade_extra_pct"] = [extra if x == "Mulher Negra" else 0.0 for x in out["grupo"]]
    else:
        out["penalidade_extra_pct"] = 0.0
    return out

TABLES = Path("outputs/tables")
SEED = 42
COLS = ["Ano", "log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
        "educ_fund_completo", "educ_medio_completo", "educ_superior_completo",
        "educ_pos_graduacao", "educ_cat", "pct_negro_upa_z", "tx_desemprego_upa_z",
        "media_educ_upa_z", "pea", "renda_bruta", "UF", "UPA"]


def carregar():
    df = pd.read_parquet("data/processed/features.parquet", columns=COLS)
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0) & df["negro"].notna()].copy()
    df["educ_missing"] = df["educ_cat"].isna().astype(int)
    req = [c for c in COLS if c not in ("UF", "UPA", "educ_cat", "pea", "renda_bruta")]
    df = df.dropna(subset=req).reset_index(drop=True)
    df["UF_str"] = df["UF"].astype(str)
    logger.info(f"N = {len(df):,} | UPAs = {df['UPA'].nunique():,}")
    return df


def blocos(df):
    codes, idx = pd.factorize(df["UPA"])
    order = np.argsort(codes, kind="stable")
    bounds = np.flatnonzero(np.diff(codes[order])) + 1
    starts = np.concatenate([[0], bounds]); ends = np.concatenate([bounds, [len(order)]])
    return order, starts, ends, len(idx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=200)
    ap.add_argument("--frac", type=float, default=0.05, help="fração de UPAs por réplica")
    ap.add_argument("--so-ob4", action="store_true", help="pula a RIF (reaproveita rif_ob_se.csv)")
    args = ap.parse_args()

    df = carregar()
    order, starts, ends, G = blocos(df)
    m = max(int(G * args.frac), 50)
    escala = np.sqrt(m / G)
    rng = np.random.default_rng(SEED)
    logger.info(f"bootstrap em blocos: {args.boot} réplicas de m={m:,} UPAs de {G:,} "
                f"(escala sqrt(m/G) = {escala:.4f})")

    # ── ponto (população completa) ────────────────────────────────────────────
    t0 = time.time()
    rif_pt = (None if args.so_ob4 else
              pd.DataFrame([rif_ob_quantil(df, tau, CONTROLES) for tau in QUANTIS_DEFAULT]))
    ob4_pt = decomposicao_ob_4grupos(df)
    ob4_pt.to_csv(TABLES / "interseccional_ob4grupos_nucleo.csv", index=False, encoding="utf-8")
    logger.info(f"estimativas pontuais em {time.time()-t0:.0f}s")

    # ── réplicas ──────────────────────────────────────────────────────────────
    rif_b, ob4_b = [], []
    t0 = time.time()
    for b in range(args.boot):
        sel = rng.integers(0, G, size=m)
        idx = np.concatenate([order[starts[g]:ends[g]] for g in sel])
        d = df.iloc[idx]
        try:
            if not args.so_ob4:
                rif_b.append(pd.DataFrame([rif_ob_quantil(d, tau, CONTROLES) for tau in QUANTIS_DEFAULT]))
            ob4_b.append(decomposicao_ob_4grupos(d))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"  réplica {b} descartada: {e}")
        if (b + 1) % 20 == 0:
            logger.info(f"  {b+1}/{args.boot} réplicas ({(time.time()-t0)/60:.1f} min)")

    def se(frames, key_col, key_vals, cols):
        out = {}
        for kv in key_vals:
            for c in cols:
                vals = [f.loc[f[key_col] == kv, c].iloc[0] for f in frames if (f[key_col] == kv).any()]
                out[(kv, c)] = (float(np.std(vals, ddof=1)) if len(vals) > 2 else np.nan, len(vals))
        return out

    if args.so_ob4:
        rif_pt = None
    cols_rif = ["gap_obs", "end", "ret", "end_pct", "ret_pct"]
    s_rif = se(rif_b, "q_label", list(rif_pt["q_label"]), cols_rif) if rif_pt is not None else {}
    rows = []
    for _, r in (rif_pt.iterrows() if rif_pt is not None else []):
        row = {"q_label": r["q_label"], "tau": r["tau"], "n_b": r["n_b"], "n_n": r["n_n"]}
        for c in cols_rif:
            raw, nrep = s_rif[(r["q_label"], c)]
            row[c] = r[c]; row[f"se_{c}"] = raw * escala; row[f"se_{c}_raw"] = raw
        row["n_boot"] = nrep
        rows.append(row)
    if rows:
        pd.DataFrame(rows).assign(m_upas=m, n_upas=G, escala=escala).to_csv(
            TABLES / "rif_ob_se.csv", index=False, encoding="utf-8")

    cols_ob = ["gap", "gap_pct", "end_pct", "ret_pct"]
    s_ob = se(ob4_b, "grupo", list(ob4_pt["grupo"]), cols_ob)
    rows = []
    for _, r in ob4_pt.iterrows():
        row = {"grupo": r["grupo"], "n_ref": r["n_ref"], "n_n": r["n_n"],
               "penalidade_extra_pct": r["penalidade_extra_pct"]}
        for c in cols_ob:
            raw, nrep = s_ob[(r["grupo"], c)]
            row[c] = r[c]; row[f"se_{c}"] = raw * escala; row[f"se_{c}_raw"] = raw
        row["n_boot"] = nrep
        rows.append(row)
    pd.DataFrame(rows).assign(m_upas=m, n_upas=G, escala=escala).to_csv(
        TABLES / "interseccional_ob4grupos_se.csv", index=False, encoding="utf-8")

    logger.info(f"CONCLUÍDO em {(time.time()-t0)/60:.1f} min -> rif_ob_se.csv, "
                f"interseccional_ob4grupos_se.csv")
    print(pd.DataFrame(rows)[["grupo", "gap_pct", "se_gap_pct", "ret_pct", "se_ret_pct"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
