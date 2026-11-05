# DEV-09A.2 — Integração, atestação complementar e recuperação

2026-10-25, progbox. **PARCIALMENTE CONCLUÍDA.** Auxiliares funcionais, correções concretas propostas e recuperação independente sintética validados. Os cinco ficheiros críticos são protegidos: patches preparados e testados, não aplicados. Integração executável e autoridade externa continuam bloqueadas. DEV-09B não autorizada.

## Baseline e proteção

Branch `main`; HEAD `647179c928888adfeef0f69f582fd13c5fc17350`; índice SHA256 `50d32095da16e2c0e985226625971e890c33d406cbb9b97743a7198905b9541e`. 306 ficheiros iniciais, 202 tracked/104 untracked, quatro M preexistentes. Sem divergência face às fontes da DEV09A.1. Antes/depois AUTH03 `4819c697b7d12f7ab5cbb1fdfa9cf4c3fd0e98e93b53a60337296cc84036fc29`, verificador oficial PASS 52/52.

A inspeção identificou que **os três CORRIGIR também são protegidos**, embora estejam fora das 52 fontes do manifesto: `scripts/postgres/tests/test_m12b_privilege_review.py:15–31` enumera-os entre os 15 AUTH_FILES, e `docs/specifications/f0/m12b-p2c2b-operational-preparation.md:29–32` documenta a preservação dos 31/15. A DEV09A.2 só permite editar se não protegidos e proíbe alterações protegidas. Por isso foram criados patches concretos sem alterar nenhum dos cinco originais. Não se equiparou ausência no manifesto a permissão de edição.

## Implementação funcional

| Novo ficheiro | Resultado |
| --- | --- |
| `scripts/postgres/dev09a2_integration.py` | Liga o planeamento DEV09A.1 às guardas AUTH03/security reais, confirma fontes protegidas e bundle antes de imports, regista recusa auditável; abertura inesperada de guarda é erro de integridade, nunca autorização |
| `scripts/dedicated/dev09a2_packaging.py` | Produz propostas de Dockerfile/Compose e contexto literal fechado, sem build ou aplicação |
| `scripts/postgres/dev09a2-executor.lock` | 14 dependências por versão/hash, CPython3.12/Linux amd64, sem Gunicorn; derivado dos wheels históricos sem aprovar os 15 artefactos runtime |
| `scripts/dedicated/dev09a2_target.py` | Especificação executável de leitura: run explícito, imagem, rede/tmpfs/TLS/roles, colisões e campos de identidade obrigatoriamente pendentes |
| `scripts/dedicated/dev09a2_recovery.py` | Backup custom e restauro independentes, exclusivamente SQL constante em fixtures; dois clusters/initdb/CA/credenciais/redes novos; nenhuma dependência de executor de migrações |
| `backend/tests/test_dev09a2_integration.py` | 51 testes novos de ponte, guardas, propostas, dependências, contexto adversarial, alvo e integridade de backup |

Além das seis fontes, criaram-se nove artefactos de proposta (patch, índice, seis cópias e especificação do alvo) e os três entregáveis pedidos: **18 ficheiros novos**. Nenhum ficheiro inicial modificado.

Ponte de diagnóstico, só leitura (requer PYTHONPATH=backend:scripts/postgres):

```bash
.venv/bin/python -B scripts/postgres/dev09a2_integration.py --environment DEV --profile MVP --application f066a01a7230 --security b12b01a7230 --operation upgrade
```

O resultado é execution=BLOCKED e migration_command=null; security é omitida no perfil AUTH03-ISOLATED f067/none. Não há SQL, runner alternativo, callback de migração, flag de ativação ou autoridade nova. A ponte verifica integridade e recusa; **não fornece ainda transporte de novos destinos**. A nova API prepare_checked compõe a validação existente de identidade/TLS/privilégios com as guardas reais: observações inválidas são recusadas antes delas; observações consistentes continuam BLOCKED e sem autoridade. O validador DEV09A.1 foi mantido intacto; a especificação futura ainda não materializada não é uma identidade validada.

## Cinco artefactos críticos

| Ficheiro protegido | Defeito / causa | Proposta concreta e estado |
| --- | --- | --- |
| `compose.auth03-executor.yaml` | Historical fixed project/network/secret wiring and image tag; not a new-profile descriptor. | Proposed explicit project/image/UID/GID, pull never, no secrets/ports/volumes, network none, unconditional exit78. Intentional quarantine; transport still pending. **CORRIGIR**, aplicação pendente de aprovação |
| `scripts/postgres/auth03_executor.Dockerfile` | Mutable Python tag/unlocked transitive dependencies; security/coordinator/local sources omitted. | Proposed verified Python registry digest, independent 14-package hashed executor lock, exact security/local/gate source copies and exit78. **CORRIGIR**, aplicação pendente de aprovação |
| `scripts/postgres/auth03_executor.Dockerfile.dockerignore` | Recursive allow-globs can admit unreviewed Python files and omit new required chain sources. | Proposed deny-all plus exact 66 literal source/parent rules; adversarial files/traversal/globs rejected by offline strict-subset oracle. Native BuildKit validation not run. **CORRIGIR**, aplicação pendente de aprovação |
| `scripts/postgres/m12b_security_coordinator.py` | Calls historical disabled gate; only concrete memory simulations allowed, no durable production adapters. | Proposed same preparation API; all original methods/guards unchanged. Real coordination through administrative closure and independent authority remain unresolved. **BLOQUEAR**, aplicação pendente de aprovação |
| `scripts/postgres/m12b_security_migration.py` | Fixed historical target and authority disabled; binding new DEV cannot be enabled without protected contract change. | Proposed read-only prepare_dedicated_request API delegates to guarded local bridge. No target constants/gates/SQL paths changed; actual new-target migration adapter still needs approved design. **BLOQUEAR**, aplicação pendente de aprovação |

Patch: [protected-changes.NOT-APPROVED.patch](proposals/dev09a2/protected-changes.NOT-APPROVED.patch). `git apply --check` PASS; não foi aplicado. O índice [proposal-index.json](proposals/dev09a2/proposal-index.json) fixa hashes atuais e propostos. Inclui também uma API preparatória no executor AUTH03, sem tocar nos seus caminhos existentes. Todos os métodos/classes originais dos três executores ficam AST-identical nas propostas; as APIs novas foram compiladas isoladamente e devolvem BLOCKED.

**Limite do patch:** as APIs propostas são pontos de preparação, não uma implementação incompleta apresentada como executável. Alvos históricos, TLS do executor antigo, autoridade, transportes reais, exclusividade durável e fecho administrativo não são corrigidos por estas adições. Alterar esses contratos exige desenho e aprovação próprios. Aplicar qualquer alteração ao executor AUTH03 também exigiria novo par fonte/manifesto revisto; este patch nunca deve ser aplicado isoladamente mantendo o manifesto atual como se ainda atestasse os novos bytes.

A imagem proposta fixa a base Python por RepoDigest confirmado localmente, usa lock dedicado com hashes e copia security/gates/ponte. A allowlist proposta admite exatamente **66 ficheiros atuais**, em vez de globs recursivos. O oráculo offline só interpreta a gramática literal usada; **não houve BuildKit, build, instalação ou inspeção de imagem reconstruída**. A proposta Compose fica sem rede/segredos/portas, com exit78: um descritor de quarentena que ainda necessita de integração de transporte revista.

## Sete ACEITAR e proposta complementar

| Fonte revista e inalterada | Função/dependências e risco residual |
| --- | --- |
| `backend/alembic-security.ini` | Seleciona exclusivamente security_migrations e ledger independente. Real migration/privilege/ownership behavior not executed; b12 downgrade blocked; external transaction/config mandatory. |
| `backend/security_migrations/__init__.py` | Namespace da cadeia security. Real migration/privilege/ownership behavior not executed; b12 downgrade blocked; external transaction/config mandatory. |
| `backend/security_migrations/contract.py` | Metadata restrita, ligação/transação externas e ledger security. Real migration/privilege/ownership behavior not executed; b12 downgrade blocked; external transaction/config mandatory. |
| `backend/security_migrations/env.py` | Recusa SQL offline e ausência de ligação externa; sem engine/fallback. Real migration/privilege/ownership behavior not executed; b12 downgrade blocked; external transaction/config mandatory. |
| `backend/security_migrations/versions/b12b01a7230_create_security.py` | Quatro tabelas security; downgrade bloqueado. Real migration/privilege/ownership behavior not executed; b12 downgrade blocked; external transaction/config mandatory. |
| `scripts/postgres/g4/contracts.py` | F02/G4 puros, fronteira sempre recusa execução real. F02/G4 always refuses; no external trust root/authenticator/transport; acceptance never opens boundary. |
| `scripts/postgres/m12b_security_adapters.py` | Adaptadores de operações administrativas/exclusividade ainda sujeitos à autorização. In-memory models and registry only; no durable operational exclusivity/recovery or production adapters. |

Os sete SHA256 foram confirmados byte a byte; proveniência Git/local, hashes completos, conteúdo relevante, dependências, testes e riscos constam das sete fichas na evidência/proposta. Cadeia security/config/metadata exige transação externa e ledger próprio; modelos importados permanecem cobertos pelas 52 fontes AUTH03. G4 só contém tipos/fronteira de recusa; adapters são modelos em memória. **ACEITAR continua recomendação técnica, não aprovação humana.**

Classificação atual dos 27: 7 ACEITAR; 3 CORRIGIR (patch concreto pronto, protegido/não aplicado); 2 BLOQUEAR (arquitetura/autoridade/transporte); 15 FORA DO PERCURSO. Não se promoveu nenhuma categoria para obter um estado verde.

Proposta final documental [dev09a2-complementary.NOT-APPROVED.json](dev09a2-complementary.NOT-APPROVED.json), SHA256 `bc0982d34e74c3c7838742cee9d3385225ddb749491b6c906cc04b55761f4db5`: 13 fontes complementares do contexto atual, referência separada às 52 fontes e ao manifesto, contexto total 66, hashes dos auxiliares e propostas. Distingue preimages atuais de hashes propostos. Não é assinatura, autorização AUTH-BOOT-02, manifesto ativo ou input de gates.

Ficam explicitamente fora da aprovação pretendida os quinze:

- `backend/Dockerfile.dedicated`
- `backend/Dockerfile.dedicated.dockerignore`
- `backend/dedicated_wsgi.py`
- `backend/gunicorn_container.conf.py`
- `backend/gunicorn_dedicated.conf.py`
- `backend/requirements-container.constraints.txt`
- `backend/requirements-container.lock`
- `backend/requirements-dedicated.txt`
- `backend/wsgi.py`
- `compose.dedicated-tls.yaml`
- `compose.dedicated.yaml`
- `infra/dedicated/Caddyfile`
- `infra/dedicated/Dockerfile.caddy`
- `infra/dedicated/Dockerfile.caddy.dockerignore`
- `infra/dedicated/dependency-provenance.json`

A leitura dos registos de wheels/lock anteriores como proveniência não os inclui na aprovação. Dependências/imagem reconstruída e closure depois de eventual patch carecem de atestação própria. O checkout de HEAD continua insuficiente: há fontes locais não versionadas.

## Destino futuro DEV09B — reservado, não criado

Especificação [dev09b-target.NOT-APPROVED.json](proposals/dev09a2/dev09b-target.NOT-APPROVED.json): run `livenet-dev09b-4c96595539`, DB `livenet_v2_dev_4c96595539`, hostname `livenet-dev09b-4c96595539-db`, rede `livenet-dev09b-4c96595539-data`, PG16 em tmpfs, sem portas e sem credenciais/volumes operacionais. Imagem `postgres@sha256:f4610795587492cd4fb887c2dc3de301b813278bb6f616992061141b5f15ac36` corresponde localmente ao ID `sha256:6a2e324ebe59af6031c4c1cd96c1d5072c2ebc36563d2196365e43b8297c062d` (Linux/amd64). Não se inventou digest.

Não há colisão com nomes de containers/redes locais observados na preparação. Isto não atesta todo o inventário operacional. SID, CA e IDs reais permanecem null; a especificação recusa preencher esses campos como se já houvesse um alvo. CA/SAN/credenciais sintéticos serão gerados por execução só depois de criação autorizada. Verificar independentemente pg_controldata+SQL, endpoint/TLS/CA/role, ID de imagem/container/rede/storage, ausência de objetos/ledgers aplicacionais e isolamento antes de qualquer DDL futuro.

Roles previstas: owners NOLOGIN, migrator NOINHERIT sem poderes globais, runtime/inspector separados e canal administrativo de recuperação. A matriz por fase, janela btree_gist, ownership, fecho e grants D05 continuam por aprovar; nomes de roles não concedem direitos. A limpeza só pode usar IDs novos com labels verificadas, recusar volumes inesperados e comparar inventário inicial/final; nunca prune ou nomes operacionais como atalho.

## Autoridade e proposta de autorização

`docs/architecture/decision-register.md:238–271` conserva referências HUMAN_REFERENCE/SOURCE_NOT_LOCATED para I2-D01–D05, estrutura em três camadas, Ed25519, confiança independente, revogação e uso único; F03/F04/canonicalização integrais não estão disponíveis. `scripts/postgres/g4/contracts.py:491–502` não autentica nem concede autorização. As 28 lacunas G4/L02 continuam abertas, sem reconstituir originais.

1. **Local:** comparar planos/fontes/identidade/privilégios e observar recusas; não emite autorização.
2. **Permitido pelo pedido atual:** fixtures descartáveis sintéticas, backup/restauro e testes offline; sem promover resultados a evidência operacional G2/G4.
3. **Externo obrigatório:** confiança/issuer/autenticidade de aprovação, schema/canonicalização e digests aprovados, scope/expiração/revogação/uso único, vínculo ao destino e operação. Falta texto completo/implementação aprovada; não foi criado formato alternativo.
4. **Proibido nesta tarefa:** aplicar patches protegidos, alterar manifesto/gates, migrar application/security, tocar em bases/segredos operacionais ou disponibilizar serviços.

Procedimento DEV09B proposto: rever/fixar fontes, patch e par AUTH03 correspondente; aprovar e validar imagem/contexto; recuperar os contratos originais ou aprovar decisão arquitetural substituta explícita; implementar/rever autoridade e transporte guardado/exclusividade/fecho; autorizar apenas criação do alvo; recolher e rever identidade concreta independente; verificar backup recuperável e origem de ambas as cadeias; obter nova autorização operacional autenticada e humana para application base→f066 e, separadamente, security base→b12 após verificar f066. Não usar head/stamp; f067 só noutro alvo isolado e sem security automática. **Não existe comando legítimo de migração DEV09B fornecido nesta entrega.**

## Recuperação independente demonstrada

**35 verificações finais PASS**, apenas em `dev09a2_recovery`, SQL constante sintético. Backup pg_dump custom de 4518 bytes, SHA256 `dc71a797faab3dc3ac58fdd0cf33a37476570ffeaaac28a67ad385f16b8ca6f7`; corrupção recusada antes do restauro. Origem SID `7700699333583478811`, restauro SID `7700699349964722203`, CA/redes/credenciais próprias e distintas. A origem foi parada **antes** de pg_restore no segundo cluster. Dados, estados sintéticos, ownership e grants coincidiram com o snapshot anterior. Ambos os ledgers public Alembic e schemas aplicacionais permaneceram ausentes.

Cobertura: sem alteração antes da primeira operação; erro real dentro de transação com rollback confirmado por outra ligação; estado parcial persistido entre cadeias sintéticas; commit concluído com acknowledgement modelado como desconhecido, inspeção independente; backup anterior restaurado noutro cluster sem depender do executor ou da origem disponível. O native drill não importa executores, Alembic ou aplicação; esse isolamento também foi verificado por AST.

Procedimento: manter backup verificável/identidade/manifestos/catálogo/ACL/globals por canal independente antes de execução; parar runner e novas claims após falha; confirmar rollback se não houve commit; com commit tentado/ligação perdida classificar UNKNOWN. Inspecionar ambos os ledgers, catálogo, dados, owners/ACL via canal read-only independente. Application confirmada e security ausente é PARTIAL, não retry. Não fazer stamp, alterar ledger ou downgrade security.

Se precisar de restauro: quarentena do alvo falhado; criar outro alvo descartável autorizado com identidade/CA/credenciais novas; validar backup por hash/catálogo; preparar globals/roles sob procedimento separado; restaurar apenas no alvo vazio próprio, sem --clean sobre o original; verificar identidade, catálogo, revisões, dados/owners/grants e ausência de extras; reconciliar registo durável e obter nova autorização para retomar. A inspeção ou restauro, isoladamente, não autoriza nova migração.

Limites: mesmo host Docker, backup sintético em memória destruído no cleanup, sem prova off-host/durabilidade operacional; roles globais foram preparadas independentemente, não restauradas por dump de globals. A perda de acknowledgement não foi injetada no fio durante COMMIT. Nenhuma migração/ledger real foi executado. DDL não transacional, nextval e commits anteriores não são automaticamente reversíveis (prova anterior DEV09A.1 preservada).

## Testes, falhas resolvidas e limpeza

**2311 casos offline únicos aprovados, zero falhas pendentes, zero ignorados.** Incluem 51 casos novos. A execução alargada terminou com 2292 PASS/16 FAIL (102,56 s): 15 precisavam de subprocessos locais bloqueados pelo launcher e um usava spawn a partir de stdin. Repetiram-se apenas esses 16 com launcher em ficheiro, whitelist dos comandos inertes previamente lidos, stubs para Docker/SQL e bloqueio socket/psycopg: **16 PASS, 0 FAIL, 1,90 s**. Não se alteraram testes antigos, validações ou gates para obter aprovação. Após acrescentar a composição prepare_checked, os 51 casos DEV09A2 e 97 DEV09A1 passaram juntos (148 PASS), incluindo três novos casos; não se somaram repetições como casos únicos. Suites/argumentos/launcher e resultados estão na evidência.

Ensaio nativo: primeira tentativa falhou no helper de permissões porque o bind de diretório privado 0700 não era atravessável por root com apenas CAP_CHOWN; trocado por três binds de ficheiros novos. A autenticação local do initdb ficou SCRAM. Cleanup da tentativa confirmou zero recursos próprios. Um ensaio intermédio passou 33 controlos; o final passou 35 após acrescentar versão/ownership e retirar uma contagem tautológica. Falhas iniciais não foram ocultadas.

Não executados: builds/instalações/BuildKit/scan de imagem reconstruída, migrações reais, testes com dados ou credenciais operacionais, authority/supervisor reais, grants definitivos e recuperação off-host. Os 35 controlos são novos de backup/restauro; os 75 anteriores continuam evidência histórica, sem soma artificial nem repetição desnecessária.

23 containers, 14 redes e 174 volumes preexistentes preservados por IDs. Todos os clusters/helpers/redes próprios removidos; nenhum volume nomeado/anónimo criado. PKI/credenciais/backup sintéticos destruídos, sem portas publicadas, pull ou build. Um helper sem rede teve só CAP_CHOWN e mounts de ficheiros próprios; os DBs executaram UID70, rootfs read-only, cap-drop e tmpfs.

## Git, reprodução e reversão

Todos os **306 ficheiros iniciais byte-identical**, incluindo os quatro M preexistentes. 18 novos não versionados, total324 (202 tracked/122 untracked); mesma branch/HEAD/índice, sem staging, commit, push ou mudança de branch. Inventário acumulado completo desde HEAD, agrupado, está em git_consolidation da evidência. Não incluir secrets/backups/caches/artefactos temporários. Só metadados de secrets conhecidos foram consultados; conteúdo não lido. Arquivo DEV08D preservado.

Sequência de commits proposta, sem a executar: (1) conjunto AUTH03 atual coerente de fontes+manifesto revisto, nunca manifesto isolado; (2) backend dedicado/TLS e testes, separado do legado; (3) auxiliares não protegidos de planeamento/recuperação e testes; (4) infraestrutura/supply-chain em âmbito próprio revisto, sem aprovar implicitamente os quinze excluídos; (5) documentação/decisões/evidências com estados de aprovação preservados. Não usar git add .; rever listas explícitas e manter patches como propostas.

Reprodução das fixtures: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B scripts/dedicated/dev09a2_recovery.py --run-synthetic`; usa só a imagem PG local fixa, openssl e daemon local, sempre novos recursos e cleanup. Especificação sem recursos: `python -B scripts/dedicated/dev09a2_target.py --run livenet-dev09b-4c96595539`. A repetição não conserva SID/CA.

Reversão: retirar de uso apenas os 18 novos ficheiros identificados na evidência; originais e recursos preexistentes intactos, nenhuma BD/migração para reverter. Não aplicar nem reverter automaticamente o patch, restaurar manifesto antigo, usar downgrade ou executar git clean/reset.

## Decisões mínimas e próxima etapa

1. Rever/aprovar especificamente os diffs protegidos e a atestação complementar; qualquer alteração ao executor AUTH03 exige novo candidato fonte/manifesto e aprovação separada.
2. Recuperar os originais AUTH-BOOT-02/F03/F04/I2 ou aprovar explicitamente substituição arquitetural; rever autoridade, transporte real, exclusividade/registo durável e fecho administrativo. Não abrir gate por flag.
3. Aprovar imagem/contexto, alvo concreto depois de criação autorizada, matriz de privilégios e backup/recuperação; só depois uma nova autorização explícita e limitada DEV09B para as duas cadeias.

**Recomendação:** próxima etapa de revisão/autorização dos patches e fecho do contrato externo, seguida de implementação guardada especificamente autorizada. Não iniciar DEV09B com o patch preparatório, aprovação de hashes ou fixtures verdes como substituto da autoridade.
