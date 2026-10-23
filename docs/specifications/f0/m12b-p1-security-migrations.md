# M1.2B-P1 — Cadeia Alembic independente para security

## Decisão e âmbito

A decisão M1.2B-D01 separa a evolução de `security` da cadeia aplicacional.
A cadeia existente permanece `base -> ... -> f066a01a7230 -> f067a01a7230`
(f067 é AUTH-03 local). A configuração `backend/alembic-security.ini` carrega
exclusivamente `backend/security_migrations`:

```text
base -> b12b01a7230 (root/head)
ledger: public.alembic_security_version
```

`down_revision`, `branch_labels` e `depends_on` são `None`. A baseline f066 é
uma pré-condição operacional explícita, sem dependência no grafo security.
O ledger aplicacional `public.alembic_version` não é atualizado por esta cadeia.
Esta preparação não implementa AUTH-BOOT nem qualquer autorização privilegiada.

P1 escreve declarações, contratos puros e testes offline. Não estabelece ligações,
executa SQL, gera SQL offline, executa migrações, cria contas ou altera serviços.

## Estrutura declarada

| Tabela no schema security | PK | UNIQUE | FK | CHECK |
| --- | --- | --- | --- | --- |
| local_users | id | login | — | login normalizado, status, timestamps |
| login_sessions | id | token_hash | user_id → local_users.id | hash, tempos, revogação |
| global_role_grants | id | (user_id, role) | user_id → local_users.id | role, âmbito global |
| login_throttles | bucket_hash | — | — | attempts >= 1 |

São quatro PK, duas FK, três UNIQUE, nove CHECK e um índice explícito
`ix_security_login_sessions_user_id`. PK e UNIQUE implicam ainda sete índices
de suporte no PostgreSQL. Todas as constraints têm nomes determinísticos.
Os nomes explícitos das PK/FK complementam as constraints sem nome nos modelos;
os modelos M1.2A permanecem intactos. Tipos, nulabilidade, CHECK, UNIQUE e índice
correspondem aos modelos. Os defaults Python continuam exclusivamente no ORM:
não são acrescentados `server_default`, extensões ou dados iniciais.

## Configuração e isolamento

`contract.py` copia apenas a metadata das quatro tabelas, sem alterar
`Base.metadata`. Os filtros de nomes e objetos excluem inventory, audit,
authorization, public e tabelas security desconhecidas. A autogeração não deverá
propor DROP nesses domínios; nenhuma autogeração foi executada.

O ambiente exige uma ligação externa PostgreSQL já dentro de uma transação.
Não cria engines, não lê secrets nem DATABASE_URL/get_database_url(), não usa
fallback aplicacional e rejeita modo SQL offline. A configuração valida diretório
exato, ledger próprio e ausência de URLs ou diretórios de revisões adicionais.
Uma ligação externa, por si só, não constitui autorização de execução.

## Contrato de preparação do destino

`scripts/postgres/m12b_security_migration.py` prepara um plano imutável e valida
observações fornecidas, sem I/O de base de dados. `execute_security_migration()`
recusa sempre a execução em P1; não há CLI operacional.

O perfil aceita exclusivamente:

- Projeto `livenetv2-m12b-test`, base `livenet_m12b_test`, endpoint `db:5432`.
- `system_identifier` PostgreSQL explícito, inteiro decimal positivo de 64 bits.
- Identidade de migração `livenet_m12b_migrator` e aplicação `livenet_m12b_app`.
- Confirmação explícita de `f066a01a7230` como baseline aplicacional.

Estes nomes são planeados; não foram criados ambientes, roles ou credenciais.
São rejeitadas `livenet`, `livenet_f0_test`, `livenet_auth03_test`, quaisquer outras
bases/projetos, configuração incompleta e campos adicionais, incluindo passwords.
Não existem descoberta automática nem credenciais em argumentos, logs ou exemplos.

O plano verifica por AST uma única revisão independente e associa hashes dos
ficheiros de preparação/configuração, cadeia security e modelos. O digest é
determinístico, mas não constitui autorização nem manifesto de deployment completo.

`ObservedState` é a interface para inspeção futura. Antes da migração exige
PostgreSQL 16, identidade de sessão de migração, system_identifier esperado,
apenas f066 no ledger aplicacional, ausência de ledger security e exatamente
os schemas public/inventory/audit com as 12 tabelas inventory, audit.events e
public.alembic_version. Depois exige adicionalmente schema security, as quatro
tabelas, ledger próprio e revisão b12b01a7230. f067, authorization e objetos
inesperados provocam recusa.

Estas observações são dados fornecidos ao validador, não prova de estado real.
P2 terá de recolhê-las na ligação validada, verificar proveniência do ambiente,
colunas, constraints, índices, ACL e conteúdo dos ledgers. Um ambiente com objetos
adicionais exige um perfil revisto explicitamente; não se relaxa a validação.

## Contrato futuro de execução e teste PostgreSQL descartável

P2 necessita de autorização específica e de um executor próprio. O contrato
preparado exige transação externa única, mesma ligação, lock de migração,
verificação antes/depois e commit explícito após validação física. O search_path
previsto é pg_catalog/public; nenhum SET foi executado em P1. Não há retry
automático; resultado de commit incerto exige reconciliação.

Procedimento proposto, ainda não executado:

1. Preparar numa VM de laboratório Proxmox um projeto descartável independente,
   com rede/volume próprios, imagem PostgreSQL fixada, proveniência e identidade
   verificadas. Não reutilizar os três ambientes proibidos.
2. Provisionar credenciais separadas por canal apropriado, fora de argumentos e
   logs. Aplicar a baseline exatamente até f066 apenas com autorização própria;
   nunca usar `head` da cadeia aplicacional nem executar f067 por consequência.
3. Conceder à identidade de migração os privilégios DDL e do ledger necessários.
   A identidade aplicacional recebe somente o DML necessário; não deve ser dona
   dos objetos, criar schemas ou escrever no ledger. Login/RBAC não autorizam Alembic.
4. Implementar inspeção real, validação do plano/fontes, lock e transação única;
   executar apenas a revisão security autorizada e validar fisicamente os objetos.
5. Testar constraints negativas, concorrência, rollback em falha e persistência
   após commit através de nova ligação. Testar também destinos/revisões proibidos.
   Nunca repetir automaticamente uma execução com resultado incerto.

O executor AUTH-03 e o seu operation_gate não participam neste procedimento.
O Dockerfile atual copia a árvore original de migrações; a distribuição da nova
configuração/diretório terá de ser tratada em P2, sem alteração Docker nesta fase.

## Downgrade, recuperação e coexistência

`downgrade()` recusa sempre, sem flags de desbloqueio ou DROP/CASCADE. Uma
recuperação futura exige plano separado: restauro verificado ou revisão corretiva
autorizada. Rollback transacional não equivale a downgrade destrutivo.

As duas cadeias têm ledgers separados, mas partilham a base. P2 deve impedir
concorrência operacional e validar ambos os ledgers. O env.py aplicacional
existente usa metadata abrangente: autogeração nessa configuração pode cruzar
domínios; não deve ser utilizada para gerir security. Não foi alterado aqui.

## Verificação e limitações

Os testes novos leem AST e constroem metadata em memória, verificam grafo,
constraints, filtros, guardas e falha fechada com mocks. Não invocam upgrade,
downgrade, create_all, drop_all, SQL ou bases SQLite/PostgreSQL.

Os 15 ficheiros AUTH-03 são comparados por SHA-256 com o estado inicial desta
execução. Modelos M1.2A, configuração e migrações originais também são protegidos.
O manifesto AUTH-03 não é atualizado; a comparação entre início/fim não certifica
o seu estado preexistente perante alterações anteriores do repositório.

Até P2 não há prova de execução física PostgreSQL, ACL, rollback, lock ou
durabilidade; não existe instalação security nem primeira conta. Autenticação
continua sujeita à configuração M1.2A e à preparação HTTPS posterior.
