# LiveNet v2 — Roadmap incremental da plataforma

DEV-03B, 2026-10-25. **PROPOSTA PARA REVISÃO HUMANA.** Não inicia DEV-03C, não
autoriza código, instalações, builds, CI/CD, serviços, migrações ou provisionamento.

Referências: [decisões e lacunas](../architecture/decision-register.md),
[ambientes](../architecture/environments.md), [runtime](../architecture/platform-runtime.md),
[estado atual](../specifications/f0/implementation-status.md).

## Ordem e critérios comuns

Os números abaixo são rótulos de entregas propostas, não novos IDs de decisões
aprovadas nem substitutos das fases F0–F5. A segurança/recuperação é pré-requisito
de ativação, mesmo quando aparece também como entrega de consolidação posterior.
As 28 lacunas G4/L02 continuam OPEN; a enumeração original não foi localizada,
não se presume correspondência com sete famílias e não se encerra qualquer item.

Cada entrega requer escopo aprovado, fonte/versão identificável, evidência de
aceitação, limites, procedimento de reversão e registo das lacunas ainda abertas.
Testes offline, amostras históricas e validação atual são evidências distintas.

| Entrega proposta | Dependências de entrada | Resultado e critérios de aceitação | Riscos e limites |
| --- | --- | --- | --- |
| 0. Rever baseline e originais | DEV-03A/B; fontes e aprovações originais | Recuperar D-01–D-52/16 capítulos, lista das 28 lacunas e textos G4/I2; decidir bloqueios por tarefa; aprovar precedência sem fechar lacunas por inferência | SOURCE_NOT_LOCATED impede alegar conformidade integral; esta baseline não substitui originais. |
| 1. Integração operacional da aplicação | DEV-02; topologia host/contentores e destino aprovados; dependências/artefactos revistos | Preparar imagem dedicada, config/segredos externos e ingress compatível; testar sem startup DDL/contas; checker ausente mantém 503; validar servidor/config em ensaio autorizado | Dockerfile antigo não inclui DEV-02; loopback/Caddy incompatíveis; nenhuma build ou ativação autorizada agora. |
| 2. Autenticação e inventário utilizáveis | Segurança PostgreSQL/ACL, recovery independente, transporte e migrações autorizados, checker real aprovado e HTTPS validado | Login/me/logout/expiração, throttling/CSRF, lista/filtros/paginação/detalhe e negativa de acessos comprovados em STAGING; persistência/durabilidade e falhas demonstradas | f066/f067 e AUTH-03 continuam bloqueios; D05 só consulta, escrita de recursos exige decisão própria; nenhuma credencial bootstrap como runtime. |
| 3. Descoberta e reconciliação | DAT-02/03/07, contratos de fontes/alvos/observações aprovados; base assíncrona mínima | Primeiro adaptador real com proveniência, observações separadas, candidatos/conflitos e aprovação auditada; testes contra alvo controlado; repetição não duplica identidades | Alcance de rede/segredos; IP/MAC/nome não são UUID; sem fusão automática não aprovada. |
| 4. Monitorização e histórico | DAT-06, tipos/unidades/estado/retenção consolidados; workers/scheduler e permissões mínimas | Primeiro check real, estado normalizado e freshness, histórico/métrica persistidos, recuperação de tarefas e retenção/agregação testados | Estado administrativo não é online; conflito de retenção permanece até decisão; sem escolher TSDB/partições por defeito. |
| 5. Alertas e notificações | Checks/estados confiáveis; modelo de regras, Outbox/eventos e canais aprovados | Abertura/recuperação/deduplicação e entrega auditáveis; consumidores idempotentes e retries limitados; teste de canal em âmbito próprio | Sem notificações externas sem autorização; ruído/duplicação e entrega incerta; não é SIEM D-52. |
| 6. Operação estável em VM dedicada | Entregas funcionais aceites, capacidade e segurança revistas | Compose de produção integrado, redes/destinos aprovados, logs/métricas e alertas da plataforma; manutenção, restart e falhas ensaiados; rollback de aplicação compatível e recovery de dados comprovados | Uma VM é ponto de falha; volumes não são backup; privilégios mínimos e isolamento do v1/ensaios mantidos. |
| 7. CI/CD e recuperação consolidados | Artefactos/locks, critérios STAGING, política de migração/segredos e RPO/RTO aprovados | Workflows/registry, versão/digest/proveniência, promoção do mesmo artefacto, testes por categoria, approvals e rollback definidos; backup/restauro e desastre exercitados | Preparar testes/artefactos antes das primeiras promoções; nunca esperar esta entrega para cumprir recovery pré-migração; CI não desbloqueia gates. |
| 8. Kubernetes multi-nó | Runtime VM recuperável, contratos concorrentes, dados/filas/sessões e confiança de ingress aprovados | Manifests reproduzíveis, réplicas sem estado local exclusivo, scheduler coordenado, storage e BD/Redis decididos, probes compatíveis; ensaiar perda de nó e promoção/rollback sem migrações concorrentes | K8S não cria HA da BD nem substitui backup; segredos/UID, IPs de proxy e identidades físicas não podem ser relaxados. |

A base assíncrona das entregas 3–5 inclui definir o papel de Redis, tarefas/estados,
idempotência, concorrência, scheduler e Outbox quando a publicação fiável o exigir.
Essas dependências são implementações futuras, não componentes já disponíveis.
SSE só entra após contrato de eventos, autorização/replay e distribuição aprovado.

## Retoma técnica recomendada — apenas proposta

Próximo pacote candidato: **fechar o desenho da topologia dedicada e do artefacto
DEV-02**, antes de qualquer instalação/ativação. A DEV-03C, se autorizada, deve
resolver documentalmente ingress no host versus contentores, bind/peer, origem
por ambiente, transporte PostgreSQL e montagem de segredos. Não escolher uma
alternativa como aprovada nesta DEV-03B.

Uma implementação posterior, expressamente autorizada, poderá preparar imagem
dedicada e testes offline de configuração/empacotamento sem tocar o percurso
antigo. Critérios propostos: imagem inclui entrypoint/config corretos, não contém
segredos, arranque não cria engine/DDL/contas, APIs antigas mantidas, health
preservado e ready 503 sem checker. Execução do servidor exige escopo de teste
próprio; testes estáticos não demonstram integração de rede.

Ativação funcional depende ainda dos gates aprovados de PostgreSQL, implantação
security, ACL runtime, primeira conta e checker real. Não resolver f066/f067,
AUTH-03, F02, G2 ou G4 como parte incidental de embalagem/deployment. Determinar
explicitamente que lacunas bloqueiam cada ensaio; nenhuma recebe baixa automática.

## Evidências de saída e reversão por categoria

| Categoria | Evidência exigida em etapa futura | Estratégia a aprovar |
| --- | --- | --- |
| Código/configuração | Diff restrito, testes apropriados e fontes preservadas | Retirar só ficheiros/alterações da entrega, preservando trabalho anterior. |
| Imagem/release | Digest, dependências, proveniência e ensaio STAGING | Voltar a artefacto compatível; não presumir reversibilidade do schema. |
| Dados/migração/ACL | Identidade, aprovação, duas cadeias/ledgers, janela e resultado reconciliado | Plano específico; security bloqueia downgrade; restauro/revisão corretiva autorizados. |
| Tarefas/eventos | Identidade, estado persistido, retries e deduplicação | Reconciliação/compensação aprovada, não repetição cega de operação incerta. |
| VM/K8S/storage | Recuperação e falhas controladas demonstradas | Runbooks de indisponibilidade/restauro; nunca destruir volumes como rollback de app. |

## Pendências que acompanham todas as entregas

- Originais D-01–D-52 e 16 capítulos; 28 lacunas G4/L02, L02-R01–R07 e
  textos I2/L01/L02/SPEC; preservar IDs e condições quando recuperados.
- Manifesto AUTH-03 divergente, f066/f067, matriz D05/SQL ORM/ACL reais,
  snapshots/TOCTOU e limites de transporte/supervisor ainda pendentes.
- Exclusividade externa e recuperação administrativa independente; não usar
  advisory lock ou login bootstrap como prova suficiente.
- RBAC grupo/recurso, JSONB, reconciliação, regras/políticas, retenção e limpeza,
  Outbox, SSE, assíncrono, observabilidade e critérios completos F0.
- DAT-05A/nome da base e políticas de retenção divergentes; revisão explícita.

As pendências podem ser tratadas por incrementos delimitados, mas só evidência
e aprovação específicas permitem encerrá-las. Terminar esta baseline não inicia
DEV-03C, implementação ou operação.
