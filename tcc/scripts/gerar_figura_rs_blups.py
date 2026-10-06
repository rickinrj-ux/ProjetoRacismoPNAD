"""
gerar_figura_rs_blups.py — interceptos e inclinações aleatórios por bairro (M3_RS).

Figura no formato do Manual de Análise de Dados (Fávero & Belfiore, cap. de modelos
multinível): uma reta ajustada por grupo, com intercepto γ00 + u0j e inclinação
β_negro + u1j, e a dispersão dos BLUPs (u0j × u1j) que mostra a covariância entre o
nível de renda do bairro e a penalidade racial dentro dele.

Os BLUPs são calculados de forma exata a partir do M3_RS já ajustado (cache do
run_hlm_stepup.py: 50 efeitos fixos + G e σ²), sem reajustar o modelo:
    b_j = (Z_j'Z_j/σ² + G⁻¹)⁻¹ Z_j'(y_j − X_jβ)/σ²,   Z_j = [1, negro]
Com Z de duas colunas, basta somar por UPA n_j, Σnegro, Σr e Σr·negro.

Saídas: outputs/tables/hlm_m3_rs_blups.csv  ·  outputs/figures/hlm_rs_retas_upa.png
"""
import pickle
import sys
from pathlib import Path

import __main__
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys as _sys_n
from pathlib import Path as _Path_n
_sys_n.path.insert(0, str(_Path_n(__file__).resolve().parents[2] / "src"))
from figuras_ptbr import norma_manual  # manual MBA: sem título no gráfico, painéis A/B
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analise"))
import os
os.chdir(ROOT)
import run_hlm_stepup as H  # noqa: E402

__main__.Light = H.Light                     # o cache foi gravado com Light em __main__
L = pickle.load(open(ROOT / "outputs/_cache/hlm_stepup/M3_RS.pkl", "rb"))
beta, s2 = L.params, L.sigma2
G = np.array([[L.tau2, L.cov01], [L.cov01, L.tau2_slope]])
Ginv = np.linalg.inv(G)

# ── resíduo marginal r = y − Xβ (Xβ montado sem a matriz de 7,7 M × 50) ─────────
df = H.load_data(sample_frac=None)
xb = np.full(len(df), beta["Intercept"])
for k, v in beta.items():
    if k in df.columns:
        xb += v * df[k].astype(float).values
for nome, col in (("C(Ano)", "Ano"), ("C(UF_str)", "UF_str")):
    mapa = {k.split("[T.")[1].rstrip("]"): v for k, v in beta.items() if k.startswith(nome + "[T.")}
    xb += df[col].astype(str).map(mapa).fillna(0.0).values     # categoria de referência = 0
df["r"] = df["log_renda"].values - xb                            # inclui β_negro·negro
df["r_neg"] = df["r"] * df["negro"]
g = df.groupby("UPA_str").agg(n=("r", "size"), n1=("negro", "sum"), s0=("r", "sum"), s1=("r_neg", "sum"))
xb_branco = float(np.mean(xb - beta["negro"] * df["negro"].values))   # nível médio de referência
del df, xb

# ── BLUP por UPA: resolve o sistema 2×2 de cada bairro de uma vez ──────────────
a11 = g["n"] / s2 + Ginv[0, 0]
a12 = g["n1"] / s2 + Ginv[0, 1]
a22 = g["n1"] / s2 + Ginv[1, 1]
det = a11 * a22 - a12 ** 2
c0, c1 = g["s0"] / s2, g["s1"] / s2
g["u0"] = (a22 * c0 - a12 * c1) / det
g["u1"] = (-a12 * c0 + a11 * c1) / det
g.reset_index()[["UPA_str", "n", "n1", "u0", "u1"]].rename(columns={"UPA_str": "UPA", "n1": "n_negro"}) \
    .to_csv(ROOT / "outputs/tables/hlm_m3_rs_blups.csv", index=False)

r_cov = L.cov01 / np.sqrt(L.tau2 * L.tau2_slope)       # correlação estimada (G)
r_blup = float(np.corrcoef(g["u0"], g["u1"])[0, 1])   # entre os BLUPs (encolhidos)
b = float(beta["negro"])
sd1 = float(np.sqrt(L.tau2_slope))
print(f"UPAs: {len(g):,} | β_negro = {b:.4f} | DP inclinação = {sd1:.4f} | "
      f"corr(G) = {r_cov:.3f} | corr(BLUPs) = {r_blup:.3f}")

# ── figura ───────────────────────────────────────────────────────────────────
CINZA, CINZA_ESC, TEXTO, AZUL = "#BDBDBD", "#616161", "#212121", "#1565C0"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#BDBDBD", "axes.labelcolor": TEXTO,
                     "text.color": TEXTO, "xtick.color": CINZA_ESC, "ytick.color": CINZA_ESC,
                     "figure.facecolor": "white", "axes.facecolor": "white"})


def virg(x, d=2):
    return f"{x:.{d}f}".replace(".", ",").replace("-", "−")


fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw={"width_ratios": [1, 1.15]})

# (a) retas por bairro — amostra fixa de UPAs com brancos e negros (só para legibilidade)
mistas = g[(g["n1"] > 0) & (g["n1"] < g["n"])]
amostra = mistas.sample(n=min(250, len(mistas)), random_state=42)
# o tamanho da amostra vai para csv: a legenda do relatório o lê de lá (params_nucleo)
with open(ROOT / "outputs/tables/hlm_rs_figura.csv", "w", encoding="utf-8") as _f:
    _f.write(f"chave,valor\nHLM_RS_N_AMOSTRA,{len(amostra)}\n")
x = np.array([0, 1])
for _, row in amostra.iterrows():
    y = xb_branco + row["u0"] + (b + row["u1"]) * x
    ax1.plot(x, y, color=CINZA, lw=0.6, alpha=0.6, zorder=1)
ax1.plot(x, xb_branco + b * x, color=AZUL, lw=3, zorder=3)
ax1.text(1.03, xb_branco + b, f"média:\ninclinação {virg(b, 3)}", color=AZUL, fontsize=9,
         va="center", fontweight="bold")
ax1.set_xticks([0, 1], ["Branco", "Negro"])
ax1.set_xlim(-0.1, 1.45)
ax1.set_ylabel("log-rendimento ajustado (perfil médio)")
ax1.set_title(f"(a) Uma reta por bairro (amostra de {len(amostra)} UPAs)", fontsize=10, color=CINZA_ESC)

# (b) BLUPs: intercepto × inclinação, todas as UPAs
ax2.scatter(g["u0"], g["u1"], s=3, color=CINZA_ESC, alpha=0.15, linewidths=0, rasterized=True)
coef = np.polyfit(g["u0"], g["u1"], 1)
xs = np.linspace(g["u0"].quantile(0.005), g["u0"].quantile(0.995), 50)
ax2.plot(xs, np.polyval(coef, xs), color=AZUL, lw=2)
ax2.axhline(0, color=CINZA, lw=0.8)
ax2.axvline(0, color=CINZA, lw=0.8)
ax2.set_xlabel("$u_{0j}$: intercepto do bairro (nível de renda)")
ax2.set_ylabel("$u_{1j}$: desvio da inclinação de negro")
_n_upa = f"{len(g):,}".replace(",", ".")
ax2.set_title(f"(b) {_n_upa} bairros: correlação estimada de {virg(r_cov)}", fontsize=10, color=CINZA_ESC)
for lado in ("top", "right"):
    ax1.spines[lado].set_visible(False)
    ax2.spines[lado].set_visible(False)
from matplotlib.ticker import FuncFormatter   # vírgula decimal, como no resto do trabalho
_fmt = FuncFormatter(lambda v, _: virg(v, 2))
ax1.yaxis.set_major_formatter(_fmt)
ax2.xaxis.set_major_formatter(FuncFormatter(lambda v, _: virg(v, 1)))
ax2.yaxis.set_major_formatter(_fmt)

# título de ação condicionado ao sinal da covariância
acao = ("Nos bairros de renda mais alta, a penalidade racial é maior" if r_cov < 0 else
        "Nos bairros de renda mais alta, a penalidade racial é menor")
fig.suptitle(acao, fontsize=13, fontweight="bold", x=0.01, ha="left", y=0.99)
fig.text(0.01, 0.925, f"M3 com intercepto e inclinação de negro aleatórios por UPA (BLUPs); "
         f"a inclinação média é {virg(b, 3)} e varia com DP de {virg(sd1, 3)} entre bairros",
         fontsize=9.5, color=CINZA_ESC, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.92))
out = ROOT / "outputs/figures/hlm_rs_retas_upa.png"
norma_manual(fig)
fig.savefig(out, dpi=200)
print(f"OK -> {out.relative_to(ROOT)}")
