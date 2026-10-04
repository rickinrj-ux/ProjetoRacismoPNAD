# -*- coding: utf-8 -*-
"""
gerar_prevalencias_glmm.py
==========================
Prevalência de cada desfecho do GLMM (PEA ocupada com renda positiva) em
outputs/tables/glmm_prevalencias.csv.

Para que serve (E2.7, 03/10/2026): o E-value de VanderWeele & Ding (2017) aplicado direto à
razão de chances só vale para desfecho raro (prevalência < 15%). Com desfecho comum, a OR
exagera a razão de risco e o E-value tem de usar RR ≈ √OR. A prevalência decide qual fórmula.

Uso: python tcc/scripts/gerar_prevalencias_glmm.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]

OCP = ["ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo"]
df = pd.read_parquet(ROOT / "data/processed/features.parquet",
                     columns=OCP + ["renda_bruta", "pea", "negro"])
df = df[(df["pea"] == 1) & (df["renda_bruta"] > 0) & df["negro"].notna()]
r = df["renda_bruta"]
prev = {
    "ocp_qualif": float(df[OCP].max(axis=1).mean()),
    "y_top20": float((r >= r.quantile(0.80)).mean()),
    "y_top10": float((r >= r.quantile(0.90)).mean()),
}
out = ROOT / "outputs/tables/glmm_prevalencias.csv"
pd.DataFrame([{"desfecho": k, "prevalencia": v, "comum": v >= 0.15} for k, v in prev.items()]
             ).to_csv(out, index=False)
for k, v in prev.items():
    print(f"{k:11s} {v:6.1%}  {'comum → RR ≈ √OR' if v >= 0.15 else 'raro → RR ≈ OR'}")
print(f"OK -> {out.relative_to(ROOT)}")
