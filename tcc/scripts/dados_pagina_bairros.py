# -*- coding: utf-8 -*-
"""Dados dos 40.728 bairros (UPAs) para o painel de pontos da página "Bairro, porta e topo".

Cada bairro vira um ponto. A cor é a penalidade racial estimada nele pelo M3 com inclinação
aleatória de negro por UPA (β médio + u1j, os BLUPs do modelo — estimativas encolhidas para a
média, não medidas diretas do bairro). A renda-base do bairro é u0j.

Posição: a PNAD pública não informa o município da UPA, só o estado e a situação (V1023: capital,
resto da região metropolitana, resto da RIDE, resto da UF). O ponto vai para dentro do contorno
do seu estado (malha do IBGE): perto da capital real, no entorno metropolitano ou espalhado pelo
interior. A posição dentro do estado é ilustrativa — a página diz isso no "Como ler".

Saída: dict para a página e outputs/tables/pagina_bairros_resumo.csv (os números do texto).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "outputs" / "tables"
GEO = Path(__file__).with_name("dados_web") / "br_uf_ibge.json"

SIGLA = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO", 21: "MA", 22: "PI",
         23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA", 31: "MG", 32: "ES",
         33: "RJ", 35: "SP", 41: "PR", 42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}
# capitais (longitude, latitude)
CAPITAL = {11: (-63.90, -8.76), 12: (-67.81, -9.97), 13: (-60.02, -3.12), 14: (-60.67, 2.82),
           15: (-48.50, -1.46), 16: (-51.07, 0.03), 17: (-48.33, -10.18), 21: (-44.30, -2.53),
           22: (-42.80, -5.09), 23: (-38.54, -3.73), 24: (-35.21, -5.79), 25: (-34.86, -7.12),
           26: (-34.88, -8.05), 27: (-35.73, -9.65), 28: (-37.07, -10.91), 29: (-38.50, -12.97),
           31: (-43.94, -19.92), 32: (-40.31, -20.32), 33: (-43.17, -22.91), 35: (-46.63, -23.55),
           41: (-49.27, -25.43), 42: (-48.55, -27.60), 43: (-51.23, -30.03), 50: (-54.62, -20.47),
           51: (-56.10, -15.60), 52: (-49.25, -16.68), 53: (-47.88, -15.79)}


def _aneis(geom: dict) -> list[np.ndarray]:
    polis = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [np.asarray(p[0], dtype=float) for p in polis]          # só o anel externo


def _dentro(px: np.ndarray, py: np.ndarray, aneis: list[np.ndarray]) -> np.ndarray:
    """Ponto em polígono por paridade de cruzamentos (vetorizado nos pontos)."""
    res = np.zeros(px.shape, dtype=bool)
    for a in aneis:
        x0, y0 = a[:-1, 0], a[:-1, 1]
        x1, y1 = a[1:, 0], a[1:, 1]
        cruza = np.zeros(px.shape, dtype=bool)
        for xa, ya, xb, yb in zip(x0, y0, x1, y1):
            c = ((ya > py) != (yb > py)) & (px < (xb - xa) * (py - ya) / (yb - ya + 1e-12) + xa)
            cruza ^= c
        res |= cruza
    return res


def _sortear(n, aneis, rng, centro=None, dp=None):
    """n pontos dentro do estado: uniformes, ou em torno de `centro` com desvio `dp` (graus)."""
    tudo = np.vstack(aneis)
    lo, hi = tudo.min(0), tudo.max(0)
    out = np.empty((0, 2))
    tent = 0
    while len(out) < n and tent < 60:
        k = max(4 * (n - len(out)), 64)
        if centro is None:
            c = rng.uniform(lo, hi, size=(k, 2))
        else:
            c = np.asarray(centro) + rng.normal(0, dp, size=(k, 2))
        ok = _dentro(c[:, 0], c[:, 1], aneis)
        out = np.vstack([out, c[ok]])
        tent += 1
    if len(out) < n:                                     # costa recortada: completa no centro
        out = np.vstack([out, np.repeat([centro or tudo.mean(0)], n - len(out), axis=0)])
    return out[:n]


def dados(beta_rs: float, semente: int = 42) -> dict:
    geo = json.loads(GEO.read_text(encoding="utf-8"))
    aneis = {int(f["properties"]["codarea"]): _aneis(f["geometry"]) for f in geo["features"]}

    b = pd.read_csv(TAB / "hlm_m3_rs_blups.csv")
    b["uf"] = b["UPA"].astype(str).str[:2].astype(int)
    sit = (pd.read_parquet(ROOT / "data" / "processed" / "features.parquet", columns=["UPA", "V1023"])
           .dropna().groupby("UPA")["V1023"].agg(lambda s: int(s.mode().iloc[0])))
    sit.index = sit.index.astype("int64")
    b["sit"] = b["UPA"].astype("int64").map(sit).fillna(4).astype(int)
    # renda mediana do bairro (descritiva, sem controles): ocupados com renda positiva
    r = pd.read_parquet(ROOT / "data" / "processed" / "features.parquet", columns=["UPA", "log_renda"])
    r = r[r["log_renda"].notna() & (r["log_renda"] > 0)]
    med = np.exp(r.groupby("UPA")["log_renda"].median())
    med.index = med.index.astype("int64")
    b["renda_med"] = b["UPA"].astype("int64").map(med)

    rng = np.random.default_rng(semente)
    lon = np.empty(len(b)); lat = np.empty(len(b))
    for uf, g in b.groupby("uf"):
        for s, gg in g.groupby("sit"):
            idx = gg.index.to_numpy()
            if s == 1:
                p = _sortear(len(idx), aneis[uf], rng, CAPITAL[uf], 0.10)
            elif s in (2, 3):
                p = _sortear(len(idx), aneis[uf], rng, CAPITAL[uf], 0.40)
            else:
                p = _sortear(len(idx), aneis[uf], rng)
            lon[idx], lat[idx] = p[:, 0], p[:, 1]

    pen = (1 - np.exp(beta_rs + b["u1"].to_numpy())) * 100        # % de renda a menos para negros
    base = (np.exp(b["u0"].to_numpy()) - 1) * 100                  # renda-base do bairro vs. média
    pneg = (b["n_negro"] / b["n"]).to_numpy() * 100

    resumo = {
        "n_bairros": len(b),
        "pct_bairros_penalidade": float((pen > 0).mean() * 100),
        "pen_p10": float(np.percentile(pen, 10)), "pen_mediana": float(np.median(pen)),
        "pen_p90": float(np.percentile(pen, 90)),
        "corr_spearman_pnegro_base": float(pd.Series(pneg).corr(pd.Series(base), method="spearman")),
        "corr_spearman_base_pen": float(pd.Series(base).corr(pd.Series(pen), method="spearman")),
        "corr_spearman_pnegro_renda": float(pd.Series(pneg).corr(b["renda_med"], method="spearman")),
        "renda_med_q1_pneg": float(b.loc[pneg <= np.percentile(pneg, 25), "renda_med"].median()),
        "renda_med_q4_pneg": float(b.loc[pneg >= np.percentile(pneg, 75), "renda_med"].median()),
        "pneg_q1_corte": float(np.percentile(pneg, 25)), "pneg_q4_corte": float(np.percentile(pneg, 75)),
    }
    med_uf = pd.Series(pen).groupby(b["uf"].to_numpy()).median()
    resumo.update({"uf_med_min": float(med_uf.min()), "uf_med_min_sigla": SIGLA[int(med_uf.idxmin())],
                   "uf_med_max": float(med_uf.max()), "uf_med_max_sigla": SIGLA[int(med_uf.idxmax())],
                   "uf_med_todas_positivas": bool((med_uf > 0).all())})
    pd.DataFrame([resumo]).to_csv(TAB / "pagina_bairros_resumo.csv", index=False)

    # busca por estado e tipo de área (o que a PNAD informa): capital, região metropolitana/RIDE, interior
    b["pen"], b["pneg"] = pen, pneg
    b["area"] = b["sit"].map(lambda s: 1 if s == 1 else 2 if s in (2, 3) else 3)
    busca = []
    for (uf, ar), g in b.groupby(["uf", "area"]):
        busca.append({"uf": SIGLA[int(uf)], "area": int(ar), "bairros": int(len(g)),
                      "pen": round(float(g["pen"].median()), 1),
                      "renda": int(round(float(g["renda_med"].median()))),
                      "pneg": round(float(g["n_negro"].sum() / g["n"].sum() * 100), 1),
                      "com_pen": round(float((g["pen"] > 0).mean() * 100), 1)})
    pd.DataFrame(busca).to_csv(TAB / "pagina_busca_uf_area.csv", index=False)

    ordem_uf = sorted(SIGLA)
    return {
        "geo": geo,
        "ufs": [SIGLA[u] for u in ordem_uf],
        "b": {                                                        # colunas compactas
            "lon": np.round(lon, 3).tolist(), "lat": np.round(lat, 3).tolist(),
            "uf": [ordem_uf.index(u) for u in b["uf"]],
            "n": b["n"].astype(int).tolist(),
            "pneg": np.round(pneg, 1).tolist(),
            "base": np.round(base, 1).tolist(),
            "pen": np.round(pen, 2).tolist(),
            "renda": b["renda_med"].round(0).fillna(0).astype(int).tolist(),
            "sit": [1 if s == 1 else 2 if s in (2, 3) else 3 for s in b["sit"]],
        },
        "resumo": resumo,
        "busca": busca,
    }


def economia(gap_m3: float, ame_acesso: float) -> dict:
    """Ordens de grandeza do custo, com o peso amostral da PNAD no último ano da série.

    · talento fora do lugar: efeito marginal médio do acesso a cargo qualificado (GLMM A2, em p.p.)
      × ocupados negros — quantos estariam em cargo qualificado com as chances de um branco igual;
    · renda que deixa de ser paga: a massa anual de rendimentos do trabalho dos negros, se a
      penalidade condicional (M3) não existisse: massa × (1/(1 − gap) − 1).
    Associações condicionais, não efeitos causais; não é PIB perdido.
    """
    d = pd.read_parquet(ROOT / "data" / "processed" / "features.parquet",
                        columns=["Ano", "Trimestre", "negro", "V1028", "log_renda", "VD4002"])
    ano = int(d["Ano"].max())
    d = d[(d["Ano"] == ano) & (d["VD4002"] == 1) & (d["negro"] == 1)]
    nt = d["Trimestre"].nunique()
    ocup = float(d["V1028"].sum() / nt)
    r = d[d["log_renda"].notna() & (d["log_renda"] > 0)]
    massa = float((np.exp(r["log_renda"]) * r["V1028"]).sum() / nt * 12)
    out = {"ano": ano, "ocupados_negros": ocup, "massa_negros_ano": massa,
           "talento_fora": abs(ame_acesso) / 100 * ocup,
           "renda_nao_paga": massa * (1 / (1 - gap_m3 / 100) - 1)}
    pd.DataFrame([out]).to_csv(TAB / "pagina_economia.csv", index=False)
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from params_nucleo import P
    d = dados(P["B_M3_RS"])
    print(d["resumo"])
    print(economia(P["GAP_M3"], P["AME_ocp_qualif_M2"]))


def desigualdade(gap_m3: float) -> dict:
    """Peso da diferença racial na desigualdade de renda do trabalho (ocupados com renda, último ano,
    com o peso amostral): Gini observado, Gini sem a penalidade condicional (renda dos negros / (1 − gap)),
    Gini com as médias de negros e brancos igualadas (desigualdade interna mantida) e a parcela do Theil
    que é diferença entre os dois grupos."""
    d = pd.read_parquet(ROOT / "data" / "processed" / "features.parquet",
                        columns=["Ano", "negro", "V1028", "log_renda", "VD4002"])
    ano = int(d["Ano"].max())
    d = d[(d["Ano"] == ano) & (d["VD4002"] == 1) & d["negro"].isin([0, 1])
          & d["log_renda"].notna() & (d["log_renda"] > 0)]
    y, w, g = np.exp(d["log_renda"].to_numpy()), d["V1028"].to_numpy(), d["negro"].to_numpy()

    def gini(y):
        o = np.argsort(y); yy, ww = y[o], w[o]; cw, cy = np.cumsum(ww), np.cumsum(yy * ww)
        return float(1 - np.sum(ww * (2 * cy - yy * ww)) / (cw[-1] * cy[-1]))

    mu = np.average(y, weights=w)
    theil = float(np.average((y / mu) * np.log(y / mu), weights=w))
    entre = 0.0
    for k in (0, 1):
        m = g == k
        muk = np.average(y[m], weights=w[m])
        entre += w[m].sum() / w.sum() * (muk / mu) * np.log(muk / mu)
    mb, mn = np.average(y[g == 0], weights=w[g == 0]), np.average(y[g == 1], weights=w[g == 1])
    y_sp = np.where(g == 1, y / (1 - gap_m3 / 100), y)
    y_ig = np.where(g == 1, y * mb / mn, y)
    fatia = lambda yy: float((yy[g == 1] * w[g == 1]).sum() / (yy * w).sum() * 100)   # noqa: E731
    out = {"ano": ano, "gini": gini(y), "gini_sem_penalidade": gini(y_sp), "gini_medias_iguais": gini(y_ig),
           "theil": theil, "pct_theil_entre": float(entre / theil * 100),
           "renda_media_brancos": float(mb), "renda_media_negros": float(mn),
           "parcela_pop_negros": float(w[g == 1].sum() / w.sum() * 100),
           "parcela_massa_negros": fatia(y), "parcela_massa_negros_sem_pen": fatia(y_sp)}
    pd.DataFrame([out]).to_csv(TAB / "pagina_desigualdade.csv", index=False)
    return out
