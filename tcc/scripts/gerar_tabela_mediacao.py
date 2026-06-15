"""
gerar_tabela_mediacao.py
=======================
Tabela-resultado HEADLINE do TCC: decomposição/mediação do gap salarial racial
ao longo dos modelos HLM (M1->M4), pedido do orientador ("resultados em tabelas").

Fonte: outputs/tables/gap_decomposicao_serie_completo.csv
Saída: outputs/tables/gap_mediacao_tcc.tex  (label tab:mediacao)
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
d = pd.read_csv(T / "gap_decomposicao_serie_completo.csv")

CONTROLES = {
    "M1_Individual": "Individual (educ., idade, sexo)",
    "M2_Localidade": "+ contexto da UPA (vizinhança)",
    "M3_Completo":   "+ efeito de UF (estado)",
    "M4_Ocupacao":   "+ ocupação e formalidade",
}

def med(v):
    return "---" if pd.isna(v) else fmt(v, 1)

linhas = []
for _, r in d.iterrows():
    linhas.append(
        f"{CONTROLES.get(r['Modelo'], r['Modelo'])} & {fmt(r['b_negro'],4)} "
        f"& {fmt(r['Gap%'],1)} & {med(r['Mediacao_total%'])} \\\\")

tex = (r"""\begin{table}[!ht]
\centering
\caption{Decomposição do gap salarial racial por mediação contextual e ocupacional
(modelos HLM de três níveis, PNAD Contínua 2016--2025, população completa). Cada linha
acrescenta um bloco de controles ao anterior; à medida que se adiciona contexto e ocupação,
o gap encolhe e a mediação acumulada cresce.}
\label{tab:mediacao}
\begin{tabular}{lrrr}
\toprule
Modelo (controles acumulados) & $\beta_{\text{negro}}$ & Gap (\%) & Mediação acum. (\%) \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\par\smallskip
\footnotesize\emph{Como ler:} cada linha adiciona controles à anterior. $\beta_{\text{negro}}$
é a penalidade racial em log-rendimento (mais próximo de zero = menor gap); ``Gap (\%)'' é a
penalidade em \% de renda; ``Mediação acum.''\ é a fração do gap bruto (M1) já explicada pelos
controles. Do M1 ao M4 o gap cai de $-19{,}1\%$ para $-6{,}2\%$: $69{,}8\%$ do gap é mediado por
onde a pessoa mora e qual ocupação acessa --- e o residual de $-6{,}2\%$ persiste após todos os
controles observáveis.
\end{table}
""")
out = T / "gap_mediacao_tcc.tex"
out.write_text(tex, encoding="utf-8")
print(f"OK -> {out}")
print(d.to_string(index=False))
