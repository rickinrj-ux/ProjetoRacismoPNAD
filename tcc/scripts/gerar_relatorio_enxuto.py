"""
gerar_relatorio_enxuto.py
=========================
Pós-processa o relatório COMPLETO (relatorio_tcc.tex, gerado por
scripts/geradores/gerar_relatorio_tcc.py) e produz a VERSÃO ENXUTA do TCC
(núcleo de 4 métodos + robustez), conforme tcc/MANIFESTO_METODOS.md.

Opera no LaTeX já materializado (não no f-string do gerador), portanto é
seguro e reversível. O gerador completo permanece intacto (versão estendida
no branch mestrado-extenso).

O que faz:
  1. Remove as subseções do escopo ESTENDIDO (clustering, SNA, random slope,
     segregação espacial).
  2. Insere subseções de RESULTADOS para o NÚCLEO que hoje só aparecem na
     discussão (Oaxaca-Blinder, Quantílica/RIF, GLMM), com as tabelas .tex
     via \\input — atendendo ao pedido de "resultados em tabelas".
  3. Avisa sobre referências (\\ref) penduradas a rótulos removidos.

Entrada : relatorio_tcc.tex          (raiz)
Saída   : relatorio_tcc_enxuto.tex   (raiz; mesmas paths relativas de outputs/)
"""

# --- bootstrap raiz do projeto ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---

import sys, re
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from pathlib import Path

SRC = Path("relatorio_tcc.tex")
OUT = Path("relatorio_tcc_enxuto.tex")

if not SRC.exists():
    sys.exit("relatorio_tcc.tex não encontrado. Rode antes: "
             "python scripts/geradores/gerar_relatorio_tcc.py")

lines = SRC.read_text(encoding="utf-8").splitlines()

SEC_RE = re.compile(r"^\\(sub)?section\*?\{")

# Subseções a REMOVER (escopo estendido -> parqueado em mestrado-extenso)
REMOVER = [
    r"\subsection{Análise de redes sociais e capital social}",
    r"\subsection{Clustering Socioeconômico (K-Means)}",
    r"\subsection{Análise de Redes Sociais (SNA)}",
    r"\subsection{M3 com Inclinação Aleatória de Negro: Heterogeneidade Geográfica}",
    r"\subsection{Random Slope no GLMM: Heterogeneidade Geográfica do Acesso}",
    r"\subsection{Clustering Socioeconômico}",
    r"\subsection{Análise de Redes Sociais --- Isolamento Estrutural}",
    r"\subsection{Segregação Espacial: Inferência Bootstrap}",
]

# Blocos \paragraph{} de escopo estendido (PO regional, limitações de SNA/PO)
REMOVER_PARAGRAFOS = [
    r"\paragraph{Focalização territorial: Pesquisa Operacional regionalizada.}",
    r"\paragraph{Granularidade macroestrutural da SNA.}",
    r"\paragraph{Caráter normativo da Pesquisa Operacional.}",
]
PARA_RE = re.compile(r"^\\(paragraph|subsection|section)\*?\{")

# Âncora antes da qual inserimos as subseções de núcleo
ANCORA_NUCLEO = r"\subsection{Interseccionalidade: raça e gênero no acesso e no topo}"

BLOCO_NUCLEO = r"""% ── NÚCLEO: decomposições e acesso (inserido pela versão enxuta) ──
\subsection{Decomposição de Oaxaca--Blinder: composição \emph{vs.}\ discriminação}
A decomposição de Oaxaca--Blinder separa o gap salarial bruto em uma parcela
explicada por diferenças de dotações (capital humano e posição ocupacional) e
uma parcela não explicada, atribuível a retornos diferenciais --- o componente
usualmente interpretado como discriminação de mercado. A
Tabela~\ref{tab:oaxaca_blinder} reporta a decomposição \emph{two-fold} sobre a
população completa.
\input{outputs/tables/ob_decomposicao.tex}

\subsection{Regressão Quantílica e RIF-OB: teto de vidro e \emph{sticky floor}}
A regressão quantílica estima o gap em cada ponto da distribuição de renda; a
decomposição RIF-OB separa, por quantil, os componentes de dotação e de retorno.
A Tabela~\ref{tab:qr_melhorias} evidencia que o gap residual cresce ao longo da
distribuição (teto de vidro no gap bruto), ao passo que a
Tabela~\ref{tab:rif_ob} revela o padrão complementar: o componente de retorno ---
a discriminação de mercado proporcional --- é maior na base da distribuição e
\emph{decresce} rumo ao topo (\emph{sticky floor}).
\input{outputs/tables/qr_melhorias.tex}
\input{outputs/tables/rif_ob_decomposicao.tex}

\subsection{GLMM Logístico: o teto de vidro no acesso}
O GLMM logístico multinível estima a probabilidade de acesso a cargo qualificado
e ao topo da renda, com efeito aleatório de UPA. A
Tabela~\ref{tab:glmm_glassceil} sintetiza os \emph{odds ratios}, efeitos
marginais médios e E-values dos três desfechos; a Tabela~\ref{tab:evalues_glmm}
detalha a sensibilidade a confundidores não-observados. O padrão é consistente:
o teto se aperta no extremo superior (top~10\%) e resiste a todos os controles.
\input{outputs/tables/glmm_glassceil.tex}
\input{outputs/tables/evalues_glmm.tex}

"""

NOTA_CABECALHO = (
    "% ╔══════════════════════════════════════════════════════════════════════╗\n"
    "% ║ VERSÃO ENXUTA DO TCC — núcleo de 4 métodos + robustez.                ║\n"
    "% ║ Gerada automaticamente por tcc/scripts/gerar_relatorio_enxuto.py.     ║\n"
    "% ║ NÃO editar à mão: edite o gerador completo e reexecute o pós-proc.    ║\n"
    "% ║ Versão estendida (todos os métodos): branch mestrado-extenso.         ║\n"
    "% ╚══════════════════════════════════════════════════════════════════════╝\n"
)


def _remove_bloco(lines, titulo, boundary_re):
    """Remove do título (inclusive) até a próxima fronteira (exclusive)."""
    try:
        ini = lines.index(titulo)
    except ValueError:
        print(f"  [AVISO] bloco não encontrado (já removido?): {titulo}")
        return lines, []
    fim = ini + 1
    while fim < len(lines) and not boundary_re.match(lines[fim]):
        fim += 1
    removidas = lines[ini:fim]
    rotulos = []
    for ln in removidas:
        rotulos += re.findall(r"\\label\{([^}]*)\}", ln)
    return lines[:ini] + lines[fim:], rotulos


def remove_subsecao(lines, titulo):
    return _remove_bloco(lines, titulo, SEC_RE)


def remove_paragrafo(lines, titulo):
    return _remove_bloco(lines, titulo, PARA_RE)


def remove_figuras_por_conteudo(lines, agulhas):
    """Remove blocos \\begin{figure}..\\end{figure} cujo conteúdo cite método
    parqueado (ex.: figura de clustering solta fora da subseção removida)."""
    out, i, rotulos = [], 0, []
    while i < len(lines):
        if lines[i].lstrip().startswith(r"\begin{figure}"):
            j = i
            while j < len(lines) and not lines[j].lstrip().startswith(r"\end{figure}"):
                j += 1
            bloco = "\n".join(lines[i:j + 1])
            if any(a in bloco for a in agulhas):
                for ln in lines[i:j + 1]:
                    rotulos += re.findall(r"\\label\{([^}]*)\}", ln)
                print(f"  - figura removida (contém: "
                      f"{next(a for a in agulhas if a in bloco)})")
                i = j + 1
                continue
        out.append(lines[i])
        i += 1
    return out, rotulos


print("Removendo subseções do escopo estendido…")
rotulos_removidos = []
for t in REMOVER:
    lines, rots = remove_subsecao(lines, t)
    if rots:
        rotulos_removidos += rots
    print(f"  - {t.split('{',1)[1][:-1]}")

print("Removendo parágrafos de escopo estendido (PO regional, limitações SNA/PO)…")
for t in REMOVER_PARAGRAFOS:
    lines, rots = remove_paragrafo(lines, t)
    if rots:
        rotulos_removidos += rots
    print(f"  - {t.split('{',1)[1][:-1]}")

# Inserir bloco de núcleo antes da interseccionalidade
print("Removendo figuras soltas de métodos parqueados…")
lines, rots = remove_figuras_por_conteudo(lines, ["kmeans", "sna_", "segreg_"])
rotulos_removidos += rots

print("Inserindo subseções de núcleo (Oaxaca, Quantílica/RIF, GLMM)…")
try:
    idx = lines.index(ANCORA_NUCLEO)
    lines = lines[:idx] + BLOCO_NUCLEO.splitlines() + lines[idx:]
except ValueError:
    sys.exit("Âncora de núcleo não encontrada — abortando para não inserir no lugar errado.")

texto = NOTA_CABECALHO + "\n".join(lines) + "\n"

# Checagem de \ref pendentes a rótulos removidos
pendentes = []
for rot in set(rotulos_removidos):
    if re.search(r"\\(ref|autoref|cref|eqref)\{" + re.escape(rot) + r"\}", texto):
        pendentes.append(rot)

OUT.write_text(texto, encoding="utf-8")
print(f"\nOK -> {OUT}  ({len(lines)} linhas)")
if pendentes:
    print("\n[ATENÇÃO] Referências penduradas a rótulos removidos (revisar no texto):")
    for p in sorted(pendentes):
        print(f"   \\ref{{{p}}}")
else:
    print("Sem referências penduradas a rótulos removidos.")
