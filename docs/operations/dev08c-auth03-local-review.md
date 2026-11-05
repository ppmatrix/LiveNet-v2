# DEV-08C — Revisão final das nove inclusões locais AUTH-03

Data: 2026-10-25; progbox. **Conclusão: APROVAÇÃO RECOMENDADA**, exclusivamente do candidato de fontes DEV-08B-AUTH03-CANDIDATE-01, mediante decisão humana explícita. Nenhuma inclusão foi aplicada ou aprovada pelo agente; nenhuma prontidão operacional é declarada.

## Identidade e âmbito

Candidato: [dev08b-auth03-candidate.NOT-APPROVED.json](dev08b-auth03-candidate.NOT-APPROVED.json).
SHA256 do ficheiro completo, **antes = depois da revisão**:

```text
09263b8501b277f6f41df1320d08e85ee6c9a07e4770115ccc95869df25974a6
```

Os nove hashes atuais correspondem ao candidato; o conjunto exato de 52 fontes e ambos os digests internos também foram conferidos, sem alterar hashes armazenados. O manifesto ativo permanece com SHA256 `7a9993faba2af675f46bd53daea96f9e4980624c3ef07f4d5af6cdfdfbe7c326`.

Referências: [DEV-08B](dev08b-persistence-formalization.md), [contrato AUTH-03](../specifications/f0/auth03-alembic-executor.md), [contratos aprovados](../specifications/f0/dev08b-persistence-contracts.md) e verificador `scripts/postgres/auth03_alembic_executor.py:136–151`. A revisão funcional limita-se às nove inclusões; as outras fontes e os 27 complementares receberam apenas comparação de integridade, não nova auditoria.

## Estado/proveniência comum e distinção de evidências

**Cada um dos nove ficheiros está não versionado**; `git log --all -- <caminho>` não localizou commits para qualquer deles. Os contextos conhecidos são DEV-02 (factory/proxy/readiness), G2-PREP1/FIX1/FIX2 (pacote readiness_postgres) e DEV-06 (TLS), documentados nos relatórios anteriores. Isto demonstra rastreabilidade documental local, não autoria ou aprovação histórica independente.

Integridade: bytes atuais vinculados aos hashes abaixo. Comportamento observado: análise estática e testes sintéticos atuais. Aprovação: **continua humana e pendente**; existência, hash e teste verde não a concedem.

## Tabela individual

T1–T6 identificam as suites/resultados da secção de testes. Nenhum risco residual desta tabela é autorização para operar o componente.

| # | Caminho exato | Tipo/finalidade e dependências | Conteúdo funcional, segurança e efeitos | Testes | Risco residual | Recomendação |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `backend/app/dedicated.py` | Factory opt-in; configuração/segredos, sessão lazy única para auth/inventory; SQLAlchemy e módulos app. | Sem DDL/provisionamento; engine só ao pedir sessão. TLS opcional na factory base: perfil seguro deve selecionar create_tls_app. Callback de readiness é código de confiança. | T1/T2 | Configuração, paths privados e destino/ACL reais ainda por validar; memória runtime contém credenciais lidas de ficheiros privados. | **ACEITAR** |
| 2 | `backend/app/postgres_tls.py` | Configuração TLS; ssl/os/stat/pathlib, sem driver ou sockets. | Só verify-full, CA explícita, valida ownership/permissões/symlinks e gssencmode=disable. Só leitura da CA; sem privilégios ou migrações. | T3 | Handshake/hostname/CA em servidor real e TOCTOU do path até libpq fora desta prova; requer mount/parent de confiança. | **ACEITAR** |
| 3 | `backend/app/readiness.py` | Endpoint e dataclasses; Flask/dataclasses/monotonic. | 503 sem checker/evidência válida; revisões f066/b12, freshness e direitos tipados. Não emite autoridade nem executa SQL. | T4/T1 | Confia no checker Python; tipos/booleans não autenticam evidência. Proibido ligar evidência sintética como prova operacional. | **ACEITAR** |
| 4 | `backend/app/readiness_postgres/__init__.py` | Pacote; apenas docstring, sem imports. | Nenhuma instrução funcional, estado operacional, acesso a segredos ou efeito em migrações/gates. | T5 (import) | Somente lacuna comum de proveniência local. | **ACEITAR** |
| 5 | `backend/app/readiness_postgres/adapter.py` | Orquestrador offline; policy/evaluate/queries, locks/relógio. | Recusa executor real antes das factories; snapshots read-only declarados em doubles, limites, invalidation e rollback/close. revalidate repete política e não devolve prova positiva. | T5 | Callbacks são de confiança; deadlines não preemptam I/O hostil. Latch/lock em memória não coordena processos/réplicas; não instalar live. | **ACEITAR** |
| 6 | `backend/app/readiness_postgres/evaluate.py` | Validador puro; policy/queries e tipos readiness. | Confere catálogo/ACL/owners/constraints/FKs/ledgers antes de construir booleans. Recusa extras, privilégios excessivos e evidência ausente; sem alterar ACL ou executar queries. | T5 | A qualidade/autenticidade da evidência e do manifesto físico vem da fronteira externa; resultados sintéticos não provam servidor real. | **ACEITAR** |
| 7 | `backend/app/readiness_postgres/policy.py` | Política imutável D05; queries, JSON/SHA256; import diferido de evaluate. | Matriz restrita, digest vinculado a destino/catálogo, limites máximos. A validação estrutural não é substituída por um digest coerente; sem grants ou ativação. | T5 | Digest não é assinatura/aprovação; catálogo físico independente ainda necessário. Ciclo diferido policy↔evaluate compreendido e testado. | **ACEITAR** |
| 8 | `backend/app/readiness_postgres/queries.py` | Dados/templates PG16 SELECT; dataclasses/MappingProxyType. | Q1–Q16 fixos com binds para roles; sem executor, SQL livre, DDL/DML ou comandos host. Palavras INSERT/UPDATE/DELETE são rótulos de privilégios, não ações. | T5 | Sem prova nativa PostgreSQL nesta etapa; funções de catálogo como pg_control_system exigem permissão específica; não conceder admin por conveniência. | **ACEITAR** |
| 9 | `backend/app/trusted_proxy.py` | Middleware WSGI; ipaddress/Werkzeug. | Valida peer, Host/proto/forwarded; rejeita pedidos inválidos e remove headers após validação. Sem comandos, segredos, alterações de sessão/ACL ou migrações. | T6/T2 | Depende de proxy que substitui headers, origem fixa e isolamento real contra acesso direto/spoofing; não prova a fronteira de rede. | **ACEITAR** |

### SHA256 atual por inclusão

| Caminho | SHA256 atual, igual ao candidato |
| --- | --- |
| `backend/app/dedicated.py` | `1a4472e6f06937da0966dccf36542b2ed79a0d4505a019b1b18c192de00e7a2c` |
| `backend/app/postgres_tls.py` | `ca3566de364821d1f676954f6ce28646683c6a873da7b58a94c8ccc8c8d10b19` |
| `backend/app/readiness.py` | `b91aeb511c7699b98493d6d70545b43e705b022b73734d4713de97e7edf4f69c` |
| `backend/app/readiness_postgres/__init__.py` | `7df4b413bf7470326d725b74aa8b3ebab175e86e825203b78601ff0f966afcc1` |
| `backend/app/readiness_postgres/adapter.py` | `fe40580c13d92ac68a28b25528932261c127210efb62d4ae18f940b5dd0e8aaf` |
| `backend/app/readiness_postgres/evaluate.py` | `0137f9343672a95fc0138b9e6ac5207fdb23b468162dce65b5867fd2758210d5` |
| `backend/app/readiness_postgres/policy.py` | `7dc4100d063e4cb3c09957e8fb117f2b84fddc7b5b28f73f57422061042bff81` |
| `backend/app/readiness_postgres/queries.py` | `9ddad5dc61f2c5f81ca5db8e410064e506b9a93607b3f2cde3add86c3ad1ed2b` |
| `backend/app/trusted_proxy.py` | `1078a580402a3d2cddb15e5e8797f4e63c5444cb4cba9a8ecfde0dd47d505375` |

### Evidência por ficheiro

- `backend/app/dedicated.py:77,124,151,178` — revisão estática e testes offline indicados acima.
- `backend/app/postgres_tls.py:23,35` — revisão estática e testes offline indicados acima.
- `backend/app/readiness.py:84,105` — revisão estática e testes offline indicados acima.
- `backend/app/readiness_postgres/__init__.py:1` — G2; revisão estática do conteúdo, sem transporte real.
- `backend/app/readiness_postgres/adapter.py:23,53,110,122,214` — G2; revisão estática do conteúdo, sem transporte real.
- `backend/app/readiness_postgres/evaluate.py:31,200,239,383,492,517` — G2; revisão estática do conteúdo, sem transporte real.
- `backend/app/readiness_postgres/policy.py:18,225,233,278` — G2; revisão estática do conteúdo, sem transporte real.
- `backend/app/readiness_postgres/queries.py:18,30,87,163,208,212` — G2; revisão estática do conteúdo, sem transporte real.
- `backend/app/trusted_proxy.py:19,27,39` — revisão estática e testes offline indicados acima.

A notação após dois pontos identifica linhas/pontos de leitura no respetivo ficheiro. Evidência complementar de sessões partilhadas: `backend/app/security/access.py:20–23`; seleção TLS explícita sem alterar o percurso anterior: `backend/dedicated_wsgi.py:65–89`.

**Verificações comuns às nove entradas:** AST/imports e leitura não identificaram subprocessos, shell, eval/exec, edição de manifests/gates, DDL, provisionamento, revogação/grant de privilégios, remoção de ficheiros ou outros comandos destrutivos. O método query de PostgresTLS lê a CA; não executa SQL. O método execute de OfflineExecutor consulta um mapa em memória. Os callbacks de conexão/cleanup do adaptador são código injetado de confiança para doubles, não um transporte real ou sandbox.

Não foram identificados segredos, passwords, tokens, chaves privadas ou dados pessoais embebidos no conteúdo das nove fontes. Nomes de campos password/password_hash/CSRF e origem interna fixa são referências de código, não valores secretos. A factory lê credenciais e chave CSRF de ficheiros privados quando é explicitamente construída; nesta revisão só se usaram dados sintéticos dos testes. Nenhum ficheiro de segredo operacional foi lido. A pesquisa automática de padrões é complementar à leitura, não prova universal de ausência de segredos.

## Avaliação conjunta

| Pergunta | Resultado |
| --- | --- |
| Compatibilidade com contratos aprovados? | **Sim, no âmbito de fontes opt-in/offline.** Mantém D05, origem/CSRF/cookies, sessões partilhadas e f066/b12. Não implementa ainda toda a atestação de destino D01 nem novos executores D02. |
| Alteração de segurança injustificada? | Não identificada nesta revisão. Validações, recusas e limites correspondem ao desenho documental; callbacks Python de confiança não são tratados como entradas de clientes. |
| Dependência circular? | Existe ciclo diferido policy→evaluate→policy: o import em Policy.__post_init__ ocorre depois da definição do módulo; evaluate usa a política. Imports e 432 casos G2 passaram. Não foi identificado ciclo de inicialização impeditivo. |
| Dependência não atestada? | Sim: runtime/bibliotecas externas e parte da configuração/imagem estão fora do manifesto atual. A correspondência das dependências internas foi compreendida; não se afirma atestação transitiva integral. |
| Bypass AUTH-03/F02/G2/G4? | Não identificado. Nenhum dos nove altera/chama mutações dos executores. G2 real recusa antes das factories; revalidate não emite evidência. Injeção arbitrária por administrador Python está fora da fronteira que estes contratos protegem. |
| Fontes locais reproduzíveis? | O estado atual é identificável por SHA256; um clone de HEAD sozinho **não recupera** estes nove ficheiros. Reproduzir requer conservar/versionar o bundle exato numa etapa autorizada. Hash não é arquivo de conteúdo. |
| Candidato de 52 fontes íntegro? | **Sim:** conjunto exato, fontes regulares sem symlinks finais, hashes atuais, payload, projeção e ficheiro completo verificados. |
| Os 27 externos invalidam este candidato? | **Não para o âmbito declarado de fontes AUTH-03.** Limitam a conclusão: candidato não é atestação de toda a cadeia security/runtime/imagem, nem autorização de execução. Não se alargou silenciosamente o âmbito. |

Os gates permanecem: AUTH-03 recusa mutações (`scripts/postgres/auth03_alembic_executor.py:56–59`); F02/G4 devolve TARGET_REFUSED ou GATE_ABSENT (`scripts/postgres/g4/contracts.py:491–502`); executor real G2 desativado (`backend/app/readiness_postgres/adapter.py:23–26,122–125`). Evidência sintética não deve ser ligada à readiness operacional, mesmo que satisfaça dataclasses/booleans.

## Riscos bloqueantes e residuais

**Bloqueantes técnicos para recomendar estas nove inclusões: nenhum identificado no âmbito revisto.** Não há ficheiro com recomendação REJEITAR ou INVESTIGAR. A conclusão resulta do conteúdo, dependências e integridade conferidos, além dos testes; não apenas dos testes passarem.

**Aceitação humana ainda necessária:** proveniência local sem commit/autoria histórica independente; conservação de um bundle exato para reprodução; validação limitada a código e execução sintética. Estes riscos são residuais aceitáveis para aprovar o conjunto de fontes com esse âmbito explícito, sem os converter em prova de produção.

**Bloqueios operacionais que permanecem:** os 27 artefactos complementares não estão atestados por este manifesto; perfis históricos/transportes, imagens e dependências transitivas precisam de revisão própria; faltam catálogo físico G2, privilégios reais, checker real autorizado, gates/autoridade de execução e recuperação independente demonstrada. TLS opcional na factory base não satisfaz D01 por si: o futuro perfil deve selecionar o percurso verify-full explicitamente. Isolamento do proxy, paths privados e TOCTOU dependem do ambiente de confiança, ainda não certificado aqui.

Os 27 artefactos mantêm os hashes do inventário DEV-08B. Nenhum foi adicionado ao conjunto de 52 nem declarado aprovado. As lacunas G4/L02 e originais não localizados continuam abertas; não se propõe contorno ou correção nesta entrega.

## Testes e verificações executados

**949 PASS, 0 FAIL, 0 SKIP; 82,23 s**, seis suites existentes, sem modificar testes:

| ID | Suite | Resultado e âmbito relevante |
| --- | --- | --- |
| T1 | `backend/tests/test_dedicated_backend.py` | 127 PASS: configuração, destinos, segredos sintéticos, ausência de engine no arranque |
| T2 | `backend/tests/test_dedicated_entrypoint.py` | 53 PASS: seleção explícita, proxy/health/ready e sessões auth/inventory partilhadas |
| T3 | `backend/tests/test_postgres_tls.py` | 29 PASS: verify-full obrigatório, CA/mount e variantes de configuração |
| T4 | `backend/tests/test_readiness_contract.py` | 289 PASS: evidência inválida/ausente, privilégios e fail-closed |
| T5 | `backend/tests/test_readiness_postgres.py` | 432 PASS: política/queries/avaliação, defaults/ACL, limites, interrupções/cleanup e recusa de executor real |
| T6 | `backend/tests/test_trusted_proxy.py` | 19 PASS: peer/headers/origem e rejeição |

Python -B, PYTHONDONTWRITEBYTECODE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONPATH=backend; pytest --assert=plain -p no:cacheprovider, diretório exclusivo via tempfile.mkdtemp em /tmp. Bloqueio adicional de socket.create_connection/socket.socket.connect, psycopg.connect e subprocess.run/Popen reais. Um plugin apenas contou resultados em memória; não alterou recolha, testes ou expectativas.

Também passaram AST dos nove, inspeção de imports/histórico, comparação das 52 fontes e 27 complementares, digests e preservação Git. A análise por padrões não substitui prova nativa. Não executados SQL, migrações, testes de infraestrutura, TLS nativo, builds, serviços ou scripts de administração. Os dois testes AUTH-03 que falharam em DEV-08B por manifesto ativo divergente não foram repetidos: não abrangem comportamento novo destas nove inclusões e o manifesto continua intacto; não se declara a suite global verde.

## Estado Git e integridade final

Inicial: branch `main`; HEAD `647179c928888adfeef0f69f582fd13c5fc17350`; índice SHA256 `50d32095da16e2c0e985226625971e890c33d406cbb9b97743a7198905b9541e`. 292 ficheiros não ignorados: 202 versionados e 90 não versionados. Quatro modificados preexistentes: backend/migrations/env.py, docs/specifications/f0/data-model.md, docs/specifications/f0/implementation-status.md e frontend/README.md. As nove fontes já eram não versionadas.

Final: mesmos branch/HEAD/índice e alterações preexistentes; **292/292 ficheiros iniciais byte-identical**. Única criação DEV-08C: `docs/operations/dev08c-auth03-local-review.md`; total 293 ficheiros, 91 não versionados. Candidato antes/depois com o SHA256 exato indicado no início; manifesto ativo/gates/fontes/testes inalterados. Sem staging, commit, push, alterações operacionais ou aplicação do candidato.

## Conclusão

**APROVAÇÃO RECOMENDADA** do candidato exato identificado, no âmbito de reconciliação de fontes AUTH-03: **ACEITAR as nove inclusões**, com os riscos residuais explicitamente aceites pelo responsável. A aprovação humana ainda não ocorreu e o candidato continua NOT_APPROVED. Aguardar aprovação explícita antes de qualquer substituição do manifesto; eventual aplicação exige tarefa própria autorizada.
