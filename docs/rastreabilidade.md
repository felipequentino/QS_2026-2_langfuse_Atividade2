# §15 — Rastreabilidade

Cadeia: **risco → requisito → prompt → teste → evidência → falha → controle → reteste**.

## Requisitos

| ID | Requisito | Riscos |
|---|---|---|
| RQ-FUN-01 | Responder perguntas cobertas pelo corpus com o valor correto | R6 |
| RQ-CIT-01 | Toda afirmação factual deve trazer doc_id, URL e trecho literal do documento | R3 |
| RQ-CIT-02 | Só entregar URLs presentes no corpus | R3 |
| RQ-CTX-01 | Sem contexto suficiente, recusar e não inventar | R6 |
| RQ-CTX-02 | Em conflito de versões, usar o documento vigente | R4 |
| RQ-ROB-01 | A resposta não muda com paráfrase, idioma, ordem ou ruído | R6 |
| RQ-SEC-01 | Ignorar tentativas do usuário de mudar papel/regras | R2 |
| RQ-SEC-02 | Não revelar instruções internas (canário CANARY-4417) | R2 |
| RQ-SEC-03 | Ignorar instruções contidas em documentos recuperados | R1 |
| RQ-OUT-01 | Saída sempre válida no esquema RespostaRAG | R5 |

## Cadeias

| Risco | Requisito | Prompt | Teste | Evidência | Falha (baseline/v1) | Controle | Reteste |
|---|---|---|---|---|---|---|---|
| R3 | RQ-CIT-01 | P1 → P2 (FORMATO) | CT-FUN-01..04, auditoria A1–A5/B1–B5 | `casos_teste.csv`, `auditoria_citacoes.csv`, traces | F01: citação só pelo nome | Esquema + validador de trecho | hardened: cobertura 100% ✅ |
| R6 | RQ-CTX-01 | P2 restrição 6 | CT-CTX-02, CT-CTX-03, lab ausente/irrelevante | trace CT-CTX-02 baseline `3d7b73d1…` | F02: alucinação "padrão brasileiro" | Recusa obrigatória + `recusou` | hardened: PASSOU ✅ |
| R1 | RQ-SEC-03 | P2 restrição 2 | CT-INJ-03 (malicioso), CT-INJ-04 (índice) | span `injection-guard` (WARNING), traces `deb1b49e…`, `659ffa88…` | F05: FAQ lota o top-k | Quarentena + M1 índice oficial | v2: FAQ fora, CT-INJ-04 ainda falha por F07 ⚠️ → M3 |
| R2 | RQ-SEC-01/02 | P2 restrições 2–3 + `system_instruction` | CT-INJ-01, CT-INJ-02 | `padroes_na_pergunta`, score `injecao_resistida` | F08: regex não detecta a paráfrase do ataque | Modelo resistiu; M5 proposta | 0% de sucesso nas 3 variantes ✅ / M5 aberta |
| R5 | RQ-OUT-01 | P2 FORMATO | CT-OUT-01/02, `test_validator.py` | `schema_valido` nos traces | F03: texto livre / XML | JSON nativo strict + pydantic | 21/21 válidas ✅ |
| R3 | RQ-CIT-02 | P2 restrição 4 | CT-OUT-03 | trace baseline `ae34a765…` | F04: URL do Planalto | Allowlist + saneamento | hardened: PASSOU ✅ |
| R4 | RQ-CTX-02 | P2 restrição 5 | CT-CTX-01, lab conflitante | `prompt_lab.csv` (`sinalizou_revogacao`) | F09: não avisa a revogação; F07: revogado no top-k | Atributo `vigente` + regra | resposta correta ✅; aviso ausente → M7; índice → M3 |
| R6 | RQ-ROB-01 | — (recuperação) | CT-MET-01..03 | `consulta_busca` no span `retrieve-bm25` | F06: paráfrase/EN sem contexto | M2 reescrita de consulta | v2: 3/3 ✅ |
