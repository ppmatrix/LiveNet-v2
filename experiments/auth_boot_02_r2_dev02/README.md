# R2-DEV-02 — Laboratório PostgreSQL de continuidade

Autorização: pedido humano de 2026-10-27 nesta sessão, para execução experimental
isolada em `progbox:/home/paulo/projects/livenet-v2`. Baseline consultada diretamente:
`docs/architecture/auth-boot-02-r2.md`, C1–C7. Este laboratório não altera a baseline.

## Reprodução e isolamento

```sh
cd /home/paulo/projects/livenet-v2/experiments/auth_boot_02_r2_dev02
PYTHONDONTWRITEBYTECODE=1 ../../.venv/bin/python run_tests.py
```

Requer os binários já existentes de PostgreSQL 16 em `/usr/lib/postgresql/16/bin/`
e psycopg 3 no ambiente existente. Não instala dependências. O runner é Linux,
executado pelo utilizador normal, sem Docker, sudo ou gestor de serviços.

`Harness` cria dois clusters através de `initdb` em um novo diretório privado
`/tmp/ln-r2d02-*`: autoridade e referência. Todos os nomes de bases são aleatórios.
TCP fica desativado; socket e diretório são privados, modo 0700; autenticação
local peer e autenticação TCP reject. As ligações especificam sempre socket,
base e utilizador. Não se usam URLs, credenciais, serviços ou volumes existentes.
`fsync`, `synchronous_commit` e `full_page_writes` ficam ligados e são verificados.
O ensaio de SQL direto usa apenas uma terceira base descartável nesses recursos.

No fim, `pg_ctl` termina os dois clusters pela sua localização explícita; só se
elimina o diretório temporário criado pelo runner, validando pai e prefixo.
Se o runner sofrer SIGKILL, o seu `finally` não pode limpar: os recursos residuais
deverão ser identificados pelo caminho exato na evidência, nunca por glob global.
Os crashes intencionais afetam filhos experimentais ou os dois clusters próprios.

## Máquina experimental

Cada namespace tem uma única ordem de eventos. Todas as alterações conformes
adquirem um advisory lock de sessão na referência; depois bloqueiam a linha local
de estado. Revogações de aprovação, chave, autoridade e política, admissões e
alterações monotónicas de epoch/política usam esta mesma ordem. Um pedido pendente
de revogação é apenas uma observação do chamador, não uma fila durável nem eficácia.

Antes de cada alteração, o protótipo compara o head local com o head da referência
e verifica a cadeia completa do journal, consumo, vínculos, revogações e controlos.
Divergência ou reserva pendente causa quarentena persistente. Incrementar epoch
não ignora a quarentena. Não há API de desbloqueio ou reconciliação automática.

A elegibilidade em A é avaliada depois dos locks, com intervalo UTC injetado.
Exige `issued <= not_before < expires`, duração máxima 900 s, `L <= U`,
`L >= not_before`, `U < expires`, epoch/política correntes e ausência de revogação.
O teste que avança o relógio após A admite commit posterior ao prazo, conforme C2.
Não há implementação de UTC autenticado nem deteção autónoma de perda temporal.

1. A referência confirma duravelmente uma reserva pendente e, para admissão,
   um claim único de aprovação/tentativa. A reserva ainda não é admissão.
2. A autoridade confirma conjuntamente evento, consumo, vínculos, ordem e head.
3. A referência confirma recibo com payload/digest e avança o seu head; o chamador
   verifica o recibo antes de devolver `ADMITTED` experimental.

Não existe transação distribuída presumida. Falha antes da reserva não admite nem
consome; falha após a reserva deixa o namespace bloqueado. Falha após commit local
conserva consumo e bloqueia. Falha após confirmação da referência conserva consumo;
consulta posterior apenas observa e não emite permissão. Perda da resposta ou ack
ambíguo devolve `UNKNOWN`. Não há despacho, retry, retoma ou libertação de consumo.
Todas as respostas, incluindo `ADMITTED`, têm `executable=False` e `resume=False`.

`Approval` e `binding` são fixtures previamente confiadas ao modelo, não envelopes
assinados nem validação de aprovação humana. Não há protocolo de emissão.
Os vínculos persistidos não podem ser substituídos por outra admissão da mesma
aprovação/tentativa. A validação completa dos vínculos contra um payload assinado
e uma sessão protegida real permanece fora deste laboratório.

## Referência independente do estado clonado

O segundo cluster contém continuidade, reservas, claims e recibos. Não faz parte
dos dumps da autoridade. `pg_dump`/restauro copia todas as tabelas da autoridade,
inclusive estado, consumo, journal e vínculos; a identidade e os vínculos podem
permanecer iguais. Não se depende de uma encarnação autodeclarada diferente para
detetar o clone. Trata-se de clone lógico completo da base experimental, não de
snapshot físico de VM, filesystem, memória de processo ou hardware.

Contra referência atual única e honesta:

- Um snapshot histórico apresenta head antigo e é detetado/quarentenado antes de
  outra admissão: deteção de divergência com prevenção de nova admissão conforme.
- Dois clones iguais concorrem pelo mesmo lock externo. Só um avança; o outro
  encontra divergência e bloqueia. O claim externo também impede consumo duplicado.
- Duas aprovações diferentes em ramos inicialmente iguais também só deixam um
  ramo avançar. O mecanismo não escolhe qual cópia é a instância legítima.
- Uma referência indisponível bloqueia, sem fallback para estado local.
- Um restauro isolado da referência diverge do estado atual da autoridade.

O contraexemplo copia também a base da referência e entrega a cada ramo uma cópia
distinta. Ambos admitem a mesma aprovação. Essa observação é uma limitação esperada,
não um teste de resistência a split-brain aprovado. A referência não implementa
consenso, fencing contra instâncias antigas, eleição ou deteção de referência falsa.
Renomear namespace ou trocar endpoint não pode estar sob controlo do executor num
sistema real; o runner possui esses poderes exclusivamente para preparar fixtures.

## Alcance e limites

| Requisito | Evidência experimental e limite |
| --- | --- |
| C1/C3 | Transações PostgreSQL, 24 threads, 8 processos, 12 corridas de revogação, quatro âmbitos e ordem persistida |
| C2 | Intervalos e expiração durante espera; relógio injetado, sem UTC autenticado |
| C4 | Consumo e vínculos duráveis, sem libertação por rollback/savepoint; exclusividade no alvo não satisfeita |
| C5 | Mortes reais por `os._exit`, resposta perdida e ack ambíguo; observação sem permissão |
| C6 | Reinício imediato dos dois PostgreSQL, recuperação WAL, snapshots, clones, referência indisponível e corrupção; independência administrativa D09 não satisfeita |
| C7 | String interna `2`; sem alteração de parser, schema, assinatura ou bytes operacionais |

A referência é independente do conjunto de dados clonado nos ensaios, mas partilha
host, utilizador, administrador e domínio de falha. Socket peer limita acesso local;
não implementa confirmação D09 criptográfica/administrativamente independente.
O digest é SHA-256 sobre JSON interno, não JCS, assinatura R2 ou prova contra um
administrador que altera ambos os estados. Não há adversário Byzantine coberto.

Os testes de reinício imediato cobrem morte de processos e recuperação WAL, não
falha de energia, cache de hardware, destruição física, corrupção arbitrária ou
perda de um host. Uma interrupção durante o protocolo pode bloquear indefinidamente;
a disponibilidade e a recuperação humana de reservas não estão resolvidas.

A referência impede novas decisões conformes em ramos divergentes; não invalida
uma capacidade antiga já entregue, não interrompe uma execução e não controla SQL.
O teste de limite executa dois UPDATE diretos numa tabela descartável após uma
admissão única, comprovando que o alvo permanece contornável. Não há garantia de
segunda iniciação impedida ou execução exatamente uma vez.

Não há alterações de contratos R1/R2, parsers/executores operacionais, infraestrutura,
serviços ou credenciais existentes. AUTH-03/F02/G2/G4 ficam fechados; GAP-001/002
abertas; DEV-09B não autorizada; sem commits ou push.

## Próximo ensaio recomendado: R2-DEV-03

Preparar um laboratório separado com referência sob domínio de administração/falha
distinto, identidade e endpoint autenticados e fixados, sem cópia das suas raízes
de confiança para a autoridade. Definir comportamento sob partição e split-brain,
incluindo política fail-closed e perda deliberada de disponibilidade.

Demonstrar fencing no alvo: uma sessão/geração protegida deve impedir segunda
iniciação e SQL direto, inclusive quando uma instância antiga conserva contexto,
há clone concorrente, rollback/savepoint ou perda de confirmação. Provar invalidação
de capacidades antigas antes de reentrada humana, novo pedido e nova aprovação.

Definir a confirmação D09 anterior a qualquer percurso executável e a reconciliação
de reservas/consumos incertos, preservando a ausência de retoma automática. Acrescentar
UTC autenticado com limites de incerteza e perda de continuidade. Aprovação específica
continua necessária para bytes/schema R2 e para qualquer integração operacional;
esta recomendação não autoriza execução de R2-DEV-03 nem muda os gates.
