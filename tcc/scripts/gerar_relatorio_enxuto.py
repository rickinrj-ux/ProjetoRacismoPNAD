"""
gerar_relatorio_enxuto.py
=========================
Pós-processa o relatório COMPLETO (relatorio_tcc.tex, gerado por
scripts/geradores/gerar_relatorio_tcc.py) e produz a VERSÃO ENXUTA do TCC
(núcleo de 4 métodos + robustez), conforme tcc/MANIFESTO_METODOS.md.

Opera no LaTeX já materializado (não no f-string do gerador), portanto é
seguro e reversível. O gerador completo permanece intacto (versão estendida
no branch mestrado-extenso).

O que faz:
  1. Remove as subseções do escopo ESTENDIDO (clustering, SNA, random slope,
     segregação espacial).
  2. Insere subseções de RESULTADOS para o NÚCLEO que hoje só aparecem na
     discussão (Oaxaca-Blinder, Quantílica/RIF, GLMM), com as tabelas .tex
     via \\input — atendendo ao pedido de "resultados em tabelas".
  3. Avisa sobre referências (\\ref) penduradas a rótulos removidos.

Entrada : relatorio_tcc.tex          (raiz)
Saída   : relatorio_tcc_enxuto.tex   (raiz; mesmas paths relativas de outputs/)
"""

# --- bootstrap raiz do projeto ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys, re
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from pathlib import Path

SRC = Path("relatorio_tcc.tex")
OUT = Path("relatorio_tcc_enxuto.tex")

if not SRC.exists():
    sys.exit("relatorio_tcc.tex não encontrado. Rode antes: "
             "python scripts/geradores/gerar_relatorio_tcc.py")

lines = SRC.read_text(encoding="utf-8").splitlines()

SEC_RE = re.compile(r"^\\(sub)?section\*?\{")

# Subseções a REMOVER (escopo estendido -> parqueado em mestrado-extenso)
REMOVER = [
    r"\subsection{Análise de redes sociais e capital social}",
    r"\subsection{Clustering Socioeconômico (K-Means)}",
    r"\subsection{Análise de Redes Sociais (SNA)}",
    r"\subsection{M3 com Inclinação Aleatória de Negro: Heterogeneidade Geográfica}",
    r"\subsection{Random Slope no GLMM: Heterogeneidade Geográfica do Acesso}",
    r"\subsection{Clustering Socioeconômico}",
    r"\subsection{Análise de Redes Sociais --- Isolamento Estrutural}",
    r"\subsection{Segregação Espacial: Inferência Bootstrap}",
]

# Blocos \paragraph{} de escopo estendido (PO regional, limitações de SNA/PO)
REMOVER_PARAGRAFOS = [
    r"\paragraph{Focalização territorial: Pesquisa Operacional regionalizada.}",
    r"\paragraph{Granularidade macroestrutural da SNA.}",
    r"\paragraph{Caráter normativo da Pesquisa Operacional.}",
]
PARA_RE = re.compile(r"^\\(paragraph|subsection|section)\*?\{")

# Âncora antes da qual inserimos as subseções de núcleo
ANCORA_NUCLEO = r"\subsection{Interseccionalidade: raça e gênero no acesso e no topo}"

BLOCO_NUCLEO = r"""% ── NÚCLEO: decomposições e acesso (inserido pela versão enxuta) ──
\noindent\rule{\textwidth}{1pt}
\textbf{\large BARREIRA II --- PENALIDADE SALARIAL E TETO DE VIDRO}
\textit{Para quem supera a porta de entrada, qual é o custo de ser negro?}
\noindent\rule{\textwidth}{1pt}

\medskip

\subsection{Decomposição do gap por mediação contextual e ocupacional}
A Tabela~\ref{tab:mediacao} resume o resultado central dos modelos HLM: à medida
que se adiciona o bairro (intercepto aleatório e contexto da UPA), o estado e a ocupação,
o gap racial encolhe de @@HLM_GAP_POOL@@\% (agregado) para @@HLM_GAP4@@\% (M4); o que resta
no M4 é a penalidade que nenhum atributo observável explica.
\input{outputs/tables/gap_mediacao_tcc.tex}

\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.92\textwidth]{fig_hlm_gap}
  \caption{@@TITULO_BAIRRO@@ --- e o que
  sobra não é explicado por escolaridade, idade, sexo, estado nem ocupação. Barras:
  $\hat\beta_{\text{negro}}$ de cada modelo; traço: IC~95\% (estreito pelo $N$ de milhões);
  rótulo: gap em \% de renda. Em azul, o M3 (gap líquido).}
  \label{fig:hlm_gap}
\end{figure}

\subsection{Decomposição de Oaxaca--Blinder: composição \emph{vs.}\ discriminação}
A decomposição de Oaxaca--Blinder separa o gap bruto de log-rendimento
(@@OB_GAP@@ log-pontos, ou @@OB_GAP_PCT@@\%) em uma parcela explicada por diferenças de
dotações e uma parcela não explicada (retornos diferenciais --- limite inferior da
discriminação). A Tabela~\ref{tab:oaxaca_blinder} apresenta duas especificações,
porque ocupação e formalidade são \emph{bad controls} \cite{angrist2009}:
são elas próprias resultado da discriminação. Em (A), com os controles do HLM~M3
(capital humano, jornada, contexto de UPA e estado), @@OB_A_COEF@@\% do gap não é
explicado por características observáveis; em (B), tratando também formalidade e grupo
CBO como dotações, a parcela não explicada cai para @@OB_B_COEF@@\% --- a
discriminação salarial \emph{dentro} da ocupação. A diferença entre as duas
(@@OB_DIF@@ pontos percentuais) é a parcela da discriminação que opera pela
\emph{porta de entrada} das ocupações, e não pelo salário --- exatamente o que o
GLMM de acesso mede adiante. Os erros-padrão vêm de bootstrap em blocos por UPA.

\paragraph{Pressupostos das regressões por grupo.} As duas regressões auxiliares
(brancos e negros) foram submetidas aos testes de Breusch--Pagan e RESET
\cite[cap.~12]{favero2024}. Há heterocedasticidade --- esperada em log-rendimento ---
mas de magnitude modesta: o $R^2$ da regressão auxiliar do Breusch--Pagan é @@BP_R2_B@@
(brancos) e @@BP_R2_N@@ (negros), e é justamente por isso que os erros-padrão são
agrupados por UPA e a decomposição usa bootstrap em blocos. O RESET rejeita a forma
funcional linear, mas o ganho de $R^2$ ao acrescentar potências do valor predito é de
@@RESET_B@@ (brancos) e @@RESET_N@@ (negros) --- irrelevante para a decomposição. Com $N$
de milhões, ambos os testes rejeitam qualquer hipótese nula pontual; o que importa é a
magnitude, não o $p$-valor \cite{angrist2009}.
\input{outputs/tables/ob_acesso.tex}

\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.95\textwidth]{fig_ob_cascata}
  \caption{Tratar a ocupação como ``característica'' reduz a discriminação medida de
  @@OB_A_COEF@@\% para @@OB_B_COEF@@\% do gap. Os @@OB_DIF@@ pontos que somem são a parte que
  opera na porta de entrada das ocupações --- medida diretamente pelo modelo de acesso.}
  \label{fig:ob_cascata}
\end{figure}

\subsection{Regressão Quantílica e RIF-OB: teto de vidro e \emph{sticky floor}}
A regressão quantílica estima o gap em cada ponto da distribuição de renda; a
RIF-OB separa, por quantil, dotação e retorno. A Tabela~\ref{tab:qr_melhorias}
mostra a penalidade \emph{condicional} crescendo rumo ao topo (teto de vidro entre
pessoas de mesmo perfil); a
Tabela~\ref{tab:rif_ob} revela o padrão complementar: o componente de retorno
(discriminação proporcional) é maior na base e \emph{decresce} rumo ao topo
(\emph{sticky floor}). \emph{Como ler:} na Tabela~\ref{tab:rif_ob}, Dotações $+$
Retornos $=100\%$ em cada quantil; siga a coluna Retornos caindo de $@@RIF_RET_Q10@@\%$ (q10)
a $@@RIF_RET_Q90@@\%$ (q90) --- a discriminação de preço pesa mais na base.
\input{outputs/tables/qr_melhorias.tex}
\input{outputs/tables/rif_decomp_tcc.tex}

\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.98\textwidth]{fig_qr_rif}
  \caption{Teto de vidro entre pares, piso pegajoso na renda do país: duas perguntas,
  dois padrões. À
  esquerda, a penalidade em quantis \emph{condicionais} cresce rumo ao topo (faixa: IC~95\%
  por bootstrap em blocos de UPA); à direita, a parcela não explicada dos quantis
  \emph{incondicionais} da renda é maior na base.}
  \label{fig:qr_rif}
\end{figure}

\subsection{GLMM logístico: o teto de vidro no acesso}
\label{subsec:glmm_resultados}
Até aqui a pergunta foi quanto um trabalhador negro ganha a menos. Ela pressupõe que
negros e brancos estejam disputando as mesmas vagas. E se a barreira for anterior ao
salário --- se ela estiver em \emph{quais} posições cada um consegue alcançar? É a
pergunta desta subseção, e ela importa porque muda o alvo da política: se a desigualdade
se produz no salário, o remédio é fiscalização de remuneração; se ela se produz no
acesso, nenhuma política salarial a alcança. Três desfechos respondem --- ocupar cargo
qualificado (CBO~1--4), estar no top~20\% e no top~10\% da renda ---, cada um estimado
em quatro degraus próprios, rotulados A1 a A4 para não se confundirem com os do HLM
---aos quais não correspondem um a um---, com intercepto aleatório de UPA e efeitos fixos
de UF.\footnote{\texttt{lme4::glmer} com \texttt{nAGQ = 0} --- os efeitos fixos são estimados
junto com os modos condicionais, aproximação mais rápida que a de Laplace e adequada a $N$
de milhões ---, sobre a população completa.
Os degraus são: A1 individual; A2 $+$ contexto do bairro; A3 $+$ vínculo (formalidade,
setor público, conta própria, doméstico), que é desfecho da própria discriminação e por
isso faz do A3 um limite inferior; A4 $+$ interação \texttt{negro}$\times$credencial. A
Tabela~\ref{tab:glmm_glassceil} traz \emph{odds ratios}, efeitos marginais, ICC e
E-values; a Tabela~\ref{tab:glmm_ajuste}, o ajuste e a classificação.}

\paragraph{O acesso também é ``bairro''.}
A primeira coisa que o modelo mostra é que a lógica territorial do HLM se repete aqui.
Entre \textbf{@@G_ICC_CBO_M1_PCT@@\% e @@G_ICC_T10_M1_PCT@@\% da variância latente do
acesso está entre bairros}\footnote{Correlação intraclasse latente do M1:
@@G_ICC_CBO_M1@@ para o cargo qualificado e @@G_ICC_T10_M1@@ para o top~10\%, com
ICC $= \tau^2/(\tau^2+\pi^2/3)$. O teste de razão de verossimilhança contra o logit sem
efeito aleatório dá LR $=$ @@G_LR_CBO@@ para o cargo e @@G_LR_T10@@ para o top~10\%
(1~g.l., $p<0{,}001$).} --- ou seja, saber apenas em que bairro alguém mora já antecipa
boa parte da chance de essa pessoa chegar a um cargo qualificado, antes de se conhecer
sua escolaridade. E a fração é maior para o top~10\% do que para o cargo qualificado:
quanto mais alto o degrau, mais o endereço pesa.

\paragraph{A porta é mais estreita para negros --- e estreita ainda mais no topo.}
Comparando pessoas do mesmo bairro, com a mesma escolaridade, sexo, idade e estado,
a chance de um trabalhador negro ocupar cargo qualificado é
OR~$=$~@@G_OR_CBO_M2@@\footnote{IC~95\% @@G_CI_CBO_M2@@. \emph{Odds ratio} abaixo de~1 é
desvantagem; acima de~1, vantagem.} da chance de um branco --- \textbf{chances (\emph{odds})
@@G_PCT_CBO_M2@@\% menores}. Traduzido para probabilidade, que é a medida a reter
\cite{angrist2009}, são \textbf{@@G_AME_CBO_M2@@ pontos percentuais} a menos de chegar
lá. E a desvantagem cresce à medida que se sobe na renda: para chegar ao top~10\% ---
que já não é o acesso a uma ocupação, mas a uma faixa de rendimento --- o OR cai para
@@G_OR_T10_M2@@, \textbf{chances @@G_PCT_T10_M2@@\% menores}. Não é o mesmo fenômeno do
salário visto de outro ângulo --- é uma barreira que age antes, na distribuição das
posições, e que nenhuma política de remuneração igual alcançaria.

Em síntese, a desigualdade racial no mercado de trabalho brasileiro não começa
só no contracheque: começa também na porta.

\paragraph{Vínculo e credencial não desfazem a barreira.}
Duas explicações alternativas se apresentam naturalmente, e o modelo testa as duas. A
primeira é a informalidade: a barreira seria um artefato de negros estarem mais em
vínculos precários. Descontar o vínculo (A3) praticamente não move o OR do cargo
qualificado (@@G_OR_CBO_M3@@) nem o do top~10\% (@@G_OR_T10_M3@@), de modo que não é
isso. A segunda é o diploma: bastaria credenciar-se. A interação
\texttt{negro}$\times$credencial do A4 é de @@G_ORI_SUP_CBO@@ para o superior completo e
@@G_ORI_POS_CBO@@ para a pós-graduação --- @@G_INTER_TXT@@ ---, e o OR combinado de um
trabalhador negro com superior completo ainda é @@G_OR_CBO_SUP@@. A credencial não
neutraliza a barreira. A Figura~\ref{fig:glmm_or} reúne as razões
de chance dos três desfechos e dos modelos de cada um.

\paragraph{Quão forte teria de ser um confundidor omitido.}
O modelo separa bem quem acessa de quem não acessa\footnote{AUC de @@G_AUC_CBO_M2@@ com
efeitos aleatórios e @@G_AUCFE_CBO_M2@@ só com efeitos fixos, para o cargo qualificado;
no \emph{cutoff} de Youden (@@G_CUT_CBO_M2@@), sensibilidade @@G_SENS_CBO_M2@@ e
especificidade @@G_ESP_CBO_M2@@. O teste de Hosmer--Lemeshow rejeita a calibração
perfeita em todos os degraus --- inevitável com $N$ de milhões \cite{angrist2009} ---,
mas a estatística @@G_HL_QUEDA@@ ao se acrescentar o vínculo (A3).}, mas a
pergunta que interessa não é essa: é se a desvantagem poderia ser obra de algo que o
modelo não viu. O E-value responde quanto um confundidor omitido teria de ser forte para
anular o resultado, e aqui ele vale \textbf{@@G_EV_CBO_M2@@}: seria preciso uma
característica não medida associada tanto a ser negro quanto a ocupar cargo qualificado
com razão de risco de pelo menos @@G_EV_CBO_M2@@ em ambas as pontas (com o desfecho comum, a
razão de chances é convertida em razão de risco pela raiz quadrada). É uma associação
modesta --- a escolaridade, sozinha, tem efeito muito maior sobre o acesso ---, e por isso o
E-value não basta para descartar viés: o que sustenta o resultado é ele sobreviver ao
contexto de bairro e ao teste de Konfound do modelo de renda. Por fim,
o logit com efeitos fixos de UF e erro-padrão agrupado por UPA (última coluna da
Tabela~\ref{tab:glmm_glassceil}) @@G_FE_TXT@@

\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.95\textwidth]{fig_glmm_or}
  \caption{A porta é mais estreita para trabalhadores negros --- e estreita ainda mais no
  topo da renda. Razão de chances de acesso (negro \emph{vs.}\ branco do mesmo bairro) com
  IC~95\%, por desfecho e degrau; em azul, o modelo com contexto de bairro (A2).}
  \label{fig:glmm_or}
\end{figure}

\input{outputs/tables/glmm_glassceil.tex}
\input{outputs/tables/glmm_ajuste.tex}

"""

# Resumo (PT) e Abstract (EN) reescritos para o núcleo de 4 + robustez (SHAP).
# Substituem os blocos do gerador completo (que descreve K-Means/SNA/TOPSIS) sem
# tocar no gerador — sobrevivem à regeração. O % de Oaxaca (83,8/16,2) vem da tabela
# ob_acesso.tex (especificação de acesso, com ocupação). Ver tcc/PERICIA.md F1: o
# 24,8/75,2 era a especificação Mincer puro (sem ocupação), divergente da narrativa.
RESUMO_PT = r"""\begin{abstract}
\noindent
Este trabalho investiga o \textit{gap} salarial racial e as barreiras estruturais
à progressão de carreira de profissionais negros no Brasil, combinando econometria
multinível e métodos de decomposição salarial sobre a série histórica completa da
Pesquisa Nacional por Amostra de Domicílios Contínua (PNAD Contínua) de 2016 a 2025
(@@P:N_BRUTO:1:milhoes@@~milhões de observações brutas). A estratégia empírica articula quatro métodos
complementares --- modelo linear hierárquico (HLM), decomposição de Oaxaca--Blinder,
regressão quantílica com decomposição RIF e modelo logístico multinível (GLMM) ---,
validados por \textit{machine learning} interpretável (XGBoost + SHAP).

Um modelo linear hierárquico de dois níveis (indivíduos em bairros --- UPA ---, com
efeitos fixos de estado) mostra que @@HLM_ICC0_PCT@@\% da variância do log-rendimento está
entre bairros e estima que profissionais negros recebem, em média, @@HLM_GAP_POOL@@\% a menos
que brancos comparáveis em escolaridade, sexo e idade. Desse diferencial, @@HLM_MED_BAIRRO@@\%
é mediado pelo contexto de moradia (nível~2), reduzindo o \textit{gap} líquido --- não
explicado por capital humano, bairro nem estado, limite superior da penalidade
direta sob seleção em observáveis --- a @@HLM_GAP3@@\%.

A decomposição de Oaxaca--Blinder atribui @@OB_A_COEF@@\% do gap bruto a retornos
diferenciais não explicados por capital humano e contexto; quando a ocupação e a
formalidade são tratadas como dotações, essa parcela cai para @@OB_B_COEF@@\% ---
limite inferior da discriminação salarial \emph{dentro} da ocupação, pois o acesso
à ocupação é ele próprio desigual. A decomposição RIF por quantil mostra um padrão de
\textit{sticky floor}: esse componente de retorno é maior na base da distribuição
(@@RIF_RET_Q10@@\% no q10) e decresce rumo ao topo (@@RIF_RET_Q90@@\% no q90). A desigualdade opera,
portanto, também no \emph{acesso} às ocupações --- canal que o GLMM mede diretamente.

O GLMM logístico de acesso (intercepto aleatório de UPA) confirma o teto de vidro
ocupacional: controlados escolaridade, sexo, idade, estado e contexto do bairro,
trabalhadores negros têm \textit{odds} de acesso a cargo qualificado de @@G_OR_CBO_M2@@
(IC~95\% @@G_CI_CBO_M2@@) das de brancos do mesmo bairro, que se apertam para
@@G_OR_T10_M2@@ no topo~10\% da renda; o E-value de~@@G_EV_CBO_M2@@ indica robustez a
confundidores não observados.
O \textit{machine learning} (XGBoost + SHAP) corrobora, sem pressuposto de forma
funcional, que a variável racial mantém contribuição negativa direta mesmo após todos
os controles e que o contexto territorial figura entre os preditores de maior peso ---
evidência de que a segregação residencial é um canal relevante da desigualdade, e não
mero atributo individual. A penalidade recai de forma agravada sobre a mulher negra,
na intersecção de raça e gênero.

\bigskip
\noindent\textbf{Palavras-chave:} gap salarial racial; discriminação estrutural;
modelos hierárquicos lineares; decomposição de Oaxaca--Blinder; regressão quantílica;
teto de vidro; SHAP values; PNAD Contínua.
\end{abstract}"""

ABSTRACT_EN = r"""\begin{abstract}
\noindent
This study investigates the racial wage gap and structural barriers to career
progression for Black professionals in Brazil, combining multilevel econometrics and
wage-decomposition methods on the full historical series of Brazil's Continuous
National Household Sample Survey (PNAD Contínua) from 2016 to 2025 (@@P:N_BRUTO:1:milhoes_en@@~million raw
observations). The empirical strategy articulates four complementary methods --- a
hierarchical linear model (HLM), the Oaxaca--Blinder decomposition, quantile
regression with RIF decomposition, and a multilevel logistic model (GLMM) ---,
validated by interpretable machine learning (XGBoost + SHAP).

A two-level hierarchical linear model (individuals nested in neighbourhoods --- census
tracts ---, with state fixed effects) shows that @@HLM_ICC0_PCT_EN@@\% of the variance of
log earnings lies between neighbourhoods and estimates that Black workers earn
@@HLM_GAP_POOL_EN@@\% less than comparable White workers after controlling for education,
sex, and age. Of this differential, @@HLM_MED_BAIRRO_EN@@\% is
mediated by residential context (level~2), leaving a \textit{net gap} of @@HLM_GAP3_EN@@\%
unexplained by human capital or context --- a lower bound on direct labour-market
discrimination.

The Oaxaca--Blinder decomposition attributes @@OB_A_COEF_EN@@\% of the raw gap to
differential returns unexplained by human capital and context; once occupation and
formality are treated as endowments, this share falls to @@OB_B_COEF_EN@@\% --- a lower
bound on within-occupation wage discrimination, since access to occupations is itself
unequal. The quantile RIF decomposition reveals a
\textit{sticky floor}: this returns component is largest at the bottom of the
distribution (@@P:RIF_RET_Q10:1:en@@\% at q10) and declines toward the top (@@P:RIF_RET_Q90:1:en@@\% at q90). Inequality
thus also operates on \emph{access} to occupations --- which the GLMM measures directly.

The multilevel logistic model (random intercept by census tract) confirms an
occupational glass ceiling: controlling for education, sex, age, state, and neighbourhood
context, Black workers face odds of accessing a qualified occupation of @@G_OR_CBO_M2_EN@@
(95\% CI @@G_CI_CBO_M2_EN@@) relative to White workers from the same neighbourhood,
tightening to @@G_OR_T10_M2_EN@@ in the top 10\% of income; an E-value of
@@G_EV_CBO_M2_EN@@ indicates robustness to unobserved confounding. Interpretable
machine learning (XGBoost + SHAP) corroborates --- with no functional-form assumption
--- that race retains a direct negative contribution after all controls and that
territorial context ranks among the strongest predictors, indicating that residential
segregation is a relevant channel of inequality rather than a mere individual trait.
The penalty falls most heavily on Black women, at the intersection of race and gender.

\bigskip
\noindent\textbf{Keywords:} racial wage gap; structural discrimination; hierarchical
linear models; Oaxaca--Blinder decomposition; quantile regression; glass ceiling;
SHAP values; PNAD Contínua.
\end{abstract}"""

NOTA_CABECALHO = (
    "% ╔══════════════════════════════════════════════════════════════════════╗\n"
    "% ║ VERSÃO ENXUTA DO TCC — núcleo de 4 métodos + robustez.                ║\n"
    "% ║ Gerada automaticamente por tcc/scripts/gerar_relatorio_enxuto.py.     ║\n"
    "% ║ NÃO editar à mão: edite o gerador completo e reexecute o pós-proc.    ║\n"
    "% ║ Versão estendida (todos os métodos): branch mestrado-extenso.         ║\n"
    "% ╚══════════════════════════════════════════════════════════════════════╝\n"
)


def _remove_bloco(lines, titulo, boundary_re):
    """Remove do título (inclusive) até a próxima fronteira (exclusive)."""
    try:
        ini = lines.index(titulo)
    except ValueError:
        print(f"  [AVISO] bloco não encontrado (já removido?): {titulo}")
        return lines, []
    fim = ini + 1
    while fim < len(lines) and not boundary_re.match(lines[fim]):
        fim += 1
    removidas = lines[ini:fim]
    rotulos = []
    for ln in removidas:
        rotulos += re.findall(r"\\label\{([^}]*)\}", ln)
    return lines[:ini] + lines[fim:], rotulos


def remove_subsecao(lines, titulo):
    return _remove_bloco(lines, titulo, SEC_RE)


def remove_paragrafo(lines, titulo):
    return _remove_bloco(lines, titulo, PARA_RE)


def remove_figuras_por_conteudo(lines, agulhas):
    """Remove blocos \\begin{figure}..\\end{figure} cujo conteúdo cite método
    parqueado (ex.: figura de clustering solta fora da subseção removida)."""
    out, i, rotulos = [], 0, []
    while i < len(lines):
        if lines[i].lstrip().startswith(r"\begin{figure}"):
            j = i
            while j < len(lines) and not lines[j].lstrip().startswith(r"\end{figure}"):
                j += 1
            bloco = "\n".join(lines[i:j + 1])
            if any(a in bloco for a in agulhas):
                for ln in lines[i:j + 1]:
                    rotulos += re.findall(r"\\label\{([^}]*)\}", ln)
                print(f"  - figura removida (contém: "
                      f"{next(a for a in agulhas if a in bloco)})")
                i = j + 1
                continue
        out.append(lines[i])
        i += 1
    return out, rotulos


def inserir_apos_linha(texto, ancora, bloco):
    """Insere `bloco` logo após a linha que contém `ancora`."""
    i = texto.find(ancora)
    if i < 0:
        return texto, 0
    j = texto.find("\n", i)
    return texto[:j + 1] + bloco + "\n" + texto[j + 1:], 1


def inserir_apos_envfim(texto, label, fim_tok, bloco):
    """Encontra `label`, depois o próximo `fim_tok` (ex.: \\end{figure}) e
    insere `bloco` logo após — para anexar legenda 'Como ler' a figura/tabela."""
    i = texto.find(label)
    if i < 0:
        return texto, 0
    j = texto.find(fim_tok, i)
    if j < 0:
        return texto, 0
    k = j + len(fim_tok)
    return texto[:k] + "\n" + bloco + texto[k:], 1


print("Removendo subseções do escopo estendido…")
rotulos_removidos = []
for t in REMOVER:
    lines, rots = remove_subsecao(lines, t)
    if rots:
        rotulos_removidos += rots
    print(f"  - {t.split('{',1)[1][:-1]}")

print("Removendo parágrafos de escopo estendido (PO regional, limitações SNA/PO)…")
for t in REMOVER_PARAGRAFOS:
    lines, rots = remove_paragrafo(lines, t)
    if rots:
        rotulos_removidos += rots
    print(f"  - {t.split('{',1)[1][:-1]}")

# Inserir bloco de núcleo antes da interseccionalidade
print("Removendo figuras soltas de métodos parqueados…")
lines, rots = remove_figuras_por_conteudo(lines, ["kmeans", "sna_", "segreg_"])
rotulos_removidos += rots

print("Inserindo subseções de núcleo (Oaxaca, Quantílica/RIF, GLMM)…")
try:
    idx = lines.index(ANCORA_NUCLEO)
    lines = lines[:idx] + BLOCO_NUCLEO.splitlines() + lines[idx:]
except ValueError:
    sys.exit("Âncora de núcleo não encontrada — abortando para não inserir no lugar errado.")

texto = NOTA_CABECALHO + "\n".join(lines) + "\n"

# Declara caracteres Unicode usados em TEXTO pelas tabelas/prosa do núcleo que o
# pdflatex (inputenc utf8) não conhece por padrão — evita "Unicode character not
# set up for use with LaTeX". O preâmbulo já declara 2212 (−); acrescentamos os demais.
print("Declarando caracteres Unicode adicionais (Δ, →, ²)…")
_uni = ("\\DeclareUnicodeCharacter{0394}{$\\Delta$}\n"
        "\\DeclareUnicodeCharacter{2192}{$\\rightarrow$}\n"
        "\\DeclareUnicodeCharacter{00B2}{\\textsuperscript{2}}\n"
        # \note é usado por qr_melhorias.tex (tabela estendida) mas não é definido
        # no preâmbulo; define-se como nota de rodapé de tabela.
        "\\providecommand{\\note}[1]{\\par\\smallskip{\\footnotesize\\textit{#1}}}")
texto, _nu = inserir_apos_linha(texto, r"\DeclareUnicodeCharacter{2212}{$-$}", _uni)
if _nu != 1:
    print(f"  [AVISO] âncora 2212 não encontrada (n={_nu}) — declarações não inseridas.")

# Fix abntex2cite+hyperref+article: o hyperref (carregado após abntex2cite)
# sobrescreve \@lbibitem e perde o \gdef\abntnextkey, fazendo as citações alf
# saírem "(??)". Reinjeta-se \abntnextkey envolvendo o \@lbibitem/\@bibitem vigentes.
print("Corrigindo citações abntex2cite+hyperref (evita '(??)')…")
_bibfix = (
    "\n% Fix abntex2cite+hyperref+article: reinjeta \\abntnextkey (citações alf)\n"
    "\\makeatletter\n"
    "\\let\\ABCIorig@lbibitem\\@lbibitem\n"
    "\\def\\@lbibitem[#1]#2{\\gdef\\abntnextkey{#2}\\ABCIorig@lbibitem[#1]{#2}}\n"
    "\\let\\ABCIorig@bibitem\\@bibitem\n"
    "\\def\\@bibitem#1{\\gdef\\abntnextkey{#1}\\ABCIorig@bibitem{#1}}\n"
    "\\makeatother")
texto, _nb = inserir_apos_linha(texto, r"]{hyperref}", _bibfix)
if _nb != 1:
    print(f"  [AVISO] âncora hyperref não encontrada (n={_nb}) — fix de citação não aplicado.")

# Substitui resumo (PT) e abstract (EN) pelas versões alinhadas ao núcleo.
# EN primeiro (ancorado no \renewcommand) para não confundir com o PT.
print("Reescrevendo resumo (PT) e abstract (EN) para o núcleo…")
texto, n_en = re.subn(
    r"(\\renewcommand\{\\abstractname\}\{Abstract\}\s*)\\begin\{abstract\}.*?\\end\{abstract\}",
    lambda m: m.group(1) + ABSTRACT_EN, texto, count=1, flags=re.S)
texto, n_pt = re.subn(
    r"\\begin\{abstract\}.*?\\end\{abstract\}",
    lambda m: RESUMO_PT, texto, count=1, flags=re.S)
if n_pt != 1 or n_en != 1:
    print(f"  [AVISO] substituição inesperada (PT={n_pt}, EN={n_en}) — revisar manualmente.")

# Neutraliza a afirmação "renda média da UPA é o preditor mais importante" (problema do
# reflexo, Manski 1993) — sobrevive do gerador completo (não suavizado). Ver PERICIA F3.
print("Neutralizando afirmação de 'preditor mais importante' (problema do reflexo)…")
_repl_shap = (
    "figura entre os preditores de maior peso do rendimento individual "
    "($|\\text{SHAP}| = 0.275$). Trata-se, porém, de preditor parcialmente endógeno "
    "(problema do reflexo, Manski 1993), pois agrega o próprio indivíduo, o que recomenda "
    "interpretá-lo como evidência de mediação territorial e não como determinante causal isolado.")
texto, n_shap = re.subn(
    r"é o preditor mais importante do rendimento individual.*?2,5 vezes maior que o gênero\.",
    lambda m: _repl_shap, texto, count=1, flags=re.S)
if n_shap != 1:
    print(f"  [AVISO] frase 'preditor mais importante' não neutralizada (n={n_shap}).")

# Tabela interseccional (pedido do orientador: resultado em tabela, não só figura)
# + legenda "Como ler" das figuras/tabelas (tabelas e gráficos).
print("Inserindo tabela interseccional e legendas 'Como ler'…")
texto, n_it = inserir_apos_linha(
    texto,
    r"\subsection{Interseccionalidade: raça e gênero no acesso e no topo}",
    r"\input{outputs/tables/ob_interseccional_tcc.tex}")

LEGENDAS = [
    # Divisão de trabalho (SWD-55/56): o título da figura afirma o achado; a nota
    # "Como ler" explica só a mecânica — o que é cada barra, faixa ou linha de
    # referência. A nota nunca repete a conclusão.
    (r"\label{fig:hlm_gap}", r"\end{figure}",
     r"\noindent\emph{Como ler a Figura~\ref{fig:hlm_gap}:} cada barra é um modelo da "
     r"sequência e, de cima para baixo, acrescenta-se um bloco de controles ao anterior. "
     r"O comprimento da barra é a penalidade racial em log-rendimento e o rótulo dentro "
     r"dela, a mesma penalidade em \% de renda; o traço fino é o intervalo de confiança de "
     r"95\% com erro-padrão agrupado por UPA. Em azul, o M3 --- o gap líquido."),
    (r"\label{fig:ob_cascata}", r"\end{figure}",
     r"\noindent\emph{Como ler a Figura~\ref{fig:ob_cascata}:} cada painel é uma cascata "
     r"lida da esquerda para a direita. A primeira barra é o gap total em log-rendimento; "
     r"a segunda desconta a parcela atribuída a diferenças de características (dotações); "
     r"a terceira, em azul, é o que sobra sem explicação. A única diferença entre os "
     r"painéis é se a ocupação entra ou não como característica."),
    (r"\label{fig:qr_rif}", r"\end{figure}",
     r"\noindent\emph{Como ler a Figura~\ref{fig:qr_rif}:} à esquerda, cada ponto é a "
     r"penalidade racial estimada num quantil \emph{condicional} $\tau$ (eixo vertical em "
     r"log-pontos $\times100$), e a faixa é o intervalo de 95\% por bootstrap em blocos de "
     r"UPA. À direita, cada barra é um quantil \emph{incondicional} da renda e soma 100\%: "
     r"a parte azul é a parcela não explicada, com o valor escrito dentro."),
    (r"\label{fig:glmm_or}", r"\end{figure}",
     r"\noindent\emph{Como ler a Figura~\ref{fig:glmm_or}:} cada ponto é uma razão de "
     r"chances e a linha horizontal, seu intervalo de confiança de 95\%; a linha tracejada "
     r"em~1 marca a paridade, de modo que quanto mais à esquerda, maior a desvantagem. Os "
     r"blocos são os três desfechos e, dentro de cada um, os modelos; em azul, o A2, que "
     r"compara pessoas do mesmo bairro."),
    (r"\label{fig:shap_wf}", r"\end{figure}",
     r"\noindent\emph{Como ler a Figura~\ref{fig:shap_wf}:} cada linha é uma variável de "
     r"\textbf{um} trabalhador --- não de uma média. A barra mostra quanto aquela variável "
     r"empurra a previsão para cima ou para baixo, partindo da previsão média da base até "
     r"a previsão final do caso. Compare a linha \emph{Raça (negro)} nos dois painéis: "
     r"é a mesma variável, com o sinal trocado --- soma no branco, subtrai no negro. "
     r"Serve para ver como o modelo compõe uma decisão, não para generalizar: a "
     r"magnitude média está na Figura~\ref{fig:shap}, sobre os 50 mil casos."),
    (r"\label{fig:shap}", r"\end{figure}",
     r"\noindent\emph{Como ler a Figura~\ref{fig:shap}:} cada ponto é um trabalhador; "
     r"quanto mais à direita (ou maior a barra), maior o efeito da variável na renda "
     r"prevista. A cor indica se o valor da variável é alto ou baixo."),
    (r"\label{fig:interseccional}", r"\end{figure}",
     r"\noindent\emph{Como ler a Figura~\ref{fig:interseccional}:} cada linha é um grupo "
     r"raça$\times$gênero e cada ponto, a razão de chances contra o homem branco, cuja "
     r"referência é a linha tracejada em 1; abaixo dela, o grupo tem menos chance que ele. "
     r"Siga a linha azul da esquerda para a direita: a mulher negra começa acima da "
     r"referência no acesso à categoria e termina como o grupo mais distante dela no topo "
     r"da renda."),
    (r"\label{tab:ml_perf}", r"\end{table}",
     r"\noindent\emph{Como ler a Tabela~\ref{tab:ml_perf}:} R\textsuperscript{2} mais alto "
     r"= melhor previsão; o \emph{gap} treino--teste próximo de zero indica ausência de "
     r"sobreajuste."),
    (r"\label{tab:shap_importance}", r"\end{table}",
     r"\noindent\emph{Como ler a Tabela~\ref{tab:shap_importance}:} variáveis ordenadas "
     r"pela importância média ($|\text{SHAP}|$); valores maiores = maior peso na previsão "
     r"da renda."),
]
n_leg = 0
for label, fim, nota in LEGENDAS:
    texto, n = inserir_apos_envfim(texto, label, fim, nota)
    n_leg += n
    if n == 0:
        print(f"  [AVISO] legenda não inserida para {label}")
print(f"  tabela interseccional={n_it}, legendas inseridas={n_leg}/{len(LEGENDAS)}")

# Tabela SHAP: vem do gerador completo com ponto decimal e mais larga que a mancha.
# Aqui ela é ajustada ao padrão do relatório (vírgula decimal) e encaixada na largura.
_i = texto.find(r"\label{tab:shap_importance}")
if _i > 0:
    _j = texto.index(r"\end{table}", _i) + len(r"\end{table}")
    _bloco = texto[_i:_j]
    if r"\resizebox" not in _bloco:
        _bloco = _bloco.replace(r"\begin{tabular}", "\\resizebox{\\textwidth}{!}{%\n\\begin{tabular}", 1)
        _bloco = _bloco.replace(r"\end{tabular}", "\\end{tabular}\n}", 1)
    _bloco = re.sub(r"(?<= )(\d)\.(\d+)(?= )", r"\1,\2", _bloco)   # 0.325 -> 0,325 (só células)
    texto = texto[:_i] + _bloco + texto[_j:]
    print("  tabela SHAP: vírgula decimal e resizebox aplicados")

# Frase truncada no gerador completo (já corrigida lá; aqui para não exigir regeração)
texto = re.sub(r"\\emph\{ampliar\} a base\s+de amostral para populacional \\emph\{reduz\}",
               r"\\emph{ampliar} a base, de amostral para populacional, \\emph{reduz}", texto)

# Bibliografia: as referências do núcleo são citadas como texto plano nas tabelas
# (VanderWeele & Ding, Oaxaca & Ransom, Firpo et al., Crenshaw, Manski...). Um \nocite
# garante que entrem na lista de referências. Ver tcc/PERICIA.md (bibliografia).
print("Inserindo \\nocite das referências do núcleo…")
NOCITE = (r"\nocite{oaxaca1973,blinder1973,oaxaca_ransom1999,koenker1978,firpo2018,cameron2008,bickel2008,"
          r"vanderweele2017,crenshaw1989,manski1993,becker1957,arrow1973,almeida2019,"
          r"geron2021}")
texto, n_nc = inserir_apos_linha(texto, r"\begin{document}", NOCITE)
if n_nc != 1:
    print(f"  [AVISO] \\nocite não inserido (n={n_nc}).")

# O gerador completo REESCREVE relatorio_tcc.bib com o seu BIB estático (20 entradas);
# as referências do núcleo (Oaxaca, Blinder, Koenker, Firpo, Angrist & Pischke, ...)
# vivem em tcc/scripts/bib_nucleo.bib e são anexadas aqui quando faltam (idempotente).
print("Completando relatorio_tcc.bib com as referências do núcleo…")
_bib_main = Path("relatorio_tcc.bib")
_bib_nucleo = Path(__file__).resolve().parent / "bib_nucleo.bib"
if _bib_main.exists() and _bib_nucleo.exists():
    _main_txt = _bib_main.read_text(encoding="utf-8")
    _keys_main = set(re.findall(r"^@\w+\{([^,]+),", _main_txt, flags=re.M))
    _entries = re.split(r"(?=^@\w+\{)", _bib_nucleo.read_text(encoding="utf-8"), flags=re.M)
    _add = [e for e in _entries if e.strip() and re.match(r"@\w+\{([^,]+),", e).group(1) not in _keys_main]
    if _add:
        _bib_main.write_text(_main_txt.rstrip() + "\n\n" + "\n".join(e.strip() + "\n" for e in _add), encoding="utf-8")
    print(f"  entradas anexadas: {len(_add)}")

# Patches de escopo, números e linguagem (tcc/scripts/enxuto_patches.py —
# TODO_revisao blocos 0/1/6/7.1). Cada patch avisa se não casar.
print("Aplicando patches de escopo/números (enxuto_patches.py)…")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import enxuto_patches
texto = enxuto_patches.aplicar(texto)

# Tabela de desempenho ML gerada a partir de outputs/tables/ml_performance.csv
# (fonte única — os valores manuais do gerador completo estavam desatualizados).
print("Regerando tabela de desempenho ML a partir do csv…")
import csv as _csv
_mlp = Path("outputs/tables/ml_performance.csv")
if _mlp.exists():
    with _mlp.open(encoding="utf-8", newline="") as _f:
        _rows = list(_csv.DictReader(_f))

    def _fmt(v):
        return f"{float(v):.4f}".replace(".", ",")

    _linhas = []
    for r in _rows:
        nome = r["Modelo"]
        cel = [_fmt(r["R²"]), _fmt(r["MAE"]), _fmt(r["RMSE"]), _fmt(r["gap_overfit"])]
        if nome == "XGBoost":
            nome = r"\textbf{XGBoost}"
            cel = [r"\textbf{" + c + "}" for c in cel]
        _linhas.append(f"{nome} & " + " & ".join(cel) + r" \\")
    _tab = ("\\begin{tabular}{lcccc}\n\\toprule\n"
            "\\textbf{Modelo} & $R^2$ & \\textbf{MAE} & \\textbf{RMSE} & "
            "\\textbf{Gap treino--teste} \\\\\n"
            "\\midrule\n" + "\n".join(_linhas) + "\n\\bottomrule\n\\end{tabular}")
    texto = texto.replace(
        "\caption{Desempenho preditivo --- Random Forest e XGBoost.",
        "\caption{Desempenho preditivo --- Random Forest, XGBoost e XGBoost sem renda de "
        "vizinhança (robustez ao problema do reflexo).")
    texto, _nml = re.subn(
        r"\\begin\{tabular\}\{lccc\}\s*\\toprule\s*\\textbf\{Modelo\} & \$R\^2\$ & "
        r"\\textbf\{MAE\} & \\textbf\{RMSE\} \\\\.*?\\end\{tabular\}",
        lambda m: _tab, texto, count=1, flags=re.S)
    if _nml != 1:
        print(f"  [AVISO] tabela ML não substituída (n={_nml}).")
else:
    print("  [AVISO] ml_performance.csv não encontrado — tabela ML mantida.")

def _rd0(name):
    _p = Path("outputs/tables") / name
    if not _p.exists():
        return []
    import csv as _c
    with _p.open(encoding="utf-8", newline="") as _f:
        return list(_c.DictReader(_f))


# 7.8 — balanceamento e suporte comum, logo após a descrição da base (MHE-11/28)
print("Inserindo a tabela de balanceamento…")
_BAL = r"""
\paragraph{De que é feita a comparação: balanceamento e suporte comum.}
Antes de qualquer controle, convém olhar em que brancos e negros diferem --- é o que
mostra a Tabela~\ref{tab:balanceamento}. O maior desequilíbrio não está em escolaridade
nem em horas: está em \emph{onde se mora}. A composição racial do bairro tem diferença
padronizada de @@BAL_D_UPA@@ desvios --- uma ordem de grandeza acima de qualquer variável
individual ---, seguida do desemprego local (@@BAL_D_DES@@) e da educação média do entorno
(@@BAL_D_EDU@@). É esse desequilíbrio que o nível~2 do modelo hierárquico absorve.
O suporte comum é amplo: @@BAL_UPA_MISTA@@\% das UPAs abrigam trabalhadores dos dois
grupos e todas as células UF~$\times$~escolaridade contêm brancos e negros, de modo que a
comparação não depende de extrapolação \cite{angrist2009}.
\input{outputs/tables/balanceamento.tex}
"""
texto, _nb2 = re.subn(r"(?=\\subsection\{Modelo Linear Hierárquico)", lambda m: _BAL + "\n", texto, count=1)
if _nb2 != 1:
    print(f"  [AVISO] tabela de balanceamento não inserida (n={_nb2}).")
_bal = {r["variavel"]: r for r in _rd0("balanceamento.csv")}
if _bal:
    def _pt0(x, d=2):
        return f"{float(x):.{d}f}".replace(".", ",").replace("-", "−")
    _bal_vals = {
        "@@BAL_D_UPA@@": _pt0(_bal["pct_negro_upa_z"]["d_cohen"]),
        "@@BAL_D_DES@@": _pt0(_bal["tx_desemprego_upa_z"]["d_cohen"]),
        "@@BAL_D_EDU@@": _pt0(_bal["media_educ_upa_z"]["d_cohen"]),
    }
    import csv as _c3
    with (Path("outputs/tables") / "balanceamento.tex").open(encoding="utf-8") as _f3:
        _t3 = _f3.read()
    _mm = re.search(r"(\d+,\d)\\% das UPAs", _t3)
    # sem valor de reserva: se a tabela mudar de formato, o marcador fica cru e o aviso
    # de marcadores não preenchidos dispara (um "97,3" fixo passaria calado)
    _bal_vals["@@BAL_UPA_MISTA@@"] = _mm.group(1) if _mm else "@@BAL_UPA_MISTA@@"
    for _k, _v in _bal_vals.items():
        texto = texto.replace(_k, _v)
if "@@BAL_" in texto:
    print("  [AVISO] placeholders @@BAL_...@@ não preenchidos!")

# 7.2 — página "Em três minutos" logo após o sumário (Knaflic, cap. 7: a história de
# três minutos e a estrutura Bing-Bang-Bongo). Números lidos dos placeholders já
# preenchidos acima, de modo que a página nunca desatualiza.
print("Inserindo a página \"Em três minutos\"…")
_TRES_MIN = r"""
\newpage
\section*{Em três minutos}
\addcontentsline{toc}{section}{Em três minutos}

\noindent\textbf{O contexto.} Entre 2016 e 2025, um trabalhador negro ganhou em média
@@HLM_GAP_POOL@@\% a menos que um branco com a mesma escolaridade, idade e sexo. A
explicação usual --- ``é diferença de qualificação'' --- já está descontada nesse número.

\medskip
\noindent\textbf{O desequilíbrio.} Esse gap não é uma coisa só. Quando se compara apenas
pessoas \emph{do mesmo bairro}, ele encolhe: @@HLM_MED_BAIRRO@@\% do gap
transita pela segregação residencial. O que resta --- @@HLM_GAP3@@\% --- não é explicado
por capital humano, bairro ou estado. E, ao olhar quem \emph{entra} nas ocupações
qualificadas, a barreira aparece inteira: com o mesmo perfil e o mesmo bairro, a chance de
um trabalhador negro ocupar um cargo qualificado é @@G_PCT_CBO_M2@@\% menor; no décimo
superior da renda, @@G_PCT_T10_M2@@\% menor.

\medskip
\noindent\textbf{A evidência.} Quatro métodos independentes, sobre a população completa da
PNAD Contínua (cerca de @@P:N_GLMM:1:milhoes@@~milhões de observações em @@N_UPAS@@ bairros --- o $N$
exato varia com os filtros de cada método e consta da sua tabela): um modelo hierárquico que
separa pessoa e bairro; a decomposição de Oaxaca--Blinder, que separa ``ter
características diferentes'' de ``receber preços diferentes''; a regressão quantílica com
RIF, que mostra onde na distribuição a penalidade pesa; e um modelo logístico multinível
de acesso. Um XGBoost com SHAP confirma, sem impor forma funcional, que a raça mantém
contribuição própria. Os erros-padrão são agrupados por bairro, porque a PNAD amostra por
conglomerados.

\medskip
\noindent\textbf{O que isso muda.} Se o gargalo fosse escolaridade, bastaria ampliar
acesso ao ensino. Os resultados dizem outra coisa: parte do gap está em \emph{onde se
consegue morar} e a maior parte da barreira está na \emph{porta de entrada} das ocupações
--- que é onde a Lei~15.142/2025 (cotas em concursos federais, sucessora da
Lei~12.990/2014) e a fiscalização da Lei~9.029/1995 atuam. Educação é
necessária; sozinha, insuficiente.

\medskip
\noindent\textit{As três seções seguintes detalham, nesta ordem: como o bairro medeia o
gap (Barreira~I), quanto custa ser negro para quem já está empregado (Barreira~II) e o que
os números não podem dizer (Limitações).}
"""
texto, _n3 = re.subn(r"(?=\\section\{Introdução\})", lambda m: _TRES_MIN + "\n", texto, count=1)
if _n3 != 1:
    print(f"  [AVISO] página 'Em três minutos' não inserida (n={_n3}).")
# N e UPAs para a página (do HLM step-up) — leitor local: _rd só é definido adiante
_fit0 = _rd0("hlm_stepup_fit.csv")
if _fit0:
    _n = int(float(_fit0[0]["n"]))
    texto = texto.replace("@@N_OBS@@", f"{_n:,}".replace(",", "."))
_se_rows2 = _rd0("rif_ob_se.csv")
_nupas = next((r.get("n_upas") for r in _se_rows2 if r.get("n_upas")), None)
if _nupas:
    texto = texto.replace("@@N_UPAS@@", f"{int(float(_nupas)):,}".replace(",", "."))

# Números da Oaxaca-Blinder a partir de outputs/tables/ob_acesso.csv (fonte única):
# (A) sem ocupação, (B) acesso. Placeholders @@OB_...@@ no Resumo/Abstract/subseção.
print("Preenchendo números da Oaxaca-Blinder (ob_acesso.csv)…")
_obp = Path("outputs/tables/ob_acesso.csv")
if _obp.exists():
    with _obp.open(encoding="utf-8", newline="") as _f:
        _ob = {r["espec"]: r for r in _csv.DictReader(_f)}
    _A, _B = _ob.get("sem_ocupacao"), _ob.get("acesso")
    if _A and _B:
        def _pt(x, d=1):
            return f"{float(x):.{d}f}".replace(".", ",")
        _vals = {
            "@@OB_GAP@@":       _pt(_A["gap_total"], 4),
            "@@OB_GAP_PCT@@":   _pt(_A["gap_pct"], 1),
            "@@OB_A_COEF@@":    _pt(_A["pct_coeficiente"]),
            "@@OB_B_COEF@@":    _pt(_B["pct_coeficiente"]),
            "@@OB_A_DOT@@":     _pt(_A["pct_dotacao"]),
            "@@OB_B_DOT@@":     _pt(_B["pct_dotacao"]),
            "@@OB_DIF@@":       _pt(float(_A["pct_coeficiente"]) - float(_B["pct_coeficiente"])),
            "@@OB_A_COEF_EN@@": f"{float(_A['pct_coeficiente']):.1f}",
            "@@OB_B_COEF_EN@@": f"{float(_B['pct_coeficiente']):.1f}",
        }
        for k, v in _vals.items():
            texto = texto.replace(k, v)
    else:
        print("  [AVISO] ob_acesso.csv sem as duas especificações — placeholders mantidos.")
else:
    print("  [AVISO] ob_acesso.csv não encontrado — placeholders mantidos.")
if "@@OB_" in texto:
    print("  [AVISO] placeholders @@OB_...@@ não preenchidos!")

# Z do contraste quantílico (q90−q10) a partir de qr_kb_test.csv — placeholder @@QR_Z@@
_kbp = Path("outputs/tables/qr_kb_test.csv")
if _kbp.exists():
    with _kbp.open(encoding="utf-8", newline="") as _f:
        _kb = next(iter(_csv.DictReader(_f)))
    texto = texto.replace("@@QR_Z@@", f"{float(_kb['z_stat']):.2f}".replace(".", "{,}"))
if "@@QR_Z@@" in texto:
    print("  [AVISO] placeholder @@QR_Z@@ não preenchido!")

# Subseção de Metodologia "Inferência: erros-padrão e pesos" (TODO 2.2/2.6 — MHE cap. 8),
# com os números de hlm_serie_completo_se.csv e hlm_serie_completo_ponderado.csv.
print("Inserindo subseção de inferência (SE agrupados, poucos clusters, pesos)…")
_sep = Path("outputs/tables/hlm_serie_completo_se.csv")
_pop = Path("outputs/tables/hlm_serie_completo_ponderado.csv")
_txt_num = ""
if _sep.exists():
    with _sep.open(encoding="utf-8", newline="") as _f:
        _se = [r for r in _csv.DictReader(_f)]
    def _get(modelo, var, col):
        for r in _se:
            if r["modelo"] == modelo and r["variavel"] == var:
                return float(r[col])
        return float("nan")
    _sc, _su, _sf = (_get("M3_Completo_OLS", "negro", c) for c in ("se_conv", "se_cl_upa", "se_cl_uf"))
    _gc, _gu, _gf = (_get("M3_Completo_OLS", "pct_negro_upa_z", c) for c in ("se_conv", "se_cl_upa", "se_cl_uf"))
    def _pt(x, d=4):
        return f"{x:.{d}f}".replace(".", ",")
    _txt_num = (
        r"No OLS com efeitos fixos de UF (especificação do M3), o erro-padrão de $\hat\beta_{\text{negro}}$ passa de "
        f"{_pt(_sc)} (convencional) para {_pt(_su)} (agrupado por UPA) e {_pt(_sf)} (agrupado por UF); "
        r"para o regressor de contexto $\overline{\%\text{Negro}}_{\text{UPA}}$, que varia apenas no nível "
        f"da UPA, a razão é de {_pt(_gu/_gc, 1)}$\\times$ (UPA) e {_pt(_gf/_gc, 1)}$\\times$ (UF) --- "
        r"a assinatura do efeito Moulton. Como $|\hat\beta_{\text{negro}}|/\text{SE}$ permanece acima de "
        f"{abs(_get('M3_Completo_OLS','negro','coef'))/_sf:.0f} mesmo no agrupamento mais conservador, "
        r"nenhuma conclusão sobre o gap racial depende da escolha do erro-padrão; a correção importa "
        r"para os coeficientes contextuais e para as variáveis de UF. ")
_txt_peso = ""
if _pop.exists():
    with _pop.open(encoding="utf-8", newline="") as _f:
        _pd_rows = list(_csv.DictReader(_f))
    if len(_pd_rows) == 2:
        _o, _w = _pd_rows
        def _pt2(x, d=4):
            return f"{float(x):.{d}f}".replace(".", ",")
        _txt_peso = (
            r"\paragraph{Pesos amostrais.} Os modelos são estimados sem o peso amostral da PNAD (V1028), "
            r"isto é, descrevem a regressão na amostra, não a regressão populacional "
            r"\cite{angrist2009}. Como robustez, o M3 foi reestimado por mínimos quadrados ponderados "
            r"com V1028 e erro-padrão agrupado por UPA: $\hat\beta_{\text{negro}}$ passa de "
            f"{_pt2(_o['b_negro'])} (MQO equivalente, sem pesos) para {_pt2(_w['b_negro'])} "
            f"(gap de {_pt2(abs(float(_o['Gap%'])), 1)}\\% para {_pt2(abs(float(_w['Gap%'])), 1)}\\%), "
            r"diferença sem relevância econômica; os demais resultados são não ponderados. "
        )
_SUBSEC = (
    r"\subsection{Inferência: erros-padrão agrupados, poucos clusters e pesos}" "\n"
    r"\label{subsec:inferencia}" "\n\n"
    r"A PNAD Contínua é uma amostra por conglomerados: pessoas da mesma unidade primária de "
    r"amostragem (UPA, proxy de bairro) compartilham choques não observados, e os regressores de "
    r"contexto variam apenas no nível da UPA. Tratar as $7{,}7$~milhões de observações como "
    r"independentes subestima os erros-padrão pelo fator de Moulton "
    r"$\sqrt{1+(\bar n-1)\rho}$ \cite{angrist2009}. Por isso, todos os modelos de regressão "
    r"(OLS com efeitos fixos de UF, decomposição de Oaxaca--Blinder, regressão quantílica e "
    r"logit) reportam erros-padrão \emph{agrupados por UPA} (@@N_UPAS@@ clusters) --- para a OB e a "
    r"regressão quantílica, por bootstrap em blocos de UPA. O agrupamento por UF é mais "
    r"conservador, mas com 27 clusters ($<42$) a inferência assintótica é pouco confiável "
    r"\cite{angrist2009}; quando reportado, usa a distribuição $t$ com $G-1$ graus de liberdade. "
    r"No HLM, o intercepto aleatório de UPA modela explicitamente a correlação intra-bairro, de modo "
    r"que o erro-padrão do modelo já a incorpora (sob a hipótese de efeitos aleatórios); como "
    r"contraprova, os coeficientes do HLM são comparados aos do OLS com efeitos fixos de UF e "
    r"erro-padrão agrupado por UPA, que coincidem em sinal, magnitude e significância. "
    + _txt_num + "\n\n" + _txt_peso + "\n\n"
    # A tabela recolhe num lugar só o que estava espalhado pelo texto: quem
    # avalia precisa ver de uma vez o que foi testado e o que se fez a respeito.
    + r"\paragraph{O conjunto das verificações.} A Tabela~\ref{tab:robustez} "
      r"reúne os diagnósticos aplicados ao longo do trabalho, o resultado de cada um e a "
      r"providência que ele motivou." "\n\n"
    + r"\input{outputs/tables/robustez}" "\n\n"
)
texto, _ni = re.subn(r"(?=\\subsection\{Random Forest, XGBoost e SHAP Values\})",
                     lambda m: _SUBSEC, texto, count=1)
if _ni != 1:
    print(f"  [AVISO] subseção de inferência não inserida (n={_ni}).")

# Números do HLM step-up (bloco 3) e do logit — placeholders @@HLM_...@@ / @@GLMM_...@@
print("Preenchendo números do HLM step-up e do logit…")
def _rd(name):
    _p = Path("outputs/tables") / name
    if not _p.exists():
        return []
    with _p.open(encoding="utf-8", newline="") as _f:
        return list(_csv.DictReader(_f))
_gap = {r["Modelo"]: r for r in _rd("gap_decomposicao_stepup.csv")}
_fit = {r["modelo"]: r for r in _rd("hlm_stepup_fit.csv")}
# robustez de três níveis: só existe se o modelo em R já tiver sido rodado
def _num3(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None            # o M0 é nulo: não tem b_negro
def _leitura_tres_camadas(n3) -> str:
    """E7.1: a frase antiga ("caem quase na mesma proporção", "duas vezes e meia") era
    fóssil; razão e quedas agora saem dos componentes do HLM de três níveis."""
    u0, f0 = n3["M0"]["icc_upa"], n3["M0"]["icc_uf"]
    u2, f2 = n3["M2"]["icc_upa"], n3["M2"]["icc_uf"]
    qu, qf = 1 - u2 / u0, 1 - f2 / f0
    r0, r2 = u0 / f0, u2 / f2
    _r = lambda x: f"{x:.1f}".replace(".", ",")
    if r2 > 1:
        s = (f"a camada do bairro encolhe {'mais' if qu > qf else 'menos'} "
             f"(de {_r(r0)} para {_r(r2)} vez o estado), mas continua sendo a maior.")
    else:
        s = "depois dos controles, o estado passa a pesar mais que o bairro."
    return s


_niv3 = {r["modelo"]: {k: (v if k == "modelo" else _num3(v)) for k, v in r.items()}
         for r in _rd("hlm_tres_niveis.csv")}
_coef = {(r["modelo"], r["variavel"]): r for r in _rd("hlm_stepup_coefs.csv")}
_konf = {r["modelo"]: r for r in _rd("hlm_stepup_konfound.csv")}
_glm = {(r["desfecho"], r["modelo"]): r for r in _rd("glmm_glassceil_full.csv")}
def _pt(x, d=1):
    return f"{float(x):.{d}f}".replace(".", ",").replace("-", "−")
def _pten(x, d=1):
    return f"{float(x):.{d}f}"
_V = {}
if _gap and _fit and _coef:
    import math as _math
    _b = {m: float(_gap[m]["b_negro"]) for m in ("M1", "M2", "M3", "M4")}
    _V.update({
        "@@HLM_B1@@": _pt(_b["M1"], 4), "@@HLM_B2@@": _pt(_b["M2"], 4),
        "@@HLM_B3@@": _pt(_b["M3"], 4), "@@HLM_B4@@": _pt(_b["M4"], 4),
        "@@HLM_B1_IC@@": f"[{_pt(_gap['M1']['ci_lo'], 4)}; {_pt(_gap['M1']['ci_hi'], 4)}]",
        "@@HLM_B3_IC@@": f"[{_pt(_gap['M3']['ci_lo'], 4)}; {_pt(_gap['M3']['ci_hi'], 4)}]",
        "@@HLM_GAP1@@": _pt(abs(float(_gap["M1"]["Gap%"]))), "@@HLM_GAP3@@": _pt(abs(float(_gap["M3"]["Gap%"]))),
        "@@HLM_GAP4@@": _pt(abs(float(_gap["M4"]["Gap%"]))),
        "@@HLM_GAP1_EN@@": _pten(abs(float(_gap["M1"]["Gap%"]))), "@@HLM_GAP3_EN@@": _pten(abs(float(_gap["M3"]["Gap%"]))),
        "@@HLM_MED_BAIRRO@@": _pt(_gap["M2"]["Mediacao_acum%"]), "@@HLM_MED_BAIRRO_EN@@": _pten(_gap["M2"]["Mediacao_acum%"]),
        "@@HLM_MED_OCC@@": "---",   # preenchido abaixo, em relação ao gap agregado
        "@@HLM_TAU0@@": _pt(_fit["M0"]["tau2_upa"], 4), "@@HLM_SIG0@@": _pt(_fit["M0"]["sigma2"], 4),
        "@@HLM_ICC0@@": _pt(_fit["M0"]["icc_upa"], 3), "@@HLM_ICC0_PCT@@": _pt(float(_fit["M0"]["icc_upa"]) * 100),
        "@@HLM_ICC0_PCT_EN@@": _pten(float(_fit["M0"]["icc_upa"]) * 100),
        "@@HLM_ICC3@@": _pt(_fit["M3"]["icc_upa"], 3),
        # HLM de três níveis (robustez): separa em bairro e estado o que o modelo
        # de dois níveis credita inteiro ao território. Lido de hlm_tres_niveis.csv.
        **({
            "@@N3_ICC_UF0@@":  _pt(_niv3["M0"]["icc_uf"] * 100),
            "@@N3_ICC_UPA0@@": _pt(_niv3["M0"]["icc_upa"] * 100),
            "@@N3_ICC_UF2@@":  _pt(_niv3["M2"]["icc_uf"] * 100),
            "@@N3_ICC_UPA2@@": _pt(_niv3["M2"]["icc_upa"] * 100),
            "@@N3_B_NEGRO@@":  _pt(_niv3["M2"]["b_negro"], 4),
            "@@N3_LEITURA@@": _leitura_tres_camadas(_niv3),
            "@@N3_NOTA@@": (
                r"\footnote{Estimado com " + r"\texttt{lme4} sobre a mesma "
                r"população. A especificação do trabalho "
                r"continua sendo a de dois níveis: 27 estados são poucos para estimar "
                r"uma variância com precisão, e o efeito fixo absorve o contexto estadual "
                r"sem hipótese distribucional. O ponto desta checagem é outro: o "
                r"coeficiente racial não depende dessa escolha --- vale "
                # o par certo do M2 de três níveis (UF aleatória) é o M3 de dois níveis
                # (UF fixa); o M2 de dois níveis não tem UF nenhuma
                + _pt(_gap["M3"]["b_negro"], 4) + r" com a UF como efeito fixo e "
                + _pt(_niv3["M2"]["b_negro"], 4) + r" com a UF como nível aleatório.}"
            ),
        } if _niv3 else {}),
        "@@HLM_TAU_EXPL_M1@@": _pt(_fit["M1"]["pct_tau2_explicada_vs_M0"]),
        "@@HLM_TAU_EXPL_M2@@": _pt(_fit["M2"]["pct_tau2_explicada_vs_M0"]),
        "@@HLM_TAU_EXPL_M3@@": _pt(_fit["M3"]["pct_tau2_explicada_vs_M0"]),
        "@@HLM_LR2@@": f"{float(_fit['M2']['lr_vs_anterior']):,.0f}".replace(",", "."),
        "@@HLM_LR_RS@@": f"{float(_fit['M3_RS']['lr_vs_anterior']):,.0f}".replace(",", "."),
        "@@HLM_TAU1@@": _pt(_fit["M3_RS"]["tau2_slope_negro"], 4),
        "@@HLM_SD1@@": _pt(_fit["M3_RS"]["sd_slope_negro"], 3),
        "@@HLM_COV01@@": _pt(_fit["M3_RS"]["cov_int_slope"], 4),
        "@@HLM_COV01_TXT@@": "maior" if float(_fit["M3_RS"]["cov_int_slope"]) < 0 else "menor",
        "@@HLM_RS_LO@@": _pt(float(_coef[("M3_RS", "negro")]["coef"]) - float(_fit["M3_RS"]["sd_slope_negro"]), 3),
        "@@HLM_RS_HI@@": _pt(float(_coef[("M3_RS", "negro")]["coef"]) + float(_fit["M3_RS"]["sd_slope_negro"]), 3),
        "@@HLM_G01@@": _pt(_coef[("M2", "pct_negro_upa_z")]["coef"], 4),
        "@@HLM_G01_SE@@": _pt(_coef[("M2", "pct_negro_upa_z")]["se"], 4),
        "@@HLM_G01_ABS@@": _pt(abs(float(_coef[("M2", "pct_negro_upa_z")]["coef"])), 2),
        "@@HLM_KONF3@@": _pt(_konf["M3"]["pct_vies_para_invalidar"]) if "M3" in _konf else "---",
        "@@HLM_TAU_M1@@": _pt(_fit["M1"]["tau2_upa"], 4), "@@HLM_TAU_M2@@": _pt(_fit["M2"]["tau2_upa"], 4),
        "@@HLM_TAU_EXPL_M2_REL@@": _pt((float(_fit["M1"]["tau2_upa"]) - float(_fit["M2"]["tau2_upa"]))
                                       / float(_fit["M1"]["tau2_upa"]) * 100),
    })
    # gap agregado (OLS com efeitos fixos de UF, sem efeito de bairro) vs. dentro do bairro (HLM M1)
    _se_rows = _rd("hlm_serie_completo_se.csv")
    _pool = next((r for r in _se_rows if r["modelo"] == "M1_Individual_OLS" and r["variavel"] == "negro"), None)
    if _pool:
        _bp = float(_pool["coef"])
        _medb = (abs(_bp) - abs(_b["M1"])) / abs(_bp) * 100
        _V.update({"@@HLM_B_POOL@@": _pt(_bp, 4),
                   "@@HLM_GAP_POOL@@": _pt(abs((_math.exp(_bp) - 1) * 100)),
                   "@@HLM_GAP_POOL_EN@@": _pten(abs((_math.exp(_bp) - 1) * 100)),
                   "@@HLM_MED_BAIRRO@@": _pt(_medb), "@@HLM_MED_BAIRRO_EN@@": _pten(_medb),
                   "@@HLM_MED_OCC@@": _pt((abs(_b["M3"]) - abs(_b["M4"])) / abs(_bp) * 100),
                   "@@HLM_RESID_PCT@@": _pt(abs(_b["M4"]) / abs(_bp) * 100)})
        # a "régua" da narrativa: fração do gap agregado já mediada em cada degrau,
        # a mesma conta da coluna "Mediação acum." da Tabela tab:mediacao
        _V.update({f"@@HLM_MED_ACUM_{_m}@@":
                   _pt((abs(_bp) - abs(_b[_m])) / abs(_bp) * 100)
                   for _m in ("M1", "M2", "M3", "M4")})
_glmer = {(r["desfecho"], r["modelo"]): r for r in _rd("glmm_glassceil_glmer.csv")}
_src = _glmer if _glmer else _glm            # bloco 4: o glmer é a fonte; logit-FE é robustez
if _src:
    _or = lambda d, m: float(_src[(d, m)]["OR_negro"])
    _V.update({
        "@@GLMM_OR_CBO_M2@@": _pt(_or("ocp_qualif", "M2"), 3),
        "@@GLMM_OR_TOP20_M2@@": _pt(_or("y_top20", "M2"), 3),
        "@@GLMM_OR_TOP10_M2@@": _pt(_or("y_top10", "M2"), 3),
        "@@GLMM_PCT_CBO_M2@@": f"{(1 - _or('ocp_qualif', 'M2')) * 100:.0f}",
        "@@GLMM_PCT_TOP10_M2@@": f"{(1 - _or('y_top10', 'M2')) * 100:.0f}",
    })
if _glmer:
    import math as _m2
    from params_nucleo import evalue as _ev   # √OR para desfecho comum (E2.7)
    _g = lambda d, m, c: float(_glmer[(d, m)][c])
    _ci = lambda d, m, sep: f"{_pt(_g(d, m, 'CI95_lo'), 3)}{sep}{_pt(_g(d, m, 'CI95_hi'), 3)}"
    _oi_sup, _oi_pos = _g("ocp_qualif", "M4", "OR_inter_superior"), _g("ocp_qualif", "M4", "OR_inter_pos")
    _V.update({
        "@@G_ICC_CBO_M1@@": _pt(_g("ocp_qualif", "M1", "ICC_UPA"), 3),
        "@@G_ICC_T10_M1@@": _pt(_g("y_top10", "M1", "ICC_UPA"), 3),
        "@@G_ICC_CBO_M1_PCT@@": _pt(_g("ocp_qualif", "M1", "ICC_UPA") * 100, 0),
        "@@G_ICC_T10_M1_PCT@@": _pt(_g("y_top10", "M1", "ICC_UPA") * 100, 0),
        "@@G_LR_CBO@@": f"{_g('ocp_qualif', 'M2', 'LR_vs_pooled'):,.0f}".replace(",", "."),
        "@@G_LR_T10@@": f"{_g('y_top10', 'M2', 'LR_vs_pooled'):,.0f}".replace(",", "."),
        "@@G_OR_CBO_M2@@": _pt(_g("ocp_qualif", "M2", "OR_negro"), 3),
        "@@G_OR_CBO_M2_EN@@": _pten(_g("ocp_qualif", "M2", "OR_negro"), 3),
        "@@G_CI_CBO_M2@@": _ci("ocp_qualif", "M2", "--"),
        "@@G_CI_CBO_M2_EN@@": f"{_pten(_g('ocp_qualif', 'M2', 'CI95_lo'), 3)}--{_pten(_g('ocp_qualif', 'M2', 'CI95_hi'), 3)}",
        "@@G_PCT_CBO_M2@@": f"{(1 - _g('ocp_qualif', 'M2', 'OR_negro')) * 100:.0f}",
        "@@G_AME_CBO_M2@@": _pt(abs(_g("ocp_qualif", "M2", "AME_pp")), 1),
        "@@G_OR_T20_M2@@": _pt(_g("y_top20", "M2", "OR_negro"), 3),
        "@@G_OR_T10_M2@@": _pt(_g("y_top10", "M2", "OR_negro"), 3),
        "@@G_OR_T10_M2_EN@@": _pten(_g("y_top10", "M2", "OR_negro"), 3),
        "@@G_PCT_T10_M2@@": f"{(1 - _g('y_top10', 'M2', 'OR_negro')) * 100:.0f}",
        "@@G_OR_CBO_M3@@": _pt(_g("ocp_qualif", "M3", "OR_negro"), 3),
        "@@G_OR_T10_M3@@": _pt(_g("y_top10", "M3", "OR_negro"), 3),
        "@@G_ORI_SUP_CBO@@": _pt(_oi_sup, 3), "@@G_ORI_POS_CBO@@": _pt(_oi_pos, 3),
        # a leitura segue o sinal das DUAS interações (a pós-graduação pode agravar)
        "@@G_INTER_TXT@@": ("o superior completo atenua levemente a barreira, mas a "
                            "pós-graduação volta a agravá-la" if _oi_sup > 1 and _oi_pos < 1 else
                            "o diploma atenua a penalidade sem eliminá-la" if _oi_sup > 1 else
                            "o diploma não atenua a penalidade"),
        "@@G_OR_CBO_SUP@@": _pt(_g("ocp_qualif", "M4", "OR_negro") * _oi_sup, 3),
        "@@G_AUC_CBO_M2@@": _pt(_g("ocp_qualif", "M2", "AUC_com_RE"), 3),
        "@@G_AUCFE_CBO_M2@@": _pt(_g("ocp_qualif", "M2", "AUC_so_FE"), 3),
        "@@G_CUT_CBO_M2@@": _pt(_g("ocp_qualif", "M2", "cutoff_youden"), 2),
        "@@G_SENS_CBO_M2@@": _pt(_g("ocp_qualif", "M2", "sens"), 2),
        "@@G_ESP_CBO_M2@@": _pt(_g("ocp_qualif", "M2", "espec"), 2),
        "@@G_EV_CBO_M2@@": _pt(_ev(_g("ocp_qualif", "M2", "OR_negro"), "ocp_qualif"), 1),
        "@@G_EV_CBO_M2_EN@@": _pten(_ev(_g("ocp_qualif", "M2", "OR_negro"), "ocp_qualif"), 1),
    })
    # Hosmer-Lemeshow: queda do A2 para o A3 em cada desfecho (antes: "cai à metade", fóssil)
    _hl = [1 - _g(d, "M3", "HL_chi2") / _g(d, "M2", "HL_chi2")
           for d in ("ocp_qualif", "y_top20", "y_top10")]
    # E7.1: a estatística sobe num desfecho e cai nos outros — "cai entre −185% e 69%"
    # era ininteligível; a frase segue a direção de cada desfecho
    _nomes = {"ocp_qualif": "no cargo qualificado", "y_top20": "no top~20\\%",
              "y_top10": "no top~10\\%"}
    _cai = [(d, q) for d, q in zip(("ocp_qualif", "y_top20", "y_top10"), _hl) if q > 0]
    _sobe = [d for d, q in zip(("ocp_qualif", "y_top20", "y_top10"), _hl) if q <= 0]
    _V2_hl = ("cai " + " e ".join(f"{_pt(q * 100, 0)}\\% {_nomes[d]}" for d, q in _cai)
              if _cai else "não cai")
    if _sobe:
        _V2_hl += ", embora suba " + " e ".join(_nomes[d] for d in _sobe)
    texto = texto.replace("@@G_HL_QUEDA@@", _V2_hl)
    # logit-FE × GLMM: a concordância só vale com o contexto do bairro (A2 em diante)
    if _glm:
        _fe1, _fe2 = (float(_glm[("ocp_qualif", m)]["OR_negro"]) for m in ("M1", "M2"))
        _gl1, _gl2 = _g("ocp_qualif", "M1", "OR_negro"), _g("ocp_qualif", "M2", "OR_negro")
        if abs(_fe2 - _gl2) < 0.02:
            _fe_txt = (f"reproduz os OR a partir do A2 (cargo qualificado: {_pt(_fe2, 3)} contra "
                       f"{_pt(_gl2, 3)})"
                       + (f"; no A1, sem o contexto do bairro, dá {_pt(_fe1, 3)} contra "
                          f"{_pt(_gl1, 3)}, porque sem o intercepto de UPA o contexto omitido é "
                          r"absorvido pelo coeficiente racial" if abs(_fe1 - _gl1) >= 0.02 else "")
                       + ". Com o contexto do bairro no modelo, a conclusão não depende da "
                         "hipótese de efeitos aleatórios.")
        else:
            _fe_txt = (f"dá OR de {_pt(_fe2, 3)} no A2, contra {_pt(_gl2, 3)} do GLMM: a "
                       "magnitude depende da hipótese de efeitos aleatórios, o sinal não.")
        texto = texto.replace("@@G_FE_TXT@@", _fe_txt)
for _k, _v in _V.items():
    texto = texto.replace(_k, _v)
# REML vs ML do modelo nulo (FAV-73): a comparação não cabia na tabela
_vc = {r["componente"]: r for r in _rd("hlm_stepup_varcomp.csv")}
if _vc:
    texto = texto.replace("@@HLM_TAU0_ML@@", _pt(_vc["tau2_upa"]["ML"], 5))
    texto = texto.replace("@@HLM_TAU0_REML@@", _pt(_vc["tau2_upa"]["REML"], 5))

_rest = sorted(set(re.findall(r"@@(?:HLM|GLMM|G)_[A-Z0-9_]+@@", texto)))
if _rest:
    print(f"  [AVISO] placeholders não preenchidos: {_rest[:12]}")

# VIF (bloco 5.7) — placeholders @@VIF_*@@ lidos de vif_m4_preditores.csv
_vif = {r["predictor"]: float(r["VIF"]) for r in _rd("vif_m4_preditores.csv")}
if _vif:
    _ctx = [v for k, v in _vif.items() if k.endswith("_upa_z")]
    _occ = [v for k, v in _vif.items() if k.startswith("ocp_") or k in ("emprego_formal", "conta_propria", "trab_domestico")]
    # abertura condicional: quais VIF passam de 10 e se estão todos no bloco educacional
    # (as dummies cumulativas são aninhadas: quem tem superior tem médio e fundamental)
    _altos = sorted(((k, v) for k, v in _vif.items() if v > 10), key=lambda kv: -kv[1])
    _nome = lambda k: r"\texttt{" + k.replace("_", r"\_") + "}"
    if not _altos:
        _mx = max(_vif.items(), key=lambda kv: kv[1])
        _abre = (f"Nenhum preditor do M4 tem VIF acima de 10; o maior é o de {_nome(_mx[0])} "
                 f"({_pt(_mx[1], 2)}).")
    else:
        _lista = ", ".join(f"{_nome(k)} ({_pt(v, 2)})" for k, v in _altos)
        _abre = (f"{'O VIF acima de 10 é o de' if len(_altos) == 1 else 'Os VIF acima de 10 são os de'} "
                 f"{_lista}.")
        if all(k.startswith("educ_") for k, _ in _altos):
            _abre += (r" É colinearidade \emph{por construção} dentro do bloco educacional: as "
                      r"\textit{dummies} de conclusão são cumulativas e, portanto, aninhadas "
                      r"\cite[cap.~12]{favero2024}. Ela infla o erro-padrão dos retornos "
                      r"educacionais, que por isso são lidos com cautela.")
    for _k, _v in {"@@VIF_ABERTURA@@": _abre,
                   "@@VIF_NEGRO@@": _pt(_vif.get("negro", float("nan")), 2),
                   "@@VIF_CTX_MAX@@": _pt(max(_ctx) if _ctx else float("nan"), 1),
                   "@@VIF_OCC_MAX@@": _pt(max(_occ) if _occ else float("nan"), 2)}.items():
        texto = texto.replace(_k, _v)
# QR por sexo (bloco 5.6) — @@QR_SEXO@@: o padrão de cada coluna da Tabela da QR, descrito
# a partir do csv (crescente, em U ou decrescente), sem afirmar o que os números não mostram
_qr = {}
for _r in _rd("qr_melhorias.csv"):
    _qr.setdefault(_r["grupo"], {})[round(float(_r["quantil"]) * 100)] = abs(float(_r["gap_pct"]))


def _padrao_qr(g):
    g10, g50, g90 = g[10], g[50], g[90]
    if g10 > 1.1 * g50 and g90 > 1.1 * g50:
        return "U"
    return "cresce" if g90 > g10 else "cai"


if {"Homens", "Mulheres"} <= set(_qr):
    _fq = lambda v: _pt(v, 1) + r"\%"
    _partes = []
    for _nome, _rot in (("Homens", "entre homens"), ("Mulheres", "entre mulheres")):
        _g = _qr[_nome]
        _p = _padrao_qr(_g)
        if _p == "U":
            _partes.append(f"{_rot}, a penalidade é maior nas duas pontas --- {_fq(_g[10])} no q10, "
                           f"{_fq(_g[50])} na mediana e {_fq(_g[90])} no q90 ---, de modo que ao teto "
                           r"de vidro se soma um piso pegajoso \emph{condicional}")
        else:
            _partes.append(f"{_rot}, a penalidade {'cresce' if _p == 'cresce' else 'diminui'} de "
                           f"{_fq(_g[10])} (q10) para {_fq(_g[90])} (q90)")
    _qrs = (r"\paragraph{Por sexo.} As colunas por sexo da Tabela~\ref{tab:qr_melhorias} "
            r"mostram que o padrão não é o mesmo para todos: " + "; ".join(_partes) + ".")
    texto = texto.replace("@@QR_SEXO@@", _qrs)
else:
    texto = texto.replace("@@QR_SEXO@@", "")
if "@@VIF_" in texto:
    print("  [AVISO] placeholders @@VIF_...@@ não preenchidos!")

# ML (bloco 5.3): R² do XGBoost com LOO e sem renda da UPA; rank da raça no modelo sem
_mlp = {r["Modelo"]: r for r in _rd("ml_performance.csv")}
_imp_sr = _rd("shap_importance_sem_renda_upa.csv")
if _mlp:
    _V2 = {}
    if "XGBoost" in _mlp:
        _V2["@@ML_R2_XGB@@"] = _pt(_mlp["XGBoost"]["R²"], 3)
        _V2["@@ML_GAP_XGB@@"] = _pt(_mlp["XGBoost"]["gap_overfit"], 4)
    if "XGBoost (sem renda da UPA)" in _mlp:
        _V2["@@ML_R2_SR@@"] = _pt(_mlp["XGBoost (sem renda da UPA)"]["R²"], 3)
    _rk = [r for r in _imp_sr if r["Feature"].startswith("Raça")]
    if _rk:
        _V2["@@SHAP_RANK_SR@@"] = str(int(float(_rk[0]["rank"])))
        _V2["@@SHAP_NEGRO_SR@@"] = _pt(_rk[0]["SHAP_mean_abs"], 3)
        _V2["@@SHAP_NFEAT_SR@@"] = str(len(_imp_sr))
    _imp = _rd("shap_importance_comparada.csv")
    _rk2 = [r for r in _imp if r.get("Feature", "").startswith("Raça")]
    if _rk2:
        _V2["@@SHAP_NEGRO@@"] = _pt(_rk2[0]["SHAP_mean_abs_XGB"], 3)
        _V2["@@SHAP_RANK@@"] = str(int(float(_rk2[0]["Rank_XGB"])))
        _V2["@@SHAP_NFEAT@@"] = str(len(_imp))
    for _k, _v in _V2.items():
        texto = texto.replace(_k, _v)
if re.search(r"@@(ML_|SHAP_RANK)", texto):
    print("  [AVISO] placeholders de ML/SHAP não preenchidos!")

# Diagnósticos da OB (bloco 5.8) — placeholders @@BP_*@@ / @@RESET_*@@
_diag = {r["grupo"]: r for r in _rd("oaxaca_diagnosticos.csv")}
if _diag:
    for _k, _v in {"@@BP_R2_B@@": _pt(_diag["Brancos"]["bp_r2_aux"], 3),
                   "@@BP_R2_N@@": _pt(_diag["Negros"]["bp_r2_aux"], 3),
                   "@@RESET_B@@": _pt(_diag["Brancos"]["reset_ganho_r2"], 4),
                   "@@RESET_N@@": _pt(_diag["Negros"]["reset_ganho_r2"], 4)}.items():
        texto = texto.replace(_k, _v)
if re.search(r"@@(BP_|RESET_)", texto):
    print("  [AVISO] placeholders de diagnóstico não preenchidos!")

# CV do XGBoost (bloco 8) — placeholders @@CV_*@@
_cvr = _rd("ml_cv_resumo.csv")
_cvf = _rd("ml_cv_folds.csv")
if _cvr:
    _r = _cvr[0]
    _ant = [x for x in _cvf if x["config"] == "atual_tcc"]
    import statistics as _st
    _ant_r2 = [float(x["r2"]) for x in _ant]
    _V3 = {
        "@@CV_DEPTH@@": str(int(float(_r["escolhido_max_depth"]))),
        "@@CV_R2@@": _pt(_r["cv_r2_media"], 4), "@@CV_R2_DP@@": _pt(_r["cv_r2_dp"], 4),
        "@@CV_R2_ANT@@": _pt(_st.mean(_ant_r2), 4) if _ant_r2 else "---",
        "@@CV_R2_ANT_DP@@": _pt(_st.stdev(_ant_r2), 4) if len(_ant_r2) > 1 else "---",
        "@@CV_N_TREINO@@": f"{int(float(_r['n_treino'])):,}".replace(",", "."),
        "@@CV_SMEAR@@": _pt(_r["smearing_duan"], 3),
        "@@CV_ERRO_MED@@": f"{int(round(float(_r['erro_mediano_reais']))):,}".replace(",", "."),
        "@@CV_ERRO_PCT@@": _pt(_r["erro_mediano_pct"], 0),
    }
    for _k, _v in _V3.items():
        texto = texto.replace(_k, _v)
if "@@CV_" in texto:
    print("  [AVISO] placeholders @@CV_...@@ não preenchidos!")

# Checagem de \ref pendentes a rótulos removidos
pendentes = []
for rot in set(rotulos_removidos):
    if re.search(r"\\(ref|autoref|cref|eqref)\{" + re.escape(rot) + r"\}", texto):
        pendentes.append(rot)

# A subseção de Inferência (_SUBSEC) entra depois da primeira substituição de
# @@N_UPAS@@ e trazia o marcador cru para o documento: segunda passada aqui.
if _nupas:
    texto = texto.replace("@@N_UPAS@@", f"{int(float(_nupas)):,}".replace(",", "."))
# Parcela de retornos da RIF-OB em q10 e q90, na mesma conta da tab:rif_ob
# (corrigir_tabela_rif.py: ret / gap_rif) — antes estava escrita à mão no texto.
for _r in _rd0("rif_ob_decomposicao.csv"):
    if _r.get("q_label") in ("q10", "q90"):
        _v = float(_r["ret"]) / float(_r["gap_rif"]) * 100
        texto = texto.replace(f"@@RIF_RET_{_r['q_label'].upper()}@@", f"{_v:.1f}".replace(".", "{,}"))
# Marcador genérico @@P:CHAVE[:casas[:modo]]@@ — qualquer número do texto pode vir
# direto de params_nucleo, em vez de ser digitado (e virar fóssil na reestimação).
# modos: en (ponto decimal, para o Abstract), mil (milhar com ponto), milhoes (÷10⁶),
#        um_menos (100·(1−v), p.ex. OR 0,697 → 30,3% menos), x100, abs.
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from params_nucleo import P as _PN  # noqa: E402


# Penalidade racial por nível de escolaridade (robustez do HLM, pedido do autor em
# 02/10/2026; run_hlm_negro_por_educ.py). Texto montado do csv: descreve o padrão que os
# números mostrarem, sem afirmar de antemão onde a penalidade é maior.
def _bloco_negro_por_educ() -> str:
    niv = [("SEMFUND", "sem fundamental completo"), ("FUND", "com fundamental completo"),
           ("MEDIO", "com médio completo"), ("SUP", "com superior completo"),
           ("POS", "com pós-graduação")]
    if not all(f"NE_GAP_{k}" in _PN for k, _ in niv):
        print("  [AVISO] hlm_negro_por_educ.csv ausente: bloco da escada educacional omitido")
        return ""
    v = lambda x, d=1: f"{x:.{d}f}".replace(".", "{,}")
    g = {k: _PN[f"NE_GAP_{k}"] for k, _ in niv}
    rot = dict(niv)
    k_max, k_min = max(g, key=g.get), min(g, key=g.get)
    sem, pos = g["SEMFUND"], g["POS"]
    if abs(pos - sem) < 1:
        forma = (f"é praticamente a mesma nas duas pontas da escada ({v(sem)}\\% entre quem "
                 f"está {rot['SEMFUND']} e {v(pos)}\\% {rot['POS']})")
    else:
        forma = (f"{'cresce' if pos > sem else 'diminui'} da base para o topo da escada: "
                 f"{v(sem)}\\% entre quem está {rot['SEMFUND']} e {v(pos)}\\% entre quem está "
                 f"{rot['POS']}")
    extremo = ""
    if k_max not in ("SEMFUND", "POS") or k_min not in ("SEMFUND", "POS"):
        extremo = (f" O maior valor está entre quem está {rot[k_max]} ({v(g[k_max])}\\%) e o menor, "
                   f"entre quem está {rot[k_min]} ({v(g[k_min])}\\%).")
    teste = ""
    if "NE_LR" in _PN:
        p = _PN["NE_LR_P"]
        teste = (f" O teste de razão de verossimilhança contra o M3, que impõe uma penalidade "
                 f"única, {'rejeita' if p < 0.05 else 'não rejeita'} a igualdade entre os níveis "
                 f"(LR $= {v(_PN['NE_LR'], 0)}$, 4~g.l., "
                 + (r"$p<0{,}001$" if p < 0.001 else f"$p = {v(p, 3)}$") + ").")
    bruto = ""
    if all(f"GAPBRUTO_{k}" in _PN for k in ("SEMFUND", "POS")):
        bruto = (f" Sem controles, o gap mediano é de {v(_PN['GAPBRUTO_SEMFUND'])}\\% {rot['SEMFUND']} "
                 f"e de {v(_PN['GAPBRUTO_POS'])}\\% {rot['POS']}; a diferença entre o bruto e o "
                 f"condicional, em cada nível, é o que idade, sexo, jornada, bairro e estado "
                 f"explicam ali.")
    return (r"""
\paragraph{A penalidade ao longo da escada educacional.}
O M3 impõe uma única penalidade racial a todos os níveis de escolaridade. Reestimado com o
coeficiente de raça livre em cada nível --- mesma especificação, mesma população ---, ele mostra
que a penalidade condicional """ + forma + "." + extremo + teste + bruto
            + f" A composição também difere: os negros são {v(_PN['NE_PCTNEG_SEMFUND'], 0)}\\% de quem "
            f"está {rot['SEMFUND']} e {v(_PN['NE_PCTNEG_POS'], 0)}\\% de quem está {rot['POS']}. "
            r"Como no restante do trabalho, são diferenças condicionais entre pessoas comparáveis, "
            r"não o efeito de estudar mais." + r"""
\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.9\textwidth]{hlm_negro_por_educ_retas}
  \caption{Retorno de cada nível de escolaridade e penalidade racial dentro dele: M3 do
  núcleo com o coeficiente de raça estimado em cada nível.}
  \label{fig:hlm_negro_educ}
\end{figure}
\noindent\emph{Como ler a Figura~\ref{fig:hlm_negro_educ}:} cada reta é um nível de
escolaridade e vai do trabalhador branco (à esquerda) ao negro (à direita). A altura da reta
é o rendimento do nível em relação ao branco sem fundamental completo; a inclinação é a
penalidade racial dentro do nível, escrita à direita.
""")


# Discussão: "diploma × porta" (E2.15, aprovado em 03/10/2026) — liga a escada salarial à
# interação negro×credencial do GLMM; só afirma o contraste se os números o mostrarem.
def _bloco_diploma_porta() -> str:
    ks = ("NE_GAP_POS", "NE_GAP_SEMFUND", "PCTPOS_ocp_qualif", "PCTSUP_ocp_qualif")
    if not all(k in _PN for k in ks):
        return ""
    v = lambda x, d=1: f"{x:.{d}f}".replace(".", "{,}")
    sal_pos, sal_base = _PN["NE_GAP_POS"], _PN["NE_GAP_SEMFUND"]
    ac_pos, ac_sup = _PN["PCTPOS_ocp_qualif"], _PN["PCTSUP_ocp_qualif"]
    if not (sal_pos < 3 and ac_pos >= 10):
        return ""                         # o contraste não se sustenta: nada a afirmar
    return (r"""
\paragraph{O diploma quase iguala o salário, mas não abre a porta.}
As duas barreiras respondem de modo diferente à escolaridade. A penalidade salarial é de """
            + f"{v(sal_base)}\\% entre quem não tem fundamental completo e cai a {v(sal_pos)}\\% na "
            r"pós-graduação (Figura~\ref{fig:hlm_negro_educ}); a desvantagem de acesso, não: com "
            f"superior completo, as chances de um trabalhador negro chegar a um cargo qualificado "
            f"seguem {v(ac_sup, 0)}\\% menores que as de um branco de mesmo perfil e bairro, e com "
            f"pós-graduação, {v(ac_pos, 0)}\\% menores (GLMM, degrau A4, "
            r"Tabela~\ref{tab:glmm_glassceil}). A escolaridade se associa a quase toda a convergência "
            r"salarial, mas não à de acesso. Duas cautelas: são diferenças condicionais entre "
            r"pessoas comparáveis, não o efeito de estudar mais --- quem chega à pós-graduação é um "
            r"grupo selecionado ---, e as razões de chances do A4 incluem o vínculo, o que faz delas "
            r"um limite inferior da desvantagem.""" + "\n")


_dp = _bloco_diploma_porta()
_anc_dp = r"\paragraph{A segregação residencial como multiplicador da desigualdade.}"
if _dp and _anc_dp in texto:
    texto = texto.replace(_anc_dp, _dp + "\n" + _anc_dp, 1)
elif _dp:
    print("  [AVISO] âncora do parágrafo diploma × porta não encontrada")

# frases-manchete compartilhadas (params_nucleo): síntese e título do bairro
from params_nucleo import titulo_bairro as _tit_bairro, frase_sintese as _fr_sint  # noqa: E402
from params_nucleo import frase_cbo_mulher_negra as _fr_cbo  # noqa: E402
texto = (texto.replace("@@FRASE_SINTESE@@", _fr_sint(_PN).replace("%", r"\%"))
              .replace("@@FRASE_CBO_MN@@", _fr_cbo(_PN).replace("%", r"\%")
                       .replace("CBO 1–4", "CBO~1--4"))
              .replace("@@TITULO_BAIRRO@@", _tit_bairro(_PN).replace("%", r"\%")))


_blk = _bloco_negro_por_educ()
if _blk:
    _ancora = r"\paragraph{O gap verdadeiro está entre dois limites"
    if _ancora in texto:
        texto = texto.replace(_ancora, _blk + "\n" + _ancora, 1)
    else:
        print("  [AVISO] âncora do bloco da escada educacional não encontrada")


def _marcador_p(m):
    chave, casas, modo = m.group(1), m.group(2), m.group(3) or ""
    v = float(_PN[chave])
    if modo == "mil":
        return f"{int(round(v)):,}".replace(",", ".")
    v = {"milhoes": v / 1e6, "milhoes_en": v / 1e6, "um_menos": 100 * (1 - v),
         "x100": 100 * v, "abs": abs(v)}.get(modo, v)
    s = f"{v:.{int(casas) if casas else 1}f}"
    s = s if modo.endswith("en") else s.replace(".", "{,}")
    return s.replace("-", "−")


texto = re.sub(r"@@P:([A-Za-z0-9_]+)(?::(\d))?(?::([a-z_]+))?@@", _marcador_p, texto)
# frase da Conclusão sobre convergência: conclusão escolhida conforme a série anual do M3
if "@@CONV_CONCLUSAO@@" in texto:
    texto = texto.replace("@@CONV_CONCLUSAO@@", enxuto_patches.frase_conclusao_convergencia())
_sobra = sorted(set(re.findall(r"@@[A-Z0-9_:a-z]+@@", texto)))
if _sobra:
    print(f"  [AVISO] marcadores não preenchidos: {_sobra}")

OUT.write_text(texto, encoding="utf-8")
print(f"\nOK -> {OUT}  ({len(lines)} linhas)")
if pendentes:
    print("\n[ATENÇÃO] Referências penduradas a rótulos removidos (revisar no texto):")
    for p in sorted(pendentes):
        print(f"   \\ref{{{p}}}")
else:
    print("Sem referências penduradas a rótulos removidos.")
