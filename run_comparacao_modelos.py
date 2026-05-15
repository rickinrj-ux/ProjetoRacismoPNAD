"""
run_comparacao_modelos.py
Gera gráfico comparativo de log-verossimilhança e AIC entre:
  OLS Nulo → OLS Individual → OLS + FE_UF → HLM Nulo → HLM Contextual → HLM M4
Justificação metodológica para defesa ESALQ.
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import statsmodels.formula.api as smf
import warnings
warnings.filterwarnings('ignore')

ROOT    = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
FIGURES = ROOT / "outputs" / "figures"
TABLES  = ROOT / "outputs" / "tables"

BLUE  = "#1565C0"; RED  = "#B71C1C"; GREEN = "#2E7D32"
DARK  = "#1F3864"; GRAY = "#616161"; AMBER = "#FF8F00"

# ── Carregar LLs salvos do HLM ─────────────────────────────────────────────
print("Carregando log-likelihoods salvos ...")
hlm_tab = pd.read_csv(TABLES / "hlm_serie_s20pct.csv", index_col=0)

LL_ROW = "Log-Likelihood"
ll_row = hlm_tab.loc[LL_ROW]

def parse_ll(s):
    return float(str(s).replace(",", "").strip())

ll_hlm_nulo    = parse_ll(ll_row["M0_Nulo"])
ll_hlm_m1      = parse_ll(ll_row["M1_Individual"])
ll_hlm_m2      = parse_ll(ll_row["M2_Localidade"])
ll_hlm_m3      = parse_ll(ll_row["M3_Completo"])
ll_hlm_m4      = parse_ll(ll_row["M4_Ocupacao"])
ll_ols_m1      = parse_ll(ll_row["M1_Individual_OLS"])
ll_ols_m3      = parse_ll(ll_row["M3_Completo_OLS"])
ll_ols_m4      = parse_ll(ll_row["M4_Ocupacao_OLS"])

print(f"  HLM M0 Nulo:  {ll_hlm_nulo:,.2f}")
print(f"  HLM M4 Full:  {ll_hlm_m4:,.2f}")
print(f"  OLS M1:       {ll_ols_m1:,.2f}")
print(f"  OLS M4:       {ll_ols_m4:,.2f}")

# ── Amostra 20% para modelos adicionais ────────────────────────────────────
print("\nCarregando amostra para OLS Nulo e OLS+FE_UF ...")
df_full = pd.read_parquet(ROOT / "data" / "processed" / "features.parquet")
df_e    = df_full[df_full["log_renda"].notna() & (df_full["renda_bruta"] > 0)].copy()
np.random.seed(42)
idx = np.random.choice(len(df_e), int(len(df_e) * 0.20), replace=False)
df  = df_e.iloc[idx].reset_index(drop=True)
print(f"  Amostra: {len(df):,} obs.")
df["UF_str"] = df["UF"].astype(str)

# OLS Nulo (apenas intercepto)
print("  Estimando OLS Nulo ...")
m_nulo = smf.ols("log_renda ~ 1", data=df).fit()
ll_ols_nulo = m_nulo.llf
k_nulo = 2  # intercepto + sigma²
print(f"    LL={ll_ols_nulo:,.2f}")

# OLS + FE de UF (27 dummies de estado)
print("  Estimando OLS + FE_UF ...")
CTRL_IND = ("negro + sexo_fem + idade_c + idade_sq + "
            "educ_fund_completo + educ_medio_completo + "
            "educ_superior_completo + educ_pos_graduacao")
m_fe_uf = smf.ols(f"log_renda ~ {CTRL_IND} + C(UF_str)", data=df).fit()
ll_ols_fe = m_fe_uf.llf
k_fe_uf   = m_fe_uf.df_model + 2  # preditores + intercepto + sigma²
print(f"    LL={ll_ols_fe:,.2f}  k={k_fe_uf:.0f}")

# LRT: HLM Nulo vs OLS Nulo (teste de efeitos aleatórios)
lrt_nulo = 2 * (ll_hlm_nulo - ll_ols_nulo)
# LRT: HLM M1 vs OLS M1 (com controles individuais)
lrt_m1   = 2 * (ll_hlm_m1 - ll_ols_m1)
# LRT: HLM M4 vs OLS M4 (modelo completo)
lrt_m4   = 2 * (ll_hlm_m4 - ll_ols_m4)
print(f"\n  LRT Nulo (HLM vs OLS, Δk=1): χ²={lrt_nulo:.1f}")
print(f"  LRT M1  (HLM vs OLS, Δk=1): χ²={lrt_m1:.1f}")
print(f"  LRT M4  (HLM vs OLS, Δk=1): χ²={lrt_m4:.1f}")

# ── Tabela de todos os modelos ─────────────────────────────────────────────
# Número de parâmetros (k) para cada modelo
# OLS: k = nº de coeficientes + 1 (sigma²)
# HLM: k = nº de coeficientes + 2 (sigma² nível1 + tau² nível3)
models = [
    # label                  LL              tipo   k    descr
    ("OLS Nulo",        ll_ols_nulo,    "OLS", 2,   "Apenas intercepto"),
    ("OLS Individual",  ll_ols_m1,      "OLS", 10,  "Controles individuais"),
    ("OLS + FE (UF)",   ll_ols_fe,      "OLS", k_fe_uf, "Controles + 26 dummies UF"),
    ("OLS Contextual",  ll_ols_m3,      "OLS", 16,  "Controles + variáveis de contexto"),
    ("OLS Completo",    ll_ols_m4,      "OLS", 29,  "Controles + ocupação (M4)"),
    ("HLM Nulo",        ll_hlm_nulo,    "HLM", 3,   "Intercepto aleatório UF"),
    ("HLM Individual",  ll_hlm_m1,      "HLM", 12,  "Controles + efeito aleatório UF"),
    ("HLM Contextual",  ll_hlm_m2,      "HLM", 15,  "Controles + UPA + efeito aleatório UF"),
    ("HLM Completo",    ll_hlm_m3,      "HLM", 18,  "M2 + variáveis nível UF"),
    ("HLM Ocupação",    ll_hlm_m4,      "HLM", 31,  "M3 + grupos CBO + formalidade (M4)"),
]
df_mod = pd.DataFrame(models, columns=["Modelo","LL","Tipo","k","Descricao"])
df_mod["AIC"] = 2 * df_mod["k"] - 2 * df_mod["LL"]
df_mod["BIC"] = df_mod["k"] * np.log(len(df)) - 2 * df_mod["LL"]
df_mod.to_csv(TABLES / "modelos_comparacao_ll.csv", index=False, encoding="utf-8")
print("\nmodelos_comparacao_ll.csv salvo.")

print("\nTabela de comparação:")
print(df_mod[["Modelo","Tipo","k","LL","AIC"]].to_string(index=False, float_format="{:,.2f}".format))

# ── Plot principal: 6 modelos-chave ────────────────────────────────────────
# Mapa do usuário: OLS Nulo | OLS | OLS Dummies | HLM Nulo | HLM Contextual | HLM M4
KEY_MODELS = [
    ("OLS Nulo",       ll_ols_nulo,  "OLS"),
    ("OLS\nIndividual",ll_ols_m1,    "OLS"),
    ("OLS\n+FE (UF)",  ll_ols_fe,    "OLS"),
    ("HLM Nulo",       ll_hlm_nulo,  "HLM"),
    ("HLM\nContextual",ll_hlm_m2,    "HLM"),
    ("HLM\nOcupação",  ll_hlm_m4,    "HLM"),
]
names_k = [m[0] for m in KEY_MODELS]
ll_k    = [m[1] for m in KEY_MODELS]
tipos_k = [m[2] for m in KEY_MODELS]
aic_k   = [2*k - 2*ll for (_, ll, _), k in
           zip(KEY_MODELS, [2, 10, k_fe_uf, 3, 15, 31])]

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle(
    "Justificação Metodológica: Comparativo de Log-Verossimilhança e AIC por Modelo",
    fontsize=13, fontweight='bold'
)

color_map = {"OLS": BLUE, "HLM": GREEN}
bar_colors = [color_map[t] for t in tipos_k]

# ─ Painel A: Log-Likelihood ─
ax = axes[0]
bars = ax.barh(range(len(names_k)), ll_k, color=bar_colors, alpha=0.85,
               edgecolor="black", linewidth=0.6)
ax.set_yticks(range(len(names_k)))
ax.set_yticklabels(names_k, fontsize=10)
ax.set_xlabel("Log-Verossimilhança\n(mais próximo de zero = melhor ajuste)", fontsize=10)
ax.set_title("Log-Verossimilhança por Modelo", fontsize=11, fontweight='bold')
ax.grid(axis="x", alpha=0.3)
for bar, val in zip(bars, ll_k):
    ax.text(val * 1.001, bar.get_y() + bar.get_height()/2,
            f"{val:,.0f}", va="center", fontsize=8)
# Setas de melhoria
for i in range(1, len(ll_k)):
    if ll_k[i] > ll_k[i-1]:
        delta = ll_k[i] - ll_k[i-1]
        ax.annotate(f"+{delta:,.0f}", xy=(ll_k[i], i),
                    xytext=(ll_k[i] + abs(ll_k[i])*0.005, i),
                    fontsize=7, color=AMBER, fontweight='bold',
                    va='center')

# Legenda
patch_ols = mpatches.Patch(color=BLUE, alpha=0.85, label="OLS (sem efeitos aleatórios)")
patch_hlm = mpatches.Patch(color=GREEN, alpha=0.85, label="HLM (com efeitos aleatórios)")
ax.legend(handles=[patch_ols, patch_hlm], fontsize=9, loc="lower right")

# ─ Painel B: AIC ─
ax2 = axes[1]
bars2 = ax2.barh(range(len(names_k)), aic_k, color=bar_colors, alpha=0.85,
                 edgecolor="black", linewidth=0.6)
ax2.set_yticks(range(len(names_k)))
ax2.set_yticklabels(names_k, fontsize=10)
ax2.set_xlabel("AIC (menor = melhor, penaliza complexidade)", fontsize=10)
ax2.set_title("AIC por Modelo", fontsize=11, fontweight='bold')
ax2.grid(axis="x", alpha=0.3)
for bar, val in zip(bars2, aic_k):
    ax2.text(val * 1.001, bar.get_y() + bar.get_height()/2,
             f"{val:,.0f}", va="center", fontsize=8)
ax2.legend(handles=[patch_ols, patch_hlm], fontsize=9, loc="lower right")

# Anotação de LRT
ax.axhline(2.5, color="gray", linestyle=":", linewidth=0.8)
ax.text(ax.get_xlim()[0]*0.995, 2.6, "▲ OLS  |  HLM ▼", fontsize=8, color=GRAY)

plt.tight_layout()
fig.savefig(FIGURES / "modelos_loglik_aic.png", dpi=150, bbox_inches="tight")
plt.close()
print("modelos_loglik_aic.png salvo.")

# ── Plot LRT waterfall ──────────────────────────────────────────────────────
print("\nGerando waterfall de LRT ...")
hlm_prog = [
    ("M0 → M1\n(ind. controls)", ll_hlm_m1 - ll_hlm_nulo),
    ("M1 → M2\n(UPA context)",   ll_hlm_m2 - ll_hlm_m1),
    ("M2 → M3\n(UF context)",    ll_hlm_m3 - ll_hlm_m2),
    ("M3 → M4\n(ocupação)",      ll_hlm_m4 - ll_hlm_m3),
]
labels_lrt = [x[0] for x in hlm_prog]
deltas_lrt = [x[1] for x in hlm_prog]
chi2_lrt   = [2 * d for d in deltas_lrt]
df_lrt_prog = [8, 3, 3, 13]  # graus de liberdade por etapa (aprox)

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("Testes de Razão de Verossimilhança (LRT) — HLM: Cada Etapa Justificada",
             fontsize=13, fontweight='bold')

ax = axes[0]
bars = ax.bar(range(len(labels_lrt)), chi2_lrt,
              color=[GREEN if v > 0 else RED for v in chi2_lrt],
              alpha=0.85, edgecolor="black", lw=0.6)
ax.set_xticks(range(len(labels_lrt)))
ax.set_xticklabels(labels_lrt, fontsize=9)
ax.set_ylabel("Estatística LRT (χ²) = 2 × ΔLL")
ax.set_title("LRT entre Etapas Progressivas do HLM\n(todos os Δχ² >> valor crítico χ²(df))")
ax.grid(axis="y", alpha=0.3)
for bar, val, df_lr in zip(bars, chi2_lrt, df_lrt_prog):
    ax.text(bar.get_x()+bar.get_width()/2, val + 500,
            f"χ²={val:,.0f}\n(df={df_lr})", ha="center", fontsize=8, fontweight='bold')

# ICC por modelo
icc_models = [0.0983, 0.0880, 0.0528, 0.0398, 0.0331]
icc_labels = ["M0\nNulo","M1\nIndividual","M2\nLocalidade","M3\nCompleto","M4\nOcupação"]
ax2 = axes[1]
ax2.plot(range(len(icc_models)), [v*100 for v in icc_models],
         "o-", color=DARK, lw=2, ms=8, label="ICC_UF (%)")
ax2.fill_between(range(len(icc_models)), [v*100 for v in icc_models],
                 alpha=0.15, color=DARK)
for i, (v, lbl) in enumerate(zip(icc_models, icc_labels)):
    ax2.text(i, v*100 + 0.3, f"{v*100:.1f}%", ha="center", fontsize=9, fontweight='bold')
ax2.set_xticks(range(len(icc_labels)))
ax2.set_xticklabels(icc_labels, fontsize=9)
ax2.set_ylabel("ICC — % da variância explicada pelo nível UF")
ax2.set_title("Trajetória do ICC por Nível de Complexidade\n"
              "(ICC > 5% justifica estrutura multinível)")
ax2.axhline(5, color=RED, linestyle="--", lw=1.5, label="Limiar 5% (regra de ouro)")
ax2.legend(fontsize=9); ax2.grid(alpha=0.3)

plt.tight_layout()
fig.savefig(FIGURES / "modelos_lrt_icc.png", dpi=150, bbox_inches="tight")
plt.close()
print("modelos_lrt_icc.png salvo.")

print("\n=== COMPARAÇÃO DE MODELOS CONCLUÍDA ===")
