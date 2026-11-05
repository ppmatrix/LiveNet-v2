# AUTH-03 — Etapa 209D.21

Atualização 209D.24: o operador confirmou a criação/validação posterior do cluster
com identificador `7698845469694267426` e secret exclusivo já existente. A preparação
do executor, operações bloqueadas e condições da primeira migração estão em
[auth03-alembic-executor.md](auth03-alembic-executor.md). As referências abaixo a
criação futura descrevem o estado histórico da etapa 209D.21; não recriar recursos
como parte da preparação do executor. Nesta etapa continua proibida execução online.

Preparação local; nenhuma execução PostgreSQL ou alteração de recursos Docker
está autorizada nesta etapa. Não foram alteradas a migração nem a arquitetura.

## Ambiente e isolamento

Usar exclusivamente `compose.auth03-test.yaml`, projeto `livenetv2-auth03-test`,
serviço `db`, imagem `postgres:16-alpine`, base `livenet_auth03_test`.
O volume lógico `auth03_postgres_data` e a rede interna `auth03_backend` recebem
o prefixo do projeto Compose; não há recursos externos, nomes globais fixos,
bind mounts de dados, publicação de portas nem ligação às redes existentes.
Não sobrepor o projeto com `-p` diferente, nem combinar outros ficheiros Compose.
O healthcheck verifica disponibilidade com `pg_isready`; não prova autenticação,
identidade do cluster ou revisão, que são verificadas separadamente pelos testes.

O secret passa a referenciar `secrets/auth03_db_password.txt`, exclusivo do
descartável e ignorado pelo Git. O ficheiro não foi criado nesta etapa: preparar
depois com valor próprio e permissões restritas. Compose monta-o como
`/run/secrets/db_password` e PostgreSQL usa `POSTGRES_PASSWORD_FILE`.
Não imprimir o conteúdo, colocar passwords no DSN ou em argumentos de comandos.
Uma validação `config --quiet` não comprova que o secret existe ou é legível
durante o futuro arranque.

## Configuração futura dos testes

Obrigatórias, sem fallback para variáveis F066C ou `DATABASE_*`:

| Variável | Conteúdo |
| --- | --- |
| `AUTH03_ANCHOR_TEST_DATABASE_URL` | `postgresql+psycopg://livenet@db:5432/livenet_auth03_test` no contexto da rede dedicada; sem password e sem query string |
| `AUTH03_ANCHOR_TEST_PASSWORD_FILE` | Caminho legível pelo futuro executor para o secret exclusivo |
| `AUTH03_ANCHOR_TEST_SYSTEM_IDENTIFIER` | Identificador decimal do novo cluster, validado por operador após a criação |

O executor terá de alcançar a rede interna e resolver `db` exclusivamente para
o serviço deste projeto. O serviço atual contém só PostgreSQL, não o executor
Python; a instalação/execução desse executor fica para uma etapa autorizada.
Não publicar portas como atalho. Endereços locais e portas distintas de 5432 são
rejeitados; um endereço explícito alcançável na rede dedicada também é aceite.

Após autorização de criação, o operador deve confirmar projeto, labels, imagem,
mount do volume e rede antes de ler `system_identifier` por um canal de confiança
no serviço `db` deste projeto. Registar a evidência e só então configurar a
variável esperada. Não copiar o identificador F0.66C, não derivar automaticamente
o valor esperado da ligação sob teste. Uma cópia física do cluster preserva o
identificador; esta validação depende também da proveniência do volume e da rede.
Uma recriação com novo `initdb` exige nova validação humana do identificador.

## Privilégios e condições antes de escrita

Na mesma ligação e transação exterior explícita, os testes exigem:

1. `current_database()` igual a `livenet_auth03_test`.
2. `has_function_privilege` para `EXECUTE` em `pg_catalog.pg_control_system()`.
3. `system_identifier` exatamente igual ao valor previamente validado.
4. Uma única linha em `public.alembic_version`, exatamente `f067a01a7230`.

Ausência de configuração causa erro, não skip. Revisão ausente, múltipla,
incorreta ou inacessível bloqueia a execução antes do yield da fixture.
`pg_control_system()` está disponível no PostgreSQL 16 e lê a identidade do
cluster. A implementação de PostgreSQL 16 não impõe superuser internamente;
o EXECUTE é público por omissão, podendo ser revogado pelo administrador.
A fixture verifica o privilégio efetivo e falha se não existir, sem executar GRANT.
Fontes: [documentação PostgreSQL 16](https://www.postgresql.org/docs/16/functions-info.html#FUNCTIONS-PG-CONTROL),
[implementação](https://github.com/postgres/postgres/blob/REL_16_STABLE/src/backend/utils/misc/pg_controldata.c),
[privilégios das funções de sistema](https://github.com/postgres/postgres/blob/REL_16_STABLE/src/backend/catalog/system_functions.sql).

O utilizador também precisa de CONNECT na base, USAGE nos esquemas relevantes,
SELECT em `public.alembic_version` e SELECT/INSERT/UPDATE na tabela de âncoras.
O utilizador inicial `livenet` da imagem oficial é superuser; não são criadas roles
nem alterados privilégios nesta etapa ou pelas fixtures.

## Transações e cobertura

Cada caso abre transação exterior com `begin()`; `finally` faz rollback e a engine
é descartada, incluindo falhas de preflight e exceções no corpo do teste.
Não há commit, DDL, Alembic online ou alterações de roles nas fixtures.
Inserções e atualização inválidas usam savepoints para recuperar a transação.
Os erros são associados ao SQLSTATE/constraint relevante; vários casos confirmam
que a ligação continua utilizável após a rejeição. Logs SQL estão desativados,
parâmetros ocultos e erros de ligação/DBAPI substituídos por mensagens sem DSN.
Não ativar logging externo de SQL, debug do driver ou `pytest --showlocals`.

Os 11 casos iniciais foram preservados e a recolha passa a 37: acrescenta NOT NULL
nas nove colunas, hashes vazios/curtos/não hexadecimais/maiúsculos, todos os estados
posteriores válidos, textos vazios, defaults temporais e uma atualização inválida.
Os testes offline verificam as barreiras de configuração, falhas de identidade e
privilégio, rollback em sucesso/exceção e sanitização de erros, com mocks.
Limites: PostgreSQL real, persistência após encerramento, tipos/limites de tamanho
e comportamento do ciclo Alembic só serão comprovados na futura etapa online.
Não se acrescentam regras de transição, políticas de imutabilidade ou validações
de significado da operação/target que não existem na migração aprovada.

## Estratégia futura de ciclo de vida — não executada

Esta sequência requer nova autorização humana para criação do ambiente e DDL/DML.

1. Criar apenas o projeto dedicado com volume novo, secret próprio e rede interna;
   validar proveniência e guardar o identificador conforme descrito acima.
2. Preparar um executor isolado. Usar ligação SQLAlchemy explícita, construída
   apenas da configuração AUTH-03, e fornecê-la em
   `config.attributes['connection']` do Alembic. O `migrations/env.py` já suporta
   esta ligação; não usar o fallback `get_database_url()` nem DSN de produção.
3. Antes de cada operação Alembic, validar novamente base e identificador na mesma
   ligação. Preparar a base vazia mediante upgrade real até `f066a01a7230`, sem
   `stamp`, e confirmar revisão única e ausência de `authorization`.
4. Fazer upgrade dirigido para `f067a01a7230`; confirmar revisão, esquema, tabela,
   nove colunas, tipos, NOT NULL, PK, oito CHECKs e defaults via catálogos PostgreSQL.
5. Registar baseline de contagens; executar apenas o ficheiro de integração AUTH-03.
   Confirmar numa nova ligação validada que as contagens e os UUIDs registados
   demonstram ausência de linhas persistidas, também num cenário de exceção.
6. Confirmar que só existem os objetos AUTH-03 esperados no esquema; executar
   downgrade **apenas até `f066a01a7230`** e apenas neste cluster descartável.
   Verificar remoção da tabela/esquema, revisão única anterior e preservação das
   tabelas Inventory/Audit. Não usar CASCADE nem manipular ownership se houver erro.
7. Repetir upgrade para a revisão AUTH-03 e as verificações estruturais/integração.
   Não executar estes passos no projeto `livenetv2-f066c` ou na base `livenet`.
8. Desmontagem e eliminação dos recursos descartáveis exigem autorização própria;
   verificar sempre labels e nomes do projeto antes dessas operações.

Não executar a suite geral indiscriminadamente: há testes antigos de integração
com outra configuração, incluindo ficheiro sem marcador `integration` global.
Para validação offline desta etapa, selecionar explicitamente os ficheiros
`test_authorization_anchor_migration.py` e `test_authorization_anchor_safety.py`;
para o ficheiro de integração usar exclusivamente `--collect-only`.

## Validação offline desta preparação

- Compilação Python dos três ficheiros de testes AUTH-03 e da migração: sucesso.
- Testes estruturais da migração: 8 passaram; barreiras de segurança: 32 passaram.
- Integração PostgreSQL: 37 casos recolhidos, nenhum executado.
- `docker compose -f compose.auth03-test.yaml config --quiet`: sucesso.
- Configuração normalizada em JSON: verificados projeto, serviço, imagem, base,
  healthcheck, secret, ausência de portas, nomes efetivos de volume/rede e rede interna.
- Nenhum comando de arranque, paragem ou remoção de recursos Docker; nenhuma
  ligação PostgreSQL, migração online, alteração de privilégios, commit ou push.
