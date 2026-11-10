# Instalação padrão MVP — DEV, login e Inventory persistente

## Decisão e limite de âmbito — 08/11/2026

Por instrução humana expressa, a instalação/migração da própria base LiveNet no
percurso padrão substitui os requisitos incompatíveis de DEV09B-PREPARED-1 por
um comando administrativo explícito. Não exige autoridade externa, envelopes,
consumo remoto, interlock independente ou contas de supervisão. Não declara
AUTH-03/F02/G2/G4/R2/C4 satisfeitos. Documentos, executores, manifestos e evidências
anteriores permanecem históricos/opcionais, sem bloquear este percurso e sem
serem apresentados como concluídos.

Produto preservado, sem implementar Discovery/gestão de credenciais nesta etapa:
Discovery apresenta candidatas; Inventory aceita máquinas sem credenciais;
operações que precisem de autenticação pedirão credenciais ou associação às já
guardadas, indicando capacidades indisponíveis enquanto faltarem. Credenciais
futuras têm armazenamento protegido/acesso controlado e nunca são retornadas ou
logadas. São distintas das credenciais administrativas de instalação. O MVP
atual aceita attributes vazio; não guardar credenciais nesses atributos.

## Comando e substituição explícita das guardas

`./scripts/livenet --help` utiliza o intérprete existente, sem instalação ou build.
`install` faz provisionamento, migração, grants runtime e conta/dado inicial;
os subcomandos permitem completar uma etapa após reconciliação, sem repetir as
anteriores. O núcleo não contém IPs, roles ou paths do laboratório: recebe JSON
por ambiente, sem passwords inline, e ficheiros privados fora da árvore fonte.

O Alembic padrão usa `backend/installation/alembic/env.py`, connection externa,
`StandardScope` tipado e atributo `livenet_standard_installation_v1`. As chamadas
de guardas nas migrações existentes são despachadas explicitamente para esse
contexto somente nessa configuração. Não se fabrica PreparedContext,
ProfileAttestation ou aprovação DEV09B. Contextos mistos são recusados. Os env.py
históricos continuam a exigir PreparedContext e os seus gates; nenhum foi aberto.
Os ficheiros de revisões e as suas IDs não foram alterados.

Preservados: destino por host/base/principal/SID; origem de ambas as revisões
explícita; ledgers public.alembic_version e public.alembic_security_version
separados; lock PostgreSQL de sessão comum aos comandos administrativos;
app até f066a01a7230, security até b12b01a7230, sem f067/stamp/downgrade; uma
transação exterior para as duas cadeias no modo all, incluindo os ledgers.
Schema owner, ligação/transação/lock e ausência de poderes administrativos no
migrator/runtime são conferidos. A base vazia ou catálogo de tabelas deve
corresponder à revisão declarada. Isto não é a prova integral de catálogo/R2/C4
do percurso reforçado, nem isolamento contra um administrador adversarial.

Após COMMIT, outra sessão confere revisões/tabelas enquanto o lock original ainda
está retido. Em falha, fechar/rollback são tentados e o diário privado normal
regista apenas IDs/estados/classes de erro, sem SQL, passwords ou hashes de login.
Resultado incerto bloqueia nova operação nesse estado local até `reconcile`.
Não há retry, reentrada, repair ou stamp automático. Reconciliação adquire o lock,
confere destino, ausência da sessão original e estado antes/depois; resolve
migrações, provisionamento, grants e seed sem repetir efeitos.

## Privilégios e runtime

Somente dois papéis PostgreSQL novos: migrator e runtime, nomes configuráveis,
LOGIN/SCRAM, sem SUPERUSER/CREATEDB/CREATEROLE/REPLICATION/BYPASSRLS/memberships.
O administrador existente prepara schemas/extension; não é o runtime.
O migrator fica owner dos três schemas e dos objetos criados, recebe CONNECT,
USAGE/CREATE em public para os ledgers e EXECUTE pg_control_system para o pin SID.
Não recebe CREATE/TEMP na base, helper DEV09B ou autoridade externa. Roles antigas
não são eliminadas. Não há quatro papéis inertes/owners auxiliares no padrão.

Provisionamento numa base LiveNet vazia: revoga CREATE/TEMP da base e CREATE de
public a PUBLIC, transfere ownership de inventory/audit/security para migrator,
prepara btree_gist em public se ausente e restringe pg_control_system a grantee
migrator além dos grants individuais preexistentes. Não altera a função helper
instalada nem restaura ACLs de todos os membros da extensão. Se houver recusa de
permissão GiST, rollback/reconciliação e decisão sobre o objeto exato; sem ampliar
grants automaticamente. CREATE EXTENSION só ocorre no comando administrativo.

Grants runtime exatos (`RUNTIME_GRANTS`, sem defaults blanket):

* USAGE em inventory/audit/security;
* SELECT/INSERT em inventory.resources;
* UPDATE(resource_type,display_name,description,administrative_state,updated_at,row_version)
  em inventory.resources para edição com controlo de versão. Incluído em
  `install`/`grant-runtime` e conferido por `grants_state`; no DEV existente foi
  aplicado após autorização humana explícita. Não concede UPDATE em id,
  attributes, created_at ou archived_at;
* INSERT e SELECT(id,occurred_at) em audit.events;
* SELECT em security.local_users/global_role_grants;
* UPDATE(updated_at) em security.local_users, estritamente para permitir o
  FOR UPDATE já usado pelo login; sem alterar password/status/roles. O requisito
  de UPDATE numa coluna está descrito em [PostgreSQL SELECT](https://www.postgresql.org/docs/18/sql-select.html);
* SELECT/INSERT em security.login_sessions/login_throttles;
* UPDATE(last_activity_at,revoked_at) em login_sessions;
* UPDATE(window_started_at,attempts) em login_throttles.

Sem ownership/DDL/memberships/CREATE/TEMP no runtime, DELETE, alteração de
passwords ou concessão de RBAC pelo runtime. A factory confere identidade e
ausência desses poderes e usa somente a credencial runtime; não lê os ficheiros
administrativo/migrator. Num deployment de serviço, disponibilizar ao processo
apenas runtime/CSRF/TLS, não montar as credenciais de instalação.

Factory padrão reutiliza autenticação, CSRF, cookies Secure/HttpOnly/Lax, RBAC,
audit e Inventory reais, com sessions explícitas comuns e sem fallback para a DB
legada. Origem HTTPS configurável; DEBUG permanece false também em DEV.
`serve` é servidor HTTPS apenas DEV, bind privado/loopback explícito, sem confiar
em forwarded headers. Serve o frontend/dist já existente, sem rebuild. Fora de
DEV, usar a factory WSGI com servidor apropriado; DB exige verify-full/CA explícita.

## Plano conjunto DEV — autorizado e executado em 08/11/2026

Alvo DEV escolhido: contentor existente `livenetv2-dev09b-querytrial-db-1`,
volume `livenetv2-dev09b-querytrial_data`, base `livenet_v2_dev`, SID
`7705421224394444834`, admin existente `dev09b_trial_admin`. Reutilizar a imagem e
volume; não criar/recriar/apagar recursos nem usar o authoritytrial. Progbox é
exclusivamente DEV; STAGING/PROD ficam em VMs Proxmox. Acesso só interno.

As escritas propostas: iniciar o contentor existente; criar ficheiros privados,
backup e certificado DEV; criar `livenet_migrator`/`livenet_runtime`, schemas/ACL
acima; aplicar as 13 revisões app e uma security; criar login `operator` com roles
inventory_reader/editor e uma VM mínima sem credenciais; servir HTTPS em loopback.
Não cria contas Linux, autoridade, interlock dedicado, serviços systemd ou CA externa.
O bootstrap precisa de administração PostgreSQL que possa criar roles/extensão e
proteger logs do DDL de credenciais. Só verificadores SCRAM são enviados em DDL;
passwords nunca são colocadas em argv/SQL/diagnóstico. Não executar `set -x`.

Comandos exatos de progbox para autorização conjunta, a partir deste checkout:

```bash
docker start livenetv2-dev09b-querytrial-db-1
DB_HOST=$(docker inspect --format '{{(index .NetworkSettings.Networks "livenetv2-dev09b-querytrial_backend").IPAddress}}' livenetv2-dev09b-querytrial-db-1)
STATE=/home/paulo/.local/state/livenet-v2-standard-dev
./scripts/livenet init-config --directory "$STATE" --host "$DB_HOST" \
  --database livenet_v2_dev --system-identifier 7705421224394444834 \
  --admin-role dev09b_trial_admin \
  --admin-password-file /home/paulo/.local/share/livenet-v2/dev09b-querytrial/admin_password \
  --migrator-role livenet_migrator --runtime-role livenet_runtime \
  --origin https://localhost:8443 --bind 127.0.0.1 --https-port 8443 \
  --frontend-dist /home/paulo/projects/livenet-v2/frontend/dist
CFG="$STATE/installation.json"
./scripts/livenet inspect --config "$CFG"
./scripts/livenet backup --config "$CFG" --output "$STATE/backups/before-standard.dump"
# Confirmar conclusão e leitura integral, sem restauro, antes das escritas DB:
pg_restore --list "$STATE/backups/before-standard.dump" >/dev/null
pg_restore --file=/dev/null "$STATE/backups/before-standard.dump"
./scripts/livenet install --config "$CFG" --login operator \
  --password-file "$STATE/initial_password" --resource-name 'Primeira VM DEV'
# Password inicial aleatória em ficheiro 0600, nunca impressa. Aceder localmente
# por canal privado; omitir --password-file permite escolher por prompt privado.

umask 077
openssl req -x509 -newkey rsa:3072 -nodes -sha256 -days 7 \
  -keyout "$STATE/server.key" -out "$STATE/server.crt" \
  -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1' \
  -addext 'basicConstraints=critical,CA:FALSE' -addext 'extendedKeyUsage=serverAuth'
chmod 0600 "$STATE/server.key"
./scripts/livenet serve --config "$CFG"
```

Browser local ou túnel interno para progbox: `https://localhost:8443/login`.
Confiar explicitamente no certificado DEV; não desativar validação TLS nem cookies
Secure. Para outra estação sem túnel, decidir hostname/SAN/bind privado e CA antes
da emissão; são configuração, não constantes no núcleo. O certificado self-signed
é a opção DEV proposta, não uma instalação automática de CA no sistema.

Etapas separadas, úteis após reconciliação de uma falha, sem repetir instalação:

```bash
./scripts/livenet reconcile --config "$CFG"
# Escolher somente a etapa ainda não confirmada:
./scripts/livenet provision --config "$CFG"
./scripts/livenet migrate --config "$CFG" --application-from base --security-from base
./scripts/livenet grant-runtime --config "$CFG"
./scripts/livenet initial-user --config "$CFG" --login operator --resource-name 'Primeira VM DEV'
```

Rollback normal preserva o estado anterior da transação. Perda de resposta ao
COMMIT exige reconcile, sem repetir migrações automaticamente. Se a sessão
original persistir, não há autorização para a ignorar; esperar timeout/fecho ou
intervir administrativamente sobre PID/start corretos. Estado parcial/inesperado
mantém bloqueio e exige diagnóstico. O dump custom é 0600 em storage normal,
feito por pg_dump existente com PGPASSFILE temporário 0600 e snapshot consistente,
sem passwords em argumentos/ambiente PGPASSWORD. Não contém backup dos roles
globais: os nomes/ACL administrativos deste procedimento devem acompanhar a
recuperação. Restauro destrutivo não é automático; preferir base de recuperação
separada, verificar e trocar configuração com autorização própria, preservando
o volume original e as evidências. Não usar DROP OWNED ou apagar volumes.

## Validação desta preparação

Testes exercitam as duas cadeias Alembic reais e compilação de DDL PostgreSQL
sobre catálogo construído, destino/revisões, concorrência entre clientes,
rollback, COMMIT incerto/reconciliação, roles/grants, hashing/seed, backup privado,
origem/CSRF/login/Inventory e recusa dos executores históricos. O teste HTTP usa
store transacional de teste entre instâncias; não é uma execução PostgreSQL real.
Nenhum grant, migração, conta operacional, certificado, serviço ou volume foi
criado/alterado nesta preparação; sem instalações, pull/build, commits ou pushes.

## Execução real autorizada — 08/11/2026

O plano acima foi posteriormente autorizado e executado apenas no querytrial DEV
indicado. HEAD `87883da`, trabalho local e volume preservados. SID e ambas as
revisões base conferidos antes das escritas. Backup custom de 111640 bytes,
modo 0600, listagem e descodificação integral por pg_restore concluídas antes do
provisionamento; SHA-256
`362573a1b1d83d984a2fe4e5449747fecab91449f2f9f4dd6bd169e2af4f2a50`.
Estado privado em `/home/paulo/.local/state/livenet-v2-standard-dev`.

Provisionamento, migrações, grants runtime e seed retornaram CONFIRMED, cada um
com conferência em nova ligação. Application `f066a01a7230` e security
`b12b01a7230`, ledgers separados pertencentes ao migrator. Catálogo real: 12
tabelas inventory, uma audit e quatro security; índices válidos/prontos e
constraints validadas. Privilégios efetivos conferidos: runtime sem poderes
administrativos/DDL/ownership/memberships/CREATE/TEMP; sem UPDATE de password,
INSERT de RBAC ou DELETE de resources. Migrator sem administração/CREATE/TEMP
na base e sem EXECUTE no helper histórico. Nenhum grant adicional foi necessário
para btree_gist. Não houve falha, COMMIT incerto, retry ou restauro; nenhum
marcador uncertain pendente.

`operator` criado com password inicial aleatória apenas em `initial_password`
0600; resource `Primeira VM DEV`, ID `965da7c0-60df-4d3d-b9b3-a64e15ff432d`, sem
credenciais. Validação HTTPS real: acesso anónimo recusado; login, cookie
Secure/HttpOnly, sessão, lista/detalhe e logout passaram. Reinício controlado da
aplicação conservou a sessão autenticada e o recurso; logout depois do reinício
foi persistido e voltou a recusar sessão/Inventory.

Aplicação em `https://localhost:8443/login`, único listener `127.0.0.1:8443`, sem
portas publicadas pelo contentor DB. Túnel interno:
`ssh -N -L 8443:127.0.0.1:8443 paulo@progbox`.
Certificado DEV self-signed `server.crt`, SAN localhost/127.0.0.1, válido até
15/11/2026 13:41:25 UTC; chave `server.key` 0600. TLS passou com confiança
explícita nesse certificado, recusou trust store normal e hostname incorreto.
Não foi instalada CA no browser/sistema. Passwords/CSRF/chave não aparecem no
log da aplicação; secrets/configuração/log privados fora do Git.

Processo DEV iniciado em background, PID atual em `application.pid`, log em
`application.log`, resultados HTTP públicos em `validation.json`. Não é serviço
supervisionado nem arranque automático após reboot; continua a usar o servidor
DEV e a conta Unix do operador. A segregação de roles DB está aplicada, mas não
há isolamento de ficheiros entre processos desse mesmo UID. Nenhum pacote,
pull/build, serviço de sistema, gate histórico, commit ou push efetuado.

Checkpoint humano: o utilizador confirmou login, Inventory, abertura do detalhe
e regresso ao login após logout. Esta confirmação é validação humana da UI;
não representa testes automáticos adicionais. Nenhum teste ou operação sobre
serviços/base foi repetido na preparação deste checkpoint.

Incremento UI Inventory concluído após autorização humana do grant adicional delimitado: UPDATE das seis colunas de resources acima aplicado em DEV e confirmado em ligação independente, mantendo runtime sem DDL/administração e as restantes colunas sem UPDATE. Criação e edição do recurso de teste `3423d894-95d7-449f-b58c-17ad6e077853` validadas por HTTPS/runtime, com persistência na lista/detalhe e versão 2. Versão antiga recusada com 409 sem sobrescrita; Primeira VM DEV preservada. Ações Adicionar recurso/Editar disponíveis para inventory_editor em https://localhost:8443/inventory; sem credenciais de equipamento, arquivo ou eliminação.

Validação humana posterior da edição pela UI: nome alterado para terminar em
“editado-PP”, apresentado no detalhe com `row_version` 3. Registo baseado na
confirmação do utilizador, sem testes adicionais ou operações sobre serviços/base.

## Descoberta — ativada e validada no DEV autorizado

Incremento autorizado em código sobre `6ebd167`: TCP connect IPv4, sem DNS,
raw sockets, comandos, banners, autenticação ou credenciais. Nome/tipo não são
inferidos. Uma observação positiva é apresentada como candidato, nunca como
recurso consolidado. Observações por execução são imutáveis; coincidências de IP
com identificadores existentes ou decisões anteriores são apenas pistas. Associação
é manual; criar um recurso distinto perante pistas exige confirmação explícita.
Decisões são serializadas por advisory lock e únicas por observação; repetição do
mesmo pedido retorna o recurso já decidido. Nada funde, reativa ou sobrescreve
recursos. Candidato aprovado cria inicialmente `active` (DAT-03B); editar depois
continua a usar Inventory. Não se implementam rejeição, correção de associação,
limpeza, TTL ou novos prazos. Não se presume identidade comum entre observações.

Worker daemon no processo da aplicação, um líder por base por advisory lock,
com alvos paralelos limitados. Configuração ausente desativa a descoberta; não há
fallback. Ao reiniciar, execuções running/cancelling passam a interrupted, sem
reexecução; evidência/decisões permanecem. Falha de persistência/COMMIT para o
worker e exige diagnóstico antes de reiniciar; não repete tráfego. A eleição
recusada deixa a instância sem worker até reinício, sem failover automático.
Fila e limites são globais na base. Cancelamento impede novos alvos quando
observado; sockets em curso terminam no timeout e a evidência é preservada.
A UI lista as últimas 50 execuções; o limite de apresentação não elimina dados.

### Plano único DEV — autorizado e executado

Alvo preservado: querytrial existente, `livenet_v2_dev`, SID
`7705421224394444834`. Aplicação f066→`d001a01a7230`, security mantém
`b12b01a7230`. Revisão nova em `backend/installation/versions`, lida apenas pelo
runner padrão; não altera revisões publicadas nem percorre f067/AUTH-03.
Schema novo `discovery`, owner `livenet_migrator`, sem ACL PUBLIC; três tabelas
jobs/observations/decisions, índices, FKs/uniqueness e triggers que impedem
UPDATE/DELETE da evidência/decisões. Nenhum requisito histórico é declarado satisfeito.

Registo dos comandos já executados sob autorização conjunta, após backup
concluído e legível. Não repetir preparação/migração/ensaio confirmados:

```bash
STATE=/home/paulo/.local/state/livenet-v2-standard-dev
CFG="$STATE/installation.json"
./scripts/livenet inspect --config "$CFG"
./scripts/livenet backup --config "$CFG" --output "$STATE/backups/before-discovery.dump"
pg_restore --list "$STATE/backups/before-discovery.dump" >/dev/null
pg_restore --file=/dev/null "$STATE/backups/before-discovery.dump"
./scripts/livenet prepare-discovery --config "$CFG"
./scripts/livenet migrate --config "$CFG" --chain application \
  --application-from f066a01a7230 --security-from b12b01a7230
./scripts/livenet grant-runtime --config "$CFG"
./scripts/livenet inspect --config "$CFG"
```

`prepare-discovery` usa administração apenas para CREATE SCHEMA AUTHORIZATION
migrator e REVOKE ALL FROM PUBLIC; diário/reconciliação e confirmação independente.
Migração usa migrator e a mesma transação/lock/pin SID/ledgers já existentes.
`grant-runtime` conserva os grants anteriores e acrescenta somente (nomes DEV):

```sql
GRANT USAGE ON SCHEMA discovery TO livenet_runtime;
GRANT SELECT,INSERT ON TABLE discovery.jobs,discovery.observations,discovery.decisions TO livenet_runtime;
GRANT UPDATE(status,processed,finished_at) ON TABLE discovery.jobs TO livenet_runtime;
GRANT SELECT(resource_id,identifier_type,normalized_value) ON TABLE inventory.resource_identifiers TO livenet_runtime;
```

Runtime sem DDL/administração/ownership, DELETE, UPDATE de evidência/decisões ou
INSERT/UPDATE de identificadores. Logs/JSON não expõem exceções SQL ou segredos.
Resultado incerto: parar escritas, `./scripts/livenet reconcile --config "$CFG"`,
conferir estado antes/depois; não repetir migração nem restaurar automaticamente.
Rollback transacional antes do COMMIT deve conservar f066 e o catálogo anterior;
o schema vazio preparado fica identificado separadamente. Após COMMIT confirmado,
rollback de produto exige parar a aplicação/desativar Discovery e decisão de
recuperação própria, sem apagar tabelas/evidência ou usar downgrade destrutivo.

### Primeiro ensaio real — autorizado e executado

Usar apenas o endpoint da DB querytrial identificado na configuração DEV:
`172.29.0.2/32`, TCP **5432**, até duas execuções sequenciais de um alvo
(máximo duas ligações TCP de deteção), sem payload PostgreSQL/autenticação. Reconfirmar configuração/endereço antes de executar;
qualquer mudança de endereço exige rever o alvo, sem ampliar o âmbito.
Possível efeito remoto: registo de conexão aberta/fechada no servidor PostgreSQL;
não se escrevem dados nem se enviam credenciais ao alvo pela deteção.

Criar, apenas depois de autorização, ficheiro privado 0600 fora do Git em
`$STATE/discovery.json`, com estes bytes JSON (sem secrets):

```json
{"networks":["172.29.0.2/32"],"ports":[5432],"max_targets":1,"concurrency":1,"target_timeout":1.0,"job_timeout":5.0,"max_jobs":1}
```

Reinício controlado apenas da aplicação, mantendo DB/volume/dados/HTTPS existentes,
com `LIVENET_DISCOVERY_CONFIG="$STATE/discovery.json" ./scripts/livenet serve --config "$CFG"`.
Não há reload automático do scope; parar a aplicação antes de trocar este ficheiro.
No browser via túnel, `https://localhost:8443/discovery`: iniciar esse /32, observar
progresso/evidência/instante, rever candidato. Escolha humana de nome
`TESTE Discovery DEV — querytrial`, tipo `container`, descrição de teste, active;
não inferidos pelo motor. Conferir recurso na lista/detalhe. Repetir o mesmo pedido
de decisão (incluindo concorrente) deve retornar o mesmo ID, sem outro recurso.
A segunda execução do mesmo ensaio conserva observação/decisão anterior e
apresenta a associação manual ao recurso já criado, sem criar outro recurso
automaticamente. Efeitos máximos previstos: dois jobs, duas observações, um
recurso de teste e duas decisões manuais com os respetivos eventos de auditoria.
Preservar Primeira VM DEV e o teste UI anterior. Sem scan de outras redes/portas.

Validação offline: testes de rede usam doubles; persistência/concorrência usam
SQLite com locks de teste e compilação PostgreSQL das migrações, não prova de locks
ou DDL em PostgreSQL real. Na preparação offline anterior não houve migração/grant, reinício ou descoberta
real; a execução autorizada posterior está registada abaixo. STAGING/PROD continuam em VMs Proxmox, acesso só interno.


### Resultado operacional confirmado — 08/11/2026

SID `7705421224394444834` e endpoint/volume existentes conferidos antes das
escritas. Backup `before-discovery.dump`, 0600, 220022 bytes, listagem e
leitura integral pg_restore concluídas antes de preparar o schema; SHA-256
`5bd37a687e0e58cdff623eeb249838e1aede5c4636ab45c572fd7abda4cad1ae`.
Preparação, migração e grants CONFIRMED por ligações independentes; application
`d001a01a7230`, security `b12b01a7230`. Catálogo/índices/triggers conferidos.
Runtime/worker usam `livenet_runtime`, sem DDL/administração, escrita de
identificadores ou UPDATE da evidência/decisões. Configuração privada 0600 em
`/home/paulo/.local/state/livenet-v2-standard-dev/discovery.json` com o /32,
porta e limites acima; apenas aplicação reiniciada, HTTPS em 127.0.0.1:8443.

Ensaio real: dois jobs sequenciais, cada um 0/1→1/1, queued→running→completed;
duas observações `tcp_connect`, IP 172.29.0.2, única porta 5432 com `connected`,
instante/proveniência persistidos. Duas ligações de deteção ao todo; nenhum
outro alvo/porta/payload/autenticação de equipamento. Primeiro job
`c6d309eb-8ced-4d77-bb33-d4f5eb9af5b7`, segundo
`df81d3c1-e8b3-4d63-b2bc-65faff1fd679`.

Criado apenas `TESTE Discovery DEV — querytrial`, UUID
`018078d1-2292-42aa-bdf9-3bd5164bc6d0`, tipo container escolhido no ensaio,
sem credenciais. Dois pedidos concorrentes para o mesmo candidato devolveram
o mesmo recurso: uma criação e uma decisão; segundo pedido idempotente.
Segunda observação preserva a primeira/decisão e apresenta possível
correspondência. **O mandato executivo proibiu associações:** não se efetuou a
associação sugerida no plano anterior; o segundo candidato ficou pendente.
Contagens reais finais: dois jobs, duas observações, um recurso novo e uma
única decisão (`create`), zero associações. Os dois recursos preexistentes e a
conta existente foram comparados com o baseline e preservados.

Sem falhas/COMMIT incerto, retries, restauro ou marcador de reconciliação
pendente. Segredos ausentes do log da aplicação. Evidências privadas em
`discovery-real-trial.json`/`discovery-trial-baseline.json`, fora do Git; não
incluir em staging. UI disponível em https://localhost:8443/discovery pelo túnel
interno, ainda limitada ao /32 e porta autorizados. Sem instalações, downloads,
alterações DEV09B, staging, commits ou pushes. Servidor permanece DEV, sem
supervisão/reboot automático; certificado/túnel existentes preservados.

Checkpoint posterior: o utilizador comunicou validação humana das páginas de
Descoberta. Separadamente, leitura READ ONLY confirmou a associação manual do
segundo candidato `691be909-852a-438b-a286-59459a470bcf` ao recurso de teste
`018078d1-2292-42aa-bdf9-3bd5164bc6d0` (decisão associate às 20:36:01.876934 UTC).
Continuam três recursos no total e duas decisões, sem duplicado; recursos
anteriores preservados. A associação não foi criada por esta verificação.
Checkbox/texto alinhados na revisão; seis testes UI Discovery aprovados e
bundle atualizado com typecheck/build local, sem reinício ou novos scans.

Atualização operacional DEV de 10/11/2026, autorizada sem varrimento: o scope
atual substitui o /32 de ensaio por `10.10.77.0/24` exclusivamente no ficheiro
privado discovery.json. Até 254 hosts, excluindo rede/broadcast, TCP
22/80/443/445/3389/8006, 8 ligações em paralelo, timeout de 1s por ligação e
300s por execução; uma execução ativa no máximo. A chave existente
`target_timeout` representa agora o timeout por ligação; cada porta tem o seu
orçamento e todas respeitam o deadline global. Sem retries, leitura de banners,
DNS ou autenticação de equipamento. Código genérico admite até seis portas,
sem conter as definições deste laboratório. Configuração anterior preservada
fora do Git. API confirmou valores efetivos; hashes de jobs/observações/decisões
e recursos iguais antes/depois do reinício, zero jobs novos e nenhuma pesquisa.
Apenas aplicação reiniciada, HTTPS loopback preservado. Início manual na UI.

Experiência de resultados atualizada em 10/11/2026: vista de execução abre em
Candidatos detetados, com contadores de todos os alvos e filtros Todos/Diagnósticos.
Polling serializado conserva tabela/foco/scroll, acrescenta novos resultados no
fim e faz uma leitura final ao atingir estado terminal, sem polling posterior.
Execuções já terminais são lidas uma vez; atualização manual permanece disponível.
As observações históricas não são reescritas. Nos 232 registos antigos de
445:error da execução /24, o errno original não foi guardado nem consta dos logs;
a causa não pode ser determinada retroativamente. Execuções futuras preservam
códigos seguros/errno (recusa, timeout, inacessibilidade, erro local), sem mensagens
brutas e sem transformar uma recusa isolada em falha do alvo inteiro.
Só aplicação reiniciada para carregar código; hashes de jobs/observações/decisões
e recursos antes/depois iguais, zero deteções novas. Configuração/âmbito mantidos.

Validação humana da apresentação em 10/11/2026: candidatos por defeito,
contadores e evidências visíveis. Não abrange polling durante execução nem
validação da causa das 232 falhas históricas. Testes automatizados anteriores
permanecem distintos desta confirmação humana; nenhum foi repetido no checkpoint.

Detalhe do recurso com Descoberta (10/11/2026): secção de histórico apenas das
observações explicitamente ligadas ao UUID por decisões create/associate; IP não
é tratado como identidade permanente ou disponibilidade atual. Inclui evidência
TCP, datas, tipo de decisão e ligação à execução original, com paginação; ausência
ou falha do histórico não remove o detalhe normal. Mesmo scope de leitura do
Inventory; nenhuma migração/grant adicional, pois os SELECTs já instalados bastam.
Leituras históricas não exigem habilitar o motor de deteção. Validação humana
comunicada do percurso ecEng: candidato 10.10.77.160→criação→detalhe, Contentor,
versão 1; não é declaração de validação humana da secção nova. Confirmada por GET
no DEV, incluindo histórico múltiplo/vazio, após reinício só da aplicação em
loopback. Dados integralmente preservados; zero deteções novas.

Validação visual posterior em ecEng: secção Descoberta confirmada pelo utilizador,
com “Ver execução” visível. A navegação por essa ligação não foi confirmada;
a validação humana fica limitada à apresentação visual, distinta dos testes/GETs
anteriormente reportados. Nenhum teste ou operação operacional repetido no checkpoint.
