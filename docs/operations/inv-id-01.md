# INV-ID-01 — IPv4 manuais no Inventory

18/11/2026. Implementação isolada sobre `43f7197`; **ativação operacional
pendente de autorização própria**. Nenhuma migração/grant, pedido HTTP ou
Discovery foi executado no DEV por esta implementação. Frontend servido e
processo HTTPS operacional preservados. Fontes: INV-02A, DAT-02A/B/C e os
ajustes técnicos aprovados no mandato INV-ID-01. Não implementa arquivo,
eliminação, reconciliação automática ou políticas de retenção.

## Dados e semântica

Reutiliza as 18 colunas de `inventory.resource_identifiers`. Novas declarações:
`identifier_type=ipv4`, `source_type=manual`, `source_instance=UUID do ator`,
`verification_status=unverified`, confiança e verified_at nulos. UUID do recurso
é permanente; IP não prova identidade exclusiva. O servidor produz evidência
`method=manual_declaration`; clientes não fornecem evidência/verificação/origem.

`identifier_value` conserva os caracteres aceites. IPv4 normalizado é decimal
pontuado sem espaços exteriores. Entrada ASCII entre 1 e 64 caracteres; recusa
CIDR, portas, IPv6, nomes, inteiros, hexadecimal, octetos ambíguos, controlos,
unspecified, multicast e broadcast limitado. Não exige pertença à rede Discovery;
loopback/link-local são declarações, não autorização de contacto. Sem máscara
não se inferem endereços de rede/broadcast a partir do último octeto.

Namespace obrigatório entre 1 e 255 caracteres, exatamente
`[a-z0-9][a-z0-9._:-]{0,254}`, sem lowercase/trim silencioso. CHECK PostgreSQL
usa collation C para corresponder ao alfabeto ASCII da API. O namespace não é
inferido de IP, VLAN, CIDR, configuração ou observações.

Tempo UTC do PostgreSQL, obtido por `clock_timestamp()` após os locks. Início,
first_seen/last_seen e criação coincidem na declaração; não afirmam deteção TCP.
`valid_until=NULL` significa aberta; encerramento grava um fim estritamente
posterior ao início. Datas de observação não mudam ao encerrar. Se o relógio
impedir coerência com o recurso/histórico, recusa `temporal_conflict`.
Não há retrodatação, agendamento, reabertura ou DELETE no contrato.

## API

Prefixo `/api/v1/inventory/resources/{resource_id}`:

| Método/caminho | Resultado |
| --- | --- |
| GET `/identifiers` | IPv4 de todas as fontes; state=active/closed/all, page, per_page e namespace opcional |
| GET `/identifiers/{identifier_id}` | Associação pertencente ao recurso, inclusive encerrada |
| POST `/identifiers` | Declaração manual; 201 se criada, 200 se repetição |
| POST `/identifiers/{identifier_id}/close` | Encerramento manual; 200 também se já encerrada |

Adição: `identifier_value`, `namespace`, `row_version`; opcionais
`confirm_shared=false`, `conflict_revision=null`. Confirmação exige booleano true
e revisão SHA-256 da situação corrente. Encerramento aceita só `row_version`.
Campos/queries repetidas ou desconhecidas na listagem são recusados; corpo de
escrita máximo 16 KiB, application/json. UUIDs inválidos dão 400.

Escrita retorna `{identifier,resource_row_version,changed}` e Location na adição.
Lista retorna `{items,total,page,per_page,resource_row_version}`; page=1,
per_page=50 por omissão, máximo 100. Ordem created_at decrescente com desempate
UUID. Leituras usam snapshot REPEATABLE READ/READ ONLY para versão/contagem/página.

Erros estáticos: 400 invalid_ipv4/invalid_namespace/invalid_request; 401/403
contratos existentes; 404 associação/recurso inexistente ou fora do scope;
409 identifier_conflict/conflict_changed/version_conflict/resource_archived/
identifier_read_only/temporal_conflict; 413 corpo excessivo; 415 media type;
503 operation_busy para contenção/timeout/deadlock; 500 sanitizado para falhas
inesperadas. Não expor SQL, mensagens do driver ou conteúdo bruto de exceções.

## Transações, coincidências e idempotência

Advisory lock transacional SHA-256 determinístico do domínio INV-ID-01,
namespace e endereço (bigint); depois recurso com FOR UPDATE e reconsulta.
Colisão do hash apenas serializa trabalho adicional. Encerrar faz descoberta
autorizada da chave, segue a mesma ordem de locks e revalida origem/chave.
Não há estado de autorização reconstruído de uma observação Discovery.

Uma única associação manual aberta por recurso/namespace/endereço. Mesma tupla
ativa devolve o UUID e datas existentes; mesma associação já encerrada também
é noop. Não incrementa versão nem acrescenta auditoria. Outros endereços e
namespaces são permitidos; outras fontes mantêm linhas/proveniência próprias.

Coincidência aberta noutro recurso no mesmo namespace exige revisão explícita.
A revisão deriva do conjunto ordenado de UUIDs das associações coincidentes;
adição/encerramento altera-a. Confirmação desatualizada dá conflict_changed.
Não há unicidade global, fusão, transferência ou encerramento automático.
Resposta inclui no máximo 20 referências autorizadas. `visible_total` conta todas
as associações autorizadas, antes desse limite; `truncated` é true apenas quando
essa lista autorizada ultrapassa 20. Nenhum desses campos conta associações fora
do read_scope. A UI apresenta o total autorizado, quantas referências apresenta
e um aviso explícito de lista parcial; não há paginação de coincidências neste
incremento. A revisão continua a cobrir o conjunto integral, incluindo associações
não divulgadas. Uma alteração fora da lista apresentada também invalida a revisão.

Mutação real exige versão atual e incrementa Resource.row_version na mesma
transação; atualiza updated_at. Uma repetição noop pode aceitar versão anterior,
mas nunca superior à atual. Pedido antigo aponta sempre ao UUID antigo e não
encerra uma reatribuição. Nova atribuição após encerramento cria UUID novo.
Arquivados são só leitura; maintenance/disabled não impedem declaração manual.

Esta é idempotência da associação ativa, não replay universal de respostas.
Após COMMIT de resultado incerto consultar estado/versão antes de nova ação;
não introduz chaves HTTP de idempotência nem retries automáticos. Um erro após
COMMIT pode deixar a alteração durável; nunca inferir rollback de um HTTP 500.

## Segurança e grants

Reader/editor consultam sob read_scope; só update_scope autoriza mutação.
Preservados sessão, origem, CSRF e no-store. Recursos/associações fora de scope
não aparecem. Coincidências não revelam UUIDs fora do read_scope. Atualmente os
papéis são globais: eventual RBAC granular exige decisão explícita sobre autorização
de pesquisa transversal, confirmação e divulgação de existência. Recusas de conflito
e alterações da revisão integral continuam a constituir um canal de existência.
Filtrar UUIDs ou acrescentar contagens autorizadas não resolve esse risco. FIX-03
permanece risco residual documentado; não se declara não interferência entre tenants
nem suporte novo a RBAC granular.

Acrescentar ao runtime exclusivamente na tabela resource_identifiers:

- SELECT e INSERT explicitamente nas 18 colunas existentes.
- UPDATE apenas valid_until e updated_at.

Reutilizar os grants de recursos (versão/updated_at) e INSERT audit existentes.
Sem DELETE, DDL, ownership ou privilégios globais. Grants por coluna não impõem
política por linha: apenas o serviço permite encerrar declarações manuais abertas.
Um administrador/cliente SQL privilegiado não está contido pelo contrato HTTP.

Auditoria `inventory.identifier.added`/`inventory.identifier.closed` na transação
do recurso/identificador, com ator e UUID da associação; contexto de confirmação
e validade/versão. Falha de auditoria reverte ambos. Não duplicar evento em noop.

## Migração e preflight preparados

Alvo standard aplicacional novo `d002a01a7230`, depois de `d001a01a7230`.
Cadeia security `b12b01a7230` intacta; não passa por f067/AUTH-03. Os ledgers
anteriores d001 continuam reconhecidos para inspeção/backup antes de migrar.

Migração aditiva contém CHECK condicionado ao IPv4 manual e índice único parcial
`(resource_id,namespace,normalized_value)` para fontes manual e tipos ipv4/IPv4,
apenas valid_until NULL. Demais constraints preservadas, nenhuma coluna nova.
Antes do DDL, lock SHARE ROW EXCLUSIVE e SELECT preflight na mesma transação.
Tipos IPv4 não canónicos, IPv4 inválido/não normalizado, namespace manual inválido
ou duplicados manuais ativos bloqueiam com INV_ID_01_LEGACY_DATA_INCOMPATIBLE.
Não há backfill, normalização automática ou alteração de dados históricos.

Comando futuro de preflight, somente sob autorização operacional:

```bash
./scripts/livenet inspect-identifiers --config "$CFG"
```

Lê sob transação READ ONLY, verifica pin de identidade e devolve contagens;
COMPATIBLE/exit 0 ou BLOCKED/exit 78. Não cria app, worker ou journal. Esta
implementação não o executou contra o DEV. Dados de outras fontes mantêm namespace
opcional, mas tipos/valores IPv4 não canónicos continuam reportados para revisão.
Ausência de linhas legadas nunca é presumida a partir de testes.

## Frontend e Discovery

Secção independente no detalhe: IPv4 ativos, namespace/proveniência, original
quando diferente, validade, histórico paginado, formulário editor e confirmação
de encerramento/coexistência. Conflito mantém formulário e exige nova ação.
Mutação recarrega o recurso e a sua versão. Erro da secção não apaga o detalhe.
O detalhe conserva a última representação do mesmo UUID durante recarregamentos
e erros transitórios, mantendo a secção montada e o rascunho intacto. Escritas
ficam desativadas enquanto a versão do recurso não for novamente confirmada.
401/403/404 retiram os dados apresentados; uma mudança de UUID recria a vista
antes de carregar o recurso seguinte, sem reutilizar rascunho ou snapshot anterior.
Resposta incerta bloqueia novas escritas até leitura explícita bem sucedida;
não repete POST. ApiError conserva detalhes desconhecidos em memória; só o parser
de coincidências valida/expõe os campos permitidos, nunca mensagens brutas.

Discovery mantém decisões históricas e pistas dessas decisões. A consulta de
identificadores ignora encerrados e manual, pois observações atuais não têm
namespace comprovado. Não altera observações, jobs, workers, probes, recuperação
ou configuração privada. Integração futura por namespace exige contrato próprio.

## Validação isolada e futura ativação

Testes unitários e de API com PostgreSQL 16 temporário, socket Unix privado e
listen_addresses vazio; reutilizam o fixture de eleição C. Confirmam data_directory
antes de preparar/limpar tabelas e PID/data_directory antes de parar esse cluster.
Probes/sockets de deteção são proibidos por fixture; auth/HTTP UI são simulados.
Constraints/migração/grants e corridas são reais apenas nesse cluster isolado.
SQLite permanece um double de transações Discovery; não prova regex/locks PG.

Resultados de 18/11/2026: ronda relevante com **399 testes backend aprovados**
(Inventory, identificadores, Discovery/ciclo de vida/PG, instalador/runtime,
segurança API e auditoria). Após o último ajuste do preflight de tipos legados
com espaços e a prova adicional de encerramento concorrente: **65 aprovados**
em identificadores + instalação, incluindo **47 INV-ID-01**. Rondas sobrepostas,
não somar. Frontend: **84 aprovados**, typecheck e build aprovados. Bundle apenas
em `/tmp/livenet-inv-id-01-dist`; dist servido preservado. Nenhuma suite HTTPS
ou auditoria operacional foi repetida. Execução focada reproduzível:

```bash
env -u LIVENET_DISCOVERY_CONFIG PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend \
  .venv/bin/python -B -m pytest -q --tb=short -p no:cacheprovider \
  backend/tests/test_inventory_identifiers.py backend/tests/test_standard_installation.py
```

Em frontend: `npm run typecheck`, `npm test -- --reporter=dot` e
`node_modules/.bin/vite build --outDir /tmp/livenet-inv-id-01-dist`. Não usar build
por omissão enquanto frontend/dist estiver a ser servido pela instalação DEV.

Futura intervenção, com autorização separada:

1. Rever diff/testes; confirmar processo, DB/SID, ledgers d001/b12 e fila/journal
   Discovery limpos; estabelecer janela exclusiva e bloqueio verificável de escritas.
2. Criar backup atualizado e validar SHA/listagem/descodificação; preservar
   código/frontend C-E, configuração, TLS e journal. Não pressupor Synology.
3. Executar inspect-identifiers; qualquer incompatibilidade interrompe a migração,
   exigindo decisão própria sem correções automáticas.
4. Parar somente o backend identificado e confirmar término/ausência de liderança.
5. Aplicar migração standard via migrator com expectativas d001/b12 explícitas,
   depois grants mínimos via administração. Confirmar COMMIT e alvo d002/b12.
6. Instalar bundle validado atomicamente no mesmo filesystem e arrancar uma só
   instância com configuração e Discovery explícitas; TLS inalterado.
7. Validar health/login, Inventory, histórico, identificadores e Discovery READY
   sem scans. Qualquer escrita de validação operacional requer aprovação própria;
   não inventar recursos/identificadores de teste na base operacional.

### Rollback compatível — FIX-04

Não repor C-E integralmente com Discovery habilitada: a consulta C-E anterior
ignora validade e namespace e voltaria a usar IPv4 manuais/encerrados como pistas.
Preservar dados sem preservar esse filtro não é rollback compatível.

Artefacto preferido, a preparar e aprovar numa intervenção própria: código C-E
`43f7197` com o filtro localizado de compatibilidade INV-ID-01 em
`Repository._matches` (valid_until NULL, exclusão de manual enquanto observações
não têm namespace comprovado), frontend C-E correspondente e dependências já
validadas. Não inferir namespace nem alterar decisões históricas. Registar fonte,
diff restrito, hashes do artefacto/bundle e testes de ausência de sugestões manuais
ou encerradas e de preservação das decisões. Confirmar aceitação do schema d002
sem DDL no arranque e manter SELECT das colunas valid_until/source_type exigidas
pelo filtro. **Esse artefacto compatível não foi criado nem aplicado nesta tarefa.**

Condições obrigatórias antes de um rollback operacional autorizado:

1. Bloquear admissões/escritas, preservar logs, journal, backup e artefactos em uso.
2. Parar apenas a instância identificada; confirmar ausência da instância, worker,
   descendentes e liderança antiga. Não arrancar outra instância em sobreposição.
3. Consultar toda a fila: zero queued/running/cancelling, zero tentativa/recuperação
   pendente e nenhuma incerteza. Sem demonstração destas condições, rollback com
   worker Discovery permanece proibido; não limpar journal para ultrapassar o gate.
4. Verificar o artefacto compatível e instalar código/frontend controladamente,
   preservando TLS/configuração. Não restaurar a base, apagar linhas de identifiers,
   decisões, observações ou auditoria, nem reabrir associações.
5. Conservar migração aditiva d002, índice/CHECK e ledger. O CLI C-E original não
   reconhece d002: manter disponível o instalador INV-ID-01 revisto para inspeção,
   backup e reconciliação, separadamente do servidor de rollback. Não usar o CLI
   antigo nem reescrever o ledger para contornar essa incompatibilidade.
6. Validar health/login/históricos e o filtro compatível sem scans. Verificar
   hashes de dados históricos, fila limpa, uma instância e uma liderança apenas
   quando Discovery estiver explicitamente habilitada.

Se não existir artefacto compatível verificado, **bloquear Discovery**: manter o
serviço parado, ou arrancar uma versão sem carregar a configuração Discovery
somente mediante autorização operacional explícita, conservando o ficheiro privado.
Confirmar zero workers/lideranças Discovery nesse arranque. Não substituir esse
bloqueio por instrução informal para não iniciar scans. A reabilitação posterior
exige versão compatível e autorização própria; não é consequência automática de
um health 200. Esta tarefa apenas documenta essas alternativas, sem executá-las.

Qualquer redução futura de grants tem análise própria; não revogar SELECTs de
compatibilidade, permissões partilhadas ou escrita de auditoria cegamente.

Limites: protocolo de locks exigido a futuros escritores; idempotência não é
deduplicação de pedidos antigos após todo o ciclo de encerramento/reatribuição;
histórico preservado sem motor de limpeza; sem garantia contra administrador
hostil. Não altera arquitetura, serviços ou configuração da instalação em execução.

## Correções após revisão R1 — 18/11/2026

FIX-01 mantém a secção montada ao atualizar o mesmo recurso e preserva IPv4 e
namespace após revisão explícita de erro incerto, inclusive durante a leitura
pendente e depois da atualização da versão. Mudanças reais de UUID recriam a
vista, sem transportar o rascunho. FIX-02 acrescenta visible_total/truncated à
resposta e aviso de lista parcial, sem alterar o cálculo da revisão integral.
FIX-03 continua residual conforme a secção Segurança; FIX-04 está documentado
acima, sem criação ou aplicação de artefacto de rollback.

Validação restrita às alterações: **8 testes backend aprovados** (coincidências,
scope, histórico e compatibilidade Discovery; PostgreSQL apenas temporário) e
**37 testes frontend aprovados** em identificadores, detalhe Inventory e histórico
Discovery. Typecheck e build aprovados. Os testes incluem 503/timeout com refresh
completo, mudança de recurso e 25 associações, 23 autorizadas/20 apresentadas,
com validação de alterações ocultas na revisão. Não se repetiu a bateria completa.

Bundle corrigido apenas em `/tmp/livenet-inv-id-01-post-r1-dist`. O bundle anterior
`/tmp/livenet-inv-id-01-dist` é evidência da implementação anterior às correções,
não deve ser escolhido para futura ativação corrigida. Nenhum dos bundles foi
ativado e nenhum constitui o artefacto de rollback compatível ainda por aprovar.
