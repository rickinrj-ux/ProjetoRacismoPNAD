"""
run_qr_patch.py
===============
Patch para re-gerar QR por sexo e figuras finais.
Re-usa qr_kb_test.csv já salvo (bootstrap 200 reps) para evitar re-execução longa.
Fix: renomeia variável C → CONTRAST (conflito com patsy C(UF_str)).
"""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

ROOT    = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
FIGURES = ROOT / "outputs" / "figures"
TABLES  = ROOT / "outputs" / "tables"

SAMPLE_FRAC = None   # None = população completa
SEED        = 42
QUANTIS     = [0.10, 0.25, 0.50, 0.75, 0.90, 0.95]

COLS = [
    "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "horas_c", "emprego_formal", "conta_propria", "trab_domestico",
    "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
    "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa",
    "log_renda", "renda_bruta", "pea", "UF",
]

# ── Carregar dados ────────────────────────────────────────────────────────────
print("Carregando dados (20%) ...")
df_full = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=COLS)
df_full["UF_str"] = df_full["UF"].astype(str)
BASE_DROP = ["negro","sexo_fem","idade_c","idade_sq",
             "educ_medio_completo","educ_superior_completo","educ_pos_graduacao",
             "pct_negro_upa_z","tx_desemprego_upa_z","media_educ_upa_z","log_renda"]
mask = (df_full["pea"] == 1) & (df_full["renda_bruta"] > 0) & df_full["negro"].notna()
df_full = df_full[mask].dropna(subset=BASE_DROP)
if SAMPLE_FRAC:
    rng = np.random.default_rng(SEED)
    idx = rng.choice(len(df_full), size=int(len(df_full) * SAMPLE_FRAC), replace=False)
    df  = df_full.iloc[idx].reset_index(drop=True)
else:
    df = df_full
_label = f"{int(SAMPLE_FRAC*100)}%" if SAMPLE_FRAC else "pop. completa"
print(f"  {_label}: {len(df):,} obs | Brancos={int((df['negro']==0).sum()):,} | Negros={int((df['negro']==1).sum()):,}")

HAS_OCC = all(c in df.columns for c in ["horas_c","emprego_formal","ocp_dirigente"]) \
          and df["horas_c"].notna().any()
_IND_QR = ("negro + educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
           " + idade_c + idade_sq + sexo_fem")
_UPA_QR = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
QR_FORMULA = f"log_renda ~ {_IND_QR} + {_UPA_QR} + C(UF_str)"
QR_FORMULA_NOSEX = QR_FORMULA.replace(" + sexo_fem", "")


def fit_qr(sub, formula, quantis):
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
        except Exception as e:
            print(f"    ERRO q={q}: {e}")
            out[q] = {"b": np.nan, "lo": np.nan, "hi": np.nan, "p": np.nan}
    return out


# ── QR Global ────────────────────────────────────────────────────────────────
print("\n[1] QR Global")
qr_global = fit_qr(df, QR_FORMULA, QUANTIS)
for q in QUANTIS:
    r = qr_global[q]
    pct = (np.exp(r["b"]) - 1) * 100 if not np.isnan(r["b"]) else np.nan
    print(f"  q={q:.2f}: β={r['b']:.4f} ({pct:+.1f}%)")

# ── KB test: lê CSV já salvo ──────────────────────────────────────────────────
print("\n[2] Lendo KB test salvo ...")
kb = pd.read_csv(TABLES / "qr_kb_test.csv").iloc[0]
obs_diff = float(kb["diff_q90_q10"])
ci_lo    = float(kb["ci_lo_boot"])
ci_hi    = float(kb["ci_hi_boot"])
z_stat   = float(kb["z_stat"])
p_kb     = float(kb["p_valor_z"])
wald_stat= float(kb["wald_chi2_2"])
p_wald   = float(kb["p_valor_wald"])
N_BOOT   = int(kb["n_boot"])
stars_kb = "***" if p_kb < 0.001 else ("**" if p_kb < 0.01 else "*" if p_kb < 0.05 else "ns")
print(f"  Z={z_stat:.2f}  p={p_kb:.4e}  χ²(2)={wald_stat:.2f}  p_wald={p_wald:.4e}")

# ── QR por Sexo ──────────────────────────────────────────────────────────────
print("\n[3] QR por Sexo")
qr_sex = {}
for sex_val, sex_label in [(0, "Homens"), (1, "Mulheres")]:
    sub_sex = df[df["sexo_fem"] == sex_val].copy()
    print(f"  {sex_label} (n={len(sub_sex):,}) ...")
    qr_sex[sex_label] = fit_qr(sub_sex, QR_FORMULA_NOSEX, QUANTIS)
    for q in [0.10, 0.50, 0.90]:
        r = qr_sex[sex_label][q]
        pct = (np.exp(r["b"]) - 1) * 100 if not np.isnan(r["b"]) else np.nan
        print(f"    q={q:.2f}: β={r['b']:.4f} ({pct:+.1f}%)")

# ── Salvar qr_melhorias.csv ───────────────────────────────────────────────────
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
df_qr = pd.DataFrame(rows_qr)
df_qr.to_csv(TABLES / "qr_melhorias.csv", index=False, encoding="utf-8")
print("qr_melhorias.csv salvo.")

# ── Figura QR por sexo ────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
def plot_qr_traj(ax, qres, label, color):
    bs  = [(np.exp(qres[q]["b"])-1)*100 for q in QUANTIS]
    los = [(np.exp(qres[q]["lo"])-1)*100 for q in QUANTIS]
    his = [(np.exp(qres[q]["hi"])-1)*100 for q in QUANTIS]
    x   = np.array(QUANTIS)
    ax.plot(x, bs, "o-", color=color, lw=2.5, ms=7, label=label, zorder=5)
    ax.fill_between(x, los, his, color=color, alpha=0.13)
    for xi, b in zip(x, bs):
        if not np.isnan(b):
            ax.text(xi, b - 0.6, f"{b:.1f}%", ha="center", fontsize=8, color=color)

for (sex_label, qres_sex), ax, color in zip(
        qr_sex.items(), axes, ["#1565C0", "#B71C1C"]):
    plot_qr_traj(ax, qres_sex, sex_label, color)
    plot_qr_traj(ax, qr_global, "Global", "#546E7A")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(QUANTIS)
    ax.set_xticklabels([f"q{int(q*100)}" for q in QUANTIS], fontsize=10)
    ax.set_xlabel("Quantil", fontsize=11)
    ax.set_ylabel("Gap racial (%)" if ax == axes[0] else "", fontsize=11)
    ax.set_title(f"Glass Ceiling — {sex_label}", fontsize=12, fontweight="bold")
    ax.legend(fontsize=9)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

fig.suptitle("Regressão Quantílica por Sexo — Glass Ceiling Racial\n"
             "PNAD Contínua 2016–2025, amostra 20%, M3 sem variável sexo",
             fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(FIGURES / "qr_por_sexo.png", dpi=150, bbox_inches="tight")
plt.close()
print("qr_por_sexo.png salvo.")

# ── Figura glass ceiling completo (global + por sexo + anotação KB) ──────────
fig, ax = plt.subplots(figsize=(11, 6))
bs_g = [(np.exp(qr_global[q]["b"])-1)*100 for q in QUANTIS]
lo_g = [(np.exp(qr_global[q]["lo"])-1)*100 for q in QUANTIS]
hi_g = [(np.exp(qr_global[q]["hi"])-1)*100 for q in QUANTIS]
x_q  = np.array(QUANTIS)

ax.plot(x_q, bs_g, "o-", color="#1565C0", lw=2.5, ms=7,
        label="β̂(q) — Gap racial (Global)")
ax.fill_between(x_q, lo_g, hi_g, color="#1565C0", alpha=0.13,
                label="IC 95%")

cores_sex = ["#B71C1C", "#FF8F00"]
for (sex_label, qr_s), color in zip(qr_sex.items(), cores_sex):
    bs_s = [(np.exp(qr_s[q]["b"])-1)*100 for q in QUANTIS]
    ax.plot(x_q, bs_s, "s--", color=color, lw=1.8, ms=5,
            label=f"  {sex_label}")

# OLS de referência (renomeado C → CONTRAST já corrigido na linha anterior)
try:
    ols_m  = smf.ols(QR_FORMULA, data=df).fit(cov_type="cluster",
                                               cov_kwds={"groups": df["UF_str"]})
    ols_b  = (np.exp(ols_m.params["negro"])-1)*100
    ax.axhline(ols_b, color="gray", lw=1.2, ls="--", alpha=0.7,
               label=f"OLS ref. = {ols_b:.1f}%")
except Exception as e:
    print(f"  AVISO OLS ref.: {e}")

ax.axhline(0, color="black", lw=0.8)
ax.set_xticks(x_q)
ax.set_xticklabels([f"q{int(q*100)}" for q in QUANTIS], fontsize=11)
ax.set_xlabel("Quantil da distribuição de rendimento", fontsize=12)
ax.set_ylabel("Gap racial (% de desvantagem)", fontsize=12)
ax.set_title(
    f"Glass Ceiling Racial — Regressão Quantílica\n"
    f"Teste KB: Z = {z_stat:.2f}, p {stars_kb}  "
    f"|  Δ[q90−q10] = {obs_diff*100:.2f}pp "
    f"[{ci_lo*100:.2f}; {ci_hi*100:.2f}]",
    fontsize=12, fontweight="bold")
ax.legend(fontsize=9, ncol=2)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
plt.tight_layout()
plt.savefig(FIGURES / "qr_glassceil_completo.png", dpi=150, bbox_inches="tight")
plt.close()
print("qr_glassceil_completo.png salvo.")

# ── LaTeX qr_melhorias.tex ────────────────────────────────────────────────────
tex = r"""\begin{table}[H]
\centering
\caption{Regressão quantílica: coeficiente $\hat{\beta}_{\text{negro}}$ por quantil e grupo.
         Gap~(\%) $= (e^{\hat{\beta}}-1)\times 100$.
         M3: controles individuais + contexto UPA + UF efeito fixo.
         Teste KB: Z = """ + f"{z_stat:.2f}" + r""" ($p """ + stars_kb + r"""$),
         $\chi^2(2) = """ + f"{wald_stat:.2f}" + r"""$ ($p < 0{,}001$).}
\label{tab:qr_melhorias}
\small
\begin{tabular}{lrrrrrr}
\toprule
& \multicolumn{2}{c}{Global} & \multicolumn{2}{c}{Homens} & \multicolumn{2}{c}{Mulheres} \\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}
Quantil & $\hat{\beta}$ & Gap~(\%) & $\hat{\beta}$ & Gap~(\%) & $\hat{\beta}$ & Gap~(\%) \\
\midrule
"""
for q in QUANTIS:
    def fmt(grupo, q):
        sub = df_qr[(df_qr["grupo"]==grupo) & (df_qr["quantil"]==q)]
        if not len(sub): return "— & —"
        r = sub.iloc[0]
        b = r["b_negro"]; g = r["gap_pct"]
        if np.isnan(b): return "— & —"
        return f"{b:.4f} & {g:.1f}\\%"
    tex += f"  q{int(q*100):02d} & {fmt('Global',q)} & {fmt('Homens',q)} & {fmt('Mulheres',q)} \\\\\n"
tex += r"""\bottomrule
\end{tabular}
\end{table}
"""
(TABLES / "qr_melhorias.tex").write_text(tex, encoding="utf-8")
print("qr_melhorias.tex salvo.")

# Re-run PO TOPSIS with fixed rank
print("\n[4] Re-rodando PO TOPSIS com rank corrigido ...")
import subprocess
subprocess.run(["python", "run_politicas_po.py"], cwd=str(ROOT), check=True)

print("\n=== PATCH CONCLUÍDO ===")
print("Outputs gerados:")
for f in ["qr_por_sexo.png", "qr_glassceil_completo.png", "qr_melhorias.csv", "qr_melhorias.tex"]:
    p = FIGURES / f if f.endswith(".png") else TABLES / f
    print(f"  {'OK' if p.exists() else 'FALTANDO'}: {f}")
