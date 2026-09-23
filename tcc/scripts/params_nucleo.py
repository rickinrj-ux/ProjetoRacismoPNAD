# -*- coding: utf-8 -*-
"""
params_nucleo.py
================
Fonte única de números para os entregáveis do TCC **enxuto** (núcleo de 4
métodos + robustez). Lê os csv de `outputs/tables/` — os mesmos que alimentam
o relatório — e devolve um dicionário `P` já arredondado.

Existe porque o `params.py` da raiz é da versão estendida: lê csv que o núcleo
não usa mais (kmeans, SNA, TOPSIS, `hlm_serie_completo` de três níveis) e que
levariam números divergentes do relatório para dentro do guia de defesa.

Uso:  from params_nucleo import P, pt, pct
Teste: python tcc/scripts/params_nucleo.py   (imprime tudo o que foi lido)
"""
from __future__ import annotations

import csv
import re
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "outputs" / "tables"


# ── helpers de formatação (pt-BR) ─────────────────────────────────────────────
def pt(x: float, d: int = 1) -> str:
    """Número no padrão brasileiro: 0,699 — com menos sinal tipográfico."""
    return f"{float(x):.{d}f}".replace(".", ",").replace("-", "−")


def pct(x: float, d: int = 1) -> str:
    return pt(x, d) + "%"


def milhar(x: float) -> str:
    return f"{int(round(float(x))):,}".replace(",", ".")


def _rows(nome: str) -> list[dict]:
    p = TAB / nome
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _f(v) -> float | None:
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _limpar_tex(s: str) -> str:
    """Rótulos dos csv vêm prontos para LaTeX; o Word precisa de texto puro."""
    s = s.replace(r"\%", "%").replace(r"\&", "&").replace("~", " ")
    s = s.replace("$z$", "z").replace("$", "").replace(r"\emph", "").replace(r"\textit", "")
    return re.sub(r"\\[a-zA-Z]+", "", s).replace("{", "").replace("}", "").strip()


def _evalue(or_val: float) -> float:
    """VanderWeele & Ding (2017); para OR < 1 usa-se o inverso."""
    o = 1 / or_val if or_val < 1 else or_val
    return o + math.sqrt(o * (o - 1))


# ── leitura ───────────────────────────────────────────────────────────────────
def carregar() -> dict:
    P: dict = {}

    # HLM step-up (dois níveis: indivíduo em UPA, efeitos fixos de UF)
    fit = {r["modelo"]: r for r in _rows("hlm_stepup_fit.csv")}
    coef = {(r["modelo"], r["variavel"]): r for r in _rows("hlm_stepup_coefs.csv")}
    gap = {r["Modelo"]: r for r in _rows("gap_decomposicao_stepup.csv")}
    varc = {r["componente"]: r for r in _rows("hlm_stepup_varcomp.csv")}
    konf = {r["modelo"]: r for r in _rows("hlm_stepup_konfound.csv")}
    if fit:
        P["N_HLM"] = int(_f(fit["M0"]["n"]))
        P["TAU2_M0"] = _f(fit["M0"]["tau2_upa"])
        P["SIGMA2_M0"] = _f(fit["M0"]["sigma2"])
        P["ICC_M0"] = _f(fit["M0"]["icc_upa"])
        P["ICC_M3"] = _f(fit["M3"]["icc_upa"])
        P["LR_M2"] = _f(fit["M2"]["lr_vs_anterior"])
        P["LR_RS"] = _f(fit["M3_RS"]["lr_vs_anterior"])
        P["TAU2_SLOPE"] = _f(fit["M3_RS"]["tau2_slope_negro"])
        P["SD_SLOPE"] = _f(fit["M3_RS"]["sd_slope_negro"])
        P["COV_INT_SLOPE"] = _f(fit["M3_RS"]["cov_int_slope"])
        P["TAU2_EXPL_M1"] = _f(fit["M1"]["pct_tau2_explicada_vs_M0"])
        P["TAU2_EXPL_M3"] = _f(fit["M3"]["pct_tau2_explicada_vs_M0"])
    if varc:
        P["TAU2_M0_ML"] = _f(varc["tau2_upa"]["ML"])
        P["TAU2_M0_REML"] = _f(varc["tau2_upa"]["REML"])
    for m in ("M1", "M2", "M3", "M4"):
        if m in gap:
            P[f"B_{m}"] = _f(gap[m]["b_negro"])
            P[f"GAP_{m}"] = abs(_f(gap[m]["Gap%"]))
            P[f"SE_{m}"] = _f(gap[m]["se"])
    if ("M2", "pct_negro_upa_z") in coef:
        P["GAMMA01"] = _f(coef[("M2", "pct_negro_upa_z")]["coef"])
        P["GAMMA01_SE"] = _f(coef[("M2", "pct_negro_upa_z")]["se"])
    if "M3" in konf:
        P["KONFOUND_M3"] = _f(konf["M3"]["pct_vies_para_invalidar"])
        P["ITCV_M3"] = _f(konf["M3"]["itcv"])

    # Gap agregado (OLS com efeitos fixos de UF, sem efeito de bairro)
    for r in _rows("hlm_serie_completo_se.csv"):
        if r.get("modelo") == "M1_Individual_OLS" and r.get("variavel") == "negro":
            P["B_POOL"] = _f(r["coef"])
            P["GAP_POOL"] = abs((math.exp(P["B_POOL"]) - 1) * 100)
    if "GAP_POOL" in P and "B_M1" in P:
        # mediação acumulada de cada degrau em relação ao gap agregado
        for m in ("M1", "M2", "M3", "M4"):
            if f"B_{m}" in P:
                P[f"MED_ACUM_{m}"] = (abs(P["B_POOL"]) - abs(P[f"B_{m}"])) / abs(P["B_POOL"]) * 100
        P["MED_BAIRRO"] = (abs(P["B_POOL"]) - abs(P["B_M1"])) / abs(P["B_POOL"]) * 100
        P["MED_OCUP"] = (abs(P["B_M3"]) - abs(P["B_M4"])) / abs(P["B_POOL"]) * 100
        P["RESID_PCT"] = abs(P["B_M4"]) / abs(P["B_POOL"]) * 100

    # Oaxaca-Blinder: duas especificações
    for r in _rows("ob_acesso.csv"):
        suf = "SEM" if r["espec"] == "sem_ocupacao" else "COM"
        P[f"OB_{suf}_GAP_PCT"] = _f(r["gap_pct"])
        P[f"OB_{suf}_DOT_PCT"] = _f(r["pct_dotacao"])
        P[f"OB_{suf}_RET_PCT"] = _f(r["pct_coeficiente"])
        P[f"OB_{suf}_SE_RET"] = _f(r["se_coeficiente"])
        P["OB_N"] = int(_f(r["n_brancos"]) + _f(r["n_negros"]))
        P["OB_N_UPAS"] = int(_f(r["n_upas"]))
        P["OB_N_BOOT"] = int(_f(r["n_bootstrap"]))

    # Regressão quantílica (condicional) e teste de heterogeneidade
    for r in _rows("qr_melhorias.csv"):
        if r["grupo"] == "Global":
            q = str(round(_f(r["quantil"]) * 100))
            P[f"QR_B_Q{q}"] = _f(r["b_negro"])
            P[f"QR_GAP_Q{q}"] = abs(_f(r["gap_pct"]))
    for r in _rows("qr_kb_test.csv"):
        P["QR_DIFF"] = _f(r["diff_q90_q10"])
        P["QR_Z"] = _f(r["z_stat"])
        P["QR_SE_BOOT"] = _f(r["se_boot"])
        P["QR_M_UPAS"] = int(_f(r["m_upas"]))
        P["QR_N_UPAS"] = int(_f(r["n_upas"]))

    # RIF-OB (quantis incondicionais). Dotações + retornos são normalizados
    # para 100% — é assim que a tabela do relatório apresenta.
    for r in _rows("rif_ob_se.csv"):
        end, ret = _f(r["end"]), _f(r["ret"])
        if end is None or ret is None or (end + ret) == 0:
            continue
        q = r["q_label"].upper()
        P[f"RIF_RET_{q}"] = ret / (end + ret) * 100
        P[f"RIF_DOT_{q}"] = end / (end + ret) * 100
        P[f"RIF_GAP_{q}"] = _f(r["gap_obs"])

    # GLMM logístico (lme4::glmer) — fonte da barreira de acesso
    for r in _rows("glmm_glassceil_glmer.csv"):
        k = f"{r['desfecho']}_{r['modelo']}"
        P[f"OR_{k}"] = _f(r["OR_negro"])
        P[f"CI_{k}"] = (_f(r["CI95_lo"]), _f(r["CI95_hi"]))
        P[f"AME_{k}"] = _f(r["AME_pp"])
        P[f"ICC_{k}"] = _f(r["ICC_UPA"])
        P[f"AUC_{k}"] = _f(r["AUC_com_RE"])
        P[f"AUCFE_{k}"] = _f(r["AUC_so_FE"])
        P[f"LR_{k}"] = _f(r["LR_vs_pooled"])
        P[f"EV_{k}"] = _evalue(P[f"OR_{k}"])
        if r["modelo"] == "M2":
            P[f"CUT_{r['desfecho']}"] = _f(r["cutoff_youden"])
            P[f"SENS_{r['desfecho']}"] = _f(r["sens"])
            P[f"ESPEC_{r['desfecho']}"] = _f(r["espec"])
        if r["modelo"] == "M1":
            P["N_GLMM"] = int(_f(r["N"]))
            P["N_UPAS"] = int(_f(r["n_upa"]))
        if r["modelo"] == "M4":
            P[f"ORI_SUP_{r['desfecho']}"] = _f(r["OR_inter_superior"])

    # Interseccionalidade (OB de 4 grupos, referência = homem branco)
    for r in _rows("interseccional_ob4grupos_nucleo.csv"):
        g = r["grupo"].replace(" ", "_").upper()
        P[f"INT_{g}_GAP"] = _f(r["gap_pct"])
        P[f"INT_{g}_DOT"] = _f(r["end_pct"])
        P[f"INT_{g}_RET"] = _f(r["ret_pct"])
        P[f"INT_{g}_N"] = int(_f(r["n_n"]))
        if _f(r["penalidade_extra_pct"]):
            P["INT_PENAL_EXTRA"] = _f(r["penalidade_extra_pct"])
    for r in _rows("interseccional_ob4grupos_se.csv"):
        g = r.get("grupo", "").replace(" ", "_").upper()
        if g:
            P[f"INT_{g}_SE"] = _f(r.get("se_gap_pct") or r.get("se_gap"))

    # Machine learning: desempenho, validação cruzada e SHAP
    APELIDO = {"Random Forest": "RF", "XGBoost": "XGB",
               "XGBoost (sem renda da UPA)": "XGB_SEM_UPA"}
    for r in _rows("ml_performance.csv"):
        nome = APELIDO.get(r["Modelo"].strip())
        if not nome:                       # modelo novo: chave a partir do rótulo
            nome = r["Modelo"].upper().replace(" ", "_")[:12]
        P[f"ML_{nome}_R2"] = _f(r["R²"])
        P[f"ML_{nome}_R2_TREINO"] = _f(r["R2_treino"])
        P[f"ML_{nome}_GAP"] = _f(r["gap_overfit"])
        P[f"ML_{nome}_MAE"] = _f(r["MAE"])
    for r in _rows("ml_cv_resumo.csv"):
        P["CV_K"] = int(_f(r["k"]))
        P["CV_R2"] = _f(r["cv_r2_media"])
        P["CV_R2_DP"] = _f(r["cv_r2_dp"])
        P["CV_MAE"] = _f(r["cv_mae_media"])
        P["CV_DEPTH"] = int(_f(r["escolhido_max_depth"]))
        P["CV_SMEARING"] = _f(r["smearing_duan"])
        P["CV_ERRO_MEDIANO"] = _f(r["erro_mediano_reais"])
        P["CV_ERRO_PCT"] = _f(r["erro_mediano_pct"])
        P["CV_N_TREINO"] = int(_f(r["n_treino"]))
        P["CV_N_TESTE"] = int(_f(r["n_teste"]))
    hp = _rows("ml_cv_hiperparametros.csv")
    if hp:
        P["CV_N_CONFIGS"] = len(hp)
        pior = min(hp, key=lambda r: _f(r["r2"]))
        P["CV_R2_PIOR"] = _f(pior["r2"])
        P["CV_DEPTH_PIOR"] = int(_f(pior["max_depth"]))
    for r in _rows("shap_importance_comparada.csv"):
        if r["Feature"].startswith("Raça"):
            P["SHAP_RACA_XGB"] = _f(r["SHAP_mean_abs_XGB"])
            P["SHAP_RACA_RANK_XGB"] = int(_f(r["Rank_XGB"]))
            P["SHAP_RACA_RANK_RF"] = int(_f(r["Rank_RF"]))
        if r["Feature"].startswith("Renda média UPA"):
            P["SHAP_TOP1"] = r["Feature"]
            P["SHAP_TOP1_XGB"] = _f(r["SHAP_mean_abs_XGB"])
    P["SHAP_N_FEATURES"] = len(_rows("shap_importance_comparada.csv"))
    for r in _rows("shap_importance_sem_renda_upa.csv"):
        if r.get("Feature", "").startswith("Raça"):
            P["SHAP_RACA_SEM_UPA"] = _f(r.get("SHAP_mean_abs_XGB") or r.get("SHAP_mean_abs"))

    # Balanceamento (suporte comum) e VIF
    bal = [r for r in _rows("balanceamento.csv") if _f(r["d_cohen"]) is not None]
    if bal:
        maior = max(bal, key=lambda r: abs(_f(r["d_cohen"])))
        P["BAL_MAIOR_VAR"] = _limpar_tex(maior["rotulo"])
        P["BAL_MAIOR_D"] = _f(maior["d_cohen"])
        P["BAL_N_VARS"] = len(bal)
        P["BAL_N_PEQUENO"] = sum(1 for r in bal if abs(_f(r["d_cohen"])) < 0.2)
    vif = [r for r in _rows("vif_m4_preditores.csv") if _f(r["VIF"]) is not None]
    if vif:
        P["VIF_MAX"] = _f(max(vif, key=lambda r: _f(r["VIF"]))["VIF"])
        P["VIF_MAX_VAR"] = max(vif, key=lambda r: _f(r["VIF"]))["label"]
        P["VIF_N_CRITICO"] = sum(1 for r in vif if _f(r["VIF"]) > 10)
        P["VIF_N_TOTAL"] = len(vif)
        neg = [r for r in vif if r["predictor"] == "negro"]
        if neg:
            P["VIF_NEGRO"] = _f(neg[0]["VIF"])

    return P


P = carregar()


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    print(f"params_nucleo: {len(P)} parâmetros lidos de {TAB}\n")
    for k in sorted(P):
        print(f"  {k:24s} = {P[k]}")
