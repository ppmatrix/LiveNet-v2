# DEV-STABILITY-01 — Fase C: Discovery após reinício ou falha

Implementação C-A/C-B/C-C preparada em 17/11/2026, segundo C-01–C-08.
**Não ativada no DEV.** Ativação, reinício e recuperação operacional exigem uma
intervenção posteriormente autorizada. Este documento não autoriza scans.
O diff HTTPS da Fase B e o frontend atualmente servido são preservados.

## Ciclo de vida e invariantes

O coordenador em memória tem estados `STARTING`, `READY`, `BLOCKED`, separados
dos estados persistidos dos jobs, que não mudam de conjunto. Uma instância
obtém o advisory lock PostgreSQL de sessão existente, verifica o journal
privado e a fila sob o lock de admissão existente, antes de chegar a `READY`.
Não há failover, retry de execução ou reconstrução de autorização pela fila.

| Situação ao arrancar | Resultado sem operações de deteção |
| --- | --- |
| Sem jobs ativos nem evidência pendente | `READY` depois das verificações |
| Apenas `queued`, processed=0, zero observações, sem finished_at nem tentativa pendente | Transição auditada para `interrupted`, confirmada independentemente; depois `READY` |
| `running`, `cancelling`, queued inconsistente, journal pendente/corrompido/inacessível ou proprietário anterior vivo/incerto | `BLOCKED`, sem execução |
| Job terminal, sem journal pendente | Mantido integralmente; nunca executado |
| Mudança de política | Não concede autorização a nenhum job anterior |

Cada POST autenticado/autorizado em `READY` cria um UUID novo. O COMMIT é seguido
de leitura independente de confirmação da linha e da liderança. Só depois é
publicada uma permissão volátil para esse UUID. Admissão, publicação e seleção
usam o mesmo lock do coordenador. O worker consome a permissão uma única vez;
uma falha não a repõe. Jobs inseridos sem permissão bloqueiam a execução.

Antes do claim persistido e de qualquer probe, escreve-se a tentativa durável.
O claim `running` e o seu evento de auditoria são confirmados por outra transação
antes de iniciar os probes. Antes de cada alvo e entre portas verificam-se o
cancelamento, o estado e a integridade/identidade do registo ativo. A liderança
é verificada por conexão própria e pelas transações de admissão/confirmação.

Falhas de persistência, perda de liderança ou inconsistências bloqueiam novas
admissões e sinalizam cancelamento **antes** de aguardar futures. Sockets já
iniciados terminam cooperativamente, limitados pelos timeouts existentes; não
se promete corte instantâneo nem atomicidade entre o lock PostgreSQL e um
connect TCP. Observações com COMMIT confirmado são preservadas; não se repetem
probes para preencher lacunas. A tentativa só é arquivada após confirmação
independente do estado terminal, finished_at e coerência do progresso/evidência.

## Journal e âmbito de confiança

Local: `<state_dir>/discovery`, onde `state_dir` vem da configuração privada
existente (na instalação padrão, o subdiretório `operations`). Não é a pasta
do repositório nem um novo parâmetro público. Binding SHA-256 da identidade
configurada da instalação impede reutilização acidental entre instalações.

- Diretório 0700; ficheiros regulares do UID atual, 0600; rejeição de symlinks.
- `lock`: flock exclusivo, complementar à eleição PostgreSQL; um só host.
- `owner.json`: PID, start_ticks, boot_id e UUID da instância, sem credenciais.
  A presença do PID só conta quando boot e início coincidem; zombies não vivem.
  O proprietário mantém-se registado após libertar o lock.
- `attempt.json`: UUID do job, hash da política, proprietário e UUID da operação.
- `recovery.json`: plano limitado aos UUIDs, estados, contagens e UUID de auditoria.
- Envelope versionado com checksum SHA-256 e validação estrita dos campos;
  tamanho máximo 64 KiB. Escrita temporária exclusiva, fsync do ficheiro,
  replace atómico e fsync do diretório; novas entradas de diretório também
  são sincronizadas no respetivo pai. Falhas impedem execução.
- Arquivos `attempt-archived-*.json` e `recovery-archived-*.json` conservam evidência.
  Não existe limpeza automática; incluir journal/arquivos no backup protegido.

O checksum deteta corrupção acidental, não adulteração pelo mesmo UID. O desenho
pressupõe armazenamento local com semântica POSIX/fsync e um único host. Não
substitui backup externo nem demonstra integridade contra administrador hostil.
Não apagar journal, alterar permissões automaticamente ou editar estados por SQL
para ultrapassar um bloqueio. Perda/corrupção de owner ou do plano de recuperação
exige preservar os bytes e investigar; não há reset automático desses ficheiros.

## Recuperação administrativa, sem deteção de rede

Após autorização operacional, confirmar primeiro processo/comando/UID/início,
ausência da instância anterior e identidade PostgreSQL; preservar backup e
journal. O CLI verifica o pin PostgreSQL pelo mecanismo administrativo existente,
obtém a eleição com o papel runtime e o flock; não cria aplicação ou Worker.

```bash
./scripts/livenet discovery-recover --config "$CFG" --confirm-reviewed
```

O comando usa apenas ligações à base configurada; «sem rede» significa sem
scans/probes, não ausência da ligação administrativa ao PostgreSQL. Para jobs
herdados sem owner/attempt, só depois de revisão humana da identidade anterior:

```bash
./scripts/livenet discovery-recover --config "$CFG" --confirm-reviewed \
  --previous-pid "$OLD_PID" --previous-start-ticks "$OLD_START_TICKS" \
  --previous-boot-id "$OLD_BOOT_ID"
```

Os três valores são obrigatórios em conjunto e têm de ser evidência recolhida
da instância anterior; não inventar um PID inexistente. Sem prova suficiente,
manter bloqueado. A verificação local de PID/boot/start_ticks evita reutilização
de PID; a revisão humana é necessária quando não há owner anterior confiável.
O comando recusa qualquer proprietário conhecido ainda vivo, mesmo sem worker.
Por isso, terminar o backend bloqueado antes de executar o CLI, após autorização.

Jobs ativos coerentes tornam-se `interrupted`; terminais não são reescritos.
Observações, decisões e recursos são preservados. Tentativas com conclusão
terminal já persistida são confirmadas e arquivadas, sem repetir o trabalho.
Um attempt corrompido pode ser arquivado explicitamente se owner/ausência e
estado DB forem demonstráveis. Um plano corrompido continua a bloquear.

O plano é durável antes de alterar a base; usa UUID de auditoria fixo para
repetição após resultado de COMMIT incerto. Verifica-se novamente a persistência
antes de arquivar. Jobs ativos fora de um plano pendente provocam recusa.
Resultados: `RECOVERED`, ou `ALREADY_CLEAN` sem nova auditoria/mutação. Repetição
por um novo processo é segura; owner ainda vivo continua a provocar recusa.
Falhas devolvem saída 78 e código estático, sem mensagens SQL/segredos.

Recuperar não arranca o serviço nem liberta uma instância já bloqueada em memória.
Um arranque posterior passa todas as verificações; repetir uma pesquisa exige
novo POST autorizado e UUID novo. Não se recupera nem se retoma o scan antigo.

## Contratos API/UI

`GET /api/v1/discovery/config` mantém `enabled` e `policy`; acrescenta
`operational: {state, reason}`. Configuração não comprova liderança/prontidão.
POST fora de READY é 503 `discovery_not_ready`; falhas inesperadas são 503
`discovery_unavailable` e bloqueiam. Payload de criação, autenticação, RBAC,
CSRF, origem, cookies e scope Inventory mantêm-se. Estados/tabelas/ACL existentes
não mudam; não são precisos migração ou novos grants.

A UI mostra inicialização/bloqueio, desativa a submissão, mantém histórico e
atualiza prontidão por GET após 503, sem repetir POST. Uma resposta de backend
antigo sem o campo operacional é tratada como bloqueada. A leitura da prontidão
é uma fotografia; o POST volta a verificar autoridade. Idempotência HTTP continua
adiada (C-08); após resposta incerta consultar execuções antes de novo pedido.

## Validação e futura ativação

Os testes usam probes simulados e uma guarda que falha perante qualquer tentativa
de socket de deteção. SQLite exercita transações/ficheiros; um cluster PostgreSQL
16 novo, em diretório privado temporário, usa exclusivamente socket Unix e
`listen_addresses=''` para locks, runtime restrito e recuperação por processo.
Só esse cluster temporário é parado, após verificar PID e data_directory.
Não se usam DB/portas/worker/configuração operacional ou dependências novas.

Cobertura: estados anteriores × política igual/diferente, COMMITs críticos antes
e depois, fsync/replace, corrupção/permissões, corrida admissão/publicação,
liderança concorrente/perdida, cancelamento antes de futures, recuperação repetida,
recursos/decisões/observações preservados, auth/RBAC/CSRF e UI bloqueada.

Resultado em 17/11/2026: **728 testes backend aprovados** na suite relevante
(Discovery, instalação/runtime, segurança, Inventory, auditoria, sessões e
contratos), incluindo **4 testes PostgreSQL reais isolados**. **76 testes UI
aprovados**, incluindo 10 Discovery; typecheck aprovado. Bundle produzido apenas
em `/tmp/livenet-phase-c-dist`; dist operacional preservado. As rondas direcionadas
estão incluídas nestes resultados; não somar. A suite HTTPS B, sem alterações,
não foi repetida. Não houve scans, migrações/grants operacionais ou ativação C.

Reprodução backend com dependências já instaladas, a partir da raiz:

```bash
env -u LIVENET_DISCOVERY_CONFIG PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend \
  .venv/bin/python -B -m pytest -q -p no:cacheprovider \
  backend/tests/test_discovery.py backend/tests/test_discovery_lifecycle.py \
  backend/tests/test_discovery_postgres_lifecycle.py \
  backend/tests/test_standard_installation.py backend/tests/test_standard_runtime.py \
  backend/tests/test_inventory_api.py backend/tests/test_inventory_service.py \
  backend/tests/test_inventory_schemas.py backend/tests/test_inventory_models.py \
  backend/tests/test_security_api.py backend/tests/test_security_service.py \
  backend/tests/test_security_policy.py backend/tests/test_audit_service.py \
  backend/tests/test_database_sessions.py backend/tests/test_health.py \
  backend/tests/test_config.py backend/tests/test_trusted_proxy.py \
  backend/tests/test_readiness_contract.py
```

Frontend, em `frontend/`: `npm test -- --reporter=dot`, `npm run typecheck`,
`node_modules/.bin/vite build --outDir /tmp/livenet-phase-c-dist`. Não usar o
build por omissão enquanto esse dist estiver a ser servido operacionalmente.

Para futura intervenção explicitamente autorizada:

1. Rever diff C preservando B; identificar processo real, código e frontend
   servido. Confirmar jobs/evidências, sem Discovery ativa, pendente ou incerta.
   Se houver incerteza, preparar recuperação explícita; não ativar à força.
2. Verificar backup Fase A e criar backup atual protegido, incluindo configuração
   e journal existente. A cópia Synology permanece pendente, sem ser presumida.
3. Preparar artefactos C e anterior B, incluindo dist em caminho isolado; guardar
   hashes. Não executar build sobre o dist em serviço antes da janela aprovada.
4. Encerrar somente o backend inequivocamente identificado. Confirmar PID antigo
   ausente e que terminou o worker; preservar TLS, configuração e DB.
5. Se necessário, executar a recuperação aprovada acima; nunca arrancar o código
   antigo para recuperar fila. Confirmar estados/evidências e auditoria.
6. Iniciar uma só instância com o mecanismo B e `LIVENET_DISCOVERY_CONFIG`
   existente. Verificar TLS, health, login, histórico e READY, sem scans. Verificar
   invariância de recursos/observações/decisões e ausência de novos jobs/probes.

Rollback: parar somente a nova instância, confirmar ausência, preservar journal
e backup. Resolver explicitamente quaisquer jobs ativos/markers pendentes antes
de repor o código B e respetivo dist. **O worker anterior consome queued ao
arrancar: nunca fazer rollback com fila ativa ou recuperação incerta.** Se não
for demonstrável uma fila limpa, manter o serviço parado ou iniciar sem habilitar
Discovery sob autorização específica. Reverter apenas C mantendo B/TLS/configuração;
não restaurar a base nem apagar evidência como parte de rollback de código.
