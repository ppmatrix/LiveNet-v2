# DEV-07 — React real por HTTPS e reconciliação de contratos

Data: 2026-10-25. Estado: componentes independentes demonstrados; integração
persistente completa **não concluída** por decisões/gates ainda pendentes.
Nenhum deployment operacional, acesso a dados/segredos reais, migração aplicacional,
alteração de manifesto protegido, publicação de portas ou push.

## Estado inicial, integridade e proveniência

Branch main, HEAD 647179c928888adfeef0f69f582fd13c5fc17350. 202 ficheiros versionados,
76 não versionados; modificações versionadas preexistentes em backend/migrations/env.py,
docs/specifications/f0/data-model.md e docs/specifications/f0/implementation-status.md.
278 ficheiros não ignorados copiados e inventariados por SHA256 antes de alterações,
em /tmp/livenet-dev07-baseline-qzfx0lh6, diretoria privada com baseline.json.

8 715 ficheiros ignorados inventariados por nome. Candidatos sensíveis identificados:
secrets/auth03_db_password.txt, secrets/auth03_executor.json, secrets/db_password.txt.
Não foram lidos nem copiados. Chaves privadas, PKI e passwords novas são apenas
sintéticas, em diretórios temporários do ensaio, eliminados no cleanup.

A proveniência DEV-03–06 foi verificada pelos relatórios, paths e hashes existentes;
ficheiros não versionados não ganharam aprovação/atestação por estarem presentes.
O código M1.1/M1.2A e os quatro hashes protegidos foram rastreados em Git conforme
abaixo. Os textos originais D-01–D-52/16 capítulos não foram inventados ou substituídos.
As lacunas documentais anteriores, incluindo as 28 G4/L02 declaradas, permanecem abertas.

## O que foi implementado

- scripts/dedicated/dev07_frontend.py: cópia temporária do frontend sem .env/.npmrc,
  npm ci pelo lock em Node isolado, Vitest e TypeScript/Vite sem rede, hashes do
  código copiado e do dist; remove node_modules/cache de instalação dessa cópia.
- infra/dedicated/browser/: imagem de cliente Chromium/Playwright-core, base por
  digest, package-lock com integridade, contexto que permite apenas os dois JSON
  npm. Nenhum código aplicacional/segredo é copiado para a imagem browser.
- scripts/dedicated/dev07_browser.mjs: browser real, sem route mocks, valida trust
  TLS, rota protegida, CSRF/cookies, tratamento de 503, limpeza da password,
  ausência de sessão/inventário privado e recuperação por retry.
- scripts/dedicated/dev07_check.py: liga build real/browser à infraestrutura TLS
  descartável existente; regista os hashes dos mesmos assets servidos/testados.
- scripts/dedicated/dev06_check.py: novas opções keyword para dist/browser/run_tag;
  defaults DEV-06 preservados e retestados. Copia dist real sem o substituir por
  sentinela; labels e alias DNS do browser limitados ao ensaio isolado.
- scripts/dedicated/dev06_postgres_probe.py: fixture independente alargado para
  negar acessos a sequences, CREATE DATABASE, ALTER/DROP TABLE pelo runtime.
- scripts/dedicated/dev07_reconcile.py: auditoria read-only por hashes/commits,
  separando origem de fontes e aprovação/atestação. Nunca escreve AUTH-03.

Não foi necessário alterar código React, autenticação, inventário, sessões ou
readiness para fazer passar o ensaio independente: o comportamento observado
está correto perante a ausência da persistência legitimamente preparada.

## Identidade PostgreSQL: reconciliação e recomendação

| Dimensão | Significado e evidência | Estado |
|---|---|---|
| Nome da base | DAT-05A, data-model.md, texto localizado marcado Aprovada, commit 8b2e32e, define livenet | Não define explicitamente exceção/nomes por ambiente. |
| Guarda dedicada | app/dedicated.py rejeita literalmente livenet; relatório DEV-02 documenta proteção do destino original | Preservada, incluindo no perfil TLS. Não permite relaxar isolamento v1. |
| Cluster | system_identifier físico, controlado no ensaio via pg_controldata e comparado por TLS | Independente do nome; novo initdb descartável em cada ensaio. Não é aprovação humana G4. |
| Ambiente | Projeto, rede, dados, volume/tmpfs e finalidade aprovados | Nome de DB, role ou label isoladamente não identifica o ambiente. |
| Schemas | Organização dos domínios dentro da base | Não são bases nem clusters; não foram criados schemas aplicacionais. |
| Roles | Identidades e privilégios SQL separados | Não substituem identidade física/TLS do destino. |
| Hostname/TLS | SAN db, CA e verify-full | Verifica servidor TLS; não demonstra revisão, ACL nem autorização de migração. |

A guarda nasceu no percurso dedicado posterior à especificação geral; a sua
proveniência local está documentada na DEV-02, mas não existe commit próprio nem
texto original recuperado que aprove uma exceção DAT-05A por ambiente. O ensaio
continua em dev06_synthetic, apenas num cluster novo, nunca na base livenet.

Recomendação para decisão humana: formalizar uma base aplicacional por ambiente
com nomes v2 distintos (por exemplo, livenet_v2_<ambiente>), mantendo a guarda v1,
e vincular a seleção a cluster/PKI/roles/rede. Implica clarificar DAT-05A, configuração
e inventário de destinos. Alternativa: nome livenet em cluster v2 fisicamente
separado; exigiria rever a guarda apenas após aprovar controles de destino fortes.
Nenhuma alternativa foi tratada como aprovada ou implementada operacionalmente.

## Alembic: estrutura não equivale a autorização

- Grafo aplicacional: 14 revisões, cadeia linear até f067a01a7230, posterior a f066.
  f066 tem origem versionada no commit 9069aa3; f067 permanece não versionada.
- f067 cria authorization.authorization_integrity_anchors; **não** cria utilizadores,
  sessões ou throttling de security. A cadeia security é independente, revisão
  b12b01a7230, com env/contrato próprios e conexão externa/transação obrigatórias.
- A readiness exige f066a01a7230 + b12b01a7230. AUTH-03 exige f066 ou f067 conforme
  operação/perfil. Não há duas heads estruturais: há expectativas/proveniência
  diferentes e autorização não resolvida.
- operation_gate AUTH-03 continua a recusar mutações; o coordenador security mantém
  execution_enabled=False; a fronteira G4 permanece GATE_ABSENT. F02/G2/G4 intactos.
- Não foram executados head, stamp, upgrade/downgrade ou escrita em ledgers. Não
  se usou metadata.create_all nem DDL equivalente como alternativa às migrações.

Proposta de decisão: aprovar explicitamente o destino de cada perfil/ambiente e
as cadeias aplicáveis, incluindo se f066+b12b é a baseline aplicacional e se f067
pertence ao perfil de execução AUTH-03 ou passa a ser requerido noutro perfil.
Se f067 for exigido no runtime, rever readiness e os contratos dependentes como
um todo. Não substituir apenas a string da revisão nem executar DDL por outro
executor enquanto os gates continuarem fechados.

## AUTH-03: evidência recuperada e plano de aprovação

[dev07-contract-evidence.json](dev07-contract-evidence.json) contém os 21 paths
omitidos, quatro pares de hashes, grafos e proveniência por ficheiro. É relatório;
não é manifesto alternativo e não é consumido pelo executor.

31 entradas protegidas, 52 fontes esperadas, 21 omissões, zero extras, quatro
hashes divergentes, igual ao início DEV-07. As fontes são verify_bundle() e
scripts/postgres/auth03_executor_integrity.json; o conjunto esperado vem de .py
em backend/app e backend/migrations mais os três ficheiros fixos do executor.

| Hash divergente | Origem atual | Versão cujo conteúdo coincide com o hash protegido |
|---|---|---|
| backend/app/__init__.py | e02ba8a, autenticação/RBAC M1.2A | 4d85240 |
| backend/app/config.py | e02ba8a, autenticação/RBAC M1.2A | 4d85240 |
| backend/app/core/model_registry.py | e02ba8a, registo dos modelos security | 9069aa3 |
| backend/requirements.txt | e02ba8a, dependências M1.2A | 07bd817 |

Os quatro conteúdos atuais coincidem com HEAD; não são edições locais DEV-07.
Das 21 omissões, 12 são fontes versionadas M1.1/M1.2A, em 24ea360/e02ba8a,
também iguais a HEAD; nove são artefactos locais anteriores de dedicated/TLS/
proxy/readiness cuja origem por relatórios não equivale a atestação criptográfica.

| Categoria solicitada | Conclusão |
|---|---|
| Divergência documental | Texto antigo de 31 fontes não descreve as 52 atualmente exigidas. A diferença é também executável: verify_bundle recusa. |
| Código com proveniência conhecida ainda não atestado | Quatro divergências e 12 omissões têm origem Git comprovada. Isso não aprova a mudança da raiz de confiança. |
| Alteração de segurança não autorizada | Não demonstrada nesta auditoria; ausência de atestação não prova intrusão, nem autoriza aceitar os bytes. |
| Fontes/decisões indisponíveis | As nove fontes locais estão disponíveis; faltam uma referência Git atestada e textos originais/alcance de decisões suficientes. Requerem revisão explícita. |

Plano para aprovação humana, sem regeneração automática:

1. Consolidar proveniência/baseline por seleção explícita de ficheiros; rever os
   diffs 24ea360/e02ba8a e os nove artefactos locais, incluindo fronteiras de confiança.
2. Confirmar o scope do bundle, identidade do executor e relação com a cadeia
   security; AUTH-03 não abrange automaticamente a diretoria security_migrations.
3. Rever exatamente as 21 adições e quatro mudanças de hash, associando revisores,
   decisão, ambiente e versão de referência. Validar ausência de segredos/extras.
4. Só com autorização específica, aprovar uma nova referência de manifesto e
   revalidar imagem/bundle/canais/gates. O relatório de hashes não concede aprovação.
5. Reexecutar todos os testes, incluindo os dois positivos AUTH-03 hoje falhados,
   e autorizar migrações apenas pelo mecanismo revisto, num novo descartável.

Nenhum teste foi alterado para aceitar hashes novos; não houve xfail, skip ou
ocultação das duas falhas. Nada foi escrito na raiz de confiança protegida.

## D05: máximo âmbito legítimo

PostgreSQL 16.15 novo, TLS/SCRAM, roles admin/owner NOLOGIN/migrator/runtime/inspector
separadas. O schema dev06_probe é apenas o fixture independente reutilizado num
cluster novo DEV-07. Roles/tabelas com nomes DEV-06 não significam reutilização de
recursos existentes. Não são os schemas aplicacionais nem uma migração legítima.

Passaram: TLS positivo, CA/hostname errados e plaintext recusados; owner NOLOGIN;
SELECT/INSERT/UPDATE por coluna no fixture; auditoria sintética INSERT-only;
SELECT/UPDATE/DELETE/TRUNCATE proibidos; CREATE TABLE/TEMP/ROLE/DATABASE e
ALTER/DROP TABLE recusados ao runtime; nextval, setval e SELECT da sequence
recusados; row-lock autorizado apenas na tabela com UPDATE adequado; rollback
atómico e confirmação por outra ligação; inspector sem leitura de dados do fixture.

Não foi atestada a matriz D05 sobre objetos reais: sem schemas security/inventory/
audit, faltam testes PostgreSQL de utilizadores, sessões, throttling, eventos reais,
consultas autenticadas, grants por coluna e sequences dos modelos aplicacionais.
O contrato D05 existente mantém inventário SELECT-only. A existência de POST no
backend e inventory_editor no RBAC não autoriza INSERT no perfil D05; escrita de
inventário requer decisão de perfil/privilégios própria. Não se ampliaram grants
para satisfazer o objetivo de demonstração. As verificações por doubles passaram,
mas não são evidência de persistência aplicacional real.

## React e integração HTTPS reais

npm ci usou o package-lock existente, scripts de instalação desativados e dois
ficheiros npm vazios distintos; .env/.npmrc e credenciais do host não são copiados.
Dependências só em cópias temporárias/contentores Node. Os testes e o build
executaram sem rede. Nenhum node_modules, dist ou cache foi criado em frontend/.
O primeiro ensaio de configuração npm recusou user/global config ambos /dev/null;
foi corrigido para ficheiros vazios distintos. Não foi necessária alteração do lock
ou das versões React para completar a instalação/build.

40 testes Vitest em três ficheiros passaram, incluindo sessão, CSRF, RBAC de UI,
contratos HTTP, navegação, lista/detalhe e falhas. São testes com doubles HTTP;
não provam que o inventário/autenticação persistente estão operacionais.
TypeScript --noEmit e Vite 8.3.5 passaram. Node do contentor: 24.22.1, npm 11.19.1;
React/React DOM 19.3.1. Dois builds isolados produziram os mesmos hashes do dist:

| Asset | SHA256 |
|---|---|
| index.html | 428ed629b6d4fa831fe8850d52370feb6b785e87d6e2c50e0f5aac0011df1fd3 |
| assets/index-B7_Pxd3n.js | a733c8b9b3b078f8a383b0baf3c81993e12dc4f8b853a4e174276e6ae10c2b98 |
| assets/index-DDSDGLfQ.css | d384be81848002734736c0e435d0068d344ec22115acbc8733a7728650843ea6 |

Chromium 156.0.8078.47 e Playwright-core 1.58.2 executaram o bundle real pelo Caddy.
O browser recusou a CA não confiada; após importar apenas o certificado público
num NSS DB temporário, navegou sem ignoreHTTPSErrors/ignore-certificate-errors.
Node usa a mesma CA pública apenas para os pedidos auxiliares de teste. Nenhum
trust store do host foi alterado. O sandbox interno Chromium está desativado no
cliente descartável, isolado por Docker, UID 10001, cap_drop ALL, rootfs read-only,
no-new-privileges e sem ports; isto não altera TLS, CSRF ou segurança da aplicação.

Observado por browser, sem mocks de rotas ou API:

- /inventory redireciona para /login após me=401, sem consultar inventário privado.
- Assets reais 200, DOM React montado, window.isSecureContext verdadeiro.
- Formulário obtém CSRF e envia Origin da mesma origem e X-CSRF-Token.
- Login devolve 503/security_unavailable; UI apresenta erro genérico, limpa a
  password, mantém o formulário utilizável e permite retry.
- Cookie CSRF Secure/HttpOnly/SameSite=Lax; nenhuma sessão emitida.
- Retry recupera o estado anónimo; zero pageerrors de JavaScript.
- API de inventário anónima responde 401/JSON; health 200 e readiness 503.
- Uma ligação do backend ao PostgreSQL foi atestada como TLS no servidor.

Captura do estado real, com password já limpa:
`/tmp/livenet-dev07-artifacts/browser-output/react-unavailable.png`.
É evidência da UI e de indisponibilidade segura, não de uma sessão autenticada.

Fronteira exata: HTTPS → React real → tentativa de autenticação com CSRF → backend
→ ligação PostgreSQL TLS → impossibilidade de persistência nos schemas ausentes.
O acesso inicial a security.login_throttles não pode concluir; os gates impedem a
preparação dos schemas/revisões que falta. O gate AUTH-03 não é chamado diretamente
pelo login: bloqueia o percurso de preparação/execução protegido. Não se deve
confundir 503 por schemas ausentes com uma verificação HTTP do manifesto.

## Readiness e decisões humanas necessárias

Readiness permaneceu 503 antes/depois de restart do backend. Não foi fornecido um
checker positivo ou alterado o contrato f066/b12b, nem substituída a verificação por
TCP/SELECT. Dependências ainda não satisfeitas: aplicação legítima das revisões,
matriz D05 real, manifesto/identidade de verificador e gates aprovados. Recuperação
independente, backup/restauro e validação operacional continuam não demonstrados.

| Decisão | Recomendação / consequência |
|---|---|
| Nome por ambiente versus guarda v1 | Formalizar nomes v2 por ambiente mantendo isolamento; alternativa livenet exige nova atestação física/PKI e revisão da guarda. |
| Revisões por perfil | Decidir f066/f067 e cadeia security explicitamente; só depois autorizar percurso Alembic dirigido. |
| Manifesto/raiz de confiança | Rever as 21 adições e quatro alterações, consolidar proveniência e aprovar uma referência por processo humano específico. |
| D05 consulta versus escrita | Preservar SELECT-only; se escrita for requerida, aprovar um perfil/matriz separado, sem ampliar grants para fazer passar testes. |

Estas decisões não foram escolhidas nem aprovadas automaticamente. Os restantes
trabalhos independentes foram concluídos sem interromper para pequenas decisões.

## Testes executados nesta DEV-07

| Verificação | Resultado novo |
|---|---|
| Vitest React | 40 passaram; três ficheiros. |
| TypeScript + Vite | Passaram; dist real e hashes acima. |
| Chromium/HTTPS/React/API | Passou nos limites descritos, sem sessão persistente. |
| PostgreSQL/TLS/roles/ACL/sequences/rollback | Passou no fixture independente. |
| Suite backend offline, 23 ficheiros | 1 327 passaram em 100,96 s. |
| AUTH-03/G4/security gates | 289 passaram, duas falharam em AUTH-03. |
| Repetição dos dois testes AUTH-03 na baseline inicial DEV-07 | As mesmas duas falharam. |
| Compatibilidade do harness DEV-06 sem opções novas | Passou; react_ui_demonstrated=false e persistência aplicacional bloqueada, como antes. |
| Contexto backend BuildKit | 40 ficheiros reais e 41 adversariais, hashes exatos, sem extras. |
| git diff --check | Passou. |

As duas falhas preservadas são test_verified_manifest_and_tampering e
test_future_lock_conflict_and_wrong_source. verify_bundle recusa antes do resultado
positivo/lock esperado. Não houve regressão nova demonstrada; isso não significa
que a suite de gates esteja globalmente verde. Os testes PostgreSQL aplicacionais
bloqueados não foram substituídos por testes em schemas criados manualmente.

A suite backend usa PYTHONDONTWRITEBYTECODE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1,
pytest -q -p no:cacheprovider e basetemp exclusivo, com audit hook contra sockets/
processos e psycopg real proibido. Os três módulos de gates executam com as mesmas
barreiras. O PostgreSQL real é utilizado apenas no harness descartável. Não foram
executados testes de integração em bases/volumes persistentes preexistentes.

## Reprodução e proveniência de builds

1. Disponibilizar localmente as bases por digest indicadas na DEV-06 e a base Node
   node@sha256:55fb5f5a527ea2c5c4a95f963e48ef90aa38c7b346054fdc8ee9957a2b55d205.
2. Construir backend/Dockerfile.dedicated com DEV04_PYTHON_IMAGE registado,
   tag livenet-dev07/backend:integration. Construir infra/dedicated/browser/Dockerfile,
   contexto infra/dedicated/browser, DEV07_NODE_IMAGE igual ao digest Node acima,
   tag livenet-dev07/browser:integration. Confirmar exit codes antes de avançar.
3. Executar `python3 scripts/dedicated/dev07_frontend.py --evidence-dir <diretoria>`.
   frontend-build-evidence.json regista frontend_dist, fonte copiada, base e hashes.
4. Executar `python3 scripts/dedicated/dev07_check.py --frontend-dist <frontend_dist>
   --evidence-dir <diretoria/browser-output>`; não executar compose up.
5. Executar `python3 scripts/dedicated/dev07_reconcile.py` para nova auditoria
   read-only; o resultado nunca aprova o manifesto.

Downloads limitaram-se às dependências necessárias: imagem Node oficial Docker
Hub, registry.npmjs.org e repositórios Debian/segurança com verificação APT de
assinaturas. Não foi enviado código/segredo/dado da aplicação a serviços externos.
Frontend usa npm lock original; browser usa lock próprio com integridade. Os
pacotes Debian da ferramenta browser não são snapshot imutável: versões efetivas
foram registadas, sem alegar builds futuros byte-idênticos ou aprovação operacional.

Imagem backend testada: sha256:68e16b08b6e038f6fd9712a9a6fbb2a8b7e8f2839f048f744cf60db57bf64ad8.
Imagem browser final: sha256:721a6387112f333bad996f9da58022f5930b5b3fdcee389ce469d379fbecd04d.
libnss3-tools: 2:3.87.1-1+deb12u4. Demais dados/locks em browser-versions.log,
build-provenance.json e no contexto browser. Labels e IDs de cluster são evidência
de teste, não referências aprovadas de produção.

Logs/captura desta execução em /tmp/livenet-dev07-artifacts/: frontend-install.log,
frontend-test.log, frontend-build.log, frontend-build-evidence.json, browser-build.log,
backend-build.log, backend-tests.log, gates.log, auth03-baseline.log, integration.log,
dev06-compatibility.log, backend-context.log e browser-output/react-unavailable.png.
Não somar repetições do mesmo teste como casos distintos.

## Git, reversão e próximo incremento

Sem git add, commits ou push; mesma branch/HEAD e índice inicial. A baseline
preexistente contém muitos ficheiros necessários ao runtime ainda não versionados.
Um commit parcial não produziria checkout reproduzível; não foram incluídos para
limpar o estado. Plano seguro: rever/consolidar baseline anterior por paths/hunks
explícitos; depois separar commit das ferramentas React/browser e commit da
reconciliação/documentação, mantendo AUTH-03 dependente de aprovação própria.

Reversão: comparar com /tmp/livenet-dev07-baseline-qzfx0lh6 e retirar apenas os hunks
DEV-07 e os ficheiros novos listados abaixo, após confirmar ausência de trabalho
posterior. Não fazer reset/clean global. Os corpos históricos de frontend/README.md
e implementation-status.md foram preservados integralmente como sufixo. Não há
rollback PostgreSQL aplicacional, pois nenhuma migração/schema aplicacional ocorreu.

Próximo incremento recomendado: decisões humanas acima e aprovação legítima do
percurso de preparação, seguidas de novo cluster descartável com revisões dirigidas,
conta sintética provisionada pelo processo aprovado, login/sessões/throttling,
auditoria e inventário de consulta reais, com testes positivos/negativos D05.
Só depois implementar/ligar checker readiness que satisfaça G2/G4. Não declarar
STAGING/PROD ou alterar exposição de rede a partir desta evidência.

## Inventário final DEV-07

Alterados relativamente à baseline:

- `docs/specifications/f0/implementation-status.md`
- `frontend/README.md`
- `scripts/dedicated/dev06_check.py`
- `scripts/dedicated/dev06_postgres_probe.py`

Criados:

- `docs/operations/dev07-contract-evidence.json`
- `docs/operations/dev07-react-integration.md`
- `infra/dedicated/browser/Dockerfile`
- `infra/dedicated/browser/Dockerfile.dockerignore`
- `infra/dedicated/browser/package-lock.json`
- `infra/dedicated/browser/package.json`
- `scripts/dedicated/dev07_browser.mjs`
- `scripts/dedicated/dev07_check.py`
- `scripts/dedicated/dev07_frontend.py`
- `scripts/dedicated/dev07_reconcile.py`

## Estado final e limpeza

Ensaio React final: livenet-dev07-e583e74829, Chromium 156.0.8078.47,
PostgreSQL 16.15, system_identifier sintético 7700647093224869927.
status=passed refere-se às verificações independentes; persistentLogin=false e
application_persistence_demonstrated=false continuam explícitos no resultado.
Cleanup do ensaio e do teste de compatibilidade sem falhas.

Todos os contentores/redes próprios, PKI, credenciais, as duas cópias temporárias
frontend (incluindo node_modules/cache), imagem backend DEV-07, ambas as imagens
browser (intermédia/final) e base Node puxada nesta tarefa foram removidos. IDs e
tags foram conferidos antes de remoção, sem force/prune. Imagens/volumes/serviços
preexistentes permaneceram intactos; caches partilhados Docker não foram limpos.

Permanecem apenas a baseline privada de integridade e os logs/hashes/captura de
evidência sem segredos. Para repetir, reconstruir as imagens e gerar novo dist;
os paths temporários em frontend-build-evidence.json descrevem a execução
concluída e já não contêm um serviço ou build disponível para ativação.

Git final: main, HEAD 647179c928888adfeef0f69f582fd13c5fc17350; sem staging,
commits, push ou mudança de branch. Índice SHA256 inicial/final idêntico:
50d32095da16e2c0e985226625971e890c33d406cbb9b97743a7198905b9541e.
278 ficheiros iniciais: 274 mantiveram o hash; quatro receberam apenas as edições
listadas e dez ficheiros novos foram criados. Nenhum ficheiro anterior eliminado.
Fontes backend, gates, Alembic, manifesto AUTH-03 e código React/package-lock
permanecem byte-idênticos à baseline; em frontend só o README recebeu apontador.

Aceitação: reconciliação/proposta AUTH-03, ferramentas, React/browser reais e
testes independentes concluídos. D05 aplicacional e integração persistente
bloqueados. Não há sucesso global, readiness positiva ou autorização STAGING/PROD.
