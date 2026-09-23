# Entregáveis arquivados

Arquivos que **não** devem ser enviados à banca: são anteriores ao recorte do
escopo (núcleo de 4 métodos) ou à revisão pelos livros (blocos 0–8, set/2026).
Ficam aqui como registro histórico, não como entrega.

| Arquivo | Data | Por que saiu da pasta de entrega |
|---|---|---|
| `relatorio_tcc_extenso_2026-06-16.docx` | 16/06/2026 | Versão estendida: menciona análise de redes sociais (SNA) e pesquisa operacional, que saíram do escopo após o feedback do orientador; e traz números anteriores à revisão (gap de 6,2% dentro da ocupação, hoje 7,0%; OR de 0,705, hoje 0,699). Foi gerado por `scripts/geradores/gerar_relatorio_word.py`, um texto paralelo escrito à mão. |
| `apresentacao_executiva_tcc_2026-06-16.pptx` | 16/06/2026 | Segundo deck executivo, com a mesma finalidade do primeiro e a narrativa de três barreiras e cinco métodos. Substituído pelo deck único `TCC_Ricardo_Calheiros_Executiva.pptx`. |
| `Resultados_Preliminares_TCC_2026-09.docx` | set/2026 | Documento do modelo *Resultados Preliminares* da USP/Esalq, de uma entrega intermediária ao orientador. Os números foram atualizados em setembro e conferem com o relatório final, mas a peça é de uma etapa vencida — o relatório final a substitui. Se houver nova submissão nesse modelo, basta rodar `tcc/scripts/gerar_resultados_preliminares.py`. |

## O que vale hoje

| Entregável (em `entregaveis/`) | Gerador | Fonte dos números |
|---|---|---|
| `TCC_Ricardo_Calheiros_MBA_USP_Esalq.pdf` | `tcc/scripts/gerar_relatorio_enxuto.py` + pdflatex | csv de `outputs/tables/` |
| `TCC_Ricardo_Calheiros_MBA_USP_Esalq.docx` | `tcc/scripts/gerar_word_enxuto.py` | conversão do mesmo `relatorio_tcc_enxuto.tex` que gera o PDF |
| `TCC_Ricardo_Calheiros_Guia_de_Estudo.docx` | `tcc/scripts/gerar_guia_estudo.py` | `tcc/scripts/params_nucleo.py`, que lê os csv |
| `TCC_Ricardo_Calheiros_Defesa.pptx` | `scripts/geradores/gerar_apresentacao_pptx.py` | `params_nucleo.py` |
| `TCC_Ricardo_Calheiros_Executiva.pptx` | `tcc/scripts/gerar_apresentacao_executiva.py` | `params_nucleo.py` |

Todos saem juntos com `./tcc/run_tcc.ps1`. O `.tex` e o PDF da raiz mantêm o
nome do *build* (`relatorio_tcc_enxuto`); a pasta de entrega recebe a cópia com
o nome de entrega.

A versão estendida completa (SNA, pesquisa operacional, clustering, Heckman)
está preservada no branch `mestrado-extenso`.

## Geradores superados

Estes escrevem nos mesmos arquivos dos entregáveis atuais e os sobrescreveriam
com números anteriores à revisão. Por isso saem com erro; para rodá-los no
branch estendido, defina `PERMITIR_GERADOR_SUPERADO=1`.

- `scripts/geradores/gerar_relatorio_word.py`
- `scripts/geradores/gerar_guia_estudo.py`
- `scripts/geradores/gerar_apresentacao_executiva.py`
- `scripts/geradores/gerar_apresentacao_executiva_pptx.py`
- `scripts/geradores/gerar_resultados_preliminares.py`

O `params.py` da raiz continua servindo esses geradores; os entregáveis atuais
usam `tcc/scripts/params_nucleo.py`.
