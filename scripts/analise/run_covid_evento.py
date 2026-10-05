"""
run_covid_evento.py — estudo de evento da COVID-19 na base corrigida (E8.8, 05/10/2026)
========================================================================================
Substitui, para o TCC, o run_event_study_covid.py de maio/2026: aquele usava a escolaridade
antiga (V3009A), MQO poolado sem efeito de bairro e erro agrupado por UF (27 grupos, MHE-81).

Duas perguntas sobre a quebra de 2020:

1. Penalidade salarial ano a ano (base 2019), na amostra do M3:
       log_renda_i = Σ_t γ_t·1(Ano=t) + β·negro_i + Σ_{t≠2019} δ_t·negro_i·1(Ano=t)
                     + X_i'θ + α_UPA + ε_i
   X = controles individuais do M3 (sexo, idade, idade², escolaridade cumulativa, log horas);
   α_UPA = efeito fixo de bairro (absorve UF, urbano e o contexto da UPA). δ_t > 0: penalidade
   menor que em 2019. Erro agrupado por UPA.
   - pré-tendência: Wald δ_2016 = δ_2017 = δ_2018 = 0;
   - detrending: desvio de δ_2020 e δ_2021 em relação à reta ajustada a δ_2016…δ_2019
     (δ_2019 ≡ 0), com EP pelo método delta (a reta é combinação linear dos δ).

2. Ocupação na força de trabalho (pea = 1; ocupado = VD4002 == 1), mesma estrutura, MPL:
   δ^emp_t < 0 em 2020 = os negros perderam mais ocupação → a amostra de renda de 2020 fica
   selecionada (sai quem ganha menos), e o gap observado encolhe sem que o preço mude.

Base populacional, sem amostragem (regra do projeto). Não ponderado, como o núcleo.
Saídas: outputs/tables/covid_evento.csv (δ_t por desfecho) e covid_evento_resumo.csv.
"""
import os as _os
import sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())

import sys
sys.stdout.reconfigure(encoding="utf-8")
import time

import numpy as np
import pandas as pd
from scipy import stats

FEAT = _Path("data/processed/features.parquet")
TABLES = _Path("outputs/tables")
ANOS = list(range(2016, 2026))
BASE = 2019
PRE = [2016, 2017, 2018]
EDUC = ["educ_fund_completo", "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao"]
T0 = time.time()


def _log(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def fe_ols_cluster(df, y, xcols, grupo):
    """MQO com efeito fixo de `grupo` (transformação within) e EP agrupado pelo mesmo grupo.

    Feito à mão, em float64 e sem patsy: a matriz de 7,7 milhões × ~25 cabe na memória,
    mas o statsmodels duplica-a várias vezes (ver logit_cluster em run_robustez_desenho.py).
    """
    codes, uniq = pd.factorize(df[grupo], sort=False)
    G = len(uniq)
    cnt = np.bincount(codes, minlength=G).astype(float)

    def within(v):
        v = np.asarray(v, dtype=float)
        return v - (np.bincount(codes, weights=v, minlength=G) / cnt)[codes]

    yw = within(df[y].values)
    X = np.column_stack([within(df[c].values) for c in xcols])
    XtX = X.T @ X
    beta = np.linalg.solve(XtX, X.T @ yw)
    e = yw - X @ beta
    S = np.column_stack([np.bincount(codes, weights=X[:, j] * e, minlength=G)
                         for j in range(X.shape[1])])
    n, k = X.shape
    bread = np.linalg.inv(XtX)
    c = G / (G - 1) * (n - 1) / (n - k - G)        # graus de liberdade com o FE absorvido
    V = c * bread @ (S.T @ S) @ bread
    return pd.Series(beta, index=xcols), pd.DataFrame(V, index=xcols, columns=xcols), n, G


def evento(df, y, controles, rotulo):
    df = df.copy()
    for a in ANOS:
        if a != BASE:
            df[f"ano_{a}"] = (df["Ano"] == a).astype(np.int8)
            df[f"neg_{a}"] = (df["negro"] * (df["Ano"] == a)).astype(np.int8)
    xcols = (["negro"] + controles + [f"ano_{a}" for a in ANOS if a != BASE]
             + [f"neg_{a}" for a in ANOS if a != BASE])
    b, V, n, G = fe_ols_cluster(df, y, xcols, "UPA")
    _log(f"{rotulo}: N = {n:,} | UPAs = {G:,} | β_negro(2019) = {b['negro']:+.5f}")

    linhas = []
    for a in ANOS:
        if a == BASE:
            linhas.append(dict(desfecho=rotulo, ano=a, delta=0.0, se=0.0, p=np.nan))
            continue
        k = f"neg_{a}"
        se = float(np.sqrt(V.loc[k, k]))
        linhas.append(dict(desfecho=rotulo, ano=a, delta=float(b[k]), se=se,
                           p=float(2 * stats.t.sf(abs(b[k] / se), G - 1))))
    tab = pd.DataFrame(linhas)
    tab["ic_lo"], tab["ic_hi"] = tab["delta"] - 1.96 * tab["se"], tab["delta"] + 1.96 * tab["se"]

    # pré-tendência (Wald, F com G − 1 graus no denominador)
    kp = [f"neg_{a}" for a in PRE]
    bp = b[kp].values
    W = float(bp @ np.linalg.solve(V.loc[kp, kp].values, bp))
    F = W / len(kp)
    p_pre = float(stats.f.sf(F, len(kp), G - 1))

    # detrending: reta em δ_2016…δ_2019 (δ_2019 ≡ 0) → desvio em 2020 e 2021
    Z = np.column_stack([np.ones(4), np.array(PRE + [BASE]) - BASE])
    L = np.linalg.solve(Z.T @ Z, Z.T)                 # coef = L @ [δ16, δ17, δ18, 0]
    resumo = dict(desfecho=rotulo, N=n, n_upa=G, beta_negro_2019=float(b["negro"]),
                  se_beta_2019=float(np.sqrt(V.loc["negro", "negro"])),
                  F_pre=F, p_pre=p_pre)
    for a in (2020, 2021):
        cvec = pd.Series(0.0, index=xcols)
        cvec[f"neg_{a}"] = 1.0
        pred = np.array([1.0, a - BASE]) @ L          # pesos da reta sobre (δ16, δ17, δ18, δ19)
        for j, ap in enumerate(PRE):
            cvec[f"neg_{ap}"] -= pred[j]
        dev = float(cvec @ b)
        se = float(np.sqrt(cvec.values @ V.values @ cvec.values))
        resumo[f"desvio_{a}"] = dev
        resumo[f"se_desvio_{a}"] = se
        resumo[f"p_desvio_{a}"] = float(2 * stats.t.sf(abs(dev / se), G - 1))
        resumo[f"tendencia_{a}"] = float(pred[:3] @ bp)
    # inclinação da reta pré-2020: os anos anteriores derivavam ou só oscilavam?
    cs = pd.Series(0.0, index=xcols)
    for j, ap in enumerate(PRE):
        cs[f"neg_{ap}"] = L[1, j]
    resumo["inclinacao_pre"] = float(cs @ b)
    resumo["se_inclinacao_pre"] = float(np.sqrt(cs.values @ V.values @ cs.values))
    resumo["p_inclinacao_pre"] = float(2 * stats.t.sf(
        abs(resumo["inclinacao_pre"] / resumo["se_inclinacao_pre"]), G - 1))
    _log(f"  pré-tendência F = {F:.2f} (p = {p_pre:.4f}); δ2020 = {tab.loc[tab.ano == 2020, 'delta'].item():+.5f}; "
         f"desvio da tendência 2020 = {resumo['desvio_2020']:+.5f} (EP {resumo['se_desvio_2020']:.5f})")
    return tab, resumo


def main():
    # ── 1. Penalidade salarial: amostra do M3 (renda > 0, completos, UPA com ≥ 10) ──
    ctrl = ["sexo_fem", "idade_c", "idade_sq"] + EDUC + ["log_horas"]
    cols = ["log_renda", "negro", "Ano", "UPA"] + ctrl + ["UF", "urbano",
            "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z"]
    d = pd.read_parquet(FEAT, columns=cols)
    d = d[d["log_renda"].notna() & (d["log_renda"] > 0)].dropna(subset=cols)
    vc = d["UPA"].value_counts()
    d = d[d["UPA"].isin(vc[vc >= 10].index)].reset_index(drop=True)
    tab_r, res_r = evento(d, "log_renda", ctrl, "log_renda")
    del d

    # ── 2. Ocupação na força de trabalho ──
    ctrl_e = ["sexo_fem", "idade_c", "idade_sq"] + EDUC
    cols = ["pea", "VD4002", "negro", "Ano", "UPA"] + ctrl_e
    d = pd.read_parquet(FEAT, columns=cols)
    d = d[d["pea"] == 1].dropna(subset=cols).reset_index(drop=True)
    d["ocupado"] = (d["VD4002"] == 1).astype(float)
    taxa = d.groupby(["Ano", "negro"])["ocupado"].mean().unstack()
    tab_e, res_e = evento(d, "ocupado", ctrl_e, "ocupado")
    for a in ANOS:
        tab_e.loc[tab_e.ano == a, "tx_branco"] = taxa.loc[a, 0.0]
        tab_e.loc[tab_e.ano == a, "tx_negro"] = taxa.loc[a, 1.0]

    pd.concat([tab_r, tab_e]).to_csv(TABLES / "covid_evento.csv", index=False)
    pd.DataFrame([res_r, res_e]).to_csv(TABLES / "covid_evento_resumo.csv", index=False)
    _log("OK -> covid_evento.csv, covid_evento_resumo.csv")


if __name__ == "__main__":
    main()
