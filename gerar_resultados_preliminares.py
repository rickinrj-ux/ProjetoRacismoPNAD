"""
gerar_resultados_preliminares.py
================================
Monta o documento de RESULTADOS PRELIMINARES no modelo MBA USP/Esalq
(Template Resultados Preliminares_PT), puxando todos os números de params.py
(fonte única de verdade). Estrutura: Título, Autores, Resumo, Palavras-chave,
Introdução, Material e Métodos, Resultados Preliminares, Considerações,
Referências. Formatação: Times New Roman 12, espaçamento 1,5, justificado,
títulos de seção em negrito e alinhados à esquerda. Sem os textos de instrução.

Saída: Resultados_Preliminares_TCC.docx
"""
import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from params import P, fmt, fmtN, or_str, ame

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).parent
FIG  = ROOT / "outputs" / "figures"
OUT  = ROOT / "Resultados_Preliminares_TCC.docx"

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


# ── Cabeçalho ─────────────────────────────────────────────────────────────────
titulo("A desigualdade racial no mercado de trabalho brasileiro é estrutural, "
       "contextual e geograficamente heterogênea")
doc.add_paragraph()
centro("Ricardo Calheiros¹*; [Nome completo do(a) orientador(a)]²", size=12)
centro("¹* MBA em Data Science e Analytics, USP/Esalq. E-mail: rickinrj@gmail.com", size=10)
centro("² Titulação. Instituição (opcional). E-mail: orientador@email.com", size=10)
doc.add_paragraph()

# ── Resumo ────────────────────────────────────────────────────────────────────
secao("Resumo")
par(f"A desigualdade racial no mercado de trabalho brasileiro foi investigada com a PNAD "
    f"Contínua (2016–2025; {fmtN(int(g('N_GLMM',7694198)))} observações da população "
    f"economicamente ativa), integrando econometria multinível, aprendizado de máquina, "
    f"análise de redes e pesquisa operacional. Os resultados preliminares indicam que a "
    f"discriminação opera em camadas: uma barreira de acesso a ocupações qualificadas "
    f"(GLMM logístico, OR={or_str(g('OR_M2',0.69))}), uma penalidade salarial residual e um "
    f"teto de vidro que se agrava no topo da distribuição (OR de acesso ao decil superior "
    f"= {or_str(g('OR_TOP10_M1',0.45))}). Mais de metade do diferencial salarial é mediada "
    f"pelo contexto de moradia (UPA), e modelos de inclinação aleatória mostram que tanto a "
    f"penalidade de acesso quanto a salarial variam significativamente entre os estados. A "
    f"pesquisa operacional traduz o diagnóstico em priorização de políticas, com ganho de "
    f"focalização territorial.")
kv("Palavras-chave: ", "gap salarial racial; modelos hierárquicos; teto de vidro; "
   "segregação residencial; pesquisa operacional.")

# ── Introdução ────────────────────────────────────────────────────────────────
secao("Introdução")
par("A persistência da desigualdade racial no mercado de trabalho brasileiro é um dos "
    "fenômenos mais documentados das ciências sociais nacionais, desde a tese do "
    "preconceito estrutural de Hasenbalg (1979) até as decomposições contemporâneas do "
    "rendimento (Henriques, 2001; Soares, 2009). Apesar do avanço educacional das últimas "
    "décadas, trabalhadores negros seguem auferindo rendimentos inferiores e ocupando, em "
    "menor proporção, as posições de maior prestígio e remuneração — um padrão que a "
    "explicação meritocrática, baseada apenas em capital humano, não dá conta de prever.")
par("A literatura internacional sugere que a discriminação não é um evento único na "
    "contratação, mas um sistema de barreiras que se reforçam: exclusão de acesso a "
    "ocupações qualificadas (Pager, 2007), efeitos de vizinhança e segregação residencial "
    "(Wilson, 1987; Sampson, 1997) e exclusão das redes sociais que convertem credenciais "
    "em oportunidades (Granovetter, 1973; Burt, 2004). Tratados isoladamente, esses "
    "mecanismos têm sido difíceis de quantificar de forma integrada e em escala nacional.")
par("Este trabalho enfrenta essa lacuna combinando, sobre a série completa da PNAD "
    "Contínua, modelos lineares hierárquicos (HLM), modelos logísticos multiníveis (GLMM), "
    "decomposição de Oaxaca-Blinder, regressão quantílica, aprendizado de máquina com "
    "valores SHAP, análise de redes sociais (SNA) e pesquisa operacional. A convergência "
    "de métodos independentes sobre o mesmo conjunto de dados permite distinguir os "
    "mecanismos da desigualdade e testar sua robustez.")
par("O objetivo deste trabalho é identificar, isolar e quantificar os mecanismos da "
    "desigualdade racial de rendimentos e de acesso ocupacional no Brasil, avaliando sua "
    "heterogeneidade geográfica e setorial e traduzindo o diagnóstico em recomendações de "
    "política priorizadas por métodos de pesquisa operacional.")

# ── Material e Métodos ────────────────────────────────────────────────────────
secao("Material e Métodos")
sub("Base de dados")
par(f"Utilizou-se a Pesquisa Nacional por Amostra de Domicílios Contínua (PNAD Contínua/"
    f"IBGE), série completa de 2016 a 2025, totalizando {fmtN(int(g('N_GLMM',7694198)))} "
    f"observações da população economicamente ativa com rendimento positivo após o "
    f"tratamento dos dados. As variáveis incluíram raça (preto/pardo agregados em 'negro'), "
    f"gênero, idade, escolaridade, jornada, vínculo, grupo ocupacional (CBO) e indicadores "
    f"de contexto agregados por unidade primária de amostragem (UPA, proxy de bairro) e por "
    f"unidade da federação (UF). Os dados são de acesso público; nenhum indivíduo é "
    f"identificável.")
sub("Modelos multiníveis: HLM e GLMM")
par("Estimaram-se modelos lineares hierárquicos (HLM) para o logaritmo do rendimento, com "
    "efeitos aleatórios de UPA e UF, decompondo o gap bruto em mediação contextual e "
    "penalidade residual (Raudenbush; Bryk, 2002). O acesso a ocupações qualificadas e ao "
    "topo da distribuição de renda foi modelado por GLMM logístico (lme4::glmer, R), com "
    "efeito aleatório de UPA. Modelos de inclinação aleatória (random slope) de raça e de "
    "gênero por UF testaram a heterogeneidade geográfica do efeito (teste de fronteira de "
    "Stram e Lee, 1994), estimados também separadamente para os setores público e privado.")
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
sub("Redes sociais e pesquisa operacional")
par("A análise de redes sociais (SNA) modelou a co-presença ocupacional como grafo, "
    "medindo isolamento estrutural (constraint de Burt) e capacidade de corretagem "
    "(betweenness) por grupo. Por fim, a pesquisa operacional (TOPSIS, AHP e programação "
    "linear; Saaty, 1980; Hwang; Yoon, 1981) traduziu os coeficientes confirmados em "
    "priorização e alocação ótima de políticas, inclusive em versão regionalizada por UF.")

# ── Resultados Preliminares ───────────────────────────────────────────────────
secao("Resultados Preliminares")
sub("Gap salarial e mediação contextual")
par(f"O diferencial salarial racial bruto é expressivo e, no modelo hierárquico, mais da "
    f"metade dele é mediada pelo contexto de moradia (UPA): a renda média do bairro é o "
    f"determinante individual mais forte do rendimento — acima da própria escolaridade. A "
    f"decomposição de Oaxaca-Blinder atribui cerca de {pa(g('DOT_PCT',83.5),0)}% do gap a "
    f"diferenças de dotações e {pa(g('RET_PCT',16.5),0)}% a retornos diferenciais; contudo, "
    f"as dotações são, elas próprias, produto das barreiras de acesso e da segregação "
    f"territorial. O ICC de UF no modelo nulo de salário é de {pa(g('ICC_HLM_M0_pct',9.83),1)}%.")
sub("Barreira de acesso e teto de vidro")
par(f"O GLMM logístico confirma uma barreira de acesso a ocupações qualificadas: a chance "
    f"de um trabalhador negro ocupar cargos qualificados é cerca de "
    f"{fmt(round((1-g('OR_M2',0.69))*100),0)}% menor que a de um branco idêntico "
    f"(OR={or_str(g('OR_M2',0.69))}; {ame(g('AME_M2_pp',-4.84))}). O teto de vidro se "
    f"intensifica no topo: o odds ratio de acesso cai de {or_str(g('OR_TOP20_M1',0.536))} "
    f"(quintil superior de renda) para {or_str(g('OR_TOP10_M1',0.4533))} (decil superior) — "
    f"a barreira é mais alta exatamente onde os prêmios são maiores. O ICC de UPA no GLMM é "
    f"de {pa(g('ICC_M1_pct',22.2),1)}%, sinalizando forte componente territorial do acesso.")
figura("glmm_rs_real.png",
       "Figura 1. Random slope do GLMM (lme4): odds ratio de 'negro' por UF em cada desfecho "
       "de acesso; a dispersão entre estados indica heterogeneidade geográfica.", w=16)
sub("Heterogeneidade geográfica e contraste setorial")
par(f"Os modelos de inclinação aleatória rejeitam a hipótese de efeito homogêneo entre "
    f"estados (p<0,001), tanto para o salário quanto para o acesso: a discriminação é "
    f"geograficamente heterogênea. No salário, o gap racial entre UFs varia "
    f"aproximadamente de {pa(g('RS_GAP_LO_PCT',-19.8),1)}% a {pa(g('RS_GAP_HI_PCT',-2.2),1)}%. "
    f"Um achado relevante emerge do contraste por setor: o setor público ATENUA o gap "
    f"salarial racial ({pa(g('HRS_PUB_GAP_PCT',-7.8),1)}% no público contra "
    f"{pa(g('HRS_PRIV_GAP_PCT',-11.2),1)}% no privado) e o homogeneíza entre estados; "
    f"porém, no ACESSO a ocupações qualificadas, o setor público não atenua a barreira "
    f"(OR={or_str(g('GRS_PUB_OR',0.705))} no público contra {or_str(g('GRS_PRIV_OR',0.695))} "
    f"no privado). Ou seja, o concurso público equaliza a remuneração de quem entra, mas não "
    f"a entrada.")
figura("mapa_po_regional.png",
       "Figura 2. Penalidade salarial racial por estado (BLUP do random slope): mais escuro = "
       "maior desvantagem; estrelas indicam UFs prioritárias para focalização.", w=11)
sub("Gênero e interseccionalidade")
par(f"A extensão da inclinação aleatória ao gênero revela um padrão distinto do racial: "
    f"mulheres têm MAIOR acesso a 'ocupações qualificadas' (OR={fmt(g('GGE_OCP_OR',2.01),2)}), "
    f"por concentração em profissões credenciadas feminizadas, mas MENOR acesso ao topo da "
    f"renda (OR no decil superior = {or_str(g('GGE_TOP10_OR',0.522))}). O teto de vidro de "
    f"gênero é, portanto, de remuneração, não de categoria ocupacional, e sua "
    f"heterogeneidade geográfica supera a racial (desvio-padrão entre UFs de "
    f"{fmt(g('HRS_GEN_SD_SEXO',0.064),3)} para gênero contra {fmt(g('HRS_GEN_SD_NEGRO',0.05),3)} "
    f"para raça). A correlação negativa entre as duas heterogeneidades "
    f"(ρ={fmt(g('HRS_GEN_RHO',-0.46),2)}) sugere que, nas UFs de maior penalidade racial, a "
    f"de gênero tende a ser menor.")
sub("Aprendizado de máquina, redes e pesquisa operacional")
par(f"Os modelos de aprendizado de máquina (XGBoost, R²≈0,62) corroboram, de forma "
    f"não-paramétrica, o diagnóstico: o preditor mais importante do rendimento (SHAP) é a "
    f"renda média do bairro, acima da escolaridade — a raça atua sobretudo por meio dos "
    f"mediadores estruturais, o que é coerente com a decomposição de Oaxaca-Blinder. A SNA "
    f"mostra isolamento estrutural dos grupos negros nas redes profissionais. A pesquisa "
    f"operacional ranqueia 'cotas ocupacionais (CBO 1–4)' como intervenção dominante "
    f"(TOPSIS CC={fmt(g('TOPSIS_P1_CC',0.83),3)}), e a versão regionalizada mostra que "
    f"focalizar o orçamento nas UFs de maior penalidade (lideradas por "
    f"{g('RPO_WORST_UF','DF')}, {pa(g('RPO_WORST_GAP_PCT',-20.9),1)}%) rende até "
    f"{pa(g('RPO_GANHO_B9',68.2),0)}% mais redução do gap do que a alocação uniforme.")

# ── Considerações preliminares ────────────────────────────────────────────────
secao("Considerações Preliminares")
par("Os resultados parciais sustentam que a desigualdade racial no trabalho brasileiro é um "
    "fenômeno estrutural, multicausal e territorialmente desigual, que opera em pelo menos "
    "duas etapas independentes — acesso e remuneração — e que não é dissolvido "
    "espontaneamente nem integralmente pela ação do Estado. As próximas etapas incluem o "
    "refinamento das análises de robustez e a consolidação das recomendações de política.")

# ── Referências ───────────────────────────────────────────────────────────────
secao("Referências")
refs = [
    "BLINDER, A. S. Wage discrimination: reduced form and structural estimates. Journal of Human Resources, v. 8, n. 4, p. 436-455, 1973.",
    "BREIMAN, L. Random forests. Machine Learning, v. 45, n. 1, p. 5-32, 2001.",
    "BURT, R. S. Structural holes and good ideas. American Journal of Sociology, v. 110, n. 2, p. 349-399, 2004.",
    "CHEN, T.; GUESTRIN, C. XGBoost: a scalable tree boosting system. In: KDD, 2016. p. 785-794.",
    "GRANOVETTER, M. The strength of weak ties. American Journal of Sociology, v. 78, n. 6, p. 1360-1380, 1973.",
    "HASENBALG, C. Discriminação e desigualdades raciais no Brasil. Rio de Janeiro: Graal, 1979.",
    "HENRIQUES, R. Desigualdade racial no Brasil: evolução das condições de vida na década de 90. Rio de Janeiro: IPEA, 2001. (Texto para discussão, 807).",
    "HWANG, C. L.; YOON, K. Multiple attribute decision making: methods and applications. Berlin: Springer, 1981.",
    "INSTITUTO BRASILEIRO DE GEOGRAFIA E ESTATÍSTICA (IBGE). Pesquisa Nacional por Amostra de Domicílios Contínua. Rio de Janeiro: IBGE, 2016-2025.",
    "KOENKER, R.; BASSETT, G. Regression quantiles. Econometrica, v. 46, n. 1, p. 33-50, 1978.",
    "LUNDBERG, S. M.; LEE, S. A unified approach to interpreting model predictions. In: NeurIPS, 2017. p. 4765-4774.",
    "OAXACA, R. Male-female wage differentials in urban labor markets. International Economic Review, v. 14, n. 3, p. 693-709, 1973.",
    "PAGER, D. Marked: race, crime, and finding work in an era of mass incarceration. Chicago: University of Chicago Press, 2007.",
    "RAUDENBUSH, S. W.; BRYK, A. S. Hierarchical linear models: applications and data analysis methods. 2. ed. Thousand Oaks: Sage, 2002.",
    "SAATY, T. L. The analytic hierarchy process. New York: McGraw-Hill, 1980.",
    "SAMPSON, R. J.; RAUDENBUSH, S. W.; EARLS, F. Neighborhoods and violent crime. Science, v. 277, p. 918-924, 1997.",
    "SOARES, S. S. D. Perfil da discriminação no mercado de trabalho: raça, sexo e salários no Brasil 1992-2006. Rio de Janeiro: IPEA, 2009. (Texto para discussão, 1395).",
    "STRAM, D. O.; LEE, J. W. Variance components testing in the longitudinal mixed effects model. Biometrics, v. 50, n. 4, p. 1171-1177, 1994.",
    "WILSON, W. J. The truly disadvantaged: the inner city, the underclass, and public policy. Chicago: University of Chicago Press, 1987.",
]
for r in sorted(refs):
    p = doc.add_paragraph(r); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(6); p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    for run in p.runs: run.font.size = Pt(11)

doc.save(str(OUT))
print(f"Arquivo gerado: {OUT.name}")
print(f"Tamanho: {OUT.stat().st_size // 1024} KB")
