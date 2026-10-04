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

E2.16 (03/10/2026): painel à direita com o mesmo GLMM por grande grupo CBO
(grupo_rg_por_cbo.csv, scripts/R/run_grupo_rg_por_cbo.R). O OR agregado da mulher negra
em CBO 1–4 junta portas diferentes: ela entra mais no apoio administrativo e nas profissões
de ensino e saúde (feminizadas) e é o grupo com menor chance entre os dirigentes.

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

CSV_CBO = ROOT / "outputs" / "tables" / "grupo_rg_por_cbo.csv"
_tem_cbo = CSV_CBO.exists()
if _tem_cbo:
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13, 5.0),
                                  gridspec_kw={"width_ratios": [1.3, 1], "wspace": 0.42})
else:
    fig, ax = plt.subplots(figsize=(8, 4.8))
ax.axhline(1, color=CINZA_ESCURO, lw=1, ls="--", zorder=1)
ax.text(len(d) - 1 + 0.08, 1, "Homem branco\n(referência = 1)", va="center", ha="left",
        fontsize=9, color=CINZA_ESCURO)

rotulos = []
for col, nome, cor, mk, lw, z in grupos:
    y = d[col].values
    ax.plot(x, y, color=cor, lw=lw, marker=mk, ms=7, zorder=z,
            markeredgecolor="white", markeredgewidth=1)
    # rótulo direto no fim da linha: identifica o grupo sem depender da cor
    rotulos.append([float(y[-1]), f"{nome} ({virgula(y[-1])})", cor == AZUL])

# a história da mulher negra: valor no acesso, onde ela está acima do homem branco
mn = d["OR_mulher_negra"].values
ax.annotate(f"{virgula(mn[0])}: acima do homem branco no\nagregado (ver à direita)" if _tem_cbo
            else f"{virgula(mn[0])}: acima do homem branco\nno acesso à categoria",
            xy=(0, mn[0]), xytext=(0.42, 1.18) if _tem_cbo else (0.22, 1.62), fontsize=9, color=AZUL,
            arrowprops=dict(arrowstyle="-", color=AZUL, lw=0.8))

# rótulos da direita afastados em escala log (mínimo de ~9% entre vizinhos) e longe da
# linha de referência
import numpy as _np
rotulos.sort(key=lambda r: r[0])
pos = []
for v, _, _ in rotulos:
    p_ = v if not pos else max(v, pos[-1] * 1.09)
    pos.append(p_)
for (v, txt, destaque), p_ in zip(rotulos, pos):
    ax.text(len(d) - 1 + 0.08, p_, txt, va="center", ha="left", fontsize=9, color=TEXTO,
            fontweight="bold" if destaque else "normal")

ax.set_yscale("log")
_vals = d[[g[0] for g in grupos]].values
y_lo, y_hi = float(_np.nanmin(_vals)) * 0.85, max(float(_np.nanmax(_vals)) * 1.12, 1.15)
ticks = [v for v in (0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0) if y_lo <= v <= y_hi]
ax.yaxis.set_major_locator(FixedLocator(ticks))
ax.yaxis.set_minor_locator(NullLocator())
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: virgula(v, 1)))
ax.set_ylim(y_lo, y_hi)
ax.set_xlim(-0.25, len(d) - 1 + 0.9)
ax.set_xticks(list(x), rotulos_x)
ax.set_ylabel("Razão de chances vs. homem branco (escala log)")
for lado in ("top", "right"):
    ax.spines[lado].set_visible(False)
ax.grid(axis="y", color="#EEEEEE", lw=0.8, zorder=0)

if _tem_cbo:
    # painel direito: os mesmos 4 grupos, um ponto por grande grupo CBO (escala log)
    c = pd.read_csv(CSV_CBO).set_index("desfecho")
    cats = [("y_dirigente", "Dirigentes (1)"), ("y_profissional", "Profissionais (2)"),
            ("y_tecnico", "Técnicos (3)"), ("y_administrativo", "Apoio\nadministrativo (4)")]
    cats = [(k, r) for k, r in cats if k in c.index]
    yy = list(range(len(cats)))[::-1]
    ax2.axvline(1, color=CINZA_ESCURO, lw=1, ls="--", zorder=1)
    for col, nome, cor, mk, lw, z in grupos:
        v = [float(c.loc[k, col]) for k, _ in cats]
        ax2.scatter(v, yy, color=cor, marker=mk, s=70 if cor == AZUL else 45, zorder=z,
                    edgecolor="white", linewidth=1, label=nome)
    for (k, _), y_ in zip(cats, yy):
        v = float(c.loc[k, "OR_mulher_negra"])
        ax2.annotate(virgula(v), (v, y_), xytext=(0, 9), textcoords="offset points",
                     ha="center", fontsize=9, color=AZUL, fontweight="bold")
    ax2.set_xscale("log")
    _v2 = c.loc[[k for k, _ in cats], [g[0] for g in grupos]].values
    x_lo, x_hi = float(_np.nanmin(_v2)) * 0.85, float(_np.nanmax(_v2)) * 1.15
    ax2.xaxis.set_major_locator(FixedLocator(
        [v for v in (0.5, 0.7, 1.0, 1.5, 2.0, 3.0) if x_lo <= v <= x_hi]))
    ax2.xaxis.set_minor_locator(NullLocator())
    ax2.xaxis.set_major_formatter(FuncFormatter(lambda v, _: virgula(v, 1)))
    ax2.set_xlim(x_lo, x_hi)
    ax2.set_yticks(yy, [r for _, r in cats])
    ax2.set_ylim(-0.6, len(cats) - 0.4)
    ax2.set_xlabel("Razão de chances vs. homem branco (escala log)")
    ax2.set_title("Acesso por grande grupo CBO", fontsize=10.5, color=TEXTO, loc="left")
    for lado in ("top", "right"):
        ax2.spines[lado].set_visible(False)
    ax2.grid(axis="x", color="#EEEEEE", lw=0.8, zorder=0)
    ax2.legend(loc="upper right", fontsize=8.5, frameon=False, handletextpad=0.3)
    ax.set_title("Três desfechos (CBO 1–4 agregado)", fontsize=10.5, color=TEXTO, loc="left")

fig.suptitle(("A mulher negra entra pelas ocupações feminizadas, mas não chega ao comando nem ao topo"
              if _tem_cbo else "A mulher negra entra na categoria, mas não chega ao topo"),
             fontsize=13, fontweight="bold", x=0.01, ha="left", y=0.99)
fig.text(0.01, 0.925, ("À esquerda, três desfechos; à direita, o acesso separado por grande grupo CBO. "
                       "Abaixo de 1 = desvantagem" if _tem_cbo else
                       "Razões de chance dos grupos raça×gênero em três desfechos; abaixo de 1 = desvantagem"),
         fontsize=9.5, color=CINZA_ESCURO, ha="left")
fig.text(0.01, 0.01, "GLMM logístico negro×sexo + controles + (1 | UPA). "
         "PNAD Contínua 2016–2025, população completa.", fontsize=8, color=CINZA, ha="left")
fig.tight_layout(rect=(0, 0.03, 1, 0.9))
fig.savefig(OUT, dpi=200)
print(f"OK -> {OUT.relative_to(ROOT)}")
