"""
run_regressao_quantilica.py
Regressão Quantílica do gap salarial racial — PNAD Contínua 2016–2025.

Estima o coeficiente de 'negro' em log_renda nos quantis q∈{0.10,0.25,0.50,0.75,0.90,0.95}
com e sem controles de composição ocupacional (M3 e M4), revelando a estrutura do glass ceiling.

Se β̂_negro(q) decresce com q → gap aumenta no topo = glass ceiling racial confirmado.
"""

# --- bootstrap raiz do projeto (reorg estrutura) ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import statsmodels.formula.api as smf
import statsmodels.api as sm
import patsy
import gc
import warnings
warnings.filterwarnings('ignore')
from pathlib import Path

ROOT    = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
FIGURES = ROOT / "outputs" / "figures"
TABLES  = ROOT / "outputs" / "tables"
FIGURES.mkdir(parents=True, exist_ok=True)

SAMPLE_FRAC = None   # None = população completa
SEED        = 42
QUANTIS     = [0.10, 0.25, 0.50, 0.75, 0.90, 0.95]

# --so-area roda apenas a quebra por tipo de área, que ajusta o M3 dentro de
# cada fatia. Sem o flag, o script faz o percurso completo, como antes.
SO_AREA     = "--so-area" in sys.argv

COLS = [
    "Ano", "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao", "educ_cat",
    "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
    "horas_c", "emprego_formal", "conta_propria", "trab_domestico",
    "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
    "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa",
    "log_renda", "renda_bruta", "pea", "UF", "V1023",
]

print("Carregando dados ...")
df = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=COLS)
df["UF_str"] = df["UF"].astype(str)
df["educ_missing"] = df["educ_cat"].isna().astype(int)

mask = (df["pea"] == 1) & (df["renda_bruta"] > 0) & (df["negro"].notna())
df   = df[mask].copy()

BASE_DROP = ["negro","sexo_fem","idade_c","idade_sq",
             "educ_fund_completo", "educ_medio_completo","educ_superior_completo","educ_pos_graduacao",
             "pct_negro_upa_z","tx_desemprego_upa_z","media_educ_upa_z","log_renda"]
df = df.dropna(subset=BASE_DROP)

if SAMPLE_FRAC:
    rng = np.random.default_rng(SEED)
    idx = rng.choice(len(df), size=int(len(df) * SAMPLE_FRAC), replace=False)
    df  = df.iloc[idx].reset_index(drop=True)
else:
    df = df.reset_index(drop=True)
print(f"  {'Amostra '+str(int(SAMPLE_FRAC*100))+'%' if SAMPLE_FRAC else 'População completa'}: {len(df):,} obs.")

HAS_OCC = all(c in df.columns for c in ["horas_c","emprego_formal","ocp_dirigente"]) \
          and df["horas_c"].notna().any()

# ── Fórmulas ──────────────────────────────────────────────────────────────────
_IND = ("negro + educ_fund_completo + educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
        " + idade_c + idade_sq + sexo_fem")
_UPA = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z + C(Ano)"
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

# ── Figura 3: gap por quantil e por tipo de área ──────────────────────────────
def figura_gap_por_area(df, formula, quantis):
    """Ajusta o M3 dentro de cada tipo de área e grava a figura e o csv.

    Está em função, e não no fluxo linear, para poder ser chamada sozinha com
    --so-area: os ajustes na população inteira (M3 e M4, 51 colunas sobre 7,7
    milhões de linhas) são pesados, e esta parte roda sobre fatias.
    """
    # Roda M3 separado por área para mostrar heterogeneidade geográfica do glass ceiling
    # V1023 vem do próprio parquet, na mesma leitura das demais colunas. A versão
    # anterior procurava uma coluna `tipo_area` que não existe no parquet e caía num
    # fallback que reindexava o arquivo completo com o índice da amostra — e como o
    # `except` era nu, o NameError de rodar em população completa (sem `idx`) sumia
    # sem deixar rastro. Resultado: a figura por área nunca era gerada.
    # Mapeamento igual ao de run_segregacao_espacial.py e run_composicao_ocupacional.py.
    AREA_MAP = {1: "Capital", 2: "RM (exceto capital)", 3: "Interior", 4: "Interior"}

    if "V1023" in df.columns:
        df["area_label"] = df["V1023"].map(AREA_MAP)
        areas_unique = sorted(df["area_label"].dropna().unique())
        n_sem_area = int(df["area_label"].isna().sum())
        if n_sem_area:
            print(f"  [área] {n_sem_area:,} obs. sem tipo de área — fora da figura")
    else:
        areas_unique = []
        print("  [AVISO] V1023 ausente do parquet — figura por área não será gerada")

    if areas_unique:

        fig, ax = plt.subplots(figsize=(11, 6))
        area_colors = {"Capital": "#B71C1C", "RM (exceto capital)": "#FF8F00", "Interior": "#1565C0"}
        area_ls = {"Capital": "-", "RM (exceto capital)": "--", "Interior": "-."}

        linhas_area = []   # a figura sai daqui e o csv também: mesma fonte
        for area in areas_unique:
            sub_a = df[df["area_label"] == area]
            if len(sub_a) < 5000:
                print(f"  [área] {area}: {len(sub_a):,} obs. — abaixo do mínimo, fora da figura")
                continue
            color = area_colors.get(area, "#555")
            ls    = area_ls.get(area, "-")
            bs_a  = []
            # mesma economia do laço principal: a matriz da fatia é montada uma
            # vez e reusada nos seis quantis, em vez de remontada a cada um
            y_a, X_a = patsy.dmatrices(formula, sub_a, return_type="matrix")
            j_a = X_a.design_info.column_names.index("negro")
            mod_a = sm.QuantReg(np.asarray(y_a).ravel(), np.asarray(X_a))
            del y_a, X_a
            for q in quantis:
                try:
                    qm_a = mod_a.fit(q=q, max_iter=1500, p_tol=1e-5)
                    b = qm_a.params[j_a]
                    del qm_a
                except Exception as e:  # noqa: BLE001 — falha de convergência não some calada
                    print(f"  [área] {area} q{int(q*100)}: não convergiu ({type(e).__name__})")
                    b = np.nan
                gap = (np.exp(b) - 1) * 100 if np.isfinite(b) else np.nan
                bs_a.append(gap)
                linhas_area.append({"area": area, "quantil": q, "n": len(sub_a),
                                    "b_negro": b, "gap_pct": gap})
            ax.plot(quantis, bs_a, "o" + ls, color=color, lw=2, ms=6, label=area)
            del mod_a, sub_a       # a fatia seguinte não paga pela anterior
            gc.collect()

        if linhas_area:
            pd.DataFrame(linhas_area).to_csv(TABLES / "qr_gap_por_area.csv", index=False)
            print("qr_gap_por_area.csv salvo.")

        ax.axhline(0, color="black", lw=0.8)
        ax.set_xticks(quantis)
        ax.set_xticklabels([f"q{int(q*100)}" for q in quantis], fontsize=11)
        ax.set_xlabel("Quantil", fontsize=12)
        ax.set_ylabel("Gap racial (%)", fontsize=12)
        # Título de ação (Knaflic): afirma o achado em vez de nomear o assunto.
        # Sai dos próprios resultados --- se o padrão mudar, o título muda junto,
        # em vez de continuar afirmando o que a figura já não mostra.
        ARTIGO = {"Capital": "na capital", "Interior": "no interior",
                  "RM (exceto capital)": "na região metropolitana"}
        piv = pd.DataFrame(linhas_area).pivot(index="area", columns="quantil",
                                              values="gap_pct")
        if {0.50, 0.95} <= set(piv.columns) and not piv[[0.50, 0.95]].isna().any().any():
            pior = (piv[0.95] / piv[0.50]).abs().idxmax()
            meio, topo = abs(piv.loc[pior, 0.50]), abs(piv.loc[pior, 0.95])
            br = lambda v: f"{v:.1f}".replace(".", ",")   # decimal em pt-BR
            titulo = (f"O teto de vidro racial aperta mais {ARTIGO.get(pior, pior)}" +
                      chr(10) +
                      f"Penalidade de {br(meio)}% na mediana e {br(topo)}% no topo "
                      f"(q95) — quantílica M3, PNAD 2016–2025")
        else:
            titulo = ("Gap racial por quantil e tipo de área" + chr(10) +
                      "Regressão quantílica M3 — PNAD 2016–2025")
        ax.set_title(titulo, fontsize=12, fontweight="bold")
        ax.legend(fontsize=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()
        plt.savefig(FIGURES / "quantreg_por_area.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("quantreg_por_area.png salvo.")

# --so-area: só a quebra por tipo de área, sem repetir os ajustes na população
# inteira. Serve quando o M3/M4 já rodaram, ou quando a memória não os comporta.
if SO_AREA:
    figura_gap_por_area(df, MODELS["M3_sem_ocp"], QUANTIS)
    print("\n=== QUEBRA POR ÁREA CONCLUÍDA (--so-area) ===")
    sys.exit(0)

# ── Regressão quantílica ──────────────────────────────────────────────────────
results_q = {m: {} for m in MODELS}

# A matriz de design é construída UMA vez por modelo e reusada nos seis quantis
# e no OLS de referência. Antes, `smf.quantreg(formula, data=df)` estava dentro
# do laço: o patsy remontava 51 colunas sobre 7,7 milhões de linhas --- 3,1 GB
# --- a cada quantil, e o pico derrubou duas execuções no q=0,95 do M4. O
# estimador é o mesmo: `smf.quantreg` é `patsy.dmatrices` seguido de
# `sm.QuantReg`, que é o que está escrito aqui. Os coeficientes saem por posição
# porque a matriz crua não carrega os nomes; daí o índice de "negro".
ols_refs = {}
for m_name, formula in MODELS.items():
    print(f"\nModelo: {m_name}")
    y_mat, X_mat = patsy.dmatrices(formula, df, return_type="matrix")
    nomes = X_mat.design_info.column_names
    j_neg = nomes.index("negro") if "negro" in nomes else None
    y_arr = np.asarray(y_mat).ravel()
    X_arr = np.asarray(X_mat)
    del y_mat, X_mat

    mod_q = sm.QuantReg(y_arr, X_arr)
    for q in QUANTIS:
        print(f"  q={q:.2f} ...", end="", flush=True)
        try:
            if j_neg is None:
                raise KeyError("coluna 'negro' ausente da matriz de design")
            qm = mod_q.fit(q=q, max_iter=2000, p_tol=1e-6)
            ci = np.asarray(qm.conf_int())
            b, lo, hi = qm.params[j_neg], ci[j_neg, 0], ci[j_neg, 1]
            results_q[m_name][q] = {"b": b, "lo": lo, "hi": hi, "p": qm.pvalues[j_neg]}
            pct = (np.exp(b) - 1) * 100
            print(f" β={b:.4f} ({pct:+.1f}%)  CI=[{lo:.4f}, {hi:.4f}]")
            del qm
        except Exception as e:
            print(f" ERRO: {e}")
            results_q[m_name][q] = {"b": np.nan, "lo": np.nan, "hi": np.nan, "p": np.nan}

    # OLS de referência sobre a MESMA matriz, com erro-padrão agrupado por UF
    try:
        ols_m = sm.OLS(y_arr, X_arr).fit(
            cov_type="cluster", cov_kwds={"groups": df["UF_str"].to_numpy()})
        ci_o = np.asarray(ols_m.conf_int())
        ols_refs[m_name] = {"b": ols_m.params[j_neg],
                            "lo": ci_o[j_neg, 0], "hi": ci_o[j_neg, 1]}
        del ols_m
    except Exception as e:  # noqa: BLE001 — o motivo da falha não some calado
        print(f"  [OLS ref] falhou: {type(e).__name__}: {e}")
        ols_refs[m_name] = {"b": np.nan, "lo": np.nan, "hi": np.nan}

    del mod_q, y_arr, X_arr
    gc.collect()

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

# ── Figura 3: gap por quantil e por tipo de área ──────────────────────────────
figura_gap_por_area(df, MODELS["M3_sem_ocp"], QUANTIS)

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
