# R2-DEV-04 — laboratório isolado

Executar no repositório `progbox:/home/paulo/projects/livenet-v2`:

```sh
cd /home/paulo/projects/livenet-v2/experiments/auth_boot_02_r2_dev04
PYTHONDONTWRITEBYTECODE=1 ../../.venv/bin/python run_tests.py
```

Requer apenas o Python/psycopg e PostgreSQL 16 já instalados. Não instala pacotes,
extensões ou serviços. O runner substitui `evidence.json` nesta pasta; guardar a
evidência entregue antes de reproduzir, se for necessário preservar esse resultado.
As medições usam relógio local não autenticado. Uma execução termina com código
zero apenas se todos os testes passarem e a limpeza dos clusters for confirmada.

Cada execução cria uma raiz privada aleatória `/tmp/ln-r2d04-*`, três clusters
PostgreSQL e um clone físico temporário. TCP está desligado; sockets e diretórios
têm modo 0700. Os únicos mapas peer e papéis criados pertencem aos clusters novos.
Não se liga a bases, serviços ou credenciais operacionais. O clone copia a totalidade
do diretório de dados de um cluster parado, incluindo roles, bases e WAL; altera
apenas a configuração local do socket. Depois, original e clone ficam vivos
simultaneamente. Não é clone de memória, VM, host, autoridade externa ou testemunha.

O runner termina cada cluster pelo respetivo diretório de dados, valida que a raiz
fica diretamente em `/tmp` com o prefixo próprio e elimina apenas essa raiz.
Uma interrupção abrupta do runner pode impedir a limpeza; nesse caso inspecionar
o caminho exato devolvido pela evidência, sem eliminar diretórios por glob.

## O que os testes afirmam

- `executor` tem CONNECT/USAGE; sem propriedade, DML, funções de efeito, TEMP,
  CREATE ou associação a papéis privilegiados. `effect_owner` não tem LOGIN.
- `broker` pode apenas chamar uma função de UPDATE fixo com SECURITY DEFINER,
  proprietário separado e search_path fixo. O broker é componente confiado e
  consegue contornar a coordenação se usar diretamente essa função.
- O cluster externo mantém epoch, endpoint ativo, consumo por aprovação e auditoria.
  Não é incluído nos snapshots do alvo. Consumo e efeito são medidos separadamente.
- O lock partilhado externo permanece durante o efeito; takeover usa lock exclusivo.
  Há uma janela entre consumo durável e efeito, com nova validação do fence.
- A identidade local é verificada na própria ligação usada: SO_PEERCRED do kernel,
  path/device/inode/PID/UID/GID do socket, base de dados e principal SQL esperado.
  Reinício/substituição exige novo pin por configuração confiada; não há TOFU ou
  atualização automática. Não há autenticação criptográfica remota ou mTLS.
- Recibo de testemunha separado deve corresponder a aprovação, epoch, endpoint,
  nonce e intervalo UTC. É verificado antes do consumo e novamente antes do efeito.
  Intervalo invertido, ausente ou não inteiramente contido na janela bloqueia.
- O percurso normal bloqueia sempre porque D09 independente e UTC autenticado
  permanecem por demonstrar. Efeitos dos testes usam explicitamente `fixture=True`
  e `[100,102]`; estes valores sintéticos não são UTC confiável real.
- Reconciliação é observação somente leitura, com `resume=false` e
  `executable=false`; não restitui consumo nem faz retry de efeitos.

## Contraexemplos e limites deliberados

Perder a sessão do lock externo liberta a exclusão antes de parar a ligação ao
alvo. Os testes terminam apenas esse backend temporário para modelar a perda:
takeover confirma e, após essa confirmação, uma ligação antiga pode iniciar SQL
ou confirmar um UPDATE já iniciado. Os testes passam quando reproduzem a falha
esperada; não validam fencing universal. Um health check adicional conservaria
uma janela entre verificação e efeito.

As partições antes de acesso são injetadas no conector; não há alteração de rede,
firewall ou serviços. A perda do backend da âncora é real. O ensaio com lock vivo
verifica `pg_locks`: takeover espera até a transação de efeito terminar. Não existe
limite garantido para essa espera nem cancelamento retroativo de commits.

Todos os clusters partilham host, utilizador OS e administração. Esse utilizador
pode autenticar por peer como os vários serviços. Superuser/owner e o broker
confiado não são o executor restrito. A testemunha é outra base/cluster, não outro
domínio administrativo; o recibo não cobre uma cadeia completa de eventos D09,
assinaturas, completude, retenção ou durabilidade em falha física de host.
Não se inventa uma fonte UTC autenticada a partir de `now()` do PostgreSQL.

A evidência lista nomes, saídas, contagens, SQLSTATE de cada ataque SQL, versões,
hashes dos quatro fontes, caminho temporário e confirmação da limpeza. O oráculo
de efeito lê diretamente o payload do alvo por ligação de inspeção; não deriva
efeitos de recibos ou de consumo. Continua no mesmo domínio administrativo.

`preservation.py` foi executado por stdin antes da criação remota. Inventaria
conteúdo, modo e tamanho de ficheiros regulares e symlinks, incluindo ignorados,
fora da pasta nova; exclui `.git`. Também compara HEAD, estado Git e diff binário.
Não promete preservar atime, diretórios vazios ou recursos externos inventariados.
`preservation.baseline.json` conserva a baseline e `preservation.json` a comparação.

Não altera R1/R2 nem parsers/executores operacionais. Gates permanecem fechados,
GAP-001/002 abertas; sem DEV-09B, commits, push ou acesso ao Proxmox.
