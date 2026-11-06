# R2-DEV-01 — Protótipo experimental de admissão lógica

Autorização: pedido humano nesta sessão de 2026-10-27 para executar R2-DEV-01 em
`progbox:/home/paulo/projects/livenet-v2`. Autoriza código experimental e testes.
Fonte: `docs/architecture/auth-boot-02-r2.md`, C1–C7, lida diretamente no checkout.
A autorização atual permite este laboratório; não altera a baseline documental.

Todo o trabalho reside nesta pasta nova. Não importa módulos operacionais e não
abre ligações de rede, serviços, bases LiveNet ou PostgreSQL. A única operação
modelada é `LAB_FIXED_UPDATE`, um identificador sem implementação SQL no alvo.
Não há executor, despacho, retoma, libertação de consumo ou autorização executável.
AUTH-03/F02/G2/G4 permanecem fechados, GAP-001/002 abertas e DEV-09B não autorizada.

## Execução reproduzível

Em Linux, com Python 3.12 e biblioteca padrão:

```sh
cd /home/paulo/projects/livenet-v2/experiments/auth_boot_02_r2_dev01
PYTHONDONTWRITEBYTECODE=1 python3 run_tests.py
```

`evidence.json` regista resultados, IDs dos testes, saída integral, runtime, HEAD
e SHA256 dos três fontes Python. Cada teste provisiona bases descartáveis em
diretórios temporários e elimina-as ao terminar. O runner não instala dependências.
Não foi necessário PostgreSQL descartável. SQLite é uma escolha exclusiva do
protótipo, não uma seleção de produto para a autoridade real.

## Modelo e fronteiras

`laboratory.py` implementa um único estado autoritativo com journal ordenado.
`BEGIN IMMEDIATE` serializa a avaliação final em A com revogações, epochs e
política. `flock` mantém a exclusão entre processos até à confirmação da cópia,
incluindo o intervalo posterior ao commit local. Todas as instâncias conformes
para o mesmo ficheiro devem usar a mesma localização de lock, em filesystem local.
SQLite usa `synchronous=FULL` e journal `DELETE`. O estado de consumo, os vínculos,
a sequência e a evidência essencial são gravados na mesma transação.

O relógio injetado é consultado dentro dessa transação, após a aquisição do lock.
A avaliação exige `issued_at <= not_before < expires_at`, duração máxima de 900 s,
`L >= not_before`, `U < expires_at`, tempo confiável e continuidade conhecida.
O commit pode ocorrer após a expiração: o teste avança deliberadamente o relógio
depois de A. A sequência persistida estabelece a ordem; timestamps não a substituem.

`Binding` fixa pedido, tentativa, participantes, finalidade, operação, gate,
ambiente, plano, digests, destino/geração, executor/encarnação e sessão/transação.
O objeto `Approval` representa entrada previamente verificada por uma fronteira
de confiança simulada. `issue` é preparação de fixtures, não emissão/aprovação humana.
Revogação de aprovação/chave/autoridade/política e alterações de controlo partilham
o journal. `request_revocation` devolve apenas `PENDING`; não é uma fila durável.
Só `revoke` confirma eficácia. Revogação posterior não apaga a admissão anterior.

O `WitnessDouble` mantém uma segunda base SQLite e confirma o evento com HMAC de
teste. A autoridade verifica essa confirmação antes de devolver `ADMITTED`.
Este resultado continua com `executable=False`. As duas confirmações não são
atómicas: falha após commit local mantém o consumo e produz `UNKNOWN/BLOCKED`.
Resposta perdida não produz retry. Consulta devolve observação, nunca permissão.
Se uma resposta se perde depois da cópia, o estado pode esclarecer o consumo;
mesmo assim não autoriza retoma. A quarentena persistente não tem API de desbloqueio.

Recuperação verifica journal, estado, head externo, store ID e encarnação declarada.
Restauro antigo contra testemunho atual, troca de encarnação, testemunho ausente,
divergência e tempo desconhecido bloqueiam. Reinício preserva consumos, ordem,
revogações, epochs e vínculos; aumentar epoch não remove quarentena. Reconciliação
humana, invalidação real de capacidades antigas e nova aprovação ficam por construir.

## Rastreabilidade dos testes

| Cláusula | Demonstração experimental |
| --- | --- |
| C1 | Consumo/evidência conjuntos; 32 threads e 8 processos com um vencedor; crash real antes/depois do commit |
| C2 | Limites inclusivo/exclusivo de [L,U], duração 900 s, expiração durante espera, commit posterior ao prazo, tempo desconhecido e rollback temporal |
| C3 | Quatro âmbitos de revogação, ordem anterior/posterior, 16 corridas concorrentes, pedido pendente, confirmação perdida, epochs/política persistentes |
| C4 | Alteração individual dos 17 vínculos recusada; IDs conflitantes, replay/reinício/expiração sem libertação; rollback/savepoint externo não apaga consumo |
| C5 | Crash real e perda de resposta após commit/cópia; observação sem permissão; sem retry/retoma |
| C6 | Cópia ausente, ack inválido, chave errada, restauro antigo, clone com nova encarnação, corrupção, quarentena e recuperação preservando estado |
| C7 | Apenas versão interna string `2`; rejeita `1`, versões desconhecidas e inteiro `2`; sem envelope ou capacidade operacional |

O teste de rollback/savepoint usa exclusivamente uma transação SQLite em memória
do chamador. Demonstra que esse rollback não liberta o consumo da autoridade;
não demonstra exclusividade de iniciação no alvo nem prevenção de SQL direto.

## Limitações materiais

- Durabilidade observada cobre transações SQLite, reabertura e morte de processo
  com `os._exit`; não comprova perda de energia, fsync físico ou corrupção de disco.
- A cópia e a chave HMAC são doubles sob o mesmo host/administrador. Não demonstram
  independência D09, segregação administrativa ou autenticação de produção.
- O relógio e a continuidade são entradas de teste; não implementam UTC autenticado.
  A monotonicidade local deteta alguns recuos, mas não constitui prova de UTC.
- Não existe raiz externa anti-rollback/anti-clone. Copiar autoridade, testemunho,
  identidade e chave em conjunto pode reativar poderes. Um teste de limitação
  reproduz esse contraexemplo. Comparar head e encarnação declarada não invalida
  instâncias antigas nem resolve clones com identidade idêntica.
- Não há proteção contra administrador malicioso, escrita direta nas bases,
  aliases do filesystem, troca do lock ou testemunho e estado revertidos juntos.
  A ordem demonstrada abrange instâncias conformes da mesma autoridade/lock.
- As estruturas e a serialização JSON locais são apenas internas ao laboratório.
  `json.dumps(sort_keys=True)` não é apresentado como JCS. Não se define domínio
  de assinatura R2, schema de evidência aprovado nem alteração aos 25 campos do
  payload operacional. Ed25519, JCS, validação de envelopes e interoperabilidade
  continuam pendentes de especificação/aprovação próprias.
- Não há prova de segunda iniciação impedida no alvo, execução exatamente uma vez,
  cancelamento, continuidade de sessão real, reconciliação humana ou reentrada.
  GAP-001/002 e os critérios operacionais C4/C6 continuam por demonstrar.

Este laboratório fornece evidência parcial sobre a máquina de admissão lógica.
Não satisfaz os critérios mínimos operacionais da baseline R2 nem altera gates,
contratos, parsers, executores, infraestrutura ou documentos históricos.
