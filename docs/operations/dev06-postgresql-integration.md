# DEV-06 — PostgreSQL TLS e fronteira de persistência aplicacional

2026-10-25. Resultado: implementação TLS opt-in e testes reais isolados passaram;
persistência aplicacional e readiness positiva continuam bloqueadas com evidência.
Não houve ativação operacional, acesso a PostgreSQL existente, migrações, alteração
de gates, regeneração AUTH-03, publicação de portas ou push.

## Resumo técnico

Foi acrescentado `dedicated_wsgi:create_tls_app`, com CA explícita, verify-full,
GSS encryption desativado e timeout de ligação. O percurso anterior mantém-se
separado. A factory continua sem SQL/DDL/DML no arranque; autenticação e inventário
partilham a fonte lazy de sessões. O overlay `compose.dedicated-tls.yaml` foi
renderizado nativamente e validado pelo preflight real, com guards exit-78 herdados.

O ensaio utilizou PostgreSQL 16 novo em tmpfs, três redes internas únicas, SCRAM,
PKI e credenciais sintéticas. Demonstrou TLS positivo e recusa de CA/hostname errados,
plaintext e falha de ligação; separação de cinco roles, SQL permitido/proibido,
persistência entre conexões e rollback atómico num schema estritamente sintético.
A ligação TLS do backend foi observada independentemente em pg_stat_ssl/pg_stat_activity,
comparando a origem com o IP atribuído ao contentor backend pelo Docker.

O percurso real foi HTTPS → Caddy → Gunicorn/Flask → PostgreSQL TLS → tentativa de
login com CSRF válido → 503 sanitizado. Não há schemas security/inventory/audit no
novo cluster. O primeiro acesso persistente do login, o budget em
security.login_throttles, não pode concluir. Os gates impedem a preparação aprovada
que falta; não são chamados pelo pedido HTTP nem pelo login em si. O manifesto
AUTH-03 não é uma verificação diretamente integrada na factory HTTP.

Não foram usados metadata.create_all, SQL equivalente às migrações ou outro atalho
para criar os schemas aplicacionais. A sentinela HTML só testa routing; não é React.

## Estado inicial e proveniência

- Branch `main`; HEAD `647179c928888adfeef0f69f582fd13c5fc17350`.
- 202 ficheiros versionados; dois modificados: backend/migrations/env.py e
  docs/specifications/f0/implementation-status.md; 65 não versionados.
- 267 ficheiros não ignorados copiados/inventariados por SHA256 antes de alterações,
  em `/tmp/livenet-dev06-baseline-xyc73o5o`, diretoria privada, manifesto baseline.json.
- 8 715 ficheiros ignorados inventariados por nome: sobretudo .venv/caches. Os
  candidatos relevantes são secrets/auth03_db_password.txt, secrets/auth03_executor.json
  e secrets/db_password.txt. Conteúdos não lidos, copiados, impressos ou utilizados.
- Os artefactos DEV-03B/04/05A/05B já existiam majoritariamente sem versionamento.
  As referências documentais e snapshots permitem comparação, não provam por si
  aprovação ou autoria. Os 13 .pyc antigos em app e restantes caches ficaram intactos.
- Índice inicial SHA256: 50d32095da16e2c0e985226625971e890c33d406cbb9b97743a7198905b9541e.

## Reconciliação e decisão necessária

| Tema | Evidência | Conclusão e decisão pendente |
|---|---|---|
| DAT-05A | docs/specifications/f0/data-model.md, texto localizado, Estado: Aprovada; commit 8b2e32e | Define uma base livenet e seis schemas; não define uma exceção explícita de nomes por ambiente. |
| Perfil dedicado | backend/app/dedicated.py e docs/operations/dev02-dedicated-backend.md | Recusa literal livenet adicionada no percurso dedicado para proteger o destino original. Código ainda não versionado; não há commit próprio que prove a decisão original. |
| Ambientes e testes | docs/architecture/environments.md; scripts AUTH-03/M1.2B e testes dedicados | Usam identidades/nome de base isolados, sem autorizar remover a proteção original ou mudar DAT-05A. |
| Reconciliação de nomes | Novo teste usa apenas dev06_synthetic | Mantida a recusa. Alternativas para revisão: formalizar nomes por ambiente e atualizar DAT-05A, ou conservar livenet no destino operacional com isolamento físico/identidade e novo contrato aprovado. Nenhuma foi presumida aprovada. |
| Alembic aplicacional | 14 revisões lineares; f066 seguido de f067; migração f066 no commit 9069aa3, f067 ainda não versionada | Não há duas heads estruturais; a divergência é de contrato/proveniência/revisão exigida. Não se usou head, stamp, upgrade ou downgrade. |
| Readiness | backend/app/readiness.py exige f066a01a7230 e b12b01a7230 | Não foi mudada para aceitar f067 nem foi ligada evidência sintética. |
| AUTH-03 | Executor exige f066/f067 conforme operação; operation_gate recusa todas as mutações antes de I/O | Falta revisão humana do manifesto e autorização por mecanismo aprovado. Não mudar apenas a revisão esperada. |
| Alembic security | backend/security_migrations/contract.py, env.py e b12b01a7230 | Cadeia independente e conexão externa/transação obrigatórias. Coordenador mantém ExecutionAuthorization.execution_enabled=False. |
| G4 | scripts/postgres/g4/contracts.py:execution_boundary | Sempre GATE_ABSENT para o destino correspondente; nenhuma flag ou alegação de aprovação o abre. Não foi alterado. |

O facto de uma revisão estar encadeada, versionada ou documentada não autoriza
executá-la através de um percurso que contorne os gates. Nenhuma migração se
qualificou como inequivocamente autorizada para esta tarefa. A autorização DEV-06
para criar roles/schemas sintéticos foi usada exclusivamente em dev06_probe.

Os textos originais D-01–D-51 e 16 capítulos não foram reconstruídos. Permanecem
abertas as lacunas documentais já registadas, incluindo as 28 G4/L02 declaradas.

## AUTH-03: proposta de reconciliação, sem aprovação

A fonte do conjunto esperado é verify_bundle em scripts/postgres/auth03_alembic_executor.py:
todos os .py em backend/app e backend/migrations, mais backend/alembic.ini,
backend/requirements.txt e o próprio executor. A fonte dos hashes esperados é
scripts/postgres/auth03_executor_integrity.json; os atuais vêm de SHA256 dos bytes.

Inicial: 31 entradas, 51 esperadas, 20 omissões, zero extras, quatro divergências.
Final: 31 entradas, 52 esperadas, 21 omissões, zero extras, quatro divergências.
A omissão adicional é backend/app/postgres_tls.py, introduzido nesta tarefa e
explicitamente não aprovado pelo manifesto. Os bytes do manifesto e do executor
permanecem idênticos à baseline. Não foi criado um manifesto alternativo.

A evidência completa, com hashes esperados/atuais e grafos inicial/final, está em
[dev06-contract-evidence.json](dev06-contract-evidence.json). Esse JSON é um relatório,
não é consumido pelo executor nem concede autorização.

Omissões iniciais:
- `backend/app/dedicated.py`
- `backend/app/inventory/access.py`
- `backend/app/inventory/routes.py`
- `backend/app/inventory/schemas.py`
- `backend/app/inventory/service.py`
- `backend/app/readiness.py`
- `backend/app/readiness_postgres/__init__.py`
- `backend/app/readiness_postgres/adapter.py`
- `backend/app/readiness_postgres/evaluate.py`
- `backend/app/readiness_postgres/policy.py`
- `backend/app/readiness_postgres/queries.py`
- `backend/app/security/__init__.py`
- `backend/app/security/access.py`
- `backend/app/security/csrf.py`
- `backend/app/security/errors.py`
- `backend/app/security/models.py`
- `backend/app/security/policy.py`
- `backend/app/security/routes.py`
- `backend/app/security/service.py`
- `backend/app/trusted_proxy.py`

Hashes divergentes, sem alteração DEV-06 desses quatro ficheiros:

| Ficheiro | Esperado (prefixo SHA256) | Atual (prefixo SHA256) |
|---|---|---|
| backend/app/__init__.py | 74c51facab8fd44e | 0b5d3abe00795621 |
| backend/app/config.py | 1801c76af1d3f7bd | 05e82252427e37e4 |
| backend/app/core/model_registry.py | 28419b14eabd1d04 | 6b9db8825e03e894 |
| backend/requirements.txt | 70820b980a6e044a | aba67440c5f8caf5 |

As omissões abrangem autenticação, sessões, auditoria, inventário, proxy e readiness.
Isto bloqueia a garantia de integridade do executor; não demonstra corrupção dos
dados nem ausência de autenticação HTTP. As falhas dos testes positivos AUTH-03
não foram ocultadas. Proposta: rever origem/diff e hashes de cada ficheiro, rever
scope e identidade do bundle, fixar uma baseline reproduzível e aprovar uma nova
referência apenas pelo processo humano competente; depois revalidar gates e testes.
Não existe comando de aceitação automática novo.

## Grafo Alembic observado

| Cadeia | Revisão | Anterior | Ficheiro |
|---|---|---|---|
| application | 38d641dcd780 | 4f625db33d6d | backend/migrations/versions/38d641dcd780_create_inventory_resource_relations.py |
| application | 44e7eb855b5a | ba06dd956da9 | backend/migrations/versions/44e7eb855b5a_create_inventory_group_rules.py |
| application | 4f625db33d6d | af62df027d9d | backend/migrations/versions/4f625db33d6d_create_inventory_resource_identifiers.py |
| application | 7c4e2a91b605 | 44e7eb855b5a | backend/migrations/versions/7c4e2a91b605_create_inventory_tags.py |
| application | 9e1b7c42a630 | 7c4e2a91b605 | backend/migrations/versions/9e1b7c42a630_create_inventory_resource_tags.py |
| application | af62df027d9d | None | backend/migrations/versions/af62df027d9d_create_inventory_resources_baseline.py |
| application | ba06dd956da9 | da34876e4210 | backend/migrations/versions/ba06dd956da9_create_inventory_group_memberships.py |
| application | c4a91e7b205d | 9e1b7c42a630 | backend/migrations/versions/c4a91e7b205d_create_inventory_policies.py |
| application | da34876e4210 | 38d641dcd780 | backend/migrations/versions/da34876e4210_create_inventory_groups.py |
| application | e65b01a7c230 | c4a91e7b205d | backend/migrations/versions/e65b01a7c230_create_inventory_policy_versions.py |
| application | f065c01a7230 | e65b01a7c230 | backend/migrations/versions/f065c01a7230_create_inventory_policy_assignments.py |
| application | f065d01a7230 | f065c01a7230 | backend/migrations/versions/f065d01a7230_create_inventory_effective_configs.py |
| application | f066a01a7230 | f065d01a7230 | backend/migrations/versions/f066a01a7230_create_audit_events_baseline.py |
| application | f067a01a7230 | f066a01a7230 | backend/migrations/versions/f067a01a7230_create_authorization_integrity_anchors.py |
| security | b12b01a7230 | None | backend/security_migrations/versions/b12b01a7230_create_security.py |

## PostgreSQL, roles e persistência real observada

PKI temporária: CA sintética exclusiva, certificado SAN DNS:db, chave de servidor
UID/GID 70 e modo 0600; apenas o certificado público CA é montado no backend.
Scram-sha-256 é obrigatório em sockets locais e rede; pg_hba recusa hostnossl e
aceita hostssl apenas na base de teste/rede interna. Nenhum password vai em DSN,
argumentos CLI ou relatório. Helpers lêem ficheiros sintéticos privados, sem
fallback para secrets/ ou ambiente operacional. A chave privada CA foi eliminada.

Identidade física esperada foi lida pelo canal Docker local, pg_controldata no
contentor recém-criado, antes de a comparar por conexão TLS independente com
pg_control_system. Isto prova coerência deste ensaio; não é atestação humana G4 nem
aprovação de um cluster operacional. Versão/identificador efetivos constam do log.

| Identidade sintética | Capacidades demonstradas |
|---|---|
| dev06_admin | Bootstrap independente; superuser só no descartável; cria roles e atribui ownership. Credencial nunca montada no backend. |
| dev06_owner | NOLOGIN; owner da base/schema/tabelas de teste; login realmente recusado. |
| dev06_migrator | LOGIN, NOINHERIT; membership SET explícita em owner; DDL só mediante SET ROLE no fixture dev06_probe. Nenhum Alembic executado. |
| dev06_runtime | LOGIN, sem flags administrativas/memberships/ownership; SELECT em read_target, SELECT/INSERT e UPDATE(activity) em write_target, INSERT-only em audit_target. |
| dev06_inspector | LOGIN separado; inspeciona catálogos, mas SELECT/DML nos dados de teste são recusados. Não recebe funções administrativas como atalho. |

Foram executados SQL reais que recusam CREATE TABLE em public/dev06_probe,
CREATE TEMP TABLE, CREATE ROLE, SET ROLE owner pelo runtime, UPDATE de coluna
imutável, DELETE/TRUNCATE, SELECT de audit_target e SELECT FOR UPDATE em read_target.
SELECT FOR UPDATE em write_target funciona mediante UPDATE(activity). Uma transação
com INSERT em duas tabelas e exceção é integralmente revertida. Outra ligação
confirma os dados committed e a ausência das duas escritas rolled back.

Estas permissões são uma demonstração independente, não uma validação da matriz
D05 sobre security/audit/inventory. Não há tabelas de utilizadores, sessões,
throttles ou inventário no cluster. Não se mede durabilidade após perda do cluster,
backup/restauro, failover ou recuperação independente. O restart testado é do backend;
o PostgreSQL em tmpfs não foi reiniciado para simular persistência durável.

## Readiness e integração

`/api/v1/health`: 200; `/api/v1/ready`: 503 antes/depois do restart; `/auth/me` e
`/inventory/resources` anónimos: 401; login sem origem/CSRF válidos: 403; login com
CSRF válido: 503/security_unavailable. Cookies CSRF e mecanismos existentes não
foram contornados. Não foram criadas contas aplicacionais ou sessões artificiais.

Não foi implementado um executor readiness real que substitua G2/G4: faltam a
aprovação/proveniência da revisão, schemas, manifesto ACL/referência aprovada,
identidades de verificador e autorização do transporte G4. O novo probe SQL não
devolve ReadinessObservation, não se regista na factory nem concede prontidão.
A presença de TLS/SELECT não abre readiness. Não se alteraram os gates Q1–Q16,
F02, G2, G4 ou o contrato f066/b12b da resposta positiva.

Fronteira exata: transporte e ligação TLS reais do backend demonstrados; criação
aprovada dos schemas/revisões e validação dos privilégios aplicacionais bloqueadas;
login persistente, sessão persistente e inventário autenticado não demonstrados.
Os doubles de autenticação existentes passaram nos testes offline, o que não
substitui estes testes PostgreSQL aplicacionais ainda pendentes.

## Comandos e resultados

- Build local: `docker build --network=default --progress=plain --build-arg
  DEV04_PYTHON_IMAGE=python@sha256:dc9e92fcdc085ad86dda976f4cfc58856dba33a438a16db37ff00151b285c8ca
  -t livenet-dev06/backend:integration -f backend/Dockerfile.dedicated backend`.
  Dependências/layers já disponíveis, lock e `pip check` preservados; nenhuma
  instalação no ambiente Python operacional. Builder local, sem upload de código.
- `python3 scripts/dedicated/check_context.py`: BuildKit exporta contexto real
  com 40 ficheiros exatos e adversarial com 41; hashes iguais, sem extras.
- `python3 scripts/dedicated/dev06_check.py`: overlay Compose/preflight reais,
  SQL/TLS/roles e HTTPS passaram. Nenhum compose up ou remoção de exit-78.
- Regressões backend: 23 ficheiros selecionados, 1 327 testes passaram em 100,64 s,
  incluindo TLS novo e reconciliação. PYTHONDONTWRITEBYTECODE=1,
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONPATH=backend:backend/tests,
  pytest -q -p no:cacheprovider com basetemp exclusivo. Audit hook recusa sockets,
  subprocessos e psycopg real nessa suite. Testes PostgreSQL reais só no harness.
- Gates: test_auth03_alembic_executor.py, test_g4_boundaries.py e
  test_m12b_security_execution.py: **289 passaram, duas falharam**. Repetição dos
  mesmos três ficheiros na cópia inicial: **289 passaram e as mesmas duas falharam**.
  São test_verified_manifest_and_tampering e test_future_lock_conflict_and_wrong_source;
  ambos encontram primeiro a divergência AUTH-03 já existente. Não foram alterados,
  marcados xfail, silenciados ou excluídos. verify_bundle(root=baseline) e
  verify_bundle(root=current) recusam com o mesmo motivo.
- git diff --check passou. Sem testes em PostgreSQL existente ou serviços externos.

Logs sanitizados desta sessão: `/tmp/livenet-dev06-artifacts/`: build.log,
context.log, regression.log, gates.log, gates-baseline.log, integration.log e
unit-initial.log. Na regressão inicial focada passaram 209 testes; não somar ao
resultado da suite completa como casos distintos. Inspeção da imagem validou UID,
factory TLS importável e ausência de migrações/bytecode no runtime.

Imagem testada: sha256:68e16b08b6e038f6fd9712a9a6fbb2a8b7e8f2839f048f744cf60db57bf64ad8.
Caddy derivado e PostgreSQL usaram as imagens já identificadas na DEV-05B;
nenhuma imagem operacional foi modificada. A tag nova DEV-06 foi removida ao fechar
os testes; uma repetição exige reconstrução local. Caches partilhados não são limpos.

## Alterações e rastreabilidade Git

Não se forçou uma baseline Git dos artefactos preexistentes. Muitos ficheiros
necessários ao build ainda são não versionados e não têm proveniência em commits;
um commit parcial novo não produziria um checkout funcional/reproduzível.
Ficou um plano de commits para revisão, sem git add . ou staging:

1. Rever proveniência e consolidar baseline DEV-03B/04/05A/05B por lista explícita,
   separando a alteração Alembic anterior e recusando segredos/artefactos gerados.
2. Commit atómico TLS: módulo, factory/entrypoint, overlay, preflight e testes,
   apenas depois de a baseline de dependências de código ser reproduzível.
3. Commit dos probes isolados, reconciliação/evidências e documentação correspondente.

Estado final: mesma branch/HEAD, índice preservado, sem commits ou push. Não foram
apagados ficheiros anteriores. Os corpos documentais anteriores permanecem como
sufixo integral. Gates, migrações, manifesto, executores e fontes de autenticação,
inventário e auditoria conservaram os bytes iniciais.

## Recursos, limpeza e reversão

Todos os contentores/redes de ensaio têm prefixo/label livenet.dev06 único. Cleanup
confirma essa label antes de remover; nenhum prune, volume existente ou serviço
alheio é tocado. Não são criados volumes: PostgreSQL e PKI Caddy usam tmpfs. Os
recursos/credenciais/PKI de tentativas intermédias também foram eliminados. O ensaio
final regista prefixo e cleanup_failures=[] no log integration.log. A cópia privada
da baseline e logs não secretos permanecem para comparação/revisão.

Reversão: comparar os ficheiros alterados com a baseline inicial; retirar apenas os
hunks DEV-06 e os novos ficheiros deste incremento após verificar trabalho posterior.
Não usar reset/clean/checkout global, pois eliminaria trabalho anterior não versionado.
Não existe rollback PostgreSQL aplicacional: nenhum schema/migração aplicacional foi
executado. A tag de teste é removível pelo ID exato, sem force/prune de imagens.

## Aceitação e próximo incremento

| Critério | Estado |
|---|---|
| Reconciliação | Evidência completa; decisões de nomes/revisões/manifesto pendentes. |
| PostgreSQL/TLS/identidade descartáveis | Demonstrados. |
| Privilégios mínimos | Demonstrados no fixture independente; D05 aplicacional pendente. |
| Persistência real | Commit/rollback entre conexões no fixture; persistência aplicacional bloqueada. |
| Readiness | 503 preservado; checker real bloqueado legitimamente. |
| Integração | HTTPS até ligação PostgreSQL TLS e recusa sanitizada de login. |
| Regressões | 1 327 passaram; 289 gates passaram e duas falhas preexistentes reproduzidas. |
| Git | Preservado, sem baseline/commits forçados; plano de consolidação explícito. |
| Recursos | Descartáveis removidos; sem exposição e sem volumes operacionais tocados. |
| Prontidão STAGING/PROD | Não demonstrada nem declarada. |

Próximo incremento recomendado: revisão humana conjunta das identidades físicas e
nomes por ambiente, baseline f066/f067/security e reconciliação AUTH-03. Só após
aprovação legítima do percurso de migração, preparar schemas/revisões num novo
cluster descartável, demonstrar login/sessões/throttling/auditoria e inventário de
consulta com privilégios D05 reais, e então ligar um checker que cumpra G2/G4.
Backups/restauro e recuperação independente continuam necessários antes de operação.

## Inventário final do incremento

Alterados relativamente ao snapshot inicial:

- `backend/app/dedicated.py`
- `backend/dedicated_wsgi.py`
- `backend/tests/test_dedicated_preflight.py`
- `docs/specifications/f0/data-model.md`
- `docs/specifications/f0/implementation-status.md`
- `scripts/dedicated/preflight.py`

Criados:

- `backend/app/postgres_tls.py`
- `backend/tests/fixtures/dev06-parsing-only-ca.crt`
- `backend/tests/test_dev06_reconciliation.py`
- `backend/tests/test_postgres_tls.py`
- `compose.dedicated-tls.yaml`
- `docs/operations/dev06-contract-evidence.json`
- `docs/operations/dev06-postgresql-integration.md`
- `docs/specifications/f0/dev06-postgresql-transport.md`
- `scripts/dedicated/dev06_check.py`
- `scripts/dedicated/dev06_postgres_probe.py`
- `scripts/dedicated/reconcile_contracts.py`

Confirmação final: ensaio `livenet-dev06-6258d4e41b`, PostgreSQL 16.15
(server_version_num=160015), system_identifier sintético 7700614123703337001;
cleanup sem falhas. A tag/imagem DEV-06 foi removida após confirmar ID e ausência
de outras tags. Nenhum contentor ou rede com label livenet.dev06 permanece.
Foram preservados por hash 261 ficheiros iniciais, com seis edições no âmbito
e 11 criações. Índice final igual ao inicial; sem staging ou alterações de branch.
