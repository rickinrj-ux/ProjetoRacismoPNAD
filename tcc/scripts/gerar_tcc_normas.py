# -*- coding: utf-8 -*-
"""
gerar_tcc_normas.py
===================
Reestrutura o relatório na forma exigida pelo Manual de Normas do MBA USP/Esalq
(itens 15–19) e pelo Template "Implementação de Algoritmo(s) de Machine
Learning", a partir do `relatorio_tcc_enxuto.tex` já com os números preenchidos.

Por que um gerador e não edição manual: o .docx que voltou do formatador tem 331
ajustes de forma, mas os 35 problemas restantes são de estrutura e conteúdo.
Corrigi-los no .docx mataria o pipeline csv → LaTeX → documento. Aqui a fonte
continua sendo o .tex, e o .docx é regerado com os estilos do template oficial.

Estrutura de saída (manual, item 16):
    Folha de rosto → Título + Resumo + Palavras-chave → Título em inglês +
    Abstract + Keywords → Introdução → Implementação de Algoritmo(s) de Machine
    Learning → Resultados e Discussão → Conclusão → Referências

Decisões registradas em tcc/revisoes/TODO_formatacao.md (validadas em 23/09):
  · a Revisão de Literatura foi distribuída: a teoria (Becker × Arrow) entra
    condensada na Introdução e a literatura de cada método acompanha o método
    na seção de Implementação — a norma não prevê seção de revisão;
  · sem seção de Agradecimentos;
  · sem itálico em termos estrangeiros.

Saída: tcc_normas.tex
Uso:   python tcc/scripts/gerar_tcc_normas.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from params_nucleo import P, milhar, pct, pt
from tcc_normas_texto import (PREAMBULO, FOLHA_ROSTO, RESUMO_ABSTRACT,
                              INTRODUCAO, CONCLUSAO, FECHO)

ROOT = Path(__file__).resolve().parents[2]
FONTE = ROOT / "relatorio_tcc_enxuto.tex"
SAIDA = ROOT / "tcc_normas.tex"

TITULO = ("Racismo estrutural no mercado de trabalho brasileiro: uma abordagem "
          "multinível e de decomposição salarial")
TITULO_EN = ("Structural racism in the Brazilian labour market: a multilevel and "
             "wage-decomposition approach")


# ── extração dos blocos reaproveitados ────────────────────────────────────────
def fatiar(tex: str) -> dict[str, str]:
    """Recorta o .tex atual nos blocos que serão remontados."""
    marcas = [(m.start(), m.group(1), m.group(2))
              for m in re.finditer(r"\\(section|subsection)\*?\{([^}]*)\}", tex)]
    blocos: dict[str, str] = {}
    for k, (pos, tipo, nome) in enumerate(marcas):
        fim = marcas[k + 1][0] if k + 1 < len(marcas) else len(tex)
        blocos[nome] = tex[pos:fim]
    return blocos



FIM_DE_DOCUMENTO = ("\\end{document}", "\\bibliography{", "\\bibliographystyle{",
                    "%  REFERÊNCIAS")


def _ate_o_fim(bloco: str) -> str:
    """Corta o bloco no primeiro marcador de fim do documento de origem.

    O último bloco fatiado ia até o fim do arquivo e arrastava \\end{document};
    tudo o que este gerador acrescentasse depois — Conclusão, referências —
    ficava fora do documento, sem erro de compilação que denunciasse.
    """
    corte = len(bloco)
    for marca in FIM_DE_DOCUMENTO:
        i = bloco.find(marca)
        if 0 <= i < corte:
            corte = i
    return bloco[:corte].rstrip() + "\n"


def sem_italico(t: str) -> str:
    """Tira \\textit e \\emph do corpo (decisão do autor: sem destaque em termos
    estrangeiros). A chave de fechamento é achada por contagem, porque há
    comandos aninhados dentro do argumento (por exemplo \\ref nas notas)."""
    for cmd in (r"\textit{", r"\emph{"):
        while (i := t.find(cmd)) >= 0:
            j, nivel = i + len(cmd), 1
            while j < len(t) and nivel:
                if t[j] == "{":
                    nivel += 1
                elif t[j] == "}":
                    nivel -= 1
                j += 1
            # mantém as chaves: tirar o grupo inteiro colaria o comando
            # anterior na palavra seguinte (\noindentComo ler...)
            t = t[:i] + "{" + t[i + len(cmd):j - 1] + "}" + t[j:]
    return t


def sem_barreiras(t: str) -> str:
    """Os cabeçalhos 'BARREIRA I/II' eram um recurso de narrativa; a norma não
    prevê divisões fora da hierarquia de seções."""
    t = re.sub(r"\\noindent\\rule\{\\textwidth\}\{1pt\}\s*", "", t)
    t = re.sub(r"\\textbf\{\\large BARREIRA[^\n]*\n", "", t)
    t = re.sub(r"\\textit\{[^\n]*\}\\par\n(?=\s*\\)", "", t)
    return t


def sem_numeracao_titulo(t: str) -> str:
    """A norma não numera títulos nem subtítulos."""
    return re.sub(r"(\\(?:sub)?section\*?\{)\d+(?:\.\d+)*\s+", r"\1", t)


def legendas_periodo(t: str) -> str:
    """Tabela 1. / Figura 1. — o separador é ponto, não dois-pontos."""
    return t



# Frase de chamada de cada float que só era citado depois da inserção. A norma
# exige que toda tabela e figura seja chamada no parágrafo que a antecede.
CHAMADAS = {
    "fig:hlm_blups":
        "A Figura~\\ref{fig:hlm_blups} contrasta os efeitos fixos de estado com "
        "os interceptos estimados para os bairros.",
    "tab:shap_importance":
        "A Tabela~\\ref{tab:shap_importance} traz o ranking completo das "
        "variáveis nos dois modelos.",
    # fig:shap_bee não entra: é uma subfigure, absorvida pela figura-mãe na
    # conversão para .docx — a chamada da mãe (fig:shap) já a cobre
    "fig:shap_wf":
        "A Figura~\\ref{fig:shap_wf} ilustra como a previsão de um caso "
        "individual é composta.",
    "fig:hlm_gap":
        "A Figura~\\ref{fig:hlm_gap} resume a sequência de degraus em barras.",
    "fig:ob_cascata":
        "A Figura~\\ref{fig:ob_cascata} apresenta as duas especificações em "
        "forma de cascata.",
    "fig:qr_rif":
        "A Figura~\\ref{fig:qr_rif} põe os dois ângulos lado a lado.",
    "fig:glmm_or":
        "A Figura~\\ref{fig:glmm_or} reúne as razões de chance dos três "
        "desfechos e dos modelos de cada um.",
    "tab:interseccional":
        "A Tabela~\\ref{tab:interseccional} decompõe o diferencial de cada "
        "grupo contra o homem branco.",
}


def chamar_antes(doc: str) -> str:
    """Insere a frase de chamada ao fim do parágrafo anterior ao float.

    A frase entra sem linha em branco entre ela e o texto que a precede, para
    ficar no mesmo parágrafo — é isso que a norma pede.
    """
    for rot, frase in CHAMADAS.items():
        ini = _inicio_do_float(doc, rot)
        if ini is None:
            print(f"  [AVISO] float nao localizado para a chamada: {rot}")
            continue
        if re.search(r"\ref\{" + re.escape(rot) + r"\}", doc[:ini]):
            continue                      # ja e citado antes; nao mexe
        corte = doc.rfind("\n\n", 0, ini)
        if corte < 0:
            corte = ini
        doc = doc[:corte] + " " + frase + doc[corte:]
    return doc


def _inicio_do_float(doc: str, rot: str) -> int | None:
    """Posição onde o float do rótulo começa (ambiente ou \\input)."""
    for m in re.finditer(r"\\begin\{(?:table|figure)\}.*?\\end\{(?:table|figure)\}",
                         doc, re.S):
        if ("\\label{" + rot + "}") in m.group(0):
            return m.start()
    for m in re.finditer(r"\\input\{(outputs/tables/[^}]+)\}", doc):
        f = ROOT / (m.group(1) if m.group(1).endswith(".tex") else m.group(1) + ".tex")
        if f.exists() and ("\\label{" + rot + "}") in f.read_text(
                encoding="utf-8", errors="ignore"):
            return m.start()
    return None



def expandir_inputs(doc: str) -> str:
    """Traz o conteúdo das tabelas para dentro do .tex.

    Assim o documento fica autocontido: a fonte de cada tabela pode ser
    acrescentada aqui (norma) e o pandoc não precisa resolver \\input.
    """
    def _sub(m):
        alvo = m.group(1)
        f = ROOT / (alvo if alvo.endswith(".tex") else alvo + ".tex")
        if not f.exists():
            print(f"  [AVISO] \\input inexistente: {alvo}")
            return ""
        return f.read_text(encoding="utf-8", errors="ignore")
    return re.sub(r"\\input\{([^}]+)\}", _sub, doc)


FONTE_TABELA = ("\\par\\smallskip\\footnotesize "
                "Fonte: Resultados originais da pesquisa.")


def fonte_nas_tabelas(doc: str) -> str:
    """A norma exige a fonte ao pé de cada tabela."""
    def _sub(m):
        corpo = m.group(0)
        if "Fonte:" in corpo:
            return corpo
        return corpo.replace("\\end{table}", FONTE_TABELA + "\n\\end{table}")
    return re.sub(r"\\begin\{table\}.*?\\end\{table\}", _sub, doc, flags=re.S)


def numerar_equacoes(doc: str) -> str:
    """Numeração manual entre parênteses ao fim da linha.

    O ambiente equation numera no PDF, mas o pandoc descarta o número ao
    converter para .docx; escrevendo o número no corpo, ele sobrevive nos dois.
    """
    contador = [0]

    def _sub(m):
        contador[0] += 1
        # linha em branco dentro de equation* quebra a matematica
        corpo = re.sub(r"\n\s*\n", "\n", m.group(1)).strip()
        corpo = re.sub(r"\\label\{[^}]*\}", "", corpo).rstrip()
        return ("\\begin{equation*}\n" + corpo +
                f"\n  \\qquad\\text{{({contador[0]})}}\n\\end{{equation*}}")

    return re.sub(r"\\begin\{equation\}(.*?)\\end\{equation\}", _sub, doc, flags=re.S)


EXTENSO = {"1": "um", "2": "dois", "3": "três", "4": "quatro", "5": "cinco",
           "6": "seis", "7": "sete", "8": "oito", "9": "nove", "10": "dez"}


def numeros_por_extenso(doc: str) -> str:
    """Zero a dez por extenso na prosa (norma). Não toca em matemática, em
    ambientes de tabela, em rótulos nem em números seguidos de unidade."""
    partes = re.split(r"(\\begin\{(?:table|figure|equation\*?|tabular)\}.*?"
                      r"\\end\{(?:table|figure|equation\*?|tabular)\}|\$[^$]*\$)",
                      doc, flags=re.S)
    for i in range(0, len(partes), 2):          # só os trechos de prosa
        t = partes[i]
        for n, ext in EXTENSO.items():
            t = re.sub(r"(?<![\w,.\-])" + n +
                       r"(?![\d,.%\w])(?!\s*(?:p\.p\.|%|milh|mil\b|anos|pontos))",
                       ext, t)
        partes[i] = t
    return "".join(partes)


NOTA_LOG = (
    '\\footnote{Os modelos têm o logaritmo do rendimento como variável dependente, de modo que o coeficiente está em log-pontos. A variação percentual correspondente é $(e^{\\hat\\beta}-1)\\times 100$, e não $\\hat\\beta\\times 100$: para $\\hat\\beta=-0{,}2123$, por exemplo, tem-se $-19{,}1\\%$, e não $-21{,}2\\%$. As duas leituras se aproximam quando o coeficiente é pequeno e divergem à medida que ele cresce em módulo; todos os percentuais de gap deste trabalho usam a primeira forma.}'
)


def nota_sobre_log(doc: str) -> str:
    """Explica, uma única vez, a conversão de log-pontos para percentual.

    Sem isso o leitor confere "beta = -0,2123" contra "19,1%" pela conta linear
    e conclui que há erro. A nota entra na primeira frase que apresenta um gap
    em % ao lado do coeficiente.
    """
    marca = "trabalhadores negros recebem "
    i = doc.find(marca)
    if i < 0:
        print("  [AVISO] ponto de inserção da nota sobre log não encontrado")
        return doc
    fim = doc.find("$)", i)                 # fecha o parêntese do coeficiente
    if fim < 0:
        return doc
    fim += 2
    return doc[:fim] + NOTA_LOG + doc[fim:]


def refs_penduradas(doc: str) -> dict[str, int]:
    """\\ref e \\eqref cujo \\label não existe mais no documento.

    Sem isso, um bloco removido na reestruturação deixa "??" no PDF, e o leitor
    encontra a menção a uma tabela que não está mais lá.
    """
    # os \label das tabelas moram nos arquivos de \input — expandir antes
    expandido = doc
    for alvo in re.findall(r"\\input\{([^}]+)\}", doc):
        f = ROOT / (alvo if alvo.endswith(".tex") else alvo + ".tex")
        if f.exists():
            expandido += "\n" + f.read_text(encoding="utf-8", errors="ignore")
    rotulos = set(re.findall(r"\\label\{([^}]+)\}", expandido))
    citados: dict[str, int] = {}
    for m in re.finditer(r"\\(?:ref|eqref)\{([^}]+)\}", doc):
        if m.group(1) not in rotulos:
            citados[m.group(1)] = citados.get(m.group(1), 0) + 1
    return citados


def main() -> int:
    if not FONTE.exists():
        print(f"ERRO: {FONTE} não existe — rode antes gerar_relatorio_enxuto.py")
        return 1

    tex = FONTE.read_text(encoding="utf-8")
    blocos = fatiar(tex)
    print(f"{len(blocos)} blocos identificados na fonte")

    # blocos aproveitados na íntegra (já com os números preenchidos)
    def bloco(nome: str) -> str:
        for k, v in blocos.items():
            if k.startswith(nome[:38]):
                return _ate_o_fim(v)
        print(f"  [AVISO] bloco não encontrado: {nome}")
        return ""

    METODO = [
        "Base de dados: PNAD Contínua",
        "Modelo Linear Hierárquico: indivíduos em bairros",
        "Decomposição de Oaxaca--Blinder",
        "Regressão quantílica e decomposição RIF",
        "Modelo logístico multinível de acesso",
        "Sensibilidade a variáveis omitidas",
        "Inferência: erros-padrão agrupados",
        "Random Forest, XGBoost e SHAP Values",
    ]
    RESULTADOS = [
        "Modelos Hierárquicos Lineares",
        "Modelos de Machine Learning e SHAP Values",
        "Decomposição do gap por mediação contextual",
        "Decomposição de Oaxaca--Blinder: composição",
        "Regressão Quantílica e RIF-OB",
        "GLMM logístico: o teto de vidro no acesso",
        "Interseccionalidade: raça e gênero",
        "Multicolinearidade do Modelo M4",
    ]

    partes = [PREAMBULO, FOLHA_ROSTO, RESUMO_ABSTRACT, INTRODUCAO,
              "\n\\section*{Implementação de Algoritmo(s) de Machine Learning}\n"]
    partes += [bloco(n) for n in METODO]
    partes.append("\n\\section*{Resultados e Discussão}\n")
    partes += [bloco(n) for n in RESULTADOS]
    partes.append(bloco("Discussão e Prescrição").replace(
        "\\section{Discussão e Prescrição}", ""))
    partes.append(bloco("Limitações e escopo de validade").replace(
        "\\subsection*{Limitações e escopo de validade}",
        "\\subsection*{Limitações e escopo de validade}"))
    # a declaração de uso de IA vinha no fim do arquivo de origem e era cortada
    # junto com o \end{document}; entra aqui, antes das Referências
    decl = tex[tex.find("Declaração de uso de inteligência artificial"):] \
        if "Declaração de uso de inteligência artificial" in tex else ""
    if decl:
        decl = _ate_o_fim(decl)
        partes.append("\n\\subsection*{Declaração de uso de inteligência artificial}\n"
                      + decl.split("\n", 1)[1])
    partes.append(CONCLUSAO)
    partes.append(FECHO)

    doc = "\n".join(partes)
    doc = sem_numeracao_titulo(sem_italico(sem_barreiras(doc)))
    doc = chamar_antes(doc)
    doc = nota_sobre_log(doc)
    doc = expandir_inputs(doc)
    doc = fonte_nas_tabelas(doc)
    doc = numerar_equacoes(doc)
    # subseções da norma não são numeradas: tudo vira starred
    doc = re.sub(r"\\subsection\{", r"\\subsection*{", doc)
    doc = re.sub(r"\\section\{", r"\\section*{", doc)

    pendentes = refs_penduradas(doc)
    if pendentes:
        print("\n  [ERRO] referências a rótulos que não existem mais no documento:")
        for rot, quantas in sorted(pendentes.items()):
            print(f"    \\ref{{{rot}}}  ({quantas}x) — o bloco que definia este "
                  f"rótulo saiu na reestruturação")
        print("  Corrija o texto ou traga o bloco de volta antes de compilar.\n")

    SAIDA.write_text(doc, encoding="utf-8")
    n_sec = len(re.findall(r"\\section\*\{", doc))
    n_sub = len(re.findall(r"\\subsection\*\{", doc))
    print(f"OK -> {SAIDA.name}  ({len(doc.splitlines())} linhas, "
          f"{n_sec} seções, {n_sub} subseções)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
