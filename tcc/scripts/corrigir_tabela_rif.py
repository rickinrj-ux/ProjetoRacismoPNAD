"""
corrigir_tabela_rif.py
=====================
Perícia cruzada (F-RIF): a tabela rif_ob_decomposicao.tex exibe uma coluna
"Interação (%)" que está DUPLA-CONTADA — em src/rif_decomp.py, com referência
β_branco, tem-se end = E3 + I3 (a interação já está dentro de Dotações) e
end + ret = gap_rif. Reportar Interação à parte faz as % não somarem 100%.

Este script reconstrói a tabela do TCC a partir do CSV existente (sem re-rodar
o RIF), no formato twofold consistente: Dotações% + Retornos% = 100% (sobre
gap_rif). A narrativa sticky-floor (Retornos caindo do q10 ao q90) é preservada.

Saída: outputs/tables/rif_decomp_tcc.tex  (label tab:rif_ob)
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
d = pd.read_csv(T / "rif_ob_decomposicao.csv")

# Twofold consistente: % sobre gap_rif (end + ret == gap_rif por construção)
d["dot_pct"] = d["end"] / d["gap_rif"] * 100
d["ret_pct2"] = d["ret"] / d["gap_rif"] * 100

linhas = []
for _, r in d.iterrows():
    soma = r["dot_pct"] + r["ret_pct2"]
    assert abs(soma - 100) < 0.1, f"{r['q_label']}: soma={soma}"
    linhas.append(
        f"{r['q_label']} & {fmt(r['gap_obs'],3)} & {fmt(r['dot_pct'],1)} "
        f"& {fmt(r['ret_pct2'],1)} \\\\")

tex = (r"""\begin{table}[!ht]
\centering
\caption{Decomposição RIF-OB (Firpo, Fortin \& Lemieux, 2018) do gap salarial racial
por quantil incondicional, em formato \emph{two-fold} (referência: estrutura de preços
dos brancos). Dotações: diferença de características observáveis (capital humano, ocupação,
contexto). Retornos: parcela não explicada (componente discriminatório). Dotações + Retornos
$=100\%$ do gap em cada quantil. Padrão \emph{sticky floor}: o componente de retornos
(discriminação de mercado) é maior na base e decresce rumo ao topo. PNAD Contínua 2016--2025.}
\label{tab:rif_ob}
\begin{tabular}{lrrr}
\toprule
Quantil & Gap obs. & Dotações (\%) & Retornos (\%) \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\end{table}
""")
out = T / "rif_decomp_tcc.tex"
out.write_text(tex, encoding="utf-8")
print(f"OK -> {out}")
print(d[["q_label", "gap_obs", "dot_pct", "ret_pct2"]].round(1).to_string(index=False))
