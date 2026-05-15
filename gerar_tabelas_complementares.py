"""
gerar_tabelas_complementares.py
Gera os artefatos pedidos pelo orientador que ainda não existiam:
  - Tabela 1  : descritiva ponderada por grupo racial
  - Tabela 2  : gap bruto por gênero, escolaridade e faixa etária
  - Tabela 3  : regressões Mincer com controles progressivos
  - Tabela 4  : termos de interação raça×gênero, raça×escolaridade, raça×idade
  - Figura 1  : densidade do log(salário) por raça
  - Figura 2  : heatmap do gap (raça × gênero × escolaridade)
  - Figura 4  : gap por faixa etária — curva de ciclo de vida
Saídas: outputs/tables/*.csv  |  outputs/figures/*.png
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import warnings; warnings.filterwarnings("ignore")
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap
import statsmodels.api as sm
from scipy import stats

ROOT    = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
TABLES  = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

# ── Paleta de cores consistente com o projeto ─────────────────────────────────
C_BRANCO = "#1565C0"   # azul
C_NEGRO  = "#B71C1C"   # vermelho
C_DARK   = "#1F3864"

plt.rcParams.update({
    "font.family": "sans-serif",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

# ══════════════════════════════════════════════════════════════════════════════
# 1. CARGA E PREPARAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
print("Carregando dados...")
df_raw = pd.read_parquet(ROOT / "data" / "processed" / "features.parquet")
print(f"  Total bruto: {len(df_raw):,} obs.")

# Amostra de trabalho: empregados com renda positiva
df_all = df_raw[
    (df_raw["empregado"] == 1) &
    (df_raw["renda_bruta"] > 0) &
    df_raw["negro"].notna() &
    df_raw["V1028"].notna()
].copy()

# Mapeamentos de rótulos
EDUC_ORDER = [
    "sem_instrucao", "fund_incompleto", "fund_completo",
    "medio_incompleto", "medio_completo",
    "superior_incompleto", "superior_completo", "pos_graduacao"
]
EDUC_LABEL = {
    "sem_instrucao":      "Sem instrução",
    "fund_incompleto":    "Fund. incompleto",
    "fund_completo":      "Fund. completo",
    "medio_incompleto":   "Médio incompleto",
    "medio_completo":     "Médio completo",
    "superior_incompleto":"Superior incomp.",
    "superior_completo":  "Superior comp.",
    "pos_graduacao":      "Pós-graduação",
}

# Grupo de escolaridade agregado (3 níveis para heatmap / tabela 2)
def educ_grupo(cat):
    if cat in ("sem_instrucao", "fund_incompleto", "fund_completo", "medio_incompleto"):
        return "Até médio\nincompleto"
    elif cat in ("medio_completo", "superior_incompleto"):
        return "Médio completo\nou superior incomp."
    else:
        return "Superior\ncompleto ou pós"

df_all["educ_grupo"] = df_all["educ_cat"].map(educ_grupo)
EDUC_GRP_ORDER = ["Até médio\nincompleto", "Médio completo\nou superior incomp.", "Superior\ncompleto ou pós"]

FAIXA_ORDER = ["14-24", "25-34", "35-44", "45-54", "55-64", "65+"]

peso = df_all["V1028"]

print(f"  Amostra de trabalho (empregados c/ renda): {len(df_all):,} obs.")

# Amostra 20% para regressões (consistência com análise principal)
np.random.seed(42)
idx20 = np.random.choice(len(df_all), size=int(len(df_all) * 0.20), replace=False)
df = df_all.iloc[idx20].copy()
print(f"  Sub-amostra 20% para regressões: {len(df):,} obs.")

# ══════════════════════════════════════════════════════════════════════════════
# 2. TABELA 1 — DESCRITIVA PONDERADA POR GRUPO RACIAL
# ══════════════════════════════════════════════════════════════════════════════
print("\n--- Tabela 1: Descritiva ponderada ---")

def wquantile(series, weights, q):
    """Quantil ponderado."""
    df_s = pd.DataFrame({"v": series, "w": weights}).dropna().sort_values("v")
    cumw = df_s["w"].cumsum() / df_s["w"].sum()
    return float(df_s["v"][cumw >= q].iloc[0])

def desc_grupo(sub, w):
    d = {}
    d["N ponderado (mil)"]       = f"{w.sum() / 1e3:,.0f}"
    d["Renda mediana (R$)"]      = f"{wquantile(sub['renda_bruta'], w, 0.5):,.0f}"
    d["Renda média (R$)"]        = f"{np.average(sub['renda_bruta'], weights=w):,.0f}"
    d["DP renda (R$)"]           = f"{np.sqrt(np.cov(sub['renda_bruta'], aweights=w)):,.0f}"
    d["Log-renda média"]         = f"{np.average(sub['log_renda'], weights=w):.4f}"
    d["Idade média (anos)"]      = f"{np.average(sub['idade'], weights=w):.1f}"
    _mask = sub['educ_ord'].notna()
    d["Escolaridade média (0-7)"]= f"{np.average(sub.loc[_mask,'educ_ord'], weights=w[_mask]):.2f}" if _mask.any() else "N/A"
    d["Horas trab./sem (média)"] = f"{np.average(sub['horas_trabalhadas'], weights=w):.1f}"
    d["Emprego formal (%)"]      = f"{100 * np.average(sub['emprego_formal'], weights=w):.1f}"
    d["Setor público (%)"]       = f"{100 * np.average(sub['setor_publico'], weights=w):.1f}"
    d["Sexo feminino (%)"]       = f"{100 * np.average(sub['sexo_fem'], weights=w):.1f}"
    return d

branco = df_all[df_all["negro"] == 0]
negro  = df_all[df_all["negro"] == 1]
w_b    = branco["V1028"]
w_n    = negro["V1028"]

tab1 = pd.DataFrame({
    "Brancos": desc_grupo(branco, w_b),
    "Negros":  desc_grupo(negro,  w_n),
})

# Diferença bruta de renda (%)
med_b = wquantile(branco["renda_bruta"], w_b, 0.5)
med_n = wquantile(negro["renda_bruta"],  w_n, 0.5)
gap_b = (med_b - med_n) / med_b * 100
tab1.loc["Gap racial bruto (mediana, %)"] = [f"Ref. R${med_b:,.0f}", f"−{gap_b:.1f}%"]

tab1.to_csv(TABLES / "tab1_descritiva_racial.csv")
print(tab1.to_string())
print("  tab1_descritiva_racial.csv salvo.")

# ══════════════════════════════════════════════════════════════════════════════
# 3. TABELA 2 — GAP BRUTO POR SUBGRUPO
# ══════════════════════════════════════════════════════════════════════════════
print("\n--- Tabela 2: Gap bruto por subgrupo ---")

def gap_pct(sub, var_grupo, grupos, nome_grupo):
    rows = []
    for g in grupos:
        b = sub[(sub["negro"] == 0) & (sub[var_grupo] == g)]
        n = sub[(sub["negro"] == 1) & (sub[var_grupo] == g)]
        wb, wn = b["V1028"], n["V1028"]
        if len(b) < 30 or len(n) < 30:
            continue
        med_b = wquantile(b["renda_bruta"], wb, 0.5)
        med_n = wquantile(n["renda_bruta"], wn, 0.5)
        med_b_m = np.average(b["renda_bruta"], weights=wb)
        med_n_m = np.average(n["renda_bruta"], weights=wn)
        rows.append({
            "Subgrupo": g,
            "Mediana Brancos (R$)": round(med_b),
            "Mediana Negros (R$)":  round(med_n),
            "Gap Mediana (%)":      round((med_b - med_n) / med_b * 100, 1),
            "Média Brancos (R$)":   round(med_b_m),
            "Média Negros (R$)":    round(med_n_m),
            "Gap Média (%)":        round((med_b_m - med_n_m) / med_b_m * 100, 1),
        })
    return pd.DataFrame(rows).assign(Dimensão=nome_grupo)

g_genero  = gap_pct(df_all, "sexo_fem", [0, 1], "Sexo")
g_faixa   = gap_pct(df_all, "faixa_etaria", FAIXA_ORDER, "Faixa etária")
g_educ    = gap_pct(df_all, "educ_cat", EDUC_ORDER, "Escolaridade")

g_genero["Subgrupo"]  = g_genero["Subgrupo"].map({0: "Homem", 1: "Mulher"})
g_educ["Subgrupo"]    = g_educ["Subgrupo"].map(EDUC_LABEL)

tab2 = pd.concat([g_genero, g_faixa, g_educ], ignore_index=True)
tab2 = tab2[["Dimensão", "Subgrupo", "Mediana Brancos (R$)", "Mediana Negros (R$)",
             "Gap Mediana (%)", "Média Brancos (R$)", "Média Negros (R$)", "Gap Média (%)"]]
tab2.to_csv(TABLES / "tab2_gap_bruto_subgrupos.csv", index=False)
print(tab2.to_string(index=False))
print("  tab2_gap_bruto_subgrupos.csv salvo.")

# ══════════════════════════════════════════════════════════════════════════════
# 4. TABELA 3 — REGRESSÕES MINCER COM CONTROLES PROGRESSIVOS
# ══════════════════════════════════════════════════════════════════════════════
print("\n--- Tabela 3: Regressões Mincer progressivas ---")

# Preparar variáveis para regressão (amostra 20%)
d = df.copy()
d["log_renda"]    = np.log(d["renda_bruta"])
d["exp"]          = (d["idade"] - d["educ_ord"] * 2 - 6).clip(0)
d["exp2"]         = d["exp"] ** 2 / 100
d["negro"]        = d["negro"].astype(float)
d["sexo_fem"]     = d["sexo_fem"].astype(float)
d["emprego_formal"]= d["emprego_formal"].fillna(0).astype(float)
d["setor_publico"] = d["setor_publico"].fillna(0).astype(float)
d["horas_c"]      = d["horas_c"].fillna(0)

# Dummies de UF, escolaridade e ocupação (prefixos únicos para evitar conflito)
uf_dummies   = pd.get_dummies(d["UF"],                        prefix="DUF",  drop_first=True)
educ_dummies = pd.get_dummies(d["educ_cat"],                  prefix="DESC", drop_first=True)
ocp_dummies  = pd.get_dummies(d["ocp_grupo_cbo"].astype(str), prefix="DOCP", drop_first=True)

d = pd.concat([d, uf_dummies, educ_dummies, ocp_dummies], axis=1)
d = d.dropna(subset=["log_renda", "negro", "sexo_fem", "educ_ord", "idade", "horas_c"])
w_reg = d["V1028"]

# Converter dummies para float
for col in [c for c in d.columns if c.startswith(("DUF_","DESC_","DOCP_"))]:
    d[col] = d[col].astype(float)

def mincer_ols(y, X, w):
    X = sm.add_constant(X)
    m = sm.WLS(y, X, weights=w).fit(cov_type="HC3")
    return m

uf_cols   = [c for c in d.columns if c.startswith("DUF_")]
educ_cols = [c for c in d.columns if c.startswith("DESC_")]
ocp_cols  = [c for c in d.columns if c.startswith("DOCP_")]

specs = {
    "M1 — Só raça":
        ["negro"],
    "M2 — + Sexo, escolaridade, experiência":
        ["negro", "sexo_fem"] + educ_cols + ["exp", "exp2"],
    "M3 — + Região (UF)":
        ["negro", "sexo_fem"] + educ_cols + ["exp", "exp2"] + uf_cols,
    "M4 — + Horas, formalidade, setor":
        ["negro", "sexo_fem"] + educ_cols + ["exp", "exp2"] + uf_cols +
        ["horas_c", "emprego_formal", "setor_publico"],
    "M5 — + Ocupação CBO":
        ["negro", "sexo_fem"] + educ_cols + ["exp", "exp2"] + uf_cols +
        ["horas_c", "emprego_formal", "setor_publico"] + ocp_cols,
}

rows3 = []
for nome, cols in specs.items():
    X = d[cols].astype(float)
    m = mincer_ols(d["log_renda"], X, w_reg)
    b_negro = m.params["negro"]
    se      = m.bse["negro"]
    pv      = m.pvalues["negro"]
    ci_l    = m.conf_int().loc["negro", 0]
    ci_h    = m.conf_int().loc["negro", 1]
    stars   = "***" if pv < 0.001 else ("**" if pv < 0.01 else ("*" if pv < 0.05 else ""))
    rows3.append({
        "Especificação": nome,
        "β negro": round(b_negro, 4),
        "SE": round(se, 4),
        "IC 95% inf.": round(ci_l, 4),
        "IC 95% sup.": round(ci_h, 4),
        "p-valor": f"{pv:.3e}",
        "Sig.": stars,
        "Gap (%)": f"{(np.exp(b_negro)-1)*100:.1f}%",
        "R²": round(m.rsquared, 4),
        "N": len(d),
    })
    print(f"  {nome}: β={b_negro:.4f} ({stars}) gap={(np.exp(b_negro)-1)*100:.1f}%")

tab3 = pd.DataFrame(rows3)
tab3.to_csv(TABLES / "tab3_mincer_progressivo.csv", index=False)
print("  tab3_mincer_progressivo.csv salvo.")

# ══════════════════════════════════════════════════════════════════════════════
# 5. TABELA 4 — TERMOS DE INTERAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
print("\n--- Tabela 4: Termos de interação ---")

# Grupos de escolaridade ordinais para interação
d["educ_alto"] = (d["educ_ord"] >= 6).astype(float)   # superior completo ou pós
d["educ_med"]  = (d["educ_ord"].between(4, 5)).astype(float)
d["negro_x_fem"]      = d["negro"] * d["sexo_fem"]
d["negro_x_educ_alto"]= d["negro"] * d["educ_alto"]
d["negro_x_educ_med"] = d["negro"] * d["educ_med"]
d["negro_x_exp"]      = d["negro"] * d["exp"]

base_cols = ["negro", "sexo_fem"] + educ_cols + ["exp", "exp2"] + uf_cols + \
            ["horas_c", "emprego_formal", "setor_publico"]

inter_cols = ["negro_x_fem", "negro_x_educ_alto", "negro_x_educ_med", "negro_x_exp"]
X_inter = d[base_cols + inter_cols].astype(float)
m_inter = mincer_ols(d["log_renda"], X_inter, w_reg)

rows4 = []
labels = {
    "negro":            "Raça (negro)",
    "negro_x_fem":      "Negro × Sexo feminino",
    "negro_x_educ_alto":"Negro × Superior completo/pós",
    "negro_x_educ_med": "Negro × Médio completo/sup. incomp.",
    "negro_x_exp":      "Negro × Experiência (anos)",
}
for var, lbl in labels.items():
    if var in m_inter.params:
        b  = m_inter.params[var]
        se = m_inter.bse[var]
        pv = m_inter.pvalues[var]
        ci = m_inter.conf_int().loc[var]
        stars = "***" if pv < 0.001 else ("**" if pv < 0.01 else ("*" if pv < 0.05 else "ns"))
        rows4.append({
            "Variável": lbl,
            "β": round(b, 4),
            "SE": round(se, 4),
            "IC 95% inf.": round(ci[0], 4),
            "IC 95% sup.": round(ci[1], 4),
            "p-valor": f"{pv:.3e}",
            "Sig.": stars,
            "Efeito (%)": f"{(np.exp(b)-1)*100:.2f}%",
        })
        print(f"  {lbl}: β={b:.4f} {stars}")

tab4 = pd.DataFrame(rows4)
tab4.to_csv(TABLES / "tab4_interacoes.csv", index=False)
print("  tab4_interacoes.csv salvo.")
print(f"  R² modelo de interação: {m_inter.rsquared:.4f}")

# ══════════════════════════════════════════════════════════════════════════════
# 6. FIGURA 1 — DENSIDADE DO LOG(SALÁRIO) POR RAÇA
# ══════════════════════════════════════════════════════════════════════════════
print("\n--- Figura 1: Densidade log(salário) por raça ---")

from scipy.stats import gaussian_kde

fig, ax = plt.subplots(figsize=(9, 5))

for label, color, mask in [
    ("Brancos", C_BRANCO, df_all["negro"] == 0),
    ("Negros",  C_NEGRO,  df_all["negro"] == 1),
]:
    sub  = df_all[mask]["log_renda"].dropna()
    w_s  = df_all[mask & df_all["log_renda"].notna()]["V1028"]
    # KDE ponderada via amostragem bootstrap
    idx  = np.random.choice(len(sub), size=min(50_000, len(sub)),
                             p=w_s.values / w_s.sum(), replace=True)
    vals = sub.iloc[idx].values
    kde  = gaussian_kde(vals, bw_method=0.15)
    xs   = np.linspace(vals.min(), vals.max(), 500)
    ax.fill_between(xs, kde(xs), alpha=0.25, color=color)
    ax.plot(xs, kde(xs), color=color, lw=2, label=label)
    med_log   = float(np.average(sub, weights=w_s))
    kde_y_med = float(kde(np.array([med_log]))[0])
    ax.axvline(med_log, color=color, lw=1.4, ls="--", alpha=0.8)
    ax.text(med_log + 0.05, kde_y_med * 0.6,
            f"Média\n{label[:3]}: {med_log:.2f}", fontsize=8.5, color=color)

ax.set_xlabel("Log(Rendimento mensal, R$)", fontsize=12)
ax.set_ylabel("Densidade (estimativa ponderada)", fontsize=12)
ax.set_title("Distribuição do Log-Salário por Grupo Racial\n"
             "PNAD Contínua 2016–2025 — empregados com renda positiva",
             fontsize=13, color=C_DARK, fontweight="bold")
ax.legend(fontsize=11)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x, _: f"R${np.exp(x):,.0f}"))
ax.set_xticks(np.log([500, 1000, 2000, 5000, 10000, 20000]))
ax.tick_params(axis="x", rotation=30)
fig.tight_layout()
fig.savefig(FIGURES / "fig1_densidade_log_salario.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  fig1_densidade_log_salario.png salvo.")

# ══════════════════════════════════════════════════════════════════════════════
# 7. FIGURA 2 — HEATMAP GAP (RAÇA × GÊNERO × ESCOLARIDADE)
# ══════════════════════════════════════════════════════════════════════════════
print("\n--- Figura 2: Heatmap gap raça × gênero × escolaridade ---")

SEXO_LABEL = {0: "Homem", 1: "Mulher"}
educ_grps  = EDUC_GRP_ORDER
sexo_grps  = [0, 1]

heat_med = np.full((len(educ_grps), len(sexo_grps)), np.nan)
heat_n   = np.full((len(educ_grps), len(sexo_grps)), np.nan)

for ei, eg in enumerate(educ_grps):
    for si, sg in enumerate(sexo_grps):
        b  = df_all[(df_all["negro"]==0) & (df_all["educ_grupo"]==eg) & (df_all["sexo_fem"]==sg)]
        n  = df_all[(df_all["negro"]==1) & (df_all["educ_grupo"]==eg) & (df_all["sexo_fem"]==sg)]
        if len(b) < 30 or len(n) < 30:
            continue
        wb, wn = b["V1028"], n["V1028"]
        mb = wquantile(b["renda_bruta"], wb, 0.5)
        mn = wquantile(n["renda_bruta"], wn, 0.5)
        heat_med[ei, si] = (mb - mn) / mb * 100
        heat_n[ei, si]   = (
            np.average(np.log(b["renda_bruta"]), weights=wb) -
            np.average(np.log(n["renda_bruta"]), weights=wn)
        ) * 100

cmap = LinearSegmentedColormap.from_list("rg", ["#FFCDD2", "#B71C1C"])
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, data, title in zip(axes,
    [heat_med, heat_n],
    ["Gap na mediana (%)", "Gap na média do log-salário (p.p. log)"]):
    im = ax.imshow(data, cmap=cmap, vmin=0, vmax=np.nanmax(data)*1.05, aspect="auto")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Homem", "Mulher"], fontsize=11)
    ax.set_yticks(range(len(educ_grps)))
    ax.set_yticklabels([e.replace("\n", " ") for e in educ_grps], fontsize=10)
    for ei in range(len(educ_grps)):
        for si in range(2):
            v = data[ei, si]
            if not np.isnan(v):
                ax.text(si, ei, f"{v:.1f}%", ha="center", va="center",
                        fontsize=12, fontweight="bold",
                        color="white" if v > np.nanmax(data)*0.5 else "#4A0000")
    plt.colorbar(im, ax=ax, fraction=0.04, pad=0.04)
    ax.set_title(title, fontsize=12, color=C_DARK, fontweight="bold")

fig.suptitle("Heatmap: Gap Racial por Gênero e Escolaridade\n"
             "PNAD Contínua 2016–2025 (empregados, ponderado por V1028)",
             fontsize=13, color=C_DARK, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(FIGURES / "fig2_heatmap_gap_genero_educ.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  fig2_heatmap_gap_genero_educ.png salvo.")

# ══════════════════════════════════════════════════════════════════════════════
# 8. FIGURA 4 — GAP POR FAIXA ETÁRIA (LIFE-CYCLE)
# ══════════════════════════════════════════════════════════════════════════════
print("\n--- Figura 4: Gap por faixa etária (life-cycle) ---")

faixas = [f for f in FAIXA_ORDER if f in df_all["faixa_etaria"].unique()]
gaps_brutos    = []
gaps_log_bruto = []

for f in faixas:
    b = df_all[(df_all["negro"]==0) & (df_all["faixa_etaria"]==f)]
    n = df_all[(df_all["negro"]==1) & (df_all["faixa_etaria"]==f)]
    wb, wn = b["V1028"], n["V1028"]
    mb  = wquantile(b["renda_bruta"], wb, 0.5)
    mn  = wquantile(n["renda_bruta"], wn, 0.5)
    gaps_brutos.append((mb - mn) / mb * 100)
    lb  = np.average(b["log_renda"], weights=wb)
    ln  = np.average(n["log_renda"], weights=wn)
    gaps_log_bruto.append((lb - ln) * 100)

# Gap controlado (coeficiente de raça em OLS por faixa)
gaps_ctrl = []
for f in faixas:
    sub_f = d[d["faixa_etaria"] == f].copy()
    if len(sub_f) < 200:
        gaps_ctrl.append(np.nan); continue
    cols_f = ["negro", "sexo_fem"] + educ_cols + ["exp", "exp2"] + \
             ["horas_c", "emprego_formal", "setor_publico"]
    X_f = sub_f[cols_f].astype(float)
    try:
        m_f = mincer_ols(sub_f["log_renda"], X_f, sub_f["V1028"])
        gaps_ctrl.append(m_f.params["negro"] * 100)
    except Exception:
        gaps_ctrl.append(np.nan)

fig, ax = plt.subplots(figsize=(9, 5))
xs = np.arange(len(faixas))
ax.bar(xs - 0.2, gaps_brutos,    0.38, label="Gap bruto (mediana)", color=C_NEGRO,  alpha=0.8)
ax.bar(xs + 0.2, [-g if not np.isnan(g) else 0 for g in gaps_ctrl], 0.38,
       label="Gap controlado (OLS log, p.p.)", color="#7B1FA2", alpha=0.8)
ax.plot(xs - 0.2, gaps_brutos,    "o-", color=C_NEGRO,  lw=1.5, ms=5)
ax.plot(xs + 0.2, [-g if not np.isnan(g) else np.nan for g in gaps_ctrl],
        "s--", color="#7B1FA2", lw=1.5, ms=5)

ax.set_xticks(xs); ax.set_xticklabels(faixas, fontsize=11)
ax.set_xlabel("Faixa etária", fontsize=12)
ax.set_ylabel("Gap racial (%) — quanto negros recebem a menos", fontsize=11)
ax.set_title("Curva de Ciclo de Vida — Gap Racial por Faixa Etária\n"
             "PNAD Contínua 2016–2025 | Bruto (mediana) vs Controlado (OLS)",
             fontsize=13, color=C_DARK, fontweight="bold")
ax.legend(fontsize=11)
ax.set_ylim(0, max(gaps_brutos) * 1.3)
for i, (gb, gc) in enumerate(zip(gaps_brutos, gaps_ctrl)):
    ax.text(i - 0.2, gb + 0.5, f"{gb:.1f}%", ha="center", va="bottom", fontsize=9, color=C_NEGRO)
    if not np.isnan(gc):
        ax.text(i + 0.2, -gc + 0.5, f"{-gc:.1f}%", ha="center", va="bottom", fontsize=9, color="#7B1FA2")
fig.tight_layout()
fig.savefig(FIGURES / "fig4_gap_faixa_etaria.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  fig4_gap_faixa_etaria.png salvo.")

# ══════════════════════════════════════════════════════════════════════════════
# 9. SUMÁRIO FINAL
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  SUMÁRIO — TABELAS E FIGURAS COMPLEMENTARES")
print("="*60)
print(f"  Tab 1  — Descritiva racial: outputs/tables/tab1_descritiva_racial.csv")
print(f"  Tab 2  — Gap por subgrupo: outputs/tables/tab2_gap_bruto_subgrupos.csv")
print(f"  Tab 3  — Mincer progressivo: outputs/tables/tab3_mincer_progressivo.csv")
print(f"  Tab 4  — Interações: outputs/tables/tab4_interacoes.csv")
print(f"  Fig 1  — Densidade log-salário: outputs/figures/fig1_densidade_log_salario.png")
print(f"  Fig 2  — Heatmap gap: outputs/figures/fig2_heatmap_gap_genero_educ.png")
print(f"  Fig 4  — Life-cycle: outputs/figures/fig4_gap_faixa_etaria.png")
print("="*60)
print("=== CONCLUÍDO ===")
