# R2-DEV-05 — resultado experimental

Executado em 2026-10-27 por SSH em `progbox:/home/paulo/projects/livenet-v2`.
Acesso, instruções e estado verificados antes de criar a área nova.
HEAD: `647179c928888adfeef0f69f582fd13c5fc17350`.
Implementação limitada a `experiments/auth_boot_02_r2_dev05/`.

**36/36 testes passaram**: 2 contraexemplos DEV-04 originais + 34 ensaios novos;
zero falhas/erros/skips, exit code 0, 56,998 s. Os testes que reproduzem falhas
passam quando observam o contraexemplo esperado; não validam fencing universal.
Ambas as baterias confirmam limpeza dos seus clusters e diretórios temporários.

**Resultado central:** fence verificado e bloqueado dentro da transação do recurso
fecha localmente as duas janelas DEV-04, mesmo perdendo o backend da âncora.
Desativar o papel antigo e terminar os seus backends força rollback antes da
confirmação local. Isso não prova cessação da encarnação distribuída: um backend
no clone e um processo antigo continuam vivos. Reentrada distribuída permanece
bloqueada, incluindo perante recibo local ou flag de cessação forjada.

| Ensaio | Observação verificável |
| --- | --- |
| DEV-04, perda da âncora antes de SQL | Fence externo confirma epoch 2; depois ocorre um efeito antigo. Falha original reproduzida sem alterações. |
| DEV-04, perda após SQL antes de commit | Fence externo confirma; commit antigo posterior produz efeito. Falha original reproduzida. |
| Fence no recurso, antes de SQL | Sessão antiga viva recebe 42501; um consumo externo, zero efeitos. Epoch é vinculado ao principal SQL. |
| Fence no recurso, SQL já iniciado | `pg_stat_activity` observa takeover à espera de lock do recurso; confirmação só ocorre após commit antigo. Não há commit protegido antigo posterior à confirmação. |
| Cessação SQL local, ambas as janelas | Backend da âncora realmente terminado; papel antigo passa a NOLOGIN; backends antigos realmente terminados e ausência observada. SQL/commit antigo falha; UPDATE não confirmado sofre rollback. Novo papel avança só em fixture. |
| Sessões e concorrência | Cinco sessões antigas terminadas; reconexão concorrente ensaiada; oito tentativas da mesma aprovação produzem um efeito no recurso único. Não constitui prova exaustiva de todos os interleavings. |
| Transação antiga sem terminar | Timeout bloqueia confirmação; epoch permanece 1. Disponibilidade pode ser perdida. |
| Snapshots transacionais e prepared statement | REPEATABLE READ/SERIALIZABLE antigos dão serialization failure; instrução preparada antiga recebe 42501 após fence. |
| Clone físico com sessão antiga viva | Após cessação local no original: original epoch 2/zero efeitos; clone epoch 1/um efeito antigo. Recibo local não prova cessação global. |
| Snapshot físico histórico | Mesma aprovação produz um efeito em cada ramo: restauração recupera epoch e ledger locais antigos. |
| Endpoint e reinício | Clone rejeitado pelo pin; fence e NOLOGIN sobrevivem ao reinício real; pin antigo bloqueia controlador até configuração explícita nova. |
| Partição e recuperação | Indisponibilidade antes do controlo ou após freeze não confirma takeover. Recuperação requer invocação explícita; consultar estado não faz retry. Paragem real do alvo também impede confirmação. |
| Confirmação perdida | Commit do fence ou do efeito ocorre, resposta é injetada como UNKNOWN; observação é só leitura e não autoriza retoma. Consumo externo continua indisponível. |
| Rollback/savepoint | Consumo externo permanece com zero efeitos; ledger local pode reverter com a transação. Não há atomicidade distribuída. |
| Privilégios e limites | Oito tentativas de DML/alteração de fence/identidade/escalada recusadas com 42501; executor não chama efeito. Superuser contorna a função; chamada direta autorizada contorna consumo externo, mas não o fence local. |

## Alcance da prova

A função SECURITY DEFINER mantém FOR SHARE na linha de epoch até terminar a
transação; a alteração do fence precisa de lock incompatível. Perder a ligação
externa já não liberta essa proteção. `drain` demonstra serialização local, não
cessação do processo: commits anteriores continuam válidos e não são desfeitos.

O ensaio `strict_takeover` usa um controlador administrativo confiado do cluster
descartável: verifica identidade na própria ligação, congela novos logins,
termina os backends do papel dedicado, observa ausência e persiste novo epoch.
O recibo declara expressamente `LOCAL_RESOURCE_FENCED`,
`distributed_takeover_confirmed=false` e `process_cessation_proven=false`.
É evidência de revogação/cessação das sessões SQL identificadas nesse recurso,
sem prova independente de cessação do processo, host ou cópias noutros recursos.

O clone preserva roles, bases, WAL e estado antigo; o original não consegue
revogar o papel nessa cópia. A thread de aplicação antiga também continua viva
depois do recibo. Não existe nesta experiência um verificador independente capaz
de autorizar takeover distribuído. `confirm_distributed_reentry` bloqueia sempre.
Mais health checks ou recibos locais não eliminam estes contraexemplos.

Todos os clusters partilham host, utilizador OS e administrador. SO_PEERCRED e
pin de socket são autenticação local; não há identidade remota assinada/mTLS,
isolamento administrativo, consenso, fencing físico, 2PC ou proteção universal
contra administrador/owner. A partição é injeção no controlador, sem falha real
de rede/host; a confirmação perdida também é injetada depois do commit real.
As janelas de crash em todos os pontos do controlador não foram exaustivamente
exploradas. O ledger externo depende de broker honesto e autoridade sem rollback.

Efeitos positivos usam `fixture=True`. O percurso normal continua bloqueado;
D09 independente e UTC autenticado não demonstrados. `executable=false`.

## Preservação e reprodução

Baseline: **9.120 ficheiros/symlinks preexistentes**, incluindo ignorados.
Comparação final: zero alterações, zero adições fora da área nova; HEAD, estado
Git e diff binário iguais. Nenhum diretório `/tmp/ln-r2d04-*` ou
`/tmp/ln-r2d05-*` permaneceu na inspeção final.
`preservation.json` regista comparação final de conteúdo/modo/tamanho, HEAD,
estado Git e diff binário; `preservation.baseline.json` contém hashes completos.
Exclui `.git`, atime, diretórios vazios e recursos externos não utilizados.
README contém comando de reprodução, pressupostos e limites. `evidence.json`
contém resultados integrais, medições, versões e hashes dos fontes novos/reutilizados.

`evidence.initial.json` conserva a bateria anterior 28/28. A primeira invocação
executou testes mas não conseguiu gravar evidência porque a cópia criou a pasta
nova com modo 0500. Foi corrigida somente a pasta experimental e repetido o runner;
não se reivindica resultado detalhado da invocação sem artefacto. A verificação
final de diretórios temporários complementa os indicadores de limpeza dos runners.

Contratos R1/R2, parsers/executores e recursos operacionais preservados. Sem
instalações, TCP externo, Proxmox, commits ou push. AUTH-03/F02/G2/G4 fechados;
GAP-001/002 abertas; sem DEV-09B.

## Recomendação objetiva — proposta R2-DEV-06

Preparar desenho verificável de uma fronteira de efeito fora do domínio de cópia
e rollback do alvo, com identidade de recurso não clonável e atuador de revogação
que cubra todos os caminhos de efeito. Definir quem pode atestar cessação, a que
encarnação/recurso/epoch a prova se vincula, frescura, durabilidade e condições
de rejeição durante partição, confirmação perdida e recuperação.

Antes de qualquer integração, exigir teste independente em que o ramo antigo
permanece vivo e tenta escrever depois da confirmação: sucesso desse ramo deve
impedir confirmação/reentrada. Na ausência de prova verificável, bloquear ambos
os percursos operacionais e aceitar perda de disponibilidade. Incluir proposta de
segregação administrativa, identidade remota, auditoria D09 e UTC autenticado com
erro limitado. Não provisionar infraestrutura nem abrir gates nesta etapa.
