# R2-DEV-04 — resultado experimental

Executado em 2026-10-27 por SSH em `progbox:/home/paulo/projects/livenet-v2`.
Acesso e estado verificados antes de escrever. HEAD preservado:
`647179c928888adfeef0f69f582fd13c5fc17350`.
Código novo limitado a `experiments/auth_boot_02_r2_dev04/`.

**63/63 testes passaram**, zero falhas/erros/skips, exit code 0, 86,719 s.
A passagem inclui contraexemplos esperados: **fencing universal continua refutado**.
Os três clusters descartáveis e o clone físico foram terminados e eliminados;
`cleanup=true`. Sem instalações ou exposição TCP.

| Demonstração | Observação e alcance |
| --- | --- |
| Executor SQL restrito | 34 tentativas recusadas com SQLSTATE 42501: DML/SELECT, ownership, SET ROLE/session authorization, grants, funções diretas/preparadas/DO/search_path, schemas/TEMP, triggers/rules, COPY, ficheiros/programas e extensão. Nenhuma extensão foi criada. |
| Propriedade e funções | Executor sem associações privilegiadas; owner sem LOGIN; broker sem DML direto, apenas função fixa SECURITY DEFINER com search_path fixo. |
| Administrador/broker | Superuser fez UPDATE e broker chamou a função sem coordenação: zero consumos, dois efeitos. Ambos estão fora da fronteira do executor restrito. |
| Consumo externo e concorrência | Oito tentativas da mesma aprovação: um efeito e sete consumos já usados. Rollback no alvo conserva consumo externo. |
| Clone físico completo do alvo | Diretório de dados integral copiado com alvo parado; mesmo system_identifier, roles, bases e WAL. Original e clone depois vivos. Endpoint clonado rejeitado; epoch antigo bloqueado; aprovação nova na instância ativa produz um efeito, clone zero. Copiar o alvo não copia o consumo externo. |
| Sessão antiga e fence | Com ligação antiga viva, pedidos antigos bloqueados. Fence entre consumo e efeito conserva um consumo e zero efeitos. |
| Transação em curso | Com sessão da âncora viva, pg_locks confirma takeover à espera; confirmação só regressa depois de terminar o efeito protegido. Espera sem limite garantido. |
| Perda da sessão da âncora | Backend temporário realmente terminado. Takeover confirma epoch 2; depois a ligação antiga inicia SQL e produz um efeito. Outro teste confirma commit antigo posterior ao fence. Locks externos não impõem fencing no alvo após perder a sessão. |
| Confirmações perdidas | Fence, consumo ou commit devolvem UNKNOWN. Consulta posterior não emite ticket nem autoriza retry; aprovação consumida permanece indisponível. |
| Partições | Âncora indisponível durante takeover ou entre consumo/efeito bloqueia progressão; testemunha ausente antes do consumo ou da segunda verificação também bloqueia. Falhas pré-acesso são injetadas no conector. |
| Identidade/endpoint | SO_PEERCRED e pin local verificados na própria ligação: socket, device/inode/PID/UID/GID, base e principal SQL. Clone, outra base e principal trocado rejeitados. |
| D09 e UTC | Recibo separado e vínculos verificáveis apenas em fixture; intervalo UTC sintético validado por inclusão integral na janela. Gate normal bloqueia mesmo com recibo presente. Independência D09 e UTC autenticado continuam sem demonstração. |

## Interpretação

A âncora reside num PostgreSQL separado, fora dos snapshots do alvo, e conserva
epoch, endpoint ativo e consumo. A garantia observada exige âncora única sem
rollback, broker honesto, configuração confiada e sessão de exclusão contínua.
Copiar também a âncora não é resolvido. Não há consenso, fencing físico, prova
independente de cessação antiga ou atomicidade distribuída entre consumo e efeito.
O oráculo lê o payload diretamente; consumo/recibo não equivalem a efeito.

O contraexemplo termina apenas o backend próprio da âncora como injeção de falha;
não trata o administrador dessa injeção como executor restrito. A ligação ao alvo
continua viva. A rotina antiga só deteta a perda ao voltar à âncora, já depois do
efeito. Acrescentar verificações de conectividade não elimina a janela distribuída.

A autenticação demonstrada é local, mediada pelo kernel. Todos os clusters
partilham host, utilizador OS e administrador; peer permite a esse utilizador
assumir as identidades de serviço. Não há identidade remota assinada/mTLS nem
segregação administrativa. O pin é provisionado pelo coordenador confiado, fora do
clone; reinício exige configuração explícita nova. Não é raiz de confiança R1.

O recibo de fixture liga aprovação, epoch, endpoint, nonce e intervalo `[100,102]`,
e é consultado antes do consumo e antes do UPDATE. Não demonstra cópia completa
dos eventos críticos, durabilidade física ou domínio independente exigidos em D09.
O relógio local/`now()` de PostgreSQL não fornece UTC autenticado nem um limite
confiável de erro. Fonte temporal autenticada, custódia e domínio D09 independente
exigiriam infraestrutura fora deste âmbito: documentados, sem provisionamento.
Todos os efeitos positivos usam explicitamente `fixture=True`; `executable=false`.

## Preservação e reprodução

**9.109 ficheiros/symlinks preexistentes preservados**, incluindo ignorados:
zero alterações de conteúdo/modo/tamanho e zero adições fora da pasta nova.
HEAD, estado Git e diff binário iguais. Exclui conteúdo interno de `.git`, atime,
diretórios vazios e recursos externos, que não foram usados.
`preservation.baseline.json` contém os hashes; `preservation.json` a comparação.

`README.md` contém reprodução e limites. `evidence.json` contém saída integral,
medições, versões e hashes dos quatro fontes executados. `evidence.initial.json`
preserva a execução 51/52: a tentativa CREATE EXTENSION sem schema devolveu
3F000, antes da verificação de permissão; com schema explícito devolveu 42501.
A primeira invocação não guardou evidência por a pasta copiada ter modo 0500;
a pasta nova recebeu escrita e foi repetida. Os recursos próprios dessa invocação
também foram limpos. Nenhum ficheiro preexistente recebeu chmod ou escrita.

Contratos R1/R2, parsers/executores operacionais e recursos existentes preservados.
Sem serviços/bases/volumes/credenciais operacionais, Proxmox, commits ou push.
AUTH-03/F02/G2/G4 fechados; GAP-001/002 abertas; sem DEV-09B.

## Recomendação R2-DEV-05

Definir uma fronteira de efeito que imponha fence no próprio recurso mesmo após
perda da sessão externa. Exigir prova verificável de cessação da instância antiga
antes de confirmar takeover/reentrada; até lá, bloquear ambos os percursos em
incerteza. Ensaiar precisamente as duas janelas que falharam nesta experiência,
incluindo perda da âncora antes do SQL e antes do commit, clone e snapshot antigo.

Preparar proposta separada para identidades/endpoint autenticados remotamente,
segregação administrativa de broker/âncora/testemunha, confirmação D09 dos eventos
críticos e fonte UTC autenticada com erro limitado. A proposta deve discriminar
privilégios, custódia, disponibilidade perdida e infraestrutura necessária. Não
assumir que mais um health check, uma extensão ou um recibo local resolve essas
condições. R2-DEV-05 é recomendação; não autoriza infraestrutura ou integração.
