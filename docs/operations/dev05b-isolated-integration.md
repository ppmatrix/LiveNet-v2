# DEV-05B — integração dedicada isolada

Data: 2026-10-25. Estado: empacotamento e integração HTTP isolada demonstrados;
ativação operacional bloqueada. Esta evidência sucede à DEV-05A, sem reescrever
os seus resultados históricos nem aprovar automaticamente documentos anteriores.

## Resultado e fronteiras

A imagem dedicada Flask/Gunicorn foi construída e inspecionada. Compose e Caddy
foram validados nativamente. O ensaio real utilizou três redes Docker internas,
nenhuma porta publicada, ficheiros sintéticos e PostgreSQL 16 em tmpfs. Foram
verificados health 200, readiness 503, autenticação/inventário anónimos 401, CSRF,
recusa de peer direto não autorizado, headers do proxy e reinício do backend.

Isto não demonstra login persistente, inventário autenticado, TLS PostgreSQL,
privilégios runtime, migrações aprovadas, recuperação ou prontidão de produção.
O frontend do ensaio é uma sentinela HTML sintética: apenas o routing foi testado.
O PostgreSQL temporário inicializa exclusivamente a sua base/identidade de
bootstrap sintética; não foram provisionados utilizadores aplicacionais, executado
SQL administrativo manual, migrados schemas nem alteradas ACL existentes.

## Achados DEV-05A

| Achado | Alteração e evidência | Limite que permanece |
|---|---|---|
| R01 — LAN-only | `Caddyfile` aplica `remote_ip` antes de todos os handlers, dentro de `route`; `strict_sni_host on`; CIDRs obrigatórios em Compose; preflight recusa bind público/wildcard/loopback, redes públicas e parâmetros fora da política explícita. Clientes não autorizados recebem 403 em HTTPS real. | A política candidata não prova autorização humana, interfaces, firewall, routing, NAT ou ausência de túneis. Ativação continua bloqueada até atestação operacional. RFC1918 não é prova suficiente. |
| R02 — contexto | Removidas as exceções de diretório `!app/` e `!app/**/`; apenas Python runtime e ficheiros explícitos. BuildKit exportou o contexto real: 39 ficheiros exatos, hashes iguais. Contexto adversarial: 40, incluindo Python aninhado necessário e excluindo sentinelas `.env`, `.pem`, `.pyc` e ficheiros na raiz. | A allowlist permite fontes `.py`; exige revisão de código para evitar segredos embebidos em código. Não autoriza build remoto. |
| R03 — ferramentas reais | Parsing Compose v5.1.3, Caddy real, HTTPS com CA temporária validada, headers repetidos/case/forjados, Origin/Referer preservados, routing API/SPA, Host divergente, Gunicorn real e reinício. | Tráfego testado em HTTP/1.1; não foi demonstrada uma sessão HTTP/2, nem foi utilizado o frontend de produção. |
| R04 — coerência | `scripts/dedicated/preflight.py` valida IPAM, sobreposição/reservas, endereço utilizável do proxy, correspondência exata de `PROXY_PEERS`, base/roles separadas, caminhos absolutos, ficheiros regulares sem symlinks, UID/modo e inodes distintos; conteúdo JSON montado corresponde ao validado. Montagens reais sintéticas passaram. | Não atesta identidades físicas PostgreSQL, ACL, ownership dos objetos, CA/hostname PostgreSQL ou permissões de uma instalação real. O inventário de redes reservadas deve ser completo. |
| R05 — dependências | 15 wheels resolvidos no PyPI, versões transitivas e SHA256 fixos; metadados oficiais confirmam hashes. Build usa `--only-binary`, `--require-hashes` e `pip check`. Bases por digest registadas. | Lock apenas CPython 3.12/Linux x86_64; sem promessa multiarch, assinatura, SBOM ou auditoria de vulnerabilidades. Digests não equivalem a aprovação operacional. |

## Correções adicionais encontradas pelo runtime

A imagem Caddy de origem inclui `cap_net_bind_service=ep` no binário. Com
`cap_drop: ALL`, o exec falha com EPERM. `infra/dedicated/Dockerfile.caddy`
remove a file capability; não instala pacotes, não concede capabilities e mantém
UID 10002, porta 8443, filesystem read-only e `no-new-privileges`.

O Gunicorn 23 rejeita `forwarder_headers = []` em configuração Python. Os dois
ficheiros Gunicorn dedicados passaram a usar a string CSV vazia, que o servidor
valida para lista vazia. O bind local continua 127.0.0.1:8000; o bind de contentor
continua 0.0.0.0:8000. `secure_scheme_headers`, `forwarded_allow_ips` e o contrato
TrustedProxy continuam sem delegar confiança ao Gunicorn. `backend/wsgi.py`,
Dockerfile anterior e Compose anterior permanecem intactos.

O primeiro teste de ACL demonstrou que colocar `respond` fora de `route` permite
a ordenação dos handlers antes dessa recusa. A ordem efetiva foi corrigida e
retestada. Não se trata apenas de uma asserção sobre texto Caddy.

## Ficheiros do incremento

Alterados relativamente ao snapshot inicial DEV-05B:

- `backend/Dockerfile.dedicated`: instalação hash-locked e `pip check`.
- `backend/Dockerfile.dedicated.dockerignore`: allowlist corrigida.
- `backend/gunicorn_container.conf.py` e `backend/gunicorn_dedicated.conf.py`: CSV vazio válido.
- `backend/tests/test_dedicated_entrypoint.py` e `backend/tests/test_dedicated_packaging.py`: expectativas dos artefactos corrigidos.
- `compose.dedicated.yaml`: CIDRs explícitos obrigatórios e build da imagem Caddy derivada; entrypoints `exit 78` preservados.
- `infra/dedicated/Caddyfile`: ACL ordenada e coerência SNI/Host.
- `docs/operations/dev04-dedicated-integration.md` e `docs/specifications/f0/implementation-status.md`: ligação ao estado atual, preservando o texto anterior.

Criados:

- `backend/requirements-container.lock`.
- `backend/tests/test_dedicated_preflight.py`.
- `infra/dedicated/Dockerfile.caddy` e respetivo `.dockerignore`.
- `infra/dedicated/dependency-provenance.json`.
- `scripts/dedicated/preflight.py`, `check_context.py` e `isolated_check.py`.
- Este relatório.

## Reprodução controlada

Requer daemon Docker **local**, BuildKit, Compose e as três imagens base pelos
digests em `infra/dedicated/dependency-provenance.json`. Os scripts usam o socket
Unix local explicitamente. Não enviar contextos a builders remotos.

1. Construir a imagem Caddy com `infra/dedicated/Dockerfile.caddy`, contexto
   `infra/dedicated`, argumento `DEV05_CADDY_BASE_IMAGE` igual ao digest registado,
   tag local `livenet-dev05b/caddy:integration`, rede de build `none`.
2. Construir a imagem backend com `backend/Dockerfile.dedicated`, contexto
   `backend`, argumento `DEV04_PYTHON_IMAGE` igual ao digest registado, tag local
   `livenet-dev05b/backend:integration`. A instalação pode necessitar de acesso
   exclusivamente a `pypi.org`/`files.pythonhosted.org`; não usar rede `none` num
   build sem a camada de dependências em cache. Confirmar exit code antes de testar.
3. Executar `python3 scripts/dedicated/check_context.py`.
4. Executar `python3 scripts/dedicated/isolated_check.py`. Usa imagens locais com
   `--pull=never`, redes `--internal`, recursos com prefixo/label únicos e nenhum
   `-p`. Não executa `compose up` nem remove o bloqueio do descriptor operacional.

O Compose é renderizado com o perfil `dev04-blocked` explícito; sem ele, a versão
nativa utilizada omite os serviços do resultado de `config`. O harness testa também
a recusa nativa de CIDRs ausentes. Caddy aceita sintaticamente `remote_ip` sem
argumentos; a obrigatoriedade de configuração vem de Compose/preflight, não de
uma alegada rejeição pelo parser Caddy.

Para revisão de uma alocação candidata, `preflight.py --plan <JSON renderizado>
--settings <JSON dedicado> --policy <JSON da alocação>` apenas lê/valida. A política
contém `allowed_bind_addresses`, `allowed_client_networks` e `reserved_networks`.
Exigir aprovação humana e inventário de redes completo separadamente. O preflight
não instala firewall, não inicia serviços e nunca devolve autorização de ativação.

Os ficheiros backend/segredos devem pertencer a UID 10001 e ter modo privado;
a credencial de bootstrap do ensaio pertence a UID 0. O helper root só prepara,
inspeciona ou elimina ficheiros sintéticos na diretoria temporária desse ensaio.
A aplicação real conserva a validação própria de ownership/permissões, sem
qualquer exceção para teste. CA privada Caddy só existe em tmpfs; o cliente recebe
apenas o certificado público e valida certificado/hostname, sem `--insecure` nem
alterações ao trust store do host.

## Validação executada

- Docker Engine/CLI 29.4.3; Compose v5.1.3; Buildx v0.33.0.
- Resolução binária de 15 wheels e confirmação SHA256 com JSON oficial PyPI.
- Builds backend e Caddy concluídos; `pip check` passou dentro do build.
- Contextos reais/adversariais exportados e comparados por nomes e hashes.
- 1 290 testes offline passaram, com audit hook a recusar sockets, subprocessos e
  ligações psycopg. Após a correção Gunicorn, 108 testes diretamente afetados
  foram reexecutados com sucesso; não somar estes números como testes distintos.
- Ensaio final nativo: seis grupos de verificações passaram, incluindo probe direto
  com headers forjados recusado com 403, restart e ausência de bindings no host.
- Inspeção da imagem: UID 10001, Gunicorn 23.0.0, sem migrações nem `.pyc` em `/app`.

Imagem backend final: `sha256:b16b93e9ab02616547158eabe0064475e705207d1a6d7f01af9b50aa25568238`.
Imagem Caddy derivada: `sha256:e36f33676361790b51835de75db874e2927b566da435dd4ecc39a416ffee322e`.

Evidência local desta execução: `/tmp/livenet-dev05b-artifacts/` contém logs de
build/contexto/regressões/integração e wheels de teste. O ensaio final tem prefixo
`livenet-dev05b-fb69b7fa4e`, resultado `passed` e limpeza sem falhas. Os ensaios
intermédios falharam durante a correção de UID dos auxiliares, seleção do perfil,
file capability, obtenção do certificado público em tmpfs, ordem ACL, SNI/Host e
configuração Gunicorn. Os respetivos recursos também foram removidos.

## Git, preservação e reversão

Inicial: `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`; alterações
versionadas preexistentes em `backend/migrations/env.py` e no implementation-status,
além dos artefactos não versionados das etapas anteriores. Foram inventariados e
copiados 258 ficheiros para `/tmp/livenet-dev05b-baseline-tc65lgsm`, com manifesto
SHA256. Essa cópia é privada. Nenhum ficheiro anterior foi eliminado.

Final: mesma branch/HEAD, sem staging, commits ou push. Não foi criado commit para
não misturar artefactos preexistentes ainda não versionados com o incremento.
A comparação contra o snapshot identifica os dez ficheiros anteriores alterados
acima; os restantes ficheiros iniciais mantêm os hashes, incluindo gates, Alembic,
manifesto AUTH-03 e fontes aplicacionais. Documentos anteriores mantêm o corpo
integral como sufixo, com indicação nova no início.

Reversão: comparar os dez ficheiros com a cópia inicial e reverter apenas os hunks
DEV-05B; retirar apenas os nove ficheiros novos listados, após confirmar ausência
de trabalho posterior. Não usar `git clean`, reset ou checkout global, pois vários
artefactos anteriores são não versionados. Nenhuma reversão PostgreSQL é necessária.
As duas imagens locais e cache BuildKit ficam disponíveis para revisão; não houve
prune de imagens/volumes. A limpeza automática só remove contentores/redes cuja
label coincide com a execução e elimina os ficheiros privados sintéticos. Sobram
apenas relatórios públicos de teste, diretórios temporários e caches/wheels, sem
serviços ativos nem volumes de dados novos.

## Bloqueios preservados e próximo objetivo

Permanecem abertos `f066`/`f067`, AUTH-03/manifesto divergente, gates F02/G2/G4,
readiness PostgreSQL real ausente, TLS/identidade/ACL runtime por validar,
recuperação independente não demonstrada e todas as lacunas documentais anteriores,
incluindo as 28 lacunas G4/L02 declaradas cujo inventário original não foi localizado.
Não foram regenerados manifestos, fornecido checker positivo ou alterado gate algum.

Próximo objetivo recomendado: fechar, por revisão humana, o contrato de persistência
dedicada e preparar um ensaio PostgreSQL descartável aprovado que demonstre
`verify-full`, identidade física, privilégios mínimos e cadeias Alembic independentes.
Só depois ligar login/sessões/inventário autenticado e implementar o checker real,
com recuperação demonstrada. Este incremento não autoriza essas operações em
instalações existentes, STAGING ou PROD.
