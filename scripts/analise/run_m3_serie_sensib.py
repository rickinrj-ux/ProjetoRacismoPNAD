"""
run_m3_serie_sensib.py — duas reestimações com a especificação M3 do núcleo.

  --serie   β racial ano a ano (2016–2025): o M3 do run_hlm_stepup.py (UPA aleatória,
            UF fixa, contexto leave-one-out, educ_missing) ajustado em cada ano, sem C(Ano).
            Substitui o validacao_temporal.csv de 16/05, que vinha de outra especificação
            (sem educ_missing, sem jornada, anterior às correções) e alimentava a tendência
            temporal citada na Discussão. Saída no mesmo formato, lido por
            src/tendencia_temporal.py.
  --sensib  β racial do M3 com e sem o indicador educ_missing, na população — fonte da
            frase sobre a estabilidade do coeficiente à especificação da escolaridade.
            Saída: outputs/tables/sensib_educ_missing.csv

Cada ano/modelo é gravado assim que termina; uma nova execução pula o que já está no csv
(o processo pode ser encerrado e retomado). População completa, sem amostragem.
"""
import argparse
import gc
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_hlm_stepup as H  # noqa: E402  (fórmulas, carga e ajuste do núcleo)

logger = logging.getLogger("m3_serie_sensib")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")

TABLES = Path("outputs/tables")
OUT_SERIE = TABLES / "validacao_temporal.csv"
OUT_SENSIB = TABLES / "sensib_educ_missing.csv"

M3 = H.FORMULAS["M3"]
M3_ANO = M3.replace(" + C(Ano)", "")                 # dentro de um ano, o efeito de ano some
# Com a escolaridade da VD3004 (02/10/2026) não há mais indicador educ_missing: a
# sensibilidade a ele deixou de existir e --sensib não é mais usado.
M3_SEM_EDUC_MISSING = M3.replace(" + educ_missing", "")
assert M3_ANO != M3, "fórmula do M3 mudou: revise a troca de C(Ano)"


def _feitos(path, col):
    if path.exists():
        return set(pd.read_csv(path)[col].astype(str))
    return set()


def _gravar(path, row):
    df = pd.DataFrame([row])
    df.to_csv(path, mode="a", header=not path.exists(), index=False)


def serie(df, um=False):
    novo = OUT_SERIE.with_suffix(".novo.csv")          # só substitui o antigo no fim
    feitos = _feitos(novo, "label")
    for ano in sorted(df["Ano"].unique()):
        if str(ano) in feitos:
            logger.info(f"{ano}: já gravado, pulando")
            continue
        sub = df[df["Ano"] == ano].reset_index(drop=True)
        L = H.fit_mixed(f"M3_{ano}", M3_ANO, sub)
        b, se = float(L.params["negro"]), float(L.bse["negro"])
        _gravar(novo, {"label": int(ano), "n_obs": L.n, "n_upas": int(sub["UPA_str"].nunique()),
                       "beta_negro": b, "se_negro": se, "pval": float(L.pvalues["negro"]),
                       "gap_pct": (np.exp(b) - 1) * 100, "icc_upa": L.icc, "aic": L.aic,
                       "converged": L.converged, "periodo": int(ano),
                       "especificacao": "M3 do núcleo (UPA aleatória, UF fixa, contexto LOO, escolaridade VD3004)"})
        del sub, L
        gc.collect()
        if um:
            return
    out = pd.read_csv(novo).sort_values("label")
    out.to_csv(OUT_SERIE, index=False)
    logger.info(f"série gravada em {OUT_SERIE} ({len(out)} anos)")


def sensib(df, um=False):
    feitos = _feitos(OUT_SENSIB, "modelo")
    for nome, formula in [("M3", M3), ("M3_sem_educ_missing", M3_SEM_EDUC_MISSING)]:
        if nome in feitos:
            logger.info(f"{nome}: já gravado, pulando")
            continue
        L = H.fit_mixed(nome, formula, df)
        _gravar(OUT_SENSIB, {"modelo": nome, "n": L.n, "beta_negro": float(L.params["negro"]),
                             "se_negro": float(L.bse["negro"]), "llf": L.llf, "converged": L.converged})
        del L
        gc.collect()
        if um:
            return
    s = pd.read_csv(OUT_SENSIB).set_index("modelo")
    if {"M3", "M3_sem_educ_missing"} <= set(s.index):
        var = abs(s.loc["M3_sem_educ_missing", "beta_negro"] / s.loc["M3", "beta_negro"] - 1) * 100
        logger.info(f"variação do β racial sem educ_missing: {var:.2f}%")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serie", action="store_true")
    ap.add_argument("--sensib", action="store_true")
    ap.add_argument("--um", action="store_true",
                    help="ajusta um único modelo pendente e sai (memória volta ao SO entre modelos)")
    a = ap.parse_args()
    df = H.load_data(sample_frac=None)
    df["UPA_str"] = df["UPA"].astype(str)
    df["UF_str"] = df["UF"].astype(str)
    if a.sensib:
        sensib(df, a.um)
    if a.serie:
        serie(df, a.um)


if __name__ == "__main__":
    main()
