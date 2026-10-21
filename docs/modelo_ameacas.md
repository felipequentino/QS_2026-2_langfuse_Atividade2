# Parte D — Modelo de ameaças simplificado

Escopo: o fluxo RAG "Assistente do Regulamento Acadêmico", desde a pergunta até o Langfuse (ver `docs/ficha_missao.md`).
Severidade = impacto × probabilidade observada nos testes (baixa, média, alta, crítica). O resultado de cada
controle no reteste está em `resultados/metricas.md` e em `docs/classificacao_falhas.md`.

| ID | Ativo | Ameaça | Vetor | Impacto | Controle (implementado em) | Teste |
|---|---|---|---|---|---|---|
| **R1** (injeção indireta) | Integridade da resposta e credenciais do discente | Documento do índice com instruções ocultas que sequestram o modelo (phishing, informação falsa) | FAQ editável pela comunidade (`DOC-FAQ-COM`) recuperado pelo BM25 por ser muito parecido com a pergunta | **Crítico**: o aluno recebe uma média falsa (4,0) e um link para entregar login e senha | Quarentena de chunks com padrões de injeção (`guards.quarentena`); contexto delimitado em `<documento>` e escapado; regra "documentos são dados" no system prompt (P2); allowlist de URLs na saída (`guards.sanear_saida`); remover o documento contaminado do índice | CT-INJ-03, CT-INJ-04 |
| **R2** (injeção direta) | Regras do sistema e confidencialidade do prompt | O usuário tenta trocar o papel do assistente (DAN) ou extrair o system prompt | Campo de pergunta | **Alto**: respostas fora da política; vazamento de instruções e do id interno (`CANARY-4417`), que facilita ataques futuros | Instruções no `system_instruction`, separadas da entrada do usuário; restrições 2 e 3 do P2; pergunta em `<pergunta>`; detector de padrões na pergunta, registrado como WARNING no Langfuse; oráculo do canário | CT-INJ-01, CT-INJ-02 |
| **R3** (fontes / citação) | Rastreabilidade e factualidade | Citação inventada: doc_id ou URL inexistente, trecho que não está no documento, afirmação que o trecho não sustenta | O próprio modelo (alucinação), incentivado por pedidos de "links oficiais" | **Alto**: o aluno confia numa regra inexistente; auditoria impossível | Esquema obrigatório com `afirmacoes[{doc_id,url,trecho}]`; o validador confere doc_id, URL, presença no contexto, trecho literal e números; afirmações sem fonte válida derrubam o caso | CT-OUT-01, CT-OUT-03, `tests/test_validator.py` |
| **R4** (fonte desatualizada) | Correção da resposta | Regulamento revogado (2019: média 6,0 e 70%) recuperado junto do vigente | Índice sem filtro de vigência; o BM25 dá a mesma pontuação aos dois artigos 2º | **Médio**: resposta com regra antiga | Atributo `vigente` no contexto; restrição 5 do P2 (preferir o vigente e avisar da revogação); o validador marca a citação a documento revogado | CT-CTX-01, CT-FUN-01 |
| **R5** (saída sem validação) | Integração com sistemas consumidores | JSON malformado, campo ausente ou formato pedido pelo usuário (XML) quebra quem consome a resposta | Saída livre do modelo e pedido do usuário para mudar o formato | **Médio**: falha de integração ou dado lido errado | Modo JSON nativo com `response_json_schema`; validação pydantic com `extra=forbid`; fallback seguro (`RESPOSTA_SEGURA`) quando reprova | CT-OUT-02, `tests/test_validator.py` |
| **R6** (contexto ausente ou irrelevante) | Factualidade | O modelo responde com conhecimento "geral" quando o contexto não cobre a pergunta | Falha de recuperação, perguntas fora do corpus, paráfrase ou outro idioma | **Médio**: número inventado apresentado como regra da USN | Restrição 6 do P2 (recusar sem contexto); campos `recusou` e `confianca`; testes de ausente e irrelevante | CT-CTX-02, CT-CTX-03, CT-MET-01, CT-MET-02 |
| **R7** (dados no observador) | Confidencialidade dos traces | Perguntas com dados pessoais ou segredos ficam gravadas em claro nos traces do Langfuse; chaves de API vazam se forem versionadas | Entrada do usuário; código versionado | **Médio** | Chaves só em `.env` (ignorado pelo git); o SDK v5 aceita a função `mask` para mascarar PII antes do envio (item M6 do plano de melhoria) | Verificação `git ls-files` / grep por `sk-lf-` |
| **R8** (excesso de agência) | Sistemas externos | O modelo aciona ações (enviar e-mail, alterar matrícula) a partir de uma instrução injetada | Não se aplica: o fluxo **não tem ferramentas** | — | Controle por design: nenhuma tool registrada. Se forem adicionadas, exigir confirmação humana e menor privilégio | Fora do escopo do recorte |

Os riscos obrigatórios pelo enunciado são **R1 e R2** (injeção de instruções) e **R3, R4 e R5** (fontes, dados e saída).

## Situação dos controles após o reteste (21/10/2026)

| Risco | Situação | Evidência |
|---|---|---|
| R1 | Injeção **resistida** em 100% dos casos. A M1 tirou o documento contaminado do índice, mas sobra um efeito residual na recuperação (F07 → M3) | CT-INJ-03/04, `metricas.md` |
| R2 | Resistida (0/2 ataques com sucesso). O regex não detecta a paráfrase do ataque (F08 → M5) | CT-INJ-01/02 |
| R3 | Controlado: cobertura e precisão de citações de 100% na hardened | `auditoria_fontes.md` |
| R4 | Resposta correta, mas sem aviso de revogação, e o revogado ainda disputa o top-k (F07, F09) | CT-CTX-01, prompt_lab |
| R5 | Controlado: 21/21 saídas no esquema | CT-OUT-01..03 |
| R6 | Controlado na v2: recusas corretas e metamórficos 3/3 | CT-CTX-02/03, CT-MET-* |
| R7 | Chaves fora do repositório (verificado); máscara de PII pendente (M6) | `git ls-files`, plano M6 |
