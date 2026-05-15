"""
run_regressao_quantilica.py
Regressão Quantílica do gap salarial racial — PNAD Contínua 2016–2025.

Estima o coeficiente de 'negro' em log_renda nos quantis q∈{0.10,0.25,0.50,0.75,0.90,0.95}
com e sem controles de composição ocupacional (M3 e M4), revelando a estrutura do glass ceiling.

Se β̂_negro(q) decresce com q → gap aumenta no topo = glass ceiling racial confirmado.
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

print("Carregando dados ...")
df = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=COLS)
df["UF_str"] = df["UF"].astype(str)

mask = (df["pea"] == 1) & (df["renda_bruta"] > 0) & (df["negro"].notna())
df   = df[mask].copy()

BASE_DROP = ["negro","sexo_fem","idade_c","idade_sq",
             "educ_medio_completo","educ_superior_completo","educ_pos_graduacao",
             "pct_negro_upa_z","tx_desemprego_upa_z","media_educ_upa_z","log_renda"]
df = df.dropna(subset=BASE_DROP)

rng = np.random.default_rng(SEED)
idx = rng.choice(len(df), size=int(len(df) * SAMPLE_FRAC), replace=False)
df  = df.iloc[idx].reset_index(drop=True)
print(f"  Amostra {int(SAMPLE_FRAC*100)}%: {len(df):,} obs.")

HAS_OCC = all(c in df.columns for c in ["horas_c","emprego_formal","ocp_dirigente"]) \
          and df["horas_c"].notna().any()

# ── Fórmulas ──────────────────────────────────────────────────────────────────
_IND = ("negro + educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
        " + idade_c + idade_sq + sexo_fem")
_UPA = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
_OCC = ("horas_c + emprego_formal + conta_propria + trab_domestico"
        " + ocp_dirigente + ocp_profissional + ocp_tecnico + ocp_administrativo"
        " + ocp_servicos + ocp_agro + ocp_operario + ocp_operador + ocp_ffaa")

MODELS = {
    "M3_sem_ocp": f"log_renda ~ {_IND} + {_UPA} + C(UF_str)",
}
if HAS_OCC:
    MODELS["M4_com_ocp"] = f"log_renda ~ {_IND} + {_UPA} + {_OCC} + C(UF_str)"

MODEL_LABELS = {
    "M3_sem_ocp": "M3 — sem variáveis ocupacionais",
    "M4_com_ocp": "M4 — com CBO + formalidade + horas",
}
MODEL_COLORS = {
    "M3_sem_ocp": "#1565C0",
    "M4_com_ocp": "#B71C1C",
}

# ── Regressão quantílica ──────────────────────────────────────────────────────
results_q = {m: {} for m in MODELS}

for m_name, formula in MODELS.items():
    print(f"\nModelo: {m_name}")
    for q in QUANTIS:
        print(f"  q={q:.2f} ...", end="", flush=True)
        try:
            qm = smf.quantreg(formula, data=df).fit(q=q, max_iter=2000, p_tol=1e-6)
            b  = qm.params.get("negro", np.nan)
            lo = qm.conf_int().loc["negro", 0] if "negro" in qm.conf_int().index else np.nan
            hi = qm.conf_int().loc["negro", 1] if "negro" in qm.conf_int().index else np.nan
            results_q[m_name][q] = {"b": b, "lo": lo, "hi": hi, "p": qm.pvalues.get("negro", np.nan)}
            pct = (np.exp(b) - 1) * 100
            print(f" β={b:.4f} ({pct:+.1f}%)  CI=[{lo:.4f}, {hi:.4f}]")
        except Exception as e:
            print(f" ERRO: {e}")
            results_q[m_name][q] = {"b": np.nan, "lo": np.nan, "hi": np.nan, "p": np.nan}

# ── OLS de referência (para cada modelo) ─────────────────────────────────────
ols_refs = {}
for m_name, formula in MODELS.items():
    try:
        ols_f = formula.replace("log_renda ~", "log_renda ~")
        ols_m = smf.ols(ols_f, data=df).fit(
            cov_type="cluster", cov_kwds={"groups": df["UF_str"]})
        ols_refs[m_name] = {
            "b":  ols_m.params.get("negro", np.nan),
            "lo": ols_m.conf_int().loc["negro", 0] if "negro" in ols_m.conf_int().index else np.nan,
            "hi": ols_m.conf_int().loc["negro", 1] if "negro" in ols_m.conf_int().index else np.nan,
        }
    except:
        ols_refs[m_name] = {"b": np.nan, "lo": np.nan, "hi": np.nan}

# ── Salvar tabela ─────────────────────────────────────────────────────────────
rows = []
for m_name in MODELS:
    for q in QUANTIS:
        res = results_q[m_name][q]
        rows.append({
            "Modelo":  m_name,
            "Quantil": q,
            "b_negro": round(res["b"], 5),
            "CI95_lo": round(res["lo"], 5),
            "CI95_hi": round(res["hi"], 5),
            "Gap_pct": round((np.exp(res["b"]) - 1) * 100, 2),
            "p_valor": round(res["p"], 5),
        })
pd.DataFrame(rows).to_csv(TABLES / "quantreg_negro.csv", index=False, encoding="utf-8")
print("\nquantreg_negro.csv salvo.")

# ── Figura 1: Trajetória do coeficiente negro por quantil (ambos modelos) ─────
fig, ax = plt.subplots(figsize=(11, 6))

for m_name in MODELS:
    color  = MODEL_COLORS[m_name]
    label  = MODEL_LABELS[m_name]
    bs  = [results_q[m_name][q]["b"]  for q in QUANTIS]
    los = [results_q[m_name][q]["lo"] for q in QUANTIS]
    his = [results_q[m_name][q]["hi"] for q in QUANTIS]
    pcts = [(np.exp(b)-1)*100 for b in bs]

    x = np.array(QUANTIS)
    ax.plot(x, pcts, "o-", color=color, lw=2.5, ms=7, label=label, zorder=5)
    ax.fill_between(x,
                    [(np.exp(lo)-1)*100 for lo in los],
                    [(np.exp(hi)-1)*100 for hi in his],
                    color=color, alpha=0.12, zorder=3)
    # OLS reference line
    ols_b = ols_refs[m_name]["b"]
    if not np.isnan(ols_b):
        ols_pct = (np.exp(ols_b) - 1) * 100
        ax.axhline(ols_pct, color=color, lw=1.2, ls="--", alpha=0.6,
                   label=f"OLS {m_name.split('_')[0]} = {ols_pct:.1f}%")

ax.axhline(0, color="black", lw=0.8, ls="-")
ax.set_xticks(QUANTIS)
ax.set_xticklabels([f"q{int(q*100)}" for q in QUANTIS], fontsize=11)
ax.set_xlabel("Quantil da distribuição de log-rendimento", fontsize=12)
ax.set_ylabel("Gap racial (% de desvantagem dos negros)", fontsize=12)
ax.set_title("Regressão Quantílica — Gap Salarial Racial por Posição na Distribuição\n"
             "PNAD Contínua 2016–2025 | Amostra 20% | β̂_negro transformado em %",
             fontsize=12, fontweight="bold")
ax.legend(fontsize=9, loc="lower left")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Anotação: glass ceiling
q_vals_m3 = [(np.exp(results_q["M3_sem_ocp"][q]["b"])-1)*100 for q in QUANTIS]
if not any(np.isnan(q_vals_m3)):
    q10_val = q_vals_m3[0]
    q95_val = q_vals_m3[-1]
    if q95_val < q10_val:
        ax.annotate("Glass ceiling:\ngap aumenta no topo",
                    xy=(0.90, q95_val), xytext=(0.80, q95_val - 4),
                    fontsize=9, color="#B71C1C", fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color="#B71C1C", lw=1.5))

plt.tight_layout()
plt.savefig(FIGURES / "quantreg_trajetoria.png", dpi=150, bbox_inches="tight")
plt.close()
print("quantreg_trajetoria.png salvo.")

# ── Figura 2: Gap em p.p. por quantil — M3 vs M4 (mediação ocupacional) ──────
if "M4_com_ocp" in MODELS:
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.array(QUANTIS)

    bs_m3 = np.array([(np.exp(results_q["M3_sem_ocp"][q]["b"])-1)*100 for q in QUANTIS])
    bs_m4 = np.array([(np.exp(results_q["M4_com_ocp"][q]["b"])-1)*100 for q in QUANTIS])
    mediacao = bs_m3 - bs_m4  # quanto M4 explica a mais em cada quantil

    w = 0.015
    ax.bar(x - w, bs_m3, 0.028, color="#1565C0", alpha=0.80, label="M3 — sem ocp")
    ax.bar(x + w, bs_m4, 0.028, color="#B71C1C", alpha=0.80, label="M4 — com ocp")
    ax.plot(x, mediacao, "D--", color="#FF8F00", lw=2, ms=7, label="Mediação ocupacional (M3−M4)")

    for xi, med in zip(x, mediacao):
        if not np.isnan(med):
            ax.text(xi, med + 0.3, f"{med:.1f}pp", ha="center",
                    fontsize=8, color="#E65100", fontweight="bold")

    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"q{int(q*100)}" for q in QUANTIS], fontsize=11)
    ax.set_xlabel("Quantil", fontsize=12)
    ax.set_ylabel("Gap racial (%)", fontsize=12)
    ax.set_title("Mediação Ocupacional do Gap Racial por Quantil\n"
                 "(diferença M3→M4 = porção explicada por CBO + formalidade + horas)",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(FIGURES / "quantreg_mediacao_ocp.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("quantreg_mediacao_ocp.png salvo.")

# ── Figura 3: Gap por quantil por área (capital vs interior) ─────────────────
# Roda M3 separado por área para mostrar heterogeneidade geográfica do glass ceiling
AREAS_COL = None
for col_cand in ["tipo_area", "tipo_area_str", "V1022", "area_str"]:
    if col_cand in df.columns:
        AREAS_COL = col_cand
        break

if AREAS_COL is None:
    # Tentar carregar do parquet completo
    try:
        area_series = pd.read_parquet(
            ROOT / "data/processed/features.parquet", columns=["tipo_area"]
        )["tipo_area"].iloc[idx]
        df["tipo_area"] = area_series.values
        AREAS_COL = "tipo_area"
    except:
        pass

if AREAS_COL:
    area_vals = df[AREAS_COL].unique()
    area_map  = {v: str(v) for v in area_vals}
    df["area_label"] = df[AREAS_COL].map(area_map)
    areas_unique = sorted(df["area_label"].dropna().unique())

    fig, ax = plt.subplots(figsize=(11, 6))
    area_colors = {"Capital": "#B71C1C", "RM (exceto capital)": "#FF8F00", "Interior": "#1565C0"}
    area_ls = {"Capital": "-", "RM (exceto capital)": "--", "Interior": "-."}

    for area in areas_unique:
        sub_a = df[df["area_label"] == area]
        if len(sub_a) < 5000:
            continue
        color = area_colors.get(area, "#555")
        ls    = area_ls.get(area, "-")
        bs_a  = []
        for q in QUANTIS:
            try:
                qm_a = smf.quantreg(MODELS["M3_sem_ocp"], data=sub_a).fit(
                    q=q, max_iter=1500, p_tol=1e-5)
                b = qm_a.params.get("negro", np.nan)
                bs_a.append((np.exp(b) - 1) * 100)
            except:
                bs_a.append(np.nan)
        ax.plot(QUANTIS, bs_a, "o" + ls, color=color, lw=2, ms=6, label=area)

    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(QUANTIS)
    ax.set_xticklabels([f"q{int(q*100)}" for q in QUANTIS], fontsize=11)
    ax.set_xlabel("Quantil", fontsize=12)
    ax.set_ylabel("Gap racial (%)", fontsize=12)
    ax.set_title("Glass Ceiling Racial por Tipo de Área\n"
                 "Regressão Quantílica M3 — PNAD 2016–2025",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(FIGURES / "quantreg_por_area.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("quantreg_por_area.png salvo.")

# ── Sumário ───────────────────────────────────────────────────────────────────
print("\n" + "="*68)
print("  SUMÁRIO — REGRESSÃO QUANTÍLICA")
print("="*68)
for m_name in MODELS:
    print(f"\n  {MODEL_LABELS[m_name]}:")
    print(f"  {'Quantil':>8}  {'β negro':>8}  {'Gap%':>8}  {'CI95':>20}")
    for q in QUANTIS:
        res = results_q[m_name][q]
        if not np.isnan(res["b"]):
            pct = (np.exp(res["b"]) - 1) * 100
            ci  = f"[{(np.exp(res['lo'])-1)*100:.1f}%, {(np.exp(res['hi'])-1)*100:.1f}%]"
            p   = "***" if res["p"] < 0.001 else ("**" if res["p"] < 0.01 else "*")
            print(f"  {'q'+str(int(q*100)):>8}  {res['b']:>8.4f}  {pct:>7.1f}%{p}  {ci:>20}")

# Glass ceiling test: is β at q95 more negative than at q10?
print("\n  GLASS CEILING TEST (M3 — sem ocp):")
b10 = results_q["M3_sem_ocp"][0.10]["b"]
b95 = results_q["M3_sem_ocp"][0.95]["b"]
if not (np.isnan(b10) or np.isnan(b95)):
    diff = b95 - b10
    direction = "GLASS CEILING CONFIRMADO" if diff < -0.01 else \
                ("EFEITO PISO (gap maior embaixo)" if diff > 0.01 else "GAP UNIFORME")
    print(f"  β(q10)={b10:.4f} → β(q95)={b95:.4f} | Δ={diff:.4f} → {direction}")
print("="*68)
print("=== REGRESSÃO QUANTÍLICA CONCLUÍDA ===")
