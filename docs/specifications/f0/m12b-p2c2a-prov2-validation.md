# M1.2B-P2C-2A-PROV2 — Validação operacional read-only

## Resultado e fontes

Validação em 2026-10-23, main, HEAD
0637049ce8855a7298a39dab0ff9e210be949c4f. As funções de leitura R2 são
compatíveis com as identidades e grants PROV1. Não foram alterados código,
privilégios, configuração, dados ou estrutura aplicacional. Este relatório é
o único novo ficheiro desta etapa; sem staging, commit ou push.

Foram revistos m12b-p2c2a-privilege-review.md (R1),
m12b-p2c2a-r2-inspection-handoff.md (R2),
m12b-p2c2a-r3-operational-preflight.md e m12b-p2c2a-prov1-report.md, além do
coordenador scripts/postgres/m12b_security_migration.py e respetivos testes.
As observações históricas de R3 anteriores ao provisionamento não representam
o estado atual de roles/ACL; a referência operacional atual é PROV1.

## A. Identidade do destino

| Campo | Confirmado |
| --- | --- |
| Projeto | livenetv2-m12b-test |
| Contentor | livenetv2-m12b-test-db-1 |
| ID | 540e8834355c281d5874603b82231b006486e3a74103bda04bead0ac77fbc5ec |
| Estado | running / healthy, RestartCount=0 |
| Imagem | postgres:16-alpine@sha256:f4610795587492cd4fb887c2dc3de301b813278bb6f616992061141b5f15ac36 |
| ID da imagem | sha256:6a2e324ebe59af6031c4c1cd96c1d5072c2ebc36563d2196365e43b8297c062d |
| Rede | livenetv2-m12b-test_m12b_backend, internal=true, só o destino |
| ID da rede | cda632938bb938b51bfdc331f13c2af61ea1d9e1617d105d6a04573f100e1627 |
| Volume | livenetv2-m12b-test_m12b_postgres_data, único consumidor confirmado |
| Portas publicadas | Nenhuma |
| Endpoint explícito | 172.27.0.2:5432 |
| Base | livenet_m12b_test |
| system_identifier | 7699783234487926818 |
| Versão | PostgreSQL 16.15 / 160015 |
| Ledger aplicacional | public.alembic_version = f066a01a7230, única linha |
| Inventário | 12 tabelas inventory, audit.events e ledger public: 14 tabelas |
| security / authorization / ledger security | Ausentes |

Identidade e estado foram confirmados antes das leituras funcionais e novamente
em nova ligação bootstrap às 13:12:48 UTC. A amostra inicial retida para comparação
é das 13:11:09 UTC. Nenhuma ligação foi estabelecida a outra base ou cluster.

## B. Autenticação real por identidade

| Identidade | PID durante o teste simultâneo | Autenticação | CONNECT | READ ONLY |
| --- | --- | --- | --- | --- |
| livenet_m12b_inspector | 22484 | Passou | Sim | on |
| livenet_m12b_migrator | 22485 | Passou | Sim | on |
| livenet_m12b_app | 22486 | Passou | Sim | on |

As três ligações físicas estavam abertas simultaneamente: PIDs e objetos driver
distintos, current_user=session_user esperado, base, endereço, porta,
system_identifier e versão exatos. Usaram as credenciais próprias já existentes,
sem gerar ou modificar segredos. Diretório 0700 e ficheiros 0600 foram verificados.

SCRAM-SHA-256: pg_hba_file_rules, sem erros, conserva regras SCRAM locais/loopback
e host all/all/all; esta última corresponde ao acesso pela bridge. O catálogo
de autenticação foi consultado apenas para devolver booleanos de formato SCRAM
dos três LOGIN e password NULL do NOLOGIN. Não se recolheram verificadores.
password_encryption=scram-sha-256. O sucesso das ligações é compatível com essas
regras; não se capturou o protocolo de autenticação na rede. ssl continua off.

## C. Matriz de privilégios efetivos

| Identidade | CONNECT | CREATE base/public/inventory/audit | TEMP | USAGE inventory/audit | SELECT aplicacional | Ledger | Escrita |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Inspector | Sim | Não | Não | Sim | Apenas id das 13 tabelas | SELECT(version_num) | Não |
| Migrator | Sim | Não | Não | Não | Não | SELECT(version_num) | Não |
| App | Sim | Não | Não | Não | Não | Sem SELECT/UPDATE ou outros direitos | Não |
| Security owner | Não; NOLOGIN | Não | Não | Não | Não | Nenhum | Não |

As quatro roles conservam NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION,
NOBYPASSRLS e NOINHERIT. Nenhuma membership em ambos os sentidos, nem ownership
de bases, schemas, relações ou funções. USAGE de public e leitura predefinida
de catálogos continuam disponíveis. Bootstrap conserva acesso administrativo.

As negativas foram verificadas por has_database_privilege, has_schema_privilege,
has_table_privilege, has_any_column_privilege e has_column_privilege. Foram
verificadas as 14 tabelas e todas as suas colunas para as quatro novas roles,
incluindo privilégios efetivos herdados. Não houve tentativas de DDL/DML proibido,
CREATE TEMP TABLE, SELECT FOR UPDATE ou alteração de ledgers.

## D. Consultas e funções reais executadas

Todas as ligações usaram credenciais em memória e destino explícito, sem
DATABASE_URL. As três ligações SQLAlchemy usaram NullPool, creator explícito,
echo=False, hide_parameters=True e opções de arranque:
default_transaction_read_only=on, search_path=public, statement_timeout=5000,
lock_timeout=1000. Os valores efetivos 5s/1s foram confirmados por SELECT.
As inspeções bootstrap também foram READ ONLY, com limites de 10s/3s.

Um listener na validação SQLAlchemy aceitou apenas SELECT/SHOW e recusaria
advisory locks, funções de cancelamento, set_config, nextval ou FOR UPDATE/SHARE.
Foram observadas 53 instruções nesse listener, com 25 textos distintos; esta
contagem não inclui as inspeções bootstrap ou comandos internos do driver fora
desse listener. Todas as instruções observadas eram de leitura.

Funções reais, sem substituir o seu SQL por mocks:

- identify_postgresql: inspector e migrator; identidade, versão, search_path,
  read-only e pg_control_system(). App identificada por SELECT equivalente,
  sem a apresentar como migrator perante o contrato.
- verify_inspector_privileges: passou com os grants reais.
- inspect_compliance(installed=False): passou duas vezes, incluindo baseline,
  catálogo e protected_fingerprint.
- protected_fingerprint: leitura de owners/ACL, flags RLS, colunas/defaults,
  constraints, índices, triggers e funções de inventory/audit; count(id) nas
  13 tabelas fechadas pelo contrato, todas vazias.
- read_database_state e validate_observation(phase='before'): passaram na
  ligação migrator; schemas public/inventory/audit, 14 relações, apenas f066.
- SELECT exato de verify_privileges, extraído da AST: executado no migrator para
  observar os flags, sem chamar o verificador que exige CREATE para executar.

Consultas de dados aplicacionais limitadas a:

```sql
SELECT version_num FROM public.alembic_version ORDER BY version_num;
```

e SELECT count("id") FROM "schema"."tabela" para inventory.resources,
resource_identifiers, resource_relations, groups, group_memberships, group_rules,
tags, resource_tags, policies, policy_versions, policy_assignments,
effective_configs e audit.events. Não foram lidos outros valores de linhas.

Catálogos consultados incluíram pg_namespace, pg_class, pg_attribute, pg_attrdef,
pg_constraint, pg_index, pg_trigger, pg_proc, pg_roles, pg_auth_members,
pg_database, pg_settings, pg_hba_file_rules, pg_stat_activity e pg_locks.
Não foram lidos textos de consultas de outras sessões.

Fingerprint nas duas leituras reais:
21f30b337b2d9aa380b200d812afd32ac7f28eb7459cb12c06a63cd15d378c84.
É resumo de conformidade de catálogo; não é token, credencial ou autorização.

## E. Compatibilidade dos adaptadores e handoff

Os leitores R2 funcionam com os grants PROV1, sem permissões adicionais.
A separação física inspector/migrator foi comprovada. As ligações foram fechadas
e os engines descartados; a amostra bootstrap posterior já não continha os três
backends de teste. Nenhum erro SQL ou timeout ocorreu.

O repositório continua sem adaptadores operacionais predefinidos de ligação,
atestação Compose ou Alembic. Foi usado um harness efémero em memória, sem criar
código ou configuração no repositório. O plano mantém host lógico db; o harness
no host liga explicitamente ao IP conferido no Docker, sem fallback ou alterar
a validação de destino. Isto valida leitores e transporte experimental, não
consolida um adaptador operacional aprovado ou uma CLI de execução.

Não foram chamados execute_security_migration, acquire_migration_lock,
_open_compliance, _ComplianceSession.issue/consume/close ou qualquer função que
adquira/liberte advisory locks. Nenhuma evidência operacional de handoff foi
emitida ou consumida. O mesmo fingerprint em duas leituras é compatível com a
revalidação esperada; o handoff completo continua testado exclusivamente por mocks.

Erros, rollback, fecho, commit incerto, lock perdido e replay/expiração são cobertos
pela suite offline. Não se provocaram erros, esperas ou timeouts no servidor.
Timeouts reais da futura implementação operacional e falhas de rede/fecho ainda
exigem testes autorizados próprios; não se atribui essa cobertura ao ensaio atual.

## F. Incompatibilidades e limites esperados

Nenhuma incompatibilidade de leitura ou coluna não autorizada foi encontrada.
O SELECT de privilégios do migrator devolveu create_schema=False e
create_ledger=False; os outros nove flags de segurança foram True.
Isso corresponde ao PROV1: CREATE na base/public está deliberadamente ausente.
verify_privileges completo recusaria esse estado para uma migração; não foi
invocado como fluxo operacional nem contornado. Não houve correção de grants.

## G. Locks e concorrência

As amostras bootstrap inicial/final tinham apenas o backend da própria inspeção,
read-only, sem backend_xid. Não se observaram advisory locks ou locks pendentes.
Os AccessShareLock observados sobre o ledger e o seu índice são automáticos das
consultas de leitura. Não foram adquiridos locks voluntários ou canceladas sessões.

max_connections=100, superuser_reserved_connections=3, datallowconn=true e
datconnlimit=-1. A amostra tinha um cliente e foram abertas três ligações
simultâneas com sucesso. Isto comprova capacidade naquele momento, sem reservar
slots ou garantir disponibilidade futura.

PROV2 não demonstra exclusividade contra escritores externos. Os locks
cooperativos R2 previstos, de sessão (1295073858,6601) e transacional
(1295073858,6602), não foram adquiridos. Ausência amostrada de escritores,
fingerprint estável, rede internal e CONNECT restrito não impedem escrita futura
por bootstrap ou intervenção administrativa do host/Docker.

## H. Ownership, ACL e ausência de alterações persistentes

A comparação inicial/final confirmou nove grupos estáveis: identidade,
validação de roles/privilégios/ACL, estrutura física, todas as roles,
memberships, funções, configurações selecionadas, capacidade e HBA.
Owners/ACL de base/schema/tabela/coluna mantêm-se iguais; tipos, nulabilidade,
defaults, constraints, índices, triggers e flags RLS das 14 tabelas preservados.
Não surgiram roles, schemas, tabelas ou ledger security. Baseline continua f066.

PUBLIC continua sem CONNECT/TEMPORARY apenas na base M1.2B; ACL das outras bases
do mesmo cluster foram lidas no catálogo sem estabelecer ligação e não mudaram.
Nenhuma role tem membership da security_owner; esta conserva NOLOGIN. Bootstrap
continua autenticável e administrador. Não foram executados SQL modificador,
DDL/DML, GRANT/REVOKE, ALTER OWNER/ROLE, alteração de configuração ou Alembic.
Estatísticas e logs normais de acesso não representam alteração aplicacional;
não se afirma imobilidade byte a byte do volume PostgreSQL.

## I. Testes offline e integridade

Resultado: 202 pass, 0 fail, 0 skip, 1.77s.

Suite executada com PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=backend e
pytest -q -p no:cacheprovider:

- backend/tests/test_security_migration.py
- scripts/postgres/tests/test_m12b_security_migration.py
- scripts/postgres/tests/test_m12b_security_execution.py
- scripts/postgres/tests/test_m12b_privilege_review.py
- scripts/postgres/tests/test_m12b_inspection_handoff.py
- test_operations_block_before_external_access e
  test_valid_future_plans_still_cannot_execute em test_auth03_alembic_executor.py

Esses testes usam declarações/metadata e mocks, sem persistência ou execução de
upgrade/downgrade. Cobrem P1/P2C-1, R1/R2, ordenação de locks/handoff, privilégios,
replay, expiração, falhas e bloqueios. O teste de handoff não foi usado para
autorizar a execução real.

Os 31 hashes protegidos, incluindo os 15 ficheiros AUTH-03 e Compose M1.2B,
mantêm-se iguais aos anteriores. Os seis contentores conservam ID, imagem,
estado/health, arranque, restart count, mounts e redes. Rede/volume exclusivos
e RepoDigest conferidos novamente. Não foram lidas variáveis de password Docker
nem alterados serviços. Sem ligações às bases dos ambientes protegidos.
operation_gate() mantém o bloqueio de mutações e AUTHORIZATION.execution_enabled
continua False. Nenhum manifesto foi atualizado.

git diff --check e whitespace adicional deste relatório: sem erros.

## J. Riscos residuais

- Recuperação independente após perder/despromover o único administrador continua
  não demonstrada. O acesso bootstrap funcional não equivale a um restauro testado.
- Sem prova de exclusividade da futura janela ou fencing de administradores.
- ssl=off e acesso pela bridge do host; TLS e canais operacionais por rever.
- As roles pertencem apenas ao cluster descartável. CONNECT herdado de PUBLIC
  noutras bases desse cluster não foi removido; não há grants explícitos novos.
- Sem teste real de locks/handoff, migração, rollback DDL, persistência security,
  handoff de ownership ou falhas de transporte.
- DML security e requisito FOR UPDATE da app continuam pendentes.

## K. Critérios para a próxima etapa

Manter o executor desativado até autorização específica, adaptadores operacionais
revistos, identidade e integridade novamente verificadas, coordenação/exclusão
de escritores demonstrada e janela de CREATE temporário explicitamente aprovada.
Testar locks reais, falhas e recuperação apenas com âmbito próprio autorizado.
Não conceder DML à app nem membership/ownership antecipadamente.
O futuro handoff para owner NOLOGIN deve ocorrer só após persistência validada.
PROV2 não autoriza a migração b12b01a7230 nem inicia P2C-2B.

## Git final

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
?? docs/specifications/f0/m12b-p2c2a-prov2-validation.md
?? docs/specifications/f0/m12b-p2c2a-r3-operational-preflight.md
?? scripts/postgres/auth03_alembic_executor.py
?? scripts/postgres/auth03_executor.Dockerfile
?? scripts/postgres/auth03_executor.Dockerfile.dockerignore
?? scripts/postgres/auth03_executor.example.json
?? scripts/postgres/auth03_executor_integrity.json
?? scripts/postgres/tests/test_auth03_alembic_executor.py
```

Todas as entradas são preexistentes exceto este relatório. Staging vazio e HEAD
inalterado; sem commit ou push.
