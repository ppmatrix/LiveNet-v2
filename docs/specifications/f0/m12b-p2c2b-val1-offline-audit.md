# M1.2B-P2C-2B-VAL1 — Auditoria exclusivamente offline

**Resultado global: REPROVADO para consolidação IMP1 como implementação validada.**
Foram identificados três problemas: 0 CRÍTICOS, 1 ALTO, 2 MÉDIOS e 0 BAIXOS.
Não foi encontrado caminho de execução operacional indevida. A reprovação decorre
de contratos do modelo offline não satisfeitos, com oito testes adicionais a falhar.
Nenhuma correção foi aplicada; VAL2 e outras fases não foram iniciadas.

## A. Âmbito auditado e pré-verificações

Branch main e HEAD 22501be02fb3db1debf0b075fd254a120b2d1236 confirmados.
Staging inicialmente vazio. Cinco ficheiros IMP1 presentes e auditados:

- scripts/postgres/m12b_security_adapters.py
- scripts/postgres/m12b_security_coordinator.py
- scripts/postgres/tests/test_m12b_operational_adapters.py
- scripts/postgres/tests/test_m12b_operational_coordination.py
- docs/specifications/f0/m12b-p2c2b-imp1-offline-coordinator.md

Os cinco foram protegidos por snapshot SHA-256 antes da auditoria e permanecem
inalterados. Os 31 hashes protegidos anteriores coincidem, incluindo os 15
ficheiros AUTH-03. operation_gate() mantém a recusa de mutações e
ExecutionAuthorization.execution_enabled=False. Sem atualização de manifesto.
Alterações locais preexistentes, incluindo env.py e Compose, preservadas.

Somente dois novos artefactos VAL1 foram criados: este relatório e
scripts/postgres/tests/test_m12b_operational_audit.py.

## B. Metodologia

Leitura integral dos módulos, testes e documentação IMP1; inspeção das guardas
existentes e dependências importadas; reprodução da suite anterior; construção
de testes independentes de segurança no único ficheiro novo autorizado.
As asserções novas exprimem o comportamento seguro esperado. Falhas foram
mantidas visíveis, sem xfail, skip, alteração de expectativas ou correções.

As reproduções usam apenas MemoryScenario, mocks, relógio controlado e sessões
sintéticas. A01/A02 usam APIs públicas sem alterar métodos dos módulos auditados.
A03 usa uma falha configurada de unlock e uma falha de fecho por sessão, esta
última injetada no fake em runtime. Nenhuma altera o código em disco.
O teste de isolamento substitui fronteiras de I/O por mocks que lançariam erro
antes de executar qualquer operação. A cobertura dinâmica é complementada por AST;
não se declara análise formal ou sandbox contra Python hostil.

Não houve PostgreSQL, Docker operacional, Alembic upgrade/downgrade, SQL,
locks reais, credenciais novas, staging, commit ou push.

## C. Máquina de estados

| Estado | Verificação observada / resultado |
| --- | --- |
| PRECHECK | Tipagem/binding e origem esperada f066, sem security/authorization/objetos extra; A01 mostra que o contexto anterior não é consumido e a observação default não reflete um commit anterior |
| EXCLUSIVITY_VERIFIED | Exige prova tipada, controlos de writers/admissões, sessões verificadas e continuidade; tudo sintético, não uma atestação real |
| INSPECTED | Identidade inspector, sessão registada, fingerprint e chave primária verificados; a API issue isolada tem lacuna A02 |
| HANDOFF_ACCEPTED | Instância emitida, single-use, binding, TTL 5s antes/depois, fingerprint e continuidade; dentro de um fluxo fresco os negativos existentes passam |
| MIGRATION_COMMITTED | Exige validação pré-commit, transação ativa, fingerprint preservado e recibo de commit; transação encerrada ou commit incerto levam a reconciliação |
| POSTCOMMIT_VERIFIED | Exige nova sessão física sintética após fecho do migrator e prova de durabilidade/owner/fingerprint |
| OWNERSHIP_TRANSFERRED | Representa staging administrativo, conforme documentado; não é ainda confirmação persistente de ownership |
| TEMP_PRIVILEGES_REVOKED | Exige recibo de commit administrativo, owner e revogações; não corresponde a SQL executado |
| FINAL_VERIFIED | Sessão administrativa diferente, owner/ACL/baseline/fingerprint e app sem DML |
| CLOSED | Fluxo fresco exige sequência completa, provas finais, commit, ownership, revogações, recursos fechados e janela libertada; A01 permite repetir a mesma operação com outra instância |

Saltos de estado e avanço sequencial sem provas finais são recusados nos testes
existentes. Não se identificou sucesso operacional disfarçado de simulação:
SimulationResult conserva simulated=True e app_ready=False.
Falhas pós-commit/ownership/revogação são classificadas RECONCILE_REQUIRED e
não conduzem a CLOSED nessa tentativa. A03 demonstra que essa classificação
correta não garante todas as tentativas de limpeza de recursos.

## D. Evidências

- Binding por identidade de objeto liga destino, digest e operação. Provas de
  outra operação são recusadas pelo validador geral. Contudo, A01 permite nova
  tentativa com o mesmo Binding e A02 substitui o binding da inspeção recebida.
- HandoffProof já emitido tem proteção contra cópia/replay e consumo falhado;
  esses testes passaram. A02 ocorre antes dessa proteção, na emissão.
- TTL máximo 5s do handoff e limite de 30s das restantes provas, timestamps
  finitos e rejeição de booleanos são exercitados. A02 permite renovar a origem
  expirada criando um handoff novo, sem validar a InspectionProof de entrada.
- Fingerprints divergentes antes do commit ou nas provas posteriores são
  recusados nos fluxos existentes; não demonstram conteúdo ou controlo reais.
- Roles fixas e identidade das sessões sintéticas impedem bootstrap como
  substituto silencioso de inspector/migrator no fluxo testado.
- Exclusividade requer mais que lock ou lista vazia. RecoveryProof requer
  referência/canal independente e rejeita bootstrap_session_only. São alegações
  do fake, não prova da implementação ou da continuidade de mecanismos externos.
- Locks primário/transacional são flags e chaves no cenário. Não foi consultado
  pg_locks nem adquirido lock real. Nenhuma prova de concorrência real foi obtida.

Evidências offline não autorizam o executor existente: a guarda execution_enabled
continua a recusar e o novo execute() recusa mesmo depois de uma guarda simulada.
Não há integração que aceite estas dataclasses como atestação operacional.
Entregar uma RecoveryProof sintética a um operador não demonstra recuperação;
quem vier a implementar um consumidor terá de preservar essa distinção.

## E. Isolamento operacional

Os módulos novos não importam diretamente drivers PostgreSQL, Docker, subprocess,
socket ou comandos Alembic; não têm CLI/__main__, endpoints ou SQL modificador.
O import de m12b_security_migration carrega declarações SQLAlchemy/Alembic e modelos
existentes. Esse import não abre ligação nem chama migrações; o novo execute()
alcança apenas a guarda desativada e a recusa fixa, nunca run_alembic.

O teste de fronteiras confirma que simulate() e a execução recusada não chamam
psycopg.connect, sqlalchemy.create_engine, Alembic upgrade/downgrade,
subprocess.Popen ou socket.create_connection. Essas funções foram substituídas
por mocks de recusa; nenhuma operação real foi tentada. Nenhum segredo embebido
ou URL com credenciais foi identificado na revisão dos cinco ficheiros.

Tipos exatos de adaptadores não constituem isolamento de processo: clock é um
callable injetável e Python permite alterar métodos/objetos no processo confiável.
Não há configuração externa/CLI que explore isso para contornar o bloqueio.
Executar um callback arbitrário já fornecido por código Python hostil fica fora
da garantia documentada, não sendo aqui apresentado como bypass operacional.

## F. Testes executados

| Execução | Pass | Fail | Skip | Resultado |
| --- | --- | --- | --- | --- |
| Suite anterior IMP1 + regressões | 306 | 0 | 0 | 1.97s, reproduzida sem alterações |
| Apenas auditoria nova | 7 | 8 | 0 | 0.91s, falhas de segurança reproduzidas |
| Suite combinada final | 313 | 8 | 0 | 2.22s, exit code 1 esperado pelos problemas encontrados |

Não somar as linhas: a suite combinada contém as duas anteriores. Não existem
xfail ou skips a ocultar os oito resultados. Os testes a falhar são artefactos
de auditoria deliberadamente preservados, não regressões corrigidas nesta etapa.

Comando da suite combinada:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend .venv/bin/python -m pytest -q -p no:cacheprovider --tb=line scripts/postgres/tests/test_m12b_operational_adapters.py scripts/postgres/tests/test_m12b_operational_coordination.py scripts/postgres/tests/test_m12b_operational_audit.py backend/tests/test_security_migration.py scripts/postgres/tests/test_m12b_security_migration.py scripts/postgres/tests/test_m12b_security_execution.py scripts/postgres/tests/test_m12b_privilege_review.py scripts/postgres/tests/test_m12b_inspection_handoff.py scripts/postgres/tests/test_auth03_alembic_executor.py::test_operations_block_before_external_access scripts/postgres/tests/test_auth03_alembic_executor.py::test_valid_future_plans_still_cannot_execute
```

## G. Problemas classificados

### VAL1-A01 — ALTO: single-use limitado à instância, não à operação

Localizações: scripts/postgres/m12b_security_coordinator.py:63 e :105;
scripts/postgres/m12b_security_adapters.py:199 e :222.

Reprodução: criar um MemoryScenario, executar um coordenador e construir outro
com adaptadores novos sobre o mesmo cenário. O mesmo Binding.operation é usado
duas vezes. Tanto depois de CLOSED como depois de RECONCILE_REQUIRED por commit
incerto, a segunda tentativa executa migration_commit novamente e termina CLOSED.
No caso incerto basta remover a falha injetada; não existe reconciliação prévia.
O contador de tentativas de commit passa de 1 para 2 na mesma operação.

Causa: _started pertence apenas ao coordenador novo; o cenário não é reclamado
ou consumido por operação. precheck() produz sempre a observação default sem
security, mesmo depois do commit anterior modelado. Assim a nova tentativa ignora
o estado anterior e a exigência de reconciliação.

Impacto: o modelo não garante proibição de repetição cega por operação. Não é
uma segunda migração real, pois todo o caminho é fake e os executores reais
permanecem bloqueados; é uma falha importante do contrato de recuperação offline.

Testes: test_val1_a01_same_operation_cannot_be_retried_with_new_coordinator,
parâmetros success e uncertain_commit, em test_m12b_operational_audit.py:44.
Ambos falham porque a recusa esperada não acontece.

Correção recomendada, não aplicada: consumir/reclamar a operação numa autoridade
partilhada antes de qualquer trabalho e recusar contexto já utilizado/incerto;
fazer a pré-observação consistente com o estado modelado. Novos ensaios devem
ter contexto/operação novos; uma futura tentativa operacional exigirá também
reconciliação real, não apenas um novo objeto Python.

**Bloqueia a recomendação de commit IMP1 validado: sim.**

### VAL1-A02 — MÉDIO: emissão aceita inspeção expirada ou de outro binding

Localização: scripts/postgres/m12b_security_adapters.py:279.

Reprodução: obter InspectionProof legítima, substituir só o seu binding por outra
operação/destino/digest, ou avançar o relógio além de expires_at. Chamar
inspector.consume(inspector.issue(observação)). A emissão copia sessão/fingerprint
mas cria um binding e prazo novos; o consumo aceita o handoff recém-emitido.

Impacto: a API do adaptador transforma uma origem inválida em handoff válido,
sem verificar tipo, binding, validade ou proveniência da inspeção recebida.
O fluxo normal do coordenador valida a inspeção antes de issue() e possui outras
guardas temporais; não foi demonstrado bypass desse fluxo ou do executor real.
A lacuna é do contrato autónomo do adaptador, importante para futuras integrações.

Teste: test_val1_a02_issue_does_not_launder_inspection_binding_or_expiry,
em test_m12b_operational_audit.py:63. Quatro falhas: other_operation, other_target,
other_digest e expired; em todos os casos a recusa esperada não acontece.

Correção recomendada, não aplicada: validar InspectionProof de entrada, binding,
prazo, sessão, lock e proveniência antes de emitir; impedir que o novo TTL renove
uma observação antiga/incompatível. Reter a observação emitida pela autoridade,
se necessário, sem aceitar prova externa substituída pelo chamador.

**Bloqueia aceitação integral do contrato IMP1: sim**, enquanto os quatro testes
de segurança não passarem ou o contrato não for revisto e explicitamente aceite.
Não é classificado como bypass operacional.

### VAL1-A03 — MÉDIO: falha de limpeza impede outras tentativas de fecho

Localizações: scripts/postgres/m12b_security_adapters.py:302 e :412;
scripts/postgres/m12b_security_coordinator.py:210.

Reprodução 1: configurar falha persistente primary_unlock. InspectorAdapter.close
lança antes de world.close(session); repetir close no handler repete a mesma
falha e a sessão inspector fica fora de world.closed.

Reprodução 2: fazer falhar apenas o fecho da sessão de verificação final, mantendo
o fecho da sessão administrativa funcional. AdministrativeCloser.close chama o
primeiro fecho sequencialmente e não chega ao segundo. O handler chama o mesmo
método, que volta a falhar antes de tentar fechar a sessão administrativa.

Impacto: limpeza best-effort incompleta no modelo, apesar de a operação ser
corretamente classificada RECONCILE_REQUIRED e a barreira exterior permanecer
ativa. Não se observou CLOSED indevido nesses casos nem leak de ligações reais.
Se este ciclo fosse reutilizado em adaptadores operacionais, faltaria a garantia
de tentativa independente de fecho de todos os recursos.

Testes em test_m12b_operational_audit.py:80 e :91:
test_val1_a03_unlock_failure_still_attempts_physical_session_close e
test_val1_a03_final_close_failure_does_not_skip_admin_session_cleanup.
As duas asserções de sessão fechada falham.

Correção recomendada, não aplicada: tentar fecho físico em finally mesmo se
unlock falhar; tentar fechar cada sessão independentemente, agregando falhas
sem mascarar reconciliação ou presumir sucesso/rollback.

**Bloqueia aceitação integral da limpeza declarada: sim**, até correção/revisão
autorizada. Não justifica executar qualquer reparação PostgreSQL nesta fase.

## H. Riscos residuais e limites

Não há validação atual de PostgreSQL, Docker, schemas/ACL, autenticação SCRAM,
locks, durabilidade, isolamento ou recuperação real. PROV1/PROV2 são histórico.
Os contratos de timeout são declarativos; um relógio fake não prova cancelamento
de driver ou encerramento de backend. Defaults positivos do fake não podem ser
transportados para uma implementação operacional como observações reais.

Exclusividade externa e recuperação independente continuam por demonstrar;
dataclasses, fingerprint e advisory locks cooperativos não as substituem.
O modelo assume processo Python confiável. A integração futura deve reavaliar
identidade física completa, proveniência das observações e integridade do código.
DML/FOR UPDATE e auditoria da app permanecem fora do âmbito.

## I. Critério de aprovação/reprovação

Segurança de isolamento offline: aprovada no âmbito observado. Execução real
continua recusada antes dos adaptadores. Integridade local: preservada.
Conformidade do modelo de coordenação: reprovada pelos casos A01-A03.

Para aprovar IMP1 como implementação validada, exigir resolução ou revisão
formal dos três contratos, mantendo todas as guardas e executando novamente
as 321 asserções/casos recolhidos sem as oito falhas atuais. Não remover,
enfraquecer ou marcar como skip os testes apenas para obter resultado verde.
Essa correção/revisão exige outro pedido; não foi iniciada por VAL1.

## J. Recomendação de consolidação e encerramento

Não recomendar commit de IMP1 como incremento aprovado neste estado.
Preservar os cinco ficheiros originais e os dois artefactos VAL1 para revisão
posterior. Nenhum commit é criado por esta auditoria. Uma eventual consolidação
apenas documental ou snapshot de trabalho dependerá de autorização explícita
e não altera o resultado da auditoria.

Encerrar VAL1 aqui: sem correções, VAL2, infraestrutura ou início automático de
outras fases. Os problemas podem permanecer documentados enquanto o utilizador
decide a retoma do desenvolvimento funcional do LiveNet v2.

## K. Pendências para futura retoma de M1.2B

- A01: contexto single-use e reconciliação anterior à repetição.
- A02: proveniência/validade da inspeção na emissão do handoff.
- A03: fecho independente de recursos em falhas parciais.
- Revisão offline e reexecução da suite após correções autorizadas.
- Adaptadores operacionais, exclusividade externa P2B-D03 e recuperação P2B-D04,
  todos sujeitos a ensaios e autorização específicos.
- Integração do ciclo R2 até ao fecho administrativo, validação após ownership,
  janela CREATE, catálogo/ACL reais e ativação deliberada apenas numa fase futura.
- DML/FOR UPDATE P2B-D05 e prontidão da autenticação/inventário em decisão separada.

## Verificação final local e Git

HEAD preservado em 22501be02fb3db1debf0b075fd254a120b2d1236, main e staging vazio.
Os cinco hashes IMP1 e os 31 protegidos anteriores, incluindo os 15 AUTH-03,
permanecem iguais. operation_gate() bloqueado; execution_enabled=False.
git diff --check e whitespace dos dois artefactos VAL1 sem erros.

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

Só o relatório VAL1 e test_m12b_operational_audit.py são novos nesta execução.
