"""
run_model_test.py
Teste completo do HLM 3-niveis com todos os dados de 2023 T1.
Com 1 trimestre: ~120k obs, ~8k UPAs, 27 UFs — estrutura ideal para vc_formula.
"""
import sys, logging, warnings
sys.path.insert(0, "src")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
warnings.filterwarnings("ignore")

import numpy as np
from multilevel_model import run_models

print("\n=== HLM 3-NIVEIS — 2023 T1 (dataset completo) ===\n")

models = run_models(sample_frac=None, save=True)

print("\n" + "="*90)
print("RESUMO DE CONVERGENCIA E ICC")
print("="*90)
print(f"{'Modelo':<22} {'N obs':>10} {'UPAs':>7} {'sigma2':>8} {'tau2_UPA':>10} {'tau2_UF':>9} {'ICC_UPA':>9} {'ICC_UF':>8}")
print("-"*90)
for nome, m in models.items():
    print(
        f"{nome:<22} {m.n_obs:>10,} {m.n_upa:>7,}"
        f" {m.var_resid:>8.4f} {m.var_upa:>10.4f} {m.var_uf:>9.4f}"
        f" {m.icc_upa:>9.4f} {m.icc_uf:>8.4f}"
    )

print("\n" + "="*70)
print("GAP SALARIAL RACIAL — DECOMPOSICAO ENTRE MODELOS")
print("="*70)
print(f"{'Modelo':<22} {'beta_negro':>12} {'SE':>8} {'p-valor':>10} {'Gap %':>8} {'Sig':>5}")
print("-"*70)
ref_coef = None
for nome, m in models.items():
    coef = m.result.params.get("negro", np.nan)
    se   = m.result.bse.get("negro",   np.nan)
    pval = m.result.pvalues.get("negro", np.nan)
    if np.isnan(coef):
        print(f"{nome:<22} {'—':>12}")
        continue
    gap   = (np.exp(coef) - 1) * 100
    stars = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else "ns"
    print(f"{nome:<22} {coef:>12.4f} {se:>8.4f} {pval:>10.6f} {gap:>7.2f}% {stars:>5}")
    if ref_coef is None and not np.isnan(coef):
        ref_coef = coef

if ref_coef is not None:
    m3_coef = models.get("M3_Completo")
    if m3_coef:
        b3 = m3_coef.result.params.get("negro", np.nan)
        mediacao = abs(ref_coef - b3) / abs(ref_coef) * 100
        print(f"\nMediacao contextual total (M1->M3): {mediacao:.1f}% do gap bruto")
        print("= fracao do gap salarial racial explicada pelo local de moradia + estado.")
