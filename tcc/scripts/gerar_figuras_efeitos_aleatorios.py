"""
gerar_figuras_efeitos_aleatorios.py — duas figuras de efeitos aleatórios do HLM (pedido do
autor em 02/10/2026).

1. hlm_variancia_escada.png — para onde vai a variância do log-rendimento ao longo da
   escada M0 → M4: entre bairros (τ²), dentro dos bairros (σ²) e a parcela já explicada,
   em % da variância total do modelo nulo. Lê outputs/tables/hlm_stepup_fit.csv.

2. hlm_encolhimento.png — o encolhimento (partial pooling) do modelo nulo: desvio bruto da
   média de cada bairro × BLUP. No M0 o BLUP tem fórmula fechada,
       u_j = λ_j (ȳ_j − γ00),   λ_j = τ² / (τ² + σ²/n_j),
   com τ², σ² e γ00 do M0 ajustado (cache de run_hlm_stepup.py) e ȳ_j, n_j calculados na
   mesma base filtrada do HLM (load_data). Bairros pequenos são puxados para a média; os
   grandes quase não se movem (Raudenbush & Bryk, 2002, cap. 3).

Uso:  python tcc/scripts/gerar_figuras_efeitos_aleatorios.py [--so-variancia]
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "analise"))
sys.stdout.reconfigure(encoding="utf-8")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.figuras_ptbr import virgula_decimal

T = ROOT / "outputs" / "tables"
F = ROOT / "outputs" / "figures"


def _titulo(fig, titulo, sub):
    fig.suptitle(titulo, x=0.02, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.02, 0.905, sub, fontsize=9, color="#616161")


def figura_variancia() -> None:
    fit = pd.read_csv(T / "hlm_stepup_fit.csv")
    fit = fit[fit["modelo"].isin(["M0", "M1", "M2", "M3", "M4"])].set_index("modelo")
    tot0 = fit.loc["M0", "tau2_upa"] + fit.loc["M0", "sigma2"]
    rot = {"M0": "M0 nulo", "M1": "M1 + indivíduo", "M2": "M2 + contexto do bairro",
           "M3": "M3 + estado", "M4": "M4 + ocupação"}
    ordem = ["M0", "M1", "M2", "M3", "M4"]
    entre = fit.loc[ordem, "tau2_upa"] / tot0 * 100
    dentro = fit.loc[ordem, "sigma2"] / tot0 * 100
    expl = 100 - entre - dentro

    fig, ax = plt.subplots(figsize=(9, 4.6))
    y = np.arange(len(ordem))[::-1]
    cores = {"entre": "#0D47A1", "dentro": "#90CAF9", "expl": "#E0E0E0"}
    ax.barh(y, entre, color=cores["entre"], edgecolor="white", label="Entre bairros (τ²)")
    ax.barh(y, dentro, left=entre, color=cores["dentro"], edgecolor="white",
            label="Dentro dos bairros (σ²)")
    ax.barh(y, expl, left=entre + dentro, color=cores["expl"], edgecolor="white",
            label="Já explicada pelos controles")
    for yi, m, e, d in zip(y, ordem, entre, dentro):
        ax.text(e / 2, yi, f"{e:.0f}%", ha="center", va="center", color="white", fontsize=9)
        ax.text(e + d / 2, yi, f"{d:.0f}%", ha="center", va="center", color="#0D47A1", fontsize=9)
        if 100 - e - d >= 4:
            ax.text((e + d + 100) / 2, yi, f"{100 - e - d:.0f}%", ha="center", va="center",
                    color="#616161", fontsize=9)
        icc = fit.loc[m, "icc_upa"] * 100
        ax.text(101, yi, f"ICC {icc:.0f}%", va="center", fontsize=9, color="#424242")
    ax.set_yticks(y)
    ax.set_yticklabels([rot[m] for m in ordem], fontsize=9.5)
    ax.set_xlim(0, 112)
    ax.set_xlabel("% da variância total do log-rendimento no modelo nulo")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.45, -0.32), ncol=3, frameon=False, fontsize=9)
    _titulo(fig, "Para onde vai a variância do rendimento ao longo da escada do HLM",
            "Variância entre bairros, dentro dos bairros e já explicada, em % do total do M0; "
            "à direita, o ICC de cada degrau.")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    virgula_decimal(fig)
    fig.savefig(F / "hlm_variancia_escada.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("OK -> outputs/figures/hlm_variancia_escada.png")


def figura_encolhimento() -> None:
    import run_hlm_stepup as H
    # o cache foi gravado por run_hlm_stepup.py rodando como __main__: a classe Light é
    # procurada lá na hora de desserializar
    sys.modules["__main__"].Light = H.Light
    with (ROOT / "outputs" / "_cache" / "hlm_stepup" / "M0.pkl").open("rb") as fh:
        m0 = pickle.load(fh)
    tau2, sig2, g00 = m0.tau2, m0.sigma2, float(m0.params["Intercept"])

    df = H.load_data(H.SAMPLE_FRAC)
    g = df.groupby("UPA")["log_renda"].agg(["mean", "size"])
    del df
    d = g["mean"] - g00
    lam = tau2 / (tau2 + sig2 / g["size"])
    u = lam * d
    pd.DataFrame({"UPA": g.index, "n": g["size"].values, "desvio_bruto": d.values,
                  "lambda": lam.values, "blup_m0": u.values}).to_csv(
        T / "hlm_encolhimento_m0.csv", index=False)

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 4.8), width_ratios=[1.6, 1])
    sc = ax.scatter(d, u, c=np.log10(g["size"]), s=4, alpha=0.35, cmap="Blues", vmin=0.5)
    lim = np.nanpercentile(np.abs(d), 99.5)
    ax.plot([-lim, lim], [-lim, lim], color="#9E9E9E", ls="--", lw=1)
    ax.text(0.97, 0.03, "linha tracejada: sem encolhimento (λ = 1)", transform=ax.transAxes,
            fontsize=8, color="#757575", ha="right", va="bottom")
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
    ax.set_xlabel("Desvio bruto da média do bairro (log-pontos)")
    ax.set_ylabel("BLUP do bairro no M0 (log-pontos)")
    cb = fig.colorbar(sc, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("log₁₀ do nº de pessoas no bairro", fontsize=8)
    ax2.scatter(g["size"], lam, s=3, alpha=0.3, color="#1565C0")
    ax2.set_xscale("log")
    ax2.set_ylim(0, 1.02)
    ax2.set_xlabel("Pessoas no bairro (escala log)")
    ax2.set_ylabel("λ: peso dado à média do próprio bairro")
    for a in (ax, ax2):
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    # título conforme o encolhimento observado: com ICC alto e ≥10 pessoas por bairro, λ fica
    # perto de 1 e o BLUP quase coincide com a média bruta — o que também é um resultado
    lam_min, lam_med = float(lam.min()), float(lam.median())
    titulo = ("Com tantas pessoas por bairro, o encolhimento é pequeno: a média de cada bairro já é confiável"
              if lam_min >= 0.7 else
              "Bairros pequenos são puxados para a média; os grandes falam por si")
    nb = f"{len(g) / 1000:.1f} mil"          # "40.728" viraria "40,728" na vírgula decimal
    _titulo(fig, titulo,
            f"Modelo nulo: λ = τ²/(τ² + σ²/n), com τ² = {tau2:.3f} e σ² = {sig2:.3f}; "
            f"{nb} bairros; λ vai de {lam_min:.2f} a 1 (mediana {lam_med:.2f}).")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    virgula_decimal(fig)
    fig.savefig(F / "hlm_encolhimento.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("OK -> outputs/figures/hlm_encolhimento.png")


if __name__ == "__main__":
    figura_variancia()
    if "--so-variancia" not in sys.argv:
        figura_encolhimento()
