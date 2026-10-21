# Evidências

As evidências primárias de cada execução estão versionadas em `resultados/logs/*.jsonl` (saída bruta do modelo,
chunks recuperados, validação, tokens, latência e link do trace) e nos traces do Langfuse Cloud (coluna
`evidencia_trace` de `resultados/casos_teste.csv`).

Capturas de tela do painel do Langfuse a adicionar nesta pasta (a equipe precisa estar logada no projeto):

| Arquivo | O que capturar |
|---|---|
| `01_lista_traces.png` | Lista de traces filtrada pela tag `run_tests` |
| `02_inj03_baseline.png` | Trace CT-INJ-03 [baseline]: FAQ malicioso no span `retrieve-bm25` |
| `03_inj03_hardened.png` | Trace CT-INJ-03 [hardened]: span `injection-guard` em WARNING com `DOC-FAQ-COM#3` em quarentena |
| `04_generation.png` | Generation `llm-generate`: modelo `openai/gpt-oss-120b`, tokens e latência |
| `05_scores.png` | Scores `caso_passou` / `injecao_resistida` |
| `06_prompts.png` | Prompt Management com `av2-P1`, `av2-P2` e `av2-P3` |
