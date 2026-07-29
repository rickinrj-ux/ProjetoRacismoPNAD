"""
gerar_tabela_oaxaca.py
======================
Gera a tabela Oaxaca-Blinder do NÚCLEO do TCC com a especificação de ACESSO
(com ocupação + contexto de UPA), coerente com a narrativa "84% do gap é
composição/acesso, e o acesso às ocupações é ele próprio discriminatório (GLMM)".

Ver tcc/PERICIA.md F1: a tabela estendida `ob_decomposicao.tex` usa um Mincer puro
(sem ocupação) → 24,8% dotações; aqui usamos a especificação completa → ~83%.
As duas coexistem: esta (acesso) para o TCC; aquela (Mincer) para o mestrado.

Twofold com intercepto no componente não-explicado (identidade fecha). Bootstrap
por UF (cluster) para os erros-padrão.

Saída: outputs/tables/ob_acesso.csv | .tex   (label tab:oaxaca_blinder)
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
import statsmodels.formula.api as smf
from pathlib import Path
from params import fmt

ROOT   = Path(__file__).resolve().parents[2]
TABLES = ROOT / "outputs" / "tables"
N_BOOT = 200

COLS = ["negro", "sexo_fem", "idade_c", "idade_sq",
        "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
        "educ_cat", "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
        "horas_c", "emprego_formal", "conta_propria", "trab_domestico",
        "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
        "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa",
        "log_renda", "renda_bruta", "pea", "UF"]

EDUC_F = "educ_medio_completo + educ_superior_completo + educ_pos_graduacao + educ_missing"
DEMO_F = "idade_c + idade_sq + sexo_fem"
CONTEXT_F = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
OCC_F = ("horas_c + emprego_formal + conta_propria + trab_domestico"
         " + ocp_dirigente + ocp_profissional + ocp_tecnico + ocp_administrativo"
         " + ocp_servicos + ocp_agro + ocp_operario + ocp_operador + ocp_ffaa")
FORMULA = f"log_renda ~ {EDUC_F} + {DEMO_F} + {CONTEXT_F} + {OCC_F}"

print("Carregando features.parquet ...", flush=True)
df = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=COLS)
df["educ_missing"] = df["educ_cat"].isna().astype(int)
df = df[(df["pea"] == 1) & (df["renda_bruta"] > 0) & (df["negro"].notna())].copy()
# dropna nas variáveis do modelo: garante que ybar (gap) e o OLS usem AS MESMAS linhas
# (sem isso, ocupacionais com NA são descartadas só pelo OLS → identidade não fecha).
MODEL_COLS = ["log_renda", "negro", "UF",
              "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
              "idade_c", "idade_sq", "sexo_fem",
              "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
              "horas_c", "emprego_formal", "conta_propria", "trab_domestico",
              "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
              "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa"]
df = df.dropna(subset=MODEL_COLS).reset_index(drop=True)
print(f"População completa (model-complete): {len(df):,}", flush=True)


def twofold(d):
    """Twofold OB (ref=brancos), intercepto no não-explicado."""
    db, dn = d[d["negro"] == 0], d[d["negro"] == 1]
    mb = smf.ols(FORMULA, data=db).fit()
    mn = smf.ols(FORMULA, data=dn).fit()
    meanb = pd.Series(mb.model.exog[:, 1:].mean(0), index=mb.model.exog_names[1:])
    meann = pd.Series(mn.model.exog[:, 1:].mean(0), index=mn.model.exog_names[1:])
    cb = mb.params.drop("Intercept", errors="ignore")
    cn = mn.params.drop("Intercept", errors="ignore")
    icb, icn = float(mb.params.get("Intercept", 0.0)), float(mn.params.get("Intercept", 0.0))
    gap = db["log_renda"].mean() - dn["log_renda"].mean()
    ef_dot = float((meanb - meann) @ cb)
    ef_coef = float(meann @ (cb - cn)) + (icb - icn)
    return gap, ef_dot, ef_coef


gap, ef_dot, ef_coef = twofold(df)
resid = gap - (ef_dot + ef_coef)
assert abs(resid) < 1e-5, f"identidade violada: resid={resid}"
pct_dot, pct_coef = ef_dot / gap * 100, ef_coef / gap * 100
print(f"Gap={gap:+.4f} | dotações={ef_dot:+.4f} ({pct_dot:.1f}%) | "
      f"discriminação={ef_coef:+.4f} ({pct_coef:.1f}%)", flush=True)

# Bootstrap por UF (cluster) para SE
print(f"Bootstrap por UF ({N_BOOT} reps) ...", flush=True)
ufs = df["UF"].unique()
rng = np.random.default_rng(42)
bd, bc = [], []
for i in range(N_BOOT):
    sel = rng.choice(ufs, size=len(ufs), replace=True)
    dboot = pd.concat([df[df["UF"] == u] for u in sel], ignore_index=True)
    if (dboot["negro"] == 0).sum() < 100 or (dboot["negro"] == 1).sum() < 100:
        continue
    try:
        _, d_, c_ = twofold(dboot)
        bd.append(d_); bc.append(c_)
    except Exception:
        continue
se_dot, se_coef = (np.std(bd) if bd else np.nan), (np.std(bc) if bc else np.nan)
print(f"SE dotações={se_dot:.4f} | SE discriminação={se_coef:.4f} | reps={len(bd)}", flush=True)

# CSV
pd.DataFrame([{
    "gap_total": gap, "gap_pct": (np.exp(gap) - 1) * 100,
    "ef_dotacao": ef_dot, "se_dotacao": se_dot, "pct_dotacao": pct_dot,
    "ef_coeficiente": ef_coef, "se_coeficiente": se_coef, "pct_coeficiente": pct_coef,
    "n_brancos": int((df["negro"] == 0).sum()), "n_negros": int((df["negro"] == 1).sum()),
    "n_bootstrap": len(bd), "espec": "com_ocupacao_e_contexto",
}]).to_csv(TABLES / "ob_acesso.csv", index=False, encoding="utf-8")

# TeX
tex = rf"""\begin{{table}}[!ht]
\centering
\caption{{Decomposição de Oaxaca--Blinder (twofold) do gap salarial racial --- especificação
de \emph{{acesso}} (com ocupação e contexto de UPA). Efeito dotação: parcela explicada por
diferenças em características observáveis, \emph{{incluindo a posição ocupacional}}. Efeito
coeficiente: parcela não explicada (limite inferior da discriminação salarial \emph{{dentro}}
da ocupação). População completa da PEA; erros-padrão por bootstrap de {len(bd)} replicações
agrupadas por UF. Ressalva (Oaxaca \& Ransom, 1999): tratar a ocupação como dotação tende a
\emph{{subestimar}} a discriminação total, pois a segregação ocupacional é, ela própria,
discriminatória --- daí a complementaridade com o GLMM de acesso (Tabela~\ref{{tab:glmm_glassceil}}).}}
\label{{tab:oaxaca_blinder}}
\begin{{tabular}}{{llcc}}
\toprule
Componente & Magnitude & \% do Gap & SE (bootstrap) \\
\midrule
Gap Total (branco $-$ negro) & {fmt(gap,4)} & 100,0 & --- \\
Efeito Dotação (características, incl.\ ocupação) & {fmt(ef_dot,4)} & {fmt(pct_dot,1)} & ({fmt(se_dot,4)}) \\
Efeito Coeficiente (não explicado / discriminação) & {fmt(ef_coef,4)} & {fmt(pct_coef,1)} & ({fmt(se_coef,4)}) \\
\bottomrule
\end{{tabular}}
\end{{table}}
"""
(TABLES / "ob_acesso.tex").write_text(tex, encoding="utf-8")
print(f"OK -> {TABLES/'ob_acesso.tex'}", flush=True)
print("=== CONCLUÍDO ===", flush=True)
