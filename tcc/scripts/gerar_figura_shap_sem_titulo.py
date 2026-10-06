# -*- coding: utf-8 -*-
"""Cópia da figura SHAP (beeswarm) sem o título interno, para o TCC.

O manual (Tabela 8) não admite título no gráfico: ele fica na legenda "Figura N.". A figura
sai do pipeline de SHAP (run_ml_shap.py, caro); em vez de refazê-lo, apaga-se a faixa do título
— o primeiro bloco de linhas com tinta no topo, até a primeira faixa branca de 12 linhas.
Saída: outputs/figures/shap_beeswarm_xgb_tcc.png
"""
from pathlib import Path

import numpy as np
from PIL import Image

FIG = Path(__file__).resolve().parents[2] / "outputs" / "figures"
im = Image.open(FIG / "shap_beeswarm_xgb.png").convert("RGB")
a = np.asarray(im).copy()
larg = a.shape[1]
miolo = a[:, int(0.30 * larg):int(0.88 * larg)]          # onde o título está centralizado
tinta = (miolo < 200).any(axis=(1, 2))
y0 = int(np.argmax(tinta))                                 # primeira linha do título
y, branco = y0, 0
while y < a.shape[0] and branco < 12:
    branco = branco + 1 if not tinta[y] else 0
    y += 1
fim = y - branco                                           # última linha do título
a[:fim + 1, :] = 255          # a largura toda: o título passa de 88% (o "Alto" começa abaixo)
# tira a faixa branca que sobrou no topo (até a primeira linha com tinta em qualquer coluna)
topo = int(np.argmax((a < 200).any(axis=(1, 2))))
Image.fromarray(a[max(0, topo - 8):]).save(FIG / "shap_beeswarm_xgb_tcc.png", dpi=(200, 200))
print(f"OK -> shap_beeswarm_xgb_tcc.png (título nas linhas {y0}-{fim} apagado)")
