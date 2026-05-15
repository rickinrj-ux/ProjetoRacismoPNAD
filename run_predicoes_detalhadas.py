"""
run_predicoes_detalhadas.py
Predicoes por perfil demografico (medias observadas + IC95%)
e analise contrafactual via Oaxaca-Blinder com educ_ord.
Executa no Spyder Python.
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import statsmodels.formula.api as smf
from pathlib import Path

ROOT    = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
FIGURES = ROOT / "outputs" / "figures"
TABLES  = ROOT / "outputs" / "tables"

COLS = ["negro", "sexo_fem", "educ_cat", "educ_ord",
        "idade_c", "idade_sq",
        "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
        "horas_c", "emprego_formal", "conta_propria", "trab_domestico",
        "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
        "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa",
        "log_renda", "renda_bruta", "pea"]

print("Carregando dados ...")
df = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=COLS)

OCC_VARS = ["horas_c", "emprego_formal", "conta_propria", "trab_domestico",
            "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
            "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa"]
HAS_OCC = all(c in df.columns for c in OCC_VARS) and df[OCC_VARS].notna().any().any()

mask = (df["pea"] == 1) & (df["renda_bruta"] > 0) & (df["negro"].notna())
df = df[mask].dropna(subset=["log_renda", "negro", "educ_ord", "sexo_fem",
                               "idade_c", "idade_sq",
                               "pct_negro_upa_z", "tx_desemprego_upa_z",
                               "media_educ_upa_z"])

# Amostra 20% para o contrafactual
rng = np.random.default_rng(42)
idx = rng.choice(len(df), size=int(len(df) * 0.20), replace=False)
samp = df.iloc[idx].reset_index(drop=True)
print(f"Total (PEA c/ renda): {len(df):,}  |  Amostra contrafactual: {len(samp):,}")

# ── Figura 1: Rendimento medio observado por perfil ─────────────────────────
# Filtra 3 niveis de educacao claros
educ_sel = ["fund_completo", "medio_completo", "superior_completo"]
educ_labels = {"fund_completo": "Fund.\nCompleto",
               "medio_completo": "Médio\nCompleto",
               "superior_completo": "Superior\nCompleto"}

df_sel = df[df["educ_cat"].isin(educ_sel)].copy()
grp = df_sel.groupby(["negro", "sexo_fem", "educ_cat"])["log_renda"].agg(
    mean="mean", sem="sem", count="count"
).reset_index()
grp["renda"]   = np.exp(grp["mean"])
grp["ci95_hi"] = np.exp(grp["mean"] + 1.96 * grp["sem"]) - grp["renda"]
grp["ci95_lo"] = grp["renda"] - np.exp(grp["mean"] - 1.96 * grp["sem"])

COLORS = {(0, 0): "#1565C0",   # Branco Homem
          (0, 1): "#5C9BD6",   # Branco Mulher
          (1, 0): "#B71C1C",   # Negro Homem
          (1, 1): "#E57373"}   # Negro Mulher
LABELS = {(0,0):"Branco\nHomem", (0,1):"Branco\nMulher",
          (1,0):"Negro\nHomem",  (1,1):"Negro\nMulher"}

group_order = [(0,0),(0,1),(1,0),(1,1)]
x = np.arange(4)
w = 0.22

fig, axes = plt.subplots(1, 3, figsize=(15, 6), sharey=True)
for ax, educ in zip(axes, educ_sel):
    for i, gk in enumerate(group_order):
        sub = grp[(grp["negro"]==gk[0]) & (grp["sexo_fem"]==gk[1]) & (grp["educ_cat"]==educ)]
        val = sub["renda"].values[0] if len(sub) else 0
        lo  = sub["ci95_lo"].values[0] if len(sub) else 0
        hi  = sub["ci95_hi"].values[0] if len(sub) else 0
        bar = ax.bar(i, val, width=0.65, color=COLORS[gk], alpha=0.85)
        ax.errorbar(i, val, yerr=[[lo],[hi]], fmt='none', color='#333', capsize=4, lw=1.2)
        ax.text(i, val + hi + 20, f"R${val:.0f}", ha='center', va='bottom',
                fontsize=8, fontweight='bold', rotation=0)
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[g] for g in group_order], fontsize=8)
    ax.set_title(educ_labels[educ], fontsize=11, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

axes[0].set_ylabel("Rendimento mensal médio observado (R$)", fontsize=11)
patches = [mpatches.Patch(color=COLORS[g], label=LABELS[g]) for g in group_order]
fig.legend(handles=patches, loc='lower center', ncol=4, fontsize=9,
           bbox_to_anchor=(0.5, -0.04))
fig.suptitle("Rendimento Mensal Médio por Perfil Demográfico e Escolaridade\n"
             "(ocupados com renda positiva — PNAD Contínua 2016–2025 | IC 95%)",
             fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(FIGURES / "predicoes_por_perfil.png", dpi=150, bbox_inches='tight')
plt.close()
print("predicoes_por_perfil.png salvo.")

# Salva tabela
out = grp[["negro","sexo_fem","educ_cat","renda","count"]].copy()
out.columns = ["Negro","SexoFem","Escolaridade","Renda_Obs","N"]
out.to_csv(TABLES / "predicoes_por_perfil.csv", index=False, encoding='utf-8')

# ── Figura 2: Contrafactual Oaxaca-Blinder (educ_ord continuo) ────────────
_OCC_F = ("horas_c + emprego_formal + conta_propria + trab_domestico"
          " + ocp_dirigente + ocp_profissional + ocp_tecnico + ocp_administrativo"
          " + ocp_servicos + ocp_agro + ocp_operario + ocp_operador + ocp_ffaa")
if HAS_OCC:
    FORMULA = ("log_renda ~ educ_ord + sexo_fem + idade_c + idade_sq"
               " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
               f" + {_OCC_F}")
    print("Contrafactual com variáveis ocupacionais.")
else:
    FORMULA = ("log_renda ~ educ_ord + sexo_fem + idade_c + idade_sq"
               " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z")
    print("Contrafactual sem variáveis ocupacionais (ausentes).")

print("Ajustando OLS por grupo racial (contrafactual) ...")
m_b = smf.ols(FORMULA, data=samp[samp["negro"] == 0]).fit()
m_n = smf.ols(FORMULA, data=samp[samp["negro"] == 1]).fit()

# Aplica coeficientes de brancos as caracteristicas de negros (Oaxaca counterfactual)
df_blacks = samp[samp["negro"] == 1].copy()
actual_white  = samp[samp["negro"] == 0]["log_renda"].mean()
actual_black  = df_blacks["log_renda"].mean()
pred_counter  = m_b.predict(df_blacks)
counter_mean  = pred_counter.mean()

gap_actual   = actual_white - actual_black
gap_counter  = actual_white - counter_mean
gap_closed   = (gap_actual - gap_counter) / gap_actual * 100

pct_actual  = (np.exp(gap_actual)  - 1) * 100
pct_counter = (np.exp(gap_counter) - 1) * 100

print(f"\nRenda media brancos (real):         R${np.exp(actual_white):.2f}")
print(f"Renda media negros (real):          R${np.exp(actual_black):.2f}")
print(f"Renda negros (retornos de branco):  R${np.exp(counter_mean):.2f}")
print(f"Gap real:                           {pct_actual:.1f}%")
print(f"Gap residual (retornos iguais):     {pct_counter:.1f}%")
print(f"Fechamento do gap:                  {gap_closed:.1f}%")

groups_cf = ["Brancos\n(observado)", "Negros\n(observado)",
             "Negros\n(contrafactual:\nretornos de brancos)"]
values_cf = [np.exp(actual_white), np.exp(actual_black), np.exp(counter_mean)]
colors_cf = ["#1565C0", "#B71C1C", "#FF8F00"]

fig, ax = plt.subplots(figsize=(9, 6))
bars = ax.bar(groups_cf, values_cf, color=colors_cf, alpha=0.85, width=0.5)
for bar, val in zip(bars, values_cf):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 15,
            f"R${val:.0f}", ha='center', va='bottom', fontsize=13, fontweight='bold')

# Anotacoes de gap
ax.annotate("", xy=(0.15, values_cf[0]), xytext=(0.85, values_cf[1]),
            arrowprops=dict(arrowstyle='<->', color='#555', lw=2))
ax.text(0.5, (values_cf[0]+values_cf[1])/2,
        f"Gap real\n{pct_actual:.1f}%",
        ha='center', va='center', fontsize=10, color='#333',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#aaa', alpha=0.9))

ax.annotate("", xy=(1.15, values_cf[0]), xytext=(1.85, values_cf[2]),
            arrowprops=dict(arrowstyle='<->', color='#E65100', lw=2, linestyle='dashed'))
ax.text(1.5, (values_cf[0]+values_cf[2])/2 + 60,
        f"Gap residual\n{pct_counter:.1f}%\n({gap_closed:.0f}% fechado)",
        ha='center', va='bottom', fontsize=10, color='#E65100',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFF8E1', edgecolor='#FF8F00', alpha=0.9))

ax.set_ylabel("Rendimento mensal médio (R$)", fontsize=11)
ax.set_title("Análise Contrafactual: Quanto Ganhariam os Trabalhadores Negros\n"
             "se os Retornos às Suas Características Fossem Iguais aos dos Brancos?",
             fontsize=11, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_ylim(0, max(values_cf) * 1.35)
plt.tight_layout()
plt.savefig(FIGURES / "predicoes_contrafactual.png", dpi=150, bbox_inches='tight')
plt.close()
print("predicoes_contrafactual.png salvo.")

# Tabela contrafactual
cf_out = pd.DataFrame({
    "Grupo": groups_cf,
    "Renda_Media": [f"R${v:.2f}" for v in values_cf],
    "Gap_vs_Branco": ["—", f"{pct_actual:.1f}%", f"{pct_counter:.1f}%"],
})
cf_out.to_csv(TABLES / "predicoes_contrafactual.csv", index=False, encoding='utf-8')

print("\n=== PREDICOES CONCLUIDAS ===")
print(f"Gap real: {pct_actual:.1f}%  |  Gap residual: {pct_counter:.1f}%  |  Fechamento: {gap_closed:.1f}%")
