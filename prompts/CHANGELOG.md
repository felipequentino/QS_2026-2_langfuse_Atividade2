# Histórico de versões dos prompts

Os prompts são artefatos versionados: cada alteração gera nova versão (semver) neste arquivo e é sincronizada
com o Langfuse Prompt Management por `python -m scripts.sync_prompts` (nomes `av2-P1`, `av2-P2`, `av2-P3`).
As gerações no Langfuse ficam vinculadas à versão do prompt usada.

| Versão | Prompt | Data | Mudança | Motivação |
|---|---|---|---|---|
| 1.0.0 | P1 — instrução direta | 2026-10-21 | Versão inicial | Linha de base (como um protótipo ingênuo faria) |
| 1.0.0 | P2 — estruturado | 2026-10-21 | Versão inicial: objetivo, contexto, restrições de segurança, formato JSON | RQ-SEC-01, RQ-CIT-01, RQ-OUT-01 |
| 1.0.0 | P3 — poucos exemplos | 2026-10-21 | Versão inicial: regras curtas + 3 exemplos | Comparar exemplos vs. regras explícitas |
