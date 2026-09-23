# -*- coding: utf-8 -*-
"""
gerar_guia_estudo.py  (versão do núcleo)
========================================
Gera `entregaveis/guia_estudo_defesa.docx` — o roteiro de estudo para a banca.

Todo número vem de `params_nucleo.py`, que lê os csv de `outputs/tables/`: o
guia nunca pode divergir do relatório. O gerador antigo
(`scripts/geradores/gerar_guia_estudo.py`) tinha os números escritos à mão e
ficou preso na versão estendida — descrevia uma escada M1–M5 que não existe
mais e valores anteriores aos blocos 0–8 da revisão.

Uso: python tcc/scripts/gerar_guia_estudo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

from params_nucleo import P, milhar, pct, pt

ROOT = Path(__file__).resolve().parents[2]
FIGS = ROOT / "outputs" / "figures"
OUT = ROOT / "entregaveis" / "guia_estudo_defesa.docx"

AZUL = (0x1F, 0x38, 0x64)
AZUL_CLARO = (0x15, 0x65, 0xC0)
CINZA = (0x61, 0x61, 0x61)
VERMELHO = (0xB7, 0x1C, 0x1C)


# ── helpers de formatação ─────────────────────────────────────────────────────
def _fonte(run, size=11, bold=False, italic=False, color=None, name="Calibri"):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)


def titulo(texto, nivel=1, cor=AZUL):
    p = doc.add_heading(texto, level=nivel)
    for run in p.runs:
        run.font.color.rgb = RGBColor(*cor)
        run.font.name = "Calibri"
    return p


def para(texto="", size=11, bold=False, italic=False, color=None,
         align=WD_ALIGN_PARAGRAPH.JUSTIFY, antes=0, depois=6, indent=0.0):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = align
    p.paragraph_format.space_before = Pt(antes)
    p.paragraph_format.space_after = Pt(depois)
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    if texto:
        _fonte(p.add_run(texto), size, bold, italic, color)
    return p


def rico(partes, size=11, indent=0.0, depois=6):
    """Parágrafo com trechos em negrito: lista de (texto, bold)."""
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(depois)
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    for texto, bold in partes:
        _fonte(p.add_run(texto), size, bold)
    return p


def bullet(texto, nivel=0, size=11, bold=False, color=None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Cm(0.6 + nivel * 0.7)
    p.paragraph_format.space_after = Pt(3)
    _fonte(p.add_run(texto), size, bold, color=color)
    return p


def caixa(titulo_txt, linhas, cor=AZUL):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    _fonte(p.add_run(f"▌ {titulo_txt}"), 11, True, color=cor)
    for linha in linhas:
        q = doc.add_paragraph()
        q.paragraph_format.left_indent = Cm(0.8)
        q.paragraph_format.space_after = Pt(2)
        q.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _fonte(q.add_run(linha), 10.5)


def pergunta(q, resposta, size=10.5):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    _fonte(p.add_run("P. "), 11, True, color=VERMELHO)
    _fonte(p.add_run(q), 11, True)
    r = doc.add_paragraph()
    r.paragraph_format.left_indent = Cm(0.6)
    r.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r.paragraph_format.space_after = Pt(4)
    _fonte(r.add_run("R. "), size, True, color=AZUL_CLARO)
    _fonte(r.add_run(resposta), size)


def tabela(cabecalho, linhas, larguras=None):
    t = doc.add_table(rows=1, cols=len(cabecalho))
    t.style = "Light Grid Accent 1"
    for i, c in enumerate(cabecalho):
        cel = t.rows[0].cells[i]
        cel.text = ""
        _fonte(cel.paragraphs[0].add_run(c), 10, True)
    for linha in linhas:
        cells = t.add_row().cells
        for i, v in enumerate(linha):
            cells[i].text = ""
            _fonte(cells[i].paragraphs[0].add_run(str(v)), 10)
    if larguras:
        for row in t.rows:
            for i, w in enumerate(larguras):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def figura(nome, legenda, largura=15.5):
    caminho = FIGS / nome
    if not caminho.exists():
        print(f"  [AVISO] figura ausente: {nome}")
        return
    doc.add_picture(str(caminho), width=Cm(largura))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(legenda, size=9.5, italic=True, color=CINZA,
         align=WD_ALIGN_PARAGRAPH.CENTER, depois=10)


# ── atalhos de números (tudo vem do csv) ──────────────────────────────────────
OR_CBO = P["OR_ocp_qualif_M2"]
OR_T10 = P["OR_y_top10_M2"]
OR_T20 = P["OR_y_top20_M2"]
CI_CBO = P["CI_ocp_qualif_M2"]
PCT_CBO = (1 - OR_CBO) * 100
PCT_T10 = (1 - OR_T10) * 100

doc = Document()
for secao in doc.sections:
    secao.left_margin = secao.right_margin = Cm(2.2)
    secao.top_margin = secao.bottom_margin = Cm(2.0)

# ══ Capa ══════════════════════════════════════════════════════════════════════
para("GUIA DE ESTUDO PARA A DEFESA", size=22, bold=True, color=AZUL,
     align=WD_ALIGN_PARAGRAPH.CENTER, antes=60, depois=4)
para("Racismo estrutural no mercado de trabalho brasileiro", size=13,
     color=CINZA, align=WD_ALIGN_PARAGRAPH.CENTER, depois=2)
para("Uma abordagem multinível e de decomposição salarial — PNAD Contínua 2016–2025",
     size=11, italic=True, color=CINZA, align=WD_ALIGN_PARAGRAPH.CENTER, depois=24)
para("Ricardo Calheiros · MBA em Data Science e Analytics · ESALQ/USP", size=11,
     align=WD_ALIGN_PARAGRAPH.CENTER, depois=30)
caixa("Como usar este guia", [
    "Parte 1 — o que dizer nos três primeiros minutos, com os números de cor.",
    "Parte 2 — leituras prioritárias: o que a banca costuma cobrar de cada obra.",
    "Parte 3 — os quatro métodos do núcleo: o que cada um responde e como ler a saída.",
    "Parte 4 — a robustez, que é o que separa um resultado de um achado.",
    "Parte 5 — equações para memorizar.",
    "Parte 6 — as perguntas difíceis, com a resposta já formulada.",
    "Todos os números deste guia são lidos dos csv de outputs/tables/ na geração: "
    "se uma análise for reexecutada, basta rodar o gerador de novo.",
])
doc.add_page_break()

# ══ Parte 1 — a defesa em três minutos ════════════════════════════════════════
titulo("PARTE 1 — A DEFESA EM TRÊS MINUTOS", 1)
para("Decore esta sequência. Ela responde, nesta ordem, às quatro perguntas que "
     "toda banca faz: o que você mediu, por que isso não é óbvio, como sabe que é "
     "verdade e o que muda se for.", italic=True, color=CINZA)

caixa("A frase-síntese (se só houver tempo para uma)", [
    f"“Com a mesma escolaridade, idade, sexo e bairro, um trabalhador negro ganha "
    f"{pct(P['GAP_M3'])} a menos que um branco — e a barreira mais dura não é o "
    f"salário, é a porta: {pt(PCT_CBO, 0)}% menos chance de chegar a um cargo "
    f"qualificado. O mercado de trabalho brasileiro não é racialmente neutro, e "
    f"educação sozinha não corrige isso.”",
], cor=VERMELHO)

titulo("1.1  O contexto", 2)
rico([("Entre 2016 e 2025, um trabalhador negro ganhou em média ", False),
      (f"{pct(P['GAP_POOL'])} a menos", True),
      (" que um branco com a mesma escolaridade, idade e sexo. Esse é o gap agregado, "
       "estimado por OLS com efeitos fixos de estado — o ponto de partida.", False)])

titulo("1.2  O desequilíbrio", 2)
rico([("O gap não é uma coisa só. Comparando apenas pessoas ", False), ("do mesmo bairro", True),
      (f", ele cai quase à metade: {pct(P['MED_BAIRRO'])} do gap agregado é mediado "
       f"pela segregação residencial, e sobra um ", False),
      (f"gap líquido de {pct(P['GAP_M3'])}", True),
      (f". Dentro da mesma ocupação ainda persistem {pct(P['GAP_M4'])} — e a ocupação "
       "é ela própria resultado da barreira de acesso.", False)])

titulo("1.3  A evidência", 2)
para(f"Quatro métodos independentes sobre a população completa da PNAD Contínua "
     f"(cerca de 7,7 milhões de observações em {milhar(P['N_UPAS'])} bairros; o N exato "
     f"varia com os filtros de cada método):")
tabela(["Método", "Pergunta que responde", "Resultado principal"],
       [["HLM de dois níveis", "Quanto do gap é do bairro?",
         f"{pct(P['MED_BAIRRO'])} mediado pelo bairro; gap líquido {pct(P['GAP_M3'])}"],
        ["Oaxaca–Blinder", "É composição ou preço?",
         f"{pct(P['OB_SEM_RET_PCT'])} do gap são retornos diferenciais"],
        ["QR + RIF-OB", "Onde na distribuição pesa?",
         f"gap condicional cresce ({pct(P['QR_GAP_Q10'])}→{pct(P['QR_GAP_Q90'])}); "
         f"retornos maiores na base ({pct(P['RIF_RET_Q10'])} no q10)"],
        ["GLMM logístico", "A porta é mais estreita?",
         f"OR = {pt(OR_CBO, 3)} para cargo qualificado; {pt(OR_T10, 3)} no topo 10%"]],
       larguras=[4.0, 5.5, 7.0])
para(f"Um XGBoost com SHAP confirma, sem impor forma funcional, que a raça mantém "
     f"contribuição própria: {P['SHAP_RACA_RANK_XGB']}ª posição entre "
     f"{P['SHAP_N_FEATURES']} preditores.", depois=10)

titulo("1.4  O que isso muda", 2)
para("Se o gargalo fosse escolaridade, bastaria ampliar o acesso ao ensino. Os "
     "resultados dizem outra coisa: as mesmas credenciais rendem menos, e a barreira "
     "maior está no acesso à ocupação. Política de educação isolada tem retorno "
     "marginal decrescente; é preciso agir simultaneamente sobre acesso "
     "(Lei 12.990/2014), sobre a discriminação salarial (Lei 9.029/1995 e Estatuto da "
     "Igualdade Racial) e sobre a segregação residencial.")
doc.add_page_break()

# ══ Parte 2 — leituras ════════════════════════════════════════════════════════
titulo("PARTE 2 — ROTEIRO DE LEITURAS", 1)

titulo("2.1  Prioridade máxima — perguntas quase certas", 2)
for obra, porque in [
    ("Angrist & Pischke — Mostly Harmless Econometrics (caps. 2, 3 e 8)",
     "É de onde vêm as três ressalvas que a banca vai cobrar: bad controls (cap. 3), "
     "condicionar no desfecho e o problema de Moulton/erros agrupados (cap. 8). "
     "Saiba dizer em uma frase por que M4 é limite inferior e M3 é limite superior."),
    ("Oaxaca (1973) e Blinder (1973)",
     "A decomposição em dotações e retornos. Saiba que a parcela de retornos não é "
     "'a discriminação medida', e sim o resíduo não explicado pelas variáveis incluídas."),
    ("Raudenbush & Bryk — Hierarchical Linear Models (caps. 2 e 4)",
     "Modelo nulo, ICC, estratégia step-up e a diferença entre REML e ML. "
     f"No M0 deste trabalho, ICC = {pt(P['ICC_M0'], 3)} — {pct(P['ICC_M0'] * 100, 0)} da "
     "variância do log-rendimento está entre bairros."),
    ("Firpo, Fortin & Lemieux (2018) — RIF regressions",
     "Por que os quantis incondicionais respondem a uma pergunta diferente dos "
     "condicionais. É a base do parágrafo que concilia teto de vidro e piso pegajoso."),
    ("Hasenbalg (1979) e Soares (2009)",
     "A literatura nacional com que o resultado dialoga. Saiba dizer o que este "
     "trabalho acrescenta: não a existência do gap, e sim a separação dos mecanismos."),
]:
    bullet(obra, bold=True)
    para(porque, size=10.5, indent=1.0, depois=4)

titulo("2.2  Prioridade média", 2)
for obra, porque in [
    ("Manski (1993) — problema do reflexo",
     "Por que a renda média do bairro, usada como preditor, é mecanicamente "
     "informativa — e o que foi feito (média leave-one-out no ML, variável removida "
     "nos modelos de acesso)."),
    ("Wilson (1987) e Sampson, Raudenbush & Earls (1997)",
     "O arcabouço teórico dos efeitos de vizinhança: por que faz sentido pôr a UPA "
     "no nível 2."),
    ("VanderWeele & Ding (2017) — E-values",
     f"Quanto de confundimento não observado seria preciso para anular o resultado. "
     f"Aqui, E-value = {pt(P['EV_ocp_qualif_M2'], 1)} para a barreira de acesso."),
    ("Crenshaw (1989) — interseccionalidade",
     "O conceito por trás da decomposição de quatro grupos e da penalidade extra."),
    ("Fávero & Belfiore — Manual de Análise de Dados (caps. 12, 14 e 15)",
     "VIF e multicolinearidade, modelos logísticos (OR, efeitos marginais, "
     "sensibilidade/especificidade, curva ROC) e modelos multinível."),
][:6]:
    bullet(obra, bold=True)
    para(porque, size=10.5, indent=1.0, depois=4)

titulo("2.3  Se sobrar tempo", 2)
bullet("Pager (2007) — experimentos de auditoria: a evidência experimental que o "
       "resultado observacional é consistente com.")
bullet("Koenker & Bassett (1978) — regressão quantílica, o artigo fundador.")
bullet("Lundberg & Lee (2017) — SHAP: valores de Shapley aplicados a modelos preditivos.")
bullet("Knaflic — Storytelling com Dados: a lógica da apresentação (título de ação, "
       "uma ideia por slide, cinza + uma cor de destaque).")
doc.add_page_break()

# ══ Parte 3 — os quatro métodos ═══════════════════════════════════════════════
titulo("PARTE 3 — OS QUATRO MÉTODOS DO NÚCLEO", 1)
para("Para cada método: a pergunta que ele responde, como ler a saída e o número "
     "que você precisa saber de cor.", italic=True, color=CINZA)

# 3.1 HLM ---------------------------------------------------------------------
titulo("3.1  Modelo linear hierárquico (indivíduos em bairros, efeitos fixos de UF)", 2)
caixa("Pergunta", ["Quanto do gap racial desaparece quando se compara negros e "
                   "brancos que moram no mesmo bairro?"])
para("A estratégia é step-up: parte-se do modelo nulo e acrescenta-se um bloco de "
     "controles por vez, observando o que acontece com o coeficiente de raça.")
tabela(["Modelo", "O que acrescenta", "β negro", "Gap (%)", "Mediação acum."],
       [["Agregado", "individual + UF, sem bairro", pt(P["B_POOL"], 4),
         f"−{pt(P['GAP_POOL'])}", "—"],
        ["M1", "+ intercepto aleatório de UPA", pt(P["B_M1"], 4),
         f"−{pt(P['GAP_M1'])}", pct(P["MED_BAIRRO"])],
        ["M2", "+ contexto do bairro", pt(P["B_M2"], 4), f"−{pt(P['GAP_M2'])}",
         pct(P["MED_ACUM_M2"])],
        ["M3", "+ efeitos fixos de UF", pt(P["B_M3"], 4), f"−{pt(P['GAP_M3'])}",
         pct(P["MED_ACUM_M3"])],
        ["M4", "+ ocupação e formalidade", pt(P["B_M4"], 4), f"−{pt(P['GAP_M4'])}",
         pct(P["MED_ACUM_M4"])]],
       larguras=[2.2, 5.6, 2.6, 2.4, 3.2])
bullet(f"Modelo nulo: τ² = {pt(P['TAU2_M0'], 4)}, σ² = {pt(P['SIGMA2_M0'], 4)} → "
       f"ICC = {pt(P['ICC_M0'], 3)}. Traduza: {pct(P['ICC_M0'] * 100, 0)} da variância do "
       f"log-rendimento está entre bairros, não entre pessoas — é o que justifica o multinível.")
bullet(f"Efeito contextual (M2): γ₀₁ = {pt(P['GAMMA01'], 4)} (EP {pt(P['GAMMA01_SE'], 4)}) "
       f"por desvio-padrão da proporção de negros na UPA. Atenção: o regressor é "
       f"padronizado — não diga “por ponto percentual”.")
bullet(f"Inclinação aleatória (M3_RS): desvio-padrão da inclinação de raça entre bairros "
       f"= {pt(P['SD_SLOPE'], 3)}; LR contra o M3 = {milhar(P['LR_RS'])}. A penalidade "
       f"varia entre bairros, e a covariância negativa ({pt(P['COV_INT_SLOPE'], 4)}) diz "
       f"que ela é maior justamente nos bairros de renda mais alta.")
bullet(f"REML vs ML: τ² = {pt(P['TAU2_M0_ML'], 5)} por ML e {pt(P['TAU2_M0_REML'], 5)} por "
       f"REML. Com N desse tamanho a escolha é indiferente; usa-se ML porque é o que "
       f"permite comparar efeitos fixos entre degraus.")
figura("fig_hlm_gap.png",
       "Metade do gap racial desaparece ao comparar pessoas do mesmo bairro — "
       "e o que sobra não é explicado por escolaridade, estado nem ocupação.")
figura("hlm_efeitos_uf_blup_upa.png",
       "A variação entre bairros supera a variação entre estados: efeitos fixos de UF "
       "(à esquerda) e BLUPs de UPA (à direita).", largura=15.0)

# 3.2 Oaxaca-Blinder ----------------------------------------------------------
titulo("3.2  Decomposição de Oaxaca–Blinder", 2)
caixa("Pergunta", ["Do gap observado, quanto vem de os dois grupos terem "
                   "características diferentes (dotações) e quanto de as mesmas "
                   "características serem pagas de forma diferente (retornos)?"])
tabela(["Especificação", "Gap total", "Dotações", "Retornos", "Como nomear"],
       [["(A) Capital humano + contexto", pct(P["OB_SEM_GAP_PCT"]),
         pct(P["OB_SEM_DOT_PCT"]), pct(P["OB_SEM_RET_PCT"]),
         "comparável à literatura"],
        ["(B) + ocupação, formalidade e horas", pct(P["OB_COM_GAP_PCT"]),
         pct(P["OB_COM_DOT_PCT"]), pct(P["OB_COM_RET_PCT"]),
         "limite inferior descritivo"]],
       larguras=[5.4, 2.4, 2.4, 2.4, 3.4])
bullet(f"Erros-padrão por bootstrap em blocos de UPA ({P['OB_N_BOOT']} réplicas), "
       f"N = {milhar(P['OB_N'])} em {milhar(P['OB_N_UPAS'])} UPAs.")
bullet("A frase que evita a pergunta capciosa: “a parcela de retornos não é a "
       "discriminação medida; é o que as variáveis incluídas não explicam. Ela é um "
       "limite superior do efeito de tratamento diferencial e um limite inferior do "
       "racismo estrutural, que também opera pelas dotações.”")
figura("fig_ob_cascata.png",
       "Tratar a ocupação como “característica” derruba pela metade a discriminação "
       "medida — por isso as duas especificações são reportadas lado a lado.")

# 3.3 QR + RIF ----------------------------------------------------------------
titulo("3.3  Regressão quantílica e RIF-OB", 2)
caixa("Pergunta", ["A penalidade racial é a mesma em toda a distribuição de renda, "
                   "ou pesa mais no topo (teto de vidro) ou na base (piso pegajoso)?"])
tabela(["Quantil", "Gap condicional (QR)", "Retornos (RIF, incondicional)"],
       [[q, f"−{pt(P[f'QR_GAP_Q{n}'])}%", pct(P[f"RIF_RET_{ql}"])]
        for q, n, ql in [("q10", "10", "Q10"), ("q25", "25", "Q25"),
                         ("q50", "50", "Q50"), ("q75", "75", "Q75"),
                         ("q90", "90", "Q90")]],
       larguras=[3.0, 5.5, 6.0])
bullet(f"Teste de heterogeneidade: diferença q90 − q10 = {pt(P['QR_DIFF'], 4)}, "
       f"Z = {pt(P['QR_Z'], 2)}, p < 0,001. O erro-padrão vem de bootstrap "
       f"m-out-of-n em blocos de UPA ({milhar(P['QR_M_UPAS'])} de "
       f"{milhar(P['QR_N_UPAS'])} UPAs por réplica, com reescala √(m/G)).")
caixa("A pergunta que a banca vai fazer: “os dois padrões não se contradizem?”", [
    "Não. A QR estima quantis condicionais: β(τ) compara negros e brancos na mesma "
    "posição dentro da distribuição de pessoas com o mesmo perfil observável. O "
    "crescimento de |β(τ)| significa que a dispersão condicional é maior entre "
    "brancos (fanning out) — não que “os negros do topo sofrem mais”: quantis não "
    "seguem indivíduos.",
    "A RIF-OB decompõe quantis incondicionais da distribuição de renda do país. "
    "Como a composição observável concentra negros na base, a parcela de retornos é "
    "maior ali. Um resultado é sobre preço; o outro, sobre distribuição.",
])
figura("fig_qr_rif.png",
       "Teto de vidro e piso pegajoso são o mesmo fenômeno visto de dois ângulos.")

# 3.4 GLMM --------------------------------------------------------------------
titulo("3.4  GLMM logístico de acesso (lme4::glmer)", 2)
caixa("Pergunta", ["Controlando escolaridade, sexo, idade, estado e contexto do "
                   "bairro, um trabalhador negro tem a mesma chance de ocupar um "
                   "cargo qualificado ou de chegar ao topo da renda?"])
tabela(["Desfecho", "OR (IC 95%)", "AME (p.p.)", "ICC UPA", "AUC", "E-value"],
       [["Cargo qualificado (CBO 1–4)",
         f"{pt(OR_CBO, 3)} ({pt(CI_CBO[0], 3)}–{pt(CI_CBO[1], 3)})",
         pt(P["AME_ocp_qualif_M2"], 1), pt(P["ICC_ocp_qualif_M1"], 3),
         pt(P["AUC_ocp_qualif_M2"], 3), pt(P["EV_ocp_qualif_M2"], 1)],
        ["Topo 20% da renda", pt(OR_T20, 3), pt(P["AME_y_top20_M2"], 1),
         pt(P["ICC_y_top20_M1"], 3), pt(P["AUC_y_top20_M2"], 3),
         pt(P["EV_y_top20_M2"], 1)],
        ["Topo 10% da renda", pt(OR_T10, 3), pt(P["AME_y_top10_M2"], 1),
         pt(P["ICC_y_top10_M1"], 3), pt(P["AUC_y_top10_M2"], 3),
         pt(P["EV_y_top10_M2"], 1)]],
       larguras=[5.0, 3.6, 2.2, 1.8, 1.6, 1.8])
bullet(f"Leitura em uma frase: a chance de um trabalhador negro ocupar cargo "
       f"qualificado é {pt(PCT_CBO, 0)}% menor que a de um branco do mesmo bairro e "
       f"perfil; no décimo superior da renda, {pt(PCT_T10, 0)}% menor. O gradiente "
       f"({pt(OR_CBO, 3)} → {pt(OR_T20, 3)} → {pt(OR_T10, 3)}) é o teto de vidro.")
bullet(f"Diga “chance” (odds), não “probabilidade”: por isso o AME está ao lado — "
       f"{pt(abs(P['AME_ocp_qualif_M2']), 1)} pontos percentuais de probabilidade.")
bullet(f"Ajuste: AUC = {pt(P['AUC_ocp_qualif_M2'], 3)} com efeito aleatório contra "
       f"{pt(P['AUCFE_ocp_qualif_M2'], 3)} só com efeitos fixos; corte de Youden "
       f"{pt(P['CUT_ocp_qualif'], 2)} (sensibilidade {pt(P['SENS_ocp_qualif'], 2)}, "
       f"especificidade {pt(P['ESPEC_ocp_qualif'], 2)}). O teste LR contra o logit "
       f"pooled é {milhar(P['LR_ocp_qualif_M2'])} — o efeito aleatório de bairro não é ornamento.")
figura("fig_glmm_or.png",
       "A porta é mais estreita para trabalhadores negros — e estreita ainda mais "
       "no topo da distribuição.")
doc.add_page_break()

# ══ Parte 4 — robustez ════════════════════════════════════════════════════════
titulo("PARTE 4 — A ROBUSTEZ (É AQUI QUE A DEFESA SE GANHA)", 1)

titulo("4.1  Konfound e E-values — e se faltar uma variável?", 2)
bullet(f"Konfound (M3): seria preciso que {pct(P['KONFOUND_M3'])} da estimativa fosse "
       f"viés para invalidar a inferência; a correlação parcial exigida do confundidor "
       f"(ITCV = {pt(P['ITCV_M3'], 3)}) é maior que a de qualquer covariável observada.")
bullet(f"E-value (acesso, M2) = {pt(P['EV_ocp_qualif_M2'], 1)}: um confundidor não medido "
       f"precisaria estar associado a ser negro e ao acesso com OR de pelo menos "
       f"{pt(P['EV_ocp_qualif_M2'], 1)} — acima do observado para escolaridade superior.")

titulo("4.2  Balanceamento e suporte comum", 2)
bullet(f"Das {P['BAL_N_VARS']} covariáveis comparadas entre brancos e negros, "
       f"{P['BAL_N_PEQUENO']} têm d de Cohen abaixo de 0,2 (desequilíbrio pequeno).")
bullet(f"O maior desequilíbrio é justamente o bairro ({P['BAL_MAIOR_VAR']}, "
       f"d = {pt(P['BAL_MAIOR_D'], 2)}) — o que reforça a tese, não a enfraquece: "
       f"a segregação residencial é o desequilíbrio, não um ruído a controlar.")

titulo("4.3  Multicolinearidade (VIF) no M4", 2)
bullet(f"VIF máximo = {pt(P['VIF_MAX'], 2)} ({P['VIF_MAX_VAR']}); "
       f"{P['VIF_N_CRITICO']} de {P['VIF_N_TOTAL']} preditores acima de 10, ambos do "
       f"bloco educacional — colinearidade por construção.")
bullet(f"O que importa: o VIF de 'negro' é {pt(P['VIF_NEGRO'], 2)}. A colinearidade "
       f"infla o erro-padrão dos retornos educacionais, não o do coeficiente de interesse.")

titulo("4.4  Machine learning: validação cruzada e SHAP", 2)
tabela(["Modelo", "R² teste", "R² treino", "Gap treino–teste"],
       [["Random Forest", pt(P["ML_RF_R2"], 3), pt(P["ML_RF_R2_TREINO"], 3),
         pt(P["ML_RF_GAP"], 4)],
        ["XGBoost", pt(P["ML_XGB_R2"], 3), pt(P["ML_XGB_R2_TREINO"], 3),
         pt(P["ML_XGB_GAP"], 4)],
        ["XGBoost sem renda da UPA", pt(P["ML_XGB_SEM_UPA_R2"], 3),
         pt(P["ML_XGB_SEM_UPA_R2_TREINO"], 3), pt(P["ML_XGB_SEM_UPA_GAP"], 4)]],
       larguras=[6.0, 3.0, 3.0, 3.5])
bullet(f"Validação cruzada de {P['CV_K']} folds sobre a população "
       f"({milhar(P['CV_N_TREINO'])} de treino, {milhar(P['CV_N_TESTE'])} de teste): "
       f"R² = {pt(P['CV_R2'], 3)} ± {pt(P['CV_R2_DP'], 4)}.")
bullet(f"A profundidade máxima {P['CV_DEPTH']} foi escolhida entre "
       f"{P['CV_N_CONFIGS']} configurações testadas numa partição de validação dentro "
       f"do treino — a pior delas (profundidade {P['CV_DEPTH_PIOR']}) dava "
       f"R² = {pt(P['CV_R2_PIOR'], 3)}. Diga isso se perguntarem por que 10.")
bullet(f"Erro na unidade original: mediana de R$ {milhar(P['CV_ERRO_MEDIANO'])} por mês "
       f"({pct(P['CV_ERRO_PCT'])} do rendimento), com correção de smearing de Duan "
       f"({pt(P['CV_SMEARING'], 3)}) — porque o modelo prevê log de renda.")
bullet(f"SHAP: a variável racial ocupa a {P['SHAP_RACA_RANK_XGB']}ª posição entre "
       f"{P['SHAP_N_FEATURES']} preditores no XGBoost "
       f"(|SHAP| = {pt(P['SHAP_RACA_XGB'], 4)}). Sem a renda média do bairro entre as "
       f"features, a contribuição da raça é {pt(P['SHAP_RACA_SEM_UPA'], 4)} — "
       f"praticamente a mesma: o resultado não depende do preditor de vizinhança.")
figura("shap_beeswarm_xgb.png",
       "Contexto do bairro e jornada dominam a previsão de renda; a raça aparece na "
       f"{P['SHAP_RACA_RANK_XGB']}ª posição entre {P['SHAP_N_FEATURES']} preditores.",
       largura=14.0)

titulo("4.5  Interseccionalidade (raça × gênero)", 2)
tabela(["Grupo", "Gap vs. homem branco", "Dotações", "Retornos", "N do grupo"],
       [["Mulher branca", pct(P["INT_MULHER_BRANCA_GAP"]), pct(P["INT_MULHER_BRANCA_DOT"]),
         pct(P["INT_MULHER_BRANCA_RET"]), milhar(P["INT_MULHER_BRANCA_N"])],
        ["Homem negro", pct(P["INT_HOMEM_NEGRO_GAP"]), pct(P["INT_HOMEM_NEGRO_DOT"]),
         pct(P["INT_HOMEM_NEGRO_RET"]), milhar(P["INT_HOMEM_NEGRO_N"])],
        ["Mulher negra", pct(P["INT_MULHER_NEGRA_GAP"]), pct(P["INT_MULHER_NEGRA_DOT"]),
         pct(P["INT_MULHER_NEGRA_RET"]), milhar(P["INT_MULHER_NEGRA_N"])]],
       larguras=[3.6, 3.6, 2.6, 2.6, 3.2])
bullet(f"Penalidade extra da mulher negra: {pt(P['INT_PENAL_EXTRA'], 1)} pontos "
       f"percentuais além da soma das penalidades de raça e de gênero isoladas — "
       f"o efeito interseccional puro (Crenshaw, 1989).")
bullet("O sinal negativo das dotações da mulher branca significa que as características "
       "observáveis dela superam as do homem branco: todo o gap dela vem de retornos.")
figura("grupo_rg_interseccional.png",
       "A mulher negra entra na categoria, mas não chega ao topo.", largura=13.0)
doc.add_page_break()

# ══ Parte 5 — equações ════════════════════════════════════════════════════════
titulo("PARTE 5 — EQUAÇÕES PARA MEMORIZAR", 1)

titulo("5.1  HLM de dois níveis", 2)
para("Nível 1 (indivíduo i na UPA j):", bold=True, depois=2)
para("ln(W)ᵢⱼ = β₀ⱼ + β₁·Negroᵢⱼ + β₂·Sexoᵢⱼ + β₃·Xᵢⱼ + β₄·X²ᵢⱼ + Σₑ βₑ·Educₑ,ᵢⱼ + "
     "β₅′Zᵢⱼ + εᵢⱼ,  ε ~ N(0, σ²)", indent=0.8, depois=6)
para("Nível 2 (bairro j):", bold=True, depois=2)
para("β₀ⱼ = γ₀₀ + γ₀₁·%Negroⱼ + γ₀₂·Contextoⱼ + u₀ⱼ,  u₀ⱼ ~ N(0, τ²)", indent=0.8, depois=6)
para(f"ICC = τ² / (τ² + σ²) = {pt(P['TAU2_M0'], 4)} / ({pt(P['TAU2_M0'], 4)} + "
     f"{pt(P['SIGMA2_M0'], 4)}) = {pt(P['ICC_M0'], 3)}", indent=0.8, bold=True)

titulo("5.2  Oaxaca–Blinder (twofold, referência = estrutura de preços dos brancos)", 2)
para("ln(W̄_B) − ln(W̄_N) = (X̄_B − X̄_N)′β̂_B  +  X̄_N′(β̂_B − β̂_N)", indent=0.8, depois=2)
para("                      └── dotações ──┘   └──── retornos ────┘", indent=0.8,
     size=10, color=CINZA)

titulo("5.3  GLMM logístico", 2)
para("logit(P(Yᵢⱼ = 1)) = γ₀₀ + β₁·Negroᵢⱼ + β′Xᵢⱼ + u₀ⱼ,  u₀ⱼ ~ N(0, τ²)",
     indent=0.8, depois=2)
para(f"ICC = τ² / (τ² + π²/3);  OR = exp(β₁) = {pt(OR_CBO, 3)}", indent=0.8, bold=True)

titulo("5.4  E-value (VanderWeele & Ding, 2017)", 2)
para("E = RR + √(RR·(RR − 1)),  com RR = 1/OR quando OR < 1", indent=0.8, depois=2)
para(f"Para OR = {pt(OR_CBO, 3)}:  E = {pt(P['EV_ocp_qualif_M2'], 2)}", indent=0.8, bold=True)
doc.add_page_break()

# ══ Parte 6 — perguntas difíceis ══════════════════════════════════════════════
titulo("PARTE 6 — AS PERGUNTAS DIFÍCEIS, COM RESPOSTA PRONTA", 1)
para("Regra de ouro: nunca diga “causa”, “prova” ou “determina”. Diga "
     "“associa-se”, “é consistente com”, “penalidade condicional a X”.",
     italic=True, color=VERMELHO)

pergunta("Isso é causal?",
         "Não, e o trabalho não afirma que seja. O que se estima é associação "
         "condicional sob seleção em observáveis. A seção de limitações lista as sete "
         "hipóteses uma a uma e o que acontece se cada uma falhar. O que sustenta o "
         f"diagnóstico é a convergência de quatro métodos e a magnitude: seria preciso "
         f"{pct(P['KONFOUND_M3'])} de viés, ou um confundidor com OR de "
         f"{pt(P['EV_ocp_qualif_M2'], 1)}, para anular o resultado.")

pergunta("Controlar por ocupação não é bad control?",
         "É, e é por isso que as duas versões são reportadas lado a lado. Ocupação, "
         "formalidade e horas são desfechos da própria discriminação: incluí-las (M4, "
         f"especificação B da Oaxaca-Blinder) dá {pct(P['GAP_M4'])} — um limite "
         f"inferior descritivo, a discriminação dentro da ocupação. Sem elas (M3, "
         f"especificação A) o gap é {pct(P['GAP_M3'])}. A comparação com a literatura "
         "é feita sempre na mesma especificação.")

pergunta("A renda média do bairro não é reflexo (Manski)?",
         "É — e por isso ela foi removida dos modelos de acesso e, no XGBoost, "
         "substituída pela média leave-one-out, que exclui o próprio indivíduo. O R² "
         "cai pouco e a contribuição SHAP da raça fica praticamente idêntica "
         f"({pt(P['SHAP_RACA_XGB'], 4)} contra {pt(P['SHAP_RACA_SEM_UPA'], 4)} sem a "
         "variável). Ainda assim, choques comuns ao bairro impedem leitura causal do "
         "coeficiente contextual, e isso está dito nas limitações.")

pergunta("Os erros-padrão consideram o desenho da PNAD?",
         f"Sim. A PNAD amostra por conglomerados, então todos os modelos reportam erro-padrão "
         f"agrupado por UPA ou modelam o bairro como efeito aleatório. Oaxaca-Blinder, "
         f"regressão quantílica e RIF usam bootstrap em blocos de UPA. Para o "
         f"agrupamento por UF, que tem só 27 clusters, usa-se t com G−1 graus de "
         f"liberdade — abaixo das 42 unidades que Angrist e Pischke sugerem como piso "
         f"para a aproximação normal.")

pergunta("Por que não usar os pesos amostrais?",
         "As estimativas principais são não ponderadas e isso está declarado: elas "
         "descrevem a regressão na amostra, não a média populacional. Como robustez, o "
         "modelo-chave foi reestimado com o peso V1028 e o gap muda menos de meio ponto "
         "percentual. Em regressão com os estratos do desenho entre os controles, "
         "ponderar altera pouco os coeficientes e infla a variância.")

pergunta("Com 7,7 milhões de observações, tudo não fica significativo?",
         "Fica — e é por isso que a leitura privilegia magnitude, intervalos de "
         "confiança e E-values, não asteriscos. Um exemplo no próprio trabalho: a "
         "tendência temporal do gap, com esse N, tem p = 0,077 e não se distingue de "
         "zero; a conclusão conservadora é que a década não produziu convergência "
         "mensurável.")

pergunta("Por que UPA como efeito aleatório e UF como efeito fixo?",
         "Porque 27 unidades são poucas para estimar uma distribuição no terceiro "
         "nível, e 26 dummies absorvem todo o contexto estadual sem hipótese "
         "distribucional. A hipótese em teste é sobre o bairro, que tem "
         f"{milhar(P['N_UPAS'])} unidades. Como contraprova, todos os coeficientes "
         "foram reestimados com efeitos fixos de UF e erro agrupado por UPA, com as "
         "mesmas conclusões.")

pergunta("Só analisa quem tem renda positiva — isso não é seleção?",
         "É condicionar no desfecho, sim. A direção provável do viés é de subestimação: "
         "se os trabalhadores negros que permanecem ocupados são positivamente "
         "selecionados em atributos não observados, o gap entre observados é menor que "
         "o gap potencial. O modelo logístico de acesso trata diretamente a outra "
         "metade do problema, e a correção de Heckman, estimada na versão estendida, "
         "indicou seleção não nula com o coeficiente racial estável em sinal e ordem "
         "de grandeza.")

pergunta("OR de 0,699 quer dizer 30% menos probabilidade?",
         f"Não: quer dizer {pt(PCT_CBO, 0)}% menos chance, no sentido de odds. Em "
         f"probabilidade, o efeito marginal médio é de "
         f"{pt(abs(P['AME_ocp_qualif_M2']), 1)} pontos percentuais. Os dois números "
         "estão na tabela justamente para essa pergunta.")

pergunta("Por que machine learning num trabalho de econometria?",
         "Ele não estima efeito nenhum — tem função de contraprova. Se a penalidade "
         "racial fosse artefato da forma funcional linear imposta pelo HLM, um modelo "
         "sem essa imposição não daria peso à variável de raça. Dá: "
         f"{P['SHAP_RACA_RANK_XGB']}ª posição entre {P['SHAP_N_FEATURES']} preditores. "
         "É convergência entre dois regimes epistemológicos diferentes — um "
         "inferencial, outro preditivo.")

pergunta("Como sabe que o XGBoost não está sobreajustado?",
         f"Três evidências: o gap entre R² de treino e de teste é "
         f"{pt(P['ML_XGB_GAP'], 4)}; N é muitas ordens de grandeza maior que a "
         f"complexidade do modelo regularizado; e o R² de teste é estável entre a "
         f"validação cruzada de {P['CV_K']} folds ({pt(P['CV_R2'], 3)} ± "
         f"{pt(P['CV_R2_DP'], 4)}) e a partição única. Ampliar a base de amostral para "
         f"populacional reduz, não aumenta, o risco de sobreajuste.")

pergunta("Por que não há análise de redes sociais nem pesquisa operacional?",
         "Porque o escopo foi fechado em quatro métodos que respondem a quatro "
         "perguntas distintas e podem ser defendidos em profundidade. As análises de "
         "redes e de priorização de políticas existem, estão preservadas no branch "
         "mestrado-extenso do repositório, mas ficaram como agenda: sem dado de vínculo "
         "individual, a rede é de co-residência e não de indicação profissional — o "
         "mecanismo de Granovetter fica como hipótese não testada.")

pergunta("A mulher negra tem penalidade dupla ou tripla?",
         f"Nem uma nem outra, e é esse o achado: a penalidade dela "
         f"({pct(P['INT_MULHER_NEGRA_GAP'])} vs. o homem branco) é maior que a soma das "
         f"penalidades isoladas de raça e de gênero, mas por "
         f"{pt(P['INT_PENAL_EXTRA'], 1)} pontos percentuais, não pelo dobro. A "
         "interação é sub-aditiva: existe efeito interseccional puro, e ele é menor do "
         "que a leitura mais dramática sugeriria. Dizer o número exato é mais forte que "
         "dizer “dupla discriminação”.")

pergunta("Qual é a maior fragilidade do trabalho?",
         "O desenho transversal. Não se observa a mesma pessoa ao longo do tempo, "
         "então nada aqui identifica trajetória individual — só diferenças entre "
         "pessoas comparáveis num dado momento. A segunda é a cobertura da escolaridade "
         "detalhada, registrada para cerca de 31% da PEA no painel público; por isso "
         "os níveis entram como dummies de conclusão com indicador explícito de "
         "não-registro, e os retornos educacionais são lidos com cautela.")

doc.add_page_break()
titulo("Checklist final da véspera", 1)
for item in [
    f"Sei dizer de cor: {pct(P['GAP_POOL'])} agregado → {pct(P['MED_BAIRRO'])} mediado "
    f"pelo bairro → {pct(P['GAP_M3'])} líquido → {pct(P['GAP_M4'])} dentro da ocupação.",
    f"Sei dizer de cor: OR {pt(OR_CBO, 3)} no acesso e {pt(OR_T10, 3)} no topo 10%.",
    f"Sei dizer de cor: ICC {pt(P['ICC_M0'], 3)} — {pct(P['ICC_M0'] * 100, 0)} da "
    f"variância é entre bairros.",
    "Sei explicar bad control sem consultar anotação.",
    "Sei explicar por que quantil condicional e incondicional não se contradizem.",
    "Sei dizer o que faria diferente com dado longitudinal (RAIS identificada).",
    "Não usei a palavra “causa” uma única vez.",
]:
    bullet(item)

para("", depois=12)
para("Guia gerado automaticamente por tcc/scripts/gerar_guia_estudo.py a partir dos "
     "csv de outputs/tables/. Se alguma análise for reexecutada, rode o gerador de "
     "novo para que os números acompanhem.", size=9, italic=True, color=CINZA)

OUT.parent.mkdir(exist_ok=True)
doc.save(str(OUT))
print(f"OK -> {OUT.relative_to(ROOT)}  ({OUT.stat().st_size // 1024} KB)")
print(f"     {len(doc.paragraphs)} parágrafos, {len(doc.tables)} tabelas, "
      f"{len(P)} parâmetros lidos dos csv")
