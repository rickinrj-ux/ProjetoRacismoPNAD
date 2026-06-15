"""
gerar_tabela_glmm.py
====================
Gera a tabela-síntese do GLMM logístico (teto de vidro ocupacional e salarial)
para o NÚCLEO do TCC, em LaTeX (booktabs), população COMPLETA.

Fontes:
  outputs/tables/glmm_glassceil_full.csv  — OR, IC95%, AME por desfecho e modelo
  outputs/tables/evalues_glmm.csv         — E-values (sensibilidade a confundidor)

Saída:
  outputs/tables/glmm_glassceil.tex

Desfechos: ocp_qualif (cargo qualificado, CBO 1-4), y_top20, y_top10.
Modelos: M1 (controles individuais + UF FE), M2 (+contexto UPA),
         M3 (+interação negro×credencial).
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

TABLES = Path("outputs") / "tables"

gc = pd.read_csv(TABLES / "glmm_glassceil_full.csv")
ev = pd.read_csv(TABLES / "evalues_glmm.csv")

# E-value por (desfecho, modelo) — só M1/M2 disponíveis
ev_map = {(row["Desfecho"], row["Modelo"]): row["E-value (OR)"]
          for _, row in ev.iterrows()}

DESF_LABEL = {
    "ocp_qualif": r"Cargo qualificado (CBO 1--4)",
    "y_top20":    r"Top 20\% de renda",
    "y_top10":    r"Top 10\% de renda",
}
MOD_LABEL = {
    "M1": r"M1 (indiv.\ + UF)",
    "M2": r"M2 (+ contexto UPA)",
    "M3": r"M3 (+ interação credencial)",
}

def or_cell(orv, lo, hi):
    return f"{fmt(orv,3)} [{fmt(lo,3)}; {fmt(hi,3)}]"

lines = []
lines.append(r"\begin{table}[!ht]")
lines.append(r"\centering")
lines.append(r"\caption{GLMM Logístico --- Teto de Vidro Ocupacional e Salarial. "
             r"Odds ratio do coeficiente \emph{negro} (IC 95\% entre colchetes), efeito "
             r"marginal médio (AME, em pontos percentuais) e E-value "
             r"(VanderWeele \& Ding, 2017). População completa da PEA "
             r"($N=7{,}69$ milhões). Desfechos binários estimados por logit multinível "
             r"com efeito aleatório de UPA. Todos os coeficientes com $p<0{,}001$.}")
lines.append(r"\label{tab:glmm_glassceil}")
lines.append(r"\begin{tabular}{llccc}")
lines.append(r"\toprule")
lines.append(r"Desfecho & Modelo & OR (IC 95\%) & AME (p.p.) & E-value \\")
lines.append(r"\midrule")

for desf in ["ocp_qualif", "y_top20", "y_top10"]:
    sub = gc[gc["desfecho"] == desf]
    first = True
    for _, row in sub.iterrows():
        mod = row["modelo"]
        desf_col = DESF_LABEL[desf] if first else ""
        first = False
        ev_val = ev_map.get((desf, mod))
        ev_str = fmt(ev_val, 2) if pd.notna(ev_val) else "---"
        lines.append(
            f"{desf_col} & {MOD_LABEL[mod]} & {or_cell(row['OR_negro'], row['CI95_lo'], row['CI95_hi'])} "
            f"& {fmt(row['AME_pp'],2)} & {ev_str} \\\\"
        )
    lines.append(r"\midrule")

lines[-1] = r"\bottomrule"  # troca o último \midrule
lines.append(r"\end{tabular}")
lines.append(r"\par\smallskip")
lines.append(r"\footnotesize\emph{Leitura:} OR $<1$ indica menor chance de acesso para "
             r"trabalhadores negros vs.\ brancos de mesmo perfil. O teto se aperta no extremo "
             r"superior (top 10\%) e o E-value $\geq 2{,}2$ no M2 indica que um confundidor "
             r"não-observado precisaria de associação $\geq 2{,}2\times$ com raça \emph{e} com o "
             r"desfecho para anular o efeito.")
lines.append(r"\end{table}")

out = TABLES / "glmm_glassceil.tex"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"OK -> {out}")
print("\n".join(lines))
