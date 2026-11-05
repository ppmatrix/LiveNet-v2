# DEV-08B — Contratos documentais de persistência

Data: 2026-10-25. Ambiente de preparação: progbox.

## Autoridade e âmbito

**DEV-08-D01/D02: desenho aprovado. DEV-08-D03: processo fase 1 aprovado; candidato não aprovado.** Fonte humana primária: pedido DEV-08B nesta conversa, anexo `9e646608-e14d-4575-8d04-84eaa4ca6301/Pasted text.txt`, Missão e §§2–5. O pedido declara expressamente aprovadas as três decisões com os limites da DEV-08. Esta referência é verificável nesta conversa, mas o anexo não integra um checkout.

Este contrato formaliza as decisões de [DEV-08](../../operations/dev08-persistence-decisions.md); não reconstrói decisões históricas ausentes. [Registo formal](../../architecture/decision-register.md), atualização DEV-08B, e [adenda DAT-05A](data-model.md), no final do documento, identificam a precedência limitada deste incremento.

A aprovação é documental/arquitetural. Não autoriza SQL, criação de bases/roles, migração, provisionamento, atualização do manifesto ativo, alteração de gates, serviços ou deploy. Código atual não passa a implementar novos perfis por existir este contrato.

## DEV-08-D01 — Identidade e isolamento

| Ambiente | Nome aprovado | Separação obrigatória |
| --- | --- | --- |
| DEV / progbox | `livenet_v2_dev` | Cluster PostgreSQL próprio v2 DEV |
| STAGING / VM Proxmox | `livenet_v2_staging` | Cluster próprio, independente de DEV |
| PROD-VM / futuro PROD-K8S | `livenet_v2_prod` | Cluster próprio de produção; transição VM→K8S controlada |

Todos são independentes do LiveNet v1 e dos outros ambientes: clusters/initdb, redes, volumes, credenciais, roles, chaves de sessão/CSRF, confiança TLS e backups. Não criar dois primários de produção graváveis independentes durante transição VM/K8S. Réplicas/DR requerem plano próprio.

Um destino aprovado vincula ambiente, base, role, endereço/porta, endpoint/certificado/CA, system identifier e proveniência independente de projeto/instância/rede/volume/imagem. Nome, DNS interno, RFC1918 ou system identifier isolado não bastam. Clones físicos podem conservar system identifier; restauros/clones exigem quarentena e reatestação. Nomes ainda não foram verificados quanto a colisões em infraestrutura operacional.

TLS PostgreSQL é **verify-full**, com validação de hostname e CA explícita, sem fallback para require/verify-ca ou confiança implícita. Ownership/permissões e paths privados continuam a ser validados; credenciais bootstrap/admin não entram no runtime. O endpoint real e a CA de cada ambiente ainda precisam de identificação e revisão. Acesso UI/API permanece LAN-only e HTTPS, sob DEV-05A-D01; esta decisão não altera origem, proxy, cookies ou CSRF.

### Schemas e fases

Manter seis domínios lógicos DAT-05A. Materializar inicialmente somente `inventory`, `audit` e `security`, além dos objetos públicos/ledgers de D02. Não criar antecipadamente schemas vazios discovery, monitoring ou operations: o catálogo exato G2 recusá-los-ia. `authorization` pertence exclusivamente ao perfil AUTH-03 isolado nesta fase.

A adenda DAT-05A altera explicitamente o nome literal e a materialização inicial do texto histórico, preservando limites de módulos, regras de evolução Alembic e restantes decisões DAT. O texto original foi mantido integralmente.

### Papéis e privilégios

| Padrão aprovado | Função |
| --- | --- |
| `lnv2_<env>_db_owner` | Owner NOLOGIN da base |
| `lnv2_<env>_inventory_owner` | Owner NOLOGIN inventory |
| `lnv2_<env>_audit_owner` | Owner NOLOGIN audit |
| `lnv2_<env>_security_owner` | Owner NOLOGIN security |
| `lnv2_<env>_migrator` | Migração controlada, NOINHERIT; memberships/SET ROLE apenas no âmbito explicitamente revisto |
| `lnv2_<env>_runtime` | Aplicação, sem ownership/admin/memberships de owners |
| `lnv2_<env>_inspector` | Inspeção readiness, apenas catálogos/ledgers aprovados |
| `lnv2_<env>_admin` | Administração/provisionamento/recuperação separados do backend |

`<env>` é dev, staging ou prod; são identidades distintas, sem memberships cruzadas. Nomes não criam privilégios. A matriz de grants/ownership, acessos temporários e ledgers exige revisão concreta antes de provisionamento. Não atribuir ao runtime superuser, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS, DDL, TEMPORARY ou administração de contas/grants.

O inspector readiness não herda os direitos de inspeção protegida dos executores históricos M1.2B. As fronteiras de inspector de migração, verifier G2, runtime e administração são distintas; não unir as suas permissões por conveniência.

`ENVIRONMENT=production` é o modo Flask seguro, inclusive em DEV/STAGING, não uma prova da identidade do deployment. Configuração dedicada continua explícita. Coordenar futuramente DATABASE_NAME do JSON, DEV04_DB_NAME no Compose e o destino atestado; não existe descoberta automática nem substituição global dos destinos históricos.

**Aceitação futura:** recusar v1/outro ambiente, role/CA/hostname/cluster divergentes, destino ambíguo, configuração implícita e excesso de privilégios. Provar ausência de operações PostgreSQL na construção da factory. Não alterar F02/G2/G4 para aceitar um novo nome.

## DEV-08-D02 — Revisões e ledgers independentes

| Perfil aprovado | Aplicação | Security | Catálogo |
| --- | --- | --- | --- |
| MVP DEV, STAGING e PROD-VM / futuro PROD-K8S | `f066a01a7230` | `b12b01a7230` | inventory/audit/security; sem authorization |
| AUTH-03 isolado | `f067a01a7230`, após f066 | Não aplicada por defeito | Âncoras authorization, separado do alvo MVP |
| Legado | Preservado | Preservado | Sem redirecionamento implícito |

### Grafo aplicacional verificado

| Revisão | down_revision | Fonte |
| --- | --- | --- |
| `af62df027d9d` | base | `backend/migrations/versions/af62df027d9d_create_inventory_resources_baseline.py` |
| `4f625db33d6d` | `af62df027d9d` | `backend/migrations/versions/4f625db33d6d_create_inventory_resource_identifiers.py` |
| `38d641dcd780` | `4f625db33d6d` | `backend/migrations/versions/38d641dcd780_create_inventory_resource_relations.py` |
| `da34876e4210` | `38d641dcd780` | `backend/migrations/versions/da34876e4210_create_inventory_groups.py` |
| `ba06dd956da9` | `da34876e4210` | `backend/migrations/versions/ba06dd956da9_create_inventory_group_memberships.py` |
| `44e7eb855b5a` | `ba06dd956da9` | `backend/migrations/versions/44e7eb855b5a_create_inventory_group_rules.py` |
| `7c4e2a91b605` | `44e7eb855b5a` | `backend/migrations/versions/7c4e2a91b605_create_inventory_tags.py` |
| `9e1b7c42a630` | `7c4e2a91b605` | `backend/migrations/versions/9e1b7c42a630_create_inventory_resource_tags.py` |
| `c4a91e7b205d` | `9e1b7c42a630` | `backend/migrations/versions/c4a91e7b205d_create_inventory_policies.py` |
| `e65b01a7c230` | `c4a91e7b205d` | `backend/migrations/versions/e65b01a7c230_create_inventory_policy_versions.py` |
| `f065c01a7230` | `e65b01a7c230` | `backend/migrations/versions/f065c01a7230_create_inventory_policy_assignments.py` |
| `f065d01a7230` | `f065c01a7230` | `backend/migrations/versions/f065d01a7230_create_inventory_effective_configs.py` |
| `f066a01a7230` | `f065d01a7230` | `backend/migrations/versions/f066a01a7230_create_audit_events_baseline.py` |
| `f067a01a7230` | `f066a01a7230` | `backend/migrations/versions/f067a01a7230_create_authorization_integrity_anchors.py` |

Ledger: `public.alembic_version`. As 12 primeiras revisões instalam inventário; f066 acrescenta audit.events e f067 acrescenta authorization.authorization_integrity_anchors. Head do grafo atual é f067, mas não é o destino autorizado do perfil MVP.

### Grafo security verificado

Base → `b12b01a7230`, sem down_revision/depends_on aplicacional. Fonte: `backend/security_migrations/versions/b12b01a7230_create_security.py:12–19`; ledger independente `public.alembic_security_version`.

Instala local_users, login_sessions, global_role_grants e login_throttles. O baseline f066 é uma pré-condição operacional, não uma dependência de grafo. Metadata/config/env próprios exigem ligação PostgreSQL externa com transação ativa; não introduzir URL, engine/fallback ou autogeração conjunta. Downgrade security continua recusado.

Fontes: `backend/security_migrations/contract.py:10–21,41–63`; `backend/security_migrations/env.py:12–22`; `backend/migrations/env.py:46–64`. Nenhum histórico, head, versão ou fonte de migração foi alterado nesta formalização.

### Dependências, btree_gist e grants

- Autenticação e inventário partilham o mecanismo de sessões (`backend/app/security/access.py:20–23`; `backend/app/dedicated.py:178–193`).
- Login precisa das tabelas security e de DML restrito em sessões/throttles, locks de users/sessions e INSERT audit; f067 não substitui esses objetos.
- O perfil D05 permite consulta apenas de inventory.resources, sem INSERT inventory. Não conceder acesso às restantes tabelas inventory ou aos ledgers ao runtime.
- D05 exige SELECT users/grants/sessions/throttles; INSERT sessions/throttles/audit; UPDATE apenas users.updated_at, sessions.last_activity_at/revoked_at e throttles.window_started_at/attempts. Sem DELETE/TRUNCATE/REFERENCES/TRIGGER/grant options, escrita de credenciais/grants, leitura audit ou DDL.
- `ba06dd956da9` e `9e1b7c42a630` invocam CREATE EXTENSION IF NOT EXISTS btree_gist (:23 em ambas). Instalação, versão, schema/owner e ACL dos seus objetos precisam de revisão prévia. Não conceder instalação de extensões ao runtime.
- Ownership final é independente da identidade runtime e da janela temporária do migrator; não antecipar transferência que invalide as verificações transacionais dos executores. Grants operacionais exigem plano separado, não derivado automaticamente dos nomes de roles.

### Catálogo G2 e readiness

Conjunto exato de schemas: public, inventory, audit, security, pg_catalog, information_schema e pg_toast (`backend/app/readiness_postgres/evaluate.py:63–78`). Relações de negócio: as 12 tabelas inventory, quatro security, audit.events e os dois ledgers; total 19. Metadados, rotinas, tipos, owners, defaults/ACL e catálogo de sistema também precisam de evidência completa aprovada; não basta contar tabelas. authorization ou outros schemas extra recusam o perfil atual.

Readiness requer identidade exata, evidência read-only fresca até cinco segundos, revisões f066/b12 e privilégios válidos. Ausência/falha → HTTP 503 (`backend/app/readiness.py:105–132`). O adaptador G2 é offline; executor real está desativado e o tipo sintético não é evidência operacional (`backend/app/readiness_postgres/adapter.py:23–38,122–125`). A fonte aprovada não equivale a um manifesto físico G2 aprovado nem a um gate aberto.

### Ordem futura condicionada de preparação

1. Concluir aprovação de fontes D03 e atestação complementar; rever identidade real, mecanismo/gates de execução, grants, ownership e recuperação. Sem isso, parar.
2. Só com autorização específica criar alvo PostgreSQL16 novo e descartável, initdb/CA/recursos próprios; provar identidade independentemente, base vazia e ausência de schemas/ledgers aplicacionais. Rever disponibilidade e poderes limitados para btree_gist.
3. No mecanismo aprovado, ligação externa/transação explícita, lock, validação de autorização, destino e origem: percorrer a cadeia completa base→f066 pelos IDs da tabela; confirmar catálogo e ledger antes do commit. O Alembic escreve a versão.
4. Em execução independente security, validar f066, fontes/configuração, identidade e janela autorizada; transação exterior base→b12; verificar quatro tabelas/constraints/FKs e ledger próprio antes do commit.
5. Concluir ownership/handoff e grants D05 sob plano autorizado, confirmando estado persistido. Provisionamento de conta/dados sintéticos por identidade de preparação separada, nunca factory/runtime.
6. Validar integração real sessões/throttles/audit/leitura resources, negações de privilégios e checker real autorizado. Só evidência válida e gates satisfeitos poderão justificar 200; até lá, 503.
7. AUTH-03 usa outro alvo descartável autorizado: base→f066 e depois f066→f067, sem security por defeito, sem misturar dados ou exigir que G2 MVP aceite authorization.
8. Recolher prova sanitizada e encerrar apenas recursos descartáveis de propriedade comprovada, conforme autorização específica.

Esta é ordem normativa futura, não um comando autorizado. Não chamar Alembic diretamente como contorno aos executores fechados. Proibidos head automático, stamp, alteração manual de ledger, reescrita de histórico e checker positivo simulado.

**Validação/reversão:** IDs completos e destino selecionados por perfil; grafos/ledgers intactos; catalogação/ACL completas e recusa de extras. Falhas antes do commit exigem rollback; commit incerto exige inspeção independente, sem retry automático. Não usar downgrade security; descarte só do alvo novo autorizado ou restauro aprovado de par fonte/manifesto e backup validado, sem tocar em bases persistentes por conveniência.

## DEV-08-D03 — Estado formal do processo

Fase 1 autorizada: revisão individual das 21 entradas ausentes e quatro hashes divergentes, inventário de cobertura e preparação de candidato fora dos gates. **Não autoriza inclusão/substituição automática.**

Fase 2 pendente: segunda aprovação humana explícita do candidato completo e concreto, dos seus digests e da disposição de todas as fontes locais. Só tarefa posterior autorizada poderá atualizar o manifesto ativo, preservando o par anterior correspondente de fontes/manifesto.

A matriz de 25 entradas e o inventário de 52 fontes estão no [candidato de revisão não aprovado](../../operations/dev08b-auth03-candidate.NOT-APPROVED.json); síntese, verificações e procedimentos no [relatório DEV-08B](../../operations/dev08b-persistence-formalization.md). Este envelope é documental, não um formato AUTH-03/F03/F04/G4 de autorização, não é consumido por gates e não deve ser copiado para o caminho ativo.

Proveniência Git, validação técnica offline e aprovação humana têm estados separados. Correspondência com manifesto antigo ou HEAD não prova aprovação original. Os nove artefactos locais novos exigem aceitação humana explícita; outros dois locais já constam do manifesto antigo. Fontes security/runtime/imagem fora do conjunto atual exigem atestação complementar própria, sem acrescentar extras ao manifesto nem alterar o verificador silenciosamente.

## Fronteiras preservadas e bloqueios restantes

Mantêm-se o catálogo/matriz D05-G2-FIX1-v2, F02 e os contratos G4, AUTH-03 e respetivas fronteiras de confiança. `scripts/postgres/g4/contracts.py:491–502` continua a recusar execução; `scripts/postgres/auth03_alembic_executor.py:56–59` recusa mutações; `scripts/postgres/m12b_security_migration.py:52–62` mantém execution_enabled=False.

O executor AUTH-03 histórico continua a fixar livenet_auth03_test e o security fixa livenet_m12b_test; não são os novos perfis por ambiente. O transporte AUTH-03 histórico também não passa a verify-full por aprovação documental. Preparar novos perfis/transportes exige tarefa e revisão específicas, sem relaxar controlos.

Continuam abertos: manifesto ativo divergente, candidato não aprovado, autoridade/gates operacionais ausentes, checker real desativado, runtime/ACL reais por validar, recuperação independente não demonstrada, atestação complementar e originais/lacunas G4/L02 não localizados. Não declarar qualquer gate ou integração persistente operacional.
