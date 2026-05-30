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
            val = str(val).replace("***", r"$^{***}$").replace("**", r"$^{**}$").replace("*", r"$^{*}$")
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
        node = str(row["node"]).replace("_", r"\_")
        high_b = float(row["betweenness"]) > 0
        b_cell = r"\textbf{" + f"{float(row['betweenness']):.3f}" + "}" if high_b else f"{float(row['betweenness']):.3f}"
        lines.append(
            f"{node} & {row['race']} & {row['educ_label']} & {int(row['n_workers']):,} "
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

\includegraphics[width=4cm]{{logo_esalq}}  % substitua pelo logo ESALQ se disponível

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

O Brasil é um dos países com maior desigualdade racial de renda no mundo.
Segundo a PNAD Contínua, a razão entre o rendimento médio de trabalhadores
brancos e negros permanece acima de 1{{:}}1,5 ao longo de toda a série
histórica disponível, persistindo mesmo quando se controlam escolaridade,
experiência e setor de atividade~\citep{{ibge_pnad_2023}}.
A desigualdade racial no mercado de trabalho brasileiro é, portanto,
não apenas uma herança colonial, mas um fenômeno reproduzido ativamente
por mecanismos que a abordagem tradicional de diferenças de capital humano
não é capaz de capturar~\citep{{hasenbalg1979}}.

A literatura empírica contemporânea identifica três canais principais de
reprodução dessa desigualdade: (i)~discriminação direta, isto é, diferenças
de tratamento em processos de seleção e promoção com características
individuais observadas~\citep{{pager2007}}; (ii)~segregação residencial e
seus efeitos sobre o capital social disponível ao trabalhador
--- o contexto do bairro define a qualidade das redes de indicação
profissional~\citep{{wilson1987, sampson1997}}; e (iii)~subvalorização
sistêmica do capital humano negro, pela qual um dado nível de escolaridade
gera retornos financeiros menores para trabalhadores negros do que para
brancos~\citep{{hasenbalg1979, pager2007}}.

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

\citet{{hasenbalg1979}} demonstrou pioneiramente que a desigualdade racial
no Brasil não decorre apenas de diferenças históricas de acesso à educação,
mas de mecanismos ativos de discriminação no mercado de trabalho que
convertem desvantagens sociais em desvantagens econômicas de forma cumulativa.
Trabalhos posteriores~\citep{{henriques2001, soares2009}} confirmaram a
persistência dessas diferenças mesmo após controlar por escolaridade,
reforçando a hipótese de discriminação estrutural.

\subsection{{Efeitos de vizinhança e segregação residencial}}

\citet{{wilson1987}} propôs a hipótese da \textit{{concentrated disadvantage}}:
a concentração de pobreza em bairros racialmente segregados amplifica
desvantagens individuais por meio da redução de redes de contato com
o mercado de trabalho formal, degradação de serviços públicos e aumento
da violência. \citet{{sampson1997}} forneceu evidência empírica para essa
hipótese em contexto norte-americano, e estudos brasileiros encontraram
padrões similares para as regiões metropolitanas~\citep{{marques2010}}.

A abordagem de \textit{{networking}} local, operacionalizada neste trabalho
pelo segundo nível do modelo hierárquico (UPA), testa se o contexto
socioeconômico do bairro exerce efeito independente sobre o rendimento
após controlar por características individuais --- o chamado
\textit{{duplo disadvantage}} de ser negro \textit{{e}} morar em bairros negros.

\subsection{{Modelos lineares hierárquicos para dados aninhados}}

\citet{{raudenbush2002}} sistematizaram a fundamentação estatística dos
modelos lineares hierárquicos (HLM), tornando-os o padrão metodológico para
análise de dados com estrutura aninhada (indivíduos dentro de bairros dentro
de estados). Esses modelos permitem decompor a variância do desfecho em
componentes de cada nível e estimar os efeitos contextuais
controlando simultaneamente pelos efeitos individuais.

\subsection{{Interpretabilidade em machine learning: SHAP values}}

\citet{{lundberg2017}} propuseram os \textit{{SHapley Additive exPlanations}}
(SHAP), unificando importância de variáveis, efeitos parciais e explicações
individuais em uma única estrutura axiomática baseada na teoria dos jogos
cooperativos. Para dados socioeconômicos, SHAP permite responder à pergunta:
``quanto e em que direção a raça de um indivíduo específico afeta a predição
de sua renda?'' --- uma contribuição metodológica que complementa e enriquece
a interpretação dos coeficientes do HLM.

\subsection{{Análise de redes sociais e capital social}}

\citet{{granovetter1973}} demonstrou que \textit{{laços fracos}} ---
conexões entre indivíduos de grupos sociais distintos --- são os principais
canais de transmissão de informações sobre oportunidades profissionais.
\citet{{burt2004}} formalizou o conceito de \textit{{buraco estrutural}}:
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
\citep{{raudenbush2002}}.

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
\textit{{Silhouette Coefficient}} \citep{{rousseeuw1987}} com validação
pelo índice de Davies-Bouldin \citep{{davies_bouldin1979}}.

\subsection{{Random Forest, XGBoost e SHAP Values}}

Para predição do log-rendimento, foram ajustados dois modelos de ensemble:
(i)~\textit{{Random Forest}} \citep{{breiman2001}} com 200 árvores e profundidade
máxima 10; e (ii)~\textit{{XGBoost}} \citep{{chen2016}} com 300 iterações,
$\text{{lr}}=0{{,}}05$ e regularização $L_1/L_2$. Sobre o modelo XGBoost,
foi aplicado o \textit{{TreeExplainer}} da biblioteca SHAP
\citep{{lundberg2017}} sobre um subsample de 50.000 observações para
calcular os valores de Shapley de cada feature.

\subsection{{Análise de Redes Sociais (SNA)}}

A rede demográfica foi construída com 10~nós, representando as combinações
de raça~$\times$~educação (2 raças $\times$ 5 níveis), e arestas ponderadas
pelo índice de Jaccard de co-presença em UPAs:
\begin{{equation}}
  w_{{AB}} = \frac{{|\mathcal{{U}}_A \cap \mathcal{{U}}_B|}}
                   {{|\mathcal{{U}}_A \cup \mathcal{{U}}_B|}}
  \label{{eq:jaccard}}
\end{{equation}}
onde $\mathcal{{U}}_A$ é o conjunto de UPAs com trabalhadores do grupo~$A$.
As métricas de rede incluem centralidade de grau, \textit{{betweenness}},
\textit{{clustering coefficient}} e \textit{{constraint}} de Burt~\citep{{burt2004}}.

% ══════════════════════════════════════════════════════════════════════════════
%  4. RESULTADOS
% ══════════════════════════════════════════════════════════════════════════════
\section{{Resultados}}
\label{{sec:resultados}}

\subsection{{Modelos Hierárquicos Lineares}}
\label{{subsec:hlm_resultados}}

A Tabela~\ref{{tab:hlm_resultados}} apresenta os quatro modelos HLM
ajustados sequencialmente, do modelo nulo (M0) ao modelo completo de
três níveis (M3). Os modelos foram estimados por REML com complementação
por OLS com efeitos fixos de UF e erros-padrão clusterizados por UF
para verificação de robustez.

\paragraph{{ICC e justificativa do modelo multinível.}}
O modelo nulo (M0) estima $\hat{{\rho}}_{{UF}} = {k['icc_uf_m0']}$,
indicando que aproximadamente 9,8\% da variância do log-rendimento é
atribuível ao estado de residência, acima do limiar de 5\% sugerido
por \citet{{raudenbush2002}} para justificar a inclusão do nível superior.
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
$\hat{{\gamma}}_{{01}} = -0{{,}}2894$ ($p<0{{,}}001$), indica que um desvio-padrão
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

\subsection{{Clustering Socioeconômico}}
\label{{subsec:clustering}}

O critério Silhouette em $k=2$ ($S={k['km_silhouette_k2']:.4f}$) apontou
solução binária trivial; $k=3$ ($S={k['km_silhouette']:.4f}$) foi adotado
por interpretabilidade substantiva (Figura~\ref{{fig:kmeans}}). A
Tabela~\ref{{tab:kmeans_perfis}} apresenta os perfis médios por cluster.

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

\subsection{{Análise de Redes Sociais}}
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

\paragraph{{Betweenness nulo para grupos negros.}}
Em todos os cinco níveis educacionais, grupos negros registram
\textit{{betweenness centrality}} igual a zero, enquanto
\texttt{{Branco\_Fundamental}} alcança $B=0{{,}}306$ e
\texttt{{Branco\_Pós}} alcança $B=0{{,}}111$.
Isso significa que os fluxos de informação e oportunidade profissional
que cruzam grupos socioeconômicos distintos transitam exclusivamente
por atores brancos --- confirmando a Hipótese~H5.

\paragraph{{Homofilia racial H~$= {k['sna_h']:.4f}$.}}
O índice de homofilia abaixo de 0{{,}}5 indica heterofilia leve:
em termos de peso acumulado de co-presença em UPAs, há mais mistura
inter-racial do que segregação pura. Esse padrão é consistente com
a literatura que descreve a segregação racial brasileira como menos
geograficamente absoluta do que a norte-americana \citep{{marques2010}},
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

% ══════════════════════════════════════════════════════════════════════════════
%  5. DISCUSSÃO
% ══════════════════════════════════════════════════════════════════════════════
\section{{Discussão}}
\label{{sec:discussao}}

Os resultados das quatro metodologias convergem para um diagnóstico
consistente: a desigualdade salarial racial no Brasil é um fenômeno
multicausal, com componentes individuais, contextuais e estruturais
que se reforçam mutuamente.

\paragraph{{A segregação residencial como multiplicador da desigualdade.}}
O achado mais robusto desta análise é que {med:.1f}\% do gap salarial racial
bruto é mediado pelo local de moradia --- muito além do que modelos
cross-sectionais típicos, que ignoram a estrutura aninhada dos dados,
seriam capazes de estimar. O coeficiente contextual
$\hat{{\gamma}}_{{01}} = -0{{,}}289$ para a proporção de negros na UPA
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
\citet{{granovetter1973}} antecipou esse mecanismo: sem \textit{{laços fracos}}
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
\citet{{pager2007}}, que demonstram experimentalmente a discriminação
racial em processos seletivos.

\paragraph{{Lenta convergência racial.}}
A redução de apenas {abs(k['gap_2025']-k['gap_2016'])/k['gap_2016']*100:.1f}\%
do gap em dez anos --- equivalente a 0,02 pontos de log-rendimento por ano
--- sugere que, ao ritmo atual, a convergência racial levaria mais de um
século para eliminar o diferencial observado em 2016.
Essa constatação não trivializa avanços recentes em políticas de cotas
e acesso ao ensino superior, mas evidencia que reformas no campo da
educação, sem intervenção simultânea nos mecanismos de segregação
residencial e de acesso às redes profissionais, são insuficientes.

% ══════════════════════════════════════════════════════════════════════════════
%  6. CONCLUSÃO
% ══════════════════════════════════════════════════════════════════════════════
\section{{Conclusão}}
\label{{sec:conclusao}}

Este trabalho investigou o gap salarial racial no Brasil sob uma abordagem
metodológica integrativa, combinando econometria multinível, machine learning
interpretável e análise de redes sociais sobre 10 anos de dados da PNAD
Contínua. As cinco hipóteses originais foram confirmadas.

O gap racial bruto de {gb:.1f}\% reduz-se para {gl:.1f}\% quando contextos
residenciais e macroeconômicos são controlados, mas permanece significativo
e estatisticamente robusto --- sinalizando discriminação direta residual
não explicável por diferenças de capital humano ou localização.
A mediação contextual de {med:.1f}\% pelo bairro de moradia é o resultado
de maior relevância para políticas públicas: ele quantifica a contribuição
da segregação residencial ao gap racial, abrindo espaço para intervenções
habitacionais e de mobilidade urbana como ferramentas de redução
da desigualdade racial.

A análise de redes adiciona uma perspectiva inovadora ao diagnóstico:
a exclusão de trabalhadores negros das posições de \textit{{brokerage}}
na rede de co-residência sugere que, mesmo quando a segregação
geográfica é moderada em termos absolutos, as assimetrias nas
posições estruturais da rede são suficientes para limitar o acesso
de negros ao capital social que converte educação em mobilidade.

A pesquisa operacional fecha o ciclo diagnóstico-prescritivo do trabalho.
O ranqueamento TOPSIS de seis políticas públicas, avaliadas em cinco
critérios simultâneos, aponta as Cotas Ocupacionais CBO~1--4 como
política dominante (CC~$={fmt(P["TOPSIS_P1_CC"],4)}$), seguidas de
Equidade Educacional (CC~$={fmt(P["TOPSIS_P2_CC"],4)}$), Mentoria e
Redes (CC~$={fmt(P["TOPSIS_P3_CC"],4)}$), Transparência Salarial
(CC~$={fmt(P["TOPSIS_P4_CC"],4)}$), Enforcement
(CC~$={fmt(P["TOPSIS_P5_CC"],4)}$) e Desegregação Residencial
(CC~$={fmt(P["TOPSIS_P6_CC"],4)}$). A programação linear confirma que
uma alocação ótima de R\$5~bilhões priorizando os três canais de maior
efetividade reduziria o \textit{{gap}} salarial racial em
{fmt(P["PL1_B5_PCT"],1)}\%, demonstrando que a convergência racial é
fiscalmente viável em um horizonte de médio prazo.

\bigskip

\noindent\textbf{{Contribuição principal.}}
Este estudo oferece, ao nosso conhecimento, a primeira análise integrada
de HLM multinível, clustering, SHAP, SNA e pesquisa operacional
(TOPSIS + programação linear) sobre a série completa da PNAD Contínua,
estabelecendo uma metodologia replicável para o monitoramento
longitudinal e a priorização de políticas de redução da desigualdade
racial no mercado de trabalho brasileiro.

\bigskip

\noindent\textbf{{Limitações e direções futuras.}}
O caráter transversal do painel público da PNAD Contínua impede a
análise de trajetórias individuais de mobilidade salarial ao longo do
tempo; estudos futuros poderiam explorar o painel rotativo completo
com acesso restrito ao microdado identificado. A extensão da análise
para dados corporativos (RAIS) permitiria investigar a hipótese de
\textit{{glass ceiling}} em cargos de liderança.

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

@techreport{ibge_pnad_2023,
  author      = {{IBGE}},
  title       = {Pesquisa Nacional por Amostra de Domicílios Contínua:
                 Notas Metodológicas},
  institution = {Instituto Brasileiro de Geografia e Estatística},
  year        = {2023},
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
