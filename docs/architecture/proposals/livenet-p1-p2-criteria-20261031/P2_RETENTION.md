# P2 — critérios de retenção, proteção e saída

Candidata 0.1 · 31/10/2026 · Europe/Lisbon. **Derivação documental para revisão; sem alteração normativa ou execução.**

## 1. Fontes e precedência

**D2:** [DR-07 retention addendum](../../../specifications/f0/dr07-retention-addendum.md), V03/V04/V05 e B1–B10; **A:** [P4-B4](../../decisions/dr09a-p4-b4-acceptance-20261030.md), aprovação dos bytes D1/D2/D3 em 30/10/2026; **DAT:** [data-model.md](../../../specifications/f0/data-model.md), DAT-02A/B/C, DAT-03A/B, DAT-07A/08A. D1 é consultado apenas para proveniência/reservas pertinentes, sem reconstruir atos ausentes.

O hash D2 coincide com o aceite por A: `a996d78fff71002db47f2756836669fd3f096bff3074bae10c98c31afdaab818`. Cabeçalhos históricos de pendência não reabrem P4-B4. DAT-07A continua aprovado; D2 B8 qualifica Discovery e mantém as reservas expressas. Não se atribui 365 dias a todas as observações/eventos nem se convertem meses de calendário em dias fixos. D2 V04-03 sucede apenas à parcela de auditoria comum identificada, preservando o texto DAT histórico.

**Aprovado** nas tabelas significa regra da fonte já aceite; **TBD** significa parâmetro/decisão ainda reservado, não ausência da obrigação; **critério derivado** é verificação documental dessa regra, sem novo mecanismo, schema, prazo ou autoridade. Nenhum cenário foi executado. Esta entrega não cria algoritmo de limpeza, política de hold ou máquina de estados de dados.

## 2. Classes Discovery e prazos preservados

| Objeto | Regra já aprovada | Referência/condição não preenchida por este documento | Critério de proteção/saída |
| --- | --- | --- | --- |
| Observações brutas Discovery | 30 dias nominais, sujeitos a proteções/dependências. | D2 B8-01 e reserva B8: referências temporais Discovery ainda TBD quando não explicitadas; não importar automaticamente evento de «métrica bruta». | Decurso nominal não permite apagar evidência necessária a conflito, histórico, hold ou R2. |
| Candidato pendente | Até decisão válida, com revisão periódica documentada. | B8-02; periodicidade e responsáveis de revisão TBD. | Data de revisão não decide candidato nem autoriza eliminação; preservar evidência enquanto pendente. |
| Candidato rejeitado | 90 dias após rejeição, preservando evidência necessária. | B8-03; demais proteções e rastreabilidade da rejeição mantidas. | 90 dias satisfaz apenas parcela temporal; não recriar automaticamente sem nova evidência relevante ou decisão autorizada (B8-08). |
| Resultado de reconciliação | 180 dias. | B8-04: evento inicial ainda por definir. Não escolher observação, execução, decisão ou persistência como início. | Sem referência aprovada e confiável, não demonstrar elegibilidade temporal para eliminação. |
| Identificador consolidado | Enquanto subsistir necessidade histórica demonstrável. | B8-05/DAT-07A, sem prazo universal novo. | Limpeza de observações/candidatos não elimina identidade consolidada, proveniência ou relações históricas necessárias. |
| Aprovações/rejeições | Política de auditoria aplicável, com proteção adicional quando necessária. | B8-06; auditoria comum tem 365 dias online/global no âmbito de V04-03; não aplicar esse prazo a evidência R2/continuidade. | Classificar o objeto antes de usar prazo; decisão histórica e observação são classes relacionadas, não intercambiáveis. |

Retenções comuns de outras classes continuam exatamente como D2 V04-02 e respetivas referências V03: checks/métricas brutas/logs 30 dias; agregados 5 minutos 180 dias, horários 12 meses de calendário, diários 3 anos de calendário; classes de eventos expressamente identificadas 365 dias; inventário/configuração vida do recurso + arquivo TBD. Este resumo não amplia classes nem substitui D2, e não atribui a Discovery as regras temporais de métricas por analogia.

## 3. Matriz de condições cumulativas de proteção e saída

«Saída» precisa sempre de objeto explícito: satisfazer condição temporal, levantar hold, aprovar arquivo, demonstrar separação, libertar proteção R2, recuperar/reativar e eliminar são atos diferentes. Nenhum implica automaticamente os seguintes.

| ID / condição | Requisito aprovado e fonte | Verificação documental exigida | Proteção/saída e reservas |
| --- | --- | --- | --- |
| P2-01 — classificação | D2 B3-02/03/05/07, B8/B9/B10. | Identificar classe, finalidade, original/cópia/derivado e relações probatórias. | Classe desconhecida não recebe eliminação automática; não herdar 365 dias por ser «evento». Catálogo final B3 TBD. |
| P2-02 — referência temporal | V03-01/02/03; B2-01–06. | Conservar evento próprio, UTC, proveniência e distinção evento/receção/persistência; não reiniciar contagem com chegada/correção tardia. | Timestamp/relógio incertos não provam prazo terminado. Métodos/autoridades B2 e referências B8 TBD quando assinalados. |
| P2-03 — elegibilidade temporal | V03-03. | Quando classe/referência estiverem fixadas, aplicar unidade original e `nowUTC >= limite`; igualdade só satisfaz tempo. | Meses/anos de calendário com clamp aprovado; não converter para 365/1095 dias nem inventar início Discovery. Sem autorização de limpeza. |
| P2-04 — agregação/correções | V03-04/05, B1. | Onde aplicável, preservar gaps, proveniência, brutos necessários e correções rastreáveis/idempotentes; COMPLETE exige suporte verificável. | PENDING/PARTIAL não desaparecem por timeout/tolerância. Algoritmos completos/limiares específicos TBD; não aplicar agregação métrica a Discovery por analogia. |
| P2-05 — dependências | V03-06; B3-07; B6-07; B9. | Identificar dependências de preservação, continuidade, arquivo, cópias, conflitos, publicação e R2 aplicáveis. | Prazo nominal atingido não supera dependência ainda necessária; não se define novo algoritmo universal de precedência. |
| P2-06 — hold/exceção | V03-06; B2-07/08. | Hold identifica objeto, motivo, responsável, evidência e revisão; manutenção/resolução da causa rastreável. | Revisão vencida não levanta hold. Levantamento exige decisão justificada/auditável, não autoriza eliminação. Métodos/autoridades/procedimento/prazos de hold não escolhidos. |
| P2-07 — conflito Discovery | DAT-02B/C, DAT-07A; B8-07/09. | Preservar observações contraditórias, proveniência e evidência necessária à resolução. | Conflito aberto impede descartar a evidência necessária só por prazo vencido; não escolher limiar/fusão para o fechar. |
| P2-08 — candidato pendente/rejeitado | DAT-03B/07A; B8-02/03/08. | Distinguir decisão válida, rejeição e revisão; conservar histórico e evitar recriação repetitiva sem fundamento permitido. | Pendente não expira por timeout inventado; rejeição não elimina automaticamente observações protegidas. Política automática não é introduzida. |
| P2-09 — identidade/histórico | DAT-01B/02A/C/03A; B4/B8-05/07. | UUID, proveniência, decisões, associações/correções e contexto histórico relevantes mantidos. | Repetição não cria identidade nova por si; limpeza não elimina consolidado; arquivo não perde UUID; ausência de observações não determina estado automaticamente. |
| P2-10 — inventário/estado/arquivo | V04-04/05; B4/B5/B6. | Estado atual, inventário e histórico distintos. Entrada em arquivo requer autorização humana explícita/auditável, identidade/relações, último estado/histórico, dependências/holds/R2. | Desativar, perder contacto ou tempo decorrido não arquiva automaticamente; revisão anual não é expurgo. Duração/período mínimo/disposição final do arquivo TBD. |
| P2-11 — partilhados/consulta/recuperação | V04-06; B7. | Preservar identidade/ciclo próprios de configuração global/grupo/partilhada, relações e versões históricas relevantes. Distinguir consulta, recuperação e reativação. | Arquivo de um recurso não termina configuração partilhada; recuperação exige versão/integridade/dependências e autorização; reativação tem autorização própria. Consulta não reativa. |
| P2-12 — objeto misto | V05-01/02; B10-02/03. | Identificar conteúdo R2/continuidade e o objeto que o contém; manter original e demonstrar conteúdo, identidade, ordem, vínculos, proveniência e recuperabilidade se for proposta separação. | Objeto inteiro protegido até demonstração independente de separação segura. Nem a demonstração permite destruir/substituir original ou libertar automaticamente proteção. |
| P2-13 — custódia/histórico R2 | V05-03/04; B10-04/05/06. | Cadeia auditável de conteúdo recuperável, proveniência, custódia, ordem, vínculos e continuidade; emissão/uso/consumo/revogação/expiração preservados. | Hash/recibo isolado não recupera conteúdo. Rollback, expiração e restore não libertam evidência/capacidade; custódia técnica concreta ainda TBD. |
| P2-14 — prazo/libertação R2 | V05-05; B10-07/08/09. | Reconhecer prazo/condição final ainda TBD; eventual libertação precisa de demonstração verificável e decisão humana autorizada/auditável. | 900 segundos, retenção comum, logs/backup não definem retenção R2; falta de prazo não aprova eternidade nem eliminação; libertação não autoriza destruição física. |
| P2-15 — V05-06/D09 | V05-06; B10-10. | V05-06 demonstra preservação/separação/continuidade no âmbito indicado; resultado COMPROVADO/FALHA/INDETERMINADO fundamentado. D09 confirma preservação pertinente antes do percurso executável no seu âmbito contratual. | Distintos e cumulativos: nenhum substitui/dispensa o outro. COMPROVADO não é confirmação D09 ou autorização de destruição; FALHA/INDETERMINADO mantêm bloqueio. Não se declara nenhum demonstrado. |
| P2-16 — cópias/exportações/derivados | B6-07; B9-07/08; B10-06. | Relação com origem, conteúdo, finalidade, custódia e proteções identificáveis em cada cópia/backup/derivado relevante. | Criar cópia não reduz proteção do original nem autoriza eliminá-lo. Preservar cópia não prova que capacidade antiga foi invalidada; I-04 intacta. |
| P2-17 — Outbox | DAT-08A; B9-01–06/09/10. | Classe própria; pendentes conservadas enquanto publicação devida, falhadas com diagnóstico suficiente; publicação não prova processamento de todos os consumidores. | Prazo/condição dos publicados TBD. Retry de publicação não contorna C5 ou repete operação protegida. Nenhum worker/política executado. |
| P2-18 — eliminação/disposição | V03-06/V04-05/V05-02; B6-06/08, B8-10, B9-10, B10-09. | Avaliar cumulativamente classificação, referência/prazo aplicáveis, dependências, holds/proteções e ato específico competente de disposição. | Nenhuma combinação desta grelha é licença de limpeza; autorização física própria continua ausente e gates/limites aplicáveis preservados. Não se encurta proteção por exceção. |

## 4. TBD e decisões materiais que continuam por tomar

| Tema | Reserva da fonte | Consequência para os critérios |
| --- | --- | --- |
| Cobertura/completude | B1: algoritmos específicos TBD. | Preservar obrigação, gaps e estado não demonstrado; sem percentual/tolerância nova ou motor implementado. |
| Tempo e holds | B2/V03-06: métodos/autoridades/procedimento concretos não fixados. | Não nomear nova autoridade/role, mecanismo de correção ou duração de hold; materialidade avaliada antes de adoção. |
| Catálogo de eventos | B3: catálogo final TBD. | Classificar apenas no âmbito conhecido; não generalizar prazo comum. |
| Arquivo | B5 tem alternativa A já fixada; detalhes não definidos permanecem; B6 alternativa C, períodos/duração/disposição TBD. | Não reabrir a escolha A/C. Qualquer parâmetro normativo residual exige decisão própria, não valor por conveniência. |
| Discovery | B8: revisão, responsáveis e referências temporais TBD; reconciliação sem evento inicial fixado. | P3 pode descrever casos preservando estes desconhecidos; não converter `observed_at` ou data de decisão em relógio universal de retenção. |
| Outbox | B9 alternativa C; prazo/condição de publicados TBD. | Não reaproveitar prazo de auditoria; pendências e proteções continuam aplicáveis. |
| R2 | B10 alternativa C; custódia/retenção e condição final TBD. | Sem nova raiz/recuperação/formato ou prazo; D09/V05-06/C4 não reabertos nem considerados demonstrados. |

A aceitação dos critérios P2 não resolve estas matérias nem altera V02/CF-02. As reservas são cumulativas; não se inventa uma hierarquia normativa nova entre elas.

## 5. Casos documentais de aceitação

- Observação bruta com 30 dias e conflito de identidade aberto: preservar evidência necessária; idade não autoriza limpeza (B8-01/09).
- Rejeição com 90 dias mas hold ainda ativo: não eliminar por decurso temporal; revisão do hold não vale como levantamento (B2/B8).
- Resultado de reconciliação com «180 dias desde ingestão»: não aceitar essa referência como requisito aprovado, pois B8-04 mantém início TBD.
- Objeto comum expirado que contém evidência R2: objeto misto permanece protegido; hash/cópia não autorizam separação, libertação ou destruição (V05/B10).
- V05-06 COMPROVADO e confirmação D09 disponível: continuam atos distintos e nenhuma eliminação é autorizada só por esses factos (V05-06/B10-08/09/10).
- Recurso desativado ou arquivado consultado: identidade/contexto histórico preservados; leitura não é reativação, ausência de contacto não é arquivo automático (V04/B4/B5/B7).

São exemplos de leitura normativa, não avaliações reais de dados, demonstrações V05-06 ou ensaios autorizados. Não se aplicam prazos a objetos de classe incerta para concluir saída.

## 6. Prontidão documental para P3

**P3 Discovery pode começar a ser preparado documentalmente com esta base de proteção, sem esperar fechar os TBD de P2 ou resolver C4**, porque exemplos podem conservar «referência ainda não definida», revisão autorizada e proteções em vez de executar uma decisão. P2 é grelha candidata derivada; a autoridade continua a ser DAT e D2 aprovados, não uma suposta aprovação de P2.

Escopo possível: casos de identificador contraditório, candidato repetido/rejeitado e recurso arquivado, distinguindo observação/candidato/consolidado, UUID/proveniência/histórico e proteção. Nenhum limiar, regra concreta de fusão, hierarquia de confiança, política automática, schema ou retenção nova é escolhido. Esta entrega apenas indica prontidão; **não executa P3 nem inicia implementação**.

Aceitação de P2: rastreabilidade de cada linha; prazos/unidades/condições preservados; TBD explícitos; proteção/hold/arquivo/libertação/eliminação separados; D09/V05-06 distintos; nenhuma política ou operação nova. [Revisão conjunta](REVIEW.md).
