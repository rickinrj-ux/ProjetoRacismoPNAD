"""
_descopar_word_ranges.py  (one-off)
Remove as subseções parqueadas do gerar_relatorio_word.py por FAIXAS DE LINHA
calculadas sobre o arquivo ORIGINAL (deletadas em uma única passada, para não
deslocar índices). Backup .bak. Faixas em (inicio, fim) 1-based, [inicio, fim).
"""
import sys, py_compile
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ALVO = Path("scripts/geradores/gerar_relatorio_word.py")
# (inicio, fim) 1-based; remove linhas inicio..fim-1
RANGES = [
    (887, 898),    # 2.5 SNA (lit)
    (1182, 1197),  # 3.4 Clustering
    (1206, 1221),  # 3.6 SNA
    (1247, 1270),  # 3.8 Segregação espacial
    (1759, 2009),  # 4.1c-4.1f random slope / PO regional / setor-gênero (mantém 4.1g)
    (2039, 2114),  # 4.2 Clustering
    (2217, 2275),  # 4.4 SNA
    (2562, 2631),  # Segregação espacial (resultados)
    (3183, 3231),  # 4.14 Heckman/temporal/COVID
    (3351, 3481),  # bridge PO + 5.1 Pesquisa Operacional
    (3564, 3623),  # 6.3 Eixo 3 (armadilha/inclusão produtiva)
    (3807, 3957),  # page_break + Anexo A (Estado H1-H5) inteiro
]

lines = ALVO.read_text(encoding="utf-8").splitlines(keepends=True)
drop = set()
for ini, fim in RANGES:
    for ln in range(ini, fim):
        drop.add(ln - 1)  # para índice 0-based
kept = [l for i, l in enumerate(lines) if i not in drop]

ALVO.with_suffix(".py.bak").write_text("".join(lines), encoding="utf-8")
ALVO.write_text("".join(kept), encoding="utf-8")
print(f"Linhas: {len(lines)} -> {len(kept)} (removidas {len(lines)-len(kept)})")
try:
    py_compile.compile(str(ALVO), doraise=True)
    print("compila OK")
except py_compile.PyCompileError as ex:
    ALVO.write_text("".join(lines), encoding="utf-8")
    print(f"[ERRO] não compila — REVERTIDO.\n{ex}")
