"""
run_segregacao_espacial.py
Analise de empregabilidade e renda por tipo de area (V1023 + RM_RIDE).
V1023: 1=Capital, 2=RM nao capital, 3/4=Interior
Executa no Spyder Python.
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

ROOT    = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
FIGURES = ROOT / "outputs" / "figures"
TABLES  = ROOT / "outputs" / "tables"

COLS = ["negro", "sexo_fem", "V1022", "V1023", "RM_RIDE", "Capital",
        "log_renda", "renda_bruta", "pea", "empregado", "Ano"]

print("Carregando dados ...")
df = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=COLS)
df = df[df["negro"].notna()].copy()
df["negro"] = df["negro"].astype(int)

# V1023: 1=Capital, 2=RM exceto capital, 3+4=Interior — mapeamento vetorizado
area_map = {1: "Capital", 2: "RM (exceto\ncapital)", 3: "Interior", 4: "Interior"}
df["area_tipo"] = df["V1023"].map(area_map)
df = df.dropna(subset=["area_tipo"])

area_order = ["Capital", "RM (exceto\ncapital)", "Interior"]
race_cfg = [("Brancos", 0, "#1565C0"), ("Negros", 1, "#B71C1C")]

df_pea   = df[df["pea"] == 1].copy()
df_renda = df[(df["pea"] == 1) & (df["renda_bruta"] > 0)].copy()

print(f"PEA: {len(df_pea):,}  |  Com renda: {len(df_renda):,}")

# Distribuicao por area
dist = df_pea.groupby(["area_tipo","negro"]).size().reset_index(name="n")
print("\nDistribuicao PEA por area:")
print(dist.to_string(index=False))

# ── Figura 1: Taxa de ocupacao por raca x area ─────────────────────────────
grp_emp = df_pea.groupby(["area_tipo","negro"])["empregado"].mean().reset_index()
grp_emp["ocp_pct"] = grp_emp["empregado"] * 100

fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(area_order))
w = 0.35
for i, (lbl, negro_v, cor) in enumerate(race_cfg):
    vals = []
    for area in area_order:
        sub = grp_emp[(grp_emp["area_tipo"] == area) & (grp_emp["negro"] == negro_v)]
        vals.append(sub["ocp_pct"].values[0] if len(sub) else np.nan)
    ax.bar(x + (i - 0.5) * w, vals, w, color=cor, alpha=0.85, label=lbl)
    for j, val in enumerate(vals):
        if not np.isnan(val):
            ax.text(x[j] + (i - 0.5) * w, val + 0.5, f"{val:.1f}%",
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

ax.set_xticks(x)
ax.set_xticklabels(area_order, fontsize=11)
ax.set_ylabel("Taxa de ocupacao (%)", fontsize=11)
ax.set_ylim(0, 110)
ax.set_title("Taxa de Ocupacao por Raca e Tipo de Area de Moradia\n"
             "(PEA — PNAD Continua 2016-2025)", fontsize=12, fontweight='bold')
ax.legend(fontsize=11)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(FIGURES / "segreg_taxa_ocupacao.png", dpi=150, bbox_inches='tight')
plt.close()
print("segreg_taxa_ocupacao.png salvo.")

# ── Figura 2: Rendimento medio por raca x area ─────────────────────────────
grp_renda = df_renda.groupby(["area_tipo","negro"])["log_renda"].mean().reset_index()
grp_renda["renda_media"] = np.exp(grp_renda["log_renda"])

fig, ax = plt.subplots(figsize=(10, 5))
for i, (lbl, negro_v, cor) in enumerate(race_cfg):
    vals = []
    for area in area_order:
        sub = grp_renda[(grp_renda["area_tipo"] == area) & (grp_renda["negro"] == negro_v)]
        vals.append(sub["renda_media"].values[0] if len(sub) else np.nan)
    ax.bar(x + (i - 0.5) * w, vals, w, color=cor, alpha=0.85, label=lbl)
    for j, val in enumerate(vals):
        if not np.isnan(val):
            ax.text(x[j] + (i - 0.5) * w, val + 15, f"R${val:.0f}",
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

ax.set_xticks(x)
ax.set_xticklabels(area_order, fontsize=11)
ax.set_ylabel("Rendimento medio mensal (R$)", fontsize=11)
ax.set_title("Rendimento Medio por Raca e Tipo de Area de Moradia\n"
             "(ocupados com renda — PNAD Continua 2016-2025)", fontsize=12, fontweight='bold')
ax.legend(fontsize=11)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(FIGURES / "segreg_renda_por_area.png", dpi=150, bbox_inches='tight')
plt.close()
print("segreg_renda_por_area.png salvo.")

# ── Figura 3: Gap racial por area ─────────────────────────────────────────
gaps = []
for area in area_order:
    sub = df_renda[df_renda["area_tipo"] == area]
    yb  = sub[sub["negro"] == 0]["log_renda"].mean()
    yn  = sub[sub["negro"] == 1]["log_renda"].mean()
    g   = yb - yn
    ocp_b = df_pea[(df_pea["area_tipo"]==area) & (df_pea["negro"]==0)]["empregado"].mean() * 100
    ocp_n = df_pea[(df_pea["area_tipo"]==area) & (df_pea["negro"]==1)]["empregado"].mean() * 100
    gaps.append({"area_tipo": area, "gap_log": g, "gap_pct": (np.exp(g)-1)*100,
                 "ocp_b": ocp_b, "ocp_n": ocp_n, "diff_ocp": ocp_b - ocp_n})

gap_df = pd.DataFrame(gaps)
print("\nGap salarial e de ocupacao por area:")
print(gap_df[["area_tipo","gap_pct","ocp_b","ocp_n","diff_ocp"]].to_string(index=False))
gap_df.to_csv(TABLES / "segreg_gap_por_area.csv", index=False, encoding='utf-8')

colors_gap = ["#0D47A1", "#1565C0", "#B71C1C"]
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Gap salarial
ax = axes[0]
bars = ax.bar(area_order, gap_df["gap_pct"], color=colors_gap, alpha=0.85, width=0.5)
for bar, val in zip(bars, gap_df["gap_pct"]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
            f"{val:.1f}%", ha='center', va='bottom', fontsize=12, fontweight='bold')
ax.set_ylabel("% a menos que brancos", fontsize=11)
ax.set_title("Gap Salarial Racial\npor Tipo de Area", fontsize=11, fontweight='bold')
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.set_ylim(0, max(gap_df["gap_pct"]) * 1.3)

# Diferencial de ocupacao
ax = axes[1]
bars = ax.bar(area_order, gap_df["diff_ocp"], color=colors_gap, alpha=0.85, width=0.5)
for bar, val in zip(bars, gap_df["diff_ocp"]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
            f"{val:.1f} p.p.", ha='center', va='bottom', fontsize=12, fontweight='bold')
ax.set_ylabel("Diferenca em pontos percentuais", fontsize=11)
ax.set_title("Diferencial de Ocupacao (Brancos - Negros)\npor Tipo de Area", fontsize=11, fontweight='bold')
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.set_ylim(0, max(gap_df["diff_ocp"]) * 1.3)

fig.suptitle("Desigualdade Racial por Tipo de Area de Moradia\n(PNAD Continua 2016-2025)",
             fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(FIGURES / "segreg_gap_por_area.png", dpi=150, bbox_inches='tight')
plt.close()
print("segreg_gap_por_area.png salvo.")

# ── Figura 4: Evolucao temporal — Metropolitano vs. Interior ───────────────
df_renda["metro"] = df_renda["V1023"].isin([1, 2]).astype(int)
grp_t = (df_renda.groupby(["Ano","metro","negro"])["log_renda"]
         .mean().reset_index())

fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
for ax, (metro_v, metro_lbl) in zip(axes, [(1,"Area Metropolitana"), (0,"Interior")]):
    sub = grp_t[grp_t["metro"] == metro_v]
    sb  = sub[sub["negro"] == 0]
    sn  = sub[sub["negro"] == 1]
    ax.plot(sb["Ano"], np.exp(sb["log_renda"]), 'o-', color="#1565C0",
            label="Brancos", linewidth=2, markersize=5)
    ax.plot(sn["Ano"], np.exp(sn["log_renda"]), 's-', color="#B71C1C",
            label="Negros", linewidth=2, markersize=5)
    ax.fill_between(sb["Ano"].values, np.exp(sb["log_renda"].values),
                    np.exp(sn["log_renda"].values), alpha=0.1, color="gray",
                    label="Gap racial")
    ax.set_title(metro_lbl, fontsize=12, fontweight='bold')
    ax.set_xlabel("Ano", fontsize=10)
    ax.legend(fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

axes[0].set_ylabel("Rendimento medio mensal (R$)", fontsize=11)
fig.suptitle("Evolucao do Rendimento Racial: Area Metropolitana vs. Interior\n"
             "(ocupados com renda — PNAD Continua 2016-2025)",
             fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(FIGURES / "segreg_temporal_metro_interior.png", dpi=150, bbox_inches='tight')
plt.close()
print("segreg_temporal_metro_interior.png salvo.")

print("\n=== SEGREGACAO ESPACIAL CONCLUIDA ===")
print(gap_df[["area_tipo","gap_pct","ocp_b","ocp_n","diff_ocp"]].to_string(index=False))
