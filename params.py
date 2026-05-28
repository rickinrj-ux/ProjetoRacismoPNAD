"""
params.py — Fonte única de verdade para todos os parâmetros do TCC.

Lê os CSVs de outputs e expõe constantes prontas para uso nos três geradores.
Cada gerador deve fazer: from params import P

Hierarquia de modelos:
  GLMM_LME4   — R lme4, random intercept UPA, PEA completa (AUTORITATIVO)
  GLASSCEIL   — Python logit + UF fixed effects (robustez)
  HLM         — Modelo de renda salarial (log-rendimento, N grupos)
  OB          — Decomposição Oaxaca-Blinder
  TOPSIS      — Pesquisa Operacional, ranking multicritério
"""

from pathlib import Path
import pandas as pd

_ROOT = Path(__file__).parent
_TAB  = _ROOT / "outputs" / "tables"


def _load() -> dict:
    p = {}

    # ── GLMM lme4 R (autoritativo) ───────────────────────────────────────────
    _g = pd.read_csv(_TAB / "glmm_resumo_full.csv")
    _m1 = _g.loc[_g["modelo"].str.contains("M1")].iloc[0]
    _m2 = _g.loc[_g["modelo"].str.contains("M2")].iloc[0]

    p["OR_M1"]       = round(float(_m1["OR_negro"]),  4)   # 0.6740
    p["OR_M2"]       = round(float(_m2["OR_negro"]),  4)   # 0.6905
    p["AME_M1_pp"]   = round(float(_m1["AME_negro"]) * 100, 2)  # -5.16
    p["AME_M2_pp"]   = round(float(_m2["AME_negro"]) * 100, 2)  # -4.84
    p["ICC_M1_pct"]  = round(float(_m1["ICC_UPA"])   * 100, 1)  # 22.2
    p["ICC_M2_pct"]  = round(float(_m2["ICC_UPA"])   * 100, 1)  # 10.8
    p["N_GLMM"]      = int(_m1["N"])                             # 7694198

    # Percentual de menor odds (1 - OR), arredondado para narrativa
    p["OR_M1_menor_pct"] = round((1 - p["OR_M1"]) * 100, 1)   # 32.6
    p["OR_M2_menor_pct"] = round((1 - p["OR_M2"]) * 100, 1)   # 30.9

    # ── E-values lme4 (calculados via VanderWeele & Ding 2017) ───────────────
    # Fórmula: E = OR + sqrt(OR*(OR-1)) para OR<1 usa o inverso
    import math
    def _evalue(or_val):
        inv = 1 / or_val
        return round(inv + math.sqrt(inv * (inv - 1)), 3)

    p["EVAL_M1"]     = _evalue(p["OR_M1"])   # 2.331
    p["EVAL_M2"]     = _evalue(p["OR_M2"])   # 2.254

    # ── Glass ceiling Python (UF fixed effects, robustez) ────────────────────
    _gc = pd.read_csv(_TAB / "glmm_glassceil_full.csv")

    def _gc_val(desfecho, modelo, col):
        row = _gc.loc[(_gc["desfecho"] == desfecho) & (_gc["modelo"] == modelo)]
        return float(row[col].values[0]) if len(row) else None

    p["OR_OCP_M1"]   = round(_gc_val("ocp_qualif", "M1", "OR_negro"),  4)  # 0.5508
    p["OR_OCP_M2"]   = round(_gc_val("ocp_qualif", "M2", "OR_negro"),  4)  # 0.7023
    p["OR_TOP20_M1"] = round(_gc_val("y_top20",    "M1", "OR_negro"),  4)  # 0.5360
    p["OR_TOP20_M2"] = round(_gc_val("y_top20",    "M2", "OR_negro"),  4)  # 0.6891
    p["OR_TOP10_M1"] = round(_gc_val("y_top10",    "M1", "OR_negro"),  4)  # 0.4533
    p["OR_TOP10_M2"] = round(_gc_val("y_top10",    "M2", "OR_negro"),  4)  # 0.6539
    p["AME_OCP_M1"]  = round(_gc_val("ocp_qualif", "M1", "AME_pp"),   2)   # -8.77
    p["AME_TOP20_M1"]= round(_gc_val("y_top20",    "M1", "AME_pp"),   2)   # -8.95
    p["AME_TOP10_M1"]= round(_gc_val("y_top10",    "M1", "AME_pp"),   2)   # -6.43

    # ── E-values glassceil (Python) ───────────────────────────────────────────
    _ev = pd.read_csv(_TAB / "evalues_glmm.csv")

    def _ev_val(desfecho, modelo):
        row = _ev.loc[(_ev["Desfecho"] == desfecho) & (_ev["Modelo"] == modelo)]
        return round(float(row["E-value (OR)"].values[0]), 3) if len(row) else None

    p["EVAL_OCP_M1"]   = _ev_val("ocp_qualif", "M1")   # 3.032
    p["EVAL_OCP_M2"]   = _ev_val("ocp_qualif", "M2")   # 2.201
    p["EVAL_TOP20_M1"] = _ev_val("y_top20",    "M1")   # 3.137
    p["EVAL_TOP10_M1"] = _ev_val("y_top10",    "M1")   # 3.837

    # ── Oaxaca-Blinder (OB global) ────────────────────────────────────────────
    _ob = pd.read_csv(_TAB / "ob_melhorias.csv")
    _ob_g = _ob.loc[_ob["grupo"] == "Global"].iloc[0]

    p["GAP_LOG"]     = round(float(_ob_g["gap_log"]),  4)   # 0.4255
    p["GAP_PCT"]     = round(float(_ob_g["gap_pct"]),  1)   # 53.0
    p["DOT_LOG"]     = round(float(_ob_g["dot_log"]),  4)   # 0.3552
    p["DOT_PCT"]     = round(float(_ob_g["dot_pct"]),  1)   # 83.5
    p["RET_LOG"]     = round(float(_ob_g["ret_log"]),  4)   # 0.0702
    p["RET_PCT"]     = round(float(_ob_g["ret_pct"]),  1)   # 16.5

    # ── HLM — componentes de variância e ICC (hlm_serie_s20pct.csv) ─────────
    _hlm = pd.read_csv(_TAB / "hlm_serie_s20pct.csv", index_col=0)
    def _hlm_val(row, col):
        v = _hlm.loc[row, col]
        return float(v) if v not in ("FE", "-", "") else None

    p["HLM_SIGMA2_M0"]    = round(_hlm_val("sigma2 (Nivel 1)", "M0_Nulo"), 4)    # 0.7653
    p["HLM_TAU2_M0"]      = round(_hlm_val("tau2_UF (Nivel 3)", "M0_Nulo"), 5)   # 0.08342
    p["HLM_TAU2_M1"]      = round(_hlm_val("tau2_UF (Nivel 3)", "M1_Individual"), 5)  # 0.03993
    p["HLM_TAU2_M2"]      = round(_hlm_val("tau2_UF (Nivel 3)", "M2_Localidade"), 5)  # 0.03002
    p["HLM_TAU2_M3"]      = round(_hlm_val("tau2_UF (Nivel 3)", "M3_Completo"), 5)    # 0.01520
    p["HLM_SIGMA2_M1"]    = round(_hlm_val("sigma2 (Nivel 1)", "M1_Individual"), 4)   # 0.5126
    p["HLM_SIGMA2_M2"]    = round(_hlm_val("sigma2 (Nivel 1)", "M2_Localidade"), 4)   # 0.4864
    p["HLM_SIGMA2_M3"]    = round(_hlm_val("sigma2 (Nivel 1)", "M3_Completo"), 4)     # 0.4864
    p["ICC_HLM_M0_pct"]   = round(_hlm_val("ICC_UF", "M0_Nulo") * 100, 2)        # 9.83
    p["ICC_HLM_M1_pct"]   = round(_hlm_val("ICC_UF", "M1_Individual") * 100, 2)  # 7.23
    p["ICC_HLM_M2_pct"]   = round(_hlm_val("ICC_UF", "M2_Localidade") * 100, 2)  # 5.81
    p["ICC_HLM_M3_pct"]   = round(_hlm_val("ICC_UF", "M3_Completo") * 100, 2)    # 3.03

    # ── KMeans k=3 — perfis e gap racial (kmeans_perfis_k3.csv, kmeans_gap_racial_k3.csv) ──
    _km = pd.read_csv(_TAB / "kmeans_perfis_k3.csv")
    for i in range(3):
        row = _km.loc[_km["cluster"] == i].iloc[0]
        p[f"KM_C{i}_N"]        = int(row["N"])
        p[f"KM_C{i}_PCT_TOTAL"] = round(float(row["% total"]), 1)
        p[f"KM_C{i}_PCT_NEGRO"] = round(float(row["% Negro"]), 1)
        p[f"KM_C{i}_PCT_MULHER"]= round(float(row["% Mulher"]), 1)
        p[f"KM_C{i}_LOG_RENDA"] = round(float(row["log_Renda"]), 3)
        p[f"KM_C{i}_RENDA_BRL"] = round(float(row["Renda Bruta (R$)"]))
        p[f"KM_C{i}_PCT_SUP"]   = round(float(row["% Superior Compl."]) * 100, 1)
    p["KM_N_TOTAL"] = sum(p[f"KM_C{i}_N"] for i in range(3))

    _kmg = pd.read_csv(_TAB / "kmeans_gap_racial_k3.csv")
    for i in range(3):
        row = _kmg.loc[_kmg["cluster"] == i].iloc[0]
        p[f"KM_C{i}_GAP_LOG"]   = round(float(row["gap_log"]), 4)
        p[f"KM_C{i}_GAP_PCT"]   = round(float(row["gap_%"]),   2)

    _kmet = pd.read_csv(_TAB / "kmeans_metricas.csv")
    p["KM_SILH_K2"] = round(float(_kmet.loc[_kmet["k"]==2, "silhouette"].values[0]), 4)
    p["KM_SILH_K3"] = round(float(_kmet.loc[_kmet["k"]==3, "silhouette"].values[0]), 4)

    # ── SNA — homofilia racial (derivado de sna_arestas.csv) ─────────────────
    _ar = pd.read_csv(_TAB / "sna_arestas.csv")
    _intra = _ar.loc[~_ar["inter_racial"], "weight_jaccard"].sum()
    _inter = _ar.loc[ _ar["inter_racial"], "weight_jaccard"].sum()
    p["SNA_H"] = round(_intra / (_intra + _inter), 4)   # 0.4382

    # ── TOPSIS ────────────────────────────────────────────────────────────────
    _tp = pd.read_csv(_TAB / "po_politicas_topsis.csv")
    for _, row in _tp.iterrows():
        p[f"TOPSIS_P{int(row['Rank'])}_CC"] = round(float(row["CC"]), 4)

    # ── PL-1 B=5 ─────────────────────────────────────────────────────────────
    _pl1 = pd.read_csv(_TAB / "po_politicas_pl1.csv")
    p["PL1_B5_PCT"]  = float(_pl1.loc[_pl1["orcamento"] == 5.0, "reducao_pct"].values[0])

    return p


# Instância global — importar assim: from params import P
# Exemplo: f"OR = {P['OR_M1']:.3f}"
P: dict = _load()


# ── Helpers de formatação para uso nos geradores ─────────────────────────────

def fmt(val: float, dec: int = 3) -> str:
    """Número em locale pt-BR: ponto como separador de milhar não se aplica aqui,
    vírgula como separador decimal. Usa U+2212 (−) para negativos."""
    if val < 0:
        return f"−{abs(val):.{dec}f}".replace(".", ",")
    return f"{val:.{dec}f}".replace(".", ",")


def fmtN(n: int) -> str:
    """Inteiro grande com ponto como separador de milhar (pt-BR): 7694198 → '7.694.198'."""
    return f"{n:,}".replace(",", ".")


def ame(val: float, dec: int = 2) -> str:
    """AME em p.p.: −5,16 p.p."""
    return fmt(val, dec) + " p.p."


def or_str(val: float, dec: int = 3) -> str:
    """OR em pt-BR sem sinal: 0,674."""
    return fmt(val, dec)


if __name__ == "__main__":
    print("params.py — valores carregados dos CSVs\n")
    for k, v in sorted(P.items()):
        print(f"  {k:25s} = {v}")
