"""
comparar_antes_depois.py — E0.3: resultados-chave antes (outputs/_backup_pre_educ/, escolaridade
pela V3009A e renda nominal) × depois (outputs/tables/, VD3004 + deflator + C(Ano) + fundamental
em todos os modelos). Grava tcc/revisoes/antes_depois_<data>.md.
"""
import datetime as dt
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
A, D = ROOT / "outputs" / "_backup_pre_educ", ROOT / "outputs" / "tables"
sys.stdout.reconfigure(encoding="utf-8")


def ler(nome):
    a, d = A / nome, D / nome
    return (pd.read_csv(a) if a.exists() else None), (pd.read_csv(d) if d.exists() else None)


linhas = []


def add(bloco, item, va, vd, fmt="{:.2f}"):
    f = lambda v: "—" if v is None or (isinstance(v, float) and math.isnan(v)) else fmt.format(v)
    delta = "" if va is None or vd is None else fmt.format(vd - va)
    linhas.append((bloco, item, f(va), f(vd), delta))


def pega(df, filtro, col):
    if df is None:
        return None
    s = df.query(filtro)[col] if filtro else df[col]
    return float(s.iloc[0]) if len(s) else None


# HLM step-up
a, d = ler("gap_decomposicao_stepup.csv")
for m in ["M1", "M2", "M3", "M4"]:
    add("HLM", f"Gap {m} (%)", pega(a, f"Modelo == '{m}'", "Gap%"), pega(d, f"Modelo == '{m}'", "Gap%"))
a, d = ler("hlm_stepup_fit.csv")
for m in ["M0", "M3"]:
    add("HLM", f"ICC {m}", pega(a, f"modelo == '{m}'", "icc_upa"), pega(d, f"modelo == '{m}'", "icc_upa"), "{:.3f}")

# GLMM (lme4)
a, d = ler("glmm_glassceil_glmer.csv")
for des, rot in [("ocp_qualif", "cargo qualificado"), ("y_top20", "topo 20%"), ("y_top10", "topo 10%")]:
    for m, r in [("M2", "A2"), ("M3", "A3")]:
        add("GLMM", f"OR {rot} {r}", pega(a, f"desfecho == '{des}' and modelo == '{m}'", "OR_negro"),
            pega(d, f"desfecho == '{des}' and modelo == '{m}'", "OR_negro"), "{:.3f}")
    add("GLMM", f"AME {rot} A2 (p.p.)", pega(a, f"desfecho == '{des}' and modelo == 'M2'", "AME_pp"),
        pega(d, f"desfecho == '{des}' and modelo == 'M2'", "AME_pp"))

# Oaxaca (núcleo)
a, d = ler("ob_acesso.csv")
for e, r in [("sem_ocupacao", "A sem ocupação"), ("acesso", "B com ocupação")]:
    add("Oaxaca", f"% não explicado ({r})", pega(a, f"espec == '{e}'", "pct_coeficiente"),
        pega(d, f"espec == '{e}'", "pct_coeficiente"))

# QR
a, d = ler("qr_melhorias.csv")
for q in [0.1, 0.5, 0.9]:
    add("QR", f"Gap q{int(q*100)} (%)", pega(a, f"grupo == 'Global' and quantil == {q}", "gap_pct"),
        pega(d, f"grupo == 'Global' and quantil == {q}", "gap_pct"))

# RIF
a, d = ler("rif_ob_se.csv")
for q in ["q10", "q50", "q90"]:
    add("RIF", f"% retornos {q}", pega(a, f"q_label == '{q}'", "ret_pct"), pega(d, f"q_label == '{q}'", "ret_pct"))

# Interseccional e grupos
a, d = ler("interseccional_ob4grupos_nucleo.csv")
for g in ["Mulher Branca", "Homem Negro", "Mulher Negra"]:
    add("Interseccional", f"Gap {g} (%)", pega(a, f"grupo == '{g}'", "gap_pct"), pega(d, f"grupo == '{g}'", "gap_pct"))
a, d = ler("grupo_rg_4grupos_desfechos.csv")
for des in ["ocp_qualif", "y_top10"]:
    add("Grupos raça×gênero", f"OR mulher negra {des}", pega(a, f"desfecho == '{des}'", "OR_mulher_negra"),
        pega(d, f"desfecho == '{des}'", "OR_mulher_negra"), "{:.3f}")

# ML
a, d = ler("ml_performance.csv")
add("ML", "R² XGBoost (teste)", pega(a, "Modelo == 'XGBoost'", "R²"), pega(d, "Modelo == 'XGBoost'", "R²"), "{:.3f}")

# Tendência
a, d = ler("tendencia_temporal_testes.csv")
add("Tendência", "p da inclinação (WLS)", pega(a, None, "p-valor"), pega(d, None, "p-valor"), "{:.3f}")

hoje = dt.date.today().isoformat()
out = ROOT / "tcc" / "revisoes" / f"antes_depois_{hoje}.md"
txt = [f"# Antes × depois da correção da escolaridade e da renda — {hoje}", "",
       "Antes: `outputs/_backup_pre_educ/` (V3009A como nível, renda nominal). Depois: `outputs/tables/`",
       "(VD3004 com dummies cumulativas, deflator IBGE + efeito de ano, fundamental em todos os modelos).",
       "", "| Bloco | Resultado | Antes | Depois | Δ |", "|---|---|---|---|---|"]
txt += [f"| {b} | {i} | {va} | {vd} | {dl} |" for b, i, va, vd, dl in linhas]
out.write_text("\n".join(txt) + "\n", encoding="utf-8")
print("\n".join(txt))
print(f"\nOK -> {out.relative_to(ROOT)}")
