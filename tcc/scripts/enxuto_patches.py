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


def _virg(x, d):
    return f"{x:.{d}f}".replace(".", "{,}").replace("-", "$-$")


def _virgm(x, d):
    """Como _virg, para dentro de $...$ (o menos já está em modo matemático)."""
    return f"{x:.{d}f}".replace(".", "{,}")


def _tendencia():
    """Série anual do M3 + WLS (params_nucleo: TEND_*), já com as leituras derivadas."""
    import sys as _s
    from pathlib import Path as _P
    _s.path.insert(0, str(_P(__file__).resolve().parent))
    from params_nucleo import P
    t = {k: P[k] for k in ("TEND_REDUCAO_PCT", "TEND_DELTA", "TEND_P", "TEND_IC_LO", "TEND_IC_HI")}
    t["sig"] = t["TEND_P"] < 0.05
    t["anos_ot"] = P.get("TEND_ANOS_OTIMISTA")          # borda superior do IC de δ
    t["anos"] = P.get("TEND_ANOS")
    t["chow_f"], t["chow_p"] = P.get("TEND_CHOW_F"), P.get("TEND_CHOW_P")
    t["chow_df1"], t["chow_df2"] = P.get("TEND_CHOW_DF1"), P.get("TEND_CHOW_DF2")
    return t


def _params():
    import sys as _s
    from pathlib import Path as _P
    _s.path.insert(0, str(_P(__file__).resolve().parent))
    from params_nucleo import P
    return P


def _degrau() -> bool:
    """Estudo de evento (E8.8): pré-2020 sem inclinação, salto em 2020 acima da tendência e
    persistência em 2025 — só então o texto troca a extrapolação pelo degrau."""
    P = _params()
    return ("COV_D2020" in P and P["COV_P_INCL_PRE"] >= 0.10 and P["COV_DEV2020"] > 0
            and P["COV_P_DEV2020"] < 0.05 and P["COV_D2025"] > 0 and P["COV_P2025"] < 0.05)


def _sem_selecao() -> bool:
    """Ocupação dos negros em 2020 dentro da tendência e recuperação relativa desde 2022."""
    P = _params()
    return (P["COV_EMP_P_DEV2020"] >= 0.05 and P["COV_EMP_D2022"] > 0
            and P["COV_EMP_P2022"] < 0.05)


def _prazo(anos):
    if anos is None or anos == float("inf"):
        return None
    if anos > 100:
        return "mais de um século"
    return f"cerca de {anos:.0f} anos"


def frase_conclusao_convergencia():
    """Frase da Conclusão sobre a convergência (marcador @@CONV_CONCLUSAO@@).
    Lidera com o que os dados sustentam; prazo só pelo cenário otimista do IC."""
    t = _tendencia()
    if not t["sig"]:
        otim = _prazo(t["anos_ot"])
        return ("O ritmo observado na última década reforça a urgência: o gap não mostrou "
                f"convergência distinguível de zero ($p = {_virgm(t['TEND_P'], 3)}$)"
                + (f", e mesmo no cenário mais otimista que os dados admitem, eliminá-lo "
                   f"levaria {otim}." if otim else ".")
                + " Esperar não resolve.")
    if t["TEND_DELTA"] > 0 and _degrau():
        P = _params()
        return ("A última década não autoriza esperar: a penalidade caiu sobretudo em 2020, de "
                f"{_virg(P['COV_PEN_2019'], 1)}\\% para {_virg(P['COV_PEN_2020'], 1)}\\%, e não "
                "mostrou um ritmo de convergência a extrapolar.")
    if t["TEND_DELTA"] > 0:
        return ("O ritmo observado na última década reforça a urgência: há convergência "
                f"estatisticamente distinguível de zero ($p = {_virgm(t['TEND_P'], 3)}$), mas "
                f"lenta --- mantido o ritmo, eliminar o diferencial levaria {_prazo(t['anos'])}.")
    return ("O ritmo observado na última década reforça a urgência: o gap aumentou "
            f"($p = {_virgm(t['TEND_P'], 3)}$ para a inclinação).")


def _paragrafo_convergencia():
    """Parágrafo da Discussão sobre a convergência, montado da série anual do M3
    (run_m3_serie_sensib.py) e do WLS (run_tendencia_temporal.py). O título afirma só o
    que a inclinação sustenta; o prazo, quando citado, vem do IC — não da estimativa
    pontual, que extrapolaria dez pontos anuais por um século."""
    t = _tendencia()
    red = t["TEND_REDUCAO_PCT"]
    mov = (f"Em dez anos o gap encolheu {_virg(red, 1)}\\%" if red > 0
           else f"Em dez anos o gap aumentou {_virg(-red, 1)}\\%")
    nota = (f"\\footnote{{$\\delta = {_virgm(t['TEND_DELTA'], 6)}$ log-ponto por ano, IC~95\\% "
            f"$[{_virgm(t['TEND_IC_LO'], 6)};\\ {_virgm(t['TEND_IC_HI'], 6)}]$, "
            f"$p = {_virgm(t['TEND_P'], 3)}$, por mínimos quadrados ponderados sobre o "
            "$\\hat\\beta_{\\text{negro}}$ do M3 estimado ano a ano, 2016--2025.}")
    # Quebra estrutural em 2020 (Chow): enfraquece qualquer extrapolação linear da série
    quebra = ""
    if t.get("chow_p") is not None and t["chow_p"] < 0.05:
        p_txt = "p < 0{,}001" if t["chow_p"] < 0.001 else f"p = {_virgm(t['chow_p'], 3)}"
        quebra = (f" A série tem, além disso, uma quebra estrutural em 2020 (teste de Chow, "
                  f"$F({t['chow_df1']},{t['chow_df2']}) = {_virgm(t['chow_f'], 1)}$, ${p_txt}$), "
                  "ano em que a pandemia alterou a composição de quem permaneceu ocupado: uma "
                  "reta única sobre uma série quebrada não tem um ritmo a extrapolar.")
    if not t["sig"]:
        titulo = "Na década, nenhuma convergência mensurável"
        ambos = ("tanto com a ausência de convergência --- ou mesmo com a ampliação do gap ---"
                 if t["TEND_IC_LO"] < 0 else "tanto com a ausência de convergência")
        otim = _prazo(t["anos_ot"])
        corpo = (f"{mov}, mas a inclinação não se distingue de zero{nota}. O intervalo é "
                 f"compatível {ambos} quanto com um fechamento lento"
                 + (f": mesmo no cenário mais otimista que os dados admitem, eliminar o "
                    f"diferencial observado em 2016 levaria {otim}." if otim else ".")
                 + quebra
                 + " Extrapolar dez pontos anuais por décadas não é previsão; o que a série "
                   "sustenta é mais modesto e mais firme --- esperar não resolve.")
    elif t["TEND_DELTA"] > 0 and _degrau():
        # E8.8 (05/10/2026): o estudo de evento mostra um degrau em 2020, não um ritmo — a reta
        # não tem o que extrapolar, e o prazo em anos sai do texto
        P = _params()
        titulo = "A convergência veio num degrau, e não num ritmo"
        corpo = (f"{mov}, e a inclinação é estatisticamente distinta de zero{nota}. Uma reta, "
                 "porém, descreve mal a série. No estudo de evento --- a penalidade de cada ano "
                 "contra a de 2019, com efeito fixo de bairro e erro agrupado por "
                 f"UPA, nível que difere do M3 por comparar só vizinhos ---, ela oscilou sem tendência de 2016 a 2019 e caiu em 2020, de "
                 f"{_virg(P['COV_PEN_2019'], 1)}\\% para {_virg(P['COV_PEN_2020'], 1)}\\% "
                 f"({_virg(P['COV_DEV2020'], 1)} log-ponto acima da tendência anterior, "
                 f"$p = {_virgm(P['COV_P_DEV2020'], 3)}$), sem voltar depois: em 2025 era de "
                 f"{_virg(P['COV_PEN_2025'], 1)}\\%.")
        if _sem_selecao():
            corpo += (" A queda não reflete a saída dos negros de menor renda do emprego: a "
                      "ocupação deles caiu só "
                      f"{_virg(abs(P['COV_EMP_D2020']), 2)} ponto percentual a mais que a dos "
                      "brancos em 2020, dentro da tendência anterior, e passou a crescer mais que "
                      "a deles a partir de 2022, quando a penalidade seguia menor. Também não "
                      "reflete a entrevista por telefone, adotada pelo IBGE em 2020 e 2021: a "
                      "penalidade menor persistiu depois da volta da coleta presencial.")
        corpo += (" Sem grupo de controle, a série não identifica a causa do degrau; ela mostra "
                  "que a década não teve um ritmo de convergência a extrapolar, e que os resultados "
                  "agrupados de 2016--2025 são uma média dos dois patamares.")
    elif t["TEND_DELTA"] > 0:
        titulo = "A convergência existe, mas é lenta"
        corpo = (f"{mov}, e a inclinação é estatisticamente distinta de zero{nota}. Mantido o "
                 f"ritmo, eliminar o diferencial observado em 2016 levaria {_prazo(t['anos'])}."
                 + quebra)
    else:
        titulo = "Na década, o gap aumentou"
        corpo = f"{mov}, com inclinação estatisticamente distinta de zero{nota}." + quebra
    return (f"\\paragraph{{{titulo}.}}\n{corpo} Nada disso trivializa os avanços recentes em "
            "políticas de cotas e de acesso ao ensino superior. Diz, sim, que reformas no campo "
            "educacional, sem intervenção simultânea nos mecanismos de segregação residencial e "
            "de acesso às ocupações, são insuficientes --- que é precisamente o que a sequência "
            "de modelos deste trabalho mostrou.")


def flex(literal: str) -> str:
    """Regex que casa `literal` ignorando como os espaços e quebras caíram.

    Passos anteriores do gerador reflowam parágrafos; fixar a coluna em que a
    linha quebra faria o patch deixar de casar por um motivo que não é o dele.
    O marcador NUM (entre cifrões) casa um número já materializado no texto-fonte,
    que o substituto devolve como token, para a resolução única a partir do csv.
    """
    partes = [re.escape(p) for p in literal.split()]
    # aceita também a vírgula LaTeX "{,}" (0{,}62), além de 0,62 e 7.694.092
    return r"\s+".join(partes).replace(re.escape("$NUM$"), r"[\d.,{}]+")

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
--- que aparecem juntas nos mesmos dados. A consequência para o desenho de políticas
é direta: nenhuma intervenção unidimensional (só cotas de acesso, só fiscalização
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
contexto) dialoga diretamente com a Lei~15.142/2025, que substituiu a Lei~12.990/2014 e ampliou a reserva de vagas em concursos públicos federais a pessoas negras, indígenas e quilombolas, e cujo escopo o
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
     r"prestígio\? GLMM \(\$N=[\d.]+\$\), HLM contextual e segregação \\\\\n & espacial mostram que a exclusão começa antes do salário\. \\\\",
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
     r"a Soares, decompõe essa \\textit\{caixa preta\}: apenas [\d,]+\\% do gap bruto\nsão retornos diferenciais \(potencialmente discriminação direta\); [\d,]+\\%\nsão diferenças de dotações",
     "a Soares, decompõe essa \\textit{caixa preta}. Na especificação comparável à dele\n"
     "(capital humano e contexto, sem ocupação), @@OB_A_COEF@@\\% do gap bruto são retornos\n"
     "diferenciais --- limite superior do tratamento diferencial --- e @@OB_A_DOT@@\\% são\n"
     "diferenças de dotações; quando a ocupação é tratada como dotação, o não explicado\n"
     "cai para @@OB_B_COEF@@\\%, e @@OB_B_DOT@@\\% passam a ser dotações", 0),

    ("0.2 Discussão: sistema combinado sem redes",
     r"\\textbf\{sistema combinado\} em que discriminação de acesso, segregação\nresidencial e exclusão de redes se reforçam mutuamente, tornando",
     "\\textbf{sistema combinado} em que discriminação de acesso, segregação\n"
     "residencial e penalidade salarial operam em conjunto, tornando", 0),

    ("0.2/0.3 Discussão: subvalorização do capital humano (sem cluster/SNA)",
     r"\\paragraph\{Subvalorização do capital humano negro\.\}.*?(?=\n\\paragraph\{Persistência da discriminação direta)",
     r"""\paragraph{Subvalorização do capital humano negro.}
A decomposição de Oaxaca--Blinder atribui @@OB_A_COEF@@\% do gap a \textit{retornos}
diferenciais --- as mesmas características de capital humano e contexto rendem
menos a trabalhadores negros --- e ainda @@OB_B_COEF@@\% quando a própria posição
ocupacional é descontada; a decomposição RIF mostra que essa parcela chega a @@P:RIF_RET_Q10:0@@\%
na base da distribuição. O GLMM acrescenta que a
credencial educacional não neutraliza a barreira de acesso (OR combinado de
\texttt{negro} de @@G_OR_CBO_SUP@@ entre os de superior completo). Juntas, essas evidências indicam
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
negros têm chances (\emph{odds}) cerca de @@GLMM_PCT_CBO_M2@@\% menores de ocupar um cargo qualificado e
@@GLMM_PCT_TOP10_M2@@\% menores de chegar ao décimo superior da renda. Isso significa que aumentar a
escolaridade da população negra, sem intervir simultaneamente nos mecanismos de
seleção e promoção, produz retorno marginal decrescente: os títulos existem, mas
os canais que os convertem em mobilidade profissional permanecem estreitos.
Políticas baseadas apenas em educação são, portanto, necessárias, mas
estruturalmente insuficientes.

@@CONV_CONCLUSAO@@
Significa, concretamente, que reformas incrementais são insuficientes:
é necessário atacar as duas barreiras de forma simultânea e com recursos
proporcionais à magnitude do problema.
""", S),

    # ── Bloco 7.1 — uma única frase-síntese (substitui as quatro caixas) ──────
    ("7.1 Conclusão: Grande Ideia única",
     r"\\begin\{quote\}\n\\textit\{Mesmo após controle exaustivo de \d+ covariáveis individuais,.*?necessárias, mas insuficientes\.\}\n\\end\{quote\}",
     r"""\begin{quote}
\textit{@@FRASE_SINTESE@@}
\end{quote}""", S),

    # ── Bloco 0.4 / 1.x — síntese numérica da Conclusão ───────────────────────
    ("0.4/1.2/1.3/1.4 Conclusão: síntese numérica",
     r"Essas conclusões emergem da convergência de seis metodologias independentes.*?\(\$Z=-5\{,\}25\$, \$p<0\{,\}001\$\)\.",
     r"""Essas conclusões emergem da convergência de quatro métodos e cinco análises
de robustez sobre $N=@@P:OB_N:0:mil@@$ observações da PNAD Contínua 2016--2025.
O gap condicional a capital humano, de @@HLM_GAP_POOL@@\% (sem efeito de bairro),
decompõe-se em três parcelas: (i)~mediação de @@HLM_MED_BAIRRO@@\% pela segregação
residencial --- comparando negros e brancos do mesmo bairro ($\hat{\gamma}_{01}=@@HLM_G01@@$
por desvio-padrão da composição racial do bairro), chega-se ao \textbf{gap líquido de @@HLM_GAP3@@\%} (M3);
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
trabalho (H1) é que o \emph{bairro} media parte do gap racial; o modelo, portanto, coloca
a UPA no nível~2 e trata a UF como conjunto de efeitos fixos --- 27 unidades são poucas para
um terceiro nível aleatório \cite{angrist2009}, e os 26 \emph{dummies} absorvem todo o
contexto estadual sem hipóteses distribucionais. O modelo de dois níveis é dado pelas eq. (1) e (2):

\paragraph{Nível 1 --- indivíduo $i$ na UPA $j$, eq. (1):}
\begin{equation}
  \ln(W)_{ij} = \beta_{0j} + \beta_1\,\text{Negro}_{ij} + \beta_2\,\text{Sexo}_{ij}
  + \beta_3\,X_{ij} + \beta_4\,X^2_{ij} + \sum_{e}\beta_{e}\,\text{Educ}_{e,ij}
  + \boldsymbol{\beta}_{5}'\mathbf{Z}_{ij} + \varepsilon_{ij}
  \label{eq:nivel1}
\end{equation}
em que $\mathbf{Z}$ reúne horas, situação urbana e ano (e, no M4, vínculo e
grupo CBO), e o termo de erro é $\varepsilon_{ij}\sim\mathcal{N}(0,\sigma^2)$.

\paragraph{Nível 2 --- bairro $j$ (UPA), eq. (2):}
\begin{equation}
  \beta_{0j} = \gamma_{00} + \gamma_{01}\,\overline{\%\text{Negro}}_{j}
  + \gamma_{02}\,\overline{\text{Desemprego}}_{j} + \gamma_{03}\,\overline{\text{Educ}}_{j}
  + \sum_{k=2}^{27}\delta_k\,\text{UF}_{k(j)} + u_{0j}
  \label{eq:nivel2}
\end{equation}
com $u_{0j}\sim\mathcal{N}(0,\tau^2_{\text{UPA}})$.
O coeficiente $\gamma_{01}<0$ é a evidência de \textit{duplo disadvantage}: morar em
bairros com maior concentração de negros reduz o rendimento \emph{independentemente}
da raça individual. A correlação intraclasse, calculada por
$\rho_{\text{UPA}} = \tau^2_{\text{UPA}}/(\tau^2_{\text{UPA}} + \sigma^2)$,
mede a fração da variância do log-rendimento que está \emph{entre} bairros; valores
acima de 5\% justificam o modelo multinível \cite{raudenbush2002}.

\paragraph{Estratégia \emph{step-up}.} Seguindo \citeonline{raudenbush2002}, os modelos
são estimados em degraus aninhados: M0 (nulo: só o intercepto aleatório, que dá o ICC);
M1 (+ capital humano e demografia); M2 (+ contexto do bairro, nível~2); M3 (+ efeitos
fixos de UF) --- o modelo principal, que produz o \textbf{gap líquido}; e M4 (+ vínculo
e grupo ocupacional), reportado como \emph{limite inferior} porque ocupação e formalidade
são desfechos da própria discriminação (\emph{bad controls}) \cite{angrist2009}.
Cada degrau é comparado ao anterior por teste de razão de verossimilhança (LR), e a
redução de $\tau^2_{\text{UPA}}$ em relação ao M0 mede a variância entre bairros explicada
pelos controles. Testa-se ainda uma \emph{inclinação aleatória} de \texttt{negro} por UPA
(M3 + $u_{1j}\text{Negro}_{ij}$, com covariância não estruturada) --- a penalidade racial
varia entre bairros? --- por LR com dois graus de liberdade. Todos os modelos são
estimados por máxima verossimilhança (ML), necessária para comparar efeitos fixos entre
degraus; com $N=@@P:N_HLM:1:milhoes@@$~milhões, REML e ML produzem os mesmos componentes de variância
(no M0, $\hat\tau^2_{\text{UPA}} = @@HLM_TAU0_ML@@$ por ML e @@HLM_TAU0_REML@@ por REML;
ICC idêntico até a quarta casa).

""", S),

    ("3.2 Resultados do HLM (step-up, figura e OVB)",
     r"\\subsection\{Modelos Hierárquicos Lineares --- Mediação Contextual do Gap\}.*?(?=\\subsection\{Modelos de Machine Learning e SHAP Values\})",
     r"""\subsection{Modelos Hierárquicos Lineares --- Mediação Contextual do Gap}
\label{subsec:hlm_resultados}

Quanto do gap racial sobrevive à comparação entre dois trabalhadores que moram no
mesmo bairro? A pergunta separa duas histórias muito diferentes. Se quase nada
sobrevive, o diferencial de renda é sobretudo consequência de onde negros e brancos
conseguem morar. Se quase tudo sobrevive, o bairro é cenário, e a diferença se produz
pessoa a pessoa, dentro da mesma rua. A Tabela~\ref{tab:hlm_resultados} responde em
cinco degraus, do modelo nulo (M0) ao modelo com ocupação (M4), todos com intercepto
aleatório por UPA e estimados por máxima verossimilhança sobre a população completa:
acompanhe a linha \textbf{Raça (negro)} da esquerda para a direita e veja o coeficiente
aproximar-se de zero à medida que cada degrau acrescenta um bloco de controles.

\paragraph{Mais de um terço da diferença de renda está entre bairros, não dentro deles.}
Antes de qualquer controle, o modelo nulo reparte a variação do log-rendimento em duas
parcelas: a que separa um bairro de outro e a que separa dois vizinhos. O ICC da UPA é
de @@HLM_ICC0@@\footnote{$\hat\tau^2_{\text{UPA}} = @@HLM_TAU0@@$ (variância entre
bairros) e $\hat\sigma^2 = @@HLM_SIG0@@$ (variância entre pessoas do mesmo bairro), com
ICC $= \hat\tau^2/(\hat\tau^2+\hat\sigma^2)$.} --- isto é, \textbf{@@HLM_ICC0_PCT@@\% da
variância do log-rendimento está entre bairros}. Em linguagem de leitor: de toda a
diferença de renda entre duas pessoas sorteadas ao acaso no país, mais de um terço já
está associada a morarem em bairros diferentes, antes de se saber qualquer outra coisa
sobre elas. É muito acima do limiar de 5\% a partir do qual \citeonline{raudenbush2002}
consideram indispensável tratar a estrutura aninhada, e maior do que a parcela entre
estados (cerca de @@P:N3_ICC_UF_M0:0@@\%, no modelo alternativo com UF aleatória usado como robustez).
Ignorar essa estrutura trataria como independentes pessoas que compartilham o mesmo
mercado de trabalho local.

\paragraph{@@TITULO_BAIRRO@@.}
Com escolaridade, idade, sexo, horas, situação urbana e ano, mas \emph{sem} nenhum
efeito de bairro (OLS com efeitos fixos de UF, Subseção~\ref{subsec:inferencia}),
trabalhadores negros recebem \textbf{@@HLM_GAP_POOL@@\% a menos} que brancos comparáveis
($\hat\beta = @@HLM_B_POOL@@$). O M1 acrescenta o intercepto aleatório de UPA --- na
prática, um nível de renda próprio para cada bairro --- e com ele a comparação deixa de
ser entre todos os trabalhadores do país e passa a ser entre negros e brancos \emph{do
mesmo bairro}: a penalidade cai para \textbf{@@HLM_GAP1@@\%}\footnote{$\hat\beta_{\text{negro}}^{M1} = @@HLM_B1@@$, IC~95\%: @@HLM_B1_IC@@.}. Medida na régua do gap agregado,
\textbf{@@HLM_MED_BAIRRO@@\% da distância já foi percorrida} --- percorrida no sentido de
atribuída a um fator observável, e não no sentido de explicada sem discriminação, já que
o bairro em que se consegue morar é ele próprio produto de exclusão. Esse é o teste da
Hipótese~H1, e ele passa: negros e brancos com o mesmo capital humano não moram nos
mesmos bairros, e os bairros pagam diferente. Os controles individuais explicam, além
disso, @@HLM_TAU_EXPL_M1@@\% da variância entre bairros do M0 --- parte do que parecia
``bairro'' é composição de quem mora nele.

\noindent Vale guardar a frase: @@P:MED_BAIRRO:1@@\% do gap racial não separam duas pessoas,
separam dois endereços. Resta saber o que, num endereço, produz essa diferença.

\paragraph{Morar onde moram os negros custa outra vez.}
O M2 pergunta o que, num bairro, faz a renda ser mais alta ou mais baixa, e responde com
três covariáveis de nível~2 que juntas explicam @@HLM_TAU_EXPL_M2_REL@@\% da variância
entre bairros que restava no M1\footnote{$\hat\tau^2$ cai de @@HLM_TAU_M1@@ para
@@HLM_TAU_M2@@; LR $=$ @@HLM_LR2@@, 3 g.l., $p<0{,}001$.}. A mais eloquente é a
composição racial: $\hat\gamma_{01} = @@HLM_G01@@$ significa que um desvio-padrão a mais
na proporção de moradores negros da UPA reduz o rendimento de \emph{todos} os moradores,
negros e brancos, em @@HLM_G01_ABS@@ log-pontos --- cerca de @@P:G01_RAZAO:1@@ vezes a
penalidade que um trabalhador negro carrega individualmente no mesmo modelo. É a evidência
mais direta da \emph{dupla desvantagem}: ser negro custa, e morar onde moram os negros
custa outra vez, inclusive para quem não é negro. Já o coeficiente individual mal se move
(de $@@HLM_B1@@$ para $@@HLM_B2@@$): acrescentar a composição do bairro quase não altera a
penalidade racial média --- as duas desvantagens se somam, em vez de uma explicar a outra.

\noindent Em uma frase: o bairro cobra duas vezes --- da pessoa negra, pela cor; e de todos
os que moram ali, pela composição racial do lugar.

\paragraph{Acrescentar o estado não move a régua.}
Com os efeitos fixos de UF, a penalidade é de \textbf{@@HLM_GAP3@@\%}
($\hat\beta_{\text{negro}}^{M3} = @@HLM_B3@@$). Na régua do gap
agregado, @@HLM_MED_ACUM_M3@@\% --- praticamente os mesmos @@HLM_MED_BAIRRO@@\% do M1. O
dado relevante aqui é o que \emph{não} aconteceu: depois que a comparação já é entre
vizinhos, o contexto do bairro (M2) e a unidade da federação (M3) retiram pouco
mais do diferencial. É esse patamar que este trabalho chama de \textbf{gap líquido}: o
que capital humano, contexto de bairro e estado não explicam --- um limite superior da
penalidade direta sob seleção em observáveis (o M4 é o inferior), e não uma medida de
discriminação.\footnote{IC~95\% de $\hat\beta_{\text{negro}}^{M3}$: @@HLM_B3_IC@@. O ICC cai para @@HLM_ICC3@@ e os controles acumulados explicam
@@HLM_TAU_EXPL_M3@@\% da variância entre bairros do M0; a escada completa está nas linhas
inferiores da Tabela~\ref{tab:hlm_resultados}.}

\paragraph{Bairro ou estado? A separação em três camadas.}
Uma objeção natural: se bairros pobres se concentram em estados pobres, o que este
trabalho chama de efeito do bairro pode ser efeito da região. O modelo de dois
níveis não separa as duas coisas --- ele trata a UF como efeito fixo, e por isso
credita ao bairro tudo o que é territorial. Para medir a separação, o modelo nulo
foi reestimado com \textbf{três} níveis: pessoa dentro de bairro dentro de estado,
com intercepto aleatório nos dois.

O resultado divide o território em duas partes desiguais. Dos
@@HLM_ICC0_PCT@@\% que o modelo de dois níveis atribui ao bairro,
\textbf{@@N3_ICC_UPA0@@\%} permanecem entre bairros do \emph{mesmo} estado e
\textbf{@@N3_ICC_UF0@@\%} são diferenças entre estados. Depois dos controles
individuais e do contexto do bairro, o bairro cai para @@N3_ICC_UPA2@@\% e o estado
para @@N3_ICC_UF2@@\%: @@N3_LEITURA@@@@N3_NOTA@@


\paragraph{Dentro da mesma ocupação o gap encolhe --- o que não é o mesmo que explicá-lo.}
O M4 acrescenta vínculo e grupo ocupacional, e a penalidade cai para
\textbf{@@HLM_GAP4@@\%} ($\hat\beta_{\text{negro}}^{M4} = @@HLM_B4@@$). A régua vai a
\textbf{@@HLM_MED_ACUM_M4@@\% do gap agregado}. A tentação é ler esse número como a parte do
gap que está ``explicada'', e é precisamente essa leitura que o desenho do estudo
não autoriza: a ocupação não é uma característica que a pessoa traz consigo, é um
resultado ao qual ela precisou obter acesso --- e o acesso é justamente onde a
Subseção~\ref{subsec:glmm_resultados} encontra uma barreira própria, que a decomposição
salarial só capta em parte. Controlar por
ocupação é, portanto, descontar do gap uma parte do próprio gap. Por isso o M4 é um
limite inferior descritivo, e não o número a citar como a penalidade racial brasileira.

\paragraph{O mesmo controle pode ser legítimo num modelo e viciado noutro.}
A regra não é ``controlar por tudo'' nem ``nunca controlar por resultado'': depende do
que se está explicando. A jornada trabalhada ilustra bem. No modelo de rendimento ela
é \emph{necessária}, porque o desfecho é o rendimento \textbf{mensal}: sem ela,
comparar-se-ia quem trabalha meio período com quem trabalha jornada integral e a
diferença seria creditada à raça. No modelo de acesso o desfecho é \emph{ocupar} o
cargo, e a jornada não causa esse acesso --- ela é determinada junto com a ocupação,
de modo que condicionar nela desconta parte do próprio fenômeno. Por isso a jornada
entra no bloco individual do modelo de rendimento e, no de acesso, só no degrau
rotulado como limite inferior, ao lado do vínculo.

O critério que organiza os dois modelos é, então, o \emph{estatuto causal} de cada
variável em relação ao desfecho daquele modelo, e não a semelhança das listas
(Tabela~\ref{tab:simetria}):

\begin{table}[!ht]
\centering
\caption{Simetria dos controles entre os dois modelos. Os blocos predeterminados são
idênticos; o que difere é o tratamento das variáveis que são elas próprias desfecho
do processo estudado.}
\label{tab:simetria}
\small
\begin{tabular}{p{3.4cm}p{4.6cm}p{4.6cm}}
\toprule
Bloco & Modelo de rendimento (HLM) & Modelo de acesso (GLMM) \\
\midrule
Predeterminados & sexo, idade, idade$^2$, escolaridade (4 degraus
cumulativos), área urbana, ano, estado & os mesmos \\
\addlinespace[3pt]
Contexto do bairro & \% negro, desemprego e escolaridade média da UPA & os mesmos \\
\addlinespace[3pt]
Jornada & controle necessário: o desfecho é rendimento mensal & desfecho do processo:
entra só no degrau de limite inferior \\
\addlinespace[3pt]
Vínculo e ocupação & limite inferior (M4) & limite inferior (A3); a ocupação não entra,
pois é o próprio desfecho \\
\bottomrule
\end{tabular}
\par\smallskip\footnotesize Fonte: Resultados originais da pesquisa.
\end{table}


\noindent Dito de outro modo: @@HLM_GAP4@@\% é onde a régua termina, não onde o gap
verdadeiro está. O número deste trabalho é o gap líquido de @@HLM_GAP3@@\% do M3; o
@@HLM_GAP4@@\% mede o que sobra depois de descontar um canal que é ele próprio
discriminatório.

\paragraph{A penalidade não é a mesma em todo bairro.}
Até aqui a penalidade racial foi tratada como um número único. Deixá-la variar de bairro
para bairro melhora significativamente o ajuste (LR $=$ @@HLM_LR_RS@@, 2 g.l.,
$p<0{,}001$), e o desvio-padrão dessa variação é de @@HLM_SD1@@
log-pontos\footnote{$\hat\tau^2_1 = @@HLM_TAU1@@$, componente de variância da inclinação
aleatória de \texttt{negro} por UPA.}. Em bairros a um desvio-padrão de cada lado da
média, a penalidade vai de @@HLM_RS_LO@@ a @@HLM_RS_HI@@ log-pontos: há bairros em que o
diferencial é mais do que o dobro da média e bairros em que ele se inverte. A
discriminação salarial tem geografia --- e a covariância entre intercepto e inclinação
(@@HLM_COV01@@) indica que a penalidade é @@HLM_COV01_TXT@@ nos bairros de renda-base
mais alta. A Figura~\ref{fig:hlm_blups} contrasta os efeitos fixos de estado com os
interceptos estimados para os bairros, e a Figura~\ref{fig:hlm_rs} mostra a reta de
cada bairro.

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

\begin{figure}[htbp]
  \centering
  \includegraphics[width=\textwidth]{hlm_rs_retas_upa}
  \caption{Nos bairros de renda mais alta, a penalidade racial é @@HLM_COV01_TXT@@. M3 com
  intercepto e inclinação de \texttt{negro} aleatórios por UPA: à esquerda, a reta ajustada
  de cada bairro (amostra de @@P:HLM_RS_N_AMOSTRA:0@@ UPAs com brancos e negros) e, em azul, a média; à direita,
  os BLUPs $u_{0j}$ e $u_{1j}$ das @@P:N_UPAS_HLM:0:mil@@ UPAs, com correlação estimada de
  @@P:HLM_RS_CORR:2@@.}
  \label{fig:hlm_rs}
\end{figure}
\noindent\emph{Como ler a Figura~\ref{fig:hlm_rs}:} à esquerda, a altura de cada reta é a
renda-base do bairro e a inclinação é a penalidade racial dentro dele --- retas que descem
mais são bairros que penalizam mais. À direita, cada ponto é um bairro, e a reta azul resume a
relação: se ela desce, bairros de renda-base maior têm inclinação mais negativa, isto é,
penalizam mais.

\paragraph{O gap verdadeiro está entre dois limites, e nenhum confundidor plausível o anula.}
O coeficiente racial é uma associação condicional: pela fórmula do viés de variável
omitida \cite{angrist2009}, o coeficiente ``curto'' iguala o ``longo'' mais o efeito do
omitido vezes sua relação com a raça. Qualidade da escola, habilidade não observada e
redes de contato correlacionam-se negativamente com ser negro e positivamente com a
renda: omiti-las \emph{superestima} a penalidade --- o que faz do M3 um limite superior
para o efeito de tratamento diferencial condicional a essas características. Na direção
oposta, os controles que são desfechos (ocupação no M4) \emph{subestimam}. O gap líquido
deve ser lido entre esses dois limites. Para anular $\hat\beta^{M3}_{\text{negro}}$ seria
preciso um viés de @@HLM_KONF3@@\% do coeficiente, pelo Konfound \cite{frank2013}, e o
E-value do modelo de acesso (Tabela~\ref{tab:glmm_glassceil}) exige um confundidor
associado à raça e ao desfecho com razão de risco $\geq @@G_EV_CBO_M2@@$ --- uma associação
modesta, que sozinha não descarta viés.

\input{outputs/tables/hlm_stepup.tex}

""", S),

    ("3.2 Discussão: gamma01 e mediação lidos do csv",
     r"\$\\hat\{\\gamma\}_\{01\} = -0\{,\}269\$ para a proporção de negros na UPA\nindica que a penalidade de viver em bairro segregado equivale,\nem magnitude, à própria penalidade individual de ser negro\.",
     "$\\hat{\\gamma}_{01} = @@HLM_G01@@$ por desvio-padrão da proporção de negros na UPA\n"
     "indica que a penalidade de viver em bairro segregado é da mesma ordem\n"
     "de grandeza da própria penalidade individual de ser negro --- e que @@HLM_ICC0_PCT@@\%\n"
     "da variância do rendimento está entre bairros, não entre pessoas.", 0),

    ("3.2 Discussão: 'achado mais robusto' com a mediação pelo bairro",
     r"O achado mais robusto desta análise é que [\d.,]+\\% do gap salarial racial\nbruto é mediado pelo local de moradia",
     "O achado mais robusto desta análise é que @@HLM_MED_BAIRRO@@\\% do gap salarial racial\n"
     "condicional a capital humano é mediado pelo bairro de moradia", 0),


    # ── Bloco 5 — bad control, reflexo e diagnósticos ─────────────────────────
    ("5.7 VIF: colinearidade está no bloco educacional, não em raça",
     r"Esses resultados descartam multicolinearidade problemática entre CBO e\nformalidade, validando a especificação completa do M4 sem necessidade de\nortogonalização ou eliminação de preditores\.",
     "@@VIF_ABERTURA@@ A colinearidade que houver \\textbf{não} contamina o coeficiente de\n"
     "interesse: o VIF de\n"
     "\\texttt{negro} é @@VIF_NEGRO@@ e o das variáveis de contexto da UPA fica abaixo de\n"
     "@@VIF_CTX_MAX@@. Entre as \\textit{dummies} de CBO e as variáveis de vínculo --- a\n"
     "colinearidade que se temia no M4 --- o VIF máximo é @@VIF_OCC_MAX@@. A especificação\n"
     "do M4 dispensa, portanto, ortogonalização ou eliminação de preditores; o que ela\n"
     "não dispensa é a ressalva de \\emph{bad control} (Seção~\\ref{subsec:hlm_resultados}).", 0),

    ("5.6 QR vs RIF: condicional vs incondicional",
     r"\(\\emph\{sticky floor\}\)\. \\emph\{Como ler:\} na Tabela~\\ref\{tab:rif_ob\}, Dotações \$\+\$\nRetornos \$=100\\%\$ em cada quantil; siga a coluna Retornos caindo de \$@@RIF_RET_Q10@@\\%\$ \(q10\)\na \$@@RIF_RET_Q90@@\\%\$ \(q90\) --- a discriminação de preço pesa mais na base\.",
     "(\\emph{sticky floor}). \\emph{Como ler:} na Tabela~\\ref{tab:rif_ob}, Dotações $+$\n"
     "Retornos $=100\\%$ do gap RIF --- a coluna ao lado do gap observado ---,\n"
     "e a coluna Retornos cai de $@@RIF_RET_Q10@@\\%$ (q10) a $@@RIF_RET_Q90@@\\%$ (q90):\n"
     "a parcela não explicada pesa mais na base. Como a RIF usa os controles da\n"
     "Oaxaca--Blinder \\emph{sem} ocupação, sua parcela de retornos na mediana\n"
     "($@@P:RIF_RET_Q50:1@@\\%$) se compara aos $@@P:OB_SEM_RET_PCT:1@@\\%$ da especificação (A)\n"
     "da Tabela~\\ref{tab:oaxaca_blinder}, e não aos $@@P:OB_COM_RET_PCT:1@@\\%$ da (B), que trata a\n"
     "ocupação como característica. O q25 pede cautela: ele cai sobre o salário mínimo,\n"
     "onde muitos trabalhadores têm exatamente a mesma renda. Num ponto de massa assim a\n"
     "densidade que a RIF usa não é bem definida e depende da largura de banda do\n"
     "\\emph{kernel}; por isso, no q25, o gap que a RIF decompõe fica bem abaixo do\n"
     "observado. As parcelas de dotações e retornos, que são razões, não dependem dessa\n"
     "escolha --- a densidade escala as duas pelo mesmo fator ---, e o padrão do q10 ao q90\n"
     "também não.\n\n"
     "@@QR_SEXO@@\n\n"
     "\\paragraph{Por que os dois padrões não se contradizem.} A regressão quantílica\n"
     "estima quantis \\emph{condicionais}: $\\hat\\beta(\\tau)$ compara negros e brancos na\n"
     "mesma posição \\emph{dentro} da distribuição de pessoas com o mesmo perfil observável.\n"
     "O crescimento de $|\\hat\\beta(\\tau)|$ ao longo de $\\tau$ significa que a dispersão\n"
     "condicional do rendimento é maior entre brancos --- \\emph{fanning out} na linguagem de\n"
     "\\citeonline{angrist2009} ---, e não que ``os negros do topo sofrem mais'': quantis não\n"
     "seguem indivíduos, e a leitura em termos de pessoas exigiria invariância de posto, que\n"
     "não se testa aqui. A RIF-OB, ao contrário, decompõe quantis \\emph{incondicionais} da\n"
     "distribuição de renda \\cite{firpo2018}: responde ``de que é feito o gap no q10 da renda\n"
     "do país''. Como a composição observável concentra negros na base, a parcela de retornos\n"
     "é maior ali; e como há mais dispersão condicional no topo, o coeficiente condicional\n"
     "cresce com $\\tau$. Os dois resultados são complementares --- um é sobre o \\emph{preço}\n"
     "pago a características, o outro sobre a \\emph{distribuição} de características.", 0),

    ("5.5/6.3 Limitações: hipóteses item a item (MHE-90) e COP",
     r"\\paragraph\{Desenho transversal e direções futuras\.\}",
     r"""\paragraph{Condicionar em quem tem renda positiva.}
Todos os modelos de rendimento são estimados entre ocupados com renda positiva. Isso é
\emph{condicionar no desfecho} (\citeonline{angrist2009}, cap.~3): se a discriminação
também reduz a probabilidade de estar ocupado, o gap salarial condicional mistura o
efeito sobre o salário com a seleção de quem permanece na amostra. A direção provável do
viés é de \emph{subestimação}: se os trabalhadores negros que conseguem se manter
ocupados são positivamente selecionados em atributos não observados, o gap entre os
observados é menor que o gap potencial na população. O modelo logístico de acesso trata
diretamente a outra metade do problema --- a probabilidade de chegar à ocupação
qualificada ---; uma correção de seleção à Heckman, que exigiria uma variável de
exclusão crível (algo que afete estar ocupado sem afetar o salário), fica como extensão
e não é estimada aqui. A leitura correta é, portanto: o gap líquido aqui reportado
é o gap \emph{entre ocupados}, não o gap potencial de toda a população em idade ativa.

\paragraph{As hipóteses, uma a uma, e o que acontece se falharem.}
Seguindo a recomendação de ``ser o próprio cético'' (\citeonline{angrist2009}, cap.~8):
\begin{enumerate}
  \item \textbf{Seleção em observáveis (CIA).} O gap líquido só é o efeito do tratamento
    diferencial se, condicional a $X$, a raça for ``como se'' aleatória. Não é: qualidade
    da escola, habilidade não medida e redes ficam fora. Se esses omitidos correlacionam
    negativamente com ser negro e positivamente com renda, o coeficiente \emph{superestima}
    a discriminação --- por isso o gap líquido é apresentado como limite superior dessa
    leitura, e o Konfound/E-value quantificam quanto de confundimento seria preciso.
  \item \textbf{\emph{Bad controls}.} Ocupação e formalidade são desfechos da
    própria discriminação; a jornada, não: com renda mensal, ela é controle necessário
    e entra nas duas especificações da Oaxaca--Blinder --- no modelo de acesso, só no
    degrau de limite inferior. Com eles (M4, Oaxaca-Blinder de acesso) o resultado é um
    \emph{limite inferior descritivo}: a parcela que opera pela porta de entrada some da
    conta. Sem eles (M3, especificação~(A) da Oaxaca-Blinder) tem-se o gap total
    condicional a capital humano e bairro. As duas versões são reportadas lado a lado.
  \item \textbf{Reflexo (Manski).} Uma média de bairro que inclui o próprio indivíduo é
    mecanicamente informativa sobre ele --- a raça da pessoa entraria no \% de negros do
    seu bairro. Por isso todas as médias de contexto, de UPA e de UF, são calculadas sem a
    própria observação (\emph{leave-one-out}), e a renda média do bairro, a mais exposta ao
    problema, fica fora dos modelos estatísticos e só entra como preditor no XGBoost. Isso remove o reflexo mecânico, mas choques
    comuns ao bairro ainda impedem leitura causal do coeficiente contextual.
  \item \textbf{Efeitos aleatórios.} O HLM e o GLMM supõem que o efeito de bairro não é
    correlacionado com os regressores. Como contraprova, todos os coeficientes foram
    reestimados com efeitos fixos de UF e erro-padrão agrupado por UPA, com as mesmas
    conclusões (Subseção~\ref{subsec:inferencia}).
  \item \textbf{Pesos e desenho amostral.} As estimativas são não ponderadas: descrevem a
    regressão na amostra. A robustez ponderada pelo peso da PNAD muda o gap em cerca de
    meio ponto percentual.
  \item \textbf{Correlação intragrupo.} Ignorá-la subestimaria os erros-padrão (Moulton);
    todos os modelos reportam erro-padrão agrupado por UPA ou o modelam por efeito
    aleatório, e o agrupamento por UF usa $t$ com $G-1$ graus de liberdade.
  \item \textbf{Significância com $N$ grande.} Com @@P:N_GLMM:1:milhoes@@ milhões de observações, quase tudo é
    ``significativo''; a leitura privilegia magnitude, intervalos de confiança e E-values,
    não asteriscos.
\end{enumerate}

\paragraph{Desenho transversal e direções futuras.}""", 0),

    ("5.3/5.4 SHAP: renda de vizinhança leave-one-out e robustez sem ela",
     r"A Tabela~\\ref\{tab:shap_importance\} revela que a \\textbf\{renda média da UPA\}\nfigura entre os preditores de maior peso do rendimento individual.*?o \\textit\{onde se mora\} supera em importância o \\textit\{quanto se estudou\}\.",
     "A Tabela~\\ref{tab:shap_importance} mostra o \\textbf{contexto do bairro} entre os\n"
     "preditores de maior peso do rendimento individual. A variável usada aqui é a renda\n"
     "média da UPA \\emph{excluindo o próprio indivíduo} (\\emph{leave-one-out}): a média que\n"
     "inclui a própria pessoa é mecanicamente correlacionada com seu rendimento --- o\n"
     "problema do reflexo \\cite{manski1993} --- e inflaria artificialmente a importância do\n"
     "território. Mesmo sem essa contaminação, o bairro permanece entre os preditores de\n"
     "primeira ordem, o que é consistente com a hipótese de \\citeonline{wilson1987}; a\n"
     "leitura correta, porém, é de \\emph{mediação} territorial --- choques comuns ao bairro\n"
     "(mercado de trabalho local, transporte, redes) afetam todos os moradores --- e não de\n"
     "efeito causal de um vizinho sobre o outro. Como checagem extrema, o mesmo XGBoost\n"
     "estimado \\emph{sem qualquer} renda de vizinhança perde pouco poder preditivo\n"
     "($R^2 = @@ML_R2_SR@@$ contra @@ML_R2_XGB@@ do modelo completo) e, nele, a contribuição\n"
     "média da raça é praticamente a mesma (@@SHAP_NEGRO_SR@@ contra @@SHAP_NEGRO@@ em\n"
     "$|\\text{SHAP}|$): o sinal racial não é um artefato da variável de contexto ---\n"
     "muda apenas a posição relativa no \\emph{ranking} (@@SHAP_RANK_SR@@\\textsuperscript{a} de\n"
     "@@SHAP_NFEAT_SR@@, contra @@SHAP_RANK@@\\textsuperscript{a} de @@SHAP_NFEAT@@), porque as demais\n"
     "variáveis absorvem parte do que o território explicava.", S),

    ("7.4 SHAP: beeswarm em largura plena (corta dependence e a subfigure órfã)",
     r"\\begin\{figure\}\[H\]\s*\\centering\s*\\begin\{subfigure\}\[b\]\{0\.49\\textwidth\}\s*\\includegraphics\[width=\\textwidth\]\{shap_beeswarm_xgb\}.*?\\label\{fig:shap\}\s*\\end\{figure\}",
r"""\begin{figure}[H]
  \centering
  \includegraphics[width=0.92\textwidth]{shap_beeswarm_xgb}
  \caption{Contexto do bairro, diploma superior e jornada dominam a previsão de renda; a raça
  aparece na @@P:SHAP_RACA_RANK_XGB:0@@\textsuperscript{a} posição entre @@P:SHAP_N_FEATURES:0@@ preditores (SHAP, XGBoost,
  $N_\text{SHAP}=50.000$).}
  \label{fig:shap}
\end{figure}""", S),

    ("7.4 SHAP: waterfall do par branco/negro",
     r"\\begin\{figure\}\[H\]\n  \\centering\n  \\begin\{subfigure\}\[b\]\{0\.32\\textwidth\}\n    \\includegraphics\[width=\\textwidth\]\{shap_waterfall_A_branco_alta_renda_xgb\}.*?\\label\{fig:shap_wf\}\n\\end\{figure\}",
r"""\begin{figure}[H]
  \centering
  % 06/10/2026: uma imagem só, painéis A e B (manual 15.1); duas subfiguras viravam, no
  % Word, uma tabela de leiaute que o Sistema de Trabalho Final acusava como problema
  \includegraphics[width=0.62\textwidth]{shap_waterfall_AB_xgb}
  \caption{A mesma variável, sinais opostos: a raça soma à previsão do
  trabalhador branco e subtrai da do negro. Decomposição SHAP individual
  (\emph{waterfall}) de dois trabalhadores, cada um no percentil~75 de rendimento
  do próprio grupo; cada barra é a contribuição de uma variável ao afastamento entre
  a previsão média da base e a previsão daquele caso, em log-pontos, e as de menor
  peso estão agrupadas na linha das demais. O painel A é o trabalhador branco, e o B, o
  negro. Os painéis mostram como o modelo compõe
  uma previsão: a diferença de rendimento entre os dois é bruta, sem os controles
  que os modelos aplicam.}
  \label{fig:shap_wf}
\end{figure}""", S),

    ("8.1/8.2 CV, hiperparâmetros e erro em reais",
     r"\\paragraph\{Ausência de sobreajuste \(população completa\)\.\}",
     r"""\paragraph{Escolha de hiperparâmetros e validação cruzada.}
A profundidade das árvores, a taxa de aprendizado e o número de iterações não foram
fixados por conveniência: seis configurações foram comparadas numa partição de validação
\emph{dentro} do conjunto de treino --- o teste permanece intocado ---, e a vencedora foi
submetida a validação cruzada $k$-\emph{fold} ($k=5$) no treino completo
(Tabelas~\ref{tab:ml_cv} e~\ref{tab:ml_cv_b}). A configuração escolhida (profundidade @@CV_DEPTH@@) alcança
$R^2 = @@CV_R2@@ \pm @@CV_R2_DP@@$ entre os \emph{folds}, contra
@@CV_R2_ANT@@ $\pm$ @@CV_R2_ANT_DP@@ da profundidade~6 usada na versão anterior deste
trabalho, sem aumentar o sobreajuste. O desvio-padrão entre \emph{folds} na quarta casa
decimal mostra que, com @@CV_N_TREINO@@ observações de treino, o desempenho não depende de
qual parte dos dados é usada para validar --- a validação cruzada aqui serve menos para
estimar incerteza e mais para justificar a especificação.
\input{outputs/tables/ml_cv.tex}

\paragraph{O erro na unidade original.} Os modelos preveem o \emph{logaritmo} do
rendimento; para o leitor, o que importa é o erro em reais. Retransformando com a correção
de \citeonline{duan1983} (fator de \emph{smearing} $= @@CV_SMEAR@@$), o erro mediano de
previsão é de \textbf{R\$~@@CV_ERRO_MED@@ por mês} (reais do 2º~trimestre de 2026), ou @@CV_ERRO_PCT@@\% do rendimento
observado --- a ordem de grandeza que se deve ter em mente ao ler o $R^2$: o modelo acerta
a posição relativa das pessoas muito melhor do que o valor exato do salário de cada uma.

\paragraph{Ausência de sobreajuste (população completa).}""", 0),

    ("rev-final ML: hiperparâmetros escolhidos por validação cruzada",
     r"\(ii\)~\\textit\{XGBoost\} \\cite\{chen2016\} com 300 iterações,\n\$\\text\{lr\}=0\{,\}05\$ e regularização \$L_1/L_2\$\.",
     "(ii)~\\textit{XGBoost} \\cite{chen2016} com 300 iterações, taxa de aprendizado\n"
     "$0{,}05$, profundidade máxima @@CV_DEPTH@@ e regularização $L_1/L_2$. A profundidade\n"
     "foi escolhida por validação cruzada (Tabela~\\ref{tab:ml_cv}), e não por conveniência;\n"
     "os dois modelos usam o mesmo conjunto de \\emph{features} e a mesma partição de teste.", 0),

    # ── Revisão de Literatura: arcabouço teórico, parâmetros brasileiros e
    #    os artigos fundadores de cada método (antes só no \nocite) ──────────
    ("rev-lit: teoria da discriminação antes da evidência",
     r"\\subsection\{Desigualdade racial no mercado de trabalho brasileiro\}",
     r"""\subsection{Por que haveria discriminação: as duas teorias}

A economia do trabalho oferece duas explicações concorrentes para um
diferencial salarial que sobrevive ao controle de produtividade observável, e
elas importam porque implicam políticas distintas.
\citeonline{becker1957} propôs a discriminação \emph{por preferência}: empregadores,
colegas ou clientes têm uma desutilidade em transacionar com o grupo
minoritário e, por isso, só o contratam a um salário menor. A previsão desse
modelo é que a concorrência erode a discriminação --- empresas que discriminam
pagam mais caro pela mesma produtividade e tendem a ser expulsas do mercado.
\citeonline{arrow1973} formalizou a alternativa: a discriminação \emph{estatística},
em que o empregador, diante de informação imperfeita sobre a produtividade
individual, usa a raça como sinal da média do grupo. Aqui a concorrência não
corrige nada; ao contrário, o equilíbrio se autoconfirma, porque o menor retorno
esperado desestimula o investimento em qualificação por parte do grupo
discriminado.

A distinção tem consequência direta para a leitura dos resultados deste
trabalho. O componente de \emph{retornos} da decomposição de Oaxaca--Blinder é
compatível com as duas teorias, e os dados observacionais aqui usados não
permitem separá-las --- uma limitação assumida explicitamente
(Seção~\ref{sec:conclusao}). O que os dados permitem é testar uma implicação
comum às duas: se a barreira opera também no \emph{acesso} às ocupações, e
não só no preço pago dentro delas, então políticas de qualificação isoladas
serão insuficientes sob qualquer das duas hipóteses teóricas.

A tradição brasileira acrescenta uma terceira leitura. \citeonline{almeida2019}
argumenta que o racismo não é desvio individual nem falha informacional, mas
processo estrutural: as instituições reproduzem a desigualdade racial por
mecanismos que independem da intenção dos agentes --- o que desloca a pergunta
de ``quem discrimina'' para ``que arranjos produzem o resultado desigual''. É
essa leitura que justifica investigar a segregação residencial e a segregação
ocupacional como mecanismos, e não como controles.

\subsection{Desigualdade racial no mercado de trabalho brasileiro}""", 0),

    ("rev-lit: parâmetros empíricos brasileiros com números",
     r"Trabalhos posteriores~\\cite\{henriques2001, soares2009\} confirmaram a\npersistência dessas diferenças mesmo após controlar por escolaridade,\nreforçando a hipótese de discriminação estrutural\.",
     r"""\citeonline{henriques2001} documentou, para a década de 1990, que a escolaridade
média de trabalhadores negros era de cerca de dois anos a menos que a de
brancos e que essa diferença explicava apenas parte do diferencial de
rendimentos. \citeonline{soares2009}, cobrindo 1976--2006, estimou por decomposição
que em torno de metade do gap racial de rendimentos não era explicada por
características observáveis --- parcela que sua análise atribui a
discriminação salarial e a diferenças de qualidade da educação recebida. Esses
são os parâmetros de referência com que os resultados deste trabalho dialogam
na Seção~\ref{sec:discussao}; a comparação exige cautela, porque a magnitude do
componente não explicado depende de quais controles se tratam como dotações
(ver Seção~\ref{subsec:oaxaca_metodo}).""", 0),

    # a subseção de resultados de QR/RIF não tinha rótulo, e a revisão passou a
    # remeter a ela
    ("rev-lit: rótulo da subseção de QR/RIF nos resultados",
     '\\\\subsection\\{Regressão\\ Quantílica\\ e\\ RIF\\-OB:\\ teto\\ de\\ vidro\\ e\\ \\\\emph\\{sticky\\ floor\\}\\}',
     '\\subsection{Regressão Quantílica e RIF-OB: teto de vidro e \\emph{sticky floor}}\n\\label{subsec:qr_rif}', 0),

    ("rev-lit: decomposições, quantis e interseccionalidade",
     r"\\subsection\{Interpretabilidade em machine learning: SHAP values\}",
     r"""\subsection{Decomposições salariais e a distribuição do gap}

O instrumental que separa ``ter características diferentes'' de ``receber
preços diferentes'' vem de \citeonline{oaxaca1973} e \citeonline{blinder1973}, que
propuseram, de forma independente, decompor a diferença de médias entre dois
grupos em uma parcela de \emph{dotações} --- atribuível a diferenças nas
características observáveis --- e outra de \emph{retornos}, atribuível a
diferenças nos coeficientes com que essas características são remuneradas.
\citeonline{oaxaca_ransom1999} mostraram, porém, que a repartição não é única: ela
depende de quais variáveis se admite como dotação. Tratar a ocupação como
característica do trabalhador desloca para a parcela explicada toda a
desigualdade que opera pela porta de entrada da ocupação --- razão pela qual
este trabalho reporta as duas especificações lado a lado.

A decomposição de médias, contudo, descreve apenas o trabalhador médio.
\citeonline{koenker1978} introduziram a regressão quantílica, que estima o efeito
de um regressor em cada ponto da distribuição condicional e permite verificar
se a penalidade racial é uniforme ou se cresce rumo ao topo --- a formulação
estatística do teto de vidro. \citeonline{firpo2018} estenderam a decomposição para
quantis \emph{incondicionais} por meio de regressões da função de influência
recentrada (RIF), respondendo a uma pergunta distinta: de que é feito o gap em
um dado ponto da distribuição de renda do país, e não da distribuição
condicional a um perfil. As duas leituras são complementares e, como se verá,
apontam para padrões aparentemente opostos que descrevem o mesmo fenômeno
(Seção~\ref{subsec:qr_rif}).

\subsection{Interseccionalidade}

\citeonline{crenshaw1989} cunhou o conceito de interseccionalidade a partir da
constatação de que a experiência de mulheres negras não é descrita pela soma
das categorias ``mulher'' e ``negra'': há um efeito próprio da posição na
interseção dos eixos, que análises que tratam raça e gênero separadamente não
capturam. Empiricamente, isso implica testar se o diferencial do grupo excede a
soma dos diferenciais isolados --- e, portanto, se políticas desenhadas para um
eixo de cada vez deixam de fora justamente quem está na interseção.

\subsection{Interpretabilidade em machine learning: SHAP values}""", 0),

    # ── Metodologia: os três métodos do núcleo que só apareciam nos resultados
    ("metodo: OB, QR/RIF e GLMM na metodologia, com os artigos fundadores",
     r"\\subsection\{Random Forest, XGBoost e SHAP Values\}",
     r"""\subsection{Decomposição de Oaxaca--Blinder}
\label{subsec:oaxaca_metodo}

Estimam-se equações de rendimento separadas para brancos e negros e
decompõe-se a diferença de médias na forma \emph{twofold} de
\citeonline{blinder1973} e \citeonline{oaxaca1973}, tomando a estrutura de preços dos brancos como
referência não discriminatória:
$\ln \bar W_B - \ln \bar W_N = (\bar X_B - \bar X_N)'\hat\beta_B +
\bar X_N'(\hat\beta_B - \hat\beta_N)$, em que o primeiro termo é a parcela de
dotações e o segundo, a de retornos. Duas especificações são reportadas:
(A)~capital humano, jornada, área urbana, contexto de bairro e efeitos fixos de UF ---
os controles do HLM~M3 ---, comparável à literatura; e (B)~acrescentando formalidade e
grupo ocupacional como dotações (os controles do M4). Como
adverte \citeonline{oaxaca_ransom1999}, a especificação~(B) subestima a
discriminação total, porque a segregação ocupacional é ela própria seu
produto --- por isso ela é lida como limite inferior, e não como a estimativa
preferida. Os erros-padrão vêm de bootstrap em blocos de UPA, e não da fórmula
analítica, que pressupõe independência entre observações \cite{cameron2008}.

\subsection{Regressão quantílica e decomposição RIF}

A regressão quantílica \cite{koenker1978} estima $\hat\beta(\tau)$ em seis
pontos da distribuição condicional ($\tau \in \{0{,}10;\ 0{,}25;\ 0{,}50;\
0{,}75;\ 0{,}90;\ 0{,}95\}$), permitindo testar se a penalidade racial é constante ao
longo da distribuição. O teste de igualdade compara $\tau = 0{,}90$ e $\tau = 0{,}10$
--- os mesmos extremos da decomposição RIF ---; o $\tau = 0{,}95$ é apenas descritivo. Ele usa
bootstrap \emph{m-out-of-n} em blocos de UPA, com reescala $\sqrt{m/G}$
\cite{bickel2008} --- necessária porque reamostrar todas as @@N_UPAS@@ UPAs a cada
réplica seria proibitivo com @@P:N_GLMM:1:milhoes@@~milhões de observações.
Complementarmente, a decomposição RIF \cite{firpo2018} é aplicada aos quantis
incondicionais da distribuição de renda, separando dotações e retornos em cada
ponto.

\subsection{Modelo logístico multinível de acesso}

A barreira de entrada é modelada por um GLMM logístico com intercepto
aleatório de UPA, estimado por \texttt{lme4::glmer} em R, para três desfechos
binários: ocupar cargo qualificado (grupos CBO 1--4), estar no quintil superior
e estar no decil superior da renda. A estrutura multinível é a mesma do HLM
\cite{raudenbush2002}, agora com função de ligação logit; o ICC do nível de
bairro é calculado por $\tau^2/(\tau^2 + \pi^2/3)$, a formulação de variância
latente apropriada ao modelo logístico. Além da razão de chances, reporta-se o
efeito marginal médio em pontos percentuais, porque a razão de chances não é
interpretável como diferença de probabilidade.

\subsection{Sensibilidade a variáveis omitidas}

A hipótese de seleção em observáveis não é testável, mas é possível quantificar
quanto de confundimento não observado seria necessário para anular os
resultados. Reportam-se duas medidas: o \emph{E-value}
\cite{vanderweele2017}, que é a associação mínima --- em razão de chances ---
que um confundidor precisaria ter simultaneamente com a raça e com o desfecho
para explicar o efeito observado; e o índice de \citeonline{frank2013}, que
expressa a fração da estimativa que precisaria ser viés para invalidar a
inferência.

\subsection{Random Forest, XGBoost e SHAP Values}""", 0),

    ("tipografia: legenda 1 pt menor, justificada, e barreira de floats",
     '\\\\usepackage\\{caption\\}',
     '\\usepackage{caption}\n% Legenda 1 pt menor que o corpo (em 12 pt, \\small = 11 pt), justificada e com\n% o rótulo em negrito; e um pouco de ar entre a legenda e o objeto.\n\\captionsetup{font=small, labelfont=bf, justification=justified,\n              singlelinecheck=false, skip=6pt}\n% placeins: nenhuma figura ou tabela atravessa para a subseção seguinte\n\\usepackage{placeins}\n\\let\\oldsubsectionFB\\subsection\n\\renewcommand{\\subsection}{\\FloatBarrier\\oldsubsectionFB}', 0),

    ("rev-final: remeter à tabela interseccional, que ninguém citava",
     'ocupação\\ qualificada\\ \\(CBO\\~1\\-\\-4\\),\\ renda\\ no\\ top\\~20\\\\%\\ e\\ no\\ top\\~10\\\\%\\.',
     'ocupação qualificada (CBO~1--4), renda no top~20\\% e no top~10\\%. A Tabela~\\ref{tab:interseccional} traz a decomposição de Oaxaca--Blinder dos quatro grupos contra o homem branco, e a Figura~\\ref{fig:interseccional}, as razões de chance nos três desfechos.', 0),

    # ── Títulos de ação nas figuras que ainda eram descritivas (SWD-55) ──
    # (patch "rev-final SWD: título de ação na figura SHAP" removido em 03/10/2026: o bloco da
    #  figura SHAP acima já traz o título de ação, e o alvo nunca chegava até aqui)

    # 04/10/2026 (releitura E8): a imagem já traz "entra pelas ocupações feminizadas, mas não
    # chega ao comando"; a legenda afirma o achado com outra frase, para não repetir o título
    ("rev-final SWD: título de ação na figura interseccional",
     r"\\caption\{Razões de chance dos quatro grupos raça\$\\times\$gênero",
     "\\caption{A vantagem aparente da mulher negra no acesso é de composição: razões de "
     "chance dos quatro grupos raça$\\times$gênero", 0),

    # ── Limitações ────────────────────────────────────────────────────────────
    ("0.2 Limitações: Heckman fora do núcleo",
     r"Os modelos HLM, a decomposição de Oaxaca--Blinder, a regressão quantílica e\na correção de Heckman produzem",
     "Os modelos HLM, a decomposição de Oaxaca--Blinder, a regressão quantílica e\no modelo logístico de acesso produzem", 0),
    ("0.2 Limitações: SNA vira agenda",
     r"com identificação de firma\. A SNA poderia ser refinada para grafos bipartidos\nUPA~\$\\times\$~grupo, elevando a resolução espacial da medida de segregação\.",
     "com identificação de firma. A análise de redes de co-residência, a tipologia\n"
     "por agrupamento e a priorização de políticas por pesquisa operacional,\n"
     "desenvolvidas em versão estendida deste trabalho, ficam como agenda. Também fica\n"
     "como agenda o uso de texto livre: a PNAD divulga ocupação e atividade já codificadas\n"
     "(CBO e CNAE Domiciliar), sem o relato aberto da entrevista, de modo que técnicas de\n"
     "processamento de linguagem natural não têm aqui onde se aplicar. Bases que associam\n"
     "texto a indivíduos --- descrições de cargo em registros administrativos, anúncios de\n"
     "vaga e currículos, como nos experimentos de auditoria \\cite{pager2007} --- permitiriam\n"
     "medir o conteúdo das funções e a triagem na contratação, que os códigos ocupacionais\n"
     "não captam. A descrição oficial dos códigos não supriria essa lacuna: seria a\n"
     "ocupação de novo, um \\emph{bad control} no modelo de rendimento e o próprio desfecho\n"
     "no de acesso. Fica ainda como agenda relacionar a penalidade estimada em cada estado\n"
     "à presença de pretos e pardos nos cargos eletivos, que a Justiça Eleitoral registra\n"
     "por cor ou raça desde 2014: a sub-representação negra no comando político seria a\n"
     "face institucional do teto de vidro aqui medido \\cite{almeida2019}, mas, com uma\n"
     "observação por estado, a comparação seria apenas ecológica.", 0),

    # ── Bloco 1 — fonte única de números ──────────────────────────────────────
    ("1.4 nota terminológica: líquido = M3, residual = M4",
     r"\\textbf\{Gap líquido\} \(ou residual\) é o diferencial que \\textit\{persiste\} após\no controle exaustivo de todas as covariáveis \(M4\) --- o piso para a discriminação\ndireta não explicada por observáveis\.",
     "\\textbf{Gap líquido} é o diferencial que \\textit{persiste} após o controle de\n"
     "capital humano e contexto (M3): @@HLM_GAP3@@\\%. \\textbf{Gap residual pós-ocupação} é o\n"
     "que resta ao se controlar também ocupação e formalidade (M4): @@HLM_GAP4@@\\% --- um limite\n"
     "inferior, pois a ocupação é ela própria resultado da barreira de acesso.", 0),

    ("1.1 ML: R² ≈ 0,43 → valor do csv",  # sem-fossil: rótulo do patch, não texto de saída
     r"O \$R\^2 \\approx 0\{,\}43\$ é robusto para dados de rendimento individual,",
     "O $R^2$ de teste de @@P:ML_XGB_R2:2@@ (XGBoost) é elevado para dados de rendimento individual,", 0),

    ("1.1 ML: N_teste da população",
     r"\\textit\{Hold-out\} 20\\%, \$N_\\text\{teste\}=307\.768\$ observações\.",
     "\\textit{Hold-out} 20\\% da população ($N_\\text{teste}\\approx @@P:CV_N_TESTE:2:milhoes@@$ milhão).", 0),

    ("6.1 intro: 'comprova' → 'mostra'",
     r"\\textbf\{Este trabalho comprova que o racismo no mercado de trabalho brasileiro\nnão opera como um evento isolado de discriminação salarial --- opera como\num sistema de barreiras em camadas que começa antes do primeiro salário,\npersiste ao longo de toda a trajetória profissional e se perpetua via\nexclusão das redes que convertem educação em mobilidade\.",
     "\\textbf{Este trabalho mostra que a desigualdade racial no mercado de trabalho\n"
     "brasileiro não se reduz a um desconto salarial isolado --- opera como um\n"
     "sistema de barreiras em camadas que começa antes do primeiro salário, na\n"
     "porta de entrada das ocupações qualificadas, e persiste ao longo de toda a\n"
     "trajetória profissional.", 0),

    # ---------------------------------------------------------------------
    # N3/N4/N5 — narrativa da subseção de machine learning
    # ---------------------------------------------------------------------
    ("N3.2 ML: abertura com a pergunta que justifica o método",
     flex(r"A Tabela~\ref{tab:ml_perf} apresenta o desempenho preditivo dos dois modelos "
          r"sobre o conjunto de teste (\textit{hold-out} 20\%)."),
     r"""Todos os modelos até aqui impuseram uma forma à realidade: rendimento linear nos
controles, efeitos que se somam, penalidade racial constante. E se a forma estiver
errada --- se o gap que os coeficientes mostram for, em alguma medida, artefato da
equação escolhida? Árvores de decisão respondem a essa objeção porque não pressupõem
forma nenhuma: descobrem sozinhas interações e não linearidades e, com os valores SHAP,
dizem quanto cada variável pesou em cada previsão. Se a raça aparecer entre os
preditores relevantes de um modelo que nunca foi instruído a procurá-la, o achado deixa
de depender da especificação. A Tabela~\ref{tab:ml_perf} traz o desempenho dos modelos
sobre o conjunto de teste, separado antes de qualquer ajuste.""", 0),

    ("N5 ML: aparato da validação cruzada desce para nota",
     flex(r"A configuração escolhida (profundidade @@CV_DEPTH@@) alcança "
          r"$R^2 = @@CV_R2@@ \pm @@CV_R2_DP@@$ entre os \emph{folds}, contra "
          r"@@CV_R2_ANT@@ $\pm$ @@CV_R2_ANT_DP@@ da profundidade~6 usada na versão anterior deste "
          r"trabalho, sem aumentar o sobreajuste. O desvio-padrão entre \emph{folds} na quarta casa "
          r"decimal mostra que, com @@CV_N_TREINO@@ observações de treino, o desempenho não depende de "
          r"qual parte dos dados é usada para validar --- a validação cruzada aqui serve menos para "
          r"estimar incerteza e mais para justificar a especificação."),
     r"""A configuração escolhida melhora o $R^2$ em relação à configuração de referência
(profundidade~6), com sobreajuste maior, mas ainda desprezível
(Tabelas~\ref{tab:ml_cv} e~\ref{tab:ml_cv_b}).\footnote{Profundidade @@CV_DEPTH@@, com
$R^2 = @@CV_R2@@ \pm @@CV_R2_DP@@$ entre os \emph{folds}, contra
@@CV_R2_ANT@@ $\pm$ @@CV_R2_ANT_DP@@ da profundidade~6 de referência, sobre
@@CV_N_TREINO@@ observações de treino.} Com um treino desse tamanho, a variação entre
\emph{folds} cai na quarta casa decimal: aqui a validação cruzada serve menos para
estimar incerteza e mais para justificar a especificação.""", 0),

    ("N5 ML: sobreajuste --- rótulo que afirma, aparato em nota",
     flex(r"\paragraph{Ausência de sobreajuste (população completa).} "
          r"Estimado sobre a população (\mbox{$N=$NUM$$}; treino~80\%/teste~20\%), "
          r"o método não-paramétrico não apresenta \textit{overfitting}: o $R^2$ de treino e de "
          r"teste praticamente coincidem (\textit{gap}~$=$NUM$$ para o XGBoost e "
          r"para o Random Forest). Três evidências convergem: o \textit{gap} treino--teste "
          r"$\approx 0$; a razão $N \gg$ complexidade (modelos regularizados sobre $NUM$~milhões de "
          r"observações); e a estabilidade do $R^2$ de teste entre a subamostra de 20\% e a "
          r"população (praticamente idêntico, $\approx $NUM$$). Em suma, \emph{ampliar} a base, "
          r"de amostral para populacional, \emph{reduz} --- não aumenta --- o risco de sobreajuste."),
     r"""\paragraph{Ampliar a base reduz o risco de sobreajuste, em vez de aumentá-lo.}
A objeção usual a modelos flexíveis é que eles decoram os dados em vez de aprender com
eles --- e quem decorou prevê bem o que já viu e mal o que não viu. Não é o caso aqui, e
a razão é o tamanho da base: o $R^2$ de treino e o de teste praticamente coincidem, com
diferença de @@ML_GAP_XGB@@\footnote{População completa, $N=@@P:ML_N:0:mil@@$, com 80\% para
treino e 20\% para teste; o mesmo \emph{gap} aparece no Random Forest.}. Três evidências
convergem: a diferença entre treino e teste é praticamente nula; o número de observações
supera em muitas ordens de grandeza a complexidade dos modelos, todos regularizados; e o
$R^2$ de teste quase não muda ao se passar de uma subamostra para a população inteira. É
o contrário da intuição corrente: ampliar a base, de amostral para populacional, reduz o
risco de sobreajuste em vez de aumentá-lo.""", 0),

    ("N5 SHAP: posições de ranking descem para nota",
     flex(r"muda apenas a posição relativa no \emph{ranking} (@@SHAP_RANK_SR@@\textsuperscript{a} de "
          r"@@SHAP_NFEAT_SR@@, contra @@SHAP_RANK@@\textsuperscript{a} de @@SHAP_NFEAT@@), porque as demais "
          r"variáveis absorvem parte do que o território explicava."),
     r"""muda apenas a posição relativa no \emph{ranking},\footnote{@@SHAP_RANK_SR@@\textsuperscript{a}
de @@SHAP_NFEAT_SR@@ variáveis no modelo sem renda de vizinhança, contra
@@SHAP_RANK@@\textsuperscript{a} de @@SHAP_NFEAT@@ no modelo completo.} porque as demais
variáveis absorvem parte do que o território explicava.""", 0),


    ("N3.7/N5 VIF: a objeção antes do inventário",
     r"Para verificar se a inclusão simultânea dos 9~dummies\s+"
     r"CBO e das variáveis de vínculo empregatício \(\\texttt\{emprego\\_formal\},\s+"
     r"\\texttt\{conta\\_propria\}, \\texttt\{trab\\_domestico\}\) introduz colinearidade\s+"
     r"problemática no Modelo~M4, calculou-se o \\textit\{Variance Inflation Factor\} \(VIF\)\s+"
     r"sobre (?:subsample de ([\d.]+) observações|a população completa) da PEA com renda positiva\.\s+"
     r"(Dos .*?variáveis baixas \(\$< 2\$\)\.)",
     lambda m: (
         "Os controles do M4 estão brigando entre si? A pergunta é legítima: o modelo "
         "empilha nove indicadores de grupo ocupacional sobre três de vínculo, e variáveis "
         "muito próximas entre si inflam o erro-padrão umas das outras, a ponto de tornar "
         "instável justamente o coeficiente que interessa. O \\textit{Variance Inflation "
         "Factor} mede esse efeito: quanto a variância de cada estimativa cresce "
         "em razão das demais. A resposta, aqui, é que há colinearidade --- mas não onde ela "
         "importaria.\\footnote{Calculado sobre "
         + (m.group(1) + " observações" if m.group(1) else "a população completa")
         + " da PEA com renda positiva. " + m.group(2) + "}"),
     S),


    ("N3.6 interseccionalidade: a pergunta antes da especificação",
     flex(r"Os modelos anteriores tratam raça e gênero de forma aditiva. Uma leitura "
          r"\textit{interseccional} pergunta se a desvantagem de ser negra \emph{e} mulher é a "
          r"soma das partes. Reespecificamos o GLMM de acesso com um fator de quatro grupos "
          r"(\texttt{grupo\_rg}: homem branco [referência], mulher branca, homem negro, mulher "
          r"negra) e a interação \texttt{negro$\times$sexo\_fem}, em três desfechos: acesso a "
          r"ocupação qualificada (CBO~1--4), renda no top~20\% e no top~10\%."),
     r"""Raça e gênero simplesmente se somam? Todos os modelos até aqui responderam que sim,
por construção: tratadas como penalidades aditivas, a desvantagem de ser negra \emph{e}
mulher seria a de ser negro mais a de ser mulher. \citeonline{crenshaw1989} desconfia
dessa aritmética, e a desconfiança é testável --- basta trocar os dois indicadores
separados por um único fator de quatro grupos e deixar que os dados digam se a soma
fecha.\footnote{GLMM de acesso reespecificado com \texttt{grupo\_rg} (homem branco como
referência, mulher branca, homem negro, mulher negra) e a interação
\texttt{negro$\times$sexo\_fem}, em três desfechos: ocupação qualificada (CBO~1--4),
renda no top~20\% e no top~10\%.}""", 0),

    ("N4.6 interseccionalidade: a inversão em dois tempos",
     r"O resultado revela uma \\textbf\{inversão\} \(Figura~\\ref\{fig:interseccional\}\)\. No\s+"
     r"\\textbf\{acesso à categoria\} qualificada, a mulher negra tem OR~\$=([\d,]+)\$\s+"
     r"--- \\emph\{acima\} do homem branco ---, porque o efeito de gênero é positivo nesse\s+"
     r"desfecho \(profissões credenciadas feminizadas, em CBO~1--4\); o grupo mais penalizado\s+"
     r"é o \\textbf\{homem negro\} \(OR~\$=([\d,]+)\$\)\. No \\textbf\{topo da renda\},\s+"
     r"porém, o quadro \\emph\{inverte\}: a mulher negra passa a ser a \\textbf\{mais excluída\}\s+"
     r"de todos --- OR~\$=([\d,]+)\$ no decil superior, abaixo da mulher branca\s+"
     r"\(\$=([\d,]+)\$\) e do homem negro \(\$=([\d,]+)\$\)\. A\s+"
     r"interação \\texttt\{negro\$\\times\$sexo\\_fem\} é \\textit\{sub-aditiva\} em todos os desfechos\s+"
     r"\(OR~\$=([\d,]+)\$ no acesso; \$=([\d,]+)\$ no top~10\\%\):\s+"
     r"a penalidade racial é ligeiramente menor entre mulheres, mas isso não impede que a\s+"
     r"mulher negra acumule a barreira racial \\emph\{e\} o teto de vidro de gênero exatamente\s+"
     r"onde mais importa para a ascensão --- o topo da distribuição\.",
     lambda m: (
         "\\paragraph{Na entrada, a vantagem da mulher negra é de ocupações feminizadas.}\n"
         "No acesso à ocupação qualificada (CBO~1--4) a mulher negra tem OR~$=" + m.group(1) + "$,\n"
         "mais chance do que o homem branco de referência, e o grupo mais penalizado na entrada\n"
         "é o \\textbf{homem negro} (OR~$=" + m.group(2) + "$). O agregado, porém, junta portas\n"
         "muito diferentes, e estimar o mesmo modelo para cada grande grupo da CBO muda o\n"
         "quadro. @@FRASE_CBO_MN@@ Se a análise parasse no agregado, concluiria que a\n"
         "interseccionalidade não se confirma na entrada; separada a ocupação, ela se confirma.\n\n"
         "\\paragraph{No topo, a ordem se inverte e ela passa a ser a mais excluída.}\n"
         "No decil superior de renda o quadro vira: a mulher negra tem OR~$=" + m.group(3) + "$,\n"
         "abaixo da mulher branca ($" + m.group(4) + "$) e do homem negro\n"
         "($" + m.group(5) + "$). Em linguagem de leitor: as chances (\\emph{odds}) de uma\n"
         "mulher negra chegar aos 10\\% mais ricos equivalem a "
         + f"{float(m.group(3).replace(',', '.')) * 100:.0f}" + "\\% das de um homem branco com a\n"
         "mesma escolaridade, idade, jornada, estado e bairro. A vantagem de gênero na\n"
         "entrada, que já vinha das ocupações feminizadas, desaparece exatamente onde a ascensão\n"
         "se decide, e o que sobra é o acúmulo das duas barreiras, um pouco abaixo da soma.\\footnote{A interação \\texttt{negro$\\times$sexo\\_fem} é\n"
         "\\emph{sub-aditiva} em todos os desfechos (OR~$=" + m.group(6) + "$ no acesso;\n"
         "$=" + m.group(7) + "$ no top~10\\%): a penalidade racial é um pouco menor entre\n"
         "mulheres do que entre homens, o que atenua a soma sem desfazê-la.}\n\n"
         "Em uma frase: a mulher negra entra pelas ocupações feminizadas, mas não chega ao\n"
         "comando nem ao topo."),
     S),


    ("N5 discussão: convergência lenta --- e tênue demais para se afirmar",
     r"\\paragraph\{Lenta convergência racial\.\}\s+"
     r"A redução de apenas ([\d.,]+)\\%\s+"   # ponto decimal: a vírgula só é normalizada depois dos patches
     r"do gap em dez anos --- equivalente a ([\d,]+) ponto de log-rendimento por ano\s+"
     r"\(\$\\delta = ([\d\{\},]+)\$, \$p = ([\d\{\},]+)\$, WLS 2016--2025\)\s+"
     r"--- sugere que, ao ritmo atual, a convergência racial levaria mais de um\s+"
     r"século para eliminar o diferencial observado em 2016\.\s+"
     r"Essa constatação não trivializa avanços recentes em políticas de cotas\s+"
     r"e acesso ao ensino superior, mas evidencia que reformas no campo da\s+"
     r"educação, sem intervenção simultânea nos mecanismos de segregação\s+"
     r"residencial e de acesso às redes profissionais, são insuficientes\.",
     # O texto e as CONCLUSÕES vêm da série anual do M3 (params_nucleo: TEND_*), não dos
     # números capturados do texto-base: "mais de um século" e "não se distingue de zero"
     # dependem do resultado e eram frases fixas.
     lambda m: _paragrafo_convergencia(),
     S),

    ("N5 discussão: ressalva de comparabilidade do Gini desce para nota",
     r"Cabe uma ressalva metodológica: o Gini estimado neste trabalho refere-se ao\s+"
     r"\\textbf\{rendimento do trabalho entre ocupados\} \(em torno de ([\d\{\},]+)\), conceito\s+"
     r"distinto do Gini domiciliar \\emph\{per capita\} de todas as fontes do IBGE ---\s+"
     r"níveis próximos, mas medidas diferentes que podem divergir em tendência, pois a\s+"
     r"alta de 2025 é puxada por renda \\emph\{não\}-trabalho do topo, que não transita\s+"
     r"pelo rendimento dos ocupados\. Nesse mesmo conceito, a desigualdade",
     lambda m: (
         "As duas medidas não são a mesma coisa, e a diferença importa para não se ler "
         "tendência onde há mudança de conceito.\\footnote{O Gini estimado neste trabalho "
         "refere-se ao rendimento do trabalho entre ocupados (em torno de " + m.group(1) +
         "), ao passo que o do IBGE é domiciliar \\emph{per capita} e de todas as fontes. "
         "Os níveis são próximos, mas as medidas podem divergir em tendência: a alta de 2025 "
         "é puxada por renda não-trabalho do topo, que não transita pelo rendimento dos "
         "ocupados.} No conceito adotado aqui, a desigualdade"),
     S),


    ("N3.3 Oaxaca--Blinder: composição ou preço, a pergunta antes do método",
     flex(r"A decomposição de Oaxaca--Blinder separa o gap bruto de log-rendimento"),
     r"""De que é feito o gap? Duas explicações rivalizam desde \citeonline{becker1957}, e
elas pedem políticas opostas. Ou negros e brancos chegam ao mercado com características
diferentes e o mercado paga igual por características iguais --- o gap é
\emph{composição}, e a política tem de agir antes do mercado, na escola e na formação.
Ou chegam com as mesmas características e o mercado paga diferente --- o gap é
\emph{preço}, e a política tem de agir dentro dele, na contratação e na fiscalização.
A distinção é empírica, e a decomposição de Oaxaca--Blinder foi construída para fazê-la.

A decomposição de Oaxaca--Blinder separa o gap bruto de log-rendimento""", 0),

    ("N3.4 quantílica: teto de vidro ou piso pegajoso, a pergunta antes do método",
     flex(r"A regressão quantílica estima o gap em cada ponto da distribuição de renda; a"),
     r"""A penalidade racial é a mesma em toda a distribuição de renda? Nada obriga que seja,
e as duas possibilidades apontam para lugares diferentes. Se ela crescer rumo ao topo, o
problema é um teto de vidro: quanto mais alto se sobe, mais a cor pesa, e o alvo da
política são as posições de comando. Se for maior na base, o problema é um piso
pegajoso, e concentrar esforços nas elites profissionais erra o alvo por inteiro. Os
resultados a seguir mostram que as duas leituras estão corretas --- porque respondem a
perguntas diferentes, e a subseção termina explicando por que não se contradizem.

A regressão quantílica estima o gap em cada ponto da distribuição de renda; a""", 0),


    ("N5 discussão: índices da POF descem para nota",
     r"A melhora\s+multidimensional captada pela POF não eliminou o gap racial de qualidade de vida\s+"
     r"\(([\d\{\},]+) para chefes pretos/pardos \\emph\{vs\.\}~([\d\{\},]+) para brancos\), e a renda\s+"
     r"voltou a concentrar-se no topo em 2025 \(Gini do rendimento domiciliar\s+"
     r"\\emph\{per capita\} de ([\d\{\},]+)\)~\\cite\{ibge_pof_2019, ibge_rendimentos_2025\}\.",
     lambda m: (
         "A melhora multidimensional captada pela POF não eliminou o gap racial de "
         "qualidade de vida, e a renda voltou a concentrar-se no topo em 2025.\\footnote{"
         "Índice de Perda de Qualidade de Vida (IPQV; quanto maior, pior) de " + m.group(1)
         + " para chefes pretos ou pardos, contra " + m.group(2) + " para brancos; Gini do rendimento domiciliar "
         "\\emph{per capita} de " + m.group(3) + " em 2025 "
         "\\cite{ibge_pof_2019, ibge_rendimentos_2025}.}"),
     S),


]


def aplicar(texto: str, verbose: bool = True) -> str:
    """Aplica todos os PATCHES em ordem; avisa os que não casaram."""
    falhas = []
    for pid, pat, rep, flags in PATCHES:
        # lambda: substituto literal (o re nao interpreta escapes do LaTeX no substituto)
        # substituto invocável: reaproveita trechos capturados sem redigitá-los
        sub = rep if callable(rep) else (lambda m, r=rep: r)
        texto, n = re.subn(pat, sub, texto, count=1, flags=flags)
        if n != 1:
            falhas.append(pid)
    # cabeçalhos "BARREIRA": régua + título + subtítulo no mesmo parágrafo estouravam a largura
    _hdr = re.compile(r"(\\noindent\\rule\{\\textwidth\}\{1pt\})\n(\\textbf\{\\large BARREIRA[^\n]*\})\n(\\textit\{[^\n]*\})\n(\\noindent\\rule)")
    texto = _hdr.sub(lambda m: m.group(1) + "\\par\n" + m.group(2) + "\\par\n" + m.group(3) + "\\par\n" + m.group(4), texto)
    # 1.6 — separador decimal: percentuais na prosa com vírgula (ABNT), ex.: 19.1\% → 19,1\%
    texto, n_pct = re.subn(r"(\d)\.(\d+)\\%", r"\1,\2\\%", texto)
    if verbose:
        print(f"  patches aplicados: {len(PATCHES) - len(falhas)}/{len(PATCHES)}"
              f"; percentuais normalizados: {n_pct}")
        for f in falhas:
            print(f"  [AVISO] patch não casou: {f}")
    return texto
