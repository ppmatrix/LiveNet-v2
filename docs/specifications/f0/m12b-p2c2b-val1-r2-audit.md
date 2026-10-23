# M1.2B-P2C-2B-VAL1-R2 — Confirmação offline de IMP1-FIX1

## Resultado global

**APROVADO no âmbito exclusivamente offline.** FIX1-A, FIX1-B e FIX1-C
aprovadas. As oito regressões VAL1 passam sem alterações às suas asserções.
Suite relevante: **355 pass, 0 fail, 0 skip**. Não foram identificados novos
defeitos neste âmbito: 0 críticos, 0 altos, 0 médios e 0 baixos.

Esta confirmação não demonstra prontidão operacional, exclusividade externa,
recuperação real ou autorização para executar migrações. O relatório VAL1
original permanece como registo histórico da reprovação anterior a FIX1.

## Âmbito, fontes e método

Auditoria realizada em main, HEAD
22501be02fb3db1debf0b075fd254a120b2d1236, preservado durante a execução.
Staging vazio no início e no fim. Lidas as oito fontes indicadas no pedido:
relatórios VAL1/FIX1, contrato IMP1, dois módulos e três ficheiros de testes.
Revisão dos contratos, transições PRECHECK até CLOSED, exceções, importações,
guardas e testes negativos; reprodução dos testes existentes em memória.

Snapshot SHA-256 das oito fontes antes dos testes, comparado no final.
Nenhuma fonte existente foi modificada. Os 31 hashes protegidos anteriores,
incluindo os 15 ficheiros AUTH-03, coincidem. O manifesto não foi atualizado.
Nenhum segredo foi lido ou criado.

Não houve PostgreSQL real, Docker operacional, Alembic operacional, SQL,
DDL, locks reais, alterações de ACL/roles/Compose, ativação, commit ou push.
Os testes de metadata usam objetos e mocks locais; não instalam schemas.
Os mocks de fronteiras I/O recusam chamadas antes de qualquer operação real.

## FIX1-A — APROVADA

Evidência em scripts/postgres/m12b_security_adapters.py:132 e
scripts/postgres/m12b_security_coordinator.py:119:

- OperationRegistry é partilhado pelos coordenadores do mesmo cenário.
  claim() exige REGISTERED e é executado antes de consultar adaptadores.
- lookup() não cria registos. Binding desconhecido, registo ausente ou
  indisponível não concedem permissão. Identidade do registo/binding é retida.
- CLOSED, BLOCKED e ROLLED_BACK são terminais; RUNNING e commit incerto
  impedem nova tentativa e exigem reconciliação. Reconciliation apenas leva
  RECONCILE_REQUIRED a RECONCILED, também terminal; não reabre a operação.
- Falha de finalização impede publicar CLOSED; finish() valida autoridade,
  claim exata e estado RUNNING (coordinator.py:87 e :258).

Testes: test_val1_a01_same_operation_cannot_be_retried_with_new_coordinator
(success e uncertain_commit), test_fix1_shared_registry_terminal_success_blocks_new_coordinator_and_old_evidence,
test_fix1_uncertain_operation_requires_explicit_reconciliation_and_never_reopens,
test_fix1_missing_or_unreadable_registry_is_never_permission_to_retry e testes
de claim, identidade/substituição do registo e falha de finalização.
Verificam ausência de novos eventos/commit nas tentativas recusadas.

Risco residual documentado: registo síncrono em memória, sem persistência entre
processos/reinícios ou garantia concorrente entre threads. Novo cenário é outro
ensaio sintético; não autoriza repetir uma migração real. RUNNING após falha de
armazenamento continua bloqueado, sem reparação automática. Reconciliação e
durabilidade operacionais continuam por implementar/demonstrar.

## FIX1-B — APROVADA

Evidência em scripts/postgres/m12b_security_adapters.py:363 e :420:

- issue() valida tipo exato, binding por identidade, timestamps finitos e TTL
  antes da emissão. Exige a própria InspectionProof guardada pelo inspector.
- Valida sessão aberta e role inspector, chave/posse do lock, fingerprint
  hexadecimal esperado e continuidade. Binding liga operação, destino e digest;
  substituições ou cópias da inspeção são recusadas.
- Handoff expira em min(agora + 5 segundos, expiração da inspeção).
  Não renova a observação de origem; o prazo é validado antes da exposição.
- consume() exige a instância emitida e marca-a utilizada antes da validação.
  Revalida prazo, fingerprint e continuidade; consumo falhado também impede replay.

Testes: quatro variantes de test_val1_a02_issue_does_not_launder_inspection_binding_or_expiry,
test_fix1_handoff_cannot_outlive_source_inspection,
test_fix1_copied_inspection_is_not_an_issued_observation,
test_fix1_issue_checks_fields_even_on_issued_inspection e testes de tipo,
TTL, releitura lenta e consumo single-use.

As evidências são sintéticas. Os testes
test_synthetic_evidence_never_authorizes_existing_executor e
test_simulation_does_not_create_an_operational_entry_point confirmam que
RecoveryProof/SimulationResult não autorizam o executor e que execute()
recusa mesmo com a primeira guarda substituída por mock.
Risco residual: estas identidades de objetos não são assinaturas, credenciais
ou atestação PostgreSQL. O digest é um dado validado do cenário, sem prova de
correspondência operacional às fontes ou ao catálogo real.

## FIX1-C — APROVADA

Evidência em scripts/postgres/m12b_security_adapters.py:61, :454 e :576,
e scripts/postgres/m12b_security_coordinator.py:223:

- _cleanup_once marca cada ação antes da tentativa, conserva erros e permite
  tentar ações independentes. Não repete unlock/close já tentados.
- Falha de unlock não impede close físico do inspector. As duas sessões
  administrativas são fechadas independentemente; verificador e migrator têm
  o mesmo controlo de tentativa única.
- CoordinationFailed conserva a exceção original; CleanupIssue regista ação
  e classe do erro secundário. Mensagens/repr de saída não interpolam mensagens
  de drivers; contexto apresentado é suprimido. original_error é diagnóstico
  interno e não deve ser serializado ou registado indiscriminadamente.
- Falha de limpeza, commit incerto ou confirmação de libertação perdida levam
  a RECONCILE_REQUIRED. CLOSED exige provas finais, recursos fechados,
  libertação confirmada e finalização do registo. Ownership só ocorre depois
  da verificação pós-commit; incerteza não é apresentada como rollback confirmado.

Testes: dois test_val1_a03, test_fix1_unlock_failure_closes_once_and_retains_original,
test_fix1_unlock_and_close_failures_are_both_recorded_without_retry,
test_fix1_workflow_error_is_preserved_when_multiple_cleanup_actions_fail,
test_fix1_multiple_administrative_close_failures_are_attempted_independently,
test_fix1_second_migrator_role_close_failure_does_not_duplicate_attempts,
test_fix1_unconfirmed_window_release_is_never_closed e falhas nas transições.

Risco residual documentado: uma tentativa de close falhada pode deixar recurso
aberto; o modelo não presume libertação nem faz retry automático. Requer futura
reconciliação operacional. Fecho físico confirmado modela libertação do lock de
sessão mesmo se unlock falhar, mas o erro continua a impedir CLOSED.

## Regressões e isolamento

O ficheiro test_m12b_operational_audit.py conserva o SHA-256 anterior a FIX1:

```text
cc00c9888e1d4f05048b115d85d633b3d79d4872d3e42775fed765258def2c6d
```

O relatório VAL1 também permanece byte a byte igual. Comparação com os hashes
pré-FIX1 demonstra que os dois ficheiros de testes IMP1 conservam integralmente
o prefixo original: apenas foram acrescentados 3915 e 9855 bytes, respetivamente
em adapters e coordination. Asserções VAL1 não foram enfraquecidas; sem novos
skip/xfail. Todos estes ficheiros ficaram inalterados durante VAL1-R2.

Não foi identificado caminho operacional nos módulos IMP1: sem CLI, construção
de ligações, execução SQL/Alembic/Docker ou leitura de credenciais. Tipos exatos
e cenário comum recusam adaptadores arbitrários; execute() é separado de
simulate() e termina em recusa. SimulationResult mantém simulated=True e
app_ready=False. Bootstrap é uma identidade administrativa sintética explícita,
sem fallback para substituir inspector/migrator.

O relógio injetável e os pontos de injeção de falhas são instrumentos do fake.
Os testes I/O e a revisão estática não constituem sandbox contra código Python
hostil ou prova formal de ausência de todos os comportamentos possíveis.

## Testes reproduzidos

| Execução | Pass | Fail | Skip | Resultado |
| --- | --- | --- | --- | --- |
| Oito casos VAL1 anteriormente falhados | 8 | 0 | 0 | 0.75s; 7 deselected |
| Suite offline completa relevante | 355 | 0 | 0 | 2.36s; inclui os oito casos |

As contagens sobrepõem-se; não correspondem a 363 testes distintos.
Comandos executados no repositório:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend .venv/bin/python -m pytest -q -p no:cacheprovider scripts/postgres/tests/test_m12b_operational_audit.py -k 'val1_a01 or val1_a02 or val1_a03'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend .venv/bin/python -m pytest -q -p no:cacheprovider --tb=short scripts/postgres/tests/test_m12b_operational_audit.py scripts/postgres/tests/test_m12b_operational_adapters.py scripts/postgres/tests/test_m12b_operational_coordination.py backend/tests/test_security_migration.py scripts/postgres/tests/test_m12b_security_migration.py scripts/postgres/tests/test_m12b_security_execution.py scripts/postgres/tests/test_m12b_privilege_review.py scripts/postgres/tests/test_m12b_inspection_handoff.py scripts/postgres/tests/test_auth03_alembic_executor.py::test_operations_block_before_external_access scripts/postgres/tests/test_auth03_alembic_executor.py::test_valid_future_plans_still_cannot_execute
```

## Integridade e validação final

15/15 ficheiros AUTH-03 preservados por SHA-256, dentro dos 31 protegidos.
Compara-se a integridade com os hashes anteriores, sem atualizar o manifesto
ou afirmar uma nova validação operacional do bundle. env.py, modelos M1.2A,
Compose e executor existente permanecem intactos relativamente à entrada.
A modificação de env.py visível em Git é preexistente.

operation_gate() mantém a recusa incondicional de mutações
(auth03_alembic_executor.py:56). ExecutionAuthorization.execution_enabled=False
e require_execution_authorization recusa execução
(m12b_security_migration.py:54 e :216), corroborado por testes offline.
HEAD preservado; staging vazio; git diff --check sem erros e verificação
adicional de whitespace do novo relatório sem erros.
Único ficheiro criado nesta etapa: este relatório. Sem alterações a código/testes.

## Recomendação e pendências para retoma

Recomenda-se consolidação de IMP1/FIX1 como implementação validada offline,
mediante pedido próprio de revisão/staging com lista explícita de ficheiros.
Nenhum commit foi efetuado nesta auditoria. A aprovação não autoriza VAL2,
provisionamento, migração, ativação ou início de funcionalidades.

Preservar para futura retoma de M1.2B:

1. Adaptadores PostgreSQL permanentes separados por identidade, atestação real
   de destino/fontes e integração revista com o executor existente.
2. Exclusividade contra escritores externos (P2B-D03) e recuperação administrativa
   independente demonstrada (P2B-D04); locks sintéticos não cumprem esses requisitos.
3. Registo/coordenação duráveis, concorrência operacional e reconciliação de
   catálogo/commit incerto, sem reabertura automática de operações anteriores.
4. Continuidade da inspeção até ao fecho administrativo (P2B-D01), ownership/ACL
   reais, comparação física independente e revogações atómicas verificadas.
5. Testes PostgreSQL/locks/timeouts/recuperação sujeitos a autorização específica.
6. Decisão técnica posterior sobre DML da app, FOR UPDATE e auditoria (P2B-D05).
   Esta aprovação não torna a API pronta para uso real.

## git status --short final

```text
 M backend/migrations/env.py
?? backend/migrations/versions/f067a01a7230_create_authorization_integrity_anchors.py
?? backend/tests/test_authorization_anchor_integration.py
?? backend/tests/test_authorization_anchor_migration.py
?? backend/tests/test_authorization_anchor_safety.py
?? compose.auth03-executor.yaml
?? compose.auth03-test.yaml
?? compose.m12b-test.yaml
?? docs/specifications/f0/auth03-alembic-executor.md
?? docs/specifications/f0/auth03-integration-preparation.md
?? docs/specifications/f0/m12b-p2c2a-r3-operational-preflight.md
?? docs/specifications/f0/m12b-p2c2b-imp1-fix1-report.md
?? docs/specifications/f0/m12b-p2c2b-imp1-offline-coordinator.md
?? docs/specifications/f0/m12b-p2c2b-val1-offline-audit.md
?? docs/specifications/f0/m12b-p2c2b-val1-r2-audit.md
?? scripts/postgres/auth03_alembic_executor.py
?? scripts/postgres/auth03_executor.Dockerfile
?? scripts/postgres/auth03_executor.Dockerfile.dockerignore
?? scripts/postgres/auth03_executor.example.json
?? scripts/postgres/auth03_executor_integrity.json
?? scripts/postgres/m12b_security_adapters.py
?? scripts/postgres/m12b_security_coordinator.py
?? scripts/postgres/tests/test_auth03_alembic_executor.py
?? scripts/postgres/tests/test_m12b_operational_adapters.py
?? scripts/postgres/tests/test_m12b_operational_audit.py
?? scripts/postgres/tests/test_m12b_operational_coordination.py
```
