"""
gerar_tabela_cv.py
==================
Tabela de validação cruzada e escolha de hiperparâmetros do XGBoost (bloco 8; apostila
Alencar, ML-02/ML-06), a partir de outputs/tables/ml_cv_*.csv (run_ml_cv.py).

Saída: outputs/tables/ml_cv.tex (tab:ml_cv)
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
from params_nucleo import P as _PN   # N de treino citado na nota

T = Path("outputs/tables")
hp = pd.read_csv(T / "ml_cv_hiperparametros.csv")
fd = pd.read_csv(T / "ml_cv_folds.csv")
rs = pd.read_csv(T / "ml_cv_resumo.csv").iloc[0]

hp = hp.sort_values("r2", ascending=False)
linhas = []
for _, r in hp.iterrows():
    # a configuração 1 é a de referência (profundidade 6), não a "atual": a escolhida é outra
    atual = " (referência)" if r["config"] == 1 else ""
    escolh = r"\textbf{" if r["max_depth"] == rs["escolhido_max_depth"] and r["config"] != 1 else ""
    fim = "}" if escolh else ""
    linhas.append(f"{escolh}{int(r['max_depth'])}{fim} & {fmt(r['learning_rate'], 2)} & "
                  f"{int(r['n_estimators'])}{atual} & {fmt(r['r2'], 4)} & {fmt(r['mae'], 4)} & "
                  f"{fmt(r['gap_overfit'], 4)} \\\\")

cv = fd.groupby("config")[["r2", "mae", "rmse"]].agg(["mean", "std"])
def _cv(cfg, met):
    return (fmt(cv.loc[cfg, (met, "mean")], 4) + r" $\pm$ " + fmt(cv.loc[cfg, (met, "std")], 4))

# 06/10/2026: dois painéis viravam, no Word, duas tabelas sob um título só, e o Sistema de
# Trabalho Final acusou "tabela sem título e sem fonte". Agora são duas tabelas, cada uma com
# título, Fonte e chamada no texto (tab:ml_cv e tab:ml_cv_b); sem negrito (manual 15.2).
_ganho = fmt((cv.loc["escolhida", ("r2", "mean")] - cv.loc["atual_tcc", ("r2", "mean")]) * 100, 1)
tex = (r"""\begin{table}[!ht]
\centering
\caption{Escolha de hiperparâmetros do XGBoost na partição de validação
\cite{alencar2026a, alencar2026b, alencar2026c, geron2021}. Seis configurações comparadas
\emph{dentro} do treino --- o conjunto de teste permanece intocado. População completa:
""" + fmtN(int(rs["n_treino"])) + r""" observações de treino e """ + fmtN(int(rs["n_teste"])) + r""" de teste; nenhuma amostragem.}
\label{tab:ml_cv}
\small
\begin{tabular}{lccccc}
\toprule
Profundidade & Taxa de aprendizado & Árvores & $R^2$ & MAE & Sobreajuste \\
\midrule
""" + "\n".join(linhas).replace(r"\textbf{", "{") + r"""
\bottomrule
\end{tabular}
\normalsize
\par\smallskip
\footnotesize\emph{Como ler:} ``Sobreajuste'' é a diferença entre o $R^2$ de treino e o de
validação --- valores próximos de zero indicam que o modelo não decorou os dados. A
primeira linha é a configuração escolhida.
\end{table}

\begin{table}[!ht]
\centering
\caption{Validação cruzada $k$-\emph{fold} ($k=""" + str(int(rs["k"])) + r"""$) do XGBoost no treino completo,
com média e desvio-padrão entre \emph{folds}.}
\label{tab:ml_cv_b}
\small
\begin{tabular}{lccc}
\toprule
Configuração & $R^2$ (média $\pm$ dp) & MAE & RMSE \\
\midrule
Escolhida (profundidade """ + str(int(rs["escolhido_max_depth"])) + r""") & """ + _cv("escolhida", "r2") + " & " + _cv("escolhida", "mae") + " & " + _cv("escolhida", "rmse") + r""" \\
Referência (profundidade 6) & """ + _cv("atual_tcc", "r2") + " & " + _cv("atual_tcc", "mae") + " & " + _cv("atual_tcc", "rmse") + r""" \\
\bottomrule
\end{tabular}
\normalsize
\par\smallskip
\footnotesize\emph{Como ler:} a configuração escolhida ganha """ + _ganho + r""" ponto percentual
de $R^2$ ao custo de um sobreajuste maior, mas ainda pequeno (Tabela~\ref{tab:ml_cv}). No
conjunto de teste (intocado durante a escolha), $R^2 = """ + fmt(rs["teste_r2"], 4) + r"""$.
\end{table}
""")
(T / "ml_cv.tex").write_text(tex, encoding="utf-8")
print("OK -> ml_cv.tex")
print(cv.round(4).to_string())
