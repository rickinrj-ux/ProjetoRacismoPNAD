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

# --- bootstrap raiz do projeto (reorg estrutura) ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

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

ROOT    = Path(__file__).resolve().parents[2]
FIGURES = ROOT / "outputs" / "figures"
TABLES  = ROOT / "outputs" / "tables"
FIGURES.mkdir(parents=True, exist_ok=True)

SEED = 42

# ── Colunas necessárias ──────────────────────────────────────────────────────
COLS = [
    "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao", "educ_cat",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z", "media_renda_upa_z",
    "emprego_formal", "setor_publico", "conta_propria", "trab_domestico",
    "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
    "ocp_grupo_cbo",
    "log_renda", "renda_bruta", "pea",
    "UF", "UPA", "V1028",
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

# Dummies de educação + indicador de escolaridade não registrada.
# educ_cat está ausente em ~69% da PEA; preencher os dummies com 0 sem sinalizar a
# ausência contamina a categoria-base (mistura "sem instrução" com "dado faltante")
# e inverte os sinais. O termo educ_missing isola esse grupo e restaura os sinais.
df["educ_medio_completo"]    = df["educ_medio_completo"].fillna(0).astype(int)
df["educ_superior_completo"] = df["educ_superior_completo"].fillna(0).astype(int)
df["educ_pos_graduacao"]     = df["educ_pos_graduacao"].fillna(0).astype(int)
df["educ_missing"]           = df["educ_cat"].isna().astype(int)
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
          " + educ_missing + sexo_fem + idade_c + idade_sq"
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
    exog  = m.model.exog  # somente leitura abaixo — copy() desnecessário (economiza ~2,3GB/chamada)
    idx_v = list(m.model.exog_names).index(var)
    lp0   = exog @ m.params.values - exog[:, idx_v] * b_neg
    p1    = 1 / (1 + np.exp(-(lp0 + b_neg)))
    p0    = 1 / (1 + np.exp(-(lp0)))
    return float((p1 - p0).mean())


def stars(p):
    return "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))


# ── Ajustar modelos ───────────────────────────────────────────────────────────
# M3 (interação negro×educação) não é usado na Tabela 1 do Resultados Preliminares
# (que usa M2) nem em params.py. É também o modelo mais caro (interações + 26
# dummies de UF em 7,7M obs.) e, no desfecho mais raro (y_top10), sofre
# quase-separação (poucas observações de negros com pós-graduação no decil
# superior por UF), com tempo de convergência do MLE via BFGS imprevisível
# (minutos a mais de uma hora). Como M3 não é consumido por nenhuma
# tabela/figura do núcleo atual, pulamos M3 nos 3 desfechos (linha "OR_negro":
# NaN abaixo); M1/M2 não são afetados.

import gc
import statsmodels.api as sm

# Memória: ocp_qualif/y_top20/y_top10 são construídas sem NaN a partir de colunas
# já completas (df[y_col].notna() é sempre 100%) — usar df diretamente evita
# triplicar a base em memória com um .copy() por desfecho (7,7M linhas × ~20
# colunas cada). Também só retemos o modelo M2 (único reusado depois, na seção
# de robustez ponderada); M1 é descartado logo após extrair OR/CI/AME, e um
# gc.collect() explícito libera a memória do ajuste anterior antes do próximo
# — nesta máquina (16GB RAM) os ajustes com 26 dummies de UF em 7,7M linhas já
# entram em swap sem esse cuidado, o que torna o tempo de execução imprevisível.
most_common_uf = df["UF_str"].mode().iloc[0]
mean_vals = {c: float(df[c].mean()) for c in
             ["idade_c", "idade_sq", "media_renda_upa_z", "media_educ_upa_z",
              "tx_desemprego_upa_z", "pct_negro_upa_z"]}
emp_mean = float(df["emprego_formal"].mean())
pub_mean = float(df["setor_publico"].mean())
cp_mean  = float(df["conta_propria"].mean())
td_mean  = float(df["trab_domestico"].mean())
EDUC_CATS = [
    ("Sem superior", dict(educ_medio_completo=1, educ_superior_completo=0, educ_pos_graduacao=0)),
    ("Superior",     dict(educ_medio_completo=0, educ_superior_completo=1, educ_pos_graduacao=0)),
    ("Pós-grad",     dict(educ_medio_completo=0, educ_superior_completo=0, educ_pos_graduacao=1)),
]
has_v1028 = "V1028" in df.columns and df["V1028"].notna().any()

rows = []
rows_pond = []
pred_probs = {}   # y_col -> (probs_b, probs_n), usado na figura de predição

for y_col, y_label in OUTCOMES:
    print(f"\n--- Desfecho: {y_col.upper()} (n={len(df):,}) ---")

    # M1 — extrai os números para a tabela CSV e descarta o modelo imediatamente.
    formula_m1 = FORMULAS["M1"].format(y=y_col)
    print("  Ajustando M1 ...", end="", flush=True)
    m1 = fit_logit(formula_m1, df)
    or_, lo, hi = get_or_ci(m1)
    ame = get_ame(m1, df) * 100 if m1 is not None else np.nan
    p   = m1.pvalues.get("negro", np.nan) if m1 is not None else np.nan
    rows.append({
        "desfecho": y_col, "modelo": "M1",
        "OR_negro": round(or_, 4), "CI95_lo": round(lo, 4), "CI95_hi": round(hi, 4),
        "AME_pp": round(ame, 3) if not np.isnan(ame) else np.nan,
        "p_valor": round(p, 4) if not np.isnan(p) else np.nan,
        "OR_inter_negxedu": np.nan,
    })
    print(f" OR={or_:.3f} [{lo:.3f}–{hi:.3f}]{stars(p)} | AME={ame:+.2f}pp" if m1 is not None else " FALHOU")
    del m1
    gc.collect()

    # M2 — usado também na robustez ponderada e na figura de predição, mantido
    # vivo só até o fim deste bloco (nunca simultâneo ao M2 de outro desfecho).
    formula_m2 = FORMULAS["M2"].format(y=y_col)
    print("  Ajustando M2 ...", end="", flush=True)
    m2 = fit_logit(formula_m2, df)
    or_, lo, hi = get_or_ci(m2)
    ame = get_ame(m2, df) * 100 if m2 is not None else np.nan
    p   = m2.pvalues.get("negro", np.nan) if m2 is not None else np.nan
    rows.append({
        "desfecho": y_col, "modelo": "M2",
        "OR_negro": round(or_, 4), "CI95_lo": round(lo, 4), "CI95_hi": round(hi, 4),
        "AME_pp": round(ame, 3) if not np.isnan(ame) else np.nan,
        "p_valor": round(p, 4) if not np.isnan(p) else np.nan,
        "OR_inter_negxedu": np.nan,
    })
    print(f" OR={or_:.3f} [{lo:.3f}–{hi:.3f}]{stars(p)} | AME={ame:+.2f}pp" if m2 is not None else " FALHOU")

    rows.append({
        "desfecho": y_col, "modelo": "M3",
        "OR_negro": np.nan, "CI95_lo": np.nan, "CI95_hi": np.nan,
        "AME_pp": np.nan, "p_valor": np.nan, "OR_inter_negxedu": np.nan,
    })
    print("  Pulando M3 (quase-separação em y_top10 — ver nota acima)")

    if m2 is not None:
        # ── Robustez: desenho amostral complexo (peso V1028 + cluster UPA) ──
        # O M2 usa SE robusto a heterocedasticidade (HC1), mas não pondera por
        # V1028 nem trata o agrupamento por UPA (conglomerado) explicitamente.
        # Reajusta com (a) cluster-robusto sem peso e (b) peso + cluster, para
        # isolar o quanto da precisão reportada depende do desenho amostral.
        if has_v1028:
            # Testado em população completa (2026-07-29): o ajuste cluster-robusto
            # (statsmodels cov_type="cluster", 41.517 clusters de UPA x ~40 parâmetros
            # de M2) NÃO esgota a RAM desta máquina quando é o único modelo vivo por
            # vez (pico ~9,4GB de 16GB, ~473s) — a limitação de RAM que motivava a
            # subamostra de 20% (ROBUSTEZ_SAMPLE_FRAC) documentada em versões
            # anteriores não se confirmou com esta implementação; roda-se portanto em
            # população completa (df diretamente, sem cópia/amostragem).
            print(f"  Robustez desenho amostral (peso V1028 + cluster UPA, "
                  f"população completa) — {y_col} ...",
                  end="", flush=True)
            try:
                df_rob = df

                se_by_label = {}

                b0, se0 = m2.params["negro"], m2.bse["negro"]
                se_by_label["HC1 (atual, sem peso/cluster)"] = (b0, se0)
                rows_pond.append({
                    "desfecho": y_col, "especificacao": "HC1 (atual, sem peso/cluster)",
                    "OR_negro": round(float(np.exp(b0)), 4), "SE_negro": round(float(se0), 4),
                    "CI95_lo": round(float(np.exp(b0 - 1.96 * se0)), 4),
                    "CI95_hi": round(float(np.exp(b0 + 1.96 * se0)), 4),
                })

                m_cluster = smf.logit(formula_m2, data=df_rob).fit(
                    method="bfgs", maxiter=400, disp=False,
                    cov_type="cluster", cov_kwds={"groups": df_rob["UPA"]},
                )
                b1, se1 = m_cluster.params["negro"], m_cluster.bse["negro"]
                se_by_label["cluster UPA (sem peso)"] = (b1, se1)
                rows_pond.append({
                    "desfecho": y_col, "especificacao": "cluster UPA (sem peso)",
                    "OR_negro": round(float(np.exp(b1)), 4), "SE_negro": round(float(se1), 4),
                    "CI95_lo": round(float(np.exp(b1 - 1.96 * se1)), 4),
                    "CI95_hi": round(float(np.exp(b1 + 1.96 * se1)), 4),
                })
                del m_cluster
                gc.collect()

                peso_norm = df_rob["V1028"] / df_rob["V1028"].mean()
                m_pond = smf.glm(
                    formula_m2, data=df_rob, family=sm.families.Binomial(),
                    freq_weights=peso_norm,
                ).fit(cov_type="cluster", cov_kwds={"groups": df_rob["UPA"]})
                b2, se2 = m_pond.params["negro"], m_pond.bse["negro"]
                se_by_label["cluster UPA + peso V1028"] = (b2, se2)
                rows_pond.append({
                    "desfecho": y_col, "especificacao": "cluster UPA + peso V1028",
                    "OR_negro": round(float(np.exp(b2)), 4), "SE_negro": round(float(se2), 4),
                    "CI95_lo": round(float(np.exp(b2 - 1.96 * se2)), 4),
                    "CI95_hi": round(float(np.exp(b2 + 1.96 * se2)), 4),
                })
                del m_pond, df_rob
                gc.collect()

                print(
                    f" HC1 SE={se0:.4f} | cluster SE={se1:.4f} | "
                    f"cluster+peso SE={se2:.4f} (OR={np.exp(b2):.3f})"
                )
            except Exception as exc:
                print(f" FALHOU robustez de desenho amostral — {exc}")
            gc.collect()

        # ── Figura: probabilidade predita por raça × escolaridade (usa M2) ──
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
                pb = float(m2.predict(pd.DataFrame([{**base, "negro": 0}])).iloc[0]) * 100
                pn = float(m2.predict(pd.DataFrame([{**base, "negro": 1}])).iloc[0]) * 100
            except Exception:
                pb, pn = np.nan, np.nan
            probs_b.append(pb)
            probs_n.append(pn)
        pred_probs[y_col] = (probs_b, probs_n)

    del m2
    gc.collect()

tbl = pd.DataFrame(rows)
tbl.to_csv(TABLES / "glmm_glassceil_full.csv", index=False, encoding="utf-8")
print("\nglmm_glassceil_full.csv salvo.")

if rows_pond:
    df_pond = pd.DataFrame(rows_pond)
    df_pond.to_csv(TABLES / "glmm_glassceil_ponderado.csv", index=False, encoding="utf-8")
    print("glmm_glassceil_ponderado.csv salvo.")
elif has_v1028:
    print("Robustez de desenho amostral: nenhuma linha gerada (ver erros acima).")
else:
    print("V1028 ausente — pulando robustez de desenho amostral.")

# ── Figura: Forest plot OR por desfecho e modelo ─────────────────────────────
COLORS_M = {"M1": "#1565C0", "M2": "#B71C1C", "M3": "#2E7D32"}
n_out = len(OUTCOMES)

fig, axes = plt.subplots(1, n_out, figsize=(5 * n_out, 7), sharey=False)
if n_out == 1:
    axes = [axes]

for ax, (y_col, y_label) in zip(axes, OUTCOMES):
    x_m = np.arange(len(FORMULAS))
    for j, m_name in enumerate(FORMULAS):
        # Lê de `tbl` (já construída acima) em vez de `results`: M1 é
        # descartado da memória logo após o ajuste (ver nota de memória),
        # mas seus números já foram extraídos para a tabela CSV.
        row_m = tbl[(tbl["desfecho"] == y_col) & (tbl["modelo"] == m_name)]
        or_, lo, hi, p = np.nan, np.nan, np.nan, np.nan
        if len(row_m):
            or_ = row_m["OR_negro"].values[0]
            lo  = row_m["CI95_lo"].values[0]
            hi  = row_m["CI95_hi"].values[0]
            p   = row_m["p_valor"].values[0]
        color = COLORS_M[m_name]
        ax.scatter(j, or_, s=120, color=color, zorder=5)
        ax.plot([j, j], [lo, hi], color=color, linewidth=2.5, zorder=4)
        label = f"{or_:.3f}{stars(p)}" if not np.isnan(or_) else "—"
        ax.text(j, (hi if not np.isnan(hi) else 1.0) + 0.01, label, ha="center", va="bottom",
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
# Usa pred_probs, já coletado no loop principal (o modelo M2 de cada desfecho
# foi descartado da memória logo em seguida — ver nota de memória acima).
fig, axes = plt.subplots(1, n_out, figsize=(5 * n_out, 6), sharey=False)
if n_out == 1:
    axes = [axes]

x_pos = np.arange(len(EDUC_CATS))
width = 0.35

for ax, (y_col, y_label) in zip(axes, OUTCOMES):
    if y_col not in pred_probs:
        continue
    probs_b, probs_n = pred_probs[y_col]

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
             "Logit M2 (+ contexto UPA, população completa)",
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
        row_m = tbl[(tbl["desfecho"] == y_col) & (tbl["modelo"] == m_name)]
        if len(row_m) and not row_m["OR_negro"].isna().all():
            r = row_m.iloc[0]
            print(f"    {m_name}: OR={r['OR_negro']:.3f} [{r['CI95_lo']:.3f}–{r['CI95_hi']:.3f}]"
                  f"{stars(r['p_valor'])} | AME={r['AME_pp']:+.2f}pp")
print("\n" + "="*72)
print("=== GLMM GLASS CEILING CONCLUÍDO ===")
