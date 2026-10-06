"""
run_hlm_negro_por_educ.py — a penalidade racial muda ao longo da escada educacional?

Robustez do HLM (pedido do autor em 02/10/2026): o mesmo M3 do núcleo (indivíduo em UPA,
contexto da UPA, efeitos fixos de UF e de ano), mas com o coeficiente de raça estimado
separadamente em cada nível de escolaridade: negro:C(nivel), sem o efeito principal de
negro. Assim cada coeficiente JÁ é a penalidade naquele nível, com o próprio erro-padrão
(com as dummies cumulativas, a interação com cada dummy daria só o incremento entre
níveis). Os efeitos principais de escolaridade continuam as dummies cumulativas do M3.

Níveis (exclusivos, a partir das dummies cumulativas da VD3004):
    sem_fund  sem fundamental completo (a categoria de referência do núcleo)
    fund      fundamental completo, sem médio completo
    medio     médio completo, sem superior completo
    sup       superior completo, sem pós-graduação
    pos       pós-graduação

Teste de igualdade: LR contra o M3 do núcleo (mesma amostra, ML; 4 graus de liberdade),
lido do cache de run_hlm_stepup.py.

População completa, sem amostragem (regra do projeto). Um processo só: um MixedLM do
tamanho do M3 (~7,7 milhões de observações).

Saídas:
    outputs/tables/hlm_negro_por_educ.csv
    outputs/figures/hlm_negro_por_educ.png
"""
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
_sys.path.insert(0, str(_Path(__file__).resolve().parent))

import sys
import numpy as np
import pandas as pd
from scipy import stats

import run_hlm_stepup as H                       # mesma carga, fórmulas e ajuste do núcleo
from src.figuras_ptbr import virgula_decimal

sys.stdout.reconfigure(encoding="utf-8")
log = H.logger

NIVEIS = [("sem_fund", "Sem fundamental completo"), ("fund", "Fundamental completo"),
          ("medio", "Médio completo"), ("sup", "Superior completo"), ("pos", "Pós-graduação")]


def nivel(df: pd.DataFrame) -> pd.Series:
    return pd.Series(np.select(
        [df["educ_pos_graduacao"] == 1, df["educ_superior_completo"] == 1,
         df["educ_medio_completo"] == 1, df["educ_fund_completo"] == 1],
        ["pos", "sup", "medio", "fund"], default="sem_fund"), index=df.index)


def main() -> int:
    df = H.load_data(H.SAMPLE_FRAC)
    df["nivel"] = pd.Categorical(nivel(df), categories=[k for k, _ in NIVEIS])

    ind_sem_negro = H._IND.replace("negro + ", "", 1)
    assert ind_sem_negro != H._IND, "fórmula individual do núcleo mudou"
    formula = (f"log_renda ~ {ind_sem_negro} + negro:C(nivel) + {H._UPA} + C(UF_str)")
    log.info(f"Fórmula: {formula}")

    L = H.fit_mixed("M3_negro_educ", formula, df)

    # retorno acumulado de cada nível (dummies cumulativas: soma dos degraus até ele), em
    # relação a quem não tem fundamental completo — é a altura das retas da 2ª figura
    degraus = ["educ_fund_completo", "educ_medio_completo", "educ_superior_completo",
               "educ_pos_graduacao"]
    acum = {"sem_fund": 0.0}
    for (k, _), j in zip(NIVEIS[1:], range(1, len(degraus) + 1)):
        acum[k] = float(sum(L.params[d] for d in degraus[:j]))

    linhas = []
    for k, rot in NIVEIS:
        termo = f"negro:C(nivel)[{k}]"
        b, se = float(L.params[termo]), float(L.bse[termo])
        sub = df[df["nivel"] == k]
        linhas.append({
            "nivel": k, "rotulo": rot, "n": len(sub), "n_negros": int(sub["negro"].sum()),
            "pct_negros": float(sub["negro"].mean() * 100),
            "pct_pop": len(sub) / len(df) * 100,
            "b_negro": b, "se": se, "ci_lo": b - 1.96 * se, "ci_hi": b + 1.96 * se,
            "gap_pct": (np.exp(b) - 1) * 100, "p_valor": float(L.pvalues[termo]),
            "b_educ_acum": acum[k],
        })
    out = pd.DataFrame(linhas)

    # LR contra o M3 do núcleo (penalidade igual em todos os níveis)
    # o cache foi gravado com run_hlm_stepup.py como __main__: a classe Light é procurada
    # lá ao desserializar (sem isto o LR saía NA na rodada de 03/10)
    sys.modules["__main__"].Light = H.Light
    m3 = H.cache_load("M3")
    out_llf = L.llf
    if m3 is not None and m3.n == L.n:
        lr = 2 * (L.llf - m3.llf)
        gl = len(NIVEIS) - 1
        out["lr_vs_m3"] = lr
        out["gl_lr"] = gl
        out["p_lr"] = float(stats.chi2.sf(lr, gl))
        out["b_negro_m3"] = float(m3.params["negro"])
        log.info(f"LR vs M3 = {lr:,.1f} (gl={gl}, p={out['p_lr'].iloc[0]:.3g})")
    else:
        log.warning("cache do M3 ausente ou com outro N — LR não calculado")
    out["n_total"] = L.n
    out["llf"] = out_llf
    out["converged"] = L.converged
    H.TABLES.mkdir(parents=True, exist_ok=True)
    out.to_csv(H.TABLES / "hlm_negro_por_educ.csv", index=False, encoding="utf-8")
    log.info("\n" + out[["rotulo", "pct_pop", "pct_negros", "b_negro", "se", "gap_pct"]]
             .round(4).to_string(index=False))

    figura(out)
    figura_retas(out)
    return 0


def figura_retas(out: pd.DataFrame) -> None:
    """Uma reta por nível, de branco (x=0) a negro (x=1): a altura é o retorno do nível
    sobre quem não tem fundamental completo; a inclinação, a penalidade racial ali.
    Mesmo desenho da figura de inclinações aleatórias por UPA (Fávero), na escada."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cores = ["#BDBDBD", "#90CAF9", "#42A5F5", "#1E88E5", "#0D47A1"]
    fig, ax = plt.subplots(figsize=(8, 5.6))
    pontas = []
    for r, c in zip(out.itertuples(), cores):
        y0 = (np.exp(r.b_educ_acum) - 1) * 100
        y1 = (np.exp(r.b_educ_acum + r.b_negro) - 1) * 100
        ax.plot([0, 1], [y0, y1], "-o", color=c, lw=2.5, ms=7)
        pen = f"{(np.exp(r.b_negro) - 1) * 100:+.1f}%".replace("-", "−")
        pontas.append([y1, f"{r.rotulo}: {pen}"])
    # rótulos sem sobreposição: de baixo para cima, cada um ao menos 'passo' acima do anterior
    faixa = max(p_[0] for p_ in pontas) - min(p_[0] for p_ in pontas)
    passo = max(faixa, 1) * 0.06
    pontas.sort(key=lambda p_: p_[0])
    y_txt = [pontas[0][0]]
    for y1, _ in pontas[1:]:
        y_txt.append(max(y1, y_txt[-1] + passo))
    for (_, txt), yt in zip(pontas, y_txt):
        ax.text(1.04, yt, txt, va="center", fontsize=9, color="#212121")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Branco", "Negro"], fontsize=11)
    ax.set_xlim(-0.15, 1.75)
    ax.axhline(0, color="#9E9E9E", lw=0.8, ls=":")
    ax.set_ylabel("Rendimento em relação ao branco sem fundamental completo (%)")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.suptitle("Retorno de cada nível de escolaridade e penalidade racial dentro dele",
                 x=0.02, ha="left", fontsize=11.5, fontweight="bold")
    fig.text(0.02, 0.91, "M3 do núcleo com penalidade racial por nível; à direita, a "
             "inclinação de cada reta (penalidade condicional).", fontsize=9, color="#616161")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    virgula_decimal(fig)
    import sys as _sn; _sn.path.insert(0, str(_Path(__file__).resolve().parents[2] / "src"))
    from figuras_ptbr import norma_manual  # manual MBA: sem título no gráfico, painéis A/B
    norma_manual(fig)
    fig.savefig(H.FIGURES / "hlm_negro_por_educ_retas.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("figura: outputs/figures/hlm_negro_por_educ_retas.png")


def figura(out: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 4.8))
    y = np.arange(len(out))[::-1]
    gap = -out["gap_pct"]                                  # penalidade em % positiva
    lo = -(np.exp(out["ci_hi"]) - 1) * 100
    hi = -(np.exp(out["ci_lo"]) - 1) * 100
    ax.hlines(y, lo, hi, color="#1565C0", lw=2)
    ax.plot(gap, y, "o", color="#1565C0", ms=8)
    if "b_negro_m3" in out:
        m3 = -(np.exp(out["b_negro_m3"].iloc[0]) - 1) * 100
        ax.axvline(m3, color="#9E9E9E", ls="--", lw=1)
        ax.text(m3, len(out) - 0.45, f"  M3 (penalidade única): {m3:.1f}%", color="#616161",
                fontsize=9, ha="left")
    for yi, g, r in zip(y, gap, out.itertuples()):
        ax.text(g, yi + 0.18, f"{g:.1f}%", ha="center", fontsize=9, color="#0D47A1")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r.rotulo}\n({r.pct_pop:.0f}% dos trabalhadores, "
                        f"{r.pct_negros:.0f}% negros)" for r in out.itertuples()], fontsize=9)
    ax.set_xlabel("Penalidade racial condicional (% do rendimento, IC 95%)")
    ax.set_ylim(-0.6, len(out) - 0.2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.suptitle("A penalidade racial ao longo da escada educacional", x=0.02, ha="left",
                 fontsize=12, fontweight="bold")
    fig.text(0.02, 0.905, "M3 do núcleo com o coeficiente de raça estimado em cada nível; "
             "PNAD Contínua 2016–2025, população completa.", fontsize=9, color="#616161")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    virgula_decimal(fig)
    import sys as _sn; _sn.path.insert(0, str(_Path(__file__).resolve().parents[2] / "src"))
    from figuras_ptbr import norma_manual  # manual MBA: sem título no gráfico, painéis A/B
    norma_manual(fig)
    fig.savefig(H.FIGURES / "hlm_negro_por_educ.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("figura: outputs/figures/hlm_negro_por_educ.png")


if __name__ == "__main__":
    sys.exit(main())
