"""
run_oaxaca_blinder.py
Decomposição de Oaxaca-Blinder do gap salarial racial.
Executa no Spyder Python (statsmodels, matplotlib disponíveis).
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
FIGURES.mkdir(parents=True, exist_ok=True)

COLS = ["negro", "sexo_fem", "idade_c", "idade_sq",
        "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
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

BASE_VARS = ["log_renda", "negro",
             "educ_medio_completo", "educ_superior_completo",
             "educ_pos_graduacao", "idade_c", "idade_sq", "sexo_fem",
             "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z"]

mask = (df["pea"] == 1) & (df["renda_bruta"] > 0) & (df["negro"].notna())
df = df[mask].dropna(subset=BASE_VARS)

rng = np.random.default_rng(42)
idx = rng.choice(len(df), size=int(len(df) * 0.20), replace=False)
df = df.iloc[idx].reset_index(drop=True)
n_b = int((df["negro"] == 0).sum())
n_n = int((df["negro"] == 1).sum())
print(f"Amostra: {len(df):,}  (brancos={n_b:,}, negros={n_n:,})")

_BASE_F = ("educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
           " + idade_c + idade_sq + sexo_fem"
           " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z")
_OCC_F  = ("horas_c + emprego_formal + conta_propria + trab_domestico"
           " + ocp_dirigente + ocp_profissional + ocp_tecnico + ocp_administrativo"
           " + ocp_servicos + ocp_agro + ocp_operario + ocp_operador + ocp_ffaa")

if HAS_OCC:
    FORMULA = f"log_renda ~ {_BASE_F} + {_OCC_F}"
    print("Variáveis ocupacionais incluídas no modelo Oaxaca-Blinder.")
else:
    FORMULA = f"log_renda ~ {_BASE_F}"
    print("Variáveis ocupacionais ausentes — modelo base.")

df_b = df[df["negro"] == 0].copy()
df_n = df[df["negro"] == 1].copy()

print("Ajustando OLS por grupo racial ...")
m_b = smf.ols(FORMULA, data=df_b).fit()
m_n = smf.ols(FORMULA, data=df_n).fit()

# ── Decomposição two-fold (referência: coeficientes do grupo branco) ───────
xbar_b = m_b.model.exog.mean(axis=0)
xbar_n = m_n.model.exog.mean(axis=0)
beta_b = m_b.params.values
beta_n = m_n.params.values

ybar_b = df_b["log_renda"].mean()
ybar_n = df_n["log_renda"].mean()
gap_total  = ybar_b - ybar_n
endowment  = (xbar_b - xbar_n) @ beta_b       # efeito dotações
returns    = xbar_n    @ (beta_b - beta_n)      # efeito retornos (discriminação)
interaction = (xbar_b - xbar_n) @ (beta_b - beta_n)

print(f"\nGap total (log-renda):  {gap_total:.4f}  ({(np.exp(gap_total)-1)*100:.1f}%)")
print(f"  Efeito dotações:      {endowment:.4f}  ({endowment/gap_total*100:.1f}%)")
print(f"  Efeito retornos:      {returns:.4f}  ({returns/gap_total*100:.1f}%)")
print(f"  Interacao:            {interaction:.4f}  ({interaction/gap_total*100:.1f}%)")

res = pd.DataFrame({
    "Componente": ["Gap Total", "Efeito Dotacoes", "Efeito Retornos", "Interacao"],
    "Valor_log":  [gap_total, endowment, returns, interaction],
    "Pct_do_gap": [100.0, endowment/gap_total*100, returns/gap_total*100, interaction/gap_total*100]
})
res.to_csv(TABLES / "oaxaca_resultados.csv", index=False, encoding='utf-8')

# ── Decomposição por variável (efeito dotações) ────────────────────────────
pnames = m_b.model.exog_names
var_labels = {
    "educ_medio_completo":    "Ensino Médio completo",
    "educ_superior_completo": "Superior completo",
    "educ_pos_graduacao":     "Pós-graduação",
    "idade_c":                "Idade (centrada)",
    "idade_sq":               "Idade²",
    "sexo_fem":               "Sexo feminino",
    "pct_negro_upa_z":        "% Negros na UPA",
    "tx_desemprego_upa_z":    "Tx. desemprego UPA",
    "media_educ_upa_z":       "Educ. média UPA",
    "horas_c":                "Horas trabalhadas",
    "emprego_formal":         "Emprego formal",
    "conta_propria":          "Conta própria",
    "trab_domestico":         "Trab. doméstico",
    "ocp_dirigente":          "CBO: Dirigente",
    "ocp_profissional":       "CBO: Profissional",
    "ocp_tecnico":            "CBO: Técnico",
    "ocp_administrativo":     "CBO: Administrativo",
    "ocp_servicos":           "CBO: Serviços",
    "ocp_agro":               "CBO: Agropecuária",
    "ocp_operario":           "CBO: Operário",
    "ocp_operador":           "CBO: Operador",
    "ocp_ffaa":               "CBO: FFAA",
}
var_end = {n: (xbar_b[i] - xbar_n[i]) * beta_b[i]
           for i, n in enumerate(pnames) if n in var_labels}

# ── Figura 1: Decomposição total (barra empilhada) ─────────────────────────
fig, ax = plt.subplots(figsize=(10, 4))
components = [
    ("Efeito Dotações\n(diferença de características)", endowment, "#1565C0"),
    ("Efeito Retornos\n(retornos diferenciais / discriminação)", returns, "#B71C1C"),
    ("Interação", interaction, "#FF8F00"),
]
left = 0.0
for label, value, color in components:
    ax.barh(0, value, left=left, height=0.5, color=color,
            label=f"{label}: {value/gap_total*100:.1f}%")
    cx = left + value / 2
    if abs(value) > 0.003:
        ax.text(cx, 0, f"{value/gap_total*100:.0f}%",
                va='center', ha='center', fontsize=11, fontweight='bold', color='white')
    left += value

ax.axvline(0, color='black', linewidth=0.8)
ax.set_xlim(-0.01, gap_total + 0.01)
ax.set_yticks([])
ax.set_xlabel("Contribuição ao gap de log-rendimento", fontsize=11)
ax.set_title(
    f"Decomposição de Oaxaca-Blinder | Gap total branco-negro = {gap_total:.4f} "
    f"({(np.exp(gap_total)-1)*100:.1f}%)",
    fontsize=12, fontweight='bold')
ax.legend(loc='lower right', fontsize=9,
          bbox_to_anchor=(1, -0.45), ncol=1)
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
plt.tight_layout()
plt.savefig(FIGURES / "oaxaca_decomposicao.png", dpi=150, bbox_inches='tight')
plt.close()
print("oaxaca_decomposicao.png salvo.")

# ── Figura 2: Retornos às características por grupo racial ─────────────────
if HAS_OCC:
    show_vars = ["educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
                 "sexo_fem", "horas_c", "emprego_formal", "trab_domestico",
                 "ocp_dirigente", "ocp_profissional", "ocp_servicos"]
else:
    show_vars = ["educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
                 "sexo_fem", "pct_negro_upa_z", "tx_desemprego_upa_z"]
show_labels = [var_labels[v] for v in show_vars]
coef_b_show = [m_b.params[v] for v in show_vars]
coef_n_show = [m_n.params[v] for v in show_vars]

x = np.arange(len(show_vars))
w = 0.35
fig, ax = plt.subplots(figsize=(11, 5))
ax.bar(x - w/2, coef_b_show, w, color="#1565C0", alpha=0.85, label="Brancos")
ax.bar(x + w/2, coef_n_show, w, color="#B71C1C", alpha=0.85, label="Negros")
ax.set_xticks(x)
ax.set_xticklabels(show_labels, fontsize=9, rotation=15, ha='right')
ax.axhline(0, color='black', linewidth=0.8)
ax.set_ylabel("Coeficiente OLS (efeito sobre log-renda)", fontsize=11)
ax.set_title("Retorno às Características por Grupo Racial\n"
             "(coeficientes OLS separados por raça — diferença = efeito retornos)",
             fontsize=12, fontweight='bold')
ax.legend(fontsize=10)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(FIGURES / "oaxaca_coeficientes.png", dpi=150, bbox_inches='tight')
plt.close()
print("oaxaca_coeficientes.png salvo.")

# ── Figura 3: Efeito dotações por variável ─────────────────────────────────
sorted_items = sorted(var_end.items(), key=lambda x: abs(x[1]), reverse=True)
names_v = [var_labels.get(k, k) for k, _ in sorted_items]
vals_v  = [v for _, v in sorted_items]
colors_v = ["#1565C0" if v > 0 else "#B71C1C" for v in vals_v]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.barh(names_v[::-1], vals_v[::-1], color=colors_v[::-1], alpha=0.85)
ax.axvline(0, color='black', linewidth=0.8)
for bar, val in zip(bars, vals_v[::-1]):
    sign = 1 if val >= 0 else -1
    ax.text(val + sign * 0.0005, bar.get_y() + bar.get_height()/2,
            f"{val:.4f}", va='center', ha='left' if val >= 0 else 'right', fontsize=9)
ax.set_xlabel("Contribuição ao gap — efeito dotações (log-renda)", fontsize=11)
ax.set_title("Efeito Dotações por Variável: Quanto de Cada Característia\nExplica o Gap Salarial Racial?",
             fontsize=11, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(FIGURES / "oaxaca_por_variavel.png", dpi=150, bbox_inches='tight')
plt.close()
print("oaxaca_por_variavel.png salvo.")

print("\n=== OAXACA-BLINDER CONCLUIDO ===")
print(f"Gap total: {gap_total:.4f} ({(np.exp(gap_total)-1)*100:.2f}%)")
print(f"Dotacoes: {endowment:.4f} ({endowment/gap_total*100:.1f}%)")
print(f"Retornos: {returns:.4f} ({returns/gap_total*100:.1f}%)")
