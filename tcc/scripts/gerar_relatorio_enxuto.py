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
\subsection{Decomposição do gap por mediação contextual e ocupacional}
A Tabela~\ref{tab:mediacao} resume o resultado central dos modelos HLM: à medida
que se adicionam controles de contexto (UPA) e ocupação, o gap racial encolhe de
$-19{,}1\%$ (M1) para $-6{,}2\%$ (M4). \emph{Como ler:} acompanhe a coluna
$\beta_{\text{negro}}$ aproximando-se de zero linha a linha --- a fração do gap já
explicada aparece em ``Mediação acum.''; o que resta no M4 é a penalidade que
nenhum atributo observável explica.
\input{outputs/tables/gap_mediacao_tcc.tex}

\subsection{Decomposição de Oaxaca--Blinder: composição \emph{vs.}\ discriminação}
A decomposição de Oaxaca--Blinder separa o gap em uma parcela explicada por
diferenças de dotações (capital humano e posição ocupacional) e uma parcela não
explicada (limite inferior da discriminação). A Tabela~\ref{tab:oaxaca_blinder}
usa a especificação de acesso (ocupação e contexto como dotações): 83,8\% do gap é
composição e 16,2\% é não-explicado. \emph{Como ler:} a coluna ``\% do Gap''
reparte o gap total (100\%) entre as duas fontes; veja a ressalva da legenda
(incluir ocupação como dotação \emph{subestima} a discriminação, pois o acesso à
ocupação é ele próprio discriminatório --- medido pelo GLMM adiante).
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

\subsection{GLMM Logístico: o teto de vidro no acesso}
O GLMM logístico multinível estima a probabilidade de acesso a cargo qualificado
e ao topo da renda, com efeito aleatório de UPA. A Tabela~\ref{tab:glmm_glassceil}
traz os \emph{odds ratios}, efeitos marginais e E-values dos três desfechos.
\emph{Como ler:} OR $<1$ = menor chance de acesso para negros vs.\ brancos de mesmo
perfil; quanto mais perto de zero, maior a barreira. O teto se aperta no top~10\%
(OR menor) e o E-value $\geq 2{,}2$ (última coluna) indica robustez a confundidores
não-observados.
\input{outputs/tables/glmm_glassceil.tex}

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

Um modelo de regressão multinível de três níveis (indivíduo, UPA e Unidade da
Federação) estima que profissionais negros recebem, em média, 19,1\% a menos que
brancos comparáveis em escolaridade, sexo e idade. Desse diferencial bruto, 52,5\%
é mediado pelo contexto de moradia (Nível~2), reduzindo o \textit{gap} líquido ---
atribuível à discriminação direta --- a 9,6\%.

A decomposição de Oaxaca--Blinder (especificação de acesso, com ocupação e contexto
como dotações) atribui 83,8\% do gap a diferenças de dotações e 16,2\% à parcela não
explicada por características observáveis --- limite inferior da discriminação salarial
\emph{dentro} da ocupação. A decomposição RIF por quantil mostra um padrão de
\textit{sticky floor}: esse componente de retorno é maior na base da distribuição
(35,1\% no q10) e decresce rumo ao topo (12,9\% no q90). A discriminação opera,
portanto, sobretudo no \emph{acesso} às ocupações --- canal que o GLMM mede diretamente.

O GLMM logístico de acesso confirma o teto de vidro ocupacional: controlados
escolaridade, sexo, idade e contexto, trabalhadores negros têm \textit{odds} de
acesso a cargo qualificado de 0,70 (IC~95\% 0,70--0,71), que se apertam para 0,66 no
topo~10\% da renda; o E-value de~2,2 indica robustez a confundidores não observados.
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

A three-level hierarchical linear model (individual, census tract, and state)
estimates that Black workers earn 19.1\% less than comparable White workers after
controlling for education, sex, and age. Of this gross differential, 52.5\% is
mediated by residential context (Level~2), leaving a residual \textit{net gap} of
9.6\% attributable to direct labour-market discrimination.

The Oaxaca--Blinder decomposition (access specification, with occupation and context
treated as endowments) attributes 83.8\% of the gap to endowment differences and 16.2\%
to the component unexplained by observable characteristics --- a lower bound on
within-occupation wage discrimination. The quantile RIF decomposition reveals a
\textit{sticky floor}: this returns component is largest at the bottom of the
distribution (35.1\% at q10) and declines toward the top (12.9\% at q90). Discrimination
thus operates mainly on \emph{access} to occupations --- which the GLMM measures directly.

The multilevel logistic model confirms an occupational glass ceiling: controlling for
education, sex, age, and context, Black workers face odds of accessing a qualified
occupation of 0.70 (95\% CI 0.70--0.71), tightening to 0.66 in the top 10\% of income;
an E-value of 2.2 indicates robustness to unobserved confounding. Interpretable
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
