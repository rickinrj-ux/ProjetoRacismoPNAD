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
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
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


def formatar_corpo(doc: Document) -> tuple[int, int]:
    corpo = legendas = 0
    for p in doc.paragraphs:
        texto = p.text.strip()
        for r in p.runs:
            _fonte_do_run(r)
        if not texto:
            continue
        pf = p.paragraph_format
        if RE_LEGENDA.match(texto) or RE_FONTE.match(texto):
            pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
            pf.first_line_indent = Cm(0)
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            # o título estava colado no parágrafo anterior; a fonte e a nota
            # seguem coladas na tabela, que é como a norma mostra
            if RE_LEGENDA.match(texto):
                pf.space_before = Pt(12)
                pf.space_after = Pt(2)
            else:
                pf.space_before = Pt(2)
                pf.space_after = Pt(12)
            legendas += 1
        elif p.style.name.startswith("Heading") or RE_META.match(texto):
            pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
            pf.first_line_indent = Cm(0)
            pf.space_before = Pt(12)
            pf.space_after = Pt(6)
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        else:
            pf.line_spacing = 1.5
            pf.first_line_indent = Cm(1.25)
            pf.space_after = Pt(0)
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            corpo += 1
    return corpo, legendas


def formatar_tabelas(doc: Document) -> int:
    """Arial 11, espaçamento simples e sem negrito — o manual proíbe realce
    em negrito e código de cores nas tabelas (item 15.2)."""
    celulas = 0
    numeros = 0
    for t in doc.tables:
        bordas_da_norma(t)
        numeros += alinhar_numeros(t)
        for linha in t.rows:
            for cel in linha.cells:
                for p in cel.paragraphs:
                    pf = p.paragraph_format
                    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
                    pf.space_after = Pt(0)
                    pf.first_line_indent = Cm(0)
                    for r in p.runs:
                        _fonte_do_run(r)
                        r.font.bold = False
                    celulas += 1
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
                    par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return n


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

    corpo, legendas = formatar_corpo(doc)
    celulas = formatar_tabelas(doc)

    try:
        doc.save(str(ALVO))
    except PermissionError:
        print(f"ERRO: {ALVO.name} está aberto no Word — feche e rode de novo.")
        return 1

    print(f"OK -> {ALVO.relative_to(ROOT)}")
    print(f"     {corpo} parágrafos de corpo (Arial 11, 1,5, recuo 1,25 cm, "
          f"justificado)")
    print(f"     {legendas} legendas/fontes (simples, sem recuo)")
    print(f"     {celulas} células de tabela (simples, sem negrito)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
