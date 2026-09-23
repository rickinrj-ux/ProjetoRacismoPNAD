# Entregáveis arquivados

Arquivos que **não** devem ser enviados à banca: são anteriores ao recorte do
escopo (núcleo de 4 métodos) ou à revisão pelos livros (blocos 0–8, set/2026).
Ficam aqui como registro histórico, não como entrega.

| Arquivo | Data | Por que saiu da pasta de entrega |
|---|---|---|
| `relatorio_tcc_extenso_2026-06-16.docx` | 16/06/2026 | Versão estendida: menciona análise de redes sociais (SNA) e pesquisa operacional, que saíram do escopo após o feedback do orientador; e traz números anteriores à revisão (gap de 6,2% dentro da ocupação, hoje 7,0%; OR de 0,705, hoje 0,699). Foi gerado por `scripts/geradores/gerar_relatorio_word.py`, um texto paralelo escrito à mão. |

## O que vale hoje

| Entregável | Gerador | Fonte dos números |
|---|---|---|
| `entregaveis/relatorio_tcc_enxuto.docx` | `tcc/scripts/gerar_word_enxuto.py` | conversão do próprio `relatorio_tcc_enxuto.tex` (mesma fonte do PDF) |
| `relatorio_tcc_enxuto.pdf` | `tcc/scripts/gerar_relatorio_enxuto.py` + pdflatex | csv de `outputs/tables/` |
| `entregaveis/guia_estudo_defesa.docx` | `tcc/scripts/gerar_guia_estudo.py` | `tcc/scripts/params_nucleo.py`, que lê os csv |
| `entregaveis/apresentacao_tcc.pptx` | `scripts/geradores/gerar_apresentacao_pptx.py` | csv de `outputs/tables/` |

A versão estendida completa (SNA, pesquisa operacional, clustering, Heckman)
está preservada no branch `mestrado-extenso`.

## Ainda na pasta de entrega, mas desatualizados

`apresentacao_executiva.pptx`, `apresentacao_executiva_tcc.pptx` e
`Resultados_Preliminares_TCC.docx` são de junho de 2026 e carregam números
anteriores à revisão (6,2%; 96,4%; OR 0,705). Não estão no escopo da entrega
final, mas foram mantidos onde estavam por terem circulado com o orientador —
se forem reutilizados, precisam ser regerados antes.
