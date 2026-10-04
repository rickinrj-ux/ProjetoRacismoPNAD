"""
conferir_numeros_entregaveis.py — todo número de um entregável tem de ter fonte.

Complementa caca_fosseis.py, que olha os geradores. Este olha o produto final: extrai
cada número do texto do PDF de entrega (tcc_normas.tex), dos .docx e dos .pptx, e
procura a origem dele entre os valores atuais — params_nucleo e os csv que os
geradores leem. Um número sem correspondência é fóssil (escrito à mão e esquecido
numa reestimação) ou conta derivada que precisa ser conferida à mão.

A correspondência admite o arredondamento do próprio número (35,5 casa com 35,46) e
as transformações que o texto usa: ×100, 100·(1−OR), valor absoluto, milhões e
milhares (7,7 milhões, 41 mil) e a soma/diferença de dois parâmetros (Δ e "5 p.p.").

Uso:
    python tcc/scripts/conferir_numeros_entregaveis.py           # código 1 se houver órfão
    python tcc/scripts/conferir_numeros_entregaveis.py --detalhe # contexto de cada órfão
"""
import csv
import itertools
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tcc" / "scripts"))
from params_nucleo import P  # noqa: E402

TABLES = ROOT / "outputs" / "tables"
PARQUET_MTIME = (ROOT / "data" / "processed" / "features.parquet").stat().st_mtime
# csv pequenos que um gerador lê direto para montar texto (fora do params_nucleo)
CSV_DIRETOS = ["composicao_por_grupo_cbo.csv", "shap_importance_comparada.csv",
               # lidos pelos marcadores @@…@@ de gerar_relatorio_enxuto.py
               "ml_performance.csv", "vif_m4_preditores.csv", "glmm_glassceil_glmer_coefs.csv",
               "hlm_serie_completo_ponderado.csv", "hlm_serie_completo_se.csv",
               "hlm_stepup_coefs.csv", "hlm_stepup_fit.csv", "hlm_stepup_varcomp.csv"]

# Números externos (citados, não estimados aqui) e códigos: contexto que os identifica.
EXTERNOS = re.compile(
    r"Lei \d|DeclareUnicodeCharacter|munic[íi]pios|Gini|IBGE|Nordeste|Norte \(|Sul \("
    r"|chefiad|índice de [0-9]|qualidade de vida"
    # número de lei/decreto (04/10/2026): "Decreto 11.443/2023", "(14.611/2023)"
    r"|Decreto \d|\d{1,2}\.\d{3}/(?:19|20)\d{2}")
ENTREGAVEIS = [
    ROOT / "tcc_normas.tex",
    ROOT / "relatorio_tcc_enxuto.tex",          # vira entregaveis/relatorio_tcc_enxuto.pdf/.docx
    ROOT / "entregaveis" / "TCC_Ricardo_Calheiros_Guia_de_Estudo.docx",
    ROOT / "entregaveis" / "TCC_Ricardo_Calheiros_Versao_Narrativa.docx",
    ROOT / "entregaveis" / "TCC_Ricardo_Calheiros_Executiva.pptx",
    ROOT / "entregaveis" / "TCC_Ricardo_Calheiros_Defesa.pptx",
]
GERADORES = [
    "scripts/geradores/gerar_relatorio_tcc.py", "tcc/scripts/gerar_relatorio_enxuto.py",
    "tcc/scripts/enxuto_patches.py", "tcc/scripts/gerar_tcc_normas.py",
    "tcc/scripts/tcc_normas_texto.py", "tcc/scripts/gerar_guia_estudo.py",
    "tcc/scripts/gerar_apresentacao_executiva.py", "scripts/geradores/gerar_apresentacao_pptx.py",
    "tcc/scripts/gerar_narrativa_social.py", "tcc/scripts/params_nucleo.py",
    "tcc/scripts/gerar_tabela_glmm.py", "tcc/scripts/gerar_tabela_oaxaca.py",
    "tcc/scripts/gerar_tabela_mediacao.py", "tcc/scripts/gerar_tabela_interseccional.py",
    "tcc/scripts/gerar_tabela_robustez.py", "tcc/scripts/gerar_tabela_balanceamento.py",
    "tcc/scripts/gerar_tabela_cv.py", "tcc/scripts/corrigir_tabela_rif.py",
]


# ── 1. Valores de referência ─────────────────────────────────────────────────
def _float(x):
    try:
        v = float(str(x).replace(",", "").strip())
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def valores_fonte():
    base = set()
    for v in P.values():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            base.add(float(v))
        elif isinstance(v, tuple):
            base.update(float(x) for x in v if isinstance(x, (int, float)))
    # Universo restrito de propósito. A primeira versão aceitava toda célula de todo csv
    # citado pelos geradores (83 mil valores): qualquer número de uma casa decimal casava
    # por acaso, e "96,4" ou "35,1" — fósseis conhecidos — passavam. Agora a fonte é:
    #  (a) params_nucleo;
    #  (b) os números das tabelas .tex que vão para o documento (geradas de csv);
    #  (c) os poucos csv pequenos que um gerador lê direto para montar texto.
    for tex in TABLES.glob("*.tex"):
        if tex.stat().st_mtime < PARQUET_MTIME:
            continue                      # tabela anterior aos dados atuais não é fonte
        t = tex.read_text(encoding="utf-8").replace("{,}", ",")
        for m in re.finditer(r"[−-]?\d{1,3}(?:\.\d{3})+|[−-]?\d+(?:,\d+)?", t):
            s = m.group(0).replace("−", "-")
            base.add(float(s.replace(".", "")) if re.search(r"\.\d{3}", s) else float(s.replace(",", ".")))
    for n in CSV_DIRETOS:
        p = TABLES / n
        if not p.exists():
            continue
        with p.open(encoding="utf-8", newline="") as f:
            for linha in csv.reader(f):
                for cel in linha:
                    v = _float(cel)
                    if v is not None:
                        base.add(v)
    params = [float(v) for v in P.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return base, params


def candidatos(base, params):
    """Valor-fonte e as transformações que o texto costuma aplicar."""
    out = set()
    for v in base:
        for t in (v, 100 * v, 100 * (1 - v), v / 1e6, v / 1e3, 100 * (math.exp(v) - 1) if abs(v) < 5 else v):
            out.add(abs(t))
    # Diferenças e razões entre pares NÃO entram: com ~300 parâmetros seriam ~45 mil
    # combinações, e um fóssil acabaria casando por acaso. Conta derivada (Δ, "2,5×")
    # aparece como órfã e é conferida à mão — ou vira parâmetro.
    return sorted(out)


# ── 2. Texto dos entregáveis ─────────────────────────────────────────────────
def texto(path):
    if path.suffix == ".tex":
        t = path.read_text(encoding="utf-8")
        t = re.sub(r"(?<!\\)%.*", "", t)                 # comentários LaTeX
        t = t.replace("{,}", ",").replace("\\,", " ").replace("~", " ").replace("\\%", "%")
        t = re.sub(r"\\(cite|citeonline|ref|label|eqref|includegraphics)(\[[^]]*\])?\{[^}]*\}", " ", t)
        return t
    if path.suffix == ".docx":
        from docx import Document
        d = Document(path)
        partes = [p.text for p in d.paragraphs]
        for tb in d.tables:
            for row in tb.rows:
                partes.extend(c.text for c in row.cells)
        return "\n".join(partes)
    if path.suffix == ".pptx":
        from pptx import Presentation
        partes = []
        for sl in Presentation(path).slides:
            for sh in sl.shapes:
                if sh.has_text_frame:
                    partes.append(sh.text_frame.text)
                if getattr(sh, "has_table", False) and sh.has_table:
                    for row in sh.table.rows:
                        partes.extend(c.text for c in row.cells)
        return "\n".join(partes)
    return ""


NUM = re.compile(r"(?<![\w.,/@-])[−-]?(\d{1,3}(?:\.\d{3})+|\d+(?:,\d+)?)(?![\w])")


def numeros(t):
    for m in NUM.finditer(t):
        bruto = m.group(1)
        ini, fim = m.start(), m.end()
        depois = t[fim:fim + 3]
        antes = t[max(0, ini - 12):ini]
        if re.fullmatch(r"(19|20)\d{2}", bruto):                       # ano
            continue
        if re.search(r"(\bq|Q|M|A|\bn|τ|τ=|tau|[A-Za-z]\()$", antes.rstrip()) and "," not in bruto:
            continue                                                      # q10, M3, A2…
        if re.search(r"(Tabela|Figura|Seção|Subseção|Equação|equação|p\.|pp\.|cap\.|Anexo|Apêndice|slide|Slide)\s*$", antes):
            continue
        if re.search(r"[Tt]op\s*$", antes):                               # rótulo "top 10%"
            continue
        if "." in bruto:
            valor, casas = float(bruto.replace(".", "")), 0
        elif "," in bruto:
            valor, casas = float(bruto.replace(",", ".")), len(bruto.split(",")[1])
        else:
            valor, casas = float(bruto), 0
        # Só o que a comparação consegue discriminar: contagens (≥ 1.000) e números com
        # 2+ casas decimais. Um percentual de uma casa ("35,1%") casa por acaso com algum
        # dos ~6 mil candidatos; para esses, a garantia é caca_fosseis.py, na origem.
        if not (casas >= 2 or (casas == 0 and valor >= 1000)):
            continue
        yield bruto, valor, casas, t[max(0, ini - 50):fim + 30].replace("\n", " ")


def casa(valor, casas, cands):
    import bisect
    tol = 0.5 * 10 ** (-casas) + 1e-9
    i = bisect.bisect_left(cands, valor - tol)
    return i < len(cands) and cands[i] <= valor + tol


# ── 3. Relatório ─────────────────────────────────────────────────────────────
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    detalhe = "--detalhe" in sys.argv
    base, params = valores_fonte()
    cands = candidatos(base, params)
    total = 0
    for ent in ENTREGAVEIS:
        if not ent.exists():
            print(f"[?] {ent.name} não encontrado")
            continue
        orfaos = {}
        for bruto, valor, casas, ctx in numeros(texto(ent)):
            if not casa(valor, casas, cands) and not EXTERNOS.search(ctx):
                orfaos.setdefault(bruto, ctx)
        total += len(orfaos)
        print(f"== {ent.name}: {len(orfaos)} número(s) sem fonte")
        if detalhe:
            for b, ctx in orfaos.items():
                print(f"     {b:<12} …{ctx}…")
    print(f"\nTOTAL de números sem fonte: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
