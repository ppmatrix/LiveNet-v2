# AUTH-03 — Executor Alembic isolado — Etapa 209D.24

Estado: implementação e testes offline. Nenhum comando deste executor foi usado
para consultar Docker/PostgreSQL ou executar migrações nesta etapa. Não construir,
criar ou iniciar o serviço preparado sem autorização posterior.

## Identidade fixada

Segundo a validação humana fornecida para esta etapa:

| Campo | Valor obrigatório |
| --- | --- |
| Projeto | `livenetv2-auth03-test` |
| Container DB | `livenetv2-auth03-test-db-1` |
| Base / utilizador | `livenet_auth03_test` / `livenet` |
| PostgreSQL | 16.10 (`server_version_num = 160010`) |
| Identificador | `7698845469694267426` |
| Rede | `livenetv2-auth03-test_auth03_backend`, interna |
| Volume | `livenetv2-auth03-test_auth03_postgres_data` |
| Secret host | `secrets/auth03_db_password.txt`, já existente, 0600, ignorado pelo Git |

O executor não herda `DATABASE_*`, `F066C_*`, `PG*` ou URLs de produção. Identidade,
utilizador e host são constantes verificadas contra configuração explícita. Não
existe opção para substituir projeto, base, utilizador ou identificador. O exemplo
JSON contém marcadores deliberadamente inválidos para os IDs ainda não recolhidos
nesta etapa; não é configuração operacional nem autorização.

## Arquitetura e fronteiras de confiança

`scripts/postgres/auth03_alembic_executor.py` tem dois contextos:

1. **Host de confiança:** lê configuração privada 0600, valida SHA-256 das fontes,
   recolhe apenas metadados Docker com `container/network/volume inspect`, verifica
   IDs completos, labels, nomes, imagens fixadas por ID, saúde, mounts, rede interna,
   membros exclusivos DB+executor, volume local sem opções externas, data de criação
   fixada e ausência de portas. Verifica apenas metadados do secret, sem o ler.
2. **Executor na rede:** recebe configuração/evidência por stdin de `docker exec -i`
   dirigido ao ID fixado de um container já existente. Sem socket Docker, sem
   diretórios host montados, sem portas, processo com UID/GID não root, filesystem
   read-only, capacidades removidas e no-new-privileges. Só lê o secret exclusivo
   em `/run/secrets/auth03_db_password`. A imagem recebe uma cópia das fontes.

O host revalida Docker imediatamente antes e depois da inspeção PostgreSQL. O
contexto expira em 30 segundos, vincula o manifesto de fontes e fornece o IP
IPv4 obtido da rede validada. A ligação usa esse IP diretamente; a sessão deve
confirmar o mesmo endereço, porta, base, current_user/session_user, versão e
identificador. Evita dependência de aliases DNS ambíguos. Alterações detetadas
invalidam o resultado; não há retries automáticos.

A evidência stdin **não é uma assinatura nem autorização**. Confia no host, na
configuração revista, no daemon Docker local e no acesso ao processo `docker exec`.
Quem controla o host/daemon ou executa código arbitrário no container ultrapassa
esta fronteira. Os IDs e data do volume devem ser recolhidos e revistos pelo operador,
nunca preenchidos automaticamente a partir do alvo e tratados como confiáveis.
O volume não tem UUID imutável exposto pelo Docker: nome+labels+CreatedAt+mounts
são evidência de proveniência, não atestação criptográfica.

## Serviço preparado

`compose.auth03-executor.yaml` é um complemento explícito ao Compose AUTH-03,
com perfil `auth03-tools`. Não altera os Compose LiveNet/F0.66C nem arranca com
a utilização isolada do ficheiro original. A imagem tem Dockerfile próprio e
allowlist de contexto que exclui secrets, `.git`, `.env`, caches e ficheiros F0.66C.
Não foi construída nesta etapa. Não há pull, build, criação ou arranque automático
no executor Python; só `inspect` e `exec` sobre containers previamente aprovados.

Para futura validação estática, sem efeitos Docker:

```bash
AUTH03_EXECUTOR_UID=10001 AUTH03_EXECUTOR_GID=10001 docker compose \
  -f compose.auth03-test.yaml -f compose.auth03-executor.yaml \
  --profile auth03-tools config --quiet
```

Os valores 10001 acima servem apenas a validação estática. Para uso posterior,
UID/GID devem corresponder ao proprietário do secret host, sem mudar as suas
permissões para acomodar o serviço. Secrets de Compose local são bind mounts;
o remapeamento de utilizadores/rootless pode impedir a leitura e deve ser validado.
O preflight recusa execução root e proprietário inesperado. Só DB e executor
recebem o secret; o host transmite apenas o seu caminho conhecido por metadados.

## Operações e barreiras

| Seleção CLI | Acesso futuro | Origem → destino |
| --- | --- | --- |
| `preflight` | Metadados Docker; sem ligação PostgreSQL | Sem migração |
| `inspect` | Transação PostgreSQL read-only com rollback | Sem migração |
| `verify-revision --expected-revision empty` | Confirma base não versionada e vazia | Sem migração |
| `verify-revision --expected-revision f066a01a7230` | Confirma revisão exata | Sem migração |
| `verify-revision --expected-revision f067a01a7230` | Confirma revisão exata | Sem migração |
| `upgrade-baseline` | **Bloqueada no código nesta etapa** | Não versionada/vazia → `f066a01a7230` |
| `upgrade-auth03` | **Bloqueada no código nesta etapa** | `f066a01a7230` → `f067a01a7230` |
| `downgrade-auth03` | **Bloqueada no código nesta etapa** | `f067a01a7230` → `f066a01a7230` |

Não há SQL arbitrário, stamp, destino livre, `head`, downgrade para `base` ou modo
de autoaprovação. As operações modificadoras falham antes de ler configuração,
secret, consultar Docker ou abrir sockets, incluindo no modo interno `--runner`.
Nenhuma variável, token ou campo JSON as habilita nesta versão.

Exemplo da interface futura de leitura, **não executado nesta etapa**:

```bash
PYTHONPATH=backend .venv/bin/python scripts/postgres/auth03_alembic_executor.py \
  --config /caminho/privado/auth03-executor.json verify-revision \
  --expected-revision empty
```

A configuração deve ser copiada do exemplo, completada por operador, guardada
fora do Git em diretório de confiança e com modo 0600. Não contém password.

## Integridade, Alembic, transações e concorrência

O manifesto `auth03_executor_integrity.json` fixa as 31 fontes Python/configuração
necessárias: executor, aplicação, migrações, requisitos e Alembic ini. Rejeita
alterações, ficheiros Python adicionados/retirados e fontes symlink. O host e a
imagem devem possuir o mesmo manifesto. Mudanças exigem revisão explícita do
manifesto, sem comando de regeneração/aceitação automática no executor.
O manifesto é uma referência de revisão, não assinatura contra administrador host.
Os requisitos atuais usam intervalos: a imagem futura deve ser construída, revista
e fixada pelo seu ID; o manifesto não fixa versões transitivas do pip.

`alembic_config(connection)` usa `Config()` sem ficheiro de logging/URL e exige
`config.attributes['connection']`. O atributo adicional
`auth03_require_external_connection` faz `migrations/env.py` recusar ausência da
ligação, antes do fallback. Os fluxos existentes sem esse atributo são preservados.
As chamadas Alembic dirigidas estão atrás da barreira de etapa em `invoke_migration`.

As consultas atuais abrem transação explícita com read-only imposto nos parâmetros
de ligação, timeout de conexão/statement/lock, rollback em `finally` e NullPool.
Validam revisão única conhecida ou base efetivamente sem relações de aplicação,
e esquemas compatíveis com a origem. Não executam DDL, DML, GRANT ou SET ROLE.
Erros externos são suprimidos na CLI, parâmetros ocultos e echo desativado; não
usar debug de drivers, logging SQL externo ou traceback com locals.

Para ativação futura está preparada a primitiva `future_transaction_preflight`:
exige transação exterior, valida configuração e fontes, obtém advisory lock
transacional não bloqueante `(209024, 3)`, confirma identidade/revisão de origem
na mesma ligação. Deve ser seguida do comando Alembic e verificação de destino,
sem libertar lock ou trocar conexão. O lock só coordena executores cooperantes;
exige janela exclusiva sem Alembic/SQL paralelo fora do executor.

Não existe atomicidade entre metadados Docker e PostgreSQL. As verificações
repetidas reduzem a janela, mas não impedem intervenção concorrente de um
administrador Docker. Não podem ser apresentadas como garantia absoluta de
ausência de corrida. Por isso as mutações continuam bloqueadas.

## Autorização operacional futura — ainda não habilitada

A configuração prova intenção de ligação, nunca aprovação. `authorization_scope`
prepara os campos a vincular a uma futura autorização operacional de uso único:
projeto/base/identificador, IDs DB/rede/executor, proveniência do volume, operação,
origem/destino e digest do bundle. Não cria nem consome autorizações AUTH-03.

Antes de habilitar mutações é necessária alteração de código revista que implemente
um verificador de aprovação humana externo ao processo executor, com autenticidade,
operador responsável, validade curta, nonce e consumo de uso único resistente à
concorrência. O emissor/verificador e armazenamento desse consumo são decisões
pendentes; esta etapa não inventa nem ativa uma autoridade administrativa.
Um simples booleano, ficheiro presente ou nome do aprovador não será suficiente.

O fluxo a aprovar deve manter uma única transação: lock → autorização válida para
o estado atual → identidade/origem → Alembic com ligação externa → destino → commit
único. Exceções anteriores ao commit exigem rollback. Perda de ligação durante
commit deixa resultado incerto: não repetir; bloquear nova operação até inspeção
independente no mesmo cluster e reconciliação humana. O estado da autorização
deve acompanhar essa incerteza, sem a voltar a disponibilizar automaticamente.

## Antes da primeira migração

1. Rever código, manifesto, plano de ativação e modelo de autorização pendente.
2. Autorizar separadamente a construção/criação do executor e operações de leitura.
3. Confirmar host/daemon, UID/GID do secret, rede exclusiva e proveniência do volume;
   preencher IDs completos, IDs das imagens e CreatedAt, sem revelar passwords.
4. Construir e validar a imagem sem fontes host montadas; criar apenas o executor
   do projeto dedicado. Não recriar DB/volume/rede nem usar outros projetos.
5. Executar preflight e inspeção read-only apenas após essa autorização. Confirmar
   `empty`, identificador fixado e ausência de relações/esquemas adicionais.
6. Implementar/rever a ativação com aprovação concreta `upgrade-baseline`, mantendo
   o lock e os controlos transacionais descritos. Obter autorização humana antes
   da execução. Não usar comandos genéricos Alembic como alternativa à barreira.
7. Depois de confirmado o baseline, obter aprovação distinta para `upgrade-auth03`.
   Validar fisicamente colunas, constraints, PK/defaults e executar os 37 testes
   apenas numa etapa autorizada. Downgrade exige aprovação própria e ambiente
   descartável; nunca F0.66C. Desmontagem de recursos fica igualmente fora desta etapa.

Permanecem por comprovar online: secret no UID real, imagem/runtime de dependências,
preflight sobre metadados reais, consultas read-only, lock entre processos,
transação completa Alembic/rollback e resultados físicos das migrações. A consulta
de esquemas/revisão não substitui uma auditoria completa de todos os objetos,
funções, triggers e privilégios. PostgreSQL TLS não foi introduzido; o modelo atual
confia exclusivamente na rede interna isolada e no daemon local validado.

## Resultados offline da etapa

- 82 testes novos do executor e 40 testes AUTH-03 anteriores: **122 passaram**.
- Incluem configuração/identidades incorretas, operações bloqueadas, planos livres,
  falhas Docker simuladas, origem Alembic inesperada, fallback proibido, ficheiros
  privados inseguros, contexto expirado/divergente, lock ocupado e rollback em erro.
- `env.py` testado com ligação externa exata e com ausência de ligação sob a guarda,
  sem fallback nem execução real de migrações.
- 37 casos de integração PostgreSQL recolhidos; **nenhum executado**.
- Compilação Python e verificações de diferenças/espaços em branco: sucesso.
- Compose original e combinado: `config --quiet` passou. Configuração normalizada
  também validada estaticamente: perfil, rede, secret, UID, read-only, capacidades,
  ausência de portas e mounts de diretórios.
- Manifesto verificado offline; nenhum secret real foi lido, nenhuma imagem foi
  construída, nenhum container/recurso Docker foi criado ou alterado, nenhuma
  ligação PostgreSQL foi aberta. Sem commit ou push.
