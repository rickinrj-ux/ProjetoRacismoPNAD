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
o gap racial encolhe de @@HLM_GAP_POOL@@\% (agregado) para @@HLM_GAP4@@\% (M4). \emph{Como ler:} acompanhe a coluna
$\beta_{\text{negro}}$ aproximando-se de zero linha a linha --- a fração do gap já
explicada aparece em ``Mediação acum.''; o que resta no M4 é a penalidade que
nenhum atributo observável explica.
\input{outputs/tables/gap_mediacao_tcc.tex}

\subsection{Decomposição de Oaxaca--Blinder: composição \emph{vs.}\ discriminação}
A decomposição de Oaxaca--Blinder separa o gap bruto de log-rendimento
(@@OB_GAP@@ log-pontos, ou @@OB_GAP_PCT@@\%) em uma parcela explicada por diferenças de
dotações e uma parcela não explicada (retornos diferenciais --- limite inferior da
discriminação). A Tabela~\ref{tab:oaxaca_blinder} apresenta duas especificações,
porque ocupação e formalidade são \emph{bad controls} (Angrist \& Pischke, 2009):
são elas próprias resultado da discriminação. Em (A), com os controles do HLM~M3
(capital humano e contexto de UPA), @@OB_A_COEF@@\% do gap não é explicado por
características observáveis; em (B), tratando também horas, formalidade e grupo
CBO como dotações, a parcela não explicada cai para @@OB_B_COEF@@\% --- a
discriminação salarial \emph{dentro} da ocupação. A diferença entre as duas
(@@OB_DIF@@ pontos percentuais) é a parcela da discriminação que opera pela
\emph{porta de entrada} das ocupações, e não pelo salário --- exatamente o que o
GLMM de acesso mede adiante. \emph{Como ler:} em cada coluna, Dotações $+$ Não
explicado $=100\%$; os erros-padrão vêm de bootstrap em blocos por UPA.

\paragraph{Pressupostos das regressões por grupo.} As duas regressões auxiliares
(brancos e negros) foram submetidas aos testes de Breusch--Pagan e RESET
(Fávero \& Belfiore, cap.~12). Há heterocedasticidade --- esperada em log-rendimento ---
mas de magnitude modesta: o $R^2$ da regressão auxiliar do Breusch--Pagan é @@BP_R2_B@@
(brancos) e @@BP_R2_N@@ (negros), e é justamente por isso que os erros-padrão são
agrupados por UPA e a decomposição usa bootstrap em blocos. O RESET rejeita a forma
funcional linear, mas o ganho de $R^2$ ao acrescentar potências do valor predito é de
@@RESET_B@@ (brancos) e @@RESET_N@@ (negros) --- irrelevante para a decomposição. Com $N$
de milhões, ambos os testes rejeitam qualquer hipótese nula pontual; o que importa é a
magnitude, não o $p$-valor \cite{angrist2009}.
\input{outputs/tables/ob_acesso.tex}

\subsection{Regressão Quantílica e RIF-OB: teto de vidro e \emph{sticky floor}}
A regressão quantílica estima o gap em cada ponto da distribuição de renda; a
RIF-OB separa, por quantil, dotação e retorno. A Tabela~\ref{tab:qr_melhorias}
mostra o gap crescendo ao longo da distribuição (teto de vidro no gap bruto); a
Tabela~\ref{tab:rif_ob} revela o padrão complementar: o componente de retorno
(discriminação proporcional) é maior na base e \emph{decresce} rumo ao topo
(\emph{sticky floor}). \emph{Como ler:} na Tabela~\ref{tab:rif_ob}, Dotações $+$
Retornos $=100\%$ em cada quantil; siga a coluna Retornos caindo de $35{,}1\%$ (q10)
a $12{,}9\%$ (q90) --- a discriminação de preço pesa mais na base.
\input{outputs/tables/qr_melhorias.tex}
\input{outputs/tables/rif_decomp_tcc.tex}

\subsection{GLMM logístico: o teto de vidro no acesso}
\label{subsec:glmm_resultados}
O modelo logístico multinível (\texttt{lme4::glmer}, intercepto aleatório de UPA e
efeitos fixos de UF, estimado por Laplace na população completa) modela a probabilidade
de três desfechos --- cargo qualificado (CBO~1--4), renda no top~20\% e no top~10\% ---
em quatro degraus paralelos aos do HLM: M1 individual, M2 + contexto do bairro, M3 +
vínculo (formalidade, setor público, conta própria, doméstico --- \emph{bad controls},
logo limite inferior) e M4 + interação \texttt{negro}$\times$credencial. A
Tabela~\ref{tab:glmm_glassceil} traz \emph{odds ratios}, efeitos marginais, ICC e
E-values; a Tabela~\ref{tab:glmm_ajuste}, o ajuste e o desempenho de classificação.

\paragraph{O acesso também é ``bairro''.} No M1, a correlação intraclasse latente é de
@@G_ICC_CBO_M1@@ para o cargo qualificado e @@G_ICC_T10_M1@@ para o top~10\%: entre
@@G_ICC_CBO_M1_PCT@@\% e @@G_ICC_T10_M1_PCT@@\% da variância latente do acesso está entre
bairros. O teste de razão de verossimilhança do M2 contra o logit sem efeito aleatório
(LR $=$ @@G_LR_CBO@@ para o cargo; @@G_LR_T10@@ para o top~10\%, 1~g.l., $p<0{,}001$)
mostra que o efeito aleatório de UPA é indispensável --- o logit \emph{pooled} trataria
como independentes pessoas do mesmo mercado local.

\paragraph{A porta é mais estreita para negros --- e mais ainda no topo.} No M2,
controlados escolaridade, sexo, idade, horas, estado e contexto do bairro, a chance de
um trabalhador negro ocupar cargo qualificado é OR~$=$~@@G_OR_CBO_M2@@ (IC~95\%
@@G_CI_CBO_M2@@) da de um branco do mesmo bairro --- \textbf{@@G_PCT_CBO_M2@@\% menos
chance}, ou @@G_AME_CBO_M2@@ pontos percentuais de probabilidade. No top~20\% da renda o
OR é @@G_OR_T20_M2@@ e no top~10\%, @@G_OR_T10_M2@@ (@@G_PCT_T10_M2@@\% menos chance): o
teto se aperta à medida que se sobe. \emph{Como ler:} OR $<1$ é desvantagem; o AME traduz
o OR em probabilidade e é a medida a reter (MHE, cap.~3).

\paragraph{Vínculo e credencial não desfazem a barreira.} Descontar o vínculo
empregatício (M3) muda pouco o OR do cargo qualificado (@@G_OR_CBO_M3@@) e do top~10\%
(@@G_OR_T10_M3@@): a barreira não é um artefato da informalidade. No M4, a interação com
a credencial é OR~$=$~@@G_ORI_SUP_CBO@@ para o superior completo e @@G_ORI_POS_CBO@@ para
a pós-graduação: o diploma @@G_INTER_TXT@@, e o OR combinado do negro com superior
completo é @@G_OR_CBO_SUP@@ --- a credencial não neutraliza a barreira de acesso.

\paragraph{Ajuste e classificação.} O M2 discrimina bem os desfechos: AUC de
@@G_AUC_CBO_M2@@ (com efeitos aleatórios) e @@G_AUCFE_CBO_M2@@ (só efeitos fixos) para o
cargo qualificado; no \emph{cutoff} de Youden (@@G_CUT_CBO_M2@@) a sensibilidade é
@@G_SENS_CBO_M2@@ e a especificidade @@G_ESP_CBO_M2@@. O teste de Hosmer--Lemeshow
rejeita a calibração perfeita em todos os degraus --- inevitável com $N=7{,}7$~milhões
(MHE, cap.~8) ---, mas a estatística cai a cerca de metade quando se acrescenta o
vínculo (M3), sinal de calibração melhor; entre M1 e M2 ela praticamente não muda. O logit com efeitos fixos de UF e erro-padrão agrupado por UPA (última coluna
da Tabela~\ref{tab:glmm_glassceil}) reproduz os OR do GLMM: a conclusão não depende da
hipótese de efeitos aleatórios.
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
(15,9~milhões de observações brutas). A estratégia empírica articula quatro métodos
complementares --- modelo linear hierárquico (HLM), decomposição de Oaxaca--Blinder,
regressão quantílica com decomposição RIF e modelo logístico multinível (GLMM) ---,
validados por \textit{machine learning} interpretável (XGBoost + SHAP).

Um modelo linear hierárquico de dois níveis (indivíduos em bairros --- UPA ---, com
efeitos fixos de estado) mostra que @@HLM_ICC0_PCT@@\% da variância do log-rendimento está
entre bairros e estima que profissionais negros recebem, em média, @@HLM_GAP_POOL@@\% a menos
que brancos comparáveis em escolaridade, sexo e idade. Desse diferencial, @@HLM_MED_BAIRRO@@\%
é mediado pelo contexto de moradia (nível~2), reduzindo o \textit{gap} líquido --- não
explicado por capital humano, bairro nem estado, limite inferior da discriminação
direta --- a @@HLM_GAP3@@\%.

A decomposição de Oaxaca--Blinder atribui @@OB_A_COEF@@\% do gap bruto a retornos
diferenciais não explicados por capital humano e contexto; quando a ocupação e a
formalidade são tratadas como dotações, essa parcela cai para @@OB_B_COEF@@\% ---
limite inferior da discriminação salarial \emph{dentro} da ocupação, pois o acesso
à ocupação é ele próprio desigual. A decomposição RIF por quantil mostra um padrão de
\textit{sticky floor}: esse componente de retorno é maior na base da distribuição
(35,1\% no q10) e decresce rumo ao topo (12,9\% no q90). A discriminação opera,
portanto, sobretudo no \emph{acesso} às ocupações --- canal que o GLMM mede diretamente.

O GLMM logístico de acesso (intercepto aleatório de UPA) confirma o teto de vidro
ocupacional: controlados escolaridade, sexo, idade, estado e contexto do bairro,
trabalhadores negros têm \textit{odds} de acesso a cargo qualificado de @@G_OR_CBO_M2@@
(IC~95\% @@G_CI_CBO_M2_EN@@) das de brancos do mesmo bairro, que se apertam para
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
National Household Sample Survey (PNAD Contínua) from 2016 to 2025 (15.9~million raw
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
distribution (35.1\% at q10) and declines toward the top (12.9\% at q90). Discrimination
thus operates mainly on \emph{access} to occupations --- which the GLMM measures directly.

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
    (r"\label{fig:shap}", r"\end{figure}",
     r"\noindent\emph{Como ler a Figura~\ref{fig:shap}:} cada ponto é um trabalhador; "
     r"quanto mais à direita (ou maior a barra), maior o efeito da variável na renda "
     r"prevista. A cor indica se o valor da variável é alto ou baixo."),
    (r"\label{fig:interseccional}", r"\end{figure}",
     r"\noindent\emph{Como ler a Figura~\ref{fig:interseccional}:} cada barra é um grupo "
     r"raça$\times$gênero; a altura é o gap vs.\ o homem branco --- a mulher negra acumula "
     r"as duas penalidades."),
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

# Bibliografia: as referências do núcleo são citadas como texto plano nas tabelas
# (VanderWeele & Ding, Oaxaca & Ransom, Firpo et al., Crenshaw, Manski...). Um \nocite
# garante que entrem na lista de referências. Ver tcc/PERICIA.md (bibliografia).
print("Inserindo \\nocite das referências do núcleo…")
NOCITE = (r"\nocite{oaxaca1973,blinder1973,oaxaca_ransom1999,koenker1978,firpo2018,cameron2008,bickel2008,"
          r"vanderweele2017,crenshaw1989,manski1993,becker1957,arrow1973,almeida2019}")
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
            f"{_pt2(_o['b_negro'])} para {_pt2(_w['b_negro'])} "
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
    r"logit) reportam erros-padrão \emph{agrupados por UPA} (41.517 clusters) --- para a OB e a "
    r"regressão quantílica, por bootstrap em blocos de UPA. O agrupamento por UF é mais "
    r"conservador, mas com 27 clusters ($<42$) a inferência assintótica é pouco confiável "
    r"\cite{angrist2009}; quando reportado, usa a distribuição $t$ com $G-1$ graus de liberdade. "
    r"No HLM, o intercepto aleatório de UPA modela explicitamente a correlação intra-bairro, de modo "
    r"que o erro-padrão do modelo já a incorpora (sob a hipótese de efeitos aleatórios); como "
    r"contraprova, os coeficientes do HLM são comparados aos do OLS com efeitos fixos de UF e "
    r"erro-padrão agrupado por UPA, que coincidem em sinal, magnitude e significância. "
    + _txt_num + "\n\n" + _txt_peso + "\n\n"
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
    def _ev(o):
        o = 1 / o if o < 1 else o
        return o + _m2.sqrt(o * (o - 1))
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
        "@@G_INTER_TXT@@": ("atenua a penalidade sem eliminá-la" if _oi_sup > 1 else "não atenua a penalidade"),
        "@@G_OR_CBO_SUP@@": _pt(_g("ocp_qualif", "M4", "OR_negro") * _oi_sup, 3),
        "@@G_AUC_CBO_M2@@": _pt(_g("ocp_qualif", "M2", "AUC_com_RE"), 3),
        "@@G_AUCFE_CBO_M2@@": _pt(_g("ocp_qualif", "M2", "AUC_so_FE"), 3),
        "@@G_CUT_CBO_M2@@": _pt(_g("ocp_qualif", "M2", "cutoff_youden"), 2),
        "@@G_SENS_CBO_M2@@": _pt(_g("ocp_qualif", "M2", "sens"), 2),
        "@@G_ESP_CBO_M2@@": _pt(_g("ocp_qualif", "M2", "espec"), 2),
        "@@G_EV_CBO_M2@@": _pt(_ev(_g("ocp_qualif", "M2", "OR_negro")), 1),
        "@@G_EV_CBO_M2_EN@@": _pten(_ev(_g("ocp_qualif", "M2", "OR_negro")), 1),
    })
for _k, _v in _V.items():
    texto = texto.replace(_k, _v)
_rest = sorted(set(re.findall(r"@@(?:HLM|GLMM|G)_[A-Z0-9_]+@@", texto)))
if _rest:
    print(f"  [AVISO] placeholders não preenchidos: {_rest[:12]}")

# VIF (bloco 5.7) — placeholders @@VIF_*@@ lidos de vif_m4_preditores.csv
_vif = {r["predictor"]: float(r["VIF"]) for r in _rd("vif_m4_preditores.csv")}
if _vif:
    _ctx = [v for k, v in _vif.items() if k.endswith("_upa_z")]
    _occ = [v for k, v in _vif.items() if k.startswith("ocp_") or k in ("emprego_formal", "conta_propria", "trab_domestico")]
    for _k, _v in {"@@VIF_MISS@@": _pt(_vif.get("educ_missing", float("nan")), 2),
                   "@@VIF_SUP@@": _pt(_vif.get("educ_superior_completo", float("nan")), 2),
                   "@@VIF_NEGRO@@": _pt(_vif.get("negro", float("nan")), 2),
                   "@@VIF_CTX_MAX@@": _pt(max(_ctx) if _ctx else float("nan"), 1),
                   "@@VIF_OCC_MAX@@": _pt(max(_occ) if _occ else float("nan"), 2)}.items():
        texto = texto.replace(_k, _v)
if "@@VIF_" in texto:
    print("  [AVISO] placeholders @@VIF_...@@ não preenchidos!")

# ML (bloco 5.3): R² do XGBoost com LOO e sem renda da UPA; rank da raça no modelo sem
_mlp = {r["Modelo"]: r for r in _rd("ml_performance.csv")}
_imp_sr = _rd("shap_importance_sem_renda_upa.csv")
if _mlp:
    _V2 = {}
    if "XGBoost" in _mlp:
        _V2["@@ML_R2_XGB@@"] = _pt(_mlp["XGBoost"]["R²"], 3)
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

# Checagem de \ref pendentes a rótulos removidos
pendentes = []
for rot in set(rotulos_removidos):
    if re.search(r"\\(ref|autoref|cref|eqref)\{" + re.escape(rot) + r"\}", texto):
        pendentes.append(rot)

OUT.write_text(texto, encoding="utf-8")
print(f"\nOK -> {OUT}  ({len(lines)} linhas)")
if pendentes:
    print("\n[ATENÇÃO] Referências penduradas a rótulos removidos (revisar no texto):")
    for p in sorted(pendentes):
        print(f"   \\ref{{{p}}}")
else:
    print("Sem referências penduradas a rótulos removidos.")
