# M1.2B-P2B-D05-G2-FIX1 — Correções offline de REV1-01 a REV1-05

## Âmbito e baseline

Implementação e testes exclusivamente offline. Branch `main`, HEAD de referência
`647179c928888adfeef0f69f582fd13c5fc17350`, staging vazio. Inventário inicial:
235 ficheiros não ignorados, com SHA-256 capturados antes de qualquer alteração.
As alterações locais anteriores foram preservadas.

Alterados apenas `policy.py`, `queries.py`, `evaluate.py`, `adapter.py` em
`backend/app/readiness_postgres/`, `backend/tests/test_readiness_postgres.py` e
o relatório G2-PREP1. Criado apenas este relatório. O `__init__.py` permanece
byte-identical. Não foram alterados outros ficheiros, a factory ou migrações.

**G2 não é declarada validada. G3-REV2 e G4 não foram iniciados.** Não há
autorização operacional, transporte PostgreSQL funcional ou manifesto físico
aprovado para uma base real. Não se contactaram serviços nem se operou Docker.

## Correções por achado

| ID | Achado original | Correção offline |
| --- | --- | --- |
| REV1-01 HIGH | Regras não observadas | Q14 inventaria pg_rewrite, contexto de schema/relação, OIDs, nome, evento, INSTEAD, ativação e pg_get_ruledef(false). Cobertura por relação/global e validação separada de _RETURN de views de sistema |
| REV1-02 MEDIUM | Evidência/manifesto incompleto aceite | Política v2 com declarações mínimas, cobertura de ownership, identidades cruzadas, requisitos estruturais e de leitura dos catálogos; avaliação estrutural anterior à comparação final |
| REV1-03 MEDIUM | ACLs não-PUBLIC redundantes invisíveis | Q10 recolhe todos os ACEs e headers dos objetos mesmo vazios; owner, grantee, grantor, privilégio, grant option e distinção default/explicit; direitos efetivos continuam verificados separadamente |
| REV1-04 MEDIUM | Interrupção durante cleanup retém lock | finally exterior liberta o lock; todos os recursos recebem tentativas independentes de rollback/close; interrupções são preservadas e propagadas após limpeza |
| REV1-05 MEDIUM | Persistência não observada | Q13 inclui relpersistence; o perfil exige p nas relações físicas abrangidas e nas tabelas aplicacionais; ausência, u/t ou valor desconhecido recusam readiness |

## Política e cobertura

O contrato passou para `D05-G2-FIX1-v2`, invalidando políticas v1. O digest
continua a vincular identidade, versão e manifesto, sem representar uma
assinatura ou aprovação humana. Não se alterou a matriz D05 de operações.

`REQUIRED_STRUCTURE` e `REQUIRED_FOREIGN_KEYS` contêm requisitos mínimos
revistos a partir das declarações locais de modelos/migrações, sem importar
ou executar funções de migração: 19 tabelas/ledgers, todas as suas colunas,
19 PK, 15 FK, 6 UNIQUE, 50 CHECK, 5 EXCLUDE e 14 índices explícitos, além dos
índices de suporte. A contagem por tabela é exata para este perfil. Nomes
explicitamente declarados, PK nas colunas esperadas, referências FK e índices
de suporte são cruzados com a metadata observada. Definições canónicas
completas continuam dependentes do manifesto físico independente e de G4.

O avaliador distingue:

1. Batches recebidos e marcados completos, com limites e normalização.
2. Evidência estruturalmente coerente, sem duplicados de identidade ou UNKNOWN.
3. Política/manifesto aprovados por uma origem de confiança exterior.
4. Comparação exata final e construção de ReadinessObservation sintética.

Recolher todas as famílias ou apresentar um digest não prova completude.
Q8 exige marcador de contagem para cada uma das 23 classes, incluindo classes
vazias. As duas roles devem observar os mesmos owners/OIDs, sem ownership.
Schemas, relações e rotinas são cruzados com Q4/Q13/Q11; os outros objetos ACL
e default ACLs também são reconciliados. OIDs inválidos ou não canónicos falham.

Q14 exige cobertura de todas as relações, RLS por relação e contagens globais
para constraints, índices, triggers, regras e policies. Os objetos observados
devem reconciliar essas contagens. São obrigatórios os triggers de imutabilidade
de audit.events e inventory.policy_versions, respetivas funções SECURITY INVOKER,
e os triggers internos das FK. RLS/policies aplicacionais não são aprovados.

Este perfil não aprova regras de tabelas aplicacionais, mesmo desativadas.
Views de sistema têm exatamente uma regra _RETURN, SELECT/INSTEAD/ativa,
cuja definição é comparada com o manifesto. Não existe mecanismo novo de
autorização de regras: admitir outro comportamento exigirá revisão explícita.

Os sete schemas são fixados pelo perfil. Domínio de relkind e relpersistence
é validado; não se admite uma relação desconhecida por ter um kind não tratado.
Nas relações sem armazenamento não se infere durabilidade: conserva-se o campo
do catálogo e compara-se com o manifesto. A exigência física p aplica-se aos
kinds físicos e às tabelas esperadas. Valores ausentes são UNKNOWN, não defaults.

USAGE de pg_catalog é obrigatório nas duas identidades. `VERIFIER_COLUMNS`
enumera apenas colunas dos catálogos efetivamente lidas pelas consultas, sem
subconninfo ou rolpassword. Os direitos SELECT correspondentes e EXECUTE das
funções necessárias são exigidos. Resolução exata de overloads, visibilidade
real e necessidades do driver continuam por demonstrar em PostgreSQL.

## Consultas e ACLs

- Q4 acrescenta OID e owner de schema.
- Q8 acrescenta owner efetivo e marcadores de cobertura por classe.
- Q10 conserva ACLs integrais de bases, schemas, relações/sequences, colunas,
  rotinas, tipos, linguagens, FDWs, foreign servers, tablespaces, large objects
  e parâmetros de configuração. Não filtra apenas PUBLIC.
- Q12 conserva também default ACLs com zero entradas, com identidade e contagem.
- Q13 acrescenta OID e relpersistence às relações.
- Q14 acrescenta informação de constraints/índices/triggers necessária aos
  cruzamentos, regras e contagens globais/por relação.

Headers identificam objeto, owner quando aplicável, modo default/explicit e
número de ACEs. ACEs identificam grantor, grantee, privilege type e grant option.
Identidades compostas são arrays, evitando ambiguidades de nomes com pontos.
Normalização por linhas canónicas não depende da ordem textual das ACLs.
Modo NULL/default e ACL explícita vazia continuam distintos no fingerprint.
Grants redundantes também alteram o manifesto/digest e invalidam o checker antigo.

As ACLs completas não substituem has_*_privilege: o avaliador reconcilia ambas.
Tabela/coluna são combinadas segundo os seus efeitos; memberships e ownership
proibidos não podem fornecer direitos implícitos. Privilégios desconhecidos,
proveniência ausente, grant options indevidos ou contagens falsas são recusados.
Default privileges continuam separados de direitos já efetivos.

Parâmetros não possuem uma coluna owner: o header assinala owner não aplicável,
sem inventar ownership bootstrap. Uma ACL de parâmetro NULL, cuja proveniência
não seja determinada pelo template, é marcada unknown e recusada. Os direitos
SET/ALTER SYSTEM das duas roles são cruzados com todas as entradas recolhidas.

A evidência de ACL divergente continua a bloquear o scope em memória até
revalidação explícita. Não existe cache de observações positivas, endpoint de
revalidação, executor real utilizável ou registo automático na factory.

Os templates são SELECT parametrizados, com identificadores constantes,
sem LIMIT, DML, DDL, FOR UPDATE ou invocação de rotinas aplicacionais.
Compilação de binds SQLAlchemy não equivale a validação PostgreSQL.
Referências usadas na revisão: [pg_rewrite PG16](https://www.postgresql.org/docs/16/catalog-pg-rewrite.html),
[pg_class PG16](https://www.postgresql.org/docs/16/catalog-pg-class.html),
[funções de privilégios PG16](https://www.postgresql.org/docs/16/functions-info.html).

## Cleanup, interrupções e limites

O adaptador conserva o erro sanitizado para exceções comuns. Uma interrupção
da operação é guardada apenas para permitir a limpeza e é depois propagada,
sem a converter em sucesso ou mascarar KeyboardInterrupt/SystemExit. Na ausência
de interrupção primária, propaga-se a primeira interrupção durante cleanup;
falhas secundárias não impedem as restantes tentativas de rollback/close.
O lock é libertado uma única vez num finally exterior.

Estas são garantias de controlo Python, não garantias perante kill -9, falha
do processo, interrupções repetidas em qualquer instrução ou I/O bloqueante.
Não foi implementado cancelamento de driver ou transporte real. Os limites G1
permanecem provisórios: connect 2 s, statement 500/1000 ms, lock 200 ms, idle
transaction 1 s, global 4 s e evidência canónica até 32 MiB. O catálogo maior
pode exigir calibração futura; não se aumentaram limites nem se truncam dados.

## Testes

As fixtures anteriores foram adaptadas para os novos formatos, preservando os
298 casos. Os controlos positivos agora contêm constraints, índices, triggers,
regra de view, cobertura, owners e ACLs coerentes. Foram acrescentados 113 casos
FIX1, com expectativas literais independentes de MATRIX/COLUMNS/BUSINESS_TABLES.
Uma política incorreta não altera a fixture: existe teste de mutação de MATRIX.
As listas de colunas literais são também confrontadas com a metadata ORM.
OIDs, tipos e definições das fixtures são sintéticos e não constituem manifesto
PostgreSQL aprovado.

Cobertura adicional: regras de redireção/supressão/ALSO e desativadas; regras
de view ausentes/duplicadas/alteradas; Q8 parcial e cada classe ausente; Q14
parcial, contagens falsas, constraints/FK/triggers/índices ausentes; relkind e
schemas desconhecidos; direitos insuficientes nos catálogos; ACLs redundantes,
não-PUBLIC, grant options, NULL/explicit, owner alterado, default ACLs e parâmetros;
interrupções e falhas consecutivas de cleanup; persistência u/t/UNKNOWN/ausente.

Comando da suite final, apenas com testes offline previamente inspecionados:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=backend \
.venv/bin/python -B -m pytest -q -s --assert=plain -p no:cacheprovider --tb=short \
backend/tests/test_readiness_postgres.py \
backend/tests/test_readiness_contract.py backend/tests/test_trusted_proxy.py \
backend/tests/test_security_api.py backend/tests/test_security_service.py \
backend/tests/test_security_policy.py backend/tests/test_inventory_api.py \
backend/tests/test_inventory_service.py backend/tests/test_inventory_schemas.py \
scripts/postgres/tests/test_m12b_security_migration.py \
scripts/postgres/tests/test_m12b_security_execution.py \
scripts/postgres/tests/test_m12b_privilege_review.py \
scripts/postgres/tests/test_m12b_inspection_handoff.py \
scripts/postgres/tests/test_m12b_operational_adapters.py \
scripts/postgres/tests/test_m12b_operational_coordination.py \
scripts/postgres/tests/test_m12b_operational_audit.py
```

Resultado final: 1245 PASS, 0 FAIL, 0 SKIP: 411 casos do adaptador (298 anteriores
e 113 FIX1), mais 834 regressões. Sem caches novas no repositório ou fixtures
que escrevam manifestos/criem serviços. Não se executaram testes AUTH-03 que
escrevam ficheiros; as duas falhas históricas permanecem documentadas.

## Integridade e pendências

Os 229 ficheiros preexistentes fora da lista de alteração permanecem
byte-identical. Foram alterados seis ficheiros autorizados e criado um relatório;
HEAD, branch e staging foram preservados. git diff --check e verificação direta
de whitespace dos sete ficheiros passam, incluindo os untracked.

AUTH-03 15/15 preservado, manifesto inalterado, operation_gate bloqueado e
execution_enabled=False. Não se alteraram M1.2B, factory, modelos, migrações,
Compose, Caddy, credenciais, roles, ACLs reais ou serviços. Nenhum commit/push.
Não se consultou Docker: não há nova atestação runtime dos 23 contentores.

A inconsistência AUTH-03 mantém-se: 31 entradas para 51 fontes calculadas,
20 fontes ausentes e quatro hashes divergentes preexistentes. FIX1 não acrescenta
novas fontes Python ao conjunto; não atualiza ou contorna o manifesto.

Permanecem pendentes: manifesto físico independente aprovado; validação PG16
dos SQL, overloads, visibilidade, ACLs/defaults e definições de cada objeto;
calibração dos limites/custos; transporte com streaming, timeouts, cancelamento
e limpeza limitados; controlo de escritores externos, recuperação administrativa
e gates M1.2B. Os snapshots das duas conexões continuam separados e existe
TOCTOU. Os locks/latches são em memória, não persistentes entre processos.

O perfil continua a recusar EXECUTE direto em rotinas aplicacionais fora da
assinatura audit já prevista. A futura comparação real pode recusar defaults
PUBLIC de rotinas existentes, incluindo a de policy_versions; isso exige revisão
de privilégios em etapa própria, sem GRANT/REVOKE ou alargamento nesta correção.

Critérios propostos para G3-REV2: rever de forma independente os cinco IDs,
protocolos de cobertura, ACLs/proveniência, declarações mínimas e limpeza; confirmar
que os casos que passavam indevidamente são agora recusados; verificar ausência
de regressões e caminhos operacionais. Este relatório não aprova G3-REV2 nem G4.
Próximo passo recomendado: solicitar essa revisão independente, sem ativação.
