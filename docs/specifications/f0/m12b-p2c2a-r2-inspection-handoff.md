# M1.2B-P2C-2A-R2 — Inspeção separada, handoff interno e execução desativada

## Âmbito e fronteiras

Implementação offline da decisão M1.2B-D05. Não provisiona identidades, gera
credenciais, estabelece ligações ou executa SQL/Alembic/Docker. Mantém main e
dbf5454e70a3477c85fdc7f37b9254b1918ce27d como referência Git. AUTH-03, manifesto,
operation_gate(), Compose, migrações e modelos/autenticação M1.2A não são alterados.
O [plano R1](m12b-p2c2a-privilege-review.md) é atualizado como artefacto documental.

Mantém-se ExecutionAuthorization.execution_enabled=False, sem CLI, DATABASE_URL,
argumento de ativação ou credenciais lidas pelo coordenador. Handoff não é autorização
operacional: a autorização revista em código continua a ser a primeira guarda.
Não há novo segredo, assinatura, ficheiro de recibo ou serviço de autoridade.

## Identidades e consultas

| Identidade | Responsabilidade e privilégios mínimos previstos |
| --- | --- |
| livenet_m12b_bootstrap | Provisionamento/handoff por operador autorizado; mantém owners existentes. Recuperação administrativa validada antes de qualquer redução de atributos. Nunca substitui implicitamente o inspetor. |
| livenet_m12b_inspector | LOGIN separado, sem atributos administrativos, memberships, ownership, CREATE ou TEMPORARY. CONNECT; USAGE public/inventory/audit; SELECT(id) nas 13 tabelas; SELECT(version_num) em public.alembic_version; EXECUTE pg_control_system. Transações exclusivamente read-only. |
| livenet_m12b_migrator | Sem USAGE ou SELECT, inclusive por coluna, em inventory/audit; sem escrita nesses schemas. SELECT(version_num) no ledger public aplicacional. CREATE base/public temporário; EXECUTE pg_control_system; owner transitório de security e ledger próprio. |
| livenet_m12b_app | Sem ownership, CREATE, TEMPORARY, memberships ou ledgers; sem DML concedido nesta etapa. DML futuro sujeito à revisão FOR UPDATE e auditoria. |
| livenet_m12b_security_owner | NOLOGIN, sem credencial, owner final apenas de security/objetos e public.alembic_security_version; sem CREATE base/public. |

A role adicional inspector é necessária para separar leitura protegida e DDL.
Não usar bootstrap, pg_monitor ou pg_read_all_data como atalho; grants explícitos
por coluna limitam a exposição. As credenciais futuras de inspector/migrator/app
serão independentes, SCRAM-SHA-256 e fora do Git, ainda sem criação nesta etapa.
Todas as roles novas ficam sem SUPERUSER/CREATEDB/CREATEROLE/REPLICATION/BYPASSRLS.

Inventário de acesso do código anterior e sua posição em R2:

- protected_fingerprint lê metadados de relações, owners/ACL, colunas/defaults,
  constraints, índices, triggers e funções via pg_catalog. Não requer SELECT nas
  tabelas de aplicação para essas partes. Consultas de catálogo continuam visíveis
  ao migrator, mas a leitura protegida é chamada apenas pelo inspetor.
  O fingerprint inclui ACL por coluna, ownership/ACL de schemas e flags RLS.
  A baseline f066 não tem RLS; se aparecer, recusar a inspeção, pois políticas
  poderiam ocultar linhas de uma identidade sem BYPASSRLS.
- A prova de ausência de dados passa de count(*) para count(id), numa lista fixa
  das 12 tabelas inventory e audit.events. Todos os id são PK não nulos; SELECT(id)
  é suficiente para essa consulta e não permite ler atributos/hash/passwords.
- A revisão f066 é lida em public.alembic_version. SELECT(version_num) não concede
  INSERT/UPDATE/DELETE nesse ledger nem acesso aos schemas inventory/audit.
- O migrator lê catálogos e seus próprios objetos security/ledger. A nova ligação
  migrator read-only verifica esses objetos enquanto o ownership ainda é transitório.
- O inspetor não consulta linhas security nem seu ledger, não necessita de default
  grants sobre tabelas futuras. O seu verificador de privilégios recusa DDL, escrita
  por tabela/coluna, memberships e ownership de bases/schemas/rotinas.

Inspecionar também ACL efetivas de rotinas SECURITY DEFINER na integração futura:
privilégios de tabela não demonstram ausência de caminhos indiretos de escrita.
O código não presume que NOINHERIT neutraliza SET ROLE ou memberships transitivas.

## Sequência síncrona e autoridade da evidência

ExecutionPorts ganha inspector_connect(target, identity=livenet_m12b_inspector,
read_only=True). Não há adaptador operacional predefinido. Os adaptadores futuros
devem ser implementações locais confiáveis, auditadas e sem pooling/reconexão
silenciosa; atestação Compose proveniente de um booleano remoto não é prova.

Dentro de execute_security_migration:

1. Recusar se o contrato de execução estiver desativado; validar plano/fontes e
   atestação do projeto, rede interna, volume e ausência de portas publicadas.
2. Abrir sessão própria do inspetor e verificar identidade PostgreSQL, leitura,
   privilégios, base livenet_m12b_test, system_identifier 7699783234487926818,
   PostgreSQL 16, search_path public e baseline f066a01a7230.
3. Adquirir o lock exclusivo de sessão (1295073858,6601), verificar pg_locks para
   pg_backend_pid() e ler o catálogo inicial e o fingerprint protegido.
4. Criar evidência apenas dentro dessa sessão/coordenador. Abrir a ligação migrator,
   iniciar transação externa, validar identidade e adquirir lock transacional
   exclusivo (1295073858,6602); verificar estado e privilégios mínimos do migrator.
5. Revalidar o plano. Consumir a evidência uma única vez, com releitura real pelo
   inspetor e confirmação de que o fingerprint não mudou. Só então chamar Alembic
   pela configuração security fixa e alvo b12b01a7230, nunca head/heads/f067.
6. Validar fisicamente security na ligação migrator, ainda na transação externa.
   Revalidar inventory/audit pelo inspetor antes do commit.
7. Commit explícito. Abrir outra ligação física migrator, read-only, e verificar
   persistência de ambos os ledgers e estrutura security. Revalidar a conformidade
   protegida pelo inspetor, agora admitindo os cinco objetos relacionais novos.
8. Libertar o lock de sessão e fechar os recursos. Falhas de unlock/fecho não são
   sucesso presumido; exigem reconciliação. Não há retry automático.

_ComplianceSession é a autoridade local, criada pelo coordenador, não pelo chamador.
_InspectionEvidence associa o plano completo (incluindo digest de fontes, destino,
roles, baseline e alvo), operação object-identity, fingerprint e prazo monotónico
de cinco segundos. O registo retido na sessão aceita apenas a instância exata que
emitiu. Booleanos, strings, cópias dataclass, evidências de outra autoridade, planos
alterados, relógio anterior à emissão, expiração e replay são rejeitados. A releitura
também tem de terminar dentro do prazo; não há renovação silenciosa.

O prazo aplica-se ao início autorizado da operação, não limita a duração total da
migração. As validações posteriores são releituras independentes sob o lock mantido.
O fingerprint SHA-256 resume os dados observados; não assina autorização nem prova
proveniência por si mesmo. A proveniência é a leitura da ligação inspetor validada,
o contexto interno retido e a releitura síncrona. Não se aceita evidência serializada
ou trazida por um utilizador/API. Não se pretende defender o processo Python de
código que consiga modificar a sua memória ou substituir adaptadores confiáveis.

## Concorrência e limites que não são garantias

O lock de sessão primário sobrevive ao rollback das transações read-only e abrange
todo o ciclo. O lock transacional secundário é separado para não bloquear o próprio
migrator noutra sessão. Ordem obrigatória: inspetor/6601 antes de migrator/6602;
nenhum participante deve inverter essa ordem ou executar apenas o segundo lock.
A baseline anterior usa 6601, ficando coordenada com a sessão de conformidade.
Cada releitura confirma o lock real em pg_locks, não apenas uma flag em memória.
O adaptador deve fechar fisicamente a sessão; close() de um pool não é suficiente.
[Locks PostgreSQL 16](https://www.postgresql.org/docs/16/explicit-locking.html),
[representação em pg_locks](https://www.postgresql.org/docs/16/view-pg-locks.html).

Advisory locks não impedem participantes que ignorem o protocolo. Releituras não
são fencing e não tornam três ligações uma transação distribuída. O inspetor não
vê alterações não confirmadas feitas noutra sessão. Privilégios do migrator proíbem
escrita/DDL em inventory/audit; o hash não substitui esse controlo. Entre a última
leitura e a execução/commit continua a existir uma janela para escritores externos.

Por isso a integração real exige exclusão administrativa e de todos os escritores
fora do protocolo durante toda a janela. A aplicação não pode estar a escrever,
e o operador administrativo é uma autoridade confiável, não um adversário contido
por estes locks. Não aceitar uma simples declaração boolean de quiescência como
prova. Sem demonstrar o mecanismo de exclusão e os adaptadores na revisão futura,
o executor deve continuar desativado. Não foi acrescentada uma flag que finja
resolver esse problema, um token externo, assinatura ou segredo de teste.

Esta é a alternativa simples ao handoff assinado entre processos: duas identidades
no mesmo coordenador, inspeção síncrona, estado efémero e locks cooperativos.
Um handoff distribuído ou proteção contra administrador hostil não foi implementado
nem é alegado. Se esse requisito surgir, parar essa extensão e rever o modelo.

## Ownership, fecho e recuperação

Migração cria security, quatro tabelas e ledger próprio como migrator. O executor
confirma persistência enquanto esses owners ainda são migrator. Só depois o operador
administrativo aprovado transfere schema/tabelas/ledger ao owner NOLOGIN. A role
owner não necessita de LOGIN nem de credencial. Bootstrap pode fazer a transferência
se possuir autoridade legítima; não assumir atributos globais a partir de ACL.

O plano R1 descreve CREATE temporário ao novo owner quando necessário para ALTER
OWNER e revogação ainda na transação de handoff. Transferir somente objetos security
e o seu ledger; índices seguem as tabelas. Revogar CREATE base/public de migrator e
owner e SELECT(version_num) do migrator no ledger aplicacional explicitamente por
coluna. Não revogar a leitura de conformidade do inspetor por engano.

Não é necessária membership do migrator no owner na instalação inicial. A inspeção
final deve confirmar ausência de memberships diretas/transitivas e de poderes SET,
INHERIT e ADMIN, além de owners/ACL por tabela/coluna. REVOKE CREATE não remove
capacidades de owner. Nunca usar REASSIGN OWNED ou concessões amplas para o fecho.

Migrações futuras sob SET LOCAL ROLE owner exigem novo contrato: o atual exige
current_user=session_user=migrator e proíbe memberships. Uma eventual membership
SET TRUE temporária, INHERIT FALSE e sem ADMIN deve ser concedida/revogada pelo
administrador apenas nessa janela, com verificação de cadeias indiretas.
Não reutilizar evidências ou afrouxar o contrato atual para esse cenário.

Manter recuperação administrativa validada antes de reduzir o bootstrap. Se for o
único administrador, essa redução fica bloqueada até decisão de recuperação testada.
PUBLIC perde CONNECT/TEMPORARY apenas em livenet_m12b_test, com CONNECT explícito
para bootstrap/inspector/migrator/app. Não se alteram outros clusters/Compose.

Erro anterior ao commit: rollback do migrator e fecho do inspetor. Erro no commit,
rollback, persistência ou libertação/fecho: reconcile_required, sem sucesso nem retry.
Privilégios temporários concedidos numa transação já confirmada precisam de revogação
administrativa própria, mesmo se a migração reverter. Não executar downgrade.

## FOR UPDATE e DML da app

M1.2A bloqueia local_users no login. UPDATE(updated_at) é tecnicamente suficiente
para FOR UPDATE no PostgreSQL 16, mas também permite escrever esse timestamp;
não é uma permissão só de lock. FOR SHARE/KEY SHARE também exigem UPDATE e não
resolvem o problema de privilégios. Remover simplesmente o lock pode introduzir
uma corrida com desativação/alteração do utilizador.

Recomendação: não conceder UPDATE(updated_at) silenciosamente nem remover o lock
nesta etapa. Antes de DML real, rever num incremento próprio uma interface de lock
restrita (por exemplo função auditada com privilégios delimitados) e o protocolo
de todos os escritores de utilizadores. Se o tradeoff de UPDATE(updated_at) for
explicitamente aprovado como alternativa menor, limitar à coluna, testar em PG16
e documentar a possibilidade de escrita. Não conceder UPDATE de password_hash,
status/login/id. Nenhum código/modelo de autenticação foi alterado aqui.
[Privilégio exigido por SELECT/FOR UPDATE](https://www.postgresql.org/docs/16/sql-select.html).

## Aceitação e integração futura

Testes offline devem demonstrar rejeição de prova forjada/copiada/expirada/reutilizada,
destino/revisão divergentes, alteração de estado e perda de lock; separação das leituras,
ordem dos locks, rollback, commit incerto, nova ligação física e bloqueio por omissão.
Provar PostgreSQL real, ACL de funções/catálogo, privação de escrita, exclusão de
escritores e ownership final continua a exigir etapa operacional autorizada.
Nenhuma role/credencial, grant/revoke, migração ou autenticação real foi iniciada.
