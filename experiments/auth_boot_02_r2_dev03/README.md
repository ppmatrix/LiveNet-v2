# R2-DEV-03 — Fronteira experimental no alvo

Experiência autorizada pelo pedido humano de 2026-10-27 para
`progbox:/home/paulo/projects/livenet-v2`. Apenas UPDATE fixo numa tabela descartável.
Não é protocolo R2 executável, implementação operacional ou aprovação de schemas.

## Reprodução

```sh
cd /home/paulo/projects/livenet-v2/experiments/auth_boot_02_r2_dev03
PYTHONDONTWRITEBYTECODE=1 ../../.venv/bin/python run_tests.py
```

Utiliza PostgreSQL 16 em `/usr/lib/postgresql/16/bin/` e psycopg no `.venv`
preexistente. O Python global não tem psycopg; não instalar dependências.
Reutiliza, sem modificar, `../auth_boot_02_r2_dev02/harness.py` e `laboratory.py`.
O runner regista hashes dessas dependências e de todos os fontes novos.
Uma reprodução substitui apenas `evidence.json` desta pasta; preservar esse ficheiro
antes de repetir se for necessário conservar a execução entregue.

Três clusters novos em `/tmp/ln-r2d03-*`, bases de nomes aleatórios, TCP desligado,
sockets/diretórios 0700, peer com mapas locais apenas nos clusters descartáveis,
host auth reject. Sem passwords, sudo, Docker, Proxmox ou serviços existentes.
Os papéis novos só existem nestes clusters. `fsync`, `synchronous_commit` e
`full_page_writes` permanecem ligados. A limpeza valida pai/prefixo e termina
apenas os clusters pelos seus diretórios explícitos antes de remover a raiz própria.
SIGKILL do runner pode impedir limpeza; nesse caso inspecionar os caminhos exatos
da evidência, sem apagar diretórios de outros ensaios por glob.

## Fronteira e ordem dos eventos

1. O broker abre a transação protegida no alvo; recolhe backend PID, transaction ID,
   epoch, encarnação e geração. Constrói os vínculos internos para a admissão.
2. A autoridade DEV-02 mantém avaliação A, consumo, ordem e confirmação externa.
   Só a resposta ADMITTED diretamente recebida cria um ticket em memória da sessão.
   Consulta posterior não cria ticket. Uma nova ligação/transação não o aceita.
3. Outra ligação ao mesmo alvo confirma um registo único `starts`, por aprovação
   e tentativa. Este consumo fica fora da transação do UPDATE e sobrevive ao seu
   rollback/savepoint. Registar início não prova efeito nem sucesso da operação.
4. A ligação protegida volta a verificar o fence sob advisory lock partilhado e
   executa o UPDATE fixo na mesma transação/sessão ligada à admissão.
5. O controlador altera epoch/encarnação sob advisory lock exclusivo. Aguarda
   transações que já entraram na secção protegida. Quando a confirmação do fence
   regressa, pedidos antigos conformes já não podem iniciar efeitos nesse alvo.

Não há atomicidade entre autoridade, referência, consumo no alvo e UPDATE. Pode
haver consumo sem efeito. Confirmação perdida deixa UNKNOWN; não há retry,
retoma automática, libertação de consumo ou API de reconciliação autorizadora.
Um fence entre consumo e UPDATE bloqueia o UPDATE, conservando o consumo.
O fence pode esperar indefinidamente por uma transação presa; não há garantia de
latência, cancelamento retroativo ou eleição automática de uma instância legítima.

## Papéis e pressupostos

`executor` não possui direitos nas tabelas nem CREATE no schema; não pode assumir
os papéis de serviço. `target_service` possui SELECT no fence, SELECT/INSERT no
consumo e SELECT/UPDATE no payload. Não é proprietário ou superuser.
`reference_service` tem SELECT/INSERT/UPDATE nas tabelas da referência, sem
DDL/TRUNCATE ou administração; é componente confiado. `reference_reader` só lê;
`authority_client` e `executor` não reescrevem a referência.

O serviço de referência e o broker são fronteiras de confiança, não adversários
cobertos. A classe Laboratory é executada pelo coordenador confiado e recebe o
DSN do serviço de referência. Os testes não implementam um serviço remoto separado.
O processo de teste mantém acesso administrativo para criar fixtures e crashes.
Tudo partilha host e utilizador OS: esse utilizador pode autenticar como os vários
papéis por peer. Segregação SQL não equivale a administração independente/D09.

O broker é o único caminho permitido ao executor no modelo. Quem obtiver
`target_service`, propriedade da tabela ou superuser pode executar SQL que ignora
os advisory locks e o consumo. O contraexemplo executa o segundo UPDATE usando
o próprio papel de serviço. Não existe proteção PostgreSQL contra esse privilégio.
Os tickets internos não são assinaturas, envelopes, JCS ou formatos operacionais;
a integridade da memória do broker e a configuração dos endpoints são pressupostas.

D09 bloqueia por omissão. Os testes de efeito usam explicitamente
`d09_assumed=True` para explorar a fronteira; essa fixture não demonstra D09.
As respostas DEV-02 e a evidência final continuam `executable=false`.
UTC é injetado; `trusted=True` é fixture, não fonte autenticada.

## Ensaios e interpretação

Os testes positivos contam `starts` e o valor da tabela de efeito separadamente.
As partições são modeladas por endpoint/socket indisponível e paragem de cluster;
não há rede distribuída real neste laboratório local.
Incluem replay concorrente, mutação de vínculos, rollback/savepoint, SQL direto
restrito, fence com sessão antiga viva e durante a janela consumo/efeito, clone
concorrente, referência indisponível, partição após confirmação, morte do alvo,
confirmações perdidas e observação sem retoma. Quatro filhos morrem realmente
com `os._exit`; os três clusters sofrem paragem imediata e recuperação WAL.

Copiar autoridade e referência produz duas admissões; um alvo partilhado ainda
permite um só consumo. Copiar também o alvo vazio permite um efeito em cada ramo.
São dumps/restauros lógicos, não clones de VM/memória. A unicidade da referência
e do alvo, a não reversão do ledger/fence e a administração honesta são pressupostos.
Não há consenso, testemunha externa do fence ou continuidade autenticada do alvo.
Paragem imediata demonstra recuperação WAL, sem provar resistência a perda de
energia, armazenamento hostil ou perda física do host.

`preservation.baseline.json` e `preservation.json` verificam ficheiros tracked e
untracked não ignorados, HEAD, estado Git exterior a esta pasta e diff binário.
Não inventariam conteúdo de `.git`, ficheiros ignorados ou bases/volumes externos.
Contratos R1/R2, parsers e executores operacionais não são modificados.
AUTH-03/F02/G2/G4 fechados; GAP-001/002 abertas; sem DEV-09B, commits ou push.
