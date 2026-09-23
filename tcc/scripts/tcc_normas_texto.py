# -*- coding: utf-8 -*-
"""
tcc_normas_texto.py
===================
Texto autoral da versão normativa: preâmbulo, folha de rosto, Resumo, Abstract,
Introdução e Conclusão. Fica separado do gerador porque é prosa, não lógica.

Restrições que moldaram cada peça (Manual de Normas, item 16):
  · Resumo e Abstract: um único parágrafo, no máximo 250 palavras, pretérito
    perfeito do indicativo, precedidos do título centralizado em negrito;
  · Palavras-chave: até cinco, diferentes das do título;
  · Introdução: no máximo duas páginas (~35 linhas), sem marcadores, sem
    subtópicos e sem tabelas ou figuras, com o objetivo enunciado no último
    parágrafo;
  · Conclusão: sucinta, sem citações e sem tabelas ou figuras.

Os números vêm de params_nucleo (csv de outputs/tables), como no resto do
projeto — nenhum valor é escrito à mão.
"""
from __future__ import annotations

from params_nucleo import P, milhar, pct, pt

_OR_CBO = pt(P["OR_ocp_qualif_M2"], 3)
_OR_T10 = pt(P["OR_y_top10_M2"], 3)
_PCT_CBO = pt((1 - P["OR_ocp_qualif_M2"]) * 100, 0)
_PCT_T10 = pt((1 - P["OR_y_top10_M2"]) * 100, 0)

PREAMBULO = r"""% ══════════════════════════════════════════════════════════════════════════════
% VERSÃO NORMATIVA — MBA USP/Esalq (Manual de Instruções e Normas, itens 15–19)
% Gerada por tcc/scripts/gerar_tcc_normas.py. NÃO editar à mão.
% ══════════════════════════════════════════════════════════════════════════════
\documentclass[11pt, a4paper, oneside]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[brazil]{babel}
% Arial: helvet é a métrica equivalente em LaTeX; no .docx a fonte vem do
% template oficial, via --reference-doc
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage[top=2.5cm, bottom=2.5cm, left=2.5cm, right=2.5cm,
            headsep=0.6cm]{geometry}
\usepackage{setspace}
\onehalfspacing
\usepackage{indentfirst}
\setlength{\parindent}{1.25cm}
\usepackage{amsmath, amssymb}
\usepackage{graphicx}
\graphicspath{{outputs/figures/}}
\usepackage{float}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{multirow}
\usepackage{array}
\usepackage{caption}
\usepackage{subcaption}
% Tabela 1. / Figura 1. — separador é ponto, e a legenda é 1 pt menor
\captionsetup{font=small, labelfont=bf, labelsep=period,
              justification=justified, singlelinecheck=false, skip=6pt}
\usepackage{placeins}
\usepackage[alf, abnt-etal-list=5]{abntex2cite}
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\fontsize{8}{10}\selectfont Trabalho de Conclusão de Curso
  apresentado para obtenção do título de especialista em Data Science e
  Analytics -- 2026}
\fancyfoot[R]{\fontsize{9}{11}\selectfont\thepage}
\renewcommand{\headrulewidth}{0pt}
\setlength{\headheight}{28pt}
% \note é usado nas tabelas geradas por outros scripts
\providecommand{\note}[1]{\par\smallskip{\footnotesize #1}}
\DeclareUnicodeCharacter{2212}{$-$}
\DeclareUnicodeCharacter{0394}{$\Delta$}
\DeclareUnicodeCharacter{2192}{$\rightarrow$}
\DeclareUnicodeCharacter{00B2}{\textsuperscript{2}}
\makeatletter
\providecommand{\abntnextkey}{}
\makeatother
% seções e subseções sem numeração (norma), em negrito e à esquerda
\usepackage{titlesec}
\titleformat{\section}{\normalsize\bfseries}{}{0pt}{}
\titleformat{\subsection}{\normalsize\bfseries}{}{0pt}{}
\titlespacing*{\section}{0pt}{12pt}{6pt}
\titlespacing*{\subsection}{1.25cm}{10pt}{6pt}

\begin{document}
"""

FOLHA_ROSTO = r"""
% ── Folha de rosto: só título, autores e filiação (norma, item 16.1) ──────────
\thispagestyle{fancy}
\begin{center}
\vspace*{2cm}
{\fontsize{11}{14}\selectfont\bfseries
Racismo estrutural no mercado de trabalho brasileiro: uma abordagem multinível
e de decomposição salarial\par}

\vspace{2\baselineskip}

{\fontsize{11}{14}\selectfont
Ricardo Gomes Calheiros\textsuperscript{1*}; Edilson José Rodrigues\textsuperscript{2}\par}
\end{center}

\vspace{\baselineskip}

\begin{flushleft}
{\fontsize{9}{11}\selectfont
\textsuperscript{1*} Bacharel em Sistemas de Informação. E-mail autor
correspondente: rickinrj@gmail.com\par
\textsuperscript{2} Pós-doutor em Linguística Computacional. MBA USP/Esalq.
E-mail: orientador@usp.br\par}
\end{flushleft}

\newpage
"""

RESUMO_ABSTRACT = (r"""
% ── Título + Resumo + Palavras-chave (norma, item 16.2) ──────────────────────
\begin{center}
{\fontsize{11}{14}\selectfont\bfseries
Racismo estrutural no mercado de trabalho brasileiro: uma abordagem multinível
e de decomposição salarial\par}
\end{center}

\vspace{\baselineskip}
\noindent\textbf{Resumo}
\vspace{\baselineskip}

\begin{singlespace}\noindent
""" + f"""Este trabalho investigou o diferencial racial de rendimentos e as barreiras de
acesso ocupacional no Brasil com a série completa da Pesquisa Nacional por
Amostra de Domicílios Contínua, de 2016 a 2025, sobre {milhar(P['N_GLMM'])}
observações da população ocupada com rendimento positivo em
{milhar(P['N_UPAS'])} setores de amostragem. Quatro métodos foram aplicados de
forma articulada: modelo linear hierárquico de dois níveis, com indivíduos
aninhados em bairros e efeitos fixos de estado; decomposição de
Oaxaca--Blinder; regressão quantílica com decomposição por função de influência
recentrada; e modelo logístico multinível de acesso, estimado por máxima
verossimilhança. Um modelo de aprendizado de máquina interpretável serviu de
contraprova à forma funcional. O gap agregado foi de {pct(P['GAP_POOL'])}, dos
quais {pct(P['MED_BAIRRO'])} resultaram da mediação pelo bairro de moradia;
o diferencial que sobreviveu ao controle de capital humano, contexto e estado
foi de {pct(P['GAP_M3'])}, e {pct(P['GAP_M4'])} persistiram dentro da mesma
ocupação. A decomposição atribuiu {pct(P['OB_SEM_RET_PCT'])} do gap a retornos
diferenciais. O modelo de acesso estimou razão de chances de {_OR_CBO} para
cargo qualificado e {_OR_T10} para o décimo superior da renda, indicando
barreira que se agrava no topo. A desvantagem da mulher negra excedeu em
{pt(P['INT_PENAL_EXTRA'], 1)} pontos percentuais a soma das penalidades de raça
e de gênero isoladas. Concluiu-se que a discriminação operou sobretudo no
acesso à ocupação, e não apenas no salário, de modo que políticas centradas
apenas em escolaridade se mostraram insuficientes.
""" + r"""\end{singlespace}

\vspace{\baselineskip}
\noindent\textbf{Palavras-chave}: diferencial racial de rendimentos;
segregação residencial; teto de vidro; decomposição de Oaxaca--Blinder;
interseccionalidade.

\newpage

% ── Título em inglês + Abstract + Keywords ───────────────────────────────────
\begin{center}
{\fontsize{11}{14}\selectfont\bfseries
Structural racism in the Brazilian labour market: a multilevel and
wage-decomposition approach\par}
\end{center}

\vspace{\baselineskip}
\noindent\textbf{Abstract}
\vspace{\baselineskip}

\begin{singlespace}\noindent
""" + f"""This study examined the racial earnings differential and occupational access
barriers in Brazil using the complete series of the Brazilian Continuous
National Household Sample Survey, from 2016 to 2025, covering
{milhar(P['N_GLMM'])} observations of employed workers with positive earnings
in {milhar(P['N_UPAS'])} sampling units. Four methods were jointly applied: a
two-level hierarchical linear model, with individuals nested in neighbourhoods
and state fixed effects; an Oaxaca--Blinder decomposition; quantile regression
with recentred influence function decomposition; and a multilevel logistic
model of occupational access, estimated by maximum likelihood. An interpretable
machine learning model served as a functional-form check. The aggregate gap was
{pct(P['GAP_POOL'])}, of which {pct(P['MED_BAIRRO'])} was mediated by
neighbourhood of residence; the differential surviving controls for human
capital, context and state was {pct(P['GAP_M3'])}, and {pct(P['GAP_M4'])}
persisted within the same occupation. The decomposition attributed
{pct(P['OB_SEM_RET_PCT'])} of the gap to differential returns. The access model
estimated odds ratios of {_OR_CBO} for qualified occupations and {_OR_T10} for
the top income decile, indicating a barrier that tightens towards the top. The
disadvantage faced by Black women exceeded the sum of the separate race and
gender penalties by {pt(P['INT_PENAL_EXTRA'], 1)} percentage points. It was
concluded that discrimination operated mainly in access to occupations, not
only in wages, so that policies centred solely on schooling proved
insufficient.
""" + r"""\end{singlespace}

\vspace{\baselineskip}
\noindent\textbf{Keywords}: racial earnings gap; residential segregation; glass
ceiling; Oaxaca--Blinder decomposition; intersectionality.

\newpage
""")

INTRODUCAO = (r"""
\section{Introdução}

""" + f"""O Brasil é um dos países com maior desigualdade racial de renda no mundo, e a
razão entre o rendimento médio de trabalhadores brancos e negros permanece acima
de 1{{:}}1,5 em toda a série histórica disponível, mesmo quando se controlam
escolaridade, experiência e setor de atividade \\cite{{ibge_pnad_2023}}. A
explicação usual atribui esse hiato a diferenças de qualificação; se ela fosse
suficiente, a expansão do acesso ao ensino teria dissolvido o diferencial ao
longo das últimas décadas, o que não ocorreu \\cite{{hasenbalg1979}}. O quadro
recente reforça o ponto: a Pesquisa de Orçamentos Familiares [POF] registrou
queda de cerca de 30\\% no Índice de Perda de Qualidade de Vida entre 2008 e
2018, sem fechar o hiato racial \\cite{{ibge_pof_2019}}, enquanto o índice de
Gini do rendimento domiciliar per capita voltou a subir em 2025, puxado pelo
topo da distribuição \\cite{{ibge_rendimentos_2025}}.

A teoria econômica oferece duas explicações concorrentes para um diferencial que
sobrevive ao controle da produtividade observável, e elas implicam políticas
distintas. \\citeonline{{becker1957}} propôs a discriminação por preferência, em
que o empregador incorre em desutilidade ao contratar o grupo minoritário e, por
isso, só o faz a salário menor; nesse modelo, a concorrência tende a erodir a
prática. \\citeonline{{arrow1973}} formalizou a discriminação estatística, em que
a raça é usada como sinal da produtividade média do grupo sob informação
imperfeita; aqui o equilíbrio se autoconfirma, porque o menor retorno esperado
desestimula o investimento em qualificação. A tradição brasileira acrescenta uma
terceira leitura, na qual o racismo é processo estrutural reproduzido pelas
instituições independentemente da intenção dos agentes \\cite{{almeida2019}} —
leitura que justifica tratar a segregação residencial e a segregação ocupacional
como mecanismos, e não como controles estatísticos.

A literatura empírica identifica três canais de reprodução dessa desigualdade: a
discriminação direta em processos de seleção e promoção \\cite{{pager2007}}; os
efeitos de vizinhança, pelos quais a concentração de pobreza em bairros
segregados reduz as redes de contato com o mercado formal \\cite{{wilson1987,
sampson1997, marques2010}}; e a subvalorização do capital humano negro, pela qual
um mesmo nível de escolaridade rende menos \\cite{{henriques2001, soares2009}}.
Tratados isoladamente, esses mecanismos têm sido difíceis de quantificar de forma
integrada e em escala nacional, e é essa lacuna que o presente trabalho enfrenta.

Três hipóteses orientaram a investigação. A primeira supôs que parte relevante do
diferencial racial de rendimentos é mediada pelo contexto do bairro de moradia, e
não apenas por atributos individuais. A segunda supôs que a penalidade racial não
é uniforme ao longo da distribuição de renda, mas se agrava no topo, configurando
teto de vidro. A terceira supôs que a barreira opera antes do salário, no acesso
às ocupações qualificadas, de modo que trabalhadores negros com o mesmo perfil
observável enfrentam menor probabilidade de nelas ingressar.

O objetivo deste trabalho foi identificar, isolar e quantificar os mecanismos da
desigualdade racial de rendimentos e de acesso ocupacional no Brasil,
distinguindo a parcela atribuível a diferenças de características da parcela
atribuível a retornos diferenciais, e traduzindo o diagnóstico em implicações de
política focadas no acesso a ocupações qualificadas.

\\newpage
""")

CONCLUSAO = (r"""
\section{Conclusão}

""" + f"""A desigualdade racial no mercado de trabalho brasileiro não se reduziu a um
desconto salarial isolado: operou como um sistema de barreiras em camadas, que
começou antes do primeiro salário e persistiu ao longo da trajetória
profissional. Comparados trabalhadores de mesma escolaridade, idade, sexo e
bairro, o diferencial de rendimento foi de {pct(P['GAP_M3'])}, e
{pct(P['GAP_M4'])} permaneceram dentro da mesma ocupação — parcela que deve ser
lida como limite inferior, já que a própria ocupação é resultado da barreira de
acesso.

O achado mais relevante para o debate de políticas foi o da barreira de entrada.
Com o mesmo perfil observável e no mesmo bairro, trabalhadores negros tiveram
cerca de {_PCT_CBO}\\% menos chance de ocupar cargo qualificado e {_PCT_T10}\\%
menos chance de alcançar o décimo superior da renda. Aumentar a escolaridade sem
intervir nos mecanismos de seleção e promoção produz, portanto, retorno marginal
decrescente: as credenciais existem, mas os canais que as convertem em mobilidade
permanecem estreitos.

O contexto de moradia respondeu por {pct(P['MED_BAIRRO'])} do diferencial
agregado, o que indica que política de renda que ignore o território tem eficácia
limitada. A desvantagem da mulher negra excedeu em
{pt(P['INT_PENAL_EXTRA'], 1)} pontos percentuais a soma das penalidades de raça e
de gênero isoladas, de modo que intervenções desenhadas para um eixo de cada vez
deixam de fora justamente quem está na interseção.

Os resultados são estimativas de associação condicional, e não de efeito causal
no sentido contrafactual. Ainda assim, a convergência de quatro métodos
independentes sobre a população completa, a magnitude dos diferenciais e a
robustez a confundimento não observado sustentam o diagnóstico: a discriminação
operou sobretudo no acesso à ocupação, e políticas unidimensionais — centradas
apenas em escolaridade, apenas em fiscalização salarial ou apenas em cotas — são
insuficientes para desmontá-lo.
""")

FECHO = r"""
\newpage
\bibliography{relatorio_tcc}
\bibliographystyle{abntex2-alf}

\end{document}
"""
