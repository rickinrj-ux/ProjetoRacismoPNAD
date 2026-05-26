"""
run_glmm_glassceil.py
=====================
GLMM Logístico — Teto de Vidro Ocupacional e Salarial (população COMPLETA)

Desfechos analisados:
  1. ocp_qualif  — acesso a cargo qualificado (CBO grupos 1–4)
  2. y_top20     — acesso ao quintil superior de renda (teto de vidro salarial)
  3. y_top10     — acesso ao decil superior de renda

Modelos estimados para cada desfecho:
  M1 — controles individuais + UF efeito fixo
  M2 — M1 + contexto UPA (renda média, educação média)
  M3 — M2 + interações negro × educ_superior_completo + negro × educ_pos_graduacao  (teto de credencial)

Estimação: logit statsmodels com SE robusto (HC1).
Nota: efeito aleatório de UPA via lme4 (R) estimado em logit_multinivel_glmm.R.
      Resultados R (full pop) já em outputs/tables/glmm_resumo_full.csv.
"""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import statsmodels.formula.api as smf
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

ROOT    = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
FIGURES = ROOT / "outputs" / "figures"
TABLES  = ROOT / "outputs" / "tables"
FIGURES.mkdir(parents=True, exist_ok=True)

SEED = 42

# ── Colunas necessárias ──────────────────────────────────────────────────────
COLS = [
    "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z", "media_renda_upa_z",
    "emprego_formal", "setor_publico", "conta_propria", "trab_domestico",
    "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
    "ocp_grupo_cbo",
    "log_renda", "renda_bruta", "pea",
    "UF", "UPA",
]

print("Carregando dados — população completa ...")
df = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=COLS)
print(f"  Bruto: {len(df):,} obs.")

# ── Filtros (mesmos do script R: empregado + renda + controles) ───────────────
mask = (
    (df["pea"] == 1)
    & df["renda_bruta"].notna() & (df["renda_bruta"] > 0)
    & df["negro"].notna()
    & df["sexo_fem"].notna()
    # educ_ord REMOVIDO — substitui por dummies com cobertura 100% da PEA
    & df["media_renda_upa_z"].notna()
    & df["media_educ_upa_z"].notna()
)
df = df[mask].copy()
print(f"  Filtrado (pea==1 + renda>0): {len(df):,} obs.")

# ── Construir variáveis ───────────────────────────────────────────────────────
df["UF_str"] = df["UF"].astype(str)

df["ocp_qualif"] = (
    (df.get("ocp_dirigente", 0) == 1) |
    (df.get("ocp_profissional", 0) == 1) |
    (df.get("ocp_tecnico", 0) == 1) |
    (df.get("ocp_administrativo", 0) == 1)
).astype(int)

# Top 20% e Top 10% de renda (na distribuição de trabalhadores empregados)
q80 = df["renda_bruta"].quantile(0.80)
q90 = df["renda_bruta"].quantile(0.90)
df["y_top20"] = (df["renda_bruta"] >= q80).astype(int)
df["y_top10"] = (df["renda_bruta"] >= q90).astype(int)

# Dummies de educação (100% cobertura PEA — substitui educ_ord ordinal)
df["educ_medio_completo"]    = df["educ_medio_completo"].fillna(0).astype(int)
df["educ_superior_completo"] = df["educ_superior_completo"].fillna(0).astype(int)
df["educ_pos_graduacao"]     = df["educ_pos_graduacao"].fillna(0).astype(int)
# Variáveis de vínculo empregatício — NA → 0
df["emprego_formal"] = df["emprego_formal"].fillna(0).astype(int)
df["setor_publico"]  = df["setor_publico"].fillna(0).astype(int)
df["conta_propria"]  = df["conta_propria"].fillna(0).astype(int)
df["trab_domestico"] = df["trab_domestico"].fillna(0).astype(int)

print(f"  ocp_qualif  = 1: {df['ocp_qualif'].mean()*100:.1f}%")
print(f"  y_top20     = 1: {df['y_top20'].mean()*100:.1f}%")
print(f"  y_top10     = 1: {df['y_top10'].mean()*100:.1f}%")
print(f"  Brancos: {(df['negro']==0).sum():,}  |  Negros: {(df['negro']==1).sum():,}")

# ── Fórmulas ──────────────────────────────────────────────────────────────────
_IND   = ("negro + educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
          " + sexo_fem + idade_c + idade_sq"
          " + emprego_formal + setor_publico + conta_propria + trab_domestico")
_UPA   = "media_renda_upa_z + media_educ_upa_z + tx_desemprego_upa_z + pct_negro_upa_z"
_INTER = "negro:educ_superior_completo + negro:educ_pos_graduacao"

FORMULAS = {
    "M1": f"{{y}} ~ {_IND} + C(UF_str)",
    "M2": f"{{y}} ~ {_IND} + {_UPA} + C(UF_str)",
    "M3": f"{{y}} ~ {_IND} + {_UPA} + {_INTER} + C(UF_str)",
}
MODEL_LABELS = {
    "M1": "M1: Individuais + UF FE",
    "M2": "M2: + Contexto UPA",
    "M3": "M3: + negro×educação",
}

OUTCOMES = [
    ("ocp_qualif", "Ocupação Qualificada\n(CBO 1–4)"),
    ("y_top20",    "Renda no Top 20%\n(teto de vidro salarial)"),
    ("y_top10",    "Renda no Top 10%\n(decil superior)"),
]


def fit_logit(formula_str: str, data: pd.DataFrame):
    try:
        return smf.logit(formula_str, data=data).fit(
            method="bfgs", maxiter=400, disp=False, cov_type="HC1"
        )
    except Exception as e:
        print(f"    bfgs falhou ({e}), tentando newton ...")
        try:
            return smf.logit(formula_str, data=data).fit(
                method="newton", maxiter=400, disp=False, cov_type="HC1"
            )
        except Exception as e2:
            print(f"    FALHOU: {e2}")
            return None


def get_or_ci(m, var="negro"):
    if m is None or var not in m.params:
        return np.nan, np.nan, np.nan
    b, se = m.params[var], m.bse[var]
    return np.exp(b), np.exp(b - 1.96 * se), np.exp(b + 1.96 * se)


def get_ame(m, data, var="negro"):
    if m is None or var not in m.params:
        return np.nan
    b_neg = m.params[var]
    exog  = m.model.exog.copy()
    idx_v = list(m.model.exog_names).index(var)
    lp0   = exog @ m.params.values - exog[:, idx_v] * b_neg
    p1    = 1 / (1 + np.exp(-(lp0 + b_neg)))
    p0    = 1 / (1 + np.exp(-(lp0)))
    return float((p1 - p0).mean())


def stars(p):
    return "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))


# ── Ajustar modelos ───────────────────────────────────────────────────────────
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

# ── Tabela CSV ────────────────────────────────────────────────────────────────
rows = []
for y_col, y_label in OUTCOMES:
    for m_name in FORMULAS:
        m = results[y_col].get(m_name)
        or_, lo, hi = get_or_ci(m)
        sub = df[df[y_col].notna()]
        ame = get_ame(m, sub) * 100 if m is not None else np.nan
        p   = m.pvalues.get("negro", np.nan) if m is not None else np.nan
        inter_or = np.nan
        if m_name == "M3" and m is not None:
            nm = "negro:educ_superior_completo"
            if nm in m.params:
                inter_or = np.exp(m.params[nm])
        rows.append({
            "desfecho": y_col, "modelo": m_name,
            "OR_negro": round(or_, 4), "CI95_lo": round(lo, 4), "CI95_hi": round(hi, 4),
            "AME_pp":   round(ame, 3), "p_valor":  round(p,  4),
            "OR_inter_negxedu": round(inter_or, 4) if not np.isnan(inter_or) else np.nan,
        })
tbl = pd.DataFrame(rows)
tbl.to_csv(TABLES / "glmm_glassceil_full.csv", index=False, encoding="utf-8")
print("\nglmm_glassceil_full.csv salvo.")

# ── Interação negro × educação: variação do gap por nível de credencial ───────
print("\n--- Efeito moderador de educação no gap (M3) ---")
for y_col, y_label in OUTCOMES:
    m = results[y_col].get("M3")
    if m is None:
        continue
    print(f"\n  {y_col}:")
    for educ_label, nm in [("Superior completo", "negro:educ_superior_completo"),
                            ("Pós-graduação",    "negro:educ_pos_graduacao")]:
        if "negro" not in m.params or nm not in m.params:
            continue
        b_negro = m.params["negro"]
        b_inter = m.params.get(nm, 0)
        or_comb = np.exp(b_negro + b_inter)
        print(f"    {educ_label}: β_negro+inter={b_negro+b_inter:.4f} → OR={or_comb:.4f}")

# ── Figura: Forest plot OR por desfecho e modelo ─────────────────────────────
COLORS_M = {"M1": "#1565C0", "M2": "#B71C1C", "M3": "#2E7D32"}
n_out = len(OUTCOMES)

fig, axes = plt.subplots(1, n_out, figsize=(5 * n_out, 7), sharey=False)
if n_out == 1:
    axes = [axes]

for ax, (y_col, y_label) in zip(axes, OUTCOMES):
    x_m = np.arange(len(FORMULAS))
    for j, m_name in enumerate(FORMULAS):
        m = results[y_col].get(m_name)
        or_, lo, hi = get_or_ci(m)
        p = m.pvalues.get("negro", np.nan) if m else np.nan
        color = COLORS_M[m_name]
        ax.scatter(j, or_, s=120, color=color, zorder=5)
        ax.plot([j, j], [lo, hi], color=color, linewidth=2.5, zorder=4)
        label = f"{or_:.3f}{stars(p)}"
        ax.text(j, hi + 0.01, label, ha="center", va="bottom",
                fontsize=9, fontweight="bold", color=color)
    ax.axhline(1.0, color="gray", linewidth=1.2, linestyle="--")
    ax.set_xticks(x_m)
    ax.set_xticklabels([MODEL_LABELS[m] for m in FORMULAS], fontsize=8,
                       rotation=15, ha="right")
    ax.set_ylabel("Odds Ratio (negro vs. branco)" if ax == axes[0] else "")
    ax.set_title(y_label.replace("\n", " "), fontsize=10, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(0.5, 0.02, "OR < 1 → desvantagem negro",
            transform=ax.transAxes, ha="center", fontsize=8, color="gray", style="italic")

patches_legend = [mpatches.Patch(color=COLORS_M[m], label=MODEL_LABELS[m]) for m in FORMULAS]
fig.legend(handles=patches_legend, loc="lower center", ncol=3, fontsize=9,
           bbox_to_anchor=(0.5, -0.05))
fig.suptitle("Teto de Vidro Racial — Odds Ratios (população completa)\n"
             "Logit com UF efeito fixo e SE robusto (HC1)",
             fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(FIGURES / "glmm_glassceil_forest.png", dpi=150, bbox_inches="tight")
plt.close()
print("glmm_glassceil_forest.png salvo.")

# ── Figura: Probabilidade predita por raça × nível de escolaridade ────────────
fig, axes = plt.subplots(1, n_out, figsize=(5 * n_out, 6), sharey=False)
if n_out == 1:
    axes = [axes]

most_common_uf = df["UF_str"].mode().iloc[0]
mean_vals = {c: float(df[c].mean()) for c in
             ["idade_c", "idade_sq", "media_renda_upa_z", "media_educ_upa_z",
              "tx_desemprego_upa_z", "pct_negro_upa_z"]}
emp_mean = float(df["emprego_formal"].mean())
pub_mean  = float(df["setor_publico"].mean())
cp_mean   = float(df["conta_propria"].mean())
td_mean   = float(df["trab_domestico"].mean())

# 4 education categories: none / secondary / superior / pos-grad
EDUC_CATS = [
    ("Sem superior", dict(educ_medio_completo=1, educ_superior_completo=0, educ_pos_graduacao=0)),
    ("Superior",     dict(educ_medio_completo=0, educ_superior_completo=1, educ_pos_graduacao=0)),
    ("Pós-grad",     dict(educ_medio_completo=0, educ_superior_completo=0, educ_pos_graduacao=1)),
]
x_pos = np.arange(len(EDUC_CATS))
width = 0.35

for ax, (y_col, y_label) in zip(axes, OUTCOMES):
    m = results[y_col].get("M3") or results[y_col].get("M2")
    if m is None:
        continue
    probs_b, probs_n = [], []
    for _, educ_vals in EDUC_CATS:
        base = {
            "sexo_fem": 0, "idade_c": mean_vals["idade_c"],
            "idade_sq": mean_vals["idade_sq"],
            "emprego_formal": emp_mean, "setor_publico": pub_mean,
            "conta_propria": cp_mean, "trab_domestico": td_mean,
            "media_renda_upa_z": mean_vals["media_renda_upa_z"],
            "media_educ_upa_z": mean_vals["media_educ_upa_z"],
            "tx_desemprego_upa_z": mean_vals["tx_desemprego_upa_z"],
            "pct_negro_upa_z": mean_vals["pct_negro_upa_z"],
            "UF_str": most_common_uf,
            **educ_vals,
        }
        try:
            pb = float(m.predict(pd.DataFrame([{**base, "negro": 0}])).iloc[0]) * 100
            pn = float(m.predict(pd.DataFrame([{**base, "negro": 1}])).iloc[0]) * 100
        except Exception:
            pb, pn = np.nan, np.nan
        probs_b.append(pb)
        probs_n.append(pn)

    bars_b = ax.bar(x_pos - width/2, probs_b, width, color="#1565C0", alpha=0.85, label="Branco")
    bars_n = ax.bar(x_pos + width/2, probs_n, width, color="#B71C1C", alpha=0.85, label="Negro")
    ax.set_xticks(x_pos)
    ax.set_xticklabels([c for c, _ in EDUC_CATS], fontsize=9)
    ax.set_ylabel("Probabilidade predita (%)" if ax == axes[0] else "")
    ax.set_title(y_label.replace("\n", " "), fontsize=10, fontweight="bold")
    ax.legend(fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

fig.suptitle("Teto de Vidro Racial — Probabilidade Predita por Nível de Escolaridade\n"
             "Logit M3 com interação negro × credencial (população completa)",
             fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(FIGURES / "glmm_glassceil_probpredita.png", dpi=150, bbox_inches="tight")
plt.close()
print("glmm_glassceil_probpredita.png salvo.")

# ── Sumário final ─────────────────────────────────────────────────────────────
print("\n" + "="*72)
print("  SUMÁRIO — GLMM GLASS CEILING (população completa)")
print("="*72)
for y_col, y_label in OUTCOMES:
    lbl = y_label.replace("\n", " ")
    pb = df.loc[df["negro"] == 0, y_col].mean() * 100
    pn = df.loc[df["negro"] == 1, y_col].mean() * 100
    print(f"\n  {lbl}")
    print(f"    Branco: {pb:.1f}%  |  Negro: {pn:.1f}%  |  Gap bruto: {pb-pn:.1f} p.p.")
    for m_name in FORMULAS:
        m = results[y_col].get(m_name)
        if m is not None:
            or_, lo, hi = get_or_ci(m)
            sub = df[df[y_col].notna()]
            ame = get_ame(m, sub) * 100
            p   = m.pvalues.get("negro", np.nan)
            print(f"    {m_name}: OR={or_:.3f} [{lo:.3f}–{hi:.3f}]{stars(p)} | AME={ame:+.2f}pp")
print("\n" + "="*72)
print("=== GLMM GLASS CEILING CONCLUÍDO ===")
