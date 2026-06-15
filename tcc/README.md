# TCC — Versão Enxuta (Núcleo de 4 Métodos)

Esta pasta materializa a **versão focada do TCC**, definida após o feedback do orientador
(jun/2026). Ela não contém cópias de código — é a **camada de governança de escopo** que diz
o que entra no TCC e o que fica para depois, apontando para os scripts canônicos em
`scripts/analise/` e as tabelas em `outputs/tables/`.

## Duas versões, um repositório

| Versão | Onde está | Para quê |
|--------|-----------|----------|
| **TCC enxuto** | branch `master` + esta pasta `tcc/` | Entrega do MBA: 4 métodos no núcleo + robustez |
| **Estendida (completa)** | branch **`mestrado-extenso`** (GitHub) | Base para artigo / mestrado: ~18 técnicas, nada removido |

```bash
# voltar à versão completa a qualquer momento, sem perder nada:
git checkout mestrado-extenso

# voltar ao TCC enxuto:
git checkout master
```

## Arquivos desta pasta

- **`ESCOPO_TCC.md`** — a decisão de priorização, o feedback do orientador e a resposta aos
  três pontos (métodos, tabelas, frase do "principal determinante").
- **`MANIFESTO_METODOS.md`** — classificação de cada método em Núcleo / Robustez / Estendido,
  com o script e a tabela `.tex` correspondentes.
- **`run_tcc.ps1`** — launcher curado: roda **apenas** os scripts do núcleo + robustez, na
  ordem, e ao final (re)gera o relatório enxuto. Use `-NucleoSo` para só o núcleo, ou
  `-Relatorio` para só (re)gerar o relatório.
- **`scripts/gerar_tabela_glmm.py`** — gera `outputs/tables/glmm_glassceil.tex` (tabela-síntese
  do GLMM: 3 desfechos × M1–M3, OR/IC/AME/E-value, população completa).
- **`scripts/gerar_relatorio_enxuto.py`** — pós-processa `relatorio_tcc.tex` (completo) em
  **`relatorio_tcc_enxuto.tex`**: remove as seções do escopo estendido (clustering, SNA,
  random slope, segregação, PO regional) e **insere** as subseções de Resultados do núcleo
  (Oaxaca, Quantílica/RIF, GLMM) com as tabelas via `\input`. Não toca no gerador completo.

## Relatório enxuto

```powershell
./tcc/run_tcc.ps1 -Relatorio   # gera relatorio_tcc_enxuto.tex (na raiz)
```

Compilar **a partir da raiz do projeto** (as paths de `outputs/` são relativas à raiz):
`pdflatex relatorio_tcc_enxuto.tex` → `bibtex` → `pdflatex` ×2. No Overleaf, subir o repo e
definir `relatorio_tcc_enxuto.tex` como documento principal.

### Pendências de revisão MANUAL (prosa — não automatizadas)

O pós-processador trata estrutura (seções, figuras, tabelas), mas **não reescreve a prosa
autoral**. Revisar à mão no `relatorio_tcc_enxuto.tex`:

1. **Resumo (PT) e Abstract (EN)** ainda descrevem K-Means, SNA e TOPSIS como parte da
   metodologia — ajustar para o núcleo de 4 + robustez.
2. **Discussão/Conclusão** mencionam SNA/clustering/PO de passagem (ex.: "isolamento de
   redes", ranqueamento TOPSIS) — remover ou reposicionar como agenda futura.
3. **Metodologia** descreve formalmente HLM e ML/SHAP, mas Oaxaca, Quantílica/RIF e GLMM
   entram direto em Resultados — convém adicionar parágrafos de método para esses três.
4. Ordem em Resultados: ML/SHAP (robustez) aparece antes do trio de núcleo; opcional movê-lo
   para depois.

## Núcleo de 4 (resumo)

1. **HLM 3 níveis** — quanto do gap sobrevive e onde nasce.
2. **Oaxaca-Blinder** — composição vs. discriminação.
3. **Regressão quantílica (+RIF-OB)** — teto de vidro / sticky floor.
4. **GLMM logístico** — gap de acesso a cargo qualificado / topo.

Detalhes e justificativa em `MANIFESTO_METODOS.md`.
