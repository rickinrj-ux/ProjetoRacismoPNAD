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
# Bloco 3: fonte = HLM step-up (indivíduo em UPA, UF fixo); fallback = série antiga
if (T / "gap_decomposicao_stepup.csv").exists():
    import numpy as np
    d = pd.read_csv(T / "gap_decomposicao_stepup.csv")
    d["Modelo"] = d["Modelo"].map({"M1": "M1_Individual", "M2": "M2_Localidade",
                                   "M3": "M3_Completo", "M4": "M4_Ocupacao"})
    # linha 0: gap agregado (OLS com efeitos fixos de UF, sem efeito de bairro) — mesma base
    # de controles do M1; a mediação acumulada é medida em relação a ele
    se = pd.read_csv(T / "hlm_serie_completo_se.csv")
    bp = float(se.loc[(se["modelo"] == "M1_Individual_OLS") & (se["variavel"] == "negro"), "coef"].iloc[0])
    pool = pd.DataFrame([{"Modelo": "M0_Agregado", "b_negro": bp, "Gap%": (np.exp(bp) - 1) * 100}])
    d = pd.concat([pool, d], ignore_index=True)
    d["Mediacao_total%"] = (abs(bp) - d["b_negro"].abs()) / abs(bp) * 100
    d.loc[0, "Mediacao_total%"] = np.nan
else:
    d = pd.read_csv(T / "gap_decomposicao_serie_completo.csv")

CONTROLES = {
    "M0_Agregado":   "Agregado: individual + UF, sem efeito de bairro (OLS)",
    "M1_Individual": "M1: + intercepto aleatório de bairro (UPA)",
    "M2_Localidade": "M2: + contexto do bairro (UPA)",
    "M3_Completo":   "M3: + efeitos fixos de UF (gap líquido)",
    "M4_Ocupacao":   "M4: + ocupação e formalidade (limite inferior)",
}

def med(v):
    return "---" if pd.isna(v) else fmt(v, 1)

linhas = []
for _, r in d.iterrows():
    linhas.append(
        f"{CONTROLES.get(r['Modelo'], r['Modelo'])} & {fmt(r['b_negro'],4)} "
        f"& {fmt(r['Gap%'],1)} & {med(r['Mediacao_total%'])} \\\\")

g1 = float(d.loc[d["Modelo"] == d["Modelo"].iloc[0], "Gap%"].iloc[0])
g4 = float(d.loc[d["Modelo"] == "M4_Ocupacao", "Gap%"].iloc[0])
m4 = float(d.loc[d["Modelo"] == "M4_Ocupacao", "Mediacao_total%"].iloc[0])
tex = (r"""\begin{table}[!ht]
\centering
\caption{Decomposição do gap salarial racial por mediação contextual e ocupacional
(HLM de dois níveis, indivíduos em UPA, com efeitos fixos de UF; PNAD Contínua
2016--2025, população completa). Cada linha
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
\footnotesize\emph{Como ler:} cada linha adiciona algo à anterior. $\beta_{\text{negro}}$
é a penalidade racial em log-rendimento (mais próximo de zero = menor gap); ``Gap (\%)'' é a
penalidade em \% de renda; ``Mediação acum.''\ é a fração do gap agregado (primeira linha) já
explicada. O salto da primeira para a segunda linha é a mediação pela segregação residencial:
comparar negros e brancos \emph{do mesmo bairro} reduz o gap quase à metade. Do M1 ao M4 o gap cai de {fmt(abs(g1),1)}\% para {fmt(abs(g4),1)}\%: {fmt(m4,1)}\% do gap é mediado por
onde a pessoa mora, o estado e a ocupação que acessa --- e a penalidade de {fmt(abs(g4),1)}\% persiste
dentro da mesma ocupação (limite inferior, pois a ocupação é ela própria resultado da barreira de acesso).
\end{table}
""")
out = T / "gap_mediacao_tcc.tex"
out.write_text(tex, encoding="utf-8")
print(f"OK -> {out}")
print(d.to_string(index=False))
