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


# ── frases-manchete compartilhadas (aprovadas pelo autor em 03/10/2026) ─────────
# Um único lugar para as frases que aparecem em texto, decks, Guia e figuras: se os
# números mudarem, todas mudam juntas — e a forma ("metade", "o diploma iguala") segue
# o que os números mostram, nunca o contrário.
def titulo_bairro(P: dict) -> str:
    """Título da mediação pelo bairro: 'metade' só se for, de fato, ~metade."""
    m = P["MED_BAIRRO"]
    if 45 <= m <= 55:
        return "Metade do gap desaparece ao comparar pessoas do mesmo bairro"
    return f"Comparar vizinhos reduz o gap em cerca de {pct(5 * round(m / 5), 0)}"


def frase_diploma(P: dict) -> str:
    """Segunda frase da síntese: o diploma iguala o salário, mas não a porta? Depende de
    a penalidade salarial na pós ser pequena e a desvantagem de acesso na pós persistir."""
    sal_pos, ac_pos = P.get("NE_GAP_POS"), P.get("PCTPOS_ocp_qualif")
    if sal_pos is None or ac_pos is None:
        return ""
    if sal_pos < 3 and ac_pos >= 10:
        return "O diploma quase iguala o salário, mas não abre a porta."
    if sal_pos < 3:
        return "Com diploma, salário e acesso quase se igualam."
    return "Nem o diploma iguala o salário."


def frase_sintese(P: dict) -> str:
    """A frase-síntese do trabalho (sem marcação; cada gerador formata)."""
    return (f"Com a mesma escolaridade, idade, sexo e bairro, um trabalhador negro ganha "
            f"{pct(P['GAP_M3'])} a menos e tem chances "
            f"{pct((1 - P['OR_ocp_qualif_M2']) * 100, 0)} menores de chegar a um cargo "
            f"qualificado. " + frase_diploma(P)).strip()


def _int_logs(P: dict) -> tuple[float, float]:
    """(gap da mulher negra, soma mulher branca + homem negro), em log-pontos."""
    return (P["INT_MULHER_NEGRA_LOG"],
            P["INT_MULHER_BRANCA_LOG"] + P["INT_HOMEM_NEGRO_LOG"])


def frase_interseccional(P: dict) -> str:
    """Leitura única da interseccionalidade (E2.3, 03/10/2026).

    A "penalidade extra" somava percentuais, escala convexa: 80,7% > 19,9% + 56,4%, mas em
    log-pontos (escala aditiva) 0,592 < 0,182 + 0,447 — sub-aditivo, como a interação
    negro×mulher do GLMM. O texto segue o sinal em log-pontos.
    """
    mn, soma = _int_logs(P)
    base = (f"A mulher negra teve o maior gap ({pct(P['INT_MULHER_NEGRA_GAP'])} contra o homem "
            f"branco), ")
    if mn < soma:
        return base + (f"mas suas desvantagens de raça e de gênero se acumularam sem se "
                       f"multiplicar: em log-pontos, o gap dela ({pt(mn, 3)}) ficou abaixo da "
                       f"soma das penalidades isoladas ({pt(soma, 3)}).")
    return base + (f"e ele superou em {pt(mn - soma, 3)} log-pontos a soma das penalidades "
                   f"isoladas de raça e de gênero.")


def frase_interseccional_en(P: dict) -> str:
    mn, soma = _int_logs(P)
    e = lambda x, d=1: f"{x:.{d}f}"
    base = (f"Black women faced the largest gap ({e(P['INT_MULHER_NEGRA_GAP'])}% relative to "
            f"white men), ")
    if mn < soma:
        return base + (f"but their race and gender disadvantages accumulated without "
                       f"multiplying: in log points, their gap ({e(mn, 3)}) fell below the sum "
                       f"of the separate penalties ({e(soma, 3)}).")
    return base + (f"exceeding the sum of the separate race and gender penalties by "
                   f"{e(mn - soma, 3)} log points.")


def frase_cbo_mulher_negra(P: dict) -> str:
    """E2.16 (03/10/2026): a "vantagem" da mulher negra no acesso a CBO 1-4 é composição.

    GLMM por grande grupo CBO (run_grupo_rg_por_cbo.R): ela entra mais no apoio
    administrativo e nas profissões de ensino e saúde — ocupações feminizadas em que a mulher
    branca entra ainda mais — e é o grupo com menor chance entre os dirigentes. O texto segue
    os números: cada trecho só é afirmado se o sinal o sustentar.
    """
    if "CBO_MN_dirigente" not in P:
        return ""
    o = lambda k: pt(P[k], 2)
    partes = []
    fem = [g for g in ("administrativo", "profissional")
           if P[f"CBO_MN_{g}"] > 1 and P[f"CBO_MB_{g}"] > P[f"CBO_MN_{g}"]]
    if fem:
        nomes = {"administrativo": "do apoio administrativo", "profissional": "das profissões de nível superior, sobretudo ensino e saúde"}
        partes.append(
            "A aparente vantagem da mulher negra no acesso a cargos CBO 1–4 é composição: vem "
            + " e ".join(f"{nomes[g]} (OR {o(f'CBO_MN_{g}')})" for g in fem)
            + ", ocupações feminizadas em que a mulher branca entra ainda mais ("
            + " e ".join(o(f"CBO_MB_{g}") for g in fem) + ").")
    menor = min(("MB", "HN", "MN"), key=lambda g: P[f"CBO_{g}_dirigente"])
    if P["CBO_MN_dirigente"] < 1:
        partes.append(
            f"Entre os dirigentes, onde se exerce comando, a mulher negra tem "
            + ("a menor chance de todos os grupos" if menor == "MN" else "chance menor que o homem branco")
            + f" (OR {o('CBO_MN_dirigente')}).")
    return " ".join(partes)


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


def _prevalencias() -> dict:
    out = {}
    for r in _rows("glmm_prevalencias.csv"):
        out[r["desfecho"]] = float(r["prevalencia"])
    return out


_PREV = None


def evalue(or_val: float, desfecho: str | None = None) -> float:
    """E-value de VanderWeele & Ding (2017) para uma razão de chances (OR < 1: o inverso).

    Desfecho comum (prevalência >= 15%): a OR exagera a razão de risco, e o E-value usa
    RR ≈ √OR (E2.7, 03/10/2026 — antes aplicava-se a fórmula direto à OR do acesso, com 30%
    de prevalência, e o E-value saía 1,76 em vez de 1,45). Desfecho raro: RR ≈ OR.
    É a ÚNICA implementação: tabela do GLMM, relatório, robustez e validate importam daqui.
    """
    global _PREV
    if _PREV is None:
        _PREV = _prevalencias()
    o = 1 / or_val if or_val < 1 else or_val
    if desfecho is not None and _PREV.get(desfecho, 0.0) >= 0.15:
        o = math.sqrt(o)
    return o + math.sqrt(o * (o - 1))


def _evalue(or_val: float, desfecho: str | None = None) -> float:
    return evalue(or_val, desfecho)


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
    # E2.2: teste da escada — o agregado tem UF e o M1 não; o M1 com UF (mesma base) mostra
    # quanto da "mediação pelo bairro" seria o estado saindo do modelo
    for r in _rows("hlm_m1_uf.csv"):
        P["B_M1_UF"] = _f(r["b_negro"])
        P["GAP_M1_UF"] = abs(_f(r["gap_pct"]))
        if "B_POOL" in P:
            P["MED_BAIRRO_UF"] = (abs(P["B_POOL"]) - abs(P["B_M1_UF"])) / abs(P["B_POOL"]) * 100
    for r in _rows("gap_agregado.csv"):
        if r["modelo"] == "agregado_sem_UF":
            P["GAP_POOL_SEM_UF"] = abs(_f(r["gap_pct"]))
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
            # do β, não do gap_pct do csv (2 casas): 4,25 arredondava para 4,2 no Guia
            # enquanto o TCC, que parte do β (4,257), mostrava 4,3 (E7.1)
            P[f"QR_GAP_Q{q}"] = abs((math.exp(_f(r["b_negro"])) - 1) * 100)
    # HLM de TRÊS níveis (pessoa < UPA < UF, ambos aleatórios) — robustez.
    # Não é a especificação do trabalho; serve para separar o que o modelo de
    # dois níveis credita ao "território" em bairro e estado.
    for r in _rows("hlm_tres_niveis.csv"):
        m = r["modelo"]
        P[f"N3_ICC_UF_{m}"]  = _f(r["icc_uf"]) * 100
        P[f"N3_ICC_UPA_{m}"] = _f(r["icc_upa"]) * 100
        P[f"N3_TAU2_UF_{m}"]  = _f(r["tau2_uf"])
        P[f"N3_TAU2_UPA_{m}"] = _f(r["tau2_upa"])
        if _f(r.get("b_negro")) is not None:
            P[f"N3_B_NEGRO_{m}"] = _f(r["b_negro"])

    # Gap por quantil dentro de cada tipo de área (Capital, RM, Interior).
    # Chaves no formato QR_AREA_{AREA}_Q{quantil}, em valor absoluto — o texto
    # fala em "penalidade de X%", não em coeficiente negativo.
    _slug = {"Capital": "CAPITAL", "Interior": "INTERIOR",
             "RM (exceto capital)": "RM"}
    for r in _rows("qr_gap_por_area.csv"):
        a = _slug.get(r["area"])
        if a:
            q = str(round(_f(r["quantil"]) * 100))
            P[f"QR_AREA_{a}_Q{q}"] = abs(_f(r["gap_pct"]))

    # Contraprova de forma funcional: contraste da contribuição racial entre os
    # dois grupos no modelo preditivo. É o análogo do coeficiente racial num
    # método que não impõe forma nenhuma — serve de checagem do resíduo.
    _sg = {r["grupo"]: r for r in _rows("shap_negro_por_grupo.csv")
           if r.get("modelo") == "XGBoost"}
    if {"negros", "brancos"} <= set(_sg):
        _d = _f(_sg["negros"]["shap_medio_negro"]) - _f(_sg["brancos"]["shap_medio_negro"])
        P["ML_CONTRASTE_PCT"] = abs((math.exp(_d) - 1) * 100)

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
        P[f"EV_{k}"] = _evalue(P[f"OR_{k}"], r["desfecho"])
        # A4: razão de chances da raça para quem tem superior e para quem tem pós. As
        # dummies são cumulativas (pós ⊂ superior), então a pós soma as duas interações.
        if r["modelo"] == "M4" and _f(r.get("OR_inter_superior")) is not None:
            d_ = r["desfecho"]
            P[f"ORSUP_{d_}"] = P[f"OR_{k}"] * _f(r["OR_inter_superior"])
            P[f"ORPOS_{d_}"] = P[f"ORSUP_{d_}"] * _f(r["OR_inter_pos"])
            P[f"PCTSUP_{d_}"] = (1 - P[f"ORSUP_{d_}"]) * 100
            P[f"PCTPOS_{d_}"] = (1 - P[f"ORPOS_{d_}"]) * 100
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
        P[f"INT_{g}_LOG"] = _f(r["gap"])            # log-pontos (escala aditiva)
        P[f"INT_{g}_DOT"] = _f(r["end_pct"])
        P[f"INT_{g}_RET"] = _f(r["ret_pct"])
        P[f"INT_{g}_N"] = int(_f(r["n_n"]))
        if _f(r["penalidade_extra_pct"]):
            P["INT_PENAL_EXTRA"] = _f(r["penalidade_extra_pct"])
    for r in _rows("interseccional_ob4grupos_se.csv"):
        g = r.get("grupo", "").replace(" ", "_").upper()
        if g:
            P[f"INT_{g}_SE"] = _f(r.get("se_gap_pct") or r.get("se_gap"))

    # Interseccionalidade no acesso (GLMM por grupo raça×gênero) — é a fonte da
    # figura grupo_rg_interseccional.png usada no relatório
    for r in _rows("grupo_rg_4grupos_desfechos.csv"):
        d = r["desfecho"].upper().replace("Y_", "")
        P[f"GRG_MB_{d}"] = _f(r["OR_mulher_branca"])
        P[f"GRG_HN_{d}"] = _f(r["OR_homem_negro"])
        P[f"GRG_MN_{d}"] = _f(r["OR_mulher_negra"])
        P[f"GRG_INT_{d}"] = _f(r["OR_interacao"])
    # E2.16: os 4 grupos por grande grupo CBO (dirigente, profissional, tecnico,
    # administrativo, cbo12), mesma especificação do GLMM acima
    for r in _rows("grupo_rg_por_cbo.csv"):
        g = r["desfecho"].replace("y_", "")
        P[f"CBO_MB_{g}"] = _f(r["OR_mulher_branca"])
        P[f"CBO_HN_{g}"] = _f(r["OR_homem_negro"])
        P[f"CBO_MN_{g}"] = _f(r["OR_mulher_negra"])
        P[f"CBO_MN_{g}_LO"] = _f(r["OR_mn_lo"])
        P[f"CBO_MN_{g}_HI"] = _f(r["OR_mn_hi"])
        P[f"CBO_PREV_{g}"] = _f(r["prevalencia"])

    # Gini intra-raça da renda do trabalho entre ocupados (ponderado por V1028)
    for r in _rows("gini_raca.csv"):
        chave = {"Total": "TOTAL", "Brancos": "BRANCO", "Negros": "NEGRO"}.get(r["grupo"])
        if chave:
            P[f"GINI_{chave}"] = _f(r["gini"])

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
        P["VIF_N_ALTO"] = sum(1 for r in vif if 5 < _f(r["VIF"]) <= 10)
        P["VIF_N_MODERADO"] = sum(1 for r in vif if 2 <= _f(r["VIF"]) <= 5)
        P["VIF_N_BAIXO"] = sum(1 for r in vif if _f(r["VIF"]) < 2)
        P["VIF_N_TOTAL"] = len(vif)
        neg = [r for r in vif if r["predictor"] == "negro"]
        if neg:
            P["VIF_NEGRO"] = _f(neg[0]["VIF"])

    # Descritivos brutos (ponderados), antes calculados só dentro do deck da defesa.
    # O csv vem em formato en-US ("1,607,081"; "53.3").
    def _en(s):
        return float(str(s).replace(",", ""))

    t1 = {r[""]: r for r in _rows("tab1_descritiva_racial.csv")}
    if t1:
        P["MED_BR"], P["MED_NG"] = _en(t1["Renda mediana (R$)"]["Brancos"]), _en(t1["Renda mediana (R$)"]["Negros"])
        P["MEDIA_BR"], P["MEDIA_NG"] = _en(t1["Renda média (R$)"]["Brancos"]), _en(t1["Renda média (R$)"]["Negros"])
        P["FORMAL_BR"], P["FORMAL_NG"] = _en(t1["Emprego formal (%)"]["Brancos"]), _en(t1["Emprego formal (%)"]["Negros"])
        P["GAP_MEDIANA"] = (1 - P["MED_NG"] / P["MED_BR"]) * 100
        P["GAP_MEDIA"] = (1 - P["MEDIA_NG"] / P["MEDIA_BR"]) * 100
        P["GAP_LOG"] = (_en(t1["Log-renda média"]["Brancos"]) - _en(t1["Log-renda média"]["Negros"])) * 100
        P["FORMAL_DIF"] = P["FORMAL_BR"] - P["FORMAL_NG"]
    _NIV = {"Sem fundamental completo": "SEMFUND", "Fundamental completo": "FUND",
            "Médio completo": "MEDIO", "Superior completo": "SUP", "Pós-graduação": "POS"}
    for r in _rows("tab2_gap_bruto_subgrupos.csv"):
        if r["Dimensão"] == "Escolaridade" and r["Subgrupo"] == "Pós-graduação":
            P["GAP_MEDIANA_POS"] = _f(r["Gap Mediana (%)"])
        if r["Dimensão"] == "Nível (núcleo)" and r["Subgrupo"] in _NIV:
            P[f"GAPBRUTO_{_NIV[r['Subgrupo']]}"] = _f(r["Gap Mediana (%)"])

    # Penalidade racial condicional por nível de escolaridade (M3 + negro:C(nivel)),
    # run_hlm_negro_por_educ.py — robustez do HLM pedida em 02/10/2026
    _ne = _rows("hlm_negro_por_educ.csv")
    for r in _ne:
        k = {"sem_fund": "SEMFUND", "fund": "FUND", "medio": "MEDIO", "sup": "SUP", "pos": "POS"}[r["nivel"]]
        P[f"NE_GAP_{k}"] = abs(_f(r["gap_pct"]))
        P[f"NE_PCTPOP_{k}"] = _f(r["pct_pop"])
        P[f"NE_PCTNEG_{k}"] = _f(r["pct_negros"])
        P[f"NE_CILO_{k}"] = abs((math.exp(_f(r["ci_hi"])) - 1) * 100)
        P[f"NE_CIHI_{k}"] = abs((math.exp(_f(r["ci_lo"])) - 1) * 100)
    if _ne and _ne[0].get("p_lr") not in (None, ""):
        P["NE_LR"], P["NE_LR_P"] = _f(_ne[0]["lr_vs_m3"]), _f(_ne[0]["p_lr"])

    # Konfound do HLM step-up, por degrau
    for r in _rows("hlm_stepup_konfound.csv"):
        P[f"KF_{r['modelo']}"] = _f(r["pct_vies_para_invalidar"])

    # UPAs do HLM: uma linha por BLUP (difere da contagem do GLMM e da OB/QR pelos filtros)
    blups = _rows("hlm_stepup_blups_upa.csv")
    if blups:
        P["N_UPAS_HLM"] = len(blups)

    # M3 com inclinação aleatória de negro por UPA: correlação intercepto × inclinação
    for r in _rows("hlm_stepup_fit.csv"):
        if r["modelo"] == "M3_RS" and _f(r.get("cov_int_slope")) is not None:
            t0, t1, c01 = _f(r["tau2_upa"]), _f(r["tau2_slope_negro"]), _f(r["cov_int_slope"])
            P["HLM_RS_CORR"] = c01 / math.sqrt(t0 * t1)
            P["HLM_RS_SD_SLOPE"] = math.sqrt(t1)
    for r in _rows("hlm_stepup_coefs.csv"):
        if r["modelo"] == "M3_RS" and r["variavel"] == "negro":
            P["B_M3_RS"] = _f(r["coef"])          # inclinação média do M3 com RS (≠ B_M3)

    # distância entre o efeito racial do XGBoost (SHAP) e o gap do M4, em pontos percentuais
    if P.get("ML_CONTRASTE_PCT") is not None and P.get("GAP_M4") is not None:
        P["ML_VS_M4_PP"] = abs(P["GAP_M4"] - P["ML_CONTRASTE_PCT"])

    # N do ML = treino + teste (não é o N do HLM, que tem outros filtros)
    if P.get("CV_N_TREINO") and P.get("CV_N_TESTE"):
        P["ML_N"] = int(P["CV_N_TREINO"] + P["CV_N_TESTE"])

    # γ01 (composição racial do bairro) em múltiplos da penalidade individual do mesmo M2
    if P.get("GAMMA01") and P.get("B_M2"):
        P["G01_RAZAO"] = abs(P["GAMMA01"]) / abs(P["B_M2"])

    # OR combinado do negro com superior completo no acesso (M4 × interação)
    if "OR_ocp_qualif_M4" in P and "ORI_SUP_ocp_qualif" in P:
        P["OR_COMB_SUP"] = P["OR_ocp_qualif_M4"] * P["ORI_SUP_ocp_qualif"]

    # Contas derivadas que os textos citam — viram parâmetro para ter fonte única
    if "RIF_RET_Q10" in P and "RIF_RET_Q90" in P:
        P["RIF_RET_RAZAO"] = P["RIF_RET_Q10"] / P["RIF_RET_Q90"]
        P["RIF_RET_DELTA"] = P["RIF_RET_Q90"] - P["RIF_RET_Q10"]
        P["RIF_DOT_DELTA"] = P["RIF_DOT_Q90"] - P["RIF_DOT_Q10"]

    # Tendência temporal: β racial do M3 ano a ano (run_m3_serie_sensib.py --serie) e o WLS
    # sobre ela (run_tendencia_temporal.py). Antes, a redução vinha do sna_temporal.csv
    # (gap bruto, versão estendida) e δ/p estavam digitados no texto.
    serie = {int(_f(r["label"])): _f(r["beta_negro"]) for r in _rows("validacao_temporal.csv")
             if "especificacao" in r and r["especificacao"].startswith("M3 do núcleo")}
    if 2016 in serie and 2025 in serie:
        P["TEND_B2016"], P["TEND_B2025"] = serie[2016], serie[2025]
        P["TEND_REDUCAO_PCT"] = (1 - serie[2025] / serie[2016]) * 100   # >0 = o gap encolheu
    for r in _rows("tendencia_temporal_testes.csv"):
        if r["Teste"].startswith("Chow"):
            m = re.search(r"F\((\d+),\s*(\d+)\)\s*=\s*([\d.]+)", r["Estatística"])
            if m:
                P["TEND_CHOW_DF1"], P["TEND_CHOW_DF2"] = int(m.group(1)), int(m.group(2))
                P["TEND_CHOW_F"] = float(m.group(3))
            P["TEND_CHOW_P"] = _f(r["p-valor"])
        if r["Teste"].startswith("WLS"):
            m = re.search(r"([−-]?\d+\.\d+)", r["Estatística"])
            if m:
                # β < 0: δ > 0 significa β subindo rumo a zero, isto é, convergência
                P["TEND_DELTA"] = float(m.group(1).replace("−", "-"))
            P["TEND_P"] = _f(r["p-valor"])
            ic = re.findall(r"[−-]?\d+\.\d+", r.get("IC 95%", "").replace("−", "-"))
            if len(ic) == 2:
                P["TEND_IC_LO"], P["TEND_IC_HI"] = float(ic[0]), float(ic[1])
    if "TEND_DELTA" in P and "TEND_B2016" in P:
        P["TEND_ANOS"] = abs(P["TEND_B2016"]) / P["TEND_DELTA"] if P["TEND_DELTA"] > 0 else float("inf")
        # prazo no cenário mais otimista que os dados admitem (borda superior do IC de δ);
        # é este, e não o ponto, que o texto cita quando a inclinação não é significante
        if P.get("TEND_IC_HI", 0) > 0:
            P["TEND_ANOS_OTIMISTA"] = abs(P["TEND_B2016"]) / P["TEND_IC_HI"]

    # Sensibilidade do β racial ao indicador educ_missing (run_m3_serie_sensib.py --sensib)
    sens = {r["modelo"]: _f(r["beta_negro"]) for r in _rows("sensib_educ_missing.csv")}
    if {"M3", "M3_sem_educ_missing"} <= set(sens):
        P["EDUC_SENS_VAR"] = abs(sens["M3_sem_educ_missing"] / sens["M3"] - 1) * 100

    # Contagens da base (observações brutas, PEA, cobertura da escolaridade), gravadas
    # por tcc/scripts/gerar_descritivos_base.py
    for r in _rows("hlm_rs_figura.csv"):           # tamanho da amostra de retas na figura
        P[r["chave"]] = _f(r["valor"])
    for r in _rows("descritivos_base.csv"):
        v = _f(r["valor"])
        # contagens voltam a int: como float, saíam "15.941.675.0" no texto
        P[r["chave"]] = int(v) if r["chave"].startswith("N_") else v

    # ── Robustez ao desenho amostral e baseline do ML (E8, 04/10/2026) ───────────────
    _abv = {"ocp_qualif": "OCP", "y_top20": "T20", "y_top10": "T10"}
    for r in _rows("glmm_ponderado_a2.csv"):
        P[f"PESO_OR_{_abv[r['desfecho']]}_{'P' if r['ponderado'] == 'True' else 'S'}"] = _f(r["OR_negro"])
    for r in _rows("oaxaca_ponderado_ab.csv"):
        P[f"PESO_OB_{r['espec']}_{'P' if r['ponderado'] == 'True' else 'S'}"] = _f(r["pct_retornos"])
    for r in _rows("ml_baseline_comparacao.csv"):
        _m = {"MQO (baseline linear)": "MQO", "Random Forest": "RF", "XGBoost": "XGB"}.get(r["Modelo"])
        if _m:
            P[f"BASE_R2_{_m}"] = _f(r["R2_teste"])
    # ── Heterogeneidade: cor, setor, idade e topo na UF (E8.6) ───────────────────────
    for r in _rows("hlm_heterogeneidade.csv"):
        t = r["termo"]
        if r["bloco"] == "cor3":
            P[f"HET_HLM_{t.upper()}"] = abs(_f(r["gap_pct"]))
        elif r["bloco"] in ("setor0", "setor1"):
            P[f"HET_HLM_SETOR{r['bloco'][-1]}"] = abs(_f(r["gap_pct"]))
        elif r["bloco"] == "idade":
            P.setdefault("_HET_IDADE", {})[t] = _f(r["beta"])
    if "_HET_IDADE" in P:                       # penalidade implícita por faixa (ref. 30–39)
        _i = P.pop("_HET_IDADE")
        b0 = _i.get("negro")
        for fx in ("14_29", "30_39", "40_49", "50_64", "65mais"):
            b = b0 + _i.get(f"negro:C(faixa, Treatment('30_39'))[T.{fx}]", 0.0)
            P[f"HET_IDADE_{fx.upper()}"] = abs((math.exp(b) - 1) * 100)
    for r in _rows("glmm_heterogeneidade.csv"):
        d = {"ocp_qualif": "OCP", "y_top20": "T20", "y_top10": "T10", "y_top10_uf": "T10UF"}[r["desfecho"]]
        if r["bloco"] == "cor3":
            P[f"HET_OR_{r['termo'].upper()}_{d}"] = _f(r["OR"])
        elif r["bloco"] == "setor":
            P[f"HET_OR_SETOR{int(float(r['setor']))}_{d}"] = _f(r["OR"])
        elif r["bloco"] == "topuf":
            P["HET_OR_T10UF"] = _f(r["OR"])
    for r in _rows("oaxaca_por_cor.csv"):
        P[f"HET_OB_{r['cor'].upper()}_{r['espec']}"] = _f(r["pct_retornos"])
    for r in _rows("qr_por_cor.csv"):
        P[f"HET_QR_{r['cor'].upper()}_Q{round(_f(r['quantil']) * 100)}"] = abs(_f(r["gap_pct"]))
    for r in _rows("rif_por_cor.csv"):
        P[f"HET_RIF_{r['cor'].upper()}_{r['quantil'].upper()}"] = _f(r["pct_retornos"])

    return P


P = carregar()


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    print(f"params_nucleo: {len(P)} parâmetros lidos de {TAB}\n")
    for k in sorted(P):
        print(f"  {k:24s} = {P[k]}")
