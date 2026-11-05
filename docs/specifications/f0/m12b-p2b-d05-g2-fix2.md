# M1.2B-P2B-D05-G2-FIX2 — Reserva REV2-01

## Âmbito e baseline

Implementação e testes exclusivamente offline, em 2026-10-24. Branch `main`,
HEAD `647179c928888adfeef0f69f582fd13c5fc17350`, staging inicialmente vazio.
Foram capturados SHA-256 dos 236 ficheiros não ignorados preexistentes.
As alterações locais, incluindo AUTH-03, foram preservadas.

Modificados apenas:

- `backend/app/readiness_postgres/adapter.py`.
- `backend/tests/test_readiness_postgres.py`.

Criado apenas este documento. Nenhuma alteração ao relatório FIX1, política,
consultas, avaliador, factory, modelos, migrações, Compose ou manifestos.
Esta correção não constitui revisão independente nem autorização de G4–G8.

## Causa técnica

O `finally` exterior de `OfflineReadinessAdapter.__call__` chamava diretamente
`lock.release()`. Se o cleanup já estivesse a propagar KeyboardInterrupt ou
SystemExit, um RuntimeError secundário de release substituía essa interrupção.
O cenário foi reproduzido com um double em memória; não demonstra falha física
do `threading.Lock` normal.

## Correção e contrato de exceções

Um contexto privado `_hold_scope()` concentra a aquisição não bloqueante e a
única tentativa de release por aquisição bem-sucedida. É utilizado por
`__call__` e pela revalidação explícita já existente; não abre conexões nem
concede novas autorizações.

- Sem aquisição bem-sucedida, não tenta release.
- Com uma exceção primária em propagação, conserva o mesmo objeto e tipo.
  Uma falha de release não substitui essa exceção, mesmo se a falha secundária
  também for KeyboardInterrupt/SystemExit.
- Sem exceção primária, uma falha comum de release produz `Unavailable`.
  KeyboardInterrupt/SystemExit originados no próprio release são propagados
  com a identidade original. Nenhum desses caminhos devolve uma observação.
- A exceção propagada recebe, quando possível, uma nota constante:
  `Readiness lock release failed; lock state is unknown; scope invalidated.`
  A nota não interpola mensagens, argumentos ou representações da exceção
  secundária. Não há logs novos nem exposição de detalhes do lock.
- A falha comum sanitizada é levantada fora do handler da falha de release,
  sem conservar a exceção secundária como cause/context. A impossibilidade de
  anexar a nota não pode substituir a exceção principal.
- Qualquer falha de release invalida o scope partilhado em memória. Mesmo que
  o lock tenha sido fisicamente libertado antes de lançar o erro, não há nova
  observação positiva automática. Uma revalidação cujo release falhe também
  deixa o scope invalidado.

O contrato anterior para falhas comuns de factories, queries e cleanup permanece:
os detalhes são sanitizados para `Unavailable` antes de chegarem à fronteira do
lock. A preservação de identidade nessa fronteira refere-se à exceção já em
propagação, não à divulgação de um RuntimeError original do driver. Há testes
distintos para RuntimeError primário no contexto privado e para a identidade
da falha pública sanitizada do adaptador.

O cleanup existente continua a tentar rollback e close independentemente, por
recurso, antes do release. Não foram alteradas as verificações dos cinco achados
REV1, nem a política D05. BaseException é capturada para concluir a limpeza e
preservar a falha primária, nunca para retomar um caminho de sucesso.

## Testes

Foram acrescentados 21 casos em memória, sem alterar os 411 casos anteriores:

- KeyboardInterrupt, SystemExit e RuntimeError primários com RuntimeError em release.
- Interrupções em rollback e close, verificando identidade e ordem de cleanup.
- Falha comum da operação, rollback, close ou ambos os recursos, seguida de
  falha de release, preservando a falha pública sanitizada.
- Release com RuntimeError, KeyboardInterrupt ou SystemExit sem falha anterior.
- Interrupção secundária de release com interrupção primária já em propagação.
- Double que liberta o lock antes de lançar erro, com invalidação partilhada.
- Aquisição recusada sem release ou abertura de recursos.
- Revalidação sem capacidade de limpar o latch se o release falhar.
- Exceção que recusa a nota diagnóstica, sem mascarar a primária.
- Lock normal: preservação da exceção original e sucesso posterior normal.

As asserções usam identidades, mensagens e sequências de eventos explícitas.
Os doubles não recorrem a PostgreSQL, drivers, Docker, Alembic ou locks de base
de dados. Todos os caminhos de falha exigem uma exceção em vez de sucesso.

Validação dirigida final: **21 PASS, 0 FAIL, 0 SKIP**, 411 deselected, **5,18 s**.

Comando da suite completa, com fixtures offline previamente inspecionadas:

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

Resultado da suite completa: **1266 PASS, 0 FAIL, 0 SKIP**, **88,23 s**:
432 casos do adaptador (411 anteriores + 21 FIX2) e 834 regressões. O prefixo
do ficheiro com os 411 casos anteriores foi comparado por SHA-256 com a
baseline e permanece byte-identical; os testes FIX2 foram apenas acrescentados.
O corpo anterior de recolha, avaliação e cleanup do adaptador também permanece
inalterado: a alteração limita-se ao contexto do lock e aos seus dois pontos de uso.

Também foram repetidos por stdin os 21 controlos adversariais de REV2:
**21 PASS, 0 FAIL, 0 SKIP**, sem cronometragem isolada. A reprodução adicional
de REV2-01 passou a propagar o mesmo KeyboardInterrupt, com um único release
e cleanup tentado nos dois recursos. O double continua bloqueado por desenho;
isso não é apresentado como recuperação do lock.

## Limitações e integridade

Perante falha de release, o estado físico do lock é desconhecido. Não há retry,
double-release, substituição forçada do lock ou manipulação do seu estado
interno. Um lock efetivamente retido pode impedir chamadas posteriores nesse
processo. O latch é apenas em memória; não existe recuperação operacional
implementada ou garantia perante kill -9, falha de processo ou I/O bloqueante.
O registo da falha secundária é best effort quando a própria exceção não aceita
notas. A evidência é sintética, sem validação de comportamento de driver real.

A verificação final confirmou **234/234 ficheiros preexistentes fora dos dois
caminhos de alteração byte-identical**, apenas este documento adicional (237
ficheiros não ignorados no total), HEAD preservado, staging vazio,
`git diff --check` e whitespace direto dos três caminhos sem erros.

AUTH-03 **15/15 preservado**, manifesto inalterado, operation_gate bloqueado
e execution_enabled=False. A inconsistência conhecida do manifesto
permanece: 20 fontes ausentes e quatro hashes divergentes. Não se regeneram
hashes nem se modifica a factory ou qualquer migração para a resolver.

Não se executaram PostgreSQL, SQL real, Docker, serviços, Alembic, operações de
roles/ACL, Caddy, rede, staging, commit ou push. Não se iniciou revisão
independente, ativação ou G4.

## Critérios para revisão independente curta

1. Confirmar o diff limitado aos dois módulos autorizados e a este documento.
2. Reproduzir REV2-01 e verificar identidade primária, nota sanitizada, cleanup
   anterior ao release e uma única tentativa por aquisição.
3. Confirmar falha fechada sem primária e ausência de detalhes secundários
   nos erros comuns públicos.
4. Confirmar invalidação mesmo quando o double liberta antes de falhar, sem
   recuperação física implícita ou novo caminho de ativação.
5. Confirmar os 411 casos anteriores, os novos casos FIX2 e as regressões,
   integridade AUTH-03, HEAD, staging e ausência de alterações fora do âmbito.

Próximo passo recomendado: revisão independente curta, mediante pedido próprio.
Este relatório não autoriza nem inicia essa revisão ou qualquer gate operacional.
