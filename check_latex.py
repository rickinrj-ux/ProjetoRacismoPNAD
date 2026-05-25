"""Validação estrutural do arquivo LaTeX relatorio_tcc.tex."""
import re, os, sys
from collections import Counter

with open("relatorio_tcc.tex", encoding="utf-8") as f:
    content = f.read()
    lines = content.splitlines()

errors = []
warnings = []

# 1. Ambientes begin/end balanceados
begins = re.findall(r'\\begin\{(\w+)\}', content)
ends   = re.findall(r'\\end\{(\w+)\}', content)
bc, ec = Counter(begins), Counter(ends)
for env in sorted(set(list(bc.keys()) + list(ec.keys()))):
    if bc[env] != ec[env]:
        errors.append(f"  Ambiente nao balanceado: {env}  begins={bc[env]}  ends={ec[env]}")

# 2. Chaves não balanceadas
depth = 0
for i, line in enumerate(lines, 1):
    clean = re.sub(r'(?<!\\)%.*', '', line)
    for ch in clean:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
    if depth < 0:
        errors.append(f"  Chave fechando sem abertura na linha {i}: {line.strip()[:80]}")
        depth = 0
if depth != 0:
    errors.append(f"  {depth} chave(s) nao fechada(s) no final do arquivo")

# 3. \ref sem \label
defined_labels = set(re.findall(r'\\label\{([^}]+)\}', content))
used_refs = set(re.findall(r'\\(?:ref|pageref)\{([^}]+)\}', content))
for r in sorted(used_refs - defined_labels):
    warnings.append(f"  \\ref sem \\label: {r}")

# 4. citações sem entrada .bib
bib_keys = set()
if os.path.exists("relatorio_tcc.bib"):
    bib_keys = set(re.findall(r'@\w+\{(\w+),', open("relatorio_tcc.bib", encoding="utf-8").read()))
used_cites = set()
for m in re.finditer(r'\\cite[tp]?\{([^}]+)\}', content):
    for key in m.group(1).split(','):
        used_cites.add(key.strip())
for c in sorted(used_cites - bib_keys):
    warnings.append(f"  Citacao sem .bib: {c}")

# 5. \input arquivos ausentes
for m in re.finditer(r'\\input\{([^}]+)\}', content):
    path = m.group(1).replace('../', '')
    if not os.path.exists(path) and not os.path.exists(path + '.tex'):
        warnings.append(f"  \\input ausente: {m.group(1)}")

# 6. \includegraphics arquivos ausentes
for m in re.finditer(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', content):
    base = m.group(1).replace('../', '')
    found = any(os.path.exists(base + ext) for ext in ['', '.png', '.pdf', '.jpg', '.eps'])
    if not found:
        warnings.append(f"  \\includegraphics ausente: {m.group(1)}")

# 7. Pacotes necessários para comandos usados
pkg_checks = {
    r'\\checkmark': 'amssymb',
    r'\\toprule|\\midrule|\\bottomrule': 'booktabs',
    r'\\multirow': 'multirow',
}
loaded_pkgs = set(re.findall(r'\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}', content))
for pattern, pkg in pkg_checks.items():
    if re.search(pattern, content) and pkg not in ' '.join(loaded_pkgs):
        errors.append(f"  Comando requer pacote nao carregado: {pkg}")

print("=== ERROS ===")
print('\n'.join(errors) if errors else "  Nenhum erro estrutural.")

print("\n=== AVISOS ===")
print('\n'.join(warnings) if warnings else "  Nenhum aviso.")

print(f"\n=== ESTATISTICAS ===")
print(f"  Linhas: {len(lines)}")
print(f"  Labels definidos: {len(defined_labels)}")
print(f"  Refs usadas: {len(used_refs)}")
print(f"  Citacoes usadas: {len(used_cites)}")
print(f"  Entradas .bib: {len(bib_keys)}")
