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
]
# Banners cujo título contém estes termos NÃO são removidos (reescrita manual):
KEEP_OVERRIDE = ["TRIÂNGULO", "SÍNTESE", "IMPLICAÇÕES", "CONCLUSÃO", "LIMITAÇÕES",
                 "INTERSECCIONALIDADE OB", "4 GRUPOS"]

BANNER = re.compile(r"^#\s*[═=]{10,}\s*$")


def parse_blocks(lines):
    """Retorna lista de (ini, fim, titulo) para cada bloco de banner ═══."""
    idx = []
    for i in range(len(lines) - 2):
        if BANNER.match(lines[i]) and lines[i + 1].startswith("#") and BANNER.match(lines[i + 2]):
            idx.append(i)
    blocks = []
    for k, start in enumerate(idx):
        end = idx[k + 1] if k + 1 < len(idx) else len(lines)
        titulo = lines[start + 1].lstrip("# ").strip().upper()
        blocks.append((start, end, titulo))
    return blocks, (idx[0] if idx else len(lines))


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
