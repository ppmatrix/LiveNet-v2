# R1-PROTO-03 — fronteira PostgreSQL (desenho candidato)

SQL experimental nunca aplicado: `postgres_boundary.NOT-APPLIED.sql`.
Modelos/testes: `postgres_boundary.py`, `tests/test_postgres_boundary.py`.
Sem driver, serviço, executor, instalação ou alteração a AUTH-03/F02/G2/G4.
Nenhuma garantia operacional nem fecho de GAP-001/002 é demonstrado.

## Operações existentes e primeiro efeito

Fontes abaixo são relativas à raiz. O efeito não é o commit, envio SQL, consumo,
reserva ou atualização final do ledger. Locks, atribuição de XID, controlo R1 e
mutações aplicacionais são efeitos distintos: não declarar que os primeiros são
inexistentes. O contrato já coloca locks antes da migração. Se "primeiro efeito"
incluir esses locks de preparação, a fronteira terá de os abranger também;
essa ambiguidade requer decisão explícita, não uma redefinição neste protótipo.

| Operação/fonte | Primeiro efeito relevante e limites |
| --- | --- |
| AUTH-03 `preflight` (`scripts/postgres/auth03_alembic_executor.py`, OPERATIONS/host_run) | Não contacta PostgreSQL. Preflight de host não concede autoridade. |
| AUTH-03 `inspect`/`verify-revision`; readiness G2 | Primeiro SELECT pode adquirir locks de leitura no catálogo/relações. Transação read-only; não há mutação aplicacional prevista. G2 continua sintético. |
| AUTH-03 `upgrade-baseline`, base→f066 | Alembic pode criar `public.alembic_version` antes de chamar upgrade; depois a revisão raiz executa `CREATE SCHEMA inventory`. Seguem tabelas, índices, constraints, btree_gist, objetos audit e DML no ledger. A primeira mutação NÃO pode ser identificada apenas pela primeira linha da revisão. |
| AUTH-03 `upgrade-auth03`, f066→f067 | Ledger já existe no estado de origem esperado; primeiro comando da revisão é `CREATE SCHEMA authorization`, seguido de CREATE TABLE e atualização do ledger. O comando pode adquirir locks antes da alteração de catálogo. |
| AUTH-03 `downgrade-auth03`, f067→f066 | `DROP TABLE authorization.authorization_integrity_anchors` é a primeira instrução da revisão; lock de DDL pode preceder remoção de catálogo/dados. Depois DROP SCHEMA e ledger. Continua bloqueado. |
| Security base→b12 (`backend/security_migrations/versions/b12b01a7230_create_security.py`) | Criação inicial de `public.alembic_security_version` pode anteceder `CREATE SCHEMA security`; depois tabelas/índices/constraints e ledger. Downgrade é explicitamente recusado. |
| DML runtime previsto em DEV-08B/D05 | INSERT de sessões/throttles/audit e UPDATE restrito de users/sessions/throttles: locks, defaults e triggers podem preceder a alteração da primeira tupla. SELECT inventory é leitura. Não se estende automaticamente R1 às operações normais da aplicação. |
| Provisionamento/ownership/ACL, DEV-08B | Criação de base/roles, GRANT/REVOKE/ALTER OWNER são preparação separada, sem execução autorizada nos percursos acima. Alterações de catálogo/ACL são efeitos próprios; exigem plano distinto. |

O comportamento do ledger foi confirmado por leitura da biblioteca Alembic local
(`alembic/runtime/migration.py`, `_ensure_version_table`/`run_migrations`), sem
executá-la. Fontes: `backend/migrations/versions/af62df027d9d_*`, `f067a01a7230_*`,
`scripts/postgres/auth03_alembic_executor.py:245–271`,
`scripts/postgres/m12b_security_migration.py:605–657`,
`docs/specifications/f0/auth03-alembic-executor.md`, secção transações,
`docs/specifications/f0/dev08b-persistence-contracts.md`, D02/D05 e catálogo G2.

Para o alvo real, falta demonstrar a fronteira interna exata anterior a locks,
defaults/triggers, catálogo ou tuplas, por operação e versão. A tabela identifica
o primeiro comando e efeitos possíveis; não é uma instrumentação do servidor.
`CREATE INDEX CONCURRENTLY`/`CREATE DATABASE` e sequências `nextval/setval` não
constituem um percurso genérico autorizado. Os dois primeiros têm restrições de
transação; sequências podem manter efeitos apesar de rollback. CREATE EXTENSION
existente também exige revisão dos scripts/privilégios da extensão concreta.

## Marcador: garantia local limitada

Tabela logged no alvo, propriedade segregada, sem escrita runtime. Unicidade
por `(authority_id, approval_id)` E `(authority_id, attempt_id)`; geração/sessão
não pertencem à chave para não permitir reutilização ao mudá-las. Guardar bindings
de executor/encarnação/sessão/transação/destino/plano e epochs. O identificador de
sessão deve ser atestado; PID ou string fornecida pelo cliente não o substitui.

Marcador confirmado significa apenas **BURNED**, nunca autorização, início
observado ou commit. INSERT conflitante não se converte em sucesso idempotente.
Sem DELETE, reset, UPDATE de binding, lease que liberte ou retry automático.
Confirmação perdida => bloqueio/reconciliação; pode existir burn sem execução.

Na transação protegida, rollback apaga o marcador e permite nova iniciação.
Persisti-lo antes numa transação de controlo separada preserva o burn sob rollback
da operação, assumindo WAL/storage duráveis e confirmação correta. Não torna
atómicos os dois commits; crash entre eles sacrifica disponibilidade. O vínculo
à ligação/transação protegida e a exclusão de despachos duplicados ainda precisam
de enforcement não contornável. Tabela/recibo não impedem SQL direto pelo migrator.

**Conflitos atuais:** AUTH-03/security exigem uma única transação externa para a
migração; o controlo separado não pode ser inserido silenciosamente nesse contrato.
Os catálogos exatos AUTH-03/G2/security recusam schema/tabela extra (até no caso de
origem vazia). Não reutilizar anchors f067 como marcador por inferência. A proposta
exige revisão específica de integração/contratos; nada foi alterado nesta tarefa.

## Revogação, expiração e escolha técnica

Unicidade/transações locais são úteis. Row lock pode ordenar uma revogação
**aplicada no mesmo alvo** com um fluxo cooperante. Não ordena automaticamente
uma revogação já decidida na autoridade remota. Na partição, a ausência de nova
mensagem não prova elegibilidade. Manter lock remoto, 2PC ou pedir cancelamento
também não fornece UTC confiável nem impede por si um efeito atrasado.

Um protocolo que só confirme revogação após aplicação no alvo deve distinguir
pedido/pendente/aplicada; isso muda a fronteira de eficácia e exige decisão humana.
Não é adotado como solução compatível por pressuposto. Réplicas de epochs e
notificação assíncrona são insuficientes para a semântica R1 atual.

`now()`/`transaction_timestamp()` medem início da transação e podem estar antigos.
`clock_timestamp()` mede o momento da chamada, mas não torna check e alteração de
catálogo indivisíveis. Mesmo dentro de função/trigger pode haver suspensão/locks
depois do check. Statement/lock timeout e consulta pré-SQL reduzem risco, não
provam início antes da expiração. UTC e incerteza continuam dependências GAP-014.

**Recomendação mais simples:** desenvolver separadamente a reserva local
irreversível como componente candidato e manter a execução recusada. Para uma
solução completa, falta demonstrar enforcement no alvo por operação, sem poderes
de contorno, e coordenação da revogação com o primeiro efeito efetivo. Não há
solução genérica demonstrada com tabela + SQL prévio para Alembic/DDL arbitrário
que satisfaça integralmente os contratos atuais. Hooks/extensões não são escolhidos
ou declarados suficientes. Se a solução exigir nova semântica de revogação ou de
primeiro efeito, isso é decisão contratual, não detalhe de implementação.

Crash/rollback: burn separado pode sobreviver; resultado incerto nunca autoriza
reexecução. Snapshot/clone: pode perder/copiar burn e identidade; exige quarentena,
referência independente e invalidação de instâncias antigas (GAP-003/007).
Partições: fail-closed; nenhum fallback de epoch/relógio/autoridade.
Também dependem GAP-004/005/006/008/010/011/012/014/015/016/017/018.

## Evidência e fontes técnicas

Testes apenas modelam transações, conflitos, rollback e interleavings. Não validam
sintaxe SQL, isolamento real, fsync, engine hooks ou privilégios no PostgreSQL.
O SQL tem erro deliberado antes do DDL, dentro de BEGIN/ROLLBACK, para impedir
aplicação acidental intacta; não está referenciado por migrations ou executores.

Referências oficiais PostgreSQL 16 consultadas:
- https://www.postgresql.org/docs/16/explicit-locking.html
- https://www.postgresql.org/docs/16/functions-datetime.html
- https://www.postgresql.org/docs/16/sql-createtable.html
- https://www.postgresql.org/docs/16/sql-createindex.html
- https://www.postgresql.org/docs/16/sql-createdatabase.html
- https://www.postgresql.org/docs/16/functions-sequence.html

Executar apenas offline: `python3 -B -m unittest discover -s protocols/auth_boot_r1/tests`.
