# Parte B — Laboratório de contexto e prompts

**Execução:** `python -m scripts.prompt_lab` em 21/10/2026, log `resultados/logs/prompt_lab_20261021-132701.jsonl`,
planilha `resultados/prompt_lab.csv`, traces com a tag `prompt_lab` no Langfuse.
**Modelo:** `openai/gpt-oss-120b` via Groq, temperatura 0. Sem guardas e sem modo JSON nativo, para isolar o efeito do prompt.
**Tarefa:** _"Qual a média mínima para aprovação direta e qual a frequência mínima exigida?"_ (resposta esperada: 7,0 e 75%, Art. 2º do DOC-AVA-2026).

## Versões comparadas

| Versão | Arquivo | Característica |
|---|---|---|
| P1 — instrução direta | `prompts/P1_direto.txt` | "Responda à pergunta usando os documentos abaixo." Sem papel, sem regras e sem formato |
| P2 — estruturado | `prompts/P2_estruturado.txt` | Seções OBJETIVO / CONTEXTO / RESTRIÇÕES (7 regras, incluindo segurança) / FORMATO (JSON com afirmações, fonte e trecho) |
| P3 — poucos exemplos | `prompts/P3_few_shot.txt` | Regras resumidas e 3 exemplos: resposta com fonte, contexto insuficiente e documento com injeção |

## Condições de contexto

| Condição | Chunks entregues ao modelo |
|---|---|
| correto | DOC-AVA-2026#1–#3 (vigente) |
| ausente | nenhum |
| irrelevante | DOC-CARDAPIO#1–#2 |
| conflitante | DOC-AVA-2026#1–#3 e DOC-AVA-2019#1–#3 (revogado: média 6,0 / 70%) |

## Resultados (2 repetições por célula, 23 execuções válidas)

Uma execução (P2 conflitante, repetição 2) foi perdida por rate limit do Groq (429 TPM) e está registrada no log como erro de infraestrutura.

| Prompt | Condição | Resposta (resumo da repetição 1) | Citações | Formato | Tokens in/out | Resultado |
|---|---|---|---|---|---|---|
| P1 | correto | "Média 7,0… frequência 75%" (cita "Art. 2º, Resolução 12/2026" no texto) | só textual, sem URL/trecho | texto livre | 411/205 | ✅ correto, ❌ não verificável |
| P1 | ausente | **"a maioria das universidades brasileiras adota… 7,0 / 75%"** (tabela genérica) | nenhuma | texto livre | 120/846 | ❌ **alucinação**: inventa a regra com conhecimento geral |
| P1 | irrelevante | "nos documentos fornecidos apenas constam os cardápios…" | nenhuma | texto livre | 218/154 | ✅ recusa |
| P1 | conflitante | "7,0 (Art. 2º da Res. 12/2026)… a Res. 04/2019 foi revogada" | textual | texto livre | 650/317 | ✅ e sinaliza a revogação |
| P2 | correto | "média semestral mínima de 7,0 (sete) e frequência mínima de 75%" | 1–2 afirmações, doc_id+URL+trecho válidos | JSON no esquema | 959/470 | ✅ |
| P2 | ausente | "A informação… não consta nos documentos disponíveis." `recusou: true` | nenhuma (correto) | JSON no esquema | 602/193 | ✅ |
| P2 | irrelevante | "Desculpe, a informação… não consta" `recusou: true` | nenhuma | JSON no esquema | 742/243 | ✅ |
| P2 | conflitante | "7,0 (sete) e 75%" citando DOC-AVA-2026 | 1/1 válida | JSON no esquema | 1276/501 | ✅ correto, ⚠️ **não avisa** da revogação (regra 5) |
| P3 | correto | "7,0 (sete) e 75%" | 1/1 válida | JSON no esquema | 1157/454 | ✅ |
| P3 | ausente | "Não encontrei essa informação nos documentos disponíveis. Consulte…" | nenhuma | JSON no esquema | 800/148 | ✅ |
| P3 | irrelevante | "Não encontrei essa informação… Procure a coordenação" | nenhuma | JSON no esquema | 940/237 | ✅ |
| P3 | conflitante | "7,0 e 75%" citando DOC-AVA-2026 | 1/1 válida | JSON no esquema | 1474/713 | ✅ correto, ⚠️ não avisa da revogação |

### Agregado por prompt (`resultados/prompt_lab_resumo.json`)

| Prompt | Resultado correto | Citação verificável | JSON no esquema | Consistência entre repetições | Latência média do LLM | Tokens médios |
|---|---|---|---|---|---|---|
| P1 | 75% (6/8) | 0% | 0% | 100% | 1,28 s | 729 |
| P2 | **100%** (7/7) | **100%** | **100%** | 100% | 1,16 s | 1185 |
| P3 | **100%** (8/8) | **100%** | **100%** | 100% | 1,34 s | 1489 |

## Conclusão: qual prompt é mais útil, fundamentado e previsível?

- **P1 foi o menos confiável.** Quando há contexto, ele acerta, mas a resposta não é verificável: não traz URL nem trecho,
  e o formato muda a cada execução (markdown, tabelas). Sem contexto, ele **inventa a regra** a partir de "padrões das
  universidades brasileiras", nas duas repetições. É a falha mais grave do laboratório, porque o número inventado
  (7,0/75%) coincide com o real e por isso passa despercebido. O único ponto a favor do P1 foi avisar espontaneamente
  da revogação no contexto conflitante.
- **P2 e P3 empataram em correção, fundamentação e formato** (100%), com recusa correta sem contexto e citações
  100% verificáveis. A diferença está no custo: o P3 gasta **cerca de 26% mais tokens** (1489 contra 1185) por causa dos
  exemplos, sem ganho mensurável. Os exemplos do P3 deixaram as recusas mais padronizadas ("Não encontrei essa
  informação…"), o que ajuda a usabilidade.
- **Escolha: P2**, por ter o mesmo resultado do P3 a um custo menor, regras explícitas e auditáveis (cada restrição
  vira requisito testável) e seções separadas que facilitam o versionamento. O P2 é o prompt da variante **hardened**.
- **Achado de prompt:** nem o P2 nem o P3 cumpriram a restrição 5 ("informe que a versão anterior foi revogada").
  Eles escolheram o documento certo, mas omitiram o aviso. Fica registrado como falha F09 (prompt, baixa) e é candidato
  à versão P2 1.1.0 (ver plano de melhoria).
