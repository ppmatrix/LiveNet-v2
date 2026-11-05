# R1-PROTO-04 — primeira classe candidata, não operacional

**Recomendação:** estudar primeiro um UPDATE fixo de uma linha pré-existente,
por chave primária e versão esperada, numa tabela simples de laboratório.
É a menor mutação útil para separar reserva, lock, verificação, efeito e commit.
Não corresponde a um novo poder sobre tabelas LiveNet. Sob os contratos atuais,
nenhuma classe de escrita foi demonstrada como suportada integralmente por R1.

`operation_scope.py` seleciona apenas candidatos de ensaio a partir de factos
fornecidos. Não interpreta SQL, atesta catálogo ou concede autorização. Os testes
verificam exclusões e recusa de metadados desconhecidos; não repetem simulações
de PostgreSQL nem transformam a allowlist em gate operacional.

## Classes reais e exclusões

| Classe e evidência existente | Primeiro efeito a abranger | Marcador/enforcement; consequência da exclusão inicial |
| --- | --- | --- |
| SELECT/inspeção: AUTH-03 inspect/verify-revision, leitura inventory e readiness | Pode adquirir locks de leitura; não é ausência absoluta de efeitos. Sem mutação aplicacional prevista. | Útil para diagnóstico autorizado; não demonstra iniciação protegida de escrita. G2 continua offline. |
| DML: security/service.py, audit/service.py, inventory/service.py | Locks e eventuais defaults/triggers podem preceder a primeira alteração de tupla. Fluxos ORM podem emitir várias instruções. | Login tem UPSERT de throttles, locks, sessões e audit; create_resource também escreve audit. Não são a operação simples candidata. Não se altera autenticação/runtime nem se concede INSERT inventory ao perfil D05. |
| DDL transacional: migrações aplicacionais/security | Locks de catálogo/relação e primeira alteração de catálogo; versão Alembic inicial pode preceder o corpo da revisão. | Reserva persistente não cobre SQL direto. Excluir deixa instalação/upgrade/downgrade protegidos bloqueados, incluindo f066/f067/b12. |
| Alembic | Orquestra DDL/DML e escrita/criação de ledgers; não é uma instrução nem uma classe de efeitos atómica. | Não promover uma revisão inteira porque contém DDL transacional. Sem migrations, stamp ou reconciliação de perfis. |
| SQL arbitrário/op.execute/funções/extensões | Depende do programa executado; pode sair da transação ou ter efeitos externos. | Sem SQL do cliente, DO dinâmico, funções não revistas ou extensão genérica. CREATE EXTENSION btree_gist das revisões existentes fica fora da primeira classe. |
| Não transacional ou efeito não revertido | nextval/setval podem sobreviver a rollback; CREATE DATABASE/CREATE INDEX CONCURRENTLY não pertencem à transação protegida ordinária. | Não são percursos R1 autorizados por aparecerem nesta classificação. Excluídos; não se oferece criação de base ou manutenção concorrente. |
| Roles, ownership, GRANT/REVOKE | Efeitos de catálogo/ACL próprios, antes da confirmação externa. | Preparação administrativa separada; sem provisioning ou handoff automático. |

Fontes já existentes: `scripts/postgres/auth03_alembic_executor.py` (operações e
invoke_migration); `scripts/postgres/m12b_security_migration.py` (execution_contract);
`backend/app/security/service.py:108–158`; `backend/app/inventory/service.py:37–55`;
`backend/app/audit/service.py:77–134`; DEV-08B, secções D02/D05/catálogo G2.
Primeiros comandos de migration e ledger estão delimitados em POSTGRES_BOUNDARY.md.

## Critérios objetivos da candidata

Identificador experimental `lab.single_row_compare_and_set.v1`. Uma instrução
fixa, parâmetros tipados, UPDATE ONLY de coluna simples e incremento de versão,
WHERE chave primária = parâmetro AND versão = parâmetro. No máximo uma linha;
zero linhas não autoriza retry nem libertação do burn. Sem INSERT, UPSERT, DELETE,
CTE, subquery, FROM, SQL dinâmico ou chamadas escolhidas pelo cliente.

Tabela local logged já preparada; sem partições/herança/FDW, triggers, rules,
colunas geradas, sequências/defaults executáveis, FKs/cascatas, RLS ou funções de
utilizador. Chave/índices, tipos e constraints simples têm de ser revistos no
alvo do ensaio. Não presumir que uma tabela atual LiveNet cumpre este perfil.

Só um entrypoint revisto pode aceder ao DML; a identidade chamadora não recebe
UPDATE direto, ownership, superuser ou poder de criar funções/triggers. A forma
concreta de enforcement e os seus privilégios ainda não estão implementados.
Este perfil reduz a superfície de efeitos; NÃO prova ausência de locks, pausas,
efeitos de controlo ou janela temporal dentro do servidor.

## Garantias e decisão arquitetural necessária

Reutilizar a proposta de burn persistente, ligado a contexto atestado, sem release
ou replay-as-success. Confirmá-lo separadamente da transação DML conserva-o sob
rollback, com perda de disponibilidade se houver crash. O marcador não permite
retoma; falta excluir continuação antiga/despacho duplicado na fronteira real.
Snapshots/clones exigem continuidade e invalidação externa; unicidade local não
resolve duas cópias graváveis. Catálogo novo/transação de controlo continuam a
exigir revisão dos contratos protegidos; não se instalam na aplicação atual.

**Decisão necessária:** fixar expressamente qual estado torna a revogação eficaz
e a sua ordenação com o primeiro efeito. Há duas alternativas distintas:

1. Preservar a revogação autoritativa remota e a fronteira de efeito real de R1.
   É o comportamento que continua obrigatório. Não há mecanismo completo
   demonstrado; a candidata continua apenas de laboratório.
2. Propor revogação por alvo, com pedido -> pendente -> aplicada, confirmação
   somente após barreira no alvo e estado durável. Autoridade externa continua a
   controlar aprovação/confiança, mas a eficácia da revogação muda. Exige revisão
   normativa explícita, não é aprovada/implementada aqui. Durante partição, pedido
   não confirmado permanece pendente: não alegar que o alvo soube da revogação.

A segunda alternativa não resolve automaticamente expiração. Check de relógio,
mesmo em função/trigger no alvo, pode preceder suspensão/lock e alteração da tupla.
Não tratar entrada na função, reserva, check, envio ou commit como primeiro efeito
real. Escolher linearização na admissão seria OUTRA alteração contratual explícita.
Um lock pode ordenar atualizações do estado local; não torna UTC, check e efeito
físico indivisíveis. Sem aprovação e prova adequadas, manter gates fechados, sem
grace period, lease autorizadora ou fallback em partição.

Assim, recomenda-se delimitar e ensaiar DML simples preservando a alternativa 1;
não adotar a alternativa 2 nem redefinir o início como atalhos de implementação.
Nenhuma destas escolhas autoriza HA, altera F02/G2/G4 ou fecha GAP-001/002.

## Menor ensaio futuro — não executado nem autorizado por este documento

Um cluster PostgreSQL 16 isolado/descartável, uma base nova sem dados LiveNet,
uma tabela cell de uma linha e controlo candidato em domínio próprio. Identidades
de preparação/controlo/chamada separadas; duas sessões concorrentes e uma sessão
de controlo permitem escalonar os casos. Sem Flask, Alembic ou serviços R1 reais.
O ensaio precisa de autorização própria, sem reutilizar roles/volumes/segredos.

1. Preparar entrypoint fixo e negação de UPDATE direto. Provar que scope alterado,
   SQL adicional, sessão/geração/binding divergentes são recusados.
2. Concorrer com a mesma aprovação/tentativa. Medir um burn confirmado; rollback
   DML, erro e perda de confirmação nunca o libertam. Demonstrar a diferença
   entre exclusividade de burn e de iniciação: estado final/row_version sozinho
   não conta tentativas revertidas nem prova GAP-001.
3. Usar locks/barreiras de sessão para aguardar ANTES e DEPOIS do check; libertar
   somente após expiração ou revogação. Procurar contraexemplo na primeira
   mutação possível, não apenas commit posterior ao prazo. Se a função ainda
   escrever após pausa pós-check, registar falha da hipótese, sem ajustar o prazo.
4. Comparar revogação remota não entregue com revogação aplicada localmente.
   Não extrapolar a segunda para a primeira. Logs/marcadores do próprio fluxo
   não são oráculo independente suficiente de primeiro efeito.
5. Reiniciar após burn e antes do DML, e após DML sem confirmação. Quarentena
   em estado incerto. Snapshots/clones/partições distribuídas permanecem ensaios
   posteriores: este mínimo não demonstra recuperação independente completa.

O ensaio serve para validar propriedades locais ou refutar a abordagem. Não basta
para fechar GAP-001/002: é necessária observação independente da fronteira real,
protocolo de coordenação/tempo aprovado e evidência de continuidade.

Referências técnicas oficiais (não equivalência com contratos históricos):
- https://www.postgresql.org/docs/16/sql-update.html
- https://www.postgresql.org/docs/16/trigger-definition.html
- Demais semânticas PostgreSQL 16 referenciadas em POSTGRES_BOUNDARY.md.
