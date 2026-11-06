# LiveNet v2 — Runtime: atualização DEV-05A

Data: 2026-10-25. Fonte humana: pedido DEV-05A, anexo
`adee713c-cd23-4bfd-a10e-c48de86c556e/Pasted text.txt` §1/§4 desta conversa.
Decisão aprovada [DEV-05A-D01](decision-register.md): acesso exclusivamente interno
ao laboratório em DEV/STAGING/PROD-VM/PROD-K8S. Opção A aprovada em DEV-03C-D01,
conforme pedido DEV-04; os artefactos são preparação offline, não operação.

## Fronteiras aprovadas versus enforcement pendente

Somente redes internas explicitamente autorizadas podem alcançar UI/API por
HTTPS. Não admitir IP público, encaminhamento/port forwarding Internet, Cloudflare
Tunnel ou equivalentes. Em K8S, ingress interno sem LoadBalancer público.
Backend/PG/Redis/auxiliares não são publicados externamente. Saída tem aprovação
separada e não autoriza entrada. Exceções só pelo responsável em decisão explícita.

O percurso aprovado em conceito é cliente da LAN autorizada → firewall/ingress
interno → Caddy → backend privado → PostgreSQL privado. Firewall/routing/VPNs e
ausência de túneis ainda não foram demonstrados. RFC1918/DNS interno não bastam.
Controlos de rede não substituem autenticação, autorização, auditoria, CSRF,
cookies ou expiração/revogação da sessão.

TrustedProxy confere peer e headers do Caddy; **não impõe ACL de redes browser**.
Nem Caddy hostname/TLS nem a origem Flask distinguem um cliente Internet que
por erro tenha alcançado o ingress. Recusar esse percurso é responsabilidade
do desenho LAN-only completo, por validar sem enfraquecer o middleware.

## Estado real do pacote DEV-04

| Componente | Implementação existente | Validação disponível / limite |
| --- | --- | --- |
| Imagem dedicada | Dockerfile opt-in, factory DEV-02, Gunicorn e UID 10001 | Descrição estática; sem build/import do servidor. Base/digests e wheels pendentes. |
| Contexto | Ignore específico e COPY app | Revisão R02 identifica inclusão recursiva mais ampla que Python; sem correção e sem prova de ausência de segredos no contexto efetivo. |
| Servidor | Config própria com bind no namespace, workers sync e forwarded desativado | Mantém TrustedProxy; parsing real, sinais, carga e SSE não validados. |
| Compose | web edge/api; backend api/data; db data; volumes separados | Só HTTPS é publicável pelo descriptor, porém endereço ainda não valida LAN. Os três entrypoints exit 78 continuam. |
| Caddy | UI/API mesma origem, remoção e reconstrução declarada de headers | Oráculo Python demonstra compatibilidade pretendida, não execução Caddy. Nenhuma ACL cliente LAN-only implementada. |
| Testes | 570 testes offline reportados em DEV-04 | Não repetidos; checks de texto/JSON e TestClient não validam matcher Docker, parser Caddy, sockets ou isolamento. |
| Operação | Nenhuma ativação nesta revisão | Sem validação operacional atual; recursos/estado de serviços não consultados. |

Os sete artefactos técnicos DEV-04 estão preservados; só a documentação
operacional autorizada recebe adição. Detalhes e severidades no
[relatório documental DEV-04/05A](../operations/dev04-dedicated-integration.md).

## Dependências antes da primeira integração

Parsing nativo local só numa DEV-05B autorizada e isolada. Build é outra
capacidade, bloqueada para o contexto real enquanto R02 não for tratado por
alteração autorizada e prova de exclusão de ficheiros indevidos. Confirmar
imagens, dependências, acesso de saída, ambiente sintético, temporários e output
sanitizado; não montar configurações/segredos/volumes reais nem contactar PG.

Ativação depende de enforcement LAN-only e parâmetros coerentes: IPAM/peer/JSON,
roles distintas, UID e montagens, TLS/identidade PostgreSQL, recuperação
independente e aprovação de migrações/conta inicial/privilégios. Readiness real
continua ausente/503; health não prova prontidão. Nenhuma probe recebe bypass.
F02/G2/G4 e gates, AUTH-03/manifesto, f066/f067, 28 lacunas G4/L02 e restantes
originais não localizados permanecem abertos. Nenhum dado é provisionado aqui.

Runtime futuro de workers/scheduler/Redis, Outbox/SSE, descoberta, monitorização,
alertas e observabilidade continua parcial/ausente conforme tabela histórica.
Todos os listeners futuros herdam LAN-only; egress de coletores não autoriza
entrada Internet. Multi-nó exige confiança de ingress, coordenação e storage
revistos; Kubernetes não remove estas fronteiras nem requisitos de recuperação.

## Runtime anterior preservado — baseline DEV-03B

O texto seguinte conserva o estado e propostas originais, agora sujeito à
restrição vinculativa LAN-only. Nenhuma proposta histórica passa a aprovada por
estar aqui; apenas DEV-03C-D01 e DEV-05A-D01 têm os âmbitos humanos acima.

# LiveNet v2 — Runtime lógico e implementação

Baseline DEV-03B, 2026-10-25; análise estática para revisão humana, sem operação.
Referências: [decisões/fontes](decision-register.md), [ambientes](environments.md),
[estado de implementação](../specifications/f0/implementation-status.md).

## Estado dos componentes

Implementado descreve código, parcial um subconjunto, ausente ausência de
implementação identificada, apenas previsto uma responsabilidade futura. Nenhuma
linha significa validado operacionalmente no ambiente atual.

| Componente | Estado | Código/documento verificável | Limite / dependência |
| --- | --- | --- | --- |
| Frontend React/TS/Vite | Implementado para consulta | [App](../../frontend/src/App.tsx), [README](../../frontend/README.md) | Login/sessão/lista/filtros/paginação/detalhe; sem UI de escrita/descoberta/monitorização. |
| Backend Flask | Parcial como plataforma | [factory](../../backend/app/__init__.py), [dedicada](../../backend/app/dedicated.py) | Módulos inventory/security/audit/health; restantes domínios ausentes. |
| WSGI dedicado | Implementado como preparação | [entrypoint](../../backend/dedicated_wsgi.py), [config Gunicorn](../../backend/gunicorn_dedicated.conf.py), [DEV-02](../operations/dev02-dedicated-backend.md) | Sem ativação; Dockerfile antigo não o inclui. Gunicorn não instalado na observação DEV-02, não reinspecionado aqui. |
| PostgreSQL e ORM | Parcial | [database](../../backend/app/core/database.py), [model registry](../../backend/app/core/model_registry.py), [Compose](../../compose.yaml) | Modelos/cadeias existentes; estado/runtime atual não consultado. |
| Autenticação/sessões | Implementado no código | [service](../../backend/app/security/service.py), [models](../../backend/app/security/models.py) | Persistência/ACL/conta inicial/HTTPS por validar no destino autorizado. |
| Autorização | Parcial | [access](../../backend/app/security/access.py) | Reader/editor globais; sem âmbito grupo/recurso. |
| Inventário | Parcial | [routes](../../backend/app/inventory/routes.py), [service](../../backend/app/inventory/service.py) | GET lista/detalhe e POST criação; sem edição/eliminação e APIs dos restantes modelos. D05 só atesta consulta. |
| Descoberta/reconciliação | Ausente, prevista | DAT-02/DAT-07, [modelo conceptual](../specifications/f0/data-model.md) | Identificadores/proveniência físicos não constituem motor Discovery. |
| Monitorização/métricas | Ausente, prevista | DAT-06, modelo conceptual | Sem checks, execuções, estado operacional ou séries implementados. |
| Alertas/notificações | Ausente, previsto | F2 no [baseline](../specifications/f0/f0-baseline.md) | Regras, deduplicação, escalonamento e entrega por definir. |
| Auditoria | Implementado base/serviço; integração parcial | [audit service](../../backend/app/audit/service.py), [f066](../../backend/migrations/versions/f066a01a7230_create_audit_events_baseline.py) | Chamador controla transação; instrumentação não universal, retenção não operacionalizada. |
| Celery workers | Ausente, previsto | Baseline F0/README | Sem app Celery, tarefas ou serviço identificados. |
| Celery scheduler | Ausente, previsto | Arquitetura lógica pedida em DEV-03B | Sem Beat/scheduler implementado nem algoritmo de coordenação aprovado. |
| Redis | Ausente, previsto | Baseline F0/README | Sem serviço, papel exato, durabilidade ou política de acesso implementados. |
| Transactional Outbox | Ausente, previsto | DAT-08A | Sem tabela/publicador; independente de audit, entrega at-least-once/idempotência declaradas. |
| SSE | Ausente, previsto | Baseline REST/SSE | Sem endpoint/canal; replay, autorização, desconexões e distribuição por definir. |
| Proxy/ingress | Parcial | [Caddyfile](../../infra/web-dev/Caddyfile), [TrustedProxy](../../backend/app/trusted_proxy.py) | Caddy serve estáticos; API 503; middleware não é prova de rede/ingress reais. |
| Health/readiness | Parcial | [health](../../backend/app/health/routes.py), [ready](../../backend/app/readiness.py), [G2](../../backend/app/readiness_postgres/adapter.py) | Liveness sem BD; readiness 503 sem checker; apenas executor offline G2. |
| Observabilidade | Parcial na fundação, plataforma ausente | Audit e health acima; [config WSGI](../../backend/gunicorn_dedicated.conf.py) | Sem métricas/exporters/dashboards/alertas identificados; log de acesso WSGI desativado. Audit não substitui diagnóstico. |
| CI/CD, backup e rollback completo | Ausentes como percurso integrado | Documentos de preparação/Compose | Sem workflows, promoção GHCR ou restauro de plataforma demonstrados localmente. |

## Percursos existentes e incompatibilidades de integração

O percurso anterior é `backend/wsgi.py` → `create_app`; Dockerfile usa flask run,
Compose backend seleciona development e base original. Continua preservado.
O percurso explícito DEV-02 é `dedicated_wsgi.create_app(config_path)` →
`create_dedicated_app`, configuração privada integral, segurança/proxy ativos,
engine lazy partilhada. Não é escolhido automaticamente pelo percurso anterior.

Caddy serve build React com fallback de UI e recusa API com JSON 503. Não existe
o percurso integrado browser→Caddy→factory dedicada→PostgreSQL. A configuração
Gunicorn planeia loopback no host; não é acessível por Caddy noutro contentor
sem desenho de topologia próprio. Não resolver expondo a API publicamente.

Na UI, recuperação/login confirma `/auth/me` e obtém CSRF vinculado à sessão.
Cookies pertencem ao browser/servidor; frontend não substitui RBAC. O cliente
exige mesma origem HTTPS. Vite HTTP local não é ambiente de autenticação válido.

Autenticação persiste sessões, throttles e auditoria; até pedidos de consulta
podem atualizar atividade da sessão. A plataforma não é globalmente read-only
quando o inventário é só de consulta. As permissões runtime precisam de refletir
SQL ORM real, incluindo FOR UPDATE; nada é concedido por este documento.

## Arquitetura lógica prevista — detalhes PROPOSED

O monólito modular conserva APIs/serviços de domínio. PROPOSED: processos web/API,
workers e scheduler usam as mesmas versões dos módulos, com responsabilidades e
privilégios separados. Não criar microserviços só para mudar Compose para K8S.
Nenhuma escolha abaixo altera decisão aprovada ou resolve domínio ausente.

| Fluxo proposto | Responsabilidade e condições a aprovar |
| --- | --- |
| UI → ingress → Flask | Mesma origem HTTPS, headers substituídos pelo ingress confiável, isolamento de acesso direto, sessão/CSRF/RBAC em Flask. |
| Flask → PostgreSQL | Transações curtas, destino/credencial runtime aprovados, timeouts/pool e transporte TLS definidos; sem DDL no arranque. |
| Pedido assíncrono → workers | Pedidos/estados/resultados persistidos, permissões de alvos e idempotência; broker/fila não é única prova de execução. |
| Scheduler → tarefas | Apenas uma emissão lógica por intervalo/escopo, com recuperação/concorrência aprovadas. Não escolher liderança/HA implicitamente. |
| Workers → equipamentos | Adaptadores e egress restritos, timeouts, limites de concorrência, proveniência e segredos por integração. |
| Alteração de domínio → Outbox | Evento e alteração na mesma transação; publicação com retry controlado, consumidores idempotentes e diagnóstico persistente conforme DAT-08A. |
| Outbox → notificações/SSE | Versão de eventos, RBAC, retenção/replay e perda de ligação definidos; canal de distribuição multi-réplica por aprovar. |
| Discovery → candidatos → inventário | Observações separadas do UUID consolidado; conflitos/reconciliação e aprovação, sem fusão automática inferida. |
| Coleta → checks/estados/métricas → alertas | Separar estado administrativo de operacional; persistência, unidades, retenção e condições de alerta aprovadas. |

O papel de Redis como broker/backend/cache, filas/prioridades, política de
ack/retry, durabilidade e comportamento perante perda ficam PROPOSED. Não foi
aprovada dependência adicional Kafka/RabbitMQ nem substituição de PostgreSQL
por TSDB. Critérios quantitativos não localizados não são preenchidos por defaults.

Observabilidade PROPOSED: correlação de pedidos/tarefas, logs sanitizados,
latência/erros, saturação, filas/retries, scheduler, capacidade BD/volumes, estado
de backups e alertas da própria plataforma. Definir retenção/acesso sem expor
segredos. Não confundir alertas sobre equipamentos com alertas da plataforma ou
com SIEM futuro D-52, que permanece fora do MVP inicial.

## Fronteiras que continuam vinculativas

1. AUTH-03 operation_gate bloqueia mutações; M1.2B execution_enabled=False;
   F02 execution_boundary recusa execução. Nenhum ficheiro, token, flag ou pipeline
   novo é autorizado a contornar estas guardas.
2. Alembic aplicacional e security mantêm cadeias/ledgers independentes. Security
   exige conexão externa/transação e bloqueia downgrade. Migrações e alteração
   de ACL são etapas administrativas separadas, nunca efeito do startup.
3. Readiness exige exatamente f066 e b12, evidência tipada fresca, destino e
   privilégios completos; f067 continua divergência aberta, não tolerada por wildcard.
4. G2 mantém Q1–Q16, matriz D05, executor sintético separado e falha fechada.
   Latches/locks em memória e snapshots separados não provam exclusividade ou
   coordenação multi-nó. Supervisor/limites físicos G4 não estão implementados.
5. As 28 lacunas G4/L02 continuam OPEN/SOURCE_NOT_LOCATED quanto à enumeração;
   L02-R01–R07 e originais/revisões pendentes constam do registo central.
6. Health é liveness, não evidência de BD. Probes futuros precisam de desenho
   aprovado compatível com proxy. Não falsificar headers/peers nem instalar
   checker sintético positivo para obter readiness verde.
7. Requisitos de segredos, HTTPS, mesma origem, cookies, CSRF e identidade de
   sessão permanecem. Conta bootstrap não é fallback da aplicação.

## Preparação para múltiplos processos/nós

A persistência de sessões/throttle em PostgreSQL evita que a autenticação dependa
apenas da memória de um worker, mas não comprova escalabilidade/HA. PROPOSED:
validar concorrência, chaves consistentes/rotação, pools agregados, budgets e
cancelamento; evitar retry automático de escrita com commit incerto.

Registos/latches dos ensaios não são locks distribuídos. Instalação/migração e
runtime têm identidades, controlo de execução e estados de recuperação distintos.
Qualquer persistência/coordenação futura deve preservar essas fronteiras,
incluindo aprovação independente, single-use e reconciliação quando exigidos.

Implementação operacional retoma apenas em tarefa delimitada, com aceitação,
reversão e autorizações próprias. Ver [roadmap](../roadmap/platform-roadmap.md).
