# M1.2B-P2C-2A-R1 — Revisão de privilégios, sem execução

Revisão R2: [separação de inspeção e execução](m12b-p2c2a-r2-inspection-handoff.md).
M1.2B-D05 aprova o owner NOLOGIN e a revogação CONNECT/TEMPORARY de PUBLIC nesta
base. O coordenador R2 move a leitura protegida para livenet_m12b_inspector;
as incompatibilidades do executor R1 abaixo ficam como histórico da decisão,
não como instrução para conceder SELECT inventory/audit ao migrator. O plano SQL
foi atualizado, mas continua documental e sem autorização operacional.

## Estado e decisão

Referência local: main, dbf5454e70a3477c85fdc7f37b9254b1918ce27d.
O catálogo abaixo provém do relatório anterior; não foi reconsultado nesta etapa.
Base livenet_m12b_test, projeto livenetv2-m12b-test, system_identifier
7699783234487926818, PostgreSQL 16, ledger aplicacional f066a01a7230.
Não existem security, authorization, ledger security, migrator ou app nesse relatório.
Base, inventory/audit e suas tabelas pertencem ao bootstrap; public pertence a
pg_database_owner. PUBLIC tem CONNECT/TEMPORARY na base e USAGE em public.
ACL nula significa ACL predefinida, não ausência de privilégios do owner/PUBLIC.

M1.2B-D04 aprova CREATE temporário, seguido de revogação. Este documento propõe
o ciclo completo; não autoriza a sua execução. Todo o SQL está apenas em Markdown,
sem script executável, credenciais ou ligação de base de dados.

## Incompatibilidades a resolver antes de executar

1. O executor consolidado faz SELECT count(*) nas 13 tabelas inventory/audit e
   SELECT no ledger aplicacional. O requisito R1 de migrator sem acesso a esses
   schemas impede esse fluxo. Não conceder SELECT silenciosamente: rever o
   executor para receber a inspeção protegida por um observador administrativo
   read-only, na mesma janela coordenada, ou aprovar uma exceção SELECT limitada.
   A proposta preferida mantém migrator sem acesso a inventory/audit. O SQL abaixo
   não concede esse acesso e, por isso, ainda não permite ativar o executor atual.
2. O executor exige ownership migrator tanto antes do commit como na nova ligação.
   A transferência final tem de ocorrer depois dessas verificações; não a inserir
   entre commit e confirmação de persistência. O estado final tem outro validador.
3. Os atributos globais do bootstrap não foram recolhidos no relatório de ACL.
   Não inferir que é NOSUPERUSER por ser owner. O utilizador de initdb normalmente
   é superuser; isto é hipótese a confirmar, não um resultado desta inspeção.
   R1 exige estado final sem poderes globais para as identidades. A eventual
   redução do bootstrap só pode ocorrer com administração/recuperação alternativa
   aprovada e testada. Não despromover o único administrador sem essa decisão.
4. A role NOLOGIN adicional foi aprovada em D05; o seu provisionamento não foi.
   Não é conta aplicacional nem mecanismo AUTH-03. Sem aprovação do provisionamento,
   não abrir a janela CREATE nem provisionar parcialmente.

Nenhum destes pontos foi resolvido alterando código consolidado ou protegido.
O plano é uma sequência condicional: os bloqueios acima são pré-condições reais,
não avisos que possam ser ignorados por um operador.

## Matriz proposta

Todas as roles novas: NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS,
NOINHERIT e nenhuma membership administrativa global. Bootstrap deve satisfazer
os mesmos atributos no estado final, condicionado à decisão de recuperação.

| Identidade | Provisionada, fora da janela | Durante migração | Estado final |
| --- | --- | --- | --- |
| livenet_m12b_bootstrap | Administração já existente; atributos por confirmar | Operador autorizado concede/revoga privilégios; não executa como migrator | Mantém ownership da base/inventory/audit; sem poderes globais após transição aprovada |
| livenet_m12b_migrator | CONNECT e USAGE em public; sem CREATE/TEMPORARY, sem inventory/audit | CREATE na base/public, EXECUTE de pg_control_system; cria e possui security, quatro tabelas e ledger próprio | CONNECT/USAGE public; sem ownership, memberships, CREATE, TEMPORARY ou privilégios nos ledgers |
| livenet_m12b_inspector | CONNECT, USAGE inventory/audit/public, SELECT(id) nas 13 tabelas e SELECT(version_num) no ledger aplicacional; EXECUTE pg_control_system | Ligação própria read-only e lock de coordenação; sem escrita, ownership, CREATE ou memberships | Mantém apenas essa leitura de conformidade; não recebe acesso às tabelas ou ledger security |
| livenet_m12b_app | CONNECT e USAGE public herdado; sem outros grants | Sem utilização e sem ownership | USAGE security e apenas DML específico posteriormente aprovado; sem ledgers/DDL/inventory/audit |
| livenet_m12b_security_owner | NOLOGIN, sem credencial, sem membership | Sem uso até handoff | Owner apenas de security, quatro tabelas e ledger security; sem CREATE na base/public |

Bootstrap poderá receber ADMIN TRUE, INHERIT FALSE, SET FALSE sobre a role owner
para gerir apenas a delegação local futura. Isso continua sendo poder administrativo
local deliberado: permite voltar a conceder SET/INHERIT; não é isolamento contra
bootstrap. Não conceder essa capacidade a migrator/app nem a roles globais.

## PUBLIC, memberships e ownership

M1.2B-D05 determina revogar CONNECT de PUBLIC nesta base: autorizar as identidades por
nome em vez de aceitar qualquer role futura. Não desconecta sessões já abertas,
não substitui pg_hba.conf e não afeta CONNECT noutras bases. Roles são globais ao
cluster: confirmar o cluster isolado também antes de CREATE ROLE.

Revogar TEMPORARY de PUBLIC retira a fonte herdada comum. Só demonstra ausência
de CREATE TEMP TABLE se não houver grant direto, membership transitiva, ownership
da base ou superuser. NOINHERIT sozinho não basta: SET ROLE pode permitir escalada.
Usar ligações novas e inspecionar também sessões/objetos temporários preexistentes.
Não executar CREATE TEMP TABLE como teste nesta revisão.

USAGE em public não permite criar objetos nem ler/escrever tabelas sem privilégios
nessas tabelas. Mantê-lo evita alterar requisitos da extensão btree_gist existente.
Não revogar USAGE de PUBLIC globalmente nesta etapa. Inspecionar EXECUTE herdado
de PUBLIC em rotinas, sobretudo SECURITY DEFINER: ausência de DML direto não exclui
uma função que escreva. Qualquer rotina privilegiada inesperada bloqueia o plano.

pg_database_owner contém implicitamente o owner da base; não conceder nem transferir
ownership da base a migrator/app/owner security. Membership na role proprietária
pode conferir os poderes do owner. REVOKE CREATE na base/public não elimina ALTER,
DROP ou GRANT inerentes ao owner de objetos já criados. A transferência final para
NOLOGIN e a ausência de membership são necessárias para retirar esse poder ao LOGIN.
[Privilégios](https://www.postgresql.org/docs/16/ddl-priv.html),
[memberships](https://www.postgresql.org/docs/16/role-membership.html) e
[pg_database_owner](https://www.postgresql.org/docs/16/predefined-roles.html).

## Contrato de aplicação e DML futuro

Não conceder DML nesta fase, pois as tabelas security ainda não existem.
Após migração, considerar SELECT em local_users/global_role_grants;
SELECT/INSERT em login_sessions e login_throttles, e UPDATE apenas nas colunas
modificadas (sessões: last_activity_at/revoked_at; throttle: window_started_at/attempts).
Sem INSERT/DELETE em local_users ou global_role_grants e sem DELETE/TRUNCATE gerais.

Há uma necessidade adicional no código M1.2A: login lê local_users com FOR UPDATE.
PostgreSQL 16 exige UPDATE em pelo menos uma coluna para esse lock. SELECT isolado
não basta. Uma opção mínima é UPDATE(updated_at), sem acesso a password_hash,
status, login ou id para escrita; essa opção ainda permite alterar updated_at e
precisa de aprovação e teste real. Alternativa: rever o contrato de lock do serviço
num incremento separado. Não alterar modelos/serviço nem adicionar grants aqui.
[Requisito SELECT/FOR UPDATE](https://www.postgresql.org/docs/16/sql-select.html).

Autenticação também insere audit.events. Como R1 mantém app sem inventory/audit,
não declarar a autenticação pronta: um grant INSERT de auditoria e o acesso REST
inventory exigirão etapa posterior explicitamente aprovada. Os dois ledgers
permanecem inacessíveis à app em todos os estados.

## Plano SQL proposto — apenas documentação

Os blocos não constituem um ficheiro para executar em sequência. Cada fase exige
autorização, atestação Compose/rede/volume sem portas e ligação explícita ao destino.
Não usar DATABASE_URL, credenciais de outros ambientes, head/heads ou AUTH-03.
O executor security permanece execution_enabled=False; nenhum bloco o ativa.

### Guarda comum, na mesma transação de cada fase futura

Comparar primeiro owners/ACL e memberships com o snapshot aprovado; não limpar
privilégios inesperados automaticamente. A divergência provoca ROLLBACK e paragem.
O operador deve verificar os booleanos, não apenas imprimir resultados.

<!-- phase: guard -->
```sql
DO $guard$
BEGIN
  IF current_database() <> 'livenet_m12b_test'
     OR current_user <> 'livenet_m12b_bootstrap'
     OR session_user <> 'livenet_m12b_bootstrap'
     OR (SELECT system_identifier::text FROM pg_control_system()) <> '7699783234487926818'
     OR current_setting('server_version_num')::integer NOT BETWEEN 160000 AND 169999
     OR (SELECT array_agg(version_num ORDER BY version_num)
         FROM public.alembic_version) IS DISTINCT FROM ARRAY['f066a01a7230']::varchar[]
     OR EXISTS (SELECT 1 FROM pg_namespace WHERE nspname='authorization') THEN
    RAISE EXCEPTION 'Destino/baseline divergente: interromper';
  END IF;
END
$guard$;
```

A guarda da sessão migrator usa current_user/session_user migrator, o mesmo
system_identifier e search_path public. Não reutilizar a guarda bootstrap sob
SET ROLE. Para as fases iniciais, exigir ausência de security/ledger security e das
quatro roles novas propostas; para handoff, exigir security com quatro tabelas vazias,
ledger b12b01a7230 e owners migrator. Nenhum IF NOT EXISTS mascara divergências.

### A–C. Provisionamento inicial e verificação

Executar sob autoridade administrativa aprovada, ainda sem reduzir o bootstrap.
BEGIN, guarda comum, lock transacional e verificação das ausências vêm antes do
bloco; pós-condições e COMMIT somente após inspeção efetiva. Guardar snapshot de
owners, ACL, memberships e atributos sem hashes de password.

<!-- phase: provision -->
```sql
CREATE ROLE livenet_m12b_migrator NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB
  NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE livenet_m12b_app NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB
  NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE livenet_m12b_security_owner NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB
  NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE livenet_m12b_inspector NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB
  NOCREATEROLE NOREPLICATION NOBYPASSRLS;
REVOKE CONNECT, TEMPORARY ON DATABASE livenet_m12b_test FROM PUBLIC;
GRANT CONNECT ON DATABASE livenet_m12b_test TO livenet_m12b_bootstrap,
  livenet_m12b_migrator, livenet_m12b_app, livenet_m12b_inspector;
GRANT USAGE ON SCHEMA public TO livenet_m12b_migrator;
GRANT USAGE ON SCHEMA public, inventory, audit TO livenet_m12b_inspector;
GRANT SELECT (version_num) ON TABLE public.alembic_version
  TO livenet_m12b_migrator, livenet_m12b_inspector;
GRANT SELECT (id) ON TABLE inventory.resources, inventory.resource_identifiers,
  inventory.resource_relations, inventory.groups, inventory.group_memberships,
  inventory.group_rules, inventory.tags, inventory.resource_tags, inventory.policies,
  inventory.policy_versions, inventory.policy_assignments, inventory.effective_configs,
  audit.events TO livenet_m12b_inspector;
GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO livenet_m12b_inspector;
```

Passwords: gerar futuramente três credenciais independentes fora do Git (diretório
0700, ficheiros 0600, criação exclusiva), SCRAM-SHA-256; a role owner não tem password.
O transporte deve ser feito por adaptador auditado, com proteção de logs de comandos,
erros e parâmetros no cliente/servidor. Nem plaintext nem verifier SCRAM podem
aparecer em argumentos, histórico, output ou SQL versionado. Não existe ainda esse
adaptador aprovado: manter NOLOGIN até confirmar SCRAM e disponibilidade do segredo.
Não ler/apresentar rolpassword; a verificação administrativa deve devolver só booleanos.

<!-- phase: enable_login -->
```sql
ALTER ROLE livenet_m12b_migrator LOGIN;
ALTER ROLE livenet_m12b_app LOGIN;
ALTER ROLE livenet_m12b_inspector LOGIN;
```

A segunda fase só é admissível após a entrega segura dos segredos e validação das
ACL. Nenhuma conta LiveNet é inserida. Não alterar LOGIN do owner NOLOGIN.

### D. Concessões temporárias

Abrir apenas imediatamente antes da migração autorizada, sem app ligada. Privilégios
CREATE não são atributos CREATEDB/CREATEROLE, mas permitem nomes arbitrários na base
ou em public; não existe GRANT CREATE limitado ao futuro nome de um objeto.

<!-- phase: window -->
```sql
GRANT CREATE ON DATABASE livenet_m12b_test TO livenet_m12b_migrator;
GRANT CREATE ON SCHEMA public TO livenet_m12b_migrator;
GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO livenet_m12b_migrator;
```

Não conceder SELECT/USAGE em inventory/audit para contornar a incompatibilidade do
executor. É obrigatório resolver essa interface antes de abrir a janela.

### E–F. Validação pré-migração e execução futura

Na ligação migrator: identidade exata, sessão própria, search_path=public, sem
transação anterior; transação externa e lock pg_try_advisory_xact_lock(1295073858,6602).
O inspetor mantém pg_try_advisory_lock(1295073858,6601) durante todo o ciclo.
Exigir baseline f066, ausência de authorization/security/ledger security; atributos
restritos, sem memberships transitivas, CREATE apenas nas concessões da janela.
A inspeção protegida é feita pelo inspetor R2 sem dar acesso a inventory/audit ao
migrator. Não existe chamada Alembic neste plano SQL.

Após autorização futura separada, executar apenas b12b01a7230 pela configuração
security. Validar quatro tabelas, 4 PK/2 FK/3 UNIQUE/9 CHECK/índice explícito,
tipos/defaults, duas revisões, tabelas vazias e preservação inventory/audit.
Confirmar commit e persistência noutra ligação física antes do handoff.

### G. Revogação, handoff e nova verificação

Como administrador aprovado: bloquear novos trabalhos, confirmar ausência de outras
sessões migrator/app e adquirir a mesma coordenação. Não terminar sessões à força.
A transferência por superuser não exige membership ao migrator. Se o operador
não for superuser, precisa de direitos do owner atual e SET para o novo owner;
transferir tabelas exige CREATE no schema de destino e transferir schema exige
CREATE na base para o novo owner. Não conceder memberships amplas como atalho.
[ALTER TABLE](https://www.postgresql.org/docs/16/sql-altertable.html),
[ALTER SCHEMA](https://www.postgresql.org/docs/16/sql-alterschema.html).

O bloco seguinte é para a variante com administrador explicitamente autorizado.
CREATE temporário ao NOLOGIN owner suporta a transferência sem o tornar LOGIN;
revogá-lo ainda na mesma transação de handoff. Não usar REASSIGN OWNED global.

<!-- phase: handoff -->
```sql
GRANT CREATE ON DATABASE livenet_m12b_test TO livenet_m12b_security_owner;
GRANT CREATE ON SCHEMA public TO livenet_m12b_security_owner;
ALTER SCHEMA security OWNER TO livenet_m12b_security_owner;
ALTER TABLE security.local_users OWNER TO livenet_m12b_security_owner;
ALTER TABLE security.login_sessions OWNER TO livenet_m12b_security_owner;
ALTER TABLE security.global_role_grants OWNER TO livenet_m12b_security_owner;
ALTER TABLE security.login_throttles OWNER TO livenet_m12b_security_owner;
ALTER TABLE public.alembic_security_version OWNER TO livenet_m12b_security_owner;
REVOKE CREATE ON DATABASE livenet_m12b_test FROM livenet_m12b_migrator,
  livenet_m12b_security_owner;
REVOKE CREATE ON SCHEMA public FROM livenet_m12b_migrator,
  livenet_m12b_security_owner;
REVOKE EXECUTE ON FUNCTION pg_catalog.pg_control_system() FROM livenet_m12b_migrator;
REVOKE SELECT (version_num) ON TABLE public.alembic_version FROM livenet_m12b_migrator;
REVOKE ALL PRIVILEGES ON SCHEMA security FROM livenet_m12b_migrator, livenet_m12b_app, PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE security.local_users, security.login_sessions,
  security.global_role_grants, security.login_throttles,
  public.alembic_security_version FROM livenet_m12b_migrator, livenet_m12b_app, PUBLIC;
```

Índices associados acompanham o ownership das tabelas. Verificar owners pelo
catálogo, inclusive índices, em vez de presumir sucesso. Não transferir public,
inventory, audit, suas tabelas ou a base. DML da app continua sem concessão até
etapa própria; não usar ALTER DEFAULT PRIVILEGES amplo.

Para futuras migrações, aprovar um novo contrato capaz de distinguir session_user
migrator de current_user owner NOLOGIN sob SET LOCAL ROLE, com membership SET TRUE
temporária e INHERIT FALSE. O contrato atual exige igualdade e proíbe memberships:
não o contornar. Ao fechar a janela, RESET ROLE e revogar a membership por um
administrador autorizado. CREATE base/public só volta se a revisão concreta precisar.

Uma variante futura permite ao bootstrap gerir apenas essa membership owner:
GRANTs separados para ADMIN TRUE, INHERIT FALSE e SET FALSE, pois PostgreSQL 16
expõe cada opção separadamente. Essa delegação local e a recuperação administrativa
têm de ser aprovadas antes de reduzir o bootstrap.
[Sintaxe e efeitos de GRANT](https://www.postgresql.org/docs/16/sql-grant.html).

<!-- phase: harden_bootstrap -->
```sql
ALTER ROLE livenet_m12b_bootstrap NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOREPLICATION NOBYPASSRLS;
```

Este último bloco é condicional à autoridade e recuperação alternativas aprovadas;
não executá-lo como consequência automática do handoff. Se bootstrap for o único
administrador, parar: o plano não declara conformidade dos seus atributos até
resolver essa condição. Ownership da base continua a dar-lhe administração local.

## Validação final e aceitação

O validador futuro deve abortar se qualquer observação estiver ausente/inconsistente.
As consultas abaixo são exemplos de evidência, não um validador completo nem SQL
executado nesta etapa. Usar parâmetros seguros nos restantes testes de catálogo.

<!-- phase: validate -->
```sql
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls,
       rolcanlogin, rolinherit FROM pg_roles
WHERE rolname IN ('livenet_m12b_bootstrap','livenet_m12b_inspector','livenet_m12b_migrator',
                 'livenet_m12b_app','livenet_m12b_security_owner');
SELECT has_database_privilege('livenet_m12b_app','livenet_m12b_test','CONNECT') AS app_connect,
       has_database_privilege('livenet_m12b_app','livenet_m12b_test','CREATE') AS app_create,
       has_database_privilege('livenet_m12b_app','livenet_m12b_test','TEMPORARY') AS app_temp,
       has_schema_privilege('livenet_m12b_app','public','CREATE') AS app_public_create;
SELECT version_num FROM public.alembic_version;
SELECT version_num FROM public.alembic_security_version;
SELECT r.rolname,
  NOT has_database_privilege(r.rolname,'livenet_m12b_test','CREATE,TEMPORARY') AS no_database_ddl,
  NOT has_schema_privilege(r.rolname,'public','CREATE') AS no_public_ddl,
  NOT EXISTS (SELECT 1 FROM pg_auth_members m WHERE m.member=r.oid) AS no_memberships,
  NOT EXISTS (SELECT 1 FROM pg_database d WHERE d.datdba=r.oid) AS owns_no_database,
  NOT EXISTS (SELECT 1 FROM pg_namespace n WHERE n.nspowner=r.oid) AS owns_no_schema,
  NOT EXISTS (SELECT 1 FROM pg_class c WHERE c.relowner=r.oid) AS owns_no_relation,
  NOT EXISTS (
    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE c.relkind IN ('r','p','v','m','f')
      AND (n.nspname IN ('inventory','audit','security') OR
           (n.nspname='public' AND c.relname IN ('alembic_version','alembic_security_version')))
      AND (has_table_privilege(r.rolname,c.oid,
             'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
           OR has_any_column_privilege(r.rolname,c.oid,'SELECT,INSERT,UPDATE,REFERENCES'))
  ) AS no_table_or_column_grants
FROM pg_roles r WHERE r.rolname IN ('livenet_m12b_migrator','livenet_m12b_app')
ORDER BY r.rolname;
```

Esperar app_connect=true e os três outros booleanos=false; f066 e b12b01a7230 nos
ledgers após a migração futura. Inspecionar pg_auth_members (ADMIN/INHERIT/SET e
transitividade), pg_namespace/pg_class owners/ACL, privilégios por coluna e EXECUTE
nas rotinas. Não basta has_table_privilege para excluir UPDATE concedido por coluna.
Exigir ausência de ownership/membership de app e migrator e de privilégios sobre
ledgers, inventory/audit, exceto CONNECT/USAGE public descritos na matriz.
Confirmar owners security/ledger da role NOLOGIN, sem CREATE base/public para owner
ou migrator. Revalidar PUBLIC e nenhuma role privilegiada indiretamente alcançável.
Sem CREATE TEMP de teste, DELETE/UPDATE de prova ou downgrade: usar catálogos.
Na matriz final sem DML ainda concedido, a última consulta deve devolver exatamente
duas linhas e todos os booleanos true; menos linhas também é falha. Após aprovar DML
da app, substituir a matriz por allowlist por tabela/coluna, mantendo ledgers e
inventory/audit proibidos. Isto não dispensa inspeção de rotinas e memberships
transitivas, nem comprovação do owner NOLOGIN e dos atributos das cinco roles.

## Transações, falhas e recuperação

CREATE ROLE, GRANT/REVOKE, ALTER OWNER e ALTER ROLE podem ser transacionais no
PostgreSQL 16. Separar provisionamento, janela/migração e handoff por checkpoints
confirmados. Nunca considerar a janela fechada só porque o processo terminou.
Em erro antes do commit: rollback; confirmar estado numa ligação nova. Se a janela
foi concedida numa transação já confirmada, rollback da migração não a revoga:
fechar explicitamente as concessões por administrador após reconciliar o catálogo.
Se migração já confirmou, não executar downgrade; verificar objetos e fazer handoff
somente com revisão b12b01a7230 comprovada. Commit incerto exige reconciliação, sem
retry ou reexecução cega. Falha de fecho/ownership deixa a etapa incompleta.

Os segredos em disco não participam na transação: manter inacessíveis enquanto
NOLOGIN e reconciliar com o estado das roles, sem remover ficheiros/roles
automaticamente. REVOKE CONNECT não encerra sessões existentes; controlar exclusão
de sessões antes da janela. Sem alterações em clusters/Compose protegidos.

R1 termina com documento/testes estáticos. Provisionamento real depende de provisionar
o owner NOLOGIN aprovado em D05, validar autoridade/recuperação do bootstrap, inspeção protegida sem SELECT
do migrator (agora separado em R2), transporte de credenciais, validação efetiva de ACL e a futura janela
de ativação. P2C-2B, migração e autenticação real continuam por autorizar.
