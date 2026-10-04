# -*- coding: utf-8 -*-
"""
run_robustez_desenho.py
=======================
Robustezes pedidas pelo orientador em jul/2026 (commits 7b63530..f6f255b, base antiga),
refeitas na base atual (VD3004, deflação, leave-one-out) e na especificação atual.

  --glmm      Logit de acesso na especificação A2 (individual + contexto do bairro + UF e
              ano fixos), sem peso e com o peso amostral V1028, ambos com erro-padrão
              agrupado por UPA, nos três desfechos. É o "atalho de um nível" do GLMM: o
              multinível ponderado é o WeMix (scripts/R/wemix_multinivel_ponderado.R).
              -> outputs/tables/glmm_ponderado_a2.csv
  --oaxaca    Decomposição de Oaxaca–Blinder (especificações A e B de
              gerar_tabela_oaxaca.py) sem peso e com V1028 (MQO ponderado e médias
              ponderadas). -> outputs/tables/oaxaca_ponderado_ab.csv
  --baseline  MQO linear com as mesmas variáveis, o mesmo treino e o mesmo teste do
              RF/XGBoost (funções de run_ml_shap.py): quanto o ML ganha sobre o linear.
              -> outputs/tables/ml_baseline_comparacao.csv

Sem argumento, roda os três. População completa (regra do projeto: não amostrar).
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
OCP = ["dirigente", "profissional", "tecnico", "administrativo"]


def _log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} | {msg}", flush=True)


def logit_cluster(y, X, w, grupos, maxiter=50, tol=1e-9, bloco=1_000_000):
    """Logit ponderado por Newton, com erro-padrão agrupado (sanduíche por cluster).

    Implementação enxuta, em blocos: o statsmodels.GLM fazia cópias da matriz n×k
    (7,7 milhões × 58) e estourava a memória, sem peso (IRLS/SVD) e com peso. Aqui só
    há a matriz X e vetores; a hessiana (k×k) e os escores por cluster (G×k) são somados
    bloco a bloco. Estimador idêntico ao GLM Binomial com freq_weights.
    """
    n, k = X.shape
    beta = np.zeros(k)
    for _ in range(maxiter):
        H = np.zeros((k, k))
        g = np.zeros(k)
        for i in range(0, n, bloco):
            Xb = X[i:i + bloco]
            p_ = 1.0 / (1.0 + np.exp(-(Xb @ beta)))
            wb = w[i:i + bloco]
            g += Xb.T @ (wb * (y[i:i + bloco] - p_))
            H += (Xb * (wb * p_ * (1 - p_))[:, None]).T @ Xb
        passo = np.linalg.solve(H, g)
        beta += passo
        if np.max(np.abs(passo)) < tol:
            break
    # sanduíche agrupado: escores somados dentro de cada cluster
    G = int(grupos.max()) + 1
    S = np.zeros((G, k))
    H = np.zeros((k, k))
    for i in range(0, n, bloco):
        Xb = X[i:i + bloco]
        p_ = 1.0 / (1.0 + np.exp(-(Xb @ beta)))
        wb = w[i:i + bloco]
        np.add.at(S, grupos[i:i + bloco], Xb * (wb * (y[i:i + bloco] - p_))[:, None])
        H += (Xb * (wb * p_ * (1 - p_))[:, None]).T @ Xb
    Hi = np.linalg.inv(H)
    corr = G / (G - 1) * (n - 1) / (n - k)
    V = corr * Hi @ (S.T @ S) @ Hi
    return beta, np.sqrt(np.diag(V))


# ── GLMM: logit A2 com e sem peso, cluster por UPA ─────────────────────────────
def glmm() -> None:
    import statsmodels.api as sm

    cols = ["pea", "renda_bruta", "negro", "sexo_fem", "UPA", "UF", "Ano", "V1028",
            "educ_fund_completo", "educ_medio_completo", "educ_superior_completo",
            "educ_pos_graduacao", "idade_c", "idade_sq", "urbano",
            "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z", "ocp_grupo_cbo"]
    df = pd.read_parquet(FEAT, columns=cols)
    df = df[(df["pea"] == 1) & (df["renda_bruta"] > 0) & df["negro"].notna()
            & df["V1028"].notna() & (df["V1028"] > 0)]
    df = df.dropna(subset=[c for c in cols if c not in ("ocp_grupo_cbo",)]).reset_index(drop=True)
    # desfechos como em scripts/R/glmm_glassceil.R
    df["ocp_qualif"] = df["ocp_grupo_cbo"].astype(str).isin(OCP).astype(int)
    q80, q90 = df["renda_bruta"].quantile(0.80), df["renda_bruta"].quantile(0.90)
    df["y_top20"] = (df["renda_bruta"] >= q80).astype(int)
    df["y_top10"] = (df["renda_bruta"] >= q90).astype(int)
    _log(f"GLMM: N = {len(df):,} | UPAs = {df['UPA'].nunique():,}")

    rhs = ("negro + sexo_fem + educ_fund_completo + educ_medio_completo + educ_superior_completo"
           " + educ_pos_graduacao + idade_c + idade_sq + urbano + C(Ano) + C(UF)"
           " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z")
    X = patsy.dmatrix(rhs, df, return_type="dataframe")
    j = list(X.columns).index("negro")
    Xv = np.ascontiguousarray(X.values)
    del X
    grupos = pd.factorize(df["UPA"])[0]
    peso = (df["V1028"] / df["V1028"].mean()).values
    linhas = []
    for y in ("ocp_qualif", "y_top20", "y_top10"):
        for ponderado in (False, True):
            t0 = time.time()
            w = peso if ponderado else np.ones(len(df))
            beta, ses = logit_cluster(df[y].values.astype(float), Xv, w, grupos)
            b, se = float(beta[j]), float(ses[j])
            linhas.append({"desfecho": y, "ponderado": ponderado,
                           "especificacao": ("A2 logit UF fixo, peso V1028 + cluster UPA" if ponderado
                                             else "A2 logit UF fixo, cluster UPA"),
                           "OR_negro": np.exp(b), "SE_negro": se,
                           "CI95_lo": np.exp(b - 1.96 * se), "CI95_hi": np.exp(b + 1.96 * se),
                           "N": len(df)})
            _log(f"  {y} | peso={ponderado} | OR = {np.exp(b):.4f} (SE {se:.4f}) | {time.time()-t0:.0f}s")
            pd.DataFrame(linhas).to_csv(TABLES / "glmm_ponderado_a2.csv", index=False)
    _log("OK -> glmm_ponderado_a2.csv")


# ── Oaxaca–Blinder com e sem peso ──────────────────────────────────────────────
def oaxaca() -> None:
    # as mesmas especificações de tcc/scripts/gerar_tabela_oaxaca.py (A ≡ M3, B ≡ M4)
    educ = "educ_fund_completo + educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
    demo = "idade_c + idade_sq + sexo_fem + C(Ano)"
    insercao = "log_horas + urbano + C(UF)"
    ctx = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
    occ = ("emprego_formal + conta_propria + trab_domestico + ocp_dirigente + ocp_profissional"
           " + ocp_tecnico + ocp_administrativo + ocp_servicos + ocp_agro + ocp_operario"
           " + ocp_operador + ocp_ffaa")
    especs = {"A": f"{educ} + {demo} + {insercao} + {ctx}",
              "B": f"{educ} + {demo} + {insercao} + {ctx} + {occ}"}
    cols = ["Ano", "negro", "sexo_fem", "idade_c", "idade_sq", "educ_fund_completo",
            "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
            "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z", "log_horas", "urbano",
            "emprego_formal", "conta_propria", "trab_domestico", "ocp_dirigente",
            "ocp_profissional", "ocp_tecnico", "ocp_administrativo", "ocp_servicos", "ocp_agro",
            "ocp_operario", "ocp_operador", "ocp_ffaa", "log_renda", "renda_bruta", "pea", "UF",
            "V1028"]
    df = pd.read_parquet(FEAT, columns=cols)
    df = df[(df["pea"] == 1) & (df["renda_bruta"] > 0) & df["negro"].notna()
            & df["V1028"].notna() & (df["V1028"] > 0)]
    df = df.dropna(subset=[c for c in cols if c not in ("renda_bruta", "pea")]).reset_index(drop=True)
    df["log_renda"] = df["log_renda"].astype(float)
    _log(f"Oaxaca: N = {len(df):,}")
    linhas = []
    for nome, rhs in especs.items():
        y, X = patsy.dmatrices(f"log_renda ~ {rhs}", df, return_type="matrix")
        y = np.asarray(y).ravel()
        X = np.asarray(X)
        b_mask = (df["negro"] == 0).values
        for ponderado in (False, True):
            w = df["V1028"].values if ponderado else np.ones(len(df))
            res = {}
            for grupo, mk in (("b", b_mask), ("n", ~b_mask)):
                Xg, yg, wg = X[mk], y[mk], w[mk]
                sw = np.sqrt(wg)
                beta = np.linalg.lstsq(Xg * sw[:, None], yg * sw, rcond=None)[0]
                res[grupo] = (beta, (Xg * wg[:, None]).sum(0) / wg.sum(), (yg * wg).sum() / wg.sum())
            (bb, xb, yb), (bn, xn, yn) = res["b"], res["n"]
            gap = yb - yn
            dot = (xb - xn) @ bb               # referência: preços dos brancos
            ret = gap - dot
            linhas.append({"espec": nome, "ponderado": ponderado, "gap": gap,
                           "pct_dotacao": dot / gap * 100, "pct_retornos": ret / gap * 100,
                           "N": len(df)})
            _log(f"  ({nome}) peso={ponderado} | gap = {gap:.4f} | retornos = {ret / gap * 100:.1f}%")
        del X
    pd.DataFrame(linhas).to_csv(TABLES / "oaxaca_ponderado_ab.csv", index=False)
    _log("OK -> oaxaca_ponderado_ab.csv")


# ── Baseline MQO do ML ─────────────────────────────────────────────────────────
def baseline() -> None:
    from sklearn.linear_model import LinearRegression
    import run_ml_shap as M

    df = M.load_data()
    X_tr, X_te, y_tr, y_te, _df, _pos = M.split(df)
    del df, _df
    lr = LinearRegression().fit(X_tr, y_tr)
    ols = M.evaluate("MQO (baseline linear)", y_te, lr.predict(X_te))
    perf = pd.read_csv(TABLES / "ml_performance.csv")
    linhas = [{"Modelo": ols["Modelo"], "R2_teste": ols["R²"], "MAE_teste": ols["MAE"],
               "RMSE_teste": ols["RMSE"], "ganho_R2_vs_MQO": 0.0}]
    for _, r in perf.iterrows():
        if r["Modelo"] in ("Random Forest", "XGBoost"):
            linhas.append({"Modelo": r["Modelo"], "R2_teste": r["R²"], "MAE_teste": r["MAE"],
                           "RMSE_teste": r["RMSE"], "ganho_R2_vs_MQO": r["R²"] - ols["R²"]})
    pd.DataFrame(linhas).to_csv(TABLES / "ml_baseline_comparacao.csv", index=False)
    _log(f"OK -> ml_baseline_comparacao.csv | MQO R² = {ols['R²']:.4f}")


if __name__ == "__main__":
    args = set(sys.argv[1:]) or {"--glmm", "--oaxaca", "--baseline"}
    if "--oaxaca" in args:
        oaxaca()
    if "--baseline" in args:
        baseline()
    if "--glmm" in args:
        glmm()
