import sys; sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\user\Documents\ProjetoRacismoPNAD\gerar_apresentacao_pptx.py', encoding='utf-8') as f:
    code = f.read()

pairs = [
    ('footer(s, 10)\n\n# ══', 'footer(s, 12)\n\n# ══'),
    ('footer(s, 11)\n\n# ══', 'footer(s, 13)\n\n# ══'),
    ('footer(s, 12)\n\n# ══', 'footer(s, 14)\n\n# ══'),
    ('footer(s, 13)\n\n# ══', 'footer(s, 15)\n\n# ══'),
    ('footer(s, 14)\n\n# ══', 'footer(s, 16)\n\n# ══'),
    ('footer(s, 15)\n\n# ══', 'footer(s, 17)\n\n# ══'),
    ('footer(s, 16)\n\n# ══', 'footer(s, 18)\n\n# ══'),
    ('footer(s, 17)\n\n# ══', 'footer(s, 19)\n\n# ══'),
]

for old, new in pairs:
    n = code.count(old)
    code = code.replace(old, new)
    print(f'{old[:25]!r} -> {new[:25]!r}  ({n}x)')

with open(r'C:\Users\user\Documents\ProjetoRacismoPNAD\gerar_apresentacao_pptx.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('OK')
