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
from params import fmt, fmtN

T = Path("outputs/tables")
# Fonte: decomposição estimada na MESMA amostra do núcleo (educ dummies + educ_missing,
# população completa) por run_se_rif_interseccional.py; o csv antigo vinha do módulo que
# exige educ_ord (só ~31% da PEA) e ficava incompatível com o resto do trabalho.
_nuc = T / "interseccional_ob4grupos_nucleo.csv"
d = pd.read_csv(_nuc if _nuc.exists() else T / "interseccional_ob4grupos.csv")
_se_path = T / "interseccional_ob4grupos_se.csv"
se = pd.read_csv(_se_path).set_index("grupo") if _se_path.exists() else None


def _cel(v, g, col, dec=1):
    if se is None or g not in se.index or f"se_{col}" not in se.columns:
        return fmt(v, dec)
    return f"{fmt(v, dec)} ({fmt(float(se.loc[g, f'se_{col}']), dec)})"

linhas = []
for _, r in d.iterrows():
    pen = "---" if abs(r["penalidade_extra_pct"]) < 1e-6 else fmt(r["penalidade_extra_pct"], 1)
    g = r["grupo"]
    linhas.append(
        f"{g} & {_cel(r['gap_pct'], g, 'gap_pct')} & {_cel(r['end_pct'], g, 'end_pct')} "
        f"& {_cel(r['ret_pct'], g, 'ret_pct')} & {pen} & {fmtN(int(r['n_n']))} \\\\")

tex = (r"""\begin{table}[!ht]
\centering
\caption{Decomposição interseccional (raça $\times$ gênero) do gap de rendimento
\emph{vs.}\ o Homem Branco (grupo de referência). Dotações: parcela explicada por
características observáveis; Retornos: parcela não explicada (discriminação). Penalidade
extra: o quanto o gap da Mulher Negra excede a soma das penalidades de raça e de gênero
isoladas (efeito interseccional puro, Crenshaw, 1989). PNAD Contínua, população completa
($N$ do grupo de referência --- homens brancos --- na última linha da nota). Entre
parênteses: erro-padrão por bootstrap em blocos por UPA.}
\label{tab:interseccional}
\resizebox{\textwidth}{!}{%
\begin{tabular}{lrrrrr}
\toprule
Grupo & Gap vs HB (\%) & Dotações (\%) & Retornos (\%) & Penal.\ extra (p.p.) & $N$ do grupo \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
}
\par\smallskip
\footnotesize\emph{Como ler:} ``Gap vs HB'' é a desvantagem de renda de cada grupo
\emph{vs.}\ o Homem Branco; Dotações $+$ Retornos $=100\%$ do gap. A Mulher Negra tem o
maior gap e ainda uma penalidade \emph{extra} que não se reduz à soma de ``ser negro'' e
``ser mulher'' --- a marca da interseccionalidade. O sinal negativo das dotações da Mulher
Branca indica que suas características observáveis \emph{superam} as do homem branco: todo
o gap vem de retornos diferenciais. Grupo de referência: """ + fmtN(int(d["n_ref"].iloc[0])) + r""" homens brancos.
\end{table}
""")
out = T / "ob_interseccional_tcc.tex"
out.write_text(tex, encoding="utf-8")
print(f"OK -> {out}")
print(d[["grupo", "gap_pct", "end_pct", "ret_pct", "penalidade_extra_pct"]].round(1).to_string(index=False))
