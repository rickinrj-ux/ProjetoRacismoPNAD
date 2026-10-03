# Antes × depois da correção da escolaridade e da renda — 2026-10-03

Antes: `outputs/_backup_pre_educ/` (V3009A como nível, renda nominal). Depois: `outputs/tables/`
(VD3004 com dummies cumulativas, deflator IBGE + efeito de ano, fundamental em todos os modelos).

| Bloco | Resultado | Antes | Depois | Δ |
|---|---|---|---|---|
| HLM | Gap M1 (%) | -10.63 | -6.47 | 4.17 |
| HLM | Gap M2 (%) | -10.41 | -6.17 | 4.23 |
| HLM | Gap M3 (%) | -10.44 | -6.10 | 4.34 |
| HLM | Gap M4 (%) | -7.16 | -5.62 | 1.53 |
| HLM | ICC M0 | 0.369 | 0.353 | -0.016 |
| HLM | ICC M3 | 0.144 | 0.076 | -0.068 |
| GLMM | OR cargo qualificado A2 | 0.697 | 0.814 | 0.117 |
| GLMM | OR cargo qualificado A3 | 0.687 | 0.791 | 0.103 |
| GLMM | AME cargo qualificado A2 (p.p.) | -5.55 | -2.60 | 2.95 |
| GLMM | OR topo 20% A2 | 0.672 | 0.769 | 0.097 |
| GLMM | OR topo 20% A3 | 0.672 | 0.755 | 0.083 |
| GLMM | AME topo 20% A2 (p.p.) | -5.09 | -2.77 | 2.32 |
| GLMM | OR topo 10% A2 | 0.640 | 0.761 | 0.120 |
| GLMM | OR topo 10% A3 | 0.639 | 0.740 | 0.101 |
| GLMM | AME topo 10% A2 (p.p.) | -3.15 | -1.66 | 1.49 |
| Oaxaca | % não explicado (A sem ocupação) | 28.91 | 28.91 | 0.00 |
| Oaxaca | % não explicado (B com ocupação) | 16.54 | 16.54 | 0.00 |
| QR | Gap q10 (%) | -8.18 | -5.68 | 2.50 |
| QR | Gap q50 (%) | -8.01 | -5.37 | 2.64 |
| QR | Gap q90 (%) | -11.98 | -8.69 | 3.29 |
| RIF | % retornos q10 | 33.75 | 29.34 | -4.42 |
| RIF | % retornos q50 | 21.93 | 24.26 | 2.33 |
| RIF | % retornos q90 | 12.15 | 9.28 | -2.87 |
| Interseccional | Gap Mulher Branca (%) | 19.73 | 19.94 | 0.21 |
| Interseccional | Gap Homem Negro (%) | 56.25 | 56.36 | 0.11 |
| Interseccional | Gap Mulher Negra (%) | 80.62 | 80.68 | 0.06 |
| Grupos raça×gênero | OR mulher negra ocp_qualif | 1.330 | 1.306 | -0.023 |
| Grupos raça×gênero | OR mulher negra y_top10 | 0.335 | 0.278 | -0.058 |
| ML | R² XGBoost (teste) | 0.628 | 0.644 | 0.016 |
| Tendência | p da inclinação (WLS) | 0.169 | 0.027 | -0.141 |

## Notas de leitura (03/10/2026)

- **Oaxaca "inalterada" (28,91 / 16,54):** não é robustez. `ob_acesso.csv` é anterior à base
  nova e só é regerado no E6, junto com o relatório. Comparar depois do E6.
- **Desemprego do bairro/UF sem leave-one-out nos números "depois":** a reconstrução da base em
  02/10 perdeu o LOO do desemprego (o das outras médias foi mantido). Impacto medido na base de
  03/10, MQO com UF e ano, erro agrupado por UPA: β_negro −0,06302 nos dois casos (idêntico até a
  5ª casa); β_desemprego −0,00509 → −0,00497 (EP 0,0012); correlação das duas versões 0,9999.
  Decisão do autor (03/10): corrigir o código na origem e NÃO reestimar. Teste novo em
  `checar_escolaridade.py` acusa médias de contexto constantes dentro da UPA.
