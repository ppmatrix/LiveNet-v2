# DEV09B — procedimento único do primeiro ensaio application base→f066

08/11/2026 · **Desenho adotado; implementação/configuração preparadas offline.
Execução e alterações administrativas ainda não autorizadas.**
Alvo único: querytrial existente, `livenet_v2_dev`, SID `7705421224394444834`.
Direção B: administração confiável, janela coordenada sem intervenção concorrente;
não acrescenta resistência a administradores adversariais nem extensão R2/C4.

## Configuração escolhida e estado

| Serviço | Conta / UID/GID propostos | Acessos |
| --- | --- | --- |
| Executor | livenet-dev09b-executor / 62091 | Código/dependências RO; credencial migrator; CA; socket público autoridade e socket executor supervisor |
| Autoridade | livenet-dev09b-authority / 62092 | Somente credencial de serviço da autoridade; políticas/perfis aprovados RO; socket authority supervisor |
| Supervisor | livenet-dev09b-supervisor / 62093 | Credenciais existentes admin/probe do alvo; interlock privado; listeners segregados |

Leitura focada em progbox não encontrou os três nomes nem UIDs/GIDs em 08/11/2026.
Reconfirmar imediatamente antes da criação; não reutilizar identidades divergentes.
Sem login interativo, sudo, memberships Docker ou grupos suplementares.

Sockets: `/run/livenet-dev09b-authority/public.sock` (owner autoridade, caller executor),
`/run/livenet-dev09b-supervisor/executor.sock` (owner supervisor, caller executor),
`/run/livenet-dev09b-supervisor/authority.sock` (owner supervisor, caller autoridade).
Diretórios: owner rwx, callers somente travessia por ACL; sockets: owner/caller rw,
demais nenhum. `bind_listener` confere a ACL exata, aplica ACL Linux nativa sem
setfacl e recusa substituir paths existentes. `SO_PEERCRED` confere UID nos dois
extremos; frames/pedido/resposta/timeouts limitados, sem retry. Autoridade pública
expõe somente consume/check/record; executor não recebe administração PostgreSQL.

Interlock: `/var/lib/livenet-dev09b-supervisor/windows/first-f066`, owner supervisor,
0700; marcadores 0600. **Exige mount persistente com dispositivo distinto dos
filesystems da autoridade e do alvo**, identificado por st_dev e identidade de
mount aprovada, além de exclusão documental dos restauros da autoridade. Outro
diretório ou Docker volume no mesmo filesystem não satisfaz o requisito. As
referências de dispositivo da autoridade/alvo são handles RO preparados pelo
admin em `/run/livenet-dev09b-storage/{authority,target}-device`, ligados aos
filesystems reais, com proveniência registada; não dar acesso Docker/PGDATA ao
supervisor. A exclusão de restauro é um ato administrativo verificável; st_dev
sozinho não prova procedimentos de backup/restauro.

STARTED é exclusivo e fsync; reinício da mesma janela falha, mesmo após saída
limpa. BLOCKED não tem reset. Falha/detach/restauro incerto mantém admissões
bloqueadas; não recriar marcadores no filesystem subjacente. Restauro da própria
supervisão/interlock/VM requer bloqueio externo, reconciliação e nova decisão;
não há deteção mágica de rollback de todo esse storage. Âncora UTC independente
com boot_id/instante monotónico aprovados; startup consome o prazo de 900 segundos,
com margem proposta de 100 ppm. Não inferir confiança a partir de time.time().

TLS: CA explícita `/etc/livenet/dev09b/tls/ca.crt`, hostname/SAN
`dev09b-querytrial.internal`, libpq `sslmode=verify-full` e hostaddr aprovado.
GSS encryption desativada para não substituir o TLS exigido. **Pinning separado:**
extrair o certificado DER da própria sessão libpq por PQsslStruct/OpenSSL e
comparar SHA-256 com target.server_certificate_sha256, antes do SQL de setup do
SQLAlchemy. Providers nativos têm paths/hashes conferidos e dladdr confirma as
bibliotecas efetivamente usadas; não passar PGconn a outra libpq do sistema.
CA/hostname e fingerprint são verificações distintas, ambas obrigatórias.
Referências: [libpq 16](https://www.postgresql.org/docs/16/libpq-status.html),
[psycopg PGconn](https://www.psycopg.org/psycopg3/docs/api/pq.html),
[OpenSSL peer certificate](https://docs.openssl.org/3.0/man3/SSL_get_peer_certificate/).

Chave do servidor: ficheiro host privado, montado RO em
`/run/dev09b-tls/server.key`, 0600 e owner UID PostgreSQL efetivamente mapeado.
Chave da CA cifrada/offline, fora dos serviços. Cliente usa SCRAM por ficheiro
0600 próprio, sem chave TLS de cliente. Certificados ainda não emitidos; hostname,
CA, fingerprint e endpoint reais ainda não vinculados. Overlay TLS e HBA são
propostos, sem aplicação. Autoridade usa CA/endpoint/certificado próprios e SID
diferente do alvo; o antigo storage trial não é promovido a autoridade.

## Código preparado e entradas ainda ausentes

`scripts/postgres/dev09b_operational_cli.py` hospeda supervisor/autoridade e o
executor rollback-only, além de contain/verify e bootstrap administrativo separado.
Requer política root-owned sem escrita por terceiros e hash exato fornecido ao
processo, envelope Ed25519 já assinado, validators de layers existentes, fontes/
artefactos/perfil aprovados, configuração/dependency lock/supervisão vinculados ao
executor e UID correto. Não emite assinaturas ou aprovações. `check` é integridade,
não autorização. JSON de proposta e placeholders são recusados antes da ligação.

`InspectionPolicy` usa templates fonte aprovados: apenas binding e subject_session
são preenchidos em runtime. Supervisor verifica independentemente PID/start/xact,
virtualxid e xid numérico da sessão antes de attach único. Catálogo/contexto não
são aprendidos da base. Templates exigem cinco prerequisites, precommit, rollback
e final, com conversion_source presente no inventário assinado. O executor não
fornece um verificador fictício através da CLI.

Helper: v1 preservada, v2 acrescenta exclusivamente EXECUTE temporário ao migrator;
corpo/owner/membership/configuração mantidos. `trial_policy.active_helper` produz
expectativas/contexto v2 por fontes, exigindo novas referências no perfil assinado.
Coletores só chamam o helper após verificar a política exata e vinculam o PID.

Reconciliação: após rollback/fecho, supervisor usa outra sessão probe READ ONLY e
compara o catálogo completo com APP-ENTRY prefixo zero, ainda com grants temporários.
Confere ausência de sessões migrator/outros clientes e prepared transactions.
Controller autentica origem/independência via canal exato e só transita para
ROLLED_BACK_CONFIRMED após gravar prova com fsync fora da autoridade. Falha de
comparação/origem/journal mantém UNKNOWN. Não depende de a autoridade estar disponível. Uma aplicação que falhe antes de
PRECOMMIT também pode reconciliar o rollback, mas nunca recebe exit 0 como ensaio
concluído: PRECOMMIT MATCHED continua obrigatório.

Contenção: o comando de fallback usa só política administrativa root-controlled,
TLS e SID fixos, sem carregar envelope/perfil/issuer da admissão; sempre tenta
fechar a ligação local; supervisor continua a servir
rollback/contain/verify_final com admissões bloqueadas. NOLOGIN, terminação das
sessões do papel dedicado e revogações são transações administrativas separadas,
com timeouts e identidade conferida. Falha num passo não suprime os seguintes.
Não DROP/REASSIGN OWNED, não reparar objetos, não libertar consumo ou janela.
Depois da remoção, nova recolha probe compara integralmente com a transformação
fonte das ACL temporárias removidas e grava CLEANED_VERIFIED. Exit 0 do executor
exige rollback confirmado, poderes efetivamente retirados, catálogo final igual
e bloqueio durável; qualquer ausência/erro dá 78.

Preparados `dev09b_runtime_policy.proposed.json`, executor_configuration candidato,
unidade systemd template e overlay TLS. Dados privados reais, volume/restore,
certificados, origem da autoridade, contratos/perfis/assinaturas e aprovações das
dependências continuam por fixar. Os hashes de providers locais existentes estão
preenchidos como observação técnica, sem equivaler a aprovação de compatibilidade.

## Privilégios mínimos, sem ampliação silenciosa

O migrator recebe somente:

```sql
GRANT CONNECT ON DATABASE livenet_v2_dev TO dev09b_trial_migrator;
GRANT USAGE,CREATE ON SCHEMA public,inventory,audit TO dev09b_trial_migrator;
GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO dev09b_trial_migrator;
GRANT EXECUTE ON FUNCTION public.dev09b_own_preload_settings() TO dev09b_trial_migrator;
ALTER ROLE dev09b_trial_migrator LOGIN CONNECTION LIMIT 1;
```

`dev09b_application_grants_v2.proposed.sql` inclui guardas SID/admin/role, ausência
de memberships/CREATE/TEMP na base, SCRAM privado preexistente, ausência de settings
do papel e corpo/owner/configuração do helper. Proposta anterior intacta. Não é
necessário executar separadamente o SQL delta do helper: esse GRANT já está no v2.

O schema de parâmetros existente também exige identidades lógicas runtime,
application/security ledger owner e recovery. O v2 permite que database_owner seja
o admin já proprietário da base, sem duplicar papel ou ACL de owner e sem ALTER OWNER.
As restantes identidades mantêm-se distintas. Propõem-se quatro papéis
**inertes NOLOGIN/sem password/memberships/grants** no SQL profile_roles, item
material próprio da autorização conjunta. O compilador v2 não exige CONNECT para
recovery explicitamente NOLOGIN; não se cria poder de recuperação. Owners de
inventory/audit/security e probe/admin existentes não são recriados.

Preflight READ ONLY na sessão migrator verifica USAGE dos tipos built-in efetivamente
usados, EXECUTE de now/tstzrange e as duas opclasses default de btree_gist 1.7:
gist_uuid_ops e gist_text_ops (varchar usa compatibilidade com text). USAGE dos
tipos internos gbtreekey16/gbtreekey_var é registado, sem o promover automaticamente
a requisito de chamada interna GiST. Não existe GRANT ON OPCLASS; não acrescentar
EXECUTE a todas as funções de suporte. A análise de fontes não substitui o ensaio
PostgreSQL; recusa real de privilégios exige decisão sobre assinatura/tipo exato,
nunca retry com grants ampliados. Verificação completa dos membros/ACL/dependências
permanece nos checkpoints de catálogo existentes. Referência de resolução:
[indexcmds.c PG16.15](https://github.com/postgres/postgres/blob/REL_16_15/src/backend/commands/indexcmds.c).

Sem SELECT do ledger nesta tentativa. Sem CREATE EXTENSION, ownership da extensão,
pg_read_all_settings no migrator, CREATE/TEMP na base, poderes security ou runtime.
Revogações exatas, também em UNKNOWN quando seguro:

```sql
ALTER ROLE dev09b_trial_migrator NOLOGIN;
-- Fechar/terminar as sessões desse papel dedicado; não tocar noutros papéis.
REVOKE EXECUTE ON FUNCTION public.dev09b_own_preload_settings() FROM dev09b_trial_migrator;
REVOKE EXECUTE ON FUNCTION pg_catalog.pg_control_system() FROM dev09b_trial_migrator;
REVOKE ALL ON SCHEMA public,inventory,audit FROM dev09b_trial_migrator;
REVOKE CONNECT ON DATABASE livenet_v2_dev FROM dev09b_trial_migrator;
```

A CLI contain não espera reconciliação para executar estes passos. Ownership,
memberships, ACL efetiva, sessões, prepared xacts e ledger são verificados depois.
Residual bloqueia o fecho; nenhuma limpeza destrutiva automática.

## Sequência única proposta para autorização conjunta — NÃO EXECUTADA

1. **Infraestrutura e fonte de confiança.** Fornecer volume persistente separado,
   UUID/identidade de mount e exclusão de restauro aprovados; não formatar discos
   desconhecidos. Fornecer autoridade PostgreSQL segregada/TLS, SID/base/admin,
   storage e política de restauro reais. Fixar todos os hashes/perfis/contratos e
   referência do ato; envelope assinado por issuer confiável, nunca por uma fixture.
   Recursos/valores ausentes impedem avançar, não são aceites como defaults.
2. **Contas/ficheiros.** Reconfirmar colisões e criar as três contas abaixo. Montar
   o checkout congelado RO em `/opt/livenet-dev09b/source`; reutilizar dependências
   existentes sem instalar pacotes. Criar diretórios de runtime e ACLs exatas.
3. **TLS.** Emitir por canal administrativo a CA/certificado aprovados com SAN
   indicado, guardar a chave CA offline; provisionar server.key com owner PostgreSQL
   real/0600. Renderizar HBA com um único CIDR aprovado do host de controlo.
   Aplicar overlay somente ao descartável existente, conservando volume/imagem;
   reconfirmar SID antes/depois. Registar hashes CA e DER do leaf, não hash do PEM.
4. **Autoridade.** Em base segregada vazia aprovada, executar authority-bootstrap:
   cria owner/service NOLOGIN, schema proposto, ACL mínima e carrega somente o
   envelope assinado validado. Sem upsert/reset/issuance. Provisionar SCRAM privado
   e só depois habilitar LOGIN/limite 1 do serviço. Repetição/colisão recusa.
   ACL do serviço: CONNECT; USAGE schema; SELECT control/approvals;
   UPDATE(last_time) control; UPDATE(state,session_json) approvals;
   INSERT nonces/events; USAGE events_sequence_seq; EXECUTE pg_control_system().
   Sem novos grants para revoker/observer nem poder de emitir aprovações.
5. **Alvo.** Criar migrator NOLOGIN e quatro papéis inertes propostos; provisionar
   SCRAM em canal privado, ainda NOLOGIN. Aplicar só o grants_v2 abaixo. A instalação
   v1 do helper permanece; não reinstalar função/owner/pg_read_all_settings.
6. **Arranque e ensaio.** Fixar âncora independente fresca/boot_id e token de janela;
   instalar política root-owned com hash exato e unidade proposta. Arrancar
   supervisor, autoridade e finalmente executor, com Restart=no. O executor abre
   uma única transação, fixa xid/binding, faz attach independente e preflight de
   privilégios, consome uma única tentativa e executa ApplicationTransport até
   PRECOMMIT. **ROLLBACK/fecho obrigatório em finally; não há COMMIT aplicacional.**
7. **Reconciliação/contensão/fecho.** Prova independente e journal; em sucesso ou
   falha tentar contenção, depois verificação completa final. Se socket/processo
   supervisor se perder, executar contain por canal administrativo segregado.
   Conservar UNKNOWN se a prova de rollback faltar, mesmo com poderes retirados.
   Parar serviços após recolher evidências; preservar marcadores/bloqueio/consumo.
   Não repetir, reiniciar a janela ou remover residuais por iniciativa do runner.

Comandos preparados (executar só após autorização conjunta e bindings completos):

```bash
# Criação: somente se getent confirmar ausência de nomes, UIDs e GIDs.
for entry in executor:62091 authority:62092 supervisor:62093; do
  role=${entry%:*}; uid=${entry#*:}; account=livenet-dev09b-$role
  if getent passwd "$account" || getent passwd "$uid" || getent group "$account" || getent group "$uid"; then exit 78; fi
  groupadd --gid "$uid" "$account"
  useradd --uid "$uid" --gid "$uid" --groups '' --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin "$account"
done
# Bind RO da fonte congelada; sem cópia/instalação de dependências.
install -d -o root -g root -m 0755 /opt/livenet-dev09b/source
mount --bind /home/paulo/projects/livenet-v2 /opt/livenet-dev09b/source
mount -o remount,bind,ro /opt/livenet-dev09b/source
# Volume já identificado/autorizado; sem mkfs ou seleção automática de disco.
install -d -o root -g root -m 0755 /var/lib/livenet-dev09b-supervisor
mount --uuid "$DEV09B_INTERLOCK_UUID" /var/lib/livenet-dev09b-supervisor
install -d -o 62091 -g 62091 -m 0700 /run/livenet-dev09b-executor
install -d -o 62092 -g 62092 -m 0700 /run/livenet-dev09b-authority
install -d -o 62093 -g 62093 -m 0700 /run/livenet-dev09b-supervisor
install -d -o 62093 -g 62093 -m 0700 /var/lib/livenet-dev09b-supervisor/windows/first-f066
/opt/livenet-dev09b/source/.venv/bin/python - <<'ACL'
import os,sys
sys.path.insert(0,'/opt/livenet-dev09b/source')
sys.path.insert(0,'/opt/livenet-dev09b/source/backend')
from scripts.dedicated.dev09b.hosting import acl_bytes
os.setxattr('/run/livenet-dev09b-authority','system.posix_acl_access',acl_bytes(7,[62091],1))
os.setxattr('/run/livenet-dev09b-supervisor','system.posix_acl_access',acl_bytes(7,[62091,62092],1))
ACL
```

Os diretórios de runtime devem ser criados com owner/GID correspondente e 0700;
root aplica `hosting.acl_bytes(7,[62091],1)` ao diretório da autoridade e
`hosting.acl_bytes(7,[62091,62092],1)` ao do supervisor via os.setxattr. O host
aplica a ACL rw do caller a cada socket. Diretório de janela novo 0700 supervisor;
não substituir/reutilizar um diretório com STARTED. Proteger passwords 0600 pelo
respetivo serviço; autoridade_admin_password é somente root. Política/artifactos
públicos root-owned sem escrita de terceiros, com hashes efetivos no deployment.

```bash
# Emissão administrativa futura, fora dos serviços; NÃO executada na preparação.
# OFFLINE_CA_DIR é media privado/offline aprovado; umask protege os novos ficheiros.
umask 077
install -d -o root -g root -m 0755 /etc/livenet/dev09b/tls
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -aes-256-cbc -out "$DEV09B_OFFLINE_CA_DIR/ca.key"
openssl req -new -x509 -sha256 -days 30 -key "$DEV09B_OFFLINE_CA_DIR/ca.key" -subj '/CN=LiveNet DEV09B Trial CA' -addext 'basicConstraints=critical,CA:TRUE' -addext 'keyUsage=critical,keyCertSign,cRLSign' -out "$DEV09B_OFFLINE_CA_DIR/ca.crt"
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out "$DEV09B_TLS_DIR/server.key"
openssl req -new -key "$DEV09B_TLS_DIR/server.key" -subj '/CN=dev09b-querytrial.internal' -addext 'subjectAltName=DNS:dev09b-querytrial.internal' -addext 'basicConstraints=critical,CA:FALSE' -addext 'extendedKeyUsage=serverAuth' -out "$DEV09B_TLS_DIR/server.csr"
openssl x509 -req -sha256 -days 7 -set_serial 1 -copy_extensions copy -in "$DEV09B_TLS_DIR/server.csr" -CA "$DEV09B_OFFLINE_CA_DIR/ca.crt" -CAkey "$DEV09B_OFFLINE_CA_DIR/ca.key" -out "$DEV09B_TLS_DIR/server.crt"
# PG_UID/PG_GID são os IDs mapeados e verificados da imagem fixada, não os do host.
chown "$DEV09B_PG_UID:$DEV09B_PG_GID" "$DEV09B_TLS_DIR/server.key"
chmod 0600 "$DEV09B_TLS_DIR/server.key"
chmod 0644 "$DEV09B_TLS_DIR/server.crt"
install -o root -g root -m 0444 "$DEV09B_OFFLINE_CA_DIR/ca.crt" /etc/livenet/dev09b/tls/ca.crt
# A autoridade exige endpoint/certificado próprios já provisionados e vinculados.
# Certificado emitido: fingerprints para o binding (não emite chaves/certificados).
openssl x509 -in "$DEV09B_TLS_DIR/server.crt" -outform DER | sha256sum
sha256sum /etc/livenet/dev09b/tls/ca.crt
# CIDR já aprovado: somente o host de controlo (/32 ou /128), nunca uma rede ampla.
python3 - <<'HBA'
import ipaddress,os,pathlib
network=ipaddress.ip_network(os.environ['DEV09B_CONTROL_HOST_CIDR'],strict=True)
assert network.prefixlen==network.max_prefixlen
source=pathlib.Path('scripts/postgres/dev09b_trial.pg_hba.proposed.conf').read_text()
path=pathlib.Path(os.environ['DEV09B_TLS_DIR'])/'pg_hba.conf'
with path.open('x') as output:output.write(source.replace('@APPROVED_CONTROL_HOST_CIDR@',str(network)))
path.chmod(0o644)
HBA
# Aprovar/hashar estes bytes finais antes da alteração do serviço.
docker compose -f compose.dev09b-querytrial.yaml -f compose.dev09b-querytrial-tls.proposed.yaml up -d --no-build --pull never db

# CLI comum: policy é privada ao admin para escrita e publicada RO aos serviços.
PY=/opt/livenet-dev09b/source/.venv/bin/python
POLICY=/etc/livenet/dev09b/deployment.json
export PYTHONPATH=/opt/livenet-dev09b/source:/opt/livenet-dev09b/source/backend:/usr/lib/python3/dist-packages
install -o root -g root -m 0644 "$DEV09B_AUTHORIZED_POLICY_FILE" "$POLICY"
DEV09B_POLICY_SHA256=$(sha256sum "$POLICY" | cut -d ' ' -f 1)
"$PY" -m scripts.postgres.dev09b_operational_cli check --policy "$POLICY" --policy-sha256 "$DEV09B_POLICY_SHA256"
# Root; base/role administrativas da autoridade já provisionadas por infraestrutura.
"$PY" -m scripts.postgres.dev09b_operational_cli authority-bootstrap --policy "$POLICY" --policy-sha256 "$DEV09B_POLICY_SHA256"
# Provisionar SCRAM privadamente; psql \password não coloca password no argv.
PGOPTIONS='-c password_encryption=scram-sha-256' PGSERVICE=dev09b-authority-admin psql -X -v ON_ERROR_STOP=1 -c '\password dev09b_authority_service'
PGSERVICE=dev09b-authority-admin psql -X -v ON_ERROR_STOP=1 -c 'ALTER ROLE dev09b_authority_service LOGIN CONNECTION LIMIT 1'

PGSERVICE=dev09b-querytrial-admin psql -X -v ON_ERROR_STOP=1 --file scripts/postgres/dev09b_application_identity.proposed.sql
PGSERVICE=dev09b-querytrial-admin psql -X -v ON_ERROR_STOP=1 --file scripts/postgres/dev09b_trial_profile_roles.proposed.sql
PGOPTIONS='-c password_encryption=scram-sha-256' PGSERVICE=dev09b-querytrial-admin psql -X -v ON_ERROR_STOP=1 -c '\password dev09b_trial_migrator'
PGSERVICE=dev09b-querytrial-admin psql -X -v ON_ERROR_STOP=1 --file scripts/postgres/dev09b_application_grants_v2.proposed.sql

# Publicar aos serviços o hash final já conferido; não copiar JSON de proposta.
for role in executor authority supervisor; do
  printf 'DEV09B_POLICY_SHA256=%s\n' "$DEV09B_POLICY_SHA256" > "/etc/livenet/dev09b/$role.env"
  chmod 0600 "/etc/livenet/dev09b/$role.env"
done
install -o root -g root -m 0644 scripts/postgres/dev09b-runtime@.service.proposed /etc/systemd/system/dev09b-runtime@.service
systemctl daemon-reload
systemctl start dev09b-runtime@supervisor.service dev09b-runtime@authority.service
systemctl start --wait dev09b-runtime@executor.service
# Fallback administrativo se o executor/socket falhar; não reexecutar o executor.
runuser -u livenet-dev09b-supervisor -- env PYTHONPATH="$PYTHONPATH" "$PY" -m scripts.postgres.dev09b_operational_cli contain --policy "$POLICY" --policy-sha256 "$DEV09B_POLICY_SHA256"
runuser -u livenet-dev09b-supervisor -- env PYTHONPATH="$PYTHONPATH" "$PY" -m scripts.postgres.dev09b_operational_cli verify --policy "$POLICY" --policy-sha256 "$DEV09B_POLICY_SHA256"
```

Os COMMIT administrativos destes scripts persistem somente identidades/ACL/estado
da autoridade explicitamente autorizados; não são COMMIT da migração aplicacional.
Não executar o close histórico como gate de contenção em UNKNOWN: a nova CLI
contain foi criada precisamente para não depender do sucesso da reconciliação.

## Validação e limitações

Testes offline incluem evidências construídas, canal Unix/ACL real efémero e
resolução real dos providers nativos já instalados. Não emitem certificados nem
exercitam PostgreSQL/migrações. Pin do leaf de sessão real, mapas pós-f066,
privilégios internos efetivos no alvo e fronteira real de storage/restauro ainda
exigem o futuro ensaio autorizado. Igualdade de fixtures não demonstra operação.
Sem contas/serviços/mounts criados, certificados emitidos, PostgreSQL alterado,
grants reais, migrações, instalações, staging, commits ou pushes nesta preparação.
