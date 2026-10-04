# -*- coding: utf-8 -*-
"""
exportar_m1_uf.py
=================
Lê do cache do step-up o M1 com efeitos fixos de UF (run_hlm_stepup.py --fit M1_UF) e grava
o coeficiente de negro em outputs/tables/hlm_m1_uf.csv, para a escada de mediação aninhada
(E2.2, 03/10/2026):

    agregado (MQO + UF) -> M1_UF (+ bairro) -> M3 (+ contexto) -> M4 (+ ocupação)

Uso: python scripts/analise/exportar_m1_uf.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "scripts" / "analise"))
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

import run_hlm_stepup as S

# o pickle guarda a classe como __main__.Light (o step-up rodou como script)
sys.modules["__main__"].Light = S.Light

L = S.cache_load("M1_UF")
if L is None:
    print("ERRO: cache do M1_UF não encontrado — rode run_hlm_stepup.py --fit M1_UF")
    sys.exit(1)
b, se = float(L.params["negro"]), float(L.bse["negro"])
pd.DataFrame([{"modelo": "M1_UF", "b_negro": b, "se": se, "gap_pct": (np.exp(b) - 1) * 100,
               "tau2": L.tau2, "sigma2": L.sigma2, "icc": L.icc, "llf": L.llf,
               "converged": L.converged, "n": L.n}]).to_csv(
    ROOT / "outputs" / "tables" / "hlm_m1_uf.csv", index=False)
print(f"M1_UF: b = {b:.5f} (SE {se:.5f}) | gap = {(np.exp(b) - 1) * 100:.2f}% | conv = {L.converged}")
