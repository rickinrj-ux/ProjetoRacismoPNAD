"""
descopar_entregavel.py
=====================
Remove blocos de slide/seção de ESCOPO ESTENDIDO dos geradores de entregáveis
(pptx/docx), alinhando-os ao núcleo de 4. Opera sobre blocos delimitados por
banners de comentário `# ═══...` (3 linhas: ═══ / título / ═══), preservando o
preâmbulo e o rodapé/save. Não toca no gerador do relatório.

Uso:
    python tcc/scripts/descopar_entregavel.py <arquivo.py> [--apply]

Sem --apply: dry-run (lista blocos mantidos/removidos). Com --apply: reescreve o
arquivo (backup .bak) e valida com py_compile.

As palavras-chave de remoção estão em PARKED (parqueados). Blocos de síntese/
implicações/conclusão NÃO são removidos (reescritos à mão depois).
"""
import sys, re, py_compile
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PARKED = [
    "TENDÊNCIA TEMPORAL", "TENDENCIA TEMPORAL", "HECKMAN", "EVENT STUDY",
    "CLUSTERING", "K-MEANS", "KMEANS",
    " SNA", "REDES SOCIAIS", "BETWEENNESS", "CAPITAL SOCIAL",
    "ESTADO E DESIGUALDADE", "RENDA REAL", "ARMADILHA", "SETOR PÚBLICO",
    "PESQUISA OPERACIONAL", "PO REGIONAL", "PO:", "TOPSIS", "FOCALIZAÇÃO",
    "RANDOM SLOPE", "INTERSECCIONALIDADE GLMM", "GRUPO_RG", "SEGREGAÇÃO ESPACIAL",
    # títulos específicos das apresentações executivas
    "REDES E DISCRIMINA", "REDE QUE EXCLUI", "ESTADO AJUDA", "RACISMO TEM ENDERE",
    "VARIAÇÃO ENTRE ESTADOS",
    # títulos de figuras parqueadas (guia de estudo, docx)
    "REDE SOCIAL", "GINI POR SETOR", "POR SETOR (H2", "SIMULAÇÃO DE INCLUSÃO",
    "(H1)", "(H4)", "(H5", "ESTADO COMO INDUTOR", "INCLINAÇÃO ALEATÓRIA",
    "HETEROGENEIDADE GEOGRÁFICA", "FOCALIZAÇÃO TERRITORIAL",
]
# Banners cujo título contém estes termos NÃO são removidos (reescrita manual):
KEEP_OVERRIDE = ["TRIÂNGULO", "SÍNTESE", "IMPLICAÇÕES", "CONCLUSÃO", "LIMITAÇÕES",
                 "INTERSECCIONALIDADE OB", "4 GRUPOS"]

BANNER = re.compile(r"^#\s*[═=]{10,}\s*$")
# blocos de seção em docx: add_heading(doc, "Titulo", level=2)  (figuras/subseções)
HEADING = re.compile(r'add_heading\(\s*doc\s*,\s*[fr]?"([^"]+)"[^)]*level\s*=\s*2')


def parse_blocks(lines):
    """Retorna (blocos, idx_primeiro). Um bloco começa num banner ═══ (3 linhas)
    OU num add_heading(...,level=2); vai até o próximo começo de bloco."""
    starts = []  # (idx, titulo)
    i = 0
    n = len(lines)
    while i < n:
        if i + 2 < n and BANNER.match(lines[i]) and lines[i + 1].startswith("#") and BANNER.match(lines[i + 2]):
            starts.append((i, lines[i + 1].lstrip("# ").strip().upper()))
            i += 3
            continue
        m = HEADING.search(lines[i])
        if m:
            starts.append((i, m.group(1).strip().upper()))
        i += 1
    blocks = []
    for k, (s, t) in enumerate(starts):
        e = starts[k + 1][0] if k + 1 < len(starts) else n
        blocks.append((s, e, t))
    return blocks, (starts[0][0] if starts else n)


def is_parked(titulo):
    if any(k in titulo for k in KEEP_OVERRIDE):
        return False
    return any(k in titulo for k in PARKED)


def main():
    if len(sys.argv) < 2:
        sys.exit("uso: descopar_entregavel.py <arquivo.py> [--apply]")
    path = Path(sys.argv[1])
    apply = "--apply" in sys.argv
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    blocks, first = parse_blocks(lines)
    if not blocks:
        sys.exit(f"[{path.name}] nenhum bloco de banner ═══ encontrado.")

    keep_mask = [not is_parked(t) for (_, _, t) in blocks]
    print(f"=== {path.name} === ({len(blocks)} blocos)")
    for (s, e, t), keep in zip(blocks, keep_mask):
        print(f"  [{'KEEP' if keep else 'DROP'}] L{s+1:<5} {t[:60]}")
    n_drop = keep_mask.count(False)
    print(f"  -> {n_drop} blocos a remover")

    if not apply:
        print("  (dry-run; use --apply para reescrever)")
        return

    out = lines[:first]  # preâmbulo
    # adiciona blocos mantidos; o último bloco mantido carrega seu rodape/save
    for (s, e, t), keep in zip(blocks, keep_mask):
        if keep:
            out.extend(lines[s:e])
    path.with_suffix(".py.bak").write_text("".join(lines), encoding="utf-8")
    path.write_text("".join(out), encoding="utf-8")
    try:
        py_compile.compile(str(path), doraise=True)
        print(f"  APLICADO + compila OK. Backup: {path.name}.bak")
    except py_compile.PyCompileError as ex:
        path.write_text("".join(lines), encoding="utf-8")
        print(f"  [ERRO] não compila — revertido. {ex}")


if __name__ == "__main__":
    main()
