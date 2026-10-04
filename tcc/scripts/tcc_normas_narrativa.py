# -*- coding: utf-8 -*-
"""
tcc_normas_narrativa.py
=======================
O fio narrativo da versão normativa (04/10/2026, pedido do autor): o conceito de racismo
estrutural, o roteiro que segue a trajetória de um trabalhador, as pontes entre as
subseções de Resultados, as críticas às políticas de diversidade com as propostas
(Discussão) e a Conclusão em dois parágrafos.

Regras do template oficial (Implementação de Algoritmo(s) de Machine Learning):
  · Considerações Iniciais: contexto, objetivos, finalidade dos algoritmos; no máximo
    duas páginas;
  · Conclusão: frases curtas, conclusões e implicações práticas para a tomada de decisão,
    NENHUMA citação ou resultado de outros estudos, sem tabelas ou figuras, no máximo
    dois parágrafos — por isso as críticas e as propostas, que citam leis, ficam na
    Discussão, e a Conclusão só as resume;
  · Resultados e Discussão: resultados e discussão dos outputs.

Todo número vem de params_nucleo, e toda afirmação que depende de um resultado é
condicional a ele (nada afirmado de antemão).
"""
from __future__ import annotations

from params_nucleo import P, pt
from params_nucleo import pct as _pct_bruto


def pct(x: float, d: int = 1) -> str:
    return _pct_bruto(x, d).replace("%", "\\%")


def _menos(odds: float) -> str:
    """Odds ratio < 1 em "x% menores" (sem o sinal)."""
    return pt((1 - odds) * 100, 0)


# ── condições (cada frase só é afirmada se o número a sustentar) ─────────────
_H1 = P["MED_BAIRRO"] > 0
_H2 = P["QR_GAP_Q90"] > P["QR_GAP_Q10"]
_H3 = P["CI_ocp_qualif_M2"][1] < 1
_DIPLOMA = (P.get("NE_GAP_POS") is not None and P.get("PCTPOS_ocp_qualif") is not None
            and P["NE_GAP_POS"] < 3 and P["PCTPOS_ocp_qualif"] >= 10)
_CBO = "CBO_MN_dirigente" in P
_MN_MENOR_DIR = _CBO and P["CBO_MN_dirigente"] < min(P["CBO_MB_dirigente"], P["CBO_HN_dirigente"], 1)
_TOPO_PIOR = P["OR_y_top10_M2"] < P["OR_ocp_qualif_M2"]


# ══ Considerações Iniciais ════════════════════════════════════════════════════
INTRODUCAO = (r"""
\section{Considerações Iniciais}

""" + f"""O Brasil é um dos países com maior desigualdade racial de renda no mundo, e a
razão entre o rendimento médio de trabalhadores brancos e negros permanece acima
de 1{{:}}1,5 em toda a série histórica disponível, mesmo quando se controlam
escolaridade, experiência e setor de atividade \\cite{{ibge_pnad_2023}}. A
explicação usual atribui esse hiato a diferenças de qualificação; se ela fosse
suficiente, a expansão do acesso ao ensino teria dissolvido o diferencial ao
longo das últimas décadas, o que não ocorreu \\cite{{hasenbalg1979}}.

A teoria econômica oferece duas explicações para um diferencial que sobrevive ao
controle da produtividade observável. \\citeonline{{becker1957}} propôs a
discriminação por preferência, que a concorrência tenderia a erodir;
\\citeonline{{arrow1973}}, a discriminação estatística, em que a raça serve de sinal
da produtividade média do grupo e o equilíbrio se autoconfirma. Nenhuma das duas
explica por que o diferencial atravessa décadas de mudança na concorrência e na
informação. É essa persistência que o conceito de racismo estrutural nomeia.

\\citeonline{{almeida2019}} distingue três concepções de racismo. Na individualista,
ele é desvio moral de pessoas; na institucional, está nas regras e práticas das
organizações, que conferem vantagens a um grupo mesmo sem intenção explícita; na
estrutural, as instituições reproduzem o racismo porque ele faz parte do modo
normal de funcionamento das relações econômicas, políticas e jurídicas, sem
depender da intenção de ninguém. \\citeonline{{hasenbalg1979}} deu a essa ideia forma
empírica: um ciclo de desvantagens cumulativas, em que cada etapa da trajetória ---
origem, escola, inserção, promoção --- herda a desigualdade da anterior e a acrescenta.
Racismo estrutural, assim, não é uma variável a inserir num modelo, mas um padrão, e
este trabalho o leu por três marcas mensuráveis: a persistência da desvantagem depois
de igualadas as características individuais; a sua mediação por estruturas --- o
bairro de moradia e a porta das ocupações; e a sua acumulação onde se decide a
ascensão. Os métodos medem as marcas, não as intenções; por isso o texto fala em
penalidade condicional, e não em discriminação provada.

A literatura empírica identifica três canais dessa reprodução: a discriminação
direta em seleção e promoção \\cite{{pager2007}}; os efeitos de vizinhança, pelos quais
a concentração de pobreza em bairros segregados reduz as redes de contato com o
mercado formal \\cite{{wilson1987, sampson1997, marques2010}}; e a subvalorização do
capital humano negro \\cite{{henriques2001, soares2009}}. Tratados isoladamente, esses
canais têm sido difíceis de quantificar de forma integrada e em escala nacional.

Três hipóteses orientaram a investigação: que parte relevante do diferencial é
mediada pelo bairro de moradia (H1); que a penalidade se agrava no topo da
distribuição, configurando teto de vidro (H2); e que a barreira opera antes do
salário, no acesso às ocupações qualificadas (H3).

O objetivo deste trabalho foi identificar, isolar e quantificar os mecanismos da
desigualdade racial de rendimentos e de acesso ocupacional no Brasil e traduzir o
diagnóstico em implicações de política. A análise seguiu a trajetória de um
trabalhador: onde mora (modelo linear hierárquico, que separa a variação entre
bairros), de que é feito o diferencial de renda (decomposição de Oaxaca--Blinder), que
porta encontra (modelo logístico multinível de acesso a ocupações qualificadas), até
onde sobe (regressão quantílica e decomposição por função de influência recentrada) e
quem está na interseção de raça e gênero. Um modelo de aprendizado supervisionado
(\\emph{{gradient boosting}}, interpretado por valores SHAP) serviu de verificação sem
forma funcional imposta.

\\newpage
""")


# ══ Resultados: abertura e pontes ═════════════════════════════════════════════
ABERTURA_RESULTADOS = (
    "Os resultados seguem a trajetória anunciada nas Considerações Iniciais: o bairro, a "
    "composição do diferencial, a porta das ocupações, a escada da distribuição de renda e "
    "a interseção de raça e gênero. Cada etapa responde a uma pergunta e deixa a seguinte; "
    "a Discussão, ao final, reúne as respostas e as confronta com as políticas vigentes.\n")

# uma frase no início de cada subseção, ligando a resposta anterior à próxima pergunta
PONTES = {
    "Modelos Hierárquicos Lineares":
        "A trajetória começa onde a pessoa mora.",
    "Decomposição de Oaxaca--Blinder: composição":
        "Comparar vizinhos explicou parte do diferencial; resta saber de que é feito o que sobra.",
    "GLMM logístico: o teto de vidro no acesso":
        ("A decomposição mostrou que parte do diferencial opera na entrada das ocupações; "
         "o modelo de acesso mede essa porta diretamente."),
    "Regressão Quantílica e RIF-OB":
        ("Passada a porta, resta a escada: a penalidade é a mesma para quem ganha pouco e "
         "para quem ganha muito?"),
    "Interseccionalidade: raça e gênero":
        ("Até aqui, raça foi tratada como um eixo só; a última etapa pergunta quem está "
         "na interseção."),
    "Modelos de Machine Learning e SHAP Values":
        "Resta verificar se o padrão depende da forma funcional imposta pelos modelos.",
    "Multicolinearidade do Modelo M4":
        "Antes da Discussão, uma checagem técnica do modelo com mais controles, o M4.",
}


# ══ Discussão: críticas às políticas e propostas ══════════════════════════════
def _criticas() -> str:
    c = []
    # C1 — ingresso x subida
    if _TOPO_PIOR or _MN_MENOR_DIR:
        c.append(
            "\\textbf{As políticas cuidam do ingresso, não da subida.} A reserva de vagas no "
            "ensino superior federal \\cite{brasil2012lei12711, brasil2023lei14723} e nos concursos "
            "federais \\cite{brasil2025lei15142} atua na entrada. A desvantagem medida aqui, "
            "porém, cresce onde se decide a ascensão: as chances de alcançar o décimo mais rico "
            f"foram {_menos(P['OR_y_top10_M2'])}\\% menores"
            + (f", e, entre os dirigentes, a mulher negra teve a menor chance de todos os "
               f"grupos (OR~$={pt(P['CBO_MN_dirigente'], 2)}$)" if _MN_MENOR_DIR else "")
            + ". O único instrumento federal voltado ao comando, a reserva de cargos "
            "em comissão e funções de confiança \\cite{brasil2023decreto11443}, vale apenas "
            "para a administração pública federal, e o setor privado, que concentra a maior "
            "parte do emprego, não tem obrigação equivalente."
            + (" O recorte por setor precisa o diagnóstico: entre pessoas comparáveis, o setor "
               "público não abre mais a porta do cargo qualificado "
               f"(OR~${pt(P['HET_OR_SETOR1_OCP'], 3)}$, contra ${pt(P['HET_OR_SETOR0_OCP'], 3)}$ no "
               "privado), mas tem teto bem mais baixo --- no décimo mais rico, "
               f"${pt(P['HET_OR_SETOR1_T10'], 3)}$ contra ${pt(P['HET_OR_SETOR0_T10'], 3)}$ --- e "
               f"penalidade salarial menor ({pct(P['HET_HLM_SETOR1'])} contra "
               f"{pct(P['HET_HLM_SETOR0'])}). É no setor privado, sem obrigação, que a subida mais "
               "se fecha." if "HET_OR_SETOR1_OCP" in P and P["HET_OR_SETOR0_T10"] < P["HET_OR_SETOR1_T10"]
               else ""))
    # C2 — aposta educacional
    if _DIPLOMA:
        c.append(
            "\\textbf{A aposta educacional é necessária, mas insuficiente.} A escolaridade se "
            "associou a quase toda a convergência salarial --- a penalidade caiu de "
            f"{pct(P['NE_GAP_SEMFUND'])} sem fundamental completo para {pct(P['NE_GAP_POS'])} "
            "na pós-graduação ---, mas não à de acesso: com pós-graduação, as chances de chegar "
            f"a um cargo qualificado seguiram {pct(P['PCTPOS_ocp_qualif'], 0)} menores. "
            "Programas de acesso ao ensino atacam a barreira que mais cede ao diploma.")
    # C3 — território
    if _H1:
        c.append(
            "\\textbf{Não há território na política de diversidade.} A diversidade é medida "
            f"dentro da empresa, mas {pct(P['MED_BAIRRO'])} do diferencial agregado passou pelo "
            "bairro de moradia, e nenhum instrumento federal de diversidade usa o local de "
            "moradia como critério.")
    # C4 — um eixo de cada vez
    if _CBO:
        c.append(
            "\\textbf{Um eixo de cada vez deixa a mulher negra de fora.} Ela entrou mais do que "
            "o homem branco nas ocupações feminizadas --- apoio administrativo "
            f"(OR~$={pt(P['CBO_MN_administrativo'], 2)}$), ensino e saúde ---, mas menos do que "
            f"a mulher branca (OR~$={pt(P['CBO_MB_administrativo'], 2)}$ no apoio "
            "administrativo); metas separadas para mulheres e para negros podem ser cumpridas "
            "pela mulher branca e pelo homem negro sem alcançá-la. A lei de transparência "
            "salarial \\cite{brasil2023lei14611} coleta raça no relatório das empresas com 100 "
            "ou mais empregados, mas a obrigação de igualdade que estabelece é entre mulheres "
            "e homens.")
    return "\n\n".join(c)


def _propostas() -> str:
    return (
        "As propostas a seguir são sugeridas pelos resultados, não avaliadas por eles. "
        "\\textbf{(i) Metas de representação em cargos de direção e gerência no setor "
        "privado, com recorte interseccional}, apoiadas no relatório que a lei de "
        "transparência salarial já exige. \\textbf{(ii) Igualdade salarial por raça como "
        "obrigação, e não só como dado}, com fiscalização dirigida à diferença que persiste "
        f"dentro da mesma ocupação ({pct(P['GAP_M4'])}), base que a proibição de práticas "
        "discriminatórias e o Estatuto da Igualdade Racial já oferecem "
        "\\cite{brasil1995lei9029, brasil2010lei12288}. \\textbf{(iii) Um componente "
        "territorial}, já que o bairro carrega parte do diferencial: transporte e intermediação "
        "de emprego que liguem os bairros segregados aos polos de emprego qualificado; "
        "aprendizagem, estágio e mentoria que levem redes de contato a quem não as tem --- a "
        "entrada na carreira é o momento de maior retorno, pois a penalidade é mínima entre os "
        "mais jovens ---; currículo sem endereço nas primeiras etapas de seleção, para que o "
        "CEP não funcione como sinal de raça; escola de tempo integral e ensino técnico nos "
        "bairros de maior proporção de população negra; habitação de interesse social em áreas "
        "centrais, e não em novos conjuntos periféricos; e, como a penalidade é maior nos "
        "bairros de renda mais alta, fiscalização também ali, e não só na periferia. As "
        "estimativas por bairro do modelo hierárquico servem para escolher onde começar e para "
        "medir se a penalidade mudou. \\textbf{(iv) Promoção, e não só "
        "ingresso}: estender a lógica da reserva de cargos de confiança às empresas estatais "
        "e à progressão nas carreiras. \\textbf{(v) Monitoramento anual} destes indicadores "
        "--- o diferencial líquido, a chance de acesso e a chance de comando por raça e "
        "gênero ---, reproduzíveis com a PNAD Contínua, para verificar se uma intervenção "
        "moveu a barreira que importa.")


DISCUSSAO_POLITICAS = (
    "\n\\paragraph{O que os resultados dizem sobre a política de diversidade vigente.}\n"
    + _criticas() + "\n\n"
    "\\paragraph{Propostas para reduzir o racismo estrutural no mercado de trabalho.}\n"
    + _propostas() + "\n")


# ══ Conclusão — dois parágrafos, frases curtas, sem citações ═════════════════
def _paragrafo_conclusoes() -> str:
    f = ["A desigualdade racial no mercado de trabalho brasileiro apresentou as marcas "
         "do racismo estrutural."]
    f.append(f"Persistiu: com a mesma escolaridade, idade, sexo e bairro, trabalhadores negros "
             f"ganharam {pct(P['GAP_M3'])} a menos, e {pct(P['GAP_M4'])} dentro da mesma ocupação.")
    if _H1 and _H3:
        f.append(f"Passou por estruturas: o bairro mediou {pct(P['MED_BAIRRO'])} do diferencial "
                 f"agregado, e as chances de chegar a um cargo qualificado foram "
                 f"{_menos(P['OR_ocp_qualif_M2'])}\\% menores.")
    if _H2:
        f.append(f"Acumulou-se rumo ao topo: a penalidade condicional subiu de "
                 f"{pct(P['QR_GAP_Q10'])} na base para {pct(P['QR_GAP_Q90'])} no nono decil.")
    if _CBO and _MN_MENOR_DIR:
        f.append("A mulher negra entrou pelas ocupações feminizadas, mas foi o grupo com menor "
                 "chance de chegar ao comando.")
    if _DIPLOMA:
        f.append(f"O diploma quase igualou o salário ({pct(P['NE_GAP_POS'])} na pós-graduação), "
                 f"mas não a porta: as chances de acesso seguiram {pct(P['PCTPOS_ocp_qualif'], 0)} "
                 "menores.")
    hs = [h for h, ok in (("H1", _H1), ("H2", _H2), ("H3", _H3)) if ok]
    if len(hs) == 3:
        f.append("As três hipóteses encontraram respaldo.")
    elif hs:
        f.append("Encontraram respaldo " + ", ".join(hs) + ".")
    return " ".join(f)


def _paragrafo_implicacoes() -> str:
    f = ["Esses resultados indicam limites da política de diversidade vigente."]
    if _TOPO_PIOR:
        f.append("As cotas atuam no ingresso, mas a desvantagem cresce onde se decide a ascensão.")
    if _DIPLOMA:
        f.append("A educação reduz a penalidade salarial, mas não abre a porta.")
    if _H1:
        f.append("O território não entra nos critérios, embora carregue parte do diferencial.")
    if _CBO:
        f.append("Metas separadas por raça e por gênero não alcançam a mulher negra no comando.")
    f.append("As prioridades sugeridas são metas de representação em cargos de direção com "
             "recorte interseccional, igualdade salarial por raça como obrigação fiscalizada, "
             "ação territorial nos bairros de maior proporção de população negra e "
             "monitoramento anual destes indicadores.")
    f.append("Os resultados são associações condicionais, não efeitos causais, e as propostas "
             "são agenda, não efeito estimado.")
    return " ".join(f)


CONCLUSAO = (r"""
\section{Conclusão}

""" + _paragrafo_conclusoes() + "\n\n" + _paragrafo_implicacoes() + "\n")


# ══ Heterogeneidade (E8, 04/10/2026): o que o agregado esconde ═════════════════
def _o(k):
    return pt(P[k], 3)


def _heterogeneidade() -> str:
    if "HET_HLM_PRETO" not in P:
        return ""
    par = []
    # cor: só se a penalidade dos pretos for maior que a dos pardos no salário e no acesso
    preto_pior = (P["HET_HLM_PRETO"] > P["HET_HLM_PARDO"]
                  and P["HET_OR_PRETO_OCP"] < P["HET_OR_PARDO_OCP"])
    if preto_pior:
        s = ("Pretos e pardos estão abaixo dos brancos em todos os recortes, o que sustenta a "
             "categoria negro como referência de política; mas a penalidade dos pretos é maior em "
             f"todos eles: {pct(P['HET_HLM_PRETO'])} contra {pct(P['HET_HLM_PARDO'])} no salário, "
             f"OR~$={_o('HET_OR_PRETO_OCP')}$ contra ${_o('HET_OR_PARDO_OCP')}$ no acesso e "
             f"${_o('HET_OR_PRETO_T10')}$ contra ${_o('HET_OR_PARDO_T10')}$ no décimo mais rico "
             "(Tabela~\\ref{tab:heterogeneidade}).")
        if P["HET_QR_PRETO_Q95"] - P["HET_QR_PARDO_Q95"] > P["HET_QR_PRETO_Q10"] - P["HET_QR_PARDO_Q10"]:
            s += (" A distância entre os dois grupos cresce rumo ao topo: na regressão quantílica, "
                  f"vai de {pct(P['HET_QR_PRETO_Q10'])} e {pct(P['HET_QR_PARDO_Q10'])} na base a "
                  f"{pct(P['HET_QR_PRETO_Q95'])} e {pct(P['HET_QR_PARDO_Q95'])} no q95.")
        if (P["HET_RIF_PARDO_Q10"] > P["HET_RIF_PARDO_Q90"]
                and P["HET_RIF_PRETO_Q90"] > P["HET_RIF_PARDO_Q90"]):
            s += (" O preço também se distribui de outro modo: nos pardos concentra-se na base "
                  f"({pct(P['HET_RIF_PARDO_Q10'])} do gap RIF no q10, {pct(P['HET_RIF_PARDO_Q90'])} "
                  f"no q90); nos pretos alcança {pct(P['HET_RIF_PRETO_Q50'])} na mediana e "
                  f"permanece em {pct(P['HET_RIF_PRETO_Q90'])} no topo. O padrão é compatível com "
                  "colorismo --- um preço maior para a pele mais escura onde a seleção é mais "
                  "visível ---, sem que estes dados o identifiquem como causa.")
        par.append(s)
    # setor: a porta é igual, o teto não
    if abs(P["HET_OR_SETOR0_OCP"] - P["HET_OR_SETOR1_OCP"]) < 0.03 and P["HET_OR_SETOR0_T10"] < P["HET_OR_SETOR1_T10"]:
        par.append(
            "Entre pessoas comparáveis, a entrada em cargo qualificado é igualmente desigual no "
            f"setor privado (OR~$={_o('HET_OR_SETOR0_OCP')}$) e no público "
            f"(${_o('HET_OR_SETOR1_OCP')}$); a diferença entre os setores está na subida. No "
            f"privado, a penalidade salarial é de {pct(P['HET_HLM_SETOR0'])} e a chance de chegar "
            f"ao décimo mais rico tem OR~$={_o('HET_OR_SETOR0_T10')}$; no público, "
            f"{pct(P['HET_HLM_SETOR1'])} e ${_o('HET_OR_SETOR1_T10')}$. O teto de vidro não é efeito "
            "da geografia: com o topo definido dentro de cada estado, o OR é "
            f"${_o('HET_OR_T10UF')}$, como no corte nacional (${_o('OR_y_top10_M2')}$).")
    # idade
    if P["HET_IDADE_65MAIS"] > P["HET_IDADE_14_29"]:
        par.append(
            f"A penalidade cresce com a idade: {pct(P['HET_IDADE_14_29'])} entre 14 e 29 anos, "
            f"{pct(P['HET_IDADE_50_64'])} entre 50 e 64 e {pct(P['HET_IDADE_65MAIS'])} a partir dos 65. "
            "Dados transversais não separam as duas leituras possíveis --- coorte (gerações que "
            "chegaram ao mercado depois das cotas) ou ciclo de vida (a desigualdade se acumula ao "
            "longo da carreira) ---, e ambas são compatíveis com o teto de vidro.")
    return ("\n\subsection*{O que o agregado esconde: cor, setor e idade}\n"
            "Os resultados até aqui tratam negros como um grupo e o mercado como um todo. "
            "Estimados os mesmos modelos por recorte, três diferenças aparecem.\n\n"
            "\input{outputs/tables/heterogeneidade_tcc.tex}\n\n" + "\n\n".join(par) + "\n")


HETEROGENEIDADE = _heterogeneidade()

# robustez ao desenho amostral: completa o parágrafo "Pesos amostrais" da Inferência
_PESO_ANCORA = "diferença sem relevância econômica; os demais resultados são não ponderados."
PESO_COMPLEMENTO = (
    "diferença sem relevância econômica. O mesmo vale para o acesso e para a decomposição: com o "
    f"peso V1028 e erro agrupado por UPA, o OR do acesso vai de ${_o('PESO_OR_OCP_S')}$ a "
    f"${_o('PESO_OR_OCP_P')}$, o do décimo mais rico de ${_o('PESO_OR_T10_S')}$ a "
    f"${_o('PESO_OR_T10_P')}$, e a parcela de preço da Oaxaca--Blinder (A) de "
    f"{pct(P['PESO_OB_A_S'])} a {pct(P['PESO_OB_A_P'])}. O modelo multinível ponderado (WeMix) "
    "mostrou-se computacionalmente inviável com 41 mil UPAs e fica como agenda; os demais "
    "resultados são não ponderados.") if "PESO_OR_OCP_P" in P else _PESO_ANCORA
