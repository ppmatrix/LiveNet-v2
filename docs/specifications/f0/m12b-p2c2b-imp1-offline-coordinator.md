# M1.2B-P2C-2B-IMP1 — Coordenador exclusivamente offline

## Âmbito e estado

Implementação em main, base 22501be02fb3db1debf0b075fd254a120b2d1236.
Aplica P2B-D01 a P2B-D05 ao modelo de coordenação, sem implementar os mecanismos
operacionais de acesso/exclusividade/recuperação. Não estabelece ligações,
executa SQL/Alembic/Docker, adquire locks ou lê/cria credenciais. Sem CLI,
endpoints, commit ou push. Nenhum ficheiro existente foi alterado.

Ficheiros novos:

- scripts/postgres/m12b_security_adapters.py
- scripts/postgres/m12b_security_coordinator.py
- scripts/postgres/tests/test_m12b_operational_adapters.py
- scripts/postgres/tests/test_m12b_operational_coordination.py
- Este documento.

O executor anterior, security env/migração, modelos M1.2A, Compose e AUTH-03
permanecem intactos. execution_enabled=False e operation_gate() continua
bloqueado. O estado PostgreSQL não foi consultado nesta etapa: a ausência
de CREATE/DML e de security é evidência histórica de PROV1/PROV2, não uma
revalidação operacional atual.

## Componentes e interfaces

Os seis adaptadores são implementações concretas de simulação em memória,
injetadas em MigrationCoordinator. MemoryScenario é o fake partilhado do mundo,
com relógio injetável, sessões sintéticas, observações tipadas e falhas por fase.
Nenhum recebe callback de conexão, driver, engine, shell ou comando de migração.
O coordenador exige exatamente estes tipos e o mesmo cenário; rejeita adaptadores
arbitrários e cenários misturados. Isto delimita o ensaio, não isola Python hostil.

| Componente | Interface principal / evidência | Identidade e ciclo |
| --- | --- | --- |
| InspectorAdapter | inspect, issue, consume, verify_unchanged, continuity, close; InspectionProof/HandoffProof | inspector fixo; uma sessão mantém o lock primário modelado até depois da validação final |
| MigratorAdapter | begin, work, commit, rollback, close; PrecommitProof/CommitProof | migrator fixo; uma transação externa modelada, lock transacional e commit sem retry |
| PostCommitVerifier | verify, close; DurabilityProof | migrator RO em sessão física sintética nova, distinta da sessão fechada do commit |
| AdministrativeCloser | transfer, revoke, verify_final, rollback, close; OwnershipProof/ClosureProof/FinalProof | bootstrap administrativo explícito, nunca substitui inspector/migrator; verificação final em outra sessão |
| ExclusivityController | verify, check, release; ExclusivityProof/ReleaseProof | controlo exterior sintético de writers, admissões, sessões e continuidade; não altera infraestrutura |
| RecoveryVerifier | verify; RecoveryProof | referência a ensaio/canal independente; recusa depender apenas da sessão bootstrap |
| MigrationCoordinator | simulate; SimulationResult, state/history; execute recusa operação real | dirige o ciclo e retém a janela até ao fecho completo |

FIX1 acrescenta OperationRegistry, injetável no cenário e partilhado entre
coordenadores, e CleanupIssue/CleanupError para limpeza independente. São
componentes do modelo offline; não implementam persistência ou novos canais I/O.

Cada adaptador expõe AdapterContract com identidade, capacidades, transação,
timeouts, ciclo e erros esperados. Limites declarados: inspector/verificador
5s/1s; migrator/fecho administrativo 30s/3s; controlo/recuperação 5s/1s.
São contratos para os futuros adaptadores: não existem instruções bloqueantes,
timeouts de servidor ou threads de cancelamento implementados aqui.

Isolamentos declarados: inspector/verificador REPEATABLE READ READ ONLY;
migrator READ COMMITTED com transação externa; ownership/revogação num bloco
administrativo atómico modelado. Não se executam essas transações no PostgreSQL.
Queries/capacidades futuras ficam limitadas a catálogo, baseline, id_counts,
própria cadeia security, verificação e fecho previstos no PREP. Não há SQL
modificador ou qualquer construtor de conexão nos módulos novos.

## Execução bloqueada e simulação explícita

MigrationCoordinator.execute(plan) chama primeiro a guarda existente
require_execution_authorization(plan). Com execution_enabled=False recusa antes
de tocar em adaptadores ou evidências. Mesmo se essa guarda for substituída por
um mock de teste, o método recusa: IMP1 não tem caminho de execução operacional.
O executor existente não foi editado nem ligado automaticamente ao novo modelo.

simulate() é uma API distinta, aceita apenas os componentes em memória e devolve
simulated=True/app_ready=False. Não é uma autorização alternativa: apenas calcula
o resultado de um ensaio. O cenário sintético pode demonstrar um fluxo completo
mesmo sem CREATE real concedido; nenhuma conclusão sobre PostgreSQL decorre disso.

Uma instância de coordenador e cada operação registada admitem uma única tentativa.
O registo partilhado é reclamado antes de qualquer adaptador; outra instância
não reabre a operação. Registo ausente, vazio, indisponível ou substituído exige
reconciliação, sem interpretar ausência como permissão. Sucesso anterior bloqueia
repetição; estado incerto continua RECONCILE_REQUIRED. Não renova evidência,
repete migração ou reabre sessões automaticamente.
Não há fallback de credenciais ou identidade; nenhum segredo é necessário.

## Registo partilhado e reconciliação FIX1

OperationRegistry.new_binding cria uma operação nova explicitamente registada,
sempre com identidade própria. lookup nunca insere registos. claim exige
REGISTERED e emite OperationClaim ligada à autoridade e ao binding exatos;
finish exige essa instância e registo RUNNING. O coordenador conserva identidade
do registo/binding durante o ciclo e confirma o registo CLOSED antes de publicar
o seu estado CLOSED. Falha de finalização exige reconciliação, não sucesso.

Estados do registo: REGISTERED -> RUNNING -> CLOSED/BLOCKED/ROLLED_BACK/
RECONCILE_REQUIRED. Uma Reconciliation sintética explícita, com referência e
resultado confirmado, pode marcar RECONCILE_REQUIRED como RECONCILED. Esse estado
é terminal: nunca volta a REGISTERED. Mesmo se a avaliação disser que o commit
não aconteceu, uma eventual tentativa exige operação nova e reconciliação
adequada ao contexto; um novo coordenador sozinho não basta.

O registo é síncrono, em memória e só partilhado por instâncias que recebem a
mesma autoridade. Não oferece durabilidade entre processos/reinícios, controlo
concorrente de threads ou prova de estado PostgreSQL. Um cenário novo é um novo
ensaio, não permissão para repetir migrações numa base real. Referências de
reconciliação são dados sintéticos, não comprovativos operacionais. Estado RUNNING
após falha de armazenamento permanece bloqueado para investigação; não existe
reabertura automática ou rotina de reparação persistente.

## Máquina de estados e invariantes

```text
PRECHECK
  -> EXCLUSIVITY_VERIFIED
  -> INSPECTED
  -> HANDOFF_ACCEPTED
  -> MIGRATION_COMMITTED
  -> POSTCOMMIT_VERIFIED
  -> OWNERSHIP_TRANSFERRED
  -> TEMP_PRIVILEGES_REVOKED
  -> FINAL_VERIFIED
  -> CLOSED

Falhas: BLOCKED | ROLLED_BACK | RECONCILE_REQUIRED
```

PRECHECK exige observação de f066, ausência de revisão security/authorization
e de objetos inesperados. O Binding fixa projeto livenetv2-m12b-test, base
livenet_m12b_test, system_identifier 7699783234487926818, db:5432,
baseline f066a01a7230, alvo b12b01a7230 e digest de plano explícito.
Não calcula atestação Docker ou digest real das fontes: essa integração fica pendente.

CLOSED exige todas as transições anteriores, commit confirmado, nova verificação
de durabilidade, owner NOLOGIN esperado, CREATE/memberships temporárias fechados,
verificação final independente, recursos fechados e libertação confirmada da janela.
Tentar saltar estados, ou avançar sequencialmente sem as provas finais, é recusado.
Não equivale a APP_READY; DML e FOR UPDATE continuam fora do âmbito por P2B-D05.

OWNERSHIP_TRANSFERRED representa transferência preparada e verificada dentro do
bloco administrativo ainda não confirmado. revoke() modela o commit conjunto
de ownership e revogações; TEMP_PRIVILEGES_REVOKED exige esse commit. Falha antes
do commit administrativo reverte o staging; tentativa de commit incerta exige
reconciliação, sem afirmar rollback. Não há ALTER OWNER/GRANT/REVOKE executáveis.

Ordem de fecho: confirmar catálogo final -> fechar sessões administrativas ->
libertar/fechar a sessão primária -> libertar a barreira exterior -> CLOSED.
A barreira exterior cobre o intervalo depois do unlock. Falhas de fecho bloqueiam
a libertação da janela; uma resposta inválida após a tentativa de libertação é
reconciliação, nunca uma garantia de que a barreira ainda existe.

## Evidências e continuidade

Proofs são dataclasses imutáveis tipadas, ligadas à mesma instância Binding com
operação única, destino e digest. Prazos usam relógio monotónico e valores finitos;
booleanos usados como timestamps são recusados. Validade geral máxima 30s no
ensaio e TTL de handoff máximo 5s, inclusivo no limite; sem renovação implícita.
Esses limites fazem o ensaio falhar fechado se a validade terminar durante o ciclo.

- ExclusivityProof exige controlos não vazios de writers e de novas admissões,
  sessões verificadas/contabilizadas, bloqueio externo e identificador estável de
  continuidade. Lista de sessões vazia ou advisory lock não substitui essa prova.
  O coordenador revalida a prova e o estado ativo da janela durante todo o ciclo.
- RecoveryProof exige demonstração, referência do ensaio e canal independente.
  Evidência ausente, expirada, de outra operação ou bootstrap_session_only bloqueia
  o fluxo antes de abrir a sessão inspector.
- HandoffProof só é aceite como a instância exata emitida pelo inspector desta
  operação. Cópia, replay, outra autoridade/destino, fingerprint divergente, lock
  perdido e expiração são recusados. Uma tentativa de consumo falhada também
  invalida esse handoff; relógio é verificado antes/depois da releitura modelada.
  FIX1 valida também a InspectionProof antes de issue(): tipo exato, instância
  emitida, binding/operação/destino/digest, validade, sessão/lock e fingerprint.
  O prazo do handoff é o menor entre agora+5s e o fim de validade da inspeção;
  não renova uma observação antiga nem aumenta o TTL.
- Lock primário (1295073858,6601) pertence à mesma sessão inspector até ao fim
  administrativo. Lock transacional (1295073858,6602) é modelado separadamente e
  verificado enquanto a transação está ativa. Nenhum lock real é adquirido.
- Session exige papel exato, pertença ao cenário e sessão ainda aberta. Bootstrap
  nunca pode substituir migrator/inspector. Persistência exige sessão/objeto físico
  diferente e sessão original fechada. FinalProof usa sessão administrativa nova.
- DurabilityProof/FinalProof verificam fingerprint, owner e resultados físicos/ACL
  modelados; app_dml_enabled deve permanecer False. ReleaseProof só é aceite depois
  da prova final e do fecho dos recursos.

Antes da tentativa de commit, PrecommitProof exige revisão aplicacional/alvo e
validação física modelada. O inspector revalida o fingerprint e a continuidade dos
locks/janela; uma alteração durante o trabalho impede o commit. Depois do commit,
a observação independente volta a comparar o fingerprint antes do ownership.

São observações sintéticas, não provas autenticadas, assinadas ou provenientes
de infraestrutura. Os campos de controlo não demonstram exclusividade real e
nenhuma dataclass autoriza o executor. Objetos emitidos neste ensaio não são
aceites como handoff operacional R2; o protocolo existente permanece inalterado.
Um processo Python confiável e adaptadores futuros auditados continuam necessários.

## Falhas, limpeza e recuperação

| Situação | Resultado modelado |
| --- | --- |
| Pré-condição, recuperação ou exclusividade inválida antes da transação | BLOCKED; não iniciar trabalho |
| Falha antes da tentativa de commit, com rollback confirmado | ROLLED_BACK; uma nova tentativa continua proibida nesta instância |
| Commit tentado/incerto, commit prematuro, rollback/fecho falhado | RECONCILE_REQUIRED; não repetir ou afirmar reversão |
| Falha pós-commit, ownership, revogação ou verificação final | RECONCILE_REQUIRED; migração não é interpretada como operação concluída |
| Perda de evidência, lock ou exclusividade durante o ciclo | Interromper; nunca prosseguir para CLOSED por histórico incompleto |

Na falha, tenta-se rollback apenas quando não houve tentativa/indício de commit,
rollback do staging administrativo apenas antes de tentativa do seu commit, e
fecho de todos os recursos próprios. FIX1 tenta unlock e close independentemente,
assim como as duas sessões administrativas. Cada ação de limpeza é tentada uma
vez por adaptador: novas chamadas close não repetem unlock/close já tentados e
mantêm o erro registado. Uma falha de unlock não impede fecho físico; uma falha
do primeiro close não impede os seguintes. Uma falha de limpeza exige reconciliação.
O caminho de recuperação não liberta/reabre a barreira automaticamente nem
executa reparação. Estados de memória não provam que um backend remoto terminou.

Exceções são convertidas em CoordinationFailed com estado fixo, sem detalhes
brutos ou encadeamento apresentado de erros de driver. original_error preserva
o objeto original para inspeção confiável, sem o interpolar em str/repr ou logs;
não deve ser serializado. cleanup_failures regista apenas ações e classes de erro,
sem mensagens secundárias. O histórico permite
identificar a última transição, mas não é autorização ou recibo persistente.
Não há downgrade, restauro automático, cancelamento de backend ou novos segredos.

## Testes executados

Base IMP1: 306 pass. VAL1 revelou oito falhas adicionais, preservadas no teste
de auditoria e no relatório histórico VAL1. FIX1: **355 pass, 0 fail, 0 skip**,
2.29s, incluindo os 306 anteriores, os 15 VAL1 (oito regressões corrigidas) e
34 casos adicionais FIX1. Nenhum teste anterior foi eliminado ou enfraquecido;
test_m12b_operational_audit.py permanece byte a byte igual ao original VAL1.

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend .venv/bin/python -m pytest -q -p no:cacheprovider scripts/postgres/tests/test_m12b_operational_adapters.py scripts/postgres/tests/test_m12b_operational_coordination.py scripts/postgres/tests/test_m12b_operational_audit.py backend/tests/test_security_migration.py scripts/postgres/tests/test_m12b_security_migration.py scripts/postgres/tests/test_m12b_security_execution.py scripts/postgres/tests/test_m12b_privilege_review.py scripts/postgres/tests/test_m12b_inspection_handoff.py scripts/postgres/tests/test_auth03_alembic_executor.py::test_operations_block_before_external_access scripts/postgres/tests/test_auth03_alembic_executor.py::test_valid_future_plans_still_cannot_execute
```

Cobertura: sucesso completo/ordem de fecho, falha em todas as transições e fases,
TTL nos limites e releitura lenta, replay/cópia, operação/destino diferentes,
fingerprint/identidade divergentes, perda de exclusividade/locks, recuperação
indisponível, commit incerto/prematuro, rollback falhado, falhas de ownership,
revogação/commit administrativo e fecho, durabilidade não independente, finais
incompletos, DML indevido e tentativas de execução bloqueadas.
FIX1 cobre ainda replay entre coordenadores, armazenamento vazio/indisponível,
operação nova, evidência antiga, emissão com origem inválida/expirada, TTL limitado
pela origem, limpeza parcial/múltipla, preservação da exceção original, ausência
de duplicação e confirmação incerta de libertação da janela.

Testes não executam SQL, Docker, Alembic upgrade/downgrade ou persistência.
Valores de timeout/isolamento são contratos declarados, não ensaios de servidor.
Os testes novos não substituem os testes R2 existentes nem alteram as suas guardas.

## Limitações, pendências e critérios para VAL1

VAL1 deve começar por revisão independente do código/contratos e testes offline,
incluindo o mapeamento de estados às evidências e limites de confiança. Nenhuma
aprovação desse ensaio deve ser interpretada como ativação de execution_enabled.

Continuam pendentes:

1. Adaptadores operacionais separados, credenciais/canais e atestação real de
   projeto/contentor/imagem/rede/volume/endpoint; distribuição e digest revistos.
2. Implementação autorizada de exclusividade contra writers externos e canal de
   recuperação testado independentemente, requisitos P2B-D03/P2B-D04.
3. Integração revista com a sessão compliance R2 até ao fecho administrativo;
   o finally do executor anterior ainda não foi refatorado por IMP1.
4. Comparador físico pós-ownership e allowlists reais de ACL/colunas/defaults/rotinas;
   fecho administrativo atómico e reconciliação de catálogo após commit incerto.
5. Testes operacionais de isolamento/timeouts/locks/conexões/DDL/durabilidade e
   recuperação, sujeitos a autorização própria; nenhuma prova real foi produzida.
6. Decisão posterior para DML/FOR UPDATE e auditoria da app. Não conceder poderes,
   criar contas LiveNet ou declarar a API utilizável por concluir esta simulação.

Para nova auditoria: 355 testes reproduzidos ou resultado justificado após revisão,
nenhuma regressão das guardas, provas sintéticas claramente identificadas,
recusa anterior a qualquer I/O real, integridade AUTH-03 e âmbito preservados.
Não iniciar migração, provisionamento ou ensaio PostgreSQL por consequência.

## Integridade final

Os 31 hashes protegidos, incluindo os 15 AUTH-03, coincidem com o estado anterior.
operation_gate() bloqueado e execution_enabled=False, staging vazio, HEAD
preservado. git diff --check e whitespace dos cinco ficheiros novos sem erros.
As adições originais IMP1 continuam a ser os cinco ficheiros listados acima.
FIX1 altera só os dois módulos, acrescenta testes aos dois ficheiros IMP1,
atualiza este documento e cria m12b-p2c2b-imp1-fix1-report.md. O relatório e
o ficheiro de testes VAL1 mantêm-se intactos. Alterações locais anteriores
preservadas integralmente. Sem alteração do manifesto AUTH-03 ou Compose.
