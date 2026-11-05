# DEV-08B — Formalização da persistência e candidato AUTH-03

Data: 2026-10-25. Ambiente: progbox. Estado: **formalização documental concluída; candidato NÃO APROVADO; integração persistente não iniciada**.

## Resumo e autoridade

O pedido humano DEV-08B, anexo `9e646608-e14d-4575-8d04-84eaa4ca6301/Pasted text.txt`, Missão, aprova expressamente DEV-08-D01/D02/D03 com os limites DEV-08. Foi formalizado o desenho de identidade PostgreSQL, os destinos Alembic por perfil e o processo D03 fase 1. A segunda aprovação dos bytes do candidato permanece pendente.

Entregas: adenda DAT-05A, registo formal, contrato de persistência e candidato documental com inventário de 52 fontes, matriz individual das 25 divergências e inventário suplementar de 27 artefactos. O manifesto ativo, código, testes, gates e configuração operacional permanecem intactos.

Não foram executados SQL, migrações, Docker, builds, serviços, instalação, deploy, alterações de rede ou operações persistentes. Testes offline usaram apenas fixtures sintéticas e diretório temporário exclusivo em /tmp.

## Alterações documentais e rastreabilidade

| Ficheiro | Alteração DEV-08B | Justificação |
| --- | --- | --- |
| `docs/specifications/f0/data-model.md` | Acrescentada adenda no final; texto anterior integral preservado | Formalizar exceção aprovada ao nome literal e materialização inicial DAT-05A |
| `docs/architecture/decision-register.md` | Acrescentada atualização DEV-08B no final; histórico preservado | Registar aprovação humana com fonte, âmbito, limites e estado distinto de implementação |
| `docs/specifications/f0/dev08b-persistence-contracts.md` | Novo contrato documental | Centralizar identidade, roles, grafos, ledgers, D05/G2, sequência e reversão sem duplicar contratos históricos |
| `docs/operations/dev08b-auth03-candidate.NOT-APPROVED.json` | Novo envelope de revisão, fora do caminho ativo | Congelar inventário, hashes, proveniência e revisão individual, sem atribuir aprovação |
| `docs/operations/dev08b-persistence-formalization.md` | Este relatório | Registar resultado, matriz resumida, verificações e proposta de segunda aprovação |

O relatório DEV-08 continua intacto como proposta histórica; o registo DEV-08B documenta a aprovação posterior e a sua fonte. Outros documentos históricos que indicam f066/f067 ou manifesto divergente não são apagados nem apresentados como execução resolvida.

## Decisões formalizadas

**D01:** DEV `livenet_v2_dev`, STAGING `livenet_v2_staging`, PROD-VM/futuro PROD-K8S `livenet_v2_prod`; clusters, redes, volumes, roles, credenciais e confiança TLS independentes dos restantes ambientes e do v1. Nome, endereço interno e system identifier isolados não bastam. TLS verify-full, identidade/proveniência de destino e papéis separados são obrigatórios. Nomes/colisões e parâmetros operacionais reais ainda não foram consultados.

**Adenda DAT-05A:** preserva os seis domínios lógicos, mas materializa inicialmente só inventory, audit e security. Não pré-criar schemas vazios adicionais devido ao catálogo G2. O nome literal livenet e os seis schemas inicialmente físicos são explicitamente superados apenas nesse âmbito. Não é uma reinterpretação silenciosa do texto original.

**D02:** MVP em `f066a01a7230` + security `b12b01a7230`; AUTH-03 em alvo isolado com `f067a01a7230`, security não aplicada por defeito. Grafo aplicacional com 14 revisões lineares e grafo security com uma raiz própria; ledgers independentes. F067 no manifesto de fontes não significa autorização de aplicá-lo ao MVP.

**D03:** revisão individual e candidato preparados; conteúdo candidato não aprovado. Processo, proveniência, validação técnica offline e aprovação humana são estados diferentes.

Contrato detalhado: [DEV-08B — persistência](../specifications/f0/dev08b-persistence-contracts.md). Evidência técnica principal: `backend/app/dedicated.py:77–121,151–194`, `backend/app/postgres_tls.py:23–52`, `backend/app/readiness.py:105–132`, `backend/security_migrations/contract.py:10–63` e `backend/app/readiness_postgres/evaluate.py:63–104`.

## Matriz individual AUTH-03 — síntese das 25 divergências

O envelope contém todos os 11 campos pedidos para cada divergência em `payload.source_inventory[*]`: caminho, estado Git, hash esperado/atual, proveniência, função, impacto de segurança, dependências, risco, recomendação e evidência. Cada uma tem `review.content_approved=false`. A tabela seguinte é a síntese para leitura; os hashes completos e detalhes são mantidos no candidato para evitar cópias divergentes.

Risco é a consequência potencial de atestar/alterar incorretamente esta fonte, não a afirmação de uma vulnerabilidade comprovada. ALTO não significa aprovação recusada nem exploração demonstrada.

| # | Caminho exato | Proveniência / estado | Função técnica | Risco | Recomendação e aprovação |
| --- | --- | --- | --- | --- | --- |
| 1 | `backend/app/dedicated.py` | Local; sem commit demonstrável | Factory dedicada com configuração explícita e sessão lazy partilhada. | ALTO | Inclusão proposta; aceitação local explícita pendente |
| 2 | `backend/app/inventory/access.py` | Versionado, limpo; proveniência Git comprovada | Contrato de identidade e autorização de inventário; default deny. | ALTO | Inclusão proposta; aprovação do conteúdo pendente |
| 3 | `backend/app/inventory/routes.py` | Versionado, limpo; proveniência Git comprovada | API resources, paginação, scopes e transações explícitas. | ALTO | Inclusão proposta; aprovação do conteúdo pendente |
| 4 | `backend/app/inventory/schemas.py` | Versionado, limpo; proveniência Git comprovada | Validação de inputs e serialização explícita. | MEDIO | Inclusão proposta; aprovação do conteúdo pendente |
| 5 | `backend/app/inventory/service.py` | Versionado, limpo; proveniência Git comprovada | Consultas com scope e criação de recurso com audit transacional. | ALTO | Inclusão proposta; aprovação do conteúdo pendente |
| 6 | `backend/app/postgres_tls.py` | Local; sem commit demonstrável | Configuração e leitura controlada da CA PostgreSQL. | ALTO | Inclusão proposta; aceitação local explícita pendente |
| 7 | `backend/app/readiness.py` | Local; sem commit demonstrável | Contrato /api/v1/ready e evidência tipada. | ALTO | Inclusão proposta; aceitação local explícita pendente |
| 8 | `backend/app/readiness_postgres/__init__.py` | Local; sem commit demonstrável | Declaração do pacote offline G2. | BAIXO | Inclusão proposta; aceitação local explícita pendente |
| 9 | `backend/app/readiness_postgres/adapter.py` | Local; sem commit demonstrável | Orquestração offline de evidências Q1-Q16, dois sujeitos e cleanup. | ALTO | Inclusão proposta; aceitação local explícita pendente |
| 10 | `backend/app/readiness_postgres/evaluate.py` | Local; sem commit demonstrável | Validação integral de identidades, schemas, ACLs, owners, estrutura e ledgers. | ALTO | Inclusão proposta; aceitação local explícita pendente |
| 11 | `backend/app/readiness_postgres/policy.py` | Local; sem commit demonstrável | Política D05 imutável, normalização, digest e limites. | ALTO | Inclusão proposta; aceitação local explícita pendente |
| 12 | `backend/app/readiness_postgres/queries.py` | Local; sem commit demonstrável | Templates fixos PG16 de SELECT e limites Q1-Q16. | ALTO | Inclusão proposta; aceitação local explícita pendente |
| 13 | `backend/app/security/__init__.py` | Versionado, limpo; proveniência Git comprovada | Declaração do pacote de autenticação aplicacional. | BAIXO | Inclusão proposta; aprovação do conteúdo pendente |
| 14 | `backend/app/security/access.py` | Versionado, limpo; proveniência Git comprovada | Ligação das sessões persistentes ao InventoryAccess e RBAC global. | ALTO | Inclusão proposta; aprovação do conteúdo pendente |
| 15 | `backend/app/security/csrf.py` | Versionado, limpo; proveniência Git comprovada | Double-submit assinado com vínculo à sessão ou pre-login. | ALTO | Inclusão proposta; aprovação do conteúdo pendente |
| 16 | `backend/app/security/errors.py` | Versionado, limpo; proveniência Git comprovada | Erros públicos de autenticação e indisponibilidade. | MEDIO | Inclusão proposta; aprovação do conteúdo pendente |
| 17 | `backend/app/security/models.py` | Versionado, limpo; proveniência Git comprovada | Quatro modelos de users, sessions, role grants e throttles. | ALTO | Inclusão proposta; aprovação do conteúdo pendente |
| 18 | `backend/app/security/policy.py` | Versionado, limpo; proveniência Git comprovada | Política explícita de origem HTTPS, cookies e tempos. | ALTO | Inclusão proposta; aprovação do conteúdo pendente |
| 19 | `backend/app/security/routes.py` | Versionado, limpo; proveniência Git comprovada | CSRF/login/logout/me, cookies __Host e proteção de escritas inventory. | ALTO | Inclusão proposta; aprovação do conteúdo pendente |
| 20 | `backend/app/security/service.py` | Versionado, limpo; proveniência Git comprovada | Autenticação persistente, sessões opacas, scrypt, budgets e auditoria. | ALTO | Inclusão proposta; aprovação do conteúdo pendente |
| 21 | `backend/app/trusted_proxy.py` | Local; sem commit demonstrável | Validação do peer e reconstrução da origem HTTPS. | ALTO | Inclusão proposta; aceitação local explícita pendente |
| 22 | `backend/app/__init__.py` | Versionado, limpo; proveniência Git comprovada | Factory aplicacional integra security e inventory. | ALTO | Substituição de hash proposta; aprovação do conteúdo pendente |
| 23 | `backend/app/config.py` | Versionado, limpo; proveniência Git comprovada | Defaults seguros e perfis Flask. | ALTO | Substituição de hash proposta; aprovação do conteúdo pendente |
| 24 | `backend/app/core/model_registry.py` | Versionado, limpo; proveniência Git comprovada | Registo explícito de modelos inventory/audit/security. | ALTO | Substituição de hash proposta; aprovação do conteúdo pendente |
| 25 | `backend/requirements.txt` | Versionado, limpo; proveniência Git comprovada | Dependências diretas Flask/SQLAlchemy/Alembic/psycopg/itsdangerous. | ALTO | Substituição de hash proposta; aprovação do conteúdo pendente |

### Proveniência comprovada e lacunas

- As 12 inclusões versionadas e as quatro substituições têm bytes atuais iguais à última alteração Git; são 16 divergências com proveniência comprovada.
- Commit M1.2A completo: `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`, `feat(security): implement M1.2A local authentication and RBAC`. Contém os quatro conteúdos divergentes atuais, oito módulos security e inventory/routes.py.
- Os outros três ficheiros inventory vêm de `24ea3601b36423d2cd0f68b6a1e07619e3377b3e` (M1.1). Os hashes esperados dos quatro divergentes foram localizados em commits anteriores e estão individualizados no candidato/DEV-08.
- Os nove novos ficheiros locais são dedicated.py, postgres_tls.py, readiness.py, trusted_proxy.py e os cinco ficheiros do pacote readiness_postgres. Leitura do conteúdo, contexto documental DEV-02/06/G2 e testes atuais suportam a proposta técnica; não provam autoria/aprovação original independente. Nenhum foi incluído como aprovado.
- No conjunto total de 52 há **11 fontes não versionadas**, incluindo executor AUTH-03 e f067 já presentes no manifesto antigo, e **uma fonte versionada com modificação local preexistente**, backend/migrations/env.py, cujo hash coincide com o manifesto ativo. As outras 27 entradas coincidentes não receberam uma nova certificação exaustiva nesta etapa.
- A aprovação original do manifesto de 31 entradas não foi localizada. Correspondência de hashes é evidência de integridade relativamente a essa referência, sem prova autónoma de aprovação histórica.
- Não foi demonstrada alteração de segurança não autorizada. Ausência de aprovação/proveniência suficiente deve continuar visível, sem a converter em acusação ou em aprovação automática.

### Conteúdo tecnicamente validado versus aprovado

Foi realizada revisão estática orientada das 25 divergências, parsing AST de todas as fontes Python do âmbito e testes offline relacionados. Os controlos observados incluem configuração explícita, ausência de engine no arranque, sessões partilhadas, CSRF/origem/cookies, recusa de proxy não confiável, TLS verify-full e readiness sem evidência → 503.

Isto não certifica segurança integral, cobertura por linha, SQL real, ownership/ACL ou operação. A matriz limita expressamente a afirmação de validação técnica. O único âmbito aprovado agora é o desenho D01/D02 e o processo D03 fase 1, não os novos hashes do candidato.

## Cobertura adicional: security, runtime e imagem

O verificador ativo cobre apenas `backend/app/**/*.py`, `backend/migrations/**/*.py`, backend/alembic.ini, backend/requirements.txt e o executor Python (`scripts/postgres/auth03_alembic_executor.py:136–151`). Espera conjunto exato: acrescentar entradas complementares ao manifesto atual seria recusado.

O candidato inventaria **27 artefactos externos ao âmbito**, com hashes, estado e proveniência, em `payload.supplemental_coverage`. Não são fontes propostas para o manifesto atual e não estão aprovados:

- Quatro ficheiros Python security_migrations e backend/alembic-security.ini: cadeia independente, versão b12, quatro tabelas, transação externa e downgrade bloqueado. A migração está versionada em `8a9bd369ebe4563286509bb1b154f255165db2df`; isso não autoriza execução nem elimina necessidade de atestação própria.
- Entrypoint dedicado, WSGI legado, duas configurações Gunicorn, Dockerfile/contexto dedicado e dependências/lock/constraints.
- Compose dedicado/TLS, Caddyfile, Dockerfile/contexto Caddy e proveniência de dependências.
- Dockerfile/contexto e Compose do executor AUTH-03 histórico; executor/coordenador/adaptadores security e contratos F02/G4.

Riscos concretos:

1. **Imagem AUTH-03 histórica:** `scripts/postgres/auth03_executor.Dockerfile:1–10` usa base Python por tag e dependências em intervalos; não recebe o lock hashado da imagem dedicada nem copia security_migrations. Atestar requirements.txt não atesta a resolução transitiva ou a imagem. Build não executado.
2. **Contexto de build:** `scripts/postgres/auth03_executor.Dockerfile.dockerignore:1–16` e COPY backend/app requerem validação nativa da allowlist antes de construção; regras de diretório não bastam como prova de exclusão. Não foi demonstrada cópia/exposição de segredo nesta etapa.
3. **Transporte/perfis históricos:** o executor AUTH-03 ainda fixa a identidade antiga e não ganha TLS verify-full pelo contrato documental. O candidato não implementa novos destinos, transporte nem mecanismo de aprovação operacional.
4. **G2:** manifesto físico de catálogos/ACL, autorização autenticada, executor real e recuperação continuam pendentes. O pacote offline aceita exclusivamente executor sintético e não deve ser ligado à aplicação operacional.
5. **Escopos distintos:** uma futura atestação de security/runtime/imagem exige formato, autoridade e processo próprios revistos. Este envelope DEV-08B é apenas um formato documental local; não pretende resolver F03/F04, G4-WF1 ou as lacunas de especificação ainda abertas.

## Candidato concreto — NÃO APROVADO

Ficheiro: [dev08b-auth03-candidate.NOT-APPROVED.json](dev08b-auth03-candidate.NOT-APPROVED.json).

| Elemento | Valor |
| --- | --- |
| Identificador | DEV-08B-AUTH03-CANDIDATE-01 |
| Estado | NOT_APPROVED; active=false; executable=false |
| Conjunto proposto | 52 fontes exatas |
| Delta | 21 inclusões + quatro substituições; 27 entradas sem alteração; zero exclusões |
| Manifesto ativo, SHA256 | `7a9993faba2af675f46bd53daea96f9e4980624c3ef07f4d5af6cdfdfbe7c326` |
| Envelope completo, SHA256 | `09263b8501b277f6f41df1320d08e85ee6c9a07e4770115ccc95869df25974a6` |
| Payload canónico, SHA256 | `cde103b540b6f3f99956f92e600c33ec1e96a9bf5865ff589e81ab17e0a0a6f7` |
| Projeção futura de manifesto, SHA256 | `4819c697b7d12f7ab5cbb1fdfa9cf4c3fd0e98e93b53a60337296cc84036fc29` |

**Completude:** o candidato é completo no inventário e nos hashes do conjunto esperado atual. É incompleto como prova de aprovação/proveniência original dos nove locais e como atestação integral de security/runtime/imagem. Todas as fontes continuam propostas, não aprovadas por este ficheiro. As lacunas não foram removidas do inventário para obter um conjunto artificialmente verde.

Formato reproduzível: JSON UTF-8. O payload usa `json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)`, sem newline. A projeção usa `json.dumps(payload['proposed_manifest'], sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + '\\n'` (um LF real). SHA256 é calculado sobre esses bytes. O digest do envelope completo está fora do ficheiro para evitar autorreferência.

A projeção está embebida apenas como dados em `payload.proposed_manifest`; não foi escrita num caminho ativo. O envelope tem estrutura incompatível com o mapa plano exigido por verify_bundle e fica fora dos diretórios percorridos pelo gate. Nenhum gate foi alterado para o descobrir ou aceitar. Digest é identificação de bytes, não assinatura ou aprovação.

### Procedimento de segunda aprovação

1. Rever as 25 fichas e as lacunas do inventário completo; aceitar/rejeitar explicitamente os nove locais, sem inferir aceitação de HEAD ou do manifesto antigo.
2. Vincular a decisão ao identificador, SHA256 do envelope, payload, projeção e manifesto ativo de origem acima. Qualquer mudança de fonte, âmbito ou candidato exige novo digest e revisão.
3. Declarar expressamente se a aceitação dos bytes cobre a evidência disponível apesar da ausência de autoria/aprovação histórica independente dos locais. Se essa evidência for considerada insuficiente, pedir investigação adicional e manter execução recusada.
4. Não confundir aprovação do candidato com autorização para o aplicar, executar migrações, alterar gates ou produzir readiness 200. Uma tarefa posterior deve autorizar a aplicação documental concreta.

### Aplicação futura após aprovação — não realizada

Revalidar hashes do candidato, conjunto exato de fontes regulares sem symlinks e hash do manifesto ativo de origem. Preservar referência recuperável ao par anterior fontes/manifesto, sem sobrepor trabalho local. Aplicar **apenas** a projeção na serialização definida, numa tarefa autorizada, e conferir o digest previsto; nunca copiar o envelope para o caminho ativo.

Executar o verificador/testes existentes sem alterar expectativas: bundle válido, recusa de adulteração/ausente/extra/symlink/versão antiga, dois casos positivos e negativos dos gates. Uma aprovação de fontes não autoriza build, deploy ou DDL. Imagem AUTH-03 e cadeia security continuam sujeitas a atestação e implementação próprias.

**Reversão:** voltar apenas a um par completo e aprovado de fontes/manifesto da mesma versão. Não repor o manifesto antigo contra código novo, não reverter alterações locais em bloco, não modificar ledgers. Em resultado incerto, manter gates fechados e obter revisão; não repetir mutações automaticamente.

## Verificações e testes executados

1. Inspeção de branch/HEAD/índice/status e SHA256 inicial de 289 ficheiros não ignorados.
2. `python3 -B scripts/dedicated/dev07_reconcile.py`: leitura de manifesto/fontes/grafos/proveniência; 31/52, 21 ausentes, quatro divergentes, zero extras. Sem PostgreSQL/Docker.
3. Inventário SHA256/Git de 52 fontes e 27 complementares; prova dos hashes M1.2A; parsing AST de 62 ficheiros Python do âmbito e cobertura complementar, sem import/execução dessas fontes nessa verificação de sintaxe.
4. Testes offline: **1251 PASS, 2 FAIL, 0 SKIP**, 88,71 s. Python -B, bytecode e autoload de plugins desativados, cacheprovider desativado, assert=plain, fixtures num diretório exclusivo criado por tempfile.mkdtemp em /tmp. Sockets connect/create_connection, psycopg.connect e subprocess.run/Popen reais foram bloqueados por AssertionError.
5. Verificação do candidato: JSON e digests reproduzíveis, 52 caminhos/hashes exatos, 25 fichas completas, 27 itens complementares fora do âmbito, marcador NOT_APPROVED, ausência de referências de consumo do candidato em código/gates; manifesto ativo continua a falhar fechado.
6. Preservação dos 287 ficheiros iniciais fora das duas adendas, do prefixo integral das duas fontes documentais, HEAD, branch e índice; somente três caminhos novos. Diff/whitespace e links documentais locais verificados.

Suites executadas, sem alteração dos testes:

```text
backend/tests/test_dedicated_backend.py
backend/tests/test_dedicated_entrypoint.py
backend/tests/test_postgres_tls.py
backend/tests/test_readiness_contract.py
backend/tests/test_readiness_postgres.py
backend/tests/test_trusted_proxy.py
backend/tests/test_security_api.py
backend/tests/test_security_service.py
backend/tests/test_security_policy.py
backend/tests/test_inventory_api.py
backend/tests/test_inventory_service.py
backend/tests/test_inventory_schemas.py
scripts/postgres/tests/test_auth03_alembic_executor.py
```

As duas falhas preservadas:

- `test_verified_manifest_and_tampering`: verify_bundle recusa conjunto divergente antes da verificação de adulteração.
- `test_future_lock_conflict_and_wrong_source`: a mesma recusa antecede o erro de lock esperado. Não se alcança o lock; não é evidência de um problema novo no lock.

Ambas são as falhas históricas referidas DEV-08. Não foram corrigidas, ignoradas, convertidas em xfail ou ocultadas por substituição do manifesto. **A suite completa selecionada não ficou verde.** Os 1251 casos aprovados sustentam apenas as propriedades offline exercitadas.

Não executados: SQL/migrações/stamp, testes PostgreSQL reais, grants/ownership reais, builds de imagens, TLS/browser nativos, checker real, recuperação e integração persistente. Dependem de infraestrutura descartável, mecanismos/gates e autorização próprios; esta tarefa é documental/offline.

## Estado Git inicial e final

Inicial: branch `main`; HEAD `647179c928888adfeef0f69f582fd13c5fc17350`; SHA256 do índice `50d32095da16e2c0e985226625971e890c33d406cbb9b97743a7198905b9541e`; 202 ficheiros versionados, 87 não versionados, total 289. Quatro modificados preexistentes: backend/migrations/env.py, docs/specifications/f0/data-model.md, docs/specifications/f0/implementation-status.md e frontend/README.md. Registo de decisões e restantes artefactos DEV anteriores já eram não versionados.

Final: mesma branch, HEAD e índice, sem staging/commit/push. Permanecem os quatro modificados; no data-model.md foi acrescentada somente a adenda própria. O registo de decisões preexistente não versionado recebeu somente a atualização própria. Restantes 287 ficheiros iniciais byte-identical. Três novos ficheiros DEV-08B: contrato, candidato e relatório; total final 292 ficheiros não ignorados, 90 não versionados.

Os hashes das 52 fontes propostas, do manifesto ativo e dos gates permaneceram iguais à baseline; nenhuma alteração documental muda o comportamento em execução. Os ficheiros temporários dos testes contêm apenas dados sintéticos; não são credenciais operacionais.

O conjunto protegido nesta entrega é todo o conteúdo inicial fora das duas adendas expressamente autorizadas: código, testes, migrações, manifests, Dockerfiles, Compose, infraestrutura e contratos anteriores. O inventário de fontes/cobertura identifica os caminhos de maior impacto; a comparação dos 287 SHA256 abrange também os restantes ficheiros. São preservados em particular `scripts/postgres/auth03_executor_integrity.json`, `scripts/postgres/auth03_alembic_executor.py`, `scripts/postgres/g4/contracts.py`, `scripts/postgres/tests/test_g4_boundaries.py`, `scripts/postgres/tests/g4_doubles.py`, `scripts/postgres/m12b_security_migration.py`, `backend/app/readiness_postgres/`, ambas as cadeias Alembic e os testes AUTH-03. Ficheiros ignorados de segredos não foram usados como entrada, lidos ou modificados.

## Decisões ainda necessárias e próximo passo

A decisão imediata é a **segunda aprovação explícita deste candidato**, incluindo a disposição individual dos nove locais e a aceitação ou pedido de investigação das lacunas declaradas. A formalização D01/D02 já está aprovada e não precisa de nova aprovação geral.

Mesmo com aprovação do candidato: aplicar o manifesto exige tarefa posterior; faltam perfis/identidades concretos, atestação complementar security/runtime/imagem, mecanismo de aprovação operacional autenticado, executores autorizados, manifesto físico G2, transporte/checagem reais, grants/ownership e recuperação independente comprovados. As 28 lacunas G4/L02 e originais não localizados permanecem abertas.

Próximo incremento proposto: tarefa fechada para aplicação do candidato exato aprovado e testes offline do verificador, seguida de desenho/revisão dos perfis concretos e da atestação complementar. Só depois propor autorização de ensaio PostgreSQL descartável com revisão do mecanismo de execução, destino, roles, TLS, evidência e rollback. Não executar Alembic diretamente para ultrapassar gates.

**Pergunta de segunda aprovação:** aprova os 52 hashes de DEV-08B-AUTH03-CANDIDATE-01, vinculados aos três digests acima, para aplicação posterior expressamente autorizada, incluindo aceitação explícita das nove inclusões locais revistas e das limitações de proveniência declaradas, mantendo fora desta aprovação atestação de imagem/security, gates, DDL, serviços e integração persistente?
