"""
gerar_relatorio_tcc.py
======================
Gera relatorio_tcc.tex — documento LaTeX completo com todos os resultados.
Compilar em Overleaf (recomendado) ou MiKTeX local com pdflatex.

Dependências LaTeX: geometry, booktabs, graphicx, amsmath, amssymb,
hyperref, setspace, natbib, caption, subcaption, lmodern, babel (portuguese),
inputenc, fontenc, tabularx, float, longtable, multirow, xcolor, csquotes
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from params import P, fmt, fmtN, ame, or_str

ROOT    = Path(".")
TABLES  = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
OUT_TEX = ROOT / "relatorio_tcc.tex"
OUT_BIB = ROOT / "relatorio_tcc.bib"

# ── Carrega resultados ────────────────────────────────────────────────────────

def load_results():
    r = {}

    # HLM
    hlm_raw = pd.read_csv(TABLES / "hlm_serie_completo.csv", index_col=0)
    r["hlm"] = hlm_raw

    gap = pd.read_csv(TABLES / "gap_decomposicao_serie_completo.csv")
    r["gap"] = gap

    lrt = pd.read_csv(TABLES / "lrt_serie_s20pct.csv")  # LRT NaN estrutural
    r["lrt"] = lrt

    # K-Means
    km_perfis = pd.read_csv(TABLES / "kmeans_perfis_k3.csv", index_col=0)
    r["km_perfis"] = km_perfis
    km_gap = pd.read_csv(TABLES / "kmeans_gap_racial_k3.csv")
    r["km_gap"] = km_gap
    km_metricas = pd.read_csv(TABLES / "kmeans_metricas.csv")
    r["km_metricas"] = km_metricas

    # ML + SHAP
    ml_perf = pd.read_csv(TABLES / "ml_performance.csv")
    r["ml_perf"] = ml_perf
    shap_imp = pd.read_csv(TABLES / "shap_importance_comparada.csv", index_col=0)
    r["shap_imp"] = shap_imp

    # SNA
    sna_nos = pd.read_csv(TABLES / "sna_metricas_nos.csv")
    r["sna_nos"] = sna_nos
    sna_temporal = pd.read_csv(TABLES / "sna_temporal.csv")
    r["sna_temporal"] = sna_temporal

    return r


# ── Extrai métricas-chave para a narrativa ────────────────────────────────────

def extract_kpis(r):
    k = {}

    gap = r["gap"]
    k["b_negro_m1"]     = float(gap.loc[gap["Modelo"] == "M1_Individual", "b_negro"].values[0])
    k["b_negro_m2"]     = float(gap.loc[gap["Modelo"] == "M2_Localidade", "b_negro"].values[0])
    k["b_negro_m3"]     = float(gap.loc[gap["Modelo"] == "M3_Completo",   "b_negro"].values[0])
    k["gap_bruto_pct"]  = float(gap.loc[gap["Modelo"] == "M1_Individual", "Gap%"].values[0])
    k["gap_upa_pct"]    = float(gap.loc[gap["Modelo"] == "M2_Localidade", "Gap%"].values[0])
    k["gap_liquido_pct"]= float(gap.loc[gap["Modelo"] == "M3_Completo",   "Gap%"].values[0])
    k["mediacao_upa"]   = float(gap.loc[gap["Modelo"] == "M2_Localidade", "Mediacao_UPA%"].values[0])
    k["mediacao_total"] = float(gap.loc[gap["Modelo"] == "M3_Completo",   "Mediacao_total%"].values[0])
    if "M4_Ocupacao" in gap["Modelo"].values:
        k["gap_m4"]  = float(gap.loc[gap["Modelo"] == "M4_Ocupacao", "Gap%"].values[0])
        k["med_occ"] = float(gap.loc[gap["Modelo"] == "M4_Ocupacao", "Mediacao_occ%"].values[0])
    else:
        k["gap_m4"]  = k["gap_liquido_pct"]
        k["med_occ"] = 0.0

    hlm = r["hlm"]
    def hlm_val(row, col):
        try:
            return str(hlm.loc[row, col]) if row in hlm.index and col in hlm.columns else "—"
        except Exception:
            return "—"

    k["icc_uf_m0"] = hlm_val("ICC_UF", "M0_Nulo")
    k["icc_uf_m3"] = hlm_val("ICC_UF", "M3_Completo")
    k["n_obs"]     = hlm_val("N (obs.)", "M1_Individual")

    # K-Means
    km = r["km_perfis"]
    c0 = km.loc[0] if 0 in km.index else km.iloc[0]
    c1 = km.loc[1] if 1 in km.index else km.iloc[1]
    c2 = km.loc[2] if 2 in km.index else km.iloc[2]
    k["km_k"]           = 3
    k["km_silhouette"]    = float(r["km_metricas"].loc[r["km_metricas"]["k"] == 3, "silhouette"].values[0])
    k["km_silhouette_k2"] = float(r["km_metricas"].loc[r["km_metricas"]["k"] == 2, "silhouette"].values[0])

    # ML
    xgb_row = r["ml_perf"][r["ml_perf"]["Modelo"] == "XGBoost"]
    rf_row  = r["ml_perf"][r["ml_perf"]["Modelo"] == "Random Forest"]
    k["xgb_r2"]  = float(xgb_row["R²"].values[0])
    k["rf_r2"]   = float(rf_row["R²"].values[0])
    k["xgb_mae"] = float(xgb_row["MAE"].values[0])

    top1 = r["shap_imp"].index[0]
    k["shap_top1"]       = top1
    k["shap_top1_val"]   = float(r["shap_imp"].loc[top1, "SHAP_mean_abs_XGB"])
    k["shap_negro_rank"] = int(r["shap_imp"].reset_index()[
        r["shap_imp"].reset_index()["Feature"].str.contains("Ra", na=False)
    ].index[0]) + 1 if any(r["shap_imp"].reset_index()["Feature"].str.contains("Ra", na=False)) else 6

    # SNA
    sna = r["sna_nos"]
    k["sna_h"]          = P["SNA_H"]
    k["gap_2016"]       = float(r["sna_temporal"].loc[r["sna_temporal"]["Ano"] == 2016, "gap_log"].values[0])
    k["gap_2025"]       = float(r["sna_temporal"].loc[r["sna_temporal"]["Ano"] == 2025, "gap_log"].values[0])
    k["pct_upa_mista_2025"] = float(r["sna_temporal"].loc[r["sna_temporal"]["Ano"] == 2025, "pct_upa_mista"].values[0]) * 100

    bra_between = sna.loc[sna["race"] == "Branco", "betweenness"].max()
    neg_between = sna.loc[sna["race"] == "Negro",  "betweenness"].max()
    k["branco_betweenness_max"] = round(float(bra_between), 4)
    k["negro_betweenness_max"]  = round(float(neg_between), 4)

    return k


# ── Tabelas LaTeX embutidas ───────────────────────────────────────────────────

def hlm_table_latex(r):
    """Tabela HLM compacta para o corpo do texto."""
    hlm = r["hlm"]
    rows_of_interest = [
        "Intercept", "negro", "sexo_fem", "idade_c", "idade_sq",
        "educ_fund_completo", "educ_medio_completo",
        "educ_superior_completo", "educ_pos_graduacao",
        "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
        "pct_negro_uf_z", "tx_desemprego_uf_z", "media_educ_uf_z",
        "sigma2 (Nivel 1)", "tau2_UF (Nivel 3)", "ICC_UF", "N (obs.)", "AIC",
    ]
    keep_rows = [r for r in rows_of_interest if r in hlm.index]
    sub = hlm.loc[keep_rows]

    label_map = {
        "Intercept":             r"Intercepto",
        "negro":                 r"\textbf{Raça (negro)}",
        "sexo_fem":              r"Gênero (feminino)",
        "idade_c":               r"Idade (centralizada)",
        "idade_sq":              r"Idade$^2$ (experiência)",
        "educ_fund_completo":    r"Educ.: Fundamental",
        "educ_medio_completo":   r"Educ.: Médio",
        "educ_superior_completo":r"Educ.: Superior",
        "educ_pos_graduacao":    r"Educ.: Pós-graduação",
        "pct_negro_upa_z":       r"\% Negro na UPA ($z$)",
        "tx_desemprego_upa_z":   r"Desemprego UPA ($z$)",
        "media_educ_upa_z":      r"Educ. média UPA ($z$)",
        "pct_negro_uf_z":        r"\% Negro no Estado ($z$)",
        "tx_desemprego_uf_z":    r"Desemprego Estado ($z$)",
        "media_educ_uf_z":       r"Educ. média Estado ($z$)",
        "sigma2 (Nivel 1)":      r"$\hat{\sigma}^2$ (Nível 1)",
        "tau2_UF (Nivel 3)":     r"$\hat{\tau}^2_{UF}$ (Nível 3)",
        "ICC_UF":                r"$\text{ICC}_{UF}$",
        "N (obs.)":              r"$N$ (observações)",
        "AIC":                   r"AIC",
    }

    cols_hlm = [c for c in ["M0_Nulo", "M1_Individual", "M2_Localidade", "M3_Completo"]
                if c in sub.columns]
    col_headers = {"M0_Nulo": "M0", "M1_Individual": "M1", "M2_Localidade": "M2", "M3_Completo": "M3"}

    sep_rows = {"educ_fund_completo", "pct_negro_upa_z", "pct_negro_uf_z",
                "sigma2 (Nivel 1)"}

    lines = []
    lines.append(r"\begin{longtable}{l" + "c" * len(cols_hlm) + "}")
    lines.append(r"\caption{Modelos HLM de Três Níveis --- Determinantes do Log-Rendimento Mensal "
                 r"por Raça no Brasil (PNAD Contínua, 2016--2025). "
                 r"Coeficientes com erro-padrão entre parênteses; SE clusterizado por UF nos modelos OLS. "
                 r"$^{***}$\,$p<0{,}001$; $^{**}$\,$p<0{,}01$; $^{*}$\,$p<0{,}05$.}"
                 r"\label{tab:hlm_resultados}\\")
    lines.append(r"\toprule")
    header = " & ".join([r"\textbf{Variável}"] + [r"\textbf{" + col_headers[c] + "}" for c in cols_hlm])
    lines.append(header + r" \\")
    lines.append(r"\midrule \endfirsthead")
    lines.append(r"\toprule")
    lines.append(header + r" \\")
    lines.append(r"\midrule \endhead")
    lines.append(r"\midrule \multicolumn{" + str(len(cols_hlm)+1) + r"}{r}{\textit{continua}} \\ \endfoot")
    lines.append(r"\bottomrule \endlastfoot")

    for row_key in keep_rows:
        if row_key in sep_rows:
            lines.append(r"\addlinespace[3pt]")
            if row_key == "educ_fund_completo":
                lines.append(r"\multicolumn{" + str(len(cols_hlm)+1) + r"}{l}{\textit{Controles educacionais}} \\")
            elif row_key == "pct_negro_upa_z":
                lines.append(r"\multicolumn{" + str(len(cols_hlm)+1) + r"}{l}{\textit{Contexto de localidade (Nível 2 --- UPA)}} \\")
            elif row_key == "pct_negro_uf_z":
                lines.append(r"\multicolumn{" + str(len(cols_hlm)+1) + r"}{l}{\textit{Contexto macrorregional (Nível 3 --- UF)}} \\")
            elif row_key == "sigma2 (Nivel 1)":
                lines.append(r"\addlinespace[2pt] \midrule")
                lines.append(r"\multicolumn{" + str(len(cols_hlm)+1) + r"}{l}{\textit{Componentes de variância e ajuste}} \\")

        label = label_map.get(row_key, row_key.replace("_", r"\_"))
        cells = [label]
        for col in cols_hlm:
            val = sub.loc[row_key, col] if col in sub.columns else "—"
            import re as _re
            def _star(m):
                n = len(m.group())
                return r"$^{***}$" if n==3 else (r"$^{**}$" if n==2 else r"$^{*}$")
            val = _re.sub(r"\*{1,3}", _star, str(val))
            cells.append(val)
        lines.append(" & ".join(cells) + r" \\")

    lines.append(r"\end{longtable}")
    return "\n".join(lines)


def shap_table_latex(r):
    imp = r["shap_imp"].copy().reset_index()
    imp = imp.rename(columns={
        "Feature": "Feature",
        "SHAP_mean_abs_RF": r"$|\text{SHAP}|$ RF",
        "SHAP_mean_abs_XGB": r"$|\text{SHAP}|$ XGB",
        "Rank_RF": "Rank RF",
        "Rank_XGB": "Rank XGB",
    })
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Importância SHAP Comparada --- Random Forest e XGBoost. "
        r"Predição de log-rendimento, PNAD 2016--2025 ($N_{\text{SHAP}}=50.000$). "
        r"Valores: $|\text{SHAP}|$ médio. Destaque em negrito: variáveis raciais/contextuais.}",
        r"\label{tab:shap_importance}",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"\textbf{Feature} & \textbf{$|\text{SHAP}|$ RF} & \textbf{Rank RF} "
        r"& \textbf{$|\text{SHAP}|$ XGB} & \textbf{Rank XGB} \\",
        r"\midrule",
    ]
    racial_feats = {"Raça (negro)", "% Negro na UPA", "% Negro no Estado",
                    "Renda média UPA", "Desemprego na UPA", "Desemprego no Estado"}
    col_rf  = r"$|\text{SHAP}|$ RF"
    col_xgb = r"$|\text{SHAP}|$ XGB"
    for _, row in imp.iterrows():
        feat = str(row["Feature"])
        bold = feat in racial_feats
        label = r"\textbf{" + feat.replace("%", r"\%") + "}" if bold else feat.replace("%", r"\%")
        rf_val  = f"{row[col_rf]:.5f}"
        xgb_val = f"{row[col_xgb]:.5f}"
        lines.append(
            f"{label} & {rf_val} & {int(row['Rank RF'])} "
            f"& {xgb_val} & {int(row['Rank XGB'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


def sna_table_latex(r):
    sna = r["sna_nos"][[
        "node", "race", "educ_label", "n_workers", "mean_renda",
        "betweenness", "constraint",
    ]].copy()
    sna = sna.sort_values(["race", "educ_grp"] if "educ_grp" in sna.columns else ["race"])
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Métricas de Rede por Grupo Demográfico (Raça $\times$ Educação). "
        r"PNAD 2016--2025. \textit{Constraint} de Burt: maior valor = maior isolamento estrutural. "
        r"\textit{Betweenness}: capacidade de corretagem entre grupos.}",
        r"\label{tab:sna_metricas}",
        r"\begin{tabular}{llllcccc}",
        r"\toprule",
        r"\textbf{Grupo} & \textbf{Raça} & \textbf{Educação} & \textbf{N} "
        r"& \textbf{log\_Renda} & \textbf{Betweenness} & \textbf{Constraint} \\",
        r"\midrule",
    ]
    for _, row in sna.iterrows():
        # Escapa underscores em TODAS as colunas de texto (ex.: educ_label "Sem_Instrução")
        node = str(row["node"]).replace("_", r"\_")
        race = str(row["race"]).replace("_", r"\_")
        educ = str(row["educ_label"]).replace("_", r"\_")
        high_b = float(row["betweenness"]) > 0
        b_cell = r"\textbf{" + f"{float(row['betweenness']):.3f}" + "}" if high_b else f"{float(row['betweenness']):.3f}"
        lines.append(
            f"{node} & {race} & {educ} & {int(row['n_workers']):,} "
            f"& {float(row['mean_renda']):.3f} & {b_cell} & {float(row['constraint']):.4f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


# ── Gera o documento LaTeX ─────────────────────────────────────────────────────

def build_latex(r, k):
    hlm_tab  = hlm_table_latex(r)
    shap_tab = shap_table_latex(r)
    sna_tab  = sna_table_latex(r)

    # Gap formatado
    gb  = abs(k["gap_bruto_pct"])
    gl  = abs(k["gap_liquido_pct"])
    med = k["mediacao_total"]

    # Variáveis pré-computadas (não podem usar backslash dentro de f-string expressions)
    sna_top_node_latex = P.get("SNA_EXP_BETWN_TOP_NODE", "Branco_Fundamental_Fem").replace("_", "\\_")

    # Random slope — strings pré-computadas
    _rs_disponivel = P.get("RS_TAU2_NEGRO") is not None
    if _rs_disponivel:
        import math as _math
        # Locale pt-BR: usar fmt() (vírgula decimal + sinal U+2212) para todos os
        # valores numéricos, inclusive percentuais — o helper :.1f produzia ponto.
        _rs_lr_str   = fmt(P.get("RS_LRT_LR", 0.0), 1)
        _rs_b_str    = fmt(P.get("RS_B_NEGRO_FIXO", 0.0), 4)
        _rs_gap_str  = fmt(abs(P.get('RS_GAP_PCT', 0.0)), 1)
        _rs_tau2_str = fmt(P.get("RS_TAU2_NEGRO", 0.0), 6)
        _rs_sd_str   = fmt(P.get("RS_SD_NEGRO", 0.0), 4)
        _rs_lo_str   = fmt(P.get('RS_GAP_LO_PCT', 0.0), 1)
        _rs_hi_str   = fmt(P.get('RS_GAP_HI_PCT', 0.0), 1)
        _rs_rho_str  = fmt(P.get("RS_RHO", 0.0), 3)
        _rs_var_str  = fmt(abs(round(P.get('RS_GAP_HI_PCT', 0.0) - P.get('RS_GAP_LO_PCT', 0.0), 1)), 1)
        _rs_amostra  = (f"população completa ($N={fmtN(int(P.get('RS_N_OBS', 0)))}$)"
                        if P.get("RS_SAMPLE_FRAC", 0) >= 0.99
                        else f"amostra {P.get('RS_SAMPLE_FRAC', 0)*100:.0f}\\% ($N={fmtN(int(P.get('RS_N_OBS', 0)))}$)")
        _rs_lrt_block = (
            f"O LRT boundary test \\cite{{stram1994}} rejeita $H_0$ com "
            f"$LR={_rs_lr_str}$, $p<0{{,}}001$: "
            f"o gap racial varia significativamente entre estados. "
            f"O efeito fixo nacional é $\\hat{{\\beta}}_1={_rs_b_str}$ "
            f"(gap de {_rs_gap_str}\\%), com $\\tau^2_1={_rs_tau2_str}$ "
            f"($DP={_rs_sd_str}$ log-pontos). "
            f"Em 95\\% das UFs o gap situa-se em $[{_rs_lo_str}\\%;\\,{_rs_hi_str}\\%]$ "
            f"--- variação de {_rs_var_str} pontos percentuais entre extremos."
        )
        _rs_rho_block = (
            f"A correlação $\\rho(u_0,u_1)={_rs_rho_str}$ é negativa: UFs com maior "
            f"nível salarial médio (intercepto $u_0$ mais alto) exibem penalidade "
            f"racial mais severa (inclinação $u_1$ mais negativa). A discriminação se "
            f"intensifica nas economias mais ricas e desiguais --- e não nas mais "
            f"pobres: as maiores penalidades estimadas por UF concentram-se no Distrito "
            f"Federal, Rio de Janeiro e São Paulo, ao passo que estados do Nordeste "
            f"(RN, PB, SE) registram as menores ($r_{{\\text{{UF}}}}=+0{{,}}45$ entre renda "
            f"média e magnitude do gap)."
            if P.get("RS_RHO", 0) < -0.1 else
            f"A correlação $\\rho(u_0,u_1)={_rs_rho_str}$ é próxima de zero."
        )
    else:
        _rs_lrt_block = "Resultados em processamento --- ver \\texttt{{hlm\\_m3\\_random\\_slope\\_varcov.csv}}."
        _rs_rho_block = ""
        _rs_amostra   = "amostra 20\\%"

    # PO Regional (BLUP MixedLM) — bloco LaTeX pré-computado
    if P.get("RPO_GANHO_B9") is not None:
        _rpo_g3    = fmt(P.get("RPO_GANHO_B3", 0.0), 1)
        _rpo_g9    = fmt(P.get("RPO_GANHO_B9", 0.0), 1)
        _rpo_worst = P.get("RPO_WORST_UF", "DF")
        _rpo_wgap  = fmt(abs(P.get("RPO_WORST_GAP_PCT", 0.0)), 1)
        _rpo_best  = P.get("RPO_BEST_UF", "MG")
        _rpo_bgap  = fmt(abs(P.get("RPO_BEST_GAP_PCT", 0.0)), 1)
        _rpo_top5  = P.get("RPO_TOP5", "")
        _rpo_spear = fmt(P.get("RPO_SPEARMAN", 0.0), 2)
        _rpo_nufs  = P.get("RPO_N_UFS", 27)
        _rpo_block = (
            "\\paragraph{Focalização territorial: Pesquisa Operacional regionalizada.}\n"
            "A inclinação aleatória de \\texttt{negro} por UF (Seção~\\ref{subsec:hlm_rs}) "
            "estabeleceu que a penalidade racial é geograficamente heterogênea. "
            "Traduzimos essa heterogeneidade em alocação ótima de recursos: usando os BLUPs "
            f"do MixedLM como gap específico de cada uma das {_rpo_nufs} UFs, um programa "
            "linear distribui o orçamento priorizando os estados de maior penalidade. "
            "A Tabela~\\ref{tab:po_regional} mostra que concentrar recursos nas UFs mais "
            f"críticas reduz o gap agregado {_rpo_g9}\\% acima da alocação uniforme com "
            f"orçamento intermediário (e {_rpo_g3}\\% quando o orçamento é escasso) --- ganho "
            "decorrente exclusivamente da focalização, mantida constante a efetividade da "
            f"política. As unidades prioritárias ({_rpo_top5}) combinam alta penalidade "
            f"--- liderada por {_rpo_worst} ({_rpo_wgap}\\%) --- e elevada população negra "
            f"afetada, enquanto {_rpo_best} apresenta o menor diferencial ({_rpo_bgap}\\%). "
            "Metodologicamente, a estimação por BLUP é indispensável: a aproximação rápida "
            "por OLS estadual com encolhimento \\textit{empirical Bayes} diverge do BLUP "
            f"(Spearman $\\rho={_rpo_spear}$), pois trata heterogeneamente os coeficientes "
            "de controle --- por isso adotamos o modelo misto completo como base oficial.\n\n"
            "\\begin{figure}[H]\n"
            "  \\centering\n"
            "  \\includegraphics[width=0.70\\textwidth]{outputs/figures/mapa_po_regional.png}\n"
            "  \\caption{Mapa de calor da penalidade racial salarial por UF (BLUP do "
            "\\textit{random slope}). Estados mais escuros indicam maior desvantagem; "
            "$\\bigstar$ marca os estados prioritários para a focalização orçamentária.}\n"
            "  \\label{fig:mapa_po_regional}\n"
            "\\end{figure}\n\n"
            "\\input{outputs/tables/po_regional.tex}\n\n"
            "\\begin{figure}[H]\n"
            "  \\centering\n"
            "  \\includegraphics[width=\\textwidth]{outputs/figures/po_regional.png}\n"
            "  \\caption{Penalidade racial por UF (BLUP do \\textit{random slope}) e ganho da "
            "focalização orçamentária sobre a alocação uniforme (Pesquisa Operacional "
            "regionalizada).}\n"
            "  \\label{fig:po_regional}\n"
            "\\end{figure}\n"
        )
    else:
        _rpo_block = ""

    # GLMM random slope (acesso, lme4) — bloco LaTeX pré-computado
    if P.get("GRS_OCP_OR") is not None:
        _grs_n      = fmtN(int(P.get("GRS_N", 7694198)))
        _grs_ocpor  = fmt(P.get("GRS_OCP_OR", 0.705), 3)
        _grs_t10or  = fmt(P.get("GRS_TOP10_OR", 0.660), 3)
        _grs_tau    = fmt(P.get("GRS_OCP_TAU2", 0.0112), 4)
        _grs_sd     = fmt(P.get("GRS_OCP_SD", 0.106), 3)
        _grs_rho    = fmt(P.get("GRS_OCP_RHO", 0.636), 2)
        _grs_lr1    = fmtN(int(round(P.get("GRS_OCP_LR", 2402.6))))
        _grs_lr2    = fmtN(int(round(P.get("GRS_TOP20_LR", 321.7))))
        _grs_lr3    = fmtN(int(round(P.get("GRS_TOP10_LR", 501.7))))
        _grs_pubor  = fmt(P.get("GRS_PUB_OR", 0.705), 3)
        _grs_privor = fmt(P.get("GRS_PRIV_OR", 0.695), 3)
        _grs_pubt   = fmt(P.get("GRS_PUB_TAU2", 0.0114), 4)
        _grs_privt  = fmt(P.get("GRS_PRIV_TAU2", 0.0107), 4)
        _grs_block = (
            f"Estendeu-se o \\textit{{random slope}} de \\texttt{{negro}} ao GLMM logístico de "
            f"acesso (\\texttt{{lme4::glmer}}, população completa, $N={_grs_n}$), em três desfechos. "
            f"O LRT de fronteira rejeita $H_0{{\\colon}}\\,\\tau^2_1=0$ em todos --- "
            f"\\texttt{{ocp\\_qualif}} ($LR={_grs_lr1}$), \\texttt{{y\\_top20}} ($LR={_grs_lr2}$) e "
            f"\\texttt{{y\\_top10}} ($LR={_grs_lr3}$), todos $p<0{{,}}001$: a barreira de acesso "
            f"também varia geograficamente. A heterogeneidade é maior no acesso a ocupações "
            f"qualificadas ($\\tau^2_1={_grs_tau}$, $DP={_grs_sd}$ log-odds) e preserva o gradiente "
            f"de teto de vidro no efeito fixo (OR cai de {_grs_ocpor} para {_grs_t10or} rumo ao "
            f"decil superior).\n\n"
            f"Em contraste com o salário ($\\rho=-0{{,}}37$), o acesso a cargos qualificados "
            f"correlaciona-se \\emph{{positivamente}} com o nível ocupacional do estado "
            f"($\\rho={_grs_rho}$): UFs com mais empregos qualificados exibem \\emph{{menor}} "
            f"penalidade de acesso --- nas economias desenvolvidas, negros enfrentam acesso "
            f"relativamente mais fácil, porém maior gap salarial uma vez dentro.\n\n"
            f"\\textbf{{Setor público {{\\texttimes}} privado.}} A barreira de acesso é praticamente "
            f"idêntica (OR$_{{\\text{{púb}}}}={_grs_pubor}$ vs OR$_{{\\text{{priv}}}}={_grs_privor}$) "
            f"e igualmente heterogênea entre UFs ($\\tau^2={_grs_pubt}$ vs ${_grs_privt}$): o concurso "
            f"público \\emph{{não dissolve}} a exclusão racial de acesso a ocupações qualificadas.\n\n"
            f"\\begin{{figure}}[H]\n  \\centering\n"
            f"  \\includegraphics[width=\\textwidth]{{outputs/figures/glmm_rs_real.png}}\n"
            f"  \\caption{{Random slope GLMM (\\texttt{{lme4}}): Odds Ratio de \\texttt{{negro}} por "
            f"UF em cada desfecho de acesso e por setor. Dispersão entre UFs = heterogeneidade "
            f"geográfica (BLUP); OR$<$1 = barreira.}}\n  \\label{{fig:glmm_rs}}\n\\end{{figure}}\n"
        )
    else:
        _grs_block = ""

    # HLM random slope estendido (setor salário + gênero) — strings pré-computadas
    if P.get("HRS_PUB_GAP_PCT") is not None:
        _hrs_priv  = fmt(abs(P.get("HRS_PRIV_GAP_PCT", 11.2)), 1)
        _hrs_pub   = fmt(abs(P.get("HRS_PUB_GAP_PCT", 7.8)), 1)
        _hrs_privt = fmt(P.get("HRS_PRIV_TAU2", 0.00218), 5)
        _hrs_pubt  = fmt(P.get("HRS_PUB_TAU2", 0.0014), 5)
        _hrs_setor_block = (
            f"Já no \\emph{{salário}}, o setor público \\emph{{atenua}} o gap racial "
            f"({_hrs_pub}\\% vs {_hrs_priv}\\% no privado) e o \\emph{{homogeneíza}} entre UFs "
            f"($\\tau^2_1={_hrs_pubt}$ vs ${_hrs_privt}$). O concurso equaliza a "
            f"\\emph{{remuneração}} de quem entra, mas não a \\emph{{entrada}} --- precisando o "
            f"diagnóstico ``o Estado ajuda, mas não resolve''."
        )
    else:
        _hrs_setor_block = ""

    if P.get("HRS_GEN_LR") is not None:
        _hg_lr    = fmtN(int(round(P.get("HRS_GEN_LR", 15774.9))))
        _hg_sdneg = fmt(P.get("HRS_GEN_SD_NEGRO", 0.0495), 3)
        _hg_sdsex = fmt(P.get("HRS_GEN_SD_SEXO", 0.0641), 3)
        _hg_rho   = fmt(P.get("HRS_GEN_RHO", -0.456), 2)
        _hgen_block = (
            f"\\medskip\n\\noindent\\textbf{{Nível adicional --- gênero.}} "
            f"Estendendo o \\textit{{random slope}} a \\texttt{{sexo\\_fem}} "
            f"($(1+\\text{{negro}}+\\text{{sexo\\_fem}}\\mid \\text{{UF}})$), o LRT confirma que o "
            f"gap salarial de gênero também varia geograficamente ($LR={_hg_lr}$, $p<0{{,}}001$) "
            f"--- com \\emph{{maior}} dispersão que o racial ($DP_{{\\text{{gênero}}}}={_hg_sdsex}$ "
            f"vs $DP_{{\\text{{raça}}}}={_hg_sdneg}$ log-pontos). A correlação entre as duas "
            f"inclinações é negativa ($\\rho={_hg_rho}$): nas UFs de maior penalidade racial, a de "
            f"gênero tende a ser menor (discriminações geograficamente compensatórias)."
        )
    else:
        _hgen_block = ""

    # GLMM random slope de GÊNERO (lme4) — bloco LaTeX pré-computado
    if P.get("GGE_OCP_OR") is not None:
        _gge_ocp  = fmt(P.get("GGE_OCP_OR", 2.01), 2)
        _gge_t20  = fmt(P.get("GGE_TOP20_OR", 0.567), 3)
        _gge_t10  = fmt(P.get("GGE_TOP10_OR", 0.522), 3)
        _gge_t20t = fmt(P.get("GGE_TOP20_TAU2", 0.0324), 4)
        _gge_block = (
            f"\\medskip\n\\noindent\\textbf{{Gênero no acesso.}} O mesmo \\textit{{random slope}} "
            f"aplicado a \\texttt{{sexo\\_fem}} no GLMM confirma heterogeneidade geográfica em todos "
            f"os desfechos ($p<0{{,}}001$), revelando uma divergência ausente no caso racial: mulheres "
            f"têm \\emph{{mais}} acesso a ``ocupações qualificadas'' (OR$={_gge_ocp}>1$, por profissões "
            f"credenciadas feminizadas), mas \\emph{{muito menos}} acesso ao topo da renda "
            f"(OR$_{{\\text{{top20}}}}={_gge_t20}$; OR$_{{\\text{{top10}}}}={_gge_t10}$). O teto de vidro "
            f"de gênero é de \\emph{{remuneração}}, não de categoria ocupacional --- e sua "
            f"heterogeneidade geográfica supera a racial no topo ($\\tau^2_{{\\text{{sexo}}}}={_gge_t20t}$ "
            f"no top20, contra $\\tau^2_{{\\text{{negro}}}}\\approx0{{,}}003$; cerca de 10$\\times$).\n\n"
            f"\\begin{{figure}}[H]\n  \\centering\n"
            f"  \\includegraphics[width=\\textwidth]{{outputs/figures/glmm_genero_real.png}}\n"
            f"  \\caption{{Random slope GLMM de gênero (\\texttt{{lme4}}): OR de \\texttt{{sexo\\_fem}} "
            f"por UF em cada desfecho. OR$>$1 = vantagem feminina na categoria; OR$<$1 = desvantagem "
            f"na renda (teto de vidro de remuneração).}}\n  \\label{{fig:glmm_genero}}\n\\end{{figure}}\n"
        )
    else:
        _gge_block = ""

    doc = rf"""% !TeX encoding = UTF-8
% !TeX program  = pdflatex
%
% relatorio_tcc.tex
% Relatório Final — TCC de MBA
% Escola Superior de Agricultura "Luiz de Queiroz" — ESALQ/USP
% Compilar: pdflatex → bibtex → pdflatex → pdflatex
% Ou: Upload em Overleaf (recomendado)
%
\documentclass[12pt, a4paper, oneside]{{article}}

% ── Encoding e língua ─────────────────────────────────────────────────────────
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[brazil]{{babel}}
\usepackage{{lmodern}}

% ── Layout ────────────────────────────────────────────────────────────────────
\usepackage[top=3cm, bottom=2cm, left=3cm, right=2cm]{{geometry}}
\usepackage{{setspace}}
\onehalfspacing
\usepackage{{indentfirst}}
\setlength{{\parindent}}{{1.25cm}}

% ── Matemática ────────────────────────────────────────────────────────────────
\usepackage{{amsmath, amssymb, amsthm}}

% ── Figuras e tabelas ─────────────────────────────────────────────────────────
\usepackage{{graphicx}}
\usepackage{{float}}
\usepackage{{booktabs}}
\usepackage{{longtable}}
\usepackage{{multirow}}
\usepackage{{tabularx}}
\usepackage{{caption}}
\usepackage{{subcaption}}
\usepackage{{xcolor}}
\usepackage{{array}}

% ── Referências ───────────────────────────────────────────────────────────────
\usepackage[alf, abnt-etal-list=5]{{abntex2cite}}

% Unicode minus sign (U+2212) → LaTeX math minus
\DeclareUnicodeCharacter{{2212}}{{$-$}}

% Compatibility: abntex2cite with article class
\makeatletter
\providecommand{{\abntnextkey}}{{}}
\makeatother

% ── Hiperlinks ───────────────────────────────────────────────────────────────
\usepackage[colorlinks=true, linkcolor=black, citecolor=black, urlcolor=blue]{{hyperref}}

% ── Caminho das figuras ───────────────────────────────────────────────────────
\graphicspath{{{{outputs/figures/}}}}

\begin{{document}}

% ══════════════════════════════════════════════════════════════════════════════
%  CAPA
% ══════════════════════════════════════════════════════════════════════════════
\begin{{titlepage}}
\centering
\vspace*{{1cm}}

\IfFileExists{{logo_esalq.pdf}}{{\includegraphics[width=4cm]{{logo_esalq}}}}{{%
  \framebox[4cm]{{\rule{{0pt}}{{1.5cm}}\textit{{Logo ESALQ}}}}%
}}

\vspace{{1.5cm}}
{{\Large \textbf{{ESCOLA SUPERIOR DE AGRICULTURA ``LUIZ DE QUEIROZ''\\
UNIVERSIDADE DE SÃO PAULO}}}}

\vspace{{1cm}}
{{\large MBA em Data Science e Analytics}}

\vspace{{3cm}}

{{\LARGE \textbf{{RACISMO ESTRUTURAL NO MERCADO DE TRABALHO BRASILEIRO:
UMA ABORDAGEM MULTINÍVEL, DE MACHINE LEARNING, REDES SOCIAIS
E PESQUISA OPERACIONAL COM DADOS DA PNAD CONTÍNUA (2016--2025)}}}}

\vspace{{3cm}}

{{\large \textbf{{Ricardo Calheiros}}}}

\vfill

{{\large Piracicaba, 2026}}
\end{{titlepage}}

\newpage

% ══════════════════════════════════════════════════════════════════════════════
%  RESUMO
% ══════════════════════════════════════════════════════════════════════════════
\begin{{abstract}}
\noindent
Este trabalho investiga o \textit{{gap}} salarial racial e as barreiras
estruturais à progressão de carreira de profissionais negros no Brasil,
combinando econometria multinível, \textit{{machine learning}} e análise de
redes sociais sobre a série histórica completa da Pesquisa Nacional por
Amostra de Domicílios Contínua (PNAD Contínua) de 2016 a 2025, com
15,9~milhões de observações brutas.

Um modelo de regressão multinível de três níveis (indivíduo, UPA e Unidade
da Federação) estima que profissionais negros recebem, em média,
{gb:.1f}\% a menos que brancos comparáveis em escolaridade, sexo e faixa etária.
Desse diferencial bruto, {med:.1f}\% é mediado pelo contexto de moradia
(\textit{{networking}} local, Nível~2), reduzindo o \textit{{gap}} líquido
--- atribuível à discriminação direta --- a {gl:.1f}\%.

A análise de agrupamento (\textit{{K-Means}}, $k=3$) segrega a força de trabalho
em três tipologias socioeconomicamente distintas e racialmente homogêneas,
com trabalhadores negros concentrados nos grupos de menor rendimento e as
mulheres negras formando um cluster de dupla desvantagem (raça \textit{{e}}
gênero).

Modelos de \textit{{Random Forest}} e XGBoost com valores SHAP confirmam que
a renda média da UPA é o preditor mais importante do rendimento individual
($|\text{{SHAP}}| = {k['shap_top1_val']:.3f}$), seguida de gênero e escolaridade superior,
com a variável racial ocupando o {k['shap_negro_rank']}$^\circ$ lugar mesmo após
controlar por todos os demais fatores.

A análise de redes sociais revela que grupos negros possuem
\textit{{betweenness centrality}} nula em todos os níveis educacionais,
enquanto grupos brancos de escolaridade fundamental e pós-graduação
funcionam como \textit{{brokers}} da rede de co-residência --- evidência
de que a conversão de capital humano em renda depende de capital social
estruturalmente negado a trabalhadores negros.

A pesquisa operacional traduz esses achados em recomendações concretas:
o método TOPSIS ranqueia seis políticas públicas avaliadas em cinco
critérios simultâneos, apontando as Cotas Ocupacionais CBO~1--4 como
política dominante (CC~$={fmt(P["TOPSIS_P1_CC"],4)}$), seguida da
Equidade Educacional (CC~$={fmt(P["TOPSIS_P2_CC"],4)}$).
A programação linear indica que uma alocação ótima de R\$5~bilhões,
priorizando os três canais de maior efetividade, reduziria o
\textit{{gap}} salarial racial em {fmt(P["PL1_B5_PCT"],1)}\%.

\bigskip
\noindent\textbf{{Palavras-chave:}} gap salarial racial; discriminação estrutural; modelos
hierárquicos lineares; SHAP values; análise de redes sociais; pesquisa
operacional; TOPSIS; programação linear; políticas públicas; PNAD Contínua.
\end{{abstract}}

\newpage

% ══════════════════════════════════════════════════════════════════════════════
%  ABSTRACT (English)
% ══════════════════════════════════════════════════════════════════════════════
\renewcommand{{\abstractname}}{{Abstract}}
\begin{{abstract}}
\noindent
This study investigates the racial wage gap and structural barriers to career
progression for Black professionals in Brazil using a multilevel, machine
learning, and social network analysis framework applied to the full historical
series of Brazil's Continuous National Household Sample Survey (PNAD Contínua)
from 2016 to 2025 (15.9~million raw observations).

A three-level hierarchical linear model (individual, census tract, and state)
estimates that Black workers earn {gb:.1f}\% less than comparable White
workers after controlling for education, sex, and age experience.
Of this gross differential, {med:.1f}\% is mediated by residential context
(local networking, Level~2), leaving a residual \textit{{net gap}} of
{gl:.1f}\% attributable to direct labour market discrimination.

K-Means clustering ($k=3$) reveals three racially homogeneous
socioeconomic typologies, with Black workers concentrated in lower-income
segments and Black women forming a dual-disadvantage cluster at the
intersection of race and gender.

Random Forest and XGBoost models with SHAP values confirm that neighbourhood
income is the most important predictor of individual earnings
($|\text{{SHAP}}|={k['shap_top1_val']:.3f}$), while race ranks
{k['shap_negro_rank']}$^\text{{th}}$ even after all controls.

Social network analysis shows that Black groups have zero betweenness
centrality regardless of education level, whereas White groups serve as
brokers in the co-residence network, suggesting that the conversion of
human capital into earnings depends on social capital that is structurally
denied to Black workers.

An operations research module translates these findings into policy
recommendations. A TOPSIS multicriteria ranking of six public policies
across five criteria identifies occupational quotas for CBO groups~1--4
as the dominant policy (CC~$={fmt(P["TOPSIS_P1_CC"],4)}$), followed by
educational equity (CC~$={fmt(P["TOPSIS_P2_CC"],4)}$). Linear programming
shows that an optimal R\$5-billion allocation would reduce the racial
wage gap by {fmt(P["PL1_B5_PCT"],1)}\%.

\bigskip
\noindent\textbf{{Keywords:}} racial wage gap; structural discrimination;
hierarchical linear models; SHAP values; social network analysis;
operations research; TOPSIS; linear programming; public policy; PNAD Contínua.
\end{{abstract}}

\newpage
\tableofcontents
\newpage

% ══════════════════════════════════════════════════════════════════════════════
%  1. INTRODUÇÃO
% ══════════════════════════════════════════════════════════════════════════════
\section{{Introdução}}
\label{{sec:intro}}

\begin{{quote}}
\textbf{{Este trabalho comprova que o racismo no mercado de trabalho brasileiro
não opera como um evento isolado de discriminação salarial --- opera como
um sistema de barreiras em camadas que começa antes do primeiro salário,
persiste ao longo de toda a trajetória profissional e se perpetua via
exclusão das redes que convertem educação em mobilidade.
Políticas baseadas apenas em aumento de escolaridade são, portanto,
necessárias, mas estruturalmente insuficientes.}}
\end{{quote}}

O Brasil é um dos países com maior desigualdade racial de renda no mundo.
Segundo a PNAD Contínua, a razão entre o rendimento médio de trabalhadores
brancos e negros permanece acima de 1{{:}}1,5 ao longo de toda a série
histórica disponível, persistindo mesmo quando se controlam escolaridade,
experiência e setor de atividade~\cite{{ibge_pnad_2023}}.
A desigualdade racial no mercado de trabalho brasileiro é, portanto,
não apenas uma herança colonial, mas um fenômeno reproduzido ativamente
por mecanismos que a abordagem tradicional de diferenças de capital humano
não é capaz de capturar~\cite{{hasenbalg1979}}.

Esse hiato convive com um quadro macroestrutural recente de \textbf{{avanço social
com desigualdade persistente}}. De um lado, a qualidade de vida avançou: entre as
edições 2008 e 2018 da Pesquisa de Orçamentos Familiares (POF), o Índice de Perda
de Qualidade de Vida recuou cerca de 30\%~\cite{{ibge_pof_2019}}. A melhora, porém,
foi proporcional entre os grupos e \emph{{não}} fechou o hiato racial nem o
territorial: famílias chefiadas por pessoas pretas ou pardas mantêm índice de
0{{,}}183, contra 0{{,}}122 das brancas, e o Nordeste (0{{,}}207) e o Norte
(0{{,}}223) seguem muito acima do Sul (0{{,}}114). De outro lado, no rendimento, a
desigualdade voltou a crescer: o Gini do rendimento domiciliar \emph{{per capita}}
subiu de 0{{,}}487 (2024) para 0{{,}}491 (2025), puxado pelo distanciamento do topo
--- a renda dos 10\% mais ricos cresceu 8{{,}}7\% no ano, contra 3{{,}}1\% dos 10\%
mais pobres~\cite{{ibge_rendimentos_2025}}. É precisamente esse padrão --- progresso
agregado que não dissolve a barreira racial --- que este trabalho disseca no
mercado de trabalho.

A literatura empírica contemporânea identifica três canais principais de
reprodução dessa desigualdade: (i)~discriminação direta, isto é, diferenças
de tratamento em processos de seleção e promoção com características
individuais observadas~\cite{{pager2007}}; (ii)~segregação residencial e
seus efeitos sobre o capital social disponível ao trabalhador
--- o contexto do bairro define a qualidade das redes de indicação
profissional~\cite{{wilson1987, sampson1997}}; e (iii)~subvalorização
sistêmica do capital humano negro, pela qual um dado nível de escolaridade
gera retornos financeiros menores para trabalhadores negros do que para
brancos~\cite{{hasenbalg1979, pager2007}}.

Este trabalho avança sobre a literatura nacional ao integrar três
metodologias complementares --- econometria multinível, \textit{{machine learning}}
interpretável e análise de redes sociais --- sobre a maior base de dados
longitudinal disponível no Brasil para este tema, a PNAD Contínua em sua
série completa de 2016 a 2025.

\subsection{{Hipóteses}}
\label{{subsec:hipoteses}}

\begin{{enumerate}}
  \item[\textbf{{H1}}] \textbf{{Gap racial bruto e líquido:}}
    Profissionais negros apresentam rendimento inferior ao de brancos
    comparáveis após controlar por escolaridade, experiência potencial
    e gênero --- e esse diferencial persiste após a adição de controles
    contextuais de nível de bairro e de estado.

  \item[\textbf{{H2}}] \textbf{{Mediação pelo networking local:}}
    Uma fração significativa do \textit{{gap}} racial bruto é explicada
    pelo contexto socioeconômico do local de moradia (composição racial da
    UPA, desemprego local, nível educacional médio do entorno) ---
    capturando os efeitos indiretos da segregação residencial sobre a renda.

  \item[\textbf{{H3}}] \textbf{{Tipologias de vulnerabilidade alinhadas com raça:}}
    Métodos de agrupamento não-supervisionados identificam clusters
    socioeconômicos que se sobrepõem a fronteiras raciais, com trabalhadores
    negros concentrados nos segmentos de maior vulnerabilidade.

  \item[\textbf{{H4}}] \textbf{{Importância residual da raça nos modelos preditivos:}}
    Mesmo após controlar por educação, experiência, gênero e contexto de
    moradia, a variável racial mantém relevância preditiva independente,
    conforme medida pelos valores SHAP dos modelos de \textit{{gradient boosting}}.

  \item[\textbf{{H5}}] \textbf{{Isolamento estrutural na rede de co-residência:}}
    Grupos negros ocupam posições periféricas na rede demográfica de
    co-residência, com menor capacidade de corretagem (\textit{{brokerage}})
    entre grupos do que seus pares brancos de mesma escolaridade, o que
    limita a conversão do capital humano em rendimento.
\end{{enumerate}}

% ══════════════════════════════════════════════════════════════════════════════
%  2. REVISÃO DE LITERATURA
% ══════════════════════════════════════════════════════════════════════════════
\section{{Revisão de Literatura}}
\label{{sec:revisao}}

\subsection{{Desigualdade racial no mercado de trabalho brasileiro}}

\citeonline{{hasenbalg1979}} demonstrou pioneiramente que a desigualdade racial
no Brasil não decorre apenas de diferenças históricas de acesso à educação,
mas de mecanismos ativos de discriminação no mercado de trabalho que
convertem desvantagens sociais em desvantagens econômicas de forma cumulativa.
Trabalhos posteriores~\cite{{henriques2001, soares2009}} confirmaram a
persistência dessas diferenças mesmo após controlar por escolaridade,
reforçando a hipótese de discriminação estrutural.

\subsection{{Efeitos de vizinhança e segregação residencial}}

\citeonline{{wilson1987}} propôs a hipótese da \textit{{concentrated disadvantage}}:
a concentração de pobreza em bairros racialmente segregados amplifica
desvantagens individuais por meio da redução de redes de contato com
o mercado de trabalho formal, degradação de serviços públicos e aumento
da violência. \citeonline{{sampson1997}} forneceu evidência empírica para essa
hipótese em contexto norte-americano, e estudos brasileiros encontraram
padrões similares para as regiões metropolitanas~\cite{{marques2010}}.

A abordagem de \textit{{networking}} local, operacionalizada neste trabalho
pelo segundo nível do modelo hierárquico (UPA), testa se o contexto
socioeconômico do bairro exerce efeito independente sobre o rendimento
após controlar por características individuais --- o chamado
\textit{{duplo disadvantage}} de ser negro \textit{{e}} morar em bairros negros.

\subsection{{Modelos lineares hierárquicos para dados aninhados}}

\citeonline{{raudenbush2002}} sistematizaram a fundamentação estatística dos
modelos lineares hierárquicos (HLM), tornando-os o padrão metodológico para
análise de dados com estrutura aninhada (indivíduos dentro de bairros dentro
de estados). Esses modelos permitem decompor a variância do desfecho em
componentes de cada nível e estimar os efeitos contextuais
controlando simultaneamente pelos efeitos individuais.

\subsection{{Interpretabilidade em machine learning: SHAP values}}

\citeonline{{lundberg2017}} propuseram os \textit{{SHapley Additive exPlanations}}
(SHAP), unificando importância de variáveis, efeitos parciais e explicações
individuais em uma única estrutura axiomática baseada na teoria dos jogos
cooperativos. Para dados socioeconômicos, SHAP permite responder à pergunta:
``quanto e em que direção a raça de um indivíduo específico afeta a predição
de sua renda?'' --- uma contribuição metodológica que complementa e enriquece
a interpretação dos coeficientes do HLM.

\subsection{{Análise de redes sociais e capital social}}

\citeonline{{granovetter1973}} demonstrou que \textit{{laços fracos}} ---
conexões entre indivíduos de grupos sociais distintos --- são os principais
canais de transmissão de informações sobre oportunidades profissionais.
\citeonline{{burt2004}} formalizou o conceito de \textit{{buraco estrutural}}:
indivíduos que conectam grupos desconexos obtêm vantagens relacionais
(acesso antecipado a vagas, mentoria, promoções). Aplicado à questão racial,
a SNA permite investigar se trabalhadores negros ocupam as posições de rede
que possibilitam o aproveitamento dessas vantagens.

% ══════════════════════════════════════════════════════════════════════════════
%  3. DADOS E METODOLOGIA
% ══════════════════════════════════════════════════════════════════════════════
\section{{Dados e Metodologia}}
\label{{sec:metodologia}}

\subsection{{Base de dados: PNAD Contínua (2016--2025)}}

A PNAD Contínua é uma pesquisa amostral de domicílios conduzida
trimestralmente pelo IBGE, com cobertura nacional e metodologia de painel
rotativo. O microdado contém informações sobre características demográficas,
escolaridade, inserção no mercado de trabalho e rendimentos para todos os
moradores dos domicílios selecionados. Para este trabalho, foram processados
todos os 40~trimestres disponíveis de 2016T1 a 2025T4, totalizando
15.941.675~observações brutas, das quais {fmtN(P['N_GLMM'])} possuem renda positiva
declarada e completude nas variáveis do modelo.

A classificação racial segue o critério binário adotado pelos estudos
de desigualdade racial no Brasil: \textit{{negro}} = preto (código~2) +
pardo (código~4); \textit{{branco}} = branco (código~1), ambos da variável
V2010 (cor ou raça autodeclarada).

\subsection{{Modelo Linear Hierárquico de Três Níveis}}
\label{{subsec:hlm}}

O modelo parte da equação de Mincer estendida para o log-rendimento
mensal de trabalho, estruturada em três níveis:

\paragraph{{Nível 1 --- Indivíduo ($i$) dentro da UPA ($j$) no Estado ($k$):}}
\begin{{equation}}
  \ln(W)_{{ijk}} = \beta_{{0jk}}
    + \beta_1 \cdot \text{{Negro}}_{{ijk}}
    + \beta_2 \cdot \text{{Sexo}}_{{ijk}}
    + \beta_3 \cdot X_{{ijk}}
    + \beta_4 \cdot X^2_{{ijk}}
    + \sum_{{e=1}}^{{4}} \beta_{{e+4}} \cdot \text{{Educ}}_e
    + \varepsilon_{{ijk}}, \quad \varepsilon \sim \mathcal{{N}}(0,\sigma^2)
  \label{{eq:nivel1}}
\end{{equation}}

\paragraph{{Nível 2 --- Localidade ($j$, proxy de bairro via UPA):}}
\begin{{equation}}
  \beta_{{0jk}} = \gamma_{{00k}}
    + \gamma_{{01}} \cdot \overline{{\%\text{{Negro}}}}_{{jk}}
    + \gamma_{{02}} \cdot \overline{{\text{{Desemprego}}}}_{{jk}}
    + \gamma_{{03}} \cdot \overline{{\text{{Educ}}}}_{{jk}}
    + u_{{0jk}}, \quad u_{{0j}} \sim \mathcal{{N}}(0, \tau^2_u)
  \label{{eq:nivel2}}
\end{{equation}}

O coeficiente $\gamma_{{01}} < 0$ constitui evidência de \textit{{duplo disadvantage}}:
morar em bairros com maior concentração de negros reduz o rendimento
\textit{{independentemente}} da raça individual.

\paragraph{{Nível 3 --- Estado ($k$, UF):}}
\begin{{equation}}
  \gamma_{{00k}} = \delta_{{000}}
    + \delta_1 \cdot Z_k^{{\%\text{{negro}}}}
    + \delta_2 \cdot Z_k^{{\text{{desemprego}}}}
    + \delta_3 \cdot Z_k^{{\text{{educ}}}}
    + v_{{00k}}, \quad v_{{00k}} \sim \mathcal{{N}}(0, \tau^2_v)
  \label{{eq:nivel3}}
\end{{equation}}

Em um modelo de três níveis, o ICC completo é:
\begin{{equation}}
  \rho_{{UF}} = \frac{{\tau^2_{{UF}}}}{{\tau^2_{{UF}} + \tau^2_{{UPA}} + \sigma^2}}
  \label{{eq:icc}}
\end{{equation}}
onde $\tau^2_{{UF}}$ é a variância entre estados, $\tau^2_{{UPA}}$ a variância
entre UPAs e $\sigma^2$ a variância residual intraindividual.
Valores $\rho_{{UF}} > 0{{,}}05$ justificam a inclusão do nível~3 no modelo
\cite{{raudenbush2002}}.

Os efeitos de localidade (UPA) são modelados como \textit{{interceptos fixos}}
--- estratégia computacionalmente viável para 41.517 grupos e apropriada quando
o interesse reside em controlar heterogeneidade não observada de cada UPA,
sem necessidade de estimar a distribuição dos efeitos aleatórios de UPA.
Nessa especificação, $\tau^2_{{UPA}}$ não é estimado separadamente e a
fórmula do ICC de Nível~3 reduz-se a $\rho_{{UF}} = \tau^2_{{UF}} / (\tau^2_{{UF}} + \sigma^2)$,
reportada nas tabelas deste trabalho.
A estimação utiliza REML com método de Powell
para evitar colapso de variância na fronteira $\tau^2=0$.

\subsection{{Clustering Socioeconômico (K-Means)}}

O algoritmo \textit{{MiniBatchKMeans}} foi aplicado sobre as
$N={fmtN(P['N_GLMM'])}$ observações da PEA completa com variáveis contextuais
disponíveis, usando 12~dimensões padronizadas: idade, três dummies de
escolaridade (ensino médio completo, superior completo, pós-graduação),
log-rendimento, raça, gênero, status de emprego e quatro variáveis de
contexto da UPA. O número ótimo de clusters foi determinado pelo
\textit{{Silhouette Coefficient}} \cite{{rousseeuw1987}} com validação
pelo índice de Davies-Bouldin \cite{{davies_bouldin1979}}.
Para $k=2$: $S={fmt(P['KM_SILH_K2'],4)}$, $DB={fmt(P['KM_DB_K2'],4)}$;
para $k=3$: $S={fmt(P['KM_SILH_K3'],4)}$, $DB={fmt(P['KM_DB_K3'],4)}$.
Ambos os critérios automáticos favorecem $k=2$; $k=3$ foi adotado por
interpretabilidade substantiva superior \cite{{ketchen1996}}, uma vez que
a solução binária reproduz trivialmente a clivagem racial sem discriminar
segmentos ocupacionais internos.

\subsection{{Random Forest, XGBoost e SHAP Values}}

Para predição do log-rendimento, foram ajustados dois modelos de ensemble:
(i)~\textit{{Random Forest}} \cite{{breiman2001}} com 200 árvores e profundidade
máxima 10; e (ii)~\textit{{XGBoost}} \cite{{chen2016}} com 300 iterações,
$\text{{lr}}=0{{,}}05$ e regularização $L_1/L_2$. Sobre o modelo XGBoost,
foi aplicado o \textit{{TreeExplainer}} da biblioteca SHAP
\cite{{lundberg2017}} sobre um subsample de 50.000 observações para
calcular os valores de Shapley de cada feature.

\subsection{{Análise de Redes Sociais (SNA)}}

A rede demográfica expandida foi construída com $N_{{nós}}={P.get('SNA_EXP_N_NOS', 20)}$~nós,
representando as combinações de raça~$\times$~educação~$\times$~gênero
(2 raças $\times$ 5 níveis $\times$ 2 gêneros), e arestas ponderadas
pelo índice de Jaccard de co-presença em UPAs:
\begin{{equation}}
  w_{{AB}} = \frac{{|\mathcal{{U}}_A \cap \mathcal{{U}}_B|}}
                   {{|\mathcal{{U}}_A \cup \mathcal{{U}}_B|}}
  \label{{eq:jaccard}}
\end{{equation}}
onde $\mathcal{{U}}_A$ é o conjunto de UPAs com trabalhadores do grupo~$A$.
A expansão para 20~nós acrescenta a dimensão de gênero, aumentando a
robustez das métricas de centralidade e permitindo detectar posições de
\textit{{brokerage}} por subgrupo interseccional (raça~$\times$~gênero).
As métricas de rede incluem centralidade de grau, \textit{{betweenness}},
\textit{{clustering coefficient}} e \textit{{constraint}} de Burt~\cite{{burt2004}}.

\paragraph{{Escopo macroestrutural da rede.}}
Cabe uma delimitação conceitual: a PNAD Contínua não registra vínculos sociais
interpessoais, de modo que esta não é uma rede de \textit{{indivíduos}}, mas de
\textbf{{grupos demográficos}}. Os nós agregam estratos de raça, escolaridade e
gênero, e as arestas medem \textit{{co-residência}} na mesma UPA --- o substrato
territorial sobre o qual as redes interpessoais efetivamente se formam. Em
consequência, \textit{{betweenness}} e \textit{{constraint}} devem ser
interpretados como \textbf{{posição estrutural de grupos}} no espaço da
segregação residencial, e não como intermediação interpessoal medida. A SNA aqui
não substitui um estudo de laços egocêntricos; ela revela o \textit{{andaime
macroestrutural}} que condiciona, a montante, quem tem acesso a quais círculos
--- complementando, e não duplicando, as barreiras de acesso (GLMM) e de
remuneração (HLM).

% ══════════════════════════════════════════════════════════════════════════════
%  4. RESULTADOS
% ══════════════════════════════════════════════════════════════════════════════
\section{{Resultados}}
\label{{sec:resultados}}

As evidências deste capítulo estão organizadas em três camadas de exclusão
--- três barreiras que operam em sequência e se reforçam mutuamente.
O leitor não encontrará aqui um catálogo de modelos estatísticos:
encontrará a trajetória de um trabalhador negro no mercado de trabalho
brasileiro, documentada com rigor empírico em cada etapa.

\begin{{table}}[ht]
\centering
\caption{{Mapa das três camadas de exclusão racial --- guia de leitura}}
\label{{tab:mapa_barreiras}}
\begin{{tabularx}}{{\textwidth}}{{|l|X|}}
\hline
\textbf{{Camada}} & \textbf{{Pergunta central e evidência}} \\
\hline
\textbf{{BARREIRA I}} & Por que negros raramente chegam às ocupações de \\
\textbf{{Acesso e Segregação}} & prestígio? GLMM ($N={fmtN(P['N_GLMM'])}$), HLM contextual e segregação \\
 & espacial mostram que a exclusão começa antes do salário. \\
\hline
\textbf{{BARREIRA II}} & Para os que superam a barreira de entrada --- qual é o \\
\textbf{{Penalidade e Teto de Vidro}} & custo de ser negro? Gap residual de {k['gap_m4']:.1f}\% após 23 controles, \\
 & crescendo nos quantis mais altos (KB-test $p<0{{,}}001$). \\
\hline
\textbf{{BARREIRA III}} & Por que educação, sozinha, não quebra o ciclo? \\
\textbf{{Isolamento Estrutural}} & Redes sociais com betweenness nulo para todos os grupos \\
 & negros: capital social transita exclusivamente por atores brancos. \\
\hline
\end{{tabularx}}
\end{{table}}

\medskip

Cada seção a seguir prova empiricamente uma dessas camadas.
Nenhum método isolado teria identificado o sistema como um todo.

\noindent\rule{{\textwidth}}{{1pt}}
\textbf{{\large BARREIRA I --- ACESSO E SEGREGAÇÃO ESTRUTURAL}}
\textit{{Como a exclusão começa antes do primeiro salário}}
\noindent\rule{{\textwidth}}{{1pt}}

\subsection{{Modelos Hierárquicos Lineares --- Mediação Contextual do Gap}}
\label{{subsec:hlm_resultados}}

\textit{{Esta seção documenta como o território amplifica o gap racial:
o CEP de moradia não é apenas contexto --- é parte do mecanismo de exclusão.}}

A Tabela~\ref{{tab:hlm_resultados}} apresenta os quatro modelos HLM
ajustados sequencialmente, do modelo nulo (M0) ao modelo completo de
três níveis (M3). Os modelos foram estimados por REML com complementação
por OLS com efeitos fixos de UF e erros-padrão clusterizados por UF
para verificação de robustez.

\paragraph{{ICC e justificativa do modelo multinível.}}
O modelo nulo (M0) estima $\hat{{\rho}}_{{UF}} = {k['icc_uf_m0']}$,
indicando que aproximadamente 9,8\% da variância do log-rendimento é
atribuível ao estado de residência, acima do limiar de 5\% sugerido
por \citeonline{{raudenbush2002}} para justificar a inclusão do nível superior.
A adição dos \textit{{slopes contextuais}} da UPA (M2) reduz o ICC para
5,3\%, revelando que o contexto de bairro explica parte substancial
da heterogeneidade interestadual.

\paragraph{{Gap salarial racial: bruto, contextual e líquido.}}
O modelo M1 estima $\hat{{\beta}}_1^{{M1}} = {k['b_negro_m1']:.4f}$
($p<0{{,}}001$), indicando que profissionais negros recebem em média
{gb:.1f}\% a menos que brancos com mesma escolaridade, sexo e faixa
etária --- o \textbf{{gap racial bruto}}.

Após a inclusão das variáveis de contexto da UPA (M2),
$\hat{{\beta}}_1^{{M2}} = {k['b_negro_m2']:.4f}$, redução que implica uma
\textbf{{mediação contextual de {k['mediacao_upa']:.1f}\%}} do gap bruto pelo
local de moradia. Esse resultado confirma a Hipótese~H2 e quantifica
o \textit{{duplo disadvantage}}: a segregação residencial opera como canal
independente de reprodução da desigualdade racial.

O coeficiente de composição racial da UPA,
$\hat{{\gamma}}_{{01}} = -0{{,}}2689$ ($p<0{{,}}001$), indica que um desvio-padrão
adicional de proporção de negros na UPA reduz o log-rendimento em
0{{,}}29 pontos, efeito equivalente à penalidade individual de ser negro
--- a evidência mais direta do \textit{{duplo disadvantage}}.

O modelo completo M3 produz $\hat{{\beta}}_1^{{M3}} = {k['b_negro_m3']:.4f}$
($p<0{{,}}001$): o \textbf{{gap líquido de {gl:.1f}\%}} representa a fração
do diferencial salarial não explicável por capital humano individual
nem pelo contexto de moradia --- o limite inferior da discriminação
direta no mercado de trabalho.

{hlm_tab}

\begin{{figure}}[H]
  \centering
  \begin{{subfigure}}[b]{{0.49\textwidth}}
    \includegraphics[width=\textwidth]{{kmeans_selecao_k}}
    \caption{{Curvas de seleção de $k$: método do cotovelo,
              Silhouette e Davies-Bouldin.}}
    \label{{fig:kmeans_k}}
  \end{{subfigure}}
  \hfill
  \begin{{subfigure}}[b]{{0.49\textwidth}}
    \includegraphics[width=\textwidth]{{kmeans_composicao_racial_k3}}
    \caption{{Composição racial por cluster ($k=3$).}}
    \label{{fig:kmeans_raca}}
  \end{{subfigure}}
  \caption{{Clustering socioeconômico --- PNAD 2016--2025
            ($N=7{{,}}7$ milhões de trabalhadores da PEA completa).}}
  \label{{fig:kmeans}}
\end{{figure}}

\subsection{{M3 com Inclinação Aleatória de Negro: Heterogeneidade Geográfica}}
\label{{subsec:hlm_rs}}

No modelo M3 padrão, $\hat{{\beta}}_1$ é constante entre estados.
Estimou-se M3 com \textit{{random slope}} para \texttt{{negro}} por UF
({_rs_amostra}),
testando $H_0{{\colon}}\,\tau^2_1 = 0$ (discriminação homogênea entre estados).

{_rs_lrt_block}

{_rs_rho_block}

{_hgen_block}

\subsection{{Random Slope no GLMM: Heterogeneidade Geográfica do Acesso}}
\label{{subsec:glmm_rs}}

{_grs_block}

{_hrs_setor_block}

{_gge_block}

\noindent\rule{{\textwidth}}{{1pt}}
\textbf{{\large BARREIRA II --- PENALIDADE RESIDUAL E TETO DE VIDRO}}
\textit{{O custo de ser negro, mesmo após superar a barreira de entrada}}
\noindent\rule{{\textwidth}}{{1pt}}

\medskip

\textit{{Estabelecida a exclusão de acesso (Barreira I), a próxima questão é:
para os trabalhadores negros que superam essa barreira --- qual é a penalidade
salarial residual? E como esse custo evolui à medida que sobem na distribuição?}}

\subsection{{Clustering Socioeconômico}}
\label{{subsec:clustering}}

Os critérios automáticos apresentam divergência esperada:
$k=2$ ($S={k['km_silhouette_k2']:.4f}$, $DB={fmt(P['KM_DB_K2'],4)}$) produz
clusters mais compactos; $k=3$ ($S={k['km_silhouette']:.4f}$,
$DB={fmt(P['KM_DB_K3'],4)}$) foi adotado por interpretabilidade substantiva
\cite{{ketchen1996}}, uma vez que a solução binária reproduz trivialmente a
clivagem racial sem discriminar segmentos ocupacionais internos
(Figura~\ref{{fig:kmeans}}). A Tabela~\ref{{tab:kmeans_perfis}} apresenta os
perfis médios por cluster.

\begin{{table}}[H]
\centering
\caption{{Perfis dos Clusters Socioeconômicos ($k=3$) --- PNAD 2016--2025.
          $N=7{{,}}7$ milhões de trabalhadores da PEA completa.}}
\label{{tab:kmeans_perfis}}
\begin{{tabular}}{{lccccccc}}
\toprule
\textbf{{Cluster}} & \textbf{{N}} & \textbf{{\%}} & \textbf{{\%~Negro}} &
\textbf{{\%~Mulher}} & \textbf{{log\_Renda}} & \textbf{{Descrição}} \\
\midrule
C0 & {fmtN(P['KM_C0_N'])} & {fmt(P['KM_C0_PCT_TOTAL'],1)}\% & {fmt(P['KM_C0_PCT_NEGRO'],1)}\%  & {fmt(P['KM_C0_PCT_MULHER'],0)}\% & {fmt(P['KM_C0_LOG_RENDA'],3)} &
  Mulheres negras --- vulnerabilidade dupla \\
C1 & {fmtN(P['KM_C1_N'])} & {fmt(P['KM_C1_PCT_TOTAL'],1)}\% & {fmt(P['KM_C1_PCT_NEGRO'],1)}\%  & \phantom{{0}}{fmt(P['KM_C1_PCT_MULHER'],1)}\%  & {fmt(P['KM_C1_LOG_RENDA'],3)} &
  Brancos --- alta renda, menor escolaridade \\
C2 & {fmtN(P['KM_C2_N'])} & {fmt(P['KM_C2_PCT_TOTAL'],1)}\% & {fmt(P['KM_C2_PCT_NEGRO'],1)}\%  & \phantom{{00}}{fmt(P['KM_C2_PCT_MULHER'],0)}\% & {fmt(P['KM_C2_LOG_RENDA'],3)} &
  Homens negros --- maior escolaridade, renda inferior \\
\bottomrule
\end{{tabular}}
\end{{table}}

O Cluster~0 concentra mulheres negras ({fmt(P['KM_C0_PCT_NEGRO'],1)}\% negras,
{fmt(P['KM_C0_PCT_MULHER'],0)}\% feminino), com rendimento médio de
R\${fmtN(P['KM_C0_RENDA_BRL'])} ($\log={fmt(P['KM_C0_LOG_RENDA'],3)}$) e
{fmt(P['KM_C0_PCT_SUP'],1)}\% com ensino superior.
O Cluster~1 agrupa predominantemente brancos ({round(100-P['KM_C1_PCT_NEGRO'])}\% não negros)
com o maior rendimento do conjunto --- R\${fmtN(P['KM_C1_RENDA_BRL'])}
($\log={fmt(P['KM_C1_LOG_RENDA'],3)}$) ---
e apenas {fmt(P['KM_C1_PCT_SUP'],1)}\% com superior completo.

O Cluster~2 reúne homens negros ({fmt(P['KM_C2_PCT_NEGRO'],1)}\% negros,
{fmt(P['KM_C2_PCT_MULHER'],0)}\% feminino) com
$\log\text{{-renda}}={fmt(P['KM_C2_LOG_RENDA'],3)}$ e {fmt(P['KM_C2_PCT_SUP'],1)}\%
com superior completo: escolaridade quase três vezes maior que o Cluster~1,
porém com rendimento {round((P['KM_C1_RENDA_BRL']-P['KM_C2_RENDA_BRL'])/P['KM_C1_RENDA_BRL']*100)}\%
inferior, evidenciando a dupla desvantagem de gênero e raça
(Hipótese~H3) e confirmando que o capital humano é subconvertido em renda
para trabalhadores negros (Hipótese~H5).

\subsection{{Modelos de Machine Learning e SHAP Values}}
\label{{subsec:ml}}

A Tabela~\ref{{tab:ml_perf}} apresenta o desempenho preditivo dos dois modelos
sobre o conjunto de teste (\textit{{hold-out}} 20\%).

\begin{{table}}[H]
\centering
\caption{{Desempenho preditivo --- Random Forest e XGBoost.
          \textit{{Hold-out}} 20\%, $N_\text{{teste}}=307.768$ observações.}}
\label{{tab:ml_perf}}
\begin{{tabular}}{{lccc}}
\toprule
\textbf{{Modelo}} & $R^2$ & \textbf{{MAE}} & \textbf{{RMSE}} \\
\midrule
Random Forest  & {k['rf_r2']:.4f}  & {k['xgb_mae']:.4f} & --- \\
\textbf{{XGBoost}}      & \textbf{{{k['xgb_r2']:.4f}}} & \textbf{{{k['xgb_mae']:.4f}}} & \textbf{{0,6986}} \\
\bottomrule
\end{{tabular}}
\end{{table}}

O $R^2 \approx 0{{,}}43$ é robusto para dados de rendimento individual,
onde a variância não observada (setor, cargo, tempo de serviço) responde
pela maior parte do resíduo.

{shap_tab}

\begin{{figure}}[H]
  \centering
  \begin{{subfigure}}[b]{{0.49\textwidth}}
    \includegraphics[width=\textwidth]{{shap_beeswarm_xgb}}
    \caption{{Beeswarm: distribuição de SHAP por feature (XGBoost).}}
    \label{{fig:shap_bee}}
  \end{{subfigure}}
  \hfill
  \begin{{subfigure}}[b]{{0.49\textwidth}}
    \includegraphics[width=\textwidth]{{shap_dependence_negro_xgb}}
    \caption{{Dependence plot: efeito da raça colorido por
              \% negro na UPA (interação contextual).}}
    \label{{fig:shap_dep}}
  \end{{subfigure}}
  \caption{{Análise SHAP --- XGBoost ($N_\text{{SHAP}}=50.000$).}}
  \label{{fig:shap}}
\end{{figure}}

A Tabela~\ref{{tab:shap_importance}} revela que a \textbf{{renda média da UPA}}
é o preditor mais importante do rendimento individual
($|\text{{SHAP}}| = {k['shap_top1_val']:.3f}$), com peso três vezes maior que
a escolaridade superior e 2,5 vezes maior que o gênero.
Esse resultado confirma computacionalmente a hipótese de Wilson~(\citeyear{{wilson1987}}):
o \textit{{onde se mora}} supera em importância o \textit{{quanto se estudou}}.

A variável racial ocupa o {k['shap_negro_rank']}$^\circ$ lugar no ranking de
importância mesmo após controlar por todos os demais fatores, com SHAP
médio de $-0{{,}}0469$ para trabalhadores negros --- equivalente a uma
penalidade de 4,6\% sobre o rendimento predito que não pode ser atribuída
a diferenças em educação, experiência, gênero ou contexto de moradia.

\begin{{figure}}[H]
  \centering
  \begin{{subfigure}}[b]{{0.32\textwidth}}
    \includegraphics[width=\textwidth]{{shap_waterfall_A_branco_alta_renda_xgb}}
    \caption{{Caso A: branco de alta renda.}}
  \end{{subfigure}}
  \hfill
  \begin{{subfigure}}[b]{{0.32\textwidth}}
    \includegraphics[width=\textwidth]{{shap_waterfall_B_negro_alta_renda_xgb}}
    \caption{{Caso B: negro de alta renda.}}
  \end{{subfigure}}
  \hfill
  \begin{{subfigure}}[b]{{0.32\textwidth}}
    \includegraphics[width=\textwidth]{{shap_waterfall_C_negro_baixa_renda_xgb}}
    \caption{{Caso C: negro de baixa renda.}}
  \end{{subfigure}}
  \caption{{Decomposição SHAP individual (waterfall) para três perfis representativos.
            Valores em log-pontos; azul = contribuição positiva, vermelho = negativa.}}
  \label{{fig:shap_wf}}
\end{{figure}}

\subsection{{Interseccionalidade: raça e gênero no acesso e no topo}}
\label{{subsec:interseccional}}

Os modelos anteriores tratam raça e gênero de forma aditiva. Uma leitura
\textit{{interseccional}} pergunta se a desvantagem de ser negra \emph{{e}} mulher é a
soma das partes. Reespecificamos o GLMM de acesso com um fator de quatro grupos
(\texttt{{grupo\_rg}}: homem branco [referência], mulher branca, homem negro, mulher
negra) e a interação \texttt{{negro$\times$sexo\_fem}}, em três desfechos: acesso a
ocupação qualificada (CBO~1--4), renda no top~20\% e no top~10\%.

\begin{{figure}}[htbp]
  \centering
  \includegraphics[width=0.82\textwidth]{{grupo_rg_interseccional}}
  \caption{{Razões de chance dos quatro grupos raça$\times$gênero \textit{{vs.}}~homem
  branco, em três desfechos. A mulher negra é \emph{{alçada}} no acesso à categoria,
  mas torna-se a \emph{{mais excluída}} no topo da renda.}}
  \label{{fig:interseccional}}
\end{{figure}}

O resultado revela uma \textbf{{inversão}} (Figura~\ref{{fig:interseccional}}). No
\textbf{{acesso à categoria}} qualificada, a mulher negra tem OR~$={fmt(P['GRG_MN_OCP'],2)}$
--- \emph{{acima}} do homem branco ---, porque o efeito de gênero é positivo nesse
desfecho (profissões credenciadas feminizadas, em CBO~1--4); o grupo mais penalizado
é o \textbf{{homem negro}} (OR~$={fmt(P['GRG_HN_OCP'],2)}$). No \textbf{{topo da renda}},
porém, o quadro \emph{{inverte}}: a mulher negra passa a ser a \textbf{{mais excluída}}
de todos --- OR~$={fmt(P['GRG_MN_TOP10'],2)}$ no decil superior, abaixo da mulher branca
($={fmt(P['GRG_MB_TOP10'],2)}$) e do homem negro ($={fmt(P['GRG_HN_TOP10'],2)}$). A
interação \texttt{{negro$\times$sexo\_fem}} é \textit{{sub-aditiva}} em todos os desfechos
(OR~$={fmt(P['GRG_INT_OCP'],2)}$ no acesso; $={fmt(P['GRG_INT_TOP10'],2)}$ no top~10\%):
a penalidade racial é ligeiramente menor entre mulheres, mas isso não impede que a
mulher negra acumule a barreira racial \emph{{e}} o teto de vidro de gênero exatamente
onde mais importa para a ascensão --- o topo da distribuição.

Esse achado refina a tese central: o teto de vidro não é racial nem sexualmente neutro
--- recai com força máxima sobre a mulher negra, que pode \emph{{entrar}} em ocupações
qualificadas, mas é sistematicamente barrada de \emph{{chegar ao topo}} da remuneração.

\noindent\rule{{\textwidth}}{{1pt}}
\textbf{{\large BARREIRA III --- ISOLAMENTO ESTRUTURAL E CAPITAL SOCIAL}}
\textit{{Por que educação, sozinha, não quebra o ciclo}}
\noindent\rule{{\textwidth}}{{1pt}}

\medskip

\textit{{As barreiras anteriores documentam exclusão mensurável por econometria.
Esta seção documenta o mecanismo que as sustenta: o isolamento estrutural
das redes de capital social, que explica por que trabalhadores negros com
pós-graduação ainda não chegam ao topo.}}

\subsection{{Análise de Redes Sociais --- Isolamento Estrutural}}
\label{{subsec:sna}}

{sna_tab}

\begin{{figure}}[H]
  \centering
  \begin{{subfigure}}[b]{{0.49\textwidth}}
    \includegraphics[width=\textwidth]{{sna_rede_demografica}}
    \caption{{Grafo de co-residência: tamanho $\propto$ renda,
              vermelho = arestas inter-raciais.}}
    \label{{fig:sna_grafo}}
  \end{{subfigure}}
  \hfill
  \begin{{subfigure}}[b]{{0.49\textwidth}}
    \includegraphics[width=\textwidth]{{sna_constraint_vs_renda}}
    \caption{{Constraint de Burt $\times$ rendimento médio.}}
    \label{{fig:sna_constraint}}
  \end{{subfigure}}
  \caption{{Análise de Redes Sociais --- PNAD 2016--2025.
            Nós = raça $\times$ educação; arestas = índice Jaccard de co-presença em UPAs.}}
  \label{{fig:sna}}
\end{{figure}}

\begin{{figure}}[H]
  \centering
  \begin{{subfigure}}[b]{{0.49\textwidth}}
    \includegraphics[width=\textwidth]{{sna_homofilia_por_educ}}
    \caption{{Peso Jaccard intra vs.\ inter-racial por nível de educação.}}
    \label{{fig:sna_hom}}
  \end{{subfigure}}
  \hfill
  \begin{{subfigure}}[b]{{0.49\textwidth}}
    \includegraphics[width=\textwidth]{{sna_temporal_gap}}
    \caption{{Evolução do gap salarial e integração residencial (2016--2025).}}
    \label{{fig:sna_time}}
  \end{{subfigure}}
  \caption{{Homofilia racial e tendências temporais --- SNA (PNAD 2016--2025).}}
  \label{{fig:sna2}}
\end{{figure}}

Os resultados da SNA (Tabela~\ref{{tab:sna_metricas}}) revelam cinco achados
principais, de relevo para as hipóteses H2 e H5.

\paragraph{{Betweenness nulo para grupos negros (rede de 20 nós).}}
Na rede expandida de {P.get('SNA_EXP_N_NOS', 20)}~nós (raça $\times$ educação $\times$ gênero),
todos os grupos negros --- de ambos os gêneros e todos os níveis educacionais
--- registram \textit{{betweenness centrality}} igual a zero.
O nó de maior betweenness é \texttt{{{sna_top_node_latex}}}
($B={fmt(P.get('SNA_EXP_BETWN_TOP', 0.7836), 4)}$), indicando que a posição de
\textit{{brokerage}} é ocupada exclusivamente por trabalhadores brancos de
escolaridade fundamental femininos --- confirmando a Hipótese~H5 com maior
robustez que a análise de 10~nós e revelando a dimensão de gênero na
estrutura de intermediação de redes profissionais.

\paragraph{{Homofilia racial H~$= {k['sna_h']:.4f}$.}}
O índice de homofilia abaixo de 0{{,}}5 indica heterofilia leve:
em termos de peso acumulado de co-presença em UPAs, há mais mistura
inter-racial do que segregação pura. Esse padrão é consistente com
a literatura que descreve a segregação racial brasileira como menos
geograficamente absoluta do que a norte-americana \cite{{marques2010}},
porém com forte correlação com renda. A mistura ocorre principalmente
nos bairros populares (grupos \textit{{Sem instrução}} de ambas as raças
compartilham Jaccard~$=0{{,}}979$), enquanto o par com menor integração é
\texttt{{Branco\_Superior}} $\leftrightarrow$ \texttt{{Negro\_Pós}}
($J=0{{,}}492$): negros com pós-graduação raramente habitam as mesmas
UPAs que brancos com nível superior.

\paragraph{{Gap temporal.}}
O diferencial de log-rendimento reduziu-se de {k['gap_2016']:.3f} (2016)
para {k['gap_2025']:.3f} (2025), queda de {abs(k['gap_2025']-k['gap_2016']):.3f}
em dez anos --- uma redução de apenas {abs(k['gap_2025']-k['gap_2016'])/k['gap_2016']*100:.1f}\%
em relação ao patamar inicial. A tendência positiva mais pronunciada
ocorreu em 2020--2021, provavelmente como efeito composição
da pandemia de COVID-19 sobre os rendimentos formais, e não como
resultado estrutural de políticas de inclusão.

\subsection{{Multicolinearidade do Modelo M4: Análise VIF}}
\label{{subsec:vif}}

Para verificar se a inclusão simultânea dos 9~dummies
CBO e das variáveis de vínculo empregatício (\texttt{{emprego\_formal}},
\texttt{{conta\_propria}}, \texttt{{trab\_domestico}}) introduz colinearidade
problemática no Modelo~M4, calculou-se o \textit{{Variance Inflation Factor}} (VIF)
sobre subsample de 200.000 observações da PEA com renda positiva.
Dos ${P.get('VIF_N_TOTAL', 23)}$ preditores analisados, VIF máximo~$= {fmt(P.get('VIF_MAX', 2.09), 2)}$
({P.get('VIF_MAX_VAR', 'CBO: Serviços/Vendas')}); {P.get('VIF_N_CRITICO', 0)}~variável crítica
(VIF~$> 10$); {P.get('VIF_N_ALTO', 0)}~variável alta ($5$--$10$);
{P.get('VIF_N_MODERADO', 1)}~variável moderada ($2$--$5$);
{P.get('VIF_N_BAIXO', 22)}~variáveis baixas ($< 2$).
Esses resultados descartam multicolinearidade problemática entre CBO e
formalidade, validando a especificação completa do M4 sem necessidade de
ortogonalização ou eliminação de preditores.

\subsection{{Segregação Espacial: Inferência Bootstrap}}
\label{{subsec:segr_ci}}

O gap salarial racial (negro~$-$~branco em log-renda) foi estimado por
área com intervalos de confiança bootstrap (1.000 replicações,
$N=771.756$, 10\% da amostra). Os resultados confirmam padrão não linear:
Capital ${fmt(P.get('SEGR_CAP_GAP_PCT', -38.63), 1)}\%$
$[\text{{IC}}_{{95\%}}$: ${fmt(P.get('SEGR_CAP_CI_LO', -39.16), 1)}\%$;
${fmt(P.get('SEGR_CAP_CI_HI', -38.09), 1)}\%]$;
Interior ${fmt(P.get('SEGR_INT_GAP_PCT', -36.37), 1)}\%$
$[\text{{IC}}_{{95\%}}$: ${fmt(P.get('SEGR_INT_CI_LO', -36.68), 1)}\%$;
${fmt(P.get('SEGR_INT_CI_HI', -36.05), 1)}\%]$;
RM (exceto capital) ${fmt(P.get('SEGR_RM_GAP_PCT', -28.14), 1)}\%$
$[\text{{IC}}_{{95\%}}$: ${fmt(P.get('SEGR_RM_CI_LO', -28.83), 1)}\%$;
${fmt(P.get('SEGR_RM_CI_HI', -27.43), 1)}\%]$.
Teste de permutação Capital~vs.~Interior: $p < 0{{,}}001$, confirmando que
a diferença entre contextos não é atribuível ao acaso.

% ══════════════════════════════════════════════════════════════════════════════
%  5. DISCUSSÃO
% ══════════════════════════════════════════════════════════════════════════════
\section{{Discussão e Prescrição}}
\label{{sec:discussao}}

\paragraph{{Nota terminológica.}}
Três conceitos próximos, mas distintos, percorrem este trabalho e não devem ser
confundidos. \textbf{{Mediação contextual}} (HLM) é a fração do gap bruto que
\textit{{desaparece}} ao se controlar o local de moradia (UPA/UF) --- mede o
quanto da penalidade racial transita \textit{{pelo}} território.
\textbf{{Efeito dotação}} (Oaxaca--Blinder) é a parcela do gap atribuível a
\textit{{diferenças nas características observáveis}} entre brancos e negros
(escolaridade, ocupação, contexto), por oposição ao \textbf{{efeito retornos}}
(preços diferenciais pagos às mesmas características).
\textbf{{Gap líquido}} (ou residual) é o diferencial que \textit{{persiste}} após
o controle exaustivo de todas as covariáveis (M4) --- o piso para a discriminação
direta não explicada por observáveis. Em suma: a mediação contextual responde
``por onde passa o gap''; a decomposição de dotações, ``de que ele é feito''; e o
gap líquido, ``o que sobra sem explicação''.

\paragraph{{Da diagnose à prescrição.}}
O diagnóstico econométrico das três seções anteriores revela múltiplos
gargalos simultâneos --- exclusão de acesso, penalidade salarial direta
e isolamento de redes --- que se reforçam mutuamente.
Essa estrutura multicausal implica uma consequência metodológica direta:
nenhuma política pública unidimensional tem capacidade de romper um
sistema de três barreiras interdependentes.
A formulação de políticas eficazes exige priorização multi-critério
e alocação ótima de recursos escassos --- exatamente o que a Pesquisa
Operacional oferece: a tradução dos coeficientes de exclusão em uma
função-objetivo de alocação ótima de recursos públicos.

Os resultados das metodologias aplicadas convergem para um diagnóstico
consistente: a desigualdade salarial racial no Brasil é um fenômeno
multicausal, com componentes individuais, contextuais e estruturais
que se reforçam mutuamente.

\paragraph{{O que este trabalho acrescenta ao debate.}}
\citeonline{{hasenbalg1979}} identificou a discriminação racial como estrutural,
sem poder quantificar mecanismos em escala nacional.
\citeonline{{henriques2001}} documentou o gap educacional racial, mas não separou
o efeito educacional do de redes e contexto.
\citeonline{{soares2009}} estimou, com dados de 2006, que cerca de 50\% do gap
salarial seria ``inexplicado'' --- interpretado como discriminação direta.
Este trabalho, com dados de 2016--2025 e metodologias não disponíveis
a Soares, decompõe essa \textit{{caixa preta}}: apenas {fmt(P['RET_PCT'],1)}\% do gap bruto
são retornos diferenciais (potencialmente discriminação direta); {fmt(P['DOT_PCT'],1)}\%
são diferenças de dotações --- mas essas dotações são, elas mesmas,
produto de barreiras de acesso (GLMM) e isolamento de redes (SNA)
que este trabalho pela primeira vez quantifica de forma integrada.
A contribuição central não é mostrar que o gap existe --- isso a
literatura já sabia desde \citeonline{{hasenbalg1979}} ---,
mas demonstrar que ele é sustentado por um
\textbf{{sistema combinado}} em que discriminação de acesso, segregação
residencial e exclusão de redes se reforçam mutuamente, tornando
insuficientes políticas focadas em um único mecanismo.

\paragraph{{Diálogo com o quadro macro recente do IBGE.}}
Os resultados convergem com o retrato macroestrutural mais recente. A melhora
multidimensional captada pela POF não eliminou o gap racial de qualidade de vida
(0{{,}}183 para chefes pretos/pardos \emph{{vs.}}~0{{,}}122 para brancos), e a renda
voltou a concentrar-se no topo em 2025 (Gini do rendimento domiciliar
\emph{{per capita}} de 0{{,}}491)~\cite{{ibge_pof_2019, ibge_rendimentos_2025}}.
Cabe uma ressalva metodológica: o Gini estimado neste trabalho refere-se ao
\textbf{{rendimento do trabalho entre ocupados}} (em torno de 0{{,}}48), conceito
distinto do Gini domiciliar \emph{{per capita}} de todas as fontes do IBGE ---
níveis próximos, mas medidas diferentes que podem divergir em tendência, pois a
alta de 2025 é puxada por renda \emph{{não}}-trabalho do topo, que não transita
pelo rendimento dos ocupados. Nesse mesmo conceito, a desigualdade \emph{{interna}}
é maior entre brancos ($={fmt(P['GINI_BRANCO_TRAB'],3)}$) do que entre negros
($={fmt(P['GINI_NEGRO_TRAB'],3)}$) --- não por equidade, mas por confinamento dos
negros ao piso da distribuição, o reverso distribucional do teto de vidro.
O contraste territorial reforça a tese: o Distrito
Federal, de maior renda \emph{{per capita}} do país, é também a UF de \emph{{maior}}
penalidade racial salarial em nossos modelos regionais --- riqueza média elevada e
desigualdade racial aguda coexistem no mesmo território.

\paragraph{{Triangulação com o Índice de Progresso Social (IPS).}}
O IPS municipal (Imazon e parceiros, 2026) --- que avalia a qualidade de vida dos
5.570 municípios brasileiros a partir de 57 indicadores sociais e ambientais ---
oferece corroboração externa e multidimensional do eixo territorial desta tese.
Uma integração \textit{{fina}} com o nosso proxy de bairro (UPA) é, contudo,
inviável: o painel público da PNAD não divulga o município (apenas UF e a situação
capital/RM/interior), e o IPS é municipal --- portanto mais agregado que a UPA, que
é sub-municipal. O IPS, assim, não valida o achado de \emph{{bairro}} (situa-se
acima dele na escala), mas ecoa o gradiente macro: as regiões de menor progresso
social (Norte e Nordeste) coincidem com as de maior penalidade racial em nossos
modelos. Empregamo-lo, portanto, como evidência \textit{{convergente}} do caráter
territorial da desigualdade --- não como fonte de dados integrada, e ressalvando que
o IPS mede progresso social geral, não desigualdade racial.

\paragraph{{A segregação residencial como multiplicador da desigualdade.}}
O achado mais robusto desta análise é que {med:.1f}\% do gap salarial racial
bruto é mediado pelo local de moradia --- muito além do que modelos
cross-sectionais típicos, que ignoram a estrutura aninhada dos dados,
seriam capazes de estimar. O coeficiente contextual
$\hat{{\gamma}}_{{01}} = -0{{,}}269$ para a proporção de negros na UPA
indica que a penalidade de viver em bairro segregado equivale,
em magnitude, à própria penalidade individual de ser negro.
Isso sugere que políticas de redistribuição de renda que não enfrentem
a segregação residencial terão eficácia limitada sobre o gap racial.

\paragraph{{Subvalorização do capital humano negro.}}
O Cluster~1 (trabalhadores negros de escolaridade superior à do Cluster~0)
aufere rendimentos 8\% inferiores, e a SNA demonstra que grupos negros com
pós-graduação têm betweenness nulo. Juntas, essas evidências indicam que
negros enfrentam um duplo obstáculo ao retorno educacional: além do
gap direto mensurado pelo HLM, perdem acesso às redes de indicação
que convertem credenciais formais em mobilidade profissional.
\citeonline{{granovetter1973}} antecipou esse mecanismo: sem \textit{{laços fracos}}
que cruzem fronteiras sociais, o capital humano acumulado circula
apenas na própria comunidade.

\paragraph{{Persistência da discriminação direta.}}
O gap líquido de {gl:.1f}\%, estimado após controlar por todos os vetores
de transmissão contextual, representa um piso para a discriminação direta
não explicada por diferenças observáveis. Os valores SHAP reforçam essa
interpretação: a variável racial mantém o {k['shap_negro_rank']}$^\circ$ lugar
na importância preditiva do XGBoost mesmo quando o modelo tem acesso
completo às variáveis educacionais, demográficas e contextuais.
Essa evidência é consistente com os experimentos de auditoria de
\citeonline{{pager2007}}, que demonstram experimentalmente a discriminação
racial em processos seletivos.

\paragraph{{Lenta convergência racial.}}
A redução de apenas {abs(k['gap_2025']-k['gap_2016'])/k['gap_2016']*100:.1f}\%
do gap em dez anos --- equivalente a 0,001 ponto de log-rendimento por ano
($\delta = 0{{,}}000847$, $p = 0{{,}}077$, WLS 2016--2025)
--- sugere que, ao ritmo atual, a convergência racial levaria mais de um
século para eliminar o diferencial observado em 2016.
Essa constatação não trivializa avanços recentes em políticas de cotas
e acesso ao ensino superior, mas evidencia que reformas no campo da
educação, sem intervenção simultânea nos mecanismos de segregação
residencial e de acesso às redes profissionais, são insuficientes.

\paragraph{{Ancoragem em políticas públicas existentes.}}
As frentes priorizadas pela Pesquisa Operacional não são abstrações: cada uma
corresponde a um instrumento jurídico-institucional já existente no Brasil, cuja
intensificação ou aperfeiçoamento a análise recomenda.
A frente de \textbf{{cotas ocupacionais (CBO~1--4)}} dialoga diretamente com a
\textit{{Lei~12.990/2014}}, que reserva 20\% das vagas em concursos públicos
federais a candidatos negros, e cujo escopo o diagnóstico de barreira de acesso
(GLMM, OR~$={or_str(P['OR_M1'])}$) sugere ampliar para níveis hierárquicos
superiores --- onde o teto de vidro é mais severo
(OR(top~10\%)~$={or_str(P['OR_TOP10_M1'])}$).
A frente de \textbf{{qualificação e acesso ao ensino superior}} corresponde ao
\textit{{Prouni}} e ao \textit{{Fies}}, bem como ao legado do \textit{{PRONATEC}};
o achado de subvalorização do capital humano negro indica que tais programas
precisam ser combinados a mecanismos de inserção em redes profissionais, sob pena
de retorno marginal decrescente.
A frente de \textbf{{combate à discriminação direta}} encontra base na
\textit{{Lei~9.029/1995}} (que proíbe práticas discriminatórias na relação de
trabalho) e no \textit{{Estatuto da Igualdade Racial}} (\textit{{Lei~12.288/2010}}),
cuja fiscalização o gap líquido residual de {gl:.1f}\% justifica reforçar.
Em conjunto, a contribuição da PO é traduzir a magnitude estimada de cada
barreira em \textit{{prioridade relativa}} entre instrumentos que já integram o
arcabouço legal brasileiro.

{_rpo_block}

% ══════════════════════════════════════════════════════════════════════════════
%  6. CONCLUSÃO
% ══════════════════════════════════════════════════════════════════════════════
\section{{Conclusão}}
\label{{sec:conclusao}}

Este estudo comprova que a meritocracia baseada em capital humano falha
sistematicamente em prever o sucesso profissional da população negra no Brasil.
A exclusão não é um evento isolado na contratação, nem uma consequência automática
de menor escolaridade --- é uma engrenagem de múltiplas camadas que opera ao longo
de toda a trajetória do trabalhador: na porta de entrada das ocupações de prestígio,
no salário dentro das mesmas ocupações, e nas redes invisíveis que determinam
quem é indicado, promovido e reconhecido.
Cada uma dessas camadas foi identificada, isolada e medida de forma independente;
juntas, elas formam um sistema que nenhuma política unidimensional consegue desmontar.

O achado mais desafiador para o debate de políticas públicas é o da terceira barreira:
trabalhadores negros com alta escolaridade --- incluindo pós-graduados --- estão
estruturalmente excluídos das posições de intermediação nas redes profissionais.
Isso significa que aumentar a escolaridade da população negra, sem simultaneamente
intervir nos mecanismos de segregação residencial e exclusão de redes, produz
retorno marginal decrescente: os títulos existem, mas os canais que os convertem
em mobilidade profissional permanecem bloqueados.
Políticas baseadas apenas em educação são, portanto, necessárias, mas
estruturalmente insuficientes.

O ritmo de convergência observado na última década confirma a urgência.
Ao passo atual, a eliminação do diferencial racial levaria mais de um século.
Isso não é uma previsão pessimista --- é uma consequência aritmética da
combinação entre a magnitude do gap e a velocidade atual de redução.
Significa, concretamente, que reformas incrementais são insuficientes:
é necessário atacar o sistema de barreiras de forma simultânea e com recursos
proporcionais à magnitude do problema.

\medskip

\begin{{quote}}
\textit{{Mesmo após controle exaustivo de {P['VIF_N_TOTAL']} covariáveis individuais,
ocupacionais e contextuais, trabalhadores negros recebem sistematicamente
{k['gap_m4']:.1f}\% a menos que brancos equivalentes --- o mercado de
trabalho brasileiro não é racialmente neutro.}}
\end{{quote}}

\begin{{quote}}
\textit{{O principal mecanismo não é apenas discriminação salarial direta:
é um sistema combinado de exclusão estrutural, em que negros são barrados
na entrada das ocupações de prestígio, encontram teto de vidro na progressão
salarial e são excluídos das redes que convertem credenciais em mobilidade.}}
\end{{quote}}

\begin{{quote}}
\textit{{Educação, isoladamente, não rompe esse ciclo --- trabalhadores negros
com pós-graduação têm betweenness nulo na rede de co-residência profissional.}}
\end{{quote}}

\begin{{quote}}
\textit{{A convergência racial ao ritmo atual levaria mais de um século ---
políticas focadas apenas em capital humano são necessárias, mas insuficientes.}}
\end{{quote}}

\medskip

Essas conclusões emergem da convergência de seis metodologias independentes
sobre $N={fmtN(P['N_GLMM'])}$ observações da PNAD Contínua 2016--2025.
O gap bruto de {gb:.1f}\% (M1) decompõe-se em três camadas:
(i)~mediação contextual de {med:.1f}\% pela UPA
($\hat{{\gamma}}_{{01}}=-0{{,}}269$);
(ii)~mediação ocupacional de {k['med_occ']:.1f}\% pelo acesso desigual a
grupos CBO de alta remuneração;
(iii)~gap residual de {k['gap_m4']:.1f}\% (M4), discriminação pura
pós-ocupação.
O GLMM logístico confirma a barreira de acesso:
OR~$={or_str(P['OR_M1'])}$ para CBO~1--4,
com gradiente progressivo
OR(top~20\%)~$={or_str(P['OR_TOP20_M1'])}$ $\to$ OR(top~10\%)~$={or_str(P['OR_TOP10_M1'])}$.
A regressão quantílica formaliza o glass ceiling
($Z=-5{{,}}25$, $p<0{{,}}001$).

A pesquisa operacional fecha o ciclo diagnóstico-prescritivo.
O ranqueamento TOPSIS aponta Cotas Ocupacionais CBO~1--4 como
intervenção dominante (CC~$={fmt(P["TOPSIS_P1_CC"],4)}$).
A programação linear confirma que R\$5~bilhões alocados nas três
frentes prioritárias reduziria o gap em {fmt(P["PL1_B5_PCT"],1)}\%
--- a convergência racial é fiscalmente viável, \textbf{{desde que as
políticas ataquem o sistema de barreiras em camadas, e não apenas uma delas}}.

\bigskip

\noindent\textbf{{Contribuição principal.}}
Este estudo oferece, ao nosso conhecimento, a primeira análise integrada
de HLM multinível, clustering, SHAP, SNA e pesquisa operacional
(TOPSIS + programação linear) sobre a série completa da PNAD Contínua.
Mais do que confirmar a existência do gap racial --- resultado já documentado
desde \citeonline{{hasenbalg1979}} ---, este trabalho identifica e quantifica os
\textbf{{mecanismos}} que o sustentam em 2016--2025: discriminação de acesso,
segregação residencial e exclusão de redes, em sistema combinado.

\bigskip

\subsection*{{Limitações e escopo de validade}}

\paragraph{{Natureza inferencial \textit{{vs.}}\ preditiva dos modelos.}}
Os resultados devem ser lidos sob dois regimes epistemológicos distintos.
Os modelos HLM, a decomposição de Oaxaca--Blinder, a regressão quantílica e
a correção de Heckman produzem \textit{{estimativas de associação condicional}}:
medem o diferencial racial que persiste após o controle de covariáveis
observáveis, sob o pressuposto de seleção em observáveis. Não constituem, por
si sós, prova de causalidade no sentido contrafactual, pois não derivam de
desenho experimental ou quase-experimental. Já o XGBoost e os valores SHAP têm
finalidade \textit{{preditiva e interpretativa}}: quantificam a contribuição de
cada variável para a \textit{{previsão}} do rendimento --- não o efeito causal
de manipulá-la. A convergência entre os dois regimes (a raça permanece preditora
de primeira ordem \textit{{e}} mantém coeficiente negativo significante sob
controle exaustivo) é o que confere robustez ao diagnóstico; ainda assim, a
linguagem causal foi deliberadamente evitada.

\paragraph{{Cobertura da variável de escolaridade.}}
A escolaridade detalhada (\texttt{{educ\_cat}}) está registrada para cerca de
31\% da PEA no painel público utilizado. Para preservar o $N$ completo, os
níveis de instrução entram como \textit{{dummies}} de conclusão acompanhadas de
um indicador explícito de não-registro (\texttt{{educ\_missing}}), de modo que a
categoria de referência não confunda ``baixa escolaridade'' com ``dado ausente''.
Testes de sensibilidade mostram que o coeficiente racial é estável a essa
especificação (variação inferior a~1\%); ainda assim, os retornos educacionais
devem ser interpretados com a cautela própria de uma variável parcialmente
observada.

\paragraph{{Granularidade macroestrutural da SNA.}}
A PNAD Contínua não coleta vínculos sociais interpessoais. A rede analisada na
Seção~\ref{{subsec:sna}} é, portanto, uma rede de \textbf{{grupos demográficos}}
(raça $\times$ escolaridade $\times$ gênero) conectados por co-residência na
mesma UPA --- não uma rede de indivíduos. Métricas como \textit{{betweenness}} e
\textit{{constraint}} de Burt devem ser lidas como \textbf{{posição estrutural de
grupos}} no espaço da segregação residencial (um substrato macroestrutural da
formação de redes), e não como intermediação interpessoal medida. Uma SNA de
laços individuais exigiria dados relacionais (p.ex.\ RAIS firma--trabalhador ou
\textit{{surveys}} de redes egocêntricas) fora do escopo da PNAD.

\paragraph{{Caráter normativo da Pesquisa Operacional.}}
Os modelos de PO (TOPSIS e programação linear) são ferramentas
\textit{{prescritivas}}: dependem de pesos de critério e de premissas de
efetividade marginal das políticas, aqui calibradas com evidência internacional
e com os próprios coeficientes estimados. Os resultados indicam priorização
\textit{{condicional a essas premissas}} e requerem validação empírica no
contexto brasileiro --- não são previsões pontuais de impacto.

\paragraph{{Desenho transversal e direções futuras.}}
O caráter transversal do painel público impede a análise de trajetórias
individuais; o painel rotativo completo com microdado identificado e a extensão
à RAIS permitiriam investigar mobilidade e o teto de vidro em cargos de liderança
com identificação de firma. A SNA poderia ser refinada para grafos bipartidos
UPA~$\times$~grupo, elevando a resolução espacial da medida de segregação.

\bigskip

\noindent\textbf{{Declaração de uso de inteligência artificial.}}
Na elaboração deste trabalho foram utilizadas ferramentas de inteligência
artificial (Claude Code, da Anthropic) como apoio à implementação e depuração de
código (Python e R), à geração de figuras e tabelas e à formatação dos documentos.
A concepção da pesquisa, a escolha das metodologias, a interpretação dos resultados
e a redação final são de responsabilidade do autor, que revisou, validou e responde
por todo o conteúdo.

% ══════════════════════════════════════════════════════════════════════════════
%  REFERÊNCIAS
% ══════════════════════════════════════════════════════════════════════════════
\newpage
\bibliography{{relatorio_tcc}}

\end{{document}}
"""
    return doc


# ── BibTeX ─────────────────────────────────────────────────────────────────────

BIB = r"""
@article{stram1994,
  author    = {Stram, Daniel O. and Lee, Jae Won},
  title     = {Variance Components Testing in the Longitudinal Mixed Effects Model},
  journal   = {Biometrics},
  volume    = {50},
  number    = {4},
  pages     = {1171--1177},
  year      = {1994},
}

@book{hasenbalg1979,
  author    = {Hasenbalg, Carlos},
  title     = {Discriminação e Desigualdades Raciais no Brasil},
  publisher = {Graal},
  year      = {1979},
  address   = {Rio de Janeiro},
}

@book{raudenbush2002,
  author    = {Raudenbush, Stephen W. and Bryk, Anthony S.},
  title     = {Hierarchical Linear Models: Applications and Data Analysis Methods},
  edition   = {2},
  publisher = {Sage},
  year      = {2002},
  address   = {Thousand Oaks, CA},
}

@book{wilson1987,
  author    = {Wilson, William J.},
  title     = {The Truly Disadvantaged: The Inner City, the Underclass, and Public Policy},
  publisher = {University of Chicago Press},
  year      = {1987},
  address   = {Chicago},
}

@article{granovetter1973,
  author  = {Granovetter, Mark S.},
  title   = {The Strength of Weak Ties},
  journal = {American Journal of Sociology},
  volume  = {78},
  number  = {6},
  pages   = {1360--1380},
  year    = {1973},
}

@article{burt2004,
  author  = {Burt, Ronald S.},
  title   = {Structural Holes and Good Ideas},
  journal = {American Journal of Sociology},
  volume  = {110},
  number  = {2},
  pages   = {349--399},
  year    = {2004},
}

@article{sampson1997,
  author  = {Sampson, Robert J. and Raudenbush, Stephen W. and Earls, Felton},
  title   = {Neighborhoods and Violent Crime: A Multilevel Study of Collective Efficacy},
  journal = {Science},
  volume  = {277},
  pages   = {918--924},
  year    = {1997},
}

@book{pager2007,
  author    = {Pager, Devah},
  title     = {Marked: Race, Crime, and Finding Work in an Era of Mass Incarceration},
  publisher = {University of Chicago Press},
  year      = {2007},
  address   = {Chicago},
}

@article{lundberg2017,
  author  = {Lundberg, Scott M. and Lee, Su-In},
  title   = {A Unified Approach to Interpreting Model Predictions},
  journal = {Advances in Neural Information Processing Systems},
  volume  = {30},
  year    = {2017},
}

@article{breiman2001,
  author  = {Breiman, Leo},
  title   = {Random Forests},
  journal = {Machine Learning},
  volume  = {45},
  number  = {1},
  pages   = {5--32},
  year    = {2001},
}

@inproceedings{chen2016,
  author    = {Chen, Tianqi and Guestrin, Carlos},
  title     = {{XGBoost}: A Scalable Tree Boosting System},
  booktitle = {Proceedings of the 22nd ACM SIGKDD International Conference
               on Knowledge Discovery and Data Mining},
  pages     = {785--794},
  year      = {2016},
}

@article{rousseeuw1987,
  author  = {Rousseeuw, Peter J.},
  title   = {Silhouettes: A Graphical Aid to the Interpretation and
             Validation of Cluster Analysis},
  journal = {Journal of Computational and Applied Mathematics},
  volume  = {20},
  pages   = {53--65},
  year    = {1987},
}

@article{davies_bouldin1979,
  author  = {Davies, David L. and Bouldin, Donald W.},
  title   = {A Cluster Separation Measure},
  journal = {IEEE Transactions on Pattern Analysis and Machine Intelligence},
  volume  = {1},
  number  = {2},
  pages   = {224--227},
  year    = {1979},
}

@article{ketchen1996,
  author  = {Ketchen, David J. and Shook, Christopher L.},
  title   = {The Application of Cluster Analysis in Strategic Management Research:
             An Analysis and Critique},
  journal = {Strategic Management Journal},
  volume  = {17},
  number  = {6},
  pages   = {441--458},
  year    = {1996},
}

@techreport{ibge_pnad_2023,
  author      = {{IBGE}},
  title       = {Pesquisa Nacional por Amostra de Domicílios Contínua:
                 Notas Metodológicas},
  institution = {Instituto Brasileiro de Geografia e Estatística},
  year        = {2023},
  address     = {Rio de Janeiro},
}

@techreport{ibge_pof_2019,
  author      = {{IBGE}},
  title       = {Pesquisa de Orçamentos Familiares 2017--2018:
                 análise da qualidade de vida (Índice de Perda de Qualidade de Vida)},
  institution = {Instituto Brasileiro de Geografia e Estatística},
  year        = {2019},
  address     = {Rio de Janeiro},
}

@techreport{ibge_rendimentos_2025,
  author      = {{IBGE}},
  title       = {Pesquisa Nacional por Amostra de Domicílios Contínua:
                 Rendimento de Todas as Fontes 2025},
  institution = {Instituto Brasileiro de Geografia e Estatística},
  year        = {2025},
  address     = {Rio de Janeiro},
}

@article{henriques2001,
  author  = {Henriques, Ricardo},
  title   = {Desigualdade Racial no Brasil: Evolução das Condições de Vida
             na Década de 90},
  journal = {Texto para Discussão IPEA},
  number  = {807},
  year    = {2001},
}

@article{soares2009,
  author  = {Soares, Sergei},
  title   = {Desigualdade Racial de Renda no Brasil: 1976--2006},
  journal = {Estudos Econômicos},
  volume  = {39},
  number  = {4},
  pages   = {803--825},
  year    = {2009},
}

@article{marques2010,
  author  = {Marques, Eduardo},
  title   = {Redes Sociais, Segregação e Pobreza em São Paulo},
  journal = {Dados: Revista de Ciências Sociais},
  volume  = {53},
  number  = {1},
  pages   = {5--50},
  year    = {2010},
}
"""


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Carregando resultados ...")
    r = load_results()
    k = extract_kpis(r)

    print("KPIs extraídos:")
    for key, val in k.items():
        print(f"  {key}: {val}")

    print("\nGerando LaTeX ...")
    latex = build_latex(r, k)

    OUT_TEX.write_text(latex, encoding="utf-8")
    OUT_BIB.write_text(BIB, encoding="utf-8")

    print(f"\nArquivos gerados:")
    print(f"  {OUT_TEX}  ({len(latex):,} caracteres)")
    print(f"  {OUT_BIB}")
    print()
    print("Para compilar em Overleaf:")
    print("  1. Crie novo projeto em overleaf.com")
    print("  2. Upload: relatorio_tcc.tex + relatorio_tcc.bib")
    print("  3. Upload da pasta outputs/ com figuras e tabelas")
    print("  4. Compile com pdflatex + bibtex + pdflatex + pdflatex")
    print()
    print("Para compilar localmente (MiKTeX):")
    print("  pdflatex relatorio_tcc.tex")
    print("  bibtex relatorio_tcc")
    print("  pdflatex relatorio_tcc.tex")
    print("  pdflatex relatorio_tcc.tex")


if __name__ == "__main__":
    main()
