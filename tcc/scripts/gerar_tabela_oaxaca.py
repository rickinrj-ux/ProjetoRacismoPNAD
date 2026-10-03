"""
gerar_tabela_oaxaca.py
======================
Gera a tabela Oaxaca-Blinder do NÚCLEO do TCC em DUAS especificações lado a lado:

  (A) capital humano + contexto de UPA  — sem ocupação (≡ controles do HLM M3)
      → gap "total" e parcela não explicada comparável à literatura (Soares, 2009).
  (B) acesso — (A) + horas, formalidade e grupo CBO como dotações (≡ HLM M4)
      → parcela não explicada *dentro* da ocupação (limite inferior; Oaxaca & Ransom, 1999).

Apresentar as duas é a resposta ao problema do *bad control* (Angrist & Pischke, cap. 3):
ocupação e formalidade são desfechos da própria discriminação, logo (B) não é o gap
total — é o que sobra depois de aceitar a segregação ocupacional como dado.

Twofold com referência nos coeficientes dos brancos e intercepto no não-explicado
(a identidade gap = dotação + coeficiente fecha exatamente).

ERROS-PADRÃO: bootstrap em BLOCOS por UPA (Angrist & Pischke, cap. 8; Cameron &
Miller, 2015) — as observações da mesma UPA são correlacionadas e os regressores de
contexto variam só no nível da UPA. Em vez de reamostrar linhas (7,7 M × 200 reps),
usa-se o fato de que OLS e médias são funções de SOMAS: pré-computam-se, por
(UPA, raça), as estatísticas suficientes X'X, X'y, Σx, Σy e n; cada réplica sorteia
UPAs com reposição (pesos multinomiais) e recombina as somas. É numericamente
idêntico ao bootstrap de blocos por concatenação, e roda em segundos.

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
import time
import numpy as np
import pandas as pd
import patsy
from pathlib import Path
from params import fmt, fmtN

ROOT   = Path(_os.getcwd())
TABLES = ROOT / "outputs" / "tables"
N_BOOT = 500          # réplicas do bootstrap em blocos por UPA (barato: somas pré-computadas)
SEED   = 42

# sem educ_missing desde a correção da escolaridade (VD3004): a cobertura é total
EDUC_F    = "educ_fund_completo + educ_medio_completo + educ_superior_completo + educ_pos_graduacao"
DEMO_F    = "idade_c + idade_sq + sexo_fem + C(Ano)"   # ano: renda deflacionada + efeito de ano
CONTEXT_F = "pct_negro_upa_z + tx_desemprego_upa_z + media_educ_upa_z"
OCC_F     = ("horas_c + emprego_formal + conta_propria + trab_domestico"
             " + ocp_dirigente + ocp_profissional + ocp_tecnico + ocp_administrativo"
             " + ocp_servicos + ocp_agro + ocp_operario + ocp_operador + ocp_ffaa")

ESPECS = {
    "sem_ocupacao": {"rotulo": "Capital humano + contexto (sem ocupação)",
                     "rhs": f"{EDUC_F} + {DEMO_F} + {CONTEXT_F}"},
    "acesso":       {"rotulo": "Acesso (+ horas, formalidade e CBO)",
                     "rhs": f"{EDUC_F} + {DEMO_F} + {CONTEXT_F} + {OCC_F}"},
}

COLS = ["Ano", "negro", "sexo_fem", "idade_c", "idade_sq",
        "educ_fund_completo", "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
        "educ_cat", "pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z",
        "horas_c", "emprego_formal", "conta_propria", "trab_domestico",
        "ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo",
        "ocp_servicos", "ocp_agro", "ocp_operario", "ocp_operador", "ocp_ffaa",
        "log_renda", "renda_bruta", "pea", "UF", "UPA"]
MODEL_COLS = [c for c in COLS if c not in ("educ_cat", "renda_bruta", "pea", "UF")]

print("Carregando features.parquet ...", flush=True)
df = pd.read_parquet(ROOT / "data/processed/features.parquet", columns=COLS)
df["educ_missing"] = df["educ_cat"].isna().astype(int)
df = df[(df["pea"] == 1) & (df["renda_bruta"] > 0) & (df["negro"].notna())].copy()
# dropna nas variáveis do modelo mais amplo: as DUAS especificações usam as MESMAS linhas
# (mesmo gap total), e o OLS e as médias usam as mesmas linhas (identidade fecha).
df = df.dropna(subset=MODEL_COLS).reset_index(drop=True)
df["log_renda"] = df["log_renda"].astype(float)
n_b, n_n = int((df["negro"] == 0).sum()), int((df["negro"] == 1).sum())
print(f"População completa (model-complete): {len(df):,}  (brancos={n_b:,}, negros={n_n:,})", flush=True)

upa_codes, upa_index = pd.factorize(df["UPA"])
G = len(upa_index)
print(f"UPAs (blocos do bootstrap): {G:,}", flush=True)


def suff_stats(X, y, groups, G):
    """Somas por grupo: S_xx[g] = Σ x x', S_xy[g] = Σ x y, S_x[g] = Σ x, S_y[g] = Σ y, n[g]."""
    k = X.shape[1]
    S_xx = np.zeros((G, k, k))
    S_xy = np.zeros((G, k))
    S_x  = np.zeros((G, k))
    S_y  = np.zeros(G)
    n    = np.zeros(G)
    # np.add.at é lento para k×k; acumula por blocos ordenados pelo grupo
    order = np.argsort(groups, kind="stable")
    Xs, ys, gs = X[order], y[order], groups[order]
    bounds = np.flatnonzero(np.diff(gs)) + 1
    starts = np.concatenate([[0], bounds]); ends = np.concatenate([bounds, [len(gs)]])
    for s, e in zip(starts, ends):
        g = gs[s]
        Xg = Xs[s:e]; yg = ys[s:e]
        S_xx[g] = Xg.T @ Xg
        S_xy[g] = Xg.T @ yg
        S_x[g]  = Xg.sum(0)
        S_y[g]  = yg.sum()
        n[g]    = e - s
    return S_xx, S_xy, S_x, S_y, n


def twofold_from_sums(w, st_b, st_n):
    """Twofold OB (ref = brancos) a partir das somas por UPA ponderadas por w (pesos de bootstrap).
    Intercepto no componente não explicado; retorna (gap, dotação, coeficiente)."""
    out = []
    for S_xx, S_xy, S_x, S_y, n in (st_b, st_n):
        XX = np.tensordot(w, S_xx, axes=1)
        Xy = w @ S_xy
        N  = w @ n
        xbar = (w @ S_x) / N
        ybar = (w @ S_y) / N
        beta = np.linalg.solve(XX, Xy)
        out.append((beta, xbar, ybar))
    (bb, xb, yb), (bn, xn, yn) = out
    gap = yb - yn
    # coluna 0 = intercepto (xbar = 1): entra em (cb - cn) como (icb - icn), não em dotação
    ef_dot  = float((xb[1:] - xn[1:]) @ bb[1:])
    ef_coef = float(xn @ (bb - bn))          # inclui intercepto pois xn[0] = 1
    return float(gap), ef_dot, ef_coef


resultados = {}
rng = np.random.default_rng(SEED)
for key, spec in ESPECS.items():
    t0 = time.time()
    y_all, X_all = patsy.dmatrices(f"log_renda ~ {spec['rhs']}", df, return_type="dataframe")
    X = np.ascontiguousarray(X_all.to_numpy(float)); y = y_all.to_numpy(float).ravel()
    mask_b = (df["negro"].to_numpy() == 0)
    st_b = suff_stats(X[mask_b], y[mask_b], upa_codes[mask_b], G)
    st_n = suff_stats(X[~mask_b], y[~mask_b], upa_codes[~mask_b], G)
    del X, y, X_all, y_all

    w1 = np.ones(G)
    gap, ef_dot, ef_coef = twofold_from_sums(w1, st_b, st_n)
    resid = gap - (ef_dot + ef_coef)
    assert abs(resid) < 1e-6, f"identidade violada ({key}): resid={resid}"

    # bootstrap em blocos por UPA: pesos multinomiais (= nº de vezes que a UPA foi sorteada)
    bd, bc, bg = [], [], []
    for _ in range(N_BOOT):
        w = rng.multinomial(G, np.full(G, 1.0 / G)).astype(float)
        try:
            g_, d_, c_ = twofold_from_sums(w, st_b, st_n)
        except np.linalg.LinAlgError:
            continue
        bg.append(g_); bd.append(d_); bc.append(c_)
    se_gap, se_dot, se_coef = np.std(bg, ddof=1), np.std(bd, ddof=1), np.std(bc, ddof=1)
    resultados[key] = dict(rotulo=spec["rotulo"], gap=gap, se_gap=se_gap,
                           ef_dot=ef_dot, se_dot=se_dot, pct_dot=ef_dot / gap * 100,
                           ef_coef=ef_coef, se_coef=se_coef, pct_coef=ef_coef / gap * 100,
                           n_boot=len(bd))
    print(f"[{key}] gap={gap:+.4f} ({se_gap:.4f}) | dotações={ef_dot:+.4f} ({se_dot:.4f}; {ef_dot/gap*100:.1f}%) | "
          f"não explicado={ef_coef:+.4f} ({se_coef:.4f}; {ef_coef/gap*100:.1f}%) | "
          f"reps={len(bd)} | {time.time()-t0:.0f}s", flush=True)
    del st_b, st_n

# CSV (uma linha por especificação)
rows = []
for key, r in resultados.items():
    rows.append({"espec": key, "rotulo": r["rotulo"],
                 "gap_total": r["gap"], "se_gap": r["se_gap"], "gap_pct": (np.exp(r["gap"]) - 1) * 100,
                 "ef_dotacao": r["ef_dot"], "se_dotacao": r["se_dot"], "pct_dotacao": r["pct_dot"],
                 "ef_coeficiente": r["ef_coef"], "se_coeficiente": r["se_coef"], "pct_coeficiente": r["pct_coef"],
                 "n_brancos": n_b, "n_negros": n_n, "n_upas": G, "n_bootstrap": r["n_boot"],
                 "bootstrap": "blocos por UPA (multinomial sobre somas suficientes)"})
pd.DataFrame(rows).to_csv(TABLES / "ob_acesso.csv", index=False, encoding="utf-8")

A, B = resultados["sem_ocupacao"], resultados["acesso"]
tex = rf"""\begin{{table}}[!ht]
\centering
\caption{{Decomposição de Oaxaca--Blinder (\emph{{twofold}}, referência: estrutura de preços
dos brancos) do gap salarial racial em duas especificações. (A)~\emph{{Capital humano +
contexto}}: escolaridade, idade, sexo e contexto de UPA --- os mesmos controles do HLM~M3;
a parcela não explicada é comparável à da literatura. (B)~\emph{{Acesso}}: (A) + horas,
formalidade e grupo CBO tratados como dotações --- a parcela não explicada é a discriminação
\emph{{dentro}} da ocupação, um limite inferior, pois a segregação ocupacional é ela própria
discriminatória \cite{{oaxaca_ransom1999}} (ver o GLMM de acesso, Tabela~\ref{{tab:glmm_glassceil}}).
População completa da PEA com renda positiva ($N = {fmtN(n_b + n_n)}$; {fmtN(G)}~UPAs).
Erros-padrão entre parênteses: bootstrap em blocos por UPA ({A['n_boot']} réplicas).}}
\label{{tab:oaxaca_blinder}}
\resizebox{{\textwidth}}{{!}}{{%
\begin{{tabular}}{{lcccc}}
\toprule
& \multicolumn{{2}}{{c}}{{(A) Sem ocupação}} & \multicolumn{{2}}{{c}}{{(B) Acesso (com ocupação)}} \\
\cmidrule(lr){{2-3}}\cmidrule(lr){{4-5}}
Componente & log-pontos (SE) & \% do gap & log-pontos (SE) & \% do gap \\
\midrule
Gap total (branco $-$ negro) & {fmt(A['gap'],4)} ({fmt(A['se_gap'],4)}) & 100,0 & {fmt(B['gap'],4)} ({fmt(B['se_gap'],4)}) & 100,0 \\
Dotações (características observáveis) & {fmt(A['ef_dot'],4)} ({fmt(A['se_dot'],4)}) & {fmt(A['pct_dot'],1)} & {fmt(B['ef_dot'],4)} ({fmt(B['se_dot'],4)}) & {fmt(B['pct_dot'],1)} \\
Não explicado (retornos / discriminação) & {fmt(A['ef_coef'],4)} ({fmt(A['se_coef'],4)}) & {fmt(A['pct_coef'],1)} & {fmt(B['ef_coef'],4)} ({fmt(B['se_coef'],4)}) & {fmt(B['pct_coef'],1)} \\
\bottomrule
\end{{tabular}}
}}
\par\smallskip
\footnotesize\emph{{Como ler:}} em cada especificação, Dotações $+$ Não explicado $=$ Gap total.
De (A) para (B), parte do ``não explicado'' migra para ``dotações'' porque a ocupação passa a
ser tratada como característica --- é exatamente a parcela da discriminação que opera pela
\emph{{porta de entrada}}, e não pelo salário.
\end{{table}}
"""
(TABLES / "ob_acesso.tex").write_text(tex, encoding="utf-8")
print(f"OK -> {TABLES/'ob_acesso.tex'}", flush=True)
print("=== CONCLUÍDO ===", flush=True)
