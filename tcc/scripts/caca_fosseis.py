"""
caca_fosseis.py — procura números escritos à mão ("fósseis") nos geradores dos entregáveis.

Um número fóssil é um resultado digitado no texto de um gerador em vez de lido de
params_nucleo / csv: fica certo até a próxima reestimação e depois mente sem avisar.
Foi assim que "35,1%", "96,4%" e "40.120 UPAs" sobreviveram à correção do vazamento.

O script percorre os literais de string de cada gerador (com tokenize, para não
confundir código com texto), descarta o que está dentro de {…} das f-strings — isso é
lido de parâmetro — e acusa todo número que sobrar no texto. Anos, numeração de
seções/equações, códigos CBO e similares entram na lista de exceções abaixo.

Uso:
    python tcc/scripts/caca_fosseis.py            # relatório; código 1 se houver fóssil
    python tcc/scripts/caca_fosseis.py --todos    # mostra também os ignorados
"""
import io
import re
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Geradores que produzem entregáveis (README de entregaveis/_arquivo e run_tcc.ps1)
GERADORES = [
    "scripts/geradores/gerar_relatorio_tcc.py",
    "tcc/scripts/gerar_relatorio_enxuto.py",
    "tcc/scripts/enxuto_patches.py",
    "tcc/scripts/gerar_tcc_normas.py",
    "tcc/scripts/tcc_normas_texto.py",
    "tcc/scripts/gerar_tcc_normas_docx.py",
    "tcc/scripts/gerar_word_enxuto.py",
    "tcc/scripts/gerar_guia_estudo.py",
    "tcc/scripts/gerar_apresentacao_executiva.py",
    "scripts/geradores/gerar_apresentacao_pptx.py",
    "tcc/scripts/gerar_narrativa_social.py",
    "tcc/scripts/gerar_tabela_glmm.py",
    "tcc/scripts/gerar_tabela_oaxaca.py",
    "tcc/scripts/gerar_tabela_mediacao.py",
    "tcc/scripts/gerar_tabela_interseccional.py",
    "tcc/scripts/gerar_tabela_robustez.py",
    "tcc/scripts/gerar_tabela_balanceamento.py",
    "tcc/scripts/gerar_tabela_cv.py",
    "tcc/scripts/corrigir_tabela_rif.py",
    "tcc/scripts/gerar_figuras_nucleo.py",
    "tcc/scripts/gerar_figura_interseccional.py",
]

# Número "de resultado": decimal com vírgula (ou {,}), milhar com ponto, ou seguido de %
NUM = re.compile(r"(?<![\w@])(\d{1,3}(?:\.\d{3})+|\d+(?:\{?,\}?\d+)?)(\s*\\?%|\s*p\.?p\.?|\s*pp\b|×)?")

# Contextos que não são resultado: anos, intervalos de anos, referências bibliográficas,
# numeração de seção/tabela/equação/slide, CBO 1-4, quantis q10..q95, níveis, dimensões.
IGNORA_CTX = re.compile(
    r"(19|20)\d{2}"                       # anos
    r"|\bq\d{2}\b|\bQ\d{2}\b|\\tau|τ"     # rótulos de quantil
    r"|CBO|ISCO|V\d{4}|VD\d{4}"           # códigos de variável
    r"|\b(M|A)\d\b|nível|Nível|degrau"    # nomes de modelo/nível
    r"|\\(section|subsection|ref|label|cite|includegraphics|hspace|vspace|setlength|"
    r"textwidth|linewidth|cm|pt|em)\b"
    r"|In\(|Pt\(|Inches|RGBColor|font|width|height|figsize|dpi|fontsize|zorder|alpha"
    r"|[Tt]op[~ ]?\d+|decil|quintil"      # rótulos de desfecho: "top 10%", "top~20\%"
)

INTEIROS_LIVRES = {"0", "1", "2", "3", "4", "5", "10", "100"}   # contagens e numeração triviais

# Parâmetros de DESENHO (escolhas de método, não resultados): não mudam com a reestimação.
# Cada entrada é um padrão que precisa casar na vizinhança do número.
DESENHO = [
    r"SHAP[^\d]{0,20}50[.]000|subsample de 50[.]000|50[.]000 observa|50 mil observações sorteadas|em 50 mil casos do treino",      # amostra do SHAP
    r"200[.]000",                                                          # subamostra do VIF
    r"treino[~ ]?80|80\\?%[^\d]{0,12}(treino|para treino)|teste[~ ]?20|[Hh]old-out\}? 20|subamostra de 20|20\\?% para teste",
    r"0\{?,\}?10;\\? ?0\{?,\}?25;|0\{?,\}?50;\\? ?0\{?,\}?75;|0\{?,\}?75;\\? ?0\{?,\}?90",  # τ da QR
    r"lr\}?=0,05|\\textlr|taxa de aprendizado|learning",                    # hiperparâmetro
    r"limiar de 5|acima de 5\\?% justific|> ?0,05\$ justific|rho_UF > 0,05",  # limiar do ICC
    r"\b10 decis|200 reps|200 réplicas|1:1,5",                              # HL, bootstrap, IBGE
    r"(?:reserva|Reserva aos negros) 20\\{0,2}% das\s+vagas|Lei 12[.]990",                         # lei de cotas
    r"profund|n_estimators|iterações",                                     # hiperparâmetros
    r"DeclareUnicodeCharacter|âncora \d{4}",                               # códigos Unicode
    r"Arial \d|palavras|\d cm\b|entrelinha|ajustes|\(251, 252\)",          # normas de formatação
    r"95\\{0,2}% CI|IC 95|95\\{0,2}% com erro",                             # convenção de IC
    r"volume|pages|number|year",                                           # bibliografia
    r"(?:Lei|Decreto) n\. \d",                                             # legislação no .bib
    r"\\\*\{",                                                             # quantificador de regex
    r"& 100,0|Total",                                                      # linha de total = 100
    # fatos EXTERNOS citados (IBGE, literatura), não estimados neste trabalho
    r"citeibge|IBGE|Nordeste|Norte \(|Sul \(|Vida recuou|mais ricos|mais pobr|munic[íi]pios"
    r"|de 2006|capita de|U\+2212|qualidade de vida|índice de 0",
    # texto da versão estendida que o enxuto remove (conferido: não chega a entregável;
    # conferir_numeros_entregaveis.py acusaria se voltasse)
    r"2,5 vezes mai|771[.]756|homofilia",
    r"mant[êe]m [íi]ndice",                                                # IPQV do IBGE (externo)
]


def _linhas_docstring(src):
    """Linhas onde começam docstrings (módulo, classe, função): não chegam a entregável."""
    import ast
    linhas = set()
    for no in ast.walk(ast.parse(src)):
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            corpo = getattr(no, "body", [])
            if corpo and isinstance(corpo[0], ast.Expr) and isinstance(getattr(corpo[0], "value", None), ast.Constant) \
                    and isinstance(corpo[0].value.value, str):
                linhas.add(corpo[0].lineno)
    return linhas


def _linhas_ancora(src):
    """Linhas onde começam padrões de busca (âncoras), que procuram o texto antigo para
    trocá-lo e não chegam ao entregável. Regra estrutural, não heurística: a versão
    anterior adivinhava pelo conteúdo e classificava texto LaTeX como regex, deixando
    passar um "7{,}7 milhões" de saída.
      · 1º argumento de re.sub/subn/search/match/findall/finditer/compile e de flex();
      · 2º elemento das tuplas da lista PATCHES (nome, padrão, substituto, flags)."""
    import ast
    linhas = set()

    def _strings(no):
        return [n.lineno for n in ast.walk(no)
                if isinstance(n, ast.JoinedStr) or (isinstance(n, ast.Constant) and isinstance(n.value, str))]

    for no in ast.walk(ast.parse(src)):
        if isinstance(no, ast.Call) and no.args:
            f = no.func
            nome = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if nome in ("sub", "subn", "search", "match", "findall", "finditer", "compile",
                        "fullmatch", "split", "flex"):
                linhas.update(_strings(no.args[0]))
        if isinstance(no, ast.Assign) and any(getattr(t, "id", "") == "PATCHES" for t in no.targets):
            for el in getattr(no.value, "elts", []):
                if isinstance(el, ast.Tuple) and len(el.elts) >= 2:
                    linhas.update(_strings(el.elts[1]))
    return linhas


def literais(path):
    """(linha, texto) de cada literal de string, sem os trechos {…} das f-strings."""
    src = path.read_text(encoding="utf-8")
    docs = _linhas_docstring(src) | _linhas_ancora(src)
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type != tokenize.STRING or tok.start[0] in docs:
            continue
        s = tok.string
        prefixo = re.match(r"^[rRbBuUfF]*", s).group(0).lower()
        corpo = s[len(prefixo):]
        corpo = corpo[3:-3] if corpo[:3] in ('"""', "'''") else corpo[1:-1]
        if "f" in prefixo:
            corpo = re.sub(r"\{[^{}]*\}", "", corpo.replace("{{", "").replace("}}", ""))
        yield tok.start[0], corpo


def fosseis(path):
    achados = []
    linhas_fonte = path.read_text(encoding="utf-8").splitlines()
    for lin, txt in literais(path):
        fonte = linhas_fonte[lin - 1] if lin - 1 < len(linhas_fonte) else ""
        if fonte.lstrip().startswith("#"):
            continue
        # exceção justificada na própria linha: "# sem-fossil: <motivo>"
        if "# sem-fossil:" in fonte:
            continue
        # exemplos em docstring ("'1,607,081' -> 1607081.0") não chegam a entregável
        if "->" in txt and "'" in txt and len(txt) < 120 and "\n" not in txt and lin < 80:
            continue
        for m in NUM.finditer(txt):
            num, suf = m.group(1), m.group(2) or ""
            # rótulo de desfecho ("top 10%", "Topo 20%") é nome, não resultado
            if re.search(r"[Tt]opo?[~ ]?$", txt[:m.start()]):
                continue
            # parâmetro de desenho (lista DESENHO acima)
            viz = txt[max(0, m.start() - 40): m.end() + 30]
            if any(re.search(d, viz) for d in DESENHO):
                continue
            # convenções, não resultados: IC 95%, 100% (soma), limiares de p e de Cohen
            antes = txt[max(0, m.start() - 30):m.start()]
            if num in ("95", "90", "99") and re.search(r"(IC|intervalo|confiança|CI)[^\d]{0,6}$", antes):
                continue
            if num == "100" and suf.strip().startswith(("%", "\\%")):
                continue
            if num.replace("{,}", ",") in ("0,05", "0,01", "0,001", "0,10", "0,1") and re.search(r"(p|α|signific)[^\d]{0,8}$", antes):
                continue
            if num.replace("{,}", ",") in ("0,1", "0,10", "0,2", "0,5", "0,8") and \
                    re.search(r"(Cohen|\bd\b|\|d\||acima de)[^\d]{0,25}$", antes):
                continue
            janela = txt[max(0, m.start() - 25): m.end() + 10]
            if IGNORA_CTX.search(janela) and not suf.strip():
                continue
            resultado = bool(suf.strip()) or "," in num or "." in num
            if not resultado and num in INTEIROS_LIVRES:
                continue
            if not resultado and len(num) <= 2:
                continue
            if re.fullmatch(r"(19|20)\d{2}", num):
                continue
            achados.append((lin, num + suf, janela.replace("\n", " ").strip()))
    return achados


def texto_entregaveis():
    """Texto de todos os entregáveis, para separar fóssil vivo de texto morto."""
    sys.path.insert(0, str(ROOT / "tcc" / "scripts"))
    from conferir_numeros_entregaveis import ENTREGAVEIS, texto
    return "\n".join(texto(p) for p in ENTREGAVEIS if p.exists())


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    # --vivos: só o que aparece num entregável (texto que o enxuto remove não conta)
    vivo = texto_entregaveis().replace("{,}", ",") if "--vivos" in sys.argv else None
    total = 0
    for rel in GERADORES:
        p = ROOT / rel
        if not p.exists():
            print(f"[?] não encontrado: {rel}")
            continue
        a = fosseis(p)
        if vivo is not None:
            # vivo = o número aparece no entregável junto com a palavra que o antecede no
            # gerador (o número sozinho casava com pedaços de células de tabela)
            def _vivo(x):
                num = re.sub(r"[^\d,.]", "", x[1].replace("{,}", ",")).strip(".,")
                m = re.search(r"([A-Za-zÀ-ú]{2,})\W{0,6}$", x[2].split(num)[0] if num in x[2] else "")
                chave = (m.group(1) + " " + num) if m else num
                return re.sub(r"\s+", " ", chave) in vivo_norm
            vivo_norm = re.sub(r"\s+", " ", re.sub(r"[~$\\{}()]", " ", vivo))
            a = [x for x in a if _vivo(x)]
        total += len(a)
        if a:
            print(f"\n== {rel}: {len(a)}")
            for lin, num, ctx in a:
                print(f"  {lin:>5}  {num:<12} …{ctx[:110]}…")
    print(f"\nTOTAL de números fixos suspeitos: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
