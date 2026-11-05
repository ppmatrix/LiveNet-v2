# LiveNet v2 — DEV-08: propostas de desbloqueio da persistência

Data: 2026-10-25. Ambiente: progbox. Repositório: `/home/paulo/projects/livenet-v2`.

**Estado: três propostas pendentes de aprovação humana.** Este documento não constitui autorização de DDL, aprovação de fontes, abertura de gates ou ativação operacional.

## Resumo executivo

Recomenda-se: (D01) bases por ambiente em clusters independentes do LiveNet v1 e entre si; (D02) MVP com aplicação em `f066a01a7230` e security independente em `b12b01a7230`, reservando `f067a01a7230` ao perfil AUTH-03 num destino separado; (D03) reconciliação AUTH-03 em duas aprovações, primeiro o processo de revisão e depois um candidato concreto e imutável.

A análise confirma 31 entradas no manifesto, contra 52 fontes exigidas atualmente: 21 ausentes, quatro hashes divergentes e zero entradas excedentes. Os quatro hashes atuais correspondem ao commit M1.2A; 12 das ausências têm proveniência Git e nove são ficheiros locais. Nenhuma destas constatações equivale a aprovação de segurança.

A recomendação D02 preserva o catálogo exato do G2. Aplicar `f067` ao MVP introduziria `authorization` e violaria esse catálogo, além da revisão exigida pela readiness. Criar antecipadamente os seis schemas DAT-05A também violaria esse conjunto exato: propõe-se documentar a materialização por fases.

Aprovar estas propostas não torna a persistência operacional. Faltam implementação revista dos destinos e executores, atestação de fontes, autorizações de execução, privilégios reais, checker real autorizado e demonstração de recuperação independente.

## Método, evidência e limites

**Factos** abaixo resultam de leitura dos ficheiros, comparação SHA256 e proveniência Git. Foi executado apenas o reconciliador documental read-only `python3 -B scripts/dedicated/dev07_reconcile.py`, sem testes, Docker, ligações PostgreSQL ou mudanças de configuração. As sequências operacionais descritas são **propostas futuras condicionadas**, não operações realizadas.

A análise incide exclusivamente nos três bloqueios. Resultados operacionais DEV-05B/06/07 são evidência histórica descrita em `docs/operations/dev06-postgresql-integration.md` e `docs/operations/dev07-react-integration.md`; não foram repetidos nem provam autenticação/inventário persistentes operacionais. Os contratos ausentes e lacunas registados nas etapas anteriores continuam abertos. Não se reconstrói aprovação dos originais D01–D52 ou dos capítulos não localizados.

## DEV-08-D01 — Identidade PostgreSQL por ambiente

### 1. Problema exato

DAT-05A documenta a base literal `livenet`, mas o perfil dedicado recusa esse nome. Trocar apenas o nome não identifica um cluster seguro e pode atingir instalações existentes, incluindo v1. Os executores de migração também fixam projetos, nomes e identidades físicas próprios; não são automaticamente compatíveis com um nome novo.

### 2. Evidências comprovadas

- `docs/specifications/f0/data-model.md:306–329`: DAT-05A marcado como aprovado, base `livenet`, seis schemas e separação lógica. O estado documental não substitui o original da aprovação humana.
- `backend/app/dedicated.py:79–109`: configuração estrita, `ENVIRONMENT=production`, recusa de `livenet` e origem HTTPS fixa.
- `backend/dedicated_wsgi.py:75–89` e `backend/app/postgres_tls.py:23–52`: variante TLS exige `verify-full`, CA explícita e ficheiro regular com ownership/permissões controlados.
- `compose.dedicated.yaml:27–65`: configuração privada do backend, perfil fechado e nome PostgreSQL por `DEV04_DB_NAME`; identidade bootstrap distinta do runtime.
- `scripts/dedicated/preflight.py:99–115`: coerência entre configuração, destino Compose, roles distintas e TLS.
- `docs/specifications/f0/auth03-integration-preparation.md:48–63`: identidade física e controlo independente; clones físicos podem preservar o system identifier.
- `scripts/postgres/auth03_alembic_executor.py:27–43` e `scripts/postgres/m12b_security_migration.py:28–62`: contratos de identidade específicos e distintos, execução mutante bloqueada.

**Não verificado:** nomes já usados, DNS, system identifiers, OIDs, memberships e privilégios de quaisquer clusters operacionais. Não foi consultado PostgreSQL.

### 3. Opção recomendada — proposta

| Ambiente | Base proposta | Cluster / fronteira |
| --- | --- | --- |
| DEV, progbox | `livenet_v2_dev` | Cluster v2 DEV próprio, sem partilha com v1 ou outros ambientes |
| STAGING, VM Proxmox | `livenet_v2_staging` | Cluster próprio e credenciais, rede, persistência e backups independentes |
| PROD-VM; posteriormente PROD-K8S | `livenet_v2_prod` | Cluster de produção próprio; migração VM→K8S controlada, sem dois primários graváveis independentes |

Os nomes são uma proposta, não uma reserva ou confirmação de ausência de colisões. Ensaios descartáveis usam nomes exclusivos `livenet_v2_dev_<runid>`, novo initdb e recursos exclusivos; não usam automaticamente as bases canónicas.

A identidade autorizada deve vincular ambiente, base, role, endpoint TLS/certificado, CA, system identifier e proveniência independente do cluster/volume/rede/projeto/imagem. System identifier isolado ou nome isolado são insuficientes. Clones/restauros ficam em quarentena até reatestação; não se presume que um clone seja um novo cluster independente.

Cada ambiente terá rede, volumes, credenciais, chaves CSRF/sessão e fronteira de confiança TLS próprias. Certificados devem identificar o endpoint efetivamente usado; um alias Docker repetido só é aceitável com redes e confiança CA independentes e comprovadas. Não se escolhem DNS/IP operacionais nesta decisão.

**Schemas:** conservar o modelo lógico inventory, discovery, monitoring, operations, security e audit, mas materializar no primeiro MVP apenas inventory, audit e security, mais os catálogos/ledgers previstos. discovery, monitoring e operations ficam para fase posterior, mesmo vazios; authorization existe exclusivamente no destino AUTH-03 proposto em D02. Isto exige uma adenda explícita à materialização inicial DAT-05A, sem fingir compatibilidade integral com o texto atual.

**Roles propostas, distintas por ambiente:** substituir `<env>` por `dev`, `staging` ou `prod`; sem memberships entre ambientes.

| Role proposta | Função e limite |
| --- | --- |
| `lnv2_<env>_db_owner` | NOLOGIN; ownership da base, sem uso pela aplicação |
| `lnv2_<env>_inventory_owner` | NOLOGIN; ownership dos objetos inventory |
| `lnv2_<env>_audit_owner` | NOLOGIN; ownership de audit |
| `lnv2_<env>_security_owner` | NOLOGIN; ownership security, independente do runtime |
| `lnv2_<env>_migrator` | LOGIN controlado, NOINHERIT; apenas memberships e SET ROLE necessários e aprovados para cada cadeia |
| `lnv2_<env>_runtime` | LOGIN; sem ownership, administração ou memberships de owners; somente grants D05 revistos |
| `lnv2_<env>_inspector` | LOGIN; leitura apenas dos catálogos/ledgers necessários ao checker, sem leitura geral dos dados |
| `lnv2_<env>_admin` | Administração/provisionamento separado e auditado; nunca montado no backend |

Para DEV, por exemplo, os nomes são `lnv2_dev_db_owner`, `lnv2_dev_inventory_owner`, `lnv2_dev_audit_owner`, `lnv2_dev_security_owner`, `lnv2_dev_migrator`, `lnv2_dev_runtime`, `lnv2_dev_inspector` e `lnv2_dev_admin`; a mesma expansão aplica-se a staging/prod. A matriz final de ownership, grants e direitos sobre os dois ledgers exige revisão antes de criar roles. Não se atribuem agora superuser, CREATEDB, CREATEROLE, BYPASSRLS ou permissões administrativas ao runtime.

### 4. Alternativas consideradas

- Manter `livenet` em clusters separados: respeitaria o literal DAT-05A, mas exigiria alterar a recusa dedicada e provar destinos com outro contrato. Menos seguro perante a colisão histórica; não recomendado.
- Bases por ambiente no mesmo cluster: isolamento lógico insuficiente para a separação completa pedida; não recomendado.
- Alterar apenas o nome: não resolve a identidade física, credenciais nem a confiança no destino; rejeitado.

### 5. Justificação técnica

Separar nome e identidade verificável permite reutilizar a aplicação sem transportar pressupostos de uma fixture ou do v1. As factories já aceitam configuração explícita, mas os executores históricos têm identidades fixas que precisam de novos perfis revistos, não de substituição global de strings.

### 6. Impacto na arquitetura e segurança

Adenda DAT-05A necessária para nomes por ambiente e materialização por fases. Preservam-se schemas lógicos, HTTPS, mesma origem, CSRF, cookies, proxy e isolamento de sessões. `ENVIRONMENT=production` continua a ser o modo seguro Flask mesmo em DEV/STAGING; não deve ser usado como seletor de identidade do deployment. Não se introduz nesta etapa uma variável nova ou um mecanismo genérico de desbloqueio.

### 7. Ficheiros afetados futuramente

`docs/specifications/f0/data-model.md`; contratos de destinos em `docs/specifications/f0/`; `backend/app/dedicated.py` apenas se a revisão demonstrar necessidade; `backend/dedicated_wsgi.py`; `compose.dedicated.yaml` e `compose.dedicated-tls.yaml`; `scripts/dedicated/preflight.py`; perfis revistos em `scripts/postgres/`; testes dos mesmos e exemplos documentais privados de configuração.

Coordenar `DATABASE_NAME` do JSON privado com `DEV04_DB_NAME` no Compose e com a identidade atestada. Não alterar automaticamente fixtures históricas, system identifiers, configurações protegidas ou instalações existentes.

### 8. Plano após aprovação

1. Documentar adenda e contratos concretos de cada destino; verificar colisões sem usar credenciais runtime para administração.
2. Rever matriz de ownership, permissões e isolamento, incluindo nomes reais, endpoint/CA e atestação independente.
3. Implementar perfis explícitos e testes offline de recusa de v1, outro ambiente, base/role/TLS/projeto divergentes e destinos ambíguos.
4. Submeter o destino descartável concreto e o mecanismo de execução à autorização posterior. Nenhuma criação persistente decorre desta aprovação.

### 9. Critérios de aceitação

Nomes e identidades documentados sem colisões conhecidas; fronteiras por ambiente comprovadas; bases proibidas continuam recusadas; runtime sem poderes administrativos; TLS verify-full e segredos privados preservados; preflight recusa destinos cruzados; zero provisionamento ou migração na factory; nenhuma mudança em F02/G2/G4.

### 10. Riscos e reversão

Naming não garante isolamento; restores podem preservar identidade física; roles propostas ainda não tiveram grants reais validados. Antes de execução, rollback é reversão apenas das alterações novas e identificadas, preservando trabalho local. Depois de ensaio autorizado, remover apenas recursos descartáveis cuja propriedade foi comprovada. Remoção/renomeação de uma base persistente exige outro plano e aprovação; não faz parte desta decisão.

### 11. Aprovação humana

**Aprova a D01 com `livenet_v2_dev`, `livenet_v2_staging` e `livenet_v2_prod`, clusters e identidades independentes do v1 e entre ambientes, roles separadas e adenda DAT-05A para nomes por ambiente e materialização por fases, sem autorizar criação de bases ou alterações operacionais?**

## DEV-08-D02 — Destinos explícitos das duas cadeias Alembic

### 1. Problema exato

O head aplicacional é `f067a01a7230`, enquanto a readiness MVP exige `f066a01a7230` e security `b12b01a7230`. `f067` cria outro schema e não instala autenticação. Selecionar head ou mudar uma string da readiness ocultaria uma divergência estrutural.

### 2. Evidências: grafos efetivamente inspecionados

Grafo aplicacional linear, derivado de revision/down_revision das 14 fontes atuais:

| Revisão | Predecessora | Fonte |
| --- | --- | --- |
| `af62df027d9d` | base (raiz) | `backend/migrations/versions/af62df027d9d_create_inventory_resources_baseline.py` |
| `4f625db33d6d` | `af62df027d9d` | `backend/migrations/versions/4f625db33d6d_create_inventory_resource_identifiers.py` |
| `38d641dcd780` | `4f625db33d6d` | `backend/migrations/versions/38d641dcd780_create_inventory_resource_relations.py` |
| `da34876e4210` | `38d641dcd780` | `backend/migrations/versions/da34876e4210_create_inventory_groups.py` |
| `ba06dd956da9` | `da34876e4210` | `backend/migrations/versions/ba06dd956da9_create_inventory_group_memberships.py` |
| `44e7eb855b5a` | `ba06dd956da9` | `backend/migrations/versions/44e7eb855b5a_create_inventory_group_rules.py` |
| `7c4e2a91b605` | `44e7eb855b5a` | `backend/migrations/versions/7c4e2a91b605_create_inventory_tags.py` |
| `9e1b7c42a630` | `7c4e2a91b605` | `backend/migrations/versions/9e1b7c42a630_create_inventory_resource_tags.py` |
| `c4a91e7b205d` | `9e1b7c42a630` | `backend/migrations/versions/c4a91e7b205d_create_inventory_policies.py` |
| `e65b01a7c230` | `c4a91e7b205d` | `backend/migrations/versions/e65b01a7c230_create_inventory_policy_versions.py` |
| `f065c01a7230` | `e65b01a7c230` | `backend/migrations/versions/f065c01a7230_create_inventory_policy_assignments.py` |
| `f065d01a7230` | `f065c01a7230` | `backend/migrations/versions/f065d01a7230_create_inventory_effective_configs.py` |
| `f066a01a7230` | `f065d01a7230` | `backend/migrations/versions/f066a01a7230_create_audit_events_baseline.py` |
| `f067a01a7230` | `f066a01a7230` | `backend/migrations/versions/f067a01a7230_create_authorization_integrity_anchors.py` |

Grafo security independente: base → `b12b01a7230`, sem depends_on aplicacional, em `backend/security_migrations/versions/b12b01a7230_create_security.py:12–19`. Esta migração cria `security.local_users`, `login_sessions`, `global_role_grants` e `login_throttles` (:20–78). Downgrade é explicitamente recusado (:82–83).

- `backend/migrations/versions/f066a01a7230_create_audit_events_baseline.py:12–22`: acrescenta audit.events após as 12 tabelas de inventário.
- `backend/migrations/versions/f067a01a7230_create_authorization_integrity_anchors.py:12–22`: acrescenta authorization e respetivas âncoras; não cria users/sessões.
- `backend/security_migrations/contract.py:10–21,52–63`: metadata independente, versão security própria em `public.alembic_security_version`, ligação PostgreSQL externa e transação ativa.
- `backend/migrations/env.py:46–64`: percurso externo e validações específicas AUTH-03; existe fallback legado de engine, que não deve ser usado para contornar o percurso controlado.
- `backend/app/core/model_registry.py:3–21`: modelos inventory/audit/security; não regista as âncoras authorization.
- `backend/app/readiness.py:105–132`: checker ausente ou evidência inválida → 503; exige revisões exatas f066/b12.
- `backend/app/readiness_postgres/evaluate.py:63–104`: G2 exige conjunto exato de schemas e relações; authorization e os schemas futuros DAT-05A não cabem nesse catálogo.
- `backend/app/readiness_postgres/adapter.py:23–26,122–125`: executor real desativado e fronteira offline explícita. Compatibilidade de catálogo não equivale a readiness operacional.
- `backend/migrations/versions/ba06dd956da9_create_inventory_group_memberships.py:23` e `backend/migrations/versions/9e1b7c42a630_create_inventory_resource_tags.py:23`: instalação idempotente de `btree_gist`, necessária às constraints de exclusão. As funções/objetos da extensão e as ACL também integram a revisão do catálogo; não autorizar extensões arbitrárias.

**Proveniência:** f067 e os artefactos dedicados são locais, não versionados. A migração security está versionada; última alteração em `8a9bd369ebe4563286509bb1b154f255165db2df` (`feat(security): prepare M1.2B isolated Alembic migrations`). Nenhuma destas proveniências equivale a autorização de execução. O manifesto AUTH-03 inclui o âmbito migrations aplicacional, mas não a cadeia security. Não foi localizado um original de decisão que autorize reconciliar globalmente f066/f067 ou abrir os gates atuais. A proposta seguinte é nova e explicitamente pendente.

### 3. Opção recomendada — destinos por perfil

| Perfil futuro | Aplicação | Security | Limite |
| --- | --- | --- | --- |
| MVP DEV descartável e depois DEV persistente | `f066a01a7230` | `b12b01a7230` | Só após autorização específica do destino e execução |
| MVP STAGING | `f066a01a7230` | `b12b01a7230` | Cluster independente; não promover dados DEV |
| MVP PROD-VM / posterior PROD-K8S | `f066a01a7230` | `b12b01a7230` | Alvo arquitetural; promoção/recuperação ainda não autorizadas |
| Validação AUTH-03 isolada | `f067a01a7230` após f066 | Não aplicada por defeito | Contrato próprio; fora da readiness MVP e sem partilha do destino |
| Perfil legado | Preservar comportamento existente | Preservar | Não redirecionar implicitamente |

Manter f067 no histórico e a cadeia security separada. Nunca usar `head`, stamp ou escrita manual dos ledgers como reconciliação. O head de código e a revisão autorizada de um perfil são conceitos distintos.

O destino histórico AUTH-03 é `livenet_auth03_test`, projeto `livenetv2-auth03-test`, system identifier `7698845469694267426` (`scripts/postgres/auth03_alembic_executor.py:28–35`). Não é uma autorização para usar esse cluster, nem deve ser reutilizado automaticamente para os novos ambientes. O executor security também fixa identidade própria e tem execução desativada (`scripts/postgres/m12b_security_migration.py:28–62,216–225`). É necessário um contrato novo e revisto para um alvo descartável concreto.

### 4. Dependências funcionais

- Inventário: 12 tabelas aplicacionais e autorização via identidade autenticada; `backend/app/security/access.py:20–56` reutiliza o mecanismo de sessões de inventário e roles reader/editor.
- Autenticação e sessões: precisam das quatro tabelas security. Login consulta/atualiza throttles antes de validar credenciais, cria sessão e auditoria; `backend/app/security/service.py:93–159`.
- Auditoria: audit.events em f066 e eventos transacionais em `backend/app/audit/service.py:1–23`; não pode ser substituída por logs de diagnóstico.
- D05 pode manter inventário só de leitura, mas autenticação não é read-only na BD: sessões, throttles e auditoria exigem escritas restritas. Política de grants em `backend/app/readiness_postgres/policy.py:18–40`.
- authorization de f067 é infraestrutura das âncoras AUTH-03, não substitui role grants nem a autenticação M1.2A.

### 5. Alternativas consideradas

- Uniformizar tudo em f067: exige rever catálogo G2, objetos, ownership/ACL, atestação, política e readiness; não basta mudar revisão. Escopo maior e desnecessário para o primeiro MVP.
- Separar futuramente authorization numa terceira cadeia: exige ADR e plano de evolução sem reescrever revisões aplicadas. Não executar nesta fase.
- Usar f066 sem security: não permite autenticação/sessões persistentes; rejeitado como MVP autenticado.
- Forçar readiness positiva ou usar head: rejeitado.

### 6. Justificação e impacto de segurança

O par f066/b12 preserva os objetos exigidos atualmente e reduz a mudança de contrato. Não demonstra, por si, ACL corretas, executor real autorizado ou operação. A adenda de materialização por fases D01 é necessária. Mantêm-se F02, G2, G4, autoria e validação de evidências, transações externas, separação de privilégios e factory sem escritas PostgreSQL.

### 7. Ficheiros afetados futuramente

Documentação de destinos e `docs/specifications/f0/data-model.md`; contratos/perfis revistos dos executores em `scripts/postgres/`; configuração Alembic externa para cada cadeia; testes de seleção de revisão e catálogo. Preservar fontes históricas em `backend/migrations/versions/` e `backend/security_migrations/versions/`. Qualquer integração real do checker ou autorização de execução exige tarefa separada, revisão dos contratos e autorização específica; não introduzir flags genéricas.

### 8. Sequência exata proposta para preparação descartável, após aprovações

1. Aprovar D01/D02 e o bundle concreto D03; rever previamente mecanismo de execução, gate aplicável e contrato do alvo descartável. Aprovar identidade, ownership, grants e plano de limpeza. Com os gates atuais fechados, parar aqui.
2. Criar apenas depois dessa autorização um PostgreSQL 16 novo, vazio e descartável, com initdb próprio, TLS verify-full, recursos/CA/credenciais próprios. Confirmar identidade por evidência independente e conexão administrativa autorizada. Não pré-criar schemas aplicacionais nem ledgers; não usar bases persistentes. Rever previamente disponibilidade/versão de `btree_gist`, identidade autorizada a instalá-la e ownership/ACL dos seus objetos; as revisões ba06/9e1b invocam CREATE EXTENSION IF NOT EXISTS. Não conceder esse poder ao runtime; se o mecanismo aprovado não conseguir cumprir este pré-requisito, parar antes da migração.
3. Por ligação externa controlada e transação explícita, verificar alvo/fontes, adquirir lock previsto e aplicar exclusivamente a cadeia aplicacional **base→af62→4f62→38d6→da34→ba06→44e7→7c4e→9e1b→c4a9→e65b→f065c→f065d→f066**, usando os IDs completos da tabela. O Alembic escreve o seu ledger; não o editar. Verificar catálogo, constraints e revisão f066 antes do commit pelo mecanismo aprovado.
4. Numa execução independente com configuração/metadata/ledger security próprios, abrir ligação externa e transação ativa, validar o estado f066 e aplicar **base→b12b01a7230**. Verificar quatro tabelas security, constraints/FKs, ledger `public.alembic_security_version` e ownership previstos antes do commit. Falha deve abortar/rollback da transação, não produzir stamp.
5. Aplicar somente os grants D05 aprovados, com runtime sem ownership ou capacidade de criar contas. Provisionar utilizador sintético, reader grant e dados de inventário por identidade de preparação separada e explicitamente autorizada; nunca pela factory/runtime. Confirmar persistência de sessão/throttle/audit e leitura de inventário com o mesmo mecanismo de sessões.
6. Validar invariantes de destino, TLS, role, catálogo, revisão e privilégios. Só um checker real previamente revisto e autorizado, com todos os gates satisfeitos, poderá produzir readiness 200. Até lá, 503 é o resultado correto; não introduzir checker positivo simulado.
7. Para AUTH-03, usar **outra base descartável**, com contrato e autorização próprios: aplicar base→f066 e depois f066→f067, verificando cada revisão pelo seu executor autorizado. Não aplicar security por defeito, não misturar dados com MVP e não chamar o catálogo MVP de G2 para aceitar authorization.
8. Recolher evidências sanitizadas; encerrar/remover apenas os recursos novos identificados pelo ensaio e conforme autorização. Não transportar esta sequência para produção sem promoção, backup e recuperação revistos.

Estes passos não são executáveis com os gates atuais e não constituem instrução para os contornar por Alembic direto.

### 9. Critérios de aceitação

Perfis selecionam IDs completos e recusam destino/revisão errados; grafos intactos e sem merges/stamps artificiais; ledgers independentes; catálogo MVP exato sem authorization; testes offline mantêm falhas negativas; ensaio real posterior prova constraints, ownership, grants, sessões/auditoria e ausência de DDL no arranque; 503 quando falta qualquer evidência. Nenhuma aprovação desta decisão autoriza modificar o checker ou gates.

### 10. Riscos e reversão

Ferramentas/CI podem pressupor head; devem verificar o destino do perfil, não eliminá-lo do histórico. A cadeia security versionada necessita atestação própria; f067 local necessita revisão explícita de proveniência e aprovação antes de execução. Não usar downgrade security, que é recusado. Rollback de ensaio: transação abortada ou descarte apenas do alvo novo autorizado. Para dados persistentes, recuperação de backup validado requer plano independente; nunca corrigir ledgers à mão.

### 11. Aprovação humana

**Aprova a D02 com MVP em f066a01a7230 + security b12b01a7230 e AUTH-03 em f067a01a7230 num alvo isolado, preservando histórico, catálogo G2 e cadeias independentes, sem autorizar agora migrações nem abertura de gates?**

## DEV-08-D03 — Reconciliação AUTH-03 com revisão de fontes

### 1. Problema exato

O manifesto não corresponde ao conjunto de fontes exigido atualmente. A verificação falha antes de alguns controlos posteriores. Proveniência Git explica parte da divergência, mas não comprova aprovação das fontes ou do manifesto.

### 2. Evidência e resultado atual

- Manifesto: `scripts/postgres/auth03_executor_integrity.json`, SHA256 **`7a9993faba2af675f46bd53daea96f9e4980624c3ef07f4d5af6cdfdfbe7c326`**; 31 entradas.
- Verificador: `scripts/postgres/auth03_alembic_executor.py:136–151`. Espera exatamente todos os .py de backend/app e backend/migrations, mais backend/alembic.ini, backend/requirements.txt e o próprio executor. Hoje: 52 entradas, 21 ausentes, zero excedentes e quatro hashes divergentes.
- Gatilho de mutações continua fechado em `scripts/postgres/auth03_alembic_executor.py:56–59`; nenhuma variável/token abre DDL nesta etapa.
- `scripts/postgres/tests/test_auth03_alembic_executor.py:374–394`: os dois casos positivos históricos esperam bundle válido antes da adulteração/lock. A DEV-07 registou as duas falhas e a reprodução na baseline. Não foram executados nesta DEV-08.
- Evidência auxiliar: `docs/operations/dev07-contract-evidence.json` e leitura atual via `scripts/dedicated/dev07_reconcile.py`.

### 3. Lista exata das 21 entradas ausentes e classificação individual

**L** significa proveniência legítima comprovada quanto aos bytes versionados, **não aprovação de inclusão/execução**. **P** significa pendente de aprovação individual; fonte local disponível, sem commit/atestação Git demonstráveis. A autoria/aprovação original dos nove artefactos locais não pode ser estabelecida apenas por relatórios anteriores.

| # | Entrada ausente | Proveniência atual | Classificação |
| --- | --- | --- | --- |
| 1 | `backend/app/dedicated.py` | Não versionado; sem commit Git demonstrável | P: pendente de aprovação individual |
| 2 | `backend/app/inventory/access.py` | `24ea3601b36423d2cd0f68b6a1e07619e3377b3e`; igual a HEAD | L: proveniência legítima comprovada; inclusão pendente |
| 3 | `backend/app/inventory/routes.py` | `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`; igual a HEAD | L: proveniência legítima comprovada; inclusão pendente |
| 4 | `backend/app/inventory/schemas.py` | `24ea3601b36423d2cd0f68b6a1e07619e3377b3e`; igual a HEAD | L: proveniência legítima comprovada; inclusão pendente |
| 5 | `backend/app/inventory/service.py` | `24ea3601b36423d2cd0f68b6a1e07619e3377b3e`; igual a HEAD | L: proveniência legítima comprovada; inclusão pendente |
| 6 | `backend/app/postgres_tls.py` | Não versionado; sem commit Git demonstrável | P: pendente de aprovação individual |
| 7 | `backend/app/readiness.py` | Não versionado; sem commit Git demonstrável | P: pendente de aprovação individual |
| 8 | `backend/app/readiness_postgres/__init__.py` | Não versionado; sem commit Git demonstrável | P: pendente de aprovação individual |
| 9 | `backend/app/readiness_postgres/adapter.py` | Não versionado; sem commit Git demonstrável | P: pendente de aprovação individual |
| 10 | `backend/app/readiness_postgres/evaluate.py` | Não versionado; sem commit Git demonstrável | P: pendente de aprovação individual |
| 11 | `backend/app/readiness_postgres/policy.py` | Não versionado; sem commit Git demonstrável | P: pendente de aprovação individual |
| 12 | `backend/app/readiness_postgres/queries.py` | Não versionado; sem commit Git demonstrável | P: pendente de aprovação individual |
| 13 | `backend/app/security/__init__.py` | `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`; igual a HEAD | L: proveniência legítima comprovada; inclusão pendente |
| 14 | `backend/app/security/access.py` | `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`; igual a HEAD | L: proveniência legítima comprovada; inclusão pendente |
| 15 | `backend/app/security/csrf.py` | `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`; igual a HEAD | L: proveniência legítima comprovada; inclusão pendente |
| 16 | `backend/app/security/errors.py` | `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`; igual a HEAD | L: proveniência legítima comprovada; inclusão pendente |
| 17 | `backend/app/security/models.py` | `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`; igual a HEAD | L: proveniência legítima comprovada; inclusão pendente |
| 18 | `backend/app/security/policy.py` | `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`; igual a HEAD | L: proveniência legítima comprovada; inclusão pendente |
| 19 | `backend/app/security/routes.py` | `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`; igual a HEAD | L: proveniência legítima comprovada; inclusão pendente |
| 20 | `backend/app/security/service.py` | `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`; igual a HEAD | L: proveniência legítima comprovada; inclusão pendente |
| 21 | `backend/app/trusted_proxy.py` | Não versionado; sem commit Git demonstrável | P: pendente de aprovação individual |

Totais: 12 ficheiros versionados, todos iguais a HEAD; nove ficheiros locais. Para os nove P, o historial documental DEV-02 a DEV-07 é contexto de origem alegada, não atestação independente. A origem aprovada permanece **não comprovada**; não se classifica código como malicioso sem evidência.

### 4. Quatro hashes divergentes, proveniência e classificação

#### D03-H1 — `backend/app/__init__.py`

- SHA256 esperado no manifesto: `74c51facab8fd44eacc4260429c6182ea53cd6f30bf8715f633b0ccd334fd0b2`.
- SHA256 atual: `0b5d3abe007956211c0bd8167641a991388f9dd0a50d6873124e91c0ed001862`.
- Última alteração Git: `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`; bytes atuais iguais a HEAD.
- Hash esperado localizado no commit: `4d85240af69c2e43b078623e892358d0e0dad6cc`.
- Classificação: **L, proveniência legítima comprovada em Git; substituição no manifesto pendente de aprovação**. Não demonstra aprovação arquitetural nem de segurança.

#### D03-H2 — `backend/app/config.py`

- SHA256 esperado no manifesto: `1801c76af1d3f7bdfcc30b831883ac0b1e36d66ccf92886192ad5d5d6d72fbbd`.
- SHA256 atual: `05e82252427e37e47bf0e40162f1377e95a26a0297d6725261df83266c2535f9`.
- Última alteração Git: `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`; bytes atuais iguais a HEAD.
- Hash esperado localizado no commit: `4d85240af69c2e43b078623e892358d0e0dad6cc`.
- Classificação: **L, proveniência legítima comprovada em Git; substituição no manifesto pendente de aprovação**. Não demonstra aprovação arquitetural nem de segurança.

#### D03-H3 — `backend/app/core/model_registry.py`

- SHA256 esperado no manifesto: `28419b14eabd1d041c1ba21e1fb3a4466522910c474c4eeb6e15f141374bdeb6`.
- SHA256 atual: `6b9db8825e03e894b4f07870459c2ad64cf14687e1abfcddc255bca77a0efb19`.
- Última alteração Git: `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`; bytes atuais iguais a HEAD.
- Hash esperado localizado no commit: `9069aa39913e9be9b87f136ed07acb1992f252f7`.
- Classificação: **L, proveniência legítima comprovada em Git; substituição no manifesto pendente de aprovação**. Não demonstra aprovação arquitetural nem de segurança.

#### D03-H4 — `backend/requirements.txt`

- SHA256 esperado no manifesto: `70820b980a6e044ab90cb8d59cef38a6ac8d905faeeac0a24a9ed656196c4c04`.
- SHA256 atual: `aba67440c5f8caf5d3acb0f7aeee7afcaab5afdad4cab0760f90cde7d818bc6c`.
- Última alteração Git: `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`; bytes atuais iguais a HEAD.
- Hash esperado localizado no commit: `07bd81799c1fd97e78772f65394d806b897bd9bf`.
- Classificação: **L, proveniência legítima comprovada em Git; substituição no manifesto pendente de aprovação**. Não demonstra aprovação arquitetural nem de segurança.


**Prova Git M1.2A:** commit completo `e02ba8a13df2ec6de2aadceecd4c24eed42a4cbd`, assunto `feat(security): implement M1.2A local authentication and RBAC`. Os quatro conteúdos atuais são iguais aos objetos correspondentes desse commit e a HEAD. Oito módulos security e inventory/routes.py ausentes também têm última alteração nesse commit; os outros três ficheiros inventory ausentes vêm de `24ea3601b36423d2cd0f68b6a1e07619e3377b3e` (M1.1).

Os hashes esperados são localizáveis em commits anteriores, como individualizado acima. Isto sustenta a **inferência** de manifesto desatualizado relativamente à evolução M1.2A; não prova quando, por quem ou com que aprovação o manifesto original foi constituído. Não foi demonstrada alteração de segurança não autorizada; também não foi demonstrada aprovação destas substituições.

### 5. Impacto funcional e limites de cobertura

- app/__init__.py e config.py: integração/configuração da autenticação; recuar cegamente pode retirar proteções.
- model_registry.py: registo de modelos security; requirements.txt: dependências da implementação M1.2A.
- security/*: autenticação, autorização, sessões, CSRF, cookies e persistência de grants/throttles; inventory/*: acesso e contratos REST partilhados.
- dedicated/proxy/TLS/readiness: identidade do deployment, fronteira do proxy, transporte e decisão de disponibilidade. Os nove locais não são uma adição documental inócua.
- Um bundle inválido impede confiar em fases seguintes do executor; passar o bundle não abre o gate de mutações nem valida o destino PostgreSQL.

**Lacuna distinta:** o conjunto atual não atesta `backend/security_migrations/**`, entrypoints dedicados, configuração Gunicorn ou toda a cadeia de dependências da imagem (apenas requirements.txt está incluído). Não declarar cobertura integral por obter 52 entradas. Deve ser revisto um mecanismo complementar de atestação destes artefactos e da imagem, sem alargar silenciosamente o manifesto: entradas extras são recusadas pelo verificador atual. Qualquer mudança de âmbito/verificador exige proposta e aprovação próprias.

### 6. Opção recomendada — aprovação em duas fases

**Fase 1, proposta agora:** aprovar o processo e o âmbito da reconciliação. Rever individualmente os 21 ficheiros ausentes e os quatro conteúdos divergentes, identificando responsável, origem, diff e compatibilidade com os contratos. As 16 fontes versionadas têm proveniência demonstrável, mas a inclusão/substituição continua pendente; os nove locais exigem revisão adicional explícita.

**Fase 2, tarefa posterior:** depois de estabilizar alterações decorrentes de D01/D02, congelar o conjunto concreto de bytes e produzir um candidato separado para revisão, com lista completa de fontes, diffs, hashes e digest do próprio candidato. Exigir **nova aprovação humana explícita desse candidato concreto**, antes de substituir o manifesto protegido. Não se aprova nesta DEV-08 qualquer hash novo como autoridade executável.

O conjunto esperado é hoje 52; se o código mudar, a futura revisão deve recontar e justificar o conjunto completo, não forçar 52 nem ignorar fontes para obter um teste verde.

### 7. Alternativas consideradas

- Repor todos os ficheiros nos hashes antigos: exige reverter funcionalidade M1.2A e pode remover segurança; não recomendado sem decisão específica.
- Excluir módulos security/readiness do verificador ou aceitar conjunto parcial: enfraquece a raiz de confiança; rejeitado.
- Regenerar automaticamente e aceitar os hashes encontrados: transforma o estado corrente em aprovação; rejeitado.
- Adiar reconciliação e manter gates fechados: alternativa segura se a revisão individual não puder ser concluída.

### 8. Justificação e impacto arquitetural/de segurança

Aprovação de código, integridade de bytes e autorização operacional são três decisões diferentes. A sequência proposta torna a reconciliação rastreável sem atribuir autoridade automática ao HEAD, aos artefactos locais ou a um relatório. Preserva a falha perante origem não validada, alterações de segurança, fonte ausente/excedente e destino divergente.

### 9. Ficheiros afetados futuramente e plano

1. Rever as 25 fontes listadas, os commits e os contratos correspondentes; não é obrigatório modificá-las. As dúvidas de origem/aprovação devem ter resolução explícita por ficheiro.
2. Estabilizar implementação D01/D02 previamente autorizada e âmbito de atestação complementar; congelar bytes, referências e imagem prevista.
3. Preparar candidato e evidência de revisão; submeter a segunda aprovação explícita.
4. Só depois, numa tarefa autorizada, atualizar `scripts/postgres/auth03_executor_integrity.json` para os bytes aprovados, conservando referência imutável da versão anterior e vínculo ao artefacto/imagem. Atualização de imagem/executor exige tarefa posterior autorizada.
5. Testar sem adulterar gates ou expectativas de segurança; qualquer execução PostgreSQL continua a exigir a sua própria autorização.

Ficheiros potencialmente afetados: manifesto, documentação de aprovação/proveniência, teste do bundle e empacotamento do executor se necessário. Não alterar automaticamente os 25 ficheiros para os fazer coincidir com o manifesto, nem o verificador para esconder falhas.

### 10. Critérios de aceitação e testes futuros

- Todos os ficheiros do conjunto esperado têm revisão e aprovação individual rastreáveis, incluindo os nove locais; candidato completo e digest aprovados separadamente.
- Verificação do bundle aprovado passa; alteração de um byte, arquivo ausente/excedente, symlink ou manifesto/código de outra versão falha.
- Os dois casos positivos históricos (bundle e lock) passam pelo motivo correto, sem enfraquecer as verificações negativas.
- Cobertura offline confirma manutenção de autenticação, CSRF, cookies, sessões partilhadas, TLS/proxy, configuração explícita e readiness 503 sem evidência válida.
- Gates de mutação AUTH-03, F02/G2/G4 e validação de identidade continuam a recusar operações não autorizadas, mesmo com manifesto válido.
- Sem segredos nos diffs/logs/manifesto; construção da factory sem DDL, provisionamento ou administração.
- Nenhum teste real PostgreSQL é autorizado por esta decisão; deve constar de tarefa posterior descartável específica.

### 11. Riscos e reversão

Aceitar em bloco os nove locais ou incluir um artefacto errado torna o manifesto internamente coerente mas inseguro. Código que mude depois da aprovação invalida a atestação. Rollback deve restaurar **o par de artefactos/fontes e manifesto da mesma versão aprovada**, sem sobrepor trabalho local e sem usar um manifesto antigo com código novo. Se isso não for possível, manter execução recusada e preparar nova revisão. Não apagar a evidência anterior nem transformar rollback em abertura de gates.

### 12. Aprovação humana

**Aprova a D03 apenas como processo de reconciliação em duas fases, com revisão individual das 21 inclusões e quatro substituições e nova aprovação explícita de um candidato completo com digest, sem aprovar automaticamente os nove artefactos locais, sem atualizar agora o manifesto e sem abrir gates?**

## Matriz de dependências

| Decisão / ação | Depende de | Efeito permitido após aprovação arquitetural | O que não fica autorizado |
| --- | --- | --- | --- |
| D01 — identidade | Revisão humana do naming, isolamento e adenda DAT-05A | Preparar implementação revista dos perfis | Criar/alterar bases, roles ou clusters |
| D02 — destinos | D01 para alvo concreto; decisão de catálogo/materialização | Preparar seleção explícita f066/b12 vs f067 | Executar migrações, alterar ledgers ou gates |
| D03 fase 1 — revisão | Pode começar em paralelo à análise D01/D02 | Rever individualmente fontes e plano de atestação | Aceitar bytes automaticamente ou substituir manifesto |
| D03 fase 2 — candidato | D01/D02 estabilizados; fontes concretas e âmbito revistos | Pedir aprovação de candidato completo | Aplicar candidato antes da segunda aprovação |
| Primeiro ensaio persistente descartável | Implementações revistas + candidato aprovado + contrato/execução especificamente autorizados | Apenas o ensaio no alvo autorizado | Ativação operacional ou uso de bases persistentes |

## Ordem recomendada de aprovação e implementação posterior

1. Aprovar D01, depois D02 e D03 fase 1; podem ser respondidas no mesmo parecer, com cada identificador explicitamente aceite/rejeitado.
2. Abrir tarefa de implementação com âmbito fechado: adenda documental, perfis de destino e revisões explícitas, sem gates globais nem operações em bases persistentes; testes offline de identidade/catálogo.
3. Concluir revisão individual das fontes e cobertura complementar security/runtime. Congelar o resultado e pedir a aprovação D03 fase 2 do candidato concreto.
4. Preparar e obter autorização separada de mecanismo/target descartável, roles/ACL, execuções externas e evidências. Só então realizar a sequência D02.
5. Demonstrar integração real de autenticação/sessões/auditoria/inventário e checker autorizado, recuperação independente e rollback. Só depois propor promoção e disponibilização.

Não iniciar qualquer destas implementações como continuação automática desta entrega. Aguardar aprovação explícita das três propostas; futuras alterações de gates/contratos protegidos necessitam da sua autorização específica.

## Bloqueios que permanecem mesmo após aprovação das propostas

- Manifesto AUTH-03 continua inválido até revisão/segunda aprovação e atualização autorizada; os nove locais não passam a fontes aprovadas por esta proposta.
- Executores de mutação AUTH-03 e security continuam fechados; G4 mantém fronteira de execução recusada (`scripts/postgres/g4/contracts.py:491–502`). Não existe autorização implícita de F02/G2/G4.
- Readiness real continua ausente/desativada; f066/b12 é condição necessária e não suficiente.
- Privilégios runtime e ownership/ACL no destino real ainda precisam de verificação. D05 não elimina as escritas restritas de autenticação/auditoria.
- Falta demonstrar recuperação independente de um backup e continuidade operacional, sem deduzir isso de fixtures.
- Identidades reais, colisões, TLS, isolamento de clusters e perfis de execução futuros não foram validados contra infraestrutura operacional.
- A proveniência/aprovação original dos artefactos locais, documentos originais não localizados e lacunas G4/L02 previamente registadas permanecem abertas. Este relatório não as declara resolvidas.
- Preparação de sessões/contas/dados sintéticos, migrações e ensaio persistente exigem autorização e plano próprios. Nada é provisionado no arranque.
- Não há nesta entrega prova nova de funcionalidades persistentes testadas/operacionais.

## Estado Git inicial, final e alterações desta entrega

Baseline inicial: branch `main`; HEAD `647179c928888adfeef0f69f582fd13c5fc17350`; índice SHA256 `50d32095da16e2c0e985226625971e890c33d406cbb9b97743a7198905b9541e`. Quatro ficheiros versionados já modificados: `backend/migrations/env.py`, `docs/specifications/f0/data-model.md`, `docs/specifications/f0/implementation-status.md` e `frontend/README.md`. Existiam 86 ficheiros não versionados e 202 ficheiros versionados, totalizando 288 ficheiros não ignorados na baseline.

**Única alteração DEV-08:** criação de `docs/operations/dev08-persistence-decisions.md`. Nenhum contrato protegido, manifesto, gate, código, configuração ou teste foi alterado. Estado final verificado: mesma branch, mesmo HEAD e índice, mesmos quatro modificados e mesmos 86 não versionados, acrescidos deste relatório (87 não versionados; 289 ficheiros não ignorados).

Verificação de preservação concluída: os SHA256 dos 288 ficheiros iniciais permanecem iguais; índice, HEAD e branch preservados; o único caminho novo é este relatório. `git diff --check` passou; o relatório não tem whitespace no final das linhas. Não houve commit, push, migração, SQL, teste, instalação, serviço, exposição de porta ou mudança de firewall/routing. Nenhum ficheiro de segredo foi lido para esta análise.

