"""
run_gini_raca.py
================
Gini da renda do TRABALHO entre OCUPADOS, intra-raça (branco vs. negro) e total,
ponderado pelo peso amostral V1028, PNAD Contínua 2016-2025.

Achado (corroboração do teto de vidro / efeito-chão): o Gini interno dos brancos é
MAIOR que o dos negros — não por equidade entre negros, mas por confinamento ao piso
da distribuição (renda homogeneamente baixa), o reverso da barreira de acesso ao topo.

Saídas: outputs/tables/gini_raca.csv | outputs/figures/gini_raca.png
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).parent
TAB  = ROOT / "outputs" / "tables"
FIG  = ROOT / "outputs" / "figures"


def gini_w(x, w):
    """Gini ponderado (Lorenz trapezoidal). x>0, w pesos amostrais."""
    o = np.argsort(x); x = x[o]; w = w[o]
    fp = np.cumsum(w) / w.sum()
    fi = np.cumsum(w * x) / np.sum(w * x)
    fp = np.concatenate(([0], fp)); fi = np.concatenate(([0], fi))
    return 1 - np.sum((fp[1:] - fp[:-1]) * (fi[1:] + fi[:-1]))


def theil_w(x, w, g):
    """Theil-T ponderado decomposto por grupo g: (total, between, within)."""
    mu = np.average(x, weights=w)
    T = np.sum(w * (x / mu) * np.log(x / mu)) / w.sum()
    Tb = Tw = 0.0
    for gv in np.unique(g):
        m = g == gv; wg = w[m]; xg = x[m]
        sg = (wg.sum() / w.sum()) * (np.average(xg, weights=wg) / mu)
        Tb += sg * np.log(np.average(xg, weights=wg) / mu)
        Tw += sg * (np.sum(wg * (xg / np.average(xg, weights=wg)) *
                           np.log(xg / np.average(xg, weights=wg))) / wg.sum())
    return T, Tb, Tw


def main():
    print("Carregando dados ...")
    df = pd.read_parquet(ROOT / "data/processed/features.parquet",
                         columns=["renda_bruta", "negro", "pea", "V1028", "Ano"])
    df = df[(df["pea"] == 1) & df["renda_bruta"].notna() & (df["renda_bruta"] > 0)
            & df["negro"].notna()].copy()
    r = df["renda_bruta"].values
    w = df["V1028"].values.astype(float)
    g = df["negro"].values

    g_tot = gini_w(r, w); g_bra = gini_w(r[g == 0], w[g == 0]); g_neg = gini_w(r[g == 1], w[g == 1])
    T, Tb, Tw = theil_w(r, w, g)

    rows = [{"grupo": "Total",   "gini": round(g_tot, 4), "n": int((g >= 0).sum())},
            {"grupo": "Brancos", "gini": round(g_bra, 4), "n": int((g == 0).sum())},
            {"grupo": "Negros",  "gini": round(g_neg, 4), "n": int((g == 1).sum())}]
    by_year = []
    for y in sorted(df["Ano"].dropna().unique()):
        d = df[df["Ano"] == y]; ry = d["renda_bruta"].values; wy = d["V1028"].values.astype(float); gy = d["negro"].values
        by_year.append({"Ano": int(y),
                        "gini_total":  round(gini_w(ry, wy), 4),
                        "gini_branco": round(gini_w(ry[gy == 0], wy[gy == 0]), 4),
                        "gini_negro":  round(gini_w(ry[gy == 1], wy[gy == 1]), 4)})
    dfy = pd.DataFrame(by_year)

    out = pd.DataFrame(rows)
    out["theil_total"] = round(T, 4); out["theil_between_pct"] = round(100 * Tb / T, 1)
    out["theil_within_pct"] = round(100 * Tw / T, 1)
    out.to_csv(TAB / "gini_raca.csv", index=False, encoding="utf-8")
    dfy.to_csv(TAB / "gini_raca_anual.csv", index=False, encoding="utf-8")
    print(out.to_string(index=False))
    print(f"Theil: between={100*Tb/T:.1f}% within={100*Tw/T:.1f}%")

    # ── Figura: Gini branco vs negro por ano ──────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(dfy["Ano"], dfy["gini_branco"], "o-", color="#1565C0", lw=2.4, ms=8, label="Brancos")
    ax.plot(dfy["Ano"], dfy["gini_negro"],  "s-", color="#C62828", lw=2.4, ms=8, label="Negros")
    ax.plot(dfy["Ano"], dfy["gini_total"],  "--", color="#888888", lw=1.6, label="Total")
    ax.fill_between(dfy["Ano"], dfy["gini_negro"], dfy["gini_branco"], color="#1565C0", alpha=0.06)
    ax.set_ylabel("Gini da renda do trabalho (ponderado)", fontsize=11)
    ax.set_xlabel("Ano", fontsize=11)
    ax.set_title("Gini intra-raça — o reverso do teto de vidro\n"
                 "Brancos têm MAIOR desigualdade interna; negros, comprimidos no piso (não é equidade)",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=10, loc="upper right")
    ax.grid(alpha=0.3)
    ax.set_xticks(dfy["Ano"])
    for lab in ax.get_xticklabels(): lab.set_rotation(0)
    ax.text(0.5, -0.16, "Fonte: PNAD Contínua 2016-2025, renda do trabalho entre ocupados, ponderado por V1028.",
            transform=ax.transAxes, ha="center", fontsize=8, color="#555")
    fig.tight_layout()
    fig.savefig(FIG / "gini_raca.png", dpi=160, bbox_inches="tight")
    plt.close()
    print("Figura salva: gini_raca.png")


if __name__ == "__main__":
    main()
