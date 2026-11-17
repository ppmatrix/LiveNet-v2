# DEV-STABILITY-01 — Fase B: transporte HTTPS DEV

Estado: implementado e validado em testes isolados; **não ativado no DEV**.
Base: main, `590468ee7a81edc3dff9a0e6adf620a66476c811`, Python 3.12,
Werkzeug 3.1.9. A implementação não demonstra a causa histórica do incidente.
Não inicia a Fase C nem instala supervisão.

## Âmbito e implementação

`installation.https.DevHTTPSServer` reutiliza o listener TCP e o handler WSGI
do Werkzeug. O listener permanece TCP: nenhuma negociação TLS ocorre no accept.
Uma pool fixa executa o handshake explícito e um único pedido por ligação.
Ao esgotar a capacidade, a ligação TCP nova é fechada e contabilizada; não se
tenta negociar TLS nem enviar uma resposta HTTPS 503 no ciclo de aceitação.

O handler reutiliza o parser HTTP do Python. O input aplica deadlines monotónicos
absolutos antes de cada leitura de rede: enviar bytes regularmente não renova o
prazo. O corpo completo, com tamanho limitado, é recebido antes de chamar WSGI.
Corpos interrompidos não chegam à aplicação nem iniciam transações aplicacionais.
O input entregue à aplicação é memória; a drenagem final do Werkzeug não lê a
rede. A resposta tem um prazo absoluto desde a primeira escrita, incluindo todas
as escritas seguintes e cada envio TLS parcial. Existe suporte ao chunked com
comprimentos hexadecimais e CRLF estritos e a `Expect: 100-continue`, após
validação de framing/tamanho. Extensões/trailers chunked continuam sem suporte,
como no decoder anterior; não são silenciosamente aceites.

Content-Length repetido, negativo, inválido, combinação Content-Length com
Transfer-Encoding e codificações de transferência diferentes de chunked são
recusados. Defeitos do parser de headers, nomes inválidos, controlos, folding
obsoleto, Host repetido/ausente em HTTP/1.1 e Expect repetido são recusados.
Request line e headers exigem CRLF e a linha vazia final: EOF não substitui
o terminador nem permite chamar WSGI com um pedido incompleto.
Não existe keep-alive ou pipelining entre pedidos: cada ligação fecha
após um pedido. A negociação TLS admite TLS 1.2 ou superior.

## Limites por omissão

| Limite | Valor | Efeito |
| --- | --- | --- |
| Workers HTTP/TLS | 4 | Inclui ligações em handshake, receção e aplicação |
| Backlog TCP solicitado | 8 | Fila do kernel; o SO pode ajustar a capacidade |
| Admissões no processo | 4 | Inclui o trabalho ainda não iniciado pela pool; sem fila adicional de espera |
| Handshake | 5 s | Desde a admissão TCP, incluindo espera pela pool |
| Headers e request line | 10 s / 64 KiB agregados | Prazo absoluto; limites de linhas/quantidade do parser também se mantêm |
| Corpo | 15 s / 1 MiB descodificado | Prazo absoluto desde a preparação da receção do corpo |
| Bytes recebidos na ligação | 64 KiB + 2 MiB | Limite adicional para overhead/framing chunked |
| Escrita da resposta | 10 s | Prazo absoluto desde a primeira escrita |
| Encerramento HTTP | 5 s | Fecha listener/sockets e aguarda a pool dentro deste orçamento total |
| Encerramento Discovery | Até mais 5 s | Sinaliza apenas o worker existente e aguarda a thread |

Os limites são centralizados na classe `Limits`, sem mudar o formato da
configuração operacional. Os testes usam prazos curtos e limites menores.
Os quatro workers deixam margem face ao limite runtime documentado de dez
ligações DB e ao worker existente; isto não altera privilégios ou configurações
PostgreSQL, nem demonstra capacidade sob qualquer carga possível.

Login e decisões/início Discovery conservam o limite aplicacional de 16 KiB.
Inventory não tinha um limite explícito de tamanho da descrição no contrato
Python: passa a existir um teto de transporte de 1 MiB para o pedido inteiro,
com 413 acima desse valor. Trata-se de uma restrição de transporte explícita,
não de um novo limite de caracteres do campo. Headers excessivos dão 431;
framing ambíguo dá 400. Timeouts de transporte encerram a ligação; o cliente
não deve presumir que receberá uma resposta HTTP de erro.

## Ciclo de vida e diagnóstico

`serve` passa a chamar `run_dev_https`, sem reloader, subprocessos ou dependências
novas. Carrega TLS e faz bind antes de construir a aplicação, uma única vez.
Uma falha de bind não constrói a factory e não cria worker Discovery.
Configuração de origem, TrustedProxy desativado, autenticação, sessões, CSRF,
cookies e RBAC continuam nas mesmas factories e serviços.

SIGINT/SIGTERM sinalizam stop/cancel no worker pertencente à aplicação e pedem
paragem do servidor. O handler do sinal limita-se a atribuir um booleano, sem
locks, logging ou Event.set; o ciclo regular sinaliza o worker antes de fechar
o transporte. Os sockets, incluindo os que negoceiam TLS, são encerrados
sem TLS unwrap bloqueante. A transferência de posse do socket TCP para TLS é
protegida pelo mesmo lock usado no encerramento. O servidor não cria nem relança
workers Discovery. Não tenta terminar threads Python de forma assíncrona.
O iterável WSGI é fechado exatamente uma vez, também quando a limpeza interna
do Werkzeug encontra um socket já fechado. Uma falha parcial ao iniciar a pool
aguarda somente as threads que efetivamente arrancaram.

O logger `livenet.https` emite eventos JSON de início/paragem, timeout por fase,
erro TLS/transporte, rejeição, fecho e duração do pedido. Os contadores incluem
aceites, ativos, pico de ativos, rejeitados, concluídos e timeouts por fase.
São acessíveis internamente por `snapshot()` e nos eventos de fecho/rejeição;
não se adicionou endpoint de administração ou monitorização.
Não são incluídos endereço do cliente, URL, query string, headers, cookies,
corpo, credenciais, erro bruto ou contexto Discovery. Mensagens/tracebacks
fornecidos ao logger de transporte pelo Werkzeug são substituídos por evento
genérico. Não se altera o logging dos serviços aplicacionais existentes.

Se código aplicacional/DB não regressar dentro da graça, o diagnóstico informa
`clean=false`. O entrypoint recusa declarar encerramento limpo, com erro genérico
`HTTPS_SHUTDOWN_INCOMPLETE` e o código 78 já usado pelo CLI. As threads HTTP são
daemon: isto não é uma garantia de cancelamento transacional. Não se pode inferir
rollback de uma operação porque o socket fechou. Não há retry automático.

## Validação isolada

Testes novos: `backend/tests/test_dev_https.py`. Todos os listeners usam
127.0.0.1 e porta efémera diferente de 8443. Os certificados são gerados em
diretório de teste por OpenSSL existente; o cliente valida a confiança explícita
e o hostname. O fixture proíbe `Settings.connect` e `Worker.start`, remove a
variável operacional Discovery e usa WSGI/Flask sintético ou o OfflineStore.
Os ensaios de sinais usam subprocessos novos, com aplicação sintética e sem
thread/worker Discovery real; só esses processos recebem SIGINT/SIGTERM.

Cobertura de transporte:

- Ausência de ClientHello, ClientHello parcial e tráfego que não é TLS.
- Headers/corpos incompletos, EOF e fecho inesperado antes de executar WSGI.
- Headers e corpos Content-Length/chunked enviados byte a byte em intervalos
  inferiores ao timeout; o deadline absoluto continua a expirar.
- Pedidos concorrentes, saturação, rejeição e recuperação de capacidade.
- Três ciclos de saturação com pico de quatro ligações, quatro threads fixas
  e sem aumento persistente de descritores após libertação.
- Cliente que não lê uma resposta grande; timeout absoluto de escrita.
- Health abaixo de dois segundos com clientes problemáticos e capacidade livre.
- Limites de headers/corpo/framing, chunked e 100-continue.
- Paragem com ligações pendentes, indicação honesta de aplicação bloqueada,
  factory única e erro quando o worker não termina dentro do prazo.
- Ausência de dados sintéticos sensíveis nos eventos de transporte.

O percurso HTTPS real de compatibilidade utiliza a factory padrão com store
offline: frontend/login, sessão, flags Secure/HttpOnly/Lax, CSRF, origem,
recusa de forwarded headers, Inventory, logout e Discovery desativada.
As regressões Discovery existentes usam probes simulados e SQLite; não validam
locks PostgreSQL reais nem executam pesquisas na rede.

Resultados em 12/11/2026: ronda integrada com transporte, instalação/runtime,
security API/policy/service, Inventory API/service/schemas e Discovery:
**341 pass em 22,23 s**. Após reforçar apenas chunked/escrita/encerramento, ronda
final de transporte: **27 pass em 10,37 s**. As rondas sobrepõem-se; não somar.
Última verificação da integração do diagnóstico de encerramento com o CLI:
**3 pass, 24 deselected em 0,77 s**, apenas os testes afetados.
Nenhum teste usa a base operacional ou a porta 8443. Comando da ronda final:

```bash
env -u LIVENET_DISCOVERY_CONFIG PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend \
  .venv/bin/python -B -m pytest -q -p no:cacheprovider \
  backend/tests/test_dev_https.py
```

## Ativação futura — requer autorização própria

1. Rever o diff e resultados, incluindo a revisão final abaixo. Confirmar a
   baseline Fase A em
   `/home/paulo/.local/state/livenet-v2-standard-dev/baselines/dev-stability-01-phase-a-20261112T200158Z`:
   manifesto, `recovery-validation.json` com passed=true e backup legível,
   254965 bytes, SHA-256
   `63e9a5443a2cb226ba0a5c1584b56f6263ae8d637ffb90fbab310ac69c62f8cb`.
   Verificar SHA256SUMS a partir desse diretório, sem imprimir os materiais
   privados. Se escritas posteriores o exigirem, obter backup atualizado antes
   da transição. A cópia externa não é presumida; continua pendente.
2. Identificar o PID proprietário do socket 127.0.0.1:8443 por `ss`, cruzando
   com `/proc/<pid>/stat` (instante de arranque), exe, cwd e cmdline. Exigir
   diretório deste projeto, intérprete esperado e `-m installation serve`
   com `--config` no estado privado indicado; não imprimir environ nem usar
   apenas application.pid ou um match genérico de nome Python. O último PID
   observado foi 28586, arranque 12/11/2026 19:48:45 UTC: é referência histórica,
   não um alvo de sinal sem reconfirmação imediatamente antes da paragem.
   Confirmar DB `livenet_v2_dev`, SID `7705421224394444834`, contentor
   `livenetv2-dev09b-querytrial-db-1`, volume `livenetv2-dev09b-querytrial_data`,
   application `d001a01a7230` e security `b12b01a7230`. Exigir
   zero jobs queued/running/cancelling e ausência de incerteza de persistência.
   Suspender iniciativas humanas de escrita/Discovery durante a janela. Não
   migrar, conceder privilégios, executar seed nem criar/restaurar recursos.
3. Confirmar certificado válido, SAN/origem, key e configuração Discovery
   preservados. A validade documentada do certificado anterior termina em
   15/11/2026: conferir antes da ativação; renovação não ocorreu nesta fase.
4. Parar controladamente apenas a instância DEV identificada por PID e instante
   de arranque, e confirmar libertação de 8443 e do worker anterior. Não usar um
   PID antigo de ficheiro sem reconfirmar a identidade do processo.
5. Arrancar manualmente, com umask 077 e logs privados, a partir do checkout
   revisto, usando exatamente uma instância:

   ```bash
   STATE=/home/paulo/.local/state/livenet-v2-standard-dev
   LIVENET_DISCOVERY_CONFIG="$STATE/discovery.json" \
     ./scripts/livenet serve --config "$STATE/installation.json"
   ```

6. Confirmar bind exclusivo 127.0.0.1:8443, TLS com confiança explícita, evento
   server_started, quatro threads HTTP/TLS e no máximo o único worker Discovery
   previsto. Conferir configuração efetiva sem iniciar jobs. Validar health,
   login/sessão/Inventory/logout sob a autorização operacional dessa janela.
   O fluxo de autenticação pode escrever sessões: não é uma probe read-only DB.
7. Comparar evidências/dados preservados, ausência de jobs novos e logs seguros.
   Não repetir os ensaios de clientes lentos contra o DEV operacional sem
   autorização específica; foram demonstrados isoladamente.

## Rollback futuro

Se houver regressão, preservar logs e diagnóstico; impedir novas operações e
parar apenas a instância nova confirmada por PID/start. Verificar o diff antes
de reverter apenas os ficheiros desta entrega, recuperando o entrypoint anterior
da baseline/HEAD de referência. Não usar reset/clean globais nem eliminar
trabalho posterior. Remover módulos novos apenas se corresponderem aos bytes
revistos desta entrega. Não restaurar a base, apagar volumes ou fazer downgrade.
Retomar o comando anterior com a mesma configuração e variável Discovery, depois
de confirmar que não há trabalho pendente/incerto. Validar listener e dados.

O rollback recupera também a fragilidade HTTPS anterior: é uma medida de
contingência, não a solução do bloqueio. Um encerramento incompleto ou COMMIT
incerto exige diagnóstico/reconciliação, nunca repetição automática.

## Riscos e limites remanescentes

- A causa histórica exata não é provada por estes testes.
- Quatro clientes podem ocupar toda a capacidade durante o prazo configurado;
  nesse caso ligações adicionais são rejeitadas, incluindo health. A garantia
  de health abaixo de dois segundos pressupõe capacidade disponível.
- Deadlines de rede não cancelam código WSGI/DB arbitrariamente bloqueado;
  quatro operações aplicacionais bloqueadas ainda podem esgotar a pool.
- Há acoplamento ao handler Werkzeug 3.1.9/stdlib Python 3.12. Atualizar estas
  dependências exige repetir os testes de transporte afetados.
- A aplicação continua DEV, com o mesmo UID e sem supervisão após reboot.
- Ausência de `LIVENET_DISCOVERY_CONFIG` continua a desativar o motor. Jobs
  queued ainda podem ser consumidos no arranque pelo worker existente. A guarda
  persistente e a recuperação após reboot não são implementadas nesta fase.
- A baseline contém segredos protegidos por permissões e permanece na progbox;
  não foi transferida para o Synology.

## Revisão final dirigida — 12/11/2026

Não foi repetida a bateria integrada de 341 testes. A revisão acrescentou
reproduções concretas de lacunas; na primeira ronda pré-correção, 12 falharam e
três passaram. Os três aprovados já recusavam dois casos de folding em CL/TE e não
executavam um segundo pedido pipelined. As falhas não são uma demonstração de
smuggling explorável: o servidor é direto, sem proxy e atende um pedido apenas.
Uma segunda reprodução mostrou três falhas relativas a EOF/CRLF nos headers;
dois controlos de Host ausente/vazio já passavam. Estes caminhos foram corrigidos.

| Problema | Gravidade | Correção e evidência |
| --- | --- | --- |
| Deadline de escrita não recalculado dentro de SSLSocket.sendall | Alta | Loop explícito de send parcial, recalculando o orçamento; TLS real com send parcial forçado reproduziu o desvio e passou após correção |
| Handler de sinal podia readquirir um Event lock já tomado | Alta | Handler apenas atribui flag; stop/cancel deslocados para o ciclo regular; SIGINT/SIGTERM reais em filhos com locks do servidor/worker tomados |
| Parser tolerava headers malformados, EOF antes do terminador e chunks com +hex, 0xhex ou LF | Média | Exigir CRLF/linha vazia final e rejeitar defeitos/controlos/Host duplicado e framing chunked não estrito antes de WSGI; pedidos malformados passam a 400 |
| close do iterável WSGI omitido quando o socket era fechado durante execução | Média | Vista por pedido acompanha close idempotente, com finally independente da drenagem Werkzeug; cancelamento e sucesso verificados |
| Thread registada antes de start falhar prejudicava o cleanup | Média | Registar só threads iniciadas; falha da segunda thread conserva o erro original e liberta a primeira/listener |

Os testes acrescentados usam TLS real, sockets efémeros e eventos controlados.
A fragmentação de send é forçada sobre SSLSocket real; o esgotamento de threads
é uma falha injetada. São doubles de condições de erro, não uma simulação da
aceitação TCP/TLS. Confiança TLS e hostname têm testes negativos explícitos.
As regras de autenticação/CSRF/sessão continuam verificadas por HTTPS com store
offline, sem ligação PostgreSQL ou worker Discovery real.

Resultados após correções, com rondas sobrepostas (não somar):

| Ronda dirigida | Resultado |
| --- | --- |
| Transporte e regressões diretamente afetadas pelas cinco correções | 42 pass, 15,16 s |
| SIGINT/SIGTERM reais em filhos, confiança/hostname TLS e close WSGI normal | 7 pass, 40 deselected, 2,59 s |
| Terminador/CRLF de headers e regressões afetadas de limites, deadlines e segurança HTTPS | 24 pass, 28 deselected, 9,07 s |

Por área: aceitação/concorrência, CLI/sinais, framing e recursos foram revistos e
corrigidos conforme a tabela. Os limites de quatro admissões, fila interna no
máximo quatro entradas (parte dessas mesmas admissões) e backlog solicitado de
oito permanecem. A integração serve/config/bind e as políticas de segurança
continuam no percurso padrão. O preflight identifica PID/start/exe/cwd/cmdline,
destino DB/volume e baseline verificada; o rollback é só de código, sem restauro
da base ou pressuposto de acesso externo. O bind privado genérico do CLI não é
uma garantia de loopback: a ativação DEV deve reconfirmar exatamente 127.0.0.1.

Parecer técnico: **APTO COM RESERVAS para ativação controlada** após passar o
preflight e obter autorização humana. Permanecem os limites documentados de
saturação e aplicação/DB bloqueada, validade TLS a reconfirmar, mesmo UID Unix,
supervisão/guarda Discovery fora desta fase e cópia externa pendente. Não existe
isolamento de credenciais entre processos do mesmo UID; a revisão não o criou
nem o presume. Nenhuma ativação, alteração DB ou transferência foi executada.
