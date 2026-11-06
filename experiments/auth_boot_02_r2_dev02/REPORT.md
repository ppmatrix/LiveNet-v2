# R2-DEV-02 — Resultado experimental

Executado em 2026-10-27 no repositório verificado por SSH:
`progbox:/home/paulo/projects/livenet-v2`.
HEAD: `647179c928888adfeef0f69f582fd13c5fc17350`.
Implementação nova limitada a `experiments/auth_boot_02_r2_dev02/`.

**36/36 testes passaram**, zero falhas/erros/skips, exit code 0, 44,752 s no runner
(44,751 s no unittest). PostgreSQL 16.15, Python 3.12.3, psycopg 3.3.6 já existentes.
`evidence.json` contém nomes, saída integral, medições e SHA-256 dos fontes.

Dois PostgreSQL temporários independentes em diretórios privados, TCP desativado,
socket 0700 e autenticação peer, sem instalar dependências. Durabilidade configurada
com fsync, synchronous_commit e full_page_writes ligados. Os dois clusters foram
terminados e o seu diretório temporário eliminado; `cleanup=true` na evidência.

## Evidência decisiva

| Ensaio | Resultado observado |
| --- | --- |
| Concorrência na autoridade | Uma admissão entre 24 threads; uma entre 8 processos |
| Admissão/revogação | Ordem persistida; quatro âmbitos, anterior/posterior e 12 corridas; pedido pendente não é eficácia |
| Confirmação perdida | Consumo permanece; consulta apenas observa; sem permissão, retry ou retoma |
| Crash real antes da reserva | Nenhuma admissão nem consumo local; nenhuma autorização emitida |
| Crash após reserva / commit local | Reserva externa sobrevive; namespace bloqueia e entra em quarentena; consumo local confirmado não se liberta |
| Crash após confirmação externa | Consumo persiste, reapresentação recusada |
| Reinício imediato de ambos os PostgreSQL | Recuperação WAL preserva ordem, consumo, vínculos, revogações, epoch e política; pendência continua bloqueante |
| Snapshot histórico da autoridade | Head 0 contra referência atual 1: deteção e quarentena, zero novas admissões |
| Clone concorrente com identidade/vínculos iguais | Referência única fora do clone: uma admissão e um bloqueio por divergência |
| Clones com aprovações diferentes | Só um ramo avança a referência partilhada |
| Referência indisponível / revertida isoladamente | Bloqueio sem fallback / divergência detetada |
| Referência também copiada | Duas admissões da mesma aprovação em ramos separados: contraexemplo de split-brain |
| SQL direto no alvo descartável | Dois UPDATE após uma admissão única: exclusividade no alvo não demonstrada |

O mecanismo usa um lock de sessão na referência, reserva durável externa, commit
local conjunto e recibo externo confirmado. Não presume atomicidade distribuída.
O journal e as tabelas materializadas são verificados antes de cada mudança.
Incerteza entre confirmações bloqueia progresso; não existe recuperação automática
de pendências. Todas as respostas são `executable=false`, inclusive `ADMITTED`.

## Independência, deteção e prevenção

A referência tem cluster e base próprios, fora de todos os snapshots/clones lógicos
da autoridade. A prevenção observada não depende de uma identidade de encarnação
autodeclarada diferente: clones com os mesmos vínculos concorrem na referência
externa única. Detetar divergência antes de decidir impede novas admissões conformes
no ramo atrasado. Não identifica qual ramo é legítimo, não invalida uma capacidade
antiga nem impede SQL fora do protótipo.

Esta independência é de estado e localização PostgreSQL no laboratório. Ambos os
clusters partilham host, utilizador e administração: **não constitui confirmação
D09 independente**. O clone é um dump/restauro integral da base experimental,
não uma cópia física de VM/memória/hardware. Copiar também a referência reabre
split-brain, como o contraexemplo confirma. O serviço pressupõe uma referência
única honesta; não implementa consenso, fencing ou autenticação de endpoint remota.

UTC é injetado; os testes validam intervalos e expiração após espera, não UTC
autenticado. A expiração limita A; o commit pode ocorrer depois. Recuperação WAL
após morte de processo não prova resistência a perda de energia ou armazenamento.
Envelopes, assinaturas, domínio/schema R2 e validação de vínculos operacionais
não foram implementados. Não há garantia de segunda iniciação impedida no alvo.

## Preservação e histórico de validação

`preservation.json` regista a comparação de **367 ficheiros preexistentes**, HEAD,
estado Git fora desta pasta e diff binário. A captura anterior completa fica em
`preservation.baseline.json`; o estado inicial já continha alterações de terceiros.
A verificação final confirmou zero ficheiros alterados/adicionados fora do
laboratório e igualdade de HEAD, estado e diff, com exit code 0.

A primeira suite passou 32/32. A ampliação para 36 testes encontrou um recibo de
controlos com tuple local versus lista JSON: o commit era conservado, mas a resposta
ficava UNKNOWN. Corrigida a representação do payload para lista antes de persistir;
a execução final passou 36/36. `evidence.initial.json` e
`evidence.intermediate.json` preservam as execuções anteriores.

Não se alteraram contratos R1/R2, parsers/executores operacionais, infraestrutura,
serviços, bases, volumes ou credenciais existentes. Não houve commits nem push.
AUTH-03/F02/G2/G4 permanecem fechados, GAP-001/002 abertas e DEV-09B não autorizada.

## Recomendação R2-DEV-03

Priorizar referência sob administração e domínio de falha separados, com identidade
e endpoint autenticados/fixados e política explícita de partição/split-brain.
Ensaiar fencing no alvo com instância antiga ainda ativa, clone, SQL direto,
rollback/savepoint e perda de confirmação. Demonstrar invalidação de capacidades
antigas antes de reentrada humana, novo pedido e nova aprovação. Acrescentar
confirmação D09 anterior ao percurso executável e UTC autenticado com incerteza.

R2-DEV-02 fica concluída como protótipo e demonstração parcial; os critérios
operacionais R2 continuam incompletos. Esta recomendação não autoriza DEV-03
ou integração operacional. Detalhes, pressupostos e reprodução em `README.md`.
