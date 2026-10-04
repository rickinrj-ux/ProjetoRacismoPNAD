"""
figuras_ptbr.py — vírgula decimal (norma ABNT) em figuras matplotlib já montadas.

`virgula_decimal(fig)` reescreve eixos, rótulos fixos e anotações; `ativar()` faz
todo `savefig` passar por ela, para scripts com muitas figuras.
"""
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


def virgula_decimal(fig=None):
    """Vírgula decimal (norma ABNT) em eixos e anotações de uma figura já montada.

    O shap escreve os valores com ponto ("+0.12", "f(x) = 7.81"); os eixos são
    refeitos pelo formatador, e os textos soltos, por substituição entre dígitos.
    """
    import re
    from matplotlib.ticker import FuncFormatter
    from matplotlib.text import Text
    fig = fig or plt.gcf()
    # dentro de $...$ (mathtext) a vírgula ganharia espaço: "6, 739"
    # "{,}" só dentro de fórmula ($...$, dois cifrões); "R$ 4.444" não é fórmula
    _v = lambda s: re.sub(r"(?<=\d)\.(?=\d)", "{,}" if s.count("$") >= 2 else ",", s)
    fmt = FuncFormatter(lambda v, _p: f"{v:g}".replace(".", ",").replace("-", "−"))
    for ax in fig.axes:
        for eixo in (ax.xaxis, ax.yaxis):
            if eixo.get_major_formatter().__class__.__name__ in (
                    "ScalarFormatter", "FormatStrFormatter"):
                eixo.set_major_formatter(fmt)
    # rótulos fixos do waterfall ("0.998 = UF", "f(x) = 7.81"): o matplotlib os
    # regenera ao desenhar, então desenha-se primeiro e regrava-se o texto
    fig.canvas.draw()
    for ax in fig.axes:
        for eixo in (ax.xaxis, ax.yaxis):
            for minor in (False, True):          # o waterfall usa os dois níveis
                if not minor and eixo.get_major_formatter() is fmt:     # já em vírgula
                    continue
                velhos = [t.get_text() for t in eixo.get_ticklabels(minor=minor)]
                novos = [{"Low": "Baixo", "High": "Alto"}.get(s, _v(s)) for s in velhos]
                if novos != velhos:
                    eixo.set_ticks(eixo.get_ticklocs(minor=minor), minor=minor)
                    eixo.set_ticklabels(novos, minor=minor)
    for txt in fig.findobj(Text):
        s = txt.get_text()
        novo = _v(s)
        if novo != s:
            txt.set_text(novo)


def ativar():
    """Aplica virgula_decimal antes de cada savefig (plt.savefig e Figure.savefig)."""
    if getattr(Figure.savefig, "_ptbr", False):
        return
    original = Figure.savefig

    def savefig(self, *a, **k):
        virgula_decimal(self)
        return original(self, *a, **k)
    savefig._ptbr = True
    Figure.savefig = savefig
