# LiveNet v2 — Especificação do Modelo de Dados (F0.28)

**Estado:** Rascunho de consolidação documental — não autoriza criação de tabelas nem migrações.

**Âmbito:** Identificar contratos conceptuais já aprovados e lacunas a resolver antes de implementar modelos SQLAlchemy/Alembic.

## 1. Princípios e fronteiras

- O LiveNet v2 é independente do LiveNet v1. Não se deve copiar automaticamente o esquema anterior.
- A base de dados é PostgreSQL 16; a aplicação usa SQLAlchemy 2.x e Alembic.
- Escala prevista: menos de 100 equipamentos inicialmente, com preparação proporcional para 100–1000, sem penalizar o cenário inicial.
- Distinguir **entidades conceptuais** de **tabelas físicas**. Exceto `inventory.resources`, nomes físicos abaixo não estão aprovados neste documento.
- A F0.28 é apenas documental: sem DDL, migrações, alterações de serviços ou dados.

## 2. Inventário e identidade

### 2.1 Recursos

**Contrato aprovado:** `inventory.resources` representa recursos consolidados com UUID persistente; atributos estruturais relacionais e atributos extensíveis em JSONB sujeito a validação.

**Por definir:** catálogo de tipos, campos estruturais obrigatórios, esquema/versões de validação JSONB, unicidade, índices, ciclo de vida administrativo e regras de eliminação/arquivamento.

### 2.2 Identificadores e proveniência

**Contrato aprovado:** identificação multifonte, identificadores externos, proveniência e reconciliação de observações com recursos persistentes.

**Por definir:** prioridade das fontes, regras de equivalência/colisão, tratamento de alterações de IP/MAC/hostname, unicidade e revisão manual de ambiguidades.

### 2.3 Relações, grupos e etiquetas

**Contrato aprovado:** relações tipadas e direcionadas entre recursos.

**Por definir:** catálogo de tipos, cardinalidades, restrições, histórico temporal, grupos, etiquetas e herança de políticas.

## 3. Discovery

**Contrato aprovado:** observações de descoberta separadas dos recursos consolidados, com histórico e possibilidade de aprovação manual.

**Campos do contrato de adaptador já referenciados:** `external_id`, `resource_type`, `observed_name`, `attributes`, `identifiers`, `relationships`, `observed_at`, `source_id`.

**Por definir:** persistência física das observações, retenção, deduplicação, estados de candidato/aprovação, correlação e tratamento de observações contraditórias.

## 4. Monitoring

**Contrato aprovado:** separação conceptual de checks, execuções, estados e métricas; estados normalizados `up`, `down`, `degraded`, `unknown`, `stale`.

**Parâmetros anteriormente aprovados a reconfirmar na transcrição oficial:** 3 falhas consecutivas para confirmar indisponibilidade; 2 sucessos consecutivos para recuperação; validade da observação de 3 vezes o intervalo de recolha. Retenção: métricas brutas por 30 dias, agregados horários por 12 meses e agregados diários por 3 anos.

**Por definir:** esquema físico de séries temporais, partições, índices, formatos de valores/unidades, agregações, relógios, política de correções e associação a recursos.

## 5. Operations e ciclo de vida

**Contrato aprovado:** operações assíncronas; modalidades de execução `Observe`, `Manual`, `Scheduled` e `Campaign`.

**Por definir:** entidades de pedido/execução/resultado, idempotência, tentativas, estado de execução, rastreabilidade, aprovação e políticas de retenção.

## 6. Utilizadores, RBAC e auditoria

**Contrato aprovado:** RBAC com âmbitos global, grupo e recurso; auditoria estruturada *append-only* com retenção online de 12 meses.

**Por definir:** entidades físicas de utilizadores, papéis, permissões, atribuições, herança/precedência, sessões e integração de identidade; campos mínimos do evento auditável, integridade, exportação e retenção posterior.

## 7. Integração SIEM futura

A arquitetura deverá permitir integração posterior de eventos de segurança em tempo real. **Não** implica implementar um SIEM no MVP nem criar já tabelas SIEM. Contratos de eventos, fontes, normalização, encaminhamento e retenção específicos permanecem por definir na fase correspondente.

## 8. Contratos transversais

- Adaptadores previstos: `DiscoverAdapter`, `CollectAdapter`, `HealthAdapter`, `ExecuteAdapter`.
- A separação entre observações, recursos consolidados, estados e auditoria deve manter-se no desenho físico.
- A futura estrutura de schemas, nomes de tabelas e relações não deve ser inferida apenas desta especificação.

## 9. Lacunas a resolver antes de implementar DDL

| Referência | Questão em aberto |
|---|---|
| DAT-01 | Catálogo de recursos, tipos e atributos |
| DAT-02 | Identificadores, proveniência e reconciliação |
| DAT-03 | Estados administrativos, candidatos e aprovação |
| DAT-04 | Relações, cardinalidades e histórico |
| DAT-05 | Schemas e nomes físicos de tabelas |
| DAT-06 | Índices, partições e armazenamento de métricas |
| DAT-07 | Retenção e limpeza de observações de descoberta |
| DAT-08 | Necessidade e contrato de Outbox transacional |
| DAT-09 | Grupos, etiquetas e associação de recursos |
| DAT-10 | Políticas e respetiva aplicação/herança |

Estas referências são lacunas de consolidação já identificadas; não representam decisões novas.

## 10. Critérios de saída da especificação

Antes de criar os primeiros modelos SQLAlchemy e migrações:

1. Conferir cada contrato com a versão integral aprovada das decisões D-01 a D-51 e os 16 capítulos do Plano Técnico; incluir a previsão posterior de SIEM.
2. Resolver ou classificar explicitamente cada lacuna DAT-01 a DAT-10 como bloqueante ou diferida.
3. Aprovar entidades, campos obrigatórios, chaves, unicidade, relações e política de evolução de esquemas.
4. Definir estratégia de migração e testes de integridade sem afetar o LiveNet v1.
5. Registar aprovação documental antes de gerar DDL.

**Próximo estado pretendido:** revisão e validação desta especificação; ainda sem implementação do modelo físico.

## 11. Decisões complementares aprovadas

### DAT-01A — Catálogo inicial de tipos de recursos

**Estado:** Aprovada.

O catálogo inicial de recursos contém os seguintes tipos:

- `physical_host`
- `virtual_machine`
- `container`
- `network_device`
- `storage_device`
- `iot_device`
- `service`
- `cluster`

O catálogo é extensível e controlado. A introdução de novos tipos
exige uma definição registada e regras de validação próprias.

### DAT-01B — Atributos estruturais comuns

**Estado:** Aprovada.

| Atributo | Obrigatório | Descrição |
|---|---|---|
| `id` | Sim | UUID interno e imutável |
| `resource_type` | Sim | Tipo registado no catálogo |
| `display_name` | Sim | Nome de apresentação |
| `description` | Não | Descrição administrativa |
| `administrative_state` | Sim | Estado administrativo |
| `attributes` | Sim | JSONB validado; admite objeto vazio |
| `created_at` | Sim | Data de criação |
| `updated_at` | Sim | Data da última alteração |
| `archived_at` | Não | Data de arquivamento |

Regras aprovadas:

1. `display_name` não necessita de ser único.
2. IP, MAC e hostname não constituem a identidade primária.
3. O estado administrativo é independente do estado operacional.
4. `attributes` é validado segundo o tipo de recurso.
5. O arquivamento preserva a identidade e as referências históricas.
6. Os valores e transições de `administrative_state` ficam para DAT-03.
7. A política de eliminação definitiva permanece por definir.

Estas decisões complementam DAT-01, que só ficará integralmente
resolvida após a definição dos restantes contratos aplicáveis.

### DAT-02A — Identificadores externos

**Estado:** Aprovada.

Os recursos possuem UUID interno imutável e podem apresentar
múltiplos identificadores externos contextualizados.

Categorias iniciais:
- Rede: IPv4, IPv6 e MAC.
- Sistema: hostname, FQDN e machine-id.
- Virtualização: VMID e UUID de VM.
- Containers: Docker ID e Kubernetes UID.
- Hardware: número de série e UUID SMBIOS.
- Integrações: identificadores de agentes e sistemas externos.

Cada identificador conserva origem, contexto e histórico.
A unicidade não é necessariamente global.
Coincidências isoladas não implicam fusão automática.

### DAT-02B — Proveniência e confiança

**Estado:** Aprovada.

Cada observação deve preservar conceptualmente:
- source_type
- source_instance
- observed_at
- first_seen_at
- last_seen_at
- confidence
- evidence
- verification_status

A confiança é contextual e reavaliável.
Não existe uma hierarquia universal rígida entre fontes.
Informações contraditórias são preservadas e sinalizadas.
As decisões de reconciliação devem ser auditáveis.

### DAT-02C — Reconciliação de identidades

**Estado:** Aprovada.

A reconciliação será conservadora, auditável e idempotente.

Regras:
1. Identificadores fortes contextualizados podem permitir associação determinística.
2. IP ou hostname isolados não comprovam identidade.
3. Identificadores fortes contraditórios impedem fusão automática.
4. Correspondências ambíguas exigem revisão autorizada.
5. Ausência de correspondência origina candidato a recurso.
6. Decisões automáticas e manuais são auditadas.
7. Associações incorretas podem ser corrigidas preservando histórico.
8. Repetir observações não pode criar recursos duplicados.

Os critérios concretos de correspondência e os limiares
de confiança permanecem por definir.

### DAT-03A — Estados administrativos

**Estado:** Aprovada.

Os candidatos de Discovery são separados dos recursos consolidados.

Estados administrativos:
- active
- maintenance
- disabled
- archived

Os estados administrativos são independentes dos estados operacionais.
O arquivamento preserva UUID, auditoria e referências históricas.
Novas descobertas não reativam automaticamente recursos arquivados.

### DAT-03B — Aprovação e transições

**Estado:** Aprovada.

A aprovação de candidatos é manual por defeito.
A aprovação automática exige política explícita e evidência suficiente.
Rejeições preservam histórico e ambiguidades exigem revisão autorizada.

Transições administrativas permitidas:
- Candidato -> active, mediante aprovação.
- active <-> maintenance.
- active <-> disabled.
- maintenance <-> disabled.
- Qualquer estado não arquivado -> archived.
- archived -> active, apenas por recuperação manual autorizada.

Todas as transições exigem autorização RBAC e auditoria.
A recuperação preserva o UUID original.
A eliminação física não integra o fluxo administrativo normal.

Os efeitos operacionais dos estados serão definidos
nos contratos de Monitoring e Operations.

### DAT-04A — Relações tipadas e direcionadas

**Estado:** Aprovada.

Os recursos podem estabelecer relações tipadas, direcionadas
e extensíveis, com origem e destino identificados por UUID.

Catálogo inicial:
- member_of: pertença a agrupamento.
- hosts: alojamento de VM ou container.
- runs: execução de serviço.
- depends_on: dependência funcional.
- connected_to: ligação de infraestrutura.
- managed_by: gestão por outro recurso.

Regras:
1. As relações possuem tipo, origem e destino explícitos.
2. A direção é semanticamente relevante.
3. Os tipos pertencem a um catálogo extensível e controlado.
4. Cada tipo pode restringir os recursos de origem e destino.
5. Relações descobertas preservam proveniência e evidência.
6. Relações ambíguas não são consolidadas automaticamente.
7. O arquivamento não elimina automaticamente o histórico.

### DAT-04B — Cardinalidades e histórico temporal

**Estado:** Aprovada.

As cardinalidades dependem do tipo de relação.

- member_of: múltiplos agrupamentos possíveis.
- hosts: um host de execução ativo por contexto e instante.
- runs: múltiplos serviços e instâncias possíveis.
- depends_on: múltiplas dependências permitidas.
- connected_to: múltiplas ligações permitidas.
- managed_by: múltiplos gestores conforme contexto.

As relações consolidadas suportam conceptualmente:
- Início e fim de validade.
- Proveniência e evidência.
- Estado atual ou histórico.
- Alterações e correções auditáveis.

Regras de integridade:
1. Ciclos em depends_on são detetados e sinalizados.
2. Ciclos hierárquicos em hosts são proibidos.
3. Os extremos devem referenciar recursos existentes.
4. Relações equivalentes duplicadas no mesmo contexto
   e período devem ser impedidas.
5. Contradições permanecem como observações até reconciliação.
6. O encerramento de uma relação preserva o histórico.

As restrições físicas, os intervalos temporais e as políticas
de retenção serão definidos antes da implementação DDL.

### DAT-05A — Organização dos schemas PostgreSQL

**Estado:** Aprovada.

O LiveNet v2 utilizará uma única base de dados PostgreSQL
denominada `livenet`, organizada inicialmente em seis schemas:

- `inventory`: recursos, identidades e relações.
- `discovery`: fontes, observações e candidatos.
- `monitoring`: estados, verificações e métricas.
- `operations`: ações, execuções e tarefas.
- `security`: utilizadores, RBAC e sessões.
- `audit`: eventos e histórico auditável.

Regras:
1. Cada domínio possui um schema próprio.
2. São permitidas chaves estrangeiras entre schemas quando necessárias.
3. O acesso aos dados respeita os limites dos módulos.
4. O Alembic gere a evolução dos schemas.
5. Os nomes físicos das tabelas são definidos progressivamente.
6. A arquitetura deve funcionar com menos de 100 recursos
   e permitir evolução para 100–1000.
7. A futura integração SIEM utiliza contratos próprios,
   sem sobrecarregar as tabelas operacionais.

### DAT-05B — Convenções de nomenclatura e integridade

**Estado:** Aprovada.

Convenções:
- Schemas, tabelas e colunas em `snake_case`.
- Nomes de tabelas no plural.
- Chaves primárias denominadas `id`.
- Chaves estrangeiras no formato `<entidade>_id`.
- Índices no formato `ix_<tabela>_<campos>`.
- Unicidade no formato `uq_<tabela>_<campos>`.
- Check constraints no formato `ck_<tabela>_<regra>`.
- Foreign keys no formato `fk_<tabela>_<campo>`.

Regras:
1. UUID como chave primária por defeito para entidades de domínio.
2. TIMESTAMPTZ para datas e horas, representando instantes UTC.
3. JSONB para atributos extensíveis e evidências adequadas.
4. Chaves estrangeiras e constraints explícitas.
5. Índices definidos por necessidades de consulta.
6. Sem eliminação em cascata de dados históricos críticos.
7. Migrações Alembic versionadas, revistas e testadas.
8. Alterações destrutivas exigem plano de migração.
9. Privilegiar evolução compatível com versões anteriores.

### DAT-06A — Armazenamento de monitorização

**Estado:** Aprovada.

A monitorização utilizará inicialmente PostgreSQL 16,
sem dependência obrigatória de TimescaleDB ou outras
bases especializadas.

Categorias:
- Estado operacional atual.
- Histórico de verificações.
- Métricas temporais.

Regras:
1. Separar estado atual de histórico.
2. Utilizar timestamps UTC.
3. Indexar por recurso e intervalo temporal.
4. Prever retenção e agregação.
5. Não ativar particionamento por defeito.
6. Permitir evolução futura para particionamento temporal.
7. Introduzir tecnologias especializadas apenas quando
   volume e desempenho reais o justificarem.

### DAT-06B — Retenção e agregação de métricas

**Estado:** Aprovada.

Política inicial:

| Categoria | Retenção |
|---|---|
| Estado atual | Enquanto o recurso existir |
| Verificações individuais | 90 dias |
| Métricas brutas | 30 dias |
| Agregações de 5 minutos | 180 dias |
| Agregações horárias | 12 meses |
| Eventos operacionais | Política específica do domínio |
| Auditoria | 12 meses online |

Regras:
1. Retenção configurável por política.
2. Agregações com média, mínimo, máximo e contagem.
3. Limpeza controlada e auditável.
4. Agregação concluída antes de eliminar dados brutos.
5. Retenção ajustável por métrica e criticidade.
6. Respeito por requisitos de preservação.
7. Auditoria e segurança têm retenção independente.
8. Monitorizar crescimento do armazenamento.

### DAT-07A — Retenção de Discovery

**Estado:** Aprovada.

Política inicial:

| Categoria | Retenção |
|---|---|
| Observações brutas | 30 dias |
| Candidatos pendentes | Até decisão, com revisão periódica |
| Candidatos rejeitados | 90 dias após rejeição |
| Resultados de reconciliação | 180 dias |
| Identificadores consolidados | Conforme necessidade histórica |
| Aprovações e rejeições | Política de auditoria |

Regras:
1. A limpeza não elimina identidades consolidadas.
2. Candidatos pendentes não são eliminados sem política explícita.
3. Rejeições devem evitar recriações repetitivas sem nova evidência.
4. Conflitos abertos preservam observações relevantes.
5. Retenção configurável por fonte e tipo.
6. Limpeza auditável, incluindo contagens processadas.
7. Proveniência histórica necessária permanece preservada.

### DAT-08A — Transactional Outbox

**Estado:** Aprovada.

O LiveNet v2 utilizará Transactional Outbox em PostgreSQL
para eventos de domínio que exijam publicação fiável.

Regras:
1. Alteração de domínio e evento Outbox na mesma transação.
2. Publicação assíncrona através de workers.
3. Repetição controlada após falhas.
4. Semântica de entrega `at-least-once`.
5. Consumidores obrigatoriamente idempotentes.
6. Eventos com ID, tipo, versão, timestamp e payload validado.
7. Diagnóstico, tentativas e tratamento de falhas persistentes.
8. Outbox independente da auditoria.
9. Retenção configurável dos eventos publicados.
10. Sem introdução obrigatória de Kafka ou RabbitMQ.

### DAT-09A — Grupos e etiquetas

**Estado:** Aprovada.

Os recursos podem pertencer a múltiplos grupos,
estáticos ou dinâmicos.

As etiquetas utilizam pares chave-valor normalizados.

Regras:
1. Grupos possuem identidade e nome próprios.
2. Pertença múltipla permitida.
3. Grupos dinâmicos baseados em critérios definidos.
4. Múltiplas etiquetas por recurso.
5. Utilização em filtros, dashboards, políticas e permissões.
6. Alterações relevantes são auditáveis.
7. Histórico de associações preservado quando necessário.
8. Sem imposição de hierarquia única.
9. Herança e conflitos de políticas tratados em DAT-10A.

### DAT-10A — Políticas, âmbito e herança

**Estado:** Aprovada.

As políticas serão tipadas e versionadas.

Âmbitos e precedência:
1. Global — configuração base.
2. Grupo — sobreposição da configuração global.
3. Recurso — sobreposição da configuração de grupo.

Regras:
1. Configuração efetiva calculada a partir das políticas aplicáveis.
2. Sobreposições explícitas e auditáveis.
3. Conflitos entre grupos resolvidos por prioridade determinística.
4. A origem de cada configuração efetiva deve ser consultável.
5. Alterações podem desencadear reavaliação dos recursos.
6. Políticas inválidas são rejeitadas antes da ativação.
7. Aplicação sujeita a RBAC.
8. Restrições de segurança não podem ser enfraquecidas
   por políticas de menor âmbito sem autorização explícita.

Os critérios físicos de prioridade, avaliação e armazenamento
serão definidos na especificação de implementação.

## 12. Estado da consolidação conceptual

As decisões complementares DAT-01A a DAT-10A encontram-se
aprovadas e documentadas.

A revisão conceptual dos dez grupos DAT está concluída.

Permanecem pendentes:
- Definição física de entidades, colunas e constraints.
- Contratos concretos de validação JSONB.
- Critérios técnicos de reconciliação.
- Definição detalhada de índices e relações.
- Configuração dos mecanismos de retenção e limpeza.
- Validação de migrações e integridade referencial.

A aprovação conceptual não autoriza automaticamente
a criação de tabelas ou execução de migrações.

A próxima etapa será a especificação física do domínio
`inventory`, sujeita a revisão antes da implementação.
