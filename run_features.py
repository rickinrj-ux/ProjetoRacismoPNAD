"""
run_features.py
Executa feature engineering no dado disponivel e imprime diagnostico completo.
"""
import sys, logging
sys.path.insert(0, "src")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")

from feature_engineering import build_features
import numpy as np

df = build_features(save=True)

print("\n" + "="*60)
print("DIAGNOSTICO DE FEATURES — 3 NIVEIS")
print("="*60)

print(f"\nAmostra total (negro binario): {len(df):,} obs.")
print(f"  Negros (Preta+Parda): {df['negro'].sum():,.0f} ({df['negro'].mean()*100:.1f}%)")
print(f"  Brancos:              {(df['negro']==0).sum():,.0f} ({(df['negro']==0).mean()*100:.1f}%)")

print("\n-- Nivel 1: Variaveis Individuais --")
print(df[["log_renda","idade","educ_ord","empregado","sexo_fem"]].describe().round(3))

print("\n-- Gap Salarial Bruto por Raca --")
gap = df.groupby("negro")["log_renda"].agg(["mean","median","count"])
gap.index = gap.index.map({0:"Branco", 1:"Negro"})
gap["gap_%"] = ((gap["mean"] / gap.loc["Branco","mean"]) - 1) * 100
print(gap.round(3))

print("\n-- Nivel 2: Contexto de Localidade (UPA) --")
upa_ctx = df[["pct_negro_upa","tx_desemprego_upa","media_educ_upa","media_renda_upa"]].describe()
print(upa_ctx.round(3))

print("\n-- Nivel 3: Contexto Estadual (UF) --")
uf_ctx = df.groupby("UF")[["pct_negro_uf","tx_desemprego_uf","media_educ_uf"]].first()
print(uf_ctx.describe().round(3))

print("\n-- Correlacao: negro vs. variaveis contextuais de Nivel 2 --")
ctx_cols = ["pct_negro_upa","tx_desemprego_upa","media_educ_upa","media_renda_upa"]
corr = df[["negro"] + ctx_cols].corr()["negro"].drop("negro")
print(corr.round(4))
print("\nInterpretacao: correlacao positiva entre negro e pct_negro_upa confirma")
print("segregacao residencial — negros vivem em areas com maior concentracao racial.")

print("\nFeatures salvas em data/processed/features.parquet")
