# -*- coding: utf-8 -*-
"""
tabela_qr_tex.py
================
Monta `outputs/tables/qr_melhorias.tex` a partir dos csv, em formatação pt-BR.

Por que existe em separado: a tabela era escrita no meio de
`run_ob_qr_melhorias.py`, com f-strings de `{:.4f}` — decimal com ponto,
notação científica (`p = 1.84e-64`) e `Z = -16.95`, destoando do resto do
documento, que usa vírgula. Como `qr_melhorias.csv` e `qr_kb_test.csv` já
guardam tudo o que a tabela mostra, ela pode ser remontada sem repetir o
bootstrap de 200 réplicas que produziu os números.

Limite conhecido: `qr_melhorias.csv` guarda os coeficientes com 5 casas, e a
tabela mostra 4. Quando a 5.a casa do csv é exatamente 5, o arredondamento
parte de um valor já arredondado e pode diferir em uma unidade na última casa
do que a execução original imprimiu (aconteceu com Homens q75: -0,1012 na
execução, -0,1013 a partir do csv). Salvar mais casas no csv resolve na
próxima execução de `run_ob_qr_melhorias.py`.

Uso:
    python scripts/analise/tabela_qr_tex.py     # regera o .tex a partir dos csv
    from tabela_qr_tex import escrever_tabela   # chamada pelo script de análise
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "outputs" / "tables"
BAR = chr(92)


def br(x: float, casas: int) -> str:
    """Decimal em pt-BR no padrão do documento: 0{,}0832."""
    return f"{x:.{casas}f}".replace(".", "{,}")


def p_br(p: float) -> str:
    """P-valor legível. Notação científica é de saída de software, não de tabela."""
    if pd.isna(p):
        return "---"
    if p < 0.001:
        return "p < 0{,}001"
    return f"p = {br(p, 3)}"


def escrever_tabela(destino: Path | None = None) -> Path:
    qr = pd.read_csv(TABLES / "qr_melhorias.csv")
    kb = pd.read_csv(TABLES / "qr_kb_test.csv").iloc[0]

    quantis = sorted(qr["quantil"].unique())
    por_grupo = {g: d.set_index("quantil") for g, d in qr.groupby("grupo")}

    def cel(grupo: str, q: float, col: str, casas: int) -> str:
        d = por_grupo.get(grupo)
        if d is None or q not in d.index or pd.isna(d.loc[q, col]):
            return "---"
        return f"${br(float(d.loc[q, col]), casas)}$"

    def gap(grupo: str, q: float) -> str:
        """Gap recalculado do coeficiente, não lido de `gap_pct`.

        `gap_pct` vem do csv com 2 casas, e arredondar duas vezes muda o
        resultado: -10,95 vira -10,9, quando o valor cheio (-10,9507) dá -11,0.
        """
        d = por_grupo.get(grupo)
        if d is None or q not in d.index or pd.isna(d.loc[q, "b_negro"]):
            return "---"
        b = float(d.loc[q, "b_negro"])
        return f"${br((math.exp(b) - 1) * 100, 1)}{BAR}%$"

    L = []
    A = L.append
    A(BAR + r"begin{table}[H]")
    A(BAR + "centering")
    A(BAR + r"caption{Regressão quantílica: coeficiente $" + BAR +
      r"hat{" + BAR + r"beta}_{" + BAR + r"text{negro}}$ por quantil e sexo.")
    A(r"         Gap~(" + BAR + r"%) $= (e^{" + BAR + r"hat{" + BAR +
      r"beta}}-1)" + BAR + r"times 100$.")
    A(r"         M3: controles individuais + contexto UPA + UF efeito fixo. População completa.")
    A(r"         Entre parênteses (coluna Global): erro-padrão por bootstrap em blocos por UPA.")
    A(r"         $^{***}p<0{,}001$ em todos os quantis e grupos.}")
    A(BAR + r"label{tab:qr_melhorias}")
    A(BAR + "small")
    A(BAR + r"begin{tabular}{lrrrrrr}")
    A(BAR + "toprule")
    A(r"& " + BAR + r"multicolumn{2}{c}{Global} & " + BAR +
      r"multicolumn{2}{c}{Homens} & " + BAR + r"multicolumn{2}{c}{Mulheres} " + BAR * 2)
    A(BAR + r"cmidrule(lr){2-3}" + BAR + r"cmidrule(lr){4-5}" + BAR + r"cmidrule(lr){6-7}")
    A(r"Quantil & $" + BAR + r"hat{" + BAR + r"beta}$ (SE) & Gap~(" + BAR +
      r"%) & $" + BAR + r"hat{" + BAR + r"beta}$ & Gap~(" + BAR + r"%) & $" + BAR +
      r"hat{" + BAR + r"beta}$ & Gap~(" + BAR + r"%) " + BAR * 2)
    A(BAR + "midrule")

    for q in quantis:
        g = por_grupo["Global"]
        se = g.loc[q, "se_cl_upa"] if q in g.index else float("nan")
        b_glob = cel("Global", q, "b_negro", 4)
        cel_g = (f"{b_glob} ({br(float(se), 4)})" if not pd.isna(se) else b_glob)
        A(f"$" + BAR + f"tau={br(q, 2)}$ & {cel_g} & {gap('Global', q)} & "
          f"{cel('Homens', q, 'b_negro', 4)} & {gap('Homens', q)} & "
          f"{cel('Mulheres', q, 'b_negro', 4)} & {gap('Mulheres', q)} " + BAR * 2)

    A(BAR + "midrule")
    A(BAR + r"textbf{Δ (q90−q10)} & $" + BAR + r"mathbf{" +
      br(float(kb["diff_q90_q10"]) * 100, 2) + BAR + r"text{pp}}^{***}$ (" +
      br(float(kb["se_boot"]), 4) + r") & " + BAR +
      r"multicolumn{2}{c}{$Z = " + br(float(kb["z_stat"]), 2) + r"$} & " + BAR +
      r"multicolumn{2}{c}{$" + p_br(float(kb["p_valor_z"])) + r"$} " + BAR * 2)
    A(BAR + "bottomrule")
    A(BAR + r"end{tabular}")

    n_boot = int(kb["n_boot"])
    m_upas = f"{int(kb['m_upas']):,}".replace(",", ".")
    n_upas = f"{int(kb['n_upas']):,}".replace(",", ".")
    A(BAR + r"note{Teste de heterogeneidade quantílica (Koenker-Bassett style):")
    A(r"      $H_0$: $" + BAR + r"hat{" + BAR + r"beta}(q)$ constante para todo $q$.")
    A(r"      SE por bootstrap em blocos por UPA, ``$m$ de $n$'' ($B=" + str(n_boot) +
      r"$; $m=" + m_upas + r"$ das $" + n_upas + r"$ UPAs por réplica;")
    A(r"      SE escalado por $" + BAR + r"sqrt{m/G}$, Bickel " + BAR +
      r"& Sakov, 2008). Sem a escala (conservador): $Z=" +
      br(float(kb["z_stat_raw"]), 2) + r"$, $" + p_br(float(kb["p_valor_z_raw"])) + r"$.}")
    A(BAR + r"end{table}")

    destino = destino or (TABLES / "qr_melhorias.tex")
    destino.write_text("\n".join(L) + "\n", encoding="utf-8")
    return destino


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    p = escrever_tabela()
    print(f"OK -> {p.relative_to(ROOT)}")
    print(p.read_text(encoding="utf-8"))
