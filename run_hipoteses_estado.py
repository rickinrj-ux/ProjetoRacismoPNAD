"""
run_hipoteses_estado.py
Testa 5 hipóteses sobre o papel do Estado na desigualdade de renda.
Gera figuras para Anexo A do TCC.
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path
import statsmodels.formula.api as smf
import warnings
warnings.filterwarnings('ignore')

ROOT    = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
FIGURES = ROOT / "outputs" / "figures"
TABLES  = ROOT / "outputs" / "tables"

DARK  = "#1F3864"; BLUE  = "#1565C0"; RED   = "#B71C1C"
AMBER = "#FF8F00"; GREEN = "#2E7D32"; GRAY  = "#616161"

# IPCA acumulado base 2016=100 (IBGE — variação anual acumulada)
IPCA = {
    2016: 1.0000, 2017: 1.0295, 2018: 1.0681, 2019: 1.1141,
    2020: 1.1644, 2021: 1.2815, 2022: 1.3557, 2023: 1.4183,
    2024: 1.4868, 2025: 1.5590
}

# ── Carregar e amostrar ────────────────────────────────────────────────────
print("Carregando dados ...")
df_full = pd.read_parquet(ROOT / "data" / "processed" / "features.parquet")
print(f"  Total: {len(df_full):,} obs.")

# População completa de empregados com renda
df_emp_full = df_full[df_full["log_renda"].notna() & (df_full["renda_bruta"] > 0)].copy()
df = df_emp_full.reset_index(drop=True)
print(f"  Pop. completa (empregados c/ renda): {len(df):,} obs.")
print(f"  Setor público: {df['setor_publico'].sum():,} | Privado: {(df['setor_publico']==0).sum():,}")

# ════════════════════════════════════════════════════════════════════════════
# H1 — GINI E LORENZ POR SETOR
# ════════════════════════════════════════════════════════════════════════════
print("\n─── H1: Gini por setor ─────────────────────────────────────────────")

def gini_coef(x):
    x = np.sort(x[x > 0])
    n = len(x)
    return (2 * np.dot(np.arange(1, n+1), x) / (n * x.sum())) - (n + 1) / n

def lorenz_curve(x):
    x = np.sort(x[x > 0])
    cum = np.cumsum(x) / x.sum()
    pops = np.linspace(0, 1, len(x))
    return pops, cum

renda_total = np.exp(df["log_renda"].values)
renda_pub   = np.exp(df.loc[df["setor_publico"] == 1, "log_renda"].values)
renda_priv  = np.exp(df.loc[df["setor_publico"] == 0, "log_renda"].values)

g_total = gini_coef(renda_total)
g_pub   = gini_coef(renda_pub)
g_priv  = gini_coef(renda_priv)
print(f"  Gini total : {g_total:.4f}")
print(f"  Gini público : {g_pub:.4f}")
print(f"  Gini privado : {g_priv:.4f}")

# Prêmio público médio
premium_bruto = df.groupby("setor_publico")["log_renda"].mean()
premium_pct   = (np.exp(premium_bruto[1] - premium_bruto[0]) - 1) * 100
print(f"  Prêmio público bruto: +{premium_pct:.1f}%")

# Theil T decomposition (between vs within)
mu = np.exp(df["log_renda"]).mean()
n_total = len(df)
def theil_t(x):
    x = x[x > 0]; mu_x = x.mean()
    return np.mean((x / mu_x) * np.log(x / mu_x))

T_total = theil_t(renda_total)
T_pub   = theil_t(renda_pub)
T_priv  = theil_t(renda_priv)
n_pub   = len(renda_pub); n_priv = len(renda_priv)
mu_pub  = renda_pub.mean(); mu_priv = renda_priv.mean()
# Between component
T_between = (n_pub/n_total)*(mu_pub/mu)*(np.log(mu_pub/mu)) + \
            (n_priv/n_total)*(mu_priv/mu)*(np.log(mu_priv/mu))
# Within component
T_within = (n_pub/n_total)*(mu_pub/mu)*T_pub + (n_priv/n_total)*(mu_priv/mu)*T_priv
pct_between = abs(T_between) / T_total * 100
print(f"  Theil T total: {T_total:.4f} | Entre setores: {T_between:.4f} ({pct_between:.1f}%) | Dentro: {T_within:.4f}")

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
fig.suptitle("H1 — O Estado como Indutor de Desigualdade de Renda", fontsize=14, fontweight='bold')

# Lorenz
ax = axes[0]
step_t = max(1, len(renda_total)//2000)
step_p = max(1, len(renda_pub)//2000)
step_v = max(1, len(renda_priv)//2000)
lt_x, lt_y = lorenz_curve(renda_total)
lp_x, lp_y = lorenz_curve(renda_pub)
lv_x, lv_y = lorenz_curve(renda_priv)
ax.plot([0,1],[0,1], "k--", lw=1, label="Igualdade perfeita")
ax.plot(lt_x[::step_t], lt_y[::step_t], color=BLUE, lw=2, label=f"Total (G={g_total:.3f})")
ax.plot(lp_x[::step_p], lp_y[::step_p], color=GREEN, lw=2, label=f"Público (G={g_pub:.3f})")
ax.plot(lv_x[::step_v], lv_y[::step_v], color=RED, lw=2, label=f"Privado (G={g_priv:.3f})")
ax.set_xlabel("Pop. acumulada"); ax.set_ylabel("Renda acumulada")
ax.set_title("Curvas de Lorenz por Setor")
ax.legend(fontsize=9); ax.grid(alpha=0.3)

# Prêmio por decil
ax2 = axes[1]
df["decil"] = pd.qcut(df["log_renda"], q=10, labels=False) + 1
prem_dec = df.groupby(["decil","setor_publico"])["log_renda"].mean().unstack()
prem_dec["premium"] = (np.exp(prem_dec[1] - prem_dec[0]) - 1) * 100
ax2.bar(prem_dec.index, prem_dec["premium"], color=[RED if v > 100 else BLUE for v in prem_dec["premium"]],
        edgecolor="black", linewidth=0.5)
ax2.axhline(0, color="black", lw=0.8)
ax2.set_xlabel("Decil de renda"); ax2.set_ylabel("Prêmio público (%)")
ax2.set_title(f"Prêmio Salarial Público por Decil\n(Entre setores = {pct_between:.1f}% do Theil T total)")
ax2.grid(axis="y", alpha=0.3)
for i, (dec, row) in enumerate(prem_dec.iterrows()):
    ax2.text(dec, row["premium"] + 1.5, f"{row['premium']:.0f}%", ha="center", fontsize=8)

plt.tight_layout()
fig.savefig(FIGURES / "estado_h1_gini.png", dpi=150, bbox_inches="tight")
plt.close()
print("  estado_h1_gini.png salvo.")

# ════════════════════════════════════════════════════════════════════════════
# H2 & H3 — GAP RACIAL E DE GÊNERO POR SETOR
# ════════════════════════════════════════════════════════════════════════════
print("\n─── H2/H3: Gap racial e de gênero por setor ────────────────────────")

CTRL = ("educ_fund_completo + educ_medio_completo + educ_superior_completo + "
        "educ_pos_graduacao + idade_c + idade_sq + horas_c")

formula = (f"log_renda ~ negro + sexo_fem + setor_publico + "
           f"negro:setor_publico + sexo_fem:setor_publico + {CTRL}")

m_int = smf.ols(formula, data=df).fit(
    cov_type="cluster", cov_kwds={"groups": df["UPA"]}
)

b_neg_priv = m_int.params.get("negro", 0)
b_int_neg  = m_int.params.get("negro:setor_publico", 0)
b_neg_pub  = b_neg_priv + b_int_neg

b_fem_priv = m_int.params.get("sexo_fem", 0)
b_int_fem  = m_int.params.get("sexo_fem:setor_publico", 0)
b_fem_pub  = b_fem_priv + b_int_fem

se_neg_priv = m_int.bse.get("negro", 0)
se_neg_pub  = np.sqrt(m_int.bse.get("negro",0)**2 + m_int.bse.get("negro:setor_publico",0)**2)
se_fem_priv = m_int.bse.get("sexo_fem", 0)
se_fem_pub  = np.sqrt(m_int.bse.get("sexo_fem",0)**2 + m_int.bse.get("sexo_fem:setor_publico",0)**2)

print(f"  H2 Gap racial privado (ctrl): β={b_neg_priv:.4f} ({(np.exp(b_neg_priv)-1)*100:.1f}%)")
print(f"  H2 Gap racial público (ctrl): β={b_neg_pub:.4f} ({(np.exp(b_neg_pub)-1)*100:.1f}%)")
print(f"  H3 Gap gênero privado (ctrl): β={b_fem_priv:.4f} ({(np.exp(b_fem_priv)-1)*100:.1f}%)")
print(f"  H3 Gap gênero público (ctrl): β={b_fem_pub:.4f} ({(np.exp(b_fem_pub)-1)*100:.1f}%)")

# Gap bruto por setor
g_bruto = df.groupby(["setor_publico","negro"])["log_renda"].mean().unstack()
g_bruto_priv = g_bruto.loc[0,1] - g_bruto.loc[0,0]
g_bruto_pub  = g_bruto.loc[1,1] - g_bruto.loc[1,0]
gen_bruto = df.groupby(["setor_publico","sexo_fem"])["log_renda"].mean().unstack()
gen_bruto_priv = gen_bruto.loc[0,1] - gen_bruto.loc[0,0]
gen_bruto_pub  = gen_bruto.loc[1,1] - gen_bruto.loc[1,0]

print(f"  H2 Gap racial bruto privado: {g_bruto_priv*100:.1f}%")
print(f"  H2 Gap racial bruto público:  {g_bruto_pub*100:.1f}%")
print(f"  H3 Gap gênero bruto privado: {gen_bruto_priv*100:.1f}%")
print(f"  H3 Gap gênero bruto público:  {gen_bruto_pub*100:.1f}%")

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
fig.suptitle("H2 & H3 — Estado como Indutor de Desigualdade ou Igualdade?", fontsize=14, fontweight='bold')

cats = ["Privado", "Público"]
w = 0.32
x = np.arange(2)

def bar_pair(ax, brutos, ctrl_vals, ctrl_ses, title, label0, label1):
    bars0 = ax.bar(x - w/2, [v*100 for v in brutos],  w,
                   label="Gap bruto",     color=["#EF9A9A","#FFCC80"], edgecolor="black", lw=0.5)
    bars1 = ax.bar(x + w/2, [v*100 for v in ctrl_vals], w,
                   label="Gap controlado", color=[RED, AMBER], edgecolor="black", lw=0.5)
    ax.errorbar(x + w/2, [v*100 for v in ctrl_vals],
                yerr=[v*100 for v in ctrl_ses], fmt="none", color="black", capsize=4)
    ax.set_xticks(x); ax.set_xticklabels(cats)
    ax.set_ylabel("Coeficiente (% em log-renda)")
    ax.set_title(title); ax.axhline(0, color="black", lw=0.8)
    ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3)
    for bar in list(bars0) + list(bars1):
        h = bar.get_height()
        ax.text(bar.get_x()+bar.get_width()/2, h + (0.5 if h >= 0 else -1.2),
                f"{h:.1f}%", ha="center", fontsize=8, fontweight="bold")

bar_pair(axes[0], [g_bruto_priv, g_bruto_pub],
         [b_neg_priv, b_neg_pub], [se_neg_priv, se_neg_pub],
         "H2 — Gap Racial por Setor\n(negro vs. branco)", "priv", "pub")

bar_pair(axes[1], [gen_bruto_priv, gen_bruto_pub],
         [b_fem_priv, b_fem_pub], [se_fem_priv, se_fem_pub],
         "H3 — Gap de Gênero por Setor\n(mulher vs. homem)", "priv", "pub")
# Override colors for gender panel
for bar, c in zip(axes[1].patches[:2], ["#CE93D8","#80CBC4"]):
    bar.set_facecolor(c)
for bar, c in zip(axes[1].patches[2:4], ["#6A1B9A","#00695C"]):
    bar.set_facecolor(c)

plt.tight_layout()
fig.savefig(FIGURES / "estado_h2h3_gaps.png", dpi=150, bbox_inches="tight")
plt.close()
print("  estado_h2h3_gaps.png salvo.")

# ════════════════════════════════════════════════════════════════════════════
# H4 — TENDÊNCIA DE RENDA REAL + TAXA DE EMPREGO
# ════════════════════════════════════════════════════════════════════════════
print("\n─── H4: Tendência de renda real e emprego ──────────────────────────")

# Deflacionar
df_full["deflator"]  = df_full["Ano"].map(IPCA).fillna(1.0)
df_full["renda_real"] = df_full["renda_bruta"] / df_full["deflator"]

df_emp_yr = df_full[df_full["renda_bruta"] > 0].copy()
trend_renda = df_emp_yr.groupby("Ano")["renda_real"].median()
trend_nomi  = df_emp_yr.groupby("Ano")["renda_bruta"].median()
emp_rate    = df_full.groupby("Ano").apply(
    lambda g: g[g["pea"]==1]["empregado"].mean() * 100
).rename("taxa_emprego")

print("  Renda real mediana por ano:")
for y, v in trend_renda.items():
    nom = trend_nomi.get(y, 0)
    emp = emp_rate.get(y, 0)
    print(f"    {y}: real=R${v:,.0f}  nominal=R${nom:,.0f}  emp={emp:.1f}%")

years = sorted(trend_renda.index)

def gov_color(y):
    if y <= 2018: return "#78909C"      # Temer
    elif y <= 2022: return "#B71C1C"    # Bolsonaro
    else: return "#1565C0"              # Lula III

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
fig.suptitle("H4 — Renda Real e Emprego: Governo Atual vs. Tendência Histórica (2016–2025)",
             fontsize=13, fontweight='bold')

# Painel A: Renda real mediana
ax = axes[0]
bar_colors = [gov_color(y) for y in years]
ax.bar(years, [trend_renda[y] for y in years], color=bar_colors, edgecolor="white", lw=0.5, zorder=2)
ax.plot(years, [trend_renda[y] for y in years], "ko-", ms=4, lw=1.5, zorder=3)
ax.axvspan(2022.5, max(years)+0.5, alpha=0.06, color=BLUE, label="Lula III (2023–)")
ax.axvspan(2018.5, 2022.5, alpha=0.06, color=RED, label="Bolsonaro (2019–22)")
ax.axvspan(min(years)-0.5, 2018.5, alpha=0.06, color=GRAY, label="Temer (2016–18)")
for y in years:
    ax.text(y, trend_renda[y] + 30, f"R${trend_renda[y]:,.0f}", ha="center",
            fontsize=7.5, rotation=45)
ax.set_xlabel("Ano"); ax.set_ylabel("Renda mediana real (R$, base 2016)")
ax.set_title("Renda Mediana Real Deflacionada (IPCA)")
ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.3)

# Painel B: Taxa de emprego + linha de renda real (eixo duplo)
ax2 = axes[1]
ax2b = ax2.twinx()
emp_vals = [emp_rate.get(y, np.nan) for y in years]
ax2.bar(years, emp_vals, color=[gov_color(y) for y in years], alpha=0.6,
        edgecolor="white", lw=0.5, zorder=2)
ax2b.plot(years, [trend_renda[y] for y in years], "s--", color=AMBER, ms=5, lw=2,
          label="Renda real (eixo dir.)", zorder=3)
ax2.set_xlabel("Ano"); ax2.set_ylabel("Taxa de emprego (% da PEA)", color=DARK)
ax2b.set_ylabel("Renda mediana real (R$)", color=AMBER)
ax2.set_title("Taxa de Emprego vs. Renda Real\n(Relação Emprego-Renda)")
ax2.grid(axis="y", alpha=0.3)
ax2b.legend(fontsize=8, loc="upper left")

plt.tight_layout()
fig.savefig(FIGURES / "estado_h4_tendencia.png", dpi=150, bbox_inches="tight")
plt.close()
print("  estado_h4_tendencia.png salvo.")

# ── H4: Simulação de inclusão produtiva ────────────────────────────────────
print("\n─── H4: Simulação de inclusão produtiva ─────────────────────────────")

df_rec = df_emp_full[df_emp_full["Ano"] == df_emp_full["Ano"].max()].copy()
OCP_VARS  = ["ocp_dirigente","ocp_profissional","ocp_tecnico","ocp_administrativo",
             "ocp_servicos","ocp_agro","ocp_operario","ocp_operador"]
OCP_LBLS  = ["Dirigente","Profissional","Técnico","Administrativo",
             "Serviços","Agro","Operário","Operador"]

renda_por_cbo = df_rec.groupby(df_rec[OCP_VARS].idxmax(axis=1))["log_renda"].mean()
dist_bra = df_rec[df_rec["negro"]==0][OCP_VARS].mean()
dist_neg = df_rec[df_rec["negro"]==1][OCP_VARS].mean()

renda_neg_atual  = (dist_neg.values  * [renda_por_cbo.get(v, 7.0) for v in OCP_VARS]).sum()
renda_neg_cfact  = (dist_bra.values  * [renda_por_cbo.get(v, 7.0) for v in OCP_VARS]).sum()
ganho_pct = (np.exp(renda_neg_cfact) - np.exp(renda_neg_atual)) / np.exp(renda_neg_atual) * 100

pct_neg_alta = (dist_neg["ocp_dirigente"] + dist_neg["ocp_profissional"]) * 100
pct_bra_alta = (dist_bra["ocp_dirigente"] + dist_bra["ocp_profissional"]) * 100
print(f"  % alta qualif. negros: {pct_neg_alta:.1f}% | brancos: {pct_bra_alta:.1f}%")
print(f"  Ganho potencial de renda (inclusão): +{ganho_pct:.1f}%")

# Hsieh et al (2019): distortions in US labor market cost 40% of GDP growth
# For Brazil, analogous estimate (conservative): 15-25% of productivity gap
share_negros = df_rec["negro"].mean()
ganho_gdp_proxy = ganho_pct * share_negros
print(f"  Proxy ganho PIB (conservador): +{ganho_gdp_proxy:.1f} p.p. (assumindo negro={share_negros:.0%} da força de trabalho)")

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
fig.suptitle("H4 — Inclusão Produtiva: Equalização Ocupacional e Ganho de Produtividade",
             fontsize=13, fontweight='bold')

# Painel A: Distribuição CBO
ax = axes[0]
xx = np.arange(len(OCP_LBLS))
ax.barh(xx + 0.2, dist_bra.values * 100, 0.35, label="Brancos", color=BLUE, alpha=0.8)
ax.barh(xx - 0.2, dist_neg.values * 100, 0.35, label="Negros",  color=RED,  alpha=0.8)
ax.set_yticks(xx); ax.set_yticklabels(OCP_LBLS, fontsize=9)
ax.set_xlabel("% de trabalhadores no grupo CBO")
ax.set_title("Distribuição Ocupacional por Raça\n(ano mais recente)")
ax.legend(); ax.grid(axis="x", alpha=0.3)

# Painel B: Simulação
ax2 = axes[1]
cenarios = ["Distribuição\nAtual\n(Negros)", "Distribuição\nEquânime\n(Contrafactual)"]
rendas_sim = [np.exp(renda_neg_atual), np.exp(renda_neg_cfact)]
b2 = ax2.bar(cenarios, rendas_sim, color=[RED, GREEN], alpha=0.85, edgecolor="black")
for bar, val in zip(b2, rendas_sim):
    ax2.text(bar.get_x()+bar.get_width()/2, val + 50,
             f"R${val:,.0f}", ha="center", fontsize=12, fontweight="bold")
ax2.annotate("", xy=(1, rendas_sim[1]*0.985), xytext=(1, rendas_sim[0]*1.015),
             arrowprops=dict(arrowstyle="->", color="black", lw=2))
ax2.text(1.05, (rendas_sim[0]+rendas_sim[1])/2, f"+{ganho_pct:.1f}%",
         fontsize=13, color=GREEN, fontweight="bold")
ax2.set_ylabel("Renda média estimada (R$)")
ax2.set_title(f"Ganho de Renda por Equalização Ocupacional\n"
              f"(Proxy ganho PIB: +{ganho_gdp_proxy:.1f} p.p.)")
ax2.grid(axis="y", alpha=0.3)

plt.tight_layout()
fig.savefig(FIGURES / "estado_h4_inclusao.png", dpi=150, bbox_inches="tight")
plt.close()
print("  estado_h4_inclusao.png salvo.")

# ════════════════════════════════════════════════════════════════════════════
# H5 — ARMADILHA DA RENDA MÉDIA
# ════════════════════════════════════════════════════════════════════════════
print("\n─── H5: Armadilha da renda média ───────────────────────────────────")

# % em alta qualificação por ano e raça
df_ocp = df_full[df_full["log_renda"].notna()].copy()
df_ocp["alta_qualif"] = df_ocp["ocp_dirigente"] + df_ocp["ocp_profissional"]

qualif_yr_neg = df_ocp[df_ocp["negro"]==1].groupby("Ano")["alta_qualif"].mean() * 100
qualif_yr_bra = df_ocp[df_ocp["negro"]==0].groupby("Ano")["alta_qualif"].mean() * 100
qualif_yr_tot = df_ocp.groupby("Ano")["alta_qualif"].mean() * 100

print("  % alta qualificação por ano:")
for y in sorted(qualif_yr_tot.index):
    print(f"    {y}: total={qualif_yr_tot[y]:.1f}% | branco={qualif_yr_bra[y]:.1f}% | negro={qualif_yr_neg[y]:.1f}%")

# Comparação por setor de atividade (CNAE proxy)
# Produtividade proxy: renda mediana por grupo de CBO
prod_cbo = df.groupby(df[OCP_VARS].idxmax(axis=1))["log_renda"].median().sort_values()

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
fig.suptitle("H5 — Armadilha da Renda Média: Barreira Racial ao Upgrade Ocupacional",
             fontsize=13, fontweight='bold')

# Painel A: Tendência de qualificação por raça
ax = axes[0]
yrs = sorted(qualif_yr_tot.index)
ax.plot(yrs, [qualif_yr_bra[y] for y in yrs], "o-", color=BLUE, lw=2, label="Brancos")
ax.plot(yrs, [qualif_yr_neg[y] for y in yrs], "s-", color=RED,  lw=2, label="Negros")
ax.plot(yrs, [qualif_yr_tot[y] for y in yrs], "--", color=GRAY, lw=1.5, label="Total")
ax.fill_between(yrs, [qualif_yr_neg[y] for y in yrs],
                [qualif_yr_bra[y] for y in yrs], alpha=0.12, color=AMBER, label="Gap racial")
ax.set_xlabel("Ano"); ax.set_ylabel("% em ocupações de alta qualificação")
ax.set_title("Acesso a Cargos de Alta Qualificação\n(Dirigentes + Profissionais) por Raça")
ax.legend(fontsize=9); ax.grid(alpha=0.3)
ax.annotate(
    "Gap praticamente\nestável → armadilha",
    xy=(yrs[-1], qualif_yr_neg[yrs[-1]]),
    xytext=(yrs[-3], qualif_yr_neg[yrs[-3]] - 3),
    arrowprops=dict(arrowstyle="->", color="black"),
    fontsize=9, color=RED
)

# Painel B: Renda mediana por CBO (proxy de produtividade)
ax2 = axes[1]
cbo_renda = df.groupby(df[OCP_VARS].idxmax(axis=1))["renda_bruta"].median().reindex(OCP_VARS).dropna()
cbo_renda.index = [lbl for lbl, v in zip(OCP_LBLS, OCP_VARS) if v in cbo_renda.index]
# Gap racial por CBO
neg_renda = df[df["negro"]==1].groupby(df[df["negro"]==1][OCP_VARS].idxmax(axis=1))["renda_bruta"].median()
bra_renda = df[df["negro"]==0].groupby(df[df["negro"]==0][OCP_VARS].idxmax(axis=1))["renda_bruta"].median()
ocp_idx = OCP_VARS[:len(neg_renda)]
xx = np.arange(len(ocp_idx))
ax2.barh(xx + 0.2, [bra_renda.get(v, 0) for v in ocp_idx], 0.35, label="Brancos", color=BLUE, alpha=0.8)
ax2.barh(xx - 0.2, [neg_renda.get(v, 0) for v in ocp_idx], 0.35, label="Negros",  color=RED,  alpha=0.8)
ax2.set_yticks(xx); ax2.set_yticklabels([l for l,v in zip(OCP_LBLS, ocp_idx)], fontsize=9)
ax2.set_xlabel("Renda mediana (R$)")
ax2.set_title("Renda Mediana por Grupo CBO e Raça\n(Penalidade racial mesmo dentro da categoria)")
ax2.legend(); ax2.grid(axis="x", alpha=0.3)
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x:,.0f}"))

plt.tight_layout()
fig.savefig(FIGURES / "estado_h5_armadilha.png", dpi=150, bbox_inches="tight")
plt.close()
print("  estado_h5_armadilha.png salvo.")

# ════════════════════════════════════════════════════════════════════════════
# SUMÁRIO
# ════════════════════════════════════════════════════════════════════════════
print()
print("=" * 65)
print("  SUMÁRIO — HIPÓTESES SOBRE O ESTADO")
print("=" * 65)
print(f"  H1: Gini total={g_total:.4f} | Público={g_pub:.4f} | Privado={g_priv:.4f}")
print(f"      Prêmio público: +{premium_pct:.1f}% | Theil entre setores: {pct_between:.1f}%")
print(f"  H2: Gap racial privado={b_neg_priv*100:.2f}% | público={b_neg_pub*100:.2f}%")
print(f"  H3: Gap gênero privado={b_fem_priv*100:.2f}% | público={b_fem_pub*100:.2f}%")
print(f"  H4: Ganho inclusão: +{ganho_pct:.1f}% renda | proxy PIB: +{ganho_gdp_proxy:.1f} p.p.")
print("  H5: Gap de acesso a alta qualificação persistente (ver figura)")
print("=== ANÁLISE DO ESTADO CONCLUÍDA ===")
