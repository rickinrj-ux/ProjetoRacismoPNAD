# TODO — adequação às normas MBA USP/Esalq

Origem: `[Relatório de Formatação] - Ricardo Gomes Calheiros.pdf` (23/09/2026) —
**35 problemas**, **81 alertas**, 331 ajustes já aplicados pelo formatador.
Normas: `Manual de Instruções e Normas para TCC (251, 252).pdf`, itens 15–19.
Template: `Template TCC - Implementação de Algoritmo(s) de Machine Learning`.

> **Validado em 23/09/2026:** opção **B** (reestruturar o LaTeX e regerar);
> Revisão de Literatura pela **opção 2** (teoria condensada na Introdução, a
> literatura de cada método migra para a Implementação); **sem Agradecimentos**;
> **tirar todos os itálicos** dos termos estrangeiros. Orientador: Edilson José
> Rodrigues, pós-doutor em Linguística Computacional.

---

## F0 — Decisão de abordagem (precisa da sua validação primeiro)

O formatador devolveu um `.docx` com 331 ajustes de forma (Arial 11, margens
2,5 cm, cabeçalho, numeração, entrelinha 1,5, recuo 1,25 cm). Os 35 problemas
restantes são de **conteúdo e estrutura** — só o autor pode resolvê-los.

| Opção | Como | Prós | Contras |
|---|---|---|---|
| **A. Editar o .docx formatado** | mexer direto no arquivo que voltou | mantém os 331 ajustes; caminho mais curto | mata o pipeline csv → LaTeX → documento; qualquer reexecução das análises não chega mais ao texto; os comentários deles se perdem ao editar |
| **B. Reestruturar o LaTeX e regerar** (recomendada) | ajustar a fonte e converter com `--reference-doc` apontando para o template oficial | preserva a fonte única dos números; o `.docx` sai já com os estilos do template; dá para reenviar ao formatador quantas vezes quiser | exige refazer a conversão e conferir o resultado |

**Recomendo a B.** O pandoc aceita `--reference-doc`: os estilos (Arial 11,
margens, cabeçalho) vêm do template oficial e o conteúdo, do nosso `.tex`.
Assim os 331 ajustes deixam de ser trabalho manual perdido e passam a ser
propriedade do gerador.

- [ ] **F0.1** Você aprova a opção B? (se preferir a A, o restante desta lista
      vale igual, só muda onde se edita)

---

## F1 — Estrutura das seções (o item mais invasivo)

A norma (item 16) prevê **exatamente** esta sequência, e **não existe seção de
Revisão de Literatura**:

```
Folha de rosto → Título + Resumo + Palavras-chave → Título em inglês +
Abstract + Keywords → Introdução → Implementação de Algoritmo(s) de Machine
Learning → Resultados e Discussão → Conclusão → Agradecimentos (opcional) →
Referências → Apêndices (opcional)
```

Hoje temos: *Em três minutos* · Introdução (+ Hipóteses) · Revisão de Literatura
(7 subseções) · Dados e Metodologia (8) · Resultados (8) · Discussão e
Prescrição · Conclusão · Limitações.

- [ ] **F1.1** Renomear "3 Dados e Metodologia" → **Implementação de
      Algoritmo(s) de Machine Learning** (problema apontado 2×)
- [ ] **F1.2** Renomear "4 Resultados" → **Resultados e Discussão** e fundir com
      "5 Discussão e Prescrição" (hoje "Resultados e Discussão" e "Conclusão"
      aparecem mais de uma vez — 4 problemas)
- [ ] **F1.3** Remover a numeração dos títulos e subtítulos (a norma não numera)
- [ ] **F1.4** **Decidir o destino da Revisão de Literatura** — ver F1.5
- [ ] **F1.5** "Limitações e escopo de validade" não é seção prevista: vai para
      o fim de Resultados e Discussão ou para a Conclusão
- [ ] **F1.6** Remover a página **"Em três minutos"**: a norma manda que entre a
      folha de rosto e o Resumo não haja nada
- [ ] **F1.7** Remover a tabela-mapa "BARREIRA I/II" ou convertê-la — a
      Introdução não aceita tabelas e os cabeçalhos em caixa-alta não são
      previstos

### ⚠ F1.4 é uma decisão sua, não minha

A estrutura normativa **não tem** seção de revisão de literatura, e a Introdução
tem **limite de duas páginas (~35 linhas)**, sem marcadores e sem tabelas ou
figuras. Hoje a Introdução tem 2 páginas e a Revisão, 3 — as que acabamos de
expandir a seu pedido.

Três saídas:

1. **Condensar** a revisão dentro da Introdução, respeitando as 2 páginas.
   Significa cortar de ~5 páginas para 2: Becker × Arrow e os parâmetros
   brasileiros sobrevivem em forma resumida; o resto vira citação pontual.
2. **Distribuir**: o arcabouço teórico vai para a Introdução (condensado) e a
   literatura de cada método migra para a seção de Implementação, onde o método
   é apresentado. Preserva quase todo o conteúdo, dentro da norma.
3. **Manter como está** e aceitar o apontamento. Não recomendo: o formatador
   reposicionou a seção para depois da Metodologia, e ela ficou solta.

**Minha recomendação: opção 2.** Preserva Becker × Arrow e os fundadores dos
métodos sem estourar o limite da Introdução.

---

## F2 — Folha de rosto (5 problemas + 1 alerta)

- [ ] **F2.1** Linha de autores no formato `Ricardo Gomes Calheiros¹*; Nome do
      Orientador²`
- [ ] **F2.2** Filiação do aluno (¹*): titulação. instituição (opcional).
      `E-mail autor correspondente: rickinrj@gmail.com` — sem endereço, CEP,
      cidade, estado ou país
- [ ] **F2.3** Filiação do orientador (²): titulação. instituição. `E-mail: …`
      — **preciso do nome completo e da titulação do orientador**
- [ ] **F2.4** Título em caixa-alta → só a primeira letra maiúscula
      (ESTRUTURAL, MERCADO, TRABALHO, BRASILEIRO, ABORDAGEM, MULTINÍVEL)
- [ ] **F2.5** Conferir o limite de 15 palavras do título (o atual tem 20)

---

## F3 — Resumo e Abstract (12 problemas)

- [ ] **F3.1** Título do trabalho centralizado e em negrito **antes** do Resumo
- [ ] **F3.2** Resumo em **um único parágrafo** (hoje são 5)
- [ ] **F3.3** Resumo de **400 → 250 palavras**
- [ ] **F3.4** Resumo no **pretérito perfeito do indicativo**
- [ ] **F3.5** Palavras-chave: no máximo 5, e **sem "PNAD Contínua"** (está no
      título)
- [ ] **F3.6** Inserir o **título em inglês**, centralizado e em negrito, antes
      do Abstract
- [ ] **F3.7** Abstract em um único parágrafo, **377 → 250 palavras**
- [ ] **F3.8** Keywords: no máximo 5, sem "PNAD Contínua"
- [ ] **F3.9** Abstract sem subtópicos
- [ ] **F3.10** Decimal com vírgula também no Abstract (11 números com ponto)

---

## F4 — Introdução (3 problemas + 6 alertas)

- [ ] **F4.1** Remover o subtópico **"Hipóteses"** (a seção não aceita
      subtópicos) e reescrever as hipóteses em texto corrido
- [ ] **F4.2** Remover a **lista com marcadores** (não permitida)
- [ ] **F4.3** Enunciar o **objetivo da pesquisa no último parágrafo**, de forma
      direta
- [ ] **F4.4** Respeitar o limite de **2 páginas**
- [ ] **F4.5** Siglas entre colchetes na primeira ocorrência: `[POF]`, `[VIF]`,
      `[IPS]` (hoje entre parênteses)

---

## F5 — Tabelas e figuras (28 alertas — o bloco mais volumoso)

A norma exige que **toda tabela e figura seja citada no texto no parágrafo
imediatamente anterior à sua inserção**. Hoje:

- **Nunca citadas:** Tabelas 2, 5, 15, 16, 17, 18, 19, 20 e Figuras 1, 2, 3, 4,
  5, 6, 7
- **Citadas só depois da inserção:** Tabelas 7, 8, 9, 10, 11, 13, 14
- **Citadas longe:** Tabelas 3, 12 e Figura 8

- [ ] **F5.1** Inserir a chamada de cada tabela/figura no parágrafo anterior
- [ ] **F5.2** Título das figuras **abaixo**, no padrão `Figura X. Título`
- [ ] **F5.3** Fonte das tabelas: trocar o marcador por
      `Fonte: Resultados originais da pesquisa`
- [ ] **F5.4** Figuras com painéis (QR/RIF e OB): identificar `A`, `B` no canto
      superior esquerdo, maiúscula, sem parênteses nem ponto
- [ ] **F5.5** Tabela 4 (step-up) quebra página: repetir o título com
      `(continua)`, `(continuação)` e `(conclusão)`
- [ ] **F5.6** Verificar a numeração sequencial após as mudanças

---

## F6 — Equações (1 alerta, 3 equações)

- [ ] **F6.1** Numerar em algarismos arábicos entre parênteses, alinhados à
      direita: (1), (2), (3)

---

## F7 — Linguagem e tipografia (≈30 alertas)

- [ ] **F7.1** Termos estrangeiros **não consagrados** vão entre **aspas**, não
      em itálico: "concentrated disadvantage", "duplo disadvantage", "E-value",
      "TreeExplainer", "SHapley Additive exPlanations"
- [ ] **F7.2** Termos estrangeiros **já incorporados** perdem o itálico:
      machine learning, gap, gradient boosting, dummies, step-up, bad controls,
      twofold, m-out-of-n, Random Forest, XGBoost, features, hold-out, fold,
      folds, smearing, overfitting, leave-one-out, odds ratios, pooled, cutoff,
      sticky floor, fanning out, networking, Prouni, Fies, PRONATEC, per capita
      — **decisão sua**: o formatador diz que o destaque é escolha do autor
- [ ] **F7.3** Números de zero a dez por extenso, exceto com unidade
- [ ] **F7.4** Conferir o gráfico classificado como imagem (a norma pede objeto
      do Excel/Word; se não der, manter a imagem, mas sem grade, sem borda, sem
      preenchimento e sem título interno, eixos em 1,5 pt)

---

## F8 — Seções finais

- [ ] **F8.1** **Referências** depois de **Agradecimentos**, em negrito, à
      esquerda, sem numeração
- [ ] **F8.2** Decidir se inclui **Agradecimentos** (opcional, até 3 linhas)
- [ ] **F8.3** Conferir as 31 referências no padrão do item 19 do manual
- [ ] **F8.4** Conclusão **sem citações** e **sem tabelas/figuras** (a norma
      proíbe nas duas)

---

## F9 — Fechamento

- [ ] **F9.1** Regerar o `.docx` com `--reference-doc` do template oficial
- [ ] **F9.2** Conferir o limite de páginas: **50** para Data Science com
      temática de ML (o trabalho tem 44 no formato deles)
- [ ] **F9.3** Rodar o verificador e conferir que os números seguem batendo
- [ ] **F9.4** Reenviar ao Sistema de TCC e comparar o novo relatório

---

## O que preciso de você antes de começar

1. **F0.1** — aprova a opção B (reestruturar o LaTeX e regerar)?
2. **F1.4** — qual saída para a Revisão de Literatura? (recomendo a 2)
3. **F2.3** — nome completo e titulação do orientador
4. **F7.2** — tirar o itálico de todos os termos estrangeiros consagrados, ou
   manter o destaque onde é intencional?
5. **F8.2** — quer seção de Agradecimentos?
