# -*- coding: utf-8 -*-
"""
recalcular_contexto_loo.py — médias de contexto sem o próprio indivíduo.

O problema: `compute_upa_aggregates` calculava as médias do bairro com
`mean()` simples, de modo que a raça, a escolaridade e a situação de emprego
da própria pessoa entravam no regressor contextual que deveria descrevê-la.
É o problema do reflexo (Manski, 1993), que o trabalho já nomeia — e que
`run_ml_shap.py` já corrigia, mas só para a renda e só no modelo preditivo.

O que muda: `pct_negro_upa`, `media_educ_upa`, `media_renda_upa` e
`tx_desemprego_upa` (e os equivalentes de UF) passam a ser calculados
excluindo a observação. As versões padronizadas (`_z`) são refeitas a partir
delas.

Por que não reprocessar do zero: as colunas de origem (UPA, UF, negro,
educ_ord, log_renda, empregado, pea) já estão no parquet e não mudam. Refazer
a ingestão dos 40 trimestres levaria horas e introduziria risco em variáveis
que não são o alvo desta correção.

Uso: python scripts/utils/recalcular_contexto_loo.py [--dry-run]
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
ALVO = ROOT / "data" / "processed" / "features.parquet"
BAK = ALVO.with_suffix(".parquet.pre_loo")
DRY = "--dry-run" in sys.argv

MIN_UPA_SIZE = 10          # mesmo limiar de feature_engineering.py


def media_loo(df: pd.DataFrame, col: str, grupo: str) -> np.ndarray:
    """Média do grupo excluindo a própria linha.

    Quem tem o valor ausente não contribui para a soma nem para a contagem, e
    para essa linha a média do grupo já é 'sem o próprio' — por isso o
    denominador só desconta quem de fato tem valor.
    """
    g = df.groupby(grupo, observed=True)[col]
    soma = g.transform("sum")
    cont = g.transform("count")
    tem = df[col].notna()
    num = soma - df[col].where(tem, 0)
    den = cont - tem.astype("int64")
    return np.where(den > 0, num / den, np.nan)


def padronizar(s: pd.Series) -> pd.Series:
    dp = s.std()
    return (s - s.mean()) / dp if dp and dp > 0 else s * 0.0


def main() -> int:
    print(f"lendo {ALVO.relative_to(ROOT)} ...")
    tab = pq.ParquetFile(ALVO).read()
    df = tab.to_pandas()
    print(f"  {len(df):,} linhas, {len(df.columns)} colunas".replace(",", "."))

    antes = {c: df[c].copy() for c in
             ("pct_negro_upa", "media_educ_upa", "media_renda_upa", "tx_desemprego_upa")
             if c in df.columns}

    # ── nível 2: UPA ─────────────────────────────────────────────────────────
    df["pct_negro_upa"]   = media_loo(df, "negro", "UPA")
    df["media_educ_upa"]  = media_loo(df, "educ_ord", "UPA")
    df["media_renda_upa"] = media_loo(df, "log_renda", "UPA")

    # desemprego: definido sobre a PEA, então o leave-one-out também é na PEA
    pea = df["pea"].fillna(0).astype(bool)
    emp = df.loc[pea, ["UPA", "UF", "empregado"]].copy()
    emp["empregado"] = emp["empregado"].astype("float32")
    emp["_loo_upa"] = media_loo(emp, "empregado", "UPA")
    emp["_loo_uf"] = media_loo(emp, "empregado", "UF")
    df["tx_desemprego_upa"] = np.nan
    df.loc[pea, "tx_desemprego_upa"] = 1 - emp["_loo_upa"].to_numpy()
    df["tx_desemprego_uf"] = np.nan
    df.loc[pea, "tx_desemprego_uf"] = 1 - emp["_loo_uf"].to_numpy()
    # quem está fora da PEA recebe a taxa do grupo (não há 'próprio' a excluir)
    for col, grupo in (("tx_desemprego_upa", "UPA"), ("tx_desemprego_uf", "UF")):
        media_grupo = df.groupby(grupo, observed=True)[col].transform("mean")
        df[col] = df[col].fillna(media_grupo)

    # UPAs com amostra insuficiente seguem mascaradas, como antes
    # mesmo critério de feature_engineering.py: conta de `negro` não-nulo,
    # não o total de linhas do grupo
    n_upa = df.groupby("UPA", observed=True)["negro"].transform("count")
    pequenas = n_upa < MIN_UPA_SIZE
    ctx = ["pct_negro_upa", "tx_desemprego_upa", "media_educ_upa", "media_renda_upa"]
    df.loc[pequenas, ctx] = np.nan
    print(f"  {int(pequenas.sum()):,} linhas em UPAs com n < {MIN_UPA_SIZE}: contexto NaN"
          .replace(",", "."))

    # ── nível 3: UF ──────────────────────────────────────────────────────────
    df["pct_negro_uf"]   = media_loo(df, "negro", "UF")
    df["media_educ_uf"]  = media_loo(df, "educ_ord", "UF")
    df["media_renda_uf"] = media_loo(df, "log_renda", "UF")

    # ── padronizadas ─────────────────────────────────────────────────────────
    for base in ctx + ["pct_negro_uf", "media_educ_uf", "media_renda_uf", "tx_desemprego_uf"]:
        z = f"{base}_z"
        if z in df.columns:
            df[z] = padronizar(df[base])

    print()
    print("=== o que mudou ===")
    for c, orig in antes.items():
        novo = df[c]
        m = pd.DataFrame({"a": orig, "b": novo}).dropna()
        print(f"  {c:<20} corr={m['a'].corr(m['b']):.6f}  dif média={abs(m['b']-m['a']).mean():.6f}")

    if DRY:
        print("\n--dry-run: nada gravado")
        return 0

    if not BAK.exists():
        print(f"\nguardando original em {BAK.name} ...")
        shutil.copy2(ALVO, BAK)
    df.to_parquet(ALVO, index=False)
    print(f"OK -> {ALVO.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
