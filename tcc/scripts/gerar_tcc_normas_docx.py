# -*- coding: utf-8 -*-
"""
gerar_tcc_normas_docx.py
========================
Converte `tcc_normas.tex` em .docx usando o **template oficial do MBA USP/Esalq**
como `--reference-doc`: os estilos (Arial 11, margens de 2,5 cm, cabeçalho,
entrelinha 1,5) vêm do template, e o conteúdo vem do nosso LaTeX.

É o que torna desnecessário refazer à mão os 331 ajustes de forma que o
formatador do Sistema de TCC havia aplicado: eles passam a ser propriedade do
template, e o documento pode ser regerado quantas vezes for preciso.

Saída: entregaveis/TCC_Ricardo_Calheiros_MBA_USP_Esalq.docx
Uso:   python tcc/scripts/gerar_tcc_normas_docx.py
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
TEX = ROOT / "tcc_normas.tex"
BIB = ROOT / "relatorio_tcc.bib"
CSL = Path(__file__).with_name("abnt.csl")
SAIDA = ROOT / "entregaveis" / "TCC_Ricardo_Calheiros_MBA_USP_Esalq.docx"

# o template oficial serve de referência de estilos para o pandoc
TEMPLATES = [
    Path(r"C:\Users\user\Downloads\Template TCC - Implementação de Algoritmo(s)"
         r" de Machine Learning (251, 252) (1).docx"),
    Path(r"C:\Users\user\Downloads\Template TCC_PT (251, 252).docx"),
]


def normalizar(texto: str) -> str:
    """Prepara o LaTeX para o pandoc, como no gerador do relatório."""
    texto = re.sub(r"\\nocite\{[^}]*\}", "", texto)
    texto = re.sub(r"\\cite(online|author)\b", r"\\citet", texto)
    texto = re.sub(r"\\cite(year|yearpar)\b", r"\\citeyear", texto)
    texto = re.sub(r"\\cite(?![a-zA-Z])", r"\\citep", texto)

    # \resizebox sobrevive mal: o pandoc descarta a tabela inteira
    padrao = re.compile(r"\\resizebox\{[^{}]*\}\{[^{}]*\}\{%?[ \t]*\n?")
    while (m := padrao.search(texto)):
        i, nivel = m.end(), 1
        while i < len(texto) and nivel:
            if texto[i] == "{":
                nivel += 1
            elif texto[i] == "}":
                nivel -= 1
            i += 1
        texto = texto[:m.start()] + texto[m.end():i - 1] + texto[i:]

    # subfigure vira só a imagem (senão o pandoc cria uma tabela em volta)
    def _sub(m: re.Match) -> str:
        img = re.search(r"\\includegraphics(?:\[[^\]]*\])?\{[^}]+\}", m.group(1))
        return img.group(0) if img else ""

    texto = re.sub(r"\\begin\{subfigure\}(?:\[[^\]]*\])?\{[^}]*\}(.*?)\\end\{subfigure\}",
                   _sub, texto, flags=re.S)

    # \paragraph vira cabeçalho numerado no Word; no PDF é título corrido
    texto = re.sub(r"\\paragraph\*?\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}",
                   r"\\textbf{\1}", texto)

    texto = re.sub(r"\\noindent\\rule\{[^}]*\}\{[^}]*\}", "", texto)
    texto = re.sub(r"\\vspace\*?\{[^}]*\}|\\hspace\*?\{[^}]*\}", "", texto)

    # caminhos das figuras (o \graphicspath não viaja para o pandoc)
    def _fig(m: re.Match) -> str:
        opts, nome = m.group(1) or "", m.group(2)
        if "/" not in nome:
            nome = f"outputs/figures/{nome}"
        if not Path(nome).suffix:
            for ext in (".png", ".pdf", ".jpg"):
                if (ROOT / (nome + ext)).exists():
                    nome += ext
                    break
        return f"\\includegraphics{opts}{{{nome}}}"

    return re.sub(r"\\includegraphics(\[[^\]]*\])?\{([^}]+)\}", _fig, texto)


def main() -> int:
    try:
        import pypandoc
    except ImportError:
        print("ERRO: pypandoc não instalado (pip install pypandoc_binary)")
        return 1
    if not TEX.exists():
        print(f"ERRO: {TEX.name} não existe — rode antes gerar_tcc_normas.py")
        return 1

    texto = normalizar(TEX.read_text(encoding="utf-8"))
    with tempfile.NamedTemporaryFile("w", suffix=".tex", delete=False,
                                     encoding="utf-8", dir=str(ROOT)) as fh:
        fh.write(texto)
        tmp = Path(fh.name)

    args = ["--from=latex", "--to=docx", f"--resource-path={ROOT}",
            "--wrap=preserve"]
    ref = next((t for t in TEMPLATES if t.exists()), None)
    if ref:
        args.append(f"--reference-doc={ref}")
        print(f"estilos do template: {ref.name}")
    else:
        print("  [AVISO] template oficial não encontrado; estilos padrão do pandoc")
    if BIB.exists():
        args += ["--citeproc", f"--bibliography={BIB}"]
        if CSL.exists():
            args.append(f"--csl={CSL}")

    SAIDA.parent.mkdir(exist_ok=True)
    try:
        print("Convertendo com pandoc…")
        pypandoc.convert_file(str(tmp), "docx", format="latex",
                              outputfile=str(SAIDA), extra_args=args)
    except Exception as e:
        print(f"ERRO na conversão: {e}")
        return 1
    finally:
        tmp.unlink(missing_ok=True)

    from docx import Document
    doc = Document(str(SAIDA))
    imagens = sum(1 for r in doc.part.rels.values() if "image" in r.reltype)
    print(f"\nOK -> {SAIDA.relative_to(ROOT)}  ({SAIDA.stat().st_size // 1024} KB)")
    print(f"     {len([p for p in doc.paragraphs if p.text.strip()])} parágrafos, "
          f"{len(doc.tables)} tabelas, {imagens} imagens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
