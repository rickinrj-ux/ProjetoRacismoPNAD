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

O pós-processador trata estrutura (seções, figuras, tabelas) **e** reescreve o resumo/abstract,
mas **não reescreve o restante da prosa autoral**. Revisar à mão no `relatorio_tcc_enxuto.tex`:

1. ~~Resumo (PT) e Abstract (EN)~~ — **FEITO**: reescritos para o núcleo de 4 + robustez,
   diretamente no pós-processador (sobrevivem à regeração).
2. **Discussão/Conclusão** mencionam SNA/clustering/PO de passagem (ex.: "isolamento de
   redes", ranqueamento TOPSIS) — remover ou reposicionar como agenda futura.
3. **Metodologia** descreve formalmente HLM e ML/SHAP, mas Oaxaca, Quantílica/RIF e GLMM
   entram direto em Resultados — convém adicionar parágrafos de método para esses três.
4. Ordem em Resultados: ML/SHAP (robustez) aparece antes do trio de núcleo; opcional movê-lo
   para depois.
5. **Decomposição Oaxaca — RESOLVIDO** (`tcc/PERICIA.md` F1): a divergência era de
   **especificação** (ocupação dentro/fora), não de amostra. Tabela `ob_acesso.tex` (com
   ocupação) → **dotações 83,8% / discriminação 16,2%**, reproduzindo o "84%". Resumo cita
   o número; narrativa vindicada.

## Tabelas de resultado e legendas "Como ler" (pedido do orientador)

O relatório enxuto agora insere **6 tabelas de resultado** do núcleo (mediação M1→M4,
Oaxaca de acesso, quantílica, RIF corrigido, GLMM, interseccional), cada uma com legenda
``Como ler''; figuras (SHAP, interseccional) e tabelas de ML também receberam legendas.
Geradores em `tcc/scripts/`: `gerar_tabela_mediacao.py`, `gerar_tabela_oaxaca.py`,
`corrigir_tabela_rif.py`, `gerar_tabela_glmm.py`, `gerar_tabela_interseccional.py`.

## Perícia cruzada (`tcc/PERICIA.md` seção 2 + `pericia_cruzada_resultado.txt`)

Auditoria numérica (`tcc/scripts/pericia_cruzada.py`): identidades de decomposição +
consistência params↔tabelas. Achados FC1–FC7 (coluna RIF dupla-contada, `inter` órfão no
interseccional, `evalues` stale, LRT degenerado, gap_decomposicao duplicado). Os que afetam
o relatório foram corrigidos; os de escopo estendido ficaram flagueados para o mestrado.

## Pendências de revisão MANUAL remanescentes
- Discussão/Conclusão ainda mencionam SNA/clustering/PO de passagem (remover/agendar).
- Metodologia: adicionar parágrafos formais de Oaxaca/QR/GLMM.

## Núcleo de 4 (resumo)

1. **HLM 3 níveis** — quanto do gap sobrevive e onde nasce.
2. **Oaxaca-Blinder** — composição vs. discriminação.
3. **Regressão quantílica (+RIF-OB)** — teto de vidro / sticky floor.
4. **GLMM logístico** — gap de acesso a cargo qualificado / topo.

Detalhes e justificativa em `MANIFESTO_METODOS.md`.
