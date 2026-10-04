"""
checar_escolaridade.py — sanidade da escolaridade depois da correção (VD3004).

Falha (código 1) se o padrão do erro antigo reaparecer: cobertura baixa, renda que não
sobe com o nível, ou superior completo implausível. Referências aproximadas da PNAD
Contínua para a PEA: superior completo ~20%, médio completo ou mais ~55–60%.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding="utf-8")
cols = ["educ_cat", "educ_fund_completo", "educ_medio_completo", "educ_superior_completo",
        "educ_pos_graduacao", "log_renda", "pea", "negro", "media_educ_upa"]
d = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=cols)
d = d[d["pea"] == 1]
erros = []

cob = d["educ_cat"].notna().mean()
print(f"cobertura da escolaridade na PEA: {cob:.1%}")
if cob < 0.98:
    erros.append(f"cobertura {cob:.1%} < 98%")

ordem = ["sem_instrucao", "fund_incompleto", "fund_completo", "medio_incompleto",
         "medio_completo", "superior_incompleto", "superior_completo", "pos_graduacao"]
r = d.groupby("educ_cat", observed=True)["log_renda"].agg(["size", "mean"]).reindex(ordem)
print("\nrenda por nível:\n", r.round(3).to_string())
completos = r.loc[["fund_completo", "medio_completo", "superior_completo", "pos_graduacao"], "mean"]
if not completos.is_monotonic_increasing:
    erros.append("renda não cresce com os níveis completos")

sup = d["educ_superior_completo"].mean()
med = d["educ_medio_completo"].mean()
print(f"\n≥ médio completo: {med:.1%} | ≥ superior completo: {sup:.1%}")
if not (0.10 <= sup <= 0.35):
    erros.append(f"superior completo {sup:.1%} fora de 10–35%")
for g, nome in ((0, "brancos"), (1, "negros")):
    s = d[d["negro"] == g]
    print(f"{nome}: ≥ médio {s['educ_medio_completo'].mean():.1%} | "
          f"≥ superior {s['educ_superior_completo'].mean():.1%} | pós {s['educ_pos_graduacao'].mean():.2%}")
if d.loc[d.negro == 1, "educ_superior_completo"].mean() >= d.loc[d.negro == 0, "educ_superior_completo"].mean():
    erros.append("negros com superior completo ≥ brancos (padrão do erro antigo)")
print(f"\nmedia_educ_upa (escala 0–7): média {d['media_educ_upa'].mean():.2f}")

# Deflação: a renda real média por ano não pode ter a tendência inflacionária da nominal
r = pd.read_parquet(ROOT / "data/processed/features.parquet",
                    columns=["Ano", "pea", "renda_nominal", "renda_bruta"])
r = r[(r["pea"] == 1) & (r["renda_bruta"] > 0)]
import numpy as np
por_ano = r.groupby("Ano").agg(nominal=("renda_nominal", lambda s: np.log(s[s > 0]).mean()),
                               real=("renda_bruta", lambda s: np.log(s).mean()))
print("\nlog-renda média por ano (nominal × real, reais do 2º tri/2026):\n", por_ano.round(3).to_string())
sub_nom = por_ano["nominal"].iloc[-1] - por_ano["nominal"].iloc[0]
sub_real = por_ano["real"].iloc[-1] - por_ano["real"].iloc[0]
print(f"variação 2016→2025: nominal {sub_nom:+.3f} | real {sub_real:+.3f}")
if abs(sub_real) > 0.5 * abs(sub_nom):
    erros.append(f"deflação não removeu a tendência (real {sub_real:+.3f} vs nominal {sub_nom:+.3f})")

# Leave-one-out das médias de contexto: uma média LOO varia dentro da UPA (cada pessoa vê
# o bairro sem si mesma). Constante na maioria das UPAs = a própria pessoa voltou a entrar.
# Foi assim que a regressão do desemprego (reconstrução de 02/10) passou sem ser vista.
ctx = ["pct_negro_upa", "tx_desemprego_upa", "media_educ_upa", "media_renda_upa"]
c = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=["UPA", "pea"] + ctx)
c = c[c["pea"] == 1]
for col in ctx:
    const = (c.groupby("UPA")[col].nunique() <= 1).mean()
    print(f"{col}: constante em {const:.1%} das UPAs")
    if const > 0.5:
        erros.append(f"{col} sem leave-one-out (constante em {const:.0%} das UPAs)")

print("\n" + ("OK — escolaridade coerente" if not erros else "FALHAS: " + "; ".join(erros)))
sys.exit(1 if erros else 0)
