# M1.3D-PREP1 — Preparação offline do backend HTTPS

Base main, HEAD 647179c928888adfeef0f69f582fd13c5fc17350. Seis ficheiros
novos; nenhuma alteração de ficheiros existentes ou aplicação operacional.
Não foram consultadas bases, executadas migrações, criadas contas ou ativados
serviços. AUTH-03 e M1.2B não são modificados ou ativados por esta preparação.

## Configuração explícita, sem novo entrypoint operacional

`app.dedicated.create_dedicated_app(values)` reutiliza `create_app` sem alterar
`wsgi.py`, Dockerfile, dependências, configurações development/testing ou Compose.
Não há descoberta automática de SECURITY_* nem seleção automática de ambiente.
A factory existente continua exatamente como estava. A nova factory não é
invocada pelo backend em execução e não instala servidor WSGI.

O dicionário Python confiável exige ENVIRONMENT=production, DATABASE_HOST,
DATABASE_PORT (inteiro 1..65535), DATABASE_NAME, DATABASE_USER e
DATABASE_PASSWORD_FILE absoluto. Não aceita chaves desconhecidas. Não há
fallback para variáveis de ambiente, db/livenet ou credencial bootstrap.
O perfil dedicado recusa expressamente a base original `livenet`.

FIX1 corrige REV1-01: DATABASE_HOST admite exatamente um hostname DNS ASCII
(labels de 1..63 caracteres alfanuméricos/hífen, sem hífen nas extremidades,
máximo 253 caracteres sem ponto terminal) ou IPv4/IPv6 válido. Hostnames são
normalizados para minúsculas; admite-se um único ponto terminal DNS, preservado
para resolução absoluta. IPs usam a representação canónica de ipaddress; IPv6
é fornecido sem brackets ao URL SQLAlchemy/driver. Não se fazem consultas DNS
durante a validação. Nomes simples de serviços Docker continuam suportados.

Recusam-se vírgulas/listas, elementos vazios, espaços, controlos, caracteres
não ASCII, underscores, URLs/connection strings, parâmetros embutidos, sockets,
IPv6 com scope/brackets, IPs inválidos ou abreviados/numéricos/hexadecimais/octal
ambíguos, endereços não especificados e multicast. Não há tentativa de converter
IP inválido num nome DNS. Hostname/IP não é atestação do servidor: resolução DNS
normal continua sujeita à infraestrutura e exige validação operacional futura.

DATABASE_NAME e DATABASE_USER também recusam controlos e `=`, além das restrições
anteriores; não podem transportar connection strings. A porta continua a ser um
inteiro explícito. O URL não tem query/opções de override. PGHOSTADDR, PGSERVICE,
PGSERVICEFILE e PGOPTIONS no ambiente fazem a factory falhar antes de ler segredos
ou criar engine, pois poderiam redirecionar o transporte ou alterar a sessão
libpq. A guarda é repetida antes de cada sessão lazy. Os restantes parâmetros
de destino/credenciais são passados explicitamente.
Os testes com create_connect_args do dialeto PostgreSQL verificam host, port,
dbname, user e password finais, sem abrir ligação e sem apresentar passwords.

SECURITY_ENABLED e PROXY_ENABLED são booleanos, ambos False por omissão.
Ativar segurança no futuro exige PROXY_ENABLED=True, PROXY_PEERS explícitos
e SECURITY_CSRF_KEY_FILE absoluto. A origem admitida neste incremento é apenas
https://livenet-v2.home.arpa:8443. A política M1.2A valida a chave (mínimo 32
caracteres) e os parâmetros existentes; não são aceites parâmetros para
enfraquecer cookies, DEBUG, CSRF ou limites de sessão.

Os ficheiros de segredos são lidos apenas quando alguém invoca explicitamente
a nova factory: ficheiro regular do UID do processo, sem leitura/escrita/execução
de grupo/outros, sem symlink final, até 16 KiB, conteúdo não vazio. O transporte
futuro deve fornecer montagens restritas com UID compatível; este incremento não
cria credenciais nem montagens. Não incluir dicionários, app.config ou URLs
completos em logs. Erros de configuração são genéricos, sem valores sensíveis.

Engine e sessões são construídos de forma lazy, partilhados por auth e inventory,
com URL SQLAlchemy explícita, echo=False e hide_parameters=True. Construir a app
não abre ligação nem engine. Uma operação autenticada futura pode abrir a base
e escrever conforme M1.2A: isto continua dependente de autorização e privilégios.
Não existem criação de schema, revisão ou primeira conta no arranque.

## Fronteira Caddy -> Flask

`TrustedProxy` está desativado por omissão. Nesse modo rejeita Forwarded e
X-Forwarded-* em vez de os interpretar. Quando explicitamente ativado:

- Exige REMOTE_ADDR do socket igual a um IP exato da lista de peers; não aceita
  CIDRs, wildcard, contagem de hops como única prova ou bootstrap implícito.
- Exige Host e X-Forwarded-Host exatamente livenet-v2.home.arpa:8443,
  X-Forwarded-Proto=https e X-Forwarded-For com um único IP válido.
- X-Forwarded-Port, se presente, tem de ser 8443. Rejeita Forwarded,
  X-Forwarded-Prefix, campos desconhecidos e listas de endereços/protocolos.
- Só depois reconstrói scheme=https, host/porta externos e remote_addr do cliente
  para o throttle; remove os headers interpretados antes de entregar ao Flask.
- O CSRF continua a verificar Origin/Referer pela política existente. Cookies
  __Host-* mantêm Secure, HttpOnly, Lax, Path=/ e ausência de Domain. Sem CORS.

Este contrato NÃO demonstra identidade criptográfica do proxy. Exige futura
rede privada API, backend sem portas públicas, controlo de peers e Caddy como
único ingress. O proxy terá de substituir headers de clientes, não preservar
listas recebidas. O comportamento real de Caddy e o endereço do peer precisam
de validação autorizada; não basta copiar um IP Docker observado ou confiar
num IP que outro contentor possa obter. Se existir outro proxy antes do Caddy,
este contrato de um único ingress tem de ser revisto. Não foram alteradas redes
ou Caddy; o mecanismo permanece fora do entrypoint operacional.

## Liveness e readiness

`/api/v1/health` preserva o contrato anterior. A nova factory acrescenta
GET `/api/v1/ready`: 503 `{"status":"unavailable"}` por omissão, no-store,
sem detalhes internos. Autenticação desativada ou ausência de checker nunca
produzem readiness positiva. Não substitui autenticação nem permite ativação.

Foi preparado apenas um contrato de dependência Python confiável, não uma
implementação de consulta PostgreSQL. O futuro checker tem de usar ligação nova,
transação READ ONLY, limites de timeout e exclusivamente leituras de catálogo/
privilégios/ledgers. Não pode chamar authenticate(), efetuar FOR UPDATE,
advisory locks, probes DML/DDL, nextval, migrações ou reparações.

A observação tipada exige destino completo igual ao configurado (host, porta,
base, role), conectividade, read-only, schemas inventory/audit/security, revisão
aplicacional exatamente f066a01a7230, revisão security b12b01a7230 e evidência
integral de privilégios. Prazo máximo 5 segundos monotónicos; observação futura,
expirada, incompleta ou exceção dão 503. O destino tem tipos estritos e a prova
de privilégios repete o binding ao mesmo destino/role; contradições são recusadas.

FIX1 corrige REV1-02 substituindo o conjunto de rótulos por PrivilegeEvidence,
com quatro estruturas imutáveis de campos obrigatórios. Não são novos privilégios
PostgreSQL nem instruções GRANT: são resultados tipados de verificações futuras.

| Estrutura | Campos e significado exigido |
| --- | --- |
| RequiredPrivileges — todos exatamente True | users_select, grants_select, sessions_select: SELECT efetivo nas colunas carregadas dos modelos security correspondentes; sessions_insert: INSERT nas colunas emitidas; sessions_update_activity/revocation: UPDATE nas colunas last_activity_at/revoked_at; throttles_select/insert/update: direitos da operação UPSERT descrita na matriz; audit_insert: INSERT das colunas emitidas em audit.events; inventory_select: SELECT das colunas de inventory.resources; users_row_lock/sessions_row_lock: SELECT e UPDATE necessários para os FOR UPDATE existentes |
| AdministrativePrivileges — todos exatamente False | superuser, createdb, createrole, replication, bypassrls: atributos administrativos; role_membership: qualquer membership direta/indireta, incluindo caminhos SET ROLE, recusada neste perfil mínimo sem roles herdadas; privileged_routine_execute: acesso a rotina não aprovada que delegue administração/DDL; user_credential_update: UPDATE em login/password_hash/status de security.local_users; role_grants_write: INSERT/UPDATE/DELETE/TRUNCATE em security.global_role_grants; audit_mutation: UPDATE/DELETE/TRUNCATE em audit.events |
| OwnershipPrivileges — todos exatamente False | database: ownership da base alvo; schemas: ownership de schema não sistémico na base; relations: ownership de relações não sistémicas, incluindo tabelas, views e sequences; routines: ownership de rotinas não sistémicas. Considerar todos os caminhos de autoridade/membership, não só grants diretos |
| DDLPrivileges — todos exatamente False | database_create, database_temporary: CREATE/TEMPORARY na base; public_create, security_create, inventory_create, audit_create: CREATE nos schemas indicados; other_schema_create: CREATE em qualquer outro schema não sistémico da base |

O consumidor exige as classes exatas, todos os campos, e booleanos por identidade:
não aceita 0/1, strings, None/UNKNOWN, dicionários parciais, conjuntos vazios ou
rótulos. Nenhum campo negativo é omitido por default e uma capacidade positiva
não anula uma proibição: superuser/ownership/DDL presentes vetam o HTTP 200 mesmo
quando todas as leituras funcionam. PrivilegeEvidence ausente produz 503.

O adaptador futuro terá de confirmar current_database/current_user/session_user
e destino físico, observar atributos de role, memberships transitivas, catálogo
de owners e privilégios efetivos incluindo PUBLIC e colunas, e rever rotinas
privilegiadas acessíveis. Não basta SELECT bem-sucedido, ausência de grants diretos
ou teste dos nomes de schema. Campos de scope agregado só podem ser False após
examinar o âmbito completo; leitura negada, objeto desconhecido ou resultado
inconclusivo é UNKNOWN e não pode ser traduzido para False. O catálogo e os
direitos exatos por coluna precisam de revisão P2B-D05 e validação PostgreSQL.
O adaptador não pode alterar roles/ACL ou executar probes modificadoras para
obter estes resultados; se não conseguir demonstrá-los, readiness fica 503.

Os testes injetam observações SINTÉTICAS e não comprovam schema, ACL, atomicidade
ou readiness operacional. Nenhum checker real é fornecido ou instalado aqui.
Um checker Python confiável é código privilegiado: a interface não constitui
sandbox contra implementação hostil que escreva ou fabrique evidências.
Antes da instalação futura, rever e testar o adaptador read-only e a origem de
cada prova; nunca configurar readiness a partir de um booleano/env do operador.
Não se permite f067 por wildcard/head; qualquer revisão adicional requer rever
explicitamente este contrato. O perfil atual prepara login e consulta, não
atesta prontidão para criação de recursos.

## Matriz de operações e privilégios identificados

S=SELECT; I=INSERT; U=UPDATE. Todas as tabelas têm UUID gerado no Python ou chave
hash explícita; não há sequences necessárias nos caminhos abaixo. Necessários
CONNECT na base e USAGE nos schemas efetivamente usados, sem CREATE/ownership.
Os SELECT ORM carregam as colunas completas dos modelos, incluindo password_hash
em local_users e as colunas de sessão; não confundir com leitura apenas de id.

| Operação/código | Tabelas e direitos identificados | Locks/transação | Dependência e risco |
| --- | --- | --- | --- |
| Login: orçamento `_budget` | security.login_throttles: S(bucket_hash, window_started_at, attempts), I nas três colunas, U(window_started_at, attempts); audit.events: I se limitado | UPSERT ON CONFLICT; locks implícitos; transação própria confirmada antes de autenticar | b12b01a7230 + f066; concorrência e RETURNING por validar em PostgreSQL |
| Login: consulta/verificação password | security.local_users: S em todas as colunas; U em pelo menos uma coluna para FOR UPDATE | Lock de linha; transação login; scrypt executa localmente | b12b01a7230; escolher direito U é decisão P2B-D05, não concedido aqui |
| Login: rotação e nova sessão | security.login_sessions: S, I de todas as colunas, U(revoked_at); security.global_role_grants: S; audit.events: I | Sessão antiga FOR UPDATE; nova sessão + eventos na mesma transação | b12b01a7230 + f066; cookie só depois de commit confirmado |
| Recuperação `/me` e acesso inventory | security.login_sessions: S, U(last_activity_at, revoked_at); security.local_users e global_role_grants: S; audit.events: I se revogar | Sessão FOR UPDATE; atualização de atividade ou revogação transacional | Mesmo GET pode escrever; nunca usar esta operação para readiness |
| Logout/revogação | security.login_sessions: S, U(revoked_at); audit.events: I | FOR UPDATE e eventos na mesma transação | Falha/commit incerto exige reconciliação; não declarar logout por antecipação |
| CSRF | Nenhuma tabela | HMAC/assinatura e cookies; sem transação DB | Chave externa e HTTPS/origem; não autentica |
| RBAC `_roles` | security.global_role_grants: S em todas as colunas | Dentro da transação de autenticação | Só inventory_reader/editor globais; app não recebe I/U de grants |
| Auditoria `record_audit_event` | audit.events: I nas colunas emitidas pelo ORM | Flush/commit da operação chamadora; sem transação independente | f066; confirmar eventual RETURNING/defaults reais antes de fixar ACL por coluna |
| Lista e detalhe | inventory.resources: S em todas as colunas | SELECT e count; sem lock explícito inventory; autenticação é transação separada | Baseline até f066; contagem/filtros aplicam âmbito autorizado |
| **Escrita existente: POST recurso** | inventory.resources: I nas colunas do modelo, S para consultas posteriores; audit.events: I | Recurso + evento transacionais; sem FOR UPDATE explícito | Editor + CSRF; não coberto pela readiness de consulta nem pela UI atual |

Não há DELETE nos fluxos existentes, nem criação/alteração de users ou grants
por HTTP. Limpeza de sessões/buckets e primeira conta requerem procedimentos
separados. As FKs existentes não implicam automaticamente conceder REFERENCES
à app; esse privilégio é para criação de FKs, não utilização de relações já criadas.

PostgreSQL exige UPDATE em pelo menos uma coluna para SELECT FOR UPDATE, além
de SELECT. Isto é especialmente delicado em local_users: não se recomenda
UPDATE amplo, muito menos password_hash/status. Escolher coluna/estratégia de
lock sem ampliar indevidamente a escrita requer decisão e teste específicos.
Fonte: https://www.postgresql.org/docs/16/ddl-priv.html
UPSERT/RETURNING também exigem direitos das colunas referenciadas. Esta matriz
não é SQL de GRANT nem aprovação de ACL. Se for necessário mudar M1.2A para
resolver privilégios, pedir autorização própria, sem o fazer em PREP1.

## Validação e pendências

Testes PREP1: test_dedicated_backend.py e test_trusted_proxy.py. FIX1 acrescenta
test_readiness_contract.py, isolando a matriz adversarial e as evidências sintéticas.
Sem engine real,
configuração aplicada, credenciais operacionais, testes Docker ou PostgreSQL.
Regressões relevantes: security API/service/policy, inventory API/service/schemas,
metadata security e testes offline dos coordenadores. Resultado histórico PREP1: 617 pass,
0 fail, 0 skip (inclui 67 casos novos), em 9.52s. Execução com
PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=backend, pytest -q -p no:cacheprovider,
apenas os ficheiros offline explicitamente selecionados. Nenhum teste PostgreSQL
ou Docker foi executado. FIX1: 985 pass, 0 fail, 0 skip, em 10.97s; inclui os
617 casos anteriores e 368 casos novos. Foram selecionados os três ficheiros
PREP1/FIX1, security API/service/policy, inventory API/service/schemas,
test_security_migration e os sete ficheiros de testes M1.2B security_migration,
security_execution, privilege_review, inspection_handoff, operational_adapters,
operational_coordination e operational_audit. Resultados simulados não são
validação operacional nem autorização de ativação.

Permanecem pendentes: adaptador readiness real, servidor WSGI operacional,
montagens de segredos com UID apropriado, política de proxy e rede API,
M1.2B e prova de exclusividade/recuperação/fecho, decisão P2B-D05, migração
autorizada, primeira conta auditada, testes PostgreSQL e E2E. P2B-D01..D05
continuam aplicáveis. AUTH-BOOT não é dependência do login normal. Não alterar
operation_gate, execution_enabled, f067 ou manifesto para disponibilizar login.

Próximo incremento recomendado: confirmação independente offline da FIX1 e decisão
explícita sobre privilégios/lock de local_users e modelo do checker read-only.
Nenhuma alteração de Compose, imagem, rede, Caddy, serviços ou configuração
Windows é autorizada por este documento.
