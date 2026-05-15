"""
run_logit_multinivel.py
Logit multinível para identificação do gap de oportunidades racial.

Três desfechos binários:
  1. Emprego formal      — acesso a trabalho com carteira / setor público
  2. Ocupação qualificada — CBO grupos Dirigente / Profissional / Técnico / Administrativo
  3. Renda no top 20%   — acesso ao quintil superior de rendimento

Estrutura multinível (aproximação por efeito fixo):
  Nível 1: indivíduo (negro, educ, idade, sexo)
  Nível 2: UPA — variáveis contextuais (pct_negro_upa_z, tx_desemprego_upa_z, media_educ_upa_z)
  Nível 3: UF — dummies de efeito fixo + SE clusterizado por UPA

Modelos sequenciais:
  M1: controles individuais + UF FE
  M2: M1 + contexto da UPA (nível 2)
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import statsmodels.formula.api as smf
import warnings
warnings.filterwarnings('ignore')
from pathlib import Path

ROOT    = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
FIGURES = ROOT / "outputs" / "figures"
TABLES  = ROOT / "outputs" / "tables"
FIGURES.mkdir(parents=True, exist_ok=True)

SAMPLE_FRAC = 0.20
SEED        = 42

COLS = [
    "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "emprego_formal", "ocp_dirigente", "ocp_profissional",
    "ocp_tecnico", "ocp_administrativo",
    "log_renda", "renda_bruta", "pea",
    "UF", "UPA",
]

print("Carregando dados ...")
df_full = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=COLS)

df_full["UF_str"] = df_full["UF"].astype(str)

mask = (df_full["pea"] == 1) & (df_full["renda_bruta"] > 0) & (df_full["negro"].notna())
df_full = df_full[mask].copy()

HAS_OCC = (
    all(c in df_full.columns for c in ["emprego_formal","ocp_dirigente"])
    and df_full["emprego_formal"].notna().any()
)

BASE_DROP = ["negro","sexo_fem","idade_c","idade_sq",
             "educ_medio_completo","educ_superior_completo","educ_pos_graduacao",
             "pct_negro_upa_z","tx_desemprego_upa_z","media_educ_upa_z","log_renda"]
df_full = df_full.dropna(subset=BASE_DROP)
print(f"  PEA filtrada: {len(df_full):,} obs.")

rng = np.random.default_rng(SEED)
idx = rng.choice(len(df_full), size=int(len(df_full) * SAMPLE_FRAC), replace=False)
df  = df_full.iloc[idx].reset_index(drop=True)
print(f"  Amostra {int(SAMPLE_FRAC*100)}%: {len(df):,} obs. | "
      f"Brancos={int((df['negro']==0).sum()):,} | Negros={int((df['negro']==1).sum()):,}")

# ── Variáveis dependentes ─────────────────────────────────────────────────────
if HAS_OCC:
    df["y_formal"] = df["emprego_formal"].fillna(0).astype(int)
    df["y_ocp_qualificada"] = (
        (df.get("ocp_dirigente", 0) == 1) |
        (df.get("ocp_profissional", 0) == 1) |
        (df.get("ocp_tecnico", 0) == 1) |
        (df.get("ocp_administrativo", 0) == 1)
    ).astype(int)
else:
    df["y_formal"] = np.nan
    df["y_ocp_qualificada"] = np.nan

q80 = df["log_renda"].quantile(0.80)
df["y_top20"] = (df["log_renda"] >= q80).astype(int)

OUTCOMES = [
    ("y_formal",         "Emprego Formal"),
    ("y_ocp_qualificada","Ocupação Qualificada\n(CBO: Dirig./Prof./Téc./Adm.)"),
    ("y_top20",          "Renda no Top 20%"),
]
if not HAS_OCC:
    OUTCOMES = [o for o in OUTCOMES if o[0] == "y_top20"]

for y_col, lbl in OUTCOMES:
    pct = df[y_col].mean() * 100
    print(f"  P({y_col}): {pct:.1f}% na amostra")

# ── Fórmulas ──────────────────────────────────────────────────────────────────
_IND = ("negro + educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
        " + idade_c + idade_sq + sexo_fem")
_UPA = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"

FORMULAS = {
    "M1": f"{{y}} ~ {_IND} + C(UF_str)",
    "M2": f"{{y}} ~ {_IND} + {_UPA} + C(UF_str)",
}
MODEL_LABELS = {
    "M1": "M1: Individuais + UF FE",
    "M2": "M2: + Contexto UPA",
}

# ── Ajuste logit com SE clusterizado por UPA ──────────────────────────────────
def fit_logit(formula_str, data):
    try:
        m = smf.logit(formula_str, data=data).fit(
            method="newton", maxiter=300, disp=False,
            cov_type="cluster", cov_kwds={"groups": data["UPA"]},
        )
        return m
    except Exception as e:
        try:
            m = smf.logit(formula_str, data=data).fit(
                method="bfgs", maxiter=300, disp=False,
                cov_type="cluster", cov_kwds={"groups": data["UPA"]},
            )
            return m
        except Exception as e2:
            print(f"    FALHOU: {e2}")
            return None

def get_or_ci(m, var="negro"):
    if m is None or var not in m.params:
        return np.nan, np.nan, np.nan
    b, se = m.params[var], m.bse[var]
    return np.exp(b), np.exp(b - 1.96*se), np.exp(b + 1.96*se)

def get_ame(m, data, var="negro"):
    """Average Marginal Effect para variável binária: E[F(Xb+b_negro) - F(Xb)]."""
    if m is None or var not in m.params:
        return np.nan
    b_neg = m.params[var]
    exog  = m.model.exog.copy()
    idx_v = list(m.model.exog_names).index(var)
    lp0   = exog @ m.params.values
    lp0   = lp0 - exog[:, idx_v] * b_neg  # remove negro contribution
    p1    = 1 / (1 + np.exp(-(lp0 + b_neg)))
    p0    = 1 / (1 + np.exp(-(lp0)))
    return (p1 - p0).mean()

def stars(p):
    return "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))

# ── Ajustar modelos para cada desfecho ────────────────────────────────────────
results = {}
for y_col, y_label in OUTCOMES:
    sub = df[df[y_col].notna()].copy()
    print(f"\n--- Desfecho: {y_col.upper()} (n={len(sub):,}) ---")
    results[y_col] = {}
    for m_name, formula_tpl in FORMULAS.items():
        formula = formula_tpl.format(y=y_col)
        print(f"  Ajustando {m_name} ...", end="", flush=True)
        m = fit_logit(formula, sub)
        results[y_col][m_name] = m
        if m is not None:
            or_, lo, hi = get_or_ci(m)
            ame = get_ame(m, sub) * 100
            p   = m.pvalues.get("negro", np.nan)
            print(f" OR={or_:.3f} [{lo:.3f}–{hi:.3f}]{stars(p)} | AME={ame:+.2f}pp")
        else:
            print(" FALHOU")

# ── Tabela de resultados ──────────────────────────────────────────────────────
rows = []
for y_col, y_label in OUTCOMES:
    for m_name in FORMULAS:
        m = results[y_col].get(m_name)
        or_, lo, hi = get_or_ci(m)
        sub = df[df[y_col].notna()]
        ame = get_ame(m, sub) * 100 if m is not None else np.nan
        p   = m.pvalues.get("negro", np.nan) if m is not None else np.nan
        rows.append({
            "Desfecho": y_col, "Modelo": m_name,
            "OR_negro": round(or_, 4), "CI95_lo": round(lo, 4), "CI95_hi": round(hi, 4),
            "AME_pp":   round(ame, 3), "p_valor":  round(p, 4),
        })
table_or = pd.DataFrame(rows)
table_or.to_csv(TABLES / "logit_or_ame.csv", index=False, encoding="utf-8")
print("\nlogit_or_ame.csv salvo.")

# ── Gap bruto observado ───────────────────────────────────────────────────────
raw_gaps = {}
for y_col, y_label in OUTCOMES:
    pb = df.loc[df["negro"]==0, y_col].mean() * 100
    pn = df.loc[df["negro"]==1, y_col].mean() * 100
    raw_gaps[y_col] = {"branco": pb, "negro": pn, "gap": pb - pn, "label": y_label}

# ── Figura 1: Gap de oportunidades bruto (proporções observadas) ──────────────
fig, ax = plt.subplots(figsize=(11, 6))
n_out = len(OUTCOMES)
x     = np.arange(n_out)
w     = 0.32

pb_vals = [raw_gaps[y]["branco"] for y, _ in OUTCOMES]
pn_vals = [raw_gaps[y]["negro"]  for y, _ in OUTCOMES]
ylabels = [raw_gaps[y]["label"].replace("\n"," ") for y, _ in OUTCOMES]

bars_b = ax.bar(x - w/2, pb_vals, w, color="#1565C0", alpha=0.85, label="Branco")
bars_n = ax.bar(x + w/2, pn_vals, w, color="#B71C1C", alpha=0.85, label="Negro")

for i, (pb, pn) in enumerate(zip(pb_vals, pn_vals)):
    ax.text(i - w/2, pb + 0.8, f"{pb:.1f}%", ha="center", fontsize=10,
            fontweight="bold", color="#1565C0")
    ax.text(i + w/2, pn + 0.8, f"{pn:.1f}%", ha="center", fontsize=10,
            fontweight="bold", color="#B71C1C")
    ax.annotate(
        f"Gap = {pb-pn:.1f} p.p.",
        xy=(i, max(pb, pn) + 2.5), ha="center", fontsize=10,
        color="#E65100", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFF8E1", edgecolor="#FF8F00", alpha=0.9),
    )

ax.set_xticks(x)
ax.set_xticklabels(ylabels, fontsize=11)
ax.set_ylabel("Proporção da PEA (%)", fontsize=11)
ax.set_title("Gap de Oportunidades Racial — Proporções Observadas\n"
             "(PEA com renda positiva — PNAD Contínua 2016–2025)",
             fontsize=12, fontweight="bold")
ax.legend(fontsize=10)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.set_ylim(0, max(pb_vals + pn_vals) * 1.35)
plt.tight_layout()
plt.savefig(FIGURES / "logit_gap_bruto.png", dpi=150, bbox_inches="tight")
plt.close()
print("logit_gap_bruto.png salvo.")

# ── Figura 2: Odds Ratios por desfecho e modelo ───────────────────────────────
COLORS_M = {"M1": "#1565C0", "M2": "#B71C1C"}

fig, axes = plt.subplots(1, n_out, figsize=(5 * n_out, 6), sharey=False)
if n_out == 1:
    axes = [axes]

for ax, (y_col, y_label) in zip(axes, OUTCOMES):
    x_m = np.arange(len(FORMULAS))
    for j, m_name in enumerate(FORMULAS):
        m = results[y_col].get(m_name)
        or_, lo, hi = get_or_ci(m)
        p = m.pvalues.get("negro", np.nan) if m else np.nan
        color = COLORS_M[m_name]
        ax.scatter(j, or_, s=140, color=color, zorder=5)
        ax.plot([j, j], [lo, hi], color=color, linewidth=2.5, zorder=4)
        label = f"{or_:.3f}{stars(p)}"
        ax.text(j, hi + 0.02, label, ha="center", va="bottom",
                fontsize=10, fontweight="bold", color=color)

    ax.axhline(1.0, color="gray", linewidth=1.2, linestyle="--", label="OR=1 (paridade)")
    ax.set_xticks(x_m)
    ax.set_xticklabels([MODEL_LABELS[m] for m in FORMULAS], fontsize=8,
                        rotation=12, ha="right")
    ax.set_ylabel("Odds Ratio (negro vs. branco)" if ax == axes[0] else "")
    ax.set_title(y_label, fontsize=10, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(0.5, 0.03, "OR < 1  →  desvantagem dos negros",
            transform=ax.transAxes, ha="center", fontsize=8,
            color="gray", style="italic")

patches = [mpatches.Patch(color=COLORS_M[m], label=MODEL_LABELS[m]) for m in FORMULAS]
fig.legend(handles=patches, loc="lower center", ncol=2, fontsize=9,
           bbox_to_anchor=(0.5, -0.06))
fig.suptitle("Gap de Oportunidades Racial — Odds Ratios (negro vs. branco)\n"
             "Logit multinível: UF efeito fixo, SE clusterizado por UPA",
             fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(FIGURES / "logit_odds_ratios.png", dpi=150, bbox_inches="tight")
plt.close()
print("logit_odds_ratios.png salvo.")

# ── Figura 3: Efeito Marginal Médio (AME) em pontos percentuais ───────────────
fig, ax = plt.subplots(figsize=(10, 5))
x     = np.arange(n_out)
w     = 0.30
offsets = [-w/2, w/2]
ylabels_ame = [raw_gaps[y]["label"].replace("\n"," ") for y, _ in OUTCOMES]

for j, m_name in enumerate(FORMULAS):
    ames = []
    for y_col, _ in OUTCOMES:
        m   = results[y_col].get(m_name)
        sub = df[df[y_col].notna()]
        ame = get_ame(m, sub) * 100 if m is not None else np.nan
        ames.append(ame)
    ax.bar(x + offsets[j], ames, w * 0.9, color=COLORS_M[m_name],
           alpha=0.85, label=MODEL_LABELS[m_name])
    for xi, ame in zip(x + offsets[j], ames):
        if not np.isnan(ame):
            ax.text(xi, ame - 0.3 if ame < 0 else ame + 0.1,
                    f"{ame:+.1f}pp", ha="center", fontsize=9,
                    fontweight="bold", color=COLORS_M[m_name])

ax.axhline(0, color="black", linewidth=0.8)
ax.set_xticks(x)
ax.set_xticklabels(ylabels_ame, fontsize=10)
ax.set_ylabel("Efeito Marginal Médio (pontos percentuais)", fontsize=11)
ax.set_title("Gap de Oportunidades Racial — Efeito Marginal de Ser Negro\n"
             "(AME em p.p. — ceteris paribus, relativo a ser branco)",
             fontsize=12, fontweight="bold")
ax.legend(fontsize=9)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.tight_layout()
plt.savefig(FIGURES / "logit_ame.png", dpi=150, bbox_inches="tight")
plt.close()
print("logit_ame.png salvo.")

# ── Figura 4: Probabilidades preditas por raça × escolaridade ─────────────────
EDUC_LEVELS = [
    ("Sem compl. médio", dict(educ_medio_completo=0, educ_superior_completo=0, educ_pos_graduacao=0)),
    ("Médio completo",   dict(educ_medio_completo=1, educ_superior_completo=0, educ_pos_graduacao=0)),
    ("Superior completo",dict(educ_medio_completo=1, educ_superior_completo=1, educ_pos_graduacao=0)),
    ("Pós-graduação",    dict(educ_medio_completo=1, educ_superior_completo=1, educ_pos_graduacao=1)),
]

most_common_uf = df["UF_str"].mode().iloc[0]
mean_idade_c   = float(df["idade_c"].mean())
mean_idade_sq  = float(df["idade_sq"].mean())

fig, axes = plt.subplots(1, n_out, figsize=(5 * n_out, 6), sharey=False)
if n_out == 1:
    axes = [axes]

for ax, (y_col, y_label) in zip(axes, OUTCOMES):
    m = results[y_col].get("M2")  # modelo mais completo sem dummies explícitas
    probs_b, probs_n, gaps = [], [], []

    for educ_name, educ_dict in EDUC_LEVELS:
        base = dict(
            sexo_fem=0, idade_c=mean_idade_c, idade_sq=mean_idade_sq,
            pct_negro_upa_z=0.0, tx_desemprego_upa_z=0.0, media_educ_upa_z=0.0,
            UF_str=most_common_uf, **educ_dict,
        )
        try:
            pb = float(m.predict(pd.DataFrame([{**base, "negro": 0}])).iloc[0]) * 100
            pn = float(m.predict(pd.DataFrame([{**base, "negro": 1}])).iloc[0]) * 100
        except Exception:
            pb, pn = np.nan, np.nan
        probs_b.append(pb)
        probs_n.append(pn)
        gaps.append(pb - pn)

    x_e = np.arange(len(EDUC_LEVELS))
    ax.plot(x_e, probs_b, "o-", color="#1565C0", lw=2, ms=8, label="Branco")
    ax.plot(x_e, probs_n, "s-", color="#B71C1C", lw=2, ms=8, label="Negro")

    for i, (pb, pn, gap) in enumerate(zip(probs_b, probs_n, gaps)):
        if not (np.isnan(pb) or np.isnan(pn)):
            mid = (pb + pn) / 2
            ax.annotate(f"Δ={gap:.1f}pp", xy=(i, mid),
                        xytext=(8, 0), textcoords="offset points",
                        fontsize=8, color="#E65100", fontweight="bold")

    ax.set_xticks(x_e)
    ax.set_xticklabels([e[0] for e in EDUC_LEVELS], fontsize=8, rotation=15, ha="right")
    ax.set_ylabel("Probabilidade predita (%)" if ax == axes[0] else "")
    ax.set_title(y_label, fontsize=10, fontweight="bold")
    ax.legend(fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylim(0, 100)

fig.suptitle("Probabilidade Predita por Raça e Escolaridade\n"
             "(homem, contexto UPA médio — Logit M2 com UF FE)",
             fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(FIGURES / "logit_prob_predita.png", dpi=150, bbox_inches="tight")
plt.close()
print("logit_prob_predita.png salvo.")

# ── Figura 5: Decomposição do gap de oportunidades (bruto → ajustado) ─────────
fig, ax = plt.subplots(figsize=(11, 6))
x = np.arange(n_out)
w = 0.25

for i, (y_col, y_label) in enumerate(OUTCOMES):
    # Gap bruto
    gap_bruto = raw_gaps[y_col]["gap"]
    # Gap ajustado por M1 (AME)
    m1 = results[y_col].get("M1")
    sub1 = df[df[y_col].notna()]
    ame_m1 = get_ame(m1, sub1) * 100 if m1 is not None else np.nan
    # Gap ajustado por M2 (AME)
    m2 = results[y_col].get("M2")
    sub2 = df[df[y_col].notna()]
    ame_m2 = get_ame(m2, sub2) * 100 if m2 is not None else np.nan

    xs = [i - w, i, i + w]
    vals = [gap_bruto, ame_m1, ame_m2]
    lbls = ["Bruto", "M1 (AME)", "M2 (AME)"]
    clrs = ["#546E7A", "#1565C0", "#B71C1C"]

    for xi, val, lbl, clr in zip(xs, vals, lbls, clrs):
        if not np.isnan(val):
            ax.bar(xi, val, w * 0.85, color=clr, alpha=0.85)
            ax.text(xi, val + 0.15, f"{val:.1f}pp", ha="center",
                    fontsize=9, fontweight="bold", color=clr)

y_lbl_str = [raw_gaps[y]["label"].replace("\n"," ") for y, _ in OUTCOMES]
ax.set_xticks(x)
ax.set_xticklabels(y_lbl_str, fontsize=10)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_ylabel("Gap (branco − negro, pontos percentuais)", fontsize=11)
ax.set_title("Decomposição do Gap de Oportunidades\n"
             "Bruto vs. Ajustado por Características Individuais e Contexto",
             fontsize=12, fontweight="bold")
patches_legend = [
    mpatches.Patch(color="#546E7A", label="Gap bruto (sem controles)"),
    mpatches.Patch(color="#1565C0", label="AME M1 (individuais + UF FE)"),
    mpatches.Patch(color="#B71C1C", label="AME M2 (+ contexto UPA)"),
]
ax.legend(handles=patches_legend, fontsize=9)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.tight_layout()
plt.savefig(FIGURES / "logit_decomposicao_gap.png", dpi=150, bbox_inches="tight")
plt.close()
print("logit_decomposicao_gap.png salvo.")

# ── Sumário ───────────────────────────────────────────────────────────────────
print("\n" + "="*72)
print("  SUMÁRIO — LOGIT MULTINÍVEL: GAP DE OPORTUNIDADES RACIAL")
print("="*72)
for y_col, y_label in OUTCOMES:
    lbl = y_label.replace("\n"," ")
    g   = raw_gaps[y_col]
    print(f"\n  {lbl}")
    print(f"    Branco: {g['branco']:.1f}%  |  Negro: {g['negro']:.1f}%  |  Gap bruto: {g['gap']:.1f} p.p.")
    for m_name in FORMULAS:
        m = results[y_col].get(m_name)
        if m is not None:
            or_, lo, hi = get_or_ci(m)
            sub = df[df[y_col].notna()]
            ame = get_ame(m, sub) * 100
            p   = m.pvalues.get("negro", np.nan)
            print(f"    {m_name}: OR={or_:.3f} [{lo:.3f}–{hi:.3f}]{stars(p)} | AME={ame:+.2f}pp")
print("\n" + "="*72)
print("=== LOGIT MULTINÍVEL CONCLUÍDO ===")
