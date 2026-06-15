"""
pericia_cruzada.py
==================
Auditoria cruzada NUMÉRICA das tabelas do projeto. Checa identidades de
decomposição (em valor absoluto, sem ambiguidade de base %) e consistência
cruzada de números-chave entre tabelas e params.py.

Não altera nada — só imprime um laudo PASS/FAIL com evidências.
Saída: stdout (redirecionar para tcc/pericia_cruzada_resultado.txt).
"""

# --- bootstrap raiz do projeto ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import numpy as np
import pandas as pd
from pathlib import Path

T = Path("outputs/tables")
TOL = 1e-3
ok = lambda c: "PASS" if c else "**FALHA**"


def hr(t):
    print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)


def chk(nome, cond, detalhe=""):
    print(f"  [{ok(cond)}] {nome}" + (f"  {detalhe}" if detalhe else ""))
    return cond


# ── 1. Identidades de decomposição ────────────────────────────────────────────
hr("1. IDENTIDADES DE DECOMPOSIÇÃO (soma das partes == total)")

# 1a. Oaxaca agregado (ambas especificações)
for f in ["ob_decomposicao.csv", "ob_acesso.csv"]:
    p = T / f
    if not p.exists():
        print(f"  [n/d] {f} ausente"); continue
    d = pd.read_csv(p).iloc[0]
    soma = d["ef_dotacao"] + d["ef_coeficiente"]
    chk(f"{f}: dotação+coef == gap",
        abs(soma - d["gap_total"]) < TOL,
        f"({d['ef_dotacao']:.4f}+{d['ef_coeficiente']:.4f}={soma:.4f} vs gap={d['gap_total']:.4f})")

# 1b. RIF-OB por quantil: end+ret+inter == gap_rif?  e  end+ret == gap_rif?
p = T / "rif_ob_decomposicao.csv"
if p.exists():
    d = pd.read_csv(p)
    for _, r in d.iterrows():
        s3 = r["end"] + r["ret"] + r["inter"]
        s2 = r["end"] + r["ret"]
        c3 = abs(s3 - r["gap_rif"]) < TOL
        c2 = abs(s2 - r["gap_rif"]) < TOL
        chk(f"RIF {r['q_label']}: threefold end+ret+inter==gap_rif", c3,
            f"(soma3={s3:.4f} vs {r['gap_rif']:.4f}; end+ret={s2:.4f})")
        if not c3 and c2:
            print(f"        -> 'inter'={r['inter']:.4f} é ÓRFÃO (end+ret já = gap_rif)")

# 1c. Interseccional 4 grupos
p = T / "interseccional_ob4grupos.csv"
if p.exists():
    d = pd.read_csv(p)
    for _, r in d.iterrows():
        s3 = r["end"] + r["ret"] + r["inter"]
        s2 = r["end"] + r["ret"]
        c3 = abs(s3 - r["gap"]) < TOL
        c2 = abs(s2 - r["gap"]) < TOL
        chk(f"OB4 {r['grupo']}: end+ret+inter==gap", c3,
            f"(soma3={s3:.4f} vs gap={r['gap']:.4f})")
        if not c3 and c2:
            print(f"        -> 'inter'={r['inter']:.4f} ÓRFÃO (end+ret={s2:.4f}=gap)")
        # pct também
        sp = r["end_pct"] + r["ret_pct"] + r["inter_pct"]
        chk(f"OB4 {r['grupo']}: end%+ret%+inter% == 100", abs(sp - 100) < 0.5,
            f"(={sp:.1f}%)")

# ── 2. Consistência cruzada params <-> tabelas ────────────────────────────────
hr("2. CONSISTÊNCIA params.py  <->  TABELAS")
import params as pm
P = pm.P

glm = pd.read_csv(T / "glmm_glassceil_full.csv")
def or_of(des, mod):
    r = glm[(glm.desfecho == des) & (glm.modelo == mod)]
    return float(r["OR_negro"].iloc[0]) if len(r) else np.nan
pairs = [("OR_OCP_M2", or_of("ocp_qualif", "M2")),
         ("OR_TOP20_M2", or_of("y_top20", "M2")),
         ("OR_TOP10_M2", or_of("y_top10", "M2")),
         ("OR_OCP_M1", or_of("ocp_qualif", "M1"))]
for k, v in pairs:
    if k in P:
        chk(f"params[{k}] == glmm_glassceil_full", abs(P[k] - v) < 5e-3,
            f"(params={P[k]} vs tabela={v:.4f})")

# GAP_PCT vs ob gap
ob = pd.read_csv(T / "ob_decomposicao.csv").iloc[0]
chk("params[GAP_PCT] ~ ob_decomposicao gap_pct", abs(P.get("GAP_PCT", -1) - ob["gap_pct"]) < 1.0,
    f"(params={P.get('GAP_PCT')} vs ob={ob['gap_pct']:.1f})")

# ── 3. Dois gap_decomposicao divergentes ──────────────────────────────────────
hr("3. DUPLICIDADE: gap_decomposicao vs gap_decomposicao_serie_completo")
a = pd.read_csv(T / "gap_decomposicao.csv")
b = pd.read_csv(T / "gap_decomposicao_serie_completo.csv")
ga = a.iloc[0]["Gap %"]; gb = b.iloc[0]["Gap%"]
print(f"  gap_decomposicao M1 Gap%        = {ga}")
print(f"  serie_completo   M1 Gap%        = {gb}")
chk("M1 coincide entre os dois arquivos", abs(ga - gb) < 0.5,
    "(se FALHA: são períodos/amostras distintos — exigem rótulo claro)")

# ── 4. R² do ML ───────────────────────────────────────────────────────────────
hr("4. ML: R² e overfit")
ml = pd.read_csv(T / "ml_performance.csv")
print(ml.to_string(index=False))
for _, r in ml.iterrows():
    chk(f"{r['Modelo']}: overfit treino-teste < 0.05",
        abs(r["R²"] - r["R2_treino"]) < 0.05, f"(gap={r['gap_overfit']})")

# ── 5. Nakagawa R² / LRT ──────────────────────────────────────────────────────
hr("5. HLM Nakagawa R² / LRT")
nk = pd.read_csv(T / "hlm_nakagawa_r2.csv")
print(nk.to_string(index=False))
for _, r in nk.iterrows():
    lrt = str(r["LRT_vs_prev"])
    if "inf" in lrt.lower() or (str(r["p_LRT"]).strip() in ("1.0000e+00", "1.0")):
        print(f"  [**ATENÇÃO**] {r['Modelo']}: LRT={r['LRT_vs_prev']} p={r['p_LRT']} (valor degenerado)")

print("\n=== AUDITORIA CONCLUÍDA ===")
