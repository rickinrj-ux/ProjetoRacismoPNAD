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
from params import fmt, fmtN

T = Path("outputs/tables")
d = pd.read_csv(T / "rif_ob_decomposicao.csv")
# SE por bootstrap em blocos por UPA (run_se_rif_interseccional.py), se disponível
_se_path = T / "rif_ob_se.csv"
se = pd.read_csv(_se_path).set_index("q_label") if _se_path.exists() else None

# Twofold consistente: % sobre gap_rif (end + ret == gap_rif por construção)
d["dot_pct"] = d["end"] / d["gap_rif"] * 100
d["ret_pct2"] = d["ret"] / d["gap_rif"] * 100

def _cel(v, q, col, dec=1):
    """valor (SE) quando o bootstrap existir."""
    if se is None or q not in se.index or f"se_{col}" not in se.columns:
        return fmt(v, dec)
    return f"{fmt(v, dec)} ({fmt(float(se.loc[q, f'se_{col}']), dec)})"


linhas = []
for _, r in d.iterrows():
    soma = r["dot_pct"] + r["ret_pct2"]
    assert abs(soma - 100) < 0.1, f"{r['q_label']}: soma={soma}"
    q = r["q_label"]
    # SE das % vem do bootstrap nas mesmas quantidades (end_pct/ret_pct do three-fold);
    # aqui as % são renormalizadas pelo gap_rif, então usa-se o SE da parcela em log-pontos
    # convertido pela mesma escala.
    esc = 100 / r["gap_rif"]
    se_dot = float(se.loc[q, "se_end"]) * esc if se is not None and q in se.index else None
    se_ret = float(se.loc[q, "se_ret"]) * esc if se is not None and q in se.index else None
    cel_dot = fmt(r["dot_pct"], 1) if se_dot is None else f"{fmt(r['dot_pct'],1)} ({fmt(se_dot,1)})"
    cel_ret = fmt(r["ret_pct2"], 1) if se_ret is None else f"{fmt(r['ret_pct2'],1)} ({fmt(se_ret,1)})"
    cel_gap = _cel(r["gap_obs"], q, "gap_obs", 3)
    n_q = fmtN(int(r["n_b"] + r["n_n"])) if "n_b" in d.columns else "---"
    linhas.append(f"{q} & {cel_gap} & {cel_dot} & {cel_ret} & {n_q} \\\\")

tex = (r"""\begin{table}[!ht]
\centering
\caption{Decomposição RIF-OB (Firpo, Fortin \& Lemieux, 2018) do gap salarial racial
por quantil incondicional, em formato \emph{two-fold} (referência: estrutura de preços
dos brancos). Dotações: diferença de características observáveis (capital humano, ocupação,
contexto). Retornos: parcela não explicada (componente discriminatório). Dotações + Retornos
$=100\%$ do gap em cada quantil. Padrão \emph{sticky floor}: o componente de retornos
(discriminação de mercado) é maior na base e decresce rumo ao topo. PNAD Contínua 2016--2025,
população completa. Entre parênteses: erro-padrão por bootstrap em blocos por UPA.}
\label{tab:rif_ob}
\begin{tabular}{lrrrr}
\toprule
Quantil & Gap obs. (SE) & Dotações (\%) & Retornos (\%) & $N$ \\
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
