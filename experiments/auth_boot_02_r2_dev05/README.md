# R2-DEV-05 — laboratório de fencing no recurso

Executar em `progbox:/home/paulo/projects/livenet-v2`:

```sh
cd /home/paulo/projects/livenet-v2/experiments/auth_boot_02_r2_dev05
PYTHONDONTWRITEBYTECODE=1 ../../.venv/bin/python -B run_tests.py
```

O runner substitui `evidence.json`; guardar uma cópia antes de reproduzir.
Usa Python/psycopg e PostgreSQL 16 preexistentes, sem instalação. Reutiliza por
leitura `Cluster`, identidade local e cópia física de DEV-04; também executa os
dois testes DEV-04 originais num subprocesso sem escrever nessa pasta.
Os hashes dos módulos reutilizados constam da evidência.

Cada bateria cria uma raiz aleatória `/tmp/ln-r2d05-*`, dois clusters novos e
três clones físicos do alvo, feitos com o alvo parado. Os dois testes originais
criam outra raiz `/tmp/ln-r2d04-*` com três clusters novos. Todos usam sockets
privados 0700, `listen_addresses=''`, fsync, synchronous_commit e full_page_writes
ligados. Não há rede externa, instalação, serviço ou base operacional.
Os papéis SQL e mapas peer existem apenas nesses clusters descartáveis.

A limpeza termina cada cluster pelo diretório de dados próprio, valida a raiz
exata sob `/tmp` e remove só essa raiz. Interrupção abrupta pode impedir a
limpeza: inspecionar os caminhos da evidência antes de qualquer remoção manual;
nunca remover por glob. `cleanup=true` documenta a conclusão do runner normal.

## Fronteira experimental

`resource.apply` é SECURITY DEFINER com owner NOLOGIN e search_path fixo.
`old_writer` e `new_writer` só executam essa função, sem DML, ownership ou
associação entre papéis. O epoch é vinculado a `session_user`, não apenas ao
argumento fornecido pelo cliente. Uma linha do próprio recurso fica bloqueada
FOR SHARE desde a verificação até commit/rollback; alterar o fence requer lock
incompatível. SELECTs em snapshots antigos não substituem esse bloqueio.

`drain` avança epoch somente depois de drenar transações protegidas. Pode esperar
ou falhar por timeout; deixa o processo e a sessão antiga vivos. `strict_takeover`
é exclusivamente um ensaio de fencing **local**: verifica o pin da ligação,
desativa LOGIN do papel antigo, termina os seus backends neste cluster, observa
ausência e avança epoch. O recibo declara `LOCAL_RESOURCE_FENCED`,
`distributed_takeover_confirmed=false` e `process_cessation_proven=false`.

Esse controlador usa administração SQL confiada do cluster novo. A identificação
dos backends usa papel próprio, PID e backend_start; a observação posterior usa
nova instrução autocommit. Não configura identidades operacionais. O laboratório
usa a configuração PostgreSQL padrão sem prepared transactions; não cobre 2PC,
workers externos, replicação, restore de memória, processos com outras credenciais
ou revogação perante administrador adversarial. NOLOGIN não termina sozinho
sessões existentes. A terminação real, e não o booleano de uma health check,
provoca rollback dos efeitos em curso.

O pin é SO_PEERCRED + path/device/inode/PID/UID/GID/base da própria ligação,
provisionado por código confiado. Após reinício, pin antigo falha; só testes de
clone provisionam explicitamente novo pin do original. Não há mTLS, assinatura,
consenso, prova de energia desligada nem raiz de confiança remota.

## Evidência e limites

- A baseline reproduz as duas falhas DEV-04 sem alterar o código original.
- Os testes novos inspecionam o payload diretamente: consumo, recibo e epoch não
  são usados como substitutos da observação de efeito.
- Um clone completo mantém epoch e credenciais antigos. Mesmo após o controlador
  terminar as sessões do original, um backend vivo no clone consegue escrever.
  Um snapshot histórico permite repetir a mesma aprovação nos dois ramos.
- Uma thread antiga continua viva depois do recibo local. Ausência de backends
  neste cluster não prova cessação do processo nem de encarnações noutros recursos.
- `confirm_distributed_reentry` bloqueia sempre porque não existe verificador
  independente de cessação de todos os recursos. Nem flags forjadas, recibos
  locais ou observação após confirmação perdida habilitam reentrada.
- Partições são falhas injetadas no controlador; também há paragem real do alvo
  temporário e perda real de backend da âncora. Não se altera firewall/rede/host.
- Confirmação perdida é injetada depois do commit real, sem perda real de pacotes.
  Recuperação explícita é distinta da consulta de estado, sempre `resume=false`.
- O ledger externo de consumo é separado e durável perante rollback do alvo,
  mas continua dependente do broker: função direta pode evitar o consumo externo.
  A unicidade local é transacional e não substitui consumo externo irreversível.
- Superuser altera o payload contornando a função. Todos os clusters partilham
  host, utilizador OS e administrador; não há segregação administrativa.
- Efeitos são fixtures explícitas. O percurso normal bloqueia por D09 e UTC
  autenticado ausentes. Não se demonstra atomicidade distribuída/exatamente uma vez.

`preservation.py` foi executado por stdin antes de criar a pasta remota. Compara
conteúdo, modo e tamanho de todos os ficheiros/symlinks preexistentes, incluindo
ignorados, HEAD, estado Git e diff binário. Exclui `.git`, atime, diretórios vazios
e recursos externos. Só o diretório experimental novo é excluído da comparação.

R1/R2 e executores operacionais ficam fora da implementação. Gates fechados,
GAP-001/002 abertas, sem DEV-09B, commits, push ou Proxmox.
