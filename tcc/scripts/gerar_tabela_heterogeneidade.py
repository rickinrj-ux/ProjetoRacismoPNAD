# -*- coding: utf-8 -*-
"""
gerar_tabela_heterogeneidade.py  (04/10/2026)
=============================================
Tabela compacta do módulo de heterogeneidade: o que a categoria "negro" agregada esconde.
Uma linha por recorte (cor, setor, idade, topo dentro da UF), com o resultado de cada
modelo de referência — HLM M3, GLMM A2 (acesso e top 10%) e Oaxaca (A).
Fontes: hlm/glmm/oaxaca_heterogeneidade via params_nucleo (scripts run_heterogeneidade.py
e R/run_glmm_heterogeneidade.R). Saída: outputs/tables/heterogeneidade_tcc.tex
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from params_nucleo import P, pt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "tables" / "heterogeneidade_tcc.tex"
NA = "---"


def pc(k):
    return pt(P[k], 1) if k in P else NA


def orr(k):
    return pt(P[k], 3) if k in P else NA


linhas = [
    ("Negro (categoria do trabalho)", pt(P["GAP_M3"], 1), orr("OR_ocp_qualif_M2"),
     orr("OR_y_top10_M2"), pt(P["OB_SEM_RET_PCT"], 1)),
    ("\\quad Pardo", pc("HET_HLM_PARDO"), orr("HET_OR_PARDO_OCP"), orr("HET_OR_PARDO_T10"),
     pc("HET_OB_PARDO_A")),
    ("\\quad Preto", pc("HET_HLM_PRETO"), orr("HET_OR_PRETO_OCP"), orr("HET_OR_PRETO_T10"),
     pc("HET_OB_PRETO_A")),
    ("Setor privado", pc("HET_HLM_SETOR0"), orr("HET_OR_SETOR0_OCP"), orr("HET_OR_SETOR0_T10"), NA),
    ("Setor público", pc("HET_HLM_SETOR1"), orr("HET_OR_SETOR1_OCP"), orr("HET_OR_SETOR1_T10"), NA),
    ("Idade 14--29 anos", pc("HET_IDADE_14_29"), NA, NA, NA),
    ("Idade 30--39 anos", pc("HET_IDADE_30_39"), NA, NA, NA),
    ("Idade 40--49 anos", pc("HET_IDADE_40_49"), NA, NA, NA),
    ("Idade 50--64 anos", pc("HET_IDADE_50_64"), NA, NA, NA),
    ("Idade 65 anos ou mais", pc("HET_IDADE_65MAIS"), NA, NA, NA),
    ("Top 10\\% dentro da UF", NA, NA, orr("HET_OR_T10UF"), NA),
]
corpo = "\n".join(" & ".join(l) + " \\\\" for l in linhas)
tex = r"""\begin{table}[!ht]
\centering
\caption{O que a categoria agregada esconde: penalidade racial por cor, setor, idade e
corte de renda. Penalidade salarial: HLM~M3 (mesmo bairro, escolaridade, idade, sexo,
jornada e estado), em \% de renda; por idade, M3 com a interação negro $\times$ faixa
etária. Razões de chance: GLMM de acesso e de teto de vidro (top 10\%), contra brancos
de mesmo perfil e bairro. Preço: parcela não explicada da Oaxaca--Blinder (A), contra
brancos. Setor público: empregados do setor público, inclusive militares e estatutários
(VD4009); privado: os demais ocupados. Cada recorte foi estimado em todos os seus
indivíduos, sem amostragem, com a especificação do modelo de referência.}
\label{tab:heterogeneidade}
\begin{tabular}{lrrrr}
\toprule
Recorte & Penalidade salarial (\%) & OR cargo qualificado & OR top 10\% & Preço (\%) \\
\midrule
""" + corpo + r"""
\bottomrule
\end{tabular}
\par\smallskip
\footnotesize\emph{Como ler:} OR abaixo de~1 é menor chance que a de um branco
comparável; ``Preço'' é a parte do gap que as características observáveis não explicam.
Na última linha, o topo é definido dentro de cada estado, e não pelo corte nacional.
\end{table}
"""
OUT.write_text(tex, encoding="utf-8")
print(f"OK -> {OUT.relative_to(ROOT)}")
