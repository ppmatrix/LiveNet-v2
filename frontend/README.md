> DEV-07 (2026-10-25): React real construído e testado em Node 24 isolado,
> servido por Caddy HTTPS e exercitado em Chromium com CA validada. Login
> persistente continua bloqueado; ver [relatório DEV-07](../docs/operations/dev07-react-integration.md).
> O conteúdo anterior descreve o contexto histórico da implementação.

# LiveNet v2 — interface inicial M1.3B-IMP1

React, TypeScript strict, Vite e React Router. Fetch nativo, sem biblioteca de
componentes, estado global externo ou autenticação alternativa. Dependências
fixadas e lockfile npm incluído. Node 24.13+ na linha 24 (ambiente validado:
24.13.1), npm 11. Instalações globais não são necessárias.

## Estrutura

```text
src/api/         HTTP, contratos, auth, inventário e carregamento cancelável
src/auth/        Sessão verificada no servidor e proteção de rotas
src/layout/      Sidebar, header, conta e navegação
src/pages/       Login, lista e detalhe
src/components/  Feedback e estado administrativo
src/test/        Setup, fixtures e doubles HTTP exclusivos de testes
```

Os testes estão junto das unidades, com helpers em src/test/. O bundle normal
não importa esses helpers. Não existe flag, modo mock ou utilizador de demonstração.

## Comandos

Executar a partir de frontend/:

```bash
npm ci --cache .npm-cache --no-audit --no-fund
npm run typecheck
npm run test
npm run build
```

`npm run test:watch` abre o modo de observação de testes. `npm run dev` inicia
Vite em 127.0.0.1, exclusivamente para desenvolvimento, mediante autorização de
arranque própria. Nenhum servidor foi iniciado na implementação desta etapa.
dist/, node_modules/ e cache npm são artefactos locais ignorados.

## URL da API e HTTPS

O valor padrão é `/api/v1`. A configuração de build `VITE_API_BASE_URL` pode
especificar esse prefixo ou uma URL absoluta **da mesma origem HTTPS**. Não
colocar segredos em variáveis VITE_: são incorporadas no JavaScript público.
Por exemplo, `VITE_API_BASE_URL=/api/v1 npm run build` preserva o contrato atual.
O cliente recusa HTTP, URLs com credenciais, queries/fragments na base e outras
origens antes de enviar pedidos. Um caminho configurado diferente só funciona
se o encaminhamento do ambiente aprovado preservar os endpoints Flask reais.

A política Flask exige HTTPS, host/porta da origem configurada, cookies seguros,
CSRF e DEBUG=False. O Vite HTTP padrão permite trabalhar no código, mas **não
permite autenticar** nesta aplicação. A interface mostra essa limitação; não
relaxa TLS/cookies, não cria proxy nem reescreve Origin/Host/forwarded headers.

O acesso integrado futuro necessita de uma origem HTTPS aprovada que sirva a UI
e encaminhe /api/v1 para Flask, com tratamento de TLS/proxies explicitamente
revisto. As rotas de UI usam BrowserRouter: o servidor web deverá devolver
index.html para navegação direta nas rotas da UI, sem transformar erros /api/v1
em HTML. Essa infraestrutura não é criada aqui.

## Contratos Flask utilizados

| Método e caminho (sob /api/v1) | Pedido/resposta |
| --- | --- |
| GET /auth/csrf | `{ csrf_token: string }`; cookie CSRF definido pelo servidor |
| POST /auth/login | JSON `{ login, password }`, X-CSRF-Token; `{ user: { id, login, roles } }` |
| GET /auth/me | `{ user: { id, login, roles } }`; 401 sem sessão válida |
| POST /auth/logout | X-CSRF-Token; 204, sem corpo |
| GET /inventory/resources | page, per_page, resource_type e administrative_state; `{ items, total, page, per_page }` |
| GET /inventory/resources/:id | Objeto Resource; 404 não distingue inexistente de inacessível |

Resource contém id, resource_type, display_name, description,
administrative_state, attributes, created_at, updated_at, archived_at e
row_version. Timestamps são apresentados em pt-PT, no fuso do browser. Valores
ausentes são identificados. Atributos são texto JSON escapado por React.

Paginação: page começa em 1; per_page padrão 50, máximo 100; a UI oferece
25/50/100 e respeita um valor válido recebido na URL. As respostas do servidor
determinam total, página e dimensão apresentados. Não há pesquisa textual,
filtros por grupo/tag ou ordenação personalizada. Alterar filtros ou dimensão
reinicia a página. Pedidos anteriores são cancelados e resultados obsoletos
ignorados. O UUID apresentado é a identidade persistente do recurso, não IP/MAC.

## Sessão e CSRF

No arranque, GET /auth/me recupera a sessão no servidor. Depois de confirmação,
GET /auth/csrf obtém proteção vinculada à sessão. Um 401 leva ao login;
indisponibilidade, erro de origem ou resposta incompatível não abrem páginas
privadas. O botão de recuperação volta a consultar o servidor.

No login: GET /auth/csrf pré-login → POST /auth/login → GET /auth/me →
GET /auth/csrf renovado. A resposta de login isolada não autoriza a navegação.
O CSRF pré-login não é reutilizado. O logout obtém um CSRF fresco vinculado à
sessão e só anuncia sucesso após o 204. Falha de logout mantém a indicação da
sessão, com erro e sem presumir revogação. Não há retry automático de POST.
Pedidos de logout/login concorrentes são bloqueados.

Todos os pedidos usam credentials: include e cache: no-store. Cookies
__Host-livenet_session e __Host-livenet_csrf são geridos pelo browser/servidor;
o JavaScript não os lê nem escreve. Não há localStorage/sessionStorage, tokens
em URLs ou persistência de credenciais. O token CSRF é obtido do JSON e usado
em memória no pedido correspondente. A palavra-passe é limpa após a tentativa.

RBAC é aplicado no Flask: inventory_reader e inventory_editor podem ler;
sem atribuição, o servidor recusa. O frontend não transforma roles em autoridade
nem aceita identidade em headers. HTTP 401 do inventário invalida a indicação
local da sessão; 403 mostra acesso negado sem inventar lista vazia. Erros
padronizados usam status/code do contrato; mensagens internas não são expostas.

## Testes e limites de validação

Vitest e React Testing Library usam jsdom com origem HTTPS sintética e mocks de
fetch. Testes cobrem CSRF/login, confirmação me, recuperação, logout, falhas,
rotas protegidas, submissão concorrente, lista/paginação/filtros, detalhe, 404,
403/401, loading, vazio, rede, respostas inválidas e cancelamento. Os mocks não
contactam serviços. Não são provas de cookies/TLS, autenticação ou persistência
PostgreSQL reais. A validação em browser real e os testes ponta a ponta na
origem HTTPS aprovada ficam para uma etapa autorizada separadamente.

## Limitações operacionais e funcionalidades futuras

A autenticação backend permanece desativada por omissão. Persistência security,
privilégios DML/FOR UPDATE da app, primeira conta e integração HTTPS continuam
dependentes das decisões e autorizações M1.2B. O frontend não altera esses
controlos. AUTH-03, operation_gate() e execution_enabled não são modificados.

A UI disponibiliza apenas login/logout, lista filtrada e detalhe. Descoberta,
Monitorização, Alertas e Administração aparecem como Em breve, sem links ou
rotas operacionais fictícias. Estado administrativo não representa online/offline.
Sem criação/edição na UI, grupos, etiquetas, telemetria ou métricas inventadas.
Essas funcionalidades exigem incrementos próprios; nenhum é iniciado aqui.

Referências técnicas da stack: [Vite](https://vite.dev/guide/),
[React Router declarativo](https://reactrouter.com/start/declarative/installation)
e [ambientes Vitest](https://vitest.dev/guide/environment).
