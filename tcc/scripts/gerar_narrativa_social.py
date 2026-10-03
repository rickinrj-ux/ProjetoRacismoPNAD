#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gerar_narrativa_social.py — versão em linguagem corrente do TCC.

Público: estudante de ciências sociais e tomador de decisão. Gente que precisa
entender o problema e decidir o que fazer, e que não tem por que saber o que é
intervalo de confiança, razão de chances ou intercepto aleatório.

Regras que este documento segue, e que não devem ser afrouxadas depois:
  * nenhum nome de método, nenhuma sigla de modelo, nenhuma equação;
  * nenhuma seção numerada --- os títulos afirmam, não catalogam;
  * percentuais sim: um leitor de ciências sociais lê porcentagem sem esforço.
    O que cansa é a notação, não o número;
  * todo número sai de tcc/scripts/params_nucleo.py, que lê os csv de
    outputs/tables/. Nada é digitado à mão aqui.

Uso: python tcc/scripts/gerar_narrativa_social.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Cm, Pt, RGBColor

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from params_nucleo import P, pt  # noqa: E402

SAIDA = RAIZ / "entregaveis" / "TCC_Ricardo_Calheiros_Versao_Narrativa.docx"

FONTE = "Arial"
TINTA = RGBColor(0x1A, 0x1A, 0x1A)
REALCE = RGBColor(0x8C, 0x2F, 0x39)      # vinho discreto, só em número de manchete


# ── números, já em português e arredondados para leitura ──────────────────────

def pc(x: float, casas: int = 1) -> str:
    """Percentual com vírgula decimal e sem zero à direita desnecessário."""
    s = f"{abs(x):.{casas}f}".replace(".", ",")
    return s.rstrip("0").rstrip(",") if "," in s else s


def menos_chance(odds: float) -> str:
    """Razão de chances vira 'X% menos chance', que é como se fala."""
    return pc((1 - odds) * 100, 0)


N = {
    "gap": pc(P["GAP_POOL"]),                 # 19,1
    "gap_vizinho": pc(P["GAP_M1"]),           # 10,6
    "fatia_endereco": pc(P["MED_ACUM_M1"]),   # 47,0
    "gap_liquido": pc(P["GAP_M3"]),           # 10,2
    "gap_ocupacao": pc(P["GAP_M4"]),          # 7,0
    "fatia_total": pc(P["MED_ACUM_M4"]),      # 65,9
    "entre_bairros": pc(P["ICC_M0"] * 100),   # 36,9
    "porta_cargo": menos_chance(P["OR_ocp_qualif_M2"]),   # 30
    "porta_topo": menos_chance(P["OR_y_top10_M2"]),       # 35
    "pp_cargo": pc(abs(P["AME_ocp_qualif_M2"])),          # 5,5
    "mn_entrada": pc((P["GRG_MN_OCP_QUALIF"] - 1) * 100, 0),   # 33
    "mn_topo": menos_chance(P["GRG_MN_TOP10"]),                # 66
    "hn_entrada": menos_chance(P["GRG_HN_OCP_QUALIF"]),        # 35
    "preco_base": pc(P["RIF_RET_Q10"]),       # 35,1
    "preco_topo": pc(P["RIF_RET_Q90"]),       # 12,9
    "pessoas": f"{P['N_HLM']:,}".replace(",", "."),
    "bairros": f"{P['N_UPAS']:,}".replace(",", "."),
    # teto de vidro por tipo de área: no interior a penalidade quase dobra
    # da mediana ao topo; na capital ela já começa alta e estabiliza
    "interior_meio": pc(P["QR_AREA_INTERIOR_Q50"]),   # 7,9
    "interior_topo": pc(P["QR_AREA_INTERIOR_Q95"]),   # 14,6
    "capital_meio": pc(P["QR_AREA_CAPITAL_Q50"]),     # 9,7
    "capital_topo": pc(P["QR_AREA_CAPITAL_Q95"]),     # 10,1
    # contraprova independente do resíduo, sem impor forma à relação
    "contraprova": pc(P["ML_CONTRASTE_PCT"]),         # 6,2
}


# ── tipografia ────────────────────────────────────────────────────────────────

def estilo_base(doc: Document) -> None:
    for sec in doc.sections:
        sec.top_margin = sec.bottom_margin = Cm(2.5)
        sec.left_margin = sec.right_margin = Cm(2.5)
    n = doc.styles["Normal"]
    n.font.name, n.font.size, n.font.color.rgb = FONTE, Pt(11), TINTA
    pf = n.paragraph_format
    pf.line_spacing, pf.space_after = 1.4, Pt(10)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def titulo(doc: Document, texto: str, tamanho: int = 15, antes: int = 22) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(antes)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(texto)
    r.font.name, r.font.size, r.bold, r.font.color.rgb = FONTE, Pt(tamanho), True, TINTA


def paragrafo(doc: Document, texto: str, realce: list[str] | None = None) -> None:
    """Escreve o parágrafo; o que estiver em `realce` sai em negrito colorido.

    O realce entra só no número que o leitor deve levar embora --- se tudo é
    destaque, nada é.
    """
    p = doc.add_paragraph()
    resto = texto
    for alvo in (realce or []):
        antes, _, resto = resto.partition(alvo)
        p.add_run(antes)
        r = p.add_run(alvo)
        r.bold, r.font.color.rgb = True, REALCE
    p.add_run(resto)


def respiro(doc: Document, texto: str) -> None:
    """Frase isolada, recuada: o que o leitor deve guardar se esquecer o resto."""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = pf.right_indent = Cm(1.2)
    pf.space_before = pf.space_after = Pt(14)
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(texto)
    r.italic, r.font.size, r.font.color.rgb = True, Pt(12), REALCE


# ── o documento ───────────────────────────────────────────────────────────────

def capa(doc: Document) -> None:
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run("Onde mora a desigualdade")
    r.font.name, r.font.size, r.bold, r.font.color.rgb = FONTE, Pt(30), True, TINTA

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(30)
    r = p.add_run("O que dez anos de dados dizem sobre ser negro\n"
                  "no mercado de trabalho brasileiro")
    r.font.name, r.font.size, r.font.color.rgb = FONTE, Pt(15), TINTA

    paragrafo(doc, "Uma leitura em linguagem corrente, para quem estuda "
                   "sociedade e para quem decide políticas. Sem fórmulas, sem "
                   "siglas e sem pressupor formação em estatística.")
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(26)
    r = p.add_run("Ricardo Calheiros\nMBA em Data Science e Analytics — USP/Esalq")
    r.font.name, r.font.size, r.font.color.rgb = FONTE, Pt(11), TINTA
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def corpo(doc: Document) -> None:
    titulo(doc, "A pergunta", antes=0)
    paragrafo(doc,
              "Imagine dois brasileiros. Mesma idade, mesma escolaridade, mesma "
              "jornada de trabalho, mesmo sexo, mesma região. A única diferença "
              "entre os dois é a cor da pele. Quanto eles ganham de diferença no "
              "fim do mês?")
    paragrafo(doc,
              "Esta é a pergunta que o estudo persegue, e ela foi feita a um "
              f"conjunto de {N['pessoas']} trabalhadores acompanhados pela "
              "pesquisa domiciliar do IBGE ao longo de dez anos, entre 2016 e "
              "2025. Não é uma amostra de conveniência nem um recorte de alguma "
              "cidade: é praticamente toda a população ocupada com rendimento "
              "que a pesquisa alcança no período.")
    paragrafo(doc,
              f"A resposta é que o trabalhador negro ganha {N['gap']}% a menos. "
              "Esse número já desconta escolaridade, idade, sexo, quantidade de "
              "horas trabalhadas e o estado onde a pessoa vive. Não é a diferença "
              "bruta entre negros e brancos, que seria maior; é a diferença que "
              "sobra depois de comparar pessoas parecidas.",
              realce=[f"{N['gap']}%"])
    paragrafo(doc,
              "Poderia terminar aqui, com uma constatação conhecida. O que o "
              "estudo faz de diferente é insistir numa segunda pergunta: onde, "
              "exatamente, essa diferença se produz?")

    titulo(doc, "Quase metade da diferença não separa duas pessoas, separa dois endereços")
    paragrafo(doc,
              "A primeira descoberta é geográfica. Antes de olhar para qualquer "
              "característica das pessoas, dá para perguntar quanto da variação "
              "de renda no Brasil existe entre bairros e quanto existe dentro de "
              "cada bairro. A resposta é desconcertante: "
              f"{N['entre_bairros']}% da diferença de renda entre dois brasileiros "
              "sorteados ao acaso já está dada só por eles morarem em bairros "
              "diferentes.",
              realce=[f"{N['entre_bairros']}%"])
    paragrafo(doc,
              "Mais de um terço, portanto, antes de saber qualquer coisa sobre "
              "quem são essas pessoas. É muito. E abre a possibilidade de que a "
              "desigualdade racial de renda seja, em boa parte, uma desigualdade "
              "de endereço.")
    paragrafo(doc,
              "Para testar isso, o estudo refaz a comparação de um jeito mais "
              "exigente: em vez de comparar um trabalhador negro com um branco "
              "em qualquer lugar do país, compara os dois dentro do mesmo bairro. "
              f"A diferença cai de {N['gap']}% para {N['gap_vizinho']}%.",
              realce=[f"{N['gap_vizinho']}%"])
    paragrafo(doc,
              f"Ou seja: {N['fatia_endereco']}% da desigualdade racial de renda "
              "desaparece quando se compara vizinhos. Não porque ela não exista, "
              "mas porque ela estava operando por outro caminho — negros e brancos "
              "com a mesma escolaridade não conseguem morar nos mesmos lugares, e "
              "os lugares pagam diferente.",
              realce=[f"{N['fatia_endereco']}%"])
    respiro(doc, "Quase metade do problema não está entre duas pessoas. "
                 "Está entre dois endereços.")

    titulo(doc, "O bairro não desconta o salário de quem já trabalha: ele decide quem entra")
    paragrafo(doc,
              "A pergunta seguinte é o que, num bairro, faz a renda ser mais "
              "alta ou mais baixa. E aqui aparece o achado mais duro do estudo: "
              "quanto maior a proporção de moradores negros num bairro, menor o "
              "rendimento de todos os que moram ali — inclusive dos moradores "
              "brancos. O peso disso é da mesma ordem de grandeza da penalidade "
              "que um trabalhador negro carrega individualmente.")
    paragrafo(doc,
              "Não se trata de dizer que vizinhos negros rebaixam salários. O "
              "que o dado mostra é que os territórios onde a população negra se "
              "concentra são, eles próprios, territórios com menos oferta de "
              "trabalho, transporte pior, menos redes de contato e menos "
              "empregadores. O racismo aqui não está numa decisão isolada de "
              "alguém: está na forma como a cidade foi montada.")
    paragrafo(doc,
              "Há um detalhe que importa para quem vai desenhar política. Dentro "
              "de um mesmo bairro, a penalidade racial praticamente não muda "
              "conforme a composição da vizinhança. Quer dizer que o território "
              "não age no contracheque de quem já está empregado: ele age antes, "
              "na porta de entrada — em quem consegue morar onde.")

    titulo(doc, "O que sobra não desaparece com mais controle")
    paragrafo(doc,
              "É razoável desconfiar. Talvez a diferença que sobra seja efeito de "
              "algo ainda não considerado: o estado, a ocupação, o tipo de "
              "vínculo. O estudo testa cada uma dessas hipóteses, e o resultado é "
              "notável pelo que não acontece.")
    paragrafo(doc,
              "Acrescentar o estado não muda praticamente nada: a diferença fica "
              f"em {N['gap_liquido']}%. Esse é o número que o trabalho trata como "
              "resultado principal — o que escolaridade, idade, sexo, jornada, "
              "bairro e estado, juntos, não conseguem explicar.",
              realce=[f"{N['gap_liquido']}%"])
    paragrafo(doc,
              "Acrescentar a ocupação faz a diferença cair para "
              f"{N['gap_ocupacao']}%, e é justamente aqui que mora a armadilha "
              "interpretativa mais comum. É tentador concluir que dois terços do "
              "problema estão explicados. Mas ocupação não é uma característica "
              "que a pessoa traz de casa, como a idade: é um resultado, ao qual "
              "ela precisou conseguir acesso. Controlar por ocupação é descontar "
              "do problema uma parte do próprio problema.",
              realce=[f"{N['gap_ocupacao']}%"])
    paragrafo(doc,
              "Vale registrar uma checagem, porque a desconfiança é legítima: "
              "todo esse cálculo pressupõe uma forma de relação entre renda, "
              "escolaridade e idade. E se a forma estiver errada? O estudo "
              "refez a conta por um caminho de natureza inteiramente "
              "diferente, que não pressupõe forma alguma e deixa os próprios "
              "dados decidirem — e chegou a "
              f"{N['contraprova']}%, a cerca de {pt(P['ML_VS_M4_PP'], 1)} ponto percentual do "
              "resultado principal. A diferença que sobra não é artefato da "
              "maneira de calcular.",
              realce=[f"{N['contraprova']}%"])
    respiro(doc, f"{N['gap_ocupacao']}% é onde a conta termina, não onde a "
                 "desigualdade verdadeira está.")

    titulo(doc, "A barreira principal não está no salário: está na porta")
    paragrafo(doc,
              "Até aqui a pergunta foi quanto alguém ganha a menos. Ela pressupõe "
              "que negros e brancos estejam disputando as mesmas vagas. E se não "
              "estiverem?")
    paragrafo(doc,
              "Comparando pessoas do mesmo bairro, com a mesma escolaridade, "
              "idade, sexo e jornada, um trabalhador negro tem "
              f"{N['porta_cargo']}% menos chance de ocupar um cargo qualificado — "
              "cerca de {pp} pontos percentuais a menos de probabilidade de "
              f"chegar lá. E a porta estreita conforme se sobe: no décimo mais "
              f"rico da população, a chance é {N['porta_topo']}% menor."
              .replace("{pp}", N["pp_cargo"]),
              realce=[f"{N['porta_cargo']}%", f"{N['porta_topo']}%"])
    paragrafo(doc,
              "Essa distinção tem consequência prática imediata. Uma política que "
              "fiscalize salário igual para trabalho igual é necessária, mas não "
              "alcança o problema principal, porque o problema principal acontece "
              "antes de existir contrato. Se o filtro está na seleção, na "
              "promoção e no acesso à vaga, é lá que a política precisa chegar.")
    respiro(doc, "A desigualdade racial no trabalho brasileiro não começa no "
                 "contracheque. Começa na porta.")

    titulo(doc, "O diploma reduz a barreira, mas não a desfaz")
    paragrafo(doc,
              "Duas explicações alternativas costumam aparecer nesse ponto da "
              "conversa, e o estudo testa as duas.")
    paragrafo(doc,
              "A primeira é a informalidade: a diferença seria efeito de negros "
              "estarem mais em vínculos precários. Descontar o tipo de vínculo "
              "praticamente não move o resultado. Não é isso.")
    paragrafo(doc,
              "A segunda é o diploma: bastaria estudar mais. O ensino superior "
              "de fato reduz a barreira de acesso — mas não a elimina. Um "
              "trabalhador negro com curso superior completo continua tendo menos "
              "chance de chegar a um cargo qualificado do que um branco com a "
              "mesma formação. A credencial ajuda; ela não neutraliza.")
    paragrafo(doc,
              "Há uma leitura complementar que reforça o ponto. Quando se olha "
              "para a base da distribuição de renda, a parte da diferença que não "
              "se explica por características observáveis responde por "
              f"{N['preco_base']}% do total; no topo, por {N['preco_topo']}%. "
              "Na base, portanto, a discriminação age sobretudo pelo preço pago "
              "pelo trabalho; no topo, sobretudo pela seleção de quem chega lá. "
              "São dois mecanismos distintos, e uma política que trate apenas de "
              "um deixa o outro intacto.")

    titulo(doc, "Raça e gênero não se somam: eles se reorganizam")
    paragrafo(doc,
              "O estudo separa quatro grupos — homem branco, mulher branca, homem "
              "negro e mulher negra — e encontra uma inversão que nenhuma soma "
              "simples de penalidades preveria.")
    paragrafo(doc,
              "Na entrada em ocupações qualificadas, a mulher negra não é o grupo "
              f"mais barrado: ela tem cerca de {N['mn_entrada']}% mais chance do "
              "que o homem branco de referência, porque boa parte das profissões "
              "credenciadas é feminizada. O grupo mais barrado na entrada é o "
              f"homem negro, com {N['hn_entrada']}% menos chance.",
              realce=[f"{N['mn_entrada']}%"])
    paragrafo(doc,
              "No topo da renda, a ordem se inverte por completo. A mulher negra "
              f"passa a ser o grupo mais excluído de todos: {N['mn_topo']}% menos "
              "chance de chegar ao décimo mais rico do que um homem branco com as "
              "mesmas características. A vantagem que a alçava na entrada some "
              "exatamente onde a ascensão se decide.",
              realce=[f"{N['mn_topo']}%"])
    respiro(doc, "A mulher negra entra na categoria, mas não chega ao topo.")

    titulo(doc, "A penalidade tem geografia")
    paragrafo(doc,
              "Um achado relevante para quem pensa política territorial: "
              "a penalidade racial não é a mesma em todo lugar. Ela varia de "
              "bairro para bairro de forma acentuada — há lugares em que a "
              "diferença é mais que o dobro da média nacional e lugares em que "
              "ela praticamente se inverte.")
    paragrafo(doc,
              "E há um padrão incômodo: a penalidade tende a ser maior justamente "
              "nos bairros de renda mais alta. Riqueza média elevada e "
              "desigualdade racial aguda convivem no mesmo território. O mesmo "
              "aparece entre estados: a unidade da federação com maior renda por "
              "habitante do país é também a de maior penalidade racial.")
    paragrafo(doc,
              "Há ainda uma diferença entre tipos de lugar que muda o desenho "
              "de uma política. Na capital, a desvantagem racial é parecida em "
              "toda a escala de rendimento: quem ganha pouco e quem ganha muito "
              "enfrentam algo próximo — de "
              f"{N['capital_meio']}% no meio a {N['capital_topo']}% no topo. "
              "No interior, o desenho é outro: a desvantagem começa menor, mas "
              "quase dobra conforme se sobe, e chega a "
              f"{N['interior_topo']}% entre os que mais ganham.",
              realce=[f"{N['interior_topo']}%"])
    paragrafo(doc,
              "A leitura prática é direta. Na capital, o problema aparece na "
              "escala inteira, e uma política de base alcança muita gente. No "
              "interior, ele se concentra onde estão os melhores postos: é o "
              "acesso ao topo que está fechado, e é lá que uma política precisa "
              "mirar. Tratar as duas realidades com o mesmo instrumento "
              "desperdiça esforço em uma e erra o alvo na outra.")

    titulo(doc, "O que isso muda para quem decide")
    paragrafo(doc,
              "Três conclusões atravessam o conjunto dos resultados, e nenhuma "
              "delas depende de aceitar um método específico.")
    paragrafo(doc,
              "A primeira é que política de renda não alcança um problema de "
              "endereço. Quase metade da desigualdade racial de rendimento "
              "transita por onde as pessoas conseguem morar. Enquanto moradia, "
              "transporte e oferta de trabalho local não entrarem na conta, uma "
              "parte grande do problema fica fora do alcance da política.")
    paragrafo(doc,
              "A segunda é que política de qualificação, sozinha, tem retorno "
              "decrescente. Formar mais pessoas é necessário e insuficiente: as "
              "mesmas credenciais rendem menos a trabalhadores negros, e a "
              "barreira de acesso continua de pé depois do diploma. Qualificação "
              "precisa vir acompanhada de mecanismos de inserção — de algo que "
              "atue na seleção e na promoção, e não só na formação.")
    paragrafo(doc,
              "A terceira é que o alvo prioritário é o acesso, não o salário. A "
              "diferença de remuneração dentro da mesma ocupação existe e importa, "
              "mas é a menor parte do problema. A maior parte acontece antes: em "
              "quem é chamado para a entrevista, em quem é promovido, em quem "
              "chega às posições de comando.")
    paragrafo(doc,
              "Vale registrar que essas frentes não são invenções do estudo. "
              "Cada uma corresponde a instrumento já existente no país — a "
              "reserva de vagas em concursos públicos, os programas de acesso ao "
              "ensino superior, a legislação que proíbe discriminação na relação "
              "de trabalho e o Estatuto da Igualdade Racial. O que os resultados "
              "sugerem não é criar do zero, é onde apertar.")

    titulo(doc, "O que o estudo não diz")
    paragrafo(doc,
              "Uma palavra sobre limites, porque um trabalho que só afirma não "
              "merece confiança.")
    paragrafo(doc,
              "Os dados mostram associação, não prova de causa. Ninguém foi "
              "sorteado para ser negro ou para morar em determinado bairro, e por "
              "isso não é possível afirmar, com o rigor de um experimento, que a "
              "diferença observada seja integralmente efeito de discriminação. "
              "O que se pode dizer é que ela persiste depois de descontar tudo "
              "aquilo que os dados permitem observar — e que, para explicá-la por "
              "outra via, seria preciso um fator não medido mais forte do que "
              "qualquer um dos que foram medidos, escolaridade inclusive.")
    paragrafo(doc,
              "Há também o que os dados não enxergam: qualidade da escola "
              "frequentada, redes de contato, cor da pele autodeclarada em faixas "
              "mais finas, trajetória familiar. Parte desses fatores puxaria o "
              "resultado para baixo se pudesse ser medida; parte puxaria para "
              "cima. O trabalho trata o número encontrado como uma faixa, não "
              "como um ponto exato.")
    # Mesma lógica do parágrafo da Discussão (enxuto_patches._paragrafo_convergencia):
    # lidera com o que a inclinação sustenta; prazo só pelo cenário otimista do IC.
    _otim = P.get("TEND_ANOS_OTIMISTA")
    if P["TEND_P"] >= 0.05:
        _conv = ("Por fim, dez anos é pouco tempo para falar de tendência. A "
                 "redução observada no período é pequena e, estatisticamente, não se "
                 "distingue de nenhuma redução: os dados não permitem afirmar que a "
                 "diferença esteja se fechando."
                 + (f" Mesmo no cenário mais otimista que eles admitem, fechá-la levaria "
                    f"cerca de {_otim:.0f} anos." if _otim else "")
                 + " Esperar não resolve.")
    else:
        _conv = ("Por fim, a diferença vem diminuindo de forma estatisticamente "
                 "mensurável, mas devagar: no ritmo da década, fechá-la levaria cerca de "
                 f"{P['TEND_ANOS']:.0f} anos.")
    paragrafo(doc, _conv)

    titulo(doc, "Onde conferir")
    paragrafo(doc,
              "Todos os números deste texto vêm do trabalho completo, que "
              "documenta as fontes, os métodos e os testes de robustez, e que traz "
              "as tabelas e os gráficos correspondentes. Os dados são públicos: "
              "pesquisa domiciliar contínua do IBGE, de 2016 a 2025, cobrindo "
              f"{N['pessoas']} pessoas ocupadas em {N['bairros']} setores "
              "territoriais do país. Nada aqui depende de base proprietária ou de "
              "acesso restrito — qualquer pessoa com os dados e tempo pode "
              "refazer a conta.")


def main() -> int:
    doc = Document()
    estilo_base(doc)
    capa(doc)
    corpo(doc)
    SAIDA.parent.mkdir(exist_ok=True)
    try:
        doc.save(str(SAIDA))
    except PermissionError:
        print(f"ERRO: {SAIDA.name} está aberto no Word — feche e rode de novo.")
        return 1
    n_par = len([p for p in doc.paragraphs if p.text.strip()])
    palavras = sum(len(p.text.split()) for p in doc.paragraphs)
    print(f"OK -> {SAIDA.relative_to(RAIZ)}  ({SAIDA.stat().st_size // 1024} KB)")
    print(f"     {n_par} parágrafos, {palavras} palavras, "
          f"{len(N)} números lidos de params_nucleo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
