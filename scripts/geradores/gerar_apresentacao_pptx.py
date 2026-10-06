"""
gerar_apresentacao_pptx.py
Gera entregaveis/TCC_Ricardo_Calheiros_Defesa.pptx — 15 slides para defesa de TCC na banca.
Usa python-pptx (pip install python-pptx).
"""

# --- bootstrap raiz do projeto (reorg estrutura) ---
import re
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys; sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches as In, Pt
import pandas as pd
import numpy as np

# Fonte única: os mesmos csv que alimentam o relatório. O params.py da raiz é da
# versão estendida e trazia para cá números que o relatório já não sustenta
# (OR 0,693 do logit-FE, ICC de UF do HLM de três níveis).
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "tcc" / "scripts"))
from params_nucleo import P as _PN, milhar, pt as _pt, titulo_bairro, frase_sintese, frase_diploma
from params_nucleo import _int_logs
# E2.3: interseccionalidade lida em log-pontos (escala aditiva) — sub-aditiva quando o gap da
# mulher negra fica abaixo da soma mulher branca + homem negro
_INT_MN, _INT_SOMA = _int_logs(_PN)
_INT_SUB = _INT_MN < _INT_SOMA


def fmt(v, dec=3):    return _pt(v, dec).replace("−", "-")
def fmtN(n):          return milhar(n)
def or_str(v, dec=3): return fmt(v, dec)
def ame(v, dec=2):    return f"{fmt(v, dec)} p.p."


# nomes curtos usados nos slides -> chaves de params_nucleo
P = dict(_PN)
P.update({
    "OR_M1": _PN["OR_ocp_qualif_M1"],   "OR_M2": _PN["OR_ocp_qualif_M2"],
    "AME_M1_pp": _PN["AME_ocp_qualif_M1"], "AME_M2_pp": _PN["AME_ocp_qualif_M2"],
    "OR_M1_menor_pct": (1 - _PN["OR_ocp_qualif_M1"]) * 100,
    "OR_M2_menor_pct": (1 - _PN["OR_ocp_qualif_M2"]) * 100,
    "EVAL_M1": _PN["EV_ocp_qualif_M1"], "EVAL_M2": _PN["EV_ocp_qualif_M2"],
    "OR_OCP_M2": _PN["OR_ocp_qualif_M2"], "OR_TOP10_M2": _PN["OR_y_top10_M2"],
    "OR_TOP20_M2": _PN["OR_y_top20_M2"],
    "ICC_UPA_pct": _PN["ICC_M0"] * 100,          # ICC de BAIRRO (o do modelo nulo)
    "GAP_PCT": _PN["OB_SEM_GAP_PCT"],
    "DOT_PCT": _PN["OB_SEM_DOT_PCT"], "RET_PCT": _PN["OB_SEM_RET_PCT"],
    "DOT_PCT_COM": _PN["OB_COM_DOT_PCT"], "RET_PCT_COM": _PN["OB_COM_RET_PCT"],
})

ROOT    = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
FIGURES = ROOT / "outputs" / "figures"
TABLES  = ROOT / "outputs" / "tables"

# Descritivos (tab1/tab2), Konfound por degrau e UPAs do HLM vêm de params_nucleo,
# como todo o resto: o deck não lê csv por conta própria para esses números.
# DECK_OUT permite gerar numa pasta de teste sem tocar no entregável
OUT_PPT = _Path(_os.environ.get("DECK_OUT") or (ROOT / "entregaveis" / "TCC_Ricardo_Calheiros_Defesa.pptx"))
(ROOT / "entregaveis").mkdir(exist_ok=True)

# ── Paleta ────────────────────────────────────────────────────────────────────
C_DARK   = RGBColor(0x1F, 0x38, 0x64)   # azul escuro (cabeçalhos)
C_BLUE   = RGBColor(0x15, 0x65, 0xC0)   # azul (brancos / positivo)
C_RED    = RGBColor(0xB7, 0x1C, 0x1C)   # destaque pontual (usar com parcimônia — SWD-42)
C_GRAY2  = RGBColor(0x9E, 0x9E, 0x9E)   # cinza dos dados de contexto
C_AMBER  = RGBColor(0xFF, 0x8F, 0x00)   # âmbar (destaque)
C_WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
C_BLACK  = RGBColor(0x21, 0x21, 0x21)
C_GRAY   = RGBColor(0x61, 0x61, 0x61)
C_LGRAY  = RGBColor(0xF5, 0xF5, 0xF5)
C_GREEN  = RGBColor(0x2E, 0x7D, 0x32)

W = In(13.33)   # largura slide 16:9
H = In(7.50)    # altura slide 16:9

prs = Presentation()
prs.slide_width  = W
prs.slide_height = H

BLANK = prs.slide_layouts[6]   # layout em branco

# ── Helpers ───────────────────────────────────────────────────────────────────
def add_rect(slide, l, t, w, h, fill_rgb=None, line_rgb=None, line_pt=0):
    from pptx.util import Pt as _Pt
    shape = slide.shapes.add_shape(1, l, t, w, h)   # MSO_SHAPE_TYPE.RECTANGLE
    shape.line.width = _Pt(line_pt) if line_pt else 0
    if fill_rgb:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_rgb
    else:
        shape.fill.background()
    if line_rgb and line_pt:
        shape.line.color.rgb = line_rgb
    return shape

def add_text(slide, text, l, t, w, h,
             font_size=20, bold=False, italic=False,
             color=C_BLACK, align=PP_ALIGN.LEFT,
             wrap=True, font_name="Calibri"):
    tf = slide.shapes.add_textbox(l, t, w, h)
    tf.text_frame.word_wrap = wrap
    p = tf.text_frame.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold  = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = font_name
    return tf

def add_multiline(slide, lines, l, t, w, h,
                  font_size=16, color=C_BLACK, bold=False,
                  align=PP_ALIGN.LEFT, line_spacing=1.15,
                  font_name="Calibri"):
    tf = slide.shapes.add_textbox(l, t, w, h)
    tf.text_frame.word_wrap = True
    first = True
    for line_text in lines:
        if first:
            p = tf.text_frame.paragraphs[0]
            first = False
        else:
            p = tf.text_frame.add_paragraph()
        p.alignment = align
        p.space_after = Pt(2)
        run = p.add_run()
        run.text = line_text
        run.font.size = Pt(font_size)
        run.font.bold  = bold
        run.font.color.rgb = color
        run.font.name = font_name
    return tf

def add_img(slide, img_path, l, t, w, h=None):
    p = Path(img_path)
    if not p.exists():
        add_text(slide, f"[Figura: {p.name}]", l, t, w, In(1),
                 font_size=10, color=C_GRAY, italic=True)
        return
    # Encaixa a figura na caixa (w × h) sem distorcer. Sem h, a caixa vai até o
    # rodapé: antes a altura ficava livre e a figura vazava por baixo dos textos.
    from PIL import Image as _Img
    with _Img.open(p) as _im:
        iw, ih = _im.size
    h = h or (H - t - In(0.35))
    esc = min(w / iw, h / ih)
    slide.shapes.add_picture(str(p), l, t, int(iw * esc), int(ih * esc))

_N_TITULO = [0]


def header_bar(slide, title, subtitle=None, numerar=True):
    # numeração automática: com números fixos no texto, os slides inseridos depois
    # (penalidade por bairro, diploma) ficavam sem número ou com "9b"
    title = re.sub(r"^\d+[a-z]?\.\s+", "", title)
    if numerar:
        _N_TITULO[0] += 1
        title = f"{_N_TITULO[0]}. {title}"
    add_rect(slide, 0, 0, W, In(1.10), fill_rgb=C_DARK)
    # título longo quebrava em duas linhas e cobria o subtítulo
    tam = 26 if len(title) <= 60 else (22 if len(title) <= 72 else 19)
    add_text(slide, title, In(0.3), In(0.08), In(12.7), In(0.55),
             font_size=tam, bold=True, color=C_WHITE, font_name="Calibri")
    if subtitle:
        add_text(slide, subtitle, In(0.3), In(0.65), In(12), In(0.38),
                 font_size=14, color=RGBColor(0xBB, 0xDE, 0xFB), font_name="Calibri")

def bullet_box(slide, items, l, t, w, h,
               dot="▸", font_size=16, color=C_BLACK,
               dot_color=C_BLUE):
    tf = slide.shapes.add_textbox(l, t, w, h)
    tf.text_frame.word_wrap = True
    first = True
    for item in items:
        if first:
            p = tf.text_frame.paragraphs[0]
            first = False
        else:
            p = tf.text_frame.add_paragraph()
        p.space_after = Pt(4)
        # dot
        r1 = p.add_run(); r1.text = dot + "  "
        r1.font.size = Pt(font_size); r1.font.color.rgb = dot_color
        r1.font.bold = True; r1.font.name = "Calibri"
        # text
        r2 = p.add_run(); r2.text = item
        r2.font.size = Pt(font_size); r2.font.color.rgb = color
        r2.font.name = "Calibri"
    return tf

def kpi_box(slide, label, value, unit, l, t, w=In(2.8), h=In(1.3),
            val_color=C_BLUE):
    add_rect(slide, l, t, w, h, fill_rgb=C_LGRAY,
             line_rgb=C_DARK, line_pt=1)
    add_text(slide, label, l+In(0.1), t+In(0.05), w-In(0.2), In(0.35),
             font_size=11, color=C_GRAY, font_name="Calibri")
    add_text(slide, value, l+In(0.1), t+In(0.35), w-In(0.2), In(0.6),
             font_size=30, bold=True, color=val_color, font_name="Calibri")
    add_text(slide, unit, l+In(0.1), t+In(0.92), w-In(0.2), In(0.35),
             font_size=10, color=C_GRAY, italic=True, font_name="Calibri")

def add_table_resumo(slide, headers, rows, l, t, w, h, col_w=None, font_size=12):
    """Tabela OOXML real (editável) estilizada com a paleta."""
    gf = slide.shapes.add_table(len(rows) + 1, len(headers), l, t, w, h)
    tbl = gf.table
    if col_w:
        for j, cw in enumerate(col_w):
            tbl.columns[j].width = cw
    for j, htxt in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.fill.solid(); cell.fill.fore_color.rgb = C_DARK
        cell.vertical_anchor = 3  # MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
        r = p.add_run(); r.text = htxt
        r.font.bold = True; r.font.size = Pt(font_size); r.font.color.rgb = C_WHITE; r.font.name = "Calibri"
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.fill.solid(); cell.fill.fore_color.rgb = C_WHITE if (i % 2) else C_LGRAY
            cell.vertical_anchor = 3
            p = cell.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
            r = p.add_run(); r.text = str(val)
            r.font.size = Pt(font_size); r.font.color.rgb = C_BLACK; r.font.name = "Calibri"
            if j == 0:
                r.font.bold = True; r.font.color.rgb = C_DARK
    return tbl


_NUMEROS = []   # (slide, caixa de texto) — preenchidos no fim, quando o total é conhecido


def footer(slide, _slide_num=None):
    """Rodapé com "n/total". O número antes era passado à mão e pulava e repetia
    (2, 2, 3 … 22, 22, 28, 29 de "20"); agora sai da posição real do slide."""
    add_rect(slide, 0, H-In(0.28), W, In(0.28), fill_rgb=C_DARK)
    add_text(slide,
             "Ricardo Calheiros  |  MBA USP/ESALQ  |  Racismo Estrutural e Mercado de Trabalho",
             In(0.15), H-In(0.25), In(11), In(0.25),
             font_size=8.5, color=RGBColor(0xBB,0xDE,0xFB), font_name="Calibri")
    _NUMEROS.append((slide, add_text(slide, "", In(12.6), H-In(0.25), In(0.7), In(0.25),
                                     font_size=8.5, color=C_WHITE, align=PP_ALIGN.RIGHT,
                                     font_name="Calibri")))

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — CAPA
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, W, H, fill_rgb=C_DARK)
add_rect(s, In(0.5), In(0.4), In(12.33), In(3.8),
         fill_rgb=RGBColor(0x0D,0x1F,0x3C), line_rgb=C_AMBER, line_pt=1.5)

add_text(s, "Bairro, porta e topo: o racismo estrutural no mercado de trabalho brasileiro",
         In(0.9), In(0.65), In(11.5), In(1.5),
         font_size=30, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER, font_name="Calibri")
add_text(s, "Evidências da PNAD Contínua 2016–2025 via HLM, Oaxaca-Blinder,\nGLMM logístico e Regressão Quantílica/RIF (XGBoost/SHAP como robustez)",
         In(0.9), In(2.15), In(11.5), In(0.9),
         font_size=16, color=RGBColor(0xBB,0xDE,0xFB), align=PP_ALIGN.CENTER, font_name="Calibri")
add_rect(s, In(0.9), In(3.1), In(11.5), In(0.03), fill_rgb=C_AMBER)

add_text(s, "Ricardo Calheiros",
         In(0.9), In(3.3), In(11.5), In(0.45),
         font_size=20, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
add_text(s, "MBA em Data Science e Analytics  |  USP/ESALQ  |  Defesa: 2026",
         In(0.9), In(3.75), In(11.5), In(0.4),
         font_size=13, color=RGBColor(0xBB,0xDE,0xFB), align=PP_ALIGN.CENTER)

# stats rápidas no rodapé da capa
for i, (val, lbl) in enumerate([
    (f"{fmt(P['N_BRUTO'] / 1e6, 1)}M", "observações brutas"),
    (f"{fmt(P['N_GLMM'] / 1e6, 1)}M",  "obs. PEA c/ renda"),
    ("4",     "métodos no núcleo"),
    ("10",    "anos de série"),
]):
    x = In(0.5) + i * In(3.2)
    add_rect(s, x, In(4.7), In(2.9), In(1.0),
             fill_rgb=RGBColor(0x1A,0x30,0x5C), line_rgb=C_AMBER, line_pt=0.8)
    add_text(s, val, x+In(0.1), In(4.72), In(2.7), In(0.55),
             font_size=28, bold=True, color=C_AMBER, align=PP_ALIGN.CENTER)
    add_text(s, lbl, x+In(0.1), In(5.28), In(2.7), In(0.35),
             font_size=10, color=C_WHITE, align=PP_ALIGN.CENTER)

add_text(s, "Orientador: Edilson José Rodrigues",
         In(0.3), H-In(0.6), In(8), In(0.4),
         font_size=12, color=RGBColor(0x90,0xA4,0xAE), italic=True)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — EM TRÊS MINUTOS (resumo executivo: a resposta antes da evidência)
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, "Em três minutos", "O que foi medido, o que se achou e o que isso muda", numerar=False)

_tres = [
    ("O contexto",
     f"Entre 2016 e 2025, um trabalhador negro ganhou em média {fmt(P['GAP_POOL'],1)}% a menos "
     f"que um branco com a mesma escolaridade, idade e sexo."),
    ("O desequilíbrio",
     f"Comparando só pessoas do mesmo bairro, o gap cai {fmt(P['MED_BAIRRO'],1)}% "
     f"(a parte mediada pela segregação residencial) — e ainda sobram "
     f"{fmt(P['GAP_M3'],1)}%, dos quais {fmt(P['GAP_M4'],1)}% persistem dentro da mesma ocupação."),
    ("A evidência",
     f"Quatro métodos independentes sobre a população da PNAD Contínua "
     f"({fmtN(P['N_UPAS'])} bairros): o bairro medeia {fmt(P['MED_BAIRRO'],1)}% do gap; "
     f"{fmt(P['RET_PCT'],1)}% do gap são retornos diferenciais; a penalidade cresce no topo; "
     f"e a chance de chegar a um cargo qualificado é {fmt(P['OR_M2_menor_pct'],0)}% menor."),
    ("O que muda",
     "Entre os mais escolarizados, a penalidade salarial é pequena, mas a desvantagem de "
     "acesso persiste — política de educação isolada não alcança a porta."),
]
for _i, (_tit, _txt) in enumerate(_tres):
    _y = In(1.35) + _i * In(1.28)
    add_rect(s, In(0.4), _y, In(12.5), In(1.1), fill_rgb=C_LGRAY)
    add_text(s, _tit, In(0.65), _y + In(0.12), In(2.6), In(0.4),
             font_size=17, bold=True, color=C_DARK)
    add_text(s, _txt, In(3.35), _y + In(0.12), In(9.3), In(1.0),
             font_size=13.5, color=C_BLACK)

add_rect(s, In(0.4), In(6.38), In(12.5), In(0.75), fill_rgb=C_RED)
add_text(s, frase_sintese(_PN),
         In(0.6), In(6.42), In(12.1), In(0.68),
         font_size=13, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
footer(s, 2)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — O PROBLEMA
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, "Mesma escolaridade, salário menor: o gap racial não é só qualificação",
           "Por que olhar o gap racial brasileiro com métodos multinível?")

add_text(s, "O gap salarial racial persiste mesmo após décadas de políticas inclusivas",
         In(0.4), In(1.25), In(7.2), In(0.8),          # termina antes da caixa da direita
         font_size=18, bold=True, color=C_DARK)

bullet_box(s, [
    f"A renda média de negros é {fmt(P['GAP_MEDIA'],1)}% menor que a de brancos — bruta, sem controles",
    "O gap persiste mesmo após controlar escolaridade, sexo e experiência: é estrutural",
    "Mecanismos: segregação residencial, barreira de acesso às ocupações, teto de vidro",
    "Estudos tradicionais usam apenas OLS — não separam ACESSO de REMUNERAÇÃO",
], In(0.4), In(2.15), In(7.2), In(2.8), font_size=15)

add_rect(s, In(7.8), In(1.2), In(5.2), In(4.8),
         fill_rgb=C_LGRAY, line_rgb=C_DARK, line_pt=0.8)
add_text(s, "Inovações deste TCC", In(8.0), In(1.35), In(4.8), In(0.4),
         font_size=14, bold=True, color=C_DARK)
for i, item in enumerate([
    f"✦ {fmt(P['N_BRUTO'] / 1e6, 1)}M obs. — série histórica completa",
    "✦ CBO, vínculo, horas e escolaridade (V4010/VD4009/VD4031/VD3004) extraídos dos ZIPs brutos do IBGE",
    "✦ Discriminação de ACESSO (GLMM logístico)",
    "✦ Discriminação de REMUNERAÇÃO (HLM + QR)",
    "✦ Convergência de 4 métodos do núcleo + robustez",
]):
    # altura pelo número de linhas (~42 caracteres por linha em 13 pt): com passo fixo,
    # o item de três linhas encostava no seguinte e os vãos ficavam desiguais
    if i == 0:
        _y = In(1.85)
    _linhas = -(-len(item) // 42)
    add_text(s, item, In(8.1), _y, In(4.7), In(0.27) * _linhas + In(0.1),
             font_size=13, color=C_BLACK if i > 0 else C_BLUE)
    _y += In(0.27) * _linhas + In(0.3)

footer(s, 2)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — DADOS E DATASET
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, f"Dez anos de PNAD Contínua: {fmt(P['N_GLMM'] / 1e6, 1)} milhões de trabalhadores, "
              f"{fmt(P['N_UPAS'] / 1e3, 0)} mil bairros",
           "PNAD Contínua 2016–2025 | renda em reais do 2º tri/2026 (deflator IBGE) + efeito de ano")

kpi_box(s, "Observações brutas", f"{fmt(P['N_BRUTO'] / 1e6, 1)}M", "PNAD 2016–2025", In(0.3), In(1.2))
kpi_box(s, "PEA com renda positiva", f"{fmt(P['N_GLMM'] / 1e6, 1)}M", "após filtros", In(3.3), In(1.2))
kpi_box(s, "UPAs (bairros)", fmtN(P["N_UPAS"]), "Nível 2 do HLM", In(6.3), In(1.2))
kpi_box(s, "Cobertura temporal", "10 anos", "2016 T1 → 2025", In(9.3), In(1.2))

add_text(s, "Enriquecimento dos microdados:", In(0.4), In(2.7), In(12), In(0.4),
         font_size=16, bold=True, color=C_DARK)

cols = [
    ("V4010  →  ocp_grupo_cbo", "Grupo ocupacional CBO-Domiciliar\n(10 grupos ISCO-08)"),
    ("VD4009  →  emprego_formal", "Vínculo empregatício detalhado\n(carteira, servidor, conta-própria...)"),
    ("VD4031  →  horas_c", "Horas habitualmente\ntrabalhadas (centrada)"),
]
for i, (var, desc) in enumerate(cols):
    x = In(0.3) + i*In(4.3)
    add_rect(s, x, In(3.15), In(4.1), In(1.5),
             fill_rgb=RGBColor(0xE3,0xF2,0xFD), line_rgb=C_BLUE, line_pt=0.8)
    add_text(s, var, x+In(0.15), In(3.22), In(3.8), In(0.5),
             font_size=13, bold=True, color=C_BLUE, font_name="Courier New")
    add_text(s, desc, x+In(0.15), In(3.7), In(3.8), In(0.85),
             font_size=12, color=C_BLACK)

add_text(s, "Estratégia: leitura seletiva dos ZIPs originais do IBGE — sem re-download.\n"
            "Join por chave composta (Ano+Trimestre+UPA+V1008+V2003) com os microdados da PNAD.",
         In(0.4), In(4.85), In(12.5), In(0.9),
         font_size=13, color=C_GRAY, italic=True)

# a UPA é do desenho da PNAD, não um recorte do trabalho — a banca precisa ouvir isso cedo
add_rect(s, In(0.3), In(5.85), In(12.7), In(1.0),
         fill_rgb=RGBColor(0xFF, 0xF9, 0xE7), line_rgb=C_AMBER, line_pt=1)
add_text(s, "O que chamamos de “bairro”: a UPA (Unidade Primária de Amostragem) é do desenho "
            "da própria PNAD — o setor censitário, ou setores vizinhos, que o IBGE sorteia e "
            "identifica no microdado. Não é um recorte criado pelo trabalho; é a menor unidade "
            "territorial que a PNAD permite enxergar.",
         In(0.5), In(5.92), In(12.3), In(0.9), font_size=13, color=C_DARK)

footer(s, 3)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — ANÁLISE DESCRITIVA
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, "Antes de qualquer modelo: brancos e negros não moram nos mesmos bairros",
           f"Gap mediano bruto de {fmt(P['GAP_MEDIANA'],1)}% | ponderado pelo desenho amostral | "
           f"reais do 2º tri/2026 | PNAD Contínua 2016–2025")

add_img(s, FIGURES / "fig1_densidade_log_salario.png", In(0.3), In(1.2), In(6.4), In(4.5))

add_text(s, "O que os números dizem", In(7.0), In(1.2), In(6.1), In(0.4),
         font_size=16, bold=True, color=C_DARK)

kpi_box(s, "Gap mediano bruto", f"{fmt(P['GAP_MEDIANA'],1)}%",
        f"brancos R${fmtN(P['MED_BR'])} vs negros R${fmtN(P['MED_NG'])}", In(7.0), In(1.75), w=In(2.9), val_color=C_RED)
kpi_box(s, "Gap na média", f"{fmt(P['GAP_MEDIA'],1)}%",
        f"brancos R${fmtN(P['MEDIA_BR'])} vs negros R${fmtN(P['MEDIA_NG'])}", In(10.1), In(1.75), w=In(3.1), val_color=C_RED)
kpi_box(s, "Gap log-renda", f"{fmt(P['GAP_LOG'],1)}",
        "diferença de médias do log, em log-pontos", In(7.0), In(3.15), w=In(2.9), val_color=C_RED)
kpi_box(s, "Formal (brancos/neg.)", f"{fmt(P['FORMAL_BR'],1)}%/{fmt(P['FORMAL_NG'],1)}%",
        f"{fmt(P['FORMAL_DIF'],1)} p.p. a menos de emprego formal", In(10.1), In(3.15), w=In(3.1), val_color=C_AMBER)

add_rect(s, In(7.0), In(4.55), In(6.1), In(1.15),     # termina antes da faixa vermelha
         fill_rgb=RGBColor(0xE3,0xF2,0xFD), line_rgb=C_DARK, line_pt=0.8)
add_text(s, "Interpretação da curva de densidade:",
         In(7.15), In(4.58), In(5.8), In(0.3),
         font_size=12, bold=True, color=C_DARK)
add_multiline(s, [
    "▸  Curva vermelha (negros) deslocada à esquerda ao longo de toda a distribuição",
    "▸  Linhas tracejadas = médias de log-renda de cada grupo",
    "▸  A curva dos negros está à esquerda em toda a distribuição; a QR e a RIF mostram onde pesa mais",
], In(7.15), In(4.88), In(5.8), In(0.8), font_size=11, color=C_BLACK)

add_rect(s, In(0.3), In(5.85), In(12.7), In(0.65),
         fill_rgb=RGBColor(0xFF,0xEB,0xEE), line_rgb=C_RED, line_pt=0.8)
add_text(s, f"O gap persiste em TODOS os níveis educacionais — inclusive pós-graduação ({fmt(P['GAP_MEDIANA_POS'],1)}% na mediana). "
            "Educação é condição necessária, mas não suficiente para eliminar a desigualdade racial.",
         In(0.5), In(5.9), In(12.3), In(0.55),
         font_size=12, bold=True, color=C_RED, align=PP_ALIGN.CENTER)
footer(s, 4)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — ARQUITETURA METODOLÓGICA
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, "Quatro métodos que respondem a quatro perguntas diferentes",
           "Núcleo de 4 métodos + robustez (ML/SHAP) — convergência de evidências")

metodos = [
    (C_DARK,  "HLM",            "Modelo Hierárquico Linear\n(indivíduo em UPA, UF fixa)", "Gap médio e\nmediação contextual",
     "Quanto do gap está no bairro onde se mora?"),
    (C_RED,   "Oaxaca-Blinder", "Decomposição do gap\nem dotações vs retornos",     "ONDE opera\na discriminação",
     "O gap é diferença de características ou de preço pago por elas?"),
    (C_AMBER, "GLMM logístico", "Regressão logística\ncom intercepto de UPA",       "Gap de ACESSO\na oportunidades",
     "Quem, com o mesmo perfil, chega ao cargo qualificado e ao topo da renda?"),
    (C_GREEN, "QR + RIF-OB",    "Gap por quantil\nda distribuição",                 "Teto de vidro e\npiso pegajoso",
     "A penalidade é a mesma na base e no topo da distribuição?"),
    (C_GRAY2, "Robustez",       "XGBoost + SHAP,\nE-value, Konfound",               "Fora do núcleo:\nconfere o núcleo",
     "O resultado sobrevive a outro modelo e a um confundidor omitido?"),
]
for i, (color, title, desc, purpose, pergunta) in enumerate(metodos):
    x = In(0.25) + i * In(2.6)
    add_rect(s, x, In(1.25), In(2.45), In(4.8),
             fill_rgb=RGBColor(0xF5,0xF5,0xF5), line_rgb=color, line_pt=1.5)
    add_rect(s, x, In(1.25), In(2.45), In(0.5), fill_rgb=color)
    add_text(s, title, x+In(0.1), In(1.28), In(2.25), In(0.45),
             font_size=13, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    add_text(s, desc, x+In(0.1), In(1.85), In(2.25), In(0.9),
             font_size=11.5, color=C_BLACK, align=PP_ALIGN.CENTER)
    add_rect(s, x+In(0.1), In(2.85), In(2.25), In(0.02), fill_rgb=color)
    add_text(s, purpose, x+In(0.1), In(2.95), In(2.25), In(0.7),
             font_size=12, bold=True, color=color, align=PP_ALIGN.CENTER)
    # a pergunta que o método responde: preenche a metade de baixo, que ficava vazia
    add_rect(s, x+In(0.1), In(3.85), In(2.25), In(0.02), fill_rgb=color)
    add_text(s, "Pergunta", x+In(0.1), In(3.95), In(2.25), In(0.35),
             font_size=10.5, bold=True, color=C_GRAY2, align=PP_ALIGN.CENTER)
    add_text(s, pergunta, x+In(0.15), In(4.3), In(2.15), In(1.6),
             font_size=14, color=C_DARK, align=PP_ALIGN.CENTER)

add_rect(s, In(0.3), In(6.15), In(12.7), In(0.5),
         fill_rgb=RGBColor(0xE8,0xEA,0xF0), line_rgb=C_DARK, line_pt=0.5)
add_text(s, "Discriminação de ACESSO (GLMM) + Discriminação de REMUNERAÇÃO (HLM + Quantílica/RIF) + Penalidade interseccional (raça×gênero)",
         In(0.4), In(6.2), In(12.5), In(0.4),
         font_size=13, bold=True, color=C_DARK, align=PP_ALIGN.CENTER)
footer(s, 5)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 14 — JUSTIFICAÇÃO METODOLÓGICA
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, f"Por que multinível: {fmt(P['ICC_UPA_pct'], 0)}% da variação da renda está entre bairros",
           f"Modelo nulo: τ²={fmt(P['TAU2_M0'], 4)} entre bairros e σ²={fmt(P['SIGMA2_M0'], 4)} dentro deles "
           f"— ignorar essa estrutura invalida a inferência")

add_img(s, FIGURES / "hlm_efeitos_uf_blup_upa.png", In(0.55), In(1.2), In(12.2), In(3.45))

kpi_box(s, "ICC do bairro (UPA)", f"{fmt(P['ICC_UPA_pct'], 1)}%",
        "τ²/(τ²+σ²) — Raudenbush & Bryk (2002)", In(0.35), In(4.75), w=In(4.0), val_color=C_BLUE)
kpi_box(s, "Bairros no HLM", fmtN(P["N_UPAS_HLM"]),
        "contra 27 UFs — daí UPA aleatória e UF fixa", In(4.55), In(4.75), w=In(4.2), val_color=C_BLUE)
kpi_box(s, "LR do contexto do bairro", fmtN(P["LR_M2"]),
        "M2 vs. M1 — o contexto não é ornamento", In(8.95), In(4.75), w=In(4.05), val_color=C_GREEN)

bullet_box(s, [
    "A PNAD amostra por conglomerados: ignorar a correlação intra-UPA subestima os erros-padrão (Moulton)",
    "27 UFs são poucas para um terceiro nível aleatório — entram como 26 efeitos fixos, sem hipótese distribucional",
    "Contraprova: tudo reestimado com efeitos fixos de UF e erro agrupado por UPA leva às mesmas conclusões",
], In(0.35), In(6.15), In(12.6), In(1.0), font_size=12.5, dot_color=C_DARK)

footer(s, 5)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE — INCLINAÇÕES ALEATÓRIAS (retas por bairro, no formato do Fávero)
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
_rs_maior = P["HLM_RS_CORR"] < 0
header_bar(s, "A penalidade racial muda de bairro para bairro — e é " +
           ("maior" if _rs_maior else "menor") + " onde a renda é mais alta",
           f"M3 com intercepto e inclinação de negro aleatórios por UPA | LR = {fmtN(P['LR_RS'])} "
           f"(2 g.l.) contra o M3 de inclinação única")
add_img(s, FIGURES / "hlm_rs_retas_upa.png", In(0.3), In(1.2), In(12.7), In(4.85))
add_rect(s, In(0.3), In(6.15), In(12.7), In(0.85),
         fill_rgb=RGBColor(0xE3, 0xF2, 0xFD), line_rgb=C_DARK, line_pt=0.8)
add_text(s, f"Inclinação média {fmt(P['B_M3_RS'], 3)} log-pontos, com desvio-padrão de "
            f"{fmt(P['HLM_RS_SD_SLOPE'], 3)} entre bairros; a correlação entre renda-base e "
            f"inclinação é {fmt(P['HLM_RS_CORR'], 2)}. A discriminação salarial tem geografia.",
         In(0.5), In(6.22), In(12.3), In(0.75), font_size=13, bold=True, color=C_DARK)
footer(s)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — HLM: DECOMPOSIÇÃO DO GAP
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, f"{titulo_bairro(_PN)}",
           f"Do gap agregado de {fmt(P['GAP_POOL'], 1)}% ao que persiste dentro da mesma ocupação, "
           f"{fmt(P['GAP_M4'], 1)}% — cada degrau acrescenta um bloco de controles")

# Cada barra é um degrau do step-up; os valores vêm de gap_decomposicao_stepup.csv
levels = [
    ("Agregado\n(sem bairro)", P["GAP_POOL"], C_RED,
     "Individual + UF, comparando\npessoas de bairros diferentes"),
    ("M1\n(mesmo bairro)", P["GAP_M1"], C_BLUE,
     f"O bairro medeia {fmt(P['MED_BAIRRO'], 1)}% do gap agregado"),
    ("M3\n(gap líquido)", P["GAP_M3"], C_AMBER,
     "Após contexto do bairro e efeitos\nfixos de estado"),
    ("M4\n(dentro da ocupação)", P["GAP_M4"], C_GREEN,
     "Limite inferior: a ocupação é ela\nprópria resultado da barreira"),
]
bar_top = In(1.45)
bar_left = In(2.0)
bar_w_total = In(9.4)
max_val = P["GAP_POOL"] * 1.05

for i, (label, val, color, note) in enumerate(levels):
    bw = bar_w_total * (val / max_val)
    add_rect(s, bar_left, bar_top + i*In(1.15), bw, In(0.8), fill_rgb=color)
    add_text(s, f"{fmt(val, 1)}%", bar_left + bw + In(0.12), bar_top + i*In(1.15) + In(0.2),
             In(1.0), In(0.45), font_size=16, bold=True, color=color)
    add_text(s, label, In(0.15), bar_top + i*In(1.15) + In(0.05),
             In(1.7), In(0.75), font_size=10.5, color=C_BLACK, align=PP_ALIGN.RIGHT, bold=True)
    if bw > In(6.5):     # barra longa: a nota não cabe à direita, vai dentro da barra
        add_text(s, note.replace("\n", " "), bar_left + In(0.15), bar_top + i*In(1.15) + In(0.2),
                 bw - In(0.3), In(0.45), font_size=11, color=RGBColor(0xFF, 0xFF, 0xFF), italic=True)
    else:
        add_text(s, note, bar_left + bw + In(1.15), bar_top + i*In(1.15) + In(0.12),
                 In(4.6), In(0.62), font_size=10, color=C_GRAY, italic=True)

add_rect(s, In(0.4), In(6.25), In(12.5), In(0.62),
         fill_rgb=RGBColor(0xFF,0xF9,0xE7), line_rgb=C_AMBER, line_pt=1)
add_text(s, f"Achado central: {fmt(P['MED_ACUM_M4'], 1)}% do gap é mediado pelo bairro e pela ocupação "
            f"— mas {fmt(P['GAP_M4'], 1)}% persistem dentro da mesma ocupação, e {fmt(P['GAP_M3'], 1)}% "
            f"sem tratar a ocupação como característica.",
         In(0.6), In(6.33), In(12.1), In(0.5),
         font_size=12.5, bold=True, color=C_DARK)
footer(s, 6)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — COMPOSIÇÃO OCUPACIONAL E GLASS CEILING
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, "A ocupação explica muito — mas a ocupação é ela própria desigual",
           "Sub-representação sistemática nos grupos de alto prestígio")

# uma figura só, em largura total: as duas lado a lado ficavam ilegíveis, e a dos
# percentis do topo repete o que o GLMM (topo 10%/20%) e a QR mostram adiante
add_img(s, FIGURES / "comp_razao_grupo_cbo.png", In(0.3), In(1.2), In(12.7), In(4.45))

add_rect(s, In(0.3), In(5.8), In(12.7), In(0.6),
         fill_rgb=RGBColor(0xFF,0xEB,0xEE), line_rgb=C_RED, line_pt=0.8)
# razões lidas de composicao_por_grupo_cbo.csv (capitais)
_comp = {r["grupo"]: float(r["razao_nn_bb"])
         for r in pd.read_csv(TABLES / "composicao_por_grupo_cbo.csv").to_dict("records")
         if r["area"] == "Capital"}
add_text(s,
    f"Dirigentes: {fmt(_comp['dirigente'] * 100, 0)} negros para cada 100 brancos na mesma função  |  "
    f"Ocupações elementares: {fmt(_comp['elementar'], 2)}x mais negros que brancos  |  "
    f"E a chance de acesso ao cargo qualificado é {fmt(P['OR_M2_menor_pct'], 0)}% menor (GLMM)",
    In(0.5), In(5.85), In(12.3), In(0.55),
    font_size=12, bold=True, color=C_RED, align=PP_ALIGN.CENTER)
footer(s, 7)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — OAXACA-BLINDER
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, "Tratar a ocupação como “característica” reduz pouco a discriminação medida",
           f"Gap total {fmt(P['GAP_PCT'],1)}% | {fmt(P['DOT_PCT'],0)}% explicado por características sem a ocupação, "
           f"{fmt(P['DOT_PCT_COM'],0)}% com ela")

# figura maior (8,5" em vez de 7,5") e implicação numa faixa larga embaixo: antes a
# metade inferior do slide ficava vazia
add_img(s, FIGURES / "fig_ob_cascata.png", In(0.3), In(1.3), In(8.5))

add_text(s, "Interpretação", In(9.0), In(1.2), In(4.1), In(0.4),
         font_size=16, bold=True, color=C_DARK)
bullet_box(s, [
    f"{fmt(P['DOT_PCT_COM'],0)}% = Efeito DOTAÇÕES\nNegros têm menor acesso a ocupações de prestígio, emprego formal, mais horas em subemprego",
    f"{fmt(P['RET_PCT_COM'],0)}% = Efeito RETORNOS\nO mercado remunera as mesmas características a taxas diferentes por raça",
    (f"Conclusão: {fmt(P['OB_COM_RET_PCT'],1)} dos {fmt(P['OB_SEM_RET_PCT'],1)} pontos não explicados "
     f"persistem dentro da mesma ocupação; a porta de entrada responde pelos outros "
     f"{fmt(P['OB_SEM_RET_PCT'] - P['OB_COM_RET_PCT'],1)} — e é medida diretamente pelo GLMM "
     f"(OR {or_str(P['OR_M2'])})")
    if P['OB_COM_RET_PCT'] > P['OB_SEM_RET_PCT'] - P['OB_COM_RET_PCT'] else
    "Conclusão: a maior parte da parcela não explicada opera na porta de entrada das ocupações",
], In(9.0), In(1.7), In(4.1), In(3.6), font_size=13, dot_color=C_BLUE)

add_rect(s, In(0.3), In(5.55), In(12.8), In(0.95),
         fill_rgb=RGBColor(0xE3,0xF2,0xFD), line_rgb=C_BLUE, line_pt=0.8)
add_text(s, "Implicação de política:", In(0.5), In(5.62), In(12.4), In(0.3),
         font_size=12, bold=True, color=C_BLUE)
add_text(s, "Combater APENAS desigualdade salarial é insuficiente. É preciso atacar as barreiras de ACESSO a ocupações qualificadas.",
         In(0.5), In(5.95), In(12.4), In(0.45),
         font_size=14, color=C_BLACK)
footer(s, 8)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — LOGIT MULTINÍVEL
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, f"Também há barreira na porta: chances {fmt(P['OR_M2_menor_pct'],0)}% menores de chegar a cargo qualificado",
           f"GLMM lme4 com efeito aleatório de UPA — barreira de ACESSO "
           f"(n={fmtN(P['N_GLMM'])}, {fmtN(P['N_UPAS'])} UPAs)")

add_img(s, FIGURES / "fig_glmm_or.png", In(0.3), In(1.2), In(7.0))

add_text(s, "Resultados-chave (GLMM)", In(7.6), In(1.2), In(5.5), In(0.4),
         font_size=16, bold=True, color=C_DARK)

kpis_logit = [
    (f"OR = {or_str(P['OR_M1'])}", "Ocupação qualificada\n(A1 — individual + UF)", C_RED),
    (f"OR = {or_str(P['OR_M2'])}", "Ocupação qualificada\n(A2 — + contexto do bairro)", C_AMBER),
    (f"AME = {ame(P['AME_M1_pp'])}", "Efeito marginal, controles individuais\n(A1 — sem contexto do bairro)", C_RED),
    (f"AME = {ame(P['AME_M2_pp'])}", "Efeito marginal com contexto\n(A2 — mesmo bairro)", C_RED),
]
for i, (val, lbl, color) in enumerate(kpis_logit):
    add_rect(s, In(7.6), In(1.7)+i*In(0.97), In(5.4), In(0.82),
             fill_rgb=C_LGRAY, line_rgb=color, line_pt=1)
    add_text(s, val, In(7.75), In(1.73)+i*In(0.97), In(2.5), In(0.45),
             font_size=18, bold=True, color=color)
    add_text(s, lbl, In(10.3), In(1.73)+i*In(0.97), In(2.6), In(0.55),
             font_size=11, color=C_GRAY)

add_rect(s, In(7.6), In(5.65), In(5.4), In(0.95),
         fill_rgb=RGBColor(0xFF,0xEB,0xEE), line_rgb=C_RED, line_pt=0.8)
add_text(s, f"Mesmo com educação, sexo, idade e local de moradia IDÊNTICOS, negros têm chance (odds) "
            f"{fmt(P['OR_M2_menor_pct'],1)}% menor de estar em ocupação qualificada (OR={or_str(P['OR_M2'])}, GLMM A2).",
         In(7.75), In(5.72), In(5.1), In(0.85),
         font_size=12, bold=True, color=C_RED)
footer(s, 10)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 9b — DIPLOMA × PORTA (E2.15, aprovado em 03/10/2026)
# Só entra se a escada educacional sustentar o contraste (frase_diploma condicional).
# ══════════════════════════════════════════════════════════════════════════════
_fd = frase_diploma(_PN)
if _fd.startswith("O diploma quase iguala") and (FIGURES / "hlm_negro_por_educ_retas.png").exists():
    s = prs.slides.add_slide(BLANK)
    header_bar(s, "O diploma quase iguala o salário — não a porta",
               "Penalidade salarial por nível de escolaridade (HLM) × chances de chegar a "
               "cargo qualificado (GLMM, A4)")
    add_img(s, FIGURES / "hlm_negro_por_educ_retas.png", In(0.3), In(1.2), In(7.6), In(5.4))
    kpi_box(s, "Salário, sem fundamental completo", f"−{fmt(_PN['NE_GAP_SEMFUND'], 1)}%",
            "penalidade racial condicional", In(8.2), In(1.3), w=In(4.8), val_color=C_RED)
    kpi_box(s, "Salário, pós-graduação", f"−{fmt(_PN['NE_GAP_POS'], 1)}%",
            "quase igual ao branco de mesmo perfil", In(8.2), In(2.8), w=In(4.8), val_color=C_AMBER)
    kpi_box(s, "Acesso a cargo qualificado, pós-graduação",
            f"−{fmt(_PN['PCTPOS_ocp_qualif'], 0)}%", "nas chances (odds), GLMM A4",
            In(8.2), In(4.3), w=In(4.8), val_color=C_RED)
    add_text(s, "Diferenças condicionais entre pessoas comparáveis — não o efeito de estudar mais.",
             In(8.2), In(5.75), In(4.8), In(0.6), font_size=11, color=C_GRAY, italic=True)
    footer(s, 10)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 11 — REGRESSÃO QUANTÍLICA
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, "Entre pares, a penalidade racial cresce rumo ao topo",
           "O gap racial aumenta no topo da distribuição de renda — confirmação formal")

# figura larga (dois painéis): ocupa a largura do slide; a leitura vai numa faixa abaixo
add_img(s, FIGURES / "fig_qr_rif.png", In(0.3), In(1.2), In(12.7), In(4.75))

add_rect(s, In(0.3), In(6.05), In(12.7), In(0.95),
         fill_rgb=RGBColor(0xFF,0xEB,0xEE), line_rgb=C_RED, line_pt=1)
add_text(s, f"Teto de vidro: a penalidade condicional vai de {fmt(-P['QR_B_Q10']*100,1)} log-pontos "
            f"({fmt(P['QR_GAP_Q10'],1)}%) no q10 a {fmt(-P['QR_B_Q90']*100,1)} log-pontos "
            f"({fmt(P['QR_GAP_Q90'],1)}%) no q90 (Z = {fmt(P['QR_Z'],2)}, bootstrap em blocos de UPA). "
            "O painel da direita — a RIF-OB — é o tema do próximo slide.",
         In(0.5), In(6.12), In(12.3), In(0.85), font_size=13, bold=True, color=C_DARK)
footer(s, 11)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 12 — RIF-OB: STICKY FLOOR vs GLASS CEILING POR DOTAÇÕES
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, (f"Na base da distribuição, o preço pesa {fmt(P['RIF_RET_RAZAO'],1)} vezes mais que no topo"
               if P["RIF_RET_Q10"] < 50 else
               "Na base da distribuição, a maior parte do gap é preço, não característica"),
           f"Firpo, Fortin & Lemieux (2018) | N={fmtN(P['OB_N'])} | Decomposição incondicional por quantil")

# Tabela no lugar da figura rif_ob_retornos_quantis.png: aquela normaliza pelo gap
# observado (34% / 12%) e brigava, no mesmo slide, com a conta do relatório, que
# normaliza pelo gap RIF (Dotações + Retornos = 100%, tab:rif_ob).
add_table_resumo(
    s,
    ["Quantil", "Gap obs. (log)", "Dotações", "Retornos"],
    [[f"q{q}", fmt(P[f"RIF_GAP_Q{q}"], 3), f"{fmt(P[f'RIF_DOT_Q{q}'],1)}%", f"{fmt(P[f'RIF_RET_Q{q}'],1)}%"]
     for q in ("10", "25", "50", "75", "90")],
    In(0.4), In(1.35), In(6.7), In(3.9), col_w=[In(1.3), In(1.9), In(1.75), In(1.75)], font_size=14)
add_text(s, "Dotações + Retornos = 100% do gap RIF em cada quantil, como na tabela do relatório.",
         In(0.4), In(5.35), In(6.7), In(0.5), font_size=11, italic=True, color=C_GRAY)

add_text(s, "O que a RIF-OB revela além da QR?", In(7.5), In(1.2), In(5.6), In(0.4),
         font_size=15, bold=True, color=C_DARK)

bullet_box(s, [
    f"Retornos DECLINAM: q10={fmt(P['RIF_RET_Q10'],1)}% → q90={fmt(P['RIF_RET_Q90'],1)}%  "
    f"(Δ = {fmt(P['RIF_RET_DELTA'],1)} pp)",
    f"Dotações CRESCEM: q10={fmt(P['RIF_DOT_Q10'],1)}% → q90={fmt(P['RIF_DOT_Q90'],1)}%  "
    f"(Δ = +{fmt(P['RIF_DOT_DELTA'],1)} pp)",
    "No topo, o gap é consistente com desvantagens PRÉ-MERCADO\n(educação, jornada, segregação residencial)",
    "Mais do que com um preço diferente cobrado no topo",
], In(7.5), In(1.75), In(5.6), In(3.6), font_size=14, dot_color=C_RED)

add_rect(s, In(0.3), In(6.3), In(12.7), In(0.55),
         fill_rgb=RGBColor(0xFF,0xEB,0xEE), line_rgb=C_RED, line_pt=1)
add_text(s, f"Piso pegajoso: a parcela de retornos é {fmt(P['RIF_RET_RAZAO'],1)}× maior na base "
            f"(q10={fmt(P['RIF_RET_Q10'],1)}%) do que no topo (q90={fmt(P['RIF_RET_Q90'],1)}%). "
            "Fiscalizar igual pagamento atua na base; ampliar acesso e dotações atua no topo.",
         In(0.5), In(6.35), In(12.3), In(0.45),
         font_size=12, bold=True, color=C_DARK)
footer(s, 12)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 13 — INTERSECCIONALIDADE OB 4 GRUPOS
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, "A mulher negra entra pelas ocupações feminizadas, mas não chega ao comando nem ao topo",
           f"Esquerda: acesso (GLMM); direita: salário (Oaxaca vs. homem branco) "
           + (f"| gap dela {fmt(_INT_MN,3)} < soma {fmt(_INT_SOMA,3)} log-pontos: desvantagens se acumulam"
              if _INT_SUB else
              f"| em log-pontos, gap dela {fmt(_INT_MN,3)} > soma {fmt(_INT_SOMA,3)}"))

add_img(s, FIGURES / "grupo_rg_interseccional.png", In(0.3), In(1.2), In(6.5))

add_text(s, "Salário: Oaxaca-Blinder dos 4 grupos", In(7.1), In(1.2), In(5.9), In(0.4),
         font_size=15, bold=True, color=C_DARK)

grupos_int = [
    (C_BLUE,                       f"Mulher Branca — gap {fmt(P['INT_MULHER_BRANCA_GAP'],1)}%",
     f"Retornos dominam: {fmt(P['INT_MULHER_BRANCA_RET'],0)}%\nPenalidade de gênero sobre o mesmo perfil\n"
     f"(dotações a favor dela: {fmt(P['INT_MULHER_BRANCA_DOT'],1)}%)"),
    (C_RED,                        f"Homem Negro — gap {fmt(P['INT_HOMEM_NEGRO_GAP'],1)}%",
     f"Dotações dominam: {fmt(P['INT_HOMEM_NEGRO_DOT'],0)}%\nGap majoritariamente de composição\n"
     "(escolaridade, ocupação, bairro)"),
    (RGBColor(0x6A, 0x00, 0x8A),   f"Mulher Negra — gap {fmt(P['INT_MULHER_NEGRA_GAP'],1)}%",
     (f"O maior gap, mas abaixo da soma dos dois eixos\nem log-pontos ({fmt(_INT_MN,3)} < {fmt(_INT_SOMA,3)}): "
      "acumula as duas\ndesvantagens sem multiplicá-las (Crenshaw, 1989)") if _INT_SUB else
     (f"Acima da soma dos dois eixos em log-pontos\n({fmt(_INT_MN,3)} > {fmt(_INT_SOMA,3)}): efeito "
      "interseccional\nalém da soma (Crenshaw, 1989)")),
]
for i, (color, titulo, desc) in enumerate(grupos_int):
    add_rect(s, In(7.1), In(1.72)+i*In(1.68), In(5.9), In(1.52),
             fill_rgb=C_LGRAY, line_rgb=color, line_pt=1.5)
    add_rect(s, In(7.1), In(1.72)+i*In(1.68), In(5.9), In(0.48), fill_rgb=color)
    add_text(s, titulo, In(7.22), In(1.75)+i*In(1.68), In(5.65), In(0.45),
             font_size=13, bold=True, color=C_WHITE)
    add_text(s, desc, In(7.22), In(2.28)+i*In(1.68), In(5.65), In(0.92),
             font_size=12, color=C_BLACK)

add_rect(s, In(0.3), In(6.78), In(12.7), In(0.56),
         fill_rgb=RGBColor(0xE3,0xF2,0xFD), line_rgb=C_DARK, line_pt=0.8)
# E2.16: o OR agregado de CBO 1–4 (acima de 1) junta portas diferentes — por grande grupo
add_text(s, (f"Acesso por grande grupo: dirigentes OR={fmt(P['CBO_MN_dirigente'],2)}; "
             f"apoio administrativo {fmt(P['CBO_MN_administrativo'],2)} (mulher branca "
             f"{fmt(P['CBO_MB_administrativo'],2)}). Top 10%: OR={fmt(P['GRG_MN_TOP10'],2)}, "
             f"o grupo mais distante do homem branco.")
            if "CBO_MN_dirigente" in P else
            (f"Acesso: OR={fmt(P['GRG_MN_OCP_QUALIF'],2)}, acima do homem branco; top 10%: "
             f"OR={fmt(P['GRG_MN_TOP10'],2)}, o grupo mais distante dele. "
             f"Interação negro×mulher sub-aditiva (OR={fmt(P['GRG_INT_OCP_QUALIF'],2)})."),
         In(0.5), In(6.83), In(12.3), In(0.45),
         font_size=12, color=C_DARK)
footer(s, 13)

# ══════════════════════════════════════════════════════════════════════════════
# HETEROGENEIDADE (E8, 04/10/2026): o que o agregado esconde — cor, setor e idade
# ══════════════════════════════════════════════════════════════════════════════
if "HET_HLM_PRETO" in P:
    s = prs.slides.add_slide(BLANK)
    header_bar(s, "O agregado esconde: os pretos, o setor privado e os mais velhos",
               "Mesmos modelos por recorte — mesmo perfil e mesmo bairro, contra brancos")
    _r = lambda k, d=3: fmt(P[k], d) if k in P else "—"
    add_table_resumo(
        s, ["Recorte", "Penalidade salarial", "OR cargo qualificado", "OR top 10%"],
        [["Negro (categoria do trabalho)", f"{fmt(P['GAP_M3'],1)}%", _r("OR_OCP_M2"), _r("OR_TOP10_M2")],
         ["   Pardo", f"{_r('HET_HLM_PARDO',1)}%", _r("HET_OR_PARDO_OCP"), _r("HET_OR_PARDO_T10")],
         ["   Preto", f"{_r('HET_HLM_PRETO',1)}%", _r("HET_OR_PRETO_OCP"), _r("HET_OR_PRETO_T10")],
         ["Setor privado", f"{_r('HET_HLM_SETOR0',1)}%", _r("HET_OR_SETOR0_OCP"), _r("HET_OR_SETOR0_T10")],
         ["Setor público", f"{_r('HET_HLM_SETOR1',1)}%", _r("HET_OR_SETOR1_OCP"), _r("HET_OR_SETOR1_T10")],
         ["14–29 anos  →  65+", f"{_r('HET_IDADE_14_29',1)}% → {_r('HET_IDADE_65MAIS',1)}%", "—", "—"]],
        In(0.3), In(1.3), In(8.4), In(4.2), col_w=[In(3.2), In(1.8), In(1.7), In(1.7)], font_size=13)
    bullet_box(s, [
        f"Pretos: penalidade maior em todas as medidas — salário {_r('HET_HLM_PRETO',1)}% contra {_r('HET_HLM_PARDO',1)}% "
        f"dos pardos; no 9º decil da renda, a distância cresce ({_r('HET_QR_PRETO_Q90',1)}% × {_r('HET_QR_PARDO_Q90',1)}%)",
        "Setor público: a porta é tão desigual quanto no privado; o que muda é o teto",
        f"Idade: de {_r('HET_IDADE_14_29',1)}% a {_r('HET_IDADE_65MAIS',1)}% — carreira ou geração (o dado não separa)",
        f"Teto de vidro dentro de cada UF: OR {_r('HET_OR_T10UF')} (não decorre da geografia dos salários)",
    ], In(8.9), In(1.3), In(4.2), In(4.6), font_size=13)
    add_text(s, "\"Negro\" segue como a categoria da política: pretos e pardos estão abaixo dos brancos em todas as medidas.",
             In(0.3), In(6.5), In(12.7), In(0.45), font_size=13, bold=True, color=C_DARK,
             align=PP_ALIGN.CENTER)
    add_text(s, "OR < 1 = menor chance que um branco de mesmo perfil e bairro. Fonte: PNAD Contínua 2016–2025, população completa.",
             In(0.3), In(6.95), In(12.7), In(0.3), font_size=10, color=C_DARK, align=PP_ALIGN.CENTER)
    footer(s, 14)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 14 — SENSIBILIDADE A VARIÁVEIS OMITIDAS
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, "Quão forte teria de ser o que não medimos para derrubar o resultado",
           "Konfound (salário) e E-value (acesso, com RR ≈ √OR para desfecho comum)")

# Tabela no lugar da figura sensibilidade_konfound_evalues.png, que vem de
# run_konfound_evalues.py e ainda usa coeficientes de uma especificação antiga.
add_table_resumo(
    s,
    ["Modelo", "Konfound HLM (% de viés)", "E-value GLMM (acesso)"],
    [[m, f"{fmt(P[f'KF_{m}'],1)}%", f"{fmt(P[f'EV_ocp_qualif_{m}'],2)}×"]
     for m in ("M1", "M2", "M3", "M4")],
    In(0.4), In(1.35), In(6.6), In(3.0), col_w=[In(1.4), In(2.6), In(2.6)], font_size=13)
add_text(s, "Konfound: fração da estimativa que teria de ser viés para anulá-la (Frank et al., 2013). "
            "E-value: associação mínima que um confundidor omitido precisaria ter com a raça "
            "e com o desfecho para anular a OR (VanderWeele & Ding, 2017).",
         In(0.4), In(4.55), In(6.6), In(1.4), font_size=11, italic=True, color=C_GRAY)

add_text(s, "Resultados de robustez", In(7.5), In(1.2), In(5.6), In(0.4),
         font_size=15, bold=True, color=C_DARK)

rob_blocks = [
    (C_DARK,  "Konfound HLM (Frank et al., 2013)",
     f"{fmt(P['KF_M1'],1)}% (M1)  |  {fmt(P['KF_M3'],1)}% (M3)  |  {fmt(P['KF_M4'],1)}% (M4)",
     f"{fmt(P['KF_M3'],1)}% da estimativa do gap líquido teria de ser viés para anulá-la"),
    (C_RED,   "E-values GLMM lme4 (VanderWeele & Ding, 2017)",
     f"E ≥ {fmt(P['EVAL_M1'],2)}× (A1)  |  E ≥ {fmt(P['EVAL_M2'],2)}× (A2)  para anular OR = {or_str(P['OR_M1'])} / {or_str(P['OR_M2'])}",
     f"Confundidor precisaria de associação ≥ {fmt(P['EVAL_M2'],1)}× com raça E com o acesso"),
    (C_BLUE,  "No topo da renda (GLMM, top 10%)",
     f"E ≥ {fmt(P['EV_y_top10_M2'],2)}× para anular OR = {or_str(P['OR_TOP10_M2'])}",
     "A barreira mais estreita é também a mais difícil de explicar por omissão"),
]
for i, (color, titulo, resultado, interp) in enumerate(rob_blocks):
    add_rect(s, In(7.5), In(1.72)+i*In(1.25), In(5.6), In(1.15),
             fill_rgb=C_LGRAY, line_rgb=color, line_pt=1.2)
    add_text(s, titulo, In(7.65), In(1.76)+i*In(1.25), In(5.3), In(0.35),
             font_size=11.5, bold=True, color=color)
    add_text(s, resultado, In(7.65), In(2.12)+i*In(1.25), In(5.3), In(0.38),
             font_size=12.5, bold=True, color=C_BLACK)
    add_text(s, interp, In(7.65), In(2.5)+i*In(1.25), In(5.3), In(0.3),
             font_size=10.5, italic=True, color=C_GRAY)

footer(s, 14)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — ML/SHAP
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, "Sem impor forma funcional, a raça continua pesando na previsão da renda",
           f"XGBoost com R² de teste {fmt(P['ML_XGB_R2'], 3)} | profundidade escolhida por validação cruzada ({P['CV_DEPTH']})")

add_img(s, FIGURES / "shap_importance_xgb.png", In(0.3), In(1.2), In(6.8))

add_text(s, "Destaques com as novas variáveis", In(7.4), In(1.2), In(5.8), In(0.4),
         font_size=16, bold=True, color=C_DARK)

# ranking lido de shap_importance_comparada.csv: os quatro primeiros e a raça
_shap = pd.read_csv(TABLES / "shap_importance_comparada.csv").sort_values("Rank_XGB")
_notas = {
    "Renda média UPA (exceto o próprio)": "Wilson (1987): o contexto do bairro pesa tanto quanto o diploma",
    "Horas trabalhadas": "jornada — a variável de esforço declarado",
    "CBO: Profissionais": "grupo ocupacional, a porta que o GLMM mede",
    "Emprego formal (carteira)": "vínculo, também desfecho da discriminação",
}
ranking = []
for _, _r in _shap.head(4).iterrows():
    ranking.append((f"#{int(_r['Rank_XGB'])}", _r["Feature"],
                    fmt(_r["SHAP_mean_abs_XGB"], 3), _notas.get(_r["Feature"], "")))
_raca = _shap[_shap["Feature"].str.startswith("Raça")].iloc[0]
ranking.append((f"#{int(_raca['Rank_XGB'])}", "Raça (negro)",
                fmt(_raca["SHAP_mean_abs_XGB"], 3),
                f"sem a renda do bairro entre as features: {fmt(P['SHAP_RACA_SEM_UPA'], 3)}"))
for i, (rank, feat, shap, note) in enumerate(ranking):
    destaque = (i == len(ranking) - 1)   # a linha da raça
    color = C_RED if destaque else (C_BLUE if i == 0 else C_BLACK)
    add_rect(s, In(7.4), In(1.7)+i*In(0.88), In(5.8), In(0.82),
             fill_rgb=RGBColor(0xFF,0xEB,0xEE) if destaque else C_LGRAY,
             line_rgb=C_RED if destaque else C_GRAY, line_pt=0.5)
    add_text(s, rank, In(7.5), In(1.75)+i*In(0.88), In(0.5), In(0.4),
             font_size=12, bold=True, color=color)
    add_text(s, feat, In(8.05), In(1.75)+i*In(0.88), In(3.3), In(0.4),
             font_size=11.5, bold=(destaque or i == 0), color=color)
    add_text(s, f"|SHAP| = {shap}", In(11.4), In(1.75)+i*In(0.88), In(1.75), In(0.4),
             font_size=11, bold=True, color=color)
    add_text(s, note, In(8.05), In(2.1)+i*In(0.88), In(4.9), In(0.3),
             font_size=9.5, color=C_GRAY, italic=True)

footer(s, 16)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE — RESUMO DOS RESULTADOS (tabela real)
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, "Os quatro métodos apontam para o mesmo lugar",
           "Os quatro métodos convergem: há barreira no salário e no acesso às ocupações")
add_table_resumo(
    s,
    ["Dimensão", "Método", "Resultado-chave"],
    [["Gap e mediação", "HLM (UPA aleatória, UF fixa)",
      f"Gap {fmt(P['GAP_POOL'],1)}% (agregado) → {fmt(P['GAP_M4'],1)}% (M4); {fmt(P['MED_ACUM_M4'],1)}% mediado por bairro e ocupação"],
     ["Composição × discriminação", "Oaxaca-Blinder",
      f"{fmt(P['DOT_PCT'],1)}% dotações / {fmt(P['RET_PCT'],1)}% não explicado (sem ocupação); {fmt(P['RET_PCT_COM'],1)}% com ocupação"],
     ["Teto de vidro (acesso)", "GLMM logístico",
      f"OR {fmt(P['OR_OCP_M2'],3)} (cargo qualif.) → {fmt(P['OR_TOP10_M2'],3)} (top 10%); E-value {fmt(P['EVAL_M2'],1)}"],
     ["Distribuição da renda", "Quantílica / RIF",
      f"Gap {fmt(P['QR_GAP_Q10'],1)}% (q10) → {fmt(P['QR_GAP_Q90'],1)}% (q90); piso pegajoso: retornos "
      f"{fmt(P['RIF_RET_Q10'],0)}% → {fmt(P['RIF_RET_Q90'],0)}%"],
     ["Interseccionalidade", "Oaxaca 4 grupos + GLMM",
      f"Mulher Negra: gap {fmt(P['INT_MULHER_NEGRA_GAP'],1)}% ({'abaixo' if _INT_SUB else 'acima'} da soma dos eixos em log); "
      + (f"OR {fmt(P['CBO_MN_dirigente'],2)} entre dirigentes, {fmt(P['GRG_MN_TOP10'],2)} no top 10%"
       if "CBO_MN_dirigente" in P else
       f"OR {fmt(P['GRG_MN_OCP_QUALIF'],2)} no acesso, {fmt(P['GRG_MN_TOP10'],2)} no top 10%")],
     ["Robustez", "XGBoost + SHAP / E-value",
      f"R²={fmt(P['ML_XGB_R2'],2)}; raça é o {P['SHAP_RACA_RANK_XGB']}º de {P['SHAP_N_FEATURES']} preditores; "
      f"E-value {fmt(P['EVAL_M2'],1)}"]],
    In(0.4), In(1.35), In(12.5), In(4.9),
    col_w=[In(2.7), In(2.3), In(7.5)], font_size=12)
add_text(s, "Leitura: cada linha é um método independente respondendo uma pergunta distinta; "
            "OR < 1 indica menor acesso para negros de mesmo perfil.",
         In(0.4), In(6.5), In(12.5), In(0.5), font_size=11, italic=True, color=C_GRAY)
footer(s, 22)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 15 — SÍNTESE: TRIÂNGULO DE EVIDÊNCIAS
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, "Duas barreiras, um sistema: porta de entrada e salário",
           "Os métodos do núcleo apontam para o mesmo diagnóstico")

# Três vértices do triângulo
vertices = [
    (In(0.3),  In(1.3),  C_RED,   "DISCRIMINAÇÃO DE ACESSO",
     [f"GLMM: OR={or_str(P['OR_M2'])} para ocp. qualificada", f"AME={ame(P['AME_M2_pp'])} no A2 (mesmo bairro)", "Persiste após todos os controles observáveis"]),
    (In(6.9),  In(1.3),  C_BLUE,  "DISCRIMINAÇÃO DE REMUNERAÇÃO",
     [f"HLM M4: gap de {fmt(P['GAP_M4'],1)}% dentro da ocupação",
      f"Quantílica: de {fmt(P['QR_GAP_Q10'],1)}% no q10 a {fmt(P['QR_GAP_Q90'],1)}% no q90 (penalidade condicional)",
      f"SHAP: raça é o {P['SHAP_RACA_RANK_XGB']}º de {P['SHAP_N_FEATURES']} preditores no XGBoost"]),
    (In(3.6),  In(3.95), C_DARK,  "PENALIDADE INTERSECCIONAL",
     [f"Mulher Negra: gap de {fmt(P['INT_MULHER_NEGRA_GAP'],1)}%",
      ("Acumula raça e gênero, sem multiplicar (log)" if _INT_SUB
       else "Além da soma de raça e gênero (log)"),
      (f"Dirigentes: OR {fmt(P['CBO_MN_dirigente'],2)}; top 10%: OR {fmt(P['GRG_MN_TOP10'],2)}"
       if "CBO_MN_dirigente" in P else
       f"Acesso: OR {fmt(P['GRG_MN_OCP_QUALIF'],2)}; top 10%: OR {fmt(P['GRG_MN_TOP10'],2)}")]),
]
for l, t, color, title, items in vertices:
    add_rect(s, l, t, In(5.8), In(2.3),            # 3.95 + 2.3 < 6.4 (faixa final)
             fill_rgb=RGBColor(0xF5,0xF5,0xF5), line_rgb=color, line_pt=1.5)
    add_rect(s, l, t, In(5.8), In(0.5), fill_rgb=color)
    add_text(s, title, l+In(0.1), t+In(0.05), In(5.6), In(0.45),
             font_size=13, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    for i, item in enumerate(items):
        add_text(s, "• " + item, l+In(0.2), t+In(0.62)+i*In(0.52), In(5.4), In(0.5),
                 font_size=12, color=C_BLACK)

add_rect(s, In(0.3), In(6.4), In(12.7), In(0.5),
         fill_rgb=RGBColor(0x1F,0x38,0x64), line_rgb=C_AMBER, line_pt=0)
add_text(s, f"Oaxaca: {fmt(P['DOT_PCT'],1)}% do gap é composição e {fmt(P['RET_PCT'],1)}% retornos | GLMM mostra a barreira de acesso (OR={fmt(P['OR_OCP_M2'],3)}) | RIF: discriminação de preço maior na base (piso pegajoso)",
         In(0.5), In(6.45), In(12.3), In(0.45),
         font_size=12, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
footer(s, 22)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 13 — IMPLICAÇÕES DE POLÍTICA
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
# 04/10/2026: críticas à política de diversidade vigente (C1–C4) e propostas (P1–P5),
# as mesmas da Discussão do TCC; cada crítica só entra se o número a sustentar
header_bar(s, "As políticas de diversidade cuidam da entrada, não da subida",
           "O que os resultados dizem sobre os instrumentos vigentes")
_crit = []
if P["OR_y_top10_M2"] < P["OR_ocp_qualif_M2"]:
    _crit.append((C_RED, "Ingresso, não ascensão",
                  "Cotas no ensino (Lei 12.711/2012, atualizada em 2023) e nos concursos "
                  "(Lei 15.142/2025) atuam na entrada. A barreira cresce no topo: chances "
                  f"{fmt((1 - P['OR_y_top10_M2']) * 100, 0)}% menores no décimo mais rico. "
                  "A reserva de cargos de confiança (Decreto 11.443/2023) vale só no governo federal."))
if _PN.get("NE_GAP_POS") is not None and _PN["NE_GAP_POS"] < 3 and _PN.get("PCTPOS_ocp_qualif", 0) >= 10:
    _crit.append((C_BLUE, "Educação iguala o salário, não a porta",
                  f"A penalidade cai a {fmt(_PN['NE_GAP_POS'],1)}% na pós-graduação, mas as "
                  f"chances de acesso seguem {fmt(_PN['PCTPOS_ocp_qualif'],0)}% menores. "
                  "Prouni, Fies e cotas no ensino atacam a barreira que mais cede ao diploma."))
if P["MED_BAIRRO"] > 0:
    _crit.append((C_GREEN, "Sem território",
                  f"{fmt(P['MED_BAIRRO'],1)}% do gap passa pelo bairro de moradia, e nenhum "
                  "instrumento federal de diversidade usa o local de moradia como critério."))
if "CBO_MN_dirigente" in P:
    _crit.append((RGBColor(0x6A, 0x00, 0x8A), "Um eixo de cada vez",
                  "Metas separadas por raça e por gênero podem ser cumpridas sem alcançar a "
                  f"mulher negra: entre dirigentes, OR {fmt(P['CBO_MN_dirigente'],2)}. A lei de "
                  "transparência salarial (14.611/2023) coleta raça, mas exige igualdade só "
                  "entre mulheres e homens."))
_w = In(12.7) / max(len(_crit), 1)
for i, (cor, tit, txt) in enumerate(_crit):
    x = In(0.3) + i * _w
    add_rect(s, x + In(0.05), In(1.25), _w - In(0.1), In(5.3),
             fill_rgb=C_LGRAY, line_rgb=cor, line_pt=1.5)
    add_rect(s, x + In(0.05), In(1.25), _w - In(0.1), In(0.55), fill_rgb=cor)
    add_text(s, tit, x + In(0.15), In(1.3), _w - In(0.3), In(0.5),
             font_size=13, bold=True, color=C_WHITE)
    add_text(s, txt, x + In(0.2), In(1.95), _w - In(0.4), In(4.4), font_size=13, color=C_BLACK)
add_text(s, "Associações condicionais, não efeitos causais: os números mostram onde a política "
            "não chega, não o efeito de uma política.",
         In(0.3), In(6.75), In(12.7), In(0.45), font_size=12, color=C_GRAY2, align=PP_ALIGN.CENTER)
footer(s, 28)

s = prs.slides.add_slide(BLANK)
header_bar(s, "Cinco propostas para reduzir o racismo estrutural no mercado de trabalho",
           "Sugeridas pelos resultados, não avaliadas por eles")
_prop = [
    (C_RED, "Metas de comando",
     "Representação em cargos de direção e gerência no setor privado, com recorte "
     "interseccional, no relatório que a Lei 14.611 já exige."),  # sem-fossil: número de lei, não resultado
    (C_BLUE, "Igualdade salarial por raça",
     "Obrigação, não só dado, com fiscalização dirigida à diferença dentro da mesma "
     f"ocupação ({fmt(P['GAP_M4'],1)}%)."),
    (C_GREEN, "Território",
     "Intermediação de emprego, transporte e qualificação priorizados nos bairros de maior "
     "proporção de população negra."),
    (C_AMBER, "Promoção, não só ingresso",
     "Estender a reserva de cargos de confiança a estatais e à progressão nas carreiras."),
    (C_DARK, "Monitoramento anual",
     "Gap líquido, chance de acesso e chance de comando por raça e gênero, reproduzíveis "
     "com a PNAD Contínua."),
]
for i, (cor, tit, txt) in enumerate(_prop):
    y = In(1.3) + i * In(1.05)
    add_rect(s, In(0.3), y, In(0.12), In(0.85), fill_rgb=cor)
    add_text(s, f"{i + 1}. {tit}", In(0.6), y, In(3.6), In(0.85), font_size=16, bold=True, color=cor)
    add_text(s, txt, In(4.3), y + In(0.05), In(8.7), In(0.85), font_size=14, color=C_BLACK)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 14 — LIMITAÇÕES E AGENDA FUTURA
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
header_bar(s, "O que estes números não dizem",
           "Honestidade acadêmica: o que este trabalho não faz e por quê")

add_text(s, "Limitações", In(0.4), In(1.25), In(6.0), In(0.4),
         font_size=16, bold=True, color=C_RED)
bullet_box(s, [
    "PNAD não permite experimentos causais — coeficientes são associações condicionais, não efeitos causais no sentido de Rubin/Pearl",
    "UPA como proxy de bairro: unidade de amostragem ≠ bairro administrativo",
    f"GLMM logístico estimado na PEA completa via lme4::glmer (nAGQ=0, bobyqa, n={fmtN(P['N_GLMM'])}, "
    f"{fmtN(P['N_UPAS'])} UPAs), com efeito aleatório de UPA",
    "Médias de bairro calculadas sem a própria pessoa (leave-one-out), mas choques comuns "
    "ao bairro ainda impedem leitura causal do contexto",
    "CBO auto-declarado pode ter viés de classificação por raça (rebaixamento da ocupação declarada)",
], In(0.4), In(1.75), In(6.2), In(3.8), font_size=13, dot_color=C_RED)

add_text(s, "Agenda Futura", In(7.0), In(1.25), In(6.0), In(0.4),
         font_size=16, bold=True, color=C_BLUE)
bullet_box(s, [
    "Análise de variáveis instrumentais (IV) para identificação causal — distância à escola técnica como instrumento",
    "RAIS linkada à PNAD para rastrear trajetórias de mobilidade intraempresa",
    "Análise de mediação formal (path analysis) raça → ocupação → renda",
    "Extensão ao setor público por UF — heterogeneidade do teto de vidro entre estados",
    "Modelo longitudinal com painéis rotativos da PNAD (2T seguidos) para efeitos fixos de indivíduo",
], In(7.0), In(1.75), In(6.2), In(3.8), font_size=13, dot_color=C_BLUE)

footer(s, 29)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 18 — CONCLUSÃO
# ══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
add_rect(s, 0, 0, W, H, fill_rgb=C_DARK)
add_rect(s, 0, 0, W, In(0.8), fill_rgb=RGBColor(0x0D,0x1F,0x3C))
add_text(s, "Conclusão", In(0.4), In(0.1), In(12), In(0.65),
         font_size=26, bold=True, color=C_WHITE, font_name="Calibri")

numeros = [
    (f"{fmt(P['GAP_POOL'],1)}%", "Gap racial agregado\n(sem efeito de bairro)"),
    (f"{fmt(P['GAP_M4'],1)}%", "Persiste dentro da\nmesma ocupação (M4)"),
    (f"OR={or_str(P['OR_M2'])}", "Acesso qualificado\n(GLMM A2, lme4)"),
    (f"{fmt(P['ICC_UPA_pct'],0)}%", "da variação da renda\nestá entre bairros"),
]
for i, (val, lbl) in enumerate(numeros):
    x = In(0.4) + i * In(3.2)
    add_rect(s, x, In(0.95), In(3.0), In(1.5),
             fill_rgb=RGBColor(0x1A,0x30,0x5C), line_rgb=C_AMBER, line_pt=1)
    add_text(s, val, x+In(0.1), In(1.0), In(2.8), In(0.75),
             font_size=30, bold=True, color=C_AMBER, align=PP_ALIGN.CENTER)
    add_text(s, lbl, x+In(0.1), In(1.75), In(2.8), In(0.6),
             font_size=11, color=C_WHITE, align=PP_ALIGN.CENTER)

# a afirmação sobre convergência segue a inclinação estimada (mesma lógica de
# frase_conclusao_convergencia no texto): nada de "resistente" se o gap recua com p < 0,05
if P["TEND_P"] >= 0.05:
    _conv = "estrutural, multicausal e sem convergência distinguível de zero na última década"
elif P["TEND_DELTA"] > 0 and "COV_D2020" in _PN:
    _conv = "estrutural e multicausal: o gap recuou num degrau em 2020, sem ritmo para fechar sozinho"
elif P["TEND_DELTA"] > 0:
    _conv = "estrutural e multicausal: o gap recua, mas devagar demais para fechar sozinho"
else:
    _conv = "estrutural, multicausal e crescente na última década"
conclusoes = [
    f"A desigualdade racial no mercado de trabalho brasileiro é {_conv}.",
    (f"Duas barreiras que respondem de modo diferente à escolaridade: a penalidade salarial cai de "
     f"{fmt(_PN['NE_GAP_SEMFUND'],1)}% (sem fundamental) a {fmt(_PN['NE_GAP_POS'],1)}% (pós-graduação), "
     f"mas, com pós, as chances de chegar a cargo qualificado seguem {fmt(_PN['PCTPOS_ocp_qualif'],0)}% menores."
     if frase_diploma(_PN).startswith("O diploma quase iguala") else
     f"Duas barreiras: no ACESSO a ocupações qualificadas (GLMM: OR={or_str(P['OR_M2'])}, "
     f"AME={ame(P['AME_M2_pp'])}) e na REMUNERAÇÃO dentro das mesmas funções (HLM M4: {fmt(P['GAP_M4'],1)}%)."),
    f"O teto de vidro é real e cresce no topo da distribuição: a penalidade condicional vai de "
    f"{fmt(P['QR_GAP_Q10'],1)}% no q10 a {fmt(P['QR_GAP_Q90'],1)}% no q90 (Z={fmt(P['QR_Z'],1)}).",
    f"Política que atua só no salário deixa de fora a barreira de acesso: a chance de chegar a cargo "
    f"qualificado é {fmt(P['OR_M2_menor_pct'],0)}% menor e, no topo da renda, "
    f"{fmt((1-P['OR_TOP10_M2'])*100,0)}% menor.",
]
for i, texto in enumerate(conclusoes):
    add_rect(s, In(0.3), In(2.6)+i*In(0.9), In(12.7), In(0.82),
             fill_rgb=RGBColor(0x0F,0x27,0x4A), line_rgb=C_AMBER if i==0 else C_BLUE, line_pt=0.6)
    add_text(s, f"{i+1}. " + texto, In(0.5), In(2.65)+i*In(0.95), In(12.3), In(0.75),
             font_size=13, color=C_WHITE, font_name="Calibri")

add_rect(s, 0, H-In(0.5), W, In(0.5), fill_rgb=RGBColor(0x0D,0x1F,0x3C))
add_rect(s, In(0.3), In(6.2), In(12.7), In(0.78), fill_rgb=RGBColor(0x0D,0x1F,0x3C),
         line_rgb=C_AMBER, line_pt=1)
add_text(s, frase_sintese(_PN),
         In(0.5), In(6.25), In(12.3), In(0.7),
         font_size=13.5, bold=True, color=C_AMBER, align=PP_ALIGN.CENTER)

add_text(s, "Ricardo Calheiros  |  MBA Data Science & Analytics  |  USP/ESALQ  |  rickinrj@gmail.com",
         In(0.3), H-In(0.45), In(12.7), In(0.4),
         font_size=11, color=RGBColor(0x90,0xA4,0xAE), align=PP_ALIGN.CENTER)
_NUMEROS.append((s, add_text(s, "", In(12.4), H-In(0.4), In(0.8), In(0.3), font_size=9,
                             color=RGBColor(0x90,0xA4,0xAE), align=PP_ALIGN.RIGHT,
                             font_name="Calibri")))

# ── Numeração real dos slides ─────────────────────────────────────────────────
_ordem = {id(sl): i for i, sl in enumerate(prs.slides, start=1)}
for _sl, _tb in _NUMEROS:
    _tb.text_frame.paragraphs[0].runs[0].text = f"{_ordem[id(_sl)]}/{len(prs.slides)}"

# ── Salvar ────────────────────────────────────────────────────────────────────
prs.save(str(OUT_PPT))
print(f"Arquivo gerado: {OUT_PPT.name}")
print(f"Tamanho: {OUT_PPT.stat().st_size // 1024} KB")
print("Abra com PowerPoint para revisar e ajustar o layout.")
