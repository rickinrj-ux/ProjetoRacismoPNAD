"""
gerar_resultados_preliminares.py
================================
Monta o documento de RESULTADOS PRELIMINARES no modelo MBA USP/Esalq
(Template Resultados Preliminares_PT). Estrutura: Título, Autores, Resumo,
Palavras-chave, Introdução, Material e Métodos, Resultados Preliminares,
Limitações, Considerações, Referências. Formatação: Times New Roman 12,
espaçamento 1,5, justificado, títulos de seção em negrito à esquerda.

Todos os números vêm de `params_nucleo.py`, que lê os csv de outputs/tables/ —
os mesmos do relatório. A versão anterior (scripts/geradores/) lia o params.py
da raiz e csv da série estendida, e por isso ficou com números que o relatório
já não sustenta.

Saída: entregaveis/Resultados_Preliminares_TCC.docx

Etapa vencida: a versão de setembro está em entregaveis/_arquivo/ e o
relatório final a substitui. Este gerador fica pronto para o caso de uma
nova submissão no modelo Resultados Preliminares; por isso saiu do
run_tcc.ps1 e precisa ser chamado à mão.
"""

# --- bootstrap raiz do projeto ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
# --- fim bootstrap ---

import sys
from pathlib import Path
import pandas as pd
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from params_nucleo import P, milhar, pt as _pt

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path.cwd()
FIG  = ROOT / "outputs" / "figures"
OUT  = ROOT / "entregaveis" / "Resultados_Preliminares_TCC.docx"
(ROOT / "entregaveis").mkdir(exist_ok=True)

# compatibilidade com os helpers do documento (pt-BR, sem o menos tipográfico,
# que o Word do template não renderiza bem em tabela)
def fmt(v, dec=3):  return _pt(v, dec).replace("−", "-")
def fmtN(n):        return milhar(n)
def or_str(v, dec=3): return fmt(v, dec)
def ame(v, dec=2):  return f"AME {fmt(v, dec)} p.p."

def g(k, d=0.0): return P.get(k, d)
def pa(v, dec=1): return fmt(abs(v), dec)   # |valor| em pt-BR

doc = Document()
# Defaults de estilo (USP/Esalq)
st = doc.styles["Normal"]
st.font.name = "Times New Roman"; st.font.size = Pt(12)
st.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
st.paragraph_format.space_after = Pt(6)
for s in doc.sections:
    s.top_margin = Cm(3); s.bottom_margin = Cm(2); s.left_margin = Cm(3); s.right_margin = Cm(2)


def titulo(t):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(t); r.bold = True; r.font.size = Pt(14); r.font.name = "Times New Roman"

def centro(t, size=12, italic=False, bold=False):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(t); r.italic = italic; r.bold = bold; r.font.size = Pt(size); r.font.name = "Times New Roman"

def secao(t):
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(12)
    r = p.add_run(t); r.bold = True; r.font.size = Pt(12); r.font.name = "Times New Roman"

def sub(t):
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(6)
    r = p.add_run(t); r.bold = True; r.italic = True; r.font.size = Pt(12); r.font.name = "Times New Roman"

def par(t):
    p = doc.add_paragraph(t); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Cm(1.25)
    return p

def kv(rotulo, txt):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(rotulo); r.bold = True; r.font.name = "Times New Roman"
    r2 = p.add_run(txt); r2.font.name = "Times New Roman"

def figura(nome, legenda, w=15):
    path = FIG / nome
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if path.exists():
        p.add_run().add_picture(str(path), width=Cm(w))
    else:
        p.add_run(f"[figura: {nome}]").italic = True
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rc = c.add_run(legenda); rc.font.size = Pt(10); rc.font.name = "Times New Roman"
    c.paragraph_format.space_after = Pt(10)


def tabela(legenda, headers, rows):
    """Tabela de resultado (pedido do orientador): legenda acima (ABNT), grade."""
    cap = doc.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(8)
    rc = cap.add_run(legenda); rc.font.size = Pt(10); rc.bold = True; rc.font.name = "Times New Roman"
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER

    def _cell(cell, txt, bold=False):
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cell.paragraphs[0].add_run(str(txt))
        r.font.size = Pt(10); r.bold = bold; r.font.name = "Times New Roman"

    for j, h in enumerate(headers):
        _cell(t.rows[0].cells[j], h, bold=True)
    for row in rows:
        cells = t.add_row().cells
        for j, v in enumerate(row):
            _cell(cells[j], v)
    doc.add_paragraph().paragraph_format.space_after = Pt(8)


# ── Carrega resultados dos CSV canônicos (para as tabelas) ─────────────────────
TBL = ROOT / "outputs" / "tables"
_oba = pd.read_csv(TBL / "ob_acesso.csv").set_index("espec")
_itx = pd.read_csv(TBL / "interseccional_ob4grupos_nucleo.csv")


def _glm_m2(des):
    """GLMM de verdade (lme4::glmer) — M2 é o modelo com contexto de bairro."""
    return [fmt(g(f"OR_{des}_M2"), 3), fmt(g(f"AME_{des}_M2"), 1),
            fmt(g(f"EV_{des}_M2"), 2)]


# step-up do HLM de dois níveis, com o gap agregado (OLS + UF) como referência
_med_rows = [["Agregado (individual + UF, sem bairro)", fmt(g("B_POOL"), 4),
              f"-{fmt(g('GAP_POOL'), 1)}", "—"]]
_MEDLBL = {"M1": "M1 (+ intercepto aleatório de UPA)", "M2": "M2 (+ contexto da UPA)",
           "M3": "M3 (+ efeitos fixos de UF)", "M4": "M4 (+ ocupação e formalidade)"}
for _m in ("M1", "M2", "M3", "M4"):
    _med_rows.append([_MEDLBL[_m], fmt(g(f"B_{_m}"), 4), f"-{fmt(g(f'GAP_{_m}'), 1)}",
                      fmt(g(f"MED_ACUM_{_m}"), 1)])

# as duas especificações da Oaxaca-Blinder, lado a lado (MHE-25)
_oba_rows = [
    ["Dotações — (A) capital humano e contexto", fmt(g("OB_SEM_DOT_PCT"), 1),
     fmt(g("OB_COM_DOT_PCT"), 1)],
    ["Retornos — parcela não explicada", fmt(g("OB_SEM_RET_PCT"), 1),
     fmt(g("OB_COM_RET_PCT"), 1)],
]
_itx_rows = [[r["grupo"], fmt(r["gap_pct"], 1), fmt(r["end_pct"], 1), fmt(r["ret_pct"], 1),
              ("—" if abs(r["penalidade_extra_pct"]) < 1e-6 else fmt(r["penalidade_extra_pct"], 1))]
             for r in _itx.to_dict("records")]


# ── Cabeçalho ─────────────────────────────────────────────────────────────────
titulo("A desigualdade racial no mercado de trabalho brasileiro é estrutural, "
       "contextual e geograficamente heterogênea")
doc.add_paragraph()
centro("Ricardo Calheiros¹*; Edilson José Rodrigues²", size=12)
centro("¹* MBA em Data Science e Analytics, USP/Esalq. E-mail: rickinrj@gmail.com", size=10)
centro("² Orientador. MBA USP/Esalq.", size=10)
doc.add_paragraph()

# ── Resumo ────────────────────────────────────────────────────────────────────
secao("Resumo")
par(f"A desigualdade racial no mercado de trabalho brasileiro foi investigada com a PNAD "
    f"Contínua (2016–2025; {fmtN(g('N_GLMM'))} observações da população economicamente "
    f"ativa com rendimento positivo), integrando econometria multinível, decomposições do "
    f"gap e aprendizado de máquina interpretável. Os resultados indicam que a discriminação "
    f"opera em camadas: uma barreira de acesso a ocupações qualificadas (GLMM logístico "
    f"com intercepto aleatório de bairro, OR={or_str(g('OR_ocp_qualif_M2'))}) que se agrava "
    f"no topo da distribuição (OR de acesso ao decil superior = "
    f"{or_str(g('OR_y_top10_M2'))}) e uma penalidade salarial que persiste sob controle "
    f"exaustivo. Do gap agregado de {pa(g('GAP_POOL'))}%, {pa(g('MED_BAIRRO'))}% é mediado "
    f"pelo contexto de moradia (UPA), restando um gap líquido de {pa(g('GAP_M3'))}% e "
    f"{pa(g('GAP_M4'))}% dentro da mesma ocupação; a decomposição de Oaxaca-Blinder atribui "
    f"{pa(g('OB_SEM_RET_PCT'))}% do gap a retornos diferenciais quando a ocupação não é "
    f"tratada como dotação, e {pa(g('OB_COM_RET_PCT'))}% quando é — limite inferior, pois o "
    f"acesso à ocupação é ele próprio desigual. A penalidade recai de forma agravada sobre a "
    f"mulher negra, com efeito interseccional de +{pa(g('INT_PENAL_EXTRA'))} p.p. além da "
    f"soma dos eixos de raça e de gênero.")
kv("Palavras-chave: ", "gap salarial racial; modelos hierárquicos; teto de vidro; "
   "decomposição de Oaxaca-Blinder; interseccionalidade.")

# ── Introdução ────────────────────────────────────────────────────────────────
secao("Introdução")
par("A persistência da desigualdade racial no mercado de trabalho brasileiro é um dos "
    "fenômenos mais documentados das ciências sociais nacionais, desde a tese do "
    "preconceito estrutural de Hasenbalg (1979) até as decomposições contemporâneas do "
    "rendimento (Henriques, 2001; Soares, 2009). Apesar do avanço educacional das últimas "
    "décadas, trabalhadores negros seguem auferindo rendimentos inferiores e ocupando, em "
    "menor proporção, as posições de maior prestígio e remuneração — um padrão que a "
    "explicação meritocrática, baseada apenas em capital humano, não dá conta de prever.")
par("Esse hiato convive com um quadro recente de avanço social com desigualdade persistente: a "
    "Pesquisa de Orçamentos Familiares (POF) do IBGE registra melhora ampla na qualidade de vida "
    "entre 2008 e 2018 (queda de ~30% no Índice de Perda de Qualidade de Vida), mas sem fechar o "
    "gap racial (chefes pretos/pardos 0,183 vs. brancos 0,122) nem o territorial (Norte 0,223 / "
    "Nordeste 0,207 vs. Sul 0,114; IBGE, POF 2017–2018). No rendimento, o Gini domiciliar per "
    "capita voltou a subir em 2025 (0,491, ante 0,487 em 2024), puxado pelo topo (IBGE/PNAD "
    "Contínua, 2025). É esse padrão — progresso agregado que não dissolve a barreira racial — que "
    "este trabalho disseca no mercado de trabalho.")
par("A literatura internacional sugere que a discriminação não é um evento único na "
    "contratação, mas um sistema de barreiras que se reforçam: exclusão de acesso a "
    "ocupações qualificadas (Pager, 2007), efeitos de vizinhança e segregação residencial "
    "(Wilson, 1987; Sampson, 1997) e barreiras na conversão de credenciais em ocupações "
    "qualificadas (Pager, 2007). Tratados isoladamente, esses "
    "mecanismos têm sido difíceis de quantificar de forma integrada e em escala nacional.")
par("Este trabalho enfrenta essa lacuna combinando, sobre a série completa da PNAD "
    "Contínua, quatro métodos complementares — modelos lineares hierárquicos (HLM), "
    "decomposição de Oaxaca-Blinder, regressão quantílica com RIF e modelos logísticos "
    "multiníveis (GLMM) —, validados por aprendizado de máquina com valores SHAP. A "
    "convergência de métodos independentes sobre o mesmo conjunto de dados permite distinguir os "
    "mecanismos da desigualdade e testar sua robustez.")
par("O objetivo deste trabalho é identificar, isolar e quantificar os mecanismos da "
    "desigualdade racial de rendimentos e de acesso ocupacional no Brasil, distinguindo a "
    "parcela de composição da parcela de discriminação e traduzindo o diagnóstico em "
    "implicações de política focadas no acesso a ocupações qualificadas.")

# ── Material e Métodos ────────────────────────────────────────────────────────
secao("Material e Métodos")
sub("Base de dados")
par(f"Utilizou-se a Pesquisa Nacional por Amostra de Domicílios Contínua (PNAD Contínua/"
    f"IBGE), série completa de 2016 a 2025, totalizando {fmtN(g('N_GLMM'))} "
    f"observações da população economicamente ativa com rendimento positivo após o "
    f"tratamento dos dados. As variáveis incluíram raça (preto/pardo agregados em 'negro'), "
    f"gênero, idade, escolaridade, jornada, vínculo, grupo ocupacional (CBO) e indicadores "
    f"de contexto agregados por unidade primária de amostragem (UPA, proxy de bairro) e por "
    f"unidade da federação (UF). Os dados são de acesso público; nenhum indivíduo é "
    f"identificável.")
sub("Modelos multiníveis: HLM e GLMM")
par("Estimaram-se modelos lineares hierárquicos (HLM) de dois níveis para o logaritmo do "
    "rendimento — indivíduos aninhados em UPA, com a UF como conjunto de efeitos fixos, já "
    "que 27 unidades são poucas para um terceiro nível aleatório —, em estratégia step-up "
    "que decompõe o gap agregado em mediação contextual e penalidade residual (Raudenbush; "
    "Bryk, 2002). O acesso a ocupações qualificadas e ao "
    "topo da distribuição de renda foi modelado por GLMM logístico (lme4::glmer, R), com "
    "efeito aleatório de UPA. A robustez dos achados foi avaliada por E-values (VanderWeele; "
    "Ding, 2017).")
sub("Decomposição e regressão quantílica")
par("A decomposição de Oaxaca-Blinder (Oaxaca, 1973; Blinder, 1973) separou o gap em "
    "componentes de dotações e de retornos. A regressão quantílica (Koenker; Bassett, 1978) "
    "avaliou a trajetória do gap ao longo da distribuição de rendimentos, caracterizando o "
    "teto de vidro.")
sub("Aprendizado de máquina e interpretabilidade")
par("Random Forest (Breiman, 2001) e XGBoost (Chen; Guestrin, 2016) foram ajustados para "
    "prever o rendimento, com interpretação por valores SHAP (Lundberg; Lee, 2017), "
    "quantificando a contribuição de cada variável e suas interações de forma "
    "não-paramétrica — uma camada de triangulação e robustez frente aos modelos "
    "econométricos.")
sub("Sensibilidade e interseccionalidade")
par("A robustez do resíduo racial foi avaliada por E-values (VanderWeele; Ding, 2017), que "
    "quantificam quanto um confundidor não-observado precisaria pesar para anular o efeito. A "
    "decomposição interseccional (raça × gênero) formaliza a penalidade específica da combinação "
    "dos eixos (Crenshaw, 1989), distinguindo-a da soma dos efeitos isolados.")

# ── Resultados Preliminares ───────────────────────────────────────────────────
secao("Resultados Preliminares")
par("Os resultados preliminares sustentam uma tese central: a desigualdade racial no mercado "
    "de trabalho brasileiro não é um evento pontual de contratação, mas um SISTEMA DE BARREIRAS "
    "EM CAMADAS — acesso, remuneração e interseccionalidade — com forte mediação do território, "
    "que persiste mesmo quando se controla a escolaridade. As subseções a seguir percorrem esse "
    "sistema: partem da falha da explicação meritocrática e isolam as três camadas que a "
    "substituem.")

sub("A falha da explicação meritocrática")
par(f"Se o rendimento fosse função apenas do capital humano, controlar escolaridade, "
    f"experiência e jornada deveria dissolver o gap racial — o que não ocorre. A decomposição "
    f"de Oaxaca-Blinder atribui {pa(g('OB_SEM_DOT_PCT'),0)}% do diferencial a diferenças "
    f"de dotações e {pa(g('OB_SEM_RET_PCT'),0)}% a retornos diferenciais. O ponto decisivo, "
    f"porém, está na COMPOSIÇÃO dessas dotações (Figura 1): os fatores que mais explicam o gap "
    f"não são educacionais, mas CONTEXTUAIS e OCUPACIONAIS — a proporção de negros na UPA e o "
    f"acesso a grupos ocupacionais de prestígio. As dotações não são, portanto, mérito neutro: "
    f"são o produto das barreiras que as subseções seguintes isolam. O capital humano explica "
    f"pouco; o que importa é onde se nasce e a que ocupações se tem acesso.")
figura("oaxaca_por_variavel.png",
       "Figura 1. Decomposição de Oaxaca-Blinder por variável: o gap vem sobretudo do contexto "
       "(proporção de negros na UPA) e da ocupação — não da escolaridade.", w=15)

sub("Camada 1 — A barreira de acesso e o teto de vidro")
par(f"A primeira camada é a exclusão da PORTA DE ENTRADA. O GLMM logístico multinível estima "
    f"que um trabalhador negro com a mesma escolaridade, sexo, idade, estado e bairro que um "
    f"branco tem {fmt((1 - g('OR_ocp_qualif_M2')) * 100, 0)}% menos chance de ocupar um cargo "
    f"qualificado (OR={or_str(g('OR_ocp_qualif_M2'))}; {ame(g('AME_ocp_qualif_M2'), 1)}). A "
    f"barreira não é uniforme ao longo da hierarquia: ela se agrava no topo (Figura 2) — o "
    f"odds ratio de acesso cai de {or_str(g('OR_y_top20_M2'))} no quintil superior de renda "
    f"para {or_str(g('OR_y_top10_M2'))} no decil superior. É um teto de vidro de ACESSO: "
    f"quanto mais valiosa a posição, mais opaco o filtro racial. O ICC de UPA no modelo nulo "
    f"de acesso ({pa(g('ICC_ocp_qualif_M1') * 100, 1)}%) já antecipa que essa barreira tem "
    f"raiz territorial — o fio que conecta as camadas.")
figura("glmm_glassceil_forest.png",
       "Figura 2. GLMM — odds ratios de acesso por desfecho: o gradiente decrescente rumo ao "
       "topo da renda caracteriza o teto de vidro de acesso (OR < 1 = barreira).", w=14)
tabela("Tabela 1. GLMM logístico (M2, população completa) — teto de vidro de acesso. "
       "OR < 1 = menor chance de acesso para negros vs. brancos de mesmo perfil; AME em pontos "
       "percentuais; E-value ≥ 2 indica robustez a confundidor não observado.",
       ["Desfecho", "OR (negro)", "AME (p.p.)", "E-value"],
       [["Cargo qualificado (CBO 1–4)"] + _glm_m2("ocp_qualif"),
        ["Top 20% de renda"] + _glm_m2("y_top20"),
        ["Top 10% de renda"] + _glm_m2("y_top10")])
par(f"Uma leitura interseccional (quatro grupos raça×gênero, referência = homem branco) revela uma "
    f"inversão. No ACESSO à categoria, a mulher negra é alçada (OR={fmt(g('GRG_MN_OCP_QUALIF'),2)}, "
    f"acima do homem branco, por profissões feminizadas em CBO 1–4) e o mais penalizado é o homem "
    f"negro (OR={fmt(g('GRG_HN_OCP_QUALIF'),2)}); mas no TOPO da renda o quadro inverte e a mulher negra "
    f"torna-se a MAIS excluída de todos (OR={fmt(g('GRG_MN_TOP10'),2)} no decil superior, abaixo "
    f"da mulher branca e do homem negro). A interação é sub-aditiva, mas o teto de vidro recai com "
    f"força máxima sobre a mulher negra (Figura 2b).")
figura("grupo_rg_interseccional.png",
       "Figura 2b. Interseccionalidade raça×gênero: a mulher negra é alçada no acesso à categoria, "
       "mas a mais excluída no topo da renda (OR vs. homem branco).", w=14)
par(f"Um indicador distribucional reforça o teto de vidro. O Gini da renda do trabalho é MAIOR entre "
    f"brancos ({fmt(g('GINI_BRANCO'),3)}) do que entre negros ({fmt(g('GINI_NEGRO'),3)}) "
    f"— em todos os anos da série. Isso não é equidade entre negros: é CONFINAMENTO AO PISO (renda "
    f"homogeneamente baixa), o reverso distribucional da barreira de acesso ao topo. Quem é barrado do "
    f"topo achata-se na base. Cabe a ressalva de que este Gini refere-se ao rendimento do TRABALHO entre "
    f"ocupados — conceito distinto do Gini domiciliar per capita do IBGE (Figura 2c).")
figura("gini_raca.png",
       "Figura 2c. Gini intra-raça (renda do trabalho, ponderado): brancos têm maior desigualdade "
       "interna; negros, comprimidos no piso — o reverso do teto de vidro, não equidade.", w=13)

sub("Camada 2 — O território como eixo da desigualdade")
par("Por que as dotações são desiguais? A segunda camada responde: em parte, pelo LUGAR. No "
    "modelo hierárquico, mais da metade do gap salarial é mediada pelo contexto de moradia "
    "(UPA) — um achado robusto de mediação. A raça opera, em medida relevante, ATRAVÉS do "
    "território: a segregação residencial histórica converte-se em segregação de renda atual. "
    "Ressalva metodológica: a renda média da UPA é preditor parcialmente endógeno do rendimento "
    "individual (problema do reflexo, Manski 1993), pois agrega o próprio indivíduo; por isso a "
    "interpretamos como evidência de mediação territorial, e não como 'determinante' causal "
    "isolado. É esse eixo territorial que dá unidade às demais camadas.")
figura("shap_importance_xgb.png",
       f"Figura 3. Importância SHAP (XGBoost, R² de teste {fmt(g('ML_XGB_R2'), 3)}): o contexto territorial (renda média da "
       "UPA) está entre os preditores de maior peso, sinalizando o eixo territorial da "
       "desigualdade — interpretado como mediação, não como determinante causal isolado.", w=14)
par("Esse eixo territorial encontra corroboração externa no Índice de Progresso Social (IPS) municipal "
    "(Imazon e parceiros, 2026): as regiões de menor progresso social (Norte e Nordeste) coincidem com "
    "as de maior penalidade racial em nossos modelos. Ressalva metodológica: a integração fina com o "
    "proxy de bairro (UPA) é inviável — a PNAD não divulga o município e o IPS é municipal, mais "
    "agregado que a UPA —, de modo que o IPS entra como evidência convergente do caráter territorial, "
    "não como fonte de dados integrada.")
tabela(f"Tabela 2. Decomposição do gap por mediação (HLM de dois níveis — indivíduos em UPA, "
       f"com efeitos fixos de UF; PNAD Contínua 2016–2025, população completa). Cada modelo "
       f"acrescenta controles ao anterior; o gap encolhe de {pa(g('GAP_POOL'))}% (agregado) "
       f"para {pa(g('GAP_M4'))}% (M4), com {pa(g('MED_ACUM_M4'))}% mediado por contexto de "
       f"moradia e ocupação.",
       ["Modelo (controles acumulados)", "β negro", "Gap (%)", "Mediação acum. (%)"],
       _med_rows)
tabela("Tabela 3. Decomposição de Oaxaca-Blinder em duas especificações (população completa; "
       "erros-padrão por bootstrap em blocos de UPA). Dotações + Retornos = 100% do gap. "
       "(A) trata apenas capital humano e contexto como dotações; (B) acrescenta ocupação, "
       "formalidade e jornada. Ressalva (Oaxaca & Ransom, 1999): incluir a ocupação como "
       "dotação subestima a discriminação, pois a segregação ocupacional é ela própria "
       "discriminatória — daí a complementaridade com o GLMM de acesso (Tabela 1).",
       ["Componente", "(A) sem ocupação (%)", "(B) com ocupação (%)"],
       _oba_rows)

sub("Camada 3 — A penalidade interseccional")
par(f"As duas primeiras camadas — acesso e território — combinam-se de forma agravada na "
    f"interseção de raça e gênero. A decomposição interseccional mostra que a Mulher Negra "
    f"acumula a maior desvantagem (gap de {pa(g('INT_MULHER_NEGRA_GAP'))}% vs. o Homem "
    f"Branco) e, além disso, uma penalidade EXTRA de {pa(g('INT_PENAL_EXTRA'))} pontos "
    f"percentuais que não se reduz à soma das penalidades de raça e de gênero isoladas — a "
    f"marca da interseccionalidade (Crenshaw, 1989). A interação é sub-aditiva: o efeito "
    f"próprio da combinação existe e é menor que o dobro das penalidades isoladas. As "
    f"camadas reforçam-se mutuamente: a barreira de acesso e o eixo territorial pesam de "
    f"modo desigual sobre os diferentes grupos.")
tabela(f"Tabela 4. Decomposição interseccional (raça × gênero) do gap vs. o Homem Branco "
       f"(população completa; erro-padrão por bootstrap em blocos de UPA). Dotações + "
       f"Retornos = 100% do gap. A Mulher Negra acumula o maior gap "
       f"({pa(g('INT_MULHER_NEGRA_GAP'))}%) e uma penalidade extra de "
       f"{pa(g('INT_PENAL_EXTRA'))} p.p. não redutível à soma dos eixos de raça e gênero "
       f"(Crenshaw, 1989).",
       ["Grupo", "Gap vs HB (%)", "Dotações (%)", "Retornos (%)", "Penal. extra (p.p.)"],
       _itx_rows)
figura("grupo_rg_interseccional.png",
       "Figura 4. Decomposição interseccional (raça × gênero): gap de renda vs. o Homem Branco; "
       "a Mulher Negra acumula as duas penalidades, com um resíduo interseccional próprio.", w=13)

# ── Considerações preliminares ────────────────────────────────────────────────
secao("Limitações e escopo de validade")
par("Natureza inferencial vs. preditiva. Os modelos HLM, Oaxaca-Blinder, regressão quantílica e "
    "o GLMM logístico de acesso produzem estimativas de ASSOCIAÇÃO CONDICIONAL — o diferencial racial que "
    "persiste sob controle de observáveis —, e não prova causal contrafactual. O XGBoost e os "
    "valores SHAP têm finalidade PREDITIVA e interpretativa: medem a contribuição de cada variável "
    "para a previsão do rendimento, não o efeito causal de manipulá-la. A linguagem causal foi "
    "deliberadamente evitada.")
par("Cobertura da escolaridade. A escolaridade detalhada está registrada para cerca de 31% da PEA "
    "no painel público; os níveis entram como dummies de conclusão acompanhadas de um indicador "
    "explícito de não-registro (educ_missing), de modo que a categoria-base não confunda baixa "
    "escolaridade com dado ausente. O coeficiente racial é estável a essa especificação (variação "
    "inferior a 1%).")
par(f"Especificação da decomposição de Oaxaca-Blinder. A repartição entre composição e "
    f"discriminação depende de quais controles se tratam como dotações, e por isso as duas "
    f"especificações são reportadas lado a lado: sem a ocupação, a parcela não explicada é "
    f"{pa(g('OB_SEM_RET_PCT'))}%; com ela, {pa(g('OB_COM_RET_PCT'))}%. Como alerta Oaxaca e "
    f"Ransom (1999), tratar a ocupação como dotação tende a subestimar a discriminação total, "
    f"já que a segregação ocupacional é, ela própria, discriminatória — a segunda leitura é, "
    f"portanto, um limite inferior descritivo, e daí a complementaridade com o GLMM de acesso.")
par("Bad controls. Pelo mesmo motivo, ocupação, formalidade e jornada são desfechos da "
    "própria discriminação (Angrist; Pischke, 2009, cap. 3). Os modelos que os incluem (M4 e "
    "a especificação B) são apresentados como limite inferior; os que não os incluem (M3 e a "
    "especificação A), como o gap condicional a capital humano e bairro.")
par("Condicionamento em rendimento positivo. Todos os modelos de rendimento são estimados "
    "entre ocupados com renda positiva, o que é condicionar no desfecho. A direção provável "
    "do viés é de subestimação, caso os trabalhadores negros que permanecem ocupados sejam "
    "positivamente selecionados em atributos não observados; o GLMM de acesso trata "
    "diretamente a outra metade do problema.")
par("Inferência. Como a PNAD amostra por conglomerados, todos os modelos reportam erro-padrão "
    "agrupado por UPA ou modelam o bairro como efeito aleatório; as decomposições usam "
    "bootstrap em blocos de UPA. No agrupamento por UF, com 27 clusters, usa-se t com G−1 "
    "graus de liberdade. As estimativas são não ponderadas — descrevem a regressão na "
    "amostra —, e a robustez ponderada pelo peso V1028 altera o gap em menos de meio ponto "
    "percentual.")

secao("Considerações Preliminares")
par(f"Tomados em conjunto, os resultados convergem para a tese central: a desigualdade racial "
    f"no trabalho brasileiro é um SISTEMA DE BARREIRAS EM CAMADAS — acesso, remuneração e "
    f"interseccionalidade — com forte mediação do TERRITÓRIO: o contexto de moradia responde "
    f"por {pa(g('MED_BAIRRO'))}% do gap agregado. Boa parte do diferencial é composição "
    f"(Oaxaca-Blinder: {pa(g('OB_SEM_DOT_PCT'))}% de dotações na especificação sem ocupação), "
    f"mas a composição é ela mesma produto da discriminação no acesso às ocupações (GLMM: "
    f"OR={or_str(g('OR_ocp_qualif_M2'))}, com gradiente até "
    f"{or_str(g('OR_y_top10_M2'))} no decil superior) e convive com penalidade salarial "
    f"que persiste sob controle exaustivo — {pa(g('GAP_M3'))}% de gap líquido e "
    f"{pa(g('GAP_M4'))}% dentro da mesma ocupação — maior na base da distribuição em termos "
    f"de retornos (sticky floor). A consequência prescritiva é direta: políticas "
    f"unidimensionais são insuficientes; a intervenção deve ser multidimensional e centrada "
    f"no acesso a ocupações qualificadas. As próximas etapas incluem o refinamento das "
    f"análises de robustez e a consolidação das recomendações.")

# ── Referências ───────────────────────────────────────────────────────────────
secao("Referências")
refs = [
    "BLINDER, A. S. Wage discrimination: reduced form and structural estimates. Journal of Human Resources, v. 8, n. 4, p. 436-455, 1973.",
    "BREIMAN, L. Random forests. Machine Learning, v. 45, n. 1, p. 5-32, 2001.",
    "CHEN, T.; GUESTRIN, C. XGBoost: a scalable tree boosting system. In: KDD, 2016. p. 785-794.",
    "CRENSHAW, K. Demarginalizing the intersection of race and sex. University of Chicago Legal Forum, v. 1989, n. 1, p. 139-167, 1989.",
    "FIRPO, S.; FORTIN, N. M.; LEMIEUX, T. Decomposing wage distributions using recentered influence function regressions. Econometrics, v. 6, n. 2, p. 28, 2018.",
    "HASENBALG, C. Discriminação e desigualdades raciais no Brasil. Rio de Janeiro: Graal, 1979.",
    "HENRIQUES, R. Desigualdade racial no Brasil: evolução das condições de vida na década de 90. Rio de Janeiro: IPEA, 2001. (Texto para discussão, 807).",
    "INSTITUTO BRASILEIRO DE GEOGRAFIA E ESTATÍSTICA (IBGE). Pesquisa Nacional por Amostra de Domicílios Contínua. Rio de Janeiro: IBGE, 2016-2025.",
    "INSTITUTO BRASILEIRO DE GEOGRAFIA E ESTATÍSTICA (IBGE). Pesquisa de Orçamentos Familiares 2017-2018: análise da qualidade de vida. Rio de Janeiro: IBGE, 2019.",
    "INSTITUTO BRASILEIRO DE GEOGRAFIA E ESTATÍSTICA (IBGE). PNAD Contínua: Rendimento de Todas as Fontes 2025. Rio de Janeiro: IBGE, 2025.",
    "KOENKER, R.; BASSETT, G. Regression quantiles. Econometrica, v. 46, n. 1, p. 33-50, 1978.",
    "LUNDBERG, S. M.; LEE, S. A unified approach to interpreting model predictions. In: NeurIPS, 2017. p. 4765-4774.",
    "OAXACA, R. Male-female wage differentials in urban labor markets. International Economic Review, v. 14, n. 3, p. 693-709, 1973.",
    "OAXACA, R. L.; RANSOM, M. R. Identification in detailed wage decompositions. Review of Economics and Statistics, v. 81, n. 1, p. 154-157, 1999.",
    "PAGER, D. Marked: race, crime, and finding work in an era of mass incarceration. Chicago: University of Chicago Press, 2007.",
    "RAUDENBUSH, S. W.; BRYK, A. S. Hierarchical linear models: applications and data analysis methods. 2. ed. Thousand Oaks: Sage, 2002.",
    "SAMPSON, R. J.; RAUDENBUSH, S. W.; EARLS, F. Neighborhoods and violent crime. Science, v. 277, p. 918-924, 1997.",
    "SOARES, S. S. D. Perfil da discriminação no mercado de trabalho: raça, sexo e salários no Brasil 1992-2006. Rio de Janeiro: IPEA, 2009. (Texto para discussão, 1395).",
    "VANDERWEELE, T. J.; DING, P. Sensitivity analysis in observational research: introducing the E-value. Annals of Internal Medicine, v. 167, n. 4, p. 268-274, 2017.",
    "WILSON, W. J. The truly disadvantaged: the inner city, the underclass, and public policy. Chicago: University of Chicago Press, 1987.",
]
for r in sorted(refs):
    p = doc.add_paragraph(r); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(6); p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    for run in p.runs: run.font.size = Pt(11)

secao("Declaração de uso de inteligência artificial")
par("Na elaboração deste trabalho foram utilizadas ferramentas de inteligência artificial "
    "(Claude Code, da Anthropic) como apoio à implementação e depuração de código (Python e R), à "
    "geração de figuras e tabelas e à formatação dos documentos. A concepção da pesquisa, a escolha "
    "das metodologias, a interpretação dos resultados e a redação final são de responsabilidade do "
    "autor, que revisou, validou e responde por todo o conteúdo.")

doc.save(str(OUT))
print(f"Arquivo gerado: {OUT.name}")
print(f"Tamanho: {OUT.stat().st_size // 1024} KB")
