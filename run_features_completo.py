"""
run_features_completo.py
Feature engineering sobre a serie completa 2016-2025 (40 trimestres).
"""
import sys, logging, time
sys.path.insert(0, "src")

LOG_FILE = "logs/features_completo.log"
handlers = [
    logging.FileHandler(LOG_FILE, encoding="utf-8"),
    logging.StreamHandler(sys.stdout),
]
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=handlers,
)

import numpy as np
import pandas as pd
from feature_engineering import build_features

t0 = time.time()
print("\n=== FEATURE ENGINEERING — SERIE COMPLETA 2016-2025 ===\n")

df = build_features(years=list(range(2016, 2026)), save=True)

elapsed = (time.time() - t0) / 60
print(f"\n=== CONCLUIDO em {elapsed:.1f} min ===")
print(f"Total de observacoes (raca binaria): {len(df):,}")
print(f"  Negros (Preta+Parda): {df['negro'].sum():,.0f} ({df['negro'].mean()*100:.1f}%)")
print(f"  Brancos:              {(df['negro']==0).sum():,.0f} ({(df['negro']==0).mean()*100:.1f}%)")
print(f"Anos cobertos:          {sorted(df['Ano'].unique())}")
print(f"UFs:                    {df['UF'].nunique()}")
print(f"UPAs:                   {df['UPA'].nunique():,}")

print("\n--- Gap Salarial por Ano (log-renda media) ---")
gap_ano = (
    df[df['log_renda'].notna()]
    .groupby(['Ano','negro'])['log_renda']
    .mean()
    .unstack()
    .rename(columns={0:'Branco', 1:'Negro'})
)
gap_ano['gap_%'] = (gap_ano['Negro'] / gap_ano['Branco'] - 1) * 100
print(gap_ano.round(3).to_string())

print("\n--- Variaveis Contextuais (Nivel 2 — UPA) ---")
ctx2 = df[['pct_negro_upa','tx_desemprego_upa','media_educ_upa','media_renda_upa']].describe()
print(ctx2.round(3).to_string())

print("\n--- Variaveis Contextuais (Nivel 3 — UF) ---")
ctx3 = df.groupby('UF')[['pct_negro_uf','tx_desemprego_uf','media_educ_uf']].first()
print(ctx3.describe().round(3).to_string())

print("\n--- Correlacao: negro vs contexto de localidade (Nivel 2) ---")
corr = df[['negro','pct_negro_upa','tx_desemprego_upa','media_educ_upa','media_renda_upa']].corr()['negro'].drop('negro')
print(corr.round(4).to_string())

print(f"\nFeatures salvas: data/processed/features.parquet")
