# LiveNet v2 — M1.3C-IMP1A: entrada estática HTTPS

## Estado e objetivo

Preparação de três ficheiros de configuração, sem arranque. Serve exclusivamente
o build React/Vite existente. Não disponibiliza backend, autenticação funcional
ou bases de dados. O projeto é independente dos ambientes LiveNet v1, v2 backend,
AUTH-03, F0.66C e M1.2B. Nenhum recurso Docker é criado por `compose config`.

Projeto: `livenetv2-web-dev`. Serviço: `web`.
Origem planeada: `https://livenet-v2.home.arpa:8443`.
Publicação planeada: `10.10.77.229:8443/tcp` → `web:8443/tcp`.
O endereço privado é referência de planeamento: confirmar novamente a sua
atribuição à progbox e disponibilidade da porta antes de qualquer publicação.

```text
Windows -- HTTPS, nome dedicado, porta 8443 --> Caddy
                                                |-- /api/v1 e /api/v1/*: 503 JSON
                                                |-- rotas UI: build com fallback SPA
                                                `-- assets existentes; restantes: 404
```

Não há reverse proxy, upstream, ligação ao backend ou resposta de login fictícia.
O 503 é uma recusa explícita de serviço, para qualquer método sob a API reservada.
Não são emitidos cookies, tokens ou sessões pelo Caddy.

## Imagem, montagens e isolamento

- Imagem oficial `caddy:2.11.7-alpine`, com versão explícita confirmada no
  catálogo Docker Official Images. Não foi descarregada nem executada nesta fase.
  O digest efetivo e a disponibilidade local ficam por verificar em IMP1B.
- `pull_policy: never` impede aquisição implícita no arranque. A imagem deverá
  estar disponível e ser verificada numa etapa expressamente autorizada.
- `restart: "no"`: sem reinício automático do ambiente de desenvolvimento.
- `frontend/dist` → `/srv`, read-only. Não monta o repositório nem node_modules.
- `infra/web-dev/Caddyfile` → `/etc/caddy/Caddyfile`, read-only.
- Ambos os binds recusam criar automaticamente o caminho de origem ausente.
  Verificar também `frontend/dist/index.html`; um diretório vazio não é um build.
- `livenetv2-web-dev_caddy_data` → `/data`: volume persistente exclusivo para
  estado TLS, incluindo CA e chaves. Só será criado num arranque autorizado.
- `/config` e `/tmp` em tmpfs; root filesystem read-only, capabilities removidas
  e no-new-privileges. Sem privileged, Docker socket ou network_mode host.
- Uma única rede bridge própria, `livenetv2-web-dev_web`, sem `internal: true`.
  O serviço não está associado às redes Docker dos outros projetos. Nenhuma rede
  é external e não há depends_on, links ou serviços adicionais.
- Apenas 8443/TCP publicada no IP privado indicado. Sem publicação de 80/443,
  UDP/HTTP3, backend ou PostgreSQL. Admin API Caddy desativada.

A bridge dedicada pode permitir tráfego de saída normal; não constitui isolamento
absoluto do host ou de destinos acessíveis por encaminhamento. A exposição de
entrada continua limitada pelo bind no IP privado e pela única porta TCP 8443
configurada. A acessibilidade real, as regras de firewall e o comportamento
efetivo do Docker devem ser validados em runtime em IMP1B. Nesta etapa, a ausência
de integração funcional resulta de não haver qualquer upstream ou configuração
de cliente PostgreSQL. Não ligar esta rede a outros projetos.

## TLS, resolução e confiança no Windows

`tls internal` usa a PKI local do Caddy. O listener HTTPS interno é 8443,
coerente com o bind Docker. `auto_https disable_redirects` impede a criação
do listener de redirecionamento HTTP automático; não desativa certificados/TLS.
Protocolos h1/h2, sem h2c ou h3.

O estado da CA/certificados será gerado pelo Caddy apenas no primeiro arranque
autorizado e persistido no volume dedicado. Não há certificados/chaves no Git.
`skip_install_trust` impede tentativas automáticas de alterar trust stores;
nenhuma CA foi instalada ou exportada. `persist_config off` evita autosave de
configuração; o Caddyfile montado é a fonte explícita.

Antes do acesso integrado, o Windows precisa de:

1. Resolução autorizada de `livenet-v2.home.arpa` para o IP privado confirmado.
   Poderá ser DNS interno ou hosts, conforme decisão posterior; nada foi alterado.
2. Rota e acesso TCP à porta 8443, a verificar sem presumir regras de firewall.
3. Confiança explícita na CA local, mediante procedimento autorizado separado.
   Só o certificado público da CA poderá ser transferido; nunca a chave privada.

Não ignorar erros de certificado nem desativar a validação TLS. O hostname
dedicado evita partilhar o âmbito dos cookies host-only com outros serviços no
mesmo IP; portas diferentes, por si só, não isolam cookies.

## Validação estática desta fase

Na raiz do repositório:

```bash
docker compose -f compose.web-dev.yaml config
git diff --check
git status --short
```

Rever projeto, imagem, único serviço, bind privado 8443, montagens read-only,
volume exclusivo e única rede bridge dedicada, não internal. Estes comandos não validam
a sintaxe Caddy, não testam ligações e não demonstram emissão de certificados.
Sem binário Caddy local, a validação sintática permanece pendente para IMP1B.

## Verificações futuras — dependem de autorização IMP1B

Antes de arrancar: confirmar IP/porta, ausência de recursos inesperados com os
nomes escolhidos, conteúdo do build, imagem/digest e configuração Compose.
A aquisição da imagem, criação de recursos e arranque não estão autorizados
por este documento. Com binário Caddy aprovado, o parsing pode ser inspecionado
sem iniciar servidor:

```bash
caddy adapt --config infra/web-dev/Caddyfile --adapter caddyfile --pretty
```

Uma validação que provisione módulos TLS pode escrever no storage; só a executar
no âmbito operacional autorizado, sem a classificar como simples leitura.

Depois de arranque, resolução e confiança TLS autorizados, executar de um cliente
autorizado com a CA já confiada (sem opções para ignorar TLS):

```bash
curl --include https://livenet-v2.home.arpa:8443/api/v1
curl --include https://livenet-v2.home.arpa:8443/api/v1/
curl --include https://livenet-v2.home.arpa:8443/api/v1/auth/me
curl --include https://livenet-v2.home.arpa:8443/login
curl --include https://livenet-v2.home.arpa:8443/inventory
curl --include https://livenet-v2.home.arpa:8443/inventory/272b1a76-a172-4314-a4fe-eef7b706bff2
curl --include https://livenet-v2.home.arpa:8443/assets/ficheiro-inexistente.js
```

Esperado: os três pedidos API devolvem 503 application/json, código
`api_unavailable`, Cache-Control no-store e nunca index.html. As rotas UI
devolvem o HTML do build; o UUID no exemplo é sintético e não implica recurso
existente. O asset inexistente devolve 404. Testar também POST /api/v1/auth/login
sem credenciais: deve continuar a devolver o mesmo 503, sem criar sessão.

Para confirmar isolamento após um arranque autorizado:

```bash
docker compose -f compose.web-dev.yaml ps
docker network inspect livenetv2-web-dev_web
docker compose -f compose.web-dev.yaml port web 8443
```

Confirmar único contentor web na rede própria, Internal=false, único bind privado
8443 e nenhuma associação às redes protegidas. Rever o Caddyfile: ausência de
reverse_proxy/upstreams, apenas três binds/volumes previstos e tmpfs. Não usar
docker inspect completo se puder mostrar dados sensíveis; filtrar apenas os
campos de redes, portas e montagens necessários. Não testar bases de dados.

## Limitações funcionais

Visitar `/login` permite carregar a interface, mas a consulta inicial /auth/me
recebe 503 e a UI informa indisponibilidade. Inventário privado continua fechado.
Não haverá login real, recursos listados ou detalhe funcional. Não introduzir
credenciais reais nesta etapa. A recusa não é contornada nem substituída por mocks.

A futura API depende de imagem backend atualizada, configuração de origem HTTPS,
DEBUG=False, tratamento revisto de proxies confiáveis, persistência security,
privilégios e primeira conta LiveNet. AUTH-03 e M1.2B continuam isolados e bloqueados.
Esta configuração não autoriza qualquer uma dessas alterações.

## Paragem futura — não executada

Só mediante autorização operacional, parar exclusivamente o serviço deste projeto:

```bash
docker compose -f compose.web-dev.yaml stop web
```

Não usar comandos globais, não parar outros projetos e não remover o volume TLS.
Perder esse volume perde a identidade da CA e exige nova gestão de confiança.
Não executar down -v nem limpeza de volumes.

## Referências

- [Imagem oficial Caddy](https://github.com/docker-library/official-images/blob/master/library/caddy)
- [HTTPS local](https://caddyserver.com/docs/automatic-https)
- [Opções globais Caddy](https://caddyserver.com/docs/caddyfile/options)
- [SPA e API](https://caddyserver.com/docs/caddyfile/patterns)
- [Âmbito dos cookies](https://www.rfc-editor.org/rfc/rfc6265)
