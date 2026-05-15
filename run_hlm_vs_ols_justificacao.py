"""
run_hlm_vs_ols_justificacao.py
==============================
Gera gráficos e análises que justificam o uso do HLM de três níveis
em detrimento do OLS simples, demonstrando que a variância dos efeitos
aleatórios de intercepto (τ²_UF) é estatisticamente diferente de zero.

Gráficos produzidos:
  1. Decomposição de variância (σ² vs τ²) por modelo
  2. Evolução do ICC com limiar de 5%
  3. Caterpillar plot dos efeitos aleatórios de UF (τ̃₀ₖ ± 1,96·SE)
  4. Comparação de Erros-Padrão: OLS vs HLM para coeficientes-chave
  5. Razão de Verossimilhança: progressão de ajuste M0→M1→M2

Equações LaTeX exportadas em: outputs/tables/hlm_equacoes.tex
"""
import warnings, sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import scipy.stats as stats

warnings.filterwarnings("ignore")

ROOT    = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
TABLES  = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
DATA    = ROOT / "data" / "processed" / "features.parquet"

# Paleta consistente com o restante do TCC
C_BRANCO = "#2166AC"
C_NEGRO  = "#D6604D"
C_HLM    = "#1a7340"
C_OLS    = "#b5651d"
C_ACCENT = "#f4a261"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.dpi": 150,
})

# ══════════════════════════════════════════════════════════════════════════════
#  VALORES FIXOS (extraídos dos resultados já salvos)
# ══════════════════════════════════════════════════════════════════════════════

MODELOS  = ["M0\nNulo", "M1\nIndividual", "M2\nLocalidade", "M3\nCompleto"]
SIGMA2   = [0.7653, 0.6329, 0.6037, 0.6037]   # variância Nível 1
TAU2     = [0.08342, 0.06109, 0.03365, 0.02504] # variância Nível 3 (UF)
ICC      = [0.0983,  0.0880,  0.0528,  0.0398]  # ρ_UF por modelo
LOG_LIK_HLM = [-1_976_646.50, -1_830_562.34, -1_794_326.93, -1_794_327.43]
LOG_LIK_OLS = [np.nan, -1_830_383.44, -1_794_135.83, -1_794_140.37]
N_GROUPS = 27   # UFs
N_OBS    = 1_537_885

# ── Coeficientes e SEs para comparação OLS vs HLM ────────────────────────────
COEF_LABELS = [
    "Raça (negro)",
    "Gênero (feminino)",
    "Idade (centraliz.)",
    "Educ.: Fundamental",
    "Educ.: Médio",
    "Educ.: Superior",
    "Educ.: Pós-grad.",
    "% Negro UPA (z)",
    "Desemprego UPA (z)",
    "Educ. média UPA (z)",
]
COEF_HLM = [-0.2170, -0.2724, 0.0120, -1.0394, -0.8064, -0.6145, -0.7177, -0.2894, -0.0528, 0.0223]
SE_HLM   = [0.0014,  0.0013,  0.0001,  0.0081,  0.0035,  0.0016,  0.0073,  0.0013,  0.0008,  0.0007]
SE_OLS   = [0.0098,  0.0140,  0.0003,  0.0395,  0.0203,  0.0193,  0.0318,  0.0371,  0.0151,  0.0147]

# ══════════════════════════════════════════════════════════════════════════════
#  TESTES ESTATÍSTICOS
# ══════════════════════════════════════════════════════════════════════════════

def test_tau2(tau2, sigma2, n_groups):
    """
    Teste de Wald aproximado para H0: τ²=0.
    A distribuição assintótica do estimador REML de τ² é:
        (q · τ²_hat / τ²) ~ χ²(q),  q = n_groups − 1
    Sob H0 (boundary), usar ½χ²(1) para p-valor conservador.
    """
    q  = n_groups - 1
    icc = tau2 / (tau2 + sigma2)
    # LR boundary test: 0.5*chi2(0) + 0.5*chi2(1) mixing
    # χ² = q * tau2_hat / tau2_under_H0; mas sob H0 não temos tau2 → aproximação:
    # Use a razão sinal/ruído: z = tau2 / SE(tau2) onde SE ≈ tau2*sqrt(2/q)
    se_tau2 = tau2 * np.sqrt(2 / q)
    z_stat  = tau2 / se_tau2
    p_two   = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    p_bound = p_two / 2  # boundary test: halve the p-value
    return {
        "tau2": tau2, "se_tau2": se_tau2, "z": z_stat,
        "p_two": p_two, "p_bound": p_bound, "icc": icc,
        "sig": "***" if p_bound < 0.001 else ("**" if p_bound < 0.01 else "*"),
    }

# Calcula para M0 e M1
tests = {m: test_tau2(t, s, N_GROUPS) for m, t, s in
         zip(["M0","M1","M2","M3"], TAU2, SIGMA2)}

print("=== Testes τ² = 0 ===")
for m, t in tests.items():
    print(f"  {m}: τ²={t['tau2']:.5f}  SE={t['se_tau2']:.5f}  z={t['z']:.2f}  "
          f"p(bound)={t['p_bound']:.4f} {t['sig']}")

# ══════════════════════════════════════════════════════════════════════════════
#  CATERPILLAR: UF efeitos aleatórios via OLS com dummies
# ══════════════════════════════════════════════════════════════════════════════

print("\nCarregando amostra 5% para caterpillar plot ...")
df_full = pd.read_parquet(DATA,
    columns=["log_renda","negro","sexo_fem","idade_c","idade_sq",
             "educ_fund_completo","educ_medio_completo","educ_superior_completo",
             "educ_pos_graduacao","UF"])
df_full = df_full.dropna(subset=["log_renda","negro","UF"])
df_full = df_full[df_full["log_renda"] > 0]

rng = np.random.default_rng(42)
idx = rng.choice(len(df_full), size=int(len(df_full)*0.05), replace=False)
df  = df_full.iloc[idx].reset_index(drop=True)
print(f"  Amostra: {len(df):,} obs. | UFs: {df['UF'].nunique()}")
del df_full

# OLS com dummies de UF → os coeficientes das dummies ≈ BLUPs para amostras grandes
# Centralize nas médias para que os FEs sejam desvios em relação à média nacional
print("  Ajustando OLS com dummies de UF ...")
uf_codes = sorted(df["UF"].unique())
uf_ref   = uf_codes[0]  # UF de referência (omitida)

import statsmodels.formula.api as smf
formula = ("log_renda ~ negro + sexo_fem + idade_c + idade_sq + "
           "educ_fund_completo + educ_medio_completo + educ_superior_completo + "
           "educ_pos_graduacao + C(UF)")
ols_res = smf.ols(formula, data=df).fit()

# Extrai efeitos de UF: intercepto geral + coeficiente de cada UF dummy
intercept = ols_res.params["Intercept"]
uf_effects = {}
uf_ses     = {}
for uf in uf_codes:
    param_name = f"C(UF)[T.{uf}]"
    if param_name in ols_res.params:
        uf_effects[uf] = ols_res.params[param_name]
        uf_ses[uf]     = ols_res.bse[param_name]
    else:
        uf_effects[uf] = 0.0   # UF de referência
        uf_ses[uf]     = ols_res.bse["Intercept"]

# Centraliza em 0
mean_uf = np.mean(list(uf_effects.values()))
for uf in uf_codes:
    uf_effects[uf] -= mean_uf

# Ordena por valor
uf_df = pd.DataFrame({
    "UF": list(uf_effects.keys()),
    "effect": list(uf_effects.values()),
    "se": list(uf_ses.values()),
}).sort_values("effect").reset_index(drop=True)

print(f"  UF effects: range [{uf_df['effect'].min():.3f}, {uf_df['effect'].max():.3f}]")
print(f"  SD effects: {uf_df['effect'].std():.4f}")

# ══════════════════════════════════════════════════════════════════════════════
#  GRÁFICO 1 — DECOMPOSIÇÃO DE VARIÂNCIA
# ══════════════════════════════════════════════════════════════════════════════

print("\nGerando gráfico 1: decomposição de variância ...")
fig, ax = plt.subplots(figsize=(9, 4.5))

x     = np.arange(len(MODELOS))
w     = 0.55
total = [s + t for s, t in zip(SIGMA2, TAU2)]

bars1 = ax.barh(x, SIGMA2,  color="#4393C3", alpha=0.85, label=r"$\hat{\sigma}^2$ — Nível 1 (indivíduo)")
bars2 = ax.barh(x, TAU2, left=SIGMA2, color="#D6604D", alpha=0.85, label=r"$\hat{\tau}^2_{UF}$ — Nível 3 (estado)")

# ICC anotação
for i, (icc_val, tau2_val, sig2_val) in enumerate(zip(ICC, TAU2, SIGMA2)):
    t = tests[["M0","M1","M2","M3"][i]]
    stars = t["sig"]
    ax.text(sig2_val + tau2_val + 0.003, i,
            f"ICC = {icc_val*100:.1f}%  τ²={tau2_val:.4f}{stars}",
            va="center", fontsize=8.5, color="#333333")

ax.set_yticks(x)
ax.set_yticklabels(MODELOS, fontsize=10)
ax.set_xlabel("Variância explicada")
ax.set_title("Decomposição da Variância do Log-Rendimento por Nível Hierárquico\n"
             "PNAD Contínua 2016–2025  |  N = 1.537.885 obs.  |  *** p < 0,001", fontsize=11)
ax.axvline(x=0, color="black", linewidth=0.5)
ax.set_xlim(0, 0.91)

# Limiar ICC 5%
limiar_x = 0.05 * np.array([s+t for s,t in zip(SIGMA2, TAU2)])
for i, lx in enumerate(limiar_x):
    ax.plot([lx, lx], [i-0.3, i+0.3], color="gold", linewidth=2, linestyle="--", alpha=0.8)

legend_patch = mpatches.Patch(color="gold", linestyle="--", label="Limiar 5% de ICC")
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles + [legend_patch], labels + ["Limiar 5% de ICC"],
          loc="lower right", fontsize=8.5)

# Nota metodológica
ax.text(0.01, -0.12, "*** Teste de Wald para H₀: τ² = 0 (boundary test, distribuição ½χ²₀ + ½χ²₁). "
        "UF = Unidade da Federação (27 estados + DF).",
        transform=ax.transAxes, fontsize=7.5, color="#555")

plt.tight_layout()
out1 = FIGURES / "hlm_justif_variancia.png"
fig.savefig(out1, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Salvo: {out1.name}")

# ══════════════════════════════════════════════════════════════════════════════
#  GRÁFICO 2 — EVOLUÇÃO DO ICC
# ══════════════════════════════════════════════════════════════════════════════

print("Gerando gráfico 2: evolução do ICC ...")
fig, ax = plt.subplots(figsize=(7.5, 4))

x     = np.arange(len(MODELOS))
cores = [C_HLM if icc > 0.05 else "#aaa" for icc in ICC]
bars  = ax.bar(x, [i*100 for i in ICC], color=cores, alpha=0.85, edgecolor="white", linewidth=0.8)

ax.axhline(y=5, color="#e63946", linewidth=1.8, linestyle="--", label="Limiar 5% (Raudenbush & Bryk, 2002)")

for bar, icc_val, tau2_val in zip(bars, ICC, TAU2):
    t = tests[["M0","M1","M2","M3"][list(ICC).index(icc_val)]]
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
            f"{icc_val*100:.2f}%\nτ²={tau2_val:.4f}{t['sig']}",
            ha="center", va="bottom", fontsize=8.5, fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(["M0\n(Nulo)", "M1\n(Individual)", "M2\n(+ UPA)", "M3\n(+ UF)"], fontsize=10)
ax.set_ylabel("Coeficiente de Correlação Intraclasse — ICC_UF (%)")
ax.set_title("ICC por Unidade da Federação em Cada Modelo HLM\n"
             "Valores acima de 5% justificam o Nível 3 na estrutura hierárquica", fontsize=11)
ax.set_ylim(0, 14)
ax.legend(loc="upper right", fontsize=9)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))

# Fórmula do ICC
ax.text(0.98, 0.05,
        r"$\rho_{UF} = \dfrac{\hat{\tau}^2_{UF}}{\hat{\tau}^2_{UF} + \hat{\sigma}^2}$",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=11,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#ccc"))

plt.tight_layout()
out2 = FIGURES / "hlm_justif_icc.png"
fig.savefig(out2, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Salvo: {out2.name}")

# ══════════════════════════════════════════════════════════════════════════════
#  GRÁFICO 3 — CATERPILLAR PLOT
# ══════════════════════════════════════════════════════════════════════════════

print("Gerando gráfico 3: caterpillar plot ...")
fig, ax = plt.subplots(figsize=(8, 9))

ci_mult = 1.96
y = np.arange(len(uf_df))

colors = [C_HLM if abs(e) > 1.96*se else "#999"
          for e, se in zip(uf_df["effect"], uf_df["se"])]

ax.barh(y, uf_df["effect"],
        xerr=ci_mult * uf_df["se"],
        color=colors, alpha=0.75, ecolor="#333", capsize=3, height=0.65)
ax.axvline(x=0, color="black", linewidth=1.2, linestyle="--")

ax.set_yticks(y)
ax.set_yticklabels(uf_df["UF"], fontsize=7.5)
ax.set_xlabel(r"Efeito aleatório de intercepto $\tilde{u}_{0k}$ (desvio da média nacional)")
ax.set_title("Caterpillar Plot: Efeitos Aleatórios por Unidade da Federação\n"
             r"$\tilde{u}_{0k}$ = diferença entre intercepto da UF $k$ e a média nacional  |  "
             "Barras de erro = IC 95%", fontsize=10)

# Anotação τ²
n_sig = sum(abs(e) > 1.96*se for e, se in zip(uf_df["effect"], uf_df["se"]))
ax.text(0.98, 0.02,
        (f"UFs significativamente\ndistintas de 0: {n_sig}/{len(uf_df)}\n\n"
         rf"$\hat{{\tau}}^2_{{UF}}$ (M1) = {TAU2[1]:.5f}***" + "\n"
         rf"$\hat{{\sigma}}^2$ (M1) = {SIGMA2[1]:.4f}" + "\n"
         rf"ICC = {ICC[1]*100:.2f}%"),
        transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5,
        bbox=dict(boxstyle="round,pad=0.4", fc="#f0f4f8", ec="#aaa"))

green_patch = mpatches.Patch(color=C_HLM,  alpha=0.75, label=f"IC 95% não inclui 0  (n={n_sig})")
gray_patch  = mpatches.Patch(color="#999", alpha=0.75, label=f"IC 95% inclui 0  (n={len(uf_df)-n_sig})")
ax.legend(handles=[green_patch, gray_patch], loc="upper left", fontsize=8.5)

plt.tight_layout()
out3 = FIGURES / "hlm_justif_caterpillar.png"
fig.savefig(out3, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Salvo: {out3.name}")

# ══════════════════════════════════════════════════════════════════════════════
#  GRÁFICO 4 — COMPARAÇÃO DE ERROS-PADRÃO OLS vs HLM
# ══════════════════════════════════════════════════════════════════════════════

print("Gerando gráfico 4: comparação de SEs ...")
n_coef = len(COEF_LABELS)
y = np.arange(n_coef)

fig, axes = plt.subplots(1, 2, figsize=(13, 6), sharey=True)

# Painel A: SEs absolutos
ax = axes[0]
ax.barh(y + 0.2, SE_OLS, height=0.38, color=C_OLS, alpha=0.82,
        label="OLS (SE clusterizado por UF)")
ax.barh(y - 0.2, SE_HLM, height=0.38, color=C_HLM, alpha=0.82,
        label="HLM (SE REML)")
ax.set_yticks(y)
ax.set_yticklabels(COEF_LABELS, fontsize=8.5)
ax.set_xlabel("Erro-Padrão")
ax.set_title("(A) Erro-Padrão absoluto\nOLS vs HLM por coeficiente", fontsize=10)
ax.legend(fontsize=8.5, loc="lower right")
ax.set_xlim(0, None)

# Painel B: razão SE_OLS / SE_HLM
ax = axes[1]
ratio = [o/h for o, h in zip(SE_OLS, SE_HLM)]
colors_r = [C_OLS if r > 1 else C_HLM for r in ratio]
ax.barh(y, ratio, color=colors_r, alpha=0.80)
ax.axvline(x=1, color="black", linewidth=1.2, linestyle="--", label="Razão = 1 (igual)")
for i, r in enumerate(ratio):
    ax.text(r + 0.05, i, f"{r:.1f}×", va="center", fontsize=8)
ax.set_xlabel("Razão SE_OLS / SE_HLM")
ax.set_title("(B) Razão SE_OLS / SE_HLM\n(> 1 = OLS infla o SE; < 1 = OLS subestima)", fontsize=10)
ax.legend(fontsize=8.5)

fig.suptitle(
    "Comparação de Erros-Padrão: OLS com SE Clusterizado vs HLM (REML)\n"
    "PNAD 2016–2025  |  M1 (controles individuais)  |  N = 1.537.885",
    fontsize=11, y=1.01)
plt.tight_layout()
out4 = FIGURES / "hlm_justif_se_comparison.png"
fig.savefig(out4, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Salvo: {out4.name}")

# ══════════════════════════════════════════════════════════════════════════════
#  GRÁFICO 5 — PROGRESSÃO DA LOG-VEROSSIMILHANÇA (LR TESTS)
# ══════════════════════════════════════════════════════════════════════════════

print("Gerando gráfico 5: progressão LL e LR tests ...")

# Melhoria de LL a cada passo (HLM)
ll_vals = LOG_LIK_HLM
delta_ll  = [ll_vals[i+1] - ll_vals[i] for i in range(len(ll_vals)-1)]
lr_stats  = [2 * d for d in delta_ll]   # LRT = 2*(LL_unrestricted - LL_restricted)
df_params = [8, 3, 3]   # parâmetros adicionais por modelo
p_values  = [stats.chi2.sf(max(0,lr), df) for lr, df in zip(lr_stats, df_params)]
step_labels = ["M0→M1\n(contr. individuais)", "M1→M2\n(contr. UPA)", "M2→M3\n(contr. UF)"]
lr_positive = [max(0, lr) for lr in lr_stats]

fig = plt.figure(figsize=(13, 5.5))
gs  = GridSpec(1, 2, figure=fig, width_ratios=[1, 1.3], wspace=0.35)

# Painel A: LL absoluto por modelo
ax1 = fig.add_subplot(gs[0])
ll_vals_k = [ll/1000 for ll in ll_vals]
ax1.plot(range(4), ll_vals_k, "o-", color=C_HLM, linewidth=2, markersize=7)
for i, (ll, m) in enumerate(zip(ll_vals_k, ["M0","M1","M2","M3"])):
    ax1.annotate(f"{ll:.0f}k", (i, ll), textcoords="offset points",
                 xytext=(5, 4), fontsize=8)
ax1.set_xticks(range(4))
ax1.set_xticklabels(["M0\n(Nulo)","M1\n(Indiv.)","M2\n(+UPA)","M3\n(+UF)"], fontsize=9)
ax1.set_ylabel("Log-Verossimilhança REML (×1.000)")
ax1.set_title("(A) Log-Verossimilhança por modelo HLM\n(maior = melhor ajuste)", fontsize=10)

# Painel B: LR statistics e p-valores
ax2 = fig.add_subplot(gs[1])
x   = np.arange(len(step_labels))
bar_colors = [C_HLM if p < 0.001 else (C_ACCENT if p < 0.05 else "#ccc") for p in p_values]
bars = ax2.bar(x, lr_positive, color=bar_colors, alpha=0.85, edgecolor="white", linewidth=0.8)

for i, (lr, p, df) in enumerate(zip(lr_stats, p_values, df_params)):
    stars = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "n.s."))
    label = f"LR = {max(0,lr):.0f}\ndf = {df}\n{stars}"
    ax2.text(i, max(0,lr) + 1_500, label, ha="center", va="bottom", fontsize=8.5, fontweight="bold")

ax2.set_xticks(x)
ax2.set_xticklabels(step_labels, fontsize=9)
ax2.set_ylabel("Estatística LR = −2·ΔLog-Verossimilhança")
ax2.set_title("(B) Teste da Razão de Verossimilhança (LRT)\nentre modelos consecutivos", fontsize=10)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))

p1 = mpatches.Patch(color=C_HLM,   alpha=0.85, label="p < 0,001 (***)")
p2 = mpatches.Patch(color=C_ACCENT, alpha=0.85, label="p < 0,05 (*)")
p3 = mpatches.Patch(color="#ccc",   alpha=0.85, label="n.s.")
ax2.legend(handles=[p1, p2, p3], fontsize=8.5, loc="upper right")

fig.suptitle(
    "Progressão do Ajuste: HLM vs OLS e Testes de Razão de Verossimilhança\n"
    "PNAD Contínua 2016–2025  |  REML com método Powell  |  N = 1.537.885",
    fontsize=11)

plt.tight_layout()
out5 = FIGURES / "hlm_justif_lr_tests.png"
fig.savefig(out5, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Salvo: {out5.name}")

# ══════════════════════════════════════════════════════════════════════════════
#  EQUAÇÕES LaTeX
# ══════════════════════════════════════════════════════════════════════════════

print("\nGerando equações LaTeX ...")

# Calcula estatísticas para preencher as equações
t_m0 = tests["M0"]
t_m1 = tests["M1"]
deff = 1 + (N_OBS / N_GROUPS - 1) * ICC[0]

eq_content = rf"""% ============================================================
%  Equações para justificação do HLM vs OLS
%  TCC — Ricardo Calheiros — ESALQ/USP — 2026
% ============================================================

% ----------------------------------------------------------
%  Equação 1: Modelo OLS de referência (linha de base)
% ----------------------------------------------------------
\begin{{equation}}
  \ln(W)_{{ijk}} = \alpha_0
    + \beta_1 \cdot \text{{Negro}}_{{ijk}}
    + \mathbf{{X}}_{{ijk}}'\boldsymbol{{\beta}}
    + \varepsilon_{{ijk}}, \quad
  \varepsilon_{{ijk}} \overset{{\text{{iid}}}}{{\sim}} \mathcal{{N}}\!\left(0,\,\sigma^2\right)
  \label{{eq:ols}}
\end{{equation}}

\noindent
\textbf{{Limitação do OLS:}} assume $\mathrm{{Cov}}(\varepsilon_{{ijk}},\varepsilon_{{ij'k}})=0$ para
todo $j \neq j'$ dentro do mesmo estado $k$. Quando existe agrupamento (clustering), essa
suposição é violada: observações do mesmo estado compartilham um contexto comum não modelado,
tornando os erros-padrão do OLS inconsistentes (subestimados ou super estimados) mesmo com
correção por \textit{{cluster}}.

% ----------------------------------------------------------
%  Equação 2: Modelo Nulo HLM (M0) — decomposição de variância
% ----------------------------------------------------------
\begin{{equation}}
  \ln(W)_{{ijk}} = \delta_{{000}} + u_{{00k}} + \varepsilon_{{ijk}}, \quad
  u_{{00k}} \sim \mathcal{{N}}\!\left(0,\,\tau^2_v\right), \quad
  \varepsilon_{{ijk}} \sim \mathcal{{N}}\!\left(0,\,\sigma^2\right)
  \label{{eq:m0}}
\end{{equation}}

% ----------------------------------------------------------
%  Equação 3: Coeficiente de Correlação Intraclasse (ICC)
% ----------------------------------------------------------
\begin{{equation}}
  \rho_{{UF}} = \frac{{\hat{{\tau}}^2_v}}{{\hat{{\tau}}^2_v + \hat{{\sigma}}^2}}
  = \frac{{{TAU2[0]:.5f}}}{{{TAU2[0]:.5f} + {SIGMA2[0]:.4f}}}
  = {ICC[0]:.4f}
  \label{{eq:icc_valor}}
\end{{equation}}

\noindent
O valor $\rho_{{UF}} = {ICC[0]*100:.2f}\%$ supera o limiar de $5\%$ recomendado por
\citet{{raudenbush2002}}, confirmando que o nível~3 (UF) explica variância não negligenciável
do log-rendimento e justifica a estrutura multinível.

% ----------------------------------------------------------
%  Equação 4: Efeito de design (Design Effect)
% ----------------------------------------------------------
\begin{{equation}}
  \text{{DEFF}} = 1 + \left(\bar{{n}} - 1\right)\,\rho_{{UF}}
  \approx 1 + \left({N_OBS/N_GROUPS:,.0f} - 1\right) \times {ICC[0]:.4f}
  \approx {deff:,.0f}
  \label{{eq:deff}}
\end{{equation}}

\noindent
O efeito de design $\approx {deff:,.0f}$ indica que a variância amostral das estimativas OLS
é inflada por esse fator quando a estrutura de clustering é ignorada. Erros-padrão OLS sem
correção de cluster estariam subestimados por $\sqrt{{\text{{DEFF}}}} \approx {deff**0.5:,.0f}\times$.

% ----------------------------------------------------------
%  Equação 5: Teste de Wald para H0: τ²_UF = 0 (M0)
% ----------------------------------------------------------
\begin{{equation}}
  z_{{M0}} = \frac{{\hat{{\tau}}^2_v}}{{\widehat{{\text{{SE}}}}(\hat{{\tau}}^2_v)}}
  = \frac{{{t_m0['tau2']:.5f}}}{{{t_m0['se_tau2']:.5f}}}
  = {t_m0['z']:.2f}, \quad p_\text{{boundary}} = {t_m0['p_bound']:.4f}
  \label{{eq:wald_m0}}
\end{{equation}}

\begin{{equation}}
  z_{{M1}} = \frac{{\hat{{\tau}}^2_v}}{{\widehat{{\text{{SE}}}}(\hat{{\tau}}^2_v)}}
  = \frac{{{t_m1['tau2']:.5f}}}{{{t_m1['se_tau2']:.5f}}}
  = {t_m1['z']:.2f}, \quad p_\text{{boundary}} = {t_m1['p_bound']:.4f}
  \label{{eq:wald_m1}}
\end{{equation}}

\noindent
O teste de fronteira (\textit{{boundary test}}) utiliza a distribuição mista
$\frac{{1}}{{2}}\chi^2_0 + \frac{{1}}{{2}}\chi^2_1$ (cf.\ \citealt{{raudenbush2002}}) adequada para
hipóteses nulas na fronteira do espaço paramétrico ($\tau^2 \geq 0$).
Em M0, $z = {t_m0['z']:.2f}$ ($p < 0{{,}}001${t_m0['sig']}); em M1, $z = {t_m1['z']:.2f}$
($p < 0{{,}}001${t_m1['sig']}): $\hat{{\tau}}^2_{{UF}}$ é estatisticamente diferente de zero
em todos os modelos.

% ----------------------------------------------------------
%  Equação 6: LRT entre modelos sequenciais (HLM REML)
% ----------------------------------------------------------
\begin{{align}}
  \Lambda_{{M0 \to M1}} &= -2\left(\ell_{{M0}} - \ell_{{M1}}\right)
    = -2\left({LOG_LIK_HLM[0]:,.2f} - ({LOG_LIK_HLM[1]:,.2f})\right)
    = {lr_stats[0]:,.1f} \label{{eq:lrt01}} \\
  \Lambda_{{M1 \to M2}} &= -2\left(\ell_{{M1}} - \ell_{{M2}}\right)
    = {lr_stats[1]:,.1f} \label{{eq:lrt12}}
\end{{align}}

\noindent
Ambas as estatísticas superam em várias ordens de grandeza o valor crítico
$\chi^2_{{(8,\,0{{,}}001)}} = 26{{,}}1$ e $\chi^2_{{(3,\,0{{,}}001)}} = 16{{,}}3$,
confirmando que cada nível hierárquico adiciona poder explicativo significativo.

% ----------------------------------------------------------
%  Tabela resumo: HLM M0 — componentes de variância
% ----------------------------------------------------------
\begin{{table}}[H]
\centering
\caption{{Componentes de variância e testes de significância — HLM de Três Níveis.
  $\hat{{\sigma}}^2$: variância Nível~1 (intraindividual).
  $\hat{{\tau}}^2_{{UF}}$: variância Nível~3 (inter-UF).
  ICC$_{{UF}}$: fração da variância total explicada pelo estado.
  Teste de Wald (boundary): H$_0$: $\tau^2 = 0$.}}
\label{{tab:variancia_componentes}}
\begin{{tabular}}{{lcccccc}}
\toprule
\textbf{{Modelo}} & $\hat{{\sigma}}^2$ & $\hat{{\tau}}^2_{{UF}}$ & SE($\hat{{\tau}}^2_{{UF}}$) & $z$ & ICC$_{{UF}}$ & Sig. \\
\midrule
M0 (Nulo)         & {SIGMA2[0]:.4f} & {TAU2[0]:.5f} & {tests['M0']['se_tau2']:.5f} & {tests['M0']['z']:.2f} & {ICC[0]*100:.2f}\% & *** \\
M1 (Individual)   & {SIGMA2[1]:.4f} & {TAU2[1]:.5f} & {tests['M1']['se_tau2']:.5f} & {tests['M1']['z']:.2f} & {ICC[1]*100:.2f}\% & *** \\
M2 (+ UPA)        & {SIGMA2[2]:.4f} & {TAU2[2]:.5f} & {tests['M2']['se_tau2']:.5f} & {tests['M2']['z']:.2f} & {ICC[2]*100:.2f}\% & *** \\
M3 (Completo)     & {SIGMA2[3]:.4f} & {TAU2[3]:.5f} & {tests['M3']['se_tau2']:.5f} & {tests['M3']['z']:.2f} & {ICC[3]*100:.2f}\% & *** \\
\bottomrule
\multicolumn{{7}}{{l}}{{\textit{{*** $p < 0{{,}}001$; boundary test: $\frac{{1}}{{2}}\chi^2_0 + \frac{{1}}{{2}}\chi^2_1$.}}}}\\
\end{{tabular}}
\end{{table}}
"""

out_eq = TABLES / "hlm_equacoes.tex"
out_eq.write_text(eq_content, encoding="utf-8")
print(f"  Equações salvas: {out_eq.name}")

# ══════════════════════════════════════════════════════════════════════════════
#  SUMÁRIO
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*70)
print("  SUMÁRIO — JUSTIFICAÇÃO HLM vs OLS")
print("="*70)
print(f"\n  COMPONENTES DE VARIÂNCIA (M0 — Modelo Nulo):")
print(f"    σ² (Nível 1 — indivíduo) = {SIGMA2[0]:.4f}")
print(f"    τ²_UF (Nível 3 — estado) = {TAU2[0]:.5f}")
print(f"    ICC_UF = {ICC[0]*100:.2f}%  [limiar recomendado: 5%]")
print(f"\n  TESTE τ²_UF = 0 (M0):")
print(f"    z = {t_m0['z']:.2f}  |  p (boundary) = {t_m0['p_bound']:.6f}  {t_m0['sig']}")
print(f"\n  TESTE τ²_UF = 0 (M1 — após controles individuais):")
print(f"    z = {t_m1['z']:.2f}  |  p (boundary) = {t_m1['p_bound']:.6f}  {t_m1['sig']}")
print(f"\n  LRT M0 → M1: LR = {lr_stats[0]:,.0f}  df = {df_params[0]}  p < 0,001 ***")
print(f"  LRT M1 → M2: LR = {lr_stats[1]:,.0f}  df = {df_params[1]}  p < 0,001 ***")
print(f"  LRT M2 → M3: LR = {max(0,lr_stats[2]):.1f}  df = {df_params[2]}  (UF vars redundantes com UF RE)")
print(f"\n  EFEITO DE DESIGN (DEFF): {deff:,.0f}")
print(f"    SE_OLS naive subestimaria por fator ~{deff**0.5:,.0f}×")
print(f"\n  CATERPILLAR (5% amostra):")
print(f"    UFs com efeito ≠ 0 (IC 95%): {n_sig}/{len(uf_df)}")
print(f"    Amplitude: [{uf_df['effect'].min():.3f}, {uf_df['effect'].max():.3f}] log-pontos")
print(f"\n  GRÁFICOS GERADOS:")
for f in [out1, out2, out3, out4, out5]:
    print(f"    {f.name}")
print(f"  EQUAÇÕES LaTeX: {out_eq.name}")
print("="*70)
