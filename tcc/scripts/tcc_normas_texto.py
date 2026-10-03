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

from params_nucleo import P, milhar, pt
from params_nucleo import pct as _pct_bruto


def pct(x: float, d: int = 1) -> str:
    """Percentual escapado para LaTeX.

    `%` cru inicia comentário: tudo o que vem depois dele na linha some
    do PDF. Foi assim que o Resumo, o Abstract e a Conclusão saíram com
    frases truncadas ("o gap agregado foi de 19,1" e nada mais). O `pct`
    de params_nucleo continua cru porque serve também ao .docx e ao
    .pptx, onde a barra invertida apareceria no texto.
    """
    return _pct_bruto(x, d).replace("%", "\\%")


# ── formatação do Abstract (en-US) ───────────────────────────────────────────
# O Abstract é o único trecho em inglês, e lá a convenção se inverte: ponto
# decimal e vírgula de milhar. Escrito com as funções pt-BR, "7.694.198"
# observations é lido como um decimal, e "19,1%" não é número nenhum.
def en(x: float, d: int = 1) -> str:
    """Número no padrão inglês: 0.699, com menos tipográfico."""
    return f"{float(x):.{d}f}".replace("-", "−")


def en_pct(x: float, d: int = 1) -> str:
    return en(x, d) + "\\%"


def en_milhar(x: float) -> str:
    return f"{int(round(float(x))):,}"

_OR_CBO = pt(P["OR_ocp_qualif_M2"], 3)
_OR_T10 = pt(P["OR_y_top10_M2"], 3)
_OR_CBO_EN = en(P["OR_ocp_qualif_M2"], 3)
_OR_T10_EN = en(P["OR_y_top10_M2"], 3)
_PCT_CBO = pt((1 - P["OR_ocp_qualif_M2"]) * 100, 0)


def _conclusao_resumo(ingles: bool = False) -> str:
    """Fecho do Resumo/Abstract (aprovado em 03/10/2026), condicional à escada educacional:
    só afirma "diploma iguala o salário, não o acesso" se os números mostrarem isso."""
    sal_pos, ac_pos = P.get("NE_GAP_POS"), P.get("PCTPOS_ocp_qualif")
    padrao = sal_pos is not None and ac_pos is not None and sal_pos < 3 and ac_pos >= 10
    if ingles:
        if padrao:
            return ("It was concluded that racial inequality operates on two fronts that respond "
                    "differently to schooling: the wage penalty is largest among the least "
                    "educated and small among postgraduates, while the disadvantage in access to "
                    "qualified jobs persists at every level. Policies centred solely on schooling "
                    "reach the former but not the latter.")
        return ("It was concluded that racial inequality operates both in wages and in access to "
                "qualified occupations, so that policies centred solely on schooling are insufficient.")
    if padrao:
        return ("Concluiu-se que a desigualdade racial opera em duas frentes que respondem de modo "
                "diferente à escolaridade: a penalidade salarial é maior entre os menos "
                "escolarizados e pequena entre os pós-graduados, enquanto a desvantagem no acesso "
                "a cargos qualificados persiste em todos os níveis. Políticas centradas apenas em "
                "escolaridade alcançam a primeira, mas não a segunda.")
    return ("Concluiu-se que a desigualdade racial opera tanto no salário quanto no acesso a "
            "ocupações qualificadas, de modo que políticas centradas apenas em escolaridade são "
            "insuficientes.")


def _diploma_concl() -> str:
    """Abertura do parágrafo de políticas da Conclusão: o contraste diploma × porta, só se
    os números o mostrarem; senão, a abertura antiga (barreira de entrada)."""
    sal_pos, ac_pos = P.get("NE_GAP_POS"), P.get("PCTPOS_ocp_qualif")
    if sal_pos is not None and ac_pos is not None and sal_pos < 3 and ac_pos >= 10:
        return ("O achado mais relevante para o debate de políticas foi o contraste entre as duas "
                "barreiras diante da escolaridade. A penalidade salarial caiu de "
                f"{pct(P['NE_GAP_SEMFUND'])} entre quem não tem fundamental completo para "
                f"{pct(sal_pos)} na pós-graduação; a desvantagem de acesso, não: com pós-graduação, "
                f"as chances de chegar a um cargo qualificado seguiram {pct(ac_pos, 0)} menores. ")
    return "O achado mais relevante para o debate de políticas foi o da barreira de entrada.\n"


_DIPLOMA_CONCL = _diploma_concl()
_CONCLUSAO_RESUMO = _conclusao_resumo()
_CONCLUSAO_ABSTRACT = _conclusao_resumo(ingles=True)
_PCT_T10 = pt((1 - P["OR_y_top10_M2"]) * 100, 0)

PREAMBULO = r"""% ══════════════════════════════════════════════════════════════════════════════
% VERSÃO NORMATIVA — MBA USP/Esalq (Manual de Instruções e Normas, itens 15–19)
% Gerada por tcc/scripts/gerar_tcc_normas.py. NÃO editar à mão.
% ══════════════════════════════════════════════════════════════════════════════
\documentclass[11pt, a4paper, oneside]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[brazil]{babel}
% termos estrangeiros nao devem ser hifenizados pelas regras do portugues
\hyphenation{Scien-ce Ana-ly-tics boots-trap}
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
% Tabela 1. / Figura 1. — separador é ponto. A legenda vai no MESMO corpo do
% texto: o manual manda Arial 11 para todo o bloco da tabela e da figura,
% incluindo o título (itens 15.1 e 15.2), sem o corpo menor de praxe.
\captionsetup{labelfont=bf, labelsep=period,
              justification=justified, singlelinecheck=false, skip=6pt}
\usepackage{placeins}
\usepackage[alf, abnt-etal-list=5]{abntex2cite}
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
% cabeçalho do modelo (anexo, p. 61): texto justificado à esquerda em Arial 8
% e o logo do programa no canto superior direito
\fancyhead[L]{\parbox[b]{0.78\textwidth}{\fontsize{8}{10}\selectfont
  Trabalho de Conclusão de Curso apresentado para obtenção do título de
  especialista em Data\nolinebreak\ Science e Analytics -- 2026}}
\fancyhead[R]{\IfFileExists{outputs/figures/logo_mba_usp_esalq.png}
  {\includegraphics[height=0.9cm]{logo_mba_usp_esalq}}{}}
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
% ── Folha de rosto (manual, item 16.1 e anexo da p. 61) ──────────────────────
% Layout do modelo: cabeçalho, título logo abaixo, dois espaços de caractere
% até os autores, um espaço até a filiação. Espaçamento simples na folha toda.
\thispagestyle{fancy}
\begin{singlespace}

\begin{center}
{\fontsize{11}{13}\selectfont\bfseries
Racismo estrutural no mercado de trabalho brasileiro: uma abordagem multinível
e de decomposição salarial\par}
\end{center}

\vspace{2\baselineskip}      % dois espaços de caractere

\begin{center}
{\fontsize{11}{13}\selectfont
Ricardo Gomes Calheiros\textsuperscript{1*}; Edilson José Rodrigues\textsuperscript{2}\par}
\end{center}

\vspace{\baselineskip}       % um espaço de caractere

{\fontsize{9}{11}\selectfont
\noindent\textsuperscript{1*} Especialista em Finanças, Controladoria e Auditoria.
E-mail autor correspondente: rickinrj@gmail.com\par
\noindent\textsuperscript{2} Doutor em Engenharia Elétrica. MBA USP/Esalq.
E-mail: orientador@usp.br\par}

\end{singlespace}

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
{milhar(P['N_UPAS'])} bairros --- as unidades primárias de amostragem (UPAs) da própria
PNAD, setores censitários ou pequenos grupos de setores vizinhos. Quatro métodos foram aplicados de
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
e de gênero isoladas. {_CONCLUSAO_RESUMO}
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
{en_milhar(P['N_GLMM'])} observations of employed workers with positive earnings
in {en_milhar(P['N_UPAS'])} neighbourhoods --- the survey's own primary sampling units
(PSUs), census tracts or small clusters of adjacent tracts. Four methods were jointly applied: a
two-level hierarchical linear model, with individuals nested in neighbourhoods
and state fixed effects; an Oaxaca--Blinder decomposition; quantile regression
with recentred influence function decomposition; and a multilevel logistic
model of occupational access, estimated by maximum likelihood. An interpretable
machine learning model served as a functional-form check. The aggregate gap was
{en_pct(P['GAP_POOL'])}, of which {en_pct(P['MED_BAIRRO'])} was mediated by
neighbourhood of residence; the differential surviving controls for human
capital, context and state was {en_pct(P['GAP_M3'])}, and {en_pct(P['GAP_M4'])}
persisted within the same occupation. The decomposition attributed
{en_pct(P['OB_SEM_RET_PCT'])} of the gap to differential returns. The access model
estimated odds ratios of {_OR_CBO_EN} for qualified occupations and {_OR_T10_EN} for
the top income decile, indicating a barrier that tightens towards the top. The
disadvantage faced by Black women exceeded the sum of the separate race and
gender penalties by {en(P['INT_PENAL_EXTRA'], 1)} percentage points. {_CONCLUSAO_ABSTRACT}
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

Três hipóteses orientaram a investigação. A primeira (H1) supôs que parte relevante do
diferencial racial de rendimentos é mediada pelo contexto do bairro de moradia, e
não apenas por atributos individuais. A segunda (H2) supôs que a penalidade racial não
é uniforme ao longo da distribuição de renda, mas se agrava no topo, configurando
teto de vidro. A terceira (H3) supôs que a barreira opera antes do salário, no acesso
às ocupações qualificadas, de modo que trabalhadores negros com o mesmo perfil
observável enfrentam menor probabilidade de nelas ingressar.

O objetivo deste trabalho foi identificar, isolar e quantificar os mecanismos da
desigualdade racial de rendimentos e de acesso ocupacional no Brasil,
distinguindo a parcela atribuível a diferenças de características da parcela
atribuível a retornos diferenciais, e traduzindo o diagnóstico em implicações de
política focadas no acesso a ocupações qualificadas.

\\newpage
""")


def _retomada_hipoteses() -> str:
    """Veredito de cada hipótese conforme os números (nada afirmado de antemão)."""
    h1 = P["MED_BAIRRO"] > 0
    h2 = P["QR_GAP_Q90"] > P["QR_GAP_Q10"]
    h3 = P["CI_ocp_qualif_M2"][1] < 1
    partes = [
        (f"H1 encontrou respaldo: o bairro mediou {pct(P['MED_BAIRRO'])} do gap agregado"
         if h1 else "H1 não encontrou respaldo: comparar vizinhos não reduziu o gap"),
        (f"H2 encontrou respaldo nos quantis condicionais --- a penalidade passou de "
         f"{pct(P['QR_GAP_Q10'])} no primeiro decil para {pct(P['QR_GAP_Q90'])} no nono ---, "
         f"embora, na renda do país, a parcela não explicada pese mais na base"
         if h2 else
         f"H2 não encontrou respaldo: a penalidade condicional não cresceu rumo ao topo "
         f"({pct(P['QR_GAP_Q10'])} no primeiro decil, {pct(P['QR_GAP_Q90'])} no nono)"),
        (f"H3 encontrou respaldo: no mesmo bairro e com o mesmo perfil, as chances de "
         f"acesso a cargo qualificado foram {_PCT_CBO}\\% menores"
         if h3 else "H3 não encontrou respaldo: o intervalo da razão de chances inclui 1"),
    ]
    return "Retomando as hipóteses: " + "; ".join(partes) + "."


_RETOMADA_HIPOTESES = _retomada_hipoteses()

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

{_RETOMADA_HIPOTESES}

{_DIPLOMA_CONCL}Com o mesmo perfil observável e no mesmo bairro, trabalhadores negros tiveram
chances (\\emph{{odds}}) cerca de {_PCT_CBO}\\% menores de ocupar cargo qualificado e
{_PCT_T10}\\% menores de alcançar o décimo superior da renda. Aumentar a escolaridade sem
intervir nos mecanismos de seleção e promoção produz, portanto, retorno marginal
decrescente: as credenciais existem, mas os canais que as convertem em mobilidade
permanecem estreitos.

O contexto de moradia respondeu por {pct(P['MED_BAIRRO'])} do diferencial
agregado, o que indica que política de renda que ignore o território tem eficácia
limitada. A desvantagem da mulher negra excedeu em
{pt(P['INT_PENAL_EXTRA'], 1)} pontos percentuais a soma das penalidades de raça e
de gênero isoladas, de modo que intervenções desenhadas para um eixo de cada vez
deixam de fora justamente quem está na interseção.

A penalidade também não foi uniforme ao longo da distribuição: partiu de
{pct(P['QR_GAP_Q10'])} entre os que menos ganham e alcançou
{pct(P['QR_GAP_Q90'])} no decil superior (quantis condicionais: entre pessoas de mesmo
perfil observável), configurando o teto de vidro. A composição
dessa desvantagem, porém, inverteu-se ao longo da escala: na base, a maior
parte veio da remuneração desigual de características equivalentes
({pct(P['RIF_RET_Q10'])} do diferencial); no topo, essa parcela caiu a
{pct(P['RIF_RET_Q90'])}, e o que restou foi diferença de posição alcançada.
São dois problemas distintos sob o mesmo rótulo: preço do trabalho embaixo,
acesso ao posto em cima.

Daí decorre a implicação de política que este trabalho se propôs a formular.
As duas frentes pedem instrumentos diferentes: a desvantagem de ingresso em cargo
qualificado (chances {pt((1 - P['OR_ocp_qualif_M2']) * 100, 0)}\% menores,
{pt(abs(P['AME_ocp_qualif_M2']), 1)} pontos percentuais a menos) pede ação sobre seleção,
promoção e critérios de recrutamento; o diferencial salarial que resta dentro da mesma
ocupação ({pct(P['GAP_M4'])}) pede fiscalização de folha. Não se trata de escolher uma
das duas: são grandezas diferentes, e nenhuma substitui a outra. O alvo, porém, muda com o território: nas capitais a
desvantagem é semelhante em toda a escala de rendimento
({pct(P['QR_AREA_CAPITAL_Q50'])} na mediana e {pct(P['QR_AREA_CAPITAL_Q95'])} no
topo), e programas de base alcançam a maior parte do problema; no interior ela
quase dobra da mediana ao topo ({pct(P['QR_AREA_INTERIOR_Q50'])} para
{pct(P['QR_AREA_INTERIOR_Q95'])}), e o que está fechado é a chegada aos melhores
postos. Como indicador de acompanhamento, a própria probabilidade de acesso a
ocupação qualificada, estimada por bairro, é mensurável com a mesma base
pública e permite verificar se uma intervenção moveu a barreira que importa.

Os resultados são estimativas de associação condicional, e não de efeito causal
no sentido contrafactual. Ainda assim, a convergência de quatro métodos
independentes sobre a população completa, a magnitude dos diferenciais e a
robustez a confundimento não observado sustentam o diagnóstico: a desigualdade
operou no salário e no acesso, que respondem de modo diferente à escolaridade, e
políticas unidimensionais — centradas
apenas em escolaridade, apenas em fiscalização salarial ou apenas em cotas — são
insuficientes para desmontá-lo.
""")

FECHO = r"""
\newpage
\bibliography{relatorio_tcc}
\bibliographystyle{abntex2-alf}

\end{document}
"""
