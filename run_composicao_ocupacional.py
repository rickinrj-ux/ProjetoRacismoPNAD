"""
run_composicao_ocupacional.py
Segregacao ocupacional real por raca x tipo de area.
Usa VD4008 (grupo CBO), VD4009 (formal/informal), VD4031 (horas).
Fallback para analise por percentil se extras.parquet nao estiver disponivel.
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

# Tenta carregar features com novas colunas
BASE_COLS = ["negro", "V1023", "log_renda", "renda_bruta",
             "pea", "empregado", "sexo_fem", "Ano"]
OCC_COLS  = ["ocp_grupo_cbo", "tipo_vinculo", "emprego_formal", "conta_propria",
             "trab_domestico", "setor_publico", "horas_trabalhadas"]

print("Carregando dados ...")
_all_cols = pd.read_parquet(ROOT / "data/processed/features.parquet").columns.tolist()
LOAD_COLS = BASE_COLS + [c for c in OCC_COLS if c in _all_cols]

df = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=LOAD_COLS)
df = df[(df["pea"] == 1) & (df["renda_bruta"] > 0) & df["negro"].notna()].copy()
df["negro"] = df["negro"].astype(int)

area_map = {1: "Capital", 2: "RM (exceto capital)", 3: "Interior", 4: "Interior"}
df["area_tipo"] = df["V1023"].map(area_map)
df = df.dropna(subset=["area_tipo"])
area_order = ["Capital", "RM (exceto capital)", "Interior"]

HAS_OCC    = "ocp_grupo_cbo" in df.columns
HAS_FORMAL = "emprego_formal" in df.columns
HAS_HORAS  = "horas_trabalhadas" in df.columns

print(f"Total com renda: {len(df):,}")
print(f"Grupos CBO reais (V4010):   {'SIM' if HAS_OCC else 'NAO'}")
print(f"Formalidade (VD4009):       {'SIM' if HAS_FORMAL else 'NAO'}")
print(f"Horas trabalhadas (VD4031): {'SIM' if HAS_HORAS else 'NAO'}")

# ── Percentis de renda por raca x area ────────────────────────────────────────
pcts = [10, 25, 50, 75, 90, 95]
percentile_data = []
for area in area_order:
    for negro_v, race_lbl in [(0, "Branco"), (1, "Negro")]:
        sub = df[(df["area_tipo"] == area) & (df["negro"] == negro_v)]["renda_bruta"]
        row = {"area": area, "raca": race_lbl, "n": len(sub)}
        for p in pcts:
            row[f"p{p}"] = np.percentile(sub, p)
        percentile_data.append(row)
perc_df = pd.DataFrame(percentile_data)
perc_df.to_csv(TABLES / "composicao_percentis_renda.csv", index=False, encoding="utf-8")
print("\nPercentis de renda salvos.")

# ── Representacao nos percentis superiores ────────────────────────────────────
repr_data = []
for area in area_order:
    sub_area = df[df["area_tipo"] == area].copy()
    n_total  = len(sub_area)
    n_negros = (sub_area["negro"] == 1).sum()
    pct_negro_base = n_negros / n_total * 100
    for threshold_label, threshold_pct in [("Top 25%", 75), ("Top 10%", 90), ("Top 5%", 95)]:
        cutoff = np.percentile(sub_area["renda_bruta"], threshold_pct)
        top_group = sub_area[sub_area["renda_bruta"] >= cutoff]
        pct_top_negro = (top_group["negro"] == 1).sum() / len(top_group) * 100
        repr_data.append({
            "area": area,
            "grupo": threshold_label,
            "pct_negro_base": pct_negro_base,
            "pct_negro_top": pct_top_negro,
            "indice_repr": pct_top_negro / pct_negro_base,
            "cutoff_renda": cutoff,
        })
repr_df = pd.DataFrame(repr_data)
repr_df.to_csv(TABLES / "composicao_repr_topo.csv", index=False, encoding="utf-8")

# ── Composicao por grupo CBO real (V4010) ─────────────────────────────────────
OCP_ORDER = ["dirigente", "profissional", "tecnico", "administrativo",
             "servicos", "agro", "operario", "operador", "elementar", "ffaa"]
OCP_LABEL = {
    "dirigente":      "Dirigentes",
    "profissional":   "Profissionais",
    "tecnico":        "Técnicos",
    "administrativo": "Administrativo",
    "servicos":       "Serviços/Vendas",
    "agro":           "Agropecuária",
    "operario":       "Operários",
    "operador":       "Op. Máquinas",
    "elementar":      "Elementar",
    "ffaa":           "FFAA/Polícia",
}

if HAS_OCC:
    print("\nComposicao por grupo CBO ...")
    ocp_data = []
    for area in area_order:
        sub_area = df[df["area_tipo"] == area].copy()
        n_negro  = (sub_area["negro"] == 1).sum()
        n_branco = (sub_area["negro"] == 0).sum()
        for grp in OCP_ORDER:
            gb = ((sub_area["negro"] == 0) & (sub_area["ocp_grupo_cbo"] == grp)).sum()
            gn = ((sub_area["negro"] == 1) & (sub_area["ocp_grupo_cbo"] == grp)).sum()
            renda_grp = sub_area[sub_area["ocp_grupo_cbo"] == grp]["renda_bruta"].median()
            ocp_data.append({
                "area": area, "grupo": grp,
                "pct_branco":  gb / n_branco * 100,
                "pct_negro":   gn / n_negro  * 100,
                "razao_nn_bb": (gn / n_negro) / (gb / n_branco) if gb > 0 else np.nan,
                "renda_mediana": renda_grp,
            })
    ocp_df = pd.DataFrame(ocp_data)
    ocp_df.to_csv(TABLES / "composicao_por_grupo_cbo.csv", index=False, encoding="utf-8")
    print(ocp_df[ocp_df["area"] == "Capital"][
        ["grupo","pct_branco","pct_negro","razao_nn_bb","renda_mediana"]
    ].to_string(index=False))

# ── Formalidade real (VD4009) por raca x area ─────────────────────────────────
if HAS_FORMAL:
    print("\nFormalidade por raca x area ...")
    form_data = []
    for area in area_order:
        for negro_v, race_lbl in [(0, "Branco"), (1, "Negro")]:
            sub = df[(df["area_tipo"] == area) & (df["negro"] == negro_v)]
            form_data.append({
                "area": area, "raca": race_lbl,
                "pct_formal":    sub["emprego_formal"].mean() * 100,
                "pct_conta_prop": sub["conta_propria"].mean() * 100,
                "pct_publico":   sub["setor_publico"].mean() * 100,
                "pct_domestico": sub["trab_domestico"].mean() * 100,
            })
    form_df = pd.DataFrame(form_data)
    print(form_df.to_string(index=False))
    form_df.to_csv(TABLES / "composicao_formalidade.csv", index=False, encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# FIGURAS
# ══════════════════════════════════════════════════════════════════════════════

# ── Figura A: Representacao de negros nos percentis superiores ────────────────
fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=True)
grupo_order = ["Top 25%", "Top 10%", "Top 5%"]
COLS_GROUPS = ["#FF8F00", "#F44336", "#B71C1C"]

for ax, area in zip(axes, area_order):
    sub = repr_df[repr_df["area"] == area].set_index("grupo").reindex(grupo_order)
    base = sub["pct_negro_base"].values[0]
    bars = ax.bar(grupo_order, sub["pct_negro_top"], color=COLS_GROUPS, alpha=0.85, width=0.5)
    ax.axhline(base, color="#1565C0", linewidth=2, linestyle="--",
               label=f"Particip. geral ({base:.1f}%)")
    for bar, val in zip(bars, sub["pct_negro_top"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.4,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    for idx_r, (g, row) in enumerate(sub.iterrows()):
        ax.text(idx_r, row["pct_negro_top"] / 2, f"IR={row['indice_repr']:.2f}",
                ha="center", va="center", fontsize=8, color="white", fontweight="bold")
    ax.set_title(area, fontsize=11, fontweight="bold")
    ax.set_ylabel("% de negros no grupo" if area == "Capital" else "", fontsize=10)
    ax.legend(fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylim(0, max(sub["pct_negro_top"].max(), base) * 1.3)

fig.suptitle(
    "Representação de Negros nos Percentis Superiores de Renda por Tipo de Área\n"
    "IR = Índice de Representação (1,0 = proporcional | < 1 = sub-representado)",
    fontsize=11, fontweight="bold")
plt.tight_layout()
plt.savefig(FIGURES / "comp_representacao_topo.png", dpi=150, bbox_inches="tight")
plt.close()
print("comp_representacao_topo.png salvo.")

# ── Figura B: Razao de renda por percentil x area ─────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
markers_list = ["o", "s", "^"]
colors_area  = ["#0D47A1", "#1565C0", "#B71C1C"]
for i, area in enumerate(area_order):
    sub_b = perc_df[(perc_df["area"] == area) & (perc_df["raca"] == "Branco")]
    sub_n = perc_df[(perc_df["area"] == area) & (perc_df["raca"] == "Negro")]
    ratios = [sub_n[f"p{p}"].values[0] / sub_b[f"p{p}"].values[0] * 100 for p in pcts]
    xr = np.arange(len(pcts))
    ax.plot(xr, ratios, marker=markers_list[i], color=colors_area[i], linewidth=2,
            markersize=7, label=area)
    for j, val in enumerate(ratios):
        ax.text(xr[j], val - 2.5, f"{val:.0f}%", ha="center", va="top",
                fontsize=8, color=colors_area[i])
ax.axhline(100, color="gray", linewidth=1.2, linestyle="--", label="Paridade (100%)")
ax.set_xticks(np.arange(len(pcts)))
ax.set_xticklabels([f"P{p}" for p in pcts], fontsize=10)
ax.set_ylabel("Renda negro / renda branco (%)", fontsize=11)
ax.set_ylim(40, 115)
ax.set_title("Razão de Renda Negro/Branco por Percentil e Tipo de Área\n"
             "(100% = paridade | abaixo de 100% = negros ganham menos)",
             fontsize=12, fontweight="bold")
ax.legend(fontsize=9)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.tight_layout()
plt.savefig(FIGURES / "comp_ratio_renda.png", dpi=150, bbox_inches="tight")
plt.close()
print("comp_ratio_renda.png salvo.")

# ── Figura C: Composicao por grupo CBO (Capital) ──────────────────────────────
if HAS_OCC:
    cap = ocp_df[ocp_df["area"] == "Capital"].copy()
    cap["grp_label"] = cap["grupo"].map(OCP_LABEL)
    cap = cap.set_index("grupo").reindex([g for g in OCP_ORDER if g != "ffaa"])
    cap["grp_label"] = cap.index.map(OCP_LABEL)

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(cap))
    w = 0.35
    b1 = ax.bar(x - w/2, cap["pct_branco"], w, color="#1565C0", alpha=0.85, label="Brancos")
    b2 = ax.bar(x + w/2, cap["pct_negro"],  w, color="#B71C1C", alpha=0.85, label="Negros")
    for bar in [*b1, *b2]:
        h = bar.get_height()
        if h > 0.5:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.1, f"{h:.1f}%",
                    ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(cap["grp_label"], fontsize=9, rotation=20, ha="right")
    ax.set_ylabel("% da força de trabalho no grupo", fontsize=11)
    ax.set_title("Distribuição por Grupo Ocupacional (CBO) — Capital\n"
                 "Segregação estrutural: brancos no topo, negros nas funções elementares",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(FIGURES / "comp_grupo_cbo_capital.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("comp_grupo_cbo_capital.png salvo.")

    # Figura D: Razao negro/branco por grupo CBO nos 3 tipos de area
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
    grps_plot = [g for g in OCP_ORDER if g != "ffaa"]
    for ax, area in zip(axes, area_order):
        sub = ocp_df[ocp_df["area"] == area].copy()
        sub = sub.set_index("grupo").reindex(grps_plot)
        razoes = sub["razao_nn_bb"].values
        colors_bar = ["#1B5E20" if r > 1 else "#B71C1C" for r in razoes]
        bars = ax.barh([OCP_LABEL[g] for g in grps_plot], razoes,
                       color=colors_bar, alpha=0.8)
        ax.axvline(1, color="black", linewidth=1.2, linestyle="--")
        for bar, val in zip(bars, razoes):
            if not np.isnan(val):
                ax.text(val + 0.02, bar.get_y() + bar.get_height()/2,
                        f"{val:.2f}", va="center", fontsize=8, fontweight="bold")
        ax.set_title(area, fontsize=11, fontweight="bold")
        ax.set_xlabel("Razão (negro/branco)" if area == "Interior" else "")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle(
        "Razão de Representação Negro/Branco por Grupo Ocupacional e Tipo de Área\n"
        "Verde = sobre-representados | Vermelho = sub-representados | 1,0 = proporcional",
        fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIGURES / "comp_razao_grupo_cbo.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("comp_razao_grupo_cbo.png salvo.")

# ── Figura E: Formalidade real (VD4009) ───────────────────────────────────────
if HAS_FORMAL:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    x = np.arange(3)
    w = 0.35
    COLORS = {"Branco": "#1565C0", "Negro": "#B71C1C"}

    for ax, (metric, ylabel) in zip(axes, [
        ("pct_formal",    "% com emprego formal"),
        ("pct_conta_prop","% conta própria"),
    ]):
        for i, race_lbl in enumerate(["Branco", "Negro"]):
            vals = [form_df[(form_df["area"] == a) & (form_df["raca"] == race_lbl)][metric].values[0]
                    for a in area_order]
            ax.bar(x + (i - 0.5) * w, vals, w,
                   color=COLORS[race_lbl], alpha=0.85, label=race_lbl)
            for j, val in enumerate(vals):
                ax.text(x[j] + (i - 0.5) * w, val + 0.5, f"{val:.1f}%",
                        ha="center", va="bottom", fontsize=9, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(area_order, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.legend(fontsize=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_title("Taxa de Formalidade (carteira/estatutário)\npor Raça e Tipo de Área",
                      fontsize=11, fontweight="bold")
    axes[1].set_title("Taxa de Trabalho por Conta Própria\npor Raça e Tipo de Área",
                      fontsize=11, fontweight="bold")
    fig.suptitle("Estrutura de Vínculos Empregatícios por Raça e Tipo de Área\n"
                 "(PNAD Contínua 2016–2025 — VD4009)",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIGURES / "comp_formalidade.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("comp_formalidade.png salvo.")

# ── Figura F: Box plots de renda ──────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=False)
for ax, area in zip(axes, area_order):
    sub_area = df[df["area_tipo"] == area]
    data_b = np.log(sub_area[sub_area["negro"] == 0]["renda_bruta"].values + 1)
    data_n = np.log(sub_area[sub_area["negro"] == 1]["renda_bruta"].values + 1)
    bp = ax.boxplot([data_b, data_n], patch_artist=True,
                    medianprops=dict(color="white", linewidth=2),
                    whiskerprops=dict(linewidth=1.2), capprops=dict(linewidth=1.2),
                    flierprops=dict(marker=".", markersize=1, alpha=0.3))
    for patch, color in zip(bp["boxes"], ["#1565C0", "#B71C1C"]):
        patch.set_facecolor(color); patch.set_alpha(0.8)
    ax.set_xticks([1, 2]); ax.set_xticklabels(["Brancos", "Negros"], fontsize=10)
    ax.set_title(area, fontsize=11, fontweight="bold")
    ax.set_ylabel("log(renda + 1)" if area == "Capital" else "", fontsize=10)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    for i, (med, lbl) in enumerate(zip(
        [np.median(data_b), np.median(data_n)], ["Branco", "Negro"]
    ), 1):
        ax.text(i, med + 0.05, f"R${np.exp(med):.0f}", ha="center", va="bottom",
                fontsize=9, fontweight="bold",
                color="#1565C0" if lbl == "Branco" else "#B71C1C")

fig.suptitle("Distribuição do Rendimento por Raça e Tipo de Área\n"
             "(IQR | whiskers=1.5×IQR | mediana anotada)",
             fontsize=11, fontweight="bold")
plt.tight_layout()
plt.savefig(FIGURES / "comp_boxplot_renda.png", dpi=150, bbox_inches="tight")
plt.close()
print("comp_boxplot_renda.png salvo.")

# ── Figura G: P75 e P90 por raca x area ──────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=False)
for ax, pct_col in zip(axes, ["p75", "p90"]):
    for i, (race_lbl, cor) in enumerate([("Branco", "#1565C0"), ("Negro", "#B71C1C")]):
        vals = [perc_df[(perc_df["area"] == a) & (perc_df["raca"] == race_lbl)][pct_col].values[0]
                for a in area_order]
        ax.bar(np.arange(3) + (i - 0.5) * 0.35, vals, 0.35,
               color=cor, alpha=0.85, label=race_lbl)
        for j, val in enumerate(vals):
            ax.text(j + (i - 0.5) * 0.35, val + 20, f"R${val:.0f}",
                    ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_xticks(np.arange(3))
    ax.set_xticklabels(area_order, fontsize=10)
    ax.set_title(f"Renda no {'P75' if pct_col=='p75' else 'P90'} por Raça e Área",
                 fontsize=11, fontweight="bold")
    ax.set_ylabel("Renda (R$)", fontsize=10)
    ax.legend(fontsize=9)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

fig.suptitle("Comparação dos Percentis Superiores: Segregação no Topo\n"
             "(distância entre barras = exclusão de negros das faixas superiores)",
             fontsize=11, fontweight="bold")
plt.tight_layout()
plt.savefig(FIGURES / "comp_percentis_superiores.png", dpi=150, bbox_inches="tight")
plt.close()
print("comp_percentis_superiores.png salvo.")

print("\n=== COMPOSICAO OCUPACIONAL CONCLUIDA ===")
print("\nIndice de Representacao:")
print(repr_df[["area","grupo","pct_negro_base","pct_negro_top","indice_repr"]].to_string(index=False))
