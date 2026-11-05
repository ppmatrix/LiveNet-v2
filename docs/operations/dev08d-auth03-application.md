# DEV-08D — Aplicação controlada do manifesto AUTH-03

Data: 2026-10-25. Ambiente: progbox. **APLICADO E VALIDADO OFFLINE**. Sem migrações, SQL, ativação de serviços ou abertura de gates.

## Aprovação e âmbito

Fonte humana primária: pedido DEV-08D desta conversa, anexo `7b8d1879-6417-4d95-8774-d72e58a09a10/Pasted text.txt`, §§1–4. Aprova explicitamente o candidato de 52 fontes, as 21 inclusões, quatro substituições, nove inclusões locais revistas em DEV-08C, riscos residuais e esta aplicação controlada. Não autoriza alterar qualquer outro contrato protegido ou iniciar integração persistente.

Foram consultados [DEV-08B](dev08b-persistence-formalization.md), [DEV-08C](dev08c-auth03-local-review.md), [contrato AUTH-03](../specifications/f0/auth03-alembic-executor.md) e o verificador `scripts/postgres/auth03_alembic_executor.py:136–151`.

Candidato aprovado: [DEV-08B-AUTH03-CANDIDATE-01](dev08b-auth03-candidate.NOT-APPROVED.json). O ficheiro e o seu nome/estado histórico NOT-APPROVED permanecem intactos para conservar os bytes revistos. A aprovação posterior é externa ao envelope e fica rastreada neste relatório; não se altera o candidato para simular outra versão.

## Estado Git inicial

Branch `main`; HEAD `647179c928888adfeef0f69f582fd13c5fc17350`; SHA256 do índice `50d32095da16e2c0e985226625971e890c33d406cbb9b97743a7198905b9541e`. 293 ficheiros não ignorados: 202 versionados, 91 não versionados. Quatro modificados preexistentes: backend/migrations/env.py, docs/specifications/f0/data-model.md, docs/specifications/f0/implementation-status.md e frontend/README.md.

O manifesto ativo e os artefactos DEV anteriores já eram não versionados. Não se mudou branch, fez reset/clean, staging, commit ou push. O registo de implementação anterior não precisou de alteração: este relatório documenta o novo estado sem reescrever decisões históricas.

## Preflight e equivalência determinística

| Verificação | Resultado |
| --- | --- |
| Caminho e SHA256 do candidato completo | PASS; valor autorizado abaixo |
| Estrutura JSON/envelope, ID, mapa proposto e digests internos | PASS |
| Conjunto exigido por verify_bundle | 52 caminhos exatos; nenhum extra |
| Hash atual de cada fonte versus candidato | 52/52 PASS; nenhum hash aprovado corrigido ou recalculado para substituir valores |
| Alterações posteriores às fontes revistas | Nenhuma: hashes preservados e proveniência/estado Git sem mudanças |
| Manifesto ativo anterior | Hash igual à baseline do candidato; 31 entradas |
| Delta aprovado | 21 inclusões, quatro substituições, 27 entradas mantidas, zero exclusões |
| Procedimento oficial | Substituição do mapa revisto após aprovação; sem comando de regeneração/autoaceitação; verify_bundle permanece intacto |
| Concorrência observada | Sem mudança de inode/tamanho/mtime/ctime/hash até à verificação imediatamente anterior à substituição |

Foi extraído **somente payload.proposed_manifest**, sem gerar valores a partir das fontes atuais. Estas foram lidas apenas para comparação. Serialização prevista pelo envelope/DEV-08B: UTF-8 de `json.dumps(mapping, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False)`, seguido de **um LF real**. A leitura JSON dos bytes resultantes é igual ao mapa aprovado e o SHA256 corresponde à projeção já fixada no candidato. Metadados de revisão/aprovação e inventário suplementar não foram inseridos no manifesto plano.

### Identificadores SHA256

| Artefacto | SHA256 |
| --- | --- |
| Candidato completo, antes/depois | `09263b8501b277f6f41df1320d08e85ee6c9a07e4770115ccc95869df25974a6` |
| Payload canónico do candidato | `cde103b540b6f3f99956f92e600c33ec1e96a9bf5865ff589e81ab17e0a0a6f7` |
| Manifesto anterior e backup | `7a9993faba2af675f46bd53daea96f9e4980624c3ef07f4d5af6cdfdfbe7c326` |
| Projeção aprovada e manifesto resultante | `4819c697b7d12f7ab5cbb1fdfa9cf4c3fd0e98e93b53a60337296cc84036fc29` |

## Backup e aplicação

Backup byte a byte, criado **antes da substituição**:

```text
/tmp/livenet-dev08d-backup-ot669kfw/auth03_executor_integrity.before.json
```

Recibo de metadados, hashes das fontes e pré-condições:

```text
/tmp/livenet-dev08d-backup-ot669kfw/backup-receipt.json
```

O diretório é privado, modo 0700, e fica fora do worktree: não é incluído por operações Git sobre este repositório. O backup conserva modo 0664, UID/GID 1000:1000 e timestamps originais registados no recibo. mtime original em nanossegundos: `1792528967467999782`. Bytes e metadados relevantes foram comparados; ctime/inode anteriores são evidência, não valores reproduzíveis num novo inode.

A substituição usou lock advisory não bloqueante no manifesto anterior, revalidação de fontes/candidato/manifesto, ficheiro temporário exclusivo no mesmo diretório, preservação do modo/owner/grupo, flush/fsync e os.replace atómico. O diretório do manifesto foi sincronizado. O temporário próprio foi removido do namespace pela substituição; não restam ficheiros temporários de manifesto no repositório. O manifesto resultante mantém modo 0664 e UID/GID 1000:1000; mtime/ctime/inode refletem a substituição.

Não existe garantia absoluta contra um escritor hostil que ignore o lock ou substitua o inode. O controlo demonstra ausência de alteração observada até à comparação final; não é apresentado como exclusão operacional de administradores ou prova de atomicidade com serviços.

**Interrupção preventiva sem efeitos:** a primeira tentativa foi recusada antes do backup/substituição por perda de precisão dos timestamps ao passarem pelo registo intermédio JavaScript. Corrigiu-se apenas a representação transitória para strings/inteiros exatos. Não se alterou timestamp, fonte, candidato ou hash para fazer passar a verificação. A nova tentativa comparou os metadados exatos e passou.

## Validação pós-aplicação

**Verificador oficial: PASS.** Foi invocada apenas a função pura de leitura `auth03_alembic_executor.verify_bundle()`, não a CLI/preflight que consultaria Docker. Devolveu o SHA256 resultante indicado acima.

`python3 -B scripts/dedicated/dev07_reconcile.py`: **52 entradas / 52 esperadas, zero ausências, zero extras e zero hashes divergentes**. Não executa PostgreSQL/Docker. A comparação final confirmou as 52 fontes sem alterações e o candidato completo com o mesmo digest autorizado.

### Testes existentes

**1491 PASS, 0 FAIL, 0 SKIP; 90,37 s**, em 16 suites. São 1154 casos backend e 337 casos dos scripts offline. Nenhum teste, expectativa ou gate foi alterado.

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
scripts/postgres/tests/test_g4_boundaries.py
scripts/postgres/tests/test_m12b_security_migration.py
scripts/postgres/tests/test_m12b_security_execution.py
```

Python -B, PYTHONDONTWRITEBYTECODE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 e PYTHONPATH=backend:.; pytest --assert=plain -p no:cacheprovider. Fixtures num diretório exclusivo tempfile.mkdtemp em /tmp. Bloqueio adicional de socket.create_connection/socket.socket.connect, psycopg.connect e subprocess.run/Popen reais. Contagem por plugin em memória, sem alterar recolha/expectativas.

As duas falhas anteriores estão **resolvidas**:

| Caso AUTH-03 | Antes | Depois |
| --- | --- | --- |
| test_verified_manifest_and_tampering | Recusado por conjunto de fontes divergente | PASS: verifica bundle aprovado e rejeição prevista |
| test_future_lock_conflict_and_wrong_source | Recusa do bundle impedia chegar ao caso de lock | PASS: alcança o cenário offline e valida recusas de lock/origem |

### Sete verificações adicionais de integridade

Executadas com o **mesmo verificador oficial** sobre cópias temporárias das fontes/manifesto em /tmp, sem tocar no worktree:

1. Mapa aprovado e fontes exatas: aceite, digest correto.
2. Um byte adicional numa fonte: recusado.
3. Fonte ausente: recusada.
4. Fonte extra: recusada.
5. Fonte symlink mesmo com bytes equivalentes: recusada.
6. Manifesto antigo contra as fontes atuais: recusado.
7. Envelope documental usado como mapa plano: recusado.

**7 PASS, 0 FAIL**, contados separadamente da suite de 1491 testes. As cópias descartáveis foram eliminadas pelo seu contexto temporário; o backup foi mantido. O manifesto real permaneceu igual durante estes casos. As verificações de hashes/proveniência confirmam correspondência às fontes aprovadas, não autenticidade histórica adicional das fontes locais.

Não surgiram regressões de segurança/integridade atribuíveis à substituição; não foi necessária reversão. Não se repetiram ou ampliaram testes após estes resultados sem motivo.

## Gates e limites preservados

| Fronteira | Estado após aplicação |
| --- | --- |
| AUTH-03 operation_gate | Mutações continuam recusadas; nenhuma flag de ativação |
| F02/G4 execution_boundary | Continua TARGET_REFUSED/GATE_ABSENT; claims não concedem autoridade |
| G2 | Executor real desativado; pacote/testes sintéticos não são evidência operacional |
| Executor security | execution_enabled=False preservado |
| Alembic | Grafos, fontes, contratos e ledgers intactos; nenhum upgrade/stamp/SQL |
| Readiness | Código/contrato fail-closed preservados; sem checker real autorizado, permanece indisponível (503 nos testes); serviço real não consultado |

Evidências: `scripts/postgres/auth03_alembic_executor.py:56–59`, `scripts/postgres/g4/contracts.py:491–502`, `backend/app/readiness_postgres/adapter.py:23–26,122–125`, `scripts/postgres/m12b_security_migration.py:52–62` e `backend/app/readiness.py:105–132`, todos com hashes iguais à baseline.

Não houve uso de segredos reais, SQL, migrações, bases, roles/ACL, Docker, builds, serviços, deploy, firewall/routing/exposição, commits ou push. Os testes usaram apenas dados sintéticos. Ter manifesto de fontes válido não autoriza executar qualquer destas operações.

## Reversão verificável

As pré-condições de reversão foram verificadas **em leitura**, sem executar restauro:

1. Backup regular no caminho acima, com SHA256 anterior exato e metadados correspondentes ao recibo.
2. Manifesto ativo ainda com o SHA256 aplicado exato; recusar reversão automática se houve outra alteração.
3. Candidato com o digest aprovado e as 52 fontes ainda com os hashes do recibo/candidato; não sobrepor fontes que mudaram entretanto.
4. Sob nova autorização ou em resposta à regressão prevista nesta tarefa, adquirir lock, repetir essas comparações e preparar cópia do backup em temporário exclusivo no diretório do manifesto.
5. Preservar modo/UID/GID e timestamps documentados, fsync e substituição atómica; confirmar imediatamente o SHA256 anterior. Não executar Git reset/clean nem modificar fontes, testes ou ledgers.
6. Reconhecer o resultado: esta reversão repõe **o estado pré-DEV-08D, conhecido como inválido/fail-closed para as fontes atuais**. Não é um bundle antigo operacional aprovado; o verificador voltará a recusar o conjunto de 31 entradas. Recuperar um bundle anterior coerente e aprovado exige fontes correspondentes e autorização própria.

A aplicação incluía reversão imediata se a sua primeira verificação oficial/integridade falhasse, condicionada a o manifesto ainda ser o recém-aplicado; esse caminho não foi necessário. Os testes posteriores também não produziram condição que exigisse restauro.

O backup é local e temporário sob /tmp, sujeito a limpeza/reinício. Deve ser conservado por processo de retenção autorizado se necessário além desta janela; não substitui backup operacional nem demonstra recuperação administrativa independente.

## Estado Git final e riscos remanescentes

Mesma branch `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350` e índice `50d32095da16e2c0e985226625971e890c33d406cbb9b97743a7198905b9541e`. **292 dos 293 ficheiros iniciais permanecem byte-identical; a única alteração inicial é o manifesto autorizado.** Os quatro ficheiros versionados modificados e os 91 não versionados preexistentes foram preservados. Como o manifesto já era não versionado, o seu conteúdo alterado não aparece como um novo M no git status.

Único novo caminho no repositório: `docs/operations/dev08d-auth03-application.md`. Total final: 294 ficheiros não ignorados, 202 versionados e 92 não versionados. Fora do repositório permanecem apenas backup/recibo desta tarefa e dados temporários de testes. Não houve staging/commit/push. Diff/whitespace e preservação final foram verificados.

Riscos aceites mantidos: nove fontes sem proveniência Git histórica independente; evidência estática/sintética, sem prova operacional; **27 artefactos externos continuam fora da cobertura e não atestados por este manifesto**. Aprovação humana não autentica por si qualquer autorização operacional G4 nem resolve dependências transitivas/imagens.

Permanecem pendentes perfis concretos de destino, transporte/identidades dos executores, atestação complementar security/runtime/imagem, catálogo físico G2, verificador operacional autorizado, privilégios reais, recuperação independente e lacunas G4/L02. O âmbito de aprovação foi o mapa de fontes exato, não cobertura integral do sistema.

**Próximo incremento recomendado:** preparar/rever o contrato concreto de um ensaio descartável e a atestação complementar dos executores, mantendo a execução desativada até autorização específica. Não avançar agora para migrações ou integração persistente.
