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


SECOES = {"Resumo", "Abstract", "Introdução", "Conclusão", "Referências",
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


def chamadas_de_nota(doc: Document) -> int:
    """Chamada de nota de rodapé em sobrescrito. O pandoc usa o estilo de caractere
    'Footnote Reference', que o template oficial não define como sobrescrito: a chamada
    saía colada ao número no corpo do texto ("0,697" + nota 14 = "0,69714")."""
    from docx.oxml.ns import qn
    n = 0
    corpo = doc.element.body
    for r in corpo.iter(qn("w:r")):
        if r.find(qn("w:footnoteReference")) is not None:
            rpr = r.get_or_add_rPr()
            va = rpr.find(qn("w:vertAlign"))
            if va is None:
                va = OxmlElement("w:vertAlign")
                rpr.append(va)
            va.set(qn("w:val"), "superscript")
            n += 1
    return n


def formatar_tabelas(doc: Document) -> int:
    """Arial 11, espaçamento simples e sem negrito — o manual proíbe realce
    em negrito e código de cores nas tabelas (item 15.2)."""
    celulas = 0
    numeros = 0
    for t in doc.tables:
        bordas_da_norma(t)
        ajustar_larguras(t)
        numeros += alinhar_numeros(t)
        # Fonte da tabela conforme o número de colunas. Em Arial 11 fixo, as tabelas de
        # 7 a 10 colunas quebravam os números dentro da célula ("0,/83/0", "Qua/ntil");
        # o PDF de entrega já usa fonte menor nessas tabelas. CONFIRMAR com o orientador
        # se o manual admite tamanho menor que 11 em tabela.
        n_col = len(t.columns)
        tam = 11 if n_col <= 4 else 10 if n_col <= 6 else 9 if n_col <= 8 else 8
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



# janela do texto: A4 (21 cm) menos as margens de 2,5 cm de cada lado
JANELA_CM = 16.0


def ajustar_larguras(t) -> None:
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

    total = sum(larguras)
    # piso maior: com 0,055 da janela (~0,9 cm) um número de três casas não cabia
    minimo, maximo = 0.07, 0.42             # fração da janela
    fracoes = []
    for w in larguras:
        fracoes.append(min(max(w / total, minimo), maximo))
    soma = sum(fracoes)
    fracoes = [f / soma for f in fracoes]    # renormaliza depois do corte

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
    celulas = formatar_tabelas(doc)
    n_notas = chamadas_de_nota(doc)
    print(f"     {n_notas} chamadas de nota de rodapé em sobrescrito")

    try:
        doc.save(str(ALVO))
    except PermissionError:
        print(f"ERRO: {ALVO.name} está aberto no Word — feche e rode de novo.")
        return 1

    print(f"OK -> {ALVO.relative_to(ROOT)}")
    if transplantar_cabecalho(ALVO):
        print("     cabeçalho e logo transplantados do template oficial")
    print(f"     {quebras} quebra(s) de página inserida(s); numeração desde a "
          f"folha de rosto")
    print(f"     {corpo} parágrafos de corpo (Arial 11, 1,5, recuo 1,25 cm, "
          f"justificado)")
    print(f"     {legendas} legendas/fontes (simples, sem recuo)")
    print(f"     {celulas} células de tabela (simples, sem negrito)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
