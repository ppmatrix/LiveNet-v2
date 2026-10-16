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
- `inventory.resource_tags`: implementação física pendente (F0.64B).
- Normalização na camada de serviços: pendente.
- Auditoria de alterações e integração com grupos dinâmicos:
  pendentes das respetivas fases funcionais.

A conclusão da F0.64A não representa a conclusão integral
da INV-05A.
