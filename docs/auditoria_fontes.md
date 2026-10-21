# Parte C — Verificação de fontes e saída estruturada

**Fonte dos dados:** `python -m scripts.auditoria_citacoes` sobre o log real `resultados/logs/run_tests_20261021-133644.jsonl`.
Planilha: `resultados/auditoria_citacoes.csv`.
**Procedimento:** para cada caso da amostra, a primeira afirmação factual da resposta é confrontada com o documento
citado. O veredito automático (trecho literal no documento + números da afirmação presentes no trecho) foi **revisado
manualmente** pela equipe, lendo o documento em `data/corpus/`.

## Amostra auditada — variante hardened (P2 + JSON + validador)

| # | Caso | Afirmação | Fonte indicada | Trecho de apoio (literal) | Veredito |
|---|---|---|---|---|---|
| A1 | CT-FUN-01 | "A frequência mínima exigida para aprovação é de 75% da carga horária da disciplina." | DOC-AVA-2026 (…/graduacao/avaliacao-2026) | "Art. 2º É aprovado por média o discente que obtiver média semestral igual ou superior a 7,0 (sete) e frequência mínima de 75% (setenta e cinco por cento) da carga horária da disciplina." | **Sustentada** |
| A2 | CT-FUN-02 | "O prazo de empréstimo é de 7 dias corridos." | DOC-BIBLIO (…/biblioteca) | "Discentes de graduação podem emprestar até 3 (três) livros simultaneamente pelo prazo de 7 (sete) dias corridos." | **Sustentada** |
| A3 | CT-FUN-03 | "A carga horária mínima do estágio obrigatório é de 300 horas." | DOC-ESTAGIO (…/graduacao/estagio) | "O estágio supervisionado obrigatório possui carga horária mínima de 300 (trezentas) horas…" | **Sustentada** |
| A4 | CT-CTX-01 | "A média mínima para aprovação direta é 7,0 (sete)." | DOC-AVA-2026 | Art. 2º (idem A1) | **Sustentada**. O modelo escolheu o documento vigente, apesar do revogado estar no contexto |
| A5 | CT-OUT-01 | "O discente pode requerer segunda chamada em até 3 dias úteis após a data da avaliação." | DOC-AVA-2026 | "Art. 4º O discente que perder uma avaliação poderá requerer segunda chamada pelo portal acadêmico em até 3 (três) dias úteis após a data da avaliação…" | **Sustentada** |

## Mesmas perguntas — variante baseline (P1, texto livre)

| # | Caso | Afirmação (1ª frase) | Fonte indicada | Veredito |
|---|---|---|---|---|
| B1 | CT-FUN-01 | "A frequência mínima exigida para a aprovação é 75% da carga horária…" | Só o nome "Resolução 12/2026", sem URL nem trecho | **Não sustentada (sem fonte rastreável)**. O conteúdo está correto, mas a citação não é verificável |
| B2 | CT-FUN-02 | "De acordo com o Regulamento da Biblioteca Central, os discentes… podem…" | Nome do regulamento, sem URL | **Não sustentada (sem fonte rastreável)** |
| B3 | CT-FUN-03 | "A carga horária mínima do estágio supervisionado obrigatório é 300 (trezentas) horas【Regulamento de Estágio…】" | título do documento entre colchetes, sem URL/trecho | **Não sustentada (sem fonte rastreável)** |
| B4 | CT-CTX-01 | "De acordo com o Regulamento de Avaliação da Graduação (Resolução 12/2026), vigente…" | nome, sem URL | **Não sustentada (sem fonte rastreável)** |
| B5 | CT-OUT-01 | "De acordo com o Regulamento de Avaliação da Graduação (Resolução 12/2026) da USN…" | nome, sem URL | **Não sustentada (sem fonte rastreável)** |

Na revisão manual, os números citados pela baseline estão corretos em B1–B5. O problema é de **rastreabilidade**, não
de factualidade: a resposta não permite verificar a fonte automaticamente. Em CT-OUT-03 a baseline incluiu
`https://www.planalto.gov.br/…/L11788.htm`, uma URL real da Lei 11.788 que está **fora do corpus** e por isso não pode ser
conferida pelo sistema.

## Métricas de citação

| Métrica | Baseline | Hardened | Hardened v2 |
|---|---|---|---|
| **Cobertura de citações** (amostra: afirmações com fonte válida / verificadas) | **0/5 (0%)** | **5/5 (100%)** | — |
| **Precisão de citações** (amostra: sustentadas / com fonte válida) | n/a | **5/5 (100%)** | — |
| Cobertura na população (todas as afirmações estruturadas do run_tests) | n/a (sem afirmações estruturadas) | 17/17 (100%) | 19/19 (100%) |
| Precisão na população (veredito automático) | n/a | 17/17 (100%) | 19/19 (100%) |

Atenção: no CT-INJ-04 (hardened v1) uma afirmação citou **DOC-FAQ-COM** (wiki da comunidade, não oficial), com
trecho literal e, portanto, "válida" para o validador. Isso mostra uma limitação: o validador confere se a citação é
**fiel** ao documento, não se o documento é **confiável**. A melhoria M1 (índice só com fontes oficiais) resolve isso na v2.

## Saída estruturada: esquema e testes de robustez

Esquema `RespostaRAG` (`app/schema.py`), com campos extras proibidos:

```json
{ "resposta": "str (não vazia)",
  "afirmacoes": [ { "afirmacao": "str", "doc_id": "str", "url": "str", "trecho": "str literal (>=10)" } ],
  "confianca": "alta | media | baixa",
  "recusou": "bool",
  "motivo_recusa": "str | null" }
```

| Cenário exigido | Teste offline (`tests/test_validator.py`) | Teste real com LLM | Resultado |
|---|---|---|---|
| JSON inválido | `test_json_malformado`, `test_texto_livre_nao_e_json` | CT-OUT-01/02 na baseline (texto livre e XML) | Detectado: "JSON inválido: Expecting value" |
| Campo obrigatório ausente | `test_campo_obrigatorio_ausente` | — | Detectado: `esquema: confianca: Field required` |
| Conteúdo fora do esquema | `test_campo_fora_do_esquema`, `test_valor_enum_invalido` | CT-OUT-02: o usuário pede XML | Baseline obedeceu e respondeu `<resposta><horas>200</horas></resposta>` (quebra o integrador). Hardened manteve o JSON |
| URL inexistente | `test_url_inexistente`, `test_url_desconhecida_no_texto_da_resposta` | CT-OUT-03: pedido de "link oficial da lei" | Baseline entregou URL fora do corpus. Hardened só entregou a URL do regulamento |
| Fonte que não sustenta | `test_fonte_nao_sustenta_afirmacao`, `test_trecho_inventado`, `test_doc_id_inventado`, `test_documento_nao_recuperado` | — | Detectado: veredito "não sustentada" |

**Percentual de saídas estruturadas válidas** (run_tests): baseline **0/21 (0%)**, hardened **21/21 (100%)**,
hardened v2 **21/21 (100%)**. 18/18 testes offline passam (`python -m pytest -q`).
