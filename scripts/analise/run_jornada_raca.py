"""
run_jornada_raca.py — jornada, hora e subocupação por cor (07/10/2026, para a página "Bairro, porta e topo")
==========================================================================================================
Só para o site: o TCC entregue não usa nada daqui. Contexto: duas propostas sobre jornada no debate eleitoral
de 2026 (remuneração por hora trabalhada; fim da escala 6x1 / 40 horas sem redução de salário). O script NÃO
estima o efeito de nenhuma delas; mede quem está mais exposto a cada uma, por cor.

--microdados  Arquivos brutos da PNAD Contínua (40 trimestres, 2016–2025), ocupados, peso V1028:
              subocupação por insuficiência de horas (VD4004A), horas habituais (VD4031) e efetivas
              (VD4035) por cor e sexo e ano.  -> outputs/tables/jornada_raca_pnad.csv
--hora        Base do TCC (ocupados com renda), efeito fixo de bairro, erro agrupado por UPA:
              diferença racial no rendimento mensal, no rendimento por hora e nas horas, entre vizinhos
              de mesma idade, sexo e escolaridade.  -> outputs/tables/jornada_raca_hora.csv
--territorio  Por estado × capital/região metropolitana/interior: subocupação, jornada e penalidade na hora.
              -> outputs/tables/jornada_raca_territorio.csv
Os microdados extraídos ficam em data/processed/jornada_micro.parquet (cache).
Sem argumento, roda os três. População completa, sem amostra.
"""
import os as _os
import sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
from scipy import stats

RAW = _Path("data/raw")
FEAT = _Path("data/processed/features.parquet")
SAIDA_MICRO = _Path("outputs/tables/jornada_raca_pnad.csv")
SAIDA_HORA = _Path("outputs/tables/jornada_raca_hora.csv")
VARS = ["Ano", "Trimestre", "UF", "V1023", "V1028", "V2007", "V2010", "VD4002", "VD4004A", "VD4031", "VD4035"]
CACHE = _Path("data/processed/jornada_micro.parquet")
SAIDA_TERR = _Path("outputs/tables/jornada_raca_territorio.csv")
AREA = {1: 1, 2: 2, 3: 2, 4: 3}                  # V1023 -> 1 capital, 2 região metropolitana/RIDE, 3 interior
SEMANAS_MES = 52 / 12


def _extrair() -> pd.DataFrame:
    """Ocupados brancos, pretos e pardos dos 40 trimestres; cache em parquet para não reler os zips."""
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    from src.data_ingestion import read_pnadc_zip
    lay = pd.read_parquet(RAW / "layout" / "layout.parquet")
    sub = lay[lay["name"].isin(VARS)].sort_values("start")
    colspecs = [(int(r.start) - 1, int(r.end) - 1) for r in sub.itertuples()]
    nomes = sub["name"].tolist()
    partes = []
    for z in sorted(RAW.glob("PNADC_*.zip")):
        d = read_pnadc_zip(z, colspecs, nomes)
        d = d[d["VD4002"] == "1"]                                   # ocupados
        d = d[d["V2010"].isin(["1", "2", "4"])]
        for c in ("V1028", "VD4031", "VD4035"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
        d["Ano"] = d["Ano"].astype(int)
        d["UF"] = d["UF"].astype(int)
        d["area"] = pd.to_numeric(d["V1023"], errors="coerce").map(AREA)
        d["cor"] = d["V2010"].map({"1": "branco", "2": "preto", "4": "pardo"})
        d["sexo"] = d["V2007"].map({"1": "homens", "2": "mulheres"})
        d["subocup"] = (d["VD4004A"] == "1").astype(float)
        h = d["VD4031"]
        d["h_menos30"] = (h < 30).astype(float)
        d["h_30_39"] = ((h >= 30) & (h < 40)).astype(float)
        d["h_40_44"] = ((h >= 40) & (h <= 44)).astype(float)
        d["h_mais44"] = (h > 44).astype(float)
        d["h_mais40"] = (h > 40).astype(float)
        d["efet_menor"] = (d["VD4035"] < d["VD4031"]).astype(float)
        partes.append(d[["Ano", "UF", "area", "cor", "sexo", "V1028", "subocup", "h_menos30", "h_30_39", "h_40_44",
                         "h_mais44", "h_mais40", "efet_menor", "VD4031"]].dropna(subset=["V1028", "VD4031"]))
        print(f"{z.name}: {len(d):,} ocupados", flush=True)
    d = pd.concat(partes, ignore_index=True)
    d.to_parquet(CACHE, index=False)
    return d


def microdados():
    d = _extrair()
    d["negro"] = np.where(d["cor"] == "branco", "branco", "negro")
    met = ["subocup", "h_menos30", "h_30_39", "h_40_44", "h_mais44", "h_mais40", "efet_menor", "VD4031"]

    def resumo(g, chaves):
        w = g["V1028"]
        out = {m: float(np.average(g[m], weights=w)) * (1 if m == "VD4031" else 100) for m in met}
        out.update(chaves)
        out["n"] = len(g)
        return out

    linhas = []
    for periodo, dd in (("2016-2025", d), ("2025", d[d["Ano"] == 2025])):
        for col in ("cor", "negro"):
            for (k,), g in dd.groupby([col]):
                linhas.append(resumo(g, {"periodo": periodo, "grupo": k, "sexo": "todos"}))
            for (k, s), g in dd.groupby([col, "sexo"]):
                linhas.append(resumo(g, {"periodo": periodo, "grupo": k, "sexo": s}))
    for (a, k), g in d.groupby(["Ano", "negro"]):
        linhas.append(resumo(g, {"periodo": str(a), "grupo": k, "sexo": "todos"}))
    r = pd.DataFrame(linhas).drop_duplicates(subset=["periodo", "grupo", "sexo"])
    r.to_csv(SAIDA_MICRO, index=False)
    print(r[r["sexo"] == "todos"].round(1).to_string(index=False))
    print(f"OK -> {SAIDA_MICRO}")


def hora():
    from run_covid_evento import fe_ols_cluster, EDUC, ANOS
    cols = ["log_renda", "negro", "sexo_fem", "Ano", "UPA", "idade_c", "idade_sq", "horas_trabalhadas"] + EDUC
    d = pd.read_parquet(FEAT, columns=cols)
    d = d[d["log_renda"].notna() & (d["log_renda"] > 0) & (d["horas_trabalhadas"] > 0)].dropna(subset=cols)
    vc = d["UPA"].value_counts()
    d = d[d["UPA"].isin(vc[vc >= 10].index)].reset_index(drop=True)
    d["log_horas_mes"] = np.log(d["horas_trabalhadas"] * SEMANAS_MES)
    d["log_hora"] = d["log_renda"] - d["log_horas_mes"]
    for a in ANOS[1:]:
        d[f"ano_{a}"] = (d["Ano"] == a).astype(np.int8)
    xs = ["negro", "sexo_fem", "idade_c", "idade_sq"] + EDUC + [f"ano_{a}" for a in ANOS[1:]]
    linhas = []
    for desf, rot in (("log_renda", "rendimento mensal"), ("log_hora", "rendimento por hora"),
                      ("log_horas_mes", "horas trabalhadas")):
        b, V, n, G = fe_ols_cluster(d, desf, xs, "UPA")
        se = float(np.sqrt(V.loc["negro", "negro"]))
        linhas.append({"desfecho": desf, "rotulo": rot, "beta": float(b["negro"]), "se": se,
                       "p": float(2 * stats.t.sf(abs(b["negro"] / se), G - 1)),
                       "pct": float((np.exp(b["negro"]) - 1) * 100), "N": n, "n_upa": G})
        print(f"{rot:20s} negro {linhas[-1]['pct']:+.2f}%  (se {se:.4f})", flush=True)
    pd.DataFrame(linhas).to_csv(SAIDA_HORA, index=False)
    print(f"OK -> {SAIDA_HORA}")


def territorio():
    """Por estado × área (0 = todo o estado): subocupação e jornada (microdados, V1028) e penalidade na hora
    (base do TCC, efeito fixo de bairro, erro agrupado por UPA). Grupos pequenos ficam sem estimativa da hora."""
    from run_covid_evento import fe_ols_cluster, EDUC, ANOS
    d = _extrair()
    d["negro"] = (d["cor"] != "branco").astype(int)
    linhas = {}
    for area in (0, 1, 2, 3):
        dd = d if area == 0 else d[d["area"] == area]
        for (uf, ng), g in dd.groupby(["UF", "negro"]):
            w = g["V1028"]; k = "n" if ng else "b"
            r = linhas.setdefault((uf, area), {"uf": uf, "area": area})
            r[f"sub_{k}"] = float(np.average(g["subocup"], weights=w)) * 100
            r[f"h40_{k}"] = float(np.average(g["h_mais40"], weights=w)) * 100
            r[f"h30_{k}"] = float(np.average(g["h_menos30"], weights=w)) * 100
            r[f"n_{k}"] = len(g)
    cols = ["log_renda", "negro", "sexo_fem", "Ano", "UPA", "UF", "V1023", "idade_c", "idade_sq",
            "horas_trabalhadas"] + EDUC
    f = pd.read_parquet(FEAT, columns=cols)
    f = f[f["log_renda"].notna() & (f["log_renda"] > 0) & (f["horas_trabalhadas"] > 0)].dropna(subset=cols)
    vc = f["UPA"].value_counts()
    f = f[f["UPA"].isin(vc[vc >= 10].index)].reset_index(drop=True)
    f["log_hora"] = f["log_renda"] - np.log(f["horas_trabalhadas"] * SEMANAS_MES)
    f["UF"] = f["UF"].astype(str).astype(int)                 # na base do TCC, UF é categoria
    f["area"] = f["V1023"].astype(int).map(AREA)
    for a in ANOS[1:]:
        f[f"ano_{a}"] = (f["Ano"] == a).astype(np.int8)
    xs = ["negro", "sexo_fem", "idade_c", "idade_sq"] + EDUC + [f"ano_{a}" for a in ANOS[1:]]
    for (uf, area), r in sorted(linhas.items()):
        g = f[(f["UF"] == uf) & ((f["area"] == area) if area else True)].reset_index(drop=True)
        if g["UPA"].nunique() < 50 or g["negro"].sum() < 500 or (1 - g["negro"]).sum() < 500:
            continue
        x = [c for c in xs if g[c].std() > 0]
        b, V, n, G = fe_ols_cluster(g, "log_hora", x, "UPA")
        se = float(np.sqrt(V.loc["negro", "negro"]))
        r.update({"hora_pen": float((1 - np.exp(b["negro"])) * 100), "hora_se": se, "hora_N": n, "hora_upas": G})
    out = pd.DataFrame(list(linhas.values()))
    out.to_csv(SAIDA_TERR, index=False)
    print(out.round(1).head(12).to_string(index=False))
    print(f"OK -> {SAIDA_TERR} ({out['hora_pen'].notna().sum()} grupos com estimativa da hora de {len(out)})")


if __name__ == "__main__":
    args = set(_sys.argv[1:]) or {"--microdados", "--hora", "--territorio"}
    if "--hora" in args:
        hora()
    if "--microdados" in args:
        microdados()
    if "--territorio" in args:
        territorio()
