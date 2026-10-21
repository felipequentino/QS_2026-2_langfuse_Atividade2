# Tabela de contribuição individual

A distribuição abaixo é uma proposta e deve ser confirmada pela equipe antes da entrega.

| Integrante | Responsabilidade na AV2 | Artefatos principais |
|---|---|---|
| João Victor Oliveira Moura | Infraestrutura: Langfuse Cloud, `.env`, integração real com o LLM (Groq/Gemini) e instrumentação dos traces | `app/llm.py`, `app/pipeline.py`, `scripts/sync_prompts.py` |
| Bruno Saint Clair Silva Oliveira | Parte A: ficha da missão, fluxo de dados e classificação dos dados | `docs/ficha_missao.md`, `data/corpus/` |
| Gabriel Bastos Pimentel | Parte B: laboratório de prompts (P1, P2, P3 × contextos) e análise comparativa | `prompts/`, `scripts/prompt_lab.py`, `resultados/prompt_lab.csv` |
| João Felipe Quentino | Parte C: auditoria de fontes, esquema e validador de saída estruturada | `app/schema.py`, `app/validator.py`, `tests/test_validator.py`, `docs/auditoria_fontes.md` |
| Gian Glauberty Santos Nascimento | Parte D e §10: modelo de ameaças, classificação de falhas e plano de melhoria | `docs/modelo_ameacas.md`, `docs/classificacao_falhas.md`, `docs/plano_melhoria.md` |
| Leonardo de Souza Aragão | Parte E: casos funcionais, de contexto, metamórficos e adversariais, guardas de injeção e apresentação | `tests/casos.yaml`, `app/guards.py`, `scripts/run_tests.py`, `apresentacao/` |
| Renner do Nascimento Brito | Relatório técnico em PDF, rastreabilidade, revisão ortográfica e edição do vídeo | `relatorio/`, `docs/rastreabilidade.md`, `VIDEO.md` |
