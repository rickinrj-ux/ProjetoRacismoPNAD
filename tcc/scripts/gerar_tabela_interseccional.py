"""
gerar_tabela_interseccional.py
=============================
Tabela interseccional LIMPA (raça × gênero) para o TCC — pedido do orientador
(resultado em tabela). Substitui interseccional_coeficientes.tex, que tem
underscores crus (quebram LaTeX) e mostra coeficientes técnicos. Usa o twofold
correto (Dotações + Retornos = 100% do gap; sem a coluna 'inter' órfã — ver
PERICIA FC2) e rótulos legíveis.

Fonte: outputs/tables/interseccional_ob4grupos.csv
Saída: outputs/tables/ob_interseccional_tcc.tex  (label tab:interseccional)
"""

# --- bootstrap raiz do projeto ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import pandas as pd
from pathlib import Path
from params import fmt

T = Path("outputs/tables")
d = pd.read_csv(T / "interseccional_ob4grupos.csv")

linhas = []
for _, r in d.iterrows():
    pen = "---" if abs(r["penalidade_extra_pct"]) < 1e-6 else fmt(r["penalidade_extra_pct"], 1)
    linhas.append(
        f"{r['grupo']} & {fmt(r['gap_pct'],1)} & {fmt(r['end_pct'],1)} "
        f"& {fmt(r['ret_pct'],1)} & {pen} \\\\")

tex = (r"""\begin{table}[!ht]
\centering
\caption{Decomposição interseccional (raça $\times$ gênero) do gap de rendimento
\emph{vs.}\ o Homem Branco (grupo de referência). Dotações: parcela explicada por
características observáveis; Retornos: parcela não explicada (discriminação). Penalidade
extra: o quanto o gap da Mulher Negra excede a soma das penalidades de raça e de gênero
isoladas (efeito interseccional puro, Crenshaw, 1989). PNAD Contínua, população completa.}
\label{tab:interseccional}
\begin{tabular}{lrrrr}
\toprule
Grupo & Gap vs HB (\%) & Dotações (\%) & Retornos (\%) & Penal.\ extra (p.p.) \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\par\smallskip
\footnotesize\emph{Como ler:} ``Gap vs HB'' é a desvantagem de renda de cada grupo
\emph{vs.}\ o Homem Branco; Dotações $+$ Retornos $=100\%$ do gap. A Mulher Negra tem o
maior gap (96,4\%) e ainda uma penalidade \emph{extra} de 9,5 p.p.\ que não se reduz à
soma de ``ser negro'' e ``ser mulher'' --- a marca da interseccionalidade.
\end{table}
""")
out = T / "ob_interseccional_tcc.tex"
out.write_text(tex, encoding="utf-8")
print(f"OK -> {out}")
print(d[["grupo", "gap_pct", "end_pct", "ret_pct", "penalidade_extra_pct"]].round(1).to_string(index=False))
