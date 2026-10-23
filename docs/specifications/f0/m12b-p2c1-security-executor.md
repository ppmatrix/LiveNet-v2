# M1.2B-P2C-1 — Executor security desativado, verificado offline

## Âmbito e decisões

M1.2B-D02 separa bootstrap, migrator e app. M1.2B-D03 exige transação externa,
lock e validação física. Esta etapa escreve o mecanismo e testa-o com doubles.
Não estabelece ligações, executa SQL/Alembic/Docker ou cria roles/credenciais.
AUTH-03, operation_gate(), modelos M1.2A, migrações e Compose não são alterados.

Destino exclusivo: projeto `livenetv2-m12b-test`, base `livenet_m12b_test`,
system_identifier `7699783234487926818`, PostgreSQL 16. Baseline obrigatória
`f066a01a7230`; alvo único `b12b01a7230`, ledger
`public.alembic_security_version`. O grafo security tem apenas essa raiz/head.

## Autorização e interfaces

`ExecutionAuthorization` é um contrato imutável em código, com
`execution_enabled=False`. Não há argumento de ativação, variável de ambiente,
ficheiro de autorização, token, CLI operacional ou autorização por credenciais.
P2C-2 requer alteração deliberada e revista deste contrato; não basta provisionar
a conta migrator. AUTH-03 e login/RBAC não autorizam estas operações.

`execute_security_migration(plan, ports)` verifica o bloqueio antes de tocar
nos adaptadores. `run_alembic()` também verifica esse bloqueio. O plano é
recalculado para rejeitar fontes alteradas, digest forjado, baseline/revisão ou
destino divergentes. As guardas anteriores são preservadas e o system_identifier
passa a exigir o valor exato aprovado, em vez de aceitar qualquer uint64.

`ExecutionPorts` define a fronteira de confiança para adaptadores futuros:

- `attest(target)`: prova do projeto, rede interna exclusiva, volume e ausência
  de portas publicadas, obtida por um adaptador operacional aprovado.
- `connect(target, read_only=...)`: ligação explícita e nova, sem fallback
  aplicacional; configurar search_path/timeouts na abertura, antes da transação.
- `upgrade(config, revision)`: adaptador Alembic chamado apenas com a configuração
  security fixa, ligação externa e revisão exata.

P2C-1 não fornece adaptadores operacionais nem lê passwords. Em testes, apenas
doubles ocupam estas interfaces. Uma atestação fornecida por um chamador qualquer
não constitui prova: implementar/rever os adaptadores confiáveis e a proveniência
do ambiente é pré-requisito de P2C-2. O adaptador de ligação deverá usar NullPool
ou equivalente; a confirmação de persistência exige outra Connection e outro
driver_connection, após fechar a ligação de migração.

## Sequência e transação

1. Verificar autorização, plano/fontes e atestação do ambiente.
2. Abrir ligação sem transação anterior e iniciar transação externa.
3. Validar PostgreSQL, database/current_user/session_user, porta, versão,
   system_identifier, search_path e modo de escrita.
4. Adquirir `pg_try_advisory_xact_lock(1295073858,6601)`. A chave coincide com
   a usada na instalação controlada da baseline M1.2B; a falha recusa a execução.
5. Ler catálogos/ledgers na mesma ligação. Exigir public/inventory/audit e as
   13 tabelas aplicacionais mais o ledger f066, sem security, authorization,
   ledger security ou objetos relacionais inesperados.
6. Verificar privilégios restritos e calcular fingerprint dos catálogos de
   inventory/audit, funções, constraints, índices, triggers, ownership/ACL de
   relações, e exigir tabelas aplicacionais vazias. Não ler conteúdo de linhas.
7. Revalidar o plano e chamar apenas `backend/alembic-security.ini` com a ligação
   externa e alvo b12b01a7230. Não usar head/heads nem o env.py aplicacional.
8. Validar estado pós-migração, estrutura security e preservação do fingerprint.
9. Commit explícito somente após todas as verificações. Fechar a ligação.
10. Revalidar o ambiente e abrir outra ligação física, read-only; repetir identidade,
    ledgers, estrutura e fingerprint para confirmar persistência.

Uma falha anterior ao commit provoca rollback integral. Uma exceção no commit,
falha de rollback, fecho ou verificação após commit exige reconciliação manual;
não se afirma que um commit já confirmado foi desfeito. Não há retries automáticos.
Exceções de adaptadores/drivers são substituídas por mensagens fixas sem SQL,
URL, passwords ou encadeamento de exceções. O relatório de sucesso inclui apenas
status, base, identificador do cluster e revisões. Não há logging de parâmetros.

## Search_path e estrutura física

O contrato usa `search_path=public`, validado literalmente. PostgreSQL pesquisa
pg_catalog implicitamente antes dos schemas explícitos. Em P2B-1, colocar
pg_catalog explicitamente primeiro fez o Alembic tentar criar o ledger nesse
schema; essa configuração não é reutilizada. O ledger security tem ainda schema
public explícito no seu próprio env.py. O executor não altera o env.py existente.

A validação compara tipos PostgreSQL, ordem de colunas, nulabilidade, ausência
de defaults SQL/identity/computed, PK/FK com nomes determinísticos, UNIQUE, CHECK,
índice explícito e ausência de dados com os modelos M1.2A. O ledger é varchar(32)
não nulo, com PK. Schema, tabelas e índices security/ledger devem pertencer ao
migrator; constraints devem estar validadas e não diferíveis. Não se admitem
funções ou triggers aplicacionais em security.

Resultado esperado: 4 PK, 2 FK, 3 UNIQUE, 9 CHECK e 1 índice explícito (mais os
índices de suporte a PK/UNIQUE). O normalizador de CHECK é limitado às nove
expressões revistas: tolera casts textuais e IN/ANY emitidos pelo PostgreSQL,
preservando os literais; recusa misturas AND/OR. Não é um comparador SQL genérico.
As representações reais do catálogo continuam por confirmar em P2C-2.

## Privilégios e provisionamento futuro

| Identidade | Ownership e privilégios previstos |
| --- | --- |
| livenet_m12b_bootstrap | Administração inicial do cluster descartável; mantém ownership da base e de inventory/audit. Provisiona roles/grants; não é aceite como migrator. |
| livenet_m12b_migrator | LOGIN, sem SUPERUSER/CREATEDB/CREATEROLE/REPLICATION/BYPASSRLS, sem memberships. CONNECT, USAGE nos schemas necessários, SELECT nas 13 tabelas e ledger aplicacional para validação. EXECUTE apenas em pg_catalog.pg_control_system() para identificação, se necessário. |
| livenet_m12b_app | LOGIN e CONNECT, USAGE em inventory/audit/security; apenas DML exigido pelos serviços. Não é owner, não tem CREATE em schemas/base, poderes administrativos, memberships privilegiadas ou escrita nos ledgers. |

O migrator necessita temporariamente de CREATE ON DATABASE (para CREATE SCHEMA
security; não equivale ao atributo CREATEDB) e CREATE ON SCHEMA public (para o
ledger próprio). Será owner de security e seus objetos e do ledger security.
PostgreSQL não permite restringir CREATE em public a um único nome futuro; esses
privilégios amplos devem ser concedidos apenas para a janela controlada e
revogados por bootstrap após validação/reconciliação, com autorização específica.
Não precriar security/ledger: as guardas exigem ausência inicial.

O migrator não pode ser owner da base, public, inventory/audit ou relações
protegidas, nem membro de roles proprietárias. Não recebe CREATE em inventory/audit,
INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER nas suas tabelas ou poderes de
alterar authorization. PUBLIC também não deve conceder esses poderes. O executor
valida estes limites; não os provisiona. As funções protegidas mantêm owners
bootstrap; auditar ACL das funções durante o provisionamento futuro.

A app precisará de SELECT/INSERT/UPDATE nas tabelas security conforme os serviços
de autenticação e throttle; inventory recebe apenas operações implementadas e
audit.events apenas INSERT para auditoria transacional (SELECT somente se aprovado).
Sem DDL, TRUNCATE, ownership ou acesso a ledgers. Os UUID são gerados pela aplicação;
não há sequências security a conceder. O bootstrap permanece fora da aplicação.

Provisionar futuramente somente neste cluster identificado, sob autorização
separada: gerar credenciais exclusivas fora do Git, com permissões restritas;
transmiti-las por canal protegido e parâmetros, nunca argumentos CLI, histórico
ou logs. Rever owners, grants efetivos, PUBLIC e memberships antes de executar.
Não foi criada nenhuma role ou password nesta etapa.

## Pendências para P2C-2

Rever e implementar os adaptadores operacionais e o contrato de ativação;
provisionar migrator e seus privilégios temporários; validar catálogo real,
concorrência/lock, rollback PostgreSQL, commit e nova ligação. A prova offline
não demonstra isolamento de rede, ACL efetivas ou durabilidade real. Proteger
também o código/ficheiros contra alterações concorrentes entre validação e uso.
Dois ledgers na mesma base exigem coordenação; nenhuma autogeração aplicacional,
f067, downgrade ou autenticação real é autorizada por esta preparação.
