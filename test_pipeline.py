"""
test_pipeline.py
Teste do pipeline: layout IBGE + download + parse de 1 trimestre (2023 T1).
"""
import sys
import logging

sys.path.insert(0, "src")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s"
)

import pyarrow.parquet as pq
from data_ingestion import download_layout, run_ingestion

# ── 1. Dicionario de layout ───────────────────────────────────────────────────
print("\n=== Dicionario de layout IBGE ===")
layout = download_layout()
print(f"Total de variaveis: {len(layout)}")

vars_interesse = ["UF", "UPA", "V2007", "V2009", "V2010", "V3009A",
                  "VD4002", "VD4016", "VD4019", "VD4020"]
sub = layout[layout["name"].isin(vars_interesse)][["name", "start", "width", "end"]]
print("\nVariaveis de interesse (posicoes verificadas):")
print(sub.sort_values("start").to_string(index=False))

# ── 2. Ingesta de 1 trimestre ─────────────────────────────────────────────────
print("\n=== Ingestao: 2023 T1 ===")
run_ingestion(years=[2023], quarters=[1])

# ── 3. Valida o Parquet gerado ────────────────────────────────────────────────
print("\n=== Validacao do Parquet gerado ===")
from pathlib import Path
parquet_path = Path("data/processed/ano=2023/trimestre=1/data.parquet")

if parquet_path.exists():
    df = pq.read_table(parquet_path).to_pandas()
    print(f"Linhas: {len(df):,} | Colunas: {len(df.columns)}")
    print(f"\nMemoria em uso: {df.memory_usage(deep=True).sum() / 1e6:.1f} MB")
    print("\nDistribuicao por Raca (V2010):")
    print(df["V2010"].value_counts().sort_index().rename({
        1: "Branca", 2: "Preta", 3: "Amarela", 4: "Parda", 5: "Indigena"
    }))
    print("\nRendimento (VD4020) - estatisticas basicas:")
    print(df["VD4020"].describe())
    print("\nPipeline OK - pronto para feature_engineering.py")
else:
    print(f"ERRO: Parquet nao encontrado em {parquet_path}")
