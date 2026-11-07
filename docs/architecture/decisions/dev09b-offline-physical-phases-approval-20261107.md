# DEV09B — autorização do terceiro bloco offline: sete perfis físicos

07/11/2026 · Europe/Lisbon

## Fonte e decisões aprovadas

Fonte primária: pedido humano nesta conversa «Implementar o terceiro bloco
offline DEV09B agora aprovado: os sete perfis físicos por fase e respetivos
comparadores». Base confirmada main `2f86582`, árvore inicialmente limpa.

Decisões expressamente aprovadas:

- btree_gist pré-instalado administrativamente, com parâmetros fixados no perfil
  do alvo; migrator/runtime sem poder de instalação.
- Owners finais NOLOGIN distintos para inventory, audit e cada ledger. Funções
  pertencem ao owner do domínio; sem ownership/memberships permanentes do migrator
  após handoff. Security mantém o owner NOLOGIN próprio previsto em DEV08B.
- ACL mínima explícita, revogações PUBLIC pertinentes e administração/recuperação
  separadas. Grants runtime não autorizados.
- Fixar distribuição/template PostgreSQL e verificar propriedades relevantes
  para identidade, privilégios, extensões e execução; catálogo LiveNet completo
  e recusa de extras nos schemas geridos. Identificar conflitos antes de reduzir
  cobertura, sem alterar contratos silenciosamente.

Autorizados apenas extração determinística das fontes, schemas/comparadores,
testes offline pertinentes, este ato e atualização sucinta de CONTINUITY.md.
Não constitui aprovação antecipada dos bytes implementados nem autorização
operacional. Os três atos DEV09B anteriores permanecem intactos.

## Sete perfis e sua interpretação

DEV-BASE; APP-F066-PRECOMMIT; APP-F066-PERSISTED; APP-F066-CLOSED;
SEC-B12-PRECOMMIT; SEC-B12-PERSISTED; SEC-B12-CLOSED.

PRECOMMIT mantém owners transitórios na mesma transação. PERSISTED mantém esses
owners até confirmação pós-commit independente. CLOSED exige handoff dos objetos
para owners NOLOGIN por domínio/ledger, revogação das capacidades temporárias e
preservação apenas da inspeção restrita autorizada. Nenhuma dessas fases autoriza
DML runtime, primeira conta ou disponibilização da aplicação.

Outra ligação não pode confirmar o DDL ainda não committed de PRECOMMIT.
Comparação independente é admissível apenas nos perfis PERSISTED/CLOSED, com
identidades/documentos distintos, mesmo sujeito de execução e interfaces de
autenticidade/independência. Dois hashes ou OPERATIONAL não bastam; o double
mantém classificação sintética e não autentica dados operacionais.

## Implementação e cobertura

- [migration_catalog.py](../../../scripts/dedicated/dev09b/migration_catalog.py):
  leitura AST das 13 revisões aplicacionais até f066 e raiz security b12, sem
  importar/chamar upgrade nem gerar/executar SQL. Construções desconhecidas são
  recusadas. Extração de schemas, tabelas, colunas/tipos/defaults, constraints,
  índices, funções e triggers, preservando ordem e nomes explícitos/implícitos
  suportados. Fontes identificadas por path/SHA-256.
- [physical.py](../../../scripts/dedicated/dev09b/physical.py): perfis versionados,
  snapshots de expectativas imutáveis e comparação estrita da representação
  normalizada. Expectativas são regeneradas dos inputs fixados, nunca das
  observações; bool/int são distintos. Inclusão explícita dos dois ledgers e
  respetivas PKs/índices segundo o contrato Alembic local consultado.
- Artefactos/distribuição/template/Alembic/SQLAlchemy, parâmetros de btree_gist,
  owners, ACL e memberships relevantes de sistema/extensão, e resolução de tipos
  implícitos/arrays/TOAST são inputs aprovados do alvo. Ausência causa
  MissingParameter com o caminho do valor necessário; não se inventam valores de
  um PostgreSQL observado. ACL efetivas/expandidas e owner são campos separados.
- Base significa ausência dos objetos geridos LiveNet, não cluster PostgreSQL
  vazio. Objetos de sistema/extensão são inventários separados. Famílias extras
  de LiveNet, resíduos, definições/owners/ACL divergentes ou truncadas são recusados.
- As definições extraídas são uma forma declarativa normalizada, não saída
  genérica de pg_get_*: não existe deparser/coletor real neste bloco. Valores
  dependentes de distribuição e objetos implícitos exigem fontes/resolução
  específicas, não um booleano que afirme cobertura completa.
- PhysicalComparison observa igualdade desses inputs normalizados; não é
  confirmação operacional, autorização, prova de fonte aprovada ou garantia C4.
  Fixtures positivas são sintéticas e não constituem baselines reais aprovadas.

## Conflito identificado e recusa preservada

As migrações criam schemas, exigindo CREATE na base. PostgreSQL permite ao
detentor de CREATE instalar extensões trusted: btree_gist já instalado não
elimina esse poder. Isso conflita com a decisão de migrator sem poder de
instalação. Os comparadores não dispensam o requisito: compare_profile recusa
PRECOMMIT/PERSISTED com Unsupported mesmo se todos os dados normalizados
coincidirem. A comparação parcial continua disponível, sem alegar validação
integral ou abrir gates.

Resolver exige mecanismo de imposição revisto que diferencie a instalação de
extensões, ou alteração explicitamente aprovada do percurso de preparação/
migrações. Não foi criada guarda fictícia, evento PostgreSQL, política nova ou
alteração às migrações para contornar este conflito.

O G2 histórico exige catálogo/ACL completos próprios. O novo recorte aprovado
de propriedades relevantes do sistema não é declarado equivalente a G2; os
validadores/perfis históricos e as suas recusas mantêm-se intactos. Não reduzir
silenciosamente a sua cobertura para ativar a entrega.

## Verificação e percurso funcional seguinte

[Testes offline](../../../scripts/postgres/tests/test_dev09b_physical.py) cobrem
os sete perfis, extração, sintaxe não suportada, defaults, owners de funções e
ledgers distintos, grants restritos, conflito CREATE, parâmetros em falta,
extras/truncação, tipos estritos, falsificação de expectativas e independência.
Não demonstram exclusividade real, durabilidade, estado PostgreSQL ou
interoperabilidade com um coletor real.

Sequência mínima: resolver o conflito de poder CREATE e fixar parâmetros do
alvo; implementar/rever os adaptadores guardados de autoridade/continuidade,
executor e readiness; autorizar alvo DEV segregado e preparação; executar as
duas migrações com confirmação independente e handoff; autorizar separadamente
grants D05/primeira conta/dados, serviços e HTTPS interno para login e consulta
Inventory persistente. Nenhuma dessas operações futuras é autorizada aqui.

Sem instalações, rede, PostgreSQL, SQL/migrações, provisionamento, handoff,
serviços, infraestrutura, abertura de gates, staging, commits ou pushes.
Progbox exclusivamente DEV; STAGING/PROD em VMs Proxmox; acesso interno.
