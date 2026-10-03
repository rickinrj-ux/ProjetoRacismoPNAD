# -*- coding: utf-8 -*-
"""
gerar_apresentacao_executiva.py
===============================
Gera `entregaveis/TCC_Ricardo_Calheiros_Executiva.pptx` — 10 slides para gestores,
congressos e público não técnico: mesma história do TCC, sem jargão.

Todo número vem de `params_nucleo.py`, que lê os csv de `outputs/tables/`.
Substitui os dois decks executivos antigos (`gerar_apresentacao_executiva.py` e
`gerar_apresentacao_executiva_pptx.py` em scripts/geradores/), que traziam a
narrativa de três barreiras e cinco métodos, anterior ao recorte de escopo, com
números escritos à mão.

Uso: python tcc/scripts/gerar_apresentacao_executiva.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches as In

from params_nucleo import P, milhar, pct, pt, titulo_bairro, frase_sintese
from pptx_helpers import (C_BLACK, C_BLUE, C_DARK, C_GRAY, C_LGRAY, C_RED,
                          C_WHITE, H, W, add_img, add_multiline, add_rect,
                          add_text, bullets, faixa_final, header_bar, kpi,
                          rodape)

ROOT = Path(__file__).resolve().parents[2]
FIGS = ROOT / "outputs" / "figures"
OUT = ROOT / "entregaveis" / "TCC_Ricardo_Calheiros_Executiva.pptx"

# ── números (todos dos csv) ───────────────────────────────────────────────────
OR_CBO = P["OR_ocp_qualif_M2"]
OR_T10 = P["OR_y_top10_M2"]
PCT_CBO = (1 - OR_CBO) * 100
PCT_T10 = (1 - OR_T10) * 100

prs = Presentation()
prs.slide_width, prs.slide_height = W, H
BLANK = prs.slide_layouts[6]
novo = lambda: prs.slides.add_slide(BLANK)

# ══ 1 — Capa ══════════════════════════════════════════════════════════════════
s = novo()
add_rect(s, 0, 0, W, H, fill_rgb=C_DARK)
add_text(s, "A porta antes do salário", In(0.9), In(1.9), In(11.5), In(1.0),
         font_size=44, bold=True, color=C_WHITE)
add_text(s, "Como a desigualdade racial opera no mercado de trabalho brasileiro",
         In(0.9), In(3.0), In(11.5), In(0.6), font_size=21, color=C_WHITE)
add_rect(s, In(0.9), In(3.8), In(2.2), In(0.06), fill_rgb=C_WHITE)
add_multiline(s, [
    "PNAD Contínua 2016–2025 · 7,7 milhões de trabalhadores · "
    f"{milhar(P['N_UPAS'])} bairros",
    "Ricardo Calheiros · MBA em Data Science e Analytics · ESALQ/USP",
], In(0.9), In(4.2), In(11.5), In(1.2), font_size=15, color=C_WHITE)
rodape(s, 1, "")

# ══ 2 — A pergunta ════════════════════════════════════════════════════════════
s = novo()
header_bar(s, "Educação explica o gap racial de renda? Os dados dizem que não",
           "A pergunta que organiza o trabalho")
add_text(s, "A explicação usual para o gap racial de renda é diferença de "
            "qualificação. Se fosse só isso, ampliar o acesso ao ensino "
            "resolveria. Este trabalho testa essa hipótese separando, um a um, "
            "os mecanismos que produzem o gap.",
         In(0.5), In(1.35), In(12.4), In(1.1), font_size=18, color=C_BLACK)
bullets(s, [
    "Quanto do gap é diferença de características — e quanto é preço diferente "
    "pelas mesmas características?",
    "Quanto vem de onde a pessoa mora?",
    "A barreira está no salário ou antes dele, no acesso à ocupação?",
    "A penalidade é a mesma em toda a distribuição de renda?",
], In(0.8), In(2.7), In(11.8), In(2.6), font_size=19)
faixa_final(s, "Quatro perguntas, quatro métodos — e uma resposta que não é a "
               "do senso comum.")
rodape(s, 2)

# ══ 3 — O dado ════════════════════════════════════════════════════════════════
s = novo()
header_bar(s, "Dez anos de PNAD Contínua, com todos os registros",
           "Todos os trabalhadores ocupados com rendimento que a pesquisa entrevistou — nenhuma subamostra sorteada")
kpi(s, "Trabalhadores analisados", f"{pt(P['N_GLMM'] / 1e6, 1)} mi",
    ["Todos os ocupados com rendimento positivo,", "2016 a 2025"],
    In(0.5), In(1.5), In(3.9), In(2.6))
kpi(s, "Bairros (UPAs da PNAD)", milhar(P["N_UPAS"]),
    ["A unidade de vizinhança da PNAD —", "é o que permite comparar vizinhos"],
    In(4.7), In(1.5), In(3.9), In(2.6))
kpi(s, "Trimestres cobertos", "40",
    ["Série completa da pesquisa,", "sem recorte de conveniência"],
    In(8.9), In(1.5), In(3.9), In(2.6))
add_multiline(s, [
    "Por que isso importa: com todos os registros, o resultado não depende de "
    "uma subamostra escolhida pelo autor. Com milhões de observações, a pergunta deixa "
    "de ser “será que é ruído?” e passa a ser “qual é o tamanho do efeito?”.",
    "Os erros-padrão são agrupados por bairro, porque a PNAD entrevista "
    "domicílios vizinhos — ignorar isso faria qualquer diferença parecer mais "
    "precisa do que é.",
], In(0.6), In(4.4), In(12.2), In(1.9), font_size=16, color=C_GRAY)
rodape(s, 3)

# ══ 4 — Barreira I: a porta ═══════════════════════════════════════════════════
s = novo()
header_bar(s, f"Barreira de acesso: chances {pt(PCT_CBO, 0)}% menores de "
              f"chegar a um cargo qualificado",
           "Comparando pessoas com a mesma escolaridade, idade, sexo e bairro")
kpi(s, "Acesso a cargo qualificado", f"−{pt(PCT_CBO, 0)}%",
    [f"chance (odds ratio {pt(OR_CBO, 3)})",
     f"= {pt(abs(P['AME_ocp_qualif_M2']), 1)} pontos percentuais"],
    In(0.6), In(1.45), In(3.8), In(2.5), cor_valor=C_RED)
kpi(s, "Chegar ao topo 20% da renda", f"−{pt((1 - P['OR_y_top20_M2']) * 100, 0)}%",
    ["a barreira aperta conforme", "a posição sobe"],
    In(4.75), In(1.45), In(3.8), In(2.5))
kpi(s, "Chegar ao topo 10% da renda", f"−{pt(PCT_T10, 0)}%",
    ["é o teto de vidro:", "quanto mais alto, mais estreita a porta"],
    In(8.9), In(1.45), In(3.8), In(2.5), cor_valor=C_RED)
add_multiline(s, [
    "Mesma escolaridade. Mesma idade. Mesmo sexo. Mesmo bairro. A diferença "
    "que resta é o acesso à ocupação — e ela é maior do que a diferença de salário.",
    f"Seria preciso um fator não medido associado tanto à raça quanto ao acesso "
    f"com força de {pt(P['EV_ocp_qualif_M2'], 1)}× para explicar esse resultado por "
    f"inteiro — mais forte que ter ensino superior.",
], In(0.6), In(4.2), In(12.2), In(1.9), font_size=16.5)
faixa_final(s, "A exclusão começa antes do contracheque.", cor=C_RED)
rodape(s, 4)

# ══ 5 — Barreira II: o salário e o bairro ═════════════════════════════════════
s = novo()
header_bar(s, titulo_bairro(P),
           "E o que sobra não é explicado por escolaridade, estado nem ocupação")
add_img(s, FIGS / "fig_hlm_gap.png", In(0.55), In(1.35), In(7.5))
bullets(s, [
    f"Gap de partida: {pct(P['GAP_POOL'])} a menos, mesma escolaridade e idade.",
    f"{pct(P['MED_BAIRRO'])} desse gap é mediado pelo bairro de moradia.",
    f"Gap líquido: {pct(P['GAP_M3'])} — mesma escolaridade, idade, sexo e bairro.",
    f"Dentro da mesma ocupação ainda restam {pct(P['GAP_M4'])}.",
    f"{pct(P['ICC_M0'] * 100, 0)} da variação de renda está entre bairros, "
    f"não entre pessoas.",
], In(8.3), In(1.6), In(4.6), In(4.2), font_size=15.5)
faixa_final(s, f"Onde a pessoa mora responde por {pct(P['MED_BAIRRO'], 0)} do gap — "
               "política de renda que ignora território tem eficácia limitada.")
rodape(s, 5)

# ══ 6 — Composição ou preço ═══════════════════════════════════════════════════
s = novo()
header_bar(s, f"{pct(P['OB_SEM_RET_PCT'])} do gap é preço diferente pelas mesmas características",
           "Decomposição de Oaxaca–Blinder, o método padrão da economia do trabalho")
add_img(s, FIGS / "fig_ob_cascata.png", In(0.6), In(1.35), In(7.6))
add_multiline(s, [
    "Como ler:",
    f"• {pct(P['OB_SEM_DOT_PCT'])} do gap vem de os grupos terem características "
    f"diferentes (dotações).",
    f"• {pct(P['OB_SEM_RET_PCT'])} vem de as mesmas características renderem menos "
    f"a trabalhadores negros.",
    "",
    f"Quando a ocupação entra como se fosse característica, essa segunda parcela "
    f"cai para {pct(P['OB_COM_RET_PCT'])} — mas isso subestima o problema, porque "
    f"o acesso à ocupação é ele próprio desigual — é a porta de entrada que o GLMM mede.",
], In(8.4), In(1.6), In(4.5), In(4.4), font_size=15)
faixa_final(s, "As mesmas credenciais rendem menos — por isso educação, sozinha, "
               "não fecha a conta.")
rodape(s, 6)

# ══ 7 — Onde pesa na distribuição ═════════════════════════════════════════════
s = novo()
header_bar(s, "Quanto mais alto o salário, maior a penalidade racial",
           "E, na base da distribuição, a maior parte do gap é preço, não característica")
add_img(s, FIGS / "fig_qr_rif.png", In(0.5), In(1.3), In(12.4), In(4.05))
add_multiline(s, [
    f"À esquerda: a penalidade cresce de {pct(P['QR_GAP_Q10'])} na base para "
    f"{pct(P['QR_GAP_Q90'])} no topo — é o teto de vidro.",
    f"À direita: na base da distribuição, {pct(P['RIF_RET_Q10'])} do gap é preço "
    f"diferente; no topo, {pct(P['RIF_RET_Q90'])} — é o piso pegajoso.",
], In(0.6), In(5.5), In(12.2), In(1.0), font_size=15, color=C_GRAY)
faixa_final(s, "Duas perguntas, dois padrões: entre pares, quem sobe encontra teto; "
               "na renda do país, quem está embaixo é mal pago.")
rodape(s, 7)

# ══ 8 — Interseccionalidade ═══════════════════════════════════════════════════
s = novo()
header_bar(s, "A mulher negra entra na categoria, mas não chega ao topo",
           "Raça e gênero não se somam: combinam-se")
add_img(s, FIGS / "grupo_rg_interseccional.png", In(0.7), In(1.4), In(6.6))
kpi(s, "Gap da mulher negra vs. homem branco", pct(P["INT_MULHER_NEGRA_GAP"]),
    ["o maior de todos os grupos"],
    In(8.0), In(1.55), In(4.6), In(2.0), cor_valor=C_RED)
kpi(s, "Penalidade além da soma raça + gênero", f"+{pt(P['INT_PENAL_EXTRA'], 1)} p.p.",
    ["o efeito interseccional puro —", "existe, e é menor que o dobro"],
    In(8.0), In(3.8), In(4.6), In(2.3))
faixa_final(s, "Política desenhada só para “negros” ou só para “mulheres” deixa "
               "essa parcela de fora.")
rodape(s, 8)

# ══ 9 — Robustez ══════════════════════════════════════════════════════════════
s = novo()
header_bar(s, "O resultado sobrevive a tudo o que se tentou contra ele",
           "Quatro checagens independentes")
caixas = [
    ("Sem impor forma funcional",
     f"Um modelo de machine learning, que não assume relação linear, coloca a "
     f"raça na {P['SHAP_RACA_RANK_XGB']}ª posição entre {P['SHAP_N_FEATURES']} "
     f"variáveis — mesmo com todas as informações de escolaridade e contexto."),
    ("E se faltasse uma variável?",
     f"Um fator não medido precisaria ter força de {pt(P['EV_ocp_qualif_M2'], 1)}× "
     f"para anular o resultado do acesso, e seria preciso que "
     f"{pct(P['KONFOUND_M3'])} da estimativa do gap fosse viés."),
    ("Sem sobreajuste",
     f"Validação cruzada de {P['CV_K']} partições sobre a população inteira: "
     f"R² de {pt(P['CV_R2'], 3)} com variação de {pt(P['CV_R2_DP'], 4)} entre elas. "
     f"O erro típico de previsão é de R$ {milhar(P['CV_ERRO_MEDIANO'])} por mês."),
    ("Sem depender do bairro",
     f"Retirando a renda do bairro do modelo, a contribuição da raça praticamente "
     f"não muda ({pt(P['SHAP_RACA_XGB'], 4)} contra {pt(P['SHAP_RACA_SEM_UPA'], 4)}): "
     f"o achado não é um artefato dessa variável."),
]
for i, (titulo_c, corpo) in enumerate(caixas):
    x = In(0.5) + (i % 2) * In(6.4)
    y = In(1.45) + (i // 2) * In(2.5)
    add_rect(s, x, y, In(6.1), In(2.25), fill_rgb=C_LGRAY)
    add_text(s, titulo_c, x + In(0.25), y + In(0.15), In(5.6), In(0.4),
             font_size=17, bold=True, color=C_DARK)
    add_text(s, corpo, x + In(0.25), y + In(0.65), In(5.6), In(1.5),
             font_size=14, color=C_BLACK)
faixa_final(s, "Nenhuma dessas checagens é decisiva sozinha — juntas, tornam a "
               "explicação alternativa implausível.")
rodape(s, 9)

# ══ 10 — O que fazer ══════════════════════════════════════════════════════════
s = novo()
header_bar(s, "Cada barreira medida tem um instrumento legal que já existe",
           "O diagnóstico aponta onde intensificar, não o que inventar")
itens = [
    ("Barreira de acesso", "Lei 12.990/2014 (cotas em concursos federais)",
     f"O diagnóstico sugere ampliar o alcance para níveis hierárquicos "
     f"superiores, onde a porta é mais estreita (−{pt(PCT_T10, 0)}% no topo 10%)."),
    ("Retorno da qualificação", "Prouni, Fies e o legado do PRONATEC",
     "As mesmas credenciais rendem menos; esses programas precisam vir "
     "acompanhados de mecanismos de inserção ocupacional."),
    ("Discriminação salarial", "Lei 9.029/1995 e Estatuto da Igualdade Racial",
     f"O gap líquido de {pct(P['GAP_M3'])} — e os {pct(P['GAP_M4'])} que persistem "
     f"dentro da mesma ocupação — justificam reforçar a fiscalização."),
]
for i, (barreira, lei, acao) in enumerate(itens):
    y = In(1.35) + i * In(1.65)
    add_rect(s, In(0.5), y, In(12.3), In(1.45), fill_rgb=C_LGRAY)
    add_text(s, barreira, In(0.75), y + In(0.12), In(3.2), In(0.4),
             font_size=17, bold=True, color=C_RED)
    add_text(s, lei, In(0.75), y + In(0.62), In(3.4), In(0.6),
             font_size=13.5, color=C_GRAY)
    add_text(s, acao, In(4.4), y + In(0.22), In(8.1), In(1.1),
             font_size=15, color=C_BLACK)
add_text(s, frase_sintese(P),
         In(0.5), In(6.45), In(12.3), In(0.8), font_size=17, bold=True,
         color=C_DARK, align=PP_ALIGN.CENTER)
rodape(s, 10)

OUT.parent.mkdir(exist_ok=True)
prs.save(str(OUT))
print(f"OK -> {OUT.relative_to(ROOT)}  ({OUT.stat().st_size // 1024} KB)")
print(f"     {len(prs.slides.__iter__.__self__._sldIdLst)} slides, "
      f"{len(P)} parâmetros lidos dos csv")
