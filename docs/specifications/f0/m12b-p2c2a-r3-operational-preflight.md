# M1.2B-P2C-2A-R3 — Pré-validação operacional read-only

## Âmbito e evidência

Inspeção em 2026-10-23, amostra inicial às 11:11:46 UTC. Git main,
HEAD b2605975a4fb87f25aa84afcda3f10dac77cfd4c. O único ficheiro criado nesta
etapa é este relatório. A alteração local em backend/migrations/env.py e os
ficheiros AUTH-03/Compose não versionados são preexistentes e preservados.

Foram usadas apenas inspeções Docker, leitura local e consultas PostgreSQL por
ligação explícita ao IP validado, com default_transaction_read_only=on, confirmado
por transaction_read_only=on. Não se utilizou DATABASE_URL, Alembic ou o executor.
Não foram lidos rolpassword, variáveis de password do contentor ou texto de
consultas de outras sessões. A credencial bootstrap existente foi usada em memória
para autenticação, sem output, argumento CLI ou ficheiro novo de credenciais.

Não foram executados SQL modificador, DDL, GRANT/REVOKE, alterações de roles,
ownership/configuração, advisory locks, LOCK TABLE ou operações Docker mutadoras.
Locks AccessShare automáticos das consultas SELECT são identificados abaixo.
Pré-validação não é teste de execução de migração ou de recuperação.

## Docker e comparação histórica

| Campo | Valor observado |
| --- | --- |
| Projeto | livenetv2-m12b-test |
| Contentor | livenetv2-m12b-test-db-1 |
| ID completo | 540e8834355c281d5874603b82231b006486e3a74103bda04bead0ac77fbc5ec |
| Estado | running, healthy |
| Arranque | 2026-10-23T08:51:26.119741529Z |
| RestartCount | 0 |
| Imagem fixada | postgres:16-alpine@sha256:f4610795587492cd4fb887c2dc3de301b813278bb6f616992061141b5f15ac36 |
| ID da imagem local | sha256:6a2e324ebe59af6031c4c1cd96c1d5072c2ebc36563d2196365e43b8297c062d |
| Rede | livenetv2-m12b-test_m12b_backend, internal=true |
| ID da rede | cda632938bb938b51bfdc331f13c2af61ea1d9e1617d105d6a04573f100e1627 |
| Membros da rede | apenas este contentor |
| IP interno | 172.27.0.2/16 |
| Portas publicadas | nenhuma |
| Volume | livenetv2-m12b-test_m12b_postgres_data, exclusivo deste projeto/contentor |

Dois mounts: volume de dados em /var/lib/postgresql/data, leitura/escrita, e
credencial bootstrap exclusiva em /run/secrets/m12b_bootstrap_password, read-only,
com origem fora do Git. Nenhum volume ou rede de projetos protegidos foi montado.
O RepoDigest coincide com a referência fixada e com o registo P2A.

Imagem, digest, IP, nomes da rede/volume e exclusividade coincidem com os relatórios
anteriores. Os relatórios anteriores não registavam o ID completo do contentor;
esse identificador fica agora explícito, sem alegar comparação histórica inexistente.
A comparação de início/fim de R3 verifica também ID, imagem, arranque, restart count,
mounts e redes dos cinco contentores protegidos e do contentor M1.2B.

## Identidade e estado PostgreSQL

| Verificação | Resultado |
| --- | --- |
| current_database() | livenet_m12b_test |
| current_user / session_user | livenet_m12b_bootstrap / livenet_m12b_bootstrap |
| system_identifier | 7699783234487926818 |
| server_version_num | 160015, PostgreSQL 16.15 |
| inet_server_addr / port | 172.27.0.2/32, 5432 |
| Transação da inspeção | READ ONLY |
| public.alembic_version | f066a01a7230, única linha |
| Schemas não internos | public, inventory, audit |
| security / authorization | ausentes |
| public.alembic_security_version | ausente |

As 12 tabelas inventory e audit.events estão presentes, assim como o ledger
aplicacional: 14 relações não internas, todas tabelas. A inspeção foi de catálogo;
não se recontaram dados aplicacionais nem se repetiram testes de constraints.
Não foi aplicada a revisão security b12b01a7230.

## Roles, ownership e ACL efetivas

Bootstrap é o único LOGIN e a única role com atributos administrativos globais:
SUPERUSER, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS, LOGIN e INHERIT são true;
rolconnlimit=-1. Esta observação resolve a hipótese pendente em R1/R2: reduzir
bootstrap agora retiraria o único administrador PostgreSQL autenticável observado.

As quatro roles futuras estão ausentes: livenet_m12b_inspector,
livenet_m12b_migrator, livenet_m12b_app e livenet_m12b_security_owner.
Não existem memberships explícitas de bootstrap. As únicas linhas de pg_auth_members
são as três memberships predefinidas de pg_monitor em pg_read_all_settings,
pg_read_all_stats e pg_stat_scan_tables; ADMIN=false, INHERIT=true, SET=true.
Bootstrap surge como grantor dessas linhas, não como member.
pg_database_owner inclui bootstrap implicitamente por ser owner da base.

| Objeto | Owner | ACL efetiva relevante |
| --- | --- | --- |
| Base livenet_m12b_test | bootstrap | PUBLIC: CONNECT/TEMPORARY; owner: CONNECT/CREATE/TEMPORARY |
| Schema public | pg_database_owner | PUBLIC: USAGE; owner: USAGE/CREATE |
| Schemas inventory/audit | bootstrap | Owner: USAGE/CREATE; sem grants PUBLIC |
| 13 tabelas aplicacionais | bootstrap | Apenas owner: SELECT/INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER |
| public.alembic_version | bootstrap | Mesmos privilégios de owner; sem grants PUBLIC ou terceiros |

ACL nula de base/tabelas/schemas inventory/audit foi interpretada com acldefault
e aclexplode, não como ausência de direitos. As tabelas/ledger produzem 98 entradas
efetivas, todas de bootstrap. Não há ACL explícita por coluna. RLS e FORCE RLS
estão false nas 14 tabelas. O bootstrap, por ser superuser, não fica limitado às
ACL declaradas: os seus CONNECT/CREATE/TEMPORARY efetivos são true.

As duas funções de inventory/audit são prevent_policy_version_mutation e
prevent_event_mutation, ambas owner bootstrap, SECURITY INVOKER, ACL predefinida.
Não se encontrou função SECURITY DEFINER nesses dois schemas. Isso não representa
auditoria completa de todos os caminhos privilegiados do cluster ou extensões.

## Recuperação administrativa

**A — comprovado:** autenticação atual de bootstrap neste destino e observação dos
seus poderes administrativos globais. Isto comprova acesso atual, não recuperação
de perda de credenciais ou de redução de privilégios.

**B — tecnicamente possível, não testado:** administração pela infraestrutura do
cluster descartável. O contexto Docker default usa unix:///var/run/docker.sock;
as inspeções funcionaram e não foi reportado plugin de autorização Docker. Uma
intervenção administrativa controlada sobre a instância/volume ou um restauro pode
ser uma via de recuperação, mas não se executaram exec, paragem, restauro ou acesso
à consola da VM. Não se afirma que essas operações foram autorizadas ou testadas.

**C — não demonstrado:** recuperação independente após perder ou despromover o
único superuser. Não existe segunda identidade administrativa LOGIN observada,
nem runbook de recuperação testado nesta execução. O acesso à consola Proxmox/host
e um restauro funcional não foram validados. Preservar bootstrap e a sua credencial
até uma etapa separada comprovar a via de recuperação. Não reduzir os seus atributos
como parte automática do provisionamento.

## Sessões, locks e exclusividade

Na primeira amostra de pg_stat_activity da base existia apenas o backend desta
inspeção: PID 12125, bootstrap, cliente 172.27.0.1, transação read-only ativa, sem
backend_xid atribuído. Não foi observado outro escritor ou transação aberta de
aplicação. A amostra não é monitorização contínua e pode não apanhar ligações breves
de healthcheck. Texto de consultas alheias não foi recolhido.

Não se observaram advisory locks nem locks relevantes pendentes. Os únicos locks
de relações aplicacionais/public amostrados eram AccessShareLock concedidos à própria
inspeção sobre public.alembic_version e o seu índice alembic_version_pkc, resultantes
do SELECT do ledger. Não foram adquiridos locks explícitos nem canceladas sessões.

A ausência atual de escritores **não demonstra exclusividade futura**:

- datallowconn=true e datconnlimit=-1; bootstrap também tem rolconnlimit=-1.
- listen_addresses='*', porta 5432, max_connections=100 e três slots reservados
  a superuser. ssl=off; password_encryption=scram-sha-256.
- pg_hba_file_rules não apresenta erros: regras locais/loopback usam SCRAM e
  existe uma regra host all/all/all scram-sha-256. Não foram lidas opções contendo
  segredos nem alteradas regras/configuração.
- A própria ligação a partir de 172.27.0.1 demonstra acesso do host à bridge.
  Rede internal e ausência de portas publicadas não impedem esse acesso local,
  nem a intervenção de quem administra Docker/host.
- PUBLIC ainda concede CONNECT; bootstrap pode voltar a ligar e escrever,
  independentemente dos advisory locks cooperativos. Nenhum fencing foi testado.

Proposta futura, sujeita a autorização própria: revogar CONNECT/TEMPORARY de PUBLIC
apenas nesta base; adiar LOGIN/CONNECT da app até fechar a migração; limitar o canal
operacional às identidades e fontes previstas, preservando um canal de recuperação
administrativa verificado. Se necessário, desenhar uma restrição HBA/rede temporária
e testada, sem mudar Compose ou HBA nesta etapa. Conferir sessões/credenciais/canais
privilegiados e manter exclusão administrativa durante toda a janela.

Não tratar limite de ligações, read-only de uma sessão, REVOKE CONNECT ou advisory
locks como proteção contra um superuser/administrador hostil. A via administrativa
tem de ser confiável e coordenada. Sem prova desse controlo, manter o executor
desativado, mesmo que a base pareça inativa na amostra.

## Compatibilidade e ajustes necessários ao plano R2

| Pressuposto | Avaliação read-only |
| --- | --- |
| Baseline f066, security ausente, destino isolado | Confirmados |
| NOLOGIN como owner final | Modelo viável em PostgreSQL 16; não provisionado nem testado operacionalmente |
| Inspector SELECT(id)/ledger version_num | Compatível com tabelas existentes e sem RLS; grants e ligação da role ainda não testados |
| Migrator sem inventory/audit | Compatível com separação R2; necessita apenas leitura de version_num do ledger public, além do próprio security futuro |
| CREATE base/public temporário | Não concedido; bootstrap atual tem autoridade para o futuro ciclo aprovado |
| Transferência de ownership | Bootstrap superuser tem autoridade atual; testar e validar somente numa etapa autorizada, após persistência |
| Revogação de memberships/CREATE | Apenas planeada; nenhuma membership nova existe para revogar |
| Migrações futuras sob owner NOLOGIN | Exigem novo contrato que trate SET ROLE; o atual exige session_user=current_user=migrator |
| Recuperação antes de reduzir bootstrap | Não demonstrada independentemente; bloqueio confirmado |
| Exclusão de escritores fora do protocolo | Não demonstrada; bloqueio confirmado para ativação |

Não alterar R1/R2 nesta etapa. Registar para a próxima revisão: bootstrap é
efetivamente o único superuser; a aplicação deve permanecer sem canal de escrita
durante a janela; PUBLIC e HBA atuais não constituem fencing; os adaptadores reais
e transporte de credenciais continuam por auditar. A revisão de FOR UPDATE e do
DML da app continua pendente. Nenhuma concessão foi efetuada para ultrapassar
essas dependências.

## Validação final e critérios de autorização

A comparação final foi feita às 11:15:29 UTC, noutra ligação READ ONLY (PID 12446).
Identidade, baseline, schemas, relações, roles, memberships, owners/ACL por
base/schema/tabela/coluna, rotinas, configurações e regras HBA coincidem com a
primeira leitura: 16 grupos de resultados estáveis comparados, sem divergência.
Security/authorization/ledger security e as quatro roles futuras continuam ausentes.
Na segunda amostra existia novamente apenas a própria inspeção, sem advisory locks
ou locks relevantes pendentes. PIDs e locks automáticos das próprias inspeções são
transitórios, não alterações de ACL/roles/schema.

Os seis contentores comparados mantêm ID, imagem, estado/health, arranque,
restart count, mounts e redes; rede/volume exclusivos mantêm identidade e membros.
Os 31 hashes locais protegidos, incluindo os 15 ficheiros AUTH-03 e Compose M1.2B,
permanecem iguais aos anteriores. operation_gate() continua a recusar mutações e
execution_enabled continua False. A única diferença tracked é env.py já existente
antes de R3; o único novo artefacto desta etapa é este documento.

git diff --check e verificação adicional de whitespace deste ficheiro: sem erros.
Não foi executada suite de integração nem teste operacional de recuperação ou
exclusão. Não houve commit/push, alteração de Compose, provisionamento ou migração.

Para autorizar provisionamento posteriormente: identidade e hashes novamente
corretos, aprovação do transporte seguro de três credenciais, roles restritas e
owner NOLOGIN, redução de PUBLIC limitada à base, validação efetiva de ACL por
tabela/coluna e ausência de memberships indiretas. Não reduzir bootstrap enquanto
a recuperação independente estiver por comprovar. A ativação/migração continua
a exigir prova de exclusividade, adaptadores auditados e autorização própria.

Não foi testada execução Alembic, permissões reais de roles inexistentes, migração,
rollback DDL, handoff de ownership, recuperação ou persistência security. A única
revisão instalada continua a ser a baseline aplicacional.
