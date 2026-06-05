"""
run_po_regional.py
==================
Pesquisa Operacional REGIONALIZADA — alocação ótima de orçamento por UF.

BASE OFICIAL: BLUPs do MixedLM completo (run_blup_vs_eb.py)
-----------------------------------------------------------
O gap racial por UF é o BLUP do modelo misto M3 com random slope de `negro`
por UF (random intercept + random slope, ρ correlacionado), estimado na
população completa: gap_j = β̂_negro + û₁ⱼ.

DECISÃO METODOLÓGICA (2026-06-01): adotamos o BLUP MixedLM, e NÃO a aproximação
rápida OLS-por-UF + shrinkage Empirical Bayes. A comparação formal
(run_blup_vs_eb.py → blup_vs_eb_comparacao.csv) mostrou que os dois estimadores
divergem materialmente (Pearson r≈0,43; Spearman ρ≈0,42; overlap top-5 = 2/5),
porque NÃO são o mesmo modelo: o OLS-por-UF libera TODOS os coeficientes por
estado, enquanto o BLUP mantém as covariáveis agrupadas (nacionais) e deixa
variar apenas intercepto e inclinação de `negro`. O BLUP é a estimativa
multinível principiada e coerente com o random slope já reportado no TCC.

MOTIVAÇÃO
---------
O random slope rejeitou H0: τ²₁=0 (LR=7611,6, p<0,001): a penalidade racial não é
homogênea entre estados. A PO nacional (run_politicas_po.py) trata o gap como
escalar único e aloca implicitamente de forma uniforme. Este script quantifica
o ganho de FOCALIZAR o orçamento nas UFs de maior penalidade.

SAÍDA
-----
  outputs/tables/po_regional_gaps_uf.csv     — gap BLUP, pop e x*(B=9) por UF
  outputs/tables/po_regional_alocacao.csv    — focalizada × uniforme por orçamento
  outputs/tables/po_regional.tex             — tabelas LaTeX (gaps + alocação)
  outputs/figures/po_regional.png            — caterpillar + curva de ganho
  logs/po_regional.log

Referências:
  Raudenbush & Bryk (2002) HLM/BLUP; Robinson (1991) BLUP;
  Charnes, Cooper & Rhodes (1978) DEA; Darity & Mason (1998) gap racial.
"""

# --- bootstrap raiz do projeto (reorg estrutura) ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---


import sys
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import linprog

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path.cwd()))

ROOT    = Path.cwd()
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TAB = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)
Path("outputs/_logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("outputs/_logs/po_regional.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

BLUP_CSV = OUT_TAB / "blup_per_uf.csv"   # fonte oficial (run_blup_vs_eb.py)

# Efetividade média das políticas de acesso (Holzer & Neumark, 2000), constante
# entre UFs para isolar o efeito da FOCALIZAÇÃO (não da política).
ALPHA = 0.30
CORES_REG = {"Norte": "#4DAC26", "Nordeste": "#D01C8B", "Sudeste": "#2166AC",
             "Sul": "#7B3294", "Centro-Oeste": "#E66101"}


# ── 1. Carga dos BLUPs ───────────────────────────────────────────────────────

def load_blups():
    if not BLUP_CSV.exists():
        raise FileNotFoundError(
            f"{BLUP_CSV} não encontrado. Rode antes:  python run_blup_vs_eb.py "
            "(ajusta o MixedLM completo e persiste os BLUPs por UF)."
        )
    d = pd.read_csv(BLUP_CSV)
    cols = ["UF", "sigla", "regiao", "gap_blup", "gap_blup_pct", "n_negro", "n"]
    d = d[cols].copy()
    log.info(f"BLUPs carregados de {BLUP_CSV.name}: {len(d)} UFs.")
    log.info(f"  gap_blup: {d['gap_blup'].min():.4f} (pior) → "
             f"{d['gap_blup'].max():.4f} (melhor)")
    return d


# ── 2. Alocação regional por Programação Linear ──────────────────────────────

def alocacao(d):
    """
    Distribui orçamento B entre as 27 UFs maximizando a redução agregada do gap
    ponderada pela população negra afetada:
        max  Σ_j  α · s_j · w_j · x_j      s.a. Σ_j x_j ≤ B/c ,  0 ≤ x_j ≤ 1
    s_j = |gap_blup_j| (severidade); w_j = n_negro_j / Σ n_negro (peso pop.).
    Compara o ótimo (focalizado) com o uniforme x_j = B/(27c).
    """
    log.info("══ Alocação regional (BLUP): focalizada × uniforme ══")
    s = d["gap_blup"].abs().to_numpy()
    w = d["n_negro"].to_numpy() / d["n_negro"].sum()
    impacto = ALPHA * s * w
    J = len(d)

    rows = []
    for B in [3, 6, 9, 12, 15, 18, 27]:
        cap = min(B, J)
        res = linprog(-impacto, A_ub=[np.ones(J)], b_ub=[cap],
                      bounds=[(0, 1)] * J, method="highs")
        red_focal = float(impacto @ res.x)
        red_unif  = float(impacto @ np.full(J, cap / J))
        ganho = (red_focal / red_unif - 1) * 100 if red_unif > 0 else 0.0
        rows.append({"orcamento_ufs": B,
                     "reducao_focalizada": round(red_focal, 5),
                     "reducao_uniforme":  round(red_unif, 5),
                     "ganho_focalizacao_pct": round(ganho, 1)})
        log.info(f"  B={B:>2} UFs → focal={red_focal:.5f} | unif={red_unif:.5f} "
                 f"| ganho={ganho:+.1f}%")
    df_aloc = pd.DataFrame(rows)

    # Alocação ótima detalhada em B=9 (1/3 das UFs)
    res9 = linprog(-impacto, A_ub=[np.ones(J)], b_ub=[9],
                   bounds=[(0, 1)] * J, method="highs")
    d = d.copy()
    d["impacto_unit"] = np.round(impacto, 6)
    d["x_otimo_B9"]   = np.round(res9.x, 3)
    d["pct_pop_negra"]= np.round(w * 100, 2)
    return df_aloc, d


# ── 3. Figura ────────────────────────────────────────────────────────────────

def figura(d, df_aloc):
    d_s = d.sort_values("gap_blup")  # pior no topo
    fig, axes = plt.subplots(1, 2, figsize=(15, 7))

    # (a) Caterpillar dos gaps BLUP por UF
    ax = axes[0]
    ypos = np.arange(len(d_s))
    for i, (_, r) in enumerate(d_s.iterrows()):
        ax.scatter(r["gap_blup"], i, color=CORES_REG.get(r["regiao"], "k"),
                   s=55, zorder=3)
    ax.axvline(d_s["gap_blup"].mean(), color="black", ls="--", lw=1.2)
    ax.set_yticks(ypos); ax.set_yticklabels(d_s["sigla"], fontsize=8)
    ax.set_xlabel("Gap racial por UF — BLUP MixedLM (log-renda)", fontsize=10)
    ax.set_title("Penalidade racial por UF (BLUP, random slope)\nlinha tracejada = média nacional",
                 fontsize=11, fontweight="bold")
    handles = [plt.Line2D([0], [0], marker="o", ls="", color=c, label=r)
               for r, c in CORES_REG.items()]
    # canto superior-esquerdo: área vazia (UFs de menor gap ficam à direita) — evita
    # sobrepor os estados de maior penalidade (DF/AM/TO), no canto inferior-esquerdo.
    ax.legend(handles=handles, fontsize=8, loc="upper left", framealpha=0.9)
    ax.grid(alpha=0.3, axis="x")

    # (b) Ganho da focalização vs orçamento
    ax2 = axes[1]
    ax2.plot(df_aloc["orcamento_ufs"], df_aloc["ganho_focalizacao_pct"],
             "o-", color="#D01C8B", lw=2, ms=7)
    ax2.axhline(0, color="gray", lw=1)
    ax2.set_xlabel("Orçamento (nº de UFs-equivalentes financiáveis)", fontsize=10)
    ax2.set_ylabel("Ganho da focalização sobre alocação uniforme (%)", fontsize=10)
    ax2.set_title("Valor de regionalizar a PO (base BLUP)\nfocalização × uniforme",
                  fontsize=11, fontweight="bold")
    ax2.grid(alpha=0.3)
    for _, r in df_aloc.iterrows():
        ax2.text(r["orcamento_ufs"], r["ganho_focalizacao_pct"] + 1.0,
                 f"{r['ganho_focalizacao_pct']:.0f}%", ha="center", fontsize=8)

    plt.tight_layout()
    plt.savefig(OUT_FIG / "po_regional.png", dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  po_regional.png salvo.")


# ── 4. LaTeX ─────────────────────────────────────────────────────────────────

def _fmt(v, dec=1):
    return f"{v:.{dec}f}".replace(".", ",")

def gerar_latex(d, df_aloc):
    d_s = d.sort_values("gap_blup").reset_index(drop=True)
    # Tabela de alocação (headline)
    aloc_rows = ""
    for _, r in df_aloc.iterrows():
        aloc_rows += (f"  {int(r['orcamento_ufs'])} & {_fmt(r['reducao_focalizada'],5)} "
                      f"& {_fmt(r['reducao_uniforme'],5)} & "
                      f"{_fmt(r['ganho_focalizacao_pct'],1)}\\% \\\\\n")
    # Tabela por UF (financiadas em B=9 destacadas via x*)
    uf_rows = ""
    for i, r in d_s.iterrows():
        uf_rows += (f"  {i+1} & {r['sigla']} & {r['regiao']} & "
                    f"{_fmt(r['gap_blup_pct'],1)}\\% & {_fmt(r['pct_pop_negra'],1)}\\% & "
                    f"{_fmt(r['x_otimo_B9'],2)} \\\\\n")

    g9 = df_aloc.loc[df_aloc["orcamento_ufs"] == 9, "ganho_focalizacao_pct"].values[0]
    pior, melhor = d_s.iloc[0], d_s.iloc[-1]

    tex = rf"""\begin{{table}}[H]
  \centering
  \caption{{Pesquisa Operacional regionalizada: ganho de focalizar o orçamento
           nas UFs de maior penalidade racial \textit{{vs.}} alocação uniforme.
           Gap por UF = BLUP do MixedLM com \textit{{random slope}} de \texttt{{negro}}
           (população completa). Orçamento em UFs-equivalentes financiáveis;
           efetividade $\alpha={_fmt(ALPHA,2)}$ constante entre UFs (isola a focalização).
           Com $B=9$, focalizar reduz o gap agregado {_fmt(g9,1)}\% acima do uniforme.}}
  \label{{tab:po_regional}}
  \small
  \begin{{tabular}}{{crrr}}
    \toprule
    \textbf{{Orçamento (UFs)}} & \textbf{{Redução focalizada}} & \textbf{{Redução uniforme}} & \textbf{{Ganho}} \\
    \midrule
{aloc_rows}    \bottomrule
  \end{{tabular}}
\end{{table}}

\begin{{table}}[H]
  \centering
  \caption{{Penalidade racial por UF (BLUP MixedLM) e alocação ótima com $B=9$.
           $x_j^*$ = fração do canal financiada na UF $j$ na solução ótima.
           Maior penalidade: {pior['sigla']} ({_fmt(pior['gap_blup_pct'],1)}\%);
           menor: {melhor['sigla']} ({_fmt(melhor['gap_blup_pct'],1)}\%).}}
  \label{{tab:po_regional_uf}}
  \scriptsize
  \begin{{tabular}}{{rllrrr}}
    \toprule
    \# & \textbf{{UF}} & \textbf{{Região}} & \textbf{{Gap (\%)}} & \textbf{{\% pop. negra}} & $x_j^*(B{{=}}9)$ \\
    \midrule
{uf_rows}    \bottomrule
  \end{{tabular}}
\end{{table}}
"""
    (OUT_TAB / "po_regional.tex").write_text(tex, encoding="utf-8")
    log.info("  po_regional.tex salvo.")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("PO REGIONALIZADA — base oficial: BLUP MixedLM")
    log.info("=" * 60)

    d = load_blups()
    df_aloc, d = alocacao(d)
    figura(d, df_aloc)
    gerar_latex(d, df_aloc)

    d = d.sort_values("gap_blup").reset_index(drop=True)
    d.to_csv(OUT_TAB / "po_regional_gaps_uf.csv", index=False)
    df_aloc.to_csv(OUT_TAB / "po_regional_alocacao.csv", index=False)
    log.info(f"\nSalvo: po_regional_gaps_uf.csv ({len(d)} UFs) | po_regional_alocacao.csv")

    # ── Veredito ──────────────────────────────────────────────────────────────
    pior, melhor = d.iloc[0], d.iloc[-1]
    g9 = df_aloc.loc[df_aloc["orcamento_ufs"] == 9, "ganho_focalizacao_pct"].values[0]
    top5 = list(d.head(5)["sigla"])
    log.info("\n" + "=" * 60)
    log.info("VEREDITO — PO REGIONAL (BLUP oficial)")
    log.info(f"  Amplitude: {pior['sigla']} ({pior['gap_blup_pct']:.1f}%) → "
             f"{melhor['sigla']} ({melhor['gap_blup_pct']:.1f}%)")
    log.info(f"  Top-5 prioritárias: {top5}")
    log.info(f"  Ganho da focalização com B=9: {g9:+.1f}% sobre o uniforme")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
