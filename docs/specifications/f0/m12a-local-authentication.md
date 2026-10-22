# M1.2A — Autenticação aplicacional local

Implementação de código e testes offline da decisão M1.2-D01. Não instalada nem
ativada no laboratório. Não cria tabelas, contas ou credenciais no arranque.
AUTH-BOOT/AUTH-03 não participa no login, sessões ou RBAC aplicacional.

## Persistência prevista

Quatro modelos no schema `security`:

- `local_users`: UUID, login normalizado único, hash scrypt, estado e timestamps.
- `login_sessions`: UUID, hash SHA-256 único do token aleatório de 256 bits,
  utilizador, criação, atividade, expiração absoluta e revogação.
- `global_role_grants`: utilizador/papel únicos, FK e âmbito estritamente global.
- `login_throttles`: orçamento partilhado por login e origem de rede. É necessário
  para limitar também logins inexistentes, sem estado apenas em memória.

Não existem migrações M1.2A. Não executar `create_all`, autogeração ou
`upgrade head` para ativar esta implementação. A coexistência da revisão local
f067 com futuras revisões security exige decisão explícita em M1.2B.

## Endpoints

| Endpoint | Contrato |
|---|---|
| GET `/api/v1/auth/csrf` | Cookie CSRF seguro e JSON `csrf_token`; não autentica nem cria sessão persistente. |
| POST `/api/v1/auth/login` | JSON com exatamente `login` e `password`; normaliza login; devolve `user` e define cookie de sessão, nunca token no JSON. |
| GET `/api/v1/auth/me` | JSON `user` com UUID, login e papéis atuais; 401 sem sessão válida. |
| POST `/api/v1/auth/logout` | Revoga sessão e limpa cookies, 204; idempotente com contexto CSRF válido. |

Login inválido/conta desativada: 401 genérico. Orçamento esgotado: 429.
CSRF/origem inválidos: 403. Payload inválido: 400/415; corpo de login limitado a
16 KiB. Configuração ou persistência indisponíveis: 503 sanitizado.
Respostas auth/inventory usam `Cache-Control: no-store` e `Vary: Cookie`.
Não há registo público ou endpoints administrativos.

## Configuração

Configuração fornecida apenas por setup Python confiável, através de Config ou
`create_app(security_config=...)`. Não existe bypass de desenvolvimento nem
integração automática por cabeçalhos. Nenhuma configuração operacional foi criada.

| Chave | Default/contrato |
|---|---|
| `SECURITY_ENABLED` | `False`; endpoints auth indisponíveis e inventory negado. |
| `SECURITY_HTTPS_ORIGIN` | Ausente; uma origem HTTPS explícita, incluindo porta quando necessária. |
| `SECURITY_CSRF_KEY` | Ausente; chave externa de alta entropia, mínimo 32 caracteres, nunca em Git/logs. |
| `SECURITY_IDLE_SECONDS` | 1800; pode ser encurtado, nunca aumentado acima de 30 minutos. |
| `SECURITY_ABSOLUTE_SECONDS` | 43200; máximo 12 horas, não renovado pela atividade. |
| `SECURITY_CSRF_SECONDS` | 1800; máximo 30 minutos. |
| `SECURITY_COOKIE_SECURE` / `SECURITY_COOKIE_HTTPONLY` | Obrigatoriamente `True`. |
| `SECURITY_COOKIE_SAMESITE` | Obrigatoriamente `Lax`. |
| `SECURITY_LOGIN_LIMIT` | 5 pedidos por login/janela. |
| `SECURITY_SOURCE_LIMIT` | 50 pedidos por origem de rede/janela. |
| `SECURITY_LOGIN_WINDOW_SECONDS` | 900. |

Os três valores de limitação são parâmetros iniciais de implementação ajustáveis
por configuração, não novos serviços. Limites têm de ser inteiros positivos.
Autenticação operacional recusa `DEBUG=True`. Todos os pedidos de autenticação
e sessões inventory exigem HTTPS e host/porta correspondentes à origem configurada.

Os cookies `__Host-livenet_session` e `__Host-livenet_csrf` usam Secure, HttpOnly,
SameSite=Lax, Path=/ e nenhum Domain. Não utilizar localStorage ou URLs para tokens.
O cookie de sessão não contém identidade ou permissões. O servidor guarda apenas
o seu hash. Dados de sessão e roles são consultados em cada pedido, com cache
apenas dentro desse pedido.

## CSRF e fluxo browser/API

1. Obter `/auth/csrf` na origem HTTPS autorizada, conservando o cookie.
2. Enviar login JSON com `X-CSRF-Token` igual ao token recebido e Origin válido.
3. O login gera uma sessão nova e revoga a sessão anterior apresentada, se existir.
4. O cookie CSRF pré-login é removido. Obter novo `/auth/csrf` para a sessão nova.
5. Enviar esse token em logout e POST de inventário.

CSRF usa assinatura itsdangerous com HMAC-SHA-256 e prazo; vincula cookie/header ao
hash da sessão ou ao contexto pré-login. Pré-login não confere identidade.
Origin tem prioridade; sem Origin exige Referer HTTPS com a mesma origem.
Não existe CORS permissivo nem confiança automática em forwarded headers.

## Sessões, limitação e auditoria

Password hashing/verificação usa Werkzeug scrypt:32768:8:1. Não existe password ou
utilizador predefinido. O helper de hashing não provisiona contas.

Inatividade >= 30 minutos, expiração absoluta, revogação, conta desativada ou
retrocesso do relógio invalidam acesso. Expiração/desativação detetadas revogam
a sessão com auditoria. Logout/rotação e respetivos eventos são transacionais.

Antes da verificação de password, dois upserts condicionais atualizam orçamentos
persistentes: login normalizado e `remote_addr`. As chaves são HMACs com domínio
separado, sem guardar o IP/login em claro na tabela de limitação. A transação dos
orçamentos confirma antes da transação de autenticação: uma falha posterior não
apaga tentativas anteriores. Pedidos válidos também consomem orçamento. Não há
reset por login bem-sucedido nem fallback de memória. Não há retry automático.

Eventos usam exclusivamente `record_audit_event`; não incluem passwords, hashes
de passwords, tokens de sessão ou CSRF. Falha de auditoria impede a alteração
correspondente. Falha de commit pode ter resultado incerto: não presumir rollback
comprovado nem repetir cegamente. O cookie só é entregue após commit bem-sucedido.

## Permissões

- `inventory_reader`: leitura global.
- `inventory_editor`: leitura e criação globais.
- Sem atribuição: identidade pode consultar `/auth/me`, mas não inventory.
- Grupo/recurso/papel desconhecido não produzem permissão global.
- UUID auditável vem da sessão, nunca do cliente. A contagem e paginação continuam
  posteriores ao predicado SQL autorizado; detalhe inexistente/invisível mantém 404.

## Limitações e gates M1.2B

- Aprovar estratégia Alembic sem alterar/incorporar implicitamente AUTH-03.
- Criar/aplicar migração e validar constraints, concorrência de upserts/locks,
  commits, rollback e restauros numa base isolada expressamente autorizada.
- Preparar VM Proxmox, HTTPS, servidor operacional, privilégios mínimos e gestão
  externa de chaves. Configurar proxies confiáveis explicitamente; remote_addr
  pode representar o proxy/NAT e limitar utilizadores em conjunto.
- Definir limpeza controlada de sessões revogadas e buckets antigos, observabilidade,
  sincronização de relógios, recuperação de contas e rotação de chaves. Rotação da
  chave CSRF invalida CSRF existente e muda as chaves dos buckets: não executar
  casualmente durante uma janela de proteção.
- MFA normal e âmbitos RBAC grupo/recurso não estão implementados.
- Os testes offline com doubles não demonstram atomicidade/durabilidade PostgreSQL.
- O manifesto AUTH-03 permanece intacto e divergente do novo código aplicacional.

## Primeira conta — procedimento futuro, não executado

Após autorização específica e schema validado, um operador administrativo deve
obter uma password individual por canal seguro, gerar hash scrypt e criar conta
e atribuição global explicitamente escolhida numa transação auditada. Nenhuma
password por omissão, argumento de shell ou seed no arranque. Validar login/leitura
e, para editor, criação auditada; testar revogação. Ferramenta administrativa e
política de password/recuperação requerem revisão própria em M1.2B. Não usar a
conta PostgreSQL como conta de utilizador LiveNet e não ativar AUTH-BOOT.
