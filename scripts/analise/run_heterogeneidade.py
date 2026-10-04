# -*- coding: utf-8 -*-
"""
run_heterogeneidade.py  (04/10/2026)
====================================
Módulo de heterogeneidade: o que a categoria "negro" agrega e o que o setor e a idade
escondem. Mesmas bases e especificações dos modelos de referência do TCC.

  --hlm cor3      HLM M3 com pardo e preto separados (UPA aleatória, UF e ano fixos)
  --hlm idade     HLM M3 + negro × faixa etária (14–29, 30–39 [ref], 40–49, 50–64, 65+)
  --hlm setor0    HLM M3 só no setor privado
  --hlm setor1    HLM M3 só no setor público
                  -> outputs/tables/hlm_heterogeneidade.csv (uma linha por termo)
  --oaxaca        Oaxaca (A) e (B), branco × pardo e branco × preto (gerar_tabela_oaxaca.py)
                  -> outputs/tables/oaxaca_por_cor.csv
  --qr            QR M3 com pardo e preto, q10…q95 (run_regressao_quantilica.py)
                  -> outputs/tables/qr_por_cor.csv
  --rif           RIF-OB branco × pardo e branco × preto (src/rif_decomp.py, mesmos controles)
                  -> outputs/tables/rif_por_cor.csv

Um bloco por processo (memória). População completa — regra do projeto.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "scripts" / "analise"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import patsy

TABLES = ROOT / "outputs" / "tables"
FEAT = ROOT / "data" / "processed" / "features.parquet"
QUANTIS = (0.10, 0.25, 0.50, 0.75, 0.90, 0.95)


def _log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} | {msg}", flush=True)


def _acrescenta(linhas: list[dict], nome: str) -> None:
    out = TABLES / nome
    novo = pd.DataFrame(linhas)
    if out.exists():
        velho = pd.read_csv(out)
        # refazer um bloco substitui as linhas dele
        if "bloco" in novo.columns and "bloco" in velho.columns:
            velho = velho[~velho["bloco"].isin(novo["bloco"].unique())]
        novo = pd.concat([velho, novo], ignore_index=True)
    novo.to_csv(out, index=False)
    _log(f"OK -> {out.name}")


# ── HLM ────────────────────────────────────────────────────────────────────────
def hlm(bloco: str) -> None:
    import run_hlm_stepup as S

    extras = ["V2010", "setor_publico", "idade"]
    df = pd.read_parquet(FEAT, columns=list(dict.fromkeys(S.MODEL_VARS + extras)))
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    df = df.dropna(subset=S.MODEL_VARS).reset_index(drop=True)
    cont = df["UPA"].value_counts()
    df = df[df["UPA"].isin(cont[cont >= 10].index)].reset_index(drop=True)   # como no step-up
    df["UPA_str"] = df["UPA"].astype(str)
    df["UF_str"] = df["UF"].astype(str)
    df["log_renda"] = df["log_renda"].astype(float)
    df["setor_publico"] = df["setor_publico"].fillna(0).astype(int)
    df["pardo"] = (df["V2010"] == 4).astype(int)
    df["preto"] = (df["V2010"] == 2).astype(int)
    df["faixa"] = pd.cut(df["idade"], [13, 29, 39, 49, 64, 200],
                         labels=["14_29", "30_39", "40_49", "50_64", "65mais"]).astype(str)

    base = f"log_renda ~ {S._IND} + {S._UPA} + C(UF_str)"          # o M3
    if bloco == "cor3":
        formula, termos = base.replace("negro + ", "pardo + preto + ", 1), ["pardo", "preto"]
    elif bloco == "idade":
        formula = base + " + C(faixa, Treatment('30_39')) + negro:C(faixa, Treatment('30_39'))"
        termos = None
    elif bloco in ("setor0", "setor1"):
        df = df[df["setor_publico"] == int(bloco[-1])].reset_index(drop=True)
        formula, termos = base, ["negro"]
    else:
        raise SystemExit(f"bloco desconhecido: {bloco}")
    _log(f"HLM {bloco}: N = {len(df):,} | UPAs = {df['UPA_str'].nunique():,}")
    L = S.fit_mixed(f"het_{bloco}", formula, df)
    if termos is None:
        termos = ["negro"] + [t for t in L.params.index if t.startswith("negro:")]
    linhas = []
    for t in termos:
        b, se = float(L.params[t]), float(L.bse[t])
        linhas.append({"bloco": bloco, "termo": t, "beta": b, "se": se,
                       "gap_pct": (np.exp(b) - 1) * 100, "N": len(df),
                       "n_upa": df["UPA_str"].nunique(), "converged": L.converged})
        _log(f"  {t}: β = {b:.4f} (SE {se:.4f})")
    _acrescenta(linhas, "hlm_heterogeneidade.csv")


# ── Oaxaca por cor ─────────────────────────────────────────────────────────────
def oaxaca() -> None:
    educ = "educ_fund_completo + educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
    demo = "idade_c + idade_sq + sexo_fem + C(Ano)"
    insercao = "log_horas + urbano + C(UF)"
    ctx = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
    occ = ("emprego_formal + conta_propria + trab_domestico + ocp_dirigente + ocp_profissional"
           " + ocp_tecnico + ocp_administrativo + ocp_servicos + ocp_agro + ocp_operario"
           " + ocp_operador + ocp_ffaa")
    especs = {"A": f"{educ} + {demo} + {insercao} + {ctx}",
              "B": f"{educ} + {demo} + {insercao} + {ctx} + {occ}"}
    cols = ["Ano", "V2010", "negro", "sexo_fem", "idade_c", "idade_sq", "educ_fund_completo",
            "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
            "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z", "log_horas", "urbano",
            "emprego_formal", "conta_propria", "trab_domestico", "ocp_dirigente",
            "ocp_profissional", "ocp_tecnico", "ocp_administrativo", "ocp_servicos", "ocp_agro",
            "ocp_operario", "ocp_operador", "ocp_ffaa", "log_renda", "renda_bruta", "pea", "UF"]
    df = pd.read_parquet(FEAT, columns=cols)
    df = df[(df["pea"] == 1) & (df["renda_bruta"] > 0) & df["negro"].notna()]
    df = df.dropna(subset=[c for c in cols if c not in ("renda_bruta", "pea")]).reset_index(drop=True)
    df["log_renda"] = df["log_renda"].astype(float)
    linhas = []
    for cor, cod in (("pardo", 4), ("preto", 2)):
        sub = df[df["V2010"].isin([1, cod])].reset_index(drop=True)
        mk_b = (sub["V2010"] == 1).values
        for nome, rhs in especs.items():
            y, X = patsy.dmatrices(f"log_renda ~ {rhs}", sub, return_type="matrix")
            y, X = np.asarray(y).ravel(), np.asarray(X)
            bb = np.linalg.lstsq(X[mk_b], y[mk_b], rcond=None)[0]
            xb, xn = X[mk_b].mean(0), X[~mk_b].mean(0)
            gap = y[mk_b].mean() - y[~mk_b].mean()
            dot = (xb - xn) @ bb                     # referência: preços dos brancos
            linhas.append({"cor": cor, "espec": nome, "gap": gap,
                           "gap_pct": (np.exp(gap) - 1) * 100,
                           "pct_dotacao": dot / gap * 100, "pct_retornos": (gap - dot) / gap * 100,
                           "n_brancos": int(mk_b.sum()), "n_grupo": int((~mk_b).sum())})
            _log(f"  branco × {cor} ({nome}): gap {gap:.4f} | retornos {(gap - dot) / gap * 100:.1f}%")
            del X
    pd.DataFrame(linhas).to_csv(TABLES / "oaxaca_por_cor.csv", index=False)
    _log("OK -> oaxaca_por_cor.csv")


# ── Regressão quantílica por cor ───────────────────────────────────────────────
def qr() -> None:
    import statsmodels.api as sm

    cols = ["Ano", "V2010", "negro", "sexo_fem", "idade_c", "idade_sq", "educ_fund_completo",
            "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
            "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z", "log_horas", "urbano",
            "log_renda", "renda_bruta", "pea", "UF"]
    df = pd.read_parquet(FEAT, columns=cols)
    df = df[(df["pea"] == 1) & (df["renda_bruta"] > 0) & df["negro"].notna()]
    df = df.dropna(subset=[c for c in cols if c not in ("renda_bruta", "pea")]).reset_index(drop=True)
    df["UF_str"] = df["UF"].astype(str)
    df["pardo"] = (df["V2010"] == 4).astype(int)
    df["preto"] = (df["V2010"] == 2).astype(int)
    # o M3 de run_regressao_quantilica.py, com pardo e preto no lugar de negro
    f = ("log_renda ~ pardo + preto + educ_fund_completo + educ_medio_completo"
         " + educ_superior_completo + educ_pos_graduacao + idade_c + idade_sq + sexo_fem"
         " + log_horas + urbano + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
         " + C(Ano) + C(UF_str)")
    y, X = patsy.dmatrices(f, df, return_type="dataframe")
    jp, jt = list(X.columns).index("pardo"), list(X.columns).index("preto")
    mod = sm.QuantReg(np.asarray(y).ravel(), np.asarray(X))
    linhas = []
    for q in QUANTIS:
        t0 = time.time()
        r = mod.fit(q=q, max_iter=2000, p_tol=1e-6)
        for cor, j in (("pardo", jp), ("preto", jt)):
            b, se = float(r.params[j]), float(r.bse[j])
            linhas.append({"quantil": q, "cor": cor, "beta": b, "se": se,
                           "gap_pct": (np.exp(b) - 1) * 100, "N": len(df)})
        _log(f"  q{int(q*100)}: pardo {linhas[-2]['gap_pct']:.1f}% | preto {linhas[-1]['gap_pct']:.1f}% | {time.time()-t0:.0f}s")
        pd.DataFrame(linhas).to_csv(TABLES / "qr_por_cor.csv", index=False)
    _log("OK -> qr_por_cor.csv")


# ── RIF-OB por cor ─────────────────────────────────────────────────────────────
def rif() -> None:
    from rif_decomp import carregar_dados, rif_ob_quantil, CONTROLES, QUANTIS_DEFAULT

    df = carregar_dados()
    linhas = []
    for cor, cod in (("pardo", 4), ("preto", 2)):
        sub = df[df["V2010"].isin([1, cod])].copy()
        sub["negro"] = (sub["V2010"] == cod).astype(int)   # o "grupo" do contraste
        for tau in QUANTIS_DEFAULT:
            r = rif_ob_quantil(sub, tau, CONTROLES)
            g = r["gap_rif"]
            linhas.append({"cor": cor, "quantil": r["q_label"], "gap_obs": r["gap_obs"],
                           "gap_rif": g, "pct_dotacao": r["end"] / g * 100,
                           "pct_retornos": r["ret"] / g * 100})
            _log(f"  branco × {cor} {r['q_label']}: retornos {r['ret'] / g * 100:.1f}% do gap RIF")
        del sub
    pd.DataFrame(linhas).to_csv(TABLES / "rif_por_cor.csv", index=False)
    _log("OK -> rif_por_cor.csv")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    if a[0] == "--hlm":
        hlm(a[1])
    elif a[0] == "--oaxaca":
        oaxaca()
    elif a[0] == "--qr":
        qr()
    elif a[0] == "--rif":
        rif()
