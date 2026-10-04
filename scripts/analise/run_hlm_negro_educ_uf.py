"""
run_hlm_negro_educ_uf.py — penalidade racial por nível de escolaridade E por estado, com
efeitos aleatórios de UF (pedido do autor em 02/10/2026).

Desenho: HLM de dois estágios com variância conhecida ("V-known", Raudenbush & Bryk,
2002, cap. 7), a forma clássica de um modelo de inclinações aleatórias quando o ajuste
conjunto não cabe na memória (5 inclinações aleatórias por UF sobre 7,7 milhões de linhas).

  Estágio 1 — em cada UF: especificação do M3 do núcleo, com efeitos fixos de UPA no lugar
    do intercepto aleatório (o contexto da UPA e a UF ficam absorvidos), e o coeficiente de
    raça livre em cada nível: negro:C(nivel). Erro-padrão agrupado por UPA.
  Estágio 2 — em cada nível: modelo de efeitos aleatórios entre os 27 estados
    (DerSimonian-Laird): b_uf = mu + u_uf + e_uf, u_uf ~ N(0, tau2), e_uf ~ N(0, se_uf^2).
    O BLUP (Bayes empírico) de cada UF encolhe a estimativa em direção a mu na proporção
    lambda = tau2 / (tau2 + se^2): UFs pequenas e ruidosas não aparecem como extremas.

População completa, sem amostragem (regra do projeto).

Saídas:
    outputs/tables/hlm_negro_educ_uf.csv        (UF × nível: b, se, BLUP, IC, lambda)
    outputs/tables/hlm_negro_educ_uf_tau.csv    (por nível: mu, tau, I², Q)
    outputs/figures/hlm_negro_educ_uf.png
"""
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
_sys.path.insert(0, str(_Path(__file__).resolve().parent))

import gc
import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm

import run_hlm_stepup as H
from run_hlm_negro_por_educ import NIVEIS, nivel
from src.figuras_ptbr import virgula_decimal

sys.stdout.reconfigure(encoding="utf-8")
log = H.logger

SIGLA = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO", 21: "MA",
         22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA",
         31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR", 42: "SC", 43: "RS", 50: "MS",
         51: "MT", 52: "GO", 53: "DF"}
CONTROLES = ["sexo_fem", "idade_c", "idade_sq", "educ_fund_completo", "educ_medio_completo",
             "educ_superior_completo", "educ_pos_graduacao", "log_horas", "urbano"]


def estagio1(d: pd.DataFrame) -> pd.DataFrame:
    """OLS within-UPA numa UF; devolve b e se (cluster UPA) da penalidade por nível."""
    niv = [k for k, _ in NIVEIS]
    X = pd.DataFrame({f"negro_{k}": ((d["nivel"] == k) & (d["negro"] == 1)).astype(float)
                      for k in niv})
    for c in CONTROLES:
        X[c] = d[c].astype(float)
    anos = pd.get_dummies(d["Ano"], prefix="ano", drop_first=True, dtype=float)
    X = pd.concat([X, anos], axis=1)
    y = d["log_renda"].astype(float)
    g = d["UPA"].values
    # efeitos fixos de UPA por desvio da média do grupo
    Xd = X - X.groupby(g).transform("mean")
    yd = y - y.groupby(g).transform("mean")
    keep = Xd.columns[Xd.abs().sum() > 0]
    res = sm.OLS(yd.values, Xd[keep].values).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(g)[0]})
    idx = {c: i for i, c in enumerate(keep)}
    linhas = []
    for k in niv:
        c = f"negro_{k}"
        n_neg = int(X[c].sum())
        if c in idx and n_neg >= 30:
            linhas.append({"nivel": k, "b": float(res.params[idx[c]]),
                           "se": float(res.bse[idx[c]]), "n_negros": n_neg,
                           "n": int((d["nivel"] == k).sum())})
        else:
            linhas.append({"nivel": k, "b": np.nan, "se": np.nan, "n_negros": n_neg,
                           "n": int((d["nivel"] == k).sum())})
    return pd.DataFrame(linhas)


def dersimonian_laird(b: np.ndarray, se: np.ndarray) -> dict:
    w = 1 / se ** 2
    mu_fe = np.sum(w * b) / np.sum(w)
    Q = float(np.sum(w * (b - mu_fe) ** 2))
    k = len(b)
    c = np.sum(w) - np.sum(w ** 2) / np.sum(w)
    tau2 = max(0.0, (Q - (k - 1)) / c)
    w_re = 1 / (se ** 2 + tau2)
    mu = float(np.sum(w_re * b) / np.sum(w_re))
    lam = tau2 / (tau2 + se ** 2)
    blup = mu + lam * (b - mu)
    se_blup = np.sqrt(lam * se ** 2 + (1 - lam) ** 2 / np.sum(w_re))
    I2 = max(0.0, (Q - (k - 1)) / Q) * 100 if Q > 0 else 0.0
    return {"mu": mu, "tau2": tau2, "Q": Q, "I2": I2, "lam": lam, "blup": blup, "se_blup": se_blup}


def nacional(df: pd.DataFrame) -> int:
    """--nacional: a mesma comparação within-UPA do estágio 1, no país inteiro (os efeitos
    fixos de UPA absorvem a UF). Põe lado a lado, na mesma base, a penalidade entre vizinhos
    e a do HLM de efeitos aleatórios (run_hlm_negro_por_educ.py), que também usa a variação
    entre bairros."""
    e = estagio1(df)
    e["gap_pct"] = (np.exp(e["b"]) - 1) * 100
    e["ci_lo"], e["ci_hi"] = e["b"] - 1.96 * e["se"], e["b"] + 1.96 * e["se"]
    e.to_csv(H.TABLES / "hlm_negro_por_educ_fe.csv", index=False, encoding="utf-8")
    log.info("within-UPA nacional:\n" + e[["nivel", "b", "se", "gap_pct"]].round(4).to_string(index=False))
    return 0


def main() -> int:
    df = H.load_data(H.SAMPLE_FRAC)
    df["nivel"] = nivel(df)
    if "--nacional" in sys.argv:
        return nacional(df)
    blocos = []
    for uf, d in df.groupby("UF", sort=True):
        e = estagio1(d)
        e.insert(0, "UF", int(uf))
        blocos.append(e)
        log.info(f"UF {SIGLA.get(int(uf), uf)}: n={len(d):,} | "
                 + " ".join(f"{r.nivel}={r.b:+.3f}" for r in e.itertuples()))
        del d
        gc.collect()
    est = pd.concat(blocos, ignore_index=True)
    est["sigla"] = est["UF"].map(SIGLA)

    taus = []
    for k, rot in NIVEIS:
        m = (est["nivel"] == k) & est["b"].notna()
        r = dersimonian_laird(est.loc[m, "b"].values, est.loc[m, "se"].values)
        est.loc[m, "lambda"] = r["lam"]
        est.loc[m, "blup"] = r["blup"]
        est.loc[m, "se_blup"] = r["se_blup"]
        taus.append({"nivel": k, "rotulo": rot, "mu": r["mu"], "tau": np.sqrt(r["tau2"]),
                     "I2": r["I2"], "Q": r["Q"], "n_uf": int(m.sum()),
                     "gap_mu_pct": abs((np.exp(r["mu"]) - 1) * 100),
                     "nota_mu": "média entre estados (DerSimonian-Laird), não média do país"})
        log.info(f"[{k}] mu={r['mu']:+.4f} tau={np.sqrt(r['tau2']):.4f} I2={r['I2']:.0f}%")
    est["gap_blup_pct"] = (np.exp(est["blup"]) - 1) * 100
    est["ci_lo"] = est["blup"] - 1.96 * est["se_blup"]
    est["ci_hi"] = est["blup"] + 1.96 * est["se_blup"]
    tau = pd.DataFrame(taus)
    est.to_csv(H.TABLES / "hlm_negro_educ_uf.csv", index=False, encoding="utf-8")
    tau.to_csv(H.TABLES / "hlm_negro_educ_uf_tau.csv", index=False, encoding="utf-8")
    figura(est, tau)
    return 0


def figura(est: pd.DataFrame, tau: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm, Normalize

    niv = [k for k, _ in NIVEIS]
    rot = dict(NIVEIS)
    # penalidade em % positiva; estados ordenados pela penalidade média nos 5 níveis
    m = est.pivot(index="sigla", columns="nivel", values="gap_blup_pct")[niv] * -1
    m = m.loc[m.mean(axis=1).sort_values(ascending=False).index]
    vmax = np.nanmax(np.abs(m.values))
    if np.nanmin(m.values) < 0:          # algum estado com vantagem: escala divergente
        cmap = LinearSegmentedColormap.from_list("div", ["#B2182B", "#F7F7F7", "#2166AC"])
        norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    else:
        cmap = LinearSegmentedColormap.from_list("seq", ["#F1F6FC", "#0D47A1"])
        norm = Normalize(vmin=np.nanmin(m.values), vmax=vmax)   # contraste na faixa observada

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 9.5), width_ratios=[4, 1.25])
    ax.imshow(m.values, aspect="auto", cmap=cmap, norm=norm)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m.values[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7.5,
                        color="white" if norm(v) > 0.6 else "#212121")
    ax.set_xticks(range(len(niv)))
    ax.set_xticklabels([rot[k].replace(" completo", "\ncompleto") for k in niv], fontsize=8.5)
    ax.set_yticks(range(m.shape[0]))
    ax.set_yticklabels(m.index, fontsize=8.5)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Penalidade racial por estado e nível (%, BLUP)", fontsize=10, loc="left")

    # painel direito: média nacional e desvio-padrão entre estados (tau) por nível
    t = tau.set_index("nivel").loc[niv]
    y = np.arange(len(niv))[::-1]
    mu = t["gap_mu_pct"].values
    sd = (np.exp(t["tau"].values) - 1) * 100
    ax2.hlines(y, mu - sd, mu + sd, color="#1565C0", lw=3, alpha=0.5)
    ax2.plot(mu, y, "o", color="#0D47A1")
    for yi, a, b in zip(y, mu, sd):
        ax2.text(a, yi + 0.25, f"{a:.1f} ± {b:.1f}", ha="center", fontsize=8)
    ax2.set_yticks(y)
    ax2.set_yticklabels([rot[k] for k in niv], fontsize=8)
    ax2.set_ylim(-0.6, len(niv) - 0.3)
    ax2.set_title("Média entre estados ± τ (%)\ncada estado com peso\nquase igual", fontsize=9, loc="left")
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.suptitle("Penalidade racial por estado e nível de escolaridade",
                 x=0.02, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.02, 0.945, "Estimativas por estado encolhidas para a média entre estados (efeitos "
             "aleatórios de UF, DerSimonian-Laird) — não é a média do país, em que cada pessoa "
             "pesa igual; estados ordenados pela penalidade média.",
             fontsize=8.5, color="#616161")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    virgula_decimal(fig)
    fig.savefig(H.FIGURES / "hlm_negro_educ_uf.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("figura: outputs/figures/hlm_negro_educ_uf.png")


if __name__ == "__main__":
    sys.exit(main())
