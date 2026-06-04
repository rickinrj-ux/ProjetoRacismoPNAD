"""
run_mapa_po_regional.py
=======================
Mapa de calor (tile-grid / cartograma) do Brasil com a penalidade racial salarial
por UF — base oficial: BLUP do MixedLM (po_regional_gaps_uf.csv).

POR QUE TILE-GRID (e não choropleth geográfico):
  geopandas/shapely/contornos não estão disponíveis no ambiente. O tile-grid
  (cada UF = um quadrado na posição geográfica aproximada) é livre de dependências,
  visualmente limpo e didático para banca e público — cada estado tem o MESMO
  tamanho, evitando que estados grandes (AM) dominem visualmente a leitura, o que
  é desejável aqui: o foco é a INTENSIDADE da penalidade, não a área territorial.

SAÍDA:
  outputs/figures/mapa_po_regional.png

Dados: outputs/tables/po_regional_gaps_uf.csv (gap_blup_pct por UF) + params.RPO_*.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from params import P

ROOT    = Path(__file__).parent
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TAB = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)

# Grade geográfica aproximada do Brasil (coluna, linha) — linha 1 = Norte (topo)
GRID = {
    "RR": (3, 1), "AP": (4, 1),
    "AM": (2, 2), "PA": (3, 2), "MA": (4, 2), "CE": (5, 2), "RN": (6, 2),
    "AC": (1, 3), "RO": (2, 3), "TO": (3, 3), "PI": (4, 3), "PE": (5, 3), "PB": (6, 3),
    "MT": (2, 4), "GO": (3, 4), "BA": (4, 4), "AL": (5, 4), "SE": (6, 4),
    "MS": (2, 5), "DF": (3, 5), "MG": (4, 5), "ES": (5, 5),
    "SP": (3, 6), "RJ": (4, 6),
    "PR": (3, 7),
    "SC": (3, 8),
    "RS": (3, 9),
}


def main():
    df = pd.read_csv(OUT_TAB / "po_regional_gaps_uf.csv")
    gaps = dict(zip(df["sigla"], df["gap_blup_pct"]))     # negativo (penalidade)
    top5 = [s.strip() for s in str(P.get("RPO_TOP5", "")).split(",")]
    ganho_b9 = P.get("RPO_GANHO_B9", 68.2)

    mag = {s: abs(v) for s, v in gaps.items()}            # magnitude da penalidade
    # Escala DISCRETA por faixas de magnitude (pontos percentuais). Classificar cada
    # estado em sua faixa garante que a cor reflita inequivocamente a magnitude — evita
    # que estados de penalidade média (~11%) pareçam de baixa magnitude por compressão
    # causada pelos outliers (DF/AM ~21%). Estados de mesma faixa têm a mesma cor.
    bounds = [0, 5, 10, 15, 20, 25]
    cmap = plt.get_cmap("YlOrRd", len(bounds) - 1)        # 5 cores discretas claro→escuro
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    fig, ax = plt.subplots(figsize=(9.5, 10.5))
    cell, gap_pad = 1.0, 0.08

    for sigla, (col, row) in GRID.items():
        v = gaps.get(sigla)
        if v is None:
            continue
        x, y = col, -row
        color = cmap(norm(abs(v)))
        is_top = sigla in top5
        # quadrado do estado (cantos arredondados = lúdico)
        box = FancyBboxPatch(
            (x + gap_pad, y + gap_pad), cell - 2*gap_pad, cell - 2*gap_pad,
            boxstyle="round,pad=0.0,rounding_size=0.12",
            linewidth=3.2 if is_top else 0.8,
            edgecolor="#1A1A1A" if not is_top else "#1565C0",
            facecolor=color, zorder=2,
        )
        ax.add_patch(box)
        # texto: cor adaptativa ao fundo (faixas 15–20 e 20–25% = fundo escuro → branco)
        txt_color = "white" if norm(abs(v)) >= 3 else "#1A1A1A"
        ax.text(x + 0.5, y + 0.62, sigla, ha="center", va="center",
                fontsize=14, fontweight="bold", color=txt_color, zorder=3)
        ax.text(x + 0.5, y + 0.34, f"{v:.0f}%".replace("-", "−"),
                ha="center", va="center", fontsize=11, color=txt_color, zorder=3)
        if is_top:
            ax.text(x + 0.84, y + 0.86, "★", ha="center", va="center",
                    fontsize=11, color="#1565C0", zorder=4)

    # Limites com MARGEM: linha 1 (y=-1) e linha 9 (y=-9) inteiras dentro dos eixos
    ax.set_xlim(0.4, 7.0)
    ax.set_ylim(-10.05, 0.05)
    ax.set_aspect("equal")
    ax.axis("off")

    # Título e subtítulo em coordenadas de FIGURA (acima da grade — não sobrepõem)
    fig.suptitle("O Racismo Tem Endereço — Penalidade Racial Salarial por Estado",
                 fontsize=16, fontweight="bold", y=0.975)
    fig.text(0.5, 0.938,
             "Quanto um trabalhador negro ganha a menos que um branco idêntico, por UF "
             "(mais escuro = maior desvantagem)  |  ★ = estados prioritários",
             ha="center", fontsize=10.5, color="#444444")

    # Barra de cor
    sm = cm.ScalarMappable(norm=norm, cmap=cmap); sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.035, pad=0.02, aspect=28,
                        ticks=bounds, spacing="proportional")
    cbar.set_label("Magnitude da penalidade racial (% — faixas)", fontsize=10)
    cbar.ax.set_yticklabels([f"{b}%" for b in bounds])

    # Caixa de destaque (focalização)
    pior = df.iloc[0]; melhor = df.iloc[-1]
    nota = (f"Maior penalidade: {pior['sigla']} ({pior['gap_blup_pct']:.0f}%)   |   "
            f"menor: {melhor['sigla']} ({melhor['gap_blup_pct']:.0f}%)\n"
            f"Concentrar o orçamento nos estados ★ rende até +{ganho_b9:.0f}% "
            f"vs. distribuir por igual.")
    ax.text(0.5, 0.012, nota, transform=fig.transFigure, ha="center", va="bottom",
            fontsize=10.5, color="#1A1A1A",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFF8E7",
                      edgecolor="#FF8F00", linewidth=1.2))

    plt.subplots_adjust(top=0.90, bottom=0.085, left=0.02, right=0.92)
    out = OUT_FIG / "mapa_po_regional.png"
    plt.savefig(out, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"Mapa salvo: {out}")
    print(f"  UFs plotadas: {len(gaps)} | pior={pior['sigla']} ({pior['gap_blup_pct']:.1f}%) "
          f"| melhor={melhor['sigla']} ({melhor['gap_blup_pct']:.1f}%)")
    print(f"  Estados prioritários (★): {', '.join(top5)}")


if __name__ == "__main__":
    main()
