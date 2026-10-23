# M1.2B-P2C-2B-PREP — Preparação operacional

Plano de 2026-10-23, main, HEAD a6e6e7c4e71f00366f6cd6aeb92ee5d02fd50297.
Este documento é a única alteração desta etapa. Não implementa o protocolo,
autoriza migrações ou comprova condições operacionais atuais do PostgreSQL.
Nenhuma ligação PostgreSQL, comando Docker ou comando Alembic foi executado.
As operações futuras descritas exigem os incrementos e autorizações abaixo.

## Decisões arquiteturais aprovadas — P2B-D01 a P2B-D05

As cinco decisões seguintes foram aprovadas como contrato arquitetural na
consolidação PREP-C; não foram implementadas nesta etapa:

- P2B-D01 — Manter coordenação até ao fecho administrativo.
- P2B-D02 — Adaptadores permanentes separados por identidade PostgreSQL.
- P2B-D03 — Controlo explícito de escritores externos além dos advisory locks.
- P2B-D04 — Recuperação administrativa independente antes da migração.
- P2B-D05 — Decisão posterior separada para DML da app e FOR UPDATE.

P2B-D03 e P2B-D04 são requisitos ainda por demonstrar. Nenhuma destas decisões
autoriza a execução da migração ou a ativação do executor. DML da app e FOR UPDATE
permanecem pendentes de decisão técnica específica. As aprovações operacionais e
os detalhes de implementação enumerados abaixo continuam necessários; IMP1 não
é iniciado por esta consolidação documental.

## A. Estado confirmado e fontes

Git main/HEAD esperado, staging vazio e alterações locais preexistentes
confirmados. Os 31 hashes protegidos coincidem com os anteriores, incluindo os
15 ficheiros AUTH-03, Compose M1.2B e modelos protegidos. operation_gate() mantém
o bloqueio de mutações; ExecutionAuthorization.execution_enabled=False.
O manifesto AUTH-03 não foi atualizado nem se certifica o seu estado preexistente.

Fontes locais revistas:

- scripts/postgres/m12b_security_migration.py: plano, guardas, leitores,
  privilégios, locks, evidência, validação física e tratamento de falhas.
- backend/security_migrations/contract.py, env.py,
  versions/b12b01a7230_create_security.py e backend/alembic-security.ini.
- Testes test_security_migration.py e test_m12b_security_migration.py,
  test_m12b_security_execution.py, test_m12b_inspection_handoff.py e
  test_m12b_privilege_review.py; duas guardas offline AUTH-03.
- Documentos m12b-p1-security-migrations.md, m12b-p2c1-security-executor.md,
  m12b-p2c2a-privilege-review.md, m12b-p2c2a-r2-inspection-handoff.md,
  m12b-p2c2a-r3-operational-preflight.md, m12b-p2c2a-prov1-report.md e
  m12b-p2c2a-prov2-validation.md.
- compose.m12b-test.yaml, backend/app/security/models.py e service.py.

| Categoria | Evidência e limite |
| --- | --- |
| Implementado | Cadeia security independente, raiz/head b12b01a7230, ledger public.alembic_security_version; env exige ligação externa/transação e bloqueia modo SQL offline; downgrade bloqueado; fluxo R2 desativado |
| Validado offline | 202 testes nesta etapa: guardas, grafo/metadata, duas sessões, locks simulados, evidência single-use/TTL, falhas e persistência simulada |
| Validado em PostgreSQL real anteriormente | PROV1: quatro roles e grants mínimos; PROV2: três LOGIN, leitores reais, ACL/ownership e fingerprint estável. Não foi repetido nesta etapa |
| Pendente de implementação | Adaptadores permanentes, atestação efetiva, exclusividade e monitorização, fecho administrativo, reconciliação por fase e verificação após ownership |
| Pendente de autorização | Testes de recuperação/locks reais, mudanças temporárias de acesso/CREATE, ativação revista, migração, ownership e eventual DML da app |

Referência operacional histórica PROV2: projeto livenetv2-m12b-test,
contentor livenetv2-m12b-test-db-1,
ID 540e8834355c281d5874603b82231b006486e3a74103bda04bead0ac77fbc5ec;
PostgreSQL 16.15, base livenet_m12b_test, system_identifier 7699783234487926818,
f066a01a7230 instalado; security/authorization/ledger security ausentes.
Rede interna livenetv2-m12b-test_m12b_backend, volume exclusivo
livenetv2-m12b-test_m12b_postgres_data, sem portas publicadas; imagem fixada
postgres:16-alpine@sha256:f4610795587492cd4fb887c2dc3de301b813278bb6f616992061141b5f15ac36.
Tudo terá de ser atestado novamente antes de qualquer janela autorizada.

## B. Lacunas concretas

1. ExecutionPorts define callbacks, mas não fornece implementação operacional,
   CLI, transporte de credenciais, atestação Docker ou prova de exclusividade.
   O harness efémero PROV2 não foi incorporado no produto.
2. validate_environment compara um dicionário fornecido pelo adaptador: a origem,
   endpoint físico, ID, digest, mounts e exclusividade dependem de adaptador confiável.
   system_identifier isolado é insuficiente, inclusive perante cópias físicas.
3. Não há coordenador de janela, controlo de sessões preexistentes, watcher de
   acessos, canal de recuperação testado ou fecho de privilégios temporários.
4. execute_security_migration fecha compliance no finally e liberta 6601 ao
   terminar a validação pós-commit. Ownership/revogação/grants estão fora desse
   ciclo: existe intervalo sem o lock antes do fecho administrativo.
5. validate_physical_security exige owner=current_user=migrator. Não serve como
   verificador final sob security_owner, sem acesso posterior do migrator.
6. As guardas não abrangem continuamente HBA, permissões da base, defaults de
   privilégios, todas as rotinas privilegiadas ou canais administrativos externos.
   O fingerprint não é prova de exclusividade nem controlo completo de conteúdo.
7. O digest do plano não inclui futuros adaptadores, dependências e distribuição.
   Recalcular hashes antes de importar não elimina TOCTOU de ficheiros mutáveis.
8. RO/timeouts são responsabilidade do adaptador; faltam limites de duração global,
   isolamento por fase, watchdog e prova de fecho físico em falhas de rede.
9. O erro rolled_back presume adaptador fiel ao contrato. Se um adaptador fizer
   commit prematuro, detetar transação encerrada não prova rollback: reconciliar.
10. Dois CREATE temporários continuam ausentes. DML/FOR UPDATE e auditoria da app
    estão por aprovar. Apenas instalar security não torna login/API utilizáveis.

P1/P2C-1 contêm descrições históricas de lock e grants substituídas por R2/PROV1:
não voltar a dar SELECT/USAGE inventory/audit ao migrator nem usar 6601 como lock
transacional numa segunda sessão enquanto o inspector o mantém exclusivo.

## C. Interfaces concretas propostas

Interfaces abaixo são contratos para implementação futura; não novos callbacks
executáveis neste documento. Não introduzem tokens, credenciais fixas, autorização
por ficheiro, variável de ativação ou autorização AUTH-BOOT/login.

| Interface futura | Correspondência / resultado |
| --- | --- |
| attest(target) -> EnvironmentAttestation | Substitui a simples confiança no dicionário por leituras locais verificadas do Docker, com ID, imagem/digest, volume/mounts, rede/membros, endpoint e ausência de portas |
| open_inspector(target) -> DedicatedConnection | ExecutionPorts.inspector_connect, identidade fixa inspector, RO e ligação física exclusiva |
| open_migrator(target, read_only=False) -> DedicatedConnection | ExecutionPorts.connect, identidade fixa migrator; escrita apenas na transação explicitamente autorizada |
| open_verifier(target) -> DedicatedConnection | connect(read_only=True), outro PID/driver, nunca reaproveitado do migrator fechado |
| run_exact_revision(config, connection, revision) -> None | ExecutionPorts.upgrade, configuração security fixa, transação externa, apenas b12b01a7230, sem gerir commit/rollback |
| coordinator.run(plan, adapters) -> PhaseResult | Dono do ciclo completo, sessão inspector e exclusividade até fecho; estados separados de instalação e prontidão |
| recovery.reconcile(observed, last_phase) -> RecoveryAssessment | Só leitura/classificação; nenhuma repetição ou correção automática. Ações administrativas exigem operador autorizado |

Parâmetros comuns propostos: destino explícito, connect_timeout=5s,
search_path literalmente public, NullPool/sem reconexão silenciosa, sem URL com
password, echo=False/hide_parameters=True e sem exceções SQL brutas em output.
Ler só a credencial própria já aprovada fora do Git (0700/0600, sem symlinks ou
fallback DATABASE_URL/PGSERVICE). Mapear db lógico ao endpoint atestado do único
projeto; nunca aceitar resolução db de outra rede nem host/socket alternativo.
Confirmar current_database/current_user/session_user, system_identifier, porta,
endereço normalizado e versão antes de qualquer comando além da identificação.
Startup options configuram cada sessão sem alterar defaults persistentes.

| Canal | Privilégios e SQL permitido | Transações e ciclo | Limites propostos / falhas |
| --- | --- | --- | --- |
| Inspector | CONNECT; USAGE public/inventory/audit; SELECT(id) nas 13 tabelas, SELECT(version_num) f066 e catálogos; identificação; exclusivamente duas funções de adquirir/libertar o lock de sessão previsto | Mesma ligação até ao fim; cada inspeção em REPEATABLE READ READ ONLY curta, rollback entre snapshots; nunca pooling ou reconnect | statement_timeout=5s, lock_timeout=1s; privilégio ausente, fingerprint divergente, lock perdido ou erro de leitura bloqueiam o ciclo |
| Migrator | Sem inventory/audit, admin ou memberships; CREATE base/public apenas na janela; leitura do ledger f066; DDL estritamente da revisão e próprio ledger; lock transacional 6602 | READ COMMITTED, uma transação externa; verificação física antes de commit explícito único; fechar fisicamente depois | statement_timeout=30s, lock_timeout=3s; timeout, SQLSTATE de privilégio/deadlock/cancelamento abortam; nunca retry |
| Verificador pós-commit | Migrator RO enquanto owner transitório: catálogos, dois ledgers e quatro tabelas security vazias | Nova ligação/PID/driver, REPEATABLE READ READ ONLY; rollback e fecho antes de ownership | 5s/1s; divergência, reconexão ou inacessibilidade => reconcile_required |
| Coordenação administrativa | Bootstrap explícito, preservado; RO para sessões/locks/ACL/HBA; escrita apenas em blocos allowlist de janela/fecho aprovados, nunca DDL de migração | Canal próprio, sem substituir inspector/migrator; transações administrativas separadas e confirmadas; mantém exclusão exterior durante todo o ciclo | 5s/1s em inspeção, 30s/3s nos blocos administrativos; sessão/ACL/HBA inesperada bloqueia, sem kill/revoke automático |
| Recuperação | Diagnóstico RO por identidade administrativa explícita; intervenção privilegiada apenas com autorização própria | Nova ligação e catálogo independente; não herdar resultado presumido do processo morto; acesso de infraestrutura separado se necessário | connect_timeout=5s; indisponibilidade ou resultado ambíguo mantém estado bloqueado; não declara sucesso por timeout |

Isolamento REPEATABLE READ é proposta não testada no harness PROV2; snapshots
novos entre fases evitam observação antiga. READ COMMITTED fornece snapshots por
instrução, não uma fotografia única de múltiplas consultas; isolamento não exclui
escritores externos. [Isolamento PostgreSQL 16](https://www.postgresql.org/docs/16/transaction-iso.html).

Adicionar prazo total proposto de 120s para o ciclo de instalação/fecho, com fases
orçamentadas e relógio monotónico; TTL da evidência continua exatamente 5s.
Não configurar idle_in_transaction_session_timeout tão curto que mate o migrator
enquanto o inspector revalida; qualquer valor deve exceder essa fase e ser testado.
Expiração durante commit significa resultado incerto, nunca rollback presumido.
Cancelamento futuro é mecanismo a implementar/testar e autorizar, não ação atual.
Uma thread cliente parada não garante que o servidor parou de trabalhar.

NullPool abre/fecha ligações físicas em vez de as manter para reutilização;
a implementação ainda deve verificar PID/driver e erros de fecho.
[SQLAlchemy NullPool](https://docs.sqlalchemy.org/en/20/core/pooling.html#sqlalchemy.pool.NullPool).
O padrão de ligação externa é compatível com Config.attributes['connection'];
o adapter não pode introduzir engine, autocommit ou transação própria no env.
[Alembic: ligação partilhada](https://alembic.sqlalchemy.org/en/latest/cookbook.html#sharing-a-connection-with-a-series-of-migration-commands-and-environments).

## D. Alternativas de exclusividade

Modelo de ameaça: operadores bootstrap e administradores do host são autoridades
confiáveis e coordenadas. Nenhuma alternativa dentro do próprio PostgreSQL contém
um superuser/administrador do host hostil; esse cenário exige isolamento externo
e recuperação de compromisso, não uma afirmação de exclusividade por software.

| Alternativa | Garantia / limite | Risco e reversibilidade | Privilégio / impacto | Evidência necessária |
| --- | --- | --- | --- | --- |
| A. Apenas advisory locks | Serializa participantes que seguem o protocolo; não trava DML/DDL alheio | Reversível por fim de sessão/transação; falha de cliente pode libertar lock antes de concluir trabalho noutra sessão | LOGIN normal; sem paragem de serviços | Duas sessões concorrentes, pg_locks e rejeição de segundo participante; insuficiente para autorizar migração |
| B. Bloqueio operacional de writers | Impede trabalhos conhecidos se controlados pelo operador; não cobre processo esquecido | Inventário incompleto e arranque automático; restaurar só serviços comprovadamente suspensos | Administração dos produtores/serviços externos; apenas projeto M1.2B | Lista de produtores, políticas de restart/tarefas, confirmação de suspensão e sessões drenadas |
| C. Restrição temporária de ligações | HBA por base/role/origem e CONNECT restringem novas entradas; sessões existentes continuam | Regra errada pode cortar recuperação; guardar e validar configuração anterior, restaurar por comparação | Bootstrap/host autorizado, possível reload; não alterar Compose nem bases protegidas | Regras ordenadas, tentativa negativa autorizada por canal excluído e positiva pelo canal de recuperação; ACL e sessões antes/depois |
| D. Janela exclusiva + validação contínua | Combina B/C, allowlist de sessões e locks cooperativos; reduz janelas TOCTOU sob administração confiável | Monitorização deteta depois do facto; não é barreira contra administrador hostil; fecho deve sobreviver à morte do coordenador | Canal administrativo e controlo de acesso, indisponibilidade apenas do teste | Prova dos canais permitidos, sessões/PIDs, watcher, teste de perda de controlo e fecho/reconciliação |
| E. Locks de tabelas protegidas | Uma variante SHARE na transação migrator pode bloquear DML comum nas tabelas enumeradas; não protege roles, HBA ou novos objetos | Exige poderes sobre inventory/audit, ordem e duração trazem deadlocks; liberta ao commit antes do ownership | Contraria contrato migrator atual; bloqueia writers, não aprovar como atalho | Novo desenho e testes de matriz de conflitos; rejeitada para incremento mínimo |
| F. Clone/VM descartável exclusiva | Bom destino para ensaiar recuperação/falhas sem tocar o original | Não demonstra estado do destino original; clone físico pode repetir system_identifier | Recursos separados e autorização de criação/restauro | Novo projeto/volume/rede, imagem e cadeia de backup atestados; nunca aceitar clone como destino pela igualdade do system_identifier |

Recomendação: D, composta por B+C+A, com exclusividade exterior à simples amostra
de pg_stat_activity. Não usar datallowconn=false (impediria verificação nova),
limites de ligações ou default_transaction_read_only como substitutos do controlo.
REVOKE CONNECT não drena sessões; novas entradas devem estar restringidas antes
da drenagem. Não terminar sessões desconhecidas automaticamente: bloquear e pedir
decisão. HBA usa a primeira regra correspondente; uma regra permissiva posterior
ou uma origem comum do host não distingue processos que detenham a mesma credencial.
[Regras HBA](https://www.postgresql.org/docs/16/auth-pg-hba-conf.html).

Para este ambiente, B significa manter sem produtores aplicacionais e identificar
clientes do host, tarefas e novos docker exec/run; não desligar os ambientes
livenetv2, f066c ou auth03-test. C deve ser estritamente limitado à base M1.2B:
negar app e canais fora da janela, manter inspector/migrator e recuperação
administrativa por origens/credenciais atestadas. Não adicionar trust.
O canal Docker continua privilégio administrativo; rede internal/sem portas não
o neutralizam. Se não se conseguir controlar todos esses canais, não migrar.

## E. Protocolo definitivo recomendado, ainda por implementar

Estados distintos: PRECHECKED -> EXCLUSIVE -> WINDOW_OPEN -> INSPECTED ->
MIGRATING -> COMMIT_UNKNOWN ou INSTALLED_VERIFIED -> OWNERSHIP_CLOSED ->
APP_DISABLED_VALIDATED. Só uma etapa DML separadamente aprovada pode levar a
APP_READY. Qualquer ambiguidade leva a RECONCILE_REQUIRED, sem retry automático.
Um registo de fase sem segredos ajuda diagnóstico, mas o catálogo é a fonte de
reconciliação; o registo não autoriza operações nem é recibo AUTH-BOOT.

1. Sem ativação atual. Futuramente, conferir aprovação específica, código imutável,
   dependências fixadas, plano/grafo e proveniência do único destino. Montar/usar
   artefacto somente leitura para reduzir TOCTOU de código. Revalidar hashes sem
   modificar manifesto AUTH-03; incluir adaptadores na integridade futura própria.
2. Provar recuperação em ensaio separado. Restringir novos canais, suspender
   writers conhecidos e drenar sessões existentes legitimamente. Allowlist por
   identidade/backend, sem confiar apenas em application_name ou IP. Um PID
   inesperado, writer ou privilégio novo bloqueia a janela.
3. Abrir inspector dedicado e adquirir uma única vez o session advisory lock
   (1295073858,6601). O coordenador exterior passa a ser dono dessa mesma sessão
   até terminar ownership/revogação/validação; não adquirir 6601 noutra sessão.
   Refatorar explicitamente o finally atual para esse ciclo, preservando fecho
   garantido e evitando aquisição reentrante duplicada.
4. Com exclusão ativa, administrador confirma novamente destino/ausências e concede
   CREATE base/public ao migrator na janela aprovada. Commit administrativo
   confirmado; registar que esses privilégios não revertem com rollback posterior.
5. Inspector valida privilégios, identidade, schemas/14 relações, f066, ausência
   de security/authorization/ledger e baseline vazia. Emite evidência interna
   ligada ao plano/operação/fingerprint; TTL monotónico de 5s após emissão.
6. Abrir migrator, iniciar transação externa, validar identidade/escrita, adquirir
   xact lock (1295073858,6602), verificar origem/privilégios e revalidar plano.
   Consumir evidência exata uma só vez com releitura e prazo antes/depois; sem
   renovação automática. Se expirar, abortar tentativa e reconciliar janela antes
   de qualquer nova operação aprovada.
7. Só então executar b12b01a7230 com configuração security e mesma ligação.
   Não usar head/heads/f067, não precriar schema/ledger, não chamar env aplicacional.
   Verificar transação ainda ativa, estrutura física, ledgers, tabelas vazias e
   fingerprint protegido. Uma transação inesperadamente terminada é reconciliação,
   mesmo que a flag local de commit ainda seja False.
8. Confirmar exclusão/saúde do inspector imediatamente antes do commit, fazer
   commit único e fechar migrator. A perda de inspector durante DDL/commit não
   pode ser contida apenas por heartbeat: a barreira operacional exterior deve
   continuar ativa. Se falhar, classificar como incerto e não lançar outro executor.
9. Abrir verificador físico novo, RO, enquanto ownership ainda é migrator.
   Confirmar ambos os ledgers e estrutura, fechar a ligação e terminar a transação
   antes do handoff. Revalidar protected fingerprint em snapshot novo.
10. Mantendo a mesma sessão/lock 6601 e exclusão exterior, executar fecho
    administrativo atómico da secção F. Não delegar a outro processo que precise
    adquirir novamente 6601. O xact lock 6602 pode ser usado no bloco curto de
    fecho, depois de libertado pelo commit migrator, sempre nessa ordem.
11. Nova verificação administrativa RO do estado final, pois o migrator perde
    acesso aos próprios objetos. Confirmar ausência de CREATE/memberships/owners
    indevidos, preservação f066/inventory/audit e owner NOLOGIN esperado.
    Só depois libertar 6601, fechar fisicamente todas as ligações e restaurar
    controlos temporários permitidos. App permanece sem DML se este não foi aprovado.
    A reposição usa o snapshot PROV1/PROV2 aprovado, nunca reintroduz CONNECT ou
    TEMPORARY de PUBLIC nem reverte o hardening já consolidado.

Session lock sobrevive a rollback; xact lock termina na transação. Mesma chave
em duas sessões pode bloquear o próprio fluxo; usar ordem global 6601 -> 6602,
sem waits ilimitados ou aquisição repetida. [Semântica dos locks](https://www.postgresql.org/docs/16/explicit-locking.html).
Conferir em pg_locks backend, database, classid, objid, objsubid=2, mode e granted;
não confiar numa flag local ou noutro PID. [pg_locks](https://www.postgresql.org/docs/16/view-pg-locks.html).

TTL limita o consumo inicial, não a duração total. Snapshots não veem DDL/DML
não confirmado noutra sessão; releituras não eliminam a janela antes do commit.
O protocolo continua síncrono/in-process, não uma transação distribuída ou prova
contra código hostil no mesmo processo. Manter D02-D05 sem acrescentar autoridade
externa, token fixo ou bypass. Perda de sessão/lock invalida a operação; não
reconstituir evidência noutra ligação para continuar a mesma tentativa.

## F. Ownership e privilégios

Ordem: CREATE temporário -> migração -> verificação física -> commit -> nova
verificação -> transferência/fecho -> validação final -> eventual DML separado.
Criar security e ledger inicialmente como migrator, sem membership no owner.
Quatro tabelas: local_users, login_sessions, global_role_grants, login_throttles.
Confirmar 4 PK, 2 FK, 3 UNIQUE, 9 CHECK e 1 índice explícito, além dos índices
de suporte. Ledger acrescenta a sua PK/índice. UUID/defaults Python não criam
sequências/identity/defaults de servidor; qualquer sequência inesperada bloqueia.

O fecho deve ser uma única transação administrativa com guarda da revisão
persistida b12b01a7230 e ownership migrator exato. Transferir somente schema
security, suas quatro tabelas e public.alembic_security_version ao
livenet_m12b_security_owner. Índices associados acompanham tabelas; verificar
todos os owners no catálogo. Não transferir base, public, inventory, audit ou
public.alembic_version; não usar REASSIGN OWNED, CASCADE ou concessões globais.

Conservar a variante R1: quando necessários à transferência, direitos CREATE
temporários do NOLOGIN owner existem apenas dentro da transação de handoff e são
revogados antes do commit. Os requisitos dependem dos poderes do administrador;
ensaiar o caminho exato PG16, sem introduzir membership no migrator como atalho.
[ALTER SCHEMA](https://www.postgresql.org/docs/16/sql-alterschema.html),
[ALTER TABLE](https://www.postgresql.org/docs/16/sql-altertable.html).

No mesmo fecho, revogar CREATE base/public de migrator/owner, remover quaisquer
concessões residuais de tabela e por coluna para migrator/app/PUBLIC e a leitura
version_num do migrator no ledger f066. Preservar os grants do inspector.
Esse bloco contém somente concessões previstas na allowlist da janela; um grant
inesperado bloqueia para investigação, sem limpeza automática de divergências.
Confirmar que migrator deixa de ser owner: REVOKE CREATE isolado não retira DDL
de owner. Nenhuma membership transitória é necessária nesta instalação inicial;
qualquer membership observada é divergência, não algo a limpar silenciosamente.

Os defaults de privilégios são por role criadora e afetam objetos futuros; a
transferência de ownership não aplica retroativamente defaults do novo owner.
Inspecionar pg_default_acl e ACL efetivas, incluindo colunas e rotinas; não usar
ALTER DEFAULT PRIVILEGES amplo para dar acesso à app.
[Default privileges](https://www.postgresql.org/docs/16/sql-alterdefaultprivileges.html).
Revogar EXECUTE explícito não garante retirar EXECUTE herdado de PUBLIC; não
declarar esse bloqueio sem medir o direito efetivo, nem alterar funções pg_catalog
como parte implícita do fecho. PROV2 já mostrou identificação disponível às três roles.

DML mínimo candidato, condicionado a revisão própria:

| Tabela | App futura | Limite |
| --- | --- | --- |
| local_users | SELECT; decisão pendente sobre lock | Sem INSERT/DELETE ou UPDATE de password_hash/status/login/id |
| global_role_grants | SELECT | Sem criar/alterar grants RBAC |
| login_sessions | SELECT, INSERT, UPDATE(last_activity_at, revoked_at) | Sem DELETE/TRUNCATE ou outros UPDATE |
| login_throttles | SELECT, INSERT, UPDATE(window_started_at, attempts) | Upsert/RETURNING exigem testar os direitos exatos do SQL ORM |
| audit.events | INSERT eventualmente necessário | Requer autorização própria de USAGE audit e colunas; não conceder neste plano |

M1.2A faz FOR UPDATE em local_users e login_sessions. As colunas UPDATE de sessão
já podem suportar o lock; local_users precisa de decisão. UPDATE(updated_at) é
tecnicamente suficiente, mas permite escrita real do timestamp. Preferência R2:
rever uma interface restrita de lock e a coordenação com desativação de utilizadores
num incremento próprio; alternativa menor só com aceitação explícita desse poder.
Não trocar simplesmente para FOR SHARE/KEY SHARE ou remover o lock.
[Privilégios SELECT com lock](https://www.postgresql.org/docs/16/sql-select.html).

Sem grants de auditoria e inventário e sem revisão FOR UPDATE, autenticação/REST
não está pronta. Não criar conta LiveNet, ativar autenticação ou conceder acesso
a inventory/audit automaticamente. Por omissão o fecho termina APP_DISABLED_VALIDATED.
Se DML vier a ser aprovado, aplicá-lo numa transação posterior com allowlist por
tabela/coluna, testar negativas e só então permitir o canal app. Falha nessa fase
não autoriza desfazer a migração por downgrade.

## G. Recuperação administrativa independente e testável

Bootstrap mantém os seus atributos/credencial nesta preparação. PROV1/PROV2
provam acesso normal anterior; não provam recuperação após perda ou compromisso.
O ensaio de recuperação é pré-requisito operacional, separado da migração.

Procedimento futuro proposto:

1. Aprovar um projeto/volume/rede de recuperação diferentes do destino e dos
   ambientes protegidos, imagem por digest e acesso host/console independente.
   Verificar backup consistente e restaurável com proteção de segredos; não copiar
   PGDATA de servidor ativo por simples cp. Definir RPO/RTO e critério de perda
   admissível da base descartável antes da janela.
2. Restaurar apenas num volume novo e isolado, sem montar o volume original.
   Simular indisponibilidade da credencial bootstrap somente nessa cópia.
   Confirmar que o endpoint/projeto de recuperação nunca passa a atestação M1.2B,
   mesmo se o clone físico conservar o system_identifier.
3. Via administração OS/Docker independente, comprovar servidor normal parado
   no clone e único processo com acesso exclusivo ao seu PGDATA. Usar recuperação
   PostgreSQL single-user, sem servidor concorrente, somente nesse clone.
   O modo concede poderes administrativos implícitos e serve para recuperação;
   não é ensaio fiel de locks/conexões normais.
   [PostgreSQL single-user](https://www.postgresql.org/docs/16/app-postgres.html#APP-POSTGRES-SINGLE-USER).
4. Restaurar acesso administrativo no clone por canal de segredo protegido,
   reiniciar normalmente, autenticar com credencial independente do segredo
   indisponível e validar roles, ACL, ledgers, constraints e consistência.
   Registar resultados sem dumps de credenciais. Nenhum comando/segredo é criado aqui.
5. Registar duração, dependências, falhas, checksum/proveniência do backup e prova
   do volume original intacto. Aplicar intervenção ao destino original somente
   com autorização própria, plano de indisponibilidade e snapshot/backup consistente.

Credenciais independentes: um eventual segundo administrador break-glass requer
decisão explícita, identidade/segredo próprios e custódia separada; owner NOLOGIN,
inspector, migrator e app não são administradores de recuperação. Não os elevar.
Esse segundo administrador não substitui backup/console e não foi autorizado/criado.

Bootstrap comprometido: tratar credencial e cluster como potencialmente hostis.
Isolar externamente por autoridade de infraestrutura independente; preservar
evidência e recuperar em ambiente limpo de backup confiável anterior ao compromisso,
com revisão/rotação de credenciais e imagem/código. HBA ou advisory locks no mesmo
cluster não contêm um superuser hostil. Se o host também não for confiável,
interromper e escalar para recuperação da infraestrutura, sem promessa de reparação local.

Perda de sessão durante ownership: bloco atómico deve deixar tudo anterior ou
posterior ao commit; confirmação incerta exige catálogo por nova ligação, nunca
repetir ALTER OWNER cegamente. Falha após commit da migração mas antes de fechar
CREATE exige manter barreira exterior, impedir novos trabalhos e fechar privilégios
por administrador após reconciliação. Se nenhum canal administrativo funcionar,
manter app inativa e recorrer ao procedimento de infraestrutura aprovado.

## H. Matriz de falhas e aprovação humana

Em todas as linhas, a aprovação de uma nova tentativa é distinta da operação
anterior. Nunca usar retry de CREATE/Alembic, downgrade, DROP ou limpeza cega.

| Fase | Estado esperado / deteção | Ação segura e recuperação | Evidência e aprovação necessária |
| --- | --- | --- | --- |
| Antes do início | f066, sem security; conferir identidade/fontes/recuperação/acessos | Não abrir janela se qualquer guarda divergir | Snapshot completo; operador resolve divergência antes de autorizar tentativa |
| Inspeção | RO e lock 6601 na sessão esperada; erro/timeout/fingerprint ou ACL divergente | Invalidar evidência, fechar recursos próprios; se CREATE já abriu, reconciliar/fechar administrativamente | Locks/PIDs, snapshot e resultado de fecho; sem correção automática |
| Handoff de evidência | Instância/contexto exatos, TTL 5s, lock retido | Recusar cópia/replay/expiração/perda de sessão; rollback migrator | Relógio/fase/erro sanitizado; nova tentativa só após janela reconciliada e aprovada |
| Durante Alembic | Uma transação externa, revisão exata | Falha/timeout: tentar rollback explícito, fechar e verificar estado novo; se transação terminou inesperadamente, reconciliação | Ledgers/objetos/owners e ausência de backend anterior; operador aprova recuperação |
| Antes do commit | Validação física e fingerprint intactos; barreira ativa | Não confirmar se falhar; rollback e revogação da janela por administrador | Prova de rollback e CREATE final fechado; se rollback/fecho incerto, bloquear |
| Commit incerto | Cliente não sabe se o servidor confirmou | Não repetir; verificar se backend ainda pode estar ativo e aguardar diagnóstico limitado; catálogo por nova ligação | Dois ledgers, inventário/constraints/owners e estado da transação original; intervenção humana obrigatória |
| Após commit | b12b01a7230 persistido, owner ainda migrator | Falha de nova ligação/estrutura: manter app inativa e exclusão; reconciliar, nunca downgrade | Snapshot independente e autorização para completar fecho ou recuperação |
| Durante ownership | Transação de fecho única; owner pode continuar migrator se rollback | Não prosseguir com grants; verificar todos os seis objetos nomeados e índices | Estado integral anterior/posterior; parcial ou incerto exige investigação humana |
| Durante revogação | CREATE/ACL residuais devem fechar no mesmo commit do ownership | Falha reverte bloco inteiro; manter barreira e reconciliar excesso efetivo antes de retomar | has_* por tabela/coluna, memberships/owners e defaults; operador aprova novo bloco |
| Durante grants da app | Só fase separada aprovada; schema já fechado | Rollback do bloco de grants, canal app bloqueado; migração permanece instalada | Allowlist efetiva/negações e auditoria; sem ativar serviço até aprovação |
| Perda de inspector/watchdog em qualquer fase | Lock pode desaparecer enquanto outro backend trabalha | Suspender novos passos; barreira exterior continua; ação sobre backend só se autorizada; assumir commit incerto se aplicável | Sessões/locks e catálogo novo; aprovação humana para cancelar, recuperar ou recomeçar |

Uma leitura imediata sem security não prova rollback se o backend original ainda
puder confirmar; uma leitura com ledger não prova ownership/grants fechados.
O mecanismo de reconciliação deve classificar estado completo, nunca só uma linha.

## I. Testes offline executados e testes ainda necessários

Nesta preparação: 202 pass, 0 fail, 0 skip, 1.69s. Comando seguro:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend .venv/bin/python -m pytest -q -p no:cacheprovider backend/tests/test_security_migration.py scripts/postgres/tests/test_m12b_security_migration.py scripts/postgres/tests/test_m12b_security_execution.py scripts/postgres/tests/test_m12b_privilege_review.py scripts/postgres/tests/test_m12b_inspection_handoff.py scripts/postgres/tests/test_auth03_alembic_executor.py::test_operations_block_before_external_access scripts/postgres/tests/test_auth03_alembic_executor.py::test_valid_future_plans_still_cannot_execute
```

Declarações/metadata e mocks, sem SQL real, DDL, Alembic upgrade/downgrade ou
Docker. Não foram necessários novos testes: não se implementou protocolo nesta
etapa. Os resultados não cobrem a arquitetura proposta por antecipação.

Para o incremento futuro, exigir testes offline novos de:

- Contratos de adaptadores: destino/credencial/função exatos, ausência de fallback,
  NullPool, fecho físico, erro sanitizado, timeout por fase e driver novo.
- Coordenador exterior mantém a mesma sessão 6601 até fecho administrativo;
  falhas em cada transição não libertam exclusão prematuramente nem duplicam locks.
- TTL nos limites 0/5s e além, relógio anterior, revalidação lenta, replay e nova
  autoridade; morte do inspector durante execução/commit impede continuação presumida.
- Commit prematuro do adapter, commit incerto de migração/fecho/grants, catálogo
  parcial e backend ainda ativo: nunca retry automático nem falso rolled_back.
- Comparador final pós-ownership separado do verificador migrator transitório;
  negações por tabela/coluna/default/rotina e exclusão de objetos adicionais.

Testes PostgreSQL futuros exigem autorização própria: locks concorrentes/reais,
HBA/acessos negativos, rollback DDL, commit incerto/falhas de rede, transferência
atómica, ACL finais, FOR UPDATE e ensaio de recuperação no clone. Mocks não
demonstram essas propriedades; não foram executados aqui.

## J. Critérios de aceitação para uma janela futura

1. HEAD/artefacto e dependências aprovados; hashes AUTH-03 preservados, executores
   originais intocados e nenhuma dependência operacional de AUTH-03/f067/env aplicacional.
2. Adaptadores revistos e contratos/testes offline aprovados, ainda desativados até
   autorização específica da execução. Não há flag ambiental ou credencial que os ative.
3. Identidade Docker/PostgreSQL completa atual, f066 e ausências esperadas; leituras
   R2 reproduzidas com ACL aprovadas; nenhum privilégio/objeto inesperado tolerado.
4. Recuperação independente ensaiada e canais/backup aprovados; bootstrap não
   reduzido sem alternativa verificada. Compromisso administrativo interrompe o plano.
5. Exclusão B+C+A comprovada para sessões antigas/novas e host/serviços externos;
   monitorização e barreira de falhas mantidas até à validação final.
6. Lock 6601 retido numa única sessão até ao fim; 6602 ordenado; handoff single-use
   intacto, TTL 5s e reconciliação em todas as falhas.
7. Migração exata, transação externa, estrutura esperada e nova ligação física
   comprovadas antes do ownership; ambos os ledgers preservados e authorization ausente.
8. Owner NOLOGIN final e CREATE/memberships/ACL residuais fechados atomicamente;
   app sem privilégios adicionais salvo revisão separada e negativas aprovadas.
9. Resultado final distingue INSTALLED_VERIFIED, OWNERSHIP_CLOSED e APP_READY;
   não declara laboratório utilizável só porque Alembic confirmou a revisão.

## K. Decisões que exigem aprovação

- Perfil D de exclusividade: canais exatos a restringir, mecanismo HBA/host,
  drenagem, observação e eventual cancelamento autorizado; sem alterar Compose
  ou ambientes protegidos por consequência.
- Ensaio independente de recuperação: projeto/volume/backup novos, direitos
  console e eventual administrador break-glass; não criado nesta etapa.
- Implementação offline dos adaptadores/coordenador e extensão explícita do
  ciclo de compliance até ownership/revogação; novos testes e verificador final.
- Limites/isolações propostos, transporte/TLS e distribuição imutável com
  atestação local confiável. Acesso ao socket Docker é poder de infraestrutura.
- Janela de CREATE e ativação revista separada, depois das evidências acima;
  aprovação documental deste plano não altera execution_enabled.
- FOR UPDATE/local_users e grants DML/auditoria/inventário da app; fora do
  incremento de instalação inicial se não houver decisão específica.

## L. Próxima etapa e ficheiros futuros

Recomendar primeiro implementação e revisão exclusivamente offline, mantendo
execution_enabled=False e sem CLI que possa migrar. Caminhos candidatos, ainda
não criados/alterados:

- scripts/postgres/m12b_security_adapters.py: atestação e ligações dedicadas.
- scripts/postgres/m12b_security_coordinator.py: janela/fecho/reconciliação.
- scripts/postgres/m12b_security_migration.py: ciclo de sessão emprestada e
  validação de fase, sujeito a revisão; nunca operation_gate AUTH-03.
- scripts/postgres/tests/test_m12b_operational_adapters.py e
  test_m12b_operational_coordination.py; atualização dos testes R2 necessária.
- Documentação dos ensaios de recuperação/exclusividade e autorizações por etapa.

Só depois autorizar ensaios operacionais isolados de recuperação/acessos/locks,
antes de qualquer janela real de migração. Não modificar modelos M1.2A,
security env/migração, Compose ou AUTH-03 como atalho. A revisão de FOR UPDATE,
se escolhida, terá âmbito próprio. Esta preparação termina sem implementar,
provisionar, conceder privilégios ou iniciar a migração.

Validação final local: git diff --check e whitespace deste ficheiro sem erros;
staging vazio, HEAD preservado, 31 hashes protegidos/15 AUTH-03 inalterados,
operation_gate() bloqueado e execution_enabled=False.

git status --short esperado após criação deste único relatório:

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
?? docs/specifications/f0/m12b-p2c2b-operational-preparation.md
?? scripts/postgres/auth03_alembic_executor.py
?? scripts/postgres/auth03_executor.Dockerfile
?? scripts/postgres/auth03_executor.Dockerfile.dockerignore
?? scripts/postgres/auth03_executor.example.json
?? scripts/postgres/auth03_executor_integrity.json
?? scripts/postgres/tests/test_auth03_alembic_executor.py
```
