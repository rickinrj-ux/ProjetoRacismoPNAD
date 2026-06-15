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
  ordem, usando o Python do Spyder.

## Núcleo de 4 (resumo)

1. **HLM 3 níveis** — quanto do gap sobrevive e onde nasce.
2. **Oaxaca-Blinder** — composição vs. discriminação.
3. **Regressão quantílica (+RIF-OB)** — teto de vidro / sticky floor.
4. **GLMM logístico** — gap de acesso a cargo qualificado / topo.

Detalhes e justificativa em `MANIFESTO_METODOS.md`.
