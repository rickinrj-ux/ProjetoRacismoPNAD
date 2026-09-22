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

T = Path("outputs/tables")
hp = pd.read_csv(T / "ml_cv_hiperparametros.csv")
fd = pd.read_csv(T / "ml_cv_folds.csv")
rs = pd.read_csv(T / "ml_cv_resumo.csv").iloc[0]

hp = hp.sort_values("r2", ascending=False)
linhas = []
for _, r in hp.iterrows():
    atual = " (atual)" if r["config"] == 1 else ""
    escolh = r"\textbf{" if r["max_depth"] == rs["escolhido_max_depth"] and r["config"] != 1 else ""
    fim = "}" if escolh else ""
    linhas.append(f"{escolh}{int(r['max_depth'])}{fim} & {fmt(r['learning_rate'], 2)} & "
                  f"{int(r['n_estimators'])}{atual} & {fmt(r['r2'], 4)} & {fmt(r['mae'], 4)} & "
                  f"{fmt(r['gap_overfit'], 4)} \\\\")

cv = fd.groupby("config")[["r2", "mae", "rmse"]].agg(["mean", "std"])
def _cv(cfg, met):
    return (fmt(cv.loc[cfg, (met, "mean")], 4) + r" $\pm$ " + fmt(cv.loc[cfg, (met, "std")], 4))

tex = (r"""\begin{table}[!ht]
\centering
\caption{Escolha de hiperparâmetros e validação cruzada do XGBoost (Alencar, 2024;
Géron, 2021). Painel~A: seis configurações comparadas numa partição de validação
\emph{dentro} do treino --- o conjunto de teste permanece intocado. Painel~B: validação
cruzada $k$-\emph{fold} ($k=""" + str(int(rs["k"])) + r"""$) no treino completo, com média e
desvio-padrão entre \emph{folds}. População completa: """ + fmtN(int(rs["n_treino"])) + r""" observações de
treino e """ + fmtN(int(rs["n_teste"])) + r""" de teste; nenhuma amostragem.}
\label{tab:ml_cv}
\small
\begin{tabular}{lccccc}
\multicolumn{6}{l}{\textbf{A. Busca na partição de validação}} \\
\toprule
Profundidade & Taxa de aprendizado & Árvores & $R^2$ & MAE & Sobreajuste \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}

\vspace{0.6em}
\begin{tabular}{lccc}
\multicolumn{4}{l}{\textbf{B. Validação cruzada no treino (""" + str(int(rs["k"])) + r""" \emph{folds})}} \\
\toprule
Configuração & $R^2$ (média $\pm$ dp) & MAE & RMSE \\
\midrule
Escolhida (profundidade """ + str(int(rs["escolhido_max_depth"])) + r""") & """ + _cv("escolhida", "r2") + " & " + _cv("escolhida", "mae") + " & " + _cv("escolhida", "rmse") + r""" \\
Anterior (profundidade 6) & """ + _cv("atual_tcc", "r2") + " & " + _cv("atual_tcc", "mae") + " & " + _cv("atual_tcc", "rmse") + r""" \\
\bottomrule
\end{tabular}
\normalsize
\par\smallskip
\footnotesize\emph{Como ler:} ``Sobreajuste'' é a diferença entre o $R^2$ de treino e o de
validação --- valores próximos de zero indicam que o modelo não decorou os dados. A
configuração escolhida melhora o $R^2$ em """ + fmt((cv.loc["escolhida", ("r2", "mean")] - cv.loc["atual_tcc", ("r2", "mean")]) * 100, 1) + r""" ponto percentual sem aumentar o
sobreajuste, e a variação entre \emph{folds} é da ordem de """ + fmt(cv.loc["escolhida", ("r2", "std")], 4) + r""" --- com 6,2~milhões de
observações de treino, o desempenho praticamente não depende de qual pedaço dos dados é
usado para validar. No conjunto de teste (intocado durante a escolha), $R^2 = """ + fmt(rs["teste_r2"], 4) + r"""$.
Na unidade original, o erro mediano de previsão é de R\$~""" + fmtN(int(round(rs["erro_mediano_reais"]))) + r""" por mês
(""" + fmt(rs["erro_mediano_pct"], 0) + r"""\% do rendimento observado), com correção de Duan para a
retransformação do logaritmo.
\end{table}
""")
(T / "ml_cv.tex").write_text(tex, encoding="utf-8")
print("OK -> ml_cv.tex")
print(cv.round(4).to_string())
