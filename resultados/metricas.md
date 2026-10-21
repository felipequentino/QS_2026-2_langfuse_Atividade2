# Métricas consolidadas (geradas por `python -m scripts.metricas`)

Modelo: `openai/gpt-oss-120b` · temperatura 0 · log `resultados/logs/run_tests_20261021-133644.jsonl`

## Testes obrigatórios (Parte E)

| Métrica | Baseline (P1, sem controles) | Hardened (P2 + controles) | Hardened v2 (reteste: + M1 índice oficial + M2 reescrita) |
|---|---|---|---|
| Casos aprovados | 4/17 (24%) | 14/17 (82%) | 16/17 (94%) |
| — funcional | 0/4 | 4/4 | 4/4 |
| — contexto | 1/3 | 3/3 | 3/3 |
| — metamorfico | 0/3 | 1/3 | 3/3 |
| — adversarial-direto | 2/2 | 2/2 | 2/2 |
| — adversarial-indireto | 1/2 | 1/2 | 1/2 |
| — saida-estruturada | 0/3 | 3/3 | 3/3 |
| Taxa de sucesso das injeções (menor é melhor) | 0/4 (0%) | 0/4 (0%) | 0/4 (0%) |
| Saídas JSON válidas | 0/21 (0%) | 21/21 (100%) | 21/21 (100%) |
| Saídas válidas no esquema | 0/21 (0%) | 21/21 (100%) | 21/21 (100%) |
| Chunks postos em quarentena | 0 | 5 | 1 |
| Execuções / chamadas ao LLM | 21 / 21 | 21 / 21 | 21 / 38 |
| Latência média / p95 (s) | 1.09 / 1.9 | 1.82 / 3.67 | 2.01 / 3.02 |
| Tokens entrada / saída | 8712 / 5792 | 27135 / 10095 | 28476 / 11281 |

## Citações (Parte C)

| Métrica | Baseline (P1, sem controles) | Hardened (P2 + controles) | Hardened v2 (reteste: + M1 índice oficial + M2 reescrita) |
|---|---|---|---|
| Cobertura de citações na amostra de 5 afirmações | 0/5 (0%) | 5/5 (100%) | — |
| Precisão de citações na amostra (sustentadas / com fonte) | n/a | 5/5 (100%) | — |
| Cobertura na população (todas as afirmações estruturadas) | n/a (texto livre, sem afirmações estruturadas) | 17/17 (100%) | 19/19 (100%) |
| Precisão na população | n/a | 17/17 (100%) | 19/19 (100%) |

## Laboratório de prompts (Parte B)

Pergunta: _Qual a média mínima para aprovação direta e qual a frequência mínima exigida?_ · 23 execuções válidas (3 prompts × 4 contextos × 2 repetições; 1 perdida por rate limit, P2 conflitante r2)

| Prompt | Resultado correto | Citação verificável | JSON no esquema | Consistência entre repetições | Latência média do LLM (s) | Tokens médios |
|---|---|---|---|---|---|---|
| P1 | 75% | 0% | 0% | 100% | 1.28 | 729 |
| P2 | 100% | 100% | 100% | 100% | 1.16 | 1185 |
| P3 | 100% | 100% | 100% | 100% | 1.34 | 1489 |
