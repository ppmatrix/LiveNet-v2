# LiveNet v2 — Ambientes: política vinculativa DEV-05A

Atualização documental de 2026-10-25. [DEV-05A-D01](decision-register.md) foi
aprovada pelo responsável em 25/10/2026, conforme pedido humano DEV-05A desta
conversa, anexo `adee713c-cd23-4bfd-a10e-c48de86c556e/Pasted text.txt` §1.
DEV-03C-D01 aprovou a Opção A no pedido DEV-04; não autorizou ativação.

## Fronteira obrigatória em todos os ambientes

LiveNet v2 é exclusivamente interno ao laboratório: UI/API só para redes
internas explicitamente autorizadas. Não permitir IP público, entrada por NAT/
port forwarding Internet, Cloudflare Tunnel ou equivalentes. Nenhum ambiente
recebe exceção implícita, incluindo DEV, previews temporários e STAGING.
Saídas de build/aplicação são avaliadas separadamente, nunca justificam entrada.
Exceção futura só por decisão arquitetural explícita do responsável.

| Ambiente | Política aprovada | Implementação / validação real |
| --- | --- | --- |
| DEV progbox | Bind HTTPS apenas no endereço/interface interna aprovada e firewall para redes autorizadas; sem publicação/partilha Internet | Artefactos DEV-04 bloqueados; interfaces/firewall/routing não inspecionados operacionalmente. |
| STAGING VM Proxmox | Mesmo limite LAN-only; dados, credenciais, volumes e PKI próprios | Topologia proposta e artefactos reutilizáveis; sem deployment atual validado. |
| PROD-VM Compose | Ingress Caddy interno; API/PG/Redis/auxiliares sem exposição externa | Opção A aprovada; parâmetros, imagem, peer, TLS e segurança PostgreSQL pendentes. |
| PROD-K8S multi-nó | Ingress exclusivamente interno; sem LoadBalancer público; fechar acessos indevidos por NodePort/hostPort/hostNetwork se introduzidos futuramente | Sem manifests/cluster validados; desenho da confiança e aplicação de políticas pendente. |

Não basta is_private/RFC1918 ou DNS interno. A revisão futura tem de inventariar
endereços/listeners IPv4/IPv6, firewall efetivo host/Docker/perímetro, routing/NAT,
routers/port forwarding, VPNs, túneis/proxies e restantes percursos de entrada.
VPN ou rede não aprovada deve permanecer sem acesso; não é atalho para publicar
a plataforma. Verificações destes caminhos exigem âmbito próprio; não foram
executadas nesta revisão.

## Alcance da topologia aprovada e lacuna de enforcement

Opção A: web em edge/api, backend em api/data, PG apenas data; só web descreve
publicação. Edge é o segmento de entrada da VM para a LAN, **não permissão para
Internet**. O nome da rede não fornece firewall nem atestação de isolamento.

Em [compose.dedicated.yaml](../../compose.dedicated.yaml):17, DEV04_HTTPS_BIND_IP
continua uma string obrigatória, não um validador de endereço interno aprovado;
0.0.0.0/:: ou IP público não são opções válidas para a publicação host. Não
confundir isso com Gunicorn 0.0.0.0 dentro do contentor sem ports. A aprovação do
IP/interface e das redes cliente tem de preceder qualquer ativação; bind privado
não demonstra ausência de NAT/túnel/routing externo.

O Caddyfile contém hostname/TLS, não ACL de redes cliente. Externos que alcancem
o listener não são identificados como externos só pelo hostname, e o filtro do
TrustedProxy autentica o peer intermediário, não a pertença do browser à LAN.
DEV-05A-R01 permanece ALTA para futura ativação; nenhuma regra é alterada agora.

| Cliente / caminho | Comportamento exigido pela decisão | Evidência existente |
| --- | --- | --- |
| Rede interna autorizada | HTTPS validado e autenticação/RBAC/CSRF normais; não conceder identidade pela rede | Código de segurança presente; percurso real não validado. |
| Rede interna não autorizada / VPN não aprovada | Acesso recusado por controlos de rede aprovados | Controlos/ensaios efetivos pendentes. |
| Internet / IP público / túnel ou encaminhamento externo | Sem percurso de acesso à UI/API, nem à página de login | Política aprovada; não demonstrada em runtime nesta tarefa. |

HTTPS, autenticação, autorização, auditoria, sessões, CSRF e cookies protegidos
continuam obrigatórios na LAN. Não remover esses controlos como compensação por
firewall ou endereço privado.

## Estado DEV-04 e dependências DEV-05B

Oito artefactos criados; 570 testes offline reportados na DEV-04, não repetidos.
JSON Compose, strings de configuração e oráculo de headers não são parsing
nativo ou validação de rede. Exit 78 nos três serviços continua inalterado;
não demonstra firewall e não impede um administrador de criar recursos Docker.

Antes de propor build, resolver em tarefa autorizada o risco de contexto R02
(exceção recursiva dockerignore); depois conferir conteúdo efetivo por mecanismo
aprovado. Parsing nativo e build isolada têm escopos distintos, sem permissão
automática de arranque. Endereços/subnets/peer, UID/montagens, imagens e dependências
precisam de validação; o build não deve ler segredos reais nem contactar PG.

Primeira integração operacional requer ainda readiness real, roles/ACL runtime,
conta inicial, recuperação independente, TLS PostgreSQL, identidade/peer e prova
de enforcement LAN-only. Preservar f066/f067, AUTH-03/manifesto, F02/G2/G4/gates e
as 28 lacunas G4/L02 abertas. Não se inicia DEV-05B nem se corrige infraestrutura.

## Arquitetura anterior preservada — baseline DEV-03B

O texto histórico abaixo permanece integral. Referências anteriores a entrada
pública/externa só podem ser lidas como entrada da LAN autorizada na VM; não
autorizam Internet. Os detalhes ainda propostos mantêm-se sujeitos a aprovação.

# LiveNet v2 — Arquitetura de ambientes

Baseline DEV-03B, 2026-10-25. Preparada para revisão humana; não autoriza criação
de VM, cluster, rede, credenciais, instalação ou ativação. As escolhas operacionais
abaixo marcadas PROPOSED precisam de aprovação antes de implementação.

Fontes: [registo de decisões](decision-register.md), [baseline F0](../specifications/f0/f0-baseline.md),
[DEV-02](../operations/dev02-dedicated-backend.md), [web-dev](../../infra/web-dev/README.md).
O desenho deve preservar o monólito modular sempre que possível: a passagem de
Compose para Kubernetes muda o alojamento, não exige uma reescrita dos domínios.

## Finalidades, fronteiras e estado

| Ambiente | Finalidade / orientação existente | Estado verificável nesta etapa | Desenho e critérios ainda PROPOSED |
| --- | --- | --- | --- |
| DEV — progbox | Desenvolvimento e testes isolados, conforme F0 | Código e configurações presentes; DEV-02 validou offline, sem runtime atual inspecionado | Configuração dedicada reproduzível; integração HTTPS isolada e dados sintéticos; não usar dados/segredos PROD. |
| STAGING — VM Proxmox | Ensaio antes de promoção, conforme F0 | Sem deployment completo identificado | VM/destino próprios; mesma versão candidata e contratos de PROD, dados sanitizados; ensaios de recuperação, migração e aceitação autorizados. |
| PROD-VM — VM dedicada | Primeira produção, Compose conforme F0/H05 | Sem stack completa de produção identificada | Projeto Compose próprio; ingress, API, workers/scheduler quando necessários, Redis e PostgreSQL; operação, backup e recuperação definidos. |
| PROD-K8S — várias VMs/nós | Evolução multi-nó pedida em DEV-03B; F0 tratava K8S como condicional | Sem manifests, Helm/Kustomize ou desenho de cluster identificado | Reutilizar imagens/contratos; disponibilidade, rede, persistência, segredos, migrações e recuperação aprovadas e testadas antes da promoção. |

Os projetos AUTH-03, F0.66C e M1.2B são ensaios com contratos próprios. PROV1/PROV2
não tornam m12b-test um STAGING ou PROD. A VM exclusiva G4, com ensaios sem NIC,
é outra fronteira; não serve como plataforma conectada por reclassificação.

## Configuração e separação de dados

Existente: [config.py](../../backend/app/config.py) define development/testing/production;
o perfil dedicado tem configuração explícita. [dedicated_wsgi.py](../../backend/dedicated_wsgi.py)
exige JSON privado com todas as chaves, segurança/proxy ativos e nenhuma descoberta
automática. O perfil production, por si, não comprova ACL, TLS ou destino físico.

PROPOSED: configurações independentes por ambiente, com identidade, destino,
inventário de recursos e proprietários de operação registados. Não partilhar
passwords, chaves CSRF, CA privadas, sessões, filas, dados ou volumes entre
DEV/STAGING/PROD. Dados de PROD só entram em ensaios mediante processo aprovado
de minimização/sanitização; cópias não se tornam automaticamente destinos válidos.

Fica aberta a divergência DAT-05A (`livenet`) versus recusa dessa base no perfil
dedicado. Não escolher nomes ou destinos novos como se já estivessem aprovados.
O v1 permanece independente. Não ligar automaticamente as redes dos ensaios.

## Redes, acesso aos equipamentos e confiança

Existente: [Compose base](../../compose.yaml) define rede backend interna;
[web-dev](../../compose.web-dev.yaml) tem bridge própria e publicação planeada
de HTTPS. O [Caddyfile](../../infra/web-dev/Caddyfile) devolve 503 sob /api/v1;
não há upstream Flask. Bridge/internal não é prova de isolamento contra o host.

PROPOSED para VM: ingress como único acesso público à UI/API, API/BD/Redis em
canais privados, administração separada, regras de entrada/saída explícitas.
Não expor o backend ou PostgreSQL para contornar uma incompatibilidade de rede.
Conferir IPs, DNS, firewall e identidade do peer em ensaio autorizado.

Descoberta, recolha e operações precisam de alcance aos equipamentos. PROPOSED:
registar alvos/redes permitidos, credenciais por integração, protocolos e limites,
timeouts e auditoria; separar administração de equipamentos da administração da
plataforma. Sem scanners, portas ou permissões privilegiadas introduzidos aqui.

PROPOSED para K8S: desenhar ingress/serviços/CNI e políticas de rede equivalentes,
incluindo egress dos coletores. O [TrustedProxy](../../backend/app/trusted_proxy.py)
valida IP exato do socket e um único hop. Pods/nós/proxies dinâmicos não autorizam
CIDR amplo, wildcard ou confiança em headers do cliente. Qualquer evolução desta
fronteira exige desenho e aprovação explícitos, mantendo HTTPS/origem/CSRF.

## HTTPS, origem e PostgreSQL TLS

Existente: origem dedicada restrita a https://livenet-v2.home.arpa:8443, cookies
host-only Secure/HttpOnly/Lax, CSRF e validação Host/forwarded. Caddy usa PKI interna
planeada, sem confiança automaticamente instalada. A origem não é parametrização
livre para todos os ambientes; nomes/portas e separação de cookies por ambiente
precisam de decisão própria. Portas diferentes não isolam cookies por si.

PROPOSED: inventário de nomes, certificados, CA, validade, rotação e responsáveis
por ambiente; validação TLS sem bypass. Distinguir TLS browser→ingress do transporte
ingress→API e PostgreSQL. G4D-09 exige verify-full/CA exclusiva G4 e identidade
física; não generalizar essa CA aos outros ambientes. A factory da app não fornece
verify-full/CA explícitos e PROV2 registou ssl off no ensaio: não há prova de TLS
PostgreSQL atual. O requisito para cada destino será aprovado antes de ativação.

## Segredos, sessões e armazenamento

Existente: [factory dedicada](../../backend/app/dedicated.py) e entrypoint exigem
ficheiros regulares privados do UID do processo, limite de tamanho e ausência de
symlink final. Configuração contém referências a segredos, nunca valores inline.
Os caminhos devem ter pais controlados; o contrato atual não atesta os ancestrais.

PROPOSED: distribuição, rotação, revogação e recuperação por ambiente, sem logs,
Git, argumentos CLI ou variáveis públicas VITE com segredos. Montagens Compose
ou K8S que exponham outro UID, permissões abertas ou symlink final serão recusadas;
definir um transporte compatível, sem relaxar as validações para fazer arrancar.
Não substituir credencial runtime por bootstrap. Réplicas precisam de configuração
CSRF consistente e política de rotação; isto não foi testado em multi-nó.

Existente: volumes PostgreSQL e Caddy declarados; build frontend por bind mount.
PROPOSED para VM: dados em volumes próprios, aplicações substituíveis por imagem,
capacidade/retenção verificadas e segredos fora da imagem. Para K8S, decidir
armazenamento, acesso, localização e falha de nó; várias réplicas da API não tornam
PostgreSQL/Redis/volumes altamente disponíveis. A colocação de PostgreSQL/Redis
dentro ou fora do cluster permanece PROPOSED, sem tecnologia/operador escolhidos.

## Backups e recuperação

Não existe prova localizada de recuperação completa atual. S08/S09 do registo
mantêm recuperação administrativa independente pendente. Login bootstrap,
rollback de testes, snapshot ou trigger restaurado não equivalem a restauro da
plataforma. Não confundir repor permissões SQL com recuperar a base.

PROPOSED: definir RPO/RTO por ambiente; backup consistente de dados e ledgers,
material de configuração, estado PKI e segredos necessários à recuperação, todos
protegidos por controlos próprios. Definir destino independente, retenção, acesso,
proveniência, verificação e ensaio de restauro em destino distinto. Não copiar
identidades físicas como autorização; clones requerem nova atestação aprovada.
Documentar perda de VM/nó, credencial, único administrador e commit incerto.
Kubernetes não substitui estes requisitos nem garante recuperação dos dados.

## Promoção e evolução sem reescrita

PROPOSED: produzir um artefacto candidato identificável e promovê-lo por digest
entre STAGING e PROD, com configuração/segredos externos e evidências ligadas à
versão. Aprovar locks/dependências, SBOM/proveniência e política de imagens em
etapa própria; nenhuma build/publicação ocorre nesta baseline.

Separar promoção da aplicação, migrações e alteração de privilégios. Preservar
os dois percursos Alembic; nada de migração automática em startup/réplica/init
por conveniência. Recovery/rollback de dados exige plano próprio: security
bloqueia downgrade. Não contornar f066/f067, gates ou manifesto AUTH-03 via CI/CD.

Condições propostas para passar a multi-nó:

1. Contratos originais/lacunas revistos, incluindo o conjunto aberto de 28 G4/L02.
2. Runtime funcional e recuperável em VM; imagens e configuração reproduzíveis.
3. Sessões, chaves, pools e carga PostgreSQL validados entre réplicas.
4. Outbox/consumidores idempotentes, concorrência e scheduler coordenados.
5. Readiness real aprovada e desenho de probes compatível com TrustedProxy;
   não criar bypass, peer falso ou readiness positiva sintética para probes.
6. Confiança de ingress, segredos, storage, backups e falhas de nó ensaiados.
7. Critérios de promoção/rollback aprovados, sem enfraquecer os contratos G4.

Detalhes dos componentes: [runtime](platform-runtime.md). Dependências e critérios
de entregas: [roadmap](../roadmap/platform-roadmap.md). Nenhum item está encerrado
apenas pela sua inclusão nesta lista.
