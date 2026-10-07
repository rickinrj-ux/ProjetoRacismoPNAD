"""
run_colorismo_genero.py — colorismo por sexo (07/10/2026, para a página "Bairro, porta e topo")
================================================================================================
Pardos e pretos contra brancos do MESMO sexo, dentro do mesmo bairro, com os controles do M3:

    y_i = β_pardo·pardo_i + β_preto·preto_i + X_i'θ + Σ_t γ_t·1(Ano=t) + α_UPA + ε_i      (por sexo)

X = idade, idade², escolaridade cumulativa, log horas (salário). Efeito fixo de bairro (UPA), erro
agrupado por UPA — o mesmo desenho do estudo de evento da COVID (run_covid_evento.fe_ols_cluster).
Desfechos: log do rendimento (penalidade em % de renda) e cargo qualificado, CBO 1–4 (modelo de
probabilidade linear: diferença em pontos percentuais; o GLMM do TCC usa razão de chances).
Cor pela V2010 (1 branca, 2 preta, 4 parda; amarelos e indígenas fora). Base populacional, sem amostra.
Também: todos os grupos contra o homem branco (salário), desfecho "log_renda_ref_hb", sexo "todos".
Saída: outputs/tables/colorismo_genero.csv
"""
import os as _os
import sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, str(_Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from scipy import stats

from run_covid_evento import fe_ols_cluster, EDUC, ANOS

FEAT = _Path("data/processed/features.parquet")
SAIDA = _Path("outputs/tables/colorismo_genero.csv")


def main():
    OCP = ["ocp_dirigente", "ocp_profissional", "ocp_tecnico", "ocp_administrativo"]
    cols = ["log_renda", "V2010", "sexo_fem", "Ano", "UPA", "idade_c", "idade_sq", "log_horas"] + OCP + EDUC
    d = pd.read_parquet(FEAT, columns=cols)
    d = d[d["log_renda"].notna() & (d["log_renda"] > 0) & d["V2010"].isin([1, 2, 4])]
    d = d.dropna(subset=[c for c in cols if c not in OCP])
    vc = d["UPA"].value_counts()
    d = d[d["UPA"].isin(vc[vc >= 10].index)].reset_index(drop=True)
    d["pardo"] = (d["V2010"] == 4).astype(np.int8)
    d["preto"] = (d["V2010"] == 2).astype(np.int8)
    # cargo qualificado = CBO 1–4, a mesma definição do GLMM do TCC (run_glmm_glassceil.py)
    d["qualif"] = (d[OCP].fillna(0) == 1).any(axis=1).astype(float)
    for a in ANOS[1:]:
        d[f"ano_{a}"] = (d["Ano"] == a).astype(np.int8)
    anos = [f"ano_{a}" for a in ANOS[1:]]
    ctrl = ["idade_c", "idade_sq"] + EDUC

    linhas = []
    for fem, rot in ((0, "homens"), (1, "mulheres")):
        g = d[d["sexo_fem"] == fem].reset_index(drop=True)
        for desf, xs in (("log_renda", ctrl + ["log_horas"]), ("qualif", ctrl)):
            b, V, n, G = fe_ols_cluster(g, desf, ["pardo", "preto"] + xs + anos, "UPA")
            for grp in ("pardo", "preto"):
                se = float(np.sqrt(V.loc[grp, grp]))
                val = (1 - np.exp(b[grp])) * 100 if desf == "log_renda" else -b[grp] * 100
                linhas.append({"sexo": rot, "grupo": grp, "desfecho": desf, "beta": float(b[grp]), "se": se,
                               "p": float(2 * stats.t.sf(abs(b[grp] / se), G - 1)),
                               "valor": float(val), "N": n, "n_upa": G})
            print(f"{rot:9s} {desf:9s} pardo {linhas[-2]['valor']:.2f} | preto {linhas[-1]['valor']:.2f} | N {n:,}",
                  flush=True)
    # Segunda leitura para a página: todos contra o HOMEM BRANCO (mesmo desenho, salário). Mostra que a
    # penalidade racial maior do homem preto convive com renda menor da mulher parda (cor + gênero).
    grupos = {"brancas": (1, 1), "pretos": (2, 0), "pardos": (4, 0), "pretas": (2, 1), "pardas": (4, 1)}
    for g, (cor, fem) in grupos.items():
        d[g] = ((d["V2010"] == cor) & (d["sexo_fem"] == fem)).astype(np.int8)
    b, V, n, G = fe_ols_cluster(d, "log_renda", list(grupos) + ctrl + ["log_horas"] + anos, "UPA")
    for g in grupos:
        se = float(np.sqrt(V.loc[g, g]))
        linhas.append({"sexo": "todos", "grupo": g, "desfecho": "log_renda_ref_hb", "beta": float(b[g]), "se": se,
                       "p": float(2 * stats.t.sf(abs(b[g] / se), G - 1)),
                       "valor": float((1 - np.exp(b[g])) * 100), "N": n, "n_upa": G})
    print("contra o homem branco: " + " | ".join(f"{r['grupo']} {r['valor']:.1f}" for r in linhas[-5:]), flush=True)
    pd.DataFrame(linhas).to_csv(SAIDA, index=False)
    print(f"OK -> {SAIDA}")


if __name__ == "__main__":
    main()
