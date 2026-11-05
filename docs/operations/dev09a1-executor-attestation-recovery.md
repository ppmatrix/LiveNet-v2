# DEV-09A.1 — Executor local, atestação complementar e recuperação

2026-10-25 · progbox. **Parcialmente concluída: implementação e validação local concluídas; integração executável protegida e autorização externa bloqueadas. DEV-09B não autorizada.**

Não se executaram migrações application/security, builds, instalações, deploy, SQL sobre bases preexistentes ou alterações de contratos. Os 299 ficheiros iniciais mantêm os mesmos bytes. Esta etapa acrescenta código funcional e testes; não ativa um executor operacional.

## Implementação e limites

| Ficheiro novo | Função |
| --- | --- |
| `scripts/postgres/dev09a1_controlled.py` | CLI e API de planeamento explícito, comparação estrita da identidade/privilégios, decisão auditável por digest e máquina de estados de recuperação; sem SQL, transporte ou emissor de autoridade |
| `backend/tests/test_dev09a1_controlled.py` | 97 casos positivos/negativos: revisões, ambiente, identidade, TLS, role, colisões, ledgers, falhas e repetição |
| `scripts/dedicated/dev09a1_preflight.py` | Harness próprio, derivado por cópia do DEV09A, IDs/label exclusivos `livenet.dev09a1`, imagens locais fixas, rede interna e tmpfs; preserva original |
| `scripts/dedicated/dev09a1_fixture_probe.py` | 75 controlos reais no cluster novo, só schemas sintéticos dev09a1_fixture/dev09a1_recovery; sem importar migrações |
| `docs/operations/dev09a1-complementary.NOT-APPROVED.json` | Proposta documental de hashes; não é manifesto ativo ou autorização |
| `docs/operations/dev09a1-evidence.json` | Baseline, hashes, matriz, testes, recursos e decisões sanitizados |
| `docs/operations/dev09a1-executor-attestation-recovery.md` | Relatório e procedimentos |

Os perfis são MVP (`f066a01a7230` / `b12b01a7230`) e AUTH03-ISOLATED (`f067a01a7230` / security explicitamente `none`). Recusam-se head, stamp, downgrade, omissões, ambientes/perfis desconhecidos e ledgers alterados. A CLI só planeia; `validate_local` compara observações completas e devolve execution=BLOCKED. `execute` recusa incondicionalmente antes de qualquer I/O; não existe flag para ativar. A decisão devolvida permite auditoria local por conteúdo/digest, sem assinatura ou persistência operacional garantida.

Exemplos exclusivamente de leitura:

```bash
.venv/bin/python -B scripts/postgres/dev09a1_controlled.py --environment DEV --profile MVP --application f066a01a7230 --security b12b01a7230 --operation upgrade
.venv/bin/python -B scripts/postgres/dev09a1_controlled.py --environment DEV --profile AUTH03-ISOLATED --application f067a01a7230 --security none --operation upgrade
```

Para repetir o ensaio autorizado de fixtures, `python -B scripts/dedicated/dev09a1_preflight.py --run-disposable`: exige daemon local, openssl e as duas imagens locais por ID da evidência; não faz pull/build. Cria novo SID/CA/credenciais sintéticas e remove apenas os seus recursos. O cluster desta entrega foi removido e não constitui um alvo aprovado para DEV09B.

`validate_local` verifica ambiente/perfil/base, SID, hostname/porta, CA por SHA/verify-full, role, imagem, container, rede, storage, isolamento/portas e colisões contra inventário explícito. Recusa excesso de privilégios globais, memberships ou capabilities divergentes/incompletas. **Comparar registos fornecidos não autentica a sua origem.** O probe comprova TLS e privilégios reais da fixture; o módulo puro não abre ligação nem lê CA/segredos. O inventário operacional completo, origem independente/frescura das observações, matriz real de grants, exclusividade e autorização externa continuam pendentes. Nenhum nome, SID ou registo local autoriza DDL.

A validação AUTH03 isolada aceita apenas destino DEV09A1 descartável distinto; não inventa nome persistente AUTH03 para STAGING/PROD. O planeamento destes ambientes existe, mas a sua integração/atestado de destino não foi implementado nem ensaiado. Capabilities sintéticas não substituem a matriz MVP.

## Proposta de integração protegida — não aplicada

`scripts/postgres/auth03_alembic_executor.py:56` recusa mutações e fixa alvo histórico; `scripts/postgres/m12b_security_migration.py:126` fixa outra identidade e `:216` mantém gate fechado; o coordenador `m12b_security_coordinator.py:82` exige esse gate antes de adaptadores. `scripts/postgres/g4/contracts.py:491` recusa execução mesmo com claims. Alterá-los ou chamar Alembic diretamente contornaria o âmbito autorizado.

Proposta sujeita a aprovação: rever um adaptador dos planos explícitos para os executores existentes, conservando o gate como primeira ação, validação autenticada de destino e fontes, ligação verify-full/transação externa única, locks e validação física antes/depois. Aplicação e security continuam operações separadas com os ledgers originais; f066 é pré-condição operacional de security. A autoridade externa deve vincular operação, origem/destino, artefactos, identidade e janela; não foi definido novo formato/token/issuer AUTH-BOOT-02. A aprovação de hashes, isoladamente, nunca abre gates.

Os testes novos demonstram recusa em ambos os perfis mesmo após validação local; a regressão confirma os gates históricos sem modificar fontes/testes antigos. Falta o teste de integração com autoridade real: só pode ser escrito/executado depois de contrato/implementação próprios aprovados.

## Testes e evidência

**1633 testes offline PASS, 0 FAIL, 0 SKIP, 89,61 s**, incluindo 97 novos e 23 casos adicionais de empacotamento/reconciliação, além da regressão DEV09A de 1513. Rede/psycopg e criação de subprocessos foram bloqueados durante a regressão; plugins automáticos e caches desativados. Suites, argumentos, ambiente e resumo constam da evidência JSON.

**75 verificações nativas PASS** na execução final; uma execução anterior também passou 75. As 58 mecânicas de TLS/ACL/transações anteriores foram repetidas e ampliadas com 17 verificações de validação/recuperação. Nenhum teste usa schema ou ledger aplicacional real.

Execução final: `livenet-dev09a1-74bc010307`; PostgreSQL 160015; SID `7700694811007148059`. Apenas DB/probe na rede interna, zero portas host, dados tmpfs, zero volumes nomeados/anónimos. Um auxiliar sem rede teve CAP_CHOWN apenas sobre duas entradas sintéticas novas. Labels/IDs/armazenamento/portas verificados antes de libertar barreira de SQL. Todos os recursos e PKI sintéticos removidos; 23 containers, 14 redes e 174 volumes preexistentes preservados por IDs.

Não executados: migrações e executores operacionais, bases/credenciais reais, builds, restauro independente de backup, readiness operacional ou integração com autoridade externa. A perda de ligação antes do commit foi real; perda de acknowledgement exatamente no fio durante COMMIT não foi injetada. Foi modelada após commit sintético real e confirmada por consulta independente, sem a apresentar como prova de falha de rede no COMMIT.

## Recuperação testada

| Cenário | Resultado e ação |
| --- | --- |
| Before validation / after validation before first operation | STOPPED terminal; fresh approved operation required. No application operation supplied |
| Failure inside transaction, rollback acknowledged | ROLLED_BACK terminal; security rollback after app commit becomes PARTIAL. DDL and inserted row disappear after exception; independently inspected on another physical connection |
| Failure without rollback acknowledgement / lost journal | UNKNOWN; no inference of rollback, no automatic replay. Actual backend termination before commit rolls back fixture DDL; inspection required |
| Between chains / completed application before security | PARTIAL; first commit cannot be undone by rolling back second transaction. fixture_app_ledger persists and fixture_security_ledger absent |
| Commit acknowledgement lost | UNKNOWN, never ROLLED_BACK; retry forbidden. Acknowledgement loss injected into model after actual successful synthetic commit; independent SQL sees committed row. Wire-level failure exactly at COMMIT not injected. |
| Revision drift / retries / partial state | DRIFT/PARTIAL/UNKNOWN terminal; all retry transitions refused. Model evaluates drift; no real application ledger read/written |
| Nontransactional limits | No downgrade/retry provided. nextval allocation survives rollback; CREATE INDEX CONCURRENTLY rejected inside transaction |

Procedimento futuro: parar o runner e impedir novos claims/retries; conservar evidência da última fase, identidade, hashes, locks e erro sanitizado. Se a transação ainda estiver viva e não houver tentativa de commit, pedir rollback e exigir confirmação independente. Sem confirmação ou com commit tentado, classificar UNKNOWN e não assumir rollback.

Usar uma ligação independente read-only no mesmo alvo atestado para comparar **ambos** os ledgers, catálogo/ACL/owners e dados pertinentes com a origem/destino esperados. Depois de application confirmada e security ausente, conservar PARTIAL: rollback da segunda transação não desfaz a primeira. Estado ambíguo, catálogo incompatível ou objetos inesperados exigem inspeção/decisão humana, nunca stamp, alteração manual de ledger, retry cego ou downgrade security.

Um resultado conhecido após inspeção não desbloqueia automaticamente a operação antiga. Exige registo durável reconciliado, exclusividade revalidada, novas evidências e autorização de nova operação. A máquina desta entrega é sintética/in-memory e não substitui esse registo durável nem a recuperação independente.

Limites reais: DDL comum PostgreSQL na transação foi revertido; nextval consumido não foi reposto; CREATE INDEX CONCURRENTLY não cabe na mesma transação. Extensões, operações externas, DDL não transacional e efeitos pós-commit exigem análise específica. Security recusa downgrade. Não se promete reversibilidade das migrações reais.

Se restauro for necessário: selecionar backup/manifesto compatível e testado, preservar alvo falhado em quarentena, restaurar num alvo separado autorizado, verificar identidade/TLS, ambas as cadeias, catálogo, ACL e integridade; só promover com aprovação. Não houve restauro nesta tarefa: recuperação a partir de backup e falha entre nós permanecem bloqueios operacionais, apesar dos ensaios transacionais.

## Revisão individual dos 27 artefactos

Cada SHA abaixo coincide com a DEV09A e foi lido novamente. **ACEITAR significa recomendação técnica limitada, não aprovação humana ou operacional.** Proveniência completa/último commit, função, testes, impacto e limitações por ficheiro constam da matriz JSON. Para locais não versionados, continuidade documental e hashes não demonstram autoria/reprodução por checkout de HEAD. Não se identificaram segredos literais indevidos nesta revisão; ficheiros de segredos reais não foram lidos.

| Caminho / finalidade | Git / proveniência | SHA256 | Categoria / recomendação |
| --- | --- | --- | --- |
| `backend/Dockerfile.dedicated` — Empacotamento do backend/cliente Python usado como imagem local; não é runner de migrações. | untracked; Local; origem por commit não comprovada | `bb22c0159380d589ac57610141a0931fa05eb2ed80b5618ad8e7f617c4e8ade7` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `backend/Dockerfile.dedicated.dockerignore` — Allowlist do contexto de imagem dedicada; exclusão de material indevido. | untracked; Local; origem por commit não comprovada | `194f3cfbaf961bd12e5e13cfd18d88f6e7aa7b330a5b0bb78d4df05a3da8b608` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `backend/alembic-security.ini` — Seleciona exclusivamente security_migrations e ledger independente. | tracked; Git 8a9bd369ebe4 | `f43ed86b68499b4fb25d75421b30b75251433162b684a7e6a525274718fc0394` | NECESSARIO_DEV09B / **ACEITAR** |
| `backend/dedicated_wsgi.py` — Seleção explícita TLS/factory; não executa migrações. | untracked; Local; origem por commit não comprovada | `3d96eb601de4cabce7d666d5a4084107f66663b1cea6e4e160825696ff14b22b` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `backend/gunicorn_container.conf.py` — Bind no namespace e confiança de proxy desativada no servidor. | untracked; Local; origem por commit não comprovada | `3ba395a446ae1b3d2a24cbb6b07c5aa8f739062cb04c5e8e35e692fdbfe9c7df` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `backend/gunicorn_dedicated.conf.py` — Percurso loopback legado preservado; não é configuração inter-container. | untracked; Local; origem por commit não comprovada | `d19934dce2430f08f1f4d9db719c57dfc910146346aebbf37097743bc43d7c52` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `backend/requirements-container.constraints.txt` — Pins candidatos da cadeia de dependências dedicada. | untracked; Local; origem por commit não comprovada | `d4fe3b495e0e2bf3db6e586768138f2e5dbe3c147ed4bc1dab5d4d959426fe9b` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `backend/requirements-container.lock` — Distribuições e hashes do runtime dedicado; não fixa imagem AUTH-03 histórica. | untracked; Local; origem por commit não comprovada | `2bbe864deb5c9f8a15487fb96ca46aa811ae9f4781c24e76d269b046f68c95c9` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `backend/requirements-dedicated.txt` — Gunicorn e referência a requirements; sem atestação transitiva completa. | untracked; Local; origem por commit não comprovada | `3be08dd620770b80cf933e38a0f966ae5e1deb434fb5443387ba608de2468047` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `backend/security_migrations/__init__.py` — Namespace da cadeia security. | tracked; Git 8a9bd369ebe4 | `b450bd910d335f6ec45152bf01af5e8def18616670a430585aad3b7d5e81f677` | NECESSARIO_DEV09B / **ACEITAR** |
| `backend/security_migrations/contract.py` — Metadata restrita, ligação/transação externas e ledger security. | tracked; Git 8a9bd369ebe4 | `0a29cbc074907a4b9023709a7a8770ea5a48e1d000bcd0197255d4dcf49fb41b` | NECESSARIO_DEV09B / **ACEITAR** |
| `backend/security_migrations/env.py` — Recusa SQL offline e ausência de ligação externa; sem engine/fallback. | tracked; Git 8a9bd369ebe4 | `0bafe798a46070a53ae27ba627e099004d0a3caec143538fe3e114f16a9e90c5` | NECESSARIO_DEV09B / **ACEITAR** |
| `backend/security_migrations/versions/b12b01a7230_create_security.py` — Quatro tabelas security; downgrade bloqueado. | tracked; Git 8a9bd369ebe4 | `3f29c6e630955f2548a7a0a481aa182deda1014cd4fdfbaa2fe39e55db356481` | NECESSARIO_DEV09B / **ACEITAR** |
| `backend/wsgi.py` — Entrada anterior preservada, fora do percurso de migração. | tracked; Git 4d85240af69c | `d0e730c9f0089d5c52970d5cd0beec0557567936e631f7236b13f4245b7eea2a` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `compose.auth03-executor.yaml` — Confinamento e montagem do executor histórico; identidade antiga. | untracked; Local; origem por commit não comprovada | `be9b42028bf11a6ea423b168a30016877d8667dad2b780d7e932190bd7d1e599` | SEGURANCA_FORA_EXECUCAO_ATUAL / **CORRIGIR** |
| `compose.dedicated-tls.yaml` — Overlay verify-full/CA; guards exit78 preservados. | untracked; Local; origem por commit não comprovada | `dfd243af8547243fbe3eada07ebd27f395db3b4a57a4b932d3248fabfd44e7ff` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `compose.dedicated.yaml` — Serviços/rede/mounts separados; não autoriza operação. | untracked; Local; origem por commit não comprovada | `ac5f45ee41d491a7860b597e368362d667e28541bc32c33319781941312ee6e2` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `infra/dedicated/Caddyfile` — Origem HTTPS e headers substituídos para peer de confiança. | untracked; Local; origem por commit não comprovada | `27a05a9a945af13e15965cece8fbab1a17cc4f42f5f21be1717e51880b302ea0` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `infra/dedicated/Dockerfile.caddy` — Construção da imagem proxy. | untracked; Local; origem por commit não comprovada | `d5de76fe5d434bc94a98b3a5c51b74d66778e2a1b2a36ce45c68bda841d24c6e` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `infra/dedicated/Dockerfile.caddy.dockerignore` — Contexto allowlist da imagem proxy. | untracked; Local; origem por commit não comprovada | `27f8eb8e845cec69706c9322b65654b2b1d0c8a226bfa711f99b8b7df24c217d` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `infra/dedicated/dependency-provenance.json` — Registo de resolução/build anterior; evidência não é autoridade. | untracked; Local; origem por commit não comprovada | `48fcd0f1094cd2683a7bb4d9305a122ca3e6de0be7474f58dcfa50a3c386b62b` | FORA_AMBITO_DEV09B / **FORA DO PERCURSO** |
| `scripts/postgres/auth03_executor.Dockerfile` — Imagem antiga por tag/dependências amplas; não copia security_migrations. | untracked; Local; origem por commit não comprovada | `a19453a456d35ced7ce8c92ff3f70302c7adff5c22bb018b340e3fda5d0bfbb2` | SEGURANCA_FORA_EXECUCAO_ATUAL / **CORRIGIR** |
| `scripts/postgres/auth03_executor.Dockerfile.dockerignore` — Contexto do executor; requer revisão nativa da allowlist. | untracked; Local; origem por commit não comprovada | `4ba70dae2caee52c74888e1bdee347fdcf0fdd6ab3e92d95cd49e1e5aa2480d2` | SEGURANCA_FORA_EXECUCAO_ATUAL / **CORRIGIR** |
| `scripts/postgres/g4/contracts.py` — F02/G4 puros, fronteira sempre recusa execução real. | untracked; Local; origem por commit não comprovada | `04531a6b9f2a33d2c6334dc025ef18b750014305716a9283e81db44dad257ffc` | NECESSARIO_DEV09B / **ACEITAR** |
| `scripts/postgres/m12b_security_adapters.py` — Adaptadores de operações administrativas/exclusividade ainda sujeitos à autorização. | tracked; Git 4fbb4f0b2f71 | `66e2fa3ea5fccdcb6b4f3555babd2cd78dd3d8f6ddb2253d9687ef9ac584cba6` | NECESSARIO_DEV09B / **ACEITAR** |
| `scripts/postgres/m12b_security_coordinator.py` — Coordenação com gate prévio e portas explícitas. | tracked; Git 4fbb4f0b2f71 | `33415d4b4c51dbb03a6f67332cc77c63aebc87b7a8f90ba20da1abd79d7a012c` | NECESSARIO_DEV09B / **BLOQUEAR** |
| `scripts/postgres/m12b_security_migration.py` — Plano/transação security, destino fixo e execution_enabled=False. | tracked; Git b2605975a4fb | `c2608a2c8d0391dc3e5960fe797d4c8f77be5165475cb0058de4f66dd51ed9fe` | NECESSARIO_DEV09B / **BLOQUEAR** |

Classificação: 15 FORA DO PERCURSO, 7 ACEITAR, 3 CORRIGIR, 2 BLOQUEAR. Nove artefactos históricos são dependências do desenho de migração/contratos; três são empacotamento histórico relevante para segurança mas não executado; quinze ficam fora do percurso DEV09B.

Bloqueantes: `m12b_security_migration.py` e `m12b_security_coordinator.py` mantêm alvos/gates históricos incompatíveis com execução no novo DEV. Isto é proteção deliberada, não autorização para corrigir constantes. `g4/contracts.py` é tecnicamente aceitável precisamente porque recusa; a ausência de autoridade G4 continua bloqueante. Os adapters são somente referência/simulação, sem armazenamento durável ou transporte real.

Correções propostas, não implementadas: Compose/imagem/ignore AUTH03 necessitam de desenho para os novos perfis, fonte e configuração security, base por digest, dependências fechadas e allowlist de contexto validada. A imagem histórica não incorpora security; a imagem dedicada é runtime, não executor. Build e modificações destes ficheiros ficaram fora desta entrega, para evitar aparentar um percurso migratório autorizado ou introduzir uma cadeia não revista.

Proposta: [dev09a1-complementary.NOT-APPROVED.json](dev09a1-complementary.NOT-APPROVED.json), SHA256 `a77b09236fe2fbd6c3a54a15552f2f90e099bc72aba60c2982c160a453e71b1b`. Regista hashes exatos de nove dependências históricas e do novo planeador e do initializer `scripts/postgres/g4/__init__.py` (11 fontes), identifica as duas fontes bloqueantes e deixa imagem/dependências/autoridade por resolver. Não cobre automaticamente os 27, não substitui AUTH03 nem é input de gates. Uma futura alteração dos executores obriga a nova revisão/candidato dos bytes resultantes. Testes/harness novos também requerem revisão própria antes de reutilização em confiança.

## Contratos, Git e reversão

AUTH03 antes/depois: `4819c697b7d12f7ab5cbb1fdfa9cf4c3fd0e98e93b53a60337296cc84036fc29`; verificador oficial PASS, 52/52. F02/G4, AUTH03, security e G2 preservados. Readiness continua negativa sem evidência válida. Preservados f066 MVP/f067 isolado, HTTPS/proxy/CSRF/sessões, modelos e ambas as cadeias/ledgers. As 28 lacunas G4/L02 e textos originais não localizados continuam abertos; não se reconstituiu nem aprovou documentação ausente.

Inicial/final: branch `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`, índice SHA256 `50d32095da16e2c0e985226625971e890c33d406cbb9b97743a7198905b9541e`. Índice sem alterações, sem staging/commit/push/mudança de branch. Os quatro M preexistentes permanecem byte-identical: `backend/migrations/env.py`, `docs/specifications/f0/data-model.md`, `docs/specifications/f0/implementation-status.md`, `frontend/README.md`. Todos os 299 ficheiros iniciais preservados; sete novos não versionados, total 306 ficheiros (202 tracked, 104 untracked). A evidência inclui inventário inicial completo e estado final.

Reversão desta entrega: retirar de uso/rever apenas os sete ficheiros novos listados acima; não há migrações nem base persistente para reverter. Não restaurar manifesto antigo, fazer downgrade ou remover trabalho anterior. Recursos de fixture já removidos; nenhuma limpeza global pendente.

## Decisões pendentes para DEV09B

1. Review pending complementary candidate and new code; do not interpret technical ACEITAR as approval.
2. Approve protected integration specification for explicit new identities, verified TLS, same mandatory gates and no direct Alembic bypass.
3. Resolve missing AUTH-BOOT-02/G4 original specifications or explicitly reviewed replacement; implement authenticated external authority separately.
4. Approve concrete target, grants/ownership/extension window, durable exclusivity/journal, image/dependencies and independent recovery/backup restoration.
5. Only then explicitly authorize bounded DEV09B migrations; no authorization granted now.

Critérios locais demonstrados: seleção/recusa, identidade consistente, integridade, revisão individual e recuperação sintética sem regressões. **Critério operacional ainda parcial:** os executores protegidos não aceitam nem executam o novo destino; a autorização autenticada, imagem/closure, janela real de privilégios e recuperação independente faltam. Não iniciar DEV09B com base nestes testes.
