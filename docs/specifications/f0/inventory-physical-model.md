# LiveNet v2 — Especificação Física do Inventory

**Fase:** F0 — Fundação Técnica
**Estado:** Decisões INV-01A a INV-09A aprovadas
**Natureza:** Especificação técnica; implementação pendente

## 1. Objetivo e âmbito

Este documento consolida a especificação física inicial do domínio
`inventory` do LiveNet v2.

Referências:
- Plano Técnico LiveNet v2, decisões D-01 a D-51.
- `docs/specifications/f0/data-model.md`.
- Decisões complementares DAT-01A a DAT-10A.

A especificação está dimensionada para uma instalação inicial
inferior a 100 recursos, mantendo uma evolução razoável para
100–1000 recursos.

As estruturas descritas não constituem autorização para executar
migrações ou modificar bases de dados existentes.

## 2. INV-01A — inventory.resources

**Estado:** Aprovada.

Tabela central dos recursos.

| Coluna | Tipo PostgreSQL | Regras |
|---|---|---|
| id | UUID | PK, obrigatório, imutável |
| resource_type | VARCHAR(64) | Obrigatório |
| display_name | VARCHAR(255) | Obrigatório, não único |
| description | TEXT | Opcional |
| administrative_state | VARCHAR(32) | Obrigatório; default active |
| attributes | JSONB | Obrigatório; default {} |
| created_at | TIMESTAMPTZ | Obrigatório |
| updated_at | TIMESTAMPTZ | Obrigatório |
| archived_at | TIMESTAMPTZ | Opcional |

Tipos iniciais:
- physical_host
- virtual_machine
- container
- network_device
- storage_device
- iot_device
- service
- cluster

Estados administrativos:
- active
- maintenance
- disabled
- archived

Regras:
1. UUID gerado pela aplicação.
2. IP, MAC, hostname e nome não constituem identidade primária.
3. O catálogo de tipos é controlado e extensível.
4. O estado operacional pertence ao domínio monitoring.
5. `attributes` tem de ser um objeto JSON.
6. A validação dos atributos depende do tipo de recurso.
7. O arquivamento preserva identidade e histórico.
8. `updated_at >= created_at`.
9. Timestamps UTC, geridos pela aplicação com defaults
   de segurança na base de dados.
10. Alterações relevantes são auditáveis.

Índice inicial:
- `(resource_type, administrative_state)`.

## 3. INV-02A — inventory.resource_identifiers

**Estado:** Aprovada.

| Coluna | Tipo PostgreSQL | Regras |
|---|---|---|
| id | UUID | PK |
| resource_id | UUID | FK resources.id |
| identifier_type | VARCHAR(64) | Obrigatório |
| identifier_value | TEXT | Obrigatório |
| normalized_value | TEXT | Obrigatório |
| namespace | VARCHAR(255) | Opcional |
| source_type | VARCHAR(64) | Obrigatório |
| source_instance | VARCHAR(255) | Opcional |
| first_seen_at | TIMESTAMPTZ | Obrigatório |
| last_seen_at | TIMESTAMPTZ | Obrigatório |
| verified_at | TIMESTAMPTZ | Opcional |
| verification_status | VARCHAR(32) | Obrigatório |
| confidence | NUMERIC(5,4) | Opcional; NULL ou valor entre 0.0000 e 1.0000, inclusive |
| evidence | JSONB | Obrigatório; default {} |
| valid_from | TIMESTAMPTZ | Obrigatório |
| valid_until | TIMESTAMPTZ | Opcional |
| created_at | TIMESTAMPTZ | Obrigatório |
| updated_at | TIMESTAMPTZ | Obrigatório |

Tipos suportados inicialmente:
- IPv4, IPv6 e MAC.
- Hostname, FQDN e machine-id.
- Proxmox VMID e VM UUID.
- Docker container ID e Kubernetes UID.
- Serial number e SMBIOS UUID.
- Agent ID e identificadores externos.

Regras:
1. Múltiplos identificadores por recurso.
2. Unicidade contextual, não global.
3. Namespace interpretado segundo o tipo de identificador.
4. Normalização sem perda do valor original.
5. Preservação de proveniência e evidências.
6. Associação temporal com encerramento por valid_until.
7. Coincidência de identificadores não implica fusão automática.
8. Conflitos encaminhados para reconciliação.
9. `last_seen_at >= first_seen_at`.
10. `valid_until > valid_from`, quando preenchido.
11. Sem eliminação em cascata do histórico.
12. `confidence` é validado por constraint CHECK no intervalo [0, 1], permitindo NULL.
13. O valor de `confidence`, isoladamente, não autoriza fusão automática de recursos.

Índices iniciais:
- `(identifier_type, normalized_value, namespace)`.
- `(resource_id, valid_until)`.
- `(source_type, source_instance)`.

A definição de unicidade para identificadores fortes
depende de regras adicionais por tipo e contexto.

## 4. INV-03A — inventory.resource_relations

**Estado:** Aprovada.

| Coluna | Tipo PostgreSQL | Regras |
|---|---|---|
| id | UUID | PK |
| source_resource_id | UUID | FK resources.id |
| target_resource_id | UUID | FK resources.id |
| relation_type | VARCHAR(64) | Obrigatório |
| source_type | VARCHAR(64) | Origem da informação |
| source_instance | VARCHAR(255) | Opcional |
| evidence | JSONB | Objeto; default {} |
| valid_from | TIMESTAMPTZ | Obrigatório |
| valid_until | TIMESTAMPTZ | Opcional |
| created_at | TIMESTAMPTZ | Obrigatório |
| updated_at | TIMESTAMPTZ | Obrigatório |

Tipos de relação:
- member_of
- hosts
- runs
- depends_on
- connected_to
- managed_by

Regras:
1. Relações dirigidas entre UUIDs de recursos.
2. `connected_to` pode ter interpretação recíproca no domínio.
3. Autorrelacionamentos proibidos por defeito.
4. Combinações de tipos validadas por relation_type.
5. Histórico preservado através de validade temporal.
6. Duplicados equivalentes e temporalmente sobrepostos proibidos
   dentro do mesmo contexto lógico.
7. Um recurso alojado possui apenas um host ativo por contexto
   de execução e instante.
8. Ciclos hosts rejeitados.
9. Ciclos depends_on detetados e sinalizados.
10. Alterações relevantes auditadas.
11. Evidências contraditórias preservadas para reconciliação.

Índices iniciais:
- `(source_resource_id, relation_type)`.
- `(target_resource_id, relation_type)`.
- `(relation_type, valid_until)`.

### F0.62-C01 — Integridade temporal das relações

**Estado:** Aprovada em 2026-10-16.

A tabela `inventory.resource_relations` inclui a constraint PostgreSQL `CHECK (updated_at >= created_at)`.

**Justificação:** impedir que uma relação apresente uma data de atualização anterior à sua criação, mantendo a coerência temporal com `inventory.resources`.

Esta regra complementa as constraints de autorrelacionamento, validade temporal e formato JSONB de `evidence`.

As regras de cardinalidade contextual, sobreposição temporal e deteção de ciclos continuam a pertencer à camada de domínio.

---

## 5. INV-04A — Grupos de recursos

**Estado:** Aprovada.

### 5.1 inventory.groups

| Coluna | Tipo | Regras |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(255) | Obrigatório |
| description | TEXT | Opcional |
| group_type | VARCHAR(32) | static ou dynamic |
| created_at | TIMESTAMPTZ | Obrigatório |
| updated_at | TIMESTAMPTZ | Obrigatório |
| archived_at | TIMESTAMPTZ | Opcional |

Nome único entre grupos não arquivados, através de
índice único parcial.

### 5.2 inventory.group_memberships

| Coluna | Tipo | Regras |
|---|---|---|
| id | UUID | PK |
| group_id | UUID | FK groups |
| resource_id | UUID | FK resources |
| membership_source | VARCHAR(32) | manual ou rule |
| valid_from | TIMESTAMPTZ | Obrigatório |
| valid_until | TIMESTAMPTZ | Opcional |
| created_at | TIMESTAMPTZ | Obrigatório |

Associações ativas equivalentes não podem ser duplicadas
para a mesma origem.

### 5.3 inventory.group_rules

| Coluna | Tipo | Regras |
|---|---|---|
| id | UUID | PK |
| group_id | UUID | FK groups |
| rule_definition | JSONB | Critério validado |
| enabled | BOOLEAN | Default true |
| created_at | TIMESTAMPTZ | Obrigatório |
| updated_at | TIMESTAMPTZ | Obrigatório |

Regras:
1. Pertença múltipla permitida.
2. Grupos estáticos geridos manualmente.
3. Grupos dinâmicos definidos por regras declarativas.
4. Sem SQL arbitrário fornecido por utilizadores.
5. Associações dinâmicas materializadas.
6. Reavaliação idempotente por workers.
7. Alterações de pertença auditáveis.
8. Arquivamento preserva histórico.
9. Políticas de grupos geridas pelo sistema de políticas.
10. Avaliação com limites de complexidade.

## 6. INV-05A — Etiquetas

**Estado:** Aprovada.

### 6.1 inventory.tags

| Coluna | Tipo | Regras |
|---|---|---|
| id | UUID | PK |
| key | VARCHAR(128) | Obrigatório |
| value | VARCHAR(255) | Obrigatório |
| description | TEXT | Opcional |
| created_at | TIMESTAMPTZ | Obrigatório |
| updated_at | TIMESTAMPTZ | Obrigatório |

Constraints:
- Unicidade global de `(key, value)`.
- Chave e valor não vazios.
- Chaves normalizadas para minúsculas.
- Remoção de espaços exteriores na normalização.
- Comparação consistente dos valores.

### 6.2 inventory.resource_tags

| Coluna | Tipo | Regras |
|---|---|---|
| id | UUID | PK |
| resource_id | UUID | FK resources |
| tag_id | UUID | FK tags |
| assignment_source | VARCHAR(32) | manual, discovery ou policy |
| valid_from | TIMESTAMPTZ | Obrigatório |
| valid_until | TIMESTAMPTZ | Opcional |
| created_at | TIMESTAMPTZ | Obrigatório |

Regras:
1. Múltiplas etiquetas por recurso.
2. Múltiplos valores para a mesma chave permitidos.
3. Sem associações ativas duplicadas para a mesma origem.
4. Histórico temporal preservado.
5. Proveniência da atribuição registada.
6. Alterações relevantes auditadas.
7. Alterações podem desencadear reavaliação de grupos.
8. Remoção encerra associação sem apagar catálogo.
9. Etiquetas sem recursos são permitidas.
10. Arquivamento preserva histórico.

Índices:
- `(key, value)` único.
- `(resource_id, valid_until)`.
- `(tag_id, valid_until)`.

## 7. INV-06A — Políticas e configuração efetiva

**Estado:** Aprovada.

### 7.1 inventory.policies

| Coluna | Tipo | Regras |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(255) | Obrigatório |
| policy_type | VARCHAR(64) | Tipo controlado |
| description | TEXT | Opcional |
| enabled | BOOLEAN | Default true |
| created_at | TIMESTAMPTZ | Obrigatório |
| updated_at | TIMESTAMPTZ | Obrigatório |
| archived_at | TIMESTAMPTZ | Opcional |

### 7.2 inventory.policy_versions

| Coluna | Tipo | Regras |
|---|---|---|
| id | UUID | PK |
| policy_id | UUID | FK policies |
| version | INTEGER | Sequencial |
| definition | JSONB | Validada |
| created_at | TIMESTAMPTZ | Obrigatório |
| created_by | UUID | Autor, quando aplicável |

Versões publicadas são imutáveis.

### 7.3 inventory.policy_assignments

| Coluna | Tipo | Regras |
|---|---|---|
| id | UUID | PK |
| policy_version_id | UUID | FK policy_versions |
| scope_type | VARCHAR(32) | global, group, resource |
| group_id | UUID | FK opcional groups |
| resource_id | UUID | FK opcional resources |
| priority | INTEGER | Prioridade explícita |
| valid_from | TIMESTAMPTZ | Obrigatório |
| valid_until | TIMESTAMPTZ | Opcional |
| created_at | TIMESTAMPTZ | Obrigatório |

Constraint de coerência:
- global: sem group_id nem resource_id.
- group: apenas group_id.
- resource: apenas resource_id.

### 7.4 inventory.effective_configs

| Coluna | Tipo | Regras |
|---|---|---|
| id | UUID | PK |
| resource_id | UUID | FK resources |
| policy_type | VARCHAR(64) | Obrigatório |
| resolved_config | JSONB | Configuração calculada |
| resolution_trace | JSONB | Origem e precedência |
| calculated_at | TIMESTAMPTZ | Obrigatório |
| revision | INTEGER | Revisão calculada |

Tabela derivada e reconstruível, não fonte de verdade.

Regras:
1. Precedência resource > group > global.
2. Prioridade explícita entre grupos.
3. Resolução determinística de empates.
4. Conflitos incompatíveis sinalizados.
5. Avaliação idempotente.
6. Rastreabilidade por valor.
7. Invalidação após alterações relevantes.
8. Validação antes da publicação.
9. Alterações sujeitas a RBAC.
10. Restrições de segurança protegidas.
11. Reconstrução possível após falhas.

## 8. INV-07A — Integridade e concorrência

**Estado:** Aprovada.

Estratégia:
- PostgreSQL assegura constraints e integridade referencial.
- A camada de domínio valida regras de negócio.
- Operações relacionadas utilizam transações atómicas.
- Controlo otimista de concorrência nas entidades aplicáveis.
- Bloqueios transacionais seletivos para operações críticas.
- Workers e projeções idempotentes.
- Transactional Outbox para eventos relevantes.

A coluna `row_version INTEGER`, inicialmente 1, será introduzida
nas entidades mutáveis que necessitem de controlo otimista.

Atualizações concorrentes não podem sobrescrever alterações
silenciosamente.

Reconciliação, cardinalidades e prevenção de ciclos devem ser
protegidas contra condições de corrida.

Não utilizar bloqueios globais ou isolamento SERIALIZABLE
indiscriminadamente.

## 9. INV-08A — Auditoria centralizada

**Estado:** Aprovada.

Tabela: `audit.events`.

| Coluna | Tipo | Regras |
|---|---|---|
| id | UUID | PK |
| occurred_at | TIMESTAMPTZ | Obrigatório |
| actor_type | VARCHAR(32) | Tipo de responsável |
| actor_id | UUID | Opcional |
| action | VARCHAR(128) | Obrigatório |
| entity_type | VARCHAR(128) | Obrigatório |
| entity_id | UUID | Quando aplicável |
| correlation_id | UUID | Opcional |
| request_id | VARCHAR(128) | Opcional |
| outcome | VARCHAR(32) | Resultado |
| changes | JSONB | Alterações relevantes |
| context | JSONB | Informação contextual |

Regras:
1. Registar alterações relevantes do inventário.
2. Identificar responsável sempre que possível.
3. Distinguir utilizadores, sistemas, agentes e integrações.
4. Evitar armazenamento indiscriminado de dados sensíveis.
5. Registos imutáveis na utilização normal.
6. Auditoria obrigatória na mesma transação da operação.
7. Falha da auditoria obrigatória impede confirmação.
8. Retenção inicial de 12 meses online.
9. Preparação para integração futura com SIEM.

A auditoria é distinta da Transactional Outbox e dos logs técnicos.

## 10. INV-09A — Implementação incremental

**Estado:** Aprovada.

Sequência:
1. Schema inventory e tabela resources.
2. Identificadores e relações.
3. Grupos e etiquetas.
4. Políticas e configuração efetiva.
5. Auditoria e Transactional Outbox.
6. Testes integrados.

Regras:
- Migrações Alembic por conjunto lógico.
- Modelos SQLAlchemy antes das migrações.
- Revisão manual das migrações geradas.
- Testes em base isolada.
- Sem alterações ao LiveNet v1.
- Testes de constraints, concorrência e idempotência.
- Git como fonte de verdade do histórico de migrações.
- Produção apenas após aprovação, backup e recuperação.
- Dependências adicionais apenas quando justificadas.

## 11. Critérios de aceitação

A implementação física do inventário deverá permitir:

1. Criar e consultar recursos dos oito tipos iniciais.
2. Associar identificadores externos com histórico.
3. Criar relações válidas e rejeitar incompatibilidades.
4. Gerir grupos estáticos e dinâmicos.
5. Gerir etiquetas e respetivas associações.
6. Aplicar políticas e consultar configuração efetiva.
7. Registar alterações relevantes na auditoria.
8. Validar concorrência e idempotência.
9. Executar migrações numa base vazia.
10. Verificar integridade do esquema resultante.

## 12. Pontos ainda por concretizar

Aprovação conceptual e física inicial não significa que todos
os contratos de implementação estejam fechados.

Permanecem por definir:
- Contratos de validação JSONB.
- Catálogos e regras detalhadas de tipos.
- Regras de unicidade contextual de identificadores fortes.
- Normalização específica de cada identificador.
- Mecanismos concretos de prevenção de ciclos e concorrência.
- Seleção das entidades que utilizarão row_version.
- Semântica exata de regras de grupos dinâmicos.
- Resolução de empates e conflitos de políticas.
- Índices adicionais justificados por consultas reais.
- Implementação de retenção e limpeza.
- Contratos físicos da Transactional Outbox.
- Procedimentos de migração, rollback e recuperação.

Estes pontos deverão ser resolvidos progressivamente,
antes de implementar as funcionalidades correspondentes.

## 13. Estado da especificação

**INV-01A a INV-09A: aprovadas.**

A consolidação documental não altera o estado da base de dados.

A primeira etapa de implementação prevista é a fundação do
schema `inventory` e da entidade `inventory.resources`,
após validação deste documento.

## 14. Estado da implementação física

Esta secção regista a execução incremental da especificação,
sem substituir nem alterar as decisões INV-01A a INV-09A.

### F0.63A — inventory.groups

**Estado:** Implementação física validada em base isolada.

**Revisão Alembic:** `da34876e4210`.

**Revisão anterior:** `38d641dcd780`.

Tabela implementada: `inventory.groups`.

Colunas:
- `id UUID` — chave primária, UUID gerado pela aplicação.
- `name VARCHAR(255)` — obrigatório.
- `description TEXT` — opcional.
- `group_type VARCHAR(32)` — obrigatório.
- `created_at TIMESTAMPTZ` — obrigatório, default `now()`.
- `updated_at TIMESTAMPTZ` — obrigatório, default `now()`.
- `archived_at TIMESTAMPTZ` — opcional.

Índice único parcial:
- `uq_groups_active_name` em `name`.
- Predicado: `archived_at IS NULL`.
- Impede nomes duplicados entre grupos não arquivados.
- Permite reutilizar nomes de grupos arquivados.

### F0.63-C01 — Constraints complementares dos grupos

**Estado:** Aprovada e implementada na F0.63A.

Foram aprovadas duas constraints de integridade:

1. `ck_groups_type`:
   `CHECK (group_type IN ('static', 'dynamic'))`.
2. `ck_groups_timestamps`:
   `CHECK (updated_at >= created_at)`.

A primeira restringe os tipos aos previstos na especificação
INV-04A. A segunda impede inconsistências temporais básicas.

Estas constraints são aplicadas pelo PostgreSQL, independentemente
da validação efetuada pela aplicação.

### Validação da F0.63A

- 48 testes Python aprovados.
- SQL offline da migração inspecionado.
- Migração aplicada exclusivamente em `livenet_f0_test`.
- Estrutura física confirmada no PostgreSQL.
- 8 testes de integridade PostgreSQL aprovados.
- Testes executados com `ROLLBACK`, sem dados persistidos.
- Downgrade para `38d641dcd780` validado.
- Upgrade para `da34876e4210` validado.
- Base principal `livenet` não migrada.

### F0.63B — inventory.group_memberships

**Estado:** Implementação física validada em base isolada.

**Revisão Alembic:** `ba06dd956da9`.
**Revisão anterior:** `da34876e4210`.

Tabela: `inventory.group_memberships`.

Colunas:
- `id UUID` — chave primária.
- `group_id UUID` — FK obrigatória para `inventory.groups.id`.
- `resource_id UUID` — FK obrigatória para `inventory.resources.id`.
- `membership_source VARCHAR(32)` — obrigatório.
- `valid_from TIMESTAMPTZ` — obrigatório.
- `valid_until TIMESTAMPTZ` — opcional.
- `created_at TIMESTAMPTZ` — obrigatório, default `now()`.

As chaves estrangeiras não utilizam `ON DELETE CASCADE`.

### F0.63B-C01 — Integridade temporal

**Estado:** Aprovada e implementada.

Constraints:
- `ck_group_memberships_source`: apenas `manual` ou `rule`.
- `ck_group_memberships_validity`: fim nulo ou posterior ao início.
- `ex_group_memberships_no_overlap`: exclusão GiST para impedir
  períodos sobrepostos na mesma combinação de grupo, recurso e origem.

Os intervalos seguem a semântica `[valid_from, valid_until)`.
Um limite superior nulo representa um intervalo aberto.

As origens `manual` e `rule` podem coexistir.

A migração instala `btree_gist` quando necessário.
O downgrade não remove esta extensão.

### Validação da F0.63B

- 58 testes Python aprovados.
- SQL offline inspecionado.
- Migração validada em `livenet_f0_test`.
- 8 testes de integridade temporal aprovados.
- 4 testes de integridade referencial aprovados.
- 5 verificações de concorrência aprovadas.
- Conflito concorrente confirmado com SQLSTATE `23P01`.
- Downgrade para `da34876e4210` validado.
- Upgrade para `ba06dd956da9` validado.
- Extensão `btree_gist` 1.7 preservada no downgrade.
- Nenhuma associação de teste persistida.
- Base principal `livenet` não migrada.

A F0.63B está validada fisicamente, mas a funcionalidade
INV-04A permanece incompleta até às etapas seguintes.


### F0.63C — inventory.group_rules

**Estado:** Implementação física validada em base isolada.

**Revisão Alembic:** `44e7eb855b5a`.
**Revisão anterior:** `ba06dd956da9`.

Tabela: `inventory.group_rules`.

Colunas:
- `id UUID` — chave primária, UUID gerado pela aplicação.
- `group_id UUID` — FK obrigatória para `inventory.groups.id`.
- `rule_definition JSONB` — obrigatório.
- `enabled BOOLEAN` — obrigatório, default `true`.
- `created_at TIMESTAMPTZ` — obrigatório, default `now()`.
- `updated_at TIMESTAMPTZ` — obrigatório, default `now()`.

A chave estrangeira não utiliza `ON DELETE CASCADE`.

### F0.63C-C01 — Integridade física das regras

**Estado:** Aprovada e implementada.

Constraints:
- `ck_group_rules_definition_object`:
  `CHECK (jsonb_typeof(rule_definition) = 'object')`.
- `ck_group_rules_timestamps`:
  `CHECK (updated_at >= created_at)`.

São permitidas várias regras por grupo, sem restrição de
unicidade adicional ou cardinalidade máxima nesta fase.

A estrutura interna de `rule_definition` ainda não possui
um contrato semântico aprovado.

Não foram implementados o motor de avaliação, os workers
nem a materialização automática das associações.

### Validação da F0.63C

- 68 testes Python aprovados, incluindo 10 testes estruturais.
- Sintaxe Python e `git diff --check` validados.
- SQL offline da migração inspecionado.
- Migração aplicada exclusivamente em `livenet_f0_test`.
- Seis colunas e quatro constraints confirmadas no PostgreSQL.
- 7 testes funcionais de integridade PostgreSQL aprovados.
- Testes executados com `ROLLBACK`, sem dados persistidos.
- Downgrade para `ba06dd956da9` validado.
- Upgrade para `44e7eb855b5a` validado.
- Tabela recriada sem registos.
- Base principal `livenet` não migrada.

### Estado da INV-04A após a F0.63C

A implementação física inicial das três tabelas está validada:

- F0.63A: `inventory.groups`.
- F0.63B: `inventory.group_memberships`.
- F0.63C: `inventory.group_rules`.

A conclusão destas etapas não representa a conclusão
funcional da INV-04A.

Permanecem pendentes a definição da linguagem declarativa
das regras, a respetiva validação semântica, o motor de
avaliação, a reavaliação idempotente por workers, a
materialização automática das associações e os mecanismos
de auditoria associados.

### F0.64A — inventory.tags

**Estado:** Implementada e validada em ambiente de testes.

**Contrato de referência:** INV-05A / DAT-09A.

**Migração Alembic:** `7c4e2a91b605`, dependente de
`44e7eb855b5a`.

A tabela `inventory.tags` constitui o catálogo global de etiquetas
do inventário.

Colunas implementadas:
- `id UUID` — chave primária.
- `key VARCHAR(128)` — obrigatório.
- `value VARCHAR(255)` — obrigatório.
- `description TEXT` — opcional.
- `created_at TIMESTAMPTZ` — obrigatório, default `now()`.
- `updated_at TIMESTAMPTZ` — obrigatório, default `now()`.

O modelo SQLAlchemy utiliza UUID gerado na aplicação e timestamps
UTC gerados na aplicação, mantendo defaults de timestamps na base.

### F0.64A-C01 — Normalização e integridade das etiquetas

**Estado:** Aprovada e implementada.

Regras:
1. As chaves são armazenadas em minúsculas e sem espaços exteriores.
2. Os valores são armazenados sem espaços exteriores.
3. Os valores preservam maiúsculas e minúsculas.
4. A comparação dos valores distingue maiúsculas de minúsculas.
5. A combinação `(key, value)` é globalmente única.
6. Chaves e valores vazios, incluindo apenas espaços, são rejeitados.
7. A base de dados valida a normalização através de constraints.
8. A futura camada de serviços normalizará os dados antes da inserção.
9. `updated_at` não pode ser anterior a `created_at`.

Constraints implementadas:
- `uq_tags_key_value`:
  `UNIQUE (key, value)`.
- `ck_tags_key_normalized`:
  `CHECK (key = lower(btrim(key)) AND length(key) > 0)`.
- `ck_tags_value_normalized`:
  `CHECK (value = btrim(value) AND length(value) > 0)`.
- `ck_tags_timestamps`:
  `CHECK (updated_at >= created_at)`.

Exemplo: `environment=Production` e `environment=production`
são duas etiquetas distintas.

A normalização automática na camada de serviços não faz parte
desta implementação física.

### Validação da F0.64A

**Estado:** Concluída.

Validações realizadas:
- 9 testes estruturais específicos do modelo `Tag`.
- 77 testes Python aprovados na suite completa.
- Geração e inspeção do SQL offline da migração.
- Upgrade aplicado exclusivamente em `livenet_f0_test`.
- Estrutura PostgreSQL verificada: 6 colunas, chave primária,
  3 constraints CHECK e 1 constraint UNIQUE.
- 9 testes de integridade PostgreSQL aprovados.
- Testes executados em transação com `ROLLBACK`.
- Downgrade para `44e7eb855b5a` validado.
- Reaplicação do upgrade para `7c4e2a91b605` validada.
- Tabela recriada sem registos.

A base principal `livenet` não recebeu esta migração.

### Estado da INV-05A após a F0.64A

- `inventory.tags`: implementação física concluída e validada
  na base isolada de testes.
- `inventory.resource_tags`: implementação física validada na F0.64B.
- Normalização na camada de serviços: pendente.
- Auditoria de alterações e integração com grupos dinâmicos:
  pendentes das respetivas fases funcionais.

A conclusão da F0.64A não representa a conclusão integral
da INV-05A.

### F0.64B — inventory.resource_tags

**Estado:** Implementada e validada em ambiente de testes.

**Contrato de referência:** INV-05A / DAT-09A.

**Migração Alembic:** `9e1b7c42a630`, dependente de
`7c4e2a91b605`.

A tabela `inventory.resource_tags` representa as atribuições
temporais de etiquetas aos recursos, preservando a origem
de cada atribuição e permitindo manter o respetivo histórico.

Colunas implementadas:
- `id UUID` — chave primária, gerada pela aplicação.
- `resource_id UUID` — FK obrigatória para `inventory.resources.id`.
- `tag_id UUID` — FK obrigatória para `inventory.tags.id`.
- `assignment_source VARCHAR(32)` — obrigatório.
- `valid_from TIMESTAMPTZ` — obrigatório.
- `valid_until TIMESTAMPTZ` — opcional.
- `created_at TIMESTAMPTZ` — obrigatório, default `now()`.

As chaves estrangeiras não utilizam `ON DELETE CASCADE`.

### F0.64B-C01 — Integridade temporal das atribuições

**Estado:** Aprovada e implementada.

Origens permitidas:
- `manual`.
- `discovery`.
- `policy`.

Constraints implementadas:
- Validação de `assignment_source` através de `CHECK`.
- Validação de `valid_until IS NULL OR valid_until > valid_from`.
- Exclusão GiST de intervalos sobrepostos para a mesma
  combinação `(resource_id, tag_id, assignment_source)`.

Os intervalos utilizam a semântica `[valid_from, valid_until)`.
Um limite superior nulo representa uma atribuição sem data
de término definida.

São permitidos intervalos consecutivos sem sobreposição.
A mesma etiqueta pode coexistir no mesmo recurso quando
as origens de atribuição são diferentes.

Índices adicionais:
- `(resource_id, valid_until)`.
- `(tag_id, valid_until)`.

A migração utiliza `btree_gist`, instalando a extensão quando
necessário. O downgrade preserva a extensão, por ser partilhada
com outras estruturas do inventário.

Não foram implementados nesta etapa serviços de atribuição,
normalização automática, workers, auditoria de alterações
nem reavaliação automática de grupos.

### Validação da F0.64B

**Estado:** Concluída.

Validações realizadas:
- 12 testes estruturais específicos do modelo `ResourceTag`.
- 89 testes Python aprovados na suite completa.
- Sintaxe Python e SQL offline da migração inspecionados.
- Migração aplicada exclusivamente em `livenet_f0_test`.
- Estrutura PostgreSQL confirmada: 7 colunas, 2 constraints
  CHECK, 2 chaves estrangeiras e 1 exclusão GiST.
- Quatro índices confirmados, incluindo PK e GiST.
- 9 testes de integridade PostgreSQL aprovados.
- 4 testes de atualização temporal aprovados.
- 3 verificações de concorrência aprovadas.
- Rejeição de atribuição concorrente sobreposta confirmada.
- Dados temporários eliminados e ausência de registos verificada.
- Downgrade para `7c4e2a91b605` validado.
- Reaplicação do upgrade para `9e1b7c42a630` validada.
- Extensão `btree_gist` preservada no downgrade.
- Tabela recriada sem registos.

A base principal `livenet` não recebeu esta migração.

### Estado da INV-05A após a F0.64B

A implementação física inicial das duas tabelas está validada:

- F0.64A: `inventory.tags`.
- F0.64B: `inventory.resource_tags`.

A conclusão destas etapas não representa a conclusão
funcional da INV-05A.

Permanecem pendentes a camada de serviços, a normalização
automática na entrada, a gestão funcional das atribuições,
a auditoria, a integração com grupos dinâmicos e os
mecanismos de arquivamento e reavaliação associados.

### F0.65A — inventory.policies

**Estado:** Implementada e validada em ambiente de testes.

**Contrato de referência:** INV-06A / DAT-10A.

**Migração Alembic:** `c4a91e7b205d`, dependente de
`9e1b7c42a630`.

A tabela `inventory.policies` representa o catálogo de
políticas do LiveNet v2. Nesta etapa, apenas a estrutura
física do catálogo foi implementada, sem versões,
atribuições ou cálculo de configurações efetivas.

Colunas implementadas:
- `id UUID` — chave primária, gerada pela aplicação.
- `name VARCHAR(255)` — obrigatório.
- `policy_type VARCHAR(64)` — obrigatório.
- `description TEXT` — opcional.
- `enabled BOOLEAN` — obrigatório, default `true`.
- `created_at TIMESTAMPTZ` — obrigatório, default `now()`.
- `updated_at TIMESTAMPTZ` — obrigatório, default `now()`.
- `archived_at TIMESTAMPTZ` — opcional.

### F0.65A-C01 — Integridade do catálogo de políticas

**Estado:** Aprovada e implementada.

Constraints implementadas:
- `ck_policies_name_not_empty`:
  `length(btrim(name)) > 0`.
- `ck_policies_type_normalized`:
  `policy_type = lower(btrim(policy_type)) AND length(policy_type) > 0`.
- `ck_policies_timestamps`:
  `updated_at >= created_at`.
- `ck_policies_archived_at`:
  `archived_at IS NULL OR archived_at >= created_at`.

Regras adicionais:
- O nome não possui constraint de unicidade; nomes duplicados
  são permitidos.
- `policy_type` deve ser fornecido normalizado, em minúsculas
  e sem espaços nas extremidades.
- Não foi introduzida uma enumeração fechada de tipos de política.
- `archived_at` é independente de `enabled` ao nível da base
  de dados.
- Uma política arquivada não deverá ser aplicada pela futura
  camada de serviços.
- A geração de UUID é responsabilidade da aplicação.
- Não foi introduzido mecanismo automático de atualização
  de `updated_at`.

### Validação da F0.65A

**Estado:** Concluída em ambiente de testes.

Validações realizadas:
- 10 testes estruturais específicos do modelo `Policy`.
- 99 testes Python aprovados na suite completa.
- Sintaxe Python e cadeia de revisões Alembic verificadas.
- SQL offline da migração gerado e inspecionado.
- Migração aplicada exclusivamente em `livenet_f0_test`.
- Estrutura PostgreSQL confirmada: 8 colunas, chave primária
  UUID e 4 constraints CHECK.
- Defaults de `enabled`, `created_at` e `updated_at` confirmados.
- Inserção válida e aplicação de defaults verificadas.
- Rejeição de nomes vazios confirmada.
- Rejeição de `policy_type` não normalizado confirmada.
- Rejeição de timestamps inconsistentes confirmada.
- Rejeição de arquivamento temporal inválido confirmada.
- Aceitação de nomes duplicados confirmada.
- Independência entre `archived_at` e `enabled` confirmada.
- Testes de integridade executados com ROLLBACK.
- Downgrade para `9e1b7c42a630` validado.
- Ausência da tabela após downgrade confirmada.
- Reaplicação do upgrade para `c4a91e7b205d` validada.

A base principal `livenet` não recebeu esta migração.

### Estado da INV-06A após a F0.65A

A implementação física inicial do catálogo de políticas
está validada:

- F0.65A: `inventory.policies`.

Permanecem por implementar em fases posteriores:
- `inventory.policy_versions`.
- `inventory.policy_assignments`.
- `inventory.effective_configs`.

Também permanecem pendentes a camada de serviços, a
validação funcional das definições, a publicação e
atribuição de versões, a resolução determinística de
precedências, a rastreabilidade, a integração com RBAC,
a auditoria e os mecanismos de aplicação e reavaliação.

A conclusão da F0.65A não representa a conclusão
funcional da INV-06A.

### F0.65B — inventory.policy_versions

**Estado:** Implementada e validada em ambiente de testes.

**Contrato de referência:** INV-06A / DAT-10A.

**Migração Alembic:** `e65b01a7c230`, dependente de
`c4a91e7b205d`.

A tabela `inventory.policy_versions` armazena versões
individuais das definições das políticas do LiveNet v2.

Cada versão pertence a uma política existente e possui
uma numeração positiva, única no contexto dessa política.

Colunas implementadas:
- `id UUID` — chave primária, gerada pela aplicação.
- `policy_id UUID` — FK obrigatória para `inventory.policies`.
- `version INTEGER` — obrigatório e positivo.
- `definition JSONB` — obrigatório, contendo um objeto JSON.
- `created_at TIMESTAMPTZ` — obrigatório, default `now()`.
- `created_by UUID` — opcional, sem FK nesta fase.

### F0.65B-C01 — Integridade e imutabilidade das versões

**Estado:** Aprovada e implementada.

Constraints implementadas:
- `ck_policy_versions_version_positive`:
  `version > 0`.
- `ck_policy_versions_definition_object`:
  `jsonb_typeof(definition) = 'object'`.
- `uq_policy_versions_policy_version`:
  unicidade de `(policy_id, version)`.
- FK de `policy_id` para `inventory.policies.id`,
  sem eliminação em cascata.

A numeração sequencial, iniciada em 1, será assegurada
pela futura camada de serviços. A base de dados garante
positividade e unicidade, mas não continuidade numérica.

A validação semântica de `definition` permanece
responsabilidade da futura camada de domínio.

A coluna `created_by` não possui FK enquanto o modelo
de identidade e RBAC aplicável não estiver definido.

**Imutabilidade:**

A decisão F0.65B-C01 reforça a regra original da
INV-06A, que estabelecia a imutabilidade das versões
publicadas. Todas as versões passam a ser imutáveis
desde a sua criação, independentemente do estado
de publicação.

A função PostgreSQL
`inventory.prevent_policy_version_mutation()`
e o trigger `trg_policy_versions_immutable` impedem
operações `UPDATE` e `DELETE` sobre os registos de
`inventory.policy_versions`.

As operações rejeitadas produzem SQLSTATE `23514`.
Qualquer correção de uma definição exige a criação
de uma nova versão.

Não foram implementados nesta etapa mecanismos
funcionais de publicação, aprovação ou atribuição
de versões.

### Validação da F0.65B

**Estado:** Concluída em ambiente de testes.

Validações realizadas:
- 11 testes estruturais específicos de `PolicyVersion`.
- 110 testes Python aprovados na suite completa.
- Sintaxe Python e cadeia de revisões Alembic verificadas.
- SQL offline da migração gerado e inspecionado.
- Migração aplicada exclusivamente em `livenet_f0_test`.
- Estrutura PostgreSQL confirmada: 6 colunas,
  5 constraints e trigger de imutabilidade.
- Inserção de versão válida confirmada.
- Rejeição de `UPDATE` e `DELETE` confirmada.
- Preservação da versão original confirmada.
- Rejeição de versão zero confirmada.
- Rejeição de numeração duplicada confirmada.
- Rejeição de definição JSONB do tipo array confirmada.
- Rejeição de referência a política inexistente confirmada.
- Testes de integridade executados com ROLLBACK.
- Downgrade para `c4a91e7b205d` validado.
- Remoção da tabela, função e trigger confirmada.
- Preservação de `inventory.policies` confirmada.
- Reaplicação do upgrade para `e65b01a7c230` validada.

A base principal `livenet` não recebeu esta migração.

### Estado da INV-06A após a F0.65B

A implementação física encontra-se validada para:
- F0.65A: `inventory.policies`.
- F0.65B: `inventory.policy_versions`.

Permanecem por implementar em fases posteriores:
- `inventory.policy_assignments`.
- `inventory.effective_configs`.

Também permanecem pendentes a camada de serviços,
a validação funcional das definições, a publicação
e atribuição de versões, a resolução determinística
de precedências, a rastreabilidade, a integração
com RBAC, a auditoria e os mecanismos de aplicação
e reavaliação.

A conclusão da F0.65B não representa a conclusão
funcional da INV-06A.
### F0.65C — inventory.policy_assignments

**Estado:** Implementada e validada em ambiente de testes.

**Contrato de referência:** INV-06A / DAT-10A / F0.65C-C01.

**Migração Alembic:** `f065c01a7230`, dependente de
`e65b01a7c230`.

A tabela `inventory.policy_assignments` representa
atribuições temporais de versões de políticas a três
âmbitos: global, grupo e recurso.

Colunas implementadas:

- `id UUID` — chave primária, gerada pela aplicação.
- `policy_version_id UUID` — FK obrigatória para
  `inventory.policy_versions`.
- `scope_type VARCHAR(32)` — obrigatório; valores
  `global`, `group` ou `resource`.
- `group_id UUID` — FK opcional para `inventory.groups`.
- `resource_id UUID` — FK opcional para `inventory.resources`.
- `priority INTEGER` — obrigatório, sem default.
- `valid_from TIMESTAMPTZ` — obrigatório.
- `valid_until TIMESTAMPTZ` — opcional.
- `created_at TIMESTAMPTZ` — obrigatório, default `now()`.

As três FKs não possuem eliminação em cascata.

### F0.65C-C01 — Integridade das atribuições

**Estado:** Aprovada e implementada.

A constraint `ck_policy_assignments_scope` garante:

- `global`: `group_id` e `resource_id` nulos.
- `group`: `group_id` obrigatório e `resource_id` nulo.
- `resource`: `resource_id` obrigatório e `group_id` nulo.

A constraint `ck_policy_assignments_validity` exige
`valid_until > valid_from`, quando `valid_until` existe.

A validade temporal utiliza intervalos semiabertos
`[valid_from, valid_until)`. A ausência de `valid_until`
representa um intervalo sem limite superior definido.

A decisão F0.65C-C01 impede sobreposições temporais
da mesma versão de política no mesmo destino.

Foram implementadas três constraints de exclusão GiST
parciais:

- `ex_policy_assignments_global_overlap`:
  mesma `policy_version_id`, âmbito `global`.
- `ex_policy_assignments_group_overlap`:
  mesma `policy_version_id` e `group_id`,
  âmbito `group`.
- `ex_policy_assignments_resource_overlap`:
  mesma `policy_version_id` e `resource_id`,
  âmbito `resource`.

Cada exclusão compara os intervalos através de
`tstzrange(valid_from, valid_until, '[)')` e do
operador de sobreposição `&&`.

As constraints utilizam filtros `WHERE` por âmbito,
evitando problemas de comparação com identificadores
nulos nos restantes âmbitos.

A extensão PostgreSQL `btree_gist` é necessária
e encontrava-se instalada na base de testes,
na versão 1.7.

A coexistência temporal de versões diferentes é
permitida. A resolução de prioridades, conflitos e
precedências pertence à futura camada de serviços.

A precedência arquitetural prevista na INV-06A é:
`resource > group > global`.

A prioridade explícita entre grupos, a resolução
determinística de empates e a sinalização de conflitos
incompatíveis continuam por implementar.

Não foram acrescentadas nesta fase regras de
imutabilidade, publicação ou aprovação das atribuições.

### Validação da F0.65C

**Estado:** Concluída em ambiente de testes.

Validações realizadas:

- 10 testes estruturais específicos de `PolicyAssignment`.
- 120 testes Python aprovados na suite completa.
- Sintaxe Python e cadeia Alembic verificadas.
- SQL PostgreSQL do modelo compilado e inspecionado.
- Migração aplicada exclusivamente em `livenet_f0_test`.
- Estrutura PostgreSQL confirmada: 9 colunas e
  9 constraints, incluindo 3 exclusões GiST parciais.
- Rejeição de combinações inválidas de âmbito.
- Rejeição de intervalos temporais invertidos.
- Rejeição de sobreposições da mesma versão e destino
  nos três âmbitos.
- Aceitação de intervalos consecutivos nos três âmbitos.
- Coexistência de versões diferentes nos três âmbitos.
- Testes funcionais executados com `ROLLBACK`.
- Confirmação de zero atribuições persistidas.
- Downgrade para `e65b01a7c230` validado.
- Remoção da tabela no downgrade confirmada.
- Reaplicação do upgrade para `f065c01a7230` validada.

A base principal `livenet` não recebeu esta migração.

### Estado da INV-06A após a F0.65C

A implementação física encontra-se validada para:

- F0.65A: `inventory.policies`.
- F0.65B: `inventory.policy_versions`.
- F0.65C: `inventory.policy_assignments`.

Permanece por implementar na fase física seguinte:

- F0.65D: `inventory.effective_configs`.

Continuam pendentes os serviços de atribuição e
resolução de políticas, validação semântica das
definições, publicação e aprovação, cálculo de
configurações efetivas, rastreabilidade, RBAC,
auditoria, aplicação e reavaliação.

A conclusão da F0.65C não representa a conclusão
funcional da INV-06A.

### F0.65D — inventory.effective_configs

**Estado:** Implementada e validada em ambiente de testes.

**Contrato de referência:** INV-06A / DAT-10A / F0.65D-C01.

**Migração Alembic:** `f065d01a7230`, dependente de
`f065c01a7230`.

A tabela `inventory.effective_configs` armazena a
configuração efetiva calculada para cada recurso e
tipo de política.

É uma tabela derivada e reconstruível, não constituindo
a fonte de verdade das políticas.

Colunas implementadas:

- `id UUID` — chave primária, gerada pela aplicação.
- `resource_id UUID` — FK obrigatória para
  `inventory.resources`, sem eliminação em cascata.
- `policy_type VARCHAR(64)` — obrigatório e não vazio.
- `resolved_config JSONB` — obrigatório, objeto JSON.
- `resolution_trace JSONB` — obrigatório, objeto JSON.
- `calculated_at TIMESTAMPTZ` — obrigatório.
- `revision INTEGER` — obrigatório e positivo.

Não existem valores por defeito para os campos de
cálculo, rastreabilidade ou revisão.

### F0.65D-C01 — Integridade das configurações efetivas

**Estado:** Aprovada e implementada.

A constraint
`uq_effective_configs_resource_policy_type`
garante a unicidade de `(resource_id, policy_type)`.

Consequentemente, a tabela representa apenas uma
configuração efetiva por recurso e tipo de política,
não mantendo o histórico de cálculos anteriores.

Constraints CHECK implementadas:

- `ck_effective_configs_policy_type_not_empty`:
  `length(btrim(policy_type)) > 0`.
- `ck_effective_configs_resolved_config_object`:
  `jsonb_typeof(resolved_config) = 'object'`.
- `ck_effective_configs_resolution_trace_object`:
  `jsonb_typeof(resolution_trace) = 'object'`.
- `ck_effective_configs_revision_positive`:
  `revision > 0`.

A FK de `resource_id` assegura a existência do recurso
associado, sem utilizar `ON DELETE CASCADE`.

A coluna `revision` representa a revisão da
configuração efetiva no contexto do par
`(resource_id, policy_type)`.

A primeira configuração persistida deverá utilizar
a revisão 1. O incremento das revisões e o controlo
de concorrência pertencem à futura camada de serviços.

A base de dados garante apenas que a revisão é positiva.

Os documentos `resolved_config` e `resolution_trace`
devem ser objetos JSONB. A validação semântica dos
respetivos conteúdos será definida com o motor de
resolução de políticas.

### Validação da F0.65D

**Estado:** Concluída em ambiente de testes.

Validações realizadas:

- 10 testes estruturais específicos de `EffectiveConfig`.
- 130 testes Python aprovados na suite completa.
- Sintaxe Python e cadeia Alembic verificadas.
- SQL PostgreSQL do modelo compilado e inspecionado.
- Migração aplicada exclusivamente em `livenet_f0_test`.
- Estrutura confirmada: 7 colunas obrigatórias e
  7 constraints (PK, FK, UNIQUE e quatro CHECK).
- Inserção de configuração válida confirmada.
- Coexistência de tipos de política diferentes confirmada.
- Rejeição de duplicados por recurso e tipo confirmada.
- Rejeição de tipo de política vazio confirmada.
- Rejeição de JSONB do tipo array em ambos os campos.
- Rejeição de revisões zero e negativas.
- Rejeição de referência a recurso inexistente.
- Testes funcionais executados com `ROLLBACK`.
- Confirmação de zero configurações persistidas.
- Downgrade para `f065c01a7230` validado.
- Remoção da tabela no downgrade confirmada.
- Reaplicação do upgrade para `f065d01a7230` validada.

A base principal `livenet` não recebeu esta migração.

### Estado da INV-06A após a F0.65D

A implementação física das quatro tabelas previstas
para as políticas encontra-se validada:

- F0.65A: `inventory.policies`.
- F0.65B: `inventory.policy_versions`.
- F0.65C: `inventory.policy_assignments`.
- F0.65D: `inventory.effective_configs`.

A implementação física não representa a conclusão
funcional do subsistema de políticas.

Permanecem pendentes a camada de serviços, o motor
de resolução, a validação semântica, a publicação e
aprovação, a aplicação de políticas, a invalidação e
reconstrução de configurações, o controlo de
concorrência, a rastreabilidade funcional, a integração
com RBAC e a auditoria.

As regras arquiteturais de precedência
`resource > group > global`, prioridade entre grupos,
resolução determinística de empates, deteção de
conflitos e avaliação idempotente permanecem
reservadas para a implementação funcional.
