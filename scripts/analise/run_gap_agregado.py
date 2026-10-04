# -*- coding: utf-8 -*-
"""
run_gap_agregado.py
===================
Gap agregado (degrau zero da escada do HLM) estimado na MESMA base e com os MESMOS
controles do M1, por MQO com erro-padrão agrupado por UPA.

Por que existe (E2.2, 03/10/2026): o agregado vinha do run_hlm_serie_completa.py,
com efeitos fixos de UF, enquanto o M1 e o M2 do step-up não têm UF e o M3 tem. A
"mediação pelo bairro" (agregado -> M1) misturava duas mudanças: entrar o bairro e
sair o estado. Sem UF no agregado, a escada fica aninhada:

    agregado (MQO)  ->  M1 (+ intercepto de bairro)  ->  M2 (+ contexto)
                    ->  M3 (+ efeitos fixos de UF)   ->  M4 (+ ocupação)

A versão com UF é gravada também, só como referência (linha "agregado_com_UF").

Saída: outputs/tables/gap_agregado.csv
Uso:   python scripts/analise/run_gap_agregado.py
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
import statsmodels.formula.api as smf

import run_hlm_stepup as S          # mesma base (load_data) e mesmos controles (_IND)

OUT = ROOT / "outputs" / "tables" / "gap_agregado.csv"


def main() -> int:
    df = S.load_data(S.SAMPLE_FRAC)
    linhas = []
    for nome, formula in (("agregado_sem_UF", f"log_renda ~ {S._IND}"),
                          ("agregado_com_UF", f"log_renda ~ {S._IND} + C(UF_str)")):
        res = smf.ols(formula, data=df).fit(cov_type="cluster",
                                            cov_kwds={"groups": df["UPA_str"]})
        b, se = float(res.params["negro"]), float(res.bse["negro"])
        linhas.append({"modelo": nome, "b_negro": b, "se_cluster_upa": se,
                       "gap_pct": (np.exp(b) - 1) * 100, "n": int(res.nobs),
                       "n_upa": int(df["UPA_str"].nunique())})
        print(f"{nome}: b = {b:.5f} (SE {se:.5f}) | gap = {(np.exp(b) - 1) * 100:.2f}% "
              f"| N = {int(res.nobs):,}")
        del res
    pd.DataFrame(linhas).to_csv(OUT, index=False)
    print(f"OK -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
