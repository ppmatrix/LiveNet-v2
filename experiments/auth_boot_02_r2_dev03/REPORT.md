# R2-DEV-03 — Resultado experimental

Executado em 2026-10-27, por SSH, em
`progbox:/home/paulo/projects/livenet-v2`.
HEAD: `647179c928888adfeef0f69f582fd13c5fc17350`.
Código novo exclusivamente em `experiments/auth_boot_02_r2_dev03/`.

**37/37 testes passaram**, zero falhas/erros/skips, exit code 0, 65,472 s.
Três PostgreSQL descartáveis, TCP desligado, sockets 0700 e durabilidade ligada;
todos terminados e diretório temporário eliminado (`cleanup=true`). Sem instalação.

## O que foi observado

| Ensaio | Resultado e alcance |
| --- | --- |
| 8 replays concorrentes da mesma sessão | Uma iniciação registada e um UPDATE pelo broker |
| Rollback e rollback a savepoint | Consumo no alvo permanece; efeito pode ficar zero; replay bloqueado |
| Vínculos e reconexão | Ticket alterado, outra ligação ou outra transação bloqueados |
| SQL direto pelo executor restrito | UPDATE, falsificação/remoção de consumo, alteração do fence e escalada de papel recusados |
| Fence com sessão antiga viva | Encarnação antiga bloqueada; consumo anterior não se liberta; novo pedido/aprovação de fixture pode avançar |
| Fence entre consumo e efeito | Um consumo, zero efeitos; sem retomada |
| Fence durante efeito em curso | Controlador aguarda commit; depois de regressar, tentativa antiga não inicia outro efeito |
| 12 sessões, autoridade clonada e referência única | Uma admissão e uma iniciação no alvo partilhado |
| Snapshot antigo da autoridade | Divergência detetada e quarentena |
| Autoridade e referência copiadas, alvo único | Duas admissões, uma iniciação/efeito no alvo |
| Autoridade, referência e alvo copiados | Um efeito em cada ramo: split-brain reproduzido |
| SQL com `target_service` | Segundo UPDATE contorna o broker: privilégio no alvo permanece limite explícito |
| Referência indisponível antes de A | Bloqueio; partição após admissão confirmada permite à sessão original prosseguir |
| Confirmação perdida em admissão, consumo ou commit | UNKNOWN; consulta não autoriza retoma; consumo não é libertado |
| Crash real antes do consumo / após consumo / após UPDATE / após commit | Contagens início/efeito: 0/0, 1/0, 1/0, 1/1; aprovação continua consumida |
| Reinício imediato dos três clusters | WAL preserva consumo, fence e admissão; reconexão não retoma ticket antigo |

O registo `starts` confirma consumo para iniciação; não prova efeito. O efeito é
medido separadamente. O UPDATE protegido mantém a ligação/transação vinculadas;
o consumo usa outra ligação para sobreviver a rollback. Não há atomicidade
distribuída nem garantia de execução exatamente uma vez.

## Garantias condicionais e pressupostos

A exclusividade observada cobre o executor sem privilégios e o percurso do broker
confiado, com um alvo/ledger único que não é revertido. Advisory locks só impõem
fencing a caminhos que os respeitam. O teste de SQL privilegiado demonstra que a
garantia universal exigida em C4 continua por satisfazer. A invalidação por fence
vale após confirmação no mesmo alvo; não resolve alvos clonados ou revertidos.

A referência tem cluster e papéis SQL próprios, fora dos clones da autoridade.
O serviço de escrita é confiado; não tem DDL/TRUNCATE ou administração, mas pode
reescrever estado permitido pelo seu papel. Todos partilham host, utilizador OS
e administrador; peer permite a esse utilizador assumir as identidades de serviço.
**Independência administrativa, domínio de falha separado e D09 não demonstrados.**
O código de coordenação conhece ambos os endpoints; não há serviço remoto
autenticado, consenso ou prova criptográfica de continuidade.

D09 bloqueia por omissão; os ensaios de efeito injetam `d09_assumed=True`.
UTC confiável é igualmente injetado. Não há UTC autenticado, aprovação humana
assinada, domínio/schema R2 aprovado ou integração com executores operacionais.
Todas as evidências continuam `executable=false`; nenhum gate é aberto.

## Preservação e reprodução

Baseline anterior à criação remota: **379 ficheiros tracked/untracked não ignorados**.
A comparação final confirmou zero alterações e zero adições fora da pasta,
HEAD/estado/diff iguais, exit code 0. Consta de `preservation.json`, com hashes completos em
`preservation.baseline.json`, HEAD, estado Git e diff binário. O repositório já
continha alterações de terceiros. O âmbito não inclui inventário de ficheiros
ignorados, `.git` ou recursos externos que não foram usados.

`evidence.json` contém nomes e saída integral dos 37 testes, medições, versões,
hashes dos fontes novos e dos dois módulos DEV-02 reutilizados. Reprodução em
`README.md`. `evidence.initial.json` conserva a execução anterior 33/33, antes
dos testes adicionais e do papel dedicado de escrita da referência. A invocação
inicial com Python global falhou por ausência de psycopg, antes de criar clusters;
foi usado o `.venv` preexistente, sem instalar dependências.

As partições são modeladas pela indisponibilidade do endpoint/socket privado
ou paragem do cluster próprio; não houve rede distribuída ou falha de host real.

Preservados contratos R1/R2, parsers, executores, serviços, bases, volumes e
credenciais existentes. Sem acesso ao Proxmox, commits ou push.
AUTH-03/F02/G2/G4 fechados; GAP-001/002 abertas; DEV-09B não autorizada.

## Recomendação R2-DEV-04

Demonstrar uma fronteira administrativamente separada para referência e broker,
com identidade/endpoint autenticados e fixados, confirmação D09 verificável antes
do percurso de efeito e UTC autenticado com intervalo de incerteza. Definir quem
pode possuir SQL privilegiado e que garantia é possível perante esse ator; testar
a remoção efetiva desses privilégios do executor, incluindo funções, ownership,
SET ROLE e caminhos alternativos. Qualquer instalação de extensão ou alteração
de infraestrutura deve ter autorização própria.

Ancorar geração/fence e continuidade do ledger do alvo fora dos seus snapshots;
repetir clone de alvo e split-brain com a instância antiga ainda viva. Demonstrar
invalidação antes de reentrada humana, novo pedido e nova aprovação, com oráculo
independente de início/efeito. Ensaiar confirmação perdida do próprio fence,
partição durante takeover e reconciliação sem retry automático. A proposta deve
explicitar perda de disponibilidade e bloqueio de transações em curso.

R2-DEV-03 concluída como protótipo e demonstração parcial. A recomendação
R2-DEV-04 não autoriza execução ou integração operacional.
