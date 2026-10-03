#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
conferir_narrativa_social.py — o documento narrativo cumpre o que promete?

Três checagens, todas objetivas:
  1. jargão: nenhum nome de método, sigla de modelo ou termo técnico de
     estatística no texto visível;
  2. numeração: nenhum título numerado e nenhuma lista numerada;
  3. fonte única: todo percentual do texto tem de bater com params_nucleo.

Uso: python tcc/scripts/conferir_narrativa_social.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from params_nucleo import P  # noqa: E402

ALVO = RAIZ / "entregaveis" / "TCC_Ricardo_Calheiros_Versao_Narrativa.docx"

# o que não pode aparecer para este leitor
JARGAO = [
    "HLM", "GLMM", "SHAP", "XGBoost", "Random Forest", "Oaxaca", "Blinder",
    "quantil", "quantílic", "RIF", "odds", "razão de chances", "razões de chance",
    "intervalo de confiança", "p-valor", "significânc", "coeficiente",
    "regressão", "intercepto", "variância", "desvio-padrão", "correlação",
    "multinível", "hierárquic", "efeito fixo", "efeito aleatório", "bootstrap",
    "erro-padrão", "multicolinearidade", "heterocedastic", "endogeneidade",
    "logaritmo", "log-", "R²", "R2", "UPA", "CBO", "PNAD", "dummy", "dummies",
    "estimador", "estimativa pontual", "verossimilhança", "E-value", "ICC",
    "machine learning", "aprendizado de máquina", "modelo M", "step-up",
    "mediação", "dotaç", "retorno diferencial", "teto de vidro", "sticky floor",
]
# termos que parecem jargão mas são linguagem corrente neste contexto
PERDOADOS = {"modelo m"}


def texto_visivel(doc: Document) -> list[str]:
    return [p.text for p in doc.paragraphs if p.text.strip()]


def pc(x: float, casas: int = 1) -> str:
    s = f"{abs(x):.{casas}f}".replace(".", ",")
    return s.rstrip("0").rstrip(",") if "," in s else s


def main() -> int:
    if not ALVO.exists():
        print(f"ERRO: {ALVO.name} não existe; rode gerar_narrativa_social.py")
        return 1
    doc = Document(str(ALVO))
    linhas = texto_visivel(doc)
    tudo = "\n".join(linhas)
    falhas = 0

    # 1 ── jargão
    achados = []
    for termo in JARGAO:
        if termo.lower() in PERDOADOS:
            continue
        # sigla em caixa alta casa por palavra inteira e respeitando o caixa
        # ("UPA" nao pode acusar "populacao ocupada"); frase comum casa solta
        sigla = termo.isupper() or (termo.isalnum() and termo == termo.upper())
        alvo = (r"\b" + re.escape(termo) + r"\b") if sigla else re.escape(termo)
        flags = 0 if sigla else re.I
        for i, l in enumerate(linhas):
            if re.search(alvo, l, flags):
                achados.append(f"'{termo}' no parágrafo {i + 1}: {l[:70]}…")
                break
    if achados:
        falhas += len(achados)
        print(f"  JARGÃO ({len(achados)})")
        for a in achados:
            print(f"    - {a}")
    else:
        print(f"  jargão: nenhum dos {len(JARGAO)} termos vigiados aparece   OK")

    # 2 ── numeração
    numerados = [l for l in linhas if re.match(r"^\s*(\d+[.)]|\d+\.\d+)\s+\S", l)]
    if numerados:
        falhas += len(numerados)
        print(f"  NUMERAÇÃO ({len(numerados)}): {numerados[:3]}")
    else:
        print("  numeração: nenhum título ou item numerado              OK")

    # 3 ── fonte única: cada percentual do texto existe em params_nucleo?
    esperados = {
        pc(P["GAP_POOL"]), pc(P["GAP_M1"]), pc(P["GAP_M3"]), pc(P["GAP_M4"]),
        pc(P["MED_ACUM_M1"]), pc(P["ICC_M0"] * 100),
        pc(abs(P["AME_ocp_qualif_M2"])),
        pc(P["RIF_RET_Q10"]), pc(P["RIF_RET_Q90"]),
        pc((1 - P["OR_ocp_qualif_M2"]) * 100, 0),
        pc((1 - P["OR_y_top10_M2"]) * 100, 0),
        pc((1 - P["GRG_MN_TOP10"]) * 100, 0),
        pc((1 - P["GRG_HN_OCP_QUALIF"]) * 100, 0),
        pc((P["GRG_MN_OCP_QUALIF"] - 1) * 100, 0),
        # gap por tipo de área (qr_gap_por_area.csv)
        pc(P["QR_AREA_CAPITAL_Q50"]), pc(P["QR_AREA_CAPITAL_Q95"]),
        pc(P["QR_AREA_INTERIOR_Q50"]), pc(P["QR_AREA_INTERIOR_Q95"]),
        # contraprova de forma funcional (shap_negro_por_grupo.csv)
        pc(P["ML_CONTRASTE_PCT"]),
    }
    no_texto = set(re.findall(r"(\d+(?:,\d+)?)%", tudo))
    orfaos = sorted(no_texto - esperados)
    if orfaos:
        falhas += len(orfaos)
        print(f"  PERCENTUAL SEM FONTE ({len(orfaos)}): {orfaos}")
    else:
        print(f"  fonte única: os {len(no_texto)} percentuais batem com o csv  OK")

    palavras = sum(len(l.split()) for l in linhas)
    print(f"\n  {len(linhas)} parágrafos, {palavras} palavras")
    print("  " + ("conforme" if not falhas else f"{falhas} problema(s)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
