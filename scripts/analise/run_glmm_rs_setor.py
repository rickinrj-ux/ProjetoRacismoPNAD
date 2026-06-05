"""
run_glmm_rs_setor.py
====================
AVALIAÇÃO: (1) random slope de `negro` em TODOS os desfechos do GLMM (acesso) por
UF, e (2) heterogeneidade do teto de vidro (glass ceiling) por estado × setor
(público vs privado).

CONTEXTO METODOLÓGICO
---------------------
O random slope foi estimado no HLM (salário) — aqui completamos a simetria no
GLMM (acesso). Como `lme4` (glmer) não está instalado neste ambiente, usamos o
mesmo proxy validado no HLM: logísticas por UF (no-pooling) + agregação
meta-analítica. O teste de Cochran Q é o equivalente direto do LRT de τ²₁=0:

    β_j   = log-odds de `negro` no desfecho, na UF j (controlado)
    Q     = Σ w_j (β_j − β̄)²,  w_j = 1/SE_j²,  β̄ = Σw_jβ_j / Σw_j
    Q ~ χ²(k−1) sob H0 (efeito homogêneo entre UFs)
    I²    = max(0, (Q−(k−1))/Q)·100      (% da variação que é heterogeneidade real)
    τ²    = max(0, (Q−(k−1))/(Σw − Σw²/Σw))   (DerSimonian-Laird)

Desfechos (idênticos a run_glmm_glassceil.py):
    ocp_qualif (CBO 1–4), y_top20 (quintil renda), y_top10 (decil renda)

Especificação por UF (nível-1, igual ao GLMM M2 dentro da UF):
    negro + sexo_fem + idade_c + idade_sq + 3 dummies educ + 4 contextuais UPA

SAÍDA:
    outputs/tables/glmm_rs_uf.csv          — β/OR de negro por UF, por desfecho
    outputs/tables/glmm_rs_heterogen.csv   — Q, I², τ², amplitude OR por desfecho
    outputs/tables/glassceil_uf_setor.csv  — penalidade por UF × setor (ocp_qualif)
    outputs/figures/glmm_rs_setor.png      — heterogeneidade + público × privado
    logs/glmm_rs_setor.log
"""

# --- bootstrap raiz do projeto (reorg estrutura) ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys, logging, time, warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")

ROOT    = Path.cwd()
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TAB = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
Path("outputs/_logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S",
    handlers=[logging.FileHandler("outputs/_logs/glmm_rs_setor.log", encoding="utf-8"),
              logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)

UF_REG = {11:"N",12:"N",13:"N",14:"N",15:"N",16:"N",17:"N",
          21:"NE",22:"NE",23:"NE",24:"NE",25:"NE",26:"NE",27:"NE",28:"NE",29:"NE",
          31:"SE",32:"SE",33:"SE",35:"SE",41:"S",42:"S",43:"S",
          50:"CO",51:"CO",52:"CO",53:"CO"}
SIGLA = {11:"RO",12:"AC",13:"AM",14:"RR",15:"PA",16:"AP",17:"TO",21:"MA",22:"PI",
         23:"CE",24:"RN",25:"PB",26:"PE",27:"AL",28:"SE",29:"BA",31:"MG",32:"ES",
         33:"RJ",35:"SP",41:"PR",42:"SC",43:"RS",50:"MS",51:"MT",52:"GO",53:"DF"}

IND = ("negro + sexo_fem + idade_c + idade_sq + educ_medio_completo + "
       "educ_superior_completo + educ_pos_graduacao + pct_negro_upa_z + "
       "tx_desemprego_upa_z + media_educ_upa_z + media_renda_upa_z")
COLS = ["negro","sexo_fem","idade_c","idade_sq","educ_medio_completo",
        "educ_superior_completo","educ_pos_graduacao","pct_negro_upa_z",
        "tx_desemprego_upa_z","media_educ_upa_z","media_renda_upa_z","setor_publico",
        "ocp_dirigente","ocp_profissional","ocp_tecnico","ocp_administrativo",
        "renda_bruta","pea","UF"]
MIN_N, MIN_EVENTS = 800, 30   # célula mínima para logística estável


# ── Carga / desfechos (reaproveita run_glmm_glassceil.py) ────────────────────
def load():
    log.info("Carregando população completa ...")
    df = pd.read_parquet(ROOT/"data/processed/features.parquet", columns=COLS)
    df = df[(df["pea"]==1) & df["renda_bruta"].notna() & (df["renda_bruta"]>0)
            & df["negro"].notna() & df["sexo_fem"].notna()
            & df["media_renda_upa_z"].notna() & df["media_educ_upa_z"].notna()].copy()
    df["ocp_qualif"] = ((df.get("ocp_dirigente",0)==1)|(df.get("ocp_profissional",0)==1)
                        |(df.get("ocp_tecnico",0)==1)|(df.get("ocp_administrativo",0)==1)).astype(int)
    df["y_top20"] = (df["renda_bruta"]>=df["renda_bruta"].quantile(0.80)).astype(int)
    df["y_top10"] = (df["renda_bruta"]>=df["renda_bruta"].quantile(0.90)).astype(int)
    for c in ["educ_medio_completo","educ_superior_completo","educ_pos_graduacao","setor_publico"]:
        df[c] = df[c].fillna(0).astype(int)
    df["UF_int"] = df["UF"].astype(int)
    log.info(f"  N efetivo: {len(df):,} | UFs: {df['UF_int'].nunique()}")
    return df


# ── β_negro por UF (logística) para um desfecho, opcionalmente num subconjunto ─
def betas_por_uf(df, desfecho):
    rows = []
    for uf, g in df.groupby("UF_int", observed=True):
        ev = g[desfecho].sum()
        if len(g) < MIN_N or ev < MIN_EVENTS or ev > len(g)-MIN_EVENTS:
            continue
        try:
            r = smf.logit(f"{desfecho} ~ {IND}", data=g).fit(disp=0, maxiter=60)
            b, se = float(r.params["negro"]), float(r.bse["negro"])
            if not (np.isfinite(b) and np.isfinite(se) and se < 5):
                continue
            rows.append({"UF":uf,"sigla":SIGLA[uf],"regiao":UF_REG[uf],
                         "beta":b,"se":se,"OR":float(np.exp(b)),"n":len(g),"eventos":int(ev)})
        except Exception:
            continue
    return pd.DataFrame(rows)


# ── Estatísticas meta-analíticas de heterogeneidade (Cochran Q / I² / τ²) ─────
def heterogeneidade(d, rotulo):
    b, se = d["beta"].to_numpy(), d["se"].to_numpy()
    w = 1.0/se**2
    bbar = float(np.sum(w*b)/np.sum(w))
    Q = float(np.sum(w*(b-bbar)**2))
    k = len(b); dfree = k-1
    p = float(stats.chi2.sf(Q, dfree))
    I2 = max(0.0, (Q-dfree)/Q)*100 if Q > 0 else 0.0
    C = np.sum(w) - np.sum(w**2)/np.sum(w)
    tau2 = max(0.0, (Q-dfree)/C) if C > 0 else 0.0
    sig = "***" if p<0.001 else ("**" if p<0.01 else ("*" if p<0.05 else "ns"))
    res = {"rotulo":rotulo,"k_UFs":k,"OR_pooled":round(float(np.exp(bbar)),4),
           "OR_min":round(float(d["OR"].min()),4),"OR_max":round(float(d["OR"].max()),4),
           "Q":round(Q,1),"p_Q":p,"sig":sig,"I2_pct":round(I2,1),
           "tau2":round(tau2,5),"SD_entre_UF":round(float(np.sqrt(tau2)),4)}
    log.info(f"  [{rotulo}] OR_pool={res['OR_pooled']:.3f} | OR {res['OR_min']:.2f}–{res['OR_max']:.2f} "
             f"| Q={Q:.0f} {sig} | I²={I2:.0f}% | τ²={tau2:.4f} (k={k})")
    return res


def main():
    t0 = time.time()
    log.info("="*64); log.info("AVALIAÇÃO: random slope GLMM por UF + glass ceiling UF × setor"); log.info("="*64)
    df = load()
    desfechos = ["ocp_qualif","y_top20","y_top10"]

    # ── PARTE 1: heterogeneidade do efeito de negro por UF, todos os desfechos ──
    log.info("\n══ PARTE 1 — Random slope (proxy) por UF em todos os desfechos GLMM ══")
    rs_rows, het_rows = [], []
    for y in desfechos:
        d = betas_por_uf(df, y)
        d["desfecho"] = y
        rs_rows.append(d)
        het_rows.append(heterogeneidade(d, y))
    pd.concat(rs_rows).to_csv(OUT_TAB/"glmm_rs_uf.csv", index=False)
    df_het = pd.DataFrame(het_rows)
    df_het.to_csv(OUT_TAB/"glmm_rs_heterogen.csv", index=False)

    # ── PARTE 2: glass ceiling por UF × setor (ocp_qualif) ──────────────────────
    log.info("\n══ PARTE 2 — Glass ceiling por setor (público × privado) — ocp_qualif ══")
    setor_rows, comp = [], {}
    for nome, sub in [("Privado", df[df["setor_publico"]==0]),
                      ("Público", df[df["setor_publico"]==1])]:
        d = betas_por_uf(sub, "ocp_qualif")
        d["setor"] = nome
        setor_rows.append(d)
        comp[nome] = heterogeneidade(d, f"ocp_qualif — {nome}")
    pd.concat(setor_rows).to_csv(OUT_TAB/"glassceil_uf_setor.csv", index=False)

    figura(df_het, pd.concat(rs_rows), pd.concat(setor_rows), comp)

    # ── Veredito ────────────────────────────────────────────────────────────────
    log.info("\n"+"="*64); log.info("VEREDITO")
    any_het = (df_het["p_Q"] < 0.05).any()
    log.info(f"  Random slope GLMM agrega? Heterogeneidade significativa em "
             f"{(df_het['p_Q']<0.05).sum()}/{len(df_het)} desfechos.")
    for _,r in df_het.iterrows():
        log.info(f"    {r['rotulo']}: I²={r['I2_pct']:.0f}% ({r['sig']}) — "
                 f"OR varia {r['OR_min']:.2f}→{r['OR_max']:.2f} entre UFs")
    pr, pb = comp.get("Privado",{}), comp.get("Público",{})
    if pr and pb:
        log.info(f"  Glass ceiling por setor (ocp_qualif): "
                 f"OR_pool Privado={pr['OR_pooled']:.3f} (I²={pr['I2_pct']:.0f}%) vs "
                 f"Público={pb['OR_pooled']:.3f} (I²={pb['I2_pct']:.0f}%)")
        atenua = pb['OR_pooled'] > pr['OR_pooled']
        homog  = pb['I2_pct'] < pr['I2_pct']
        log.info(f"    → setor público {'ATENUA' if atenua else 'NÃO atenua'} a barreira de acesso "
                 f"e é {'MAIS homogêneo' if homog else 'igual/menos homogêneo'} entre UFs.")
    log.info(f"  Tempo: {(time.time()-t0)/60:.1f} min."); log.info("="*64)


# ── Figura ───────────────────────────────────────────────────────────────────
def figura(df_het, rs_all, setor_all, comp):
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
    cores = {"ocp_qualif":"#2166AC","y_top20":"#D01C8B","y_top10":"#E66101"}

    # (a) OR de negro por UF, por desfecho (dispersão = heterogeneidade)
    ax = axes[0]
    for y in ["ocp_qualif","y_top20","y_top10"]:
        d = rs_all[rs_all["desfecho"]==y].sort_values("OR")
        ax.scatter(d["OR"], range(len(d)), s=22, color=cores[y], alpha=0.75,
                   label=f"{y} (I²={df_het.loc[df_het['rotulo']==y,'I2_pct'].values[0]:.0f}%)")
    ax.axvline(1.0, color="gray", ls="--", lw=1)
    ax.set_xlabel("Odds Ratio de negro (acesso) por UF — <1 = barreira", fontsize=10)
    ax.set_ylabel("UFs (ordenadas por OR)", fontsize=10)
    ax.set_title("Random slope (proxy): a barreira de acesso varia entre estados",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=9, loc="lower right"); ax.grid(alpha=0.3, axis="x")

    # (b) Público × Privado: OR de negro (ocp_qualif) por UF
    ax2 = axes[1]
    for nome, cor in [("Privado","#C62828"),("Público","#2E7D32")]:
        d = setor_all[setor_all["setor"]==nome].sort_values("OR")
        ax2.scatter(d["OR"], range(len(d)), s=26, color=cor, alpha=0.75,
                    label=f"{nome} (OR_pool={comp[nome]['OR_pooled']:.2f}, I²={comp[nome]['I2_pct']:.0f}%)")
    ax2.axvline(1.0, color="gray", ls="--", lw=1)
    ax2.set_xlabel("Odds Ratio de negro (acesso a cargo qualificado) por UF", fontsize=10)
    ax2.set_ylabel("UFs (ordenadas por OR)", fontsize=10)
    ax2.set_title("Glass ceiling de acesso: público × privado, por estado",
                  fontsize=11, fontweight="bold")
    ax2.legend(fontsize=9, loc="lower right"); ax2.grid(alpha=0.3, axis="x")

    plt.tight_layout()
    plt.savefig(OUT_FIG/"glmm_rs_setor.png", dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  glmm_rs_setor.png salvo.")


if __name__ == "__main__":
    main()
