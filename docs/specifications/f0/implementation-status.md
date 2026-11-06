> DEV-07 (2026-10-25): React real por HTTPS validado em browser isolado;
> 40 testes frontend e 1 327 backend passaram. Gates: 289 passaram, duas falhas
> AUTH-03 preexistentes mantidas. Persistência aplicacional/readiness positiva
> continuam bloqueadas; [evidências e decisões](../../operations/dev07-react-integration.md).

> DEV-06 (2026-10-25): transporte TLS PostgreSQL e testes SQL sintéticos validados;
> persistência aplicacional e readiness positiva continuam bloqueadas. Ver
> [relatório DEV-06](../../operations/dev06-postgresql-integration.md).
> AUTH-03 não foi regenerado; falhas preexistentes dos testes estão documentadas.

> Atualização DEV-05B (2026-10-25): empacotamento e integração HTTP isolada
> validados; ativação continua bloqueada. Evidência e limites em
> [dev05b-isolated-integration](../../operations/dev05b-isolated-integration.md). O texto anterior segue preservado.

# LiveNet v2 — Estado atualizado DEV-05A

Data: 2026-10-25, progbox, main, HEAD
`647179c928888adfeef0f69f582fd13c5fc17350`. Revisão estática e documentação
limitada; sem testes, ferramentas nativas, build ou validação operacional.
O conteúdo DEV-03B e o arquivo F0 anterior continuam integralmente abaixo.

## Decisões aprovadas versus operação pendente

- DEV-03C-D01: Opção A aprovada no pedido humano DEV-04, reiterada na DEV-05A:
  Caddy/backend/PG separados, API/dados privados e backend sem ports no host.
  Aprovação de referência/preparação, não de ativação.
- DEV-05A-D01: responsável confirmou em 25/10/2026 **acesso exclusivamente interno
  ao laboratório**; fonte primária no pedido DEV-05A §1, anexo
  `adee713c-cd23-4bfd-a10e-c48de86c556e/Pasted text.txt`. UI/API só para redes
  internas explicitamente autorizadas em DEV/STAGING/PROD-VM/PROD-K8S. Sem IP
  público, port forwarding de entrada Internet, Cloudflare Tunnel/equivalentes;
  ingress K8S interno, sem LoadBalancer público. Publicação HTTPS só em interface/
  endereço interno aprovado e firewall restrito; backend/PG/Redis/auxiliares sem
  exposição externa. Egress é avaliado separadamente e não autoriza ingress.
  Exceção só por decisão explícita do responsável. HTTPS/auth/RBAC/audit/CSRF/
  cookies/sessões mantêm-se. RFC1918, hostname ou VPN não comprovam isolamento.

O [registo central](../../architecture/decision-register.md) conserva os IDs
originais; esta decisão não renumera D-01–D-52. Nenhuma proposta restante da
baseline passa a aprovada por consequência destas duas decisões.

## Estado DEV-04 após revisão

| Categoria | Estado / evidência |
| --- | --- |
| Implementado no código/artefactos | Oito ficheiros DEV-04 presentes: Dockerfile/ignore dedicados, Gunicorn container, constraints, Compose, Caddyfile, testes e documento operacional. |
| Validado offline anteriormente | DEV-04 reportou 570 testes passados; DEV-02 reportou 1135. Não repetidos na DEV-05A. |
| Revisão estática atual | Sete artefactos técnicos preservados; R01/R02 altos e R03/R04/R05 médios registados, sem correções. Não é novo resultado de testes. |
| Observação histórica isolada | PROV1/PROV2 e ensaios F0 mantidos como históricos, não revalidados. |
| Validado operacionalmente agora | Nenhum componente recebeu essa classificação; serviços/rede/firewall atuais não foram consultados. |
| Bloqueado | Compose exit 78 intacto; build do contexto real bloqueada por R02 e ativação pelos requisitos LAN-only/PG/readiness/recuperação. |
| Proposta futura | DEV-05B pode ser proposta para parsing nativo delimitado; build é capacidade separada após correção autorizada e prova do contexto. Nada iniciado. |

Relatório/evidências: [atualização DEV-05A no documento DEV-04](../../operations/dev04-dedicated-integration.md).
R01: parâmetro de bind não valida LAN e não há enforcement firewall comprovado.
R02: !app/**/ reabre a árvore app, podendo incluir não-Python; há 13 .pyc
preexistentes, sem prova de imagem construída ou segredo exposto. R03: oráculos
e strings não validam semântica Docker/Caddy/Gunicorn. R04: parâmetros obrigatórios
não comprovam coerência/montagens/identidades. R05: pins/base/dependências são
candidatos sem resolução/proveniência/hashes completos. Nenhum artefacto é corrigido.

Permanecem OPEN: f066/f067, manifesto AUTH-03 divergente, F02/G2/G4/gates,
readiness real/503, privilégios runtime, conta administrativa inicial, recuperação
independente, transporte PG/TLS, peer, UID/montagens, rede/firewall/exposição,
28 lacunas G4/L02 com enumeração SOURCE_NOT_LOCATED e restantes originais em falta.
Não se aprova acesso Internet ou enfraquecimento de segurança para testes.

## Consolidação anterior preservada — DEV-03B e arquivo F0

As linhas históricas seguintes mantêm o seu âmbito temporal. Declarações de
pending/approved/pass/externo não anulam a política LAN-only nem os achados atuais.

# LiveNet v2 — Estado atual consolidado DEV-03B

Data da leitura estática: 2026-10-25, progbox, branch `main`, HEAD
`647179c928888adfeef0f69f582fd13c5fc17350`. Consolidação documental para revisão
humana; sem testes, instalações, builds, migrações, Docker ou consultas PostgreSQL.
Não constitui aceitação F0, aprovação de decisões novas ou autorização operacional.

Esta secção distingue estado atual do código e evidência anterior. O texto
preexistente de 2026-10-18 e os registos F0.66A/B são conservados integralmente
no arquivo abaixo. Expressões antigas como pending, clean, synchronized,
committed/published e números de testes aplicam-se às etapas que os produziram,
não ao estado runtime ou Git atual.

Referências centrais: [decisões/fontes/lacunas](../../architecture/decision-register.md),
[ambientes](../../architecture/environments.md), [runtime](../../architecture/platform-runtime.md),
[roadmap](../../roadmap/platform-roadmap.md), [DEV-02](../../operations/dev02-dedicated-backend.md).
DEV-03A é um relatório no chat desta tarefa, sem ficheiro no repositório; não
é transcrição original das decisões. A presente atualização não o inventa em disco.

## Classificação da evidência

| Classificação | Significado e limite |
| --- | --- |
| Implementado no código | Fonte identificada; não implica instalação, passagem de testes ou uso real. |
| Validado por testes offline | Resultado anterior documentado com doubles/sem serviços; não repetido nesta tarefa. |
| Observado historicamente em ambiente isolado | Amostra real anterior, limitada a destino, data, permissões e operações registadas. |
| Validado operacionalmente no ambiente atual | Exigiria evidência atual específica; **nenhum componente recebeu esta classificação na DEV-03B**. |
| Parcial | Apenas parte do contrato ou produto está implementada. |
| Ausente | Implementação não identificada no inventário local consultado. |
| Bloqueado | Gate, pré-requisito ou decisão pendente impede prosseguir; não significa defeito a contornar. |

## Código presente e limites atuais

| Componente | Estado de implementação | Evidência | Operação / bloqueios |
| --- | --- | --- | --- |
| Flask e configuração | Implementado na fundação; plataforma parcial | [factory](../../../backend/app/__init__.py), [config](../../../backend/app/config.py) | Perfis não comprovam prontidão; segurança desativada por omissão na factory base. |
| Health | Implementado | [health/routes.py](../../../backend/app/health/routes.py) | Liveness sem verificar BD; operação atual não verificada. |
| Factory/arranque dedicado | Implementado como preparação | [dedicated.py](../../../backend/app/dedicated.py), [dedicated_wsgi.py](../../../backend/dedicated_wsgi.py), [Gunicorn config](../../../backend/gunicorn_dedicated.conf.py) | Sem auto-engine/DDL/contas; imagem antiga não inclui percurso DEV-02. |
| Inventário | Parcial | [rotas](../../../backend/app/inventory/routes.py), [serviço](../../../backend/app/inventory/service.py), [schemas](../../../backend/app/inventory/schemas.py) | GET lista/detalhe e POST criação; sem edição/eliminação. D05 só consulta; atributos de criação vazios. |
| Modelo físico inventory | Implementado no código, funcionalidade parcial | [models](../../../backend/app/inventory/models.py), [modelo físico](inventory-physical-model.md) | 12 tabelas; grupos/políticas/configuração efetiva não equivalem a motores funcionais. |
| Auditoria | Base/serviço implementados; instrumentação parcial | [audit](../../../backend/app/audit/service.py), [f066](../../../backend/migrations/versions/f066a01a7230_create_audit_events_baseline.py) | Auth e criação inventory usam audit; retenção/limpeza e operação atual não validadas. |
| Autenticação/sessões | Implementado no código | [security](../../../backend/app/security/service.py), [modelos](../../../backend/app/security/models.py) | Scrypt, sessão persistente, expiração, throttle e revogação; dependente de schema/ACL/conta/HTTPS. |
| RBAC | Parcial | [access](../../../backend/app/security/access.py) | Reader/editor globais; sem âmbito grupo/recurso. |
| UI React/TypeScript/Vite | Implementado para consulta | [frontend README](../../../frontend/README.md), [App](../../../frontend/src/App.tsx) | Sessão, login/logout, lista/filtros/paginação/detalhe; sem escrita ou áreas futuras funcionais. |
| Alembic aplicacional/security | Implementado em cadeias independentes | [env aplicacional](../../../backend/migrations/env.py), [contrato security](../../../backend/security_migrations/contract.py) | Dois ledgers, ligação externa security, downgrade security bloqueado; execução não autorizada. |
| Readiness | Parcial, bloqueada operacionalmente | [ready](../../../backend/app/readiness.py), [G2 adapter](../../../backend/app/readiness_postgres/adapter.py) | Sem checker real; DEV-02 devolve 503. G2 executor exclusivamente offline; revisão real pendente. |
| Proxy/HTTPS | Parcial | [TrustedProxy](../../../backend/app/trusted_proxy.py), [Caddyfile](../../../infra/web-dev/Caddyfile) | API Caddy continua 503; rede/PKI/integração não verificadas atualmente. |
| Coordenação M1.2B/G4 | Parcial, bloqueada | [coordenador](../../../scripts/postgres/m12b_security_coordinator.py), [F02](../../../scripts/postgres/g4/contracts.py) | Doubles/registos em memória e tipos não são transporte/supervisor reais ou autoridade operacional. |
| Discovery/reconciliação | Ausente funcionalmente | DAT-02/07 no [modelo conceptual](data-model.md) | Modelos de identidade não constituem descoberta. |
| Monitorização/métricas/alertas | Ausente funcionalmente | F1/F2 do [baseline](f0-baseline.md) | Sem checks, histórico operacional, séries ou notificações implementados. |
| Celery/workers/scheduler/Redis | Ausente | Tecnologias previstas no baseline/README | Sem serviços/tarefas/coordenação identificados. |
| Outbox/SSE | Ausente | DAT-08A e baseline | Sem tabela/publicador/stream; audit não substitui Outbox. |
| CI/CD/GHCR/Kubernetes | Ausente no repositório como percurso implementado | Sem workflows/manifests encontrados | Serviços externos não consultados; promoção/imagens/cluster não verificados. |
| Backup/recuperação/observabilidade | Parcial apenas em preparação/fundações | Documentos PREP/PROV2; audit/health | Sem restauro completo ou monitorização de plataforma demonstrados atualmente. |

## Validações anteriores: fontes e precedência

- F0.60–F0.66: ensaios físicos e transacionais descritos no arquivo e no modelo
  físico, restritos às bases autorizadas. Testes com savepoint/rollback externo
  comprovam atomicidade no âmbito testado, não commit durável independente.
- [R3](m12b-p2c2a-r3-operational-preflight.md), [PROV1](m12b-p2c2a-prov1-report.md),
  [PROV2](m12b-p2c2a-prov2-validation.md): sequência histórica de 2026-10-23.
  R3 antecede as roles; PROV1 criou quatro roles limitadas e PROV2 validou três
  LOGIN/leitores/ACL no cluster descartável. Em PROV2 security/authorization/ledger
  security estavam ausentes e app sem direitos aplicacionais. Não revalidado agora.
- [VAL1](m12b-p2c2b-val1-offline-audit.md) reprovou IMP1;
  [FIX1](m12b-p2c2b-imp1-fix1-report.md) e [VAL1-R2](m12b-p2c2b-val1-r2-audit.md)
  documentam 355 pass e aprovação apenas offline, sem autorização de migração.
- [G2-PREP1](m12b-p2b-d05-g2-prep1-readiness-adapter.md),
  [FIX1](m12b-p2b-d05-g2-fix1.md) e [FIX2](m12b-p2b-d05-g2-fix2.md): implementação
  e regressões sintéticas; sem transporte PostgreSQL real nem gates operacionais.
- DEV-02 documenta **1135 testes offline em 13 ficheiros, todos passados**, sem
  instalar Gunicorn/arrancar servidor. Parsing por Gunicorn, multiworker, rede,
  TLS, Caddy, PostgreSQL e durabilidade ficaram pendentes. Não repetidos na DEV-03B.
- A DEV-03A foi read-only e a DEV-03B é documental. Não há nova validação runtime,
  não se atualizaram resultados de testes nem estado externo por inferência.

## Bloqueios e lacunas mantidos

1. Originais D-01–D-52, 16 capítulos e condições integrais G4/I2 não consolidados;
   usar SOURCE_NOT_LOCATED quando ausentes, não aprovação inferida de código.
2. **As 28 lacunas G4/L02 permanecem OPEN.** A lista individual original não foi
   localizada; cardinalidade comunicada pelo pedido DEV-03B, sem verificação
   independente. L02-R01–R07 não são substituto nem mapeamento inventado dessas 28.
3. Lacunas residuais DAT-01–DAT-10, JSONB, reconciliação, ciclos/transições,
   políticas, RBAC grupo/recurso, retenção/limpeza, Outbox/SSE e assíncrono.
4. f066/f067: revisão aplicacional local f067 presente; readiness/G4 exigem f066
   e b12 security. Não resolver por head/wildcard nem alterar contratos.
5. AUTH-03: manifesto divergente conforme comparação estática DEV-03A (31/51,
   20 omissões e quatro hashes divergentes); operation_gate bloqueia mutações,
   M1.2B execution_enabled=False e F02 recusa execução. Nada regenerado/ativado.
6. Manifesto físico aprovado, avaliação PG16 real, SQL ORM/ACL/defaults, streaming,
   cancelamento/cleanup, limites medidos/supervisor, snapshots/TOCTOU e latches
   em memória continuam por tratar nas fronteiras aprovadas.
7. Recuperação administrativa independente, exclusão de escritores externos,
   migração controlada, ownership/ACL e primeira conta dependem de autorização.
8. DAT-05A/nome livenet versus factory dedicada e tabelas de retenção divergentes
   exigem clarificação. Esta atualização não altera nenhuma delas.
9. Entrega integrada, HTTPS, TLS PostgreSQL, redes/segredos por ambiente, backups,
   CI/CD, promoção, rollback e preparação multi-nó continuam pendentes.

O [roadmap proposto](../../roadmap/platform-roadmap.md) não inicia DEV-03C nem
operações. Aceitação completa F0/produção exige evidência e revisão humanas.

## Arquivo integral — registo histórico anterior à DEV-03B

O conteúdo abaixo foi preservado sem alterações; os seus estados/contagens são
históricos e não anulam os limites e fontes da consolidação acima.

# LiveNet v2 — F0 Implementation Status

Date: 2026-10-18
Status: Implementation in progress

## 1. Scope

This document tracks the implementation and validation status
of the LiveNet v2 F0 technical foundation.

Status classifications:

- Completed: implemented and validated within the stated scope.
- Partial: implementation exists but the component is incomplete.
- Pending: implementation not yet identified or started.
- To verify: available evidence is insufficient for classification.

Architectural approval, physical implementation and functional
completion are distinct milestones.

## 2. Completed foundations

- [x] Development host identified: progbox.
- [x] LiveNet v1 repository preserved.
- [x] Independent LiveNet v2 repository initialized.
- [x] GitHub repository ppmatrix/LiveNet-v2 configured.
- [x] Local main branch synchronized with origin/main.
- [x] Initial monorepo structure prepared.
- [x] Preliminary F0 technical baseline documented.
- [x] Flask application factory implemented.
- [x] Initial application configuration environments defined.
- [x] Health endpoint implemented: GET /api/v1/health.
- [x] PostgreSQL 16 Docker service configured.
- [x] Docker Secret used for the PostgreSQL password.
- [x] SQLAlchemy 2 models and Alembic migrations established.
- [x] Dedicated migration test database used.
- [x] Physical inventory model implemented through F0.65D.

## 3. Inventory physical model

Completed and committed migration stages:

| Stage | Physical entity | Alembic revision |
|---|---|---|
| F0.60 | inventory.resources | af62df027d9d |
| F0.61 | inventory.resource_identifiers | 4f625db33d6d |
| F0.62 | inventory.resource_relations | 38d641dcd780 |
| F0.63A | inventory.groups | da34876e4210 |
| F0.63B | inventory.group_memberships | ba06dd956da9 |
| F0.63C | inventory.group_rules | 44e7eb855b5a |
| F0.64A | inventory.tags | 7c4e2a91b605 |
| F0.64B | inventory.resource_tags | 9e1b7c42a630 |
| F0.65A | inventory.policies | c4a91e7b205d |
| F0.65B | inventory.policy_versions | e65b01a7c230 |
| F0.65C | inventory.policy_assignments | f065c01a7230 |
| F0.65D | inventory.effective_configs | f065d01a7230 |

The four policy tables are physically implemented.

Policy resolution, precedence enforcement, effective configuration
calculation, lifecycle services, concurrency handling and audit
integration remain functionally pending.

See inventory-physical-model.md for the physical contracts,
constraints and validation details.

## 4. Validation evidence

- [x] Full backend test suite: 130 passed.
- [x] F0.65D Alembic revision: f065d01a7230.
- [x] Latest validated test-database revision: f066a01a7230.
- [x] F0.65D PostgreSQL integrity tests: 10 passed.
- [x] F0.65D downgrade and upgrade validated.
- [x] F0.65D migration tested in livenet_f0_test.
- [x] F0.65D commit 3bb6324 published to origin/main.
- [x] Git working tree clean after publication.

These results establish the tested scope, not complete F0
acceptance or production readiness.

## 5. Partially implemented components

- [ ] Backend: application skeleton exists; domain services
      and functional APIs remain to be implemented.
- [ ] REST API: health endpoint exists; functional endpoints
      remain pending.
- [ ] PostgreSQL: infrastructure and inventory migrations
      validated; remaining domain schemas are pending.
- [ ] Docker Compose: db and backend services configured;
      complete development stack remains pending.
- [ ] Automated testing: initial backend coverage established;
      integration, security, frontend and end-to-end coverage
      remain to be assessed and implemented.
- [ ] Inventory: physical model established; business logic,
      validation services and operational interfaces pending.

## 6. Pending or unverified components

- [ ] Frontend React/TypeScript/Vite application.
- [ ] Redis and Celery integration.
- [ ] Authentication and RBAC foundation.
- [ ] Functional API contracts and module interfaces.
- [ ] Server-Sent Events infrastructure.
- [ ] GitHub Actions CI/CD pipeline.
- [ ] GitHub Container Registry integration.
- [ ] Discovery, monitoring, operations and security domain
      implementations; functional audit integration remains pending.
- [ ] Transactional Outbox implementation.
- [ ] Operational readiness, observability and deployment
      acceptance criteria.

The preceding items are not considered implemented based
on the evidence collected in the F0 review.

## 7. Documentation dependencies

- [ ] Verify the complete D-01 to D-51 decision register.
- [ ] Verify and incorporate the D-52 SIEM provision.
- [ ] Consolidate the 16 approved technical chapters.
- [ ] Preserve technical gaps and deferred decisions.
- [ ] Extract and validate complete F0 acceptance criteria.
- [ ] Validate module interfaces and data contracts.
- [ ] Reconcile historical conceptual specifications with
      subsequently approved physical implementations.

Existing documents remain historical and architectural
references; this status document does not supersede
approved decisions.

## 8. Constraints

- Do not modify LiveNet v1.
- Do not infer missing architectural decisions.
- Preserve efficient operation with fewer than 100 resources.
- Maintain proportional scalability toward 100–1,000 resources.
- Keep SIEM implementation outside the initial MVP.
- Do not migrate or modify the main PostgreSQL database
  livenet without explicit authorization.
- Use livenet_f0_test for authorized migration testing.
- Do not equate validated database models with completed
  application functionality.

## 9. Next milestone

Complete the F0 gap analysis and validate the implementation
sequence against the approved Technical Plan before starting
the next development component.

## F0.66A — Centralized audit physical baseline

**Status:** Physical implementation validated.

**Approved contract:** INV-08A / F0.66-C01.

**Implementation:**
- PostgreSQL schema: `audit`.
- Table: `audit.events`, with 12 columns.
- SQLAlchemy model: `app.audit.models.AuditEvent`.
- Alembic revision: `f066a01a7230`.
- Previous revision: `f065d01a7230`.
- Seven constraints: primary key and six CHECK constraints.
- Three indexes for chronological, entity and correlation queries.
- PostgreSQL trigger `trg_audit_events_immutable` rejects UPDATE and DELETE.
- Function `audit.prevent_event_mutation()` implements the trigger.

**Validation evidence:**
- Migration applied successfully to `livenet_f0_test`.
- Five PostgreSQL functional checks passed.
- Test events rolled back without persistence.
- Downgrade to `f065d01a7230` validated.
- Upgrade to `f066a01a7230` validated.
- Audit table and trigger restored successfully.
- Backend regression suite: 130/130 tests passed.
- SQLAlchemy metadata registration validated.

**Remaining work:**
- F0.66B: transactional audit infrastructure and integration
  tests (implemented, validated and published).
- Functional instrumentation of domain services remains pending.
- PostgreSQL permission policy.
- Operational retention and cleanup procedures.
- Transactional Outbox physical contract and implementation.
- Additional integrated tests for atomicity and idempotency.

**Safety:** All migration operations were restricted to
`livenet_f0_test`. The main `livenet` database was not migrated.


## F0.66B — Transactional audit service

**Status:** Implemented, validated, committed and published.

**Approved contract:** INV-08A / F0.66-C02.

**F0.66B.1 — SQLAlchemy session infrastructure:**
- `app.core.database.create_session_factory(engine)` creates a
  sessionmaker bound to an existing SQLAlchemy engine.
- Session configuration: `autoflush=False` and
  `expire_on_commit=False`.
- Transaction ownership belongs to the caller, using a
  shared session and an explicit transaction boundary.
- Application-lifetime engine management and integration
  into functional domain services remain pending.

**F0.66B.2 — Centralized audit writing service:**
- Implementation: `app.audit.service.record_audit_event()`.
- Receives an existing SQLAlchemy Session.
- Adds an `AuditEvent` to that session.
- Does not independently commit, flush or roll back.
- Validates required strings, maximum lengths and optional UUIDs.
- Validates `changes` and `context` as JSON objects.
- Rejects non-JSON-compatible values, including NaN and infinity.
- Creates independent JSON copies of input payloads.
- Rejects a defined set of sensitive field names, including
  occurrences in nested objects and arrays.
- Does not depend on Flask request or application context.

**F0.66B.3 — PostgreSQL transactional integration tests:**
- Three integration tests executed against `livenet_f0_test`.
- Inventory resource and audit event written in one transaction.
- Audit database failure rolls back the Inventory operation.
- Inventory database failure rolls back the audit event,
  including an event previously sent through `session.flush()`.
- Tests use an outer transaction with rollback and
  SQLAlchemy savepoints for isolation.
- Final database verification: zero residual Inventory
  resources and zero residual audit events.

**Validation evidence:**
- Implementation commit: `de9f4f3`, published to `origin/main`.
- Backend unit/regression tests: 162/162 passed.
- PostgreSQL integration tests: 3/3 passed.
- Python syntax validation passed.
- Git whitespace validation passed.
- No new database migration or physical schema change.

**Limitations and remaining work:**
- Sensitive-field filtering is based on known field names;
  it does not guarantee detection of every secret.
- Domain services must explicitly select safe audit payloads.
- Tests demonstrate transactional atomicity within an
  outer rollback boundary, not independent durable persistence
  after a final database commit.
- Functional Inventory operations are not yet instrumented
  to emit audit events.
- PostgreSQL permission policy, retention and operational
  procedures remain pending.
- Transactional Outbox and SIEM functionality are outside
  this implementation stage.

**Safety:** PostgreSQL integration tests were restricted to
`livenet_f0_test`. The main `livenet` database was not modified.
