"""
teste_oaxaca_educ_conhecida.py
==============================
DIAGNÓSTICO (perícia F1): testa se a divergência da decomposição Oaxaca-Blinder
vem do tratamento de educação ausente (educ_missing) vs educação conhecida.

Roda a MESMA decomposição twofold (com intercepto no componente não-explicado,
identidade fecha) em três cenários, sobre os mesmos dados:

  C1: população completa + educ_missing + ocupação   (esperado ~24,8% dotações)
  C2: educação conhecida (dropna educ_cat) + ocupação
  C3: educação conhecida, sem ocupação (decomposição clássica de capital humano)

Não grava tabelas oficiais — apenas imprime o diagnóstico. Sem bootstrap
(estimativa pontual basta para decidir a DIREÇÃO da narrativa).
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
import statsmodels.formula.api as smf
from pathlib import Path

ROOT = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")

COLS = ["negro", "sexo_fem", "idade_c", "idade_sq",
        "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
        "educ_cat", "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
        "horas_c", "emprego_formal", "conta_propria", "trab_domestico",
        "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
        "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa",
        "log_renda", "renda_bruta", "pea"]

OCC_F = ("horas_c + emprego_formal + conta_propria + trab_domestico"
         " + ocp_dirigente + ocp_profissional + ocp_tecnico + ocp_administrativo"
         " + ocp_servicos + ocp_agro + ocp_operario + ocp_operador + ocp_ffaa")
CONTEXT_F = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
EDUC_F = "educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
DEMO_F = "idade_c + idade_sq + sexo_fem"

print("Carregando features.parquet ...", flush=True)
df0 = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=COLS)
df0["educ_missing"] = df0["educ_cat"].isna().astype(int)
base_mask = (df0["pea"] == 1) & (df0["renda_bruta"] > 0) & (df0["negro"].notna())
df0 = df0[base_mask]
print(f"PEA com renda > 0: {len(df0):,}", flush=True)
print(f"  educação conhecida (educ_cat não-NA): {(df0['educ_missing']==0).sum():,} "
      f"({(df0['educ_missing']==0).mean()*100:.1f}%)", flush=True)


def oaxaca_twofold(df, formula):
    """Twofold OB (referência = brancos), intercepto no não-explicado.
    Retorna (gap, ef_dotacao, ef_coef, pct_dot, pct_coef, resid)."""
    df_b = df[df["negro"] == 0]
    df_n = df[df["negro"] == 1]
    m_b = smf.ols(formula, data=df_b).fit()
    m_n = smf.ols(formula, data=df_n).fit()
    mean_b = pd.Series(m_b.model.exog[:, 1:].mean(0), index=m_b.model.exog_names[1:])
    mean_n = pd.Series(m_n.model.exog[:, 1:].mean(0), index=m_n.model.exog_names[1:])
    coef_b = m_b.params.drop("Intercept", errors="ignore")
    coef_n = m_n.params.drop("Intercept", errors="ignore")
    ic_b = float(m_b.params.get("Intercept", 0.0))
    ic_n = float(m_n.params.get("Intercept", 0.0))
    gap = df_b["log_renda"].mean() - df_n["log_renda"].mean()
    ef_dot = float((mean_b - mean_n) @ coef_b)
    ef_coef = float(mean_n @ (coef_b - coef_n)) + (ic_b - ic_n)
    resid = gap - (ef_dot + ef_coef)
    return gap, ef_dot, ef_coef, ef_dot/gap*100, ef_coef/gap*100, resid


cenarios = [
    ("C1 pop completa + educ_missing + ocup",
     df0,
     f"log_renda ~ {EDUC_F} + educ_missing + {DEMO_F} + {CONTEXT_F} + {OCC_F}"),
    ("C2 educ conhecida + ocupacao",
     df0[df0["educ_missing"] == 0],
     f"log_renda ~ {EDUC_F} + {DEMO_F} + {CONTEXT_F} + {OCC_F}"),
    ("C3 educ conhecida, sem ocupacao",
     df0[df0["educ_missing"] == 0],
     f"log_renda ~ {EDUC_F} + {DEMO_F} + {CONTEXT_F}"),
]

print("\n" + "=" * 78)
print(f"{'Cenário':<40}{'N':>12}{'Dotações':>11}{'Discrim.':>11}")
print("=" * 78)
for nome, dfx, formula in cenarios:
    g, ed, ec, pd_, pc_, res = oaxaca_twofold(dfx, formula)
    flag = "" if abs(res) < 1e-6 else f"  [resid={res:+.4f}!]"
    print(f"{nome:<40}{len(dfx):>12,}{pd_:>10.1f}%{pc_:>10.1f}%{flag}", flush=True)
    print(f"{'':<40}gap={g:+.4f}  dot={ed:+.4f}  coef={ec:+.4f}")
print("=" * 78)
print("\nLeitura: se C2/C3 (educ conhecida) derem dotações dominantes (~70-85%),")
print("confirma-se que o 24,8% de C1 é artefato de educ_missing — e a narrativa")
print("'composição domina o gap' (espírito do antigo 84%) está correta.")
print("\n=== TESTE CONCLUÍDO ===")
