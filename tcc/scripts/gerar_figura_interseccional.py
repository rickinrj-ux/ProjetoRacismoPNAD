"""
gerar_figura_interseccional.py — Figura fig:interseccional do TCC.

Razões de chance dos grupos raça×gênero contra o homem branco nos três desfechos
do GLMM (acesso à ocupação qualificada, top 20% e top 10% da renda), lidas de
outputs/tables/grupo_rg_4grupos_desfechos.csv (scripts/R/run_grupo_rg_topo.R).

A figura existia desde junho sem gerador: foi feita à mão e não acompanhou a
reestimação leave-one-out. Este script a torna reprodutível.

Estilo das figuras do núcleo (gerar_figuras_nucleo.py): cinza + uma cor de
destaque, título de ação. A mulher negra é a protagonista (azul); os outros grupos
ficam em cinza e se distinguem por marcador e rótulo direto, não só pela cor
— a figura sobrevive à impressão em preto e branco.

Saída: outputs/figures/grupo_rg_interseccional.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "outputs" / "tables" / "grupo_rg_4grupos_desfechos.csv"
OUT = ROOT / "outputs" / "figures" / "grupo_rg_interseccional.png"

CINZA, CINZA_ESCURO, TEXTO = "#9E9E9E", "#616161", "#212121"
AZUL = "#1565C0"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#BDBDBD", "axes.labelcolor": TEXTO,
                     "text.color": TEXTO, "xtick.color": CINZA_ESCURO, "ytick.color": CINZA_ESCURO,
                     "figure.facecolor": "white", "axes.facecolor": "white"})


def virgula(x, casas=2):
    return f"{x:.{casas}f}".replace(".", ",")


d = pd.read_csv(CSV).set_index("desfecho").loc[["ocp_qualif", "y_top20", "y_top10"]]
rotulos_x = ["Acesso\n(CBO 1–4)", "Top 20%\nda renda", "Top 10%\nda renda"]
x = range(len(d))

# (coluna, nome, cor, marcador, espessura, z)
grupos = [
    ("OR_mulher_branca", "Mulher branca", CINZA, "s", 1.6, 2),
    ("OR_homem_negro", "Homem negro", CINZA_ESCURO, "^", 1.6, 2),
    ("OR_mulher_negra", "Mulher negra", AZUL, "D", 2.6, 3),
]

fig, ax = plt.subplots(figsize=(8, 4.8))
ax.axhline(1, color=CINZA_ESCURO, lw=1, ls="--", zorder=1)
ax.text(len(d) - 1 + 0.08, 1, "Homem branco\n(referência = 1)", va="center", ha="left",
        fontsize=9, color=CINZA_ESCURO)

for col, nome, cor, mk, lw, z in grupos:
    y = d[col].values
    ax.plot(x, y, color=cor, lw=lw, marker=mk, ms=7, zorder=z,
            markeredgecolor="white", markeredgewidth=1)
    # rótulo direto no fim da linha: identifica o grupo sem depender da cor
    ax.text(len(d) - 1 + 0.08, y[-1], f"{nome} ({virgula(y[-1])})", va="center", ha="left",
            fontsize=9, color=TEXTO, fontweight="bold" if cor == AZUL else "normal")

# a história da mulher negra: valor no acesso, onde ela está acima do homem branco
mn = d["OR_mulher_negra"].values
ax.annotate(f"{virgula(mn[0])}: acima do homem branco\nno acesso à categoria",
            xy=(0, mn[0]), xytext=(0.22, 1.62), fontsize=9, color=AZUL,
            arrowprops=dict(arrowstyle="-", color=AZUL, lw=0.8))

ax.set_yscale("log")
ticks = [0.3, 0.4, 0.5, 0.7, 1.0, 1.5, 2.0]
ax.yaxis.set_major_locator(FixedLocator(ticks))
ax.yaxis.set_minor_locator(NullLocator())
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: virgula(v, 1)))
ax.set_ylim(0.3, 2.1)
ax.set_xlim(-0.25, len(d) - 1 + 0.9)
ax.set_xticks(list(x), rotulos_x)
ax.set_ylabel("Razão de chances vs. homem branco (escala log)")
for lado in ("top", "right"):
    ax.spines[lado].set_visible(False)
ax.grid(axis="y", color="#EEEEEE", lw=0.8, zorder=0)

fig.suptitle("A mulher negra entra na categoria, mas não chega ao topo",
             fontsize=13, fontweight="bold", x=0.01, ha="left", y=0.99)
fig.text(0.01, 0.925, "Razões de chance dos grupos raça×gênero em três desfechos; abaixo de 1 = desvantagem",
         fontsize=9.5, color=CINZA_ESCURO, ha="left")
fig.text(0.01, 0.01, "GLMM logístico negro×sexo + controles + (1 | UPA). "
         "PNAD Contínua 2016–2025, população completa.", fontsize=8, color=CINZA, ha="left")
fig.tight_layout(rect=(0, 0.03, 1, 0.9))
fig.savefig(OUT, dpi=200)
print(f"OK -> {OUT.relative_to(ROOT)}")
