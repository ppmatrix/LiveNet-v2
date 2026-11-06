# LiveNet v2 — DR-07: decisões complementares de retenção

<a id="p4-b1-leitura"></a>

## Leitura atual DR-09A/P4-NC-01 — autoridade e âmbito documental

30 de outubro de 2026 · Europe/Lisbon. Referência principal: DR-09A/P4-NC-01 v1.1, Parte II, SHA-256 `794c21308c6126a6be1da9559b89ce644a36c02f2a51f2a913a79a87caa56ac1`. A aprovação normativa P3 das 86 disposições, declarada no mandato, conserva o seu objeto; esta consolidação redacional não certifica transcrição literal dos atos históricos. P3-A2, P3-F-01 e P4-A-01 mantêm os âmbitos e reservas registados em D1 #nc01-indice. As autorizações históricas DR-07B-02/DR-08C conservam o seu objeto. As menções abaixo a revisão ou aprovação pendente dos bytes DR-08C descrevem o registo anterior à aprovação posterior declarada em NC-01 v1.1. A fonte primária desse ato separado e a associação exata a ficheiros, versões e hashes continuam por cotejar; esta reserva não demonstra ausência de aprovação. A aprovação normativa P3 e a aprovação histórica DR-08C não aprovam por extensão os novos bytes D1/D2/D3 de P4-B: a sua incorporação documental exige autorização expressa do pacote exato e a aprovação dos bytes resultantes exige objeto próprio. Uma eventual incorporação documental não oficializa a baseline; F0 permanece Working draft. A leitura histórica do corpo anterior observa esta delimitação temporal.

**INCORPORAÇÃO DOCUMENTAL AUTORIZADA — DR-07B-02. BASELINE NÃO OFICIAL. CF-02 ABERTA. Bytes finais sujeitos a revisão humana. Sem autorização de implementação, limpeza ou alteração de gates.**

29 de outubro de 2026 · Europe/Lisbon. Incorporação exclusivamente documental autorizada pelo pedido humano DR-07B-02, a partir do plano DR-07B aprovado. A aprovação da incorporação não aprova automaticamente estes bytes finais. A referência histórica a Etapa B não autorizada é atualizada apenas quanto à criação documental de D1/D2/D3; nenhuma execução operacional é autorizada.

## Decisões e proveniência

DR-04 — Aprovação humana declarada da investigação preliminar CF-02, com objeto descrito no relatório de recuperação. Ato histórico integral, mensagem e versão aprovada não recuperados. Esta aprovação não é estendida a relatórios posteriores nem encerra CF-02.

DR-05 — RECONSTRUÇÃO DOCUMENTAL PROPOSTA A PARTIR DA APROVAÇÃO HUMANA CONHECIDA/DECLARADA. Pela clarificação humana aprovada DR-07B-01, o objeto conhecido de DR-05 é a aceitação documental da recuperação F0.28/DAT-06B, mantendo CF-02 ABERTA. O corpo original, a versão aprovada, a referência do ato histórico e a transcrição integral continuam ausentes. Esta reconstrução regista a declaração e o objeto conhecido; não atribui cláusulas, prazos ou recuperação de um original. Texto reconstruído sujeito a validação humana própria; nunca apresentado como original recuperado.

CF-02B-01 — Verificações individuais e checks individuais designam a mesma classe; retenção aprovada declarada: 30 dias.

CF-02A-01 — Retenção aprovada declarada dos agregados: 5 minutos, 180 dias; horários, 12 meses; diários, 3 anos.

DR-06 — Política por classes aprovada declarada, discriminada na adenda de retenção D2. O registo sucessor DR-08B-03 reúne as 18 decisões V03-01..06, V04-01..06 e V05-01..06 e as correções expressamente aprovadas no pedido humano desta preparação. As regras de D2 tratam contagem temporal, agregação, âmbito online/global, arquivo e proteção R2. A redação integral dos atos anteriores não foi recuperada; permanecem as reservas de proveniência e os detalhes residuais identificados. A redação reconciliada foi aprovada para incorporação documental DR-08C; os bytes finais exigem aprovação humana própria. Não constitui autorização operacional.

DR-07A — Aprovação humana declarada para prosseguir a preparação documental. O plano DR-07B foi aprovado e a incorporação documental D1/D2/D3 foi expressamente autorizada por DR-07B-02. Segundo a declaração humana disponível, DR-07B-03/V06 concluiu exclusivamente a revisão documental anterior. Essa conclusão não aprova futuros bytes por extensão. A redação DR-08B-03 foi aprovada para incorporação documental DR-08C; os bytes finais ficam sujeitos a aprovação humana separada. Implementação e operação permanecem NÃO AUTORIZADAS. CF-02 ABERTA e baseline NÃO OFICIAL.

## Reconciliação DR-08B-03: decisões e precedências

Este registo distingue o conteúdo decisório declarado aprovado, a redação reconciliada aprovada para incorporação documental DR-08C e a demonstração ainda necessária. Os bytes finais ficam sujeitos a aprovação humana separada.

A base documental disponível é o relatório DR-08B-02, anexo «Pasted text(20261029-194407).txt». O pedido humano DR-08B-03 confirma a preservação das 18 decisões do planeamento e aprova expressamente as correções de V03-02, V03-04, V03-05, V03-06, V04-04, V04-06, V05-02 e V05-06, bem como a organização editorial D1/D2/D3.

O texto integral dos atos anteriores, de DR-08B-01 e de P2-B1/P2-B2/P2-B3 não foi recuperado. A redação DR-08B-03 é reconciliada com as fontes disponíveis; não constitui transcrição certificada nem recuperação desses originais.

Para leitura deste pacote:

1. As oito correções expressas de DR-08B-03 qualificam as formulações correspondentes de DR-08B-02; as restantes decisões disponíveis conservam-se.
2. D1 regista decisões, proveniência, precedências, remissões e estados. D2 contém a especificação normativa. D3 contém a síntese e o acompanhamento, sem estabelecer política paralela.
3. As substituições históricas ficam limitadas às parcelas expressamente identificadas em D2. Não reescrevem os originais DH-03F/M, F0.28, DAT-06B, DR-05 reconstruído ou R2 C1–C7.
4. A proteção R2, a informação necessária à continuidade, as dependências de agregação e os holds/exceções aplicáveis impedem que um prazo comum seja interpretado como autorização de eliminação.
5. Uma divergência ou incerteza não resolvida deve ser registada para decisão humana; não pode sustentar redução de proteção ou eliminação.

| ID | Conteúdo decisório reconciliado | Especificação |
| --- | --- | --- |
| V03-01 | Timestamps aware em UTC; dias de 24 horas; meses e anos de calendário. | D2 #regras-v03 |
| V03-02 | Eventos de referência por classe; receção ou persistência tardia não reinicia o prazo; timestamp ausente ou relógio não fiável não justifica eliminação. | D2 #regras-v03 |
| V03-03 | Intervalos [start,end); clamp no último dia do calendário; elegibilidade quando nowUTC >= limite; sem reinício da contagem. | D2 #regras-v03 |
| V03-04 | PENDING/COMPLETE/PARTIAL; cobertura e completude herdadas; gaps explícitos, sem zeros artificiais; correções rastreáveis e idempotentes; brutos necessários protegidos. | D2 #regras-v03 |
| V03-05 | Tolerâncias configuráveis após o fim do intervalo: 5 minutos +10 minutos; horário +30 minutos; diário +2 horas. Não bloqueiam correções tardias. | D2 #regras-v03 |
| V03-06 | Elegibilidade temporal não autoriza limpeza; holds/exceções justificados, com responsáveis e revisão; incerteza bloqueia eliminação. | D2 #regras-v03 |
| V04-01 | Retenção online, retenção global e arquivo são âmbitos distintos. | D2 #regras-v04 |
| V04-02 | Permanência online durante a retenção global por defeito, segundo o catálogo discriminado por classes. | D2 #regras-v04 |
| V04-03 | Auditoria comum: 365 dias online/global; substituição limitada dos 12 meses online históricos, sem equivalência entre unidades nem alteração dos originais. | D2 #regras-v04 |
| V04-04 | Inventário/configuração durante a vida + arquivo; ativo, desativado e arquivado distintos; identidade, relações, histórico e configurações partilhadas preservados; arquivo lógico PostgreSQL. | D2 #regras-v04 |
| V04-05 | Revisão anual do arquivo; duração/disposição final TBD; sem expurgo autorizado. | D2 #regras-v04 |
| V04-06 | Integridade, consulta histórica controlada e recuperação; consulta não reativa; recuperação/reativação autorizada e auditada. | D2 #regras-v04 |
| V05-01 | Objetos mistos permanecem protegidos enquanto a separação segura não estiver demonstrada; o prazo comum não os liberta. | D2 #regras-v05 |
| V05-02 | Separação preserva original, conteúdo, identidade, timestamps, proveniência, ordem, continuidade e recuperabilidade; não concede autorização destrutiva. | D2 #regras-v05 |
| V05-03 | Cadeia de preservação auditável; hash isolado insuficiente para demonstrar conteúdo recuperável, custódia ou continuidade. | D2 #regras-v05 |
| V05-04 | Histórico de emissão, uso, consumo, revogação e expiração preservado, com vínculos e ordem exigidos por R2. | D2 #regras-v05 |
| V05-05 | Retenção R2 independente; prazo e condição final de libertação TBD. | D2 #regras-v05 |
| V05-06 | Demonstração verificável independentemente, distinta da confirmação D09; COMPROVADO/FALHA/INDETERMINADO; falha ou incerteza bloqueiam destruição; COMPROVADO não a autoriza. | D2 #regras-v05 |

As decisões são declaradas aprovadas no planeamento, com as oito correções expressamente aprovadas em DR-08B-03. A redação reconciliada foi aprovada para incorporação documental pelo pedido humano DR-08C nesta conversa. A aprovação dos bytes finais permanece pendente. A implementação e a demonstração operacional não são estabelecidas por este registo.

## Proteção R2 e âmbito

A política por classe consta da [adenda F0 (D2)](../../specifications/f0/dr07-retention-addendum.md). Aplica-se a [proteção R2 e de objetos mistos (M15)](../../specifications/f0/dr07-retention-addendum.md#protecao-r2); não se fixa prazo R2.

## Fontes preservadas e acesso entre ambientes

Fontes remotas: [registo arquitetural DAT-06B](../decision-register.md), [F0.28 e DAT-06B](../../specifications/f0/data-model.md), [baseline F0](../../specifications/f0/f0-baseline.md), [contratos R2](../auth-boot-02-r2.md) e [rastreabilidade R2](../auth-boot-02-r2-traceability.md). O registo complementar não reescreve a baseline DEV-03B/DEV-05A.

Fontes locais, com acesso separado no computador do utilizador, sem presumir presença em progbox:

- Plano e matriz M01–M17: `docs/reviews/release_1_0_consolidation_20261028/dr07b_documentary_plan_20261029/PLAN.md`.
- Preservação do plano: `docs/reviews/release_1_0_consolidation_20261028/dr07b_documentary_plan_20261029/PRESERVATION.json`.
- DR-04 e recuperação: `docs/reviews/release_1_0_consolidation_20261028/documentary_recovery_cf02_20261029/REPORT.md`.
- DR-07A: `docs/reviews/release_1_0_consolidation_20261028/dr07_stage_a_20261029/REPORT.md`.
- Síntese sucessora (D3): `docs/reviews/release_1_0_consolidation_20261028/dr07_retention_successor/ADDENDUM.md`.

DR-07B-01 e DR-07B-02 conservam a proveniência declarada, sem inventar identificadores de mensagens históricas ou datas dos atos anteriores. A aprovação conhecida não recupera os originais ausentes. DR-08B-02 é a base documental desta reconciliação; DR-08B-03 acrescenta as oito correções e as três verificações editoriais expressamente aprovadas no pedido humano. V02 permanece ABERTA. DR-07B-03/V06 é declarada concluída apenas quanto à revisão documental anterior. O pedido humano DR-08C nesta conversa autoriza exclusivamente a incorporação do pacote textual DR-08B-03 aprovado em D1/D2/D3; os bytes finais exigem aprovação humana própria, sem autorização operacional.

## Estados preservados

CF-02 ABERTA; V02 ABERTA; decisões V03–V05 declaradas aprovadas no planeamento, com as oito correções expressamente aprovadas em DR-08B-03; redação reconciliada aprovada para incorporação documental DR-08C; bytes finais pendentes de aprovação humana própria; DR-07B-03/V06 CONCLUÍDA apenas quanto à revisão documental anterior; H02–H12 PENDENTES/BLOQUEANTES; GAP-001/002 ABERTAS/BLOQUEANTES; AUTH-03/F02/G2/G4 e demais gates R2 FECHADOS/BLOQUEANTES; RG1–RG7 POR DEMONSTRAR; O3 NÃO APROVADO; DEV-09B NÃO AUTORIZADO; BASELINE NÃO OFICIAL; F0 Working draft. DR-08C: incorporação exclusivamente documental autorizada pelo pedido humano nesta conversa, sem autorização operacional.

<a id="nc01-indice"></a>

## DR-09A/P4-NC-01 — autoridade, proveniência e índice individual

Fonte autónoma primária: DR-09A/P4-NC-01 v1.1, Parte II, SHA-256 `794c21308c6126a6be1da9559b89ce644a36c02f2a51f2a913a79a87caa56ac1`. As 86 disposições constituem consolidação redacional completa, sem certificação de transcrição literal de atos históricos. A nota inicial da v1.1 prevalece na leitura das partes históricas I/III/IV: a fórmula de IV.7 «0 certificadas, 86 com lacuna» não descreve a completude redacional atual.

| Objeto | Alcance declarado no mandato e NC-01 v1.1 | Reserva de proveniência e efeito |
| --- | --- | --- |
| P3-A2 | Sucessor documental autónomo e limitado de DR-05; aceitação documental da recuperação F0.28/DAT-06B. | Não aprova retroativamente DR-05, não certifica equivalência literal nem recupera o original; V02/CF-02 abertas. Ato final integral, versão, data e referência primária não disponíveis nesta fonte. |
| Aprovação normativa P3 das 86 disposições | Declarada no mandato; as 86 redações e reservas estão consolidadas em NC-01 v1.1 Parte II. | Conserva o objeto normativo; não aprova bytes D1/D2/D3, incorporação ou operação. Mantém a reserva de certificação literal dos atos históricos. |
| P3-F-01 | Fecho normativo inicial. | Não autoriza escrita ou implementação; ato integral, objeto/versionamento e relação exata com as 86 entradas não cotejados com fonte primária. |
| P4-A-01 | Matriz de planeamento condicionada. | Condições finais e ato integral não certificados; não equivale a autorização P4-B. |
| Aprovação dos bytes DR-08C | Aprovação posterior declarada, distinta da autorização histórica de incorporação DR-08C. | Ato primário e associação aos ficheiros/versões/hashes indisponíveis nesta fonte; não certificar bytes aprovados nem declarar ausência de aprovação. |
| DR-07B-03/V06 | Revisão documental anterior declarada concluída. | Conserva o âmbito histórico; não aceita futuros bytes P4-B por extensão. |
| Bytes D1/D2/D3 de P4-B | Objeto documental próprio, distinto das decisões normativas P3 e dos bytes históricos DR-08C. | A autorização expressa de incorporação deve identificar destinos, bases e pacote exato; a aprovação dos bytes resultantes exige objeto próprio. Não se deduz dos atos anteriores nem oficializa a baseline. |

D2 contém a única transferência integral das 86 redações. Este índice identifica cada disposição sem repetir o seu conteúdo. As regras V03/V04/V05 e os prazos já documentados conservam-se, com as qualificações expressas da Parte II; uma divergência não resolvida bloqueia redução de proteção ou disposição destrutiva. Não se atribui autoridade histórica adicional à consolidação.

| Disposição NC-01 II.2 | Destino normativo D2 |
| --- | --- |
| B1-01 | [D2 #b1-01](../../specifications/f0/dr07-retention-addendum.md#b1-01) |
| B1-02 | [D2 #b1-02](../../specifications/f0/dr07-retention-addendum.md#b1-02) |
| B1-03 | [D2 #b1-03](../../specifications/f0/dr07-retention-addendum.md#b1-03) |
| B1-04 | [D2 #b1-04](../../specifications/f0/dr07-retention-addendum.md#b1-04) |
| B1-05 | [D2 #b1-05](../../specifications/f0/dr07-retention-addendum.md#b1-05) |
| B1-06 | [D2 #b1-06](../../specifications/f0/dr07-retention-addendum.md#b1-06) |
| B1-07 | [D2 #b1-07](../../specifications/f0/dr07-retention-addendum.md#b1-07) |
| B1-08 | [D2 #b1-08](../../specifications/f0/dr07-retention-addendum.md#b1-08) |
| B2-01 | [D2 #b2-01](../../specifications/f0/dr07-retention-addendum.md#b2-01) |
| B2-02 | [D2 #b2-02](../../specifications/f0/dr07-retention-addendum.md#b2-02) |
| B2-03 | [D2 #b2-03](../../specifications/f0/dr07-retention-addendum.md#b2-03) |
| B2-04 | [D2 #b2-04](../../specifications/f0/dr07-retention-addendum.md#b2-04) |
| B2-05 | [D2 #b2-05](../../specifications/f0/dr07-retention-addendum.md#b2-05) |
| B2-06 | [D2 #b2-06](../../specifications/f0/dr07-retention-addendum.md#b2-06) |
| B2-07 | [D2 #b2-07](../../specifications/f0/dr07-retention-addendum.md#b2-07) |
| B2-08 | [D2 #b2-08](../../specifications/f0/dr07-retention-addendum.md#b2-08) |
| B3-01 | [D2 #b3-01](../../specifications/f0/dr07-retention-addendum.md#b3-01) |
| B3-02 | [D2 #b3-02](../../specifications/f0/dr07-retention-addendum.md#b3-02) |
| B3-03 | [D2 #b3-03](../../specifications/f0/dr07-retention-addendum.md#b3-03) |
| B3-04 | [D2 #b3-04](../../specifications/f0/dr07-retention-addendum.md#b3-04) |
| B3-05 | [D2 #b3-05](../../specifications/f0/dr07-retention-addendum.md#b3-05) |
| B3-06 | [D2 #b3-06](../../specifications/f0/dr07-retention-addendum.md#b3-06) |
| B3-07 | [D2 #b3-07](../../specifications/f0/dr07-retention-addendum.md#b3-07) |
| B3-08 | [D2 #b3-08](../../specifications/f0/dr07-retention-addendum.md#b3-08) |
| B4-01 | [D2 #b4-01](../../specifications/f0/dr07-retention-addendum.md#b4-01) |
| B4-02 | [D2 #b4-02](../../specifications/f0/dr07-retention-addendum.md#b4-02) |
| B4-03 | [D2 #b4-03](../../specifications/f0/dr07-retention-addendum.md#b4-03) |
| B4-04 | [D2 #b4-04](../../specifications/f0/dr07-retention-addendum.md#b4-04) |
| B4-05 | [D2 #b4-05](../../specifications/f0/dr07-retention-addendum.md#b4-05) |
| B4-06 | [D2 #b4-06](../../specifications/f0/dr07-retention-addendum.md#b4-06) |
| B4-07 | [D2 #b4-07](../../specifications/f0/dr07-retention-addendum.md#b4-07) |
| B4-08 | [D2 #b4-08](../../specifications/f0/dr07-retention-addendum.md#b4-08) |
| B5-01 | [D2 #b5-01](../../specifications/f0/dr07-retention-addendum.md#b5-01) |
| B5-02 | [D2 #b5-02](../../specifications/f0/dr07-retention-addendum.md#b5-02) |
| B5-03 | [D2 #b5-03](../../specifications/f0/dr07-retention-addendum.md#b5-03) |
| B5-04 | [D2 #b5-04](../../specifications/f0/dr07-retention-addendum.md#b5-04) |
| B5-05 | [D2 #b5-05](../../specifications/f0/dr07-retention-addendum.md#b5-05) |
| B5-06 | [D2 #b5-06](../../specifications/f0/dr07-retention-addendum.md#b5-06) |
| B5-07 | [D2 #b5-07](../../specifications/f0/dr07-retention-addendum.md#b5-07) |
| B5-08 | [D2 #b5-08](../../specifications/f0/dr07-retention-addendum.md#b5-08) |
| B6-01 | [D2 #b6-01](../../specifications/f0/dr07-retention-addendum.md#b6-01) |
| B6-02 | [D2 #b6-02](../../specifications/f0/dr07-retention-addendum.md#b6-02) |
| B6-03 | [D2 #b6-03](../../specifications/f0/dr07-retention-addendum.md#b6-03) |
| B6-04 | [D2 #b6-04](../../specifications/f0/dr07-retention-addendum.md#b6-04) |
| B6-05 | [D2 #b6-05](../../specifications/f0/dr07-retention-addendum.md#b6-05) |
| B6-06 | [D2 #b6-06](../../specifications/f0/dr07-retention-addendum.md#b6-06) |
| B6-07 | [D2 #b6-07](../../specifications/f0/dr07-retention-addendum.md#b6-07) |
| B6-08 | [D2 #b6-08](../../specifications/f0/dr07-retention-addendum.md#b6-08) |
| B7-01 | [D2 #b7-01](../../specifications/f0/dr07-retention-addendum.md#b7-01) |
| B7-02 | [D2 #b7-02](../../specifications/f0/dr07-retention-addendum.md#b7-02) |
| B7-03 | [D2 #b7-03](../../specifications/f0/dr07-retention-addendum.md#b7-03) |
| B7-04 | [D2 #b7-04](../../specifications/f0/dr07-retention-addendum.md#b7-04) |
| B7-05 | [D2 #b7-05](../../specifications/f0/dr07-retention-addendum.md#b7-05) |
| B7-06 | [D2 #b7-06](../../specifications/f0/dr07-retention-addendum.md#b7-06) |
| B7-07 | [D2 #b7-07](../../specifications/f0/dr07-retention-addendum.md#b7-07) |
| B7-08 | [D2 #b7-08](../../specifications/f0/dr07-retention-addendum.md#b7-08) |
| B8-01 | [D2 #b8-01](../../specifications/f0/dr07-retention-addendum.md#b8-01) |
| B8-02 | [D2 #b8-02](../../specifications/f0/dr07-retention-addendum.md#b8-02) |
| B8-03 | [D2 #b8-03](../../specifications/f0/dr07-retention-addendum.md#b8-03) |
| B8-04 | [D2 #b8-04](../../specifications/f0/dr07-retention-addendum.md#b8-04) |
| B8-05 | [D2 #b8-05](../../specifications/f0/dr07-retention-addendum.md#b8-05) |
| B8-06 | [D2 #b8-06](../../specifications/f0/dr07-retention-addendum.md#b8-06) |
| B8-07 | [D2 #b8-07](../../specifications/f0/dr07-retention-addendum.md#b8-07) |
| B8-08 | [D2 #b8-08](../../specifications/f0/dr07-retention-addendum.md#b8-08) |
| B8-09 | [D2 #b8-09](../../specifications/f0/dr07-retention-addendum.md#b8-09) |
| B8-10 | [D2 #b8-10](../../specifications/f0/dr07-retention-addendum.md#b8-10) |
| B9-01 | [D2 #b9-01](../../specifications/f0/dr07-retention-addendum.md#b9-01) |
| B9-02 | [D2 #b9-02](../../specifications/f0/dr07-retention-addendum.md#b9-02) |
| B9-03 | [D2 #b9-03](../../specifications/f0/dr07-retention-addendum.md#b9-03) |
| B9-04 | [D2 #b9-04](../../specifications/f0/dr07-retention-addendum.md#b9-04) |
| B9-05 | [D2 #b9-05](../../specifications/f0/dr07-retention-addendum.md#b9-05) |
| B9-06 | [D2 #b9-06](../../specifications/f0/dr07-retention-addendum.md#b9-06) |
| B9-07 | [D2 #b9-07](../../specifications/f0/dr07-retention-addendum.md#b9-07) |
| B9-08 | [D2 #b9-08](../../specifications/f0/dr07-retention-addendum.md#b9-08) |
| B9-09 | [D2 #b9-09](../../specifications/f0/dr07-retention-addendum.md#b9-09) |
| B9-10 | [D2 #b9-10](../../specifications/f0/dr07-retention-addendum.md#b9-10) |
| B10-01 | [D2 #b10-01](../../specifications/f0/dr07-retention-addendum.md#b10-01) |
| B10-02 | [D2 #b10-02](../../specifications/f0/dr07-retention-addendum.md#b10-02) |
| B10-03 | [D2 #b10-03](../../specifications/f0/dr07-retention-addendum.md#b10-03) |
| B10-04 | [D2 #b10-04](../../specifications/f0/dr07-retention-addendum.md#b10-04) |
| B10-05 | [D2 #b10-05](../../specifications/f0/dr07-retention-addendum.md#b10-05) |
| B10-06 | [D2 #b10-06](../../specifications/f0/dr07-retention-addendum.md#b10-06) |
| B10-07 | [D2 #b10-07](../../specifications/f0/dr07-retention-addendum.md#b10-07) |
| B10-08 | [D2 #b10-08](../../specifications/f0/dr07-retention-addendum.md#b10-08) |
| B10-09 | [D2 #b10-09](../../specifications/f0/dr07-retention-addendum.md#b10-09) |
| B10-10 | [D2 #b10-10](../../specifications/f0/dr07-retention-addendum.md#b10-10) |

Os caminhos lógicos das fontes locais acima identificam documentos com acesso separado; a sua presença na árvore remota não é pressuposta.

### Estados e limites atuais

V02/CF-02 ABERTAS; H02–H12 PENDENTES/BLOQUEANTES; GAP-001/002 ABERTAS/BLOQUEANTES; AUTH-03/F02/G2/G4 FECHADOS/BLOQUEANTES; RG1–RG7, R2 D09 e V05-06 POR DEMONSTRAR; O3 NÃO APROVADO; DEV-09B NÃO AUTORIZADO; BASELINE NÃO OFICIAL; F0 Working draft.

Os parâmetros TBD e as reservas de grupo constam de D2 #nc01-b1 a #nc01-b10. Não existe autorização de eliminação automática, implementação, operação ou abertura de gates.
