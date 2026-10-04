"""
gerar_figuras_nucleo.py
=======================
Uma figura por método do núcleo (TODO_revisao, item 7.3), lidas dos csv já estimados
— não reestima nada. Seguem as regras de Knaflic: cinza + uma cor de destaque (azul),
sem gridlines supérfluas, rótulos diretos em vez de legenda, base zero nas barras,
título de ação afirmando o achado.

  fig_hlm_gap.png    barras horizontais de beta_negro (agregado -> M1 -> M2 -> M3 -> M4) com IC 95%
  fig_ob_cascata.png cascata do gap: dotações e não explicado nas duas especificações
  fig_qr_rif.png     beta(tau) com IC (esq.) e composição dotações/retornos por quantil (dir.)
  fig_glmm_or.png    OR com IC 95% dos três desfechos, por degrau

Uso: python tcc/scripts/gerar_figuras_nucleo.py
"""

# --- bootstrap raiz do projeto ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

T = _Path("outputs/tables")
F = _Path("outputs/figures")
F.mkdir(parents=True, exist_ok=True)

CINZA, CINZA_CLARO, TEXTO = "#9E9E9E", "#D6D6D6", "#212121"
AZUL, AZUL_CLARO = "#1565C0", "#90CAF9"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#BDBDBD", "axes.labelcolor": TEXTO,
                     "text.color": TEXTO, "xtick.color": "#616161", "ytick.color": "#616161",
                     "figure.facecolor": "white", "axes.facecolor": "white"})


def _limpa(ax, x=True, y=False):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if not x:
        ax.spines["bottom"].set_visible(False)
    if not y:
        ax.spines["left"].set_visible(False)


def _titulo(fig, achado, detalhe=None):
    fig.suptitle(achado, fontsize=13, fontweight="bold", color=TEXTO, x=0.01, ha="left", y=0.99)
    if detalhe:
        fig.text(0.01, 0.925, detalhe, fontsize=9.5, color="#616161", ha="left")


# ── 1. HLM: onde o gap encolhe ────────────────────────────────────────────────
def fig_hlm():
    gap = pd.read_csv(T / "gap_decomposicao_stepup.csv").set_index("Modelo")
    se = pd.read_csv(T / "hlm_serie_completo_se.csv")
    pool = se[(se["modelo"] == "M1_Individual_OLS") & (se["variavel"] == "negro")].iloc[0]
    linhas = [("Sem efeito de bairro\n(individual + UF)", float(pool["coef"]),
               float(pool["coef"]) - 1.96 * float(pool["se_cl_upa"]),
               float(pool["coef"]) + 1.96 * float(pool["se_cl_upa"]))]
    rot = {"M1": "M1: comparando dentro\ndo mesmo bairro", "M2": "M2: + contexto do bairro",
           "M3": "M3: + estado (gap líquido)", "M4": "M4: + ocupação\n(limite inferior)"}
    for m in ("M1", "M2", "M3", "M4"):
        r = gap.loc[m]
        linhas.append((rot[m], r["b_negro"], r["ci_lo"], r["ci_hi"]))

    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ys = np.arange(len(linhas))[::-1]
    for (lab, b, lo, hi), y in zip(linhas, ys):
        cor = AZUL if lab.startswith("M3") else CINZA
        ax.barh(y, b, color=cor, height=0.62, zorder=2)
        ax.plot([lo, hi], [y, y], color=TEXTO, lw=1.2, zorder=3)
        pct = (np.exp(b) - 1) * 100
        ax.text(b + 0.006, y, f"{pct:.1f}%".replace(".", ","), va="center", ha="left",
                color="white", fontsize=10.5, fontweight="bold", zorder=4)
    ax.set_yticks(ys); ax.set_yticklabels([l for l, *_ in linhas], fontsize=9.5)
    ax.axvline(0, color=TEXTO, lw=0.8)
    ax.set_xlabel("Penalidade racial no log-rendimento (barras) e IC 95% (traço)")
    ax.set_xlim(min(b for _, b, *_ in linhas) * 1.18, 0.012)
    ax.set_xticks([])
    _limpa(ax)
    from params_nucleo import P as _PN, titulo_bairro
    _titulo(fig, titulo_bairro(_PN),
            "…mas o que sobra não é explicado por escolaridade, idade, sexo, estado nem ocupação.")
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(F / "fig_hlm_gap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── 2. Oaxaca-Blinder: cascata nas duas especificações ────────────────────────
def fig_ob():
    ob = pd.read_csv(T / "ob_acesso.csv").set_index("espec")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, (esp, titulo) in zip(axes, [("sem_ocupacao", "(A) Sem ocupação\n(controles do M3)"),
                                        ("acesso", "(B) Com ocupação como dotação\n(limite inferior)")]):
        r = ob.loc[esp]
        gap, dot, coef = r["gap_total"], r["ef_dotacao"], r["ef_coeficiente"]
        ax.bar(0, gap, color=CINZA, width=0.62, zorder=2)
        ax.bar(1, dot, bottom=gap - dot, color=CINZA_CLARO, width=0.62, zorder=2)
        ax.bar(2, coef, color=AZUL, width=0.62, zorder=2)
        ax.plot([0.31, 0.69], [gap, gap], color="#757575", lw=0.9, ls=":")
        ax.plot([1.31, 1.69], [gap - dot, gap - dot], color="#757575", lw=0.9, ls=":")
        ax.text(0, gap + 0.012, f"{gap:.3f}".replace(".", ","), ha="center", fontsize=10, fontweight="bold")
        ax.text(1, gap + 0.012, f"−{dot:.3f}".replace(".", ","), ha="center", fontsize=10,
                color="#616161")
        ax.text(2, coef + 0.012, f"{coef:.3f}".replace(".", ",") + f"\n({r['pct_coeficiente']:.0f}% do gap)",
                ha="center", fontsize=10, fontweight="bold", color=AZUL)
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["Gap total", "− dotações\n(características)", "= não explicado"], fontsize=9.5)
        ax.set_title(titulo, fontsize=10, color="#424242")
        ax.set_ylim(0, gap * 1.28)
        ax.set_yticks([])
        _limpa(ax)
    axes[0].set_ylabel("Diferença de log-rendimento (branco − negro)")
    _titulo(fig, "Tratar a ocupação como \"característica\" derruba a discriminação medida pela metade",
            "A parcela que some é justamente a que opera na porta de entrada das ocupações.")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(F / "fig_ob_cascata.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── 3. QR e RIF: condicional vs incondicional ─────────────────────────────────
def fig_qr_rif():
    qr = pd.read_csv(T / "qr_melhorias.csv")
    g = qr[qr["grupo"] == "Global"].sort_values("quantil")
    rif = pd.read_csv(T / "rif_ob_decomposicao.csv")
    rif["dot"] = rif["end"] / rif["gap_rif"] * 100
    rif["ret"] = rif["ret"] / rif["gap_rif"] * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.4))
    x = g["quantil"] * 100
    ax1.fill_between(x, g["ci_lo"] * 100, g["ci_hi"] * 100, color=AZUL_CLARO, alpha=0.45, zorder=2)
    ax1.plot(x, g["b_negro"] * 100, color=AZUL, lw=2.2, marker="o", ms=5, zorder=3)
    # rótulos no q10 e no q90 — o "topo" do texto é o q90 (o teste Z compara q90 × q10);
    # o τ = 0,95 aparece na curva, mas não é o número citado
    _q90 = g[g["quantil"].round(2) == 0.90].iloc[0]
    for xi, yi in [(x.iloc[0], g["b_negro"].iloc[0] * 100), (_q90["quantil"] * 100, _q90["b_negro"] * 100)]:
        # q10: abaixo e à direita do ponto (à esquerda bateria no eixo y); q90: abaixo e à
        # esquerda, sob a curva (acima cruzava a linha, que desce rumo ao topo)
        ax1.annotate(f"{yi:.1f}".replace(".", ",").replace("-", "−") + " log-pontos", (xi, yi),
                     textcoords="offset points",
                     xytext=(34, -16) if xi < 50 else (-10, -18),
                     ha="center" if xi < 50 else "right", fontsize=9.5, color=AZUL,
                     fontweight="bold")
    ax1.set_xlabel("Quantil condicional da renda (τ)")
    ax1.set_ylabel("Penalidade racial (×100)")
    ax1.set_title("Regressão quantílica: a penalidade condicional cresce no topo",
                  fontsize=10, color="#424242")
    ax1.axhline(0, color=TEXTO, lw=0.8)
    _limpa(ax1, y=True)

    ax2.bar(range(len(rif)), rif["dot"], color=CINZA_CLARO, width=0.62, label="Dotações")
    ax2.bar(range(len(rif)), rif["ret"], bottom=rif["dot"], color=AZUL, width=0.62, label="Não explicado")
    for i, r in rif.reset_index().iterrows():
        ax2.text(i, r["dot"] + r["ret"] / 2, f"{r['ret']:.0f}%", ha="center", va="center",
                 color="white", fontsize=10, fontweight="bold")
    ax2.set_xticks(range(len(rif))); ax2.set_xticklabels(rif["q_label"])
    ax2.set_xlabel("Quantil incondicional da renda")
    ax2.set_ylim(0, 100); ax2.set_yticks([])
    ax2.set_title("RIF-OB: a parcela não explicada é maior na base", fontsize=10, color="#424242")
    ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False, fontsize=9,
               handlelength=1.2)
    _limpa(ax2)
    _titulo(fig, "Teto de vidro entre pares, piso pegajoso na renda do país: duas perguntas, dois padrões",
            "À esquerda, quantis condicionais (dispersão maior no topo); à direita, quantis "
            "incondicionais da renda do país.")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(F / "fig_qr_rif.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# ── 4. GLMM: odds ratios de acesso ────────────────────────────────────────────
def fig_glmm():
    g = pd.read_csv(T / "glmm_glassceil_glmer.csv")
    desf = [("ocp_qualif", "Cargo qualificado\n(CBO 1–4)"), ("y_top20", "Top 20% de renda"),
            ("y_top10", "Top 10% de renda")]
    mods = [("M1", "individual"), ("M2", "+ bairro"), ("M3", "+ vínculo")]
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    ypos, labels = [], []
    y = 0
    for d, dlab in desf:
        for m, mlab in mods:
            r = g[(g["desfecho"] == d) & (g["modelo"] == m)].iloc[0]
            cor = AZUL if (m == "M2") else CINZA
            ax.plot([r["CI95_lo"], r["CI95_hi"]], [y, y], color="#BDBDBD", lw=1.6, zorder=2)
            ax.scatter(r["OR_negro"], y, color=cor, s=46, zorder=3)
            if m == "M2":
                ax.annotate(f"{r['OR_negro']:.3f}".replace(".", ","), (r["OR_negro"], y),
                            textcoords="offset points", xytext=(11, -3), ha="left",
                            fontsize=9.5, color=AZUL, fontweight="bold")
            ypos.append(y); labels.append(f"{dlab} — {mlab}" if m == "M1" else mlab)
            y -= 1
        y -= 0.5
    ax.axvline(1, color=TEXTO, lw=0.9, ls="--")
    ax.text(0.995, max(ypos) + 0.55, "paridade", fontsize=9, color="#616161", ha="right")
    ax.set_yticks(ypos); ax.set_yticklabels(labels, fontsize=9.5)
    ax.set_xlabel("Razão de chances de acesso (negro vs. branco do mesmo bairro), IC 95%")
    ax.set_xlim(0.42, 1.05)
    # vírgula decimal no eixo, como no texto (o padrão do matplotlib é ponto)
    from matplotlib.ticker import FuncFormatter
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ",")))
    _limpa(ax)
    _titulo(fig, "A porta é mais estreita para negros — e estreita ainda mais no topo da renda",
            "GLMM com intercepto aleatório de UPA; em azul, o modelo com contexto de bairro (A2).")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(F / "fig_glmm_or.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_hlm(); print("OK -> fig_hlm_gap.png")
    fig_ob(); print("OK -> fig_ob_cascata.png")
    fig_qr_rif(); print("OK -> fig_qr_rif.png")
    fig_glmm(); print("OK -> fig_glmm_or.png")
