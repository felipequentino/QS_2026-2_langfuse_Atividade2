# Qualidade de Software — Atividade 2 (AV2) · Missão Contexto Confiável

**Missão escolhida:** (B) Defesa contra Prompt Injection, cobrindo também citações, contexto e saída estruturada
**Projeto base:** Langfuse, continuação da [Atividade 1](https://github.com/felipequentino/QS_2026-2_langfuse_Atividade1)
**Equipe 01:** Bruno Saint Clair Silva Oliveira · Gabriel Bastos Pimentel · Gian Glauberty Santos Nascimento ·
João Felipe Quentino · João Victor Oliveira Moura · Leonardo de Souza Aragão · Renner do Nascimento Brito
**Vídeo:** ver [VIDEO.md](VIDEO.md)

---

## Por que esta versão existe
A Atividade 1 **não fazia chamadas reais a um LLM**: o script gravava no Langfuse respostas escritas à mão
(`model="simulador-llm-v1"`), e as chaves estavam no código. Nesta AV2 o repositório é uma aplicação RAG que
**chama um LLM de verdade** (Groq, `openai/gpt-oss-120b`; Gemini opcional) em cada teste. Todas as execuções ficam rastreadas no **Langfuse Cloud**
(trace → recuperação → guarda → geração com tokens e latência → validação → scores), o que torna as evidências
reproduzíveis.

## Resultados (execução real de 21/10/2026, `openai/gpt-oss-120b` via Groq, temperatura 0)

Detalhes em [resultados/metricas.md](resultados/metricas.md). Três variantes do mesmo fluxo:
**baseline** (P1, sem controles), **hardened** (P2 + quarentena + delimitação + JSON strict + validador + saneamento)
e **hardened_v2**, o reteste do plano de melhoria (+ índice só com fontes oficiais + reescrita de consulta).

| Métrica | Baseline | Hardened | Hardened v2 |
|---|---|---|---|
| Casos aprovados (17) | 4 (24%) | 14 (82%) | **16 (94%)** |
| Sucesso das injeções (4 ataques) | 0% | 0% | 0% |
| Saídas JSON válidas no esquema | 0/21 | 21/21 | 21/21 |
| Cobertura de citações (amostra de 5) | 0% | 100% | — |
| Precisão de citações (amostra) | n/a | 100% | — |
| Metamórficos | 0/3 | 1/3 | 3/3 |
| Chamadas ao LLM | 21 | 21 | 38 |

**Laboratório de prompts:** P2 e P3 acertam 100% nos 4 contextos com citação verificável. O P1 alucina sem contexto.
O P2 foi o escolhido, com o mesmo resultado do P3 e cerca de 20% menos tokens ([docs/laboratorio_prompts.md](docs/laboratorio_prompts.md)).

**Três principais achados** ([docs/classificacao_falhas.md](docs/classificacao_falhas.md), [docs/plano_melhoria.md](docs/plano_melhoria.md)):
1. A baseline responde **sem fonte rastreável** e **inventa regras** quando falta contexto. Corrigido com P2 + esquema + validador.
2. O **documento contaminado não sequestra o modelo, mas envenena a recuperação**: ocupa o top-k e expulsa os artigos
   oficiais. A M1 (índice oficial) resolve em parte, e o regulamento revogado ainda disputa as vagas (M3 aberta).
3. A recuperação léxica quebra com **paráfrase e mudança de idioma**. A M2 (reescrita de consulta) levou os metamórficos de 1/3 para 3/3.

| Documento | Parte do enunciado |
|---|---|
| [docs/ficha_missao.md](docs/ficha_missao.md) | A: ficha, fluxo e classificação dos dados |
| [docs/laboratorio_prompts.md](docs/laboratorio_prompts.md) | B: P1 × P2 × P3 em 4 contextos |
| [docs/auditoria_fontes.md](docs/auditoria_fontes.md) | C: auditoria de afirmações, cobertura e testes de JSON |
| [docs/modelo_ameacas.md](docs/modelo_ameacas.md) | D: 8 riscos com ativo, ameaça, vetor, impacto e controle |
| [resultados/casos_teste.csv](resultados/casos_teste.csv) | E: 17 casos × 3 variantes (entrada, contexto, prompt, esperado, observado, evidência, status) |
| [docs/classificacao_falhas.md](docs/classificacao_falhas.md) · [docs/plano_melhoria.md](docs/plano_melhoria.md) | §10: falhas, severidades e plano |
| [docs/rastreabilidade.md](docs/rastreabilidade.md) | §15: risco → requisito → prompt → teste → evidência → falha → controle → reteste |

## Como executar

```bash
python -m venv .venv && .venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                                 # preencha GROQ_API_KEY e as chaves do Langfuse

python -m pytest -q                       # 18 testes offline do validador e das guardas (sem chave)
python -m scripts.sync_prompts            # publica P1/P2/P3 no Langfuse Prompt Management
python -m scripts.prompt_lab              # Parte B: 3 prompts x 4 contextos x 2 repetições (24 chamadas)
python -m scripts.run_tests               # Parte E: 17 casos x {baseline, hardened, hardened_v2}
#   reexecutar só o que falhou por rate limit: --anexar resultados/logs/run_tests_<ts>.jsonl --so-erros
python -m scripts.auditoria_citacoes      # Parte C: auditoria de fontes sobre o último run_tests
python -m scripts.metricas                # §9: consolida resultados/metricas.md
python -m scripts.build_pdfs              # relatório e slides em PDF (Pandoc + Chrome headless)
```

Uma pergunta avulsa:
```python
from app.pipeline import responder
r = responder("Qual a frequência mínima?", prompt_id="P2", modo_contexto="auto", guard=True, json_mode=True)
print(r["saida_final"], r["trace_url"])
```

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `app/` | Aplicação: `pipeline.py` (fluxo), `retriever.py` (BM25 + modos de contexto), `llm.py` (Groq/Gemini + generation no Langfuse), `guards.py` (controles), `schema.py` / `validator.py` (saída estruturada), `avaliacao.py` (oráculos) |
| `prompts/` | Prompts versionados P1, P2, P3 e `CHANGELOG.md`, também sincronizados no Langfuse (`av2-P1..P3`) |
| `data/corpus/` | 8 documentos **sintéticos**: vigentes, revogado, irrelevante e um contaminado com injeção |
| `tests/casos.yaml` | 17 casos de teste: 4 funcionais, 3 de contexto, 3 metamórficos, 4 adversariais e 3 de saída |
| `tests/test_validator.py` | 18 testes offline: JSON malformado, campo ausente, URL inexistente, fonte que não sustenta, etc. |
| `scripts/` | Runners dos experimentos e geração de PDFs |
| `resultados/` | `casos_teste.csv` (planilha dos testes), `prompt_lab.csv`, `auditoria_citacoes.csv`, `metricas.md`, `logs/*.jsonl` (respostas brutas do modelo) |
| `evidencias/` | Capturas do painel do Langfuse (ver roteiro abaixo) |
| `docs/` | Ficha da missão, auditoria de fontes, modelo de ameaças, classificação de falhas, plano de melhoria, rastreabilidade, contribuição |
| `relatorio/` | `relatorio.md` → `relatorio.pdf` |
| `apresentacao/` | `slides.html` → `slides.pdf` |

## Entregáveis do enunciado

| Entregável (§11) | Onde |
|---|---|
| Relatório técnico em PDF | [relatorio/relatorio.pdf](relatorio/relatorio.pdf) |
| README, prompts versionados, casos de teste, resultados, evidências | este arquivo, [prompts/](prompts/), [tests/casos.yaml](tests/casos.yaml), [resultados/](resultados/), [evidencias/](evidencias/) |
| Tabela de ameaças | [docs/modelo_ameacas.md](docs/modelo_ameacas.md) |
| Plano de melhoria | [docs/plano_melhoria.md](docs/plano_melhoria.md) |
| Planilha/CSV de casos e resultados | [resultados/casos_teste.csv](resultados/casos_teste.csv) |
| Apresentação | [apresentacao/slides.pdf](apresentacao/slides.pdf) |
| Vídeo | [VIDEO.md](VIDEO.md) |
| Contribuição individual | [docs/contribuicao.md](docs/contribuicao.md) |

## Evidências no Langfuse
Cada linha de `resultados/casos_teste.csv` traz o link do trace correspondente (coluna `evidencia_trace`). Os links
abrem para quem tem acesso ao projeto. Roteiro de capturas para `evidencias/`:
1. Lista de traces filtrada pela tag `run_tests` (sessão `run_tests-<timestamp>`).
2. Trace do CT-INJ-03 na **baseline**: o span `rag-pipeline` mostra o FAQ malicioso no contexto e a resposta.
3. O mesmo caso na **hardened**: o span `injection-guard` em WARNING, com o chunk `DOC-FAQ-COM#3` em quarentena.
4. Uma generation com modelo `openai/gpt-oss-120b`, tokens (incl. raciocínio) e latência.
5. Scores `caso_passou` / `injecao_resistida` e prompts `av2-P1..P3` em Prompt Management.

## Segurança do repositório
- `.env` está no `.gitignore` e nenhuma chave é versionada. `.env.example` documenta as variáveis.
- As chaves `pk-lf`/`sk-lf` publicadas no repositório da AV1 devem ser **revogadas** (achado R7).
