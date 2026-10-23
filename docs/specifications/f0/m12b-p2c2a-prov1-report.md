# M1.2B-P2C-2A-PROV1 — Provisionamento controlado

## Resultado e âmbito

Provisionamento concluído em 2026-10-23, validado às 11:25:36 UTC.
Branch main, HEAD b2605975a4fb87f25aa84afcda3f10dac77cfd4c.
Foram criadas exclusivamente as quatro roles aprovadas, sem instalar security,
ativar executores ou executar Alembic. O único ficheiro criado no repositório
nesta etapa é este relatório. As três credenciais foram guardadas fora do Git.
Não houve commit Git nem push.

## Identidade e pré-condições

| Campo | Valor confirmado |
| --- | --- |
| Projeto Compose | livenetv2-m12b-test |
| Contentor | livenetv2-m12b-test-db-1 |
| ID | 540e8834355c281d5874603b82231b006486e3a74103bda04bead0ac77fbc5ec |
| Estado | running / healthy, RestartCount=0 |
| Arranque | 2026-10-23T08:51:26.119741529Z |
| Imagem | postgres:16-alpine@sha256:f4610795587492cd4fb887c2dc3de301b813278bb6f616992061141b5f15ac36 |
| ID da imagem | sha256:6a2e324ebe59af6031c4c1cd96c1d5072c2ebc36563d2196365e43b8297c062d |
| Rede | livenetv2-m12b-test_m12b_backend, internal=true, apenas este contentor |
| ID da rede | cda632938bb938b51bfdc331f13c2af61ea1d9e1617d105d6a04573f100e1627 |
| Volume | livenetv2-m12b-test_m12b_postgres_data, único consumidor confirmado |
| Portas publicadas | Nenhuma |
| Ligação explícita | 172.27.0.2:5432, sem DATABASE_URL |
| Base | livenet_m12b_test |
| Bootstrap / session_user | livenet_m12b_bootstrap / livenet_m12b_bootstrap |
| system_identifier | 7699783234487926818 |
| PostgreSQL | 16.15, server_version_num=160015 |
| Ledger aplicacional | public.alembic_version = f066a01a7230, única linha |

Na leitura inicial às 11:23:06 UTC e novamente na transação de provisionamento:
security, authorization, ledger security e as quatro novas roles estavam ausentes.
Existiam apenas public, inventory e audit, com 12 tabelas inventory, audit.events
e o ledger aplicacional. Todas as tabelas eram de bootstrap, sem grants por coluna.
Não se observaram outras sessões na base; a ausência foi novamente verificada
antes do commit PostgreSQL. Não foram canceladas sessões nem adquiridos locks
explícitos ou advisory locks.

O contentor de destino coincide integralmente com R3. A primeira comparação
estrita dos contentores encontrou apenas uma diferença de ordem no array Mounts
de livenetv2-db-1. Comparando os mounts por Destination, os objetos coincidem;
não houve alteração de mounts ou falha de identidade do destino.

## Roles e credenciais

| Role | LOGIN | Atributos administrativos | Memberships | Ownership |
| --- | --- | --- | --- | --- |
| livenet_m12b_inspector | Sim | Nenhum | Nenhuma | Nenhum |
| livenet_m12b_migrator | Sim | Nenhum | Nenhuma | Nenhum |
| livenet_m12b_app | Sim | Nenhum | Nenhuma | Nenhum |
| livenet_m12b_security_owner | Não | Nenhum | Nenhuma | Nenhum nesta etapa |

As quatro roles usam NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION,
NOBYPASSRLS e NOINHERIT. Não foi concedida membership da security_owner.
Foram verificadas memberships em ambos os sentidos e ausência de ownership de
bases, schemas, relações e funções. Bootstrap não foi alterado.

Cada LOGIN recebeu password independente gerada com secrets.token_urlsafe(48).
Foram produzidos verificadores SCRAM-SHA-256 por libpq, sem passwords em texto
simples nas instruções SQL. A validação de pg_authid devolveu apenas booleanos
sobre o formato SCRAM; nenhum verificador foi recolhido ou apresentado.
security_owner tem password NULL.

Segredos em /home/paulo/.local/share/livenet-v2/m12b-test/prov1:
livenet_m12b_inspector_password, livenet_m12b_migrator_password e
livenet_m12b_app_password. Diretório e pai verificados com 0700; três ficheiros
criados exclusivamente, sem sobrescrita, com 0600 e fsync antes do commit.
A password bootstrap existente não foi alterada. Não há segredos neste relatório.

Antes do SQL sensível verificaram-se log_statement=none, logging de duração e
amostragem desativados e ausência de bibliotecas preload. Apenas nesta transação,
SET LOCAL elevou log_min_error_statement para panic e colocou os dois limites de
logging de parâmetros em zero. Essas proteções terminaram com a transação e não
alteraram configuração persistente. Exceções do driver não seriam apresentadas.

## ACL antes e depois

| Objeto | Antes | Depois |
| --- | --- | --- |
| Base M1.2B / PUBLIC | CONNECT, TEMPORARY | Nenhum dos dois |
| Base M1.2B / bootstrap | Owner: CONNECT, CREATE, TEMPORARY | Preservado |
| Base M1.2B / inspector, migrator, app | Roles ausentes | CONNECT explícito, sem grant option |
| Base M1.2B / security_owner | Role ausente | Sem CONNECT, CREATE ou TEMPORARY |
| Schema public | PUBLIC USAGE; pg_database_owner USAGE/CREATE | Inalterado |
| Schemas inventory/audit | Bootstrap USAGE/CREATE | Preservado; acrescentado apenas USAGE ao inspector |
| 13 tabelas inventory/audit | ACL de tabela default do owner, sem ACL por coluna | ACL de tabela preservada; SELECT(id) apenas ao inspector |
| public.alembic_version | ACL de tabela default do owner, sem ACL por coluna | ACL de tabela preservada; SELECT(version_num) ao inspector e migrator |
| Outras bases do mesmo cluster | ACL anteriores | Inalteradas; nenhum grant explícito às novas roles |

Não se revogaram privilégios existentes de inventory/audit. Os únicos acréscimos
nesses schemas são o USAGE e os grants por coluna do inspector expressamente
autorizados no pedido. Não foram concedidos SELECT de tabela, grant options,
CREATE, TEMPORARY, DML ou membership a qualquer role nova.

ACL final da base:

```text
{livenet_m12b_bootstrap=CTc/livenet_m12b_bootstrap,livenet_m12b_inspector=c/livenet_m12b_bootstrap,livenet_m12b_migrator=c/livenet_m12b_bootstrap,livenet_m12b_app=c/livenet_m12b_bootstrap}
```

Cada uma das 13 colunas id tem apenas o novo grant
livenet_m12b_inspector=r/livenet_m12b_bootstrap. version_num tem os dois grants
equivalentes para inspector e migrator. Não há outros grants por coluna.

## Matriz de privilégios efetivos

| Identidade | CONNECT | CREATE base/public | TEMP | USAGE inventory/audit | Leitura aplicacional | Ledger aplicacional | DML |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Inspector | Sim | Não | Não | Sim | Apenas id nas 13 tabelas | Apenas SELECT(version_num) | Não |
| Migrator | Sim | Não | Não | Não | Não | Apenas SELECT(version_num) | Não |
| App | Sim | Não | Não | Não | Não | Nenhum | Não |
| Security owner | Não; NOLOGIN | Não | Não | Não | Não | Nenhum | Não |
| Bootstrap | Sim | Sim | Sim | Sim | Administrador | Administrador | Administrador preservado |

Todas as novas roles mantêm USAGE de public e permissões predefinidas de leitura
de catálogos PostgreSQL. pg_control_system() já era executável via privilégios
predefinidos; as três ligações reais confirmaram-no. Não foi necessário conceder
EXECUTE adicional nem USAGE redundante em public.

Colunas R2 determinadas diretamente no código: count(id) para cada tabela
inventory/audit e version_num para o ledger. A lista fechada é:
inventory.resources, resource_identifiers, resource_relations, groups,
group_memberships, group_rules, tags, resource_tags, policies, policy_versions,
policy_assignments, effective_configs; audit.events.

## Execução e validações

Foi usada uma única transação PostgreSQL explícita, com identidade, baseline,
roles ausentes, acesso administrativo e ausência de outras sessões novamente
verificados antes das alterações. Operações persistentes:

1. CREATE ROLE das quatro identidades com os atributos acima.
2. REVOKE CONNECT, TEMPORARY ON DATABASE livenet_m12b_test FROM PUBLIC.
3. GRANT CONNECT nessa base aos três LOGIN.
4. GRANT USAGE em inventory/audit exclusivamente ao inspector.
5. GRANT SELECT(id) nas 13 tabelas exclusivamente ao inspector.
6. GRANT SELECT(version_num) no ledger a inspector e migrator.

Validações passaram antes do commit e novamente numa nova ligação bootstrap
READ ONLY após commit confirmado. Não houve falha, rollback ou commit incerto;
não foram repetidos CREATE ROLE. Foram comparadas ACL das outras bases do mesmo
cluster, sem ligação a essas bases, e permaneceram iguais.

As três novas identidades autenticaram em ligações separadas READ ONLY, com
current_user=session_user corretos, identidade física e system_identifier exatos.
Inspector executou as 13 consultas count(id) do contrato e leu o ledger; migrator
leu o ledger; app executou apenas a identificação e consultas de catálogo.
Não se executou a rotina R2 que adquire advisory lock ou qualquer executor.

Verificações negativas passaram usando has_database_privilege,
has_schema_privilege, has_table_privilege, has_any_column_privilege e
has_column_privilege, incluindo direitos efetivos herdados:

- Sem CREATE/TEMPORARY, ownership ou memberships para as quatro roles.
- Sem CREATE nos três schemas; migrator/app/owner sem USAGE inventory/audit.
- Sem direitos de escrita por tabela ou coluna nas 14 tabelas.
- Sem SELECT de tabela e sem SELECT por coluna além dos grants exatos previstos.
- App/owner sem leitura do ledger; nenhuma role nova pode alterar o ledger.
- PUBLIC sem CONNECT/TEMPORARY nesta base; bootstrap com acesso preservado.

Não se tentaram INSERT, DDL, criação de objetos, alteração de ledger ou acesso
a bases protegidas para testar negativas. Não foram criadas contas LiveNet.

A comparação física antes/depois das 14 tabelas confirmou owners, tipos,
nulabilidade, defaults, constraints, índices, triggers e flags RLS inalterados.
Não foi executado DML aplicacional. As ACL de tabela permaneceram iguais;
apenas ACL dos schemas/colunas autorizadas foram acrescentadas.
Ledger f066 preservado; security, authorization e ledger security continuam
ausentes. Não se realizou uma auditoria de conteúdo linha a linha.

## Recuperação e integridade

Nova autenticação bootstrap pós-commit confirmou acesso funcional e os atributos
administrativos anteriores. O seu ownership e a sua credencial foram preservados.
Isto comprova administração atual. Recuperação independente após perda de
credenciais ou despromoção do único administrador continua não demonstrada,
como em R3; não houve restauro, intervenção Docker ou criação de outro superuser.

Os 31 hashes protegidos coincidem com os anteriores, incluindo os 15 ficheiros
AUTH-03 e Compose M1.2B. Não foi atualizado qualquer manifesto. Os seis
contentores mantêm ID, imagem, estado/health, arranque, restart count, mounts e
redes; volume e rede exclusivos foram reconfirmados. Não se estabeleceram
ligações PostgreSQL a ambientes protegidos; a evidência sobre esses ambientes
limita-se à integridade dos ficheiros e inspeções Docker, sem alegar auditoria
interna das suas bases.

Os testes offline das duas guardas AUTH-03 passaram: 10 pass, 0 fail, 0 skip.
AST confirmou execution_enabled=False. operation_gate() continua bloqueado.
git diff --check e whitespace adicional deste relatório: sem erros.
Nenhum teste modificador de persistência foi executado.

## Pendências para PROV2

- Executor continua desativado. Migrator ainda não satisfaz os requisitos de
  CREATE temporário, deliberadamente ausentes nesta etapa.
- Ausência amostrada de escritores e revogação de CONNECT de PUBLIC não
  demonstram exclusividade da futura janela. Os três LOGIN têm CONNECT, mas app
  continua sem canal DML; bootstrap/administrador host devem ser coordenados.
- Roles são globais apenas neste cluster descartável. Nenhuma recebeu grants
  explícitos noutras bases; CONNECT herdado de PUBLIC em postgres/templates
  pode continuar efetivo. Não se alteraram essas bases ou HBA para o impedir.
- ssl permanece off na rede interna. HTTPS/TLS, recuperação independente,
  adaptadores operacionais e transporte de credenciais exigem revisão própria.
- DML security, FOR UPDATE, ownership final e memberships futuras continuam
  pendentes. Não há concessões antecipadas para ultrapassar esses bloqueios.

## Git após a execução

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
?? docs/specifications/f0/m12b-p2c2a-prov1-report.md
?? docs/specifications/f0/m12b-p2c2a-r3-operational-preflight.md
?? scripts/postgres/auth03_alembic_executor.py
?? scripts/postgres/auth03_executor.Dockerfile
?? scripts/postgres/auth03_executor.Dockerfile.dockerignore
?? scripts/postgres/auth03_executor.example.json
?? scripts/postgres/auth03_executor_integrity.json
?? scripts/postgres/tests/test_auth03_alembic_executor.py
```

Todas as entradas acima são preexistentes exceto este relatório. Sem staging,
commit ou push; PROV2 e P2C-2B não iniciados.
