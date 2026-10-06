# -*- coding: utf-8 -*-
"""Figura 10 numa imagem só: os dois waterfall SHAP empilhados, painéis A e B.

Por que (06/10/2026): no Word, duas subfiguras lado a lado viram uma tabela de leiaute do
pandoc, e o Sistema de Trabalho Final acusou "imagem dentro de célula de tabela" e "figura sem
título". O manual (15.1) também pede a identificação dos painéis com letra maiúscula, sem
parênteses nem ponto, no canto superior esquerdo de cada um.

Entrada: outputs/figures/shap_waterfall_{A_branco,B_negro}_alta_renda_xgb.png (run_ml_shap.py)
Saída:   outputs/figures/shap_waterfall_AB_xgb.png
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FIG = Path(__file__).resolve().parents[2] / "outputs" / "figures"
PAINEIS = [("A", FIG / "shap_waterfall_A_branco_alta_renda_xgb.png"),
           ("B", FIG / "shap_waterfall_B_negro_alta_renda_xgb.png")]
SAIDA = FIG / "shap_waterfall_AB_xgb.png"


def _fonte(tam: int):
    for nome in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nome, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> int:
    imgs = [(letra, Image.open(p).convert("RGB")) for letra, p in PAINEIS]
    larg = max(im.width for _, im in imgs)
    respiro = int(0.03 * larg)
    alt = sum(im.height for _, im in imgs) + respiro * (len(imgs) - 1)
    tela = Image.new("RGB", (larg, alt), "white")
    d = ImageDraw.Draw(tela)
    f = _fonte(max(28, larg // 30))
    y = 0
    for letra, im in imgs:
        tela.paste(im, (0, y))
        d.text((int(0.01 * larg), y + int(0.005 * larg)), letra, fill="black", font=f)
        y += im.height + respiro
    tela.save(SAIDA, dpi=(200, 200))
    print(f"OK -> {SAIDA.name} ({tela.width}x{tela.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
