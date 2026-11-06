# LiveNet v2 — DR-07: adenda de retenção F0

<a id="p4-b1-leitura"></a>

## Leitura atual DR-09A/P4-NC-01 — autoridade e âmbito documental

30 de outubro de 2026 · Europe/Lisbon. Referência principal: DR-09A/P4-NC-01 v1.1, Parte II, SHA-256 `794c21308c6126a6be1da9559b89ce644a36c02f2a51f2a913a79a87caa56ac1`. A aprovação normativa P3 das 86 disposições, declarada no mandato, conserva o seu objeto; esta consolidação redacional não certifica transcrição literal dos atos históricos. P3-A2, P3-F-01 e P4-A-01 mantêm os âmbitos e reservas registados em D1 #nc01-indice. As autorizações históricas DR-07B-02/DR-08C conservam o seu objeto. As menções abaixo a revisão ou aprovação pendente dos bytes DR-08C descrevem o registo anterior à aprovação posterior declarada em NC-01 v1.1. A fonte primária desse ato separado e a associação exata a ficheiros, versões e hashes continuam por cotejar; esta reserva não demonstra ausência de aprovação. A aprovação normativa P3 e a aprovação histórica DR-08C não aprovam por extensão os novos bytes D1/D2/D3 de P4-B: a sua incorporação documental exige autorização expressa do pacote exato e a aprovação dos bytes resultantes exige objeto próprio. Uma eventual incorporação documental não oficializa a baseline; F0 permanece Working draft. A leitura histórica do corpo anterior observa esta delimitação temporal.

**INCORPORAÇÃO DOCUMENTAL AUTORIZADA — DR-07B-02. BASELINE NÃO OFICIAL. CF-02 ABERTA. Bytes finais sujeitos a revisão humana. Sem autorização de implementação, limpeza ou alteração de gates.**

29 de outubro de 2026 · Europe/Lisbon. Incorporação exclusivamente documental autorizada pelo pedido humano DR-07B-02, a partir do plano DR-07B aprovado. A aprovação da incorporação não aprova automaticamente estes bytes finais. A referência histórica a Etapa B não autorizada é atualizada apenas quanto à criação documental de D1/D2/D3; nenhuma execução operacional é autorizada.

## Proveniência e leitura

As decisões e os limites da reconstrução DR-05 constam do [registo complementar (D1)](../../architecture/proposals/dr07-retention-decisions.md). Fonte histórica: [F0.28, §4, §6 e DAT-06B](data-model.md), preservada integralmente, incluindo DEV-06/DEV-08B. A [baseline F0](f0-baseline.md) permanece Working draft. Os valores declarados provêm de DR-06/CF-02A-01/CF-02B-01, com discriminação M02–M11/M15 do plano. A proveniência DH-03F dos logs é explicitada na síntese sucessora local D3, com acesso separado, identificado pelo caminho lógico: `docs/reviews/release_1_0_consolidation_20261028/dr07_retention_successor/ADDENDUM.md`.

A reconciliação DR-08B-03 tem por base o relatório DR-08B-02 e o pedido humano que aprova expressamente oito correções e três verificações editoriais. D1 regista as 18 decisões, a proveniência e as precedências. As secções #regras-v03, #regras-v04 e #regras-v05 contêm a especificação normativa desta atualização. O texto integral anteriormente aprovado de P2-B1/P2-B2/P2-B3 não foi recuperado; esta redação foi aprovada para incorporação documental pelo pedido humano DR-08C nesta conversa e não é apresentada como transcrição certificada. Os bytes finais ficam sujeitos a aprovação humana separada.

<a id="checks"></a>

## Checks

Verificações individuais e checks individuais designam a mesma classe; a retenção aprovada dessa classe é 30 dias. Na reconciliação documental, este prazo substitui apenas os 90 dias históricos das verificações individuais em DAT-06B. Checks, métricas brutas, logs de diagnóstico e agregados permanecem classes distintas. O original permanece preservado.

<a id="metricas-brutas"></a>

## Métricas brutas

Métricas brutas: 30 dias. Mantém-se a dependência histórica de agregação concluída antes de qualquer eventual eliminação de dados brutos. Aplicam-se cobertura e completude herdadas, lacunas explícitas, correções rastreáveis e idempotentes, tolerâncias configuráveis e proteção dos brutos necessários, conforme V03-04..06 em #regras-v03. O decurso do prazo ou de uma tolerância não demonstra completude nem autoriza limpeza. O algoritmo completo de cálculo da cobertura/completude não é fixado por esta redação.

<a id="agregados-5-minutos"></a>

## Agregados de 5 minutos

Agregados de 5 minutos: 180 dias. Para esta granularidade, a reconciliação documental afasta o prazo indiferenciado de 365 dias da síntese DH-03F. Não se aplica 180 dias a outras granularidades.

<a id="agregados-horarios"></a>

## Agregados horários

Agregados horários: 12 meses de calendário. Mantém-se a unidade aprovada, sem conversão para 365 dias. Aplicam-se o evento de referência, as fronteiras e o clamp de calendário definidos em V03-01..03, bem como as regras de agregação e proteção V03-04..06, em #regras-v03.

<a id="agregados-diarios"></a>

## Agregados diários

Agregados diários: 3 anos. A decisão atual declarada reconfirma esta parcela de retenção da prosa do §4. A tabela histórica DAT-06B não enumera agregados diários; conserva-se essa omissão como facto documental, sem a tratar como revogação nem inserir uma linha retroativa no original. Não se convertem 3 anos em 1095 dias.

<a id="limite-paragrafo-4"></a>

## Limite da reconciliação do §4

A reconciliação do §4 abrange exclusivamente as parcelas de retenção identificadas nesta adenda. Não reconfirma o parágrafo inteiro, não aprova freshness de 3 intervalos e não altera CF-04. Os parâmetros de transição 3/2 e as suas fontes próprias não recebem nova aprovação através desta adenda.

<a id="auditoria-comum"></a>

## Auditoria comum

Auditoria comum de produto: 365 dias online e global, excluindo evidência protegida R2 e informação necessária à continuidade. Aplica-se exclusivamente a substituição delimitada V04-03 em #regras-v04. F0.28 §6 e DAT-06B conservam as referências históricas a 12 meses online. Não se estabelece equivalência entre 12 meses de calendário e 365 dias, nem se infere um prazo posterior de arquivo. Mantêm-se integridade, append-only e requisitos de preservação. O prazo não autoriza eliminação.

<a id="eventos-identificados"></a>

## Eventos identificados

Transições de estado: 365 dias. Alertas: 365 dias. Reconhecimentos de alerta (ack): 365 dias. Esta enumeração não atribui 365 dias a todos os eventos operacionais. Ack de alerta não equivale à confirmação independente de evidência R2/D09. Aplicam-se os eventos de referência V03-02 em #regras-v03 e o âmbito online/global V04-02 em #regras-v04.

<a id="logs-diagnostico"></a>

## Logs de diagnóstico

Logs de diagnóstico: 30 dias. Constituem classe distinta dos checks individuais e das métricas brutas. Objetos que contenham evidência R2 ou informação necessária à continuidade dependem da classificação e proteção próprias de R2; a rotação de logs não demonstra conservação da evidência.

<a id="inventario-configuracao"></a>

## Inventário e configuração

Inventário e configuração: durante a vida do recurso + arquivo, de duração final TBD. Aplicam-se os estados distintos ativo, desativado e arquivado, a preservação de identidade, relações, histórico e configurações partilhadas, o arquivo lógico PostgreSQL, a revisão anual e as condições de consulta, recuperação e reativação de V04-04..06 em #regras-v04. A desativação não inicia automaticamente o arquivo nem autoriza eliminação. Configurações globais, de grupo ou partilhadas não recebem automaticamente a vida de um único recurso. Estado atual permanece uma classe histórica distinta até reconciliação específica. A entrada em arquivo exige a autorização e as verificações de B5 em #nc01-b5; os detalhes não fixados nessas disposições permanecem por especificar. A duração e a disposição final seguem B6 em #nc01-b6, com prazos TBD.

<a id="protecao-r2"></a>

## Proteção R2

Evidência protegida R2 e informação necessária à continuidade: regime independente; prazo e condição final de libertação não definidos. Sem prazo definido não significa retenção eterna aprovada nem autorização de eliminação. Os prazos comuns de produto, a janela de 900 segundos e a rotação de logs ou backups não constituem prazo R2. Mantêm-se C1/C3/C4/C5/C6, incluindo evidência essencial local, ordem, vínculos, não libertação por rollback, tratamento de incerteza, confirmação independente D09 e continuidade na recuperação. Objetos mistos exigem classificação e preservação verificável do conteúdo protegido; um hash sem conteúdo recuperável não demonstra custódia. Este plano não aprova separação física, transformação, expurgo ou condição de libertação. C1–C7 e a rastreabilidade R2 permanecem intactos.

<a id="regras-v03"></a>

## Regras temporais e de agregação — V03

### V03-01 — Unidades e referência temporal

Os timestamps usados na contagem devem identificar inequivocamente o fuso horário e ser expressos em UTC. Um dia corresponde a 24 horas. Meses e anos são unidades de calendário, sem conversão para um número fixo de dias.

### V03-02 — Evento de referência e chegada tardia

O início da contagem deve usar o evento próprio da classe:

| Classe | Evento de referência |
| --- | --- |
| Checks individuais | Conclusão do check |
| Métricas brutas | Observação da métrica |
| Logs de diagnóstico | Emissão do log |
| Agregados | Fim do intervalo representado |
| Transições de estado | Instante efetivo da transição |
| Alertas | Criação do alerta |
| Reconhecimentos de alerta | Instante do reconhecimento |
| Auditoria comum | Instante fiável do evento auditado |
| Inventário e configuração | Ciclo de vida, sujeito a V04-04..06 |
| Evidência R2 e informação necessária à continuidade | Regime independente V05 |

A receção, ingestão ou persistência tardia não deve substituir o evento de referência nem reiniciar a contagem do prazo.

A ausência de timestamp fiável ou a falta de fiabilidade do relógio não demonstra que o prazo terminou e não pode justificar eliminação. Deve conservar-se a incerteza e bloquear-se a eliminação enquanto não existir base temporal fiável e verificada. Esta regra não inventa um timestamp substituto nem define um mecanismo técnico de correção do relógio.

### V03-03 — Fronteiras e elegibilidade temporal

Os intervalos de agregação devem usar a convenção [start,end): início incluído e fim excluído.

O limite de retenção deve resultar da aplicação da duração da classe ao respetivo evento de referência. Na adição de meses ou anos de calendário, quando o dia correspondente não existir no mês de destino, deve usar-se o último dia desse mês, preservando a componente horária UTC.

A condição temporal é nowUTC >= limite. A igualdade ao limite satisfaz apenas a condição temporal. Receção, persistência ou correção posterior não reinicia a contagem.

Esta condição depende da fiabilidade temporal de V03-02 e não substitui as condições de preservação, dependências, holds, arquivo ou R2.

### V03-04 — Cobertura, completude e correções

A agregação deve distinguir PENDING, COMPLETE e PARTIAL. A cobertura e a completude do resultado devem refletir as dos dados e agregados de origem. Uma agregação de nível superior não pode ocultar lacunas ou incompletude herdadas nem apresentar como integral a cobertura que as fontes não sustentam.

Os gaps devem permanecer explícitos. Ausência de observação não deve ser convertida em valor zero nem ser usada como prova de completude.

As correções devem ser rastreáveis e idempotentes: o reprocessamento da mesma correção não deve duplicar o seu efeito. A rastreabilidade deve permitir relacionar a correção com o resultado afetado e a respetiva origem, sem impor neste documento um schema ou mecanismo de implementação.

Os brutos necessários para concluir, verificar ou corrigir a agregação devem permanecer protegidos. A mera existência de um agregado, o estado declarado sem suporte verificável ou o decurso do prazo bruto não satisfazem a dependência histórica de agregação concluída.

Esta redação não define o algoritmo completo de cobertura/completude, limiares quantitativos ou uma máquina de estados de implementação.

### V03-05 — Tolerâncias e correções tardias

As tolerâncias de referência são configuráveis e contam-se após o fim do intervalo representado:

| Granularidade | Tolerância de referência |
| --- | --- |
| Agregado de 5 minutos | Fim do intervalo +10 minutos |
| Agregado horário | Fim do intervalo +30 minutos |
| Agregado diário | Fim do intervalo +2 horas |

Estas tolerâncias não alteram as durações de retenção das classes.

O seu decurso não deve, por si só, determinar COMPLETE, apagar gaps, dispensar a verificação de cobertura ou autorizar eliminação. Também não deve impedir a receção e o tratamento de correções tardias, que continuam sujeitos a rastreabilidade, idempotência e preservação dos dados necessários.

A configuração e a alteração destes valores exigem o processo autorizado aplicável; esta adenda não executa nem autoriza mudanças de configuração. Não se alteram a janela de 900 segundos nem as condições dos contratos R2.

### V03-06 — Dependências, holds e exceções

Elegibilidade temporal não constitui autorização de limpeza. Antes de qualquer eventual eliminação autorizada, devem estar resolvidas as dependências de agregação, preservação, continuidade, arquivo e R2 aplicáveis.

Holds e exceções devem ter justificação documentada, responsáveis identificados e revisão registada. A revisão deve permitir verificar a manutenção ou resolução da causa e o âmbito afetado.

Um hold ou exceção não constitui autorização genérica para encurtar a proteção. A passagem da data de revisão não demonstra resolução da causa nem levanta automaticamente o bloqueio. A incerteza sobre aplicabilidade, cobertura, continuidade, fiabilidade temporal ou levantamento deve bloquear a eliminação.

Não são definidos nesta adenda novos prazos de hold, um procedimento operacional de levantamento ou uma autorização de limpeza.

<a id="regras-v04"></a>

## Âmbitos de retenção e arquivo — V04

### V04-01 — Online, global e arquivo

Retenção online, retenção global e arquivo devem ser distinguidos. A localização, acessibilidade ou mudança de estado não deve ser interpretada como autorização para reduzir a retenção ou eliminar conteúdo.

O arquivo não se confunde com backup nem recebe automaticamente os prazos das classes comuns.

### V04-02 — Catálogo e permanência online

Por defeito, os dados devem permanecer online durante a respetiva retenção global:

| Classe | Retenção global e permanência online por defeito |
| --- | --- |
| Checks individuais | 30 dias |
| Métricas brutas | 30 dias |
| Logs de diagnóstico | 30 dias |
| Agregados de 5 minutos | 180 dias |
| Agregados horários | 12 meses de calendário |
| Agregados diários | 3 anos de calendário |
| Transições de estado | 365 dias |
| Alertas | 365 dias |
| Reconhecimentos de alerta | 365 dias |
| Auditoria comum | 365 dias, segundo V04-03 |
| Inventário e configuração | Vida do recurso + arquivo de duração TBD, segundo V04-04..06 |
| Evidência R2 e informação necessária à continuidade | Regime independente; prazo TBD, segundo V05 |

A permanência online por defeito acompanha a retenção global declarada; esta regra não fixa um prazo final de arquivo para inventário/configuração nem um prazo R2.

Aplicam-se os eventos e unidades V03, as dependências de agregação, os holds e a proteção R2. O termo de um prazo comum não liberta conteúdo protegido.

### V04-03 — Substituição limitada da auditoria comum

A auditoria comum de produto tem retenção online e global de 365 dias.

Esta decisão substitui exclusivamente, no âmbito sucessor da auditoria comum, a referência histórica a 12 meses online de F0.28 §6/DAT-06B. Não estabelece equivalência entre 12 meses de calendário e 365 dias, não altera outras classes e não define retenção posterior de arquivo.

Os originais F0.28/DAT-06B devem permanecer intactos. A evidência R2 e a informação necessária à continuidade conservam o respetivo regime independente. Mantêm-se integridade e append-only. A substituição documental não autoriza eliminação.

### V04-04 — Ciclo de vida e arquivo lógico

No inventário e configuração, ativo, desativado e arquivado são estados distintos.

A desativação não deve ser tratada como eliminação, perda de identidade ou entrada automática em arquivo. O arquivo lógico PostgreSQL deve preservar identidade estável, relações e histórico, sem apagar a distinção entre estados.

Configurações globais, de grupo ou partilhadas devem conservar as relações com os recursos e contextos que delas dependem. A desativação ou o arquivo de um único recurso não demonstra o fim de vida de uma configuração partilhada e não autoriza a sua eliminação ou a perda de relações históricas.

Inventário e configuração seguem a vida do recurso + arquivo. A entrada em arquivo segue B5 em #nc01-b5; os detalhes não definidos permanecem por especificar e a duração final segue B6 em #nc01-b6, com prazos TBD. Estado atual mantém classe conceptual autónoma nos termos de B4 em #nc01-b4; configurações partilhadas seguem também B7 em #nc01-b7.

Esta disposição não autoriza alterações de schemas, movimentação de dados ou ativação de mecanismos.

### V04-05 — Revisão e disposição final

O arquivo deve ser objeto de revisão anual. A duração final e a disposição final permanecem TBD.

A revisão não constitui expurgo nem autoriza eliminação. A ausência de duração definida também não deve ser apresentada como aprovação de retenção eterna.

### V04-06 — Consulta, recuperação e reativação

Devem ser preservadas a integridade, a consulta histórica controlada e a capacidade de recuperação.

A consulta de informação histórica ou arquivada não deve reativar o recurso nem alterar implicitamente o seu estado.

A recuperação e a reativação devem ser autorizadas para o respetivo âmbito e auditadas. A autorização de recuperação não deve ser presumida como autorização de reativação; quando ambas forem pretendidas, ambas devem estar abrangidas expressamente.

Devem manter-se identidade, relações, histórico e requisitos de continuidade aplicáveis. Esta regra não executa recuperação ou reativação nem define novos mecanismos de autorização.

<a id="regras-v05"></a>

## Preservação R2 e objetos mistos — V05

### V05-01 — Proteção de objetos mistos

Quando um objeto contenha evidência R2 ou informação necessária à continuidade, deve permanecer protegido enquanto não estiver demonstrada a separação segura do conteúdo protegido.

O termo do prazo de uma classe comum não liberta o objeto misto. A incerteza sobre classificação, separação ou continuidade mantém a proteção.

### V05-02 — Condições de separação

Uma eventual separação deve preservar o original e permitir verificar a conservação do conteúdo protegido, da identidade, dos timestamps, da proveniência, da ordem, dos vínculos, da continuidade e da recuperabilidade.

Uma cópia, transformação, extração ou representação derivada não demonstra, por si só, o cumprimento destas condições. A verificação deve abranger o conteúdo recuperável e a sua relação com o original.

A demonstração de separação não autoriza destruir, substituir ou alterar o original, eliminar o objeto misto ou libertar conteúdo protegido. Qualquer operação física e qualquer disposição destrutiva exigem autorização própria, ausente deste pacote.

### V05-03 — Cadeia de preservação

A preservação deve dispor de cadeia auditável que sustente conteúdo recuperável, proveniência, custódia e continuidade.

Um hash isolado, mesmo coincidente, não demonstra a existência de conteúdo recuperável, a custódia ou a continuidade. Deve ser possível verificar a relação entre a evidência preservada, as operações relevantes e o conteúdo que pode ser recuperado.

### V05-04 — Histórico e continuidade R2

Deve ser preservado o histórico de emissão, uso, consumo, revogação e expiração, com os vínculos, a ordem e os requisitos de continuidade previstos nos contratos R2 preservados.

A expiração de uma admissão não define o prazo da evidência que lhe diz respeito. Rollback não liberta evidência nem dispensa os requisitos de continuidade na recuperação.

### V05-05 — Retenção independente

A retenção R2 e a da informação necessária à continuidade são independentes das retenções comuns de produto. O prazo e a condição final de libertação permanecem TBD.

Não se infere um prazo R2 da janela de 900 segundos, da rotação de logs, de backups ou das durações das classes comuns. A ausência de prazo definido não aprova retenção eterna nem autoriza eliminação.

### V05-06 — Demonstração e resultado

A demonstração de preservação, separação e continuidade deve poder ser verificada independentemente, mediante evidência suficiente sobre o objeto avaliado, as condições verificadas e o resultado obtido.

A avaliação deve distinguir:

| Resultado | Consequência |
| --- | --- |
| COMPROVADO | As condições avaliadas foram demonstradas no âmbito identificado; não constitui autorização de destruição. |
| FALHA | Existe incumprimento demonstrado; a destruição permanece bloqueada. |
| INDETERMINADO | A evidência é insuficiente ou a conclusão permanece incerta; a destruição permanece bloqueada. |

Esta demonstração é distinta da confirmação independente D09. Não substitui D09, não é dispensada por D09 e não permite usar um resultado COMPROVADO como confirmação D09.

C1–C7, a confirmação independente D09, a não libertação por rollback, a preservação da ordem e o bloqueio perante continuidade desconhecida permanecem intactos. Não são definidos novos schemas, campos, assinaturas ou capacidades.

<a id="nc01-disposicoes"></a>

## DR-09A/P4-NC-01 — disposições consolidadas B1–B10

Fonte autónoma primária: DR-09A/P4-NC-01 v1.1, Parte II, SHA-256 `794c21308c6126a6be1da9559b89ce644a36c02f2a51f2a913a79a87caa56ac1`. As 86 disposições constituem consolidação redacional completa, sem certificação de transcrição literal de atos históricos. A nota inicial da v1.1 prevalece na leitura das partes históricas I/III/IV: a fórmula de IV.7 «0 certificadas, 86 com lacuna» não descreve a completude redacional atual.

Autoridade e atos distintos: [D1 #nc01-indice](../../architecture/proposals/dr07-retention-decisions.md#nc01-indice). A aprovação normativa P3 das 86 disposições é declarada no mandato; a transferência fornece as redações e reservas de NC-01 v1.1, sem certificar os atos históricos nem aprovar os novos bytes por extensão. Os requisitos existentes V03/V04/V05 continuam aplicáveis; as remissões por grupo qualificam os pontos correspondentes. As novas classes Discovery e outbox não recebem por inferência o prazo geral de eventos. Prazo nominal, revisão anual, arquivo ou libertação de proteção não autorizam eliminação automática.

<a id="nc01-b1"></a>

### B1 — Cobertura, completude e correções

Reserva/condição: **Algoritmos específicos TBD.**

Articulação com o texto existente: Métricas brutas; V03-04/05/06.

<a id="b1-01"></a>

**B1-01** — A completude é avaliada segundo os dados esperados para cada métrica, fonte e configuração válida.

<a id="b1-02"></a>

**B1-02** — A avaliação considera a atividade e a aplicabilidade da fonte durante o intervalo.

<a id="b1-03"></a>

**B1-03** — COMPLETE exige cobertura integral demonstrável dos dados esperados.

<a id="b1-04"></a>

**B1-04** — PARTIAL identifica lacunas relativamente à cobertura esperada.

<a id="b1-05"></a>

**B1-05** — PENDING representa uma avaliação ainda não concluída ou não demonstrável.

<a id="b1-06"></a>

**B1-06** — A incompletude dos dados de origem não pode desaparecer implicitamente nos agregados derivados.

<a id="b1-07"></a>

**B1-07** — Correções tardias devem ser idempotentes, rastreáveis e preservar a proveniência.

<a id="b1-08"></a>

**B1-08** — A ausência de observações não demonstra, por si só, completude nem justifica um limiar percentual universal.

<a id="nc01-b2"></a>

### B2 — Referências temporais, correções e holds

Reserva/condição: **Métodos e autoridades TBD; sem alteração R2.**

Articulação com o texto existente: V03-02/03/06.

<a id="b2-01"></a>

**B2-01** — Preservar o timestamp original e a respetiva proveniência.

<a id="b2-02"></a>

**B2-02** — Distinguir tempo do evento, receção e persistência.

<a id="b2-03"></a>

**B2-03** — Correções temporais não reiniciam automaticamente os prazos de retenção.

<a id="b2-04"></a>

**B2-04** — Relógios não fiáveis não constituem, isoladamente, fundamento para eliminação.

<a id="b2-05"></a>

**B2-05** — Correções exigem motivo, responsável, momento e rastreabilidade.

<a id="b2-06"></a>

**B2-06** — A incerteza sobre a referência temporal necessária impede disposição destrutiva automática.

<a id="b2-07"></a>

**B2-07** — Holds devem identificar objeto, motivo, responsável, evidência e revisão.

<a id="b2-08"></a>

**B2-08** — O levantamento de um hold exige decisão justificada e auditável, sem autorizar automaticamente eliminação.

<a id="nc01-b3"></a>

### B3 — Catálogo de eventos operacionais

Reserva/condição: **Catálogo final TBD.**

Articulação com o texto existente: Eventos identificados; V03-02; V04-02.

<a id="b3-01"></a>

**B3-01** — Manter um catálogo central de classes de eventos operacionais.

<a id="b3-02"></a>

**B3-02** — Identificar objeto, finalidade e referência temporal de cada classe.

<a id="b3-03"></a>

**B3-03** — Definir retenção e âmbito online/global por classe.

<a id="b3-04"></a>

**B3-04** — Aplicar 365 dias apenas às classes já abrangidas pelas decisões existentes, sem extensão automática.

<a id="b3-05"></a>

**B3-05** — Eventos não classificados não recebem autorização de eliminação automática.

<a id="b3-06"></a>

**B3-06** — Preservar a precedência das obrigações de auditoria e proteção R2.

<a id="b3-07"></a>

**B3-07** — Identificar dependências entre originais, cópias e derivados, incluindo Discovery, outbox e configurações.

<a id="b3-08"></a>

**B3-08** — Alterações às políticas exigem aprovação humana rastreável.

<a id="nc01-b4"></a>

### B4 — Estado atual

Reserva/condição: **Sem reserva adicional específica declarada; mantêm-se as condições das disposições.**

Articulação com o texto existente: Inventário e configuração; V04-04.

<a id="b4-01"></a>

**B4-01** — O estado atual constitui uma classe conceptual autónoma enquanto não existir mapeamento sucessor aprovado.

<a id="b4-02"></a>

**B4-02** — O estado atual deve estar associado à identidade estável do recurso.

<a id="b4-03"></a>

**B4-03** — Distinguir estado atual, inventário e histórico de transições.

<a id="b4-04"></a>

**B4-04** — A ausência de observações não determina automaticamente um novo estado.

<a id="b4-05"></a>

**B4-05** — A desativação do recurso não elimina o último estado conhecido.

<a id="b4-06"></a>

**B4-06** — O arquivo lógico preserva o contexto necessário à interpretação do estado.

<a id="b4-07"></a>

**B4-07** — Uma representação derivada só substitui o estado preservado quando a reconstrução for demonstrável.

<a id="b4-08"></a>

**B4-08** — O fim de vida lógico e a disposição final exigem decisão específica.

<a id="nc01-b5"></a>

### B5 — Entrada em arquivo

Reserva/condição: **Alternativa A.**

Articulação com o texto existente: Inventário e configuração; V04-04/06.

<a id="b5-01"></a>

**B5-01** — A entrada em arquivo exige autorização humana explícita, identificável e auditável.

<a id="b5-02"></a>

**B5-02** — Desativação, ausência de contacto ou decurso do tempo não autorizam arquivo automático.

<a id="b5-03"></a>

**B5-03** — Confirmar a identidade estável do recurso e as relações relevantes.

<a id="b5-04"></a>

**B5-04** — Preservar o último estado conhecido e o histórico necessário.

<a id="b5-05"></a>

**B5-05** — Avaliar configurações partilhadas, dependências, holds e proteção R2.

<a id="b5-06"></a>

**B5-06** — Registar recurso, responsável, justificação, momento e resultado da operação.

<a id="b5-07"></a>

**B5-07** — Arquivo não equivale a eliminação nem ao levantamento de holds.

<a id="b5-08"></a>

**B5-08** — Consulta, recuperação e reativação são operações distintas.

<a id="nc01-b6"></a>

### B6 — Duração e disposição final do arquivo

Reserva/condição: **Alternativa C; prazos TBD.**

Articulação com o texto existente: V04-05.

<a id="b6-01"></a>

**B6-01** — A duração do arquivo depende da classe, finalidade e dependências.

<a id="b6-02"></a>

**B6-02** — O modelo exige um período mínimo aprovado e condições verificáveis de preservação.

<a id="b6-03"></a>

**B6-03** — Os prazos concretos devem ser definidos por decisão específica.

<a id="b6-04"></a>

**B6-04** — O termo de um prazo não determina disposição final automática.

<a id="b6-05"></a>

**B6-05** — A revisão documental anual não constitui autorização de eliminação.

<a id="b6-06"></a>

**B6-06** — A disposição final exige autorização humana explícita e auditável, respeitando proteções e dependências.

<a id="b6-07"></a>

**B6-07** — Originais, cópias, backups e derivados devem ser avaliados segundo as respetivas obrigações.

<a id="b6-08"></a>

**B6-08** — A ausência de política final aprovada impede eliminação automática, sem constituir aprovação de retenção eterna.

<a id="nc01-b7"></a>

### B7 — Configurações partilhadas e recuperação

Reserva/condição: **Alternativa C.**

Articulação com o texto existente: Inventário e configuração; V04-04/06.

<a id="b7-01"></a>

**B7-01** — Configurações globais, de grupo e partilhadas possuem identidade lógica e ciclo de vida próprios.

<a id="b7-02"></a>

**B7-02** — O arquivo ou fim de vida de um recurso não termina automaticamente uma configuração partilhada.

<a id="b7-03"></a>

**B7-03** — Preservar relações atuais e históricas relevantes entre configurações, recursos e grupos.

<a id="b7-04"></a>

**B7-04** — Conservar versões históricas relevantes para identificar a configuração aplicável em determinado período, conforme a evidência disponível.

<a id="b7-05"></a>

**B7-05** — A disposição final exige avaliação das dependências, retenções, holds e proteção R2.

<a id="b7-06"></a>

**B7-06** — A consulta histórica não implica recuperação operacional ou reativação.

<a id="b7-07"></a>

**B7-07** — A recuperação exige autorização específica, identificação da versão, verificação de integridade e avaliação das dependências.

<a id="b7-08"></a>

**B7-08** — A reativação exige autorização própria e validação de compatibilidade, sem efeitos implícitos sobre outros equipamentos.

<a id="nc01-b8"></a>

### B8 — Discovery

Reserva/condição: **Revisão, responsáveis e referências temporais TBD.**

Articulação com o texto existente: Eventos identificados; V03-02; V04-02.

<a id="b8-01"></a>

**B8-01** — Observações brutas: retenção nominal de 30 dias, sujeita a proteções e dependências.

<a id="b8-02"></a>

**B8-02** — Candidatos pendentes: preservar até decisão válida, com revisão periódica documentada.

<a id="b8-03"></a>

**B8-03** — Candidatos rejeitados: 90 dias após rejeição, preservando evidência ainda necessária.

<a id="b8-04"></a>

**B8-04** — Reconciliações: 180 dias, com evento inicial ainda por definir.

<a id="b8-05"></a>

**B8-05** — Identificadores consolidados: preservar enquanto subsistir necessidade histórica demonstrável.

<a id="b8-06"></a>

**B8-06** — Aprovações e rejeições: política de auditoria aplicável, com proteção adicional quando necessária.

<a id="b8-07"></a>

**B8-07** — Preservar proveniência de observações, decisões, associações e conflitos.

<a id="b8-08"></a>

**B8-08** — Não recriar automaticamente candidatos rejeitados sem nova evidência relevante ou decisão autorizada.

<a id="b8-09"></a>

**B8-09** — Conflitos de identidade abertos exigem preservação da evidência necessária à resolução.

<a id="b8-10"></a>

**B8-10** — Eliminação futura exige classificação, cumprimento da retenção, resolução das dependências e autorização específica.

<a id="nc01-b9"></a>

### B9 — Outbox, exportações e derivados

Reserva/condição: **Alternativa C; prazos de mensagens publicadas TBD.**

Articulação com o texto existente: Auditoria comum; V03-06; V05.

<a id="b9-01"></a>

**B9-01** — A outbox constitui classe própria, distinta da auditoria comum e da evidência R2.

<a id="b9-02"></a>

**B9-02** — A retenção depende do estado efetivo, finalidade e dependências de publicação.

<a id="b9-03"></a>

**B9-03** — Mensagens pendentes não são eliminadas enquanto subsistir obrigação válida de publicação.

<a id="b9-04"></a>

**B9-04** — Mensagens falhadas preservam informação suficiente para diagnóstico e resolução.

<a id="b9-05"></a>

**B9-05** — Mensagens publicadas terão prazo ou condição próprios, ainda por definir.

<a id="b9-06"></a>

**B9-06** — Publicação confirmada não equivale necessariamente a processamento confirmado por todos os consumidores.

<a id="b9-07"></a>

**B9-07** — Exportações, cópias e derivados identificam origem, conteúdo, finalidade, custódia e proteções.

<a id="b9-08"></a>

**B9-08** — A criação de cópias não reduz a proteção do original nem autoriza a sua eliminação.

<a id="b9-09"></a>

**B9-09** — A repetição controlada de publicação não pode contornar as proibições de retry automático R2.

<a id="b9-10"></a>

**B9-10** — Eliminação futura depende de política aprovada, dependências, holds e autorização específica.

<a id="nc01-b10"></a>

### B10 — Evidência R2 e demonstrações independentes

Reserva/condição: **Alternativa C; custódia e retenção TBD.**

Articulação com o texto existente: Proteção R2; V05-01..06.

<a id="b10-01"></a>

**B10-01** — A evidência R2 constitui categoria de proteção própria, transversal às classes de dados.

<a id="b10-02"></a>

**B10-02** — Identificar explicitamente objetos, campos, registos, cópias e derivados protegidos e respetiva justificação.

<a id="b10-03"></a>

**B10-03** — Objetos mistos permanecem integralmente protegidos até demonstração independente de separação segura.

<a id="b10-04"></a>

**B10-04** — Preservar as relações probatórias exigidas pelo contrato R2 aplicável.

<a id="b10-05"></a>

**B10-05** — A custódia exige identidade verificável, integridade, proveniência, rastreabilidade e recuperabilidade.

<a id="b10-06"></a>

**B10-06** — Exportações, backups, réplicas e derivados mantêm as obrigações de proteção aplicáveis.

<a id="b10-07"></a>

**B10-07** — A retenção R2 exige decisão normativa autónoma; os 900 segundos não constituem prazo de conservação.

<a id="b10-08"></a>

**B10-08** — A libertação exige demonstração verificável e decisão humana autorizada e auditável.

<a id="b10-09"></a>

**B10-09** — Libertar proteção R2 não autoriza automaticamente eliminação física.

<a id="b10-10"></a>

**B10-10** — A demonstração independente V05-06 é distinta da demonstração contratual R2 D09.

### Reservas transversais e estados

As reservas são cumulativas. Algoritmos; métodos e autoridades temporais/holds; catálogo final; períodos mínimos e prazos de arquivo; revisão, responsáveis e referências temporais Discovery; prazos de mensagens publicadas; custódia e retenção R2 permanecem TBD quando assim assinalados. B5 conserva alternativa A; B6/B7/B9/B10 conservam alternativa C. B4 não tem reserva adicional específica. A revisão anual existente mantém-se. Não se infere retenção R2 da janela de 900 segundos. V05-06 e R2 D09 mantêm demonstrações independentes e ainda não demonstradas.

V02/CF-02 ABERTAS; H02–H12 PENDENTES/BLOQUEANTES; GAP-001/002 ABERTAS/BLOQUEANTES; AUTH-03/F02/G2/G4 FECHADOS/BLOQUEANTES; RG1–RG7, R2 D09 e V05-06 POR DEMONSTRAR; O3 NÃO APROVADO; DEV-09B NÃO AUTORIZADO; BASELINE NÃO OFICIAL; F0 Working draft.

## Pendências e estados

V02 permanece ABERTA quanto à validação da reconstrução DR-05 e à identificação dos atos/versões. As decisões V03-01..06, V04-01..06 e V05-01..06 são declaradas aprovadas no planeamento, com as oito correções expressamente aprovadas em DR-08B-03. Esta redação reconciliada foi aprovada para incorporação documental pelo pedido humano DR-08C nesta conversa; os bytes finais ficam sujeitos a aprovação humana própria. O texto integral anterior não foi recuperado e a fidelidade literal não é certificada. As 86 redações completas e as reservas atuais encontram-se em #nc01-disposicoes. B5 fixa autorização e verificações de entrada em arquivo; apenas os detalhes não definidos continuam pendentes. Mantêm-se os algoritmos e demais parâmetros TBD expressos por grupo, a duração/disposição final do arquivo e a retenção/condição final de libertação R2. DR-07B-03/V06 concluiu apenas a revisão documental anterior, conforme declaração humana; novos bytes exigem revisão separada. Os valores e requisitos documentados não constituem autorização operacional.

CF-02 ABERTA; V02 ABERTA; decisões V03–V05 declaradas aprovadas no planeamento, com as oito correções expressamente aprovadas em DR-08B-03; redação reconciliada aprovada para incorporação documental DR-08C; bytes finais pendentes de aprovação humana própria; DR-07B-03/V06 CONCLUÍDA apenas quanto à revisão documental anterior; H02–H12 PENDENTES/BLOQUEANTES; GAP-001/002 ABERTAS/BLOQUEANTES; AUTH-03/F02/G2/G4 e demais gates R2 FECHADOS/BLOQUEANTES; RG1–RG7 POR DEMONSTRAR; O3 NÃO APROVADO; DEV-09B NÃO AUTORIZADO; BASELINE NÃO OFICIAL; F0 Working draft. DR-08C: incorporação exclusivamente documental autorizada pelo pedido humano nesta conversa, sem autorização operacional.

Fontes R2 preservadas: [contrato C1–C7](../../architecture/auth-boot-02-r2.md) e [rastreabilidade](../../architecture/auth-boot-02-r2-traceability.md). Plano local, com acesso separado, identificado pelo caminho lógico: `docs/reviews/release_1_0_consolidation_20261028/dr07b_documentary_plan_20261029/PLAN.md`.
