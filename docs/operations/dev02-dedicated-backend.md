# DEV-02 — Arranque dedicado do backend, preparação offline

Base: `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`, progbox.
Esta entrega não autoriza instalação, build, arranque, migrações ou disponibilização.
Os ficheiros anteriores, incluindo trabalho local não versionado, são preservados.

## Percurso explícito

O entrypoint é `backend/dedicated_wsgi.py:create_app(config_path)`. Importar o
módulo não constrói a aplicação. A factory exige um caminho absoluto para JSON
externo ao repositório; não procura configuração no ambiente. Não existe `app`
global, configuração por omissão ou fallback para `wsgi.py`.

O JSON tem exatamente estas chaves, sem duplicados nem valores NaN/Infinity:

| Chave | Valor/tipo exigido |
| --- | --- |
| ENVIRONMENT | string `production` |
| DATABASE_HOST | hostname/IP único, validado pela factory existente |
| DATABASE_PORT | inteiro 1..65535 |
| DATABASE_NAME | base dedicada aprovada; `livenet` é recusada |
| DATABASE_USER | role runtime aprovada, sem credenciais bootstrap |
| DATABASE_PASSWORD_FILE | caminho absoluto do ficheiro da credencial runtime |
| SECURITY_ENABLED | booleano JSON `true` |
| SECURITY_CSRF_KEY_FILE | caminho absoluto da chave CSRF |
| SECURITY_HTTPS_ORIGIN | string `https://livenet-v2.home.arpa:8443` |
| PROXY_ENABLED | booleano JSON `true` |
| PROXY_PEERS | lista explícita e não vazia de IPs exatos do ingress aprovado |

A restrição de flags true pertence apenas ao novo entrypoint. Não muda os defaults
nem os contratos de `create_dedicated_app`, `create_app` ou do entrypoint antigo.
As restantes validações são delegadas à factory existente. Não há parâmetros para
instalar checker, alterar cookies, fornecer passwords inline ou contornar gates.

O JSON deve ser UTF-8, ficheiro regular pertencente ao UID do processo, sem
permissões de grupo/outros, até 16 KiB e sem symlink final. O diretório pai deve
ser controlado pelo operador; não se garante segurança de diretórios ancestrais
escrevíveis por terceiros. Os ficheiros de segredos mantêm as restrições existentes:
owner UID, acesso privado, ficheiro regular, sem symlink final, até 16 KiB; chave
CSRF com pelo menos 32 caracteres. Não criar estes ficheiros nesta etapa.

Nunca colocar valores secretos no JSON, linha de comandos, Git ou logs. O JSON
contém referências a ficheiros, não as credenciais. Erros de leitura/parsing são
genéricos e não preservam contexto do parser. O código não imprime a configuração.

## Servidor WSGI definido, não instalado nem executado

`backend/requirements-dedicated.txt` acrescenta Gunicorn 23.0.0 como dependência
opt-in. As dependências anteriores e o Dockerfile não mudam. O pin define a versão
pretendida do servidor; não constitui lock transitivo ou certificação de segurança.
Antes de qualquer instalação futura, rever a versão e produzir artefacto/lock
aprovado das dependências completas. Não instalar durante a DEV-02.

`backend/gunicorn_dedicated.conf.py` define dois workers sync, sem preload,
reload ou daemon, timeout/graceful timeout de 30 s, log de erro warning e sem
access log. O Gunicorn não interpreta headers de proxy: o middleware TrustedProxy
existente valida peer, Host, X-Forwarded-* e reconstrói HTTPS/cliente.

Forma de integração FUTURA, apenas após autorização; NÃO executada nesta entrega:

```sh
cd /home/paulo/projects/livenet-v2/backend
/caminho/do/venv-aprovado/bin/gunicorn --config ./gunicorn_dedicated.conf.py \
  "dedicated_wsgi:create_app('/caminho/absoluto/privado/dedicated.json')"
```

Bind planeado: `127.0.0.1:8000`, para um ingress no mesmo host. Não serve para
Caddy noutro contentor. A topologia Docker atual exigirá desenho/revisão separados
de bind/rede/peer antes de integração; não publicar a API para resolver isso.
Não confiar num peer só por ter sido observado numa bridge. O proxy deve substituir
os headers recebidos e impedir acesso direto/impersonação. CLI e ambiente do
processo Gunicorn são entradas administrativas confiáveis; este ficheiro não é um
sandbox contra overrides do operador. Usar ambiente controlado, sem argumentos
Gunicorn implícitos, PYTHONPATH não aprovado ou configurações adicionais.

## Comportamento e contratos preservados

- `backend/wsgi.py`, Dockerfile, requirements antigos e Compose ficam intactos.
- Não são tocados AUTH-03, F02, G2, G4, gates ou manifestos.
- Autenticação e inventário mantêm a factory de sessões lazy partilhada.
- Construir a app lê configuração/segredos, mas não cria engine/ligação, migrações,
  utilizadores, roles, grants ou ACL. Não há código PostgreSQL no entrypoint.
- Pedidos de autenticação futuros podem escrever sessões, throttle e auditoria;
  consulta de inventário não significa aplicação globalmente read-only.
- `/api/v1/health` preserva resposta de liveness, através do proxy válido.
- `/api/v1/ready` permanece 503/no-store: nenhum checker é instalado, nem simulado.
- O requisito exato f066/b12 permanece; a divergência f066/f067 não é resolvida.
- HTTPS, mesma origem, cookies, CSRF, RBAC e matriz D05 permanecem inalterados.

## Verificação offline

Usar o Python 3.12 e as dependências já presentes. Não executar a suite inteira:
há testes que abrem PostgreSQL, inclusive alguns sem marker integration.
Desativar bytecode, cache e autoload de plugins. Selecionar explicitamente os
ficheiros offline de configuração, health, security, proxy, factory e readiness.
Os novos testes usam ficheiros sintéticos em diretório temporário e Flask test
client, bloqueando sockets/processos/engines. Não iniciam servidor Gunicorn.

O carregamento por Gunicorn, parsing da configuração por esse servidor, sinais,
multiworker, sockets reais, Caddy, TLS, PostgreSQL e durabilidade de commits
requerem validação futura autorizada. Testes de doubles não comprovam operação.

Resultado DEV-02: 1135 testes passaram em 97,97 s, nos 13 ficheiros selecionados.
Python observado: 3.12.3; Gunicorn não instalado. A execução bloqueou os eventos
socket/subprocesso e as entradas de conexão psycopg, além das guardas dos testes.
Sem bytecode, cache pytest ou plugins externos; os ficheiros sintéticos ficaram
num diretório temporário exclusivo, sem limpeza de diretórios de trabalho prévios.

Comando reproduzível dos testes, na raiz do repositório (não inicia serviços):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=backend:backend/tests .venv/bin/python -B - <<'PY'
import sys
import tempfile
import pytest
import psycopg

def forbidden(*args, **kwargs):
    raise AssertionError('DEV-02: real services forbidden')

def audit(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system', 'os.posix_spawn'):
        forbidden()

sys.addaudithook(audit)
psycopg.connect = forbidden
psycopg.Connection.connect = forbidden
psycopg.AsyncConnection.connect = forbidden
names = (
    'dedicated_entrypoint', 'dedicated_backend', 'trusted_proxy', 'readiness_contract',
    'config', 'health', 'security_policy', 'security_api', 'security_service',
    'inventory_api', 'inventory_schemas', 'inventory_service', 'readiness_postgres',
)
raise SystemExit(pytest.main([
    '-q', '-p', 'no:cacheprovider', '--basetemp', tempfile.mkdtemp(prefix='livenet-dev02-'),
    *['backend/tests/test_' + name + '.py' for name in names],
]))
PY
```

## Pré-requisitos para ativação futura

1. Rever e integrar a base de fontes local, incluindo os ficheiros anteriores
   não versionados. Esta tarefa não faz commit nem regenera manifestos.
2. Rever dependências e preparar ambiente/artefacto aprovado; Gunicorn não existe
   no ambiente observado. Não há imagem dedicada construída nesta entrega.
3. Aprovar destino, role runtime, transporte PostgreSQL e segredos. A factory atual
   não configura TLS verify-full/CA; não alegar transporte TLS validado nem usar
   variáveis libpq como atalho para esse requisito. Se exigido pelo contrato do
   destino, a implementação/revisão desse transporte precede a ativação.
4. Concluir schema security, ACL mínimas, conta inicial e recuperação numa etapa
   própria autorizada. Não usar bootstrap como runtime. A factory valida nomes e
   forma de destino; não atesta identidade física do servidor ou privilégios.
5. Implementar/validar checker real pelas fronteiras aprovadas; até lá readiness
   é negativa. Não substituir por SELECT 1 ou por booleano de configuração.
6. Rever topologia ingress/rede e integrar Caddy, cujo 503 atual fica preservado.
7. Validar o percurso completo numa infraestrutura isolada autorizada antes de
   disponibilizar o serviço. Este documento não concede essa autorização.

## Reversão

Como não há ativação nem edição de ficheiros anteriores, não há estado operacional
a reverter. Para retirar a DEV-02 após revisão, remover apenas os cinco ficheiros
novos desta entrega: dedicated_wsgi.py, gunicorn_dedicated.conf.py,
requirements-dedicated.txt, tests/test_dedicated_entrypoint.py (em backend/) e este
documento. Conferir que não receberam alterações posteriores antes de os remover.
Não usar git reset/clean nem remover o restante trabalho local. O percurso antigo
continua disponível exatamente como antes; não o iniciar como parte da reversão.
