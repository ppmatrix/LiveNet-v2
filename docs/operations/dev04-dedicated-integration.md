> Atualização DEV-05B (2026-10-25): empacotamento e integração HTTP isolada
> validados; ativação continua bloqueada. Evidência e limites em
> [dev05b-isolated-integration](dev05b-isolated-integration.md). O texto anterior segue preservado.

# DEV-05A — Revisão estática DEV-04 e política de acesso interno

Data: 2026-10-25, progbox, branch main, HEAD
`647179c928888adfeef0f69f582fd13c5fc17350`. Revisão dos artefactos sem os executar.
Este documento é a única exceção documental entre os oito ficheiros DEV-04,
expressamente autorizada pelo pedido DEV-05A §4; os sete ficheiros técnicos não
são corrigidos, reformatados ou executados. O texto original DEV-04 está
preservado integralmente depois desta atualização.

## Decisões humanas e resultado

- `DEV-03C-D01`: Opção A aprovada no pedido DEV-04, anexo
  `c94f7ffa-8d9e-4c05-af09-4cb20da87eb6/Pasted text.txt`, reiterada no pedido
  DEV-05A. Aprova arquitetura de referência/preparação, não ativação.
- `DEV-05A-D01`: acesso **exclusivamente interno ao laboratório**, aprovado pelo
  responsável em 25/10/2026 conforme pedido DEV-05A §1, anexo
  `adee713c-cd23-4bfd-a10e-c48de86c556e/Pasted text.txt` desta conversa. A UI/API
  só pode ser alcançada por redes internas explicitamente autorizadas em DEV,
  STAGING, PROD-VM e PROD-K8S. Sem IP público, entrada Internet por port forwarding,
  Cloudflare Tunnel ou equivalente. Caddy só publica HTTPS em interface/endereço
  interno aprovado, com firewall restrito às redes autorizadas. Backend/PG/Redis/
  auxiliares sem exposição externa; K8S com ingress interno, sem LoadBalancer
  público. Saídas são avaliadas separadamente; exceção só por decisão explícita
  do responsável. HTTPS, auth/RBAC, auditoria, CSRF/cookies/sessões mantêm-se.

Fontes e âmbito: [registo de decisões](../architecture/decision-register.md).
O ID LAN-only não renumera D-01–D-52. RFC1918/hostname não comprovam isolamento:
interfaces, firewall host/Docker/perímetro, routing/NAT IPv4/IPv6, VPNs, túneis e
outros percursos de entrada precisam de inventário e evidência. Egress não implica
permissão de ingress. Uma VPN não aprovada não autoriza acesso por conveniência.

Resultado: **BLOCKED para build do contexto real e ativação**. Parsing nativo
continua reservado a DEV-05B, mediante autorização própria e limites abaixo.
Não foi identificado defeito crítico demonstrado nesta leitura; não se certifica
ausência de exposição em runtime porque os serviços/redes não foram consultados.

## Revisão de cada artefacto DEV-04

As linhas citadas são dos sete ficheiros técnicos preservados, não do arquivo
documental cujo offset muda com esta adição. Caminhos relativos à raiz do repo.

| Artefacto | Conclusão estática | Limite / achado |
| --- | --- | --- |
| [Dockerfile.dedicated](../../backend/Dockerfile.dedicated):3–19 | ARG para base; requirements+constraints; cópia do entrypoint real; USER 10001:10001; CMD Gunicorn; sem flask run, import RUN, DDL ou provisionamento | Base/digests e distribuição por validar (R05); COPY app depende do contexto alargado (R02). EXPOSE não publica host. |
| [Dockerfile.dedicated.dockerignore](../../backend/Dockerfile.dedicated.dockerignore):1–9 | Inicialmente exclui tudo e depois reabre app | R02: !app/**/ não é restrição só a diretórios; a afirmação histórica de allowlist Python não está garantida. |
| [gunicorn_container.conf.py](../../backend/gunicorn_container.conf.py):7–24 | Bind no namespace, 2 workers sync, 1 thread, 30 s, tmp, logs warning sem access; forwarded desativado | Config compatível por inspeção com entrypoint; sem parsing Gunicorn ou carga/SSE; não prova prontidão. |
| [requirements-container.constraints.txt](../../backend/requirements-container.constraints.txt):1–18 | Pins candidatos explícitos; psycopg e binary alinhados; Gunicorn herdado de DEV-02 | R05: sem hashes, resolução/wheels, proveniência completa ou auditoria de versões. Não instalar para verificar nesta etapa. |
| [compose.dedicated.yaml](../../compose.dedicated.yaml):5–71 | web edge/api, backend api/data, db data; volumes próprios, só web com ports, perfil/exit 78 nos três | R01/R04: host_ip obrigatório não impõe LAN, firewall ausente, parâmetros e mounts não atestados. Sem parsing Compose, endpoints ou recursos criados. |
| [Caddyfile](../../infra/dedicated/Caddyfile):13–45 | Mesma origem HTTPS, API e UI em handles separados, política de headers explícita, sem Origin/Referer reescritos | R01/R03: hostname não é ACL cliente; sem teste Caddy real do routing, wildcard, headers/TLS ou comportamento externo. |
| [test_dedicated_packaging.py](../../backend/tests/test_dedicated_packaging.py):31–242 | Checks estruturais, factories/recusas e TestClient com peer sintético; limites do oráculo declarados | R02/R03: igualdade textual protege configuração errada; parser JSON não é Compose; oráculo Python não executa Caddy. Não executado nesta revisão. |
| Documento DEV-04, arquivo abaixo | Explica bloqueio, pendências e 570 testes offline; não alegava ativação | Complementado aqui: LAN-only vinculativa e revisão crítica. Declarações históricas de ausência de não-Python no contexto são intenção refutada por R02, não garantia atual. |

Nenhum ficheiro de segredo real foi criado/lido. Os COPY não nomeiam credenciais
ou certificados privados, mas isso não prova a exclusão de tais ficheiros se
existirem dentro de app. Não foi construída/inspecionada uma imagem final.

## Achados classificados e evidência

### DEV-05A-R01 — ALTA: enforcement LAN-only ainda não implementado/demonstrado

Compose:17 aceita qualquer valor não vazio em DEV04_HTTPS_BIND_IP; não valida IP
interno aprovado. Rede edge:69 não define ACL de clientes. Caddy:13–45 não tem
restrição de redes cliente: um cliente que consiga chegar ao listener e usar o
hostname esperado não é recusado só por ser externo. TrustedProxy confere o
peer Caddy/headers e não a autorização de rede do browser.

Impacto: se os bloqueios forem retirados com IP/interface inadequados ou houver
NAT/túnel/routing externo, UI/login/API podem ser alcançados contra DEV-05A-D01.
O risco é condicional à futura operação; não houve prova de exposição atual.
Necessário antes de ativar: endereço/interface e redes autorizados, firewall
efetivo e ausência de percursos Internet comprovados em escopo próprio. Não
basta adicionar is_private, hostname, origem HTTPS ou aceitar qualquer RFC1918.

### DEV-05A-R02 — ALTA: exceção dockerignore reabre app sem limitar a Python

Ignore:2–4 contém !app/, !app/**/ e !app/**/*.py. Docker ignora barras finais;
assim a exceção recursiva reabre também ficheiros não Python. COPY app:13 copia
o diretório incluído. Há 13 .pyc preexistentes em app, identificados só por
metadados/caminhos. O teste:55–69 verifica a própria lista de regras, não a
seleção efetiva: pode passar mesmo quando a política pretendida falha.

Impacto: bytecode/dados/credenciais ou certificados eventualmente colocados sob
app podem entrar no contexto e imagem. Não se encontrou segredo nem se executou
matcher/build para demonstrar uma imagem contaminada. Evidência estática e
referência de semântica: [Docker, dockerignore](https://docs.docker.com/build/concepts/context/#syntax).
Bloquear build/envio do contexto real até uma correção autorizada e verificação
efetiva de inclusão/exclusão. Não se corrige esse ficheiro ou teste na DEV-05A.

### DEV-05A-R03 — MÉDIA: testes sem semântica nativa permitem falsos positivos

Testes:31–34 leem JSON; 55–69 comparam instruções/texto; 161–177 removem e
reconstroem headers em Python; 180–211 procuram strings e entregam o resultado
ao Flask TestClient. Uma diretiva no contexto errado ou configuração nativa
inválida pode conservar strings esperadas e não ser detetada. O TestClient
verifica o middleware real com dados sintéticos, não proxy, peer TCP ou TLS.

Testes ausentes: matcher/contexto com não-Python/bytecode/sentinelas não secretas,
parsing nativo, headers repetidos/capitalização no proxy real, seleção de site/
Host/porta, API versus fallback SPA, TLS, peer após restart e ataques de rede.
570 pass históricos não comprovam estes requisitos. Parsing e comportamento real
são etapas distintas; não executar os testes de aplicação na presente revisão.

### DEV-05A-R04 — MÉDIA: presença de parâmetros não prova coerência/identidade

Compose:24/39–41/54–62/70–71 requer valores mas não valida subnet/peer, paths
absolutos, owner/mode/regularidade, relação JSON→db ou separação efetiva das roles.
Diretórios/nomes/digests são entradas administrativas ainda não aprovadas.
Factory e entrypoint mantêm recusas reais, mas algumas só surgem ao construir
app/abrir uma sessão; não atestam privilégio ou identidade física PostgreSQL.

Necessário: verificar cruzamentos e montagens/UID vistos no namespace, parâmetros
coerentes e roles mínimas em etapas autorizadas. Não criar credenciais ou mudar
ACL para ultrapassar uma recusa. Caddy volume/PG/admin também precisam de ownership
e ciclo de vida próprios; rootless/userns não podem ser presumidos equivalentes.

### DEV-05A-R05 — MÉDIA: reprodução e supply chain continuam candidatas

Dockerfile:3–10 permite base fornecida por ARG e pip com constraints sem hashes;
constraints:1–18 não são wheelhouse nem prova de resolução/transitivos. O teste
72–89 verifica apenas versões diretas e alguns pins. Nomes de variáveis não
validam digest, versão ou proveniência de Python/Caddy/PG/backend.

Necessário: artefactos confiáveis por digest e dependências completas verificadas
antes de build; egress/downloads, se necessários, têm aprovação separada. Nada
autoriza Docker socket, credenciais de registry ou rede operacional na build.
Não se afirma vulnerabilidade específica ou atualização de versão sem evidência.

## Checks independentes e limites da evidência

| Verificação existente | O que sustenta | O que não sustenta |
| --- | --- | --- |
| Leitura de redes/ports/entrypoints | Papéis do grafo e ausência de ports backend/PG no descriptor | Isolamento real, firewall, routing, LAN-only ou execução de exit 78. |
| Recusas da factory/TrustedProxy em TestClient | Regras reais sob inputs/segredos sintéticos | Peer real, origem da conexão, TLS ou credenciais/ACL do destino. |
| Igualdade com configuração Gunicorn anterior | Preservação textual de parâmetros selecionados | Parser/versão/arranque Gunicorn e efeitos reais. |
| Oráculo declarado de headers | Compatibilidade pretendida entre allowlist e middleware | Semântica Caddy; não é verificação independente da mesma política. |
| Comparação de hashes inicial/final | Preservação dos ficheiros inventariados | Ausência histórica de defeitos, segurança de dependências ou ambiente operacional. |

DEV-05A não executou pytest, código do projeto, Docker, Compose, Caddy, Gunicorn,
build, instalação, serviços, PostgreSQL ou migrações. Só houve leitura/análise,
atualização documental, referências/whitespace e comparação de integridade.

## Bloqueios e critérios propostos para DEV-05B

Sem autorização de iniciar DEV-05B. Uma autorização futura deve separar:

1. **Parsing nativo local**: ferramentas/versões e comandos revistos; parâmetros
   e ficheiros sintéticos, sem segredos/volumes/configuração de produção; sem
   portas/servidores/PG; temporários isolados e output sanitizado. Operações que
   importem a factory ou provisionem PKI não podem ser tratadas como leitura
   inocente: limitar efeitos e bloquear rede expressamente no escopo autorizado.
2. **Build isolada**: primeiro resolver R02 em tarefa autorizada e comprovar
   contexto limpo/exclusão efetiva; fixar bases/digests/dependências/proveniência;
   aprovar egress ou disponibilizar bundle offline; sem Docker socket dentro da
   imagem, segredos reais, contacto PostgreSQL ou publicação/ativação resultante.
   Artefactos e conteúdo da imagem exigem verificação, não só build terminada.
3. **Integração operacional posterior**: outro pedido, após enforcement LAN-only
   e resolução dos pré-requisitos abaixo. Nem parsing nem build autorizam retirar
   exit 78, iniciar serviços, inicializar PG ou aprovar runtime por associação.

R01 bloqueia ativação, não uma análise sintática sem listeners. R02 bloqueia
build/envio do contexto real, não a leitura de um Dockerfile. R03–R05 limitam
o significado de PASS e exigem plano de validação. Nada concede aprovação aqui.

Permanecem f066/f067, manifesto AUTH-03 divergente, F02/G2/G4/gates, readiness real
indisponível, privilégio runtime, conta administrativa inicial, recuperação
independente, PostgreSQL/TLS, peer Caddy, montagem/ownership de segredos e exposição
de rede/firewall não validados. As 28 lacunas G4/L02 e demais originais históricos
SOURCE_NOT_LOCATED continuam abertos; não foram reconstituídos ou encerrados.

## Arquivo integral DEV-04 — não constitui instrução de execução DEV-05A

Os comandos de testes abaixo são documentação histórica e não foram executados
nesta revisão. Menções a acesso externo/edge não autorizam Internet e ficam
subordinadas a DEV-05A-D01. A intenção histórica de allowlist só Python está
qualificada pelo achado R02 acima. Nenhuma correção técnica foi aplicada.

# DEV-04 — Empacotamento dedicado e integração exclusivamente offline

Base: progbox, `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`.
DEV-03C-D01 aprova a Opção A segundo o pedido humano DEV-04, anexo
`c94f7ffa-8d9e-4c05-af09-4cb20da87eb6/Pasted text.txt` desta conversa.
O âmbito autorizado é preparação e testes offline. Não inclui build, instalação,
arranque, publicação, provisionamento PostgreSQL ou modificação de contratos.

## Estado: BLOCKED para ativação

Não estão aprovados/verificados os destinos, identidades runtime/administrativas,
ACL, rede/peer, montagem de segredos, TLS e recuperação. O Compose foi mantido
deliberadamente não operacional:

1. Todos os parâmetros externos usam `${DEV04_...:?...}`, sem defaults operacionais.
2. Todos os serviços pertencem ao profile `dev04-blocked`, sem arranque por omissão.
3. Os **três entrypoints são `/bin/sh -c 'exit 78'`**: mesmo preenchendo parâmetros
   e selecionando o profile, Caddy, Gunicorn e PostgreSQL não arrancam por este
   descriptor. Nenhum `ALLOW_*` ou variável desbloqueia estes entrypoints.

A retirada destas recusas exige revisão/alteração posterior expressamente
autorizada; não é instrução de ativação nem um gate AUTH-03/G4 alternativo.
Um operador com controlo de Docker pode substituir entrypoints: o ficheiro não
é sandbox contra administração hostil. Invocar Compose ainda poderia criar
contentores/redes/volumes ou desencadear build, mesmo que os processos falhem;
**não executar up/create/run/build nem considerar esse ato uma verificação offline**.

## Oito ficheiros novos

| Ficheiro | Responsabilidade |
| --- | --- |
| [Dockerfile.dedicated](../../backend/Dockerfile.dedicated) | Imagem backend opt-in; factory DEV-02; Gunicorn; UID/GID 10001; nenhuma migração/provisionamento. |
| [Dockerfile.dedicated.dockerignore](../../backend/Dockerfile.dedicated.dockerignore) | Contexto allowlist: fontes Python runtime e dependências/config do servidor; sem dados/segredos/testes/migrações. |
| [gunicorn_container.conf.py](../../backend/gunicorn_container.conf.py) | Bind acessível no namespace, mantendo política de proxy da aplicação. |
| [requirements-container.constraints.txt](../../backend/requirements-container.constraints.txt) | Versões candidatas exatas, sem alterar requirements anteriores. |
| [compose.dedicated.yaml](../../compose.dedicated.yaml) | Descriptor independente, três serviços bloqueados, três redes, dois volumes persistentes. |
| [Caddyfile dedicado](../../infra/dedicated/Caddyfile) | API privada e UI na origem atual; política explícita de headers, não executada. |
| [test_dedicated_packaging.py](../../backend/tests/test_dedicated_packaging.py) | Estrutura, isolamento, recusas e oráculo offline de headers. |
| Este documento | Contratos, bloqueios, testes e reversão. |

Nenhum Dockerfile, Compose, Caddyfile, factory, middleware, requisito ou teste
anterior é editado. A baseline DEV-03B permanece tal como estava, sujeita à sua
revisão humana. Não se atualiza o registo central como efeito desta tarefa.

## Topologia descrita, não executada

```text
Browser -- HTTPS aprovado:8443 --> web (Caddy + UI)
                                     | edge: acesso externo planeado
                                     | api: rede interna, peer IPv4 explícito
                                     v
                                backend:8000
                                     | api + data; sem porta no host
                                     v
                                  db:5432
                                     data: rede interna; sem porta no host
```

`edge` pertence só ao web, permite desenhar a entrada/saída do ingress sem exigir
rota externa na rede interna `api`. Caddy não participa em `data`; PostgreSQL só
participa em `data`. Backend usa apenas `api` e `data`. Não há redes externas,
serviços antigos, includes, extends, depends_on ou Docker socket. Workers/Redis
não são acrescentados neste incremento. Host/administradores Docker continuam
fora da garantia de isolamento destas bridges.

Só web descreve publicação TCP 8443, em IP obrigatório por aprovar. Nenhum IP do
host/subnet/peer foi alocado ou observado automaticamente. O IP de web em `api`
é explícito; `PROXY_PEERS` no JSON externo deve conter exatamente esse peer,
após verificação futura. Nomes Docker servem para encaminhamento (`backend`, `db`),
não para provar identidade. Não alargar peers a CIDR/wildcard, nem reutilizar IPs
de outros ensaios.

Volumes `postgres_data` e `caddy_data` são declarados e recebem o namespace do
projeto obrigatório. Não usam volumes externos ou nomes globais fixos. Projeto,
volumes e redes têm de ser distintos do v1, base original e todos os ensaios.
Nenhum volume foi criado ou eliminado.

## Imagem, dependências e Gunicorn

Base pretendida: CPython 3.12 slim Linux. `DEV04_PYTHON_IMAGE` não tem default;
é necessária referência/digest aprovada antes de construir. Caddy 2.11.7 e
PostgreSQL 16 são linhas pretendidas; os digests continuam pendentes. Os nomes
das variáveis não validam formato ou versão de uma imagem: revisão independente
tem de conferir artefactos e digests. `pull_policy: never` evita aquisição implícita.

O Dockerfile copia os requirements já existentes e aplica constraints candidatas.
Gunicorn 23.0.0 mantém o pin DEV-02, sem instalação local. As restantes versões
foram lidas de metadata já instalada na progbox: Flask 3.1.3, Werkzeug 3.1.9,
Jinja2 3.1.6, MarkupSafe 3.0.4, click 8.5.0, blinker 1.9.0, itsdangerous 2.2.0,
SQLAlchemy 2.1.4, typing_extensions 4.16.0, Alembic 1.20.0, Mako 1.4.3,
psycopg/psycopg-binary 3.3.6 e packaging 26.3.

Estas constraints restringem versões sem substituir os contratos de requirements.
Não são wheelhouse, lock com hashes, auditoria de vulnerabilidades ou prova de
disponibilidade/compatibilidade das wheels. Não houve resolução/download. A
reprodução completa depende de base/digests e dependências transitivas/artefactos
revistos em etapa própria. A instrução pip só seria executada num build futuro
autorizado; não exige PostgreSQL, mas pode exigir um repositório de pacotes ou
bundle aprovado. Não se promete build sem rede ou bit-identical nesta entrega.

As fontes da aplicação são copiadas depois da instalação; nenhum RUN importa
o projeto, chama Alembic, lê segredo ou contacta PostgreSQL. Não são incluídas
migrações nem executores administrativos. `USER 10001:10001` é numérico, sem
necessidade de criar conta PostgreSQL ou utilizar bootstrap.

Comando descrito: Gunicorn carrega `gunicorn_container.conf.py` e
`dedicated_wsgi:create_app('/run/livenet/backend.json')`. Bind `0.0.0.0:8000`
refere-se ao namespace do contentor, sem publicação backend no host. Mantêm-se
dois workers sync, uma thread, timeout e graceful timeout 30 s, sem preload,
reload/daemon/access log; tmp/heartbeat em `/tmp`. Root filesystem é read-only
no Compose, tmpfs limitado e capabilities removidas. Não há reinterpretação de
headers Gunicorn: secure_scheme_headers vazio, forwarded_allow_ips vazio,
forwarder_headers vazio e proxy_protocol falso. SSE continua sem avaliação.

Não se adiciona healthcheck que falsifique peer/headers ou readiness. As probes
reais exigem desenho próprio, pois TrustedProxy protege todas as rotas.

## Caddy, mesma origem e política de headers

O ficheiro novo preserva origem `https://livenet-v2.home.arpa:8443`, TLS interno
planeado, sem instalação automática de confiança, admin/autosave desativados e
UI com fallback restrito. `/api/v1` e descendentes seguem para `backend:8000`,
sem remover o prefixo e sem converter erros da API em index.html.

Na rota API, antes de reverse_proxy, removem-se Forwarded e X-Forwarded-* recebidos.
Depois são definidos Host/X-Forwarded-Host exatos, X-Forwarded-Proto=https,
X-Forwarded-Port=8443 e X-Forwarded-For com o IP remoto da ligação recebida por
Caddy, não uma afirmação encaminhada pelo cliente. Não há trusted_proxies,
reescrita de Origin/Referer, CORS ou bypass TLS. A aplicação continua a validar
CSRF, origem e autorização. Um proxy adicional a montante exigiria revisão.

O upstream HTTP fica descrito para a rede privada desta proposta, não é prova
de encriptação interna. Se a política exigir TLS Caddy→API, rever esse transporte
explicitamente antes de ativação. Preservar a autoridade externa também nessa
evolução. Não confundir TLS browser→Caddy, transporte API→PostgreSQL e PKI G4.
O Caddyfile anterior permanece com a recusa 503; este ficheiro é outro percurso.

## Parâmetros externos pendentes

O Compose usa JSON, subconjunto compatível com YAML, para poder ser lido por um
parser stdlib nos testes sem instalar PyYAML. Não foi validado pelo parser Compose.
Todas as variáveis abaixo são obrigatórias e não contêm valores secretos:

| Parâmetro | Aprovação/verificação necessária |
| --- | --- |
| DEV04_PROJECT | Nome exclusivo do novo ambiente, não um projeto protegido existente. |
| DEV04_PYTHON_IMAGE | Base Python 3.12 slim por digest, arquitetura e proveniência aprovadas. |
| DEV04_BACKEND_IMAGE | Identificação do artefacto dedicado; confirmar conteúdo/entrypoint, não usar a imagem antiga. |
| DEV04_CADDY_IMAGE / DEV04_POSTGRES_IMAGE | Versões pretendidas e digests efetivos aprovados. |
| DEV04_HTTPS_BIND_IP | Interface de publicação permitida e porta 8443 disponível, DNS/confiança revistos. |
| DEV04_API_SUBNET / DEV04_DATA_SUBNET | Subnets distintas, sem conflito, redes privadas com membros controlados. |
| DEV04_CADDY_IPV4 | IP exato do ingress na API, dentro da subnet aprovada; conferir peer real após ensaio autorizado. |
| DEV04_FRONTEND_DIST | Caminho absoluto para build revisto; index.html e assets consistentes, sem segredos VITE. |
| DEV04_BACKEND_CONFIG | JSON privado externo e completo da DEV-02, caminho absoluto. |
| DEV04_RUNTIME_PASSWORD_FILE / DEV04_CSRF_KEY_FILE | Caminhos absolutos de ficheiros distintos, pertencentes ao UID 10001 visto no contentor. |
| DEV04_DB_NAME | Nome/base dedicada aprovados; não livenet, sem reutilização automática de dados. |
| DEV04_DB_BOOTSTRAP_ROLE / DEV04_PG_ADMIN_PASSWORD_FILE | Identidade/credencial administrativa separada, exclusivamente montada em db; não runtime. |

O JSON backend **não expande variáveis de ambiente**. Um operador autorizado
deve preparar os valores coerentes fora do repositório, não copiar placeholders:
ENVIRONMENT=production, DATABASE_HOST=db, DATABASE_PORT=5432, nome aprovado
igual ao destino, DATABASE_USER=role runtime aprovada (nunca bootstrap),
DATABASE_PASSWORD_FILE=/run/livenet/runtime_password,
SECURITY_CSRF_KEY_FILE=/run/livenet/csrf_key, SECURITY_ENABLED=true,
PROXY_ENABLED=true, origem exata atual e PROXY_PEERS=[IP exato aprovado do web].
Todos os onze campos são obrigatórios no entrypoint; nenhuma conta é criada.

## Montagens e procedimento administrativo ainda não executado

Não criar os ficheiros reais durante DEV-04. Na etapa administrativa autorizada:

1. Preparar diretórios externos controlados e ficheiros regulares sem symlink
   final, conteúdo permitido e até 16 KiB, configuração JSON e chave CSRF conforme
   DEV-02 (chave com pelo menos 32 caracteres). Não imprimir valores.
2. Atribuir owner equivalente ao UID/GID runtime 10001 no namespace escolhido e
   permissões privadas (por exemplo 0600; sem acesso de grupo/outros). Rootless ou
   userns-remap exigem conferir o mapeamento; não assumir UID host igual.
3. Montar cada ficheiro read-only nos caminhos fixos acima. create_host_path=false
   evita criar origens ausentes; interpolação de caminho não certifica absoluto,
   regularidade, UID ou modo. Verificar tudo no contexto real antes de ativação.
4. Não confiar em uid/mode de secrets file-based do Compose para remapear o host.
   Esta entrega usa binds explícitos e não altera permissões de ficheiros reais.
5. Preparar ownership do volume PKI Caddy para UID 10002 e diretórios de dados
   PostgreSQL/credencial administrativa segundo a imagem/identidade aprovadas.
   O UID/arranque administrativo de PostgreSQL não foi escolhido nem validado;
   não usar o UID backend para o bootstrap ou alterar permissões do volume por
   tentativa. O entrypoint oficial PostgreSQL continua bloqueado e a sua futura
   inicialização exigirá autorização própria, pois pode criar base/contas/dados.
6. Definir rotação e remontagem/restart controlados; não presumir que substituição
   do ficheiro no host atualiza uma montagem existente. Chaves coerentes por
   ambiente/réplicas e impacto em CSRF/throttle devem ser revistos.

## PostgreSQL, readiness e contratos preservados

Não foi executado SQL, Alembic, provisioning, backup ou recuperação. O descriptor
de db contém referências administrativas futuras, não utilizadores provisionados.
Não monta essa credencial no backend e não fornece grants/DDL automáticos.
SCRAM descrito para inicialização futura não comprova TLS. A factory atual não
fornece verify-full/CA; essa parte da integração fica interrompida/bloqueada até
decisão e implementação próprias, sem modificar a factory na DEV-04.

Permanecem: cadeias/ledgers Alembic independentes; owner/migrator/admin/runtime
separados; mínimo privilégio D05; divergência f066/f067; AUTH-03/manifesto divergente;
F02/G2/G4 e gates desativados; recuperação/exclusividade não demonstradas. G4D-09
não é satisfeito pelo nome db nem por URL SQLAlchemy. Não criar checker real ou
simulado aqui. A factory continua lazy e readiness 503 sem evidência válida.

As 28 lacunas G4/L02 continuam abertas conforme o [registo](../architecture/decision-register.md),
com enumeração SOURCE_NOT_LOCATED. Opção A foi aprovada; parâmetros/destinos,
privilégios, TLS, montagem/peer, origin por ambiente e ativação não foram aprovados
por consequência dessa escolha. Gunicorn iniciado não seria prova de prontidão.

## Testes offline e limites

Os testes novos leem Dockerfile/ignore, JSON Compose e Caddyfile; carregam apenas
configurações Python literais e a factory/test client offline. Verificam allowlist,
entrypoint/UID, versões candidatas, redes, portas, parâmetros sem defaults,
recusa dos três serviços, montagens, percurso anterior e recusas da aplicação.

Resultado final: **570 testes passaram em 5,53 s**, nos nove ficheiros selecionados
abaixo. A execução inicial teve 569 pass e uma falha no teste novo: a expressão
dos nomes de variáveis não aceitava o dígito de DEV04_CADDY_IPV4. Corrigido apenas
esse teste, a seleção completa passou. Sem alterações aos artefactos para resolver
a falha, sem skips e sem execução de serviços reais. Fixtures usam diretório
temporário exclusivo; bytecode, cache pytest e plugins externos desativados.

O teste de headers usa um **oráculo limitado da política declarada**, extrai e
confere a allowlist e passa o resultado ao TrustedProxy real pelo Flask test
client. Cobre claims forjados, peer errado, preservação de Origin/Referer, CSRF,
health e readiness negativa. Não é parser Caddy, não executa reverse_proxy e não
comprova a semântica real das diretivas, ordem no motor HTTP ou peer TCP.

Caddy, Gunicorn e PyYAML não estavam disponíveis no preflight; nada foi instalado.
Não houve parsing nativo Docker/Compose/Caddy/Gunicorn, build, download, servidor,
TLS, DNS, ponte Docker, PostgreSQL ou testes de durabilidade. Essas validações
continuam obrigatórias em etapa separada autorizada, incluindo ataque de headers
num Caddy real e reconfirmação da origem/peer após restart.

Comando dos testes permitidos, na raiz (bloqueia sockets/subprocessos/psycopg):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=backend:backend/tests .venv/bin/python -B - <<'PY'
import sys
import tempfile
import pytest
import psycopg

def forbidden(*args, **kwargs):
    raise AssertionError('DEV-04: real services forbidden')

def audit(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system', 'os.posix_spawn'):
        forbidden()

sys.addaudithook(audit)
psycopg.connect = forbidden
psycopg.Connection.connect = forbidden
psycopg.AsyncConnection.connect = forbidden
names = ('dedicated_packaging', 'dedicated_entrypoint', 'dedicated_backend',
         'trusted_proxy', 'readiness_contract', 'config', 'health',
         'security_policy', 'security_api')
raise SystemExit(pytest.main([
    '-q', '-p', 'no:cacheprovider', '--basetemp', tempfile.mkdtemp(prefix='livenet-dev04-'),
    *['backend/tests/test_' + name + '.py' for name in names],
]))
PY
```

## STAGING, PROD-VM, Kubernetes e reversão

Promover artefactos revistos por digest, com parâmetros/segredos/dados próprios
por ambiente. A origem fixa atual não serve nomes arbitrários; rever essa evolução
sem CORS/bypass CSRF. Não reutilizar volumes/roles de DEV/ensaios em STAGING/PROD.
Não há CI/CD, backup ou deployment completo implementado por este pacote.

K8S pode reutilizar a imagem e contratos de domínio, mas exige rever confiança do
ingress dinâmico, montagem regular/UID dos segredos, sessão/chaves entre réplicas,
pools, probes, storage/HA e recuperação. IP fixo Compose não é desenho K8S aprovado.
Migrações ficam fora do startup; não confiar em latches em memória para multi-nó.

Não houve estado operacional a reverter. Para retirar DEV-04, rever alterações
posteriores e remover **apenas os oito ficheiros novos enumerados**, preservando
todo o trabalho anterior. Não usar reset/clean, não eliminar volumes, não iniciar
o backend antigo como parte do rollback. Se houver futura ativação autorizada,
a respetiva reversão precisa de plano próprio para processos, PKI e dados.

Recomendação DEV-05: revisão independente offline do pacote e fixação dos
artefactos/condições pendentes; preparar escopo próprio para parsing nativo e
build isolada sem PostgreSQL. Ativação real exige ainda fechar transporte,
identidade/ACL, recuperação, migrações/conta/checker e peer/TLS com autorização
específica. Esta entrega não inicia DEV-05 ou qualquer operação.
