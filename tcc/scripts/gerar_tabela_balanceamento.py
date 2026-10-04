"""
gerar_tabela_balanceamento.py
=============================
Tabela de balanceamento entre brancos e negros (TODO_revisao 7.8; MHE-11/MHE-28):
antes de qualquer controle, mostra em que as duas populações diferem — é a tabela que
justifica os controles e, ao mesmo tempo, avisa onde a comparação é "maçã com laranja".

Reporta, para cada covariável do núcleo: média em cada grupo, diferença, diferença
padronizada (Cohen's d; |d| > 0,10 costuma indicar desequilíbrio relevante) e, para o
suporte comum (MHE-28), a fração de UPAs em que convivem brancos e negros e a fração de
células UF x escolaridade com os dois grupos.

Saída: outputs/tables/balanceamento.csv | .tex (tab:balanceamento)
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
import numpy as np
import pandas as pd
from pathlib import Path
from params import fmt, fmtN

T = Path("outputs/tables")
VARS = {
    "log_renda": "log do rendimento",
    "idade_c": "Idade (centrada)",
    "sexo_fem": "Sexo feminino",
    # dummies cumulativas (VD3004): "ao menos" cada nível; cobertura total, sem indicador de faltante
    "educ_fund_completo": "Fundamental completo ou mais",
    "educ_medio_completo": "Médio completo ou mais",
    "educ_superior_completo": "Superior completo ou mais",
    "educ_pos_graduacao": "Pós-graduação",
    "log_horas": "log(horas trabalhadas)",
    "urbano": "Reside em área urbana",
    "emprego_formal": "Emprego formal",
    "conta_propria": "Conta própria",
    "trab_domestico": "Trabalho doméstico",
    "ocp_dirigente": "CBO: dirigente",
    "ocp_profissional": "CBO: profissional",
    "ocp_tecnico": "CBO: técnico",
    "pct_negro_upa_z": r"\% negro na UPA ($z$)",
    "tx_desemprego_upa_z": "Desemprego na UPA ($z$)",
    "media_educ_upa_z": "Educ. média na UPA ($z$)",
}
COLS = list(VARS) + ["negro", "UF", "UPA"]

print("Carregando features ...", flush=True)
df = pd.read_parquet("data/processed/features.parquet",
                     columns=COLS)
df = df[df["log_renda"].notna() & (df["log_renda"] > 0) & df["negro"].notna()]
df = df.dropna(subset=list(VARS)).reset_index(drop=True)
b, n = df[df["negro"] == 0], df[df["negro"] == 1]
print(f"N = {len(df):,} (brancos={len(b):,}, negros={len(n):,})", flush=True)

rows = []
for v, lab in VARS.items():
    mb, mn = b[v].mean(), n[v].mean()
    sb, sn = b[v].std(), n[v].std()
    d = (mb - mn) / np.sqrt((sb ** 2 + sn ** 2) / 2) if (sb + sn) > 0 else np.nan
    rows.append({"variavel": v, "rotulo": lab, "media_branco": mb, "media_negro": mn,
                 "dif": mb - mn, "d_cohen": d})
bal = pd.DataFrame(rows)

# Suporte comum (MHE-28)
g = df.groupby("UPA")["negro"].agg(["mean", "size"])
upa_mista = float(((g["mean"] > 0) & (g["mean"] < 1)).mean())
df["_educ"] = np.select(
    [df["educ_pos_graduacao"] == 1, df["educ_superior_completo"] == 1,
     df["educ_medio_completo"] == 1, df["educ_fund_completo"] == 1],
    ["pos", "sup", "med", "fund"], default="baixa")
cel = df.groupby(["UF", "_educ"])["negro"].agg(["mean", "size"])
cel_mista = float(((cel["mean"] > 0) & (cel["mean"] < 1)).mean())
pes_mista = float(cel.loc[(cel["mean"] > 0) & (cel["mean"] < 1), "size"].sum() / cel["size"].sum())
bal.attrs.update(upa_mista=upa_mista, cel_mista=cel_mista, pes_mista=pes_mista)
bal.to_csv(T / "balanceamento.csv", index=False, encoding="utf-8")

linhas = [f"{r['rotulo']} & {fmt(r['media_branco'], 3)} & {fmt(r['media_negro'], 3)} & "
          f"{fmt(r['dif'], 3)} & {fmt(r['d_cohen'], 2)} \\\\" for _, r in bal.iterrows()]
tex = (r"""\begin{table}[!ht]
\centering
\caption{Balanceamento entre trabalhadores brancos e negros \emph{antes} de qualquer
controle --- a tabela que mostra de que é feita a comparação (Angrist \& Pischke, cap.~3).
Diferença padronizada: $d = (\bar x_b - \bar x_n)/\sqrt{(s_b^2+s_n^2)/2}$; valores acima de
$0{,}10$ em módulo indicam desequilíbrio relevante. População completa da PEA com renda
positiva (""" + f"$N = {fmtN(len(df))}$" + r"""; """ + f"{fmtN(len(b))}" + r""" brancos e """
       + f"{fmtN(len(n))}" + r""" negros).}
\label{tab:balanceamento}
\small
\begin{tabular}{lrrrr}
\toprule
Variável & Brancos & Negros & Diferença & $d$ \\
\midrule
""" + "\n".join(linhas) + r"""
\bottomrule
\end{tabular}
\normalsize
\par\smallskip
\footnotesize\emph{Suporte comum:} """ + f"{fmt(upa_mista * 100, 1)}" + r"""\% das UPAs têm
trabalhadores dos dois grupos, e """ + f"{fmt(cel_mista * 100, 1)}" + r"""\% das células
UF~$\times$~escolaridade também (""" + f"{fmt(pes_mista * 100, 1)}" + r"""\% das observações
estão em células com os dois grupos) --- a comparação não depende de extrapolar para
regiões da amostra onde só existe um dos grupos.
\end{table}
""")
(T / "balanceamento.tex").write_text(tex, encoding="utf-8")
print(bal.round(3).to_string(index=False))
print(f"UPAs mistas: {upa_mista:.1%} | células UF x educ mistas: {cel_mista:.1%} "
      f"({pes_mista:.1%} das obs.)")
print("OK -> balanceamento.csv | balanceamento.tex")
