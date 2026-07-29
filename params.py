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

    # ── Interseccionalidade raça×gênero (grupo_rg de 4 níveis; ref = homem branco) ──
    _grg_path = _TAB / "grupo_rg_4grupos_desfechos.csv"
    if _grg_path.exists():
        _grg = pd.read_csv(_grg_path).set_index("desfecho")
        def _grg_val(desfecho, col): return float(_grg.loc[desfecho, col])
        p["GRG_MB_OCP"]   = round(_grg_val("ocp_qualif", "OR_mulher_branca"), 3)  # 1.795
        p["GRG_HN_OCP"]   = round(_grg_val("ocp_qualif", "OR_homem_negro"),   3)  # 0.652
        p["GRG_MN_OCP"]   = round(_grg_val("ocp_qualif", "OR_mulher_negra"),  3)  # 1.335
        p["GRG_MB_TOP10"] = round(_grg_val("y_top10",    "OR_mulher_branca"), 3)  # 0.490
        p["GRG_HN_TOP10"] = round(_grg_val("y_top10",    "OR_homem_negro"),   3)  # 0.646
        p["GRG_MN_TOP10"] = round(_grg_val("y_top10",    "OR_mulher_negra"),  3)  # 0.338
        p["GRG_MN_TOP20"] = round(_grg_val("y_top20",    "OR_mulher_negra"),  3)  # 0.362
        p["GRG_INT_OCP"]  = round(_grg_val("ocp_qualif", "OR_interacao"),     3)  # 1.141
        p["GRG_INT_TOP10"]= round(_grg_val("y_top10",    "OR_interacao"),     3)  # 1.069

    # ── Gini intra-raça (renda do trabalho entre ocupados, ponderado V1028) ────
    _grpath = _TAB / "gini_raca.csv"
    if _grpath.exists():
        _gr = pd.read_csv(_grpath).set_index("grupo")
        p["GINI_TOTAL_TRAB"]   = round(float(_gr.loc["Total",   "gini"]), 3)   # 0.482
        p["GINI_BRANCO_TRAB"]  = round(float(_gr.loc["Brancos", "gini"]), 3)   # 0.485
        p["GINI_NEGRO_TRAB"]   = round(float(_gr.loc["Negros",  "gini"]), 3)   # 0.449
        p["GINI_THEIL_BETW_PCT"] = round(float(_gr.loc["Total", "theil_between_pct"]), 1)  # 6.3

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

    # ── HLM — componentes de variância e ICC (hlm_serie_completo.csv, pop. completa) ─────────
    _hlm = pd.read_csv(_TAB / "hlm_serie_completo.csv", index_col=0)
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

    # ── VIF — multicolinearidade M4 (vif_m4_preditores.csv) ──────────────────
    _vif_path = _TAB / "vif_m4_preditores.csv"
    if _vif_path.exists():
        _vif = pd.read_csv(_vif_path)
        p["VIF_MAX"]        = round(float(_vif["VIF"].max()), 2)
        p["VIF_MAX_VAR"]    = str(_vif.loc[_vif["VIF"].idxmax(), "label"])
        p["VIF_N_CRITICO"]  = int((_vif["VIF"] > 10).sum())
        p["VIF_N_ALTO"]     = int(((_vif["VIF"] > 5) & (_vif["VIF"] <= 10)).sum())
        p["VIF_N_MODERADO"] = int(((_vif["VIF"] > 2) & (_vif["VIF"] <= 5)).sum())
        p["VIF_N_BAIXO"]    = int((_vif["VIF"] <= 2).sum())
        p["VIF_N_TOTAL"]    = len(_vif)

    # ── SNA Expandida (20 nós: raça × educação × gênero) ─────────────────────
    _sna_exp_path = _TAB / "sna_metricas_nos_expandida.csv"
    _sna_rg_path  = _TAB / "sna_resumo_race_gender.csv"
    if _sna_exp_path.exists():
        _sna_exp = pd.read_csv(_sna_exp_path)
        p["SNA_EXP_N_NOS"]         = len(_sna_exp)
        _top_node = _sna_exp.loc[_sna_exp["betweenness"].idxmax()]
        p["SNA_EXP_BETWN_TOP"]     = round(float(_top_node["betweenness"]), 4)
        p["SNA_EXP_BETWN_TOP_NODE"]= str(_top_node["node"])
        p["SNA_EXP_CONSTR_MAX"]    = round(float(_sna_exp["constraint"].max()), 4)
        p["SNA_EXP_CONSTR_MIN"]    = round(float(_sna_exp["constraint"].min()), 4)
        # Gap de renda por raça nos nós da rede
        _br = _sna_exp[_sna_exp["race"] == "Branco"]["mean_renda"].mean()
        _ng = _sna_exp[_sna_exp["race"] == "Negro"]["mean_renda"].mean()
        p["SNA_EXP_GAP_RENDA_LOG"] = round(float(_ng - _br), 4)

    if _sna_rg_path.exists():
        _rg = pd.read_csv(_sna_rg_path)
        def _rg_v(rg, col):
            row = _rg.loc[_rg["race_gen"] == rg]
            return round(float(row[col].values[0]), 4) if len(row) else None
        p["SNA_EXP_BRANCO_FEM_BETWN"]  = _rg_v("Branco_Fem",  "betweenness_max")
        p["SNA_EXP_NEGRO_FEM_RENDA"]   = _rg_v("Negro_Fem",   "mean_renda")
        p["SNA_EXP_BRANCO_MASC_RENDA"] = _rg_v("Branco_Masc", "mean_renda")

    # ── Segregação Espacial CI Bootstrap (segreg_gap_por_area_ci.csv) ─────────
    _ci_path = _TAB / "segreg_gap_por_area_ci.csv"
    if _ci_path.exists():
        _ci = pd.read_csv(_ci_path)
        def _ci_v(area, col):
            row = _ci.loc[_ci["area_tipo"] == area]
            return round(float(row[col].values[0]), 4) if len(row) else None
        p["SEGR_CAP_GAP_PCT"]   = _ci_v("Capital",             "gap_pct")
        p["SEGR_CAP_CI_LO"]     = _ci_v("Capital",             "ci_lo_pct")
        p["SEGR_CAP_CI_HI"]     = _ci_v("Capital",             "ci_hi_pct")
        p["SEGR_RM_GAP_PCT"]    = _ci_v("RM (exceto\ncapital)","gap_pct")
        p["SEGR_RM_CI_LO"]      = _ci_v("RM (exceto\ncapital)","ci_lo_pct")
        p["SEGR_RM_CI_HI"]      = _ci_v("RM (exceto\ncapital)","ci_hi_pct")
        p["SEGR_INT_GAP_PCT"]   = _ci_v("Interior",            "gap_pct")
        p["SEGR_INT_CI_LO"]     = _ci_v("Interior",            "ci_lo_pct")
        p["SEGR_INT_CI_HI"]     = _ci_v("Interior",            "ci_hi_pct")
        _p_perm = _ci.loc[_ci["area_tipo"] == "Capital", "p_permut_cap_int"]
        p["SEGR_P_PERM"]        = round(float(_p_perm.values[0]), 4) if len(_p_perm) else None

    # ── Davies-Bouldin — adicionado ao bloco KMeans ───────────────────────────
    if "davies_bouldin" in _kmet.columns:
        p["KM_DB_K2"] = round(float(_kmet.loc[_kmet["k"]==2, "davies_bouldin"].values[0]), 4)
        p["KM_DB_K3"] = round(float(_kmet.loc[_kmet["k"]==3, "davies_bouldin"].values[0]), 4)
        p["KM_DB_K5"] = round(float(_kmet.loc[_kmet["k"]==5, "davies_bouldin"].values[0]), 4) if 5 in _kmet["k"].values else None

    # ── HLM M3 Random Slope para negro ───────────────────────────────────────
    _rs_path  = _ROOT / "outputs" / "tables" / "hlm_m3_random_slope_varcov.csv"
    _lrt_path = _ROOT / "outputs" / "tables" / "hlm_m3_random_slope_lrt.csv"
    if _rs_path.exists():
        _rs = pd.read_csv(_rs_path)
        _reml = _rs[_rs["modelo"] == "M3_rs_uncorr_REML"]
        _ml   = _rs[_rs["modelo"] == "M3_rs_uncorr_ML"]
        _row  = _reml.iloc[0] if len(_reml) else (_ml.iloc[0] if len(_ml) else None)
        if _row is not None:
            import math
            _tau2   = float(_row["tau2_negro_slope"])
            _sd     = math.sqrt(_tau2)
            _b      = float(_row["b_negro_fixo"])
            _gap_pct = (math.exp(_b) - 1) * 100
            _gap_lo  = (math.exp(_b - 1.96 * _sd) - 1) * 100
            _gap_hi  = (math.exp(_b + 1.96 * _sd) - 1) * 100
            p["RS_TAU2_NEGRO"]   = round(_tau2, 6)
            p["RS_SD_NEGRO"]     = round(_sd, 4)
            p["RS_RHO"]          = round(float(_row["rho_int_negro"]), 4)
            p["RS_ICC_NEGRO"]    = round(float(_row["icc_negro"]), 4)
            p["RS_SIGMA2"]       = round(float(_row["sigma2"]), 4)  # variância residual nível 1
            p["RS_B_NEGRO_FIXO"] = round(_b, 4)
            p["RS_GAP_PCT"]      = round(_gap_pct, 1)
            p["RS_GAP_LO_PCT"]   = round(_gap_lo, 1)
            p["RS_GAP_HI_PCT"]   = round(_gap_hi, 1)
            p["RS_N_OBS"]        = int(_row["n_obs"])
            p["RS_SAMPLE_FRAC"]  = float(_row["sample_frac"])
    if _lrt_path.exists():
        _lrt = pd.read_csv(_lrt_path)
        if len(_lrt):
            p["RS_LRT_LR"]   = round(float(_lrt["LR"].iloc[0]), 3)
            p["RS_LRT_P"]    = float(_lrt["p_boundary_mix"].iloc[0])
            p["RS_LRT_SIG"]  = str(_lrt["sig"].iloc[0])
            p["RS_LRT_SIGN"] = bool(_lrt["tau2_negro_significativo"].iloc[0])

    # ── PO Regionalizada (base oficial: BLUP MixedLM) ─────────────────────────
    _rpo_gaps = _TAB / "po_regional_gaps_uf.csv"
    _rpo_aloc = _TAB / "po_regional_alocacao.csv"
    _rpo_comp = _TAB / "blup_vs_eb_comparacao.csv"
    if _rpo_gaps.exists() and _rpo_aloc.exists():
        _rg = pd.read_csv(_rpo_gaps)   # ordenado por gap_blup (pior primeiro)
        _ra = pd.read_csv(_rpo_aloc)
        _pior, _melhor = _rg.iloc[0], _rg.iloc[-1]
        p["RPO_N_UFS"]         = len(_rg)
        p["RPO_WORST_UF"]      = str(_pior["sigla"])
        p["RPO_WORST_GAP_PCT"] = round(float(_pior["gap_blup_pct"]), 1)
        p["RPO_BEST_UF"]       = str(_melhor["sigla"])
        p["RPO_BEST_GAP_PCT"]  = round(float(_melhor["gap_blup_pct"]), 1)
        p["RPO_TOP5"]          = ", ".join(_rg.head(5)["sigla"].tolist())

        def _ganho(B):
            row = _ra.loc[_ra["orcamento_ufs"] == B, "ganho_focalizacao_pct"]
            return round(float(row.values[0]), 1) if len(row) else None
        p["RPO_GANHO_B3"] = _ganho(3)
        p["RPO_GANHO_B9"] = _ganho(9)

    if _rpo_comp.exists():
        _rc = pd.read_csv(_rpo_comp)
        p["RPO_PEARSON"]  = round(float(_rc["pearson_r"].iloc[0]), 3)
        p["RPO_SPEARMAN"] = round(float(_rc["spearman_rho"].iloc[0]), 3)
        p["RPO_OVERLAP5"] = int(_rc["overlap_top5_piores"].iloc[0])

    # ── Random slope GLMM real (lme4, acesso) — glmm_rs_varcomp.csv ───────────
    _grs_path = _TAB / "glmm_rs_varcomp.csv"
    if _grs_path.exists():
        _grs = pd.read_csv(_grs_path)
        def _grs_v(rot, col):
            row = _grs.loc[_grs["rotulo"] == rot]
            return float(row[col].values[0]) if len(row) else None
        for rot, key in [("ocp_qualif","OCP"), ("y_top20","TOP20"), ("y_top10","TOP10")]:
            if _grs_v(rot, "OR_negro") is None:
                continue
            p[f"GRS_{key}_OR"]   = round(_grs_v(rot, "OR_negro"), 4)
            p[f"GRS_{key}_TAU2"] = round(_grs_v(rot, "tau2_negro"), 5)
            p[f"GRS_{key}_SD"]   = round(_grs_v(rot, "sd_negro"), 4)
            p[f"GRS_{key}_RHO"]  = round(_grs_v(rot, "rho"), 3)
            p[f"GRS_{key}_LR"]   = round(_grs_v(rot, "LR"), 1)
        if _grs_v("ocp_qualif", "N") is not None:
            p["GRS_N"] = int(_grs_v("ocp_qualif", "N"))
        if _grs_v("ocp_qualif_PRIVADO", "OR_negro") is not None:
            p["GRS_PRIV_OR"]   = round(_grs_v("ocp_qualif_PRIVADO", "OR_negro"), 4)
            p["GRS_PRIV_TAU2"] = round(_grs_v("ocp_qualif_PRIVADO", "tau2_negro"), 5)
            p["GRS_PUB_OR"]    = round(_grs_v("ocp_qualif_PUBLICO", "OR_negro"), 4)
            p["GRS_PUB_TAU2"]  = round(_grs_v("ocp_qualif_PUBLICO", "tau2_negro"), 5)

    # ── HLM random slope estendido: setor (salário) + gênero ─────────────────
    _hrs_setor = _TAB / "hlm_rs_setor.csv"
    if _hrs_setor.exists():
        _hs = pd.read_csv(_hrs_setor)
        def _hs_v(setor, col):
            row = _hs.loc[_hs["setor"] == setor]
            return float(row[col].values[0]) if len(row) else None
        if _hs_v("Privado", "b_negro") is not None:
            p["HRS_PRIV_GAP_PCT"]  = round(_hs_v("Privado", "OR_equiv_pct"), 1)
            p["HRS_PRIV_TAU2"]     = round(_hs_v("Privado", "tau2_negro"), 5)
            p["HRS_PRIV_SD"]       = round(_hs_v("Privado", "sd_negro"), 4)
            p["HRS_PUB_GAP_PCT"]   = round(_hs_v("Público", "OR_equiv_pct"), 1)
            p["HRS_PUB_TAU2"]      = round(_hs_v("Público", "tau2_negro"), 5)
            p["HRS_PUB_SD"]        = round(_hs_v("Público", "sd_negro"), 4)

    _hrs_gen = _TAB / "hlm_rs_genero.csv"
    if _hrs_gen.exists():
        _hg = pd.read_csv(_hrs_gen).iloc[0]
        p["HRS_GEN_B_NEGRO"]   = round(float(_hg["b_negro"]), 4)
        p["HRS_GEN_B_SEXO"]    = round(float(_hg["b_sexo_fem"]), 4)
        p["HRS_GEN_TAU2_NEGRO"]= round(float(_hg["tau2_negro"]), 5)
        p["HRS_GEN_SD_NEGRO"]  = round(float(_hg["sd_negro"]), 4)
        p["HRS_GEN_TAU2_SEXO"] = round(float(_hg["tau2_sexo"]), 5)
        p["HRS_GEN_SD_SEXO"]   = round(float(_hg["sd_sexo"]), 4)
        p["HRS_GEN_RHO"]       = round(float(_hg["rho_negro_sexo"]), 4)
        p["HRS_GEN_LR"]        = round(float(_hg["LR_add_sexo"]), 1)

    # ── Random slope GLMM de GÊNERO (lme4) — glmm_genero_varcomp.csv ──────────
    _gge_path = _TAB / "glmm_genero_varcomp.csv"
    if _gge_path.exists():
        _gge = pd.read_csv(_gge_path)
        def _gge_v(des, col):
            row = _gge.loc[_gge["desfecho"] == des]
            return float(row[col].values[0]) if len(row) else None
        for des, key in [("ocp_qualif", "OCP"), ("y_top20", "TOP20"), ("y_top10", "TOP10")]:
            if _gge_v(des, "OR_sexo") is None:
                continue
            p[f"GGE_{key}_OR"]   = round(_gge_v(des, "OR_sexo"), 4)
            p[f"GGE_{key}_TAU2"] = round(_gge_v(des, "tau2_sexo"), 5)
            p[f"GGE_{key}_SD"]   = round(_gge_v(des, "sd_sexo"), 4)
            p[f"GGE_{key}_RHO"]  = round(_gge_v(des, "rho"), 3)
            p[f"GGE_{key}_LR"]   = round(_gge_v(des, "LR"), 1)

    # ── ML performance (RF/XGBoost) — protocolo de validação (hold-out 80/20) ──
    _ml_path = _TAB / "ml_performance.csv"
    if _ml_path.exists():
        _ml = pd.read_csv(_ml_path)
        for _, row in _ml.iterrows():
            key = "RF" if "Random Forest" in row["Modelo"] else "XGB"
            p[f"ML_{key}_R2_TESTE"]  = round(float(row["R²"]), 4)
            p[f"ML_{key}_MAE"]       = round(float(row["MAE"]), 4)
            p[f"ML_{key}_RMSE"]      = round(float(row["RMSE"]), 4)
            if "R2_treino" in row and pd.notna(row["R2_treino"]):
                p[f"ML_{key}_R2_TREINO"] = round(float(row["R2_treino"]), 4)
                p[f"ML_{key}_GAP_OVERFIT"] = round(float(row["gap_overfit"]), 4)

    # ── ML performance — validação cruzada k-fold (se já rodada) ──────────────
    _ml_cv_path = _TAB / "ml_performance_cv.csv"
    if _ml_cv_path.exists():
        _mlcv = pd.read_csv(_ml_cv_path)
        for _, row in _mlcv.iterrows():
            key = "RF" if "Random Forest" in row["Modelo"] else "XGB"
            p[f"ML_{key}_CV_R2_MEAN"] = round(float(row["R2_mean"]), 4)
            p[f"ML_{key}_CV_R2_SD"]   = round(float(row["R2_sd"]), 4)
            p[f"ML_{key}_CV_K"]       = int(row["k"])

    # ── ML — baseline OLS/HLM vs. ML (ganho real da camada de ML) ────────────
    _ml_base_path = _TAB / "ml_baseline_comparacao.csv"
    if _ml_base_path.exists():
        _mlb = pd.read_csv(_ml_base_path)
        _ols_row = _mlb.loc[_mlb["Modelo"].str.contains("OLS")]
        if len(_ols_row):
            p["ML_OLS_R2"] = round(float(_ols_row["R2_teste"].values[0]), 4)
        _rf_row = _mlb.loc[_mlb["Modelo"] == "Random Forest"]
        if len(_rf_row):
            p["ML_RF_GANHO_VS_OLS"] = round(float(_rf_row["ganho_R2_vs_OLS"].values[0]), 4)
        _xgb_row = _mlb.loc[_mlb["Modelo"] == "XGBoost"]
        if len(_xgb_row):
            p["ML_XGB_GANHO_VS_OLS"] = round(float(_xgb_row["ganho_R2_vs_OLS"].values[0]), 4)

    # ── SHAP — estabilidade RF × XGBoost (Spearman) ──────────────────────────
    _shap_path = _TAB / "shap_importance_comparada.csv"
    if _shap_path.exists():
        from scipy.stats import spearmanr
        _sh = pd.read_csv(_shap_path)
        _rho, _pval = spearmanr(_sh["Rank_RF"], _sh["Rank_XGB"])
        p["SHAP_SPEARMAN_RHO"] = round(float(_rho), 3)
        p["SHAP_SPEARMAN_P"]   = float(_pval)
        _top10_rf  = set(_sh.nsmallest(10, "Rank_RF")["Feature"])
        _top10_xgb = set(_sh.nsmallest(10, "Rank_XGB")["Feature"])
        p["SHAP_TOP10_OVERLAP"] = len(_top10_rf & _top10_xgb)
        _row_negro = _sh.loc[_sh["Feature"].str.contains("negro", case=False)]
        if len(_row_negro):
            p["SHAP_NEGRO_RANK_RF"]  = int(_row_negro["Rank_RF"].values[0])
            p["SHAP_NEGRO_RANK_XGB"] = int(_row_negro["Rank_XGB"].values[0])

    # ── SHAP — bootstrap de estabilidade (se já rodado) ──────────────────────
    _shap_boot_path = _TAB / "shap_bootstrap_ci.csv"
    if _shap_boot_path.exists():
        _shb = pd.read_csv(_shap_boot_path)
        _row_negro_b = _shb.loc[_shb["Feature"].str.contains("negro", case=False)]
        if len(_row_negro_b):
            p["SHAP_BOOT_NEGRO_MEAN"] = round(float(_row_negro_b["mean_abs_shap_mean"].values[0]), 5)
            p["SHAP_BOOT_NEGRO_CI_LO"] = round(float(_row_negro_b["ci_lo"].values[0]), 5)
            p["SHAP_BOOT_NEGRO_CI_HI"] = round(float(_row_negro_b["ci_hi"].values[0]), 5)

    # ── Oaxaca-Blinder — sensibilidade de especificação (com/sem ocupação) ───
    # ob_decomposicao.csv: Mincer puro (sem ocupação nem contexto de UPA) — tcc/PERICIA.md F1
    _obd_path = _TAB / "ob_decomposicao.csv"
    if _obd_path.exists():
        _obd = pd.read_csv(_obd_path)
        p["OB_SEM_OCUP_DOT_PCT"] = round(float(_obd["pct_dotacao"].iloc[0]), 1)
        p["OB_SEM_OCUP_RET_PCT"] = round(float(_obd["pct_coeficiente"].iloc[0]), 1)
    # ob_acesso.csv: especificação de acesso (com ocupação + contexto) — a usada no núcleo do TCC
    _oba_path = _TAB / "ob_acesso.csv"
    if _oba_path.exists():
        _oba2 = pd.read_csv(_oba_path)
        p["OB_COM_OCUP_DOT_PCT"] = round(float(_oba2["pct_dotacao"].iloc[0]), 1)
        p["OB_COM_OCUP_RET_PCT"] = round(float(_oba2["pct_coeficiente"].iloc[0]), 1)
        if "se_dotacao" in _oba2.columns:
            p["OB_COM_OCUP_N_BOOT"] = int(_oba2["n_bootstrap"].iloc[0])

    # ── Oaxaca-Blinder — refit ponderado por V1028 (robustez desenho amostral) ─
    _ob_pond_path = _TAB / "oaxaca_ponderado.csv"
    if _ob_pond_path.exists():
        _obp = pd.read_csv(_ob_pond_path)
        for _, row in _obp.iterrows():
            key = "POND" if row.get("ponderado", False) else "NPOND"
            p[f"OB_{key}_DOT_PCT"] = round(float(row["pct_dotacao"]), 1)
            p[f"OB_{key}_RET_PCT"] = round(float(row["pct_coeficiente"]), 1)
            p[f"OB_{key}_SE_RET"]  = round(float(row["se_coeficiente"]), 4)

    # ── GLMM ponderado por V1028 (robustez desenho amostral, R lme4-vs-glm) ──
    _glmm_pond_path = _TAB / "glmm_ponderado.csv"
    if _glmm_pond_path.exists():
        _glp = pd.read_csv(_glmm_pond_path)
        for _, row in _glp.iterrows():
            key = "POND" if row.get("ponderado", False) else "NPOND"
            p[f"GLMM_{key}_OR"]     = round(float(row["OR_negro"]), 4)
            p[f"GLMM_{key}_SE"]     = round(float(row["SE_negro"]), 4)
            p[f"GLMM_{key}_CI_LO"]  = round(float(row["CI95_lo"]), 4)
            p[f"GLMM_{key}_CI_HI"]  = round(float(row["CI95_hi"]), 4)

    # ── Glassceil (Tabela 1) ponderado por V1028 — mesmo modelo da Tabela 1 ──
    _gc_pond_path = _TAB / "glmm_glassceil_ponderado.csv"
    if _gc_pond_path.exists():
        _gcp = pd.read_csv(_gc_pond_path)
        for des in ["ocp_qualif", "y_top20", "y_top10"]:
            sub = _gcp.loc[_gcp["desfecho"] == des]
            for _, row in sub.iterrows():
                # A string "HC1 (atual, sem peso/cluster)" contém as
                # substrings "peso" E "cluster" só para dizer que NÃO tem
                # nenhum dos dois — por isso o teste de "HC1" vem primeiro.
                espec = row["especificacao"]
                if espec.startswith("HC1"):
                    tag = "HC1"
                elif "peso V1028" in espec:
                    tag = "POND"
                elif "cluster" in espec:
                    tag = "CLUSTER"
                else:
                    tag = "HC1"
                key_des = {"ocp_qualif": "OCP", "y_top20": "TOP20", "y_top10": "TOP10"}[des]
                p[f"GC_{key_des}_{tag}_OR"] = round(float(row["OR_negro"]), 4)
                p[f"GC_{key_des}_{tag}_SE"] = round(float(row["SE_negro"]), 4)

    # ── Interseccionalidade — bootstrap CI da penalidade extra ───────────────
    _itx_boot_path = _TAB / "interseccional_bootstrap_ci.csv"
    if _itx_boot_path.exists():
        _itxb = pd.read_csv(_itx_boot_path)
        _row_mn = _itxb.loc[_itxb["grupo"] == "Mulher Negra"]
        if len(_row_mn):
            p["ITX_PENAL_MEAN"]  = round(float(_row_mn["penalidade_mean"].values[0]), 2)
            p["ITX_PENAL_CI_LO"] = round(float(_row_mn["penalidade_ci_lo"].values[0]), 2)
            p["ITX_PENAL_CI_HI"] = round(float(_row_mn["penalidade_ci_hi"].values[0]), 2)
            p["ITX_PENAL_B"]     = int(_row_mn["B_efetivo"].values[0])

    # ── Interseccionalidade — IC do termo de interação tripla (HLM, já disponível) ─
    _itxc_path = _TAB / "interseccional_coeficientes.csv"
    if _itxc_path.exists():
        _itxc = pd.read_csv(_itxc_path)
        _row_triple = _itxc.loc[_itxc["Variável"] == "negro_x_mulher_x_superior"]
        if len(_row_triple):
            import re as _re
            _cell = str(_row_triple["Interseccional"].values[0])
            _m = _re.match(r"(-?[\d.,]+)\*+\s*\(([\d.,]+)\)", _cell)
            if _m:
                _b_triple  = float(_m.group(1).replace(",", "."))
                _se_triple = float(_m.group(2).replace(",", "."))
                p["ITX_TRIPLE_B"]     = round(_b_triple, 4)
                p["ITX_TRIPLE_SE"]    = round(_se_triple, 4)
                p["ITX_TRIPLE_CI_LO"] = round(_b_triple - 1.96 * _se_triple, 4)
                p["ITX_TRIPLE_CI_HI"] = round(_b_triple + 1.96 * _se_triple, 4)

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
