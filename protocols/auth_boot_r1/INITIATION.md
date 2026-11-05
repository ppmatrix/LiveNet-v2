# R1-PROTO-02 — estudo offline de iniciação (candidato)

`initiation_model.py` é uma simulação em memória, sem serviços, SQL, credenciais
ou integração com executores. Não é um mecanismo aprovável por passar testes.
Base: consolidado AUTH-BOOT-02-R1 pós-CONSOLIDAÇÃO-D, §§6–8 e 10–12.
Não altera nem resolve GAP-001/002 ou contratos AUTH-03/F02/G2/G4.

## Estados e fronteiras

Autoridade: `ISSUED -> CLAIMED -> CONSUMED_FOR_ATTEMPT`, com um único vencedor
por transição. Consumo nunca regressa a disponível; revogação é estado separado.
Execução candidata: `WAITING -> STARTED -> COMMITTED_MODEL_ONLY` ou
`ROLLED_BACK_MODEL_ONLY`; crash/perda de confirmação pode levar a
`UNKNOWN/BLOCKED`. Falha antes do início bloqueia a continuação dessa execução.
Estes nomes não alteram enums F02. Estados de commit são factos sintéticos,
nunca SUCCEEDED_VERIFIED nem evidência independente de commit real.

Contexto sintético: aprovação, tentativa, executor, encarnação, sessão,
transação, destino/geração e plano. Não implementa os 25 bindings criptográficos.
Recibos não têm assinatura; autenticidade é hipótese, não garantia do protótipo.
Tempo: intervalo UTC sintético [L,U], elegível só com 0 <= L <= U < 900.
Não há relógio real, espera real, lock real ou disco. Métodos são eventos
atómicos do modelo; testes enumeram interleavings, não provam isolamento SQL.

## Três abordagens e resultados

| Modo | Hipótese/resultado observado |
| --- | --- |
| PRECHECK | Consulta fresca antes do despacho. Consumo único não impede dois despachos, replay ou retry após rollback. Espera por locks/pausa permite expiração ou revogação antes do primeiro efeito. Controlo negativo deliberadamente inseguro. |
| TARGET_LOCAL | Reserva durável exclusiva e marcador de início no alvo, fora do rollback protegido; o teste de unicidade e a passagem ao primeiro efeito são um único evento local. Impede replay sob essa hipótese e verifica tempo após espera por locks. Não vê revogação remota ainda não entregue. Relógio falsamente confiável, snapshot e clone podem quebrar garantias. |
| IDEAL | Acrescenta consulta autoritativa e primeiro efeito indivisíveis no mesmo evento. As interleavings respeitam revogação/expiração e indisponibilidade. Esta atomicidade distribuída é uma HIPÓTESE NÃO IMPLEMENTADA; não equivale a consulta remota, mTLS, lease ou recibo assinado. |

`effects` é um observador sintético de iniciações: não conta commits e não é
ledger, auditoria independente ou implementação de confirmação D09.
Snapshots copiam apenas o estado modelado, não apagam o histórico do observador.
Os helpers `unsafe_*_negative_control` demonstram perdas de continuidade; não
são APIs de recuperação. `restore()` bloqueia por defeito, sem implementar
reentrada. Crash não simula fsync; pressupõe persistência dos marcadores.

## Recomendação e dependências reais

Recomenda-se autoridade com transições condicionais PostgreSQL e fronteira
mínima no alvo, preservando a separação administrativa/VM aprovada. Autoridade
pode garantir claim/consumo exclusivos se houver durabilidade, isolamento e
continuidade; não consegue por si impedir a execução de um despacho já entregue.

Estudar reserva e marcação de início no alvo, duráveis mesmo após rollback da
operação, sem retomar automaticamente uma tentativa reservada. Isso sacrifica
disponibilidade: crash antes do efeito pode inutilizar a aprovação sem execução.
Uma tabela escrita na mesma transação revertida não satisfaz esta hipótese.
Uma reserva isolada também não prova que código em espera não inicia duas vezes:
o marcador e a fronteira efetiva precisam de enforcement conjunto.

Antes de escolher uma implementação, identificar por operação AUTH-03/security o
primeiro efeito PostgreSQL real, incluindo locks e operações com efeitos não
transacionais. Não renomear admissão/despacho como primeiro efeito. Não presumir
que trigger, função SQL, proxy ou extensão cobre Alembic/DDL arbitrário. Privilégios
diretos que contornem a fronteira invalidam a abordagem.

**Bloqueio GAP-002:** falta mecanismo demonstrado que ordene revogação remota
e primeiro efeito real. Notificação assíncrona, igualdade com epoch local, nova
consulta pré-SQL ou prazo curto não eliminam a janela. Sem solução aprovada que
preserve D05, manter a ativação bloqueada; não introduzir grace period ou adiar
silenciosamente a eficácia da revogação.

Dependências: GAP-003/007 (continuidade, clones, recuperação), 005/006 (integração,
identidades/privilégios reais), 008/009/018 (bindings/contratos), 010 (persistência),
011/014/015 (confiança, UTC/incerteza e transporte), 004/012/016/017 (evidência,
recuperação e responsabilidades). PostgreSQL real e ensaios independentes futuros
exigem autorização própria. Não há exatamente-uma-vez distribuído demonstrado.

## Testes

Na raiz: `python3 -B -m unittest discover -s protocols/auth_boot_r1/tests -v`.
Inclui controlos negativos: um teste verde pode confirmar uma violação esperada.
Nenhum teste usa PostgreSQL, threads, processos externos ou infraestrutura.
