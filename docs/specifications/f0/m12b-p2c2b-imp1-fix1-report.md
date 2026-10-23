# M1.2B-P2C-2B-IMP1-FIX1 — Correções offline VAL1

## Resultado e âmbito

FIX1 concluído em main, HEAD preservado
22501be02fb3db1debf0b075fd254a120b2d1236. Corrigidos exclusivamente VAL1-A01,
A02 e A03. Os oito testes de regressão VAL1 passam sem qualquer modificação
ao seu ficheiro. Suite final: 355 pass, 0 fail, 0 skip.

Foram lidas as sete fontes obrigatórias, confirmados branch/HEAD/staging e hashes
protegidos e identificadas as oito falhas originais. Sem divergências inesperadas.
Não se estabeleceram ligações PostgreSQL, executou Docker, Alembic, SQL modificador
ou locks reais. Sem credenciais, alterações de roles/ACL/Compose, commit ou push.
Nenhum executor foi ativado. VAL2 e desenvolvimento funcional não foram iniciados.

Ficheiros modificados nesta etapa:

- scripts/postgres/m12b_security_adapters.py
- scripts/postgres/m12b_security_coordinator.py
- scripts/postgres/tests/test_m12b_operational_adapters.py — apenas testes novos
- scripts/postgres/tests/test_m12b_operational_coordination.py — apenas testes novos
- docs/specifications/f0/m12b-p2c2b-imp1-offline-coordinator.md

Ficheiro criado: este relatório.
test_m12b_operational_audit.py e m12b-p2c2b-val1-offline-audit.md foram preservados
byte a byte; o relatório VAL1 continua a ser o registo histórico da reprovação.

## A. Causas confirmadas

| Problema VAL1 | Causa anterior |
| --- | --- |
| A01 / FIX1-A | _started existia só numa instância do coordenador; nova instância reutilizava Binding.operation e repetia o trabalho, mesmo após commit incerto |
| A02 / FIX1-B | issue() copiava sessão/fingerprint e criava binding/prazo novos sem verificar InspectionProof de entrada |
| A03 / FIX1-C | Unlock/fecho eram sequenciais sem isolamento de falhas; a primeira exceção impedia as restantes tentativas e a chamada de limpeza posterior repetia o mesmo erro |

## B. Alterações efetuadas

OperationRegistry e OperationClaim modelam uma autoridade partilhada entre
coordenadores do mesmo cenário. O registo é reclamado antes de consultar
adaptadores e finalizado antes de publicar CLOSED. Identidade do registo e
binding são conservados durante o ciclo.

InspectorAdapter conserva a inspeção emitida e valida-a antes de issue().
O novo handoff não pode ultrapassar o prazo da observação de origem.

_Cleanup tenta cada ação independentemente, uma única vez. Inspector tenta
fecho físico mesmo se unlock falhar; AdministrativeCloser tenta as duas sessões
mesmo que o primeiro fecho falhe. Migrator e PostCommitVerifier também deixam
de repetir close já tentado. CleanupIssue/CleanupError guardam diagnóstico
estruturado; CoordinationFailed conserva a exceção original sem a imprimir.

## C. Contratos e invariantes preservados

- operation_gate() não foi editado e continua a recusar mutações.
- execution_enabled=False; execute() recusa antes de tocar nos adaptadores.
- Simulação distinta de execução, simulated=True e app_ready=False.
- Destino exclusivo, identities inspector/migrator/bootstrap explícitas, sem
  fallback, CLI, credenciais ou integração operacional nova.
- Handoff single-use, binding à operação/destino/digest e TTL máximo 5s;
  fingerprint e continuidade dos locks continuam verificados.
- Commit incerto não provoca repetição ou rollback presumido. Ownership depende
  de durabilidade confirmada; fecho completo é pré-condição de CLOSED.
- Evidências continuam sintéticas. DML da app/FOR UPDATE permanecem pendentes.

## D. Registo de operações partilhado

MemoryScenario recebe OperationRegistry por injeção; o registo default pertence
ao cenário e é usado por todas as instâncias do coordenador sobre esse cenário.
Também pode ser partilhado explicitamente entre cenários de ensaio distintos.

new_binding() cria e regista uma operação genuinamente nova com target/digest
validados e object identity própria. Não existe API de registar novamente um
binding antigo. lookup não cria registos e ausência nunca significa autorização.
claim exige REGISTERED e produz token local de autoridade; finish exige o token
exato e estado RUNNING. Tokens/dataclasses não são credenciais operacionais.

| Estado observado | Comportamento |
| --- | --- |
| REGISTERED | Uma única reclamação permitida |
| RUNNING | Nova instância bloqueada com RECONCILE_REQUIRED; não rouba a operação |
| CLOSED/BLOCKED/ROLLED_BACK | Repetição recusada como BLOCKED |
| RECONCILE_REQUIRED | Repetição recusada; exige avaliação explícita |
| RECONCILED | Terminal; não reabre a operação |
| Registo ausente, vazio, ilegível ou substituído | RECONCILE_REQUIRED, sem consultar adaptadores ou assumir operação nova |

Reconciliation regista referência e resultado de avaliação sintética explícita
para um binding conhecido RECONCILE_REQUIRED. Mesmo confirmed_not_committed não
volta a REGISTERED. Um eventual novo ensaio exige operação/contexto novos.
A mesma instância mantém ainda a sua proteção _started, adicional ao registo.
Falha de finalização impede CLOSED; não é apresentada como sucesso de armazenamento.

## E. Limitações da persistência offline

Registo em memória, síncrono, sem PostgreSQL, ficheiros de persistência ou locks
reais. Não fornece durabilidade entre processos/reinícios nem garantia concorrente
entre threads. Um registo substituído/vazio com o binding antigo falha fechado.
Um cenário novo é um novo ensaio, não autorização para repetir uma migração numa
base real. Novas operações operacionais exigirão observação/reconciliação reais
e armazenamento/coordenação revistos noutra etapa.

Se a finalização falhar e o registo ficar RUNNING, permanece bloqueado para
investigação; não há reparação ou reabertura automática. Referências de avaliação
são dados sintéticos, não comprovação de durabilidade ou recuperação real.

## F. Validação das evidências

Antes de issue(): tipo InspectionProof exato, binding da mesma instância,
operação/destino/digest da autoridade, prazo finito/válido, instância efetivamente
emitida por esse inspector, sessão própria aberta, role inspector, chave/posse
do lock e fingerprint hexadecimal esperado. Campos ausentes, cópias, origem
incompatível, expiração ou fingerprint divergente são recusados.

Prazo do handoff: min(agora + 5s, expires_at da inspeção). Uma inspeção quase
expirada gera um handoff mais curto, nunca renovação. A validade é verificada
antes de expor o handoff; consumo/replay conservam as guardas existentes.
Testes usam relógio injetado, sem esperar pelo relógio real.

## G. Limpeza e reconciliação

Cada adaptador conserva quais ações tentou e os seus erros. Unlock, fecho físico
e cada sessão administrativa são tentados independentemente. Uma segunda chamada
close não repete ações já tentadas; falhas continuam a ser comunicadas ao
coordenador como necessidade de reconciliação.

Existe um único unlock primário explícito por sessão neste protocolo. O teste
de falha num segundo unlock verifica que essa segunda tentativa não é alcançada,
sem inventar unlock transacional: o lock transacional continua a terminar com a
transação modelada. Há também teste de falha no segundo close de role migrator,
que pertence ao verificador físico distinto, sem uma terceira tentativa duplicada.

Se unlock falhar e close físico for confirmado, o fim da sessão liberta o lock
modelado, mas a falha continua a impedir CLOSED. Se ambos falharem, não se presume
lock libertado. Fecho incompleto não liberta automaticamente a janela exterior.
Acknowledgement perdido após tentar libertar a janela exige reconciliação, sem
resultado CLOSED ou declaração de libertação confirmada.

original_error mantém a exceção primária por identidade para inspeção confiável.
str/repr de CoordinationFailed não incluem esse texto; encadeamento apresentado
continua suprimido. cleanup_failures contém apenas nome fixo da ação e classe
da exceção, sem mensagens secundárias. Não serializar original_error ou o seu
traceback para logs: é preservação interna, não sanitização do objeto original.
Falhas secundárias não substituem a falha original.

## H. Resultados dos testes

| Grupo | Pass | Fail | Skip | Observação |
| --- | --- | --- | --- | --- |
| Oito regressões VAL1 selecionadas | 8 | 0 | 0 | 7 controlos não selecionados, não skips; 0.69s |
| Suite completa offline final | 355 | 0 | 0 | 306 anteriores + 15 VAL1 + 34 FIX1; 2.29s |

Os oito casos, sem alterações nas suas asserções ou ficheiro:

1. A01 success — nova instância após sucesso.
2. A01 uncertain_commit — nova instância após commit incerto.
3. A02 other_operation — origem de outra operação.
4. A02 other_target — origem de outro destino.
5. A02 other_digest — digest incompatível.
6. A02 expired — inspeção expirada.
7. A03 unlock failure — fecho físico apesar da falha de unlock.
8. A03 final close failure — fecho administrativo independente.

Suite inclui test_m12b_operational_audit.py, test_m12b_operational_adapters.py,
test_m12b_operational_coordination.py, test_security_migration.py,
test_m12b_security_migration.py, test_m12b_security_execution.py,
test_m12b_privilege_review.py, test_m12b_inspection_handoff.py e as duas guardas
AUTH-03 offline já utilizadas em IMP1/VAL1.

Comando completo documentado em m12b-p2c2b-imp1-offline-coordinator.md.
Seleção explícita das regressões: mesmo ambiente PYTHONDONTWRITEBYTECODE=1,
PYTHONPATH=backend e pytest -q -p no:cacheprovider, com
test_m12b_operational_audit.py -k 'val1_a01 or val1_a02 or val1_a03'.
Sem testes eliminados, assertions reduzidas, skip ou xfail novos.

Os 34 casos adicionais cobrem registo partilhado, estados terminais,
reconciliação explícita, operação nova, prova antiga, armazenamento vazio/ausente/
indisponível/substituído, erro de lookup/finalização, TTL limitado pela origem,
campos inválidos, fecho parcial/múltiplo, erro original com erros secundários,
não duplicação e libertação não confirmada.

## I. Integridade, riscos residuais e Git

Os 31 hashes protegidos, incluindo os 15 ficheiros AUTH-03, mantêm-se iguais.
VAL1 relatório/testes preservados. Sem alteração de Compose, migrações, modelos,
backend/migrations/env.py ou executor security existente. A modificação env.py
no git status é preexistente e mantém o hash anterior.
git diff --check e whitespace adicional dos seis ficheiros desta etapa sem erros.
main/HEAD preservados e staging vazio.

Persistem os limites offline: atestação física, isolamento, exclusividade externa
P2B-D03, recuperação P2B-D04, adaptadores operacionais e catálogo real ainda não
demonstrados. Modelos e registos sintéticos não são autorização de migração.
Não há alteração de AUTH-BOOT, operação privilegiada ou DML/FOR UPDATE.

## J. Recomendação

Recomendar aprovação técnica de FIX1 no seu âmbito offline: oito regressões
resolvidas e suite verde. Solicitar nova auditoria por pedido separado antes de
considerar IMP1 consolidado como validado; este relatório não substitui revisão
independente nem altera o resultado histórico VAL1.
Não iniciar VAL2, commit, migração ou desenvolvimento funcional automaticamente.

git status --short final:

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

Só o relatório FIX1 foi criado nesta execução; os restantes ficheiros já existiam.
