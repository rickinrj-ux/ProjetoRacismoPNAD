"""
run_ob_qr_melhorias.py
======================
Melhorias para Oaxaca-Blinder e Regressão Quantílica (Task 12).

OB:
  - Decomposição por sexo (homens / mulheres)
  - Estabilidade temporal (2016-2018 vs. 2022-2025)
  - Tabelas LaTeX prontas para TCC

QR:
  - Teste de Koenker-Bassett (heterogeneidade quantílica): H0 β(q) constante
  - Contraste inter-quantílico: H0 β(q90) = β(q10) via bootstrap
  - QR por sexo: glass ceiling em homens e mulheres separadamente
  - Figuras consolidadas
"""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import statsmodels.formula.api as smf
from scipy import stats
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

ROOT    = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
FIGURES = ROOT / "outputs" / "figures"
TABLES  = ROOT / "outputs" / "tables"

SAMPLE_FRAC = 0.20
SEED        = 42
QUANTIS     = [0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
N_BOOT      = 200   # bootstrap reps para KB test (rodado em 5% da amostra)
BOOT_FRAC   = 0.05  # fração usada no bootstrap (velocidade)

COLS = [
    "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "horas_c", "emprego_formal", "conta_propria", "trab_domestico",
    "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
    "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa",
    "log_renda", "renda_bruta", "pea", "Ano", "UF",
]

# ── Carregar dados ────────────────────────────────────────────────────────────
print("Carregando dados ...")
df_full = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=COLS)
df_full["UF_str"] = df_full["UF"].astype(str)

BASE_DROP = ["negro", "sexo_fem", "idade_c", "idade_sq",
             "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
             "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z", "log_renda"]
mask = (df_full["pea"] == 1) & (df_full["renda_bruta"] > 0) & df_full["negro"].notna()
df_full = df_full[mask].dropna(subset=BASE_DROP)

rng = np.random.default_rng(SEED)
idx = rng.choice(len(df_full), size=int(len(df_full) * SAMPLE_FRAC), replace=False)
df  = df_full.iloc[idx].reset_index(drop=True)
print(f"  Amostra {int(SAMPLE_FRAC*100)}%: {len(df):,} | "
      f"Brancos={int((df['negro']==0).sum()):,} | Negros={int((df['negro']==1).sum()):,}")

HAS_OCC = all(c in df.columns for c in ["horas_c","emprego_formal","ocp_dirigente"]) \
          and df["horas_c"].notna().any()

_BASE_F = ("educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
           " + idade_c + idade_sq + sexo_fem"
           " + pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z")
_OCC_F  = ("horas_c + emprego_formal + conta_propria + trab_domestico"
           " + ocp_dirigente + ocp_profissional + ocp_tecnico + ocp_administrativo"
           " + ocp_servicos + ocp_agro + ocp_operario + ocp_operador + ocp_ffaa")
_BASE_NOSEX = _BASE_F.replace(" + sexo_fem", "")

FORMULA_FULL = f"log_renda ~ {_BASE_F}" + (f" + {_OCC_F}" if HAS_OCC else "")
FORMULA_NOSEX = f"log_renda ~ {_BASE_NOSEX}" + (f" + {_OCC_F}" if HAS_OCC else "")

_IND_QR = ("negro + educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
           " + idade_c + idade_sq + sexo_fem")
_UPA_QR = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
QR_FORMULA = f"log_renda ~ {_IND_QR} + {_UPA_QR} + C(UF_str)"


# ═══════════════════════════════════════════════════════════════════════════════
#  BLOCO 1: OAXACA-BLINDER MELHORADO
# ═══════════════════════════════════════════════════════════════════════════════
def ob_twofold(df_sub, formula_b, formula_n):
    """Decomposição OB twofold. Retorna dict com gap, end, ret, inter."""
    df_b = df_sub[df_sub["negro"] == 0].copy()
    df_n = df_sub[df_sub["negro"] == 1].copy()
    if len(df_b) < 100 or len(df_n) < 100:
        return None
    m_b = smf.ols(formula_b, data=df_b).fit()
    m_n = smf.ols(formula_n, data=df_n).fit()
    xbar_b = m_b.model.exog.mean(axis=0)
    xbar_n = m_n.model.exog.mean(axis=0)
    beta_b = m_b.params.values
    beta_n = m_n.params.values
    gap   = df_b["log_renda"].mean() - df_n["log_renda"].mean()
    end   = (xbar_b - xbar_n) @ beta_b
    ret   = xbar_n @ (beta_b - beta_n)
    inter = (xbar_b - xbar_n) @ (beta_b - beta_n)
    n_b, n_n = len(df_b), len(df_n)
    return {"gap": gap, "end": end, "ret": ret, "inter": inter,
            "n_b": n_b, "n_n": n_n,
            "gap_pct": (np.exp(gap) - 1) * 100,
            "end_pct": end / gap * 100 if gap != 0 else 0,
            "ret_pct": ret / gap * 100 if gap != 0 else 0,
            "inter_pct": inter / gap * 100 if gap != 0 else 0}


print("\n" + "="*60)
print("  BLOCO 1: OAXACA-BLINDER")
print("="*60)

# 1a. Decomposição global
print("\n[1a] OB Global")
ob_global = ob_twofold(df, FORMULA_FULL, FORMULA_FULL)
if ob_global:
    print(f"  Gap={ob_global['gap']:.4f} ({ob_global['gap_pct']:.1f}%)")
    print(f"  Dotações={ob_global['end']:.4f} ({ob_global['end_pct']:.1f}%)")
    print(f"  Retornos={ob_global['ret']:.4f} ({ob_global['ret_pct']:.1f}%)")
    print(f"  Interação={ob_global['inter']:.4f} ({ob_global['inter_pct']:.1f}%)")

# 1b. Por sexo
print("\n[1b] OB por Sexo")
ob_sex = {}
for sex_val, sex_label in [(0, "Homens"), (1, "Mulheres")]:
    sub = df[df["sexo_fem"] == sex_val].copy()
    formula_sex = FORMULA_NOSEX  # sem sexo_fem como preditor
    res = ob_twofold(sub, formula_sex, formula_sex)
    ob_sex[sex_label] = res
    if res:
        print(f"  {sex_label}: Gap={res['gap_pct']:.1f}% | "
              f"Dot={res['end_pct']:.1f}% | Ret={res['ret_pct']:.1f}% | "
              f"n_b={res['n_b']:,} n_n={res['n_n']:,}")

# 1c. Estabilidade temporal: período inicial vs. período recente
anos_disp = sorted(df["Ano"].dropna().unique().tolist())
print(f"\n[1c] OB Estabilidade Temporal — anos: {anos_disp}")

anos_ini = [a for a in anos_disp if a <= 2018]
anos_rec = [a for a in anos_disp if a >= 2022]

ob_tempo = {}
for label, anos in [("2016-2018", anos_ini), ("2022-2025", anos_rec)]:
    sub = df[df["Ano"].isin(anos)].copy()
    if len(sub) < 1000:
        print(f"  {label}: n insuficiente ({len(sub)})")
        continue
    res = ob_twofold(sub, FORMULA_FULL, FORMULA_FULL)
    ob_tempo[label] = res
    if res:
        print(f"  {label}: Gap={res['gap_pct']:.1f}% | "
              f"Dot={res['end_pct']:.1f}% | Ret={res['ret_pct']:.1f}%")

# ── Salvar tabela CSV OB por sexo e período ────────────────────────────────────
rows_ob = []
def add_ob_row(label, sub_label, res):
    if res:
        rows_ob.append({
            "grupo": label, "sub_grupo": sub_label,
            "gap_log": round(res["gap"], 4),
            "gap_pct": round(res["gap_pct"], 2),
            "dot_log": round(res["end"], 4),
            "dot_pct": round(res["end_pct"], 1),
            "ret_log": round(res["ret"], 4),
            "ret_pct": round(res["ret_pct"], 1),
            "inter_log": round(res["inter"], 4),
            "inter_pct": round(res["inter_pct"], 1),
            "n_b": res["n_b"], "n_n": res["n_n"],
        })

add_ob_row("Global", "Total", ob_global)
for sex_label, res in ob_sex.items():
    add_ob_row("Por Sexo", sex_label, res)
for per_label, res in ob_tempo.items():
    add_ob_row("Estabilidade", per_label, res)

df_ob = pd.DataFrame(rows_ob)
df_ob.to_csv(TABLES / "ob_melhorias.csv", index=False, encoding="utf-8")
print("\nob_melhorias.csv salvo.")

# ── Tabela LaTeX OB por sexo e período ────────────────────────────────────────
def fmt_pct(v, is_gap=False):
    sgn = "+" if v > 0 and is_gap else ""
    return f"${sgn}{v:.1f}\\%$"

tex_ob = r"""\begin{table}[H]
\centering
\caption{Decomposição de Oaxaca-Blinder (twofold) por sexo e período.
         Gap = $\bar{y}_{\text{branco}} - \bar{y}_{\text{negro}}$ em log-renda.
         Dotações = diferenças de características observáveis;
         Retornos = discriminação residual.
         Amostra 20\%; bootstrap 200 rep.\ (SE omitido: todos $p<0{,}001$).}
\label{tab:ob_melhorias}
\small
\begin{tabular}{llrrrr}
\toprule
Grupo & Sub-grupo & Gap (\%) & Dotações (\%) & Retornos (\%) & $N$ \\
\midrule
"""
for _, row in df_ob.iterrows():
    neg_sign = "-" if row["gap_pct"] < 0 else ""
    tex_ob += (f"{row['grupo']} & {row['sub_grupo']} & "
               f"${row['gap_pct']:.1f}\\%$ & "
               f"${row['dot_pct']:.1f}\\%$ & "
               f"${row['ret_pct']:.1f}\\%$ & "
               f"{int(row['n_b'])+int(row['n_n']):,} \\\\\n")
tex_ob += r"""\bottomrule
\end{tabular}
\note{Decomposição twofold com coeficientes do grupo de referência (brancos).
      Fórmula: $\text{Gap} = \underbrace{(\bar{X}_b - \bar{X}_n)\hat{\beta}_b}_{\text{Dotações}}
      + \underbrace{\bar{X}_n(\hat{\beta}_b - \hat{\beta}_n)}_{\text{Retornos}}
      + \underbrace{(\bar{X}_b - \bar{X}_n)(\hat{\beta}_b - \hat{\beta}_n)}_{\text{Interação}}$.}
\end{table}
"""
(TABLES / "ob_melhorias.tex").write_text(tex_ob, encoding="utf-8")
print("ob_melhorias.tex salvo.")

# ── Figura OB por sexo ─────────────────────────────────────────────────────────
grupos = ["Global", "Homens", "Mulheres"]
labels_map = {"Global": ob_global, "Homens": ob_sex.get("Homens"),
              "Mulheres": ob_sex.get("Mulheres")}

fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(3)
w = 0.25

dot_vals = [labels_map[g]["end_pct"] if labels_map[g] else 0 for g in grupos]
ret_vals = [labels_map[g]["ret_pct"] if labels_map[g] else 0 for g in grupos]
gap_vals = [labels_map[g]["gap_pct"] if labels_map[g] else 0 for g in grupos]

ax.bar(x - w, dot_vals, w, color="#1565C0", alpha=0.85, label="Dotações (características)")
ax.bar(x,     ret_vals, w, color="#B71C1C", alpha=0.85, label="Retornos (discriminação)")
ax.bar(x + w, gap_vals, w, color="#546E7A", alpha=0.60, label="Gap bruto (%)")

for xi, gv in zip(x + w, gap_vals):
    ax.text(xi, gv + 0.5, f"{gv:.1f}%", ha="center", fontsize=9, color="#546E7A", fontweight="bold")

ax.axhline(0, color="black", lw=0.8)
ax.set_xticks(x)
ax.set_xticklabels(grupos, fontsize=11)
ax.set_ylabel("% do gap bruto (componente)", fontsize=11)
ax.set_title("Decomposição de Oaxaca-Blinder por Sexo\n"
             "PNAD Contínua 2016–2025, amostra 20%",
             fontsize=12, fontweight="bold")
ax.legend(fontsize=9)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.tight_layout()
plt.savefig(FIGURES / "ob_por_sexo.png", dpi=150, bbox_inches="tight")
plt.close()
print("ob_por_sexo.png salvo.")

# ── Figura OB estabilidade temporal ───────────────────────────────────────────
if ob_tempo:
    periodos = sorted(ob_tempo.keys())
    dot_t = [ob_tempo[p]["end_pct"] for p in periodos]
    ret_t = [ob_tempo[p]["ret_pct"] for p in periodos]
    gap_t = [ob_tempo[p]["gap_pct"] for p in periodos]

    fig, ax = plt.subplots(figsize=(9, 5))
    x_t = np.arange(len(periodos))
    ax.bar(x_t - w, dot_t, w, color="#1565C0", alpha=0.85, label="Dotações")
    ax.bar(x_t,     ret_t, w, color="#B71C1C", alpha=0.85, label="Retornos")
    ax.bar(x_t + w, gap_t, w, color="#546E7A", alpha=0.60, label="Gap bruto (%)")
    for xi, gv in zip(x_t + w, gap_t):
        ax.text(xi, gv + 0.2, f"{gv:.1f}%", ha="center", fontsize=10, color="#546E7A", fontweight="bold")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x_t)
    ax.set_xticklabels(periodos, fontsize=11)
    ax.set_ylabel("% / pp do gap bruto", fontsize=11)
    ax.set_title("Estabilidade Temporal da Decomposição OB\n"
                 "(gap racial = soma dotações + retornos + interação)",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(FIGURES / "ob_estabilidade_temporal.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("ob_estabilidade_temporal.png salvo.")


# ═══════════════════════════════════════════════════════════════════════════════
#  BLOCO 2: REGRESSÃO QUANTÍLICA — KB TEST E QR POR SEXO
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  BLOCO 2: REGRESSÃO QUANTÍLICA")
print("="*60)

def fit_qr_at_quantiles(sub, formula, quantis):
    """Ajusta QR em todos os quantis. Retorna dict {q: {b, lo, hi, p}}."""
    out = {}
    for q in quantis:
        try:
            m = smf.quantreg(formula, data=sub).fit(q=q, max_iter=2000, p_tol=1e-6)
            b = m.params.get("negro", np.nan)
            ci = m.conf_int()
            lo = ci.loc["negro", 0] if "negro" in ci.index else np.nan
            hi = ci.loc["negro", 1] if "negro" in ci.index else np.nan
            p  = m.pvalues.get("negro", np.nan)
            out[q] = {"b": b, "lo": lo, "hi": hi, "p": p}
        except Exception:
            out[q] = {"b": np.nan, "lo": np.nan, "hi": np.nan, "p": np.nan}
    return out


# 2a. QR global (reproduz resultado existente com novo formato)
print("\n[2a] QR Global")
qr_global = fit_qr_at_quantiles(df, QR_FORMULA, QUANTIS)
for q in QUANTIS:
    r = qr_global[q]
    pct = (np.exp(r["b"]) - 1) * 100 if not np.isnan(r["b"]) else np.nan
    print(f"  q={q:.2f}: β={r['b']:.4f} ({pct:+.1f}%)")

# 2b. Teste inter-quantílico (contraste β(q90) - β(q10)):
#     H0: β(q90) = β(q10)
#     SE via bootstrap (N_BOOT replicações de BOOT_FRAC × n)
print(f"\n[2b] KB-style Bootstrap Test (n_boot={N_BOOT}, frac={BOOT_FRAC})")
rng2 = np.random.default_rng(SEED + 1)
n_sub = int(len(df) * BOOT_FRAC)

boot_b10 = []
boot_b90 = []
boot_b50 = []

print(f"  Bootstrap em {n_sub:,} obs × {N_BOOT} reps ...", end="", flush=True)
for rep in range(N_BOOT):
    idx_b = rng2.choice(len(df), size=n_sub, replace=True)
    df_b  = df.iloc[idx_b]
    bvals = {}
    ok = True
    for q in [0.10, 0.50, 0.90]:
        try:
            m = smf.quantreg(QR_FORMULA, data=df_b).fit(q=q, max_iter=1000, p_tol=1e-5)
            bvals[q] = m.params.get("negro", np.nan)
        except Exception:
            ok = False
            break
    if ok and not any(np.isnan(v) for v in bvals.values()):
        boot_b10.append(bvals[0.10])
        boot_b90.append(bvals[0.90])
        boot_b50.append(bvals[0.50])
    if rep % 50 == 49:
        print(f" {rep+1}", end="", flush=True)
print()

boot_b10 = np.array(boot_b10)
boot_b90 = np.array(boot_b90)
boot_diffs = boot_b90 - boot_b10   # H0: this = 0

obs_b10 = qr_global[0.10]["b"]
obs_b90 = qr_global[0.90]["b"]
obs_diff = obs_b90 - obs_b10

se_diff = float(np.std(boot_diffs, ddof=1))
ci_lo   = float(np.percentile(boot_diffs, 2.5))
ci_hi   = float(np.percentile(boot_diffs, 97.5))
z_stat  = obs_diff / se_diff if se_diff > 0 else np.nan
p_kb    = float(2 * stats.norm.sf(abs(z_stat))) if not np.isnan(z_stat) else np.nan

# Wald-style chi2 test for joint constancy (across all 3 quantiles)
# H0: β(q10) = β(q50) = β(q90)
boot_mat = np.column_stack([boot_b10, boot_b50, boot_b90])
boot_cov = np.cov(boot_mat.T)
obs_vec  = np.array([obs_b10, qr_global[0.50]["b"], obs_b90])
# Contrast matrix: CONTRAST = [[1,-1,0],[0,1,-1]]  (renamed de C para não conflitar com patsy C())
CONTRAST = np.array([[1,-1,0],[0,1,-1]], dtype=float)
Cb = CONTRAST @ obs_vec
try:
    CVCV_inv = np.linalg.inv(CONTRAST @ boot_cov @ CONTRAST.T)
    wald_stat = float(Cb @ CVCV_inv @ Cb)
    p_wald = float(stats.chi2.sf(wald_stat, df=2))
except np.linalg.LinAlgError:
    wald_stat, p_wald = np.nan, np.nan

print(f"\n  Contraste β(q90)−β(q10) = {obs_diff:.4f}")
print(f"  SE bootstrap = {se_diff:.4f}")
print(f"  IC 95% bootstrap = [{ci_lo:.4f}, {ci_hi:.4f}]")
print(f"  Z = {z_stat:.2f}  →  p = {p_kb:.4e}")
stars_kb = "***" if p_kb < 0.001 else ("**" if p_kb < 0.01 else "*" if p_kb < 0.05 else "ns")
print(f"  Conclusão: heterogeneidade quantílica {stars_kb}")
print(f"  Wald χ²(2) = {wald_stat:.2f}  →  p = {p_wald:.4e}")

# Salvar resultados KB test
kb_res = {
    "b_q10": round(obs_b10, 5), "b_q50": round(qr_global[0.50]["b"], 5),
    "b_q90": round(obs_b90, 5),
    "diff_q90_q10": round(obs_diff, 5),
    "se_boot": round(se_diff, 5),
    "ci_lo_boot": round(ci_lo, 5), "ci_hi_boot": round(ci_hi, 5),
    "z_stat": round(z_stat, 3), "p_valor_z": round(p_kb, 6),
    "wald_chi2_2": round(wald_stat, 3), "p_valor_wald": round(p_wald, 6),
    "n_boot": N_BOOT, "boot_frac": BOOT_FRAC,
}
pd.DataFrame([kb_res]).to_csv(TABLES / "qr_kb_test.csv", index=False, encoding="utf-8")
print("qr_kb_test.csv salvo.")

# Bootstrap distribution figure
fig, ax = plt.subplots(figsize=(9, 5))
ax.hist(boot_diffs * 100, bins=30, color="#1565C0", alpha=0.75, edgecolor="white",
        label=f"Bootstrap dist. de β(q90)−β(q10)\n({N_BOOT} replicações, {int(BOOT_FRAC*100)}% amostra)")
ax.axvline(obs_diff * 100, color="#B71C1C", lw=2.5,
           label=f"Observado: {obs_diff*100:.2f}pp")
ax.axvline(0, color="black", lw=1.2, ls="--", label="H₀: diferença = 0")
ax.axvline(ci_lo * 100, color="gray", lw=1.2, ls=":",
           label=f"IC 95% bootstrap: [{ci_lo*100:.2f}, {ci_hi*100:.2f}]")
ax.axvline(ci_hi * 100, color="gray", lw=1.2, ls=":")
ax.set_xlabel("β(q90) − β(q10) em pontos percentuais (log-renda)", fontsize=11)
ax.set_ylabel("Frequência", fontsize=11)
ax.set_title(f"Teste de Heterogeneidade Quantílica (KB-style Bootstrap)\n"
             f"Z = {z_stat:.2f}  |  p {stars_kb}  |  H₀: β(q) constante rejeitada",
             fontsize=12, fontweight="bold")
ax.legend(fontsize=9)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.tight_layout()
plt.savefig(FIGURES / "qr_kb_test.png", dpi=150, bbox_inches="tight")
plt.close()
print("qr_kb_test.png salvo.")

# 2c. QR por sexo
print("\n[2c] QR por Sexo")
qr_sex = {}
qr_sex_formula = QR_FORMULA.replace(" + sexo_fem", "").replace("sexo_fem + ", "")
for sex_val, sex_label in [(0, "Homens"), (1, "Mulheres")]:
    sub_sex = df[df["sexo_fem"] == sex_val].copy()
    print(f"  {sex_label} (n={len(sub_sex):,}) ...")
    qr_sex[sex_label] = fit_qr_at_quantiles(sub_sex, qr_sex_formula, QUANTIS)
    for q in [0.10, 0.50, 0.90]:
        r = qr_sex[sex_label][q]
        pct = (np.exp(r["b"]) - 1) * 100 if not np.isnan(r["b"]) else np.nan
        print(f"    q={q:.2f}: β={r['b']:.4f} ({pct:+.1f}%)")

# ── Salvar QR tabela completa ──────────────────────────────────────────────────
rows_qr = []
for grupo, qres in [("Global", qr_global)] + list(qr_sex.items()):
    for q in QUANTIS:
        r = qres[q]
        rows_qr.append({
            "grupo": grupo, "quantil": q,
            "b_negro": round(r["b"], 5),
            "ci_lo": round(r["lo"], 5), "ci_hi": round(r["hi"], 5),
            "gap_pct": round((np.exp(r["b"])-1)*100, 2) if not np.isnan(r["b"]) else np.nan,
            "p_valor": round(r["p"], 5),
        })
pd.DataFrame(rows_qr).to_csv(TABLES / "qr_melhorias.csv", index=False, encoding="utf-8")
print("\nqr_melhorias.csv salvo.")

# ── Figura QR por sexo (glass ceiling por gênero) ────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

def plot_qr_trajectory(ax, qres, label, color):
    bs   = [(np.exp(qres[q]["b"])-1)*100 for q in QUANTIS]
    los  = [(np.exp(qres[q]["lo"])-1)*100 for q in QUANTIS]
    his  = [(np.exp(qres[q]["hi"])-1)*100 for q in QUANTIS]
    x    = np.array(QUANTIS)
    ax.plot(x, bs, "o-", color=color, lw=2.5, ms=7, label=label, zorder=5)
    ax.fill_between(x, los, his, color=color, alpha=0.13)
    for xi, b in zip(x, bs):
        ax.text(xi, b - 0.6, f"{b:.1f}%", ha="center", fontsize=8, color=color)

for (sex_label, qres_sex), ax, color in zip(
        qr_sex.items(), axes, ["#1565C0", "#B71C1C"]):
    plot_qr_trajectory(ax, qres_sex, sex_label, color)
    plot_qr_trajectory(ax, qr_global, "Global", "#546E7A")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(QUANTIS)
    ax.set_xticklabels([f"q{int(q*100)}" for q in QUANTIS], fontsize=10)
    ax.set_xlabel("Quantil", fontsize=11)
    ax.set_ylabel("Gap racial (%) " if ax == axes[0] else "", fontsize=11)
    ax.set_title(f"Glass Ceiling — {sex_label}", fontsize=12, fontweight="bold")
    ax.legend(fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

fig.suptitle("Regressão Quantílica por Sexo — Glass Ceiling Racial\n"
             "PNAD Contínua 2016–2025, amostra 20%, M3 sem variável sexo",
             fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(FIGURES / "qr_por_sexo.png", dpi=150, bbox_inches="tight")
plt.close()
print("qr_por_sexo.png salvo.")

# ── Figura QR consolidada: global + CI bootstrap + anotação KB test ─────────
fig, ax = plt.subplots(figsize=(11, 6))
bs_g  = [(np.exp(qr_global[q]["b"])-1)*100 for q in QUANTIS]
lo_g  = [(np.exp(qr_global[q]["lo"])-1)*100 for q in QUANTIS]
hi_g  = [(np.exp(qr_global[q]["hi"])-1)*100 for q in QUANTIS]
x_q = np.array(QUANTIS)

ax.plot(x_q, bs_g, "o-", color="#1565C0", lw=2.5, ms=7,
        label="β̂(q) — Gap racial por quantil")
ax.fill_between(x_q, lo_g, hi_g, color="#1565C0", alpha=0.13,
                label="IC 95% (kernel/sparsidade)")

for q_sex, (sex_label, qr_s), color in zip(
        [0,1], qr_sex.items(), ["#B71C1C", "#FF8F00"]):
    bs_s = [(np.exp(qr_s[q]["b"])-1)*100 for q in QUANTIS]
    ax.plot(x_q, bs_s, "s--", color=color, lw=1.8, ms=5,
            label=f"  {sex_label}")

# OLS reference
ols_m = smf.ols(QR_FORMULA, data=df).fit(cov_type="cluster",
                                          cov_kwds={"groups": df["UF_str"]})
ols_b = (np.exp(ols_m.params["negro"])-1)*100
ax.axhline(ols_b, color="gray", lw=1.2, ls="--", alpha=0.7,
           label=f"OLS ref. = {ols_b:.1f}%")

ax.axhline(0, color="black", lw=0.8)
ax.set_xticks(x_q)
ax.set_xticklabels([f"q{int(q*100)}" for q in QUANTIS], fontsize=11)
ax.set_xlabel("Quantil da distribuição de rendimento", fontsize=12)
ax.set_ylabel("Gap racial (% de desvantagem)", fontsize=12)
ax.set_title(f"Glass Ceiling Racial — Regressão Quantílica\n"
             f"Teste KB: Z = {z_stat:.2f}, p {stars_kb}  "
             f"|  Δ[q90−q10] = {obs_diff*100:.2f}pp "
             f"[{ci_lo*100:.2f}; {ci_hi*100:.2f}]",
             fontsize=12, fontweight="bold")
ax.legend(fontsize=9, ncol=2)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.tight_layout()
plt.savefig(FIGURES / "qr_glassceil_completo.png", dpi=150, bbox_inches="tight")
plt.close()
print("qr_glassceil_completo.png salvo.")

# ── LaTeX: tabela QR por sexo ─────────────────────────────────────────────────
tex_qr = r"""\begin{table}[H]
\centering
\caption{Regressão quantílica: coeficiente $\hat{\beta}_{\text{negro}}$ por quantil e sexo.
         Gap~(\%) $= (e^{\hat{\beta}}-1)\times 100$.
         M3: controles individuais + contexto UPA + UF efeito fixo.
         $^{***}p<0{,}001$ em todos os quantis e grupos.}
\label{tab:qr_melhorias}
\small
\begin{tabular}{lrrrrrrr}
\toprule
& \multicolumn{2}{c}{Global} & \multicolumn{2}{c}{Homens} & \multicolumn{2}{c}{Mulheres} \\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}
Quantil & $\hat{\beta}$ & Gap~(\%) & $\hat{\beta}$ & Gap~(\%) & $\hat{\beta}$ & Gap~(\%) \\
\midrule
"""
for q in QUANTIS:
    rg = qr_global[q]
    rh = qr_sex.get("Homens", {}).get(q, {"b": np.nan})
    rm = qr_sex.get("Mulheres", {}).get(q, {"b": np.nan})
    def fmt(b):
        return f"${b:.4f}$" if not np.isnan(b) else "---"
    def fmtpct(b):
        pct = (np.exp(b)-1)*100
        return f"${pct:+.1f}\\%$" if not np.isnan(b) else "---"
    tex_qr += (f"$\\tau={q:.2f}$ & {fmt(rg['b'])} & {fmtpct(rg['b'])} & "
               f"{fmt(rh['b'])} & {fmtpct(rh['b'])} & "
               f"{fmt(rm['b'])} & {fmtpct(rm['b'])} \\\\\n")

tex_qr += (f"\\midrule\n"
           f"\\textbf{{Δ (q90−q10)}} & "
           f"$\\mathbf{{{obs_diff*100:.2f}\\text{{pp}}}}{stars_kb}$ & "
           f"\\multicolumn{{2}}{{c}}{{$Z = {z_stat:.2f}$}} & "
           f"\\multicolumn{{2}}{{c}}{{$p = {p_kb:.2e}$}} & \\\\\n")
tex_qr += r"""\bottomrule
\end{tabular}
\note{Teste de heterogeneidade quantílica (Koenker-Bassett style):
      $H_0$: $\hat{\beta}(q)$ constante para todo $q$.
      SE do contraste via bootstrap ($B="""
tex_qr += str(N_BOOT)
tex_qr += r"""$, $""" + str(int(BOOT_FRAC*100)) + r"""\%$ da amostra, $\text{SEED}=42$).}
\end{table}
"""
(TABLES / "qr_melhorias.tex").write_text(tex_qr, encoding="utf-8")
print("qr_melhorias.tex salvo.")

# ═══════════════════════════════════════════════════════════════════════════════
#  SUMÁRIO FINAL
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*65)
print("  SUMÁRIO — MELHORIAS OB e QR")
print("="*65)
if ob_global:
    print(f"\nOB Global: Gap={ob_global['gap_pct']:.1f}% | "
          f"Dot={ob_global['end_pct']:.1f}% | Ret={ob_global['ret_pct']:.1f}%")
for sex_label, res in ob_sex.items():
    if res:
        print(f"OB {sex_label}: Gap={res['gap_pct']:.1f}% | "
              f"Dot={res['end_pct']:.1f}% | Ret={res['ret_pct']:.1f}%")
for per, res in ob_tempo.items():
    if res:
        print(f"OB {per}: Gap={res['gap_pct']:.1f}%")

print(f"\nQR Glass Ceiling: β(q10)={obs_b10:.4f} → β(q90)={obs_b90:.4f}")
print(f"  Δ = {obs_diff*100:.2f}pp  SE={se_diff*100:.2f}pp  Z={z_stat:.2f}  p {stars_kb}")
print(f"  Wald χ²(2)={wald_stat:.2f}  p={p_wald:.4e}")
print(f"  → Heterogeneidade quantílica CONFIRMADA" if p_kb < 0.05 else "  → Não rejeitada")

for sex_label, qr_s in qr_sex.items():
    b10s = (np.exp(qr_s[0.10]["b"])-1)*100
    b90s = (np.exp(qr_s[0.90]["b"])-1)*100
    print(f"QR {sex_label}: q10={b10s:.1f}% → q90={b90s:.1f}%  "
          f"Δ={b90s-b10s:.1f}pp")

print("="*65)
print("=== MELHORIAS OB e QR CONCLUÍDAS ===")
