# LiveNet v2 — Atualização vinculativa DEV-05A

Data: 2026-10-25, progbox. Fonte humana primária: pedido DEV-05A desta conversa,
anexo `adee713c-cd23-4bfd-a10e-c48de86c556e/Pasted text.txt`, secções 1 e 4.
Este incremento é documental; não altera código, infraestrutura, gates ou rede.

## DEV-05A-D01 — Acesso exclusivamente interno

**APROVADA PELO RESPONSÁVEL DO PROJETO em 25/10/2026**, conforme confirmação
expressa no pedido humano. É restrição arquitetural vinculativa, não proposta.
ID novo e inequívoco: `DEV-05A-D01`; nenhum D-01–D-52 é renumerado/substituído.

O LiveNet v2 destina-se exclusivamente à rede interna do laboratório, em DEV,
STAGING, PROD-VM e PROD-K8S. UI/API só são acessíveis por redes internas
explicitamente autorizadas. Não há acesso pela Internet, IP público, port
forwarding de entrada Internet, Cloudflare Tunnel ou serviço equivalente.
Caddy só pode publicar HTTPS em interface/endereço interno aprovado, com firewall
restrito às redes autorizadas. Backend, PostgreSQL, Redis e auxiliares não podem
ser publicados externamente. Em K8S, ingress exclusivamente interno, sem
LoadBalancer público. HTTPS, autenticação, autorização, auditoria, CSRF, cookies
e proteção de sessões continuam obrigatórios. Saídas são avaliadas separadamente
e não autorizam entrada. Qualquer exceção futura exige decisão arquitetural
explícita do responsável; não pode ser introduzida por conveniência de deployment.

RFC1918, DNS interno ou hostname não provam isolamento. Conferir interfaces,
firewall efetivo incluindo regras Docker, routing/NAT IPv4/IPv6, routers, VPNs,
túneis, proxies e partilha de portas. VPN/rede não inventariada não recebe acesso
implícito. Os termos históricos público/externo/edge não autorizam Internet:
no desenho válido significam no máximo entrada na VM a partir da LAN autorizada.
O bind Gunicorn 0.0.0.0 dentro do namespace não equivale a publicar no host.

## Aprovações e evidência atualizadas

| ID original | Descrição verificável | Fonte | Aprovação | Implementação / evidência | Dependências | Divergências / lacunas |
| --- | --- | --- | --- | --- | --- | --- |
| DEV-03C-D01 | Opção A: Caddy/backend/PG separados; API/dados privados; backend sem porta host | Pedido DEV-04, anexo c94f7ffa-8d9e-4c05-af09-4cb20da87eb6/Pasted text.txt; reiterado em DEV-05A | APROVADA para arquitetura de referência e preparação offline | Oito artefactos DEV-04 presentes; 570 testes históricos documentados; Compose com exit 78 | Destinos, peer, segredos, TLS, ACL, parsing/build autorizados separadamente | Não é aprovação de ativação ou de cada parâmetro. |
| DEV-05A-D01 | UI/API só na LAN explicitamente autorizada em todos os ambientes | Pedido DEV-05A §1, confirmação humana de 25/10/2026 | APROVADA, vinculativa | Documentada; enforcement e isolamento real NÃO VALIDADOS | Bind interno aprovado, redes permitidas e firewall/routing verificados | DEV04_HTTPS_BIND_IP é só obrigatório, não valida LAN; sem política firewall implementada. |

Estas aprovações específicas não promovem outras propostas DEV-03B a decisões
aprovadas. A escolha A não encerra lacunas G4/L02 ou contratos de dados/segurança.

## Revisão DEV-04: resultado e limitações

**BLOCKED para build do contexto real e ativação; validação nativa pendente de
autorização DEV-05B.** A revisão é estática, não foi executado qualquer teste.
Os sete artefactos técnicos DEV-04 ficam intactos. Só o seu documento operacional
recebe a atualização expressamente autorizada pelo pedido DEV-05A §4.

Achados completos e evidências: [revisão no documento DEV-04](../operations/dev04-dedicated-integration.md).

| Achado | Severidade | Evidência estática / condição |
| --- | --- | --- |
| DEV-05A-R01 | ALTA para ativação | compose.dedicated.yaml:17/69 e infra/dedicated/Caddyfile:13–45: não limitam redes cliente nem comprovam binding/firewall LAN-only; exit 78 não é controlo de rede. |
| DEV-05A-R02 | ALTA para build | backend/Dockerfile.dedicated.dockerignore:2–4 reabre recursivamente app; COPY app em Dockerfile:13 pode incluir não-Python. Teste de igualdade literal não deteta isso. |
| DEV-05A-R03 | MÉDIA | backend/tests/test_dedicated_packaging.py:161–211 implementa oráculo de headers, não Caddy; checks de strings/JSON não provam semântica nativa. |
| DEV-05A-R04 | MÉDIA | Compose:24/39–41/54–62/70–71 requer valores mas não prova coerência IPAM/peer/JSON, paths privados, roles distintas ou privilégios reais. |
| DEV-05A-R05 | MÉDIA | Dockerfile:3–10 e constraints:1–18: base livre por ARG e pins candidatos sem hashes/resolução; reprodução/distribuição e egress de build não validados. |

R02 é inferência estática fundamentada na semântica documentada Docker: barras
finais são ignoradas, ** é recursivo, e a última regra coincidente determina a
inclusão. Assim, `!app/**/` não restringe a diretórios/Python. Foram localizados
13 .pyc preexistentes em app; não se criou sentinela, executou matcher ou build,
nem se afirma que um segredo tenha sido encontrado/copiado. Referência técnica:
[Docker, sintaxe de dockerignore](https://docs.docker.com/build/concepts/context/#syntax).

Permanecem OPEN: as 28 lacunas G4/L02 (enumeração SOURCE_NOT_LOCATED), L02-R01–R07,
originais D-01–D-52/16 capítulos, f066/f067, manifesto AUTH-03, F02/G2/G4/gates,
readiness real, privilégios runtime, conta administrativa inicial, recuperação
independente, transporte PostgreSQL/TLS, peer e montagem/ownership dos segredos.
Não há achado crítico demonstrado nesta leitura; isso não certifica a exposição
real do ambiente, que não foi consultado. Não houve ativação nesta tarefa.

## Registo anterior preservado — baseline DEV-03B

O texto seguinte permanece integral como histórico. Aprovações e política
LAN-only acima têm o âmbito humano indicado; frases históricas não as relaxam.

# LiveNet v2 — Registo de decisões e lacunas

Baseline documental DEV-03B, 2026-10-25, progbox. Branch `main`, HEAD de leitura
`647179c928888adfeef0f69f582fd13c5fc17350`. Documento preparado para revisão humana;
não aprova decisões novas, implementação, instalação, migrações ou operação.

## Leitura do registo

- `DECLARED_APPROVED`: uma fonte documental declara aprovação. O registo humano
  original não foi localizado, salvo indicação explícita. Não equivale a autorização.
- `HUMAN_REFERENCE`: um pedido humano disponível refere a decisão/contrato; um
  resumo ou referência não substitui o texto integral original e as suas condições.
- `PROPOSED`: proposta da presente baseline, sujeita a aprovação.
- `SOURCE_NOT_LOCATED`: texto original ou fonte individual não localizado. Não
  reconstruir o original a partir de código, testes, resumos ou identificadores.
- Implementação: `IMPLEMENTED`, `PARTIAL`, `ABSENT` ou `PLANNED`; execução bloqueada
  é indicada separadamente. Código e testes offline não provam operação atual.

Os IDs abaixo conservam os prefixos originais. Não confundir M1.2B-D05,
P2B-D05 e G4D-05. Os códigos S/E servem apenas para referências documentais/técnicas.
Na ausência de ID original, usa-se `SEM_ID_NA_FONTE`, sem inventar uma decisão D-nn.

## Fontes documentais

| Ref. | Fonte e âmbito |
| --- | --- |
| S01 | [Baseline F0](../specifications/f0/f0-baseline.md): working draft, arquitetura declarada aprovada, ambientes e pendências originais. |
| S02 | [Modelo conceptual](../specifications/f0/data-model.md): DAT, contratos e lacunas. |
| S03 | [Modelo físico](../specifications/f0/inventory-physical-model.md): INV e decisões complementares F0. |
| S04 | [Autenticação M1.2A](../specifications/f0/m12a-local-authentication.md). |
| S05 | [Cadeia security P1](../specifications/f0/m12b-p1-security-migrations.md). |
| S06 | [Executor P2C-1](../specifications/f0/m12b-p2c1-security-executor.md). |
| S07 | [Privilégios R1](../specifications/f0/m12b-p2c2a-privilege-review.md) e [handoff R2](../specifications/f0/m12b-p2c2a-r2-inspection-handoff.md). |
| S08 | [R3](../specifications/f0/m12b-p2c2a-r3-operational-preflight.md), [PROV1](../specifications/f0/m12b-p2c2a-prov1-report.md), [PROV2](../specifications/f0/m12b-p2c2a-prov2-validation.md): amostras históricas, não atestação atual. |
| S09 | [Preparação P2C-2B](../specifications/f0/m12b-p2c2b-operational-preparation.md), [IMP1](../specifications/f0/m12b-p2c2b-imp1-offline-coordinator.md), [VAL1](../specifications/f0/m12b-p2c2b-val1-offline-audit.md), [FIX1](../specifications/f0/m12b-p2c2b-imp1-fix1-report.md), [VAL1-R2](../specifications/f0/m12b-p2c2b-val1-r2-audit.md). |
| S10 | [G2-PREP1](../specifications/f0/m12b-p2b-d05-g2-prep1-readiness-adapter.md), [FIX1](../specifications/f0/m12b-p2b-d05-g2-fix1.md), [FIX2](../specifications/f0/m12b-p2b-d05-g2-fix2.md). |
| S11 | [Preparação AUTH-03](../specifications/f0/auth03-integration-preparation.md) e [executor AUTH-03](../specifications/f0/auth03-alembic-executor.md). |
| S12 | [Backend HTTPS M1.3D](../specifications/f0/m13d-prep1-backend-https.md) e [DEV-02](../operations/dev02-dedicated-backend.md). |
| S13 | [Frontend](../../frontend/README.md), [web-dev](../../infra/web-dev/README.md) e [README principal](../../README.md). |
| S14 | DEV-03A: relatório no chat desta tarefa, sem ficheiro no repositório. Análise secundária, não decisão original nem prova runtime. |

Pedidos humanos anteriores disponíveis nesta conversa, externos ao repositório:

- H01: G4-HO1, anexo `dfd807fe-c083-4d5d-9d9c-cc63994b0688/Pasted text.txt`.
- H02: G4-HO2-I1, anexo `6e0cea03-07d9-4541-a777-9eb5ea6679fb/Pasted text.txt`.
- H03: I2-S01-AUDIT, anexo `deb81a29-e48f-4bb4-a3a1-db597653dc5a/Pasted text.txt`.
- H04: L02-SPEC-VERIFY, anexo `876eb65f-e7a0-4f6a-9035-51bee399dcba/Pasted text.txt`.
- H05: DEV-03B, anexo `d7aab3cd-62e5-4ee3-b5ce-98432b0fa689/Pasted text.txt`.

Estes anexos foram consultados sob `/home/paulo/.codex/attachments/`. Não são
distribuídos com um checkout. A sua incorporação futura exige recuperar os textos
originais corretos; esta baseline não os transcreve nem substitui. H04 exige
expressamente não usar o próprio pedido como substituto dos documentos originais.

## Evidência técnica estática

| Ref. | Componente / evidência |
| --- | --- |
| E01 | [Modelos inventory](../../backend/app/inventory/models.py), [schemas](../../backend/app/inventory/schemas.py), [serviço](../../backend/app/inventory/service.py), [rotas](../../backend/app/inventory/routes.py). |
| E02 | [Audit](../../backend/app/audit/service.py), [modelos](../../backend/app/audit/models.py), migração [f066](../../backend/migrations/versions/f066a01a7230_create_audit_events_baseline.py). |
| E03 | [Security models](../../backend/app/security/models.py), [service](../../backend/app/security/service.py), [access](../../backend/app/security/access.py), [policy](../../backend/app/security/policy.py), [csrf](../../backend/app/security/csrf.py). |
| E04 | [Contrato security](../../backend/security_migrations/contract.py), [env](../../backend/security_migrations/env.py), [b12](../../backend/security_migrations/versions/b12b01a7230_create_security.py), [env aplicacional](../../backend/migrations/env.py), [f067](../../backend/migrations/versions/f067a01a7230_create_authorization_integrity_anchors.py). |
| E05 | [Executor M1.2B](../../scripts/postgres/m12b_security_migration.py), [adaptadores offline](../../scripts/postgres/m12b_security_adapters.py), [coordenador](../../scripts/postgres/m12b_security_coordinator.py). |
| E06 | [Factory dedicada](../../backend/app/dedicated.py), [entrypoint](../../backend/dedicated_wsgi.py), [Gunicorn](../../backend/gunicorn_dedicated.conf.py), [proxy](../../backend/app/trusted_proxy.py), [readiness](../../backend/app/readiness.py). |
| E07 | [G2 policy](../../backend/app/readiness_postgres/policy.py), [queries](../../backend/app/readiness_postgres/queries.py), [evaluate](../../backend/app/readiness_postgres/evaluate.py), [adapter](../../backend/app/readiness_postgres/adapter.py). |
| E08 | F02: [contracts.py](../../scripts/postgres/g4/contracts.py); [doubles F16](../../scripts/postgres/tests/g4_doubles.py); [testes F23](../../scripts/postgres/tests/test_g4_boundaries.py). |
| E09 | [AUTH-03 executor](../../scripts/postgres/auth03_alembic_executor.py), [manifesto existente](../../scripts/postgres/auth03_executor_integrity.json). |
| E10 | [UI](../../frontend/src/App.tsx), [cliente HTTP](../../frontend/src/api/client.ts), [Dockerfile antigo](../../backend/Dockerfile), [Compose backend](../../compose.backend.yaml), [Caddyfile](../../infra/web-dev/Caddyfile). |

## Arquitetura geral e originais pendentes

| ID original | Título / descrição verificável | Fonte | Aprovação | Implementação | Evidência | Dependências | Divergências / lacunas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D-01–D-51 | Registo integral do plano original | S01/S02 | SOURCE_NOT_LOCATED | Não classificável por ID individual | Só referências | Recuperar originais e aprovação | Não atribuir IDs a escolhas por inferência. |
| D-52 | Previsão de integração SIEM posterior ao MVP | S01 | DECLARED_APPROVED; original SOURCE_NOT_LOCATED | PLANNED | S01 §5 | Contratos futuros de eventos | SIEM não é dependência inicial; condições integrais não localizadas. |
| Sem IDs identificados | 16 capítulos técnicos originais | S01/S02 | SOURCE_NOT_LOCATED | Não classificável | Pendência explícita | Recuperar versão integral | Não reconstruir capítulos. |
| SEM_ID_NA_FONTE | Independência do v1 e monólito modular | S01 | DECLARED_APPROVED | PARTIAL | E01–E03 | Contratos dos módulos | Faltam restantes domínios funcionais. |
| SEM_ID_NA_FONTE | Flask, React/TS/Vite e PostgreSQL | S01/S13 | DECLARED_APPROVED | IMPLEMENTED no recorte atual | E01/E03/E10 | Entrega integrada | Operação atual não verificada. |
| SEM_ID_NA_FONTE | Agentless-first | S01 | DECLARED_APPROVED | PLANNED | Sem coletores/scanners identificados | Adaptadores e alcance de rede | Não equivale a descoberta implementada. |
| SEM_ID_NA_FONTE | Celery/Redis, REST/SSE | S01 | DECLARED_APPROVED | REST PARTIAL; restantes ABSENT | E01/E10 | Filas, eventos e scheduler | Detalhes runtime por aprovar. |
| SEM_ID_NA_FONTE | Compose, GitHub Actions e GHCR | S01 | DECLARED_APPROVED | Compose PARTIAL; CI/registry ABSENT localmente | E10; sem workflows encontrados | Artefactos e promoção | Recursos externos não consultados. |
| SEM_ID_NA_FONTE | DEV progbox, STAGING Proxmox, PROD VM; K8S futuro | S01/H05 | HUMAN_REFERENCE para objetivo; detalhes PROPOSED | PARTIAL | Compose/testes isolados | environments.md | K8S condicional no baseline; desenho multi-nó ainda não aprovado. |
| SEM_ID_NA_FONTE | Escala inicial inferior a 100; preparação 100–1000 recursos | S01/S02 | DECLARED_APPROVED | PARTIAL: orientação | Modelos e limites de API | Medição/capacidade | Multi-nó não autoriza complexidade ou metas de carga inventadas. |
| SEM_ID_NA_FONTE | RBAC global, grupo e recurso | S02 §6 | DECLARED_APPROVED | PARTIAL: só global | E03 | Modelo de âmbitos/herança | Não inferir RBAC completo da autenticação. |
| SEM_ID_NA_FONTE | Checks, execuções, estados e métricas separados | S02 §4 | DECLARED_APPROVED; parâmetros a reconfirmar | PLANNED | Estados up/down/degraded/unknown/stale descritos | Contratos/monitoring | 3 falhas, 2 sucessos e freshness 3 intervalos carecem da reconfirmação original pedida em S02. |
| SEM_ID_NA_FONTE | Operações Observe, Manual, Scheduled e Campaign | S02 §5 | DECLARED_APPROVED | PLANNED | Contrato conceptual | Pedidos/execuções/idempotência | Sem operações implementadas; não autoriza executar ações. |
| SEM_ID_NA_FONTE | DiscoverAdapter, CollectAdapter, HealthAdapter e ExecuteAdapter | S02 §8 | Previsto; aprovação integral SOURCE_NOT_LOCATED | PLANNED | Apenas nomes de contratos | Interfaces e fontes originais | Não inventar assinaturas ou compatibilidade dos adaptadores. |

## Decisões conceptuais DAT

Para cada linha, S02 declara aprovação; a aprovação original independente é
`SOURCE_NOT_LOCATED`. A descrição seguinte é síntese verificável, não transcrição.

| ID original | Título / descrição verificável | Fonte | Aprovação | Implementação | Evidência | Dependências | Divergências / lacunas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DAT-01A | Catálogo inicial de oito tipos | S02 §11 | DECLARED_APPROVED | IMPLEMENTED na API inicial | E01 | Validação por tipo | Extensão controlada sem contrato completo JSONB. |
| DAT-01B | Atributos comuns e UUID persistente | S02 §11 | DECLARED_APPROVED | IMPLEMENTED | E01 | Migrações | API só aceita attributes vazio na criação. |
| DAT-02A | Identificadores externos contextualizados | S02 §11 | DECLARED_APPROVED | PARTIAL: modelo | E01 | Adaptadores | Sem API/reconciliação funcional. |
| DAT-02B | Proveniência e confiança | S02 §11 | DECLARED_APPROVED | PARTIAL: campos | E01 | Fontes/evidência | Sem processo de consolidação. |
| DAT-02C | Reconciliação de identidades | S02 §11 | DECLARED_APPROVED | PLANNED | Modelo de identificadores | Discovery/revisão | Colisões e aprovação não implementadas. |
| DAT-03A | Estados administrativos | S02 §11 | DECLARED_APPROVED | PARTIAL | E01/E10 | Ciclo de vida | Não indicam disponibilidade operacional. |
| DAT-03B | Aprovação e transições | S02 §11 | DECLARED_APPROVED | PLANNED para workflow completo | E01 | RBAC/audit | Sem API de transições. |
| DAT-04A | Relações tipadas dirigidas | S02 §11 | DECLARED_APPROVED | PARTIAL: modelo | E01 | Catálogo de relações | Sem serviço funcional completo. |
| DAT-04B | Cardinalidades e histórico temporal | S02 §11 | DECLARED_APPROVED | PARTIAL | E01/S03 | Validação/ciclos | Constraints não comprovam semântica completa. |
| DAT-05A | Uma base livenet e seis schemas de domínio | S02 §11 | DECLARED_APPROVED | PARTIAL | E01–E04 | Domínios restantes | E06 recusa livenet no perfil dedicado; âmbito por ambiente por clarificar. |
| DAT-05B | Nomes, UUID, UTC e evolução compatível | S02 §11 | DECLARED_APPROVED | PARTIAL transversal | E01–E04 | Revisão por migração | Não certifica todos os objetos nem futuras migrações. |
| DAT-06A | Monitoring inicialmente em PostgreSQL, sem partição obrigatória | S02 §11 | DECLARED_APPROVED | ABSENT | Sem módulo monitoring | Checks/estados/métricas | Não introduzir TSDB como requisito implícito. |
| DAT-06B | Retenção e agregação de métricas | S02 §11 | DECLARED_APPROVED | ABSENT | Apenas política | Scheduler/retenção | Secção 4 menciona diários por 3 anos; tabela posterior difere, sem precedência consolidada. |
| DAT-07A | Retenção Discovery | S02 §11 | DECLARED_APPROVED | ABSENT | Apenas política | Observações/candidatos | Sem limpeza implementada. |
| DAT-08A | Outbox PostgreSQL, at-least-once e consumidores idempotentes | S02 §11 | DECLARED_APPROVED | ABSENT | Sem Outbox identificado | Workers/contrato de eventos | Independente de audit; não exige Kafka/RabbitMQ. |
| DAT-09A | Grupos estáticos/dinâmicos e etiquetas | S02 §11 | DECLARED_APPROVED | PARTIAL: tabelas | E01/S03 | Avaliador e APIs | Sem agrupamento dinâmico funcional. |
| DAT-10A | Políticas versionadas; precedência global/grupo/recurso | S02 §11 | DECLARED_APPROVED | PARTIAL: tabelas | E01/S03 | Avaliação/RBAC | Cálculo, conflitos e aplicação pendentes. |

## Decisões físicas INV e complementares

S03 declara estas decisões aprovadas; a aprovação humana original independente
não foi localizada. O estado físico não prova a funcionalidade dos serviços.

| ID original | Título / descrição verificável | Fonte | Aprovação | Implementação | Evidência | Dependências | Divergências / lacunas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| INV-01A | inventory.resources | S03 §2 | DECLARED_APPROVED | IMPLEMENTED modelo/API inicial | E01 | Identidade/RBAC | Sem edição/arquivamento na API. |
| INV-02A | resource_identifiers | S03 §3 | DECLARED_APPROVED | PARTIAL: físico | E01 | Reconciliação | Sem fluxo funcional. |
| INV-03A | resource_relations | S03 §4 | DECLARED_APPROVED | PARTIAL: físico | E01 | Semântica/ciclos | Sem fluxo funcional. |
| INV-04A | Grupos de recursos | S03 §5 | DECLARED_APPROVED | PARTIAL: físico | E01 | APIs/avaliador | Regras dinâmicas sem motor. |
| INV-05A | Etiquetas e atribuições | S03 §6 | DECLARED_APPROVED | PARTIAL: físico | E01 | APIs | Filtros UI limitados a tipo/estado. |
| INV-06A | Políticas/configuração efetiva | S03 §7 | DECLARED_APPROVED | PARTIAL: físico | E01 | DAT-10A | Sem cálculo/aplicação. |
| INV-07A | Integridade e concorrência | S03 §8 | DECLARED_APPROVED | PARTIAL | E01/testes físicos históricos S03 | Operações reais | Não valida concorrência distribuída da aplicação. |
| INV-08A | Auditoria centralizada append-only | S03 §9 | DECLARED_APPROVED | IMPLEMENTED base e serviço | E02 | Instrumentação/retenção | Sem política operacional executada de retenção. |
| INV-09A | Implementação incremental | S03 §10 | DECLARED_APPROVED | PARTIAL | Cadeia de migrações | Revisão e ensaios isolados | Sem autorização genérica para DDL. |
| F0.62-C01 | Integridade temporal de relações | S03 secção homónima | DECLARED_APPROVED | IMPLEMENTED no físico | E01/migrações | Operações de domínio | Testes históricos não repetidos. |
| F0.63-C01 | Constraints dos grupos | S03 secção homónima | DECLARED_APPROVED | IMPLEMENTED no físico | E01/migrações | Serviços de grupos | Sem workflow funcional. |
| F0.63B-C01 | Integridade temporal de pertenças | S03 secção homónima | DECLARED_APPROVED | IMPLEMENTED no físico | E01/migrações | Serviços de pertença | Operação atual não verificada. |
| F0.63C-C01 | Integridade física das regras | S03 secção homónima | DECLARED_APPROVED | IMPLEMENTED no físico | E01/migrações | Motor de regras | Não demonstra avaliação. |
| F0.64A-C01 | Normalização de etiquetas | S03 secção homónima | DECLARED_APPROVED | IMPLEMENTED no físico | E01/migrações | Serviços/API | Operação atual não verificada. |
| F0.64B-C01 | Integridade temporal das atribuições | S03 secção homónima | DECLARED_APPROVED | IMPLEMENTED no físico | E01/migrações | Serviços/API | Operação atual não verificada. |
| F0.65A-C01 | Catálogo de políticas | S03 secção homónima | DECLARED_APPROVED | IMPLEMENTED no físico | E01/migrações | Validação funcional | Sem resolução. |
| F0.65B-C01 | Imutabilidade das versões | S03 secção homónima | DECLARED_APPROVED | IMPLEMENTED no físico | E01/migrações | Publicação | Sem workflow de publicação. |
| F0.65C-C01 | Integridade das atribuições de políticas | S03 secção homónima | DECLARED_APPROVED | IMPLEMENTED no físico | E01/migrações | Precedência | Sem aplicação funcional. |
| F0.65D-C01 | Integridade das configurações efetivas | S03 secção homónima | DECLARED_APPROVED | IMPLEMENTED no físico | E01/migrações | Calculador | Tabela não equivale a cálculo. |
| F0.66-C01 | Baseline física audit | Estado F0, arquivo histórico; S03 | DECLARED_APPROVED | IMPLEMENTED | E02 | ACL/retenção | Evidência física limitada a testes históricos. |
| F0.66-C02 | Serviço transacional audit | Estado F0, arquivo histórico | DECLARED_APPROVED | IMPLEMENTED | E02/S12 | Chamador detém transação | Teste com rollback externo não prova commit durável. |

## Segurança e coordenação PostgreSQL

| ID original | Título / descrição verificável | Fonte | Aprovação | Implementação | Evidência | Dependências | Divergências / lacunas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M1.2-D01 | Autenticação local persistente | S04 | DECLARED_APPROVED | IMPLEMENTED no código | E03 | Security/ACL/HTTPS | Dois papéis globais; conta inicial e operação pendentes. |
| M1.2B-D01 | Security em cadeia Alembic independente | S05 | DECLARED_APPROVED | IMPLEMENTED | E04 | Ligação externa/transação | Não fundir ledgers; autogeração aplicacional é abrangente. |
| M1.2B-D02 | Bootstrap, migrator e app separados | S06 | DECLARED_APPROVED | PARTIAL | E05/S08 | Provisionamento aprovado | PROV1/2 só atestam cluster histórico de ensaio. |
| M1.2B-D03 | Transação externa, lock e validação física | S06 | DECLARED_APPROVED | PARTIAL; execução BLOCKED | E05 | Adaptadores reais | Offline não prova locks/DDL reais. |
| M1.2B-D04 | CREATE temporário e revogação | S07 | DECLARED_APPROVED | PLANNED | Plano R1/R2 | Janela/autorização | Sem grants automáticos. |
| M1.2B-D05 | Owner NOLOGIN, restrições PUBLIC e inspeção separada | S07/S08 | DECLARED_APPROVED | PARTIAL | E05; PROV1/2 históricos | Fecho administrativo | Não dar ao migrator os direitos do inspector. |
| P2B-D01 | Coordenação até ao fecho administrativo | S09 PREP | DECLARED_APPROVED | PARTIAL offline | E05 | Continuidade real | Não comprovada operacionalmente. |
| P2B-D02 | Adaptadores permanentes separados por identidade | S09 PREP | DECLARED_APPROVED | PARTIAL: interfaces/doubles | E05 | Transporte/atestação | Harness PROV2 efémero não é produto. |
| P2B-D03 | Exclusão de escritores externos além de advisory locks | S09 PREP | DECLARED_APPROVED | PLANNED | Apenas simulação | Fencing/janela | Locks cooperativos não excluem administradores. |
| P2B-D04 | Recuperação administrativa independente antes da migração | S09 PREP | DECLARED_APPROVED | PLANNED | S08 reconhece ausência | Backup/console/restauro | Acesso bootstrap não prova recuperação. |
| P2B-D05 | Decisão separada de DML/FOR UPDATE | S09 PREP; evolução D05 em S10 | DECLARED_APPROVED | PARTIAL: matriz offline | E03/E07 | Verificação real ORM/ACL | Inventário apenas consulta em D05; grants não aplicados por esta baseline. |
| AUTH-03 | Executor isolado e mutações bloqueadas | S11 | Contrato preservado por H05 | PARTIAL; BLOCKED | E09 operation_gate | Bundle íntegro/autorização própria | Manifesto divergente; não regenerar nesta etapa. |

## G4 e manifesto I2

Os títulos G4D abaixo são sínteses de H01, não o original G4-DESIGN com todas as
condições. Aprovação referida por humano: `HUMAN_REFERENCE`; original integral
`SOURCE_NOT_LOCATED`. Não promover resumos a aprovação de implementação/ambiente.

| ID original | Título / descrição verificável | Fonte | Aprovação | Implementação | Evidência | Dependências | Divergências / lacunas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G4D-01 | VM Proxmox exclusiva; ensaios sem NIC | H01 | HUMAN_REFERENCE | PLANNED | E08 identidade | Ambiente próprio | Não é STAGING/PROD; criação não autorizada. |
| G4D-02 | Ubuntu 24.04 amd64, PG16, Python3.12 e hashes | H01 | HUMAN_REFERENCE | PARTIAL: contratos | E08 | Artefactos/validação libpq | Sem instalação comprovada; libpq17+ por validar. |
| G4D-03 | Instalador independente até f066/b12, sem f067 | H01 | HUMAN_REFERENCE | ABSENT instalador | E04/E08 | Revisão offline/identidade | Não selecionar head nem desbloquear AUTH-03. |
| G4D-04 | Migrator temporário e owner NOLOGIN | H01 | HUMAN_REFERENCE | PARTIAL: tipos | E08 | Fecho/ownership | Inventário real e revogação por demonstrar. |
| G4D-05 | Matriz D05 mínima e inventário integral | H01/S10 | HUMAN_REFERENCE | PARTIAL offline | E07/E08 | ORM/ACL/defaults reais | Sem grants automáticos. |
| G4D-06 | Manifesto e aprovação independente | H01 | HUMAN_REFERENCE | PARTIAL: registos | E08 | I2/fontes originais | H01 refere duas camadas; evolução I2 refere três. Não fundir por inferência. |
| G4D-07 | Harness real separado de OfflineExecutor | H01 | HUMAN_REFERENCE | ABSENT harness real | E07/E08 | Transporte e revisão | Double não produz evidência operacional. |
| G4D-08 | Atestação suplementar vinculada às sessões | H01 | HUMAN_REFERENCE | PARTIAL: identidades | E08 | Sessões reais | Não mudar Q1–Q16 silenciosamente. |
| G4D-09 | TLS PG verify-full, CA exclusiva e identidade física | H01 | HUMAN_REFERENCE | ABSENT transporte real G4 | E08; E06 sem TLS explícito | PKI/atestação | Sem fallback; fábrica da app não satisfaz G4 só por construir URL. |
| G4D-10 | Deadline e supervisor externo; EOF/cleanup para PASS | H01 | HUMAN_REFERENCE | PARTIAL: limites lógicos | E08 | Limites medidos/supervisor | Não há garantia física nem supervisor real. |
| F02 | Tipos, estados, identidades e fronteiras I1 | H02 | HUMAN_REFERENCE; preservação H05 | IMPLEMENTED no âmbito I1 | E08 | Revisões futuras autorizadas | execution_boundary recusa execução mesmo com claims. |
| I2-D01 | Manifesto canónico, três camadas e digests | H03 | HUMAN_REFERENCE; original SOURCE_NOT_LOCATED | PLANNED | Referência em pedido | F03 e schema integral | Não fabricar formato. |
| I2-D02 | Autoridade externa Ed25519 e confiança independente | H03 | HUMAN_REFERENCE; original SOURCE_NOT_LOCATED | PLANNED | E08 só contém registos | F04/trust root | Objetos Python não autenticam aprovação. |
| I2-D03 | Máximo inicial 15 minutos, revogação e uso único | H03 | HUMAN_REFERENCE; original SOURCE_NOT_LOCATED | PLANNED | Referência em pedido | Persistência/relógios | Sem autorização operacional implementada. |
| I2-D04 | cryptography e distribuição reproduzível offline | H03 | HUMAN_REFERENCE; original SOURCE_NOT_LOCATED | PLANNED | Referência em pedido | Bundle aprovado | Nenhuma dependência instalada por DEV-03B. |
| I2-D05 | G4-WF1, U64BE e SHA-256 | H03 | HUMAN_REFERENCE; original SOURCE_NOT_LOCATED | PLANNED | Referência em pedido | Spec integral/canonicalização | F03/F04/F17 não localizados. |
| I2-S01 | Estrutura das três camadas | H04 | HUMAN_REFERENCE; original SOURCE_NOT_LOCATED | PLANNED | Referência em pedido | Schemas originais | Não substituir por estrutura inventada. |
| I2-S01-L01-D01 | Regras L01-D01-01–14 | H04 | HUMAN_REFERENCE; original SOURCE_NOT_LOCATED | Não verificável integralmente | Só referência | Texto aprovado | Não reconstruir as 14 regras. |
| I2-S01-L02 | Regras L02-D01–12 | H04 | HUMAN_REFERENCE; original SOURCE_NOT_LOCATED | Não verificável integralmente | Só referência | Texto aprovado | L02 permanece aberta. |
| I2-S01-L02-SPEC-D01 | Regras SPEC-D01-01–14 | H04 | HUMAN_REFERENCE; original SOURCE_NOT_LOCATED | Não verificável integralmente | Só referência | Texto aprovado | Não reconstruir as 14 regras. |

## Lacunas preservadas: nenhum encerramento nesta baseline

O pedido H05 manda preservar **as 28 lacunas G4/L02**. A enumeração original com
os seus 28 IDs/descrições não foi localizada nas fontes consultadas:
`SOURCE_NOT_LOCATED`. O conjunto de 28 mantém-se **OPEN**, sem exclusões, fusões,
renumeração ou afirmação de resolução. A cardinalidade é a comunicada por H05,
não uma contagem independente. Não foram inventadas 28 entradas para preencher a
ausência. Recuperar a lista é condição para validação item a item e fecho documental.

As sete famílias abaixo são identificáveis em H04. **Não substituem as 28 lacunas**,
nem permitem deduzir correspondência de quatro lacunas por família.

| ID original | Descrição verificável em H04 | Estado / dependência |
| --- | --- | --- |
| L02-R01 | Schemas e variantes de objetos | OPEN; contratos integrais e diferenças por família. |
| L02-R02 | Enums e domínios PostgreSQL | OPEN; distinguir universo PG de subconjunto G2 observado. |
| L02-R03 | Identidade das rotinas | OPEN; argumentos, overloads, identidade lógica/física. |
| L02-R04 | Extensões | OPEN; cobertura integral e proveniência. |
| L02-R05 | Dependências e instalação | OPEN; classes, grafos e cadeias posicionais. |
| L02-R06 | Fronteira G2/G4 | OPEN; evidência sintética não satisfaz harness real. |
| L02-R07 | Rastreabilidade documental | OPEN; originais G4-DESIGN/HO1/HO2, T01–T36 e G4-WF1 não consolidados no repo. |

Também permanecem abertas as lacunas residuais DAT-01–DAT-10 de S02, respeitando
as subdecisões já declaradas aprovadas: JSONB, reconciliação, transições,
cardinalidades, domínios físicos restantes, métricas/retenção, limpeza Discovery,
Outbox física, grupos dinâmicos e cálculo/aplicação de políticas. A revisão
conceptual declarada concluída em S02 não prova conclusão física ou funcional.

## Divergências e condições para revisão humana

1. DAT-05A usa livenet; E06 recusa essa base no perfil dedicado. Clarificar âmbito
   lógico/ambiente sem renomear destinos nem alterar validações por inferência.
2. S02 §4 refere diários por três anos; DAT-06B tem outra tabela. Consolidar
   precedência com fonte/aprovação, sem escolher valores nesta baseline.
3. E04 contém f067; E06/E07 e G4 exigem f066/b12 e excluem f067. A divergência
   mantém-se aberta; não executar upgrade head nem ampliar revisões aceites.
4. S08 R3 antecede PROV1/PROV2; roles ausentes em R3 não são o último registo.
   PROV2 continua histórico, sem security instalado/DML app, nem atestação atual.
5. VAL1 reprovou IMP1; FIX1/VAL1-R2 confirmam apenas correção offline. Não
   transformar aprovação offline em autorização de migração.
6. S10 conserva limites, snapshots separados, TOCTOU, latches em memória,
   manifesto físico/PG16/cleanup/recuperação e revisões independentes pendentes.
7. Manifesto AUTH-03: última comparação estática DEV-03A, 31 entradas para 51
   fontes, 20 omissões, quatro hashes divergentes. Sem regeneração/contorno.
8. S13/README apresentam tecnologias previstas sem distinguir implementação.
   O estado corrente é separado no [estado F0](../specifications/f0/implementation-status.md);
   os textos históricos continuam preservados.

Detalhes de runtime e ambientes propostos em [runtime](platform-runtime.md) e
[ambientes](environments.md); entregas em [roadmap](../roadmap/platform-roadmap.md).
Nenhuma proposta nestes documentos passa a aprovada apenas por estar escrita.

## Atualização vinculativa DEV-08B — persistência e reconciliação AUTH-03

Data de formalização: 2026-10-25, progbox.
Fonte humana primária: pedido DEV-08B desta conversa, anexo
`9e646608-e14d-4575-8d04-84eaa4ca6301/Pasted text.txt`, Missão e §§2–5.
O pedido confirma explicitamente a aprovação DEV-08-D01/D02/D03 com as
restrições da DEV-08. O anexo é externo ao checkout; não substitui originais
históricos não localizados. O texto anterior permanece integral como histórico.

| ID | Decisão e âmbito aprovado | Estado de implementação / evidência | Limites e pendências |
| --- | --- | --- | --- |
| DEV-08-D01 | APROVADA: DEV livenet_v2_dev, STAGING livenet_v2_staging, PROD livenet_v2_prod; isolamento completo entre ambientes e v1; identidade atestada além do nome; verify-full; papéis separados; schemas iniciais inventory/audit/security | FORMALIZED_DOCUMENTATION_ONLY; adenda DAT-05A preparada, sem configurações operacionais alteradas | Identidades/colisões e grants reais ainda por validar; nenhuma criação de base/role autorizada |
| DEV-08-D02 | APROVADA: MVP f066a01a7230 + security b12b01a7230; AUTH-03 isolado f067a01a7230, security não aplicada por defeito; grafos/ledgers preservados | FORMALIZED_DOCUMENTATION_ONLY; grafos e ordem futura documentados | Não reconcilia código de perfis automaticamente, não muda gates/readiness, não autoriza head/stamp/DDL |
| DEV-08-D03 | APROVADO O PROCESSO FASE 1: revisão individual e preparação de candidato completo fora dos gates; segunda aprovação de bytes/digests continua obrigatória | REVIEW_CANDIDATE_NOT_APPROVED; 25 divergências revistas, 52 fontes propostas | Nove inclusões locais requerem aceitação explícita; manifesto ativo intacto; imagem/security fora do âmbito exigem atestação complementar |

Referência normativa atual: [contratos DEV-08B](../specifications/f0/dev08b-persistence-contracts.md).
A adenda no final de [DAT-05A](../specifications/f0/data-model.md) altera somente
nome por ambiente e materialização inicial. O [relatório DEV-08](../operations/dev08-persistence-decisions.md)
mantém-se como proposta histórica; a aprovação específica é rastreada nesta atualização.

Resultado AUTH-03 atual: 31 entradas para 52 fontes, 21 ausências, quatro hashes
divergentes e zero excedentes. Esta comparação substitui apenas as contagens
históricas DEV-03A neste registo; não transforma falhas anteriores em resolvidas.
[Relatório/matriz DEV-08B](../operations/dev08b-persistence-formalization.md) e
[candidato NÃO APROVADO](../operations/dev08b-auth03-candidate.NOT-APPROVED.json).

F02/G2/G4, AUTH-03, gates operacionais, cadeias Alembic, HTTPS/CSRF/proxy/cookies,
LAN-only, privilégios mínimos e factory sem escrita PostgreSQL permanecem.
Continuam OPEN os originais D-01–D-52/16 capítulos e as 28 lacunas G4/L02.
A separação aprovada f066/f067 resolve o destino arquitetural por perfil;
a implementação de perfis e autorizações concretas continua pendente.
Não se declara readiness real, recuperação independente ou integração persistente operacional.

<!-- BEGIN AUTH-BOOT-02-R1 CONSOLIDACAO-B -->
## AUTH-BOOT-02-R1 — Adenda CONSOLIDAÇÃO-B

**Estado: CANDIDATO DOCUMENTAL PARA REVISÃO HUMANA — bytes não aprovados.**

O pedido humano CONSOLIDAÇÃO-A, anexo
`51c3491c-5df2-493e-94aa-73be4ba3a6dd/Pasted text.txt`, declara R1-D01 a
R1-D10 aprovadas arquiteturalmente na conversa. CONSOLIDAÇÃO-B, anexo
`a80a6b23-f866-404e-83e1-120d9b1fbf06/Pasted text.txt`, autoriza exclusivamente
três novos documentos e esta adenda, sem aprovação antecipada dos bytes.

- [Consolidado AUTH-BOOT-02-R1](auth-boot-02-r1.md): dez decisões, parâmetros e limites.
- [Registo de lacunas](auth-boot-02-r1-gaps.md): R1-GAP-001 a R1-GAP-020, todas ABERTA.
- [Rastreabilidade](auth-boot-02-r1-traceability.md): fontes, proveniência parcial,
  contratos, estados e critérios de aceitação.

As decisões humanas explicitamente fornecidas têm precedência sobre as escolhas
candidatas da [proposta histórica](proposals/auth-boot-02-r1.NOT-APPROVED.md).
O draft R1-DRAFT-1, SHA256
`ec4e3afa6a6a1be5f1caaac18ec800442dfb8daddd64244f07cf4b6e32b4a4b6`,
fica intacto, incluindo PENDENTE e NOT-APPROVED. Este candidato documenta a
aprovação arquitetural informada; não constitui aprovação documental final.

Os textos integrais e datas individuais de aprovação não estão integralmente
recuperados. Não se inventam transcrições, datas ou assinaturas. Os anexos estão
fora do checkout. O original AUTH-BOOT-02 continua não localizado; não existe
equivalência histórica demonstrada com R1, I2, G4-WF1 ou F03/F04.

**BLOQUEADORES DE ATIVAÇÃO:** R1-GAP-001 (exclusividade durável de iniciação) e
R1-GAP-002 (ordenação de revogação/expiração com primeiro efeito PostgreSQL).
Uma consulta imediatamente anterior ao SQL não demonstra a segunda condição.
Persistem os restantes bloqueadores e parâmetros abertos do registo R1.

### Referência temporal AUTH-03 — sem reescrever o histórico

As comparações anteriores deste registo e do contrato AUTH-03 referem 31 entradas
e divergências nas respetivas etapas. [DEV-08D](../operations/dev08d-auth03-application.md),
§§Aprovação/Preflight/Identificadores, documenta a aprovação e aplicação posterior
do manifesto de 52 fontes. [ATTEST03](../operations/dev09-attest03-reconciliation.md),
§Integridade, regista 52/52. A leitura inicial da CONSOLIDAÇÃO-B confirmou 52/52,
com manifesto SHA256
`4819c697b7d12f7ab5cbb1fdfa9cf4c3fd0e98e93b53a60337296cc84036fc29`.
Isto contextualiza temporalmente as contagens anteriores; não altera fontes,
hashes, manifestos, candidatos ou evidências congeladas.

Não se encerram as 28 lacunas G4/L02 nem se fabrica a sua enumeração.
Preservam-se f066/f067 e implementação pendente por perfil, cadeias Alembic,
privilégios mínimos, rede interna, HTTPS/CSRF/proxy/cookies e gates.
Fonte aprovada, ficheiro aplicado, validação offline e autorização operacional
não são equivalentes. AUTH-03, F02, G2 e G4 permanecem fechados.

Sem implementação, provisionamento, chaves, testes aplicacionais, builds,
serviços, SQL, migrações, backup/restauro, staging, commit, push ou DEV-09B.
Revisão humana dos bytes continua necessária.
<!-- END AUTH-BOOT-02-R1 CONSOLIDACAO-B -->

<!-- BEGIN AUTH-BOOT-02-R2 CONSOLIDACAO-1 -->
## AUTH-BOOT-02-R2 — Baseline candidata de admissão lógica

Data de consolidação: 2026-10-27. A data identifica esta adenda, não a aprovação original.

**Estado: C1–C7 APROVADAS DOCUMENTALMENTE COMO BASELINE CANDIDATA, incluindo os riscos e a separação de versão. Consolidação dos bytes para revisão documental.**

Fonte: conversa [Planeamento das lacunas](chatgpt-conversation://6adfbb17-6350-83ed-9daa-650bf8ad109a), texto humano R1-CONTRACT-REV-01 na mensagem `408b84ef-5a83-4255-9bca-3bb79ae7ae58` e aprovação humana na mensagem `9daf5fec-5456-4d05-b296-483b9a1b3260`. O pedido atual autoriza exclusivamente a consolidação documental no repositório.

> Aprovo documentalmente C1–C7 como baseline candidata AUTH-BOOT-02-R2, incluindo expressamente os riscos identificados e a separação de versão. Não autorizo implementação, alteração operacional, abertura de gates ou encerramento de GAP-001/002.

- [Baseline candidata AUTH-BOOT-02-R2](auth-boot-02-r2.md): cláusulas integrais C1–C7, matriz de alterações, critérios de demonstração e riscos abrangidos pela aprovação documental.
- [Rastreabilidade R2](auth-boot-02-r2-traceability.md): fontes, diferenças explícitas face a R1, acompanhamento das lacunas e hashes dos documentos R1 preservados.

R2 muda expressamente a fronteira temporal e de revogação de R1-D04/D05/D08 para a avaliação lógica de admissão em `A`, condicionada a confirmação durável e ordenada com revogação. Confirmação e efeito podem ocorrer depois do prazo; revogação posterior não retira retroativamente a admissão. A fonte aprova documentalmente os riscos identificados, incluindo ausência de limite temporal até ao efeito, consumo sem execução, ausência de cancelamento garantido e dependência de continuidade/invalidação de instâncias.

A separação de versão foi aprovada documentalmente. C7 recomenda um perfil R2 com `protocol_version="2"` e domínio de assinatura próprio, preservando os 25 nomes de campos, JCS/UTF-8 e Ed25519 puro. A codificação concreta e os schemas de evidência exigem aprovação específica; nenhum domínio concreto é inventado. Não há fallback entre versões ou alteração dos parsers/executores atuais.

R1, a proposta histórica, a rastreabilidade e os critérios originais de GAP-001/002 mantêm-se preservados. A mudança não é interpretação retroativa nem demonstra satisfação do requisito R1 relativo ao primeiro efeito PostgreSQL. GAP-001/002 permanecem **ABERTAS e BLOQUEADORES DE ATIVAÇÃO**. As restantes lacunas R1 e G4/L02 continuam abertas; contratos ausentes mantêm `SOURCE_NOT_LOCATED`.

AUTH-03, F02, G2 e G4 permanecem fechados. DEV-09B continua não autorizada. Não há autorização de implementação, infraestrutura, laboratório ou alteração operacional. O eventual primeiro âmbito de implementação indicado pela fonte continua limitado ao UPDATE fixo de laboratório e requer autorização posterior; Alembic, DDL e operações administrativas não ficam abrangidos automaticamente.

Esta adenda não aprova antecipadamente os bytes consolidados nem substitui decisões próprias sobre implementação, ensaios e ativação. Sem código executável, infraestrutura, manifestos, evidências congeladas, commits ou push alterados por esta consolidação.
<!-- END AUTH-BOOT-02-R2 CONSOLIDACAO-1 -->
