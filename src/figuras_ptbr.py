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


def norma_manual(fig=None, paineis=None):
    """Figura conforme o Manual de Normas do MBA USP/Esalq (15.1 e Tabela 8), antes do savefig.

    · sem título do gráfico (suptitle) nem subtítulo/rodapé soltos na figura: o título fica na
      legenda "Figura N." do texto;
    · sem linhas de grade;
    · com mais de um painel, cada um identificado por letra maiúscula, sem parênteses nem
      ponto, no canto superior esquerdo — no lugar do título do painel (que vai para a legenda).
    O Sistema de Trabalho Final (06/10/2026) acusou os três pontos.
    """
    fig = fig or plt.gcf()
    if getattr(fig, "_suptitle", None) is not None:
        fig._suptitle.remove()
        fig._suptitle = None
    for t in list(fig.texts):
        t.remove()
    eixos = paineis if paineis is not None else [
        ax for ax in fig.axes if ax.get_visible() and ax.get_label() != "<colorbar>"
        and ax.get_navigate()]
    for ax in fig.axes:
        ax.grid(False)
    if len(eixos) > 1:
        for letra, ax in zip("ABCDEFGH", eixos):
            for loc in ("center", "left", "right"):
                ax.set_title("", loc=loc)
            ax.text(-0.02, 1.07, letra, transform=ax.transAxes, fontsize=14,
                    fontweight="bold", ha="right", va="bottom", color="black")
    elif eixos:
        for loc in ("center", "left", "right"):
            eixos[0].set_title("", loc=loc)
    return fig
