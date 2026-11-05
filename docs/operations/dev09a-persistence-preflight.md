# DEV-09A — Preparação da integração persistente PostgreSQL

Data: 2026-10-25, progbox. **Validação descartável concluída; autorização de migrações DEV-09B BLOQUEADA.** O ambiente e as fixtures passaram; não existe ainda um comando legítimo de execução para o novo destino sem trabalho adicional nos executores/contratos e autorização específica.

Fonte humana: pedido DEV-09A, anexo `2746191e-a359-47c5-86e1-088314986331/Pasted text.txt`. Autoriza preparação, implementação e testes descartáveis; exclui migrações aplicacionais/security e operação. Nenhuma foi executada.

## Preflight e baseline

Branch `main`; HEAD `647179c928888adfeef0f69f582fd13c5fc17350`; índice SHA256 `50d32095da16e2c0e985226625971e890c33d406cbb9b97743a7198905b9541e`. 294 ficheiros não ignorados (202 versionados, 92 não versionados), quatro modificados preexistentes: backend/migrations/env.py, docs/specifications/f0/data-model.md, docs/specifications/f0/implementation-status.md e frontend/README.md.

A baseline completa, status Git, hashes e resultados sanitizados estão em [dev09a-persistence-evidence.json](dev09a-persistence-evidence.json). O inventário permite distinguir alterações DEV anteriores das cinco criações desta tarefa. Proveniência documental: relatórios DEV-02–08D e [contratos DEV-08B](../specifications/f0/dev08b-persistence-contracts.md); documentos históricos não localizados continuam como tal.

AUTH-03: verificador oficial PASS, 52 fontes e manifesto `4819c697b7d12f7ab5cbb1fdfa9cf4c3fd0e98e93b53a60337296cc84036fc29`, preservados. Não se modificou o candidato ou qualquer fonte atestada. D01/D02 continuam consistentes como desenho; a aprovação posterior D03/aplicação consta da DEV-08D, sem reescrever estados históricos dos documentos anteriores.

Não foram encontrados processos relevantes alembic/DEV09/migração concorrentes na inspeção inicial. Havia 23 containers, 14 redes e 174 volumes Docker preexistentes; foram inventariados sem ler environments/credenciais ou ligar às suas bases. O isolamento de execução usa exclusivamente IDs novos desta tarefa, nunca um nome de base existente. A ausência observada de concorrência não é exclusão contra administradores hostis.

## Implementação realizada

| Novo ficheiro | Finalidade |
| --- | --- |
| `scripts/dedicated/dev09a_preflight.py` | Leitor AST, comparação do manifesto, identidade de fixture e orquestrador descartável/cleanup; não emite autoridade nem migra |
| `scripts/dedicated/dev09a_fixture_probe.py` | SQL real exclusivamente em cluster novo/schema dev09a_fixture; TLS, papéis, extensão, ACL e transações |
| `backend/tests/test_dev09a_preflight.py` | 22 casos offline de recusa de destino, leitura AST e limites de autoridade |
| `docs/operations/dev09a-persistence-evidence.json` | Baseline e resultados; inventário técnico, não atestação ou formato de autorização G4 |
| `docs/operations/dev09a-persistence-preflight.md` | Este relatório |

O novo código está fora do âmbito AUTH-03 de 52 fontes e não integra os 27 artefactos históricos. Se for usado futuramente numa cadeia de execução de confiança, necessita de revisão/atestação própria; a evidência atual não lhe concede autoridade.

Reprodução da análise e da fixture, sem migrações:

```bash
python3 -B scripts/dedicated/dev09a_preflight.py
python3 -B scripts/dedicated/dev09a_preflight.py --run-disposable
```

O primeiro comando só lê fontes e devolve STATIC_PASS_EXECUTION_BLOCKED. O segundo cria um **novo** cluster/PKI/identidades e remove-os no final; não reproduz o mesmo system identifier. Exige acesso ao daemon local, openssl e as imagens locais por ID; não instala, faz pull ou build. Não usar esta fixture como base futura de migrações.

## Ambiente nativo final, TLS e isolamento

| Elemento observado | Evidência |
| --- | --- |
| Identificador da execução | `livenet-dev09a-80414e3e0e` |
| Base sintética | `livenet_v2_dev_80414e3e0e` |
| PostgreSQL | 16.15, server_version_num=160015 |
| System identifier | `7700691028849037338` |
| Hostname/SAN TLS | `livenet-dev09a-80414e3e0e-db` |
| SHA256 CA sintética | `6f95255edf131451d81cb72ae81afc09c78a4963803fcd744b7ec048d87b5da6` |
| Imagem PostgreSQL local | `sha256:6a2e324ebe59af6031c4c1cd96c1d5072c2ebc36563d2196365e43b8297c062d` |
| Imagem cliente Python/psycopg local | `sha256:b16b93e9ab02616547158eabe0064475e705207d1a6d7f01af9b50aa25568238` |
| Rede | `livenet-dev09a-80414e3e0e-data`, internal=true, IPv6 desativado |
| Rede ID | `8110580e96a7f05536065a9d652d10a2d756b24a87b53620cd3435d7322b8984` |
| Subnet / endereço DB | `172.29.0.0/16` / `172.29.0.2` |
| Publicação host / interfaces operacionais | Nenhuma porta publicada; apenas rede interna exclusiva; sem rota IPv4 por omissão no cliente |
| Dados | initdb novo em tmpfs; nenhum volume nomeado/anónimo na execução final |
| Membros de dados | Apenas DB e probe próprios, verificados antes de libertar a barreira que permite SQL |

O system identifier foi comparado por dois canais: pg_controldata dentro do container novo e sessão PostgreSQL TLS. A identidade foi vinculada a ID de container/rede, prefixo/base, CA e role; recusaram-se substituições na comparação da fixture. Isto demonstra coerência de observações locais, **não emite uma atestação independente aprovada G2/G4**.

TLS verify-full passou com a CA/hostname certos e falhou com CA errada, hostname errado, ligação sem TLS, base errada e password sintética errada. HBA aceita apenas hostssl para a base sintética/subnet própria. Não foram sondados endereços operacionais: a prova de isolamento usa metadata, wiring e rotas. Backend/HTTP/Caddy não foram iniciados; a imagem de backend foi usada só como cliente Python, com o probe novo montado read-only.

Todos os containers foram identificados por label DEV-09A e IDs novos; sem socket Docker montado no probe/DB, rootfs read-only, capabilities removidas e no-new-privileges. Um auxiliar sem rede teve apenas CAP_CHOWN para dois ficheiros sintéticos novos; o DB correu como UID/GID 70:70. A administração SQL sintética é privilegiada para preparar roles/owner, mas nunca é runtime ou credencial operacional.

**O cluster acima já foi removido.** O seu SID/CA não são identidades autorizadas para DEV-09B nem devem ser reutilizados automaticamente. Qualquer ensaio futuro requer novo alvo e confirmação independente antes de DDL.

## Roles e privilégios: âmbito efetivamente demonstrado

Só foram criadas as roles sintéticas lnv2_dev_admin, lnv2_dev_db_owner, lnv2_dev_migrator, lnv2_dev_runtime e lnv2_dev_inspector, no cluster descartável. db_owner é NOLOGIN; migrator/runtime/inspector são NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION/NOBYPASSRLS/NOINHERIT. Runtime e migrator sem memberships.

| Papel / janela | Direitos testados |
| --- | --- |
| Admin | Apenas a identidade bootstrap/admin sintética conserva poderes administrativos; cria papéis e prepara a fixture |
| Owner NOLOGIN | Ownership separado da base e objetos finais da fixture; login recusado |
| Migrator | USAGE/CREATE apenas no schema de fixture e CREATE temporário na base para instalar btree_gist confiável; sem membership de owner; sem CREATE em public ou CREATEROLE |
| Fecho da janela | CREATE na base revogado após extensão; REASSIGN OWNED apenas dos objetos novos da fixture para NOLOGIN; direitos de schema migrator revogados; leitura de dados, CREATE SCHEMA e SET ROLE owner recusados depois |
| Runtime | SELECT num alvo de leitura, SELECT/INSERT + UPDATE(activity) num alvo de sessões, INSERT-only num alvo audit; row lock permitido só onde há direitos adequados |
| Inspector | Catálogos visíveis; sem leitura dos dados de fixture ou escrita audit |

Foram recusados DDL, TEMP, CREATE ROLE/DB, DROP, SET ROLE owner/migrator/admin, sequences (USAGE/SELECT/UPDATE), escrita no alvo de consulta, UPDATE de coluna protegida, DELETE/TRUNCATE e leitura/alteração de audit. Confirmaram-se persistência entre conexões e rollback conjunto sessão/audit.

A extensão btree_gist estava disponível/trusted; foi instalada e uma constraint EXCLUDE efetivamente rejeitou ranges sobrepostos. Tudo no schema **dev09a_fixture**, sem copiar modelos/tabelas ou ledgers aplicacionais. Este schema é uma fixture independente autorizada, não preparação manual dos schemas do MVP. O fecho/ownership é uma prova de mecânica, não a matriz definitiva de um executor operacional.

**Limite:** não se validaram grants contra o ORM/schema real do MVP, isolamento administrativo de produção, manifesto físico G2 ou recuperação independente. D05 inclui direitos concretos em users/sessions/throttles/audit/resources que só podem ser testados depois de migrações explicitamente autorizadas; não se assume equivalência integral a partir das tabelas de analogia.

## Grafos Alembic e sequência futura

Leitura AST de 14 revisões aplicacionais (incluindo Assign e AnnAssign), sem importar/executar migrações, e uma revisão security. Não há branches/raízes ambíguas nem depends_on cruzado.

```text
base → af62df027d9d → 4f625db33d6d → 38d641dcd780 → da34876e4210
→ ba06dd956da9 → 44e7eb855b5a → 7c4e2a91b605 → 9e1b7c42a630
→ c4a91e7b205d → e65b01a7c230 → f065c01a7230 → f065d01a7230
→ f066a01a7230 [DESTINO MVP] → f067a01a7230 [SÓ AUTH-03 ISOLADO]

security: base → b12b01a7230 [DESTINO MVP INDEPENDENTE]
```

Ledger aplicacional public.alembic_version; security public.alembic_security_version. Security não tem depends_on no grafo; f066 é pré-condição operacional. f066 acrescenta auditoria; f067 acrescenta authorization e é excluído do MVP. ba06/9e1b requerem btree_gist. Head do código não é destino automático. Não se executou upgrade, stamp, SQL offline Alembic, escrita manual de ledger ou criação manual de inventory/audit/security/authorization.

Ordem futura, ainda condicionada:

1. Aprovar executor/perfil e atestação complementar; obter especificações/autoridade faltantes, plano de exclusividade, recuperação e autorização de uso único.
2. Criar novo alvo descartável sem dados; provar identidade/CA/rede/volume/roles independentemente. Os dados desta DEV-09A já não existem.
3. Rever btree_gist, ownership e matriz de grants; conceder só a janela necessária a cada cadeia, mantendo administração/inspeção separadas.
4. Pelo executor autorizado: uma transação/ligação externa, lock, autorização, identidade/origem, aplicação base→f066, verificação e commit; resultado incerto bloqueia novas tentativas.
5. Execução security independente base→b12 com configuração/metadata/ledger próprios, transação exterior e validação de origem/destino/ownership; sem juntar autogeração à aplicação.
6. Handoff e fecho dos poderes temporários; grants D05 revistos, provisionamento sintético por identidade própria e integração real auth/sessões/throttles/audit/inventário.
7. Checker real e manifesto físico aprovados sob gates próprios; readiness 503 até prova válida. Recuperação independente e limpeza comprovadas.

### Comandos exatos DEV-09B: bloqueio demonstrado

**Ainda não existe um comando executável legítimo para migrar o novo perfil DEV.** AUTH-03 fixa livenetv2-auth03-test/livenet_auth03_test/SID histórico e bloqueia upgrade-baseline/upgrade-auth03 antes de I/O. O executor security fixa livenetv2-m12b-test/livenet_m12b_test/SID histórico, tem execution_enabled=False e não fornece uma CLI operacional. Um sim humano genérico não muda estes contratos.

Os parâmetros exatos das futuras chamadas internas ao Alembic são aplicação **f066a01a7230** e security **b12b01a7230**, com config/connection externas próprias. Não se fornece um comando Alembic direto ou uma CLI fictícia como alternativa aos gates. Os nomes das duas operações futuras são base→f066 e base→b12, não head. A tarefa satisfaz a preparação do plano, mas **o requisito de comandos DEV-09B executáveis permanece bloqueado** até definição/revisão/aprovação do executor apropriado.

Comandos seguros disponíveis agora são os dois de preflight acima e o verificador de fontes:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend:scripts/postgres \
.venv/bin/python -B -c 'from auth03_alembic_executor import verify_bundle; print(verify_bundle())'
```

Não iniciar migrações na DEV-09B apenas por estas verificações passarem.

## Executores, F02/G2/G4 e destino dedicado

- AUTH-03: `scripts/postgres/auth03_alembic_executor.py:27–59,136–151,388–418`. Bundle válido; mutações continuam sempre recusadas. Nenhuma autorização autenticada foi implementada.
- Security: `scripts/postgres/m12b_security_migration.py:26–62,125–139,216–225,607–635`; coordenador chama o gate antes das portas. Destino histórico incompatível com o alvo novo; não foi reconfigurado nem ativado.
- F02/G4: `scripts/postgres/g4/contracts.py:491–502` continua TARGET_REFUSED/GATE_ABSENT. Originais/especificações e 28 lacunas G4/L02 permanecem abertos; não se inventou emissor, assinatura ou authority.
- G2: `backend/app/readiness_postgres/adapter.py:23–26,122–125` recusa executor real. Catálogo exato não aceita authorization ou schemas futuros extras; a fixture nunca foi apresentada a G2 como MVP válido.
- Readiness: sem checker real autorizado, fail-closed; HTTP 503 nos testes offline. Nenhum endpoint operacional foi sondado.
- **Lacuna de destino:** DedicatedSettings recusa livenet e formatos/overrides inválidos, mas aceita sintaticamente livenet_v2_prod mesmo num contexto DEV (`backend/app/dedicated.py:77–121`; novo teste :82). Não comprova isolamento/identidade física nem autorização por ambiente. O comparador do harness recusa nomes/roles/CA/SID/container/rede trocados, mas é só proteção de fixture. Corrigir a factory atestada/perfil operacional exige revisão própria e eventual reconciliação de fontes; não foi alterada para ocultar a lacuna.

## Os 27 artefactos externos à cobertura AUTH-03

Hashes completos, commits e âmbito na evidência JSON. Os prefixos abaixo identificam comparações que passaram contra o inventário DEV-08B; **integridade não é atestação**. Todos permanecem fora das 52 fontes. “Necessária” aplica-se antes do uso no âmbito indicado; artefactos HTTP/runtime não são pré-condição para executar Alembic, mas terão de ser atestados para a integração que os inclua.

| Artefacto e finalidade | Proveniência | Integridade SHA256 | Risco / atestação complementar |
| --- | --- | --- | --- |
| `backend/Dockerfile.dedicated` — Empacotamento do backend/cliente Python usado como imagem local; não é runner de migrações. | Local, sem proveniência Git histórica | `bb22c0159380d589…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `backend/Dockerfile.dedicated.dockerignore` — Allowlist do contexto de imagem dedicada; exclusão de material indevido. | Local, sem proveniência Git histórica | `194f3cfbaf961bd1…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `backend/alembic-security.ini` — Seleciona exclusivamente security_migrations e ledger independente. | Git `8a9bd369` | `f43ed86b68499b4f…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `backend/dedicated_wsgi.py` — Seleção explícita TLS/factory; não executa migrações. | Local, sem proveniência Git histórica | `3d96eb601de4cabc…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `backend/gunicorn_container.conf.py` — Bind no namespace e confiança de proxy desativada no servidor. | Local, sem proveniência Git histórica | `3ba395a446ae1b3d…` igual à DEV-08B | MEDIO; necessária antes do uso no seu âmbito |
| `backend/gunicorn_dedicated.conf.py` — Percurso loopback legado preservado; não é configuração inter-container. | Local, sem proveniência Git histórica | `d19934dce2430f08…` igual à DEV-08B | MEDIO; necessária antes do uso no seu âmbito |
| `backend/requirements-container.constraints.txt` — Pins candidatos da cadeia de dependências dedicada. | Local, sem proveniência Git histórica | `d4fe3b495e0e2bf3…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `backend/requirements-container.lock` — Distribuições e hashes do runtime dedicado; não fixa imagem AUTH-03 histórica. | Local, sem proveniência Git histórica | `2bbe864deb5c9f8a…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `backend/requirements-dedicated.txt` — Gunicorn e referência a requirements; sem atestação transitiva completa. | Local, sem proveniência Git histórica | `3be08dd620770b80…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `backend/security_migrations/__init__.py` — Namespace da cadeia security. | Git `8a9bd369` | `b450bd910d335f6e…` igual à DEV-08B | BAIXO; necessária antes do uso no seu âmbito |
| `backend/security_migrations/contract.py` — Metadata restrita, ligação/transação externas e ledger security. | Git `8a9bd369` | `0a29cbc074907a4b…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `backend/security_migrations/env.py` — Recusa SQL offline e ausência de ligação externa; sem engine/fallback. | Git `8a9bd369` | `0bafe798a46070a5…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `backend/security_migrations/versions/b12b01a7230_create_security.py` — Quatro tabelas security; downgrade bloqueado. | Git `8a9bd369` | `3f29c6e630955f25…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `backend/wsgi.py` — Entrada anterior preservada, fora do percurso de migração. | Git `4d85240a` | `d0e730c9f0089d5c…` igual à DEV-08B | MEDIO; necessária antes do uso no seu âmbito |
| `compose.auth03-executor.yaml` — Confinamento e montagem do executor histórico; identidade antiga. | Local, sem proveniência Git histórica | `be9b42028bf11a6e…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `compose.dedicated-tls.yaml` — Overlay verify-full/CA; guards exit78 preservados. | Local, sem proveniência Git histórica | `dfd243af8547243f…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `compose.dedicated.yaml` — Serviços/rede/mounts separados; não autoriza operação. | Local, sem proveniência Git histórica | `ac5f45ee41d491a7…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `infra/dedicated/Caddyfile` — Origem HTTPS e headers substituídos para peer de confiança. | Local, sem proveniência Git histórica | `27a05a9a945af13e…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `infra/dedicated/Dockerfile.caddy` — Construção da imagem proxy. | Local, sem proveniência Git histórica | `d5de76fe5d434bc9…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `infra/dedicated/Dockerfile.caddy.dockerignore` — Contexto allowlist da imagem proxy. | Local, sem proveniência Git histórica | `27f8eb8e845cec69…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `infra/dedicated/dependency-provenance.json` — Registo de resolução/build anterior; evidência não é autoridade. | Local, sem proveniência Git histórica | `48fcd0f1094cd268…` igual à DEV-08B | MEDIO; necessária antes do uso no seu âmbito |
| `scripts/postgres/auth03_executor.Dockerfile` — Imagem antiga por tag/dependências amplas; não copia security_migrations. | Local, sem proveniência Git histórica | `a19453a456d35ced…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `scripts/postgres/auth03_executor.Dockerfile.dockerignore` — Contexto do executor; requer revisão nativa da allowlist. | Local, sem proveniência Git histórica | `4ba70dae2caee52c…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `scripts/postgres/g4/contracts.py` — F02/G4 puros, fronteira sempre recusa execução real. | Local, sem proveniência Git histórica | `04531a6b9f2a33d2…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `scripts/postgres/m12b_security_adapters.py` — Adaptadores de operações administrativas/exclusividade ainda sujeitos à autorização. | Git `4fbb4f0b` | `66e2fa3ea5fccdcb…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `scripts/postgres/m12b_security_coordinator.py` — Coordenação com gate prévio e portas explícitas. | Git `4fbb4f0b` | `33415d4b4c51dbb0…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |
| `scripts/postgres/m12b_security_migration.py` — Plano/transação security, destino fixo e execution_enabled=False. | Git `b2605975` | `c2608a2c8d0391dc…` igual à DEV-08B | ALTO; necessária antes do uso no seu âmbito |

Riscos diretos: a imagem AUTH-03 histórica usa tag base/dependências não inteiramente fixadas e não copia security_migrations; não foi reconstruída nem certificada contra o manifesto novo. As imagens locais serviram apenas à fixture, não a uma execução aprovada. O conjunto complementar ainda precisa de âmbito/autoridade/formato aprovados; este inventário não regenera ou substitui manifestos.

## Testes, correções e limpeza

- **1513 PASS, 0 FAIL, 0 SKIP**, 89,77 s: as 16 suites DEV-08D mais os 22 novos testes DEV-09A. Sockets/psycopg/subprocessos reais bloqueados no processo pytest; -B, plugins/cache desativados e fixtures sintéticas em /tmp.
- Os 22 testes do harness passaram novamente após a correção de armazenamento; não são somados duas vezes ao total. As duas falhas AUTH-03 antigas continuam resolvidas.
- **58 verificações SQL/TLS nativas finais passaram**, incluindo estado vazio antes/depois, não contadas como testes pytest nem prova de migrações.
- O leitor AST inicial não suportava declarações anotadas; foi corrigido apenas no código novo e ganhou teste sem importar migrações.
- Duas tentativas iniciais criaram um volume anónimo cada no auxiliar CHOWN, devido a VOLUME herdado da imagem PG. O controlo global detetou-os. Eram ausentes da baseline, coincidentes com as duas criações do auxiliar, vazios e sem referências; foram removidos pelos IDs exatos após verificação, sem prune. O buffer Docker já tinha truncado os eventos (256 entradas), pelo que não se afirma atribuição por eventos indisponíveis.
- Correção: tmpfs explícito também no auxiliar; cleanup recusa volumes implícitos. Nova prova nativa e comparação exata de inventários passaram. Depois reduziu-se a janela de privilégios da fixture e a prova final de 58 verificações passou.
- Os dois IDs removidos e metadados estão na evidência. Nenhum volume preexistente foi consultado, montado ou removido; somente os dois novos foram inspecionados vazios em read-only antes da remoção.
- Final: **23 containers, 14 redes e 174 volumes anteriores preservados**, IDs/estado/StartedAt sem alteração; zero recursos DEV-09A. PKI/credenciais dos runs, tmpfs e diretórios de teste próprios eliminados. Nenhuma imagem criada/removida, build, pull, publicação de porta ou alteração manual de firewall/routing.

A prova foi concluída com cleanup; não se apresentam as primeiras declarações locais de cleanup como prova de ausência global de volumes. Os resultados SQL iniciais continuaram válidos, mas a limpeza só foi aceite após correção e inventário final.

## Backup anterior e ficheiros sensíveis

O backup original /tmp DEV-08D existia e correspondia a `7a9993faba2af675f46bd53daea96f9e4980624c3ef07f4d5af6cdfdfbe7c326`. Foi preservada cópia byte a byte em:

```text
/home/paulo/projects/livenet-v2/secrets/dev08d-manifest-archive/auth03_executor_integrity.before.json
/home/paulo/projects/livenet-v2/secrets/dev08d-manifest-archive/retention.json
```

Pasta nova 0700; backup conserva modo/owner/grupo/mtime; recibo 0600; git check-ignore passou. **Não foi restaurado.** Retenção sem eliminação automática até existir arquivo substituto revisto e evidência independente de recuperação aprovada. É arquivo inativo de manifesto, não backup PostgreSQL nem autoridade operacional.

Ficheiros sensíveis preexistentes identificados só por nome/modo: secrets/auth03_db_password.txt, secrets/auth03_executor.json e secrets/db_password.txt (0600). Conteúdos não lidos/utilizados. .venv, caches, logs, secrets e chaves temporárias são excluídos da proposta de commits; nenhum ficheiro de segredo real foi criado ou alterado.

## Git, consolidação proposta e reversão

Todos os **294 ficheiros iniciais permanecem byte-identical**, incluindo as quatro alterações locais e o manifesto aprovado. Mesma branch/HEAD/índice, sem staging/commit/push. Cinco novos ficheiros não ignorados listados acima; total final esperado/verificado 299 (202 versionados, 97 não versionados). O arquivo adicional é ignorado e distinguido dos artefactos de código/teste.

Proposta de consolidação futura, sem a executar:

1. Bundle coerente das fontes aprovadas AUTH-03 e manifesto correspondente, incluindo todas as inclusões locais/alterações necessárias ao verificador. Não criar commits intermédios que publiquem um manifesto incompatível com o conjunto de fontes.
2. Empacotamento dedicado e contratos/fixtures/testes offline complementares, por grupos revistos; os artefactos ainda não atestados não passam a aprovados por estarem num commit.
3. Documentação arquitetural/operacional histórica, adendas, decisões e evidências; manter propostas, aprovações e limites distintos.
4. Incremento DEV-09A (harness/probe/testes/relatório/evidência), sujeito à revisão própria; pode ser separado dos grupos anteriores depois de fixar a baseline necessária.

Usar listas explícitas de paths após revisão; nunca git add ., secrets, PKI, caches ou temporários. Recuperar originais em falta antes de afirmar aprovação de contratos que não foram localizados. A evidência tem o inventário exato dos 92 paths inicialmente não versionados e hashes, mas não armazena os seus bytes: um checkout de HEAD sozinho continua insuficiente para reproduzir todo o trabalho acumulado.

Reversão desta etapa: recursos descartáveis já removidos, sem base persistente a reverter. Para abandonar implementação, rever/remover somente os cinco ficheiros novos DEV-09A; preservar integralmente o trabalho anterior e o arquivo de backup conforme retenção. Não restaurar o manifesto antigo, executar downgrade security, editar ledgers ou usar reset/clean. Uma futura falha durante commit de migração exige recuperação independente e estado bloqueado, não retry automático; isso não foi ensaiado aqui.

## Bloqueios e decisão sobre DEV-09B

**Não recomendo autorizar migrações DEV-09B neste estado.** Está demonstrado o ambiente técnico, não a legitimidade do percurso de execução.

São necessárias decisões/autorizações concretas para:

1. Definir/rever perfil e executor para novo alvo DEV, incluindo validação real de destino por ambiente e TLS; preservar os destinos/gates históricos, sem simples substituição de constantes.
2. Aprovar âmbito e artefactos de atestação complementar, imagem/dependências e fonte do mecanismo de autorização; resolver especificações originais ausentes ou aprovar explicitamente uma decisão substituta, sem inventar autoridade.
3. Rever contratos de janela administrativa, inspeção, ownership/grants, exclusividade, recuperação e resultado incerto; implementar/testar o percurso autorizado sem o ativar implicitamente.
4. Só depois autorizar um novo ensaio descartável: criação, identidade independente confirmada, operação base→f066 e depois base→b12, origem/destino exatos, locks, transações externas, evidência e limpeza. Nunca head/stamp ou Alembic direto como contorno.

Critérios DEV-09A demonstrados: cluster novo/tmpfs, TLS/identidade/isolamento, grafos/destinos, análise de executores, privilégios em fixtures, inventário complementar, regressões, cleanup, preservação Git e arquivo. **Pendentes:** recusa operacional completa de destinos e comandos de migração legítimos DEV-09B, dependentes dos bloqueios acima. Nenhum destes foi ocultado por teste verde ou corrigido fora do âmbito.
