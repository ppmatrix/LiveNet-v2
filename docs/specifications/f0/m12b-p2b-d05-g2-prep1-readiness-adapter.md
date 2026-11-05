# M1.2B-P2B-D05-G2-PREP1 — Adaptador de readiness offline

Atualização G2-FIX1: os cinco achados REV1-01 a REV1-05 receberam correções
offline nos mesmos módulos. Os resultados e o estado Git da secção histórica
G2-PREP1 abaixo referem-se à execução original. O contrato atual é
`D05-G2-FIX1-v2`; ver [relatório FIX1](m12b-p2b-d05-g2-fix1.md) para os testes,
alterações e limitações atuais. G2 não fica validada por esta atualização;
G3-REV2 e G4 não foram iniciados.

## Âmbito e resultado

Implementação exclusivamente offline, sobre `main`, HEAD
`647179c928888adfeef0f69f582fd13c5fc17350`. Staging inicialmente vazio.
Os 228 ficheiros preexistentes não ignorados foram inventariados por SHA-256
antes das alterações. Não foram modificados. Foram criados apenas os sete
ficheiros enumerados abaixo; não houve staging, commit ou push.

Implementados: política D05 imutável/versionada; catálogo Q1–Q16; normalização;
avaliação integral contra manifesto aprovado; orquestração injetável;
construção do contrato `ReadinessObservation`; testes adversariais.

**Não validado em PostgreSQL real. Não autorizado operacionalmente.**
Não há driver, executor PostgreSQL funcional, conexão no import, CLI,
registo na factory, descoberta de credenciais, fallback ou flag de ativação.
Não foram executados PostgreSQL, SQL real, Docker, Alembic, GRANTs ou roles.
Backend dedicado, login e os executores anteriores permanecem desativados.
Não se iniciou G3, G4 ou qualquer outro gate.

## Decisões vinculativas

D05 mantém os `SELECT FOR UPDATE` existentes em utilizadores e sessões.
Permite UPDATE apenas em `local_users.updated_at` e em
`login_sessions.last_activity_at/revoked_at`. O risco da escrita efetiva em
`updated_at` foi aceite arquiteturalmente; o probe não realiza essa escrita.
Inventário permanece apenas de consulta neste perfil.

Condições G1: runtime/verificador podem coexistir no processo, com credenciais
e conexões separadas; limites são provisórios até G4; inventário integral e
recusa de extras; desenho de ambiente isolado aprovado, criação não autorizada;
alterações detetadas de ACL invalidam readiness até revalidação explícita.
Administração permanece independente, sem fallback para bootstrap.

## Ficheiros e interfaces

| Ficheiro criado | Responsabilidade |
| --- | --- |
| `backend/app/readiness_postgres/__init__.py` | Pacote sem inicialização operacional |
| `backend/app/readiness_postgres/policy.py` | `Policy`, `Limits`, matriz, normalização canónica, digest e erro sanitizado |
| `backend/app/readiness_postgres/queries.py` | `Query` e catálogo fixo Q1–Q16 |
| `backend/app/readiness_postgres/evaluate.py` | Coerência, cobertura, comparação e observação |
| `backend/app/readiness_postgres/adapter.py` | `OfflineReadinessAdapter`, `Batch`, executor sintético e executor real bloqueado |
| `backend/tests/test_readiness_postgres.py` | Fixtures sintéticas e testes offline |
| Este documento | Contratos, resultados, limitações e gates futuros |

`OfflineReadinessAdapter.__call__()` preserva
`checker: Callable[[], ReadinessObservation]`. Factories runtime e verifier,
executor, política, relógio monotónico e limites são injetados explicitamente.
Não se alteraram `readiness.py`, `dedicated.py`, a factory original ou os
testes anteriores. Não foi acrescentada dependência de software.

O executor por omissão é `DisabledPostgresExecutor`: recusa antes das factories.
Somente o tipo exato `OfflineExecutor`, que devolve batches estáticos sintéticos,
é aceite para testar o fluxo. Não existe executor SQL real implementado.
As factories de teste recebem destino explícito, timeout e deadline, devolvendo
doubles distintos; `begin()` recebe READ ONLY / REPEATABLE READ e opções.
Um transporte futuro terá de impor e comprovar essas condições no servidor.
O resultado JSON de cada SELECT é uma coluna `evidence`, contendo um array;
um transporte futuro deverá descodificá-lo, verificar EOF e fornecer `Batch`.

Injeção de dependências é código Python de confiança, não um sandbox contra
callbacks maliciosos. Nenhuma evidência sintética deve ser ligada à readiness
de uma aplicação real. A factory atual não importa nem instancia este pacote.

## Política de privilégios

| Relação runtime | SELECT | INSERT | UPDATE |
| --- | --- | --- | --- |
| `security.local_users` | 6 colunas ORM | Não | `updated_at` |
| `security.login_sessions` | 7 colunas ORM | 7 colunas | `last_activity_at`, `revoked_at` |
| `security.global_role_grants` | 6 colunas ORM | Não | Não |
| `security.login_throttles` | 3 colunas | 3 colunas | `window_started_at`, `attempts` |
| `audit.events` | Não | 12 colunas emitidas | Não |
| `inventory.resources` | 10 colunas ORM | Não | Não |

DELETE, TRUNCATE, REFERENCES, TRIGGER e grant options são proibidos nas relações
aplicacionais. SELECT/INSERT podem resultar de direitos por coluna; UPDATE de
tabela inteira é sempre recusado. As restantes tabelas inventory e os dois
ledgers não têm acesso runtime. Não se geram GRANTs.

CONNECT na base aprovada; CREATE/TEMPORARY proibidos. USAGE runtime nos schemas
security/inventory/audit, sem CREATE. USAGE public pode constar do manifesto;
os direitos de catálogos de sistema exigem aprovação explícita. Verificador:
SELECT dos dois ledgers e metadados aprovados, sem leitura/escrita aplicacional,
ownership, administração, memberships ou DDL. A execução de `pg_control_system()`
requer autorização específica futura, sem recurso a administração se falhar.

Sem SUPERUSER, CREATEDB, CREATEROLE, REPLICATION ou BYPASSRLS; sem memberships
diretas/transitivas/SET ROLE, ownership ou privilégios preventivos em sequences.
PUBLIC não fornece acesso aplicacional. Default ACLs para PUBLIC/runtime/verifier
são recusadas; as de outros sujeitos devem corresponder exatamente ao manifesto.
ACLs de tipos e linguagens podem conter USAGE aprovado; capacidades em FDWs,
foreign servers, tablespaces e large objects para estes sujeitos são recusadas.

O trigger f066 `audit.prevent_event_mutation()` é SECURITY INVOKER. O perfil
aceita a sua assinatura sem argumentos, linguagem plpgsql e configuração nula,
com owner, ACL e hash da definição fixados no manifesto revisto. Não permite
aprovar um SECURITY DEFINER aplicacional acessível através desse nome. Rotinas
de sistema também exigem inventário/hash/configuração/ACL exatos; não se infere
segurança de uma rotina apenas por ser SECURITY INVOKER.

## Manifesto e evidência

`Policy` é frozen e contém apenas dados não secretos: versão `D05-G2-FIX1-v2`,
destino lógico, role verificadora, endereço IP, versão PG16 exata,
system_identifier, resultados esperados Q2–Q14/Q16 e digest de aprovação.
O digest SHA-256 vincula todos esses campos, incluindo destino e versão.
Não é assinatura nem autoridade de aprovação. O chamador de confiança deve
obter o manifesto completo de um processo independente de revisão/provisionamento.
Não se calcula uma baseline esperada a partir do servidor que se pretende provar.

**Não foi fornecido ou criado um manifesto físico aprovado para operação real.**
As fixtures têm metadados simplificados e explicitamente sintéticos; não provam
tipos, constraints, triggers, ACLs ou build de qualquer base existente.

Normalização aceita apenas escalares JSON tipados e arrays, converte arrays
em tuples, ordena linhas sem depender da ordem SQL e recusa duplicados,
excesso de cardinalidade, resultados ausentes, incompletos ou não tipados.
Comparação canónica distingue bool de int. NULL indispensável em identidade,
privilégios ou estrutura é recusado; NULL estrutural legítimo (default ausente,
proconfig ausente, hash não aplicável) só é aceite nas posições previstas.

Exige todos os Q, ambas as identidades, IP normalizado e mesma família,
database/current_user/session_user/port/version exatos, READ ONLY,
REPEATABLE READ, search_path `pg_catalog`, ambos os ledgers e identidade física.
Confere todas as células de privilégios por relação/coluna com Q13, schemas,
as 19 relações de negócio/ledgers e todas as suas colunas. FIX1 exige cobertura
das 23 classes de ownership, identidades/owners cruzados, contagens globais e
por relação em Q14, PK/FK/UNIQUE/CHECK/EXCLUDE e índices obrigatórios, os triggers
de imutabilidade audit e policy_versions, e RLS compatível. Regras de tabelas
aplicacionais não são aprovadas neste perfil; `_RETURN` de views de sistema
é observado separadamente. Relações físicas abrangidas exigem persistência p.
O manifesto fixa também objetos de sistema, índices, tipos, owners, rotinas e definições.
Qualquer linha extra ou divergente impede uma observação positiva.

Os booleans do contrato anterior são construídos só depois da avaliação integral;
não substituem resultados ausentes. Não há cache de observações positivas.
Divergência observada Q2–Q12 ativa um bloqueio partilhado por instâncias com a
mesma política/destino, em memória. `revalidate(approved_policy)` é uma ação
explícita de código de confiança: apenas limpa o bloqueio, sem emitir prova;
a próxima chamada repete todas as consultas. Não existe endpoint para isso.
Um lock não bloqueante partilhado recusa recolhas concorrentes no mesmo processo.

## Catálogo Q1–Q16

Cada consulta devolve arrays JSON, sem LIMIT, dados de utilizadores/sessões,
FOR UPDATE, funções aplicacionais, DML ou DDL. Nomes de objetos são constantes;
roles são bind parameters `:runtime_role`/`:verifier_role`. `current_user` e
`session_user` usam a sintaxe especial PostgreSQL, sem parênteses.

| Família | Evidência |
| --- | --- |
| Q1 | Identidade e opções da sessão, em runtime e verifier |
| Q2 | Atributos e OIDs das duas roles |
| Q3 | MEMBER/USAGE/SET transitivos e todas as edges, com flags PG16 |
| Q4 | USAGE/CREATE e grant options em todos os schemas |
| Q5 | Todas as sete capacidades de tabela e grant options |
| Q6 | SELECT/INSERT/UPDATE/REFERENCES por coluna e grant options |
| Q7 | USAGE/SELECT/UPDATE de sequences e grant options |
| Q8 | Owners/OIDs em 23 catálogos, contagens de cobertura, dependências de ownership |
| Q9 | CONNECT/CREATE/TEMPORARY; ACL de parâmetros; ACLs integrais de seis outras classes |
| Q10 | ACLs integrais PUBLIC/não-PUBLIC, headers mesmo vazios, owner, modo default/explicit e ACEs |
| Q11 | Inventário de rotinas, assinatura, owner, definer, linguagem, configuração, execução e hash |
| Q12 | Headers de default ACLs mesmo vazias, grantor/grantee e contagens |
| Q13 | OIDs, relkind, relpersistence, colunas, tipos, nulabilidade, identity/generated e defaults |
| Q14 | Constraints, índices, triggers, regras via pg_rewrite, RLS e cobertura global/por relação |
| Q15 | Uma linha f066 e uma linha b12 nos ledgers independentes |
| Q16 | system_identifier e versões físicas de controlo/catálogo |

Diferenças/precisões face ao desenho SPEC1: Q2 inclui OIDs para correlacionar
memberships/default ACLs; Q8 não depende só de pg_shdepend (omite pinned objects);
Q9/Q10 incluem ACLs de classes não tabulares; `acldefault` usa **s** para sequence
e **S** para foreign server; attacl nula é vazia; pg_get_functiondef é usado
apenas para prokind f/p; só o hash sai do servidor. Nenhuma rotina aplicacional
é invocada. Templates revistos com documentação oficial PG16 e compilação de
binds SQLAlchemy offline, **sem validação sintática/semântica no servidor**.

Fontes: [funções e ACLs PG16](https://www.postgresql.org/docs/16/functions-info.html),
[memberships PG16](https://www.postgresql.org/docs/16/catalog-pg-auth-members.html),
[dependências partilhadas](https://www.postgresql.org/docs/16/catalog-pg-shdepend.html),
[catálogo de rotinas](https://www.postgresql.org/docs/16/catalog-pg-proc.html).

## Limites e limpeza

Connect ≤2 s por conexão; statement ≤500 ms, consultas pesadas ≤1 s;
lock_timeout 200 ms; idle_in_transaction_session_timeout 1 s; orçamento global
4 s incluindo recolha/avaliação/limpeza. Os limites podem ser reduzidos, não
aumentados. Prazo restante limita os timeouts passados às dependências.
Excesso individual ou global detetado depois de uma chamada recusa a observação.
Sem retries. Rollback e close tentados independentemente em cada conexão,
mesmo após falhas; falha de limpeza recusa sucesso. FIX1 liberta o lock num
finally exterior e volta a propagar a primeira interrupção BaseException
após as tentativas de limpeza, preservando a interrupção original da operação.
Isto não garante limpeza perante kill -9, falha do processo ou I/O bloqueante.
Para exceções comuns permanece o erro público único
`Readiness unavailable`, sem causa/contexto do driver ou logging de resultados.

Limites de linhas: Q1 1 por conexão; Q2 2; Q3 8192; Q4 256; Q5–Q7 262144 cada;
Q8/Q9/Q13/Q14 65536 cada; Q10 32768; Q11 16384; Q12 8192; Q15 2; Q16 1.
Orçamento agregado de JSON canónico 32 MiB. Os limites agregam duas identidades
onde aplicável e continuam provisórios; não significam capacidade medida.
O executor sintético recebe batches materializados. O transporte futuro deverá
contar bytes/linhas em streaming e recusar overflow sem truncagem silenciosa.

Checks de relógio não interrompem callbacks síncronos bloqueados. Timeouts
efetivos, cancelamento e limpeza limitada precisam de implementação/validação
do transporte em gate futuro. Não existe garantia operacional de quatro segundos.

## Testes e integridade

Execução com `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`,
Python `-B`, pytest `-p no:cacheprovider`, `PYTHONPATH=backend`.
Sem instalação de dependências. Sem novas caches no repositório.

- Suite nova: **298 PASS, 0 FAIL, 0 SKIP**.
- Suite nova + regressões readiness/dedicated/proxy/security/inventory e
  migrações/coordenador M1.2B offline: **1283 PASS, 0 FAIL, 0 SKIP**.
- Diagnóstico adicional AUTH-03: **97 PASS, 2 FAIL, 0 SKIP**.
  Os dois testes que exigem verify_bundle falham por manifesto historicamente
  desatualizado; os testes e o manifesto foram preservados, sem xfail/skip.
- `git diff --check` e verificação direta de whitespace dos sete novos ficheiros:
  PASS. O diff normal não inclui untracked, pelo que se verificaram diretamente.
- AUTH-03: 15/15 ficheiros iguais à baseline; ambos os bloqueios preservados.

Os 298 testes novos cobrem matriz, direitos mínimos por coluna, capacidades
proibidas, PUBLIC/default ACLs, memberships, owners, funções, estruturas/RLS,
identidades, revisões, valores NULL/tipos, cobertura, duplicados, overflow,
truncagem, timeouts individuais/globais, falhas de conexão/limpeza, sanitização,
invalidação/revalidação, concorrência, não cache, binds e ausência de ativação.
As conexões são doubles e os testes novos bloqueiam sockets de conexão.

**Dívida AUTH-03 preexistente:** o manifesto tem 31 entradas, enquanto a baseline
anterior a G2 já tinha 46 fontes abrangidas pelo seu algoritmo. Faltavam 15 fontes
e divergiam os hashes de `app/__init__.py`, `app/config.py`,
`app/core/model_registry.py` e `backend/requirements.txt`. O novo pacote acrescenta
mais cinco fontes ao conjunto calculado, mas não originou a falha inicial.
Não se atualizou nem contornou essa guarda. Preservação dos 15 ficheiros não
equivale a aprovação do bundle pelo manifesto antigo.

## Riscos, G3 e G4

G3 deverá rever a política e os templates completos, a normalização e o processo
de aprovação do manifesto; decidir a estratégia para OIDs/definições que variam
entre instalações; confirmar a assinatura/hash do trigger f066 e o inventário
de rotinas do build; avaliar cobertura e custo dos catálogos, limites agregados,
memória e estado partilhado. O registo de scopes/latches é apenas em memória,
não persiste entre processos/restarts e deve permanecer limitado a políticas
estáticas de configuração de confiança. A aprovação não é criptograficamente
autenticada por este módulo. Não há garantia de exclusividade contra administradores.

O inventário exato pode recusar alterações benignas em catálogos de sistema,
schemas temporários, definições ou ACLs de terceiros. É conservador de propósito;
não há aceitação automática de novos objetos. Visibilidade insuficiente do
verificador, incluindo pg_subscription/controlo físico, deve falhar fechada.
Não se afirma que os privilégios necessários ao catálogo já estejam provisionados.

Conexões têm snapshots REPEATABLE READ separados; não há snapshot global comum,
prova contínua de ACLs nem eliminação de TOCTOU. Readiness não é uma barreira
de autorização por pedido. Mudar uma ACL e restaurá-la entre observações pode
escapar à deteção. system_identifier pode identificar clones físicos; endereço
e SID não substituem atestação de instância, transporte ou isolamento operacional.
Estes limites não são resolvidos por resultados sintéticos.

G4 exige autorização específica, ambiente PostgreSQL descartável independente,
credenciais próprias, manifesto completo aprovado por revisão independente,
transporte real revisto e validação dos SQL/privilegios/ORM/row locks/timeouts,
falhas e limites. O desenho do ambiente isolado permanece apenas aprovado em
papel. Não se usam os ambientes atuais nem se desbloqueia AUTH-03/M1.2B.
Permanecem pendentes exclusividade de escritores externos, recuperação
administrativa independente e gates operacionais M1.2B.

Próximo incremento mínimo recomendado: **revisão independente G3 deste código,
testes e contratos**, sem ativação ou criação de ambiente. G3–G8 não foram
iniciados nem autorizados por esta implementação.

Critério proposto para aprovação G3: nenhum achado crítico/alto por resolver,
matriz D05 e cobertura do catálogo confirmadas por revisão independente,
testes novos/regressões funcionais sem falhas, limites/proveniência explícitos
e ausência de caminho operacional. A dívida do manifesto AUTH-03 deve permanecer
identificada e não pode ser reparada implicitamente por esta aprovação.

## Estado Git final

HEAD preservado, branch main, staging vazio. Em relação à baseline, apenas
`readiness_postgres/`, o seu teste e este relatório foram acrescentados.
Todos os restantes registos abaixo são trabalho anterior preservado:

```text
 M backend/migrations/env.py
?? backend/app/dedicated.py
?? backend/app/readiness.py
?? backend/app/readiness_postgres/
?? backend/app/trusted_proxy.py
?? backend/migrations/versions/f067a01a7230_create_authorization_integrity_anchors.py
?? backend/tests/test_authorization_anchor_integration.py
?? backend/tests/test_authorization_anchor_migration.py
?? backend/tests/test_authorization_anchor_safety.py
?? backend/tests/test_dedicated_backend.py
?? backend/tests/test_readiness_contract.py
?? backend/tests/test_readiness_postgres.py
?? backend/tests/test_trusted_proxy.py
?? compose.auth03-executor.yaml
?? compose.auth03-test.yaml
?? compose.m12b-test.yaml
?? compose.web-dev.yaml
?? docs/specifications/f0/auth03-alembic-executor.md
?? docs/specifications/f0/auth03-integration-preparation.md
?? docs/specifications/f0/m12b-p2b-d05-g2-prep1-readiness-adapter.md
?? docs/specifications/f0/m12b-p2c2a-r3-operational-preflight.md
?? docs/specifications/f0/m13d-prep1-backend-https.md
?? infra/
?? scripts/postgres/auth03_alembic_executor.py
?? scripts/postgres/auth03_executor.Dockerfile
?? scripts/postgres/auth03_executor.Dockerfile.dockerignore
?? scripts/postgres/auth03_executor.example.json
?? scripts/postgres/auth03_executor_integrity.json
?? scripts/postgres/tests/test_auth03_alembic_executor.py
```

Não foram consultados nem operados contentores nesta etapa. A ausência de comandos
Docker preserva o âmbito autorizado; não constitui nova atestação do estado runtime
dos 23 contentores referidos no pedido. Não foram criadas credenciais ou segredos.
