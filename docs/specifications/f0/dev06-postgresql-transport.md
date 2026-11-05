# DEV-06 — transporte PostgreSQL dedicado com TLS

Estado: implementação opt-in validada em recursos descartáveis, 2026-10-25.
Não aprova identidades operacionais, migrações, manifesto AUTH-03 ou deployment.
Não altera a decisão DAT-05A nem a recusa de `DATABASE_NAME=livenet` no perfil dedicado.

## Seleção explícita e configuração

`backend/dedicated_wsgi.py:create_tls_app('/run/livenet/backend.json')` exige as
11 chaves do entrypoint anterior e duas adicionais, sem descoberta por ambiente:

| Chave adicional | Valor exigido |
|---|---|
| `DATABASE_SSLMODE` | Exatamente `verify-full` |
| `DATABASE_SSLROOTCERT_FILE` | Caminho absoluto de certificado(s) CA PEM de confiança |

O JSON continua regular, privado, sem symlinks, até 16 KiB, pertencente ao UID do
processo; chaves duplicadas, desconhecidas e constantes JSON não finitas são recusadas.
O entrypoint anterior `create_app` mantém o contrato de 11 chaves e não aceita
silenciosamente as duas novas. Não representa o percurso TLS validado na DEV-06.

A configuração TLS usa `app.postgres_tls.PostgresTLS`, não um callback arbitrário.
Só esse tipo exato é aceite pelo parâmetro Python confiável `database_tls` da
factory dedicada. O parâmetro por omissão preserva o percurso anterior; o novo
entrypoint fornece obrigatoriamente TLS. Nenhum endpoint HTTP seleciona factories.

A CA deve ser um ficheiro regular absoluto, não vazio, até 1 MiB, sem symlinks em
qualquer componente, ownership root ou UID runtime e sem escrita por grupo/outros.
Pode ser pública/readable; não é a chave privada da CA. O PEM é validado localmente
com `SSLContext.load_verify_locations`, sem sockets. A montagem é read-only.
A configuração é validada antes da aplicação e novamente antes de abrir sessões.
Alterações de PKI num ambiente real exigirão um procedimento próprio de rotação;
esta tarefa não demonstra renovação de ligações já existentes num pool.

Os argumentos finais libpq são explícitos: `sslmode=verify-full`, `sslrootcert`
igual ao caminho validado, `gssencmode=disable` e `connect_timeout=2`. Desativar GSS
encryption impede que esse transporte tome precedência sobre SSL. Não há fallback
para CA ambiental nem modos `prefer`/`require`/`verify-ca`. As recusas anteriores de
PGHOSTADDR/PGSERVICE/PGSERVICEFILE/PGOPTIONS permanecem. Verificação de identidade
TLS e identidade física PostgreSQL são distintas; ambas foram testadas no descartável.

## Montagem e empacotamento

`compose.dedicated-tls.yaml` é um overlay explícito sobre `compose.dedicated.yaml`.
Seleciona a factory TLS e acrescenta `/run/livenet/ca.crt`, com origem obrigatória
`DEV06_POSTGRES_CA_FILE`, read-only e `create_host_path=false`. Os três entrypoints
`exit 78`, profiles, ausência de ports backend/DB e restantes controlos são herdados.
O overlay não configura um servidor PostgreSQL TLS operacional nem autoriza `up`.
O servidor TLS do ensaio é criado apenas pelo harness descartável.

`preflight.py` reconhece os dois comandos, aplica os respetivos conjuntos exatos de
chaves e valida CA/montagem no percurso TLS. O resultado continua `activation=blocked`
e `network_enforcement=not_attested`. Alocação candidata não equivale a aprovação.

## Persistência e readiness

A autenticação e o inventário continuam a partilhar uma única fonte lazy de sessões
SQLAlchemy; a construção não abre conexões, não cria engines nem executa DDL/DML.
TLS não concede privilégios nem fornece contas, schemas, revisões ou checker.

A readiness permanece sem checker real. AUTH-03, migração security e fronteira G4
continuam bloqueados. Não foi alterado o catálogo Q1–Q16 ou criado um caminho de
aprovação alternativo. Conectividade/TLS/SELECT não produzem observação positiva.

O schema `dev06_probe` do ensaio SQL é independente e explicitamente sintético:
`read_target`, `write_target`, `audit_target`. Não é cópia de schemas aplicacionais,
não regista revisões e não substitui Alembic. As suas roles exemplificam separação
admin/owner/migrator/runtime/inspector; não atestam a matriz D05 sobre objetos reais.
Inventário aplicacional continua SELECT-only no contrato D05; não foram concedidos
privilégios de escrita em inventory, security ou audit.

Evidência e decisões pendentes: [relatório DEV-06](../../operations/dev06-postgresql-integration.md)
e [reconciliação por hash](../../operations/dev06-contract-evidence.json).
