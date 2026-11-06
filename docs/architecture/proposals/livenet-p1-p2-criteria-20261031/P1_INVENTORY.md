# P1 — critérios documentais de consulta Inventory/UI

Candidata 0.1 · 31/10/2026 · Europe/Lisbon. **Para revisão humana; sem implementação ou testes executados.**

## 1. Fontes, estatuto e âmbito

- **U:** [frontend/README.md](../../../../frontend/README.md), «Contratos Flask utilizados», «Sessão e CSRF» e «Limitações». É documentação do comportamento existente, não nova aprovação normativa nem prova de execução atual.
- **D:** [data-model.md](../../../specifications/f0/data-model.md), DAT-01A/B, DAT-02A/B/C e DAT-03A/B: conceitos aprovados, identidade e estados. Reservas físicas/técnicas mantidas.
- **E:** [implementation-status.md](../../../specifications/f0/implementation-status.md), «UI/Inventário/RBAC» e atualizações DEV-06/07: evidência histórica, não readiness/persistência habilitadas.
- **R:** [D2](../../../specifications/f0/dr07-retention-addendum.md), V04-04/06, B4/B5/B7, aceite em P4-B4: consulta, arquivo e recuperação distintos.

Os critérios abaixo são verificáveis numa revisão documental ou futura validação especificamente autorizada, mas **não foram ensaiados nesta etapa**. «Documentado» não implica que a fonte seja ato normativo; «derivado» explicita uma consequência dos contratos sem acrescentar funcionalidade. «Não definido» é limite a preservar, não requisito novo a implementar. Não se alteram endpoints, campos, permissões, filtros ou políticas.

Âmbito: apenas consulta de recursos consolidados. A UI existente não cria/edita/elimina recursos e não possui rotas funcionais fictícias de Discovery/Monitoring/Alertas/Administração. Não se acrescentam ação de pesquisa, ordenação, mutação, grupos/tags ou telemetria nesta entrega.

## 2. Contrato de referência preservado

Sob `/api/v1`, apenas `GET /inventory/resources` e `GET /inventory/resources/:id` são usados pela consulta Inventory. A listagem documenta `page`, `per_page`, `resource_type`, `administrative_state` e resposta `{ items, total, page, per_page }`. O detalhe é um Resource. Não se introduzem `q`, `search`, `sort`, `order`, filtros de grupo/tag ou outros parâmetros.

Resource documentado em U: `id`, `resource_type`, `display_name`, `description`, `administrative_state`, `attributes`, `created_at`, `updated_at`, `archived_at`, `row_version`. A presença de `row_version` procede do contrato UI documentado; não se inventa novo atributo conceptual DAT nem política de concorrência/escrita. UUID é identidade persistente; nome não é necessariamente único, IP/MAC/hostname não substituem UUID.

DAT-01A lista `physical_host`, `virtual_machine`, `container`, `network_device`, `storage_device`, `iot_device`, `service`, `cluster`. DAT-03A fixa `active`, `maintenance`, `disabled`, `archived`, sem equivalência a online/offline. Candidatos Discovery não são recursos consolidados. Não se infere presença de controlos/campos adicionais na UI a partir de contratos conceptuais de identificadores/proveniência.

## 3. Critérios verificáveis

| ID | Tema/estatuto | Condição de verificação e resultado esperado | Fonte |
| --- | --- | --- | --- |
| P1-01 | Listagem — documentado | Para resposta válida de listagem, usar `items/total/page/per_page` do servidor e os campos existentes; não gerar recursos/contagens/identidades para completar a página. Critério de consistência, não seleção local de dados. | U, contrato de listagem/paginação. |
| P1-02 | Identidade — aprovado/derivado | Dois recursos com nome igual continuam distinguíveis pelo UUID; nome/IP/MAC não são chave de navegação substituta nem motivo de fusão. Não se exige expor identificadores que a resposta não possui. | D DAT-01B/02A; U UUID e detalhe. |
| P1-03 | Pesquisa — ausência expressa | O contrato atual não tem pesquisa textual; os critérios não exigem caixa de pesquisa nem envio de parâmetro novo. Se for pedida, fica como requisito futuro indefinido P1-Q1, sem implementar filtragem local substituta. | U «Não há pesquisa textual». |
| P1-04 | Filtros — documentado | São considerados apenas `resource_type` e `administrative_state`; preservar valores/contrato existentes, sem adicionar grupos/tags/online. Alterar filtro reinicia a página conforme U. | U; D DAT-01A/03A. |
| P1-05 | Semântica de filtros — limite | Não fixar AND/OR, correspondência parcial, case folding, múltiplos valores ou tratamento de valor desconhecido, pois U não os especifica. A verificação regista essa lacuna, sem declarar comportamento novo correto. | U; P1-Q2. |
| P1-06 | Ordenação — ausência/limite | Não exigir ordenação personalizada, parâmetro ou clique em coluna; ordem padrão do servidor e desempates não estão especificados nas fontes consultadas. Não chamar a sequência «alfabética», «por data» ou estável entre páginas sem contrato. | U; P1-Q3. |
| P1-07 | Página/dimensão — documentado | `page` começa em 1; `per_page` padrão 50, máximo 100; UI oferece 25/50/100 e respeita dimensão válida na URL. Não mudar limites ou inventar offset/cursor. | U paginação. |
| P1-08 | Mudança de dimensão — documentado | Alteração de dimensão reinicia a página; página/dimensão/total apresentados respeitam a resposta do servidor. Não impor uma regra nova para normalizar resposta divergente ou página fora do intervalo. | U; P1-Q4 para entradas inválidas. |
| P1-09 | Concorrência da consulta — documentado | Se chegar resposta antiga após mudar filtro/página, não deve substituir o resultado corrente; pedidos anteriores são cancelados e resultados obsoletos ignorados segundo U. Não é autorização de retry de operação protegida. | U paginação/carregamento cancelável. |
| P1-10 | Detalhe — documentado/derivado | A consulta usa o UUID do recurso selecionado no endpoint existente e apresenta Resource sem inventar dados ausentes. Consulta não altera identidade/estado nem efetua recuperação/reativação. | U; D DAT-01B/03A; R V04-06. |
| P1-11 | Representação — documentado | Timestamps apresentados pt-PT no fuso do browser, sem alterar os valores de origem; valores ausentes identificados; `attributes` apresentados como texto JSON escapado. Não se fixa texto, formato adicional ou novo campo. | U Resource. |
| P1-12 | Vazio — derivado | Distinguir uma listagem válida sem itens de falha/403. Não mostrar recursos de demonstração. Um conjunto vazio de uma página não demonstra inexistência global: interpretar `total/page/per_page` existentes, preservando a lacuna sobre página fora de intervalo. | U contrato, testes/limites, ausência de modo demo. |
| P1-13 | Erro/indisponibilidade — documentado/derivado | Falha de rede/origem ou resposta incompatível é erro, não lista vazia nem sessão autenticada por suposição. Erros usam status/code padronizados sem mensagens internas. Não se exige um novo botão, política de retry ou código HTTP não documentado. | U sessão/RBAC; P1-Q5. |
| P1-14 | Sem sessão — documentado | 401 Inventory invalida indicação local da sessão e conduz ao login; resposta isolada de login não autoriza páginas privadas. A sessão é confirmada no servidor; frontend não concede autoridade por roles locais. | U sessão/CSRF. |
| P1-15 | Sem acesso — documentado | `inventory_reader` e `inventory_editor` podem ler conforme Flask documentado; sem atribuição servidor recusa. 403 mostra acesso negado e não lista vazia. Não introduzir novo papel/âmbito ou esconder dado por política local inventada. | U RBAC; E RBAC parcial. |
| P1-16 | 404 detalhe — documentado | A mensagem/comportamento não deve distinguir recurso inexistente de inacessível. Não consultar por via alternativa para revelar existência. Não se exige 403 para o detalhe que U define como 404 indistinto. | U tabela de contratos. |
| P1-17 | Administrativo/operacional — aprovado/documentado | `active/maintenance/disabled/archived` são estados administrativos. `active` não prova online, `disabled` não prova down, arquivo não perde UUID e leitura não reativa. Não apresentar estado operacional ou métricas inventados na ausência de contrato/dados. | D DAT-01B/03A/B; U limitações; R B4/V04-06. |
| P1-18 | Limites de aceitação — preservado | A revisão desta grelha não libera checker, persistência, auth/runtime, escrita, migrations ou gates. Testes/UI/TLS históricos não demonstram comportamento atual da API/dados reais. | E atualizações DEV-06/07; U limitações. |

## 4. Requisitos não definidos e dúvidas para revisão

| Ref. | Lacuna concreta | Consequência documental |
| --- | --- | --- |
| P1-Q1 | Necessidade e semântica futura de pesquisa: campos abrangidos, igualdade/parcial, normalização e interface. | Não contratada nesta UI; eventual funcionalidade exige escopo/contrato próprio. Não criada por este pedido de critérios. |
| P1-Q2 | Combinação dos dois filtros, valores inválidos e normalização, além dos parâmetros existentes. | Não decidir sem fonte; nenhuma política nova de validação é imposta. |
| P1-Q3 | Ordem padrão, desempate e estabilidade com dados concorrentes. | Ordenação personalizada explicitamente ausente; ordem padrão não fixada pelas fontes. Sem promessa nova de snapshot ou paginação sem duplicações sob mutação concorrente. |
| P1-Q4 | URL/página inválida, página vazia além do total e detalhes de normalização. | U só fixa base/limites válidos e servidor como referência; não selecionar erro/redireção/clamp. |
| P1-Q5 | Texto exato, desenho e ações de recuperação para cada erro/vazio/carregamento; lista completa de status/code. | Preservar distinções 401/403/404 e erro/vazio; não inventar mensagem/código ou retry automático. |
| P1-Q6 | Âmbito RBAC por grupo/recurso e semântica operacional/freshness. | Contratos conceptuais não provam implementação atual; não alargar ACL nem adicionar telemetria na consulta. Alteração material de segurança requer decisão própria. |

As lacunas não impedem aceitar esta grelha condicionada; impedem apresentar requisitos ausentes como já implementados/aprovados. Uma futura evolução de pesquisa/ordenação ou permissões é decisão de âmbito, e eventualmente material, não pendência a resolver por suposição nesta entrega.

## 5. Aceitação documental

Aceitar para revisão se cada linha estiver rastreada a U/D/E/R, ausências explícitas forem preservadas e nenhum campo/endpoint/papel/prazo/ação de escrita novo for imposto. Não há avaliação PASS de execução nesta etapa. A validação futura dos critérios que exigem aplicação/dados depende de autorização e pré-requisitos próprios. [Revisão conjunta e preservação](REVIEW.md).
