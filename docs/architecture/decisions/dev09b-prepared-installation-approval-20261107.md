# DEV09B-PREPARED-1 — autorização da via revista de instalação inicial

07/11/2026 · Europe/Lisbon

## Fonte e decisão

Fonte primária: pedido humano nesta conversa «Implementar a via revista de
instalação inicial DEV09B aprovada pelo utilizador». Autoriza alterações mínimas
nas cinco migrações identificadas, helper, validadores/perfis/packaging, novo
bundle candidato, testes offline e este registo/CONTINUITY.md. Inclui os cinco
ficheiros locais do bloco físico anterior, preservando o seu trabalho.

Decisões aprovadas:

- inventory, audit e security preparados administrativamente, vazios de objetos
  LiveNet, com owners NOLOGIN finais distintos.
- btree_gist pré-instalado e verificado.
- migrator sem CREATE efetivo na base e com poderes apenas nos schemas da cadeia
  em execução; ownership transitório apenas dos objetos criados.
- handoff por administração separada, após confirmação de persistência.
- instalação inicial apenas; sem downgrade, grants runtime ou operação real.

Aplicação e security mantêm pedidos/aprovações/tentativas separados e destinos
f066a01a7230 e b12b01a7230. Security continua dependente de f066 confirmado
independentemente. Não se alteram IDs/encadeamento das revisões nem se autoriza
aplicar estas fontes revistas a um histórico já instalado como se fossem os
bytes anteriormente atestados. A alteração de precondições é explícita.

## Via revista e guardas

As três instruções CREATE SCHEMA e as duas CREATE EXTENSION IF NOT EXISTS são
substituídas por verificação de pré-requisitos. Não se presume que IF NOT EXISTS
dispense privilégios. Os schemas existem desde DEV-BASE; a revisão controla a
criação dos seus objetos, não a criação/ownership dos schemas.

O helper [dev09b_prerequisites.py](../../../backend/migrations/dev09b_prerequisites.py)
exige DEV09B-PREPARED-1, parâmetros concretos, ligação externa transacional e
porta de inspeção/autenticação operacional confiável. Não existe implementação
positiva dessa porta neste bloco. Flags, digests, perfis meramente declarados e
observações sintéticas não bastam; valores/porta ausentes causam MissingParameter.
O helper não liga a PostgreSQL, não provisiona e não executa SQL.

As guardas nos dois env.py precedem configure/run_migrations e a criação
automática de ledgers pelo Alembic. Não existe fallback para engine/configuração
implícita na via preparada. O uso futuro exige contexto explicitamente injetado
pelo executor guardado; perfil de pré-requisitos não substitui autorização de
execução, consumo, exclusividade, validade/revogação ou confirmação independente.

São recusados CREATE/TEMPORARY/ownership da base, atributos administrativos e
memberships do migrator, schemas/owners/ACL/extensão divergentes, origem/fonte
divergente, resíduos e falta da confirmação de f066. A porta real terá de obter
e autenticar os factos: os testes de registos não demonstram esses privilégios.

## Perfis e contratos preservados

Novas referências `dev09b-prepared-base-v1`, `dev09b-prepared-f066-v1` e
`dev09b-prepared-b12-v1`; os perfis físicos usam prefixo dev09b-prepared.
Schemas são dos owners NOLOGIN em todas as fases. Tabelas, funções, índices e
ledgers permanecem transitórios até persistência e handoff. CREATE na base sai
da janela; USAGE/CREATE nos schemas da cadeia e public para o ledger são
enumerados. A cadeia security não recebe DDL/escrita inventory/audit.

O conflito de poder CREATE/extensões do [bloco físico](dev09b-offline-physical-phases-approval-20261107.md)
é resolvido no desenho/código da via preparada retirando esse poder, não por
dispensa da garantia. Prova PostgreSQL real e parâmetros ainda não fornecidos
continuam pendentes. Não há alegação de validação integral operacional.

Os executores históricos AUTH-03/M1.2B recusam incompatibilidade explicitamente.
AUTH-03/F02/G2/G4 continuam fechados, execution_enabled=False preservado.
Os pins históricos de fontes permanecem históricos; não foram atualizados como
se atestassem o novo conteúdo. Atos, candidatos, patches, evidências e manifestos
anteriores mantêm os bytes anteriores. Sem extensão de R2/C4/I-04.

## Novo bundle candidato

[prepared-candidate.json](../../../scripts/dedicated/dev09b/prepared-candidate.json)
é independente de auth03_executor_integrity.json e dos candidatos DEV09A.
Declara CANDIDATE_NOT_APPROVED e operational_authority=false. O verificador
confere conjunto completo de fontes locais incluídas, bytes e locks; nenhum
hash novo aprova fontes, perfil, dependências ou execução.

Fecho de fontes: backend/app, migrations, security_migrations, módulos DEV09B,
contratos g4 e executores/coordenador/adaptadores incluídos, configurações e locks
pertinentes. Os locks existentes vinculam 15 distribuições. Falta
`dependencies.cryptography.approved_transitive_lock`: a biblioteca disponível no
Python do sistema permite testes, não fixa os artefactos/transitivas do ambiente
alvo. O candidato declara dependências INCOMPLETE; require_complete_candidate
recusa precisamente esse parâmetro. Não foi escolhido/downloadado um pacote
real por suposição nem regenerado um manifesto histórico.

## Testes e incompatibilidades históricas

Testes DEV09B cobrem observações de pré-requisitos, efetiva ausência de poderes
da base no modelo, scopes por cadeia, owners, resíduos, extensão, pré-condição
f066, guardas antes do ledger, AST das cinco revisões, comparação por fase,
referências e fontes/locks adulterados. São testes offline, não execução das
migrações ou prova de PostgreSQL real.

O teste AST/metadata security foi adaptado para exigir o helper exato em vez de
CREATE SCHEMA; não ignora arbitrariamente chamadas desconhecidas. Os testes
históricos AUTH-03 e M1.2B não foram alterados para aparentar compatibilidade.
Dependem das fontes anteriores:

- test_env_uses_exact_external_connection: admite conexão sem o novo contexto
  preparado/transação validada, agora insuficiente.
- test_verified_manifest_and_tampering: exige bundle histórico válido na árvore
  revista, que deve ser recusado.
- test_future_lock_conflict_and_wrong_source: não alcança os antigos preflights,
  pois a recusa de bundle ocorre antes.
- 18 casos M1.2B dependem da fixture plan construída pelo executor histórico;
  a preparação dessa fixture é recusada por incompatibilidade antes de I/O.

Esses resultados não são contados como testes da nova via aprovados nem como
provas de locks. A ausência de ligação de fallback continua testada e recusada.

## Limites e próximo ensaio

Continuam necessários: fontes/locks candidatos revistos, lock criptográfico e
transitivas, parâmetros de distribuição/template/extensão/identidade/owners/ACL,
porta real de autoridade/continuidade/inspeção, executor e checker guardados,
recuperação independente e autorização específica do alvo DEV descartável.
Preparação administrativa, migrações, handoff e ativação de conta/dados/runtime
e HTTPS interno exigem autorizações próprias. Não executar o ensaio por existir
este ato ou por os testes offline passarem.

Sem instalações, rede, PostgreSQL, execução SQL/Alembic, provisionamento, serviços,
chaves reais, infraestrutura, abertura de gates, staging, commits ou pushes.
Progbox exclusivamente DEV; STAGING/PROD em VMs Proxmox e acesso interno.
