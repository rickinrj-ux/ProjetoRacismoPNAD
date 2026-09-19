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
A \textbf{barreira de acesso} (GLMM, OR~$=0,705$ para CBO~1--4 no modelo com
contexto) dialoga diretamente com a \textit{Lei~12.990/2014}, que reserva 20\% das
vagas em concursos públicos federais a candidatos negros, e cujo escopo o
diagnóstico sugere ampliar para níveis hierárquicos superiores --- onde o teto de
vidro é mais severo (OR(top~10\%)~$=0,656$).
A \textbf{qualificação e o acesso ao ensino superior} correspondem ao
\textit{Prouni} e ao \textit{Fies}, bem como ao legado do \textit{PRONATEC}; o
achado de que as mesmas credenciais rendem menos a trabalhadores negros (efeito
retornos da decomposição de Oaxaca--Blinder) indica que tais programas precisam ser
combinados a mecanismos de inserção ocupacional, sob pena de retorno marginal
decrescente.
O \textbf{combate à discriminação direta} encontra base na \textit{Lei~9.029/1995}
(que proíbe práticas discriminatórias na relação de trabalho) e no \textit{Estatuto
da Igualdade Racial} (\textit{Lei~12.288/2010}), cuja fiscalização o gap líquido de
9,6\% --- e a penalidade de 6,2\% que persiste dentro da mesma ocupação ---
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
     r"custo de ser negro\? Gap residual de -6\.2\\% após 23 controles, \\\\\n & crescendo nos quantis mais altos \(KB-test \$p<0\{,\}001\$\)\. \\\\",
     "custo de ser negro? Gap líquido de 9,6\\% (M3) e de 6,2\\% dentro \\\\\n"
     " & da mesma ocupação (M4), crescendo nos quantis mais altos ($Z=-5{,}57$, $p<0{,}001$). \\\\", 0),

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
    ("0.2 Discussão: sistema combinado sem redes",
     r"\\textbf\{sistema combinado\} em que discriminação de acesso, segregação\nresidencial e exclusão de redes se reforçam mutuamente, tornando",
     "\\textbf{sistema combinado} em que discriminação de acesso, segregação\n"
     "residencial e penalidade salarial se reforçam mutuamente, tornando", 0),

    ("0.2/0.3 Discussão: subvalorização do capital humano (sem cluster/SNA)",
     r"\\paragraph\{Subvalorização do capital humano negro\.\}.*?(?=\n\\paragraph\{Persistência da discriminação direta)",
     r"""\paragraph{Subvalorização do capital humano negro.}
A decomposição de Oaxaca--Blinder atribui 16,2\% do gap a \textit{retornos}
diferenciais --- as mesmas características observáveis, incluindo a posição
ocupacional, rendem menos a trabalhadores negros ---, e a decomposição RIF mostra
que essa parcela chega a 35\% na base da distribuição. O GLMM acrescenta que a
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
negros têm cerca de 30\% menos chance de ocupar um cargo qualificado e 34\% menos
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
9,6\% a menos que um branco --- e a barreira mais dura não é o salário, é a porta:
30\% menos chance de chegar a um cargo qualificado. O mercado de trabalho
brasileiro não é racialmente neutro, e educação sozinha não corrige isso.}
\end{quote}""", S),

    # ── Bloco 0.4 / 1.x — síntese numérica da Conclusão ───────────────────────
    ("0.4/1.2/1.3/1.4 Conclusão: síntese numérica",
     r"Essas conclusões emergem da convergência de seis metodologias independentes.*?\(\$Z=-5\{,\}25\$, \$p<0\{,\}001\$\)\.",
     r"""Essas conclusões emergem da convergência de quatro métodos e cinco análises
de robustez sobre $N=7.694.198$ observações da PNAD Contínua 2016--2025.
O gap condicional a capital humano, de 19,1\% (M1), decompõe-se em três parcelas:
(i)~mediação contextual de 52,5\% pelo local de moradia
($\hat{\gamma}_{01}=-0{,}269$), que leva ao \textbf{gap líquido de 9,6\%} (M3);
(ii)~mediação ocupacional de 17,3\% pelo acesso desigual a grupos CBO de alta
remuneração; e (iii)~penalidade de 6,2\% que persiste \emph{dentro} da mesma
ocupação (M4) --- limite inferior descritivo, pois a própria ocupação é
resultado da barreira de acesso.
O GLMM logístico confirma essa barreira: OR~$=0,705$ para CBO~1--4 no modelo
com contexto, com gradiente progressivo OR(top~20\%)~$=0,691$ $\to$
OR(top~10\%)~$=0,656$. A regressão quantílica formaliza o teto de vidro no gap
condicional ($Z=-5{,}57$, $p<0{,}001$), e a decomposição RIF mostra que a parcela
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
    ("1.5 ICC do M2: 5,3 → 5,8 (tabela)",
     r"A adição dos \\textit\{slopes contextuais\} da UPA \(M2\) reduz o ICC para\n5,3\\%",
     "A adição das covariáveis contextuais da UPA (M2) reduz o ICC para\n5,8\\%", 0),

    ("1.4 nota terminológica: líquido = M3, residual = M4",
     r"\\textbf\{Gap líquido\} \(ou residual\) é o diferencial que \\textit\{persiste\} após\no controle exaustivo de todas as covariáveis \(M4\) --- o piso para a discriminação\ndireta não explicada por observáveis\.",
     "\\textbf{Gap líquido} é o diferencial que \\textit{persiste} após o controle de\n"
     "capital humano e contexto (M3): 9,6\\%. \\textbf{Gap residual pós-ocupação} é o\n"
     "que resta ao se controlar também ocupação e formalidade (M4): 6,2\\% --- um limite\n"
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
