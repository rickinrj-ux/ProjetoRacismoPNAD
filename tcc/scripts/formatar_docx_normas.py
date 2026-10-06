# -*- coding: utf-8 -*-
"""
formatar_docx_normas.py
=======================
Aplica ao .docx a formatação do Manual de Normas do MBA USP/Esalq.

Por que não basta o `--reference-doc`: o template oficial guarda a formatação
**direto nos parágrafos**, não no estilo "Normal" — que chega sem entrelinha,
sem recuo e sem espaçamento. O pandoc copia os estilos, herda o vazio, e o
texto sai agrupado. Aqui a formatação é imposta explicitamente.

Regras aplicadas (manual, itens 15 e 16):
  · corpo em Arial 11, entrelinha 1,5, justificado, recuo de 1,25 cm na
    primeira linha;
  · legendas, fontes e notas em Arial 11, espaçamento simples, sem recuo;
  · tabelas em Arial 11, espaçamento simples, sem negrito e sem cor
    (item 15.2: "não é permitido utilizar realce em negrito nas tabelas").

Uso: python tcc/scripts/formatar_docx_normas.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from docx import Document
from docx.enum.text import (WD_ALIGN_PARAGRAPH, WD_LINE_SPACING,
                            WD_TAB_ALIGNMENT)
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
ALVO = ROOT / "entregaveis" / "TCC_Ricardo_Calheiros_MBA_USP_Esalq.docx"

FONTE_NOME = "Arial"
FONTE_PT = 11

# parágrafos que não levam recuo nem entrelinha 1,5
RE_LEGENDA = re.compile(r"^\s*(Tabela|Figura)\s+\d+\.")
RE_FONTE = re.compile(r"^\s*(Fonte|Nota|Fonte dos dados):")
RE_META = re.compile(r"^\s*(Resumo|Abstract|Palavras-chave|Keywords)\b")


def _fonte_do_run(run) -> None:
    run.font.name = FONTE_NOME
    run.font.size = Pt(FONTE_PT)
    if run.font.color and run.font.color.rgb is not None:
        run.font.color.rgb = RGBColor(0, 0, 0)


SECOES = {"Resumo", "Abstract", "Considerações Iniciais", "Conclusão", "Referências",
          "Implementação de Algoritmo(s) de Machine Learning",
          "Resultados e Discussão", "Agradecimentos"}

# linha do corpo, em pontos: "um espaço de caractere" dos anexos
ESPACO = 14


def _e_referencia(texto: str) -> bool:
    """Entrada da lista de referências: SOBRENOME, Nome. Título…"""
    return bool(re.match(r"^[A-ZÀ-Ü][A-ZÀ-Ü\s'-]{2,}(,|;)\s", texto))


def formatar_corpo(doc: Document) -> tuple[int, int]:
    """Aplica a formatação que os anexos cotam para cada bloco do documento.

    Percorre em ordem, mantendo a seção corrente: o Resumo e o Abstract pedem
    espaçamento simples e sem recuo, as Referências pedem à esquerda e sem
    recuo, e o corpo das demais seções pede 1,5 com recuo de 1,25 cm.
    """
    corpo = legendas = 0
    secao = ""

    for p in doc.paragraphs:
        texto = p.text.strip()
        for r in p.runs:
            _fonte_do_run(r)
        if not texto:
            continue
        pf = p.paragraph_format

        if texto in SECOES:                       # título de seção
            secao = texto
            for r in p.runs:
                r.font.bold = True
            pf.line_spacing = 1.5
            pf.first_line_indent = Cm(0)
            pf.left_indent = Cm(0)
            pf.space_before = Pt(ESPACO)          # um espaço de caractere antes
            pf.space_after = Pt(ESPACO)           # e outro depois
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            continue

        if RE_LEGENDA.match(texto) or RE_FONTE.match(texto):
            # manual, Tabelas 7 e 9: "Dados originais da pesquisa" na seção de métodos;
            # "Resultados originais da pesquisa" em Resultados e Discussão
            if secao.startswith("Implementação") and "Resultados originais" in texto:
                for r in p.runs:
                    r.text = r.text.replace("Resultados originais", "Dados originais")
            pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
            pf.first_line_indent = Cm(0)
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            if RE_LEGENDA.match(texto):
                pf.space_before = Pt(12)
                pf.space_after = Pt(2)
            else:
                pf.space_before = Pt(2)
                pf.space_after = Pt(12)
            legendas += 1
            continue

        if secao in ("Resumo", "Abstract") or texto.startswith(
                ("Palavras-chave", "Keywords")):
            # anexo p. 62: simples, justificado, SEM recuo na primeira linha
            pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
            pf.first_line_indent = Cm(0)
            pf.space_before = Pt(0)
            pf.space_after = Pt(ESPACO) if texto.startswith(
                ("Palavras-chave", "Keywords")) else Pt(0)
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            corpo += 1
            continue

        if secao == "Referências" or _e_referencia(texto):
            # anexo p. 65: à esquerda, simples, sem recuo, uma linha entre elas
            pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
            pf.first_line_indent = Cm(0)
            pf.left_indent = Cm(0)
            pf.space_before = Pt(0)
            pf.space_after = Pt(6)
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            # mesmo autor e ano (Alencar 2026a/b/c): o CSL do pandoc põe a letra antes do
            # ano ("a2026"); a ABNT pede depois ("2026a"), como na citação do texto
            for r in p.runs:
                if re.search(r"\b[a-h](?:19|20)\d{2}\b", r.text):
                    r.text = re.sub(r"\b([a-h])((?:19|20)\d{2})\b", r"\2\1", r.text)
                # manual, 19.1: "sempre inserir um hífen entre as páginas" (o citeproc põe "–")
                if "–" in r.text:
                    r.text = re.sub(r"(\d)\s*–\s*(\d)", r"\1-\2", r.text)
            corpo += 1
            continue

        if p.style.name.startswith("Heading"):    # subtítulo
            for r in p.runs:
                r.font.bold = True
            pf.line_spacing = 1.5
            pf.first_line_indent = Cm(1.25)       # subtítulo tem recuo (16.4)
            pf.space_before = Pt(ESPACO)
            pf.space_after = Pt(ESPACO)
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            continue

        pf.line_spacing = 1.5                     # corpo das demais seções
        pf.first_line_indent = Cm(1.25)
        pf.space_after = Pt(0)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        corpo += 1

    return corpo, legendas


def formatar_capa(doc: Document) -> int:
    """Folha de rosto e títulos do Resumo/Abstract (anexos pp. 61-62).

    O corpo genérico dava a tudo recuo de 1,25 cm, entrelinha 1,5 e justificado: o
    título saía torto, os autores colados nele e as afiliações do tamanho do texto.
    """
    n = 0
    na_capa = True
    for p in doc.paragraphs:
        texto = p.text.strip()
        if not texto:
            continue
        pf = p.paragraph_format
        if texto in ("Resumo", "Abstract"):
            na_capa = False
            # template: "Resumo e Palavras-chave em negrito, alinhados à esquerda" (estava
            # centralizado desde 03/10 e o conferir_anexos acusava, sem derrubar a fila)
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.first_line_indent = Cm(0)
            pf.space_before = Pt(ESPACO)
            n += 1
            continue
        if texto == "Considerações Iniciais":
            break
        if texto.startswith(INICIAM_PAGINA):             # título (pt ou en)
            pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.first_line_indent = Cm(0)
            pf.left_indent = Cm(0)
            pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
            pf.space_after = Pt(ESPACO)
            for r in p.runs:
                r.font.bold = True
            n += 1
        elif texto.startswith(("Palavras-chave", "Keywords")):
            pf.space_before = Pt(ESPACO)                 # uma linha depois do resumo
        elif na_capa and re.match(r"^\d\*?\s", texto):   # afiliações (notas da capa)
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.first_line_indent = Cm(0)
            pf.left_indent = Cm(0)
            pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
            pf.space_before = Pt(12) if texto.startswith("1") else Pt(0)
            pf.space_after = Pt(0)
            for r in p.runs:
                r.font.size = Pt(10)
            n += 1
        elif na_capa and ";" in texto and len(texto) < 120:   # linha dos autores
            pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf.first_line_indent = Cm(0)
            pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
            pf.space_before = Pt(24)
            n += 1
    return n


def formatar_notas(doc: Document) -> int:
    """Legenda, objeto, Fonte e Nota formam um bloco que não se separa.

    · a Nota vem depois da Fonte (norma): as notas de tabela chegavam antes dela;
    · Fonte e Nota coladas, com o respiro de 12 pt só depois do bloco;
    · a legenda e a imagem ficam presas ao parágrafo seguinte: a legenda da Tabela 6
      ficava no pé de uma página e a tabela na outra.
    """
    from docx.text.paragraph import Paragraph
    corpo = doc.element.body
    W_P = qn("w:p")

    def _txt(el):
        return "".join(t.text or "" for t in el.iter(qn("w:t"))).strip()

    # 1) Nota imediatamente antes da Fonte: troca a ordem
    n = 0
    filhos = list(corpo.iterchildren())
    for a, b in zip(filhos, filhos[1:]):
        if a.tag == W_P and b.tag == W_P and _txt(a).startswith("Nota:") \
                and RE_FONTE.match(_txt(b)) and not _txt(b).startswith("Nota"):
            corpo.remove(a)
            b.addnext(a)
            n += 1

    # 1b) texto solto entre a tabela e a Fonte é nota da tabela ("Suporte comum: ..."
    #     na Tabela 1): vai para depois da Fonte, com o rótulo Nota
    filhos = list(corpo.iterchildren())
    for i, el in enumerate(filhos):
        if el.tag != qn("w:tbl"):
            continue
        # o pandoc deixa um bookmarkEnd ou um parágrafo vazio depois de cada tabela
        seguintes = [x for x in filhos[i + 1:i + 6]
                     if x.tag == qn("w:tbl") or (x.tag == W_P and _txt(x))]
        if len(seguintes) < 2:
            continue
        a, b = seguintes[0], seguintes[1]
        # legenda não é nota: a Figura 10 vem numa tabela de leiaute do pandoc, e a sua
        # legenda (entre essa "tabela" e a Fonte) virava "Nota: Figura 10."
        if a.tag == W_P and b.tag == W_P and _txt(a) and not RE_FONTE.match(_txt(a)) \
                and not RE_LEGENDA.match(_txt(a)) and _txt(b).startswith("Fonte"):
            corpo.remove(a)
            b.addnext(a)
            if not _txt(a).startswith("Nota"):
                runs = a.findall(qn("w:r"))
                if runs:
                    from docx.text.run import Run
                    r0 = Run(runs[0], None)
                    r0.text = "Nota: " + r0.text
            n += 1

    # 2) espaçamentos e "manter com o próximo"
    filhos = list(corpo.iterchildren())
    for i, el in enumerate(filhos):
        if el.tag != W_P:
            continue
        p = Paragraph(el, doc._body)
        pf = p.paragraph_format
        t = _txt(el)
        prox = filhos[i + 1] if i + 1 < len(filhos) else None
        prox_txt = _txt(prox) if prox is not None and prox.tag == W_P else ""
        if el.findall(".//" + qn("w:drawing")) or RE_LEGENDA.match(t):
            pf.keep_with_next = True
            pf.keep_together = True          # a legenda longa não se parte entre páginas
        if t.startswith("Fonte") and prox_txt.startswith("Nota:"):
            pf.space_after = Pt(0)
            pf.keep_with_next = True
        if t.startswith("Nota:"):
            pf.space_before = Pt(0)
            pf.space_after = Pt(12)
            pf.first_line_indent = Cm(0)
            pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
            n += 1
    return n


_W_T, _M_T = qn("w:t"), "{http://schemas.openxmlformats.org/officeDocument/2006/math}t"
# abreviaturas que terminam em ponto sem encerrar a frase
_ABREV = {"vs", "i.e", "e.g", "p", "n", "fig", "tab", "al", "cf", "ex", "aprox", "obs"}


def _texto_el(el) -> str:
    """Texto de um elemento, contando também o das equações (m:t), na ordem do documento."""
    return "".join(x.text or "" for x in el.iter() if x.tag in (_W_T, _M_T))


def _fim_da_primeira_frase(texto: str, inicio: int) -> int | None:
    """Posição do ponto que encerra a primeira frase depois de `inicio` (None se só há uma)."""
    for m in re.finditer(r"\.\s+(?=[A-ZÀ-Ü(])", texto[inicio:]):
        pos = inicio + m.start()
        palavra = re.search(r"([\w.]+)$", texto[:pos])
        if palavra and palavra.group(1).lower().rstrip(".") in _ABREV:
            continue
        return pos
    return None


def _cortar_paragrafo(p_el, pos: int) -> list:
    """Corta o parágrafo no caractere `pos` (o ponto da frase): o que vem depois sai do
    parágrafo e é devolvido como lista de elementos. Runs e equações são movidos inteiros;
    só o run onde cai o corte é partido, para não perder itálico nem equação."""
    import copy
    resto, acum, cortado = [], 0, False
    for filho in [c for c in p_el if c.tag != qn("w:pPr")]:
        t = _texto_el(filho)
        if cortado:
            p_el.remove(filho)
            resto.append(filho)
        elif acum + len(t) > pos:
            k = pos - acum                      # posição do ponto dentro deste filho
            if filho.tag == qn("w:r") and filho.find(_W_T) is not None:
                ws = filho.find(_W_T)
                antes, depois = ws.text[:k].rstrip(), ws.text[k + 1:].lstrip()
                ws.text = antes
                if depois:
                    novo = copy.deepcopy(filho)
                    novo.find(_W_T).text = depois
                    novo.find(_W_T).set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                    resto.append(novo)
            else:                               # corte dentro de equação: ela fica no título
                pass
            cortado = True
        acum += len(t)
    return resto


def _tirar_ponto_final(p_el) -> bool:
    """Manual, Tabelas 7 e 9: sem ponto depois do título, da Fonte e da Nota."""
    textos = [x for x in p_el.iter() if x.tag in (_W_T, _M_T) and (x.text or "").strip()]
    if not textos:
        return False
    ult = textos[-1]
    s = ult.text.rstrip()
    if s.endswith(".") and not s.endswith("..."):
        ult.text = s[:-1]
        return True
    return False


def titulos_concisos(doc: Document) -> tuple[int, int]:
    """Título da tabela = primeira frase; o restante vai para a Nota, depois da Fonte.

    Os títulos chegavam com 25 a 130 palavras. O manual pede tabela autoexplicativa e prevê a
    Nota, depois da Fonte, para o que a explica; deixa o título curto, que é o que se lê
    primeiro. Depois tira o ponto final de títulos, Fontes e Notas (Tabelas 7 e 9 do manual).
    """
    import copy
    from docx.text.paragraph import Paragraph
    corpo = doc.element.body
    W_P, W_TBL = qn("w:p"), qn("w:tbl")
    movidos = 0
    filhos = list(corpo.iterchildren())
    for i, el in enumerate(filhos):
        if el.tag != W_P:
            continue
        txt = _texto_el(el)
        m = re.match(r"^\s*Tabela\s+\d+\.\s*", txt)
        if not m:
            continue
        prox = [x for x in filhos[i + 1:i + 4] if x.tag == W_TBL or (x.tag == W_P and _texto_el(x).strip())]
        if not prox or prox[0].tag != W_TBL:
            continue
        pos = _fim_da_primeira_frase(txt, m.end())
        resto1 = _cortar_paragrafo(el, pos) if pos is not None else []
        # primeira frase ainda longa (> 20 palavras): corta no travessão ou no primeiro
        # parêntese que não seja citação logo no início ("RIF-OB (Firpo; …, 2018)")
        txt2 = _texto_el(el)
        resto2 = []
        if len(txt2[m.end():].split()) > 20:
            pos2 = _corte_secundario(txt2, m.end())
            if pos2 is not None:
                resto2 = _cortar_paragrafo(el, pos2)
        if not resto1 and not resto2:
            continue
        # destino: depois da Fonte da tabela (ou da própria tabela, se não houver Fonte)
        tbl = prox[0]
        seguintes = []
        x = tbl.getnext()
        while x is not None and len(seguintes) < 3:
            if x.tag == W_P and _texto_el(x).strip():
                seguintes.append(x)
            elif x.tag == W_TBL:
                break
            x = x.getnext()
        fonte = next((s for s in seguintes[:1] if _texto_el(s).strip().startswith("Fonte")), None)
        nota = None
        if fonte is not None and len(seguintes) > 1 and _texto_el(seguintes[1]).strip().startswith("Nota:"):
            nota = seguintes[1]
        modelo = fonte if fonte is not None else el
        novo = copy.deepcopy(modelo)
        for c in [c for c in novo if c.tag != qn("w:pPr")]:
            novo.remove(c)
        r_rot = copy.deepcopy(next(c for c in el if c.tag == qn("w:r")))
        for c in [c for c in r_rot if c.tag != qn("w:rPr")]:
            r_rot.remove(c)
        t_rot = OxmlElement("w:t")
        t_rot.text = "Nota: "
        t_rot.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        r_rot.append(t_rot)
        novo.append(r_rot)
        for c in resto2:
            novo.append(c)
        if resto2 and resto1:                   # fim do título que desceu + resto da legenda
            _tirar_ponto_final(novo)
            sep1 = copy.deepcopy(r_rot)
            sep1.find(_W_T).text = ". "
            novo.append(sep1)
        for c in resto1:
            novo.append(c)
        if nota is not None:                    # a Nota que já existia continua a nova
            _tirar_ponto_final(novo)
            sep = copy.deepcopy(r_rot)
            sep.find(_W_T).text = ". "
            novo.append(sep)
            primeiro = next((x for x in nota.iter() if x.tag == _W_T and x.text), None)
            if primeiro is not None:
                primeiro.text = re.sub(r"^\s*Nota:\s*", "", primeiro.text)
            for c in [c for c in nota if c.tag != qn("w:pPr")]:
                novo.append(c)
            corpo.remove(nota)
        (fonte if fonte is not None else tbl).addnext(novo)
        pf = Paragraph(novo, doc._body).paragraph_format
        pf.space_before, pf.space_after = Pt(0), Pt(12)
        pf.first_line_indent = Cm(0)
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.keep_with_next = False
        if fonte is not None:
            fp = Paragraph(fonte, doc._body).paragraph_format
            fp.space_after, fp.keep_with_next = Pt(0), True
        movidos += 1

    pontos = 0
    for p in doc.paragraphs:
        t = p.text.strip()
        if RE_LEGENDA.match(t) or t.startswith(("Fonte", "Nota:")):
            pontos += _tirar_ponto_final(p._p)
        if t.startswith("Nota:"):
            _maiuscula_depois(p._p, "Nota:")
            anterior = ""
            for r in p.runs:                    # "...milhão). como ler a Tabela 13" no meio da Nota
                if "como ler a" in r.text:
                    r.text = re.sub(r"([.:)]\s+)como ler a", lambda m: m.group(1) + "Como ler a", r.text)
                    # o ponto pode estar no trecho (run) anterior
                    if r.text.startswith("como ler a") and anterior.rstrip().endswith((".", ":", ")")):
                        r.text = "C" + r.text[1:]
                if r.text:
                    anterior = r.text
    return movidos, pontos


def _corte_secundario(texto: str, inicio: int) -> int | None:
    """Onde encurtar um título que é uma frase só: no travessão; senão, no primeiro
    parêntese que venha depois da 6.ª palavra (os anteriores costumam ser citação)."""
    corpo = texto[inicio:]
    i = corpo.find(" — ")
    if i > 0 and len(corpo[:i].split()) >= 5:
        return inicio + i + 1                   # o próprio travessão sai
    for mt in re.finditer(r" \(", corpo):
        if len(corpo[:mt.start()].split()) >= 6:
            return inicio + mt.start()          # sai o espaço; o parêntese desce
    return None


def _maiuscula_depois(p_el, rotulo: str) -> None:
    """Primeira letra depois do rótulo em maiúscula ("Nota: como ler" → "Nota: Como ler")."""
    passou = False
    for x in p_el.iter(_W_T):
        s = x.text or ""
        if not passou:
            j = s.find(rotulo)
            if j < 0:
                continue
            passou, s0 = True, j + len(rotulo)
        else:
            s0 = 0
        for k in range(s0, len(s)):
            if s[k].isalpha():
                x.text = s[:k] + s[k].upper() + s[k + 1:]
                return
            if not s[k].isspace() and s[k] not in "(\"“":
                return


# definições cuja sigla não sai das iniciais (inglês ou termo composto)
_SIGLAS_FIXAS = {
    "razão de verossimilhança (LR)": "razão de verossimilhança [LR]",
    "máxima verossimilhança (ML)": "máxima verossimilhança [ML]",
    "Domicílios Contínua (PNAD Contínua)": "Domicílios Contínua [PNAD Contínua]",
}
_RE_DEF = re.compile(r"((?:[A-ZÀ-Ú][\wÀ-ú\-]+)(?:\s+(?:[A-ZÀ-Ú][\wÀ-ú\-]+|de|da|do|das|dos|por|e|em))"
                     r"{1,8})\s+\(([A-Z]{2,8})\)")


def siglas_em_colchetes(doc: Document) -> int:
    """Manual, Tabela 6: na 1.ª ocorrência a sigla vai entre colchetes depois da definição —
    "Taxa Interna de Retorno [TIR]". Só troca quando é definição de fato: as iniciais das
    palavras com maiúscula formam a sigla (não "(H1)", "(M3)", "(VD4020)")."""
    n = 0
    for p in doc.paragraphs:
        for r in p.runs:
            s = r.text
            for a, b in _SIGLAS_FIXAS.items():
                if a in s:
                    s, n = s.replace(a, b), n + 1

            def _sub(m):
                nonlocal n
                import unicodedata
                ini = "".join(w[0] for w in m.group(1).split() if w[0].isupper())
                ini = unicodedata.normalize("NFKD", ini).encode("ascii", "ignore").decode()
                # pelo final: "A Unidade Primária de Amostragem" → "AUPA" termina em "UPA"
                if ini.upper().endswith(m.group(2)):
                    n += 1
                    return f"{m.group(1)} [{m.group(2)}]"
                return m.group(0)
            s = _RE_DEF.sub(_sub, s)
            if s != r.text:
                r.text = s
    return n


def numerar_equacoes(doc: Document) -> int:
    """Manual, 15.3: equação alinhada à direita, com o número "(1)" no fim da linha.

    O "(1)" vinha dentro da própria equação (\\qquad\\text{(1)}), e o Sistema de Trabalho Final
    não o reconhecia como numeração. Aqui ele sai da equação e vira texto depois dela; a equação
    deixa de ser bloco (oMathPara) e fica em linha, no parágrafo alinhado à direita."""
    M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
    n = 0
    for p in doc.paragraphs:
        for mp in p._p.findall(M + "oMathPara"):
            ts = [t for t in mp.iter(M + "t") if (t.text or "").strip()]
            if not ts:
                continue
            m = re.search(r"\s*\((\d+)\)\s*$", ts[-1].text)
            if not m:
                continue
            ts[-1].text = ts[-1].text[:m.start()]
            pai, pos = mp.getparent(), mp.getparent().index(mp)
            for k, om in enumerate(mp.findall(M + "oMath")):
                pai.insert(pos + k, om)
            pai.remove(mp)
            r = OxmlElement("w:r")
            rpr = OxmlElement("w:rPr")
            fonte = OxmlElement("w:rFonts")
            fonte.set(qn("w:ascii"), FONTE_NOME)
            fonte.set(qn("w:hAnsi"), FONTE_NOME)
            rpr.append(fonte)
            r.append(rpr)
            t = OxmlElement("w:t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = f"   ({m.group(1)})"
            r.append(t)
            p._p.append(r)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p.paragraph_format.first_line_indent = Cm(0)
            n += 1
    return n


def notas_de_rodape_9(doc: Document) -> int:
    """Manual, Tabela 4: notas de rodapé em Arial 9, espaçamento simples (estavam em 11)."""
    from docx.oxml import parse_xml
    from lxml import etree
    n = 0
    for rel in doc.part.rels.values():
        if not rel.reltype.endswith("/footnotes"):
            continue
        parte = rel.target_part
        raiz = parse_xml(parte.blob)
        for r in raiz.iter(qn("w:r")):
            rpr = r.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr")
                r.insert(0, rpr)
            for tag in ("w:sz", "w:szCs"):
                e = rpr.find(qn(tag))
                if e is None:
                    e = OxmlElement(tag)
                    rpr.append(e)
                e.set(qn("w:val"), "18")
            n += 1
        for p in raiz.iter(qn("w:p")):
            ppr = p.find(qn("w:pPr"))
            if ppr is None:
                ppr = OxmlElement("w:pPr")
                p.insert(0, ppr)
            sp = ppr.find(qn("w:spacing"))
            if sp is None:
                sp = OxmlElement("w:spacing")
                ppr.append(sp)
            sp.set(qn("w:line"), "240")
            sp.set(qn("w:lineRule"), "auto")
            sp.set(qn("w:after"), "0")
        parte._blob = etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", standalone=True)
    return n


def exportar_pdf() -> bool:
    """PDF de entrega a partir do próprio .docx formatado (automação do Word), para que os
    dois sejam o mesmo documento: o PDF do LaTeX tinha ~6 páginas a menos e não recebia a
    formatação da norma aplicada aqui. Sem Office, fica o PDF copiado do LaTeX."""
    try:
        import win32com.client as w32
    except ImportError:
        return False
    wd = w32.DispatchEx("Word.Application")
    wd.Visible = False
    try:
        d = wd.Documents.Open(str(ALVO), False, True)
        d.ExportAsFixedFormat(str(ALVO.with_suffix(".pdf")), 17)
        d.Close(0)
        return True
    except Exception as e:
        print(f"[AVISO] PDF pelo Word falhou ({e}); fica o do LaTeX")
        return False
    finally:
        wd.Quit()


def chamadas_de_nota(doc: Document) -> int:
    """Chamada de nota de rodapé em sobrescrito. O pandoc usa o estilo de caractere
    'Footnote Reference', que o template oficial não define como sobrescrito: a chamada
    saía colada ao número no corpo do texto ("0,697" + nota 14 = "0,69714")."""
    from docx.oxml.ns import qn
    n = 0
    corpo = doc.element.body
    # o número também aparece dentro da própria nota (w:footnoteRef, em footnotes.xml):
    # lá saía em tamanho cheio, "7 τ²" em vez de "⁷ τ²"
    raizes = [corpo]
    parte_notas = None
    for rel in doc.part.rels.values():
        if rel.reltype.endswith("/footnotes"):
            from docx.oxml import parse_xml
            parte_notas = rel.target_part           # Part genérico: XML só no blob
            raizes.append(parse_xml(parte_notas.blob))
    for r in (r for raiz in raizes for r in raiz.iter(qn("w:r"))):
        if r.find(qn("w:footnoteReference")) is not None or \
                r.find(qn("w:footnoteRef")) is not None:
            rpr = r.get_or_add_rPr()
            va = rpr.find(qn("w:vertAlign"))
            if va is None:
                va = OxmlElement("w:vertAlign")
                rpr.append(va)
            va.set(qn("w:val"), "superscript")
            n += 1
    if parte_notas is not None:
        from lxml import etree
        parte_notas._blob = etree.tostring(raizes[-1], xml_declaration=True,
                                           encoding="UTF-8", standalone=True)
    return n


def formatar_tabelas(doc: Document) -> int:
    """Arial 11, espaçamento simples e sem negrito — o manual proíbe realce
    em negrito e código de cores nas tabelas (item 15.2)."""
    celulas = 0
    numeros = 0
    for t in doc.tables:
        if len(t.columns) == 1 and t._tbl.findall(".//" + qn("w:drawing")):
            continue        # tabela de leiaute do pandoc em volta de figura: não é tabela de dados
        bordas_da_norma(t)
        numeros += alinhar_numeros(t)
        n_col = len(t.columns)
        # 7+ colunas em 9 pt não cabiam na janela de 16 cm (Tab. 9: "0,08/7")
        tam = 11 if n_col <= 4 else 10 if n_col <= 6 else 8
        ajustar_larguras(t, tam)
        manter_inteira(t)
        # Fonte da tabela conforme o número de colunas. Em Arial 11 fixo, as tabelas de
        # 7 a 10 colunas quebravam os números dentro da célula ("0,/83/0", "Qua/ntil");
        # o PDF de entrega já usa fonte menor nessas tabelas. CONFIRMAR com o orientador
        # se o manual admite tamanho menor que 11 em tabela.
        for linha in t.rows:
            for cel in linha.cells:
                for p in cel.paragraphs:
                    pf = p.paragraph_format
                    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
                    pf.space_after = Pt(0)
                    pf.first_line_indent = Cm(0)
                    for r in p.runs:
                        _fonte_do_run(r)
                        r.font.size = Pt(tam)
                        r.font.bold = False
                    celulas += 1
        # sem bordas internas (norma), um registro de várias linhas se fundia ao seguinte
        # (Tabela 2): respiro de 4 pt depois de cada linha, texto alinhado ao topo. Só nas
        # tabelas de texto; nas numéricas, de uma linha por célula, o respiro só ocupa página
        textual = any(len(c.text) > 30 for linha in t.rows[1:] for c in linha.cells)
        if textual:
            for linha in t.rows[1:]:
                for cel in linha.cells:
                    tcPr = cel._tc.get_or_add_tcPr()
                    va = tcPr.find(qn("w:vAlign"))
                    if va is None:
                        va = OxmlElement("w:vAlign")
                        tcPr.append(va)
                    va.set(qn("w:val"), "top")
                    if cel.paragraphs:
                        cel.paragraphs[-1].paragraph_format.space_after = Pt(4)
    print(f"     {numeros} células numéricas alinhadas à direita")
    return celulas



def _borda(tag: str, tamanho: int = 8) -> "OxmlElement":
    """Uma regra horizontal preta; tamanho em oitavos de ponto (8 = 1 pt)."""
    e = OxmlElement(f"w:{tag}")
    e.set(qn("w:val"), "single")
    e.set(qn("w:sz"), str(tamanho))
    e.set(qn("w:color"), "000000")
    return e


def _sem_borda(tag: str) -> "OxmlElement":
    e = OxmlElement(f"w:{tag}")
    e.set(qn("w:val"), "nil")
    return e


def bordas_da_norma(t) -> None:
    """Superior e inferior no cabeçalho, inferior no fim da tabela.

    Sem bordas internas nem externas (item 15.2). É o desenho do booktabs, que
    o pandoc descartou na conversão.
    """
    # zera tudo no nível da tabela
    pr = t._tbl.tblPr
    for antigo in pr.findall(qn("w:tblBorders")):
        pr.remove(antigo)
    b = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b.append(_sem_borda(lado))
    pr.append(b)

    def _cel_borda(cel, cima=None, baixo=None):
        tcPr = cel._tc.get_or_add_tcPr()
        for antigo in tcPr.findall(qn("w:tcBorders")):
            tcPr.remove(antigo)
        tb = OxmlElement("w:tcBorders")
        tb.append(_borda("top", cima) if cima else _sem_borda("top"))
        tb.append(_sem_borda("left"))
        tb.append(_borda("bottom", baixo) if baixo else _sem_borda("bottom"))
        tb.append(_sem_borda("right"))
        tcPr.append(tb)

    if not t.rows:
        return
    for cel in t.rows[0].cells:                      # cabeçalho: traço acima e abaixo
        _cel_borda(cel, cima=8, baixo=6)
    for cel in t.rows[-1].cells:                     # fim da tabela: traço abaixo
        _cel_borda(cel, baixo=8)

    # cabeçalho repetido quando a tabela atravessa páginas
    trPr = t.rows[0]._tr.get_or_add_trPr()
    if not trPr.findall(qn("w:tblHeader")):
        h = OxmlElement("w:tblHeader")
        h.set(qn("w:val"), "true")
        trPr.append(h)


RE_NUMERO = re.compile(r"^\s*[−-]?[\d.]+(,\d+)?\s*%?\s*(\(.*\))?\s*$")


def alinhar_numeros(t) -> int:
    """Números à direita nas colunas de dados; a primeira coluna fica à
    esquerda e o cabeçalho, centralizado (norma, item 15.2)."""
    n = 0
    for i, linha in enumerate(t.rows):
        for j, cel in enumerate(linha.cells):
            for par in cel.paragraphs:
                if i == 0:
                    par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif j == 0:
                    par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
                elif RE_NUMERO.match(par.text):
                    par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    n += 1
                else:
                    # à esquerda: justificado numa célula estreita abria buracos entre palavras
                    par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    return n



# janela do texto: A4 (21 cm) menos as margens de 2,5 cm de cada lado
JANELA_CM = 16.0


def manter_inteira(t, max_linhas: int = 30) -> None:
    """Tabela curta não se parte entre páginas, e nenhuma linha se parte ao meio.

    Cada linha fica presa à seguinte (keep with next) e a última, à Fonte. As longas
    podem atravessar a página, com o cabeçalho repetido (bordas_da_norma).
    """
    curta = len(t.rows) <= max_linhas
    for linha in t.rows:
        trPr = linha._tr.get_or_add_trPr()
        if not trPr.findall(qn("w:cantSplit")):
            trPr.append(OxmlElement("w:cantSplit"))
        if curta:
            for cel in linha.cells:
                for par in cel.paragraphs:
                    par.paragraph_format.keep_with_next = True


def ajustar_larguras(t, tam: float = 11) -> None:
    """Reparte a largura entre as colunas conforme o conteúdo.

    A medida é o comprimento típico da célula (percentil alto, não o máximo,
    para uma única célula comprida não dominar), com piso e teto para nenhuma
    coluna sumir nem engolir a tabela.
    """
    n_col = len(t.columns)
    if not n_col:
        return

    larguras = []
    for j in range(n_col):
        comprimentos = []
        for linha in t.rows:
            try:
                cel = linha.cells[j]
            except IndexError:
                continue
            maior_palavra = max((len(w) for w in cel.text.split()), default=0)
            comprimentos.append(max(len(cel.text), maior_palavra))
        comprimentos.sort()
        if not comprimentos:
            larguras.append(1.0)
            continue
        # percentil 80: ignora a célula excepcional sem ignorar o conteúdo real
        tipico = comprimentos[min(int(len(comprimentos) * 0.8), len(comprimentos) - 1)]
        larguras.append(max(tipico, 4))

    # piso por coluna: a maior palavra tem de caber inteira (Arial ~0,5 em por caractere
    # + margens da célula); senão o Word a parte ao meio ("Qua/ntil", "Predeterminado/s";
    # 0,5 em ainda partia: minúsculas do Arial têm ~0,55 em)
    cm_por_car = 0.58 * tam * 0.03528
    piso_cm = []
    for j in range(n_col):
        palavra = 0
        for linha in t.rows:
            try:
                palavra = max(palavra, max((len(w) for w in linha.cells[j].text.split()),
                                           default=0))
            except IndexError:
                continue
        piso_cm.append(palavra * cm_por_car + 0.45)

    total = sum(larguras)
    # piso maior: com 0,055 da janela (~0,9 cm) um número de três casas não cabia
    minimo, maximo = 0.07, 0.42             # fração da janela
    fracoes = []
    for w in larguras:
        fracoes.append(min(max(w / total, minimo), maximo))
    soma = sum(fracoes)
    fracoes = [f / soma for f in fracoes]    # renormaliza depois do corte
    # garante o piso da palavra, tirando a diferença das colunas com folga; se nem a
    # soma dos pisos cabe na janela, reparte proporcionalmente a eles
    if sum(piso_cm) >= JANELA_CM:
        fracoes = [c / sum(piso_cm) for c in piso_cm]
    for _ in range(3):
        falta = sum(max(piso_cm[j] / JANELA_CM - f, 0) for j, f in enumerate(fracoes))
        if falta <= 1e-6:
            break
        folga = {j: f - piso_cm[j] / JANELA_CM for j, f in enumerate(fracoes)
                 if f > piso_cm[j] / JANELA_CM}
        tot_folga = sum(folga.values())
        if tot_folga <= 0:
            break
        fracoes = [max(f, piso_cm[j] / JANELA_CM) if j not in folga
                   else f - falta * folga[j] / tot_folga for j, f in enumerate(fracoes)]

    t.autofit = False
    for j, f in enumerate(fracoes):
        largura = Cm(JANELA_CM * f)
        t.columns[j].width = largura
        for linha in t.rows:                 # o Word respeita a largura da célula
            try:
                linha.cells[j].width = largura
            except IndexError:
                continue



CURSO = "Data Science e Analytics"
ANO_DEFESA = "2026"


def preencher_cabecalho(doc) -> int:
    """Troca as lacunas do cabeçalho do template pelos dados do trabalho.

    O cabeçalho vem do template (com o logo do programa), mas com os campos em
    branco: "especialista em _________ (Nome do curso) – ____ (ano da defesa)".
    """
    n = 0
    for sec in doc.sections:
        for cab in (sec.header, sec.first_page_header, sec.even_page_header):
            if cab is None:
                continue
            for par in cab.paragraphs:
                if "_" not in par.text:
                    continue
                # junta tudo no primeiro run: o texto vem picado em vários
                inteiro = par.text
                inteiro = re.sub(r"_{2,}\s*\(Nome do curso\)", CURSO, inteiro)
                inteiro = re.sub(r"_{2,}\s*\(ano da defesa\)", ANO_DEFESA, inteiro)
                inteiro = re.sub(r"\s{2,}", " ", inteiro).strip()
                for i, r in enumerate(par.runs):
                    r.text = inteiro if i == 0 else ""
                    if i == 0:
                        r.font.name = FONTE_NOME
                        r.font.size = Pt(8)
                n += 1
    return n


def numero_em_todas_as_paginas(doc) -> None:
    """A contagem começa na folha de rosto (norma, item 16.1).

    O template define um rodapé próprio para a primeira página, e ele chega
    vazio; sem isso, a folha de rosto sairia sem o número 1.
    """
    for sec in doc.sections:
        sec.different_first_page_header_footer = False


LOGO = ROOT / "outputs" / "figures" / "logo_mba_usp_esalq.png"


def _tem_imagem(cabecalho) -> bool:
    """Imagem de verdade: um blip com embed, não o conector reto do template."""
    xml = cabecalho._element.xml
    return "r:embed" in xml or "<a:blip" in xml


def inserir_logo(doc) -> int:
    """Põe o logo do programa à direita do texto do cabeçalho.

    O pandoc perde a imagem do template: resta o conector reto, sem `r:embed`.
    Aqui o logo é reinserido com o relacionamento refeito, num tab à direita
    da margem — o layout do anexo da página 61.
    """
    if not LOGO.exists():
        print(f"  [AVISO] logo não encontrado em {LOGO.name}; cabeçalho sem imagem")
        return 0

    n = 0
    for sec in doc.sections:
        for cab in (sec.header, sec.first_page_header, sec.even_page_header):
            if cab is None or _tem_imagem(cab):
                continue
            par = cab.paragraphs[0] if cab.paragraphs else cab.add_paragraph()
            if not par.text.strip():
                continue
            # tab à direita, na margem: o texto fica à esquerda e o logo à direita
            pf = par.paragraph_format
            pf.tab_stops.clear_all()
            pf.tab_stops.add_tab_stop(
                sec.page_width - sec.left_margin - sec.right_margin,
                WD_TAB_ALIGNMENT.RIGHT)
            run = par.add_run("\t")
            run.add_picture(str(LOGO), height=Cm(0.9))
            n += 1
    return n


TEMPLATE = Path(r"C:\Users\user\Downloads\Template TCC - Implementação de "
                r"Algoritmo(s) de Machine Learning (251, 252) (1).docx")


def transplantar_cabecalho(caminho: Path) -> bool:
    """Copia o cabeçalho do template para dentro do .docx gerado.

    O template ancora o logo em posição absoluta (wp:anchor). O pandoc perde a
    imagem e mantém só o conector reto, e reinseri-la por tabulação não
    reproduz o layout. Copiando o XML, os relacionamentos e a mídia, o
    cabeçalho fica idêntico ao do modelo.
    """
    import shutil
    import zipfile

    if not TEMPLATE.exists():
        print("  [AVISO] template não encontrado; cabeçalho fica como veio")
        return False

    with zipfile.ZipFile(TEMPLATE) as tz:
        nomes = tz.namelist()
        hdr = next((n for n in nomes if re.fullmatch(r"word/header\d+\.xml", n)), None)
        if not hdr:
            return False
        xml_hdr = tz.read(hdr)
        rels_nome = f"word/_rels/{Path(hdr).name}.rels"
        xml_rels = tz.read(rels_nome) if rels_nome in nomes else b""
        # a mídia que o cabeçalho referencia
        alvos = re.findall(rb'Target="([^"]+)"', xml_rels)
        midia = {}
        for alvo in alvos:
            caminho_midia = "word/" + alvo.decode().lstrip("./")
            if caminho_midia in nomes:
                midia[caminho_midia] = tz.read(caminho_midia)

    # texto do cabeçalho com os campos preenchidos
    texto = xml_hdr.decode("utf-8")
    texto = re.sub(r"_{3,}\s*", "", texto)
    texto = texto.replace("(Nome do curso)", CURSO)
    texto = texto.replace("(ano da defesa)", ANO_DEFESA)
    xml_hdr = texto.encode("utf-8")

    tmp = caminho.with_suffix(".tmp.docx")
    with zipfile.ZipFile(caminho) as orig, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as novo:
        subst = {"word/header1.xml": xml_hdr,
                 "word/_rels/header1.xml.rels": xml_rels}
        subst.update(midia)
        for item in orig.infolist():
            dados = subst.pop(item.filename, None)
            novo.writestr(item, dados if dados is not None else orig.read(item.filename))
        for nome, dados in subst.items():          # mídia que ainda não existia
            novo.writestr(nome, dados)
    shutil.move(str(tmp), str(caminho))
    return True


# blocos que a norma manda começar em página nova (item 16 e anexos)
INICIAM_PAGINA = ("Racismo estrutural no mercado de trabalho brasileiro",
                  "Structural racism in the Brazilian labour market")


def quebras_de_pagina(doc) -> int:
    """Insere as quebras que a conversão perdeu.

    O \\newpage do LaTeX não sobrevive ao pandoc: o .docx chegava sem nenhuma
    quebra, e o Resumo subia para a folha de rosto.
    """
    n = 0
    vistos = 0
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t.startswith(INICIAM_PAGINA):
            continue
        vistos += 1
        if vistos == 1:                 # o da folha de rosto não leva quebra
            continue
        if p.runs and "w:br" in p.runs[0]._element.xml:
            continue
        r = p.runs[0] if p.runs else p.add_run()
        r._element.insert(0, _quebra_xml())
        n += 1
    return n


def _quebra_xml():
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    return br

def main() -> int:
    if not ALVO.exists():
        print(f"ERRO: {ALVO.name} não existe — rode antes gerar_tcc_normas_docx.py")
        return 1
    doc = Document(str(ALVO))

    # estilo base, para o que não for tocado parágrafo a parágrafo
    normal = doc.styles["Normal"]
    normal.font.name = FONTE_NOME
    normal.font.size = Pt(FONTE_PT)

    for s in doc.sections:
        s.top_margin = s.bottom_margin = Cm(2.5)
        s.left_margin = s.right_margin = Cm(2.5)

    cab = preencher_cabecalho(doc)
    quebras = quebras_de_pagina(doc)
    numero_em_todas_as_paginas(doc)
    corpo, legendas = formatar_corpo(doc)
    print(f"     {formatar_capa(doc)} parágrafos da folha de rosto/resumo ajustados")
    print(f"     {formatar_notas(doc)} notas de tabela/figura em corpo de nota")
    print(f"     {siglas_em_colchetes(doc)} siglas definidas entre colchetes")
    print(f"     {numerar_equacoes(doc)} equações com número no fim da linha")
    movidos, pontos = titulos_concisos(doc)
    print(f"     {movidos} títulos de tabela encurtados (explicação → Nota); "
          f"{pontos} pontos finais retirados de títulos, Fontes e Notas")
    celulas = formatar_tabelas(doc)
    n_notas = chamadas_de_nota(doc)
    print(f"     {n_notas} chamadas de nota de rodapé em sobrescrito")
    print(f"     {notas_de_rodape_9(doc)} trechos de nota de rodapé em Arial 9")

    try:
        doc.save(str(ALVO))
    except PermissionError:
        print(f"ERRO: {ALVO.name} está aberto no Word — feche e rode de novo.")
        return 1

    print(f"OK -> {ALVO.relative_to(ROOT)}")
    if transplantar_cabecalho(ALVO):
        print("     cabeçalho e logo transplantados do template oficial")
    if exportar_pdf():
        print(f"     PDF de entrega exportado do próprio Word -> {ALVO.with_suffix('.pdf').name}")
    print(f"     {quebras} quebra(s) de página inserida(s); numeração desde a "
          f"folha de rosto")
    print(f"     {corpo} parágrafos de corpo (Arial 11, 1,5, recuo 1,25 cm, "
          f"justificado)")
    print(f"     {legendas} legendas/fontes (simples, sem recuo)")
    print(f"     {celulas} células de tabela (simples, sem negrito)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
