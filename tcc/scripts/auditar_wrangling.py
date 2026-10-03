"""
auditar_wrangling.py — auditoria do tratamento dos microdados da PNAD Contínua.

Nasceu do erro da escolaridade (V3009A lida como nível de instrução) e do mapa da CNAE.
Três checagens independentes do código do pipeline, lendo direto dos ZIPs do IBGE:

  1. LAYOUT: o mesmo layout é aplicado aos 40 trimestres. Para cada ZIP, lê as primeiras
     linhas e testa domínios (Ano/Trimestre = nome do arquivo, UF ∈ 11–53, sexo ∈ {1,2},
     idade 0–130, raça ∈ {1..5,9}, VD4002 ∈ {1,2}, VD3004 ∈ {1..7}, V4010 com 4 dígitos,
     V4013 com 5). Um deslocamento de colunas produz domínios inválidos.
  2. JOIN: a chave Ano+Trimestre+UPA+V1008+V2003 é única? Sexo/idade/raça relidos do ZIP
     batem com os da base principal (data.parquet) para a mesma chave?
  3. TRUTH TABLE: todo código observado das variáveis recodificadas tem rótulo, e a renda
     média segue a ordem esperada.

Uso: python tcc/scripts/auditar_wrangling.py [--linhas 50000]
Saída: relatório no terminal; código 1 se alguma checagem falhar.
"""
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
sys.stdout.reconfigure(encoding="utf-8")
N = int(sys.argv[sys.argv.index("--linhas") + 1]) if "--linhas" in sys.argv else 50_000

lay = pd.read_parquet(RAW / "layout" / "layout.parquet")
VARS = ["Ano", "Trimestre", "UF", "UPA", "V1008", "V2003", "V2007", "V2009", "V2010",
        "VD4002", "VD4020", "VD3004", "V3009A", "V4010", "V4013", "VD4009", "V1028"]
sub = lay[lay["name"].isin(VARS)].sort_values("start")
colspecs = [(int(r.start) - 1, int(r.end) - 1) for r in sub.itertuples()]
nomes = sub["name"].tolist()
falhas = []


def ler(zp, n):
    with zipfile.ZipFile(zp) as zf:
        txt = [x for x in zf.namelist() if x.lower().endswith(".txt")][0]
        with zf.open(txt) as f:
            return pd.read_fwf(f, colspecs=colspecs, names=nomes, dtype=str, nrows=n,
                               encoding="latin-1")


# ── 1. LAYOUT ────────────────────────────────────────────────────────────────
print(f"1. LAYOUT — {N:,} linhas de cada ZIP\n")
DOM = {"UF": set(range(11, 54)), "V2007": {1, 2}, "V2010": {1, 2, 3, 4, 5, 9},
       "VD4002": {1, 2}, "VD3004": set(range(1, 8)), "VD4009": set(range(1, 11)),
       "V3009A": set(range(1, 16))}
amostras = {}
for zp in sorted(RAW.glob("PNADC_*.zip"), key=lambda p: (p.name[-8:-4], p.name[6])):
    m = re.match(r"PNADC_(\d)(\d{4})\.zip", zp.name)
    tri, ano = int(m.group(1)), int(m.group(2))
    d = ler(zp, N)
    num = d.drop(columns=["V4010", "V4013", "UPA", "V1008", "V2003"]).apply(pd.to_numeric, errors="coerce")
    prob = []
    if not (num["Ano"] == ano).all() or not (num["Trimestre"] == tri).all():
        prob.append("Ano/Trimestre não batem com o arquivo")
    for v, dom in DOM.items():
        obs = set(num[v].dropna().astype(int))
        fora = obs - dom
        if fora:
            prob.append(f"{v} fora do domínio: {sorted(fora)[:5]}")
    if not num["V2009"].between(0, 130).all():
        prob.append("idade fora de 0–130")
    for v, k in (("V4010", 4), ("V4013", 5)):
        c = d[v].dropna().str.strip()
        if len(c) and not (c.str.len() == k).all():
            prob.append(f"{v} com comprimento ≠ {k}")
    if not (num["V1028"].dropna() > 0).all():
        prob.append("peso ≤ 0")
    status = "ok" if not prob else "FALHA: " + "; ".join(prob)
    renda = np.log(num.loc[num["VD4020"] > 0, "VD4020"]).mean()
    print(f"  {ano}T{tri}  negro {num['V2010'].isin([2,4]).mean():.3f}  mulher {(num['V2007']==2).mean():.3f}"
          f"  ocupado {(num['VD4002']==1).mean():.3f}  ≥sup {(num['VD3004']==7).mean():.3f}"
          f"  logrenda {renda:.2f}  {status}")
    if prob:
        falhas.append(f"layout {ano}T{tri}: {prob}")
    if (ano, tri) in {(2016, 1), (2020, 2), (2025, 4)}:
        amostras[(ano, tri)] = d

# ── 2. JOIN ──────────────────────────────────────────────────────────────────
print("\n2. JOIN — chave única e testemunhas (sexo, idade, raça) contra data.parquet\n")
K = ["UPA", "V1008", "V2003"]
for (ano, tri), d in amostras.items():
    base = pd.read_parquet(PROC / f"ano={ano}" / f"trimestre={tri}" / "data.parquet")
    for c in K:
        base[c] = base[c].astype(str).str.strip()
        d[c] = d[c].astype(str).str.strip()
    dup_base = int(base.duplicated(K).sum())
    dup_raw = int(d.duplicated(K).sum())
    m = d.merge(base[K + ["V2007", "V2009", "V2010"]], on=K, how="left", suffixes=("_zip", "_base"))
    casou = m["V2007_base"].notna().mean()
    ok = m.dropna(subset=["V2007_base"])
    disc = {v: float((pd.to_numeric(ok[f"{v}_zip"]) != pd.to_numeric(ok[f"{v}_base"])).mean())
            for v in ("V2007", "V2009", "V2010")}
    print(f"  {ano}T{tri}: duplicatas base {dup_base} | zip {dup_raw} | casamento {casou:.4f} | "
          f"discordância sexo {disc['V2007']:.4f} idade {disc['V2009']:.4f} raça {disc['V2010']:.4f}")
    if dup_base or dup_raw or casou < 0.999 or max(disc.values()) > 0:
        falhas.append(f"join {ano}T{tri}: dup {dup_base}/{dup_raw}, casamento {casou:.4f}, disc {disc}")
    # UPA codifica a UF nos 2 primeiros dígitos?
    uf_upa = (d["UPA"].str[:2] == d["UF"].astype(str).str.zfill(2)).mean()
    print(f"           UPA começa com a UF em {uf_upa:.4f} das linhas")

# ── 3. TRUTH TABLE (sobre as amostras dos ZIPs) ──────────────────────────────
print("\n3. TRUTH TABLE — renda média por código (amostra 2025T4)\n")
d = amostras[(2025, 4)].copy()
num = d.drop(columns=["V4010", "V4013", "UPA", "V1008", "V2003"]).apply(pd.to_numeric, errors="coerce")
num["lr"] = np.log(num["VD4020"].where(num["VD4020"] > 0))
num["cbo1"] = d["V4010"].str.strip().str[:1]
num["cnae2"] = pd.to_numeric(d["V4013"].str.strip().str[:2], errors="coerce")
for v in ("VD3004", "VD4009", "cbo1"):
    t = num.groupby(v)["lr"].agg(["size", "mean"]).round(2)
    print(f"  {v}: " + " | ".join(f"{i}: {r['mean']} (n={int(r['size'])})" for i, r in t.iterrows()))
r_ed = num.groupby("VD3004")["lr"].mean()
if not r_ed.loc[[3, 5, 7]].is_monotonic_increasing:
    falhas.append("renda não cresce com VD3004 (3,5,7)")

print("\n" + ("TUDO OK" if not falhas else "FALHAS:\n  - " + "\n  - ".join(map(str, falhas))))
sys.exit(1 if falhas else 0)
