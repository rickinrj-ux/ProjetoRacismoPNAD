"""
enxuto_patches.py
=================
Patches de TEXTO aplicados por gerar_relatorio_enxuto.py sobre o LaTeX já
materializado do relatório completo, para alinhar a versão enxuta ao núcleo de 4
métodos e às correções da revisão pelos livros (tcc/revisoes/TODO_revisao.md).

Cada patch é (id, padrão, substituto, flags). O padrão é regex (re.subn, count=1).
Se um padrão não casar, o gerador avisa — nunca falha silenciosamente.

Blocos cobertos aqui: 0 (escopo), 1 (fonte única de números), 6 (linguagem — só
onde o parágrafo já estava sendo reescrito) e 7.1 (frase-síntese única).
"""
import re

S = re.S

PATCHES = [
    # ── Bloco 0.1 — PO ────────────────────────────────────────────────────────
    ("0.1 título",
     r"UMA ABORDAGEM MULTINÍVEL, DE MACHINE LEARNING, REDES SOCIAIS\nE PESQUISA OPERACIONAL COM DADOS DA PNAD CONTÍNUA \(2016--2025\)",
     "UMA ABORDAGEM MULTINÍVEL E DE DECOMPOSIÇÃO SALARIAL\nCOM DADOS DA PNAD CONTÍNUA (2016--2025)", 0),

    ("0.1 Discussão: da diagnose à prescrição (sem PO)",
     r"\\paragraph\{Da diagnose à prescrição\.\}.*?(?=\n\\paragraph\{O que este trabalho acrescenta)",
     r"""\paragraph{Da diagnose às políticas.}
O diagnóstico das duas barreiras revela gargalos simultâneos --- exclusão de
acesso às ocupações qualificadas e penalidade salarial que persiste dentro delas
--- que se reforçam mutuamente. A consequência para o desenho de políticas é
direta: nenhuma intervenção unidimensional (só cotas de acesso, só fiscalização
salarial, só escolaridade) atinge as duas barreiras ao mesmo tempo; a magnitude
relativa de cada uma, estimada aqui, é o insumo para priorizá-las.
""", S),

    ("0.1 Ancoragem em políticas (sem PO; OR do M2)",
     r"\\paragraph\{Ancoragem em políticas públicas existentes\.\}.*?(?=\n\\section\{Conclusão\})",
     r"""\paragraph{Ancoragem em políticas públicas existentes.}
As barreiras estimadas não são abstrações: cada uma corresponde a um instrumento
jurídico-institucional já existente no Brasil, cuja intensificação ou
aperfeiçoamento os resultados sugerem.
A \textbf{barreira de acesso} (GLMM, OR~$=@@GLMM_OR_CBO_M2@@$ para CBO~1--4 no modelo com
contexto) dialoga diretamente com a \textit{Lei~12.990/2014}, que reserva 20\% das
vagas em concursos públicos federais a candidatos negros, e cujo escopo o
diagnóstico sugere ampliar para níveis hierárquicos superiores --- onde o teto de
vidro é mais severo (OR(top~10\%)~$=@@GLMM_OR_TOP10_M2@@$).
A \textbf{qualificação e o acesso ao ensino superior} correspondem ao
\textit{Prouni} e ao \textit{Fies}, bem como ao legado do \textit{PRONATEC}; o
achado de que as mesmas credenciais rendem menos a trabalhadores negros (efeito
retornos da decomposição de Oaxaca--Blinder) indica que tais programas precisam ser
combinados a mecanismos de inserção ocupacional, sob pena de retorno marginal
decrescente.
O \textbf{combate à discriminação direta} encontra base na \textit{Lei~9.029/1995}
(que proíbe práticas discriminatórias na relação de trabalho) e no \textit{Estatuto
da Igualdade Racial} (\textit{Lei~12.288/2010}), cuja fiscalização o gap líquido de
@@HLM_GAP3@@\% --- e a penalidade de @@HLM_GAP4@@\% que persiste dentro da mesma ocupação ---
justifica reforçar.
""", S),

    ("0.1 Conclusão: parágrafo da PO",
     r"\nA pesquisa operacional fecha o ciclo diagnóstico-prescritivo\..*?e não apenas uma delas\}\.\n",
     "\n", S),

    # ── Bloco 0.2 — SNA ───────────────────────────────────────────────────────
    ("0.2 intro: três metodologias → quatro métodos",
     r"Este trabalho avança sobre a literatura nacional ao integrar três\nmetodologias complementares --- econometria multinível, \\textit\{machine learning\}\ninterpretável e análise de redes sociais --- sobre",
     "Este trabalho avança sobre a literatura nacional ao integrar quatro métodos\n"
     "complementares --- modelo linear hierárquico, decomposição de Oaxaca--Blinder,\n"
     "regressão quantílica com decomposição RIF e modelo logístico de acesso ---,\n"
     "validados por \\textit{machine learning} interpretável, sobre", 0),

    ("0.2 hipóteses: H3 (clusters) → barreira de acesso e teto de vidro",
     r"  \\item\[\\textbf\{H3\}\] \\textbf\{Tipologias de vulnerabilidade alinhadas com raça:\}.*?(?=\n  \\item\[\\textbf\{H4\}\])",
     r"""  \item[\textbf{H3}] \textbf{Barreira de acesso e teto de vidro:}
    Trabalhadores negros têm menor chance de acesso a ocupações qualificadas
    e ao topo da distribuição de renda do que brancos de mesmo perfil, e a
    penalidade salarial condicional cresce ao longo da distribuição de renda
    --- a discriminação não é um desconto uniforme, mas um teto.
""", S),

    ("0.2 hipóteses: remover H5 (SNA)",
     r"\n  \\item\[\\textbf\{H5\}\] \\textbf\{Isolamento estrutural na rede de co-residência:\}.*?(?=\n\\end\{enumerate\})",
     "", S),

    ("0.2 Resultados: três camadas → duas",
     r"As evidências deste capítulo estão organizadas em três camadas de exclusão\n--- três barreiras que operam em sequência e se reforçam mutuamente\.",
     "As evidências deste capítulo estão organizadas em duas camadas de exclusão\n"
     "--- duas barreiras que operam em sequência e se reforçam mutuamente.", 0),

    ("0.2 mapa das camadas: caption",
     r"\\caption\{Mapa das três camadas de exclusão racial --- guia de leitura\}",
     r"\caption{Mapa das duas camadas de exclusão racial --- guia de leitura}", 0),

    ("0.2 mapa: linha Barreira I sem segregação espacial",
     r"prestígio\? GLMM \(\$N=7\.694\.198\$\), HLM contextual e segregação \\\\\n & espacial mostram que a exclusão começa antes do salário\. \\\\",
     "prestígio? O GLMM de acesso e o HLM contextual mostram \\\\\n & que a exclusão começa antes do salário. \\\\", 0),

    ("0.2/1.4 mapa: linha Barreira II com gap líquido e residual",
     r"custo de ser negro\? Gap residual de -?[\d.]+\\% após 23 controles, \\\\\n & crescendo nos quantis mais altos \(KB-test \$p<0\{,\}001\$\)\. \\\\",
     "custo de ser negro? Gap líquido de @@HLM_GAP3@@\\% (M3) e de @@HLM_GAP4@@\\% dentro \\\\\n"
     " & da mesma ocupação (M4), crescendo nos quantis mais altos ($Z=@@QR_Z@@$, $p<0{,}001$). \\\\", 0),

    ("0.2 mapa: remover linha Barreira III",
     r"\\hline\n\\textbf\{BARREIRA III\} & Por que educação, sozinha, não quebra o ciclo\? \\\\\n.*?\n & negros: capital social transita exclusivamente por atores brancos\. \\\\\n",
     "", S),

    ("0.2 mapa: 'prova empiricamente'",
     r"Cada seção a seguir prova empiricamente uma dessas camadas\.\nNenhum método isolado teria identificado o sistema como um todo\.",
     "Cada seção a seguir documenta empiricamente uma dessas camadas.\n"
     "Nenhum método isolado teria identificado o sistema como um todo.", 0),

    ("0.2 cabeçalho Barreira III (SNA) removido",
     r"\\noindent\\rule\{\\textwidth\}\{1pt\}\n\\textbf\{\\large BARREIRA III --- ISOLAMENTO ESTRUTURAL E CAPITAL SOCIAL\}.*?pós-graduação ainda não chegam ao topo\.\}\n\n",
     "", S),

    ("0.2 Discussão: 'O que este trabalho acrescenta' sem SNA",
     r"são diferenças de dotações --- mas essas dotações são, elas mesmas,\nproduto de barreiras de acesso \(GLMM\) e isolamento de redes \(SNA\)\nque este trabalho pela primeira vez quantifica de forma integrada\.",
     "são diferenças de dotações --- mas essas dotações são, elas mesmas,\n"
     "produto da barreira de acesso às ocupações qualificadas (GLMM), que este\n"
     "trabalho quantifica em conjunto com a penalidade salarial.", 0),
    ("5.1 Discussão: comparação com Soares na especificação comparável",
     r"a Soares, decompõe essa \\textit\{caixa preta\}: apenas 16,2\\% do gap bruto\nsão retornos diferenciais \(potencialmente discriminação direta\); 83,8\\%\nsão diferenças de dotações",
     "a Soares, decompõe essa \\textit{caixa preta}. Na especificação comparável à dele\n"
     "(capital humano e contexto, sem ocupação), @@OB_A_COEF@@\\% do gap bruto são retornos\n"
     "diferenciais --- limite inferior da discriminação direta --- e @@OB_A_DOT@@\\% são\n"
     "diferenças de dotações; quando a ocupação é tratada como dotação, o não explicado\n"
     "cai para @@OB_B_COEF@@\\%, e @@OB_B_DOT@@\\% passam a ser dotações", 0),

    ("0.2 Discussão: sistema combinado sem redes",
     r"\\textbf\{sistema combinado\} em que discriminação de acesso, segregação\nresidencial e exclusão de redes se reforçam mutuamente, tornando",
     "\\textbf{sistema combinado} em que discriminação de acesso, segregação\n"
     "residencial e penalidade salarial se reforçam mutuamente, tornando", 0),

    ("0.2/0.3 Discussão: subvalorização do capital humano (sem cluster/SNA)",
     r"\\paragraph\{Subvalorização do capital humano negro\.\}.*?(?=\n\\paragraph\{Persistência da discriminação direta)",
     r"""\paragraph{Subvalorização do capital humano negro.}
A decomposição de Oaxaca--Blinder atribui @@OB_A_COEF@@\% do gap a \textit{retornos}
diferenciais --- as mesmas características de capital humano e contexto rendem
menos a trabalhadores negros --- e ainda @@OB_B_COEF@@\% quando a própria posição
ocupacional é descontada; a decomposição RIF mostra que essa parcela chega a 35\%
na base da distribuição. O GLMM acrescenta que a
credencial educacional não neutraliza a barreira de acesso (OR de \texttt{negro}
próximo de 0,7 mesmo entre os mais escolarizados). Juntas, essas evidências indicam
um duplo obstáculo ao retorno educacional: além da penalidade direta mensurada
pelo HLM, o acesso desigual às ocupações que convertem credenciais em renda.
\citeonline{granovetter1973} oferece o mecanismo plausível --- redes de indicação
que não cruzam fronteiras sociais ---, hipótese que este trabalho não testa
diretamente e que fica como agenda.
""", S),

    ("0.2 Conclusão: parágrafos iniciais (sem redes)",
     r"Este estudo comprova que a meritocracia baseada em capital humano falha.*?(?=\n\\medskip\n\n\\begin\{quote\})",
     r"""Este estudo mostra que a meritocracia baseada em capital humano falha
sistematicamente em explicar a trajetória profissional da população negra no
Brasil. A exclusão não é um evento isolado na contratação, nem uma consequência
automática de menor escolaridade --- é uma engrenagem de duas camadas que opera ao
longo de toda a trajetória do trabalhador: na porta de entrada das ocupações de
prestígio e no salário dentro das mesmas ocupações.
Cada uma dessas camadas foi identificada, isolada e medida de forma independente;
juntas, elas formam um sistema que nenhuma política unidimensional consegue desmontar.

O achado mais desafiador para o debate de políticas públicas é o da barreira de
acesso: com a mesma escolaridade, idade, sexo e contexto de moradia, trabalhadores
negros têm cerca de @@GLMM_PCT_CBO_M2@@\% menos chance de ocupar um cargo qualificado e @@GLMM_PCT_TOP10_M2@@\% menos
chance de chegar ao décimo superior da renda. Isso significa que aumentar a
escolaridade da população negra, sem intervir simultaneamente nos mecanismos de
seleção e promoção, produz retorno marginal decrescente: os títulos existem, mas
os canais que os convertem em mobilidade profissional permanecem estreitos.
Políticas baseadas apenas em educação são, portanto, necessárias, mas
estruturalmente insuficientes.

O ritmo de convergência observado na última década reforça a urgência.
Ao passo atual, a eliminação do diferencial racial levaria mais de um século.
Isso não é uma previsão pessimista --- é uma consequência aritmética da
combinação entre a magnitude do gap e a velocidade atual de redução.
Significa, concretamente, que reformas incrementais são insuficientes:
é necessário atacar as duas barreiras de forma simultânea e com recursos
proporcionais à magnitude do problema.
""", S),

    # ── Bloco 7.1 — uma única frase-síntese (substitui as quatro caixas) ──────
    ("7.1 Conclusão: Grande Ideia única",
     r"\\begin\{quote\}\n\\textit\{Mesmo após controle exaustivo de 24 covariáveis individuais,.*?necessárias, mas insuficientes\.\}\n\\end\{quote\}",
     r"""\begin{quote}
\textit{Com a mesma escolaridade, idade, sexo e bairro, um trabalhador negro ganha
@@HLM_GAP3@@\% a menos que um branco --- e a barreira mais dura não é o salário, é a porta:
@@GLMM_PCT_CBO_M2@@\% menos chance de chegar a um cargo qualificado. O mercado de trabalho
brasileiro não é racialmente neutro, e educação sozinha não corrige isso.}
\end{quote}""", S),

    # ── Bloco 0.4 / 1.x — síntese numérica da Conclusão ───────────────────────
    ("0.4/1.2/1.3/1.4 Conclusão: síntese numérica",
     r"Essas conclusões emergem da convergência de seis metodologias independentes.*?\(\$Z=-5\{,\}25\$, \$p<0\{,\}001\$\)\.",
     r"""Essas conclusões emergem da convergência de quatro métodos e cinco análises
de robustez sobre $N=7.694.198$ observações da PNAD Contínua 2016--2025.
O gap condicional a capital humano, de @@HLM_GAP_POOL@@\% (sem efeito de bairro),
decompõe-se em três parcelas: (i)~mediação de @@HLM_MED_BAIRRO@@\% pela segregação
residencial --- comparando negros e brancos do mesmo bairro ($\hat{\gamma}_{01}=@@HLM_G01@@$
para a composição racial do bairro), chega-se ao \textbf{gap líquido de @@HLM_GAP3@@\%} (M3);
(ii)~mediação ocupacional de @@HLM_MED_OCC@@\% pelo acesso desigual a grupos CBO de alta
remuneração; e (iii)~penalidade de @@HLM_GAP4@@\% que persiste \emph{dentro} da mesma
ocupação (M4) --- limite inferior descritivo, pois a própria ocupação é
resultado da barreira de acesso.
O GLMM logístico confirma essa barreira: OR~$=@@GLMM_OR_CBO_M2@@$ para CBO~1--4 no modelo
com contexto, com gradiente progressivo OR(top~20\%)~$=@@GLMM_OR_TOP20_M2@@$ $\to$
OR(top~10\%)~$=@@GLMM_OR_TOP10_M2@@$. A regressão quantílica formaliza o teto de vidro no gap
condicional ($Z=@@QR_Z@@$, $p<0{,}001$), e a decomposição RIF mostra que a parcela
de retornos é maior na base da distribuição incondicional.""", S),

    ("0.4 Contribuição principal (só núcleo)",
     r"\\noindent\\textbf\{Contribuição principal\.\}\nEste estudo oferece, ao nosso conhecimento, a primeira análise integrada\nde HLM multinível, clustering, SHAP, SNA e pesquisa operacional\n\(TOPSIS \+ programação linear\) sobre a série completa da PNAD Contínua\.",
     "\\noindent\\textbf{Contribuição principal.}\n"
     "Este estudo oferece, ao nosso conhecimento, a primeira análise integrada de\n"
     "modelo hierárquico, decomposição de Oaxaca--Blinder, regressão quantílica com\n"
     "RIF e modelo logístico de acesso --- validados por SHAP --- sobre a série\n"
     "completa da PNAD Contínua.", 0),
    ("0.4 Contribuição principal: mecanismos",
     r"\\textbf\{mecanismos\} que o sustentam em 2016--2025: discriminação de acesso,\nsegregação residencial e exclusão de redes, em sistema combinado\.",
     "\\textbf{mecanismos} que o sustentam em 2016--2025: discriminação de acesso,\n"
     "segregação residencial e penalidade salarial dentro da ocupação, em sistema combinado.", 0),


    # ── Bloco 3 — HLM honesto: metodologia (2 níveis, indivíduo em UPA, UF fixo) ──
    ("3.2 Metodologia do HLM (2 níveis + step-up)",
     r"\\subsection\{Modelo Linear Hierárquico de Três Níveis\}.*?(?=\\subsection\{Random Forest, XGBoost e SHAP Values\})",
     r"""\subsection{Modelo Linear Hierárquico: indivíduos em bairros (UPA), com efeitos fixos de UF}
\label{subsec:hlm}

A PNAD Contínua é amostrada por conglomerados: pessoas dentro de unidades primárias de
amostragem (UPA, o proxy de bairro), dentro de estados. A hipótese substantiva do
trabalho (H2) é que o \emph{bairro} media parte do gap racial; o modelo, portanto, coloca
a UPA no nível~2 e trata a UF como conjunto de efeitos fixos --- 27 unidades são poucas para
um terceiro nível aleatório \cite{angrist2009}, e os 26 \emph{dummies} absorvem todo o
contexto estadual sem hipóteses distribucionais. O modelo de dois níveis é:

\paragraph{Nível 1 --- indivíduo $i$ na UPA $j$:}
\begin{equation}
  \ln(W)_{ij} = \beta_{0j} + \beta_1\,\text{Negro}_{ij} + \beta_2\,\text{Sexo}_{ij}
  + \beta_3\,X_{ij} + \beta_4\,X^2_{ij} + \sum_{e}\beta_{e}\,\text{Educ}_{e,ij}
  + \boldsymbol{\beta}_{5}'\mathbf{Z}_{ij} + \varepsilon_{ij},
  \qquad \varepsilon_{ij}\sim\mathcal{N}(0,\sigma^2)
  \label{eq:nivel1}
\end{equation}
em que $\mathbf{Z}$ reúne horas, situação urbana e ano (e, no M4, vínculo e grupo CBO).

\paragraph{Nível 2 --- bairro $j$ (UPA):}
\begin{equation}
  \beta_{0j} = \gamma_{00} + \gamma_{01}\,\overline{\%\text{Negro}}_{j}
  + \gamma_{02}\,\overline{\text{Desemprego}}_{j} + \gamma_{03}\,\overline{\text{Educ}}_{j}
  + \sum_{k=2}^{27}\delta_k\,\text{UF}_{k(j)} + u_{0j},
  \qquad u_{0j}\sim\mathcal{N}(0,\tau^2_{\text{UPA}})
  \label{eq:nivel2}
\end{equation}
O coeficiente $\gamma_{01}<0$ é a evidência de \textit{duplo disadvantage}: morar em
bairros com maior concentração de negros reduz o rendimento \emph{independentemente}
da raça individual. A correlação intraclasse
\begin{equation}
  \rho_{\text{UPA}} = \frac{\tau^2_{\text{UPA}}}{\tau^2_{\text{UPA}} + \sigma^2}
  \label{eq:icc}
\end{equation}
mede a fração da variância do log-rendimento que está \emph{entre} bairros; valores
acima de 5\% justificam o modelo multinível \cite{raudenbush2002}.

\paragraph{Estratégia \emph{step-up}.} Seguindo \citeonline{raudenbush2002}, os modelos
são estimados em degraus aninhados: M0 (nulo: só o intercepto aleatório, que dá o ICC);
M1 (+ capital humano e demografia); M2 (+ contexto do bairro, nível~2); M3 (+ efeitos
fixos de UF) --- o modelo principal, que produz o \textbf{gap líquido}; e M4 (+ vínculo
e grupo ocupacional), reportado como \emph{limite inferior} porque ocupação e formalidade
são desfechos da própria discriminação (\emph{bad controls}, \citeonline{angrist2009}).
Cada degrau é comparado ao anterior por teste de razão de verossimilhança (LR), e a
redução de $\tau^2_{\text{UPA}}$ em relação ao M0 mede a variância entre bairros explicada
pelos controles. Testa-se ainda uma \emph{inclinação aleatória} de \texttt{negro} por UPA
(M3 + $u_{1j}\text{Negro}_{ij}$, com covariância não estruturada) --- a penalidade racial
varia entre bairros? --- por LR com dois graus de liberdade. Todos os modelos são
estimados por máxima verossimilhança (ML), necessária para comparar efeitos fixos entre
degraus; com $N=7{,}7$~milhões, REML e ML produzem os mesmos componentes de variância
(diferença $<0{,}3\%$ no M0), como registra a Tabela~\ref{tab:hlm_resultados}. A
inferência sobre erros-padrão e pesos é discutida na Subseção~\ref{subsec:inferencia}.

""", S),

    ("3.2 Resultados do HLM (step-up, figura e OVB)",
     r"\\subsection\{Modelos Hierárquicos Lineares --- Mediação Contextual do Gap\}.*?(?=\\subsection\{Modelos de Machine Learning e SHAP Values\})",
     r"""\subsection{Modelos Hierárquicos Lineares --- Mediação Contextual do Gap}
\label{subsec:hlm_resultados}

\textit{Esta seção documenta como o território amplifica o gap racial:
o bairro de moradia não é apenas contexto --- é parte do mecanismo de exclusão.}

A Tabela~\ref{tab:hlm_resultados} apresenta os cinco degraus da estratégia
\emph{step-up}, do modelo nulo (M0) ao modelo com ocupação (M4), todos com intercepto
aleatório por UPA e estimados por máxima verossimilhança sobre a população completa.
\emph{Como ler:} acompanhe a linha \textbf{Raça (negro)} da esquerda para a direita ---
cada coluna acrescenta um bloco de controles e o coeficiente se aproxima de zero; as
linhas de baixo dizem quanto da variância entre bairros cada bloco explica e se o degrau
melhora o ajuste (LR).

\paragraph{Quanto da renda é ``bairro'': o modelo nulo.}
O M0 estima $\hat\tau^2_{\text{UPA}} = @@HLM_TAU0@@$ e $\hat\sigma^2 = @@HLM_SIG0@@$,
ou seja, ICC$_{\text{UPA}} = @@HLM_ICC0@@$: \textbf{@@HLM_ICC0_PCT@@\% da variância do
log-rendimento está entre bairros}, muito acima do limiar de 5\% de
\citeonline{raudenbush2002} e da parcela entre estados (cerca de 10\%, no modelo
alternativo com UF aleatória usado como robustez). A estrutura aninhada não é um detalhe
técnico: ignorá-la trataria como independentes pessoas que compartilham o mesmo mercado
de trabalho local.

\paragraph{Gap agregado \emph{vs.} gap dentro do bairro (M1).}
Com escolaridade, idade, sexo, horas, situação urbana e ano, mas \emph{sem} nenhum
efeito de bairro (OLS com efeitos fixos de UF, Subseção~\ref{subsec:inferencia}),
trabalhadores negros recebem @@HLM_GAP_POOL@@\% a menos que brancos comparáveis
($\hat\beta = @@HLM_B_POOL@@$). O M1 acrescenta o intercepto aleatório de UPA e passa a
comparar negros e brancos \emph{do mesmo bairro}: $\hat\beta_{\text{negro}}^{M1} =
@@HLM_B1@@$ (IC~95\%: @@HLM_B1_IC@@), ou \textbf{@@HLM_GAP1@@\% a menos}. A diferença
entre os dois --- \textbf{@@HLM_MED_BAIRRO@@\% do gap agregado} --- é a parcela do gap
racial que transita pela segregação residencial: negros e brancos com o mesmo capital
humano não moram nos mesmos bairros, e os bairros pagam diferente. Esse é o teste da
Hipótese~H2. Os controles individuais explicam, além disso, @@HLM_TAU_EXPL_M1@@\% da
variância entre bairros do M0: parte do que parecia ``bairro'' é composição de quem mora
nele.

\paragraph{O que faz de um bairro um bairro (M2).}
As três covariáveis de nível~2 explicam @@HLM_TAU_EXPL_M2_REL@@\% da variância entre
bairros que restava no M1 ($\hat\tau^2$ de @@HLM_TAU_M1@@ para @@HLM_TAU_M2@@; LR $=$
@@HLM_LR2@@, 3 g.l., $p<0{,}001$). O coeficiente de composição racial,
$\hat\gamma_{01} = @@HLM_G01@@$ (SE @@HLM_G01_SE@@), indica que um desvio-padrão a mais
na proporção de negros da UPA reduz o log-rendimento de \emph{todos} os moradores em
@@HLM_G01_ABS@@ pontos --- da mesma ordem da penalidade individual --- a evidência mais
direta do \textit{duplo disadvantage}. O coeficiente individual mal se move
($\hat\beta_{\text{negro}}^{M2} = @@HLM_B2@@$): dentro do bairro, a penalidade racial
não depende de quem são os vizinhos; o bairro opera pela \emph{porta de entrada}
(onde se consegue morar), não pelo salário de quem já está lá.

\paragraph{Gap líquido (M3).}
Com os efeitos fixos de UF, $\hat\beta_{\text{negro}}^{M3} = @@HLM_B3@@$
(IC~95\%: @@HLM_B3_IC@@): o \textbf{gap líquido de @@HLM_GAP3@@\%} é o diferencial que
capital humano, contexto de bairro e estado não explicam --- limite inferior da
discriminação direta sob seleção em observáveis. O ICC cai para @@HLM_ICC3@@ e os
controles explicam @@HLM_TAU_EXPL_M3@@\% da variância entre bairros do M0.

\paragraph{Dentro da mesma ocupação (M4).}
Acrescentar vínculo e grupo CBO leva a $\hat\beta_{\text{negro}}^{M4} = @@HLM_B4@@$
(@@HLM_GAP4@@\%). A queda adicional --- @@HLM_MED_OCC@@\% do gap agregado --- não é
``explicação'', é \emph{canal}: a ocupação é ela própria resultado da barreira de acesso
(Seção~\ref{subsec:glmm_resultados}), por isso o M4 é um limite inferior descritivo.

\paragraph{A penalidade varia entre bairros.}
A inclinação aleatória de \texttt{negro} por UPA é significativa (LR $=$ @@HLM_LR_RS@@,
2 g.l., $p<0{,}001$): $\hat\tau^2_1 = @@HLM_TAU1@@$, desvio-padrão de @@HLM_SD1@@
log-pontos. Em bairros a um desvio-padrão da média a penalidade vai de
@@HLM_RS_LO@@ a @@HLM_RS_HI@@ log-pontos --- a discriminação salarial tem geografia, e a
covariância intercepto--inclinação de @@HLM_COV01@@ indica que a penalidade é
@@HLM_COV01_TXT@@ nos bairros de renda-base mais alta.

\begin{figure}[htbp]
  \centering
  \includegraphics[width=\textwidth]{hlm_efeitos_uf_blup_upa}
  \caption{A variação entre bairros supera a variação entre estados. À esquerda, os
  efeitos fixos de UF do M3 com IC~95\% (referência: primeira UF); à direita, a
  distribuição dos interceptos aleatórios das UPAs ($u_{0j}$, BLUPs do M3).}
  \label{fig:hlm_blups}
\end{figure}
\noindent\emph{Como ler a Figura~\ref{fig:hlm_blups}:} cada ponto à esquerda é um estado;
a largura do histograma à direita é o quanto a renda-base muda de um bairro para outro,
já descontados capital humano, contexto e estado.

\paragraph{Viés de variável omitida e sensibilidade.}
O coeficiente racial é uma associação condicional: pela fórmula do viés de variável
omitida \cite{angrist2009}, o coeficiente ``curto'' iguala o ``longo'' mais o efeito do
omitido vezes sua relação com a raça. Qualidade da escola, habilidade não observada e
redes de contato correlacionam-se negativamente com ser negro e positivamente com a
renda: omiti-las \emph{superestima} a penalidade --- o que faz do M3 um limite superior
para o efeito de tratamento diferencial condicional a essas características. Na direção
oposta, os controles que são desfechos (ocupação no M4) \emph{subestimam}. O gap líquido
deve ser lido entre esses dois limites. Para anular $\hat\beta^{M3}_{\text{negro}}$ seria
preciso um viés de @@HLM_KONF3@@\% do coeficiente (Konfound, \citeonline{frank2013}), e o
E-value do modelo de acesso (Tabela~\ref{tab:glmm_glassceil}) exige um confundidor
associado à raça e ao desfecho com razão de risco $\geq 2{,}2$ --- mais forte que qualquer
covariável observada.

\input{outputs/tables/hlm_stepup.tex}

""", S),

    ("3.2 Discussão: gamma01 e mediação lidos do csv",
     r"\$\\hat\{\\gamma\}_\{01\} = -0\{,\}269\$ para a proporção de negros na UPA\nindica que a penalidade de viver em bairro segregado equivale,\nem magnitude, à própria penalidade individual de ser negro\.",
     "$\\hat{\\gamma}_{01} = @@HLM_G01@@$ para a proporção de negros na UPA\n"
     "indica que a penalidade de viver em bairro segregado é da mesma ordem\n"
     "de grandeza da própria penalidade individual de ser negro --- e que @@HLM_ICC0_PCT@@\%\n"
     "da variância do rendimento está entre bairros, não entre pessoas.", 0),

    ("3.2 Discussão: 'achado mais robusto' com a mediação pelo bairro",
     r"O achado mais robusto desta análise é que [\d.,]+\\% do gap salarial racial\nbruto é mediado pelo local de moradia",
     "O achado mais robusto desta análise é que @@HLM_MED_BAIRRO@@\\% do gap salarial racial\n"
     "condicional a capital humano é mediado pelo bairro de moradia", 0),

    # ── Limitações ────────────────────────────────────────────────────────────
    ("0.2 Limitações: Heckman fora do núcleo",
     r"Os modelos HLM, a decomposição de Oaxaca--Blinder, a regressão quantílica e\na correção de Heckman produzem",
     "Os modelos HLM, a decomposição de Oaxaca--Blinder, a regressão quantílica e\no modelo logístico de acesso produzem", 0),
    ("0.2 Limitações: SNA vira agenda",
     r"com identificação de firma\. A SNA poderia ser refinada para grafos bipartidos\nUPA~\$\\times\$~grupo, elevando a resolução espacial da medida de segregação\.",
     "com identificação de firma. A análise de redes de co-residência, a tipologia\n"
     "por agrupamento e a priorização de políticas por pesquisa operacional,\n"
     "desenvolvidas em versão estendida deste trabalho, ficam como agenda.", 0),

    # ── Bloco 1 — fonte única de números ──────────────────────────────────────
    ("1.4 nota terminológica: líquido = M3, residual = M4",
     r"\\textbf\{Gap líquido\} \(ou residual\) é o diferencial que \\textit\{persiste\} após\no controle exaustivo de todas as covariáveis \(M4\) --- o piso para a discriminação\ndireta não explicada por observáveis\.",
     "\\textbf{Gap líquido} é o diferencial que \\textit{persiste} após o controle de\n"
     "capital humano e contexto (M3): @@HLM_GAP3@@\\%. \\textbf{Gap residual pós-ocupação} é o\n"
     "que resta ao se controlar também ocupação e formalidade (M4): @@HLM_GAP4@@\\% --- um limite\n"
     "inferior, pois a ocupação é ela própria resultado da barreira de acesso.", 0),

    ("1.1 ML: R² ≈ 0,43 → valor do csv",
     r"O \$R\^2 \\approx 0\{,\}43\$ é robusto para dados de rendimento individual,",
     "O $R^2$ de teste de 0,62 (XGBoost) é elevado para dados de rendimento individual,", 0),

    ("1.1 ML: N_teste da população",
     r"\\textit\{Hold-out\} 20\\%, \$N_\\text\{teste\}=307\.768\$ observações\.",
     "\\textit{Hold-out} 20\\% da população ($N_\\text{teste}\\approx 1{,}54$ milhão).", 0),

    ("6.1 intro: 'comprova' → 'mostra'",
     r"\\textbf\{Este trabalho comprova que o racismo no mercado de trabalho brasileiro\nnão opera como um evento isolado de discriminação salarial --- opera como\num sistema de barreiras em camadas que começa antes do primeiro salário,\npersiste ao longo de toda a trajetória profissional e se perpetua via\nexclusão das redes que convertem educação em mobilidade\.",
     "\\textbf{Este trabalho mostra que a desigualdade racial no mercado de trabalho\n"
     "brasileiro não se reduz a um desconto salarial isolado --- opera como um\n"
     "sistema de barreiras em camadas que começa antes do primeiro salário, na\n"
     "porta de entrada das ocupações qualificadas, e persiste ao longo de toda a\n"
     "trajetória profissional.", 0),
]


def aplicar(texto: str, verbose: bool = True) -> str:
    """Aplica todos os PATCHES em ordem; avisa os que não casaram."""
    falhas = []
    for pid, pat, rep, flags in PATCHES:
        # lambda: substituto literal (o re nao interpreta escapes do LaTeX no substituto)
        texto, n = re.subn(pat, lambda m, r=rep: r, texto, count=1, flags=flags)
        if n != 1:
            falhas.append(pid)
    # 1.6 — separador decimal: percentuais na prosa com vírgula (ABNT), ex.: 19.1\% → 19,1\%
    texto, n_pct = re.subn(r"(\d)\.(\d+)\\%", r"\1,\2\\%", texto)
    if verbose:
        print(f"  patches aplicados: {len(PATCHES) - len(falhas)}/{len(PATCHES)}"
              f"; percentuais normalizados: {n_pct}")
        for f in falhas:
            print(f"  [AVISO] patch não casou: {f}")
    return texto
