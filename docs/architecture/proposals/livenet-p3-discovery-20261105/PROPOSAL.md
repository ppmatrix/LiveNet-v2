# P3 — casos documentais de reconciliação Discovery

Candidata 0.1 · 05/11/2026 · Europe/Lisbon. **Proposta para revisão humana; exclusivamente documental, sem implementação ou validação operacional.**

## 1. Mandato, fontes e precedência

O pedido humano desta etapa autoriza documentação reversível dos quatro casos abaixo e a atualização necessária do índice de continuidade. ChatGPT faz planeamento/revisão; Codex no VS Code trabalha no repositório. LiveNet exclusivamente interno; progbox DEV; deployments em VMs Proxmox. Nenhum caso descreve dados reais ou uma operação executada.

| Ref. | Fonte consultada | Autoridade e uso nesta proposta |
| --- | --- | --- |
| DAT | [Modelo de dados](../../../specifications/f0/data-model.md), §§2–3, DAT-01B, DAT-02A/B/C, DAT-03A/B, DAT-07A e §12 | Contratos conceptuais aprovados: identidade, proveniência, reconciliação conservadora, aprovação e retenção. As secções complementares resolvem as pendências históricas no seu âmbito; contratos técnicos residuais continuam abertos. |
| D2 | [Adenda DR-07](../../../specifications/f0/dr07-retention-addendum.md), V03-06, V04-04/05/06, V05-01–06, B2, B4–B8 e reservas transversais | Regras de proteção/arquivo/saída que qualificam DAT-07A. Bytes finais aceites por [P4-B4](../../decisions/dr09a-p4-b4-acceptance-20261030.md); cabeçalhos históricos não reabrem a decisão. |
| A | [Aceitação P1/P2 de 05/11/2026](../../decisions/p1-p2-acceptance-20261105.md) | Aceitação documental condicionada como referência derivada; permite preparação documental P3, sem implementar ou fechar reservas. |
| P1/P2 | [P1 Inventory](../livenet-p1-p2-criteria-20261031/P1_INVENTORY.md), §§1–3; [P2 Retenção](../livenet-p1-p2-criteria-20261031/P2_RETENTION.md), §§1–6; [revisão conjunta](../livenet-p1-p2-criteria-20261031/REVIEW.md), «P3 Discovery» | Referências derivadas aceites, subordinadas às fontes aprovadas. P1 ajuda a distinguir consulta de consolidados e estado administrativo; P2 indexa proteções, referências temporais e reservas. Não criam autoridade normativa própria. |
| DEP | [Matriz de dependências](../livenet-dependencies-20261031/DEPENDENCIES.md), entrada P3 e sequência | Classe I para exemplos fiéis; C para critérios técnicos residuais. Nenhuma autorização de execução resulta da classificação. |
| CONT | [Índice de continuidade](../../../project/CONTINUITY.md), estado e limites | Navegação e ponto de retoma, sem autoridade normativa. |

Os hashes P1/P2/REVIEW conferidos nesta etapa coincidem com os identificados em A; D2 coincide com o hash aceite em P4-B4. Isso identifica os ficheiros consultados, sem ampliar a verificação que A declara ter feito no ChatGPT. [Verificação desta entrega](REVIEW.md).

«Exigido» remete a regra das fontes; «resultado descritível» explicita uma consequência documental; «em aberto» não é uma política escolhida. As letras O, C e R são rótulos de exemplo, não campos, entidades físicas, estados novos ou UUID atribuídos.

## 2. Distinções e proteções comuns aos casos

- **Observação (O):** evidência de descoberta, separada do recurso consolidado. Preservar conceptualmente origem/contexto dos identificadores e `source_type`, `source_instance`, `observed_at`, `first_seen_at`, `last_seen_at`, `confidence`, `evidence`, `verification_status` (DAT-02A/B). A confiança é contextual e reavaliável; não se escolhem formato, valor, escala ou prioridade universal.
- **Candidato (C):** proposta de recurso ainda não consolidada; aprovação manual por defeito. A fonte permite aprovação automática apenas com política explícita e evidência suficiente; esta proposta não define nem ativa tal política (DAT-03A/B). Não se inventam UUID ou campos obrigatórios para candidatos/observações.
- **Recurso consolidado (R):** mantém o UUID interno imutável; IP/MAC/hostname/nome não o substituem. Associação, correção e transição devem conservar proveniência e histórico; correção não apaga a associação anterior (DAT-01B, DAT-02A/C, DAT-03A/B).

Em todos os casos aplicam-se cumulativamente as seguintes reservas, conforme os objetos efetivamente envolvidos:

| Objeto/condição | Regra e limite preservados |
| --- | --- |
| Observações e conflitos | Brutos: 30 dias nominais, sujeitos a dependências; conflitos abertos preservam evidência necessária (D2 B8-01/07/09). Não se escolhe referência temporal ainda TBD nem se considera idade suficiente para eliminar. |
| Candidatos | Pendente preservado até decisão válida com revisão periódica documentada; responsáveis e periodicidade TBD. Rejeitado: 90 dias após rejeição, preservando evidência ainda necessária (B8-02/03). Revisão ou prazo não equivale a decisão, levantamento de hold ou limpeza. |
| Resultados, identificadores e decisões | Reconciliações: 180 dias com evento inicial TBD; identificadores consolidados conforme necessidade histórica; aprovações/rejeições pela política de auditoria aplicável, com proteção adicional quando necessária (B8-04/05/06). Não se aplica 365 dias universalmente nem se inventa início por ingestão/decisão. |
| Tempo, holds e dependências | Distinguir evento/receção/persistência; preservar origem temporal; incerteza não fundamenta eliminação. Hold exige objeto, motivo, responsável, evidência e revisão; levantamento justificado/auditável não autoriza eliminação (D2 B2, V03-06; P2-02/05/06). Nenhum hold é criado ou levantado nestes exemplos. |
| R2, continuidade e objetos mistos | Se aplicáveis, V05-01–06 protegem objeto/conteúdo e continuidade; cópia ou hash isolado não demonstra separação segura. D09 e V05-06 são distintos e não são demonstrados por estes casos. Não se presume que toda observação Discovery contenha evidência R2. |
| Saída | Eliminação futura depende de classificação, retenção, dependências e autorização específica (B8-10). Preservação documental de evidência não define schema, TTL, limpeza ou retenção eterna. |

## 3. Catálogo de casos

### P3-01 — Identificadores contraditórios

**Situação inicial e evidências disponíveis.** R-A e R-B são recursos consolidados distintos com UUID próprios. O-1 contém um identificador forte contextualizado anteriormente associado a R-A e outro identificador forte contextualizado associado a R-B; pode ainda haver coincidência de IP ou hostname. Estão disponíveis as observações, contextos e associações anteriores que sustentam a contradição. «Forte» é uma premissa deste exemplo ao abrigo de DAT-02C; não se cria um catálogo ou regra que torne qualquer tipo de identificador sempre forte.

**Observação, candidato e consolidado.** O-1 é evidência contraditória, não um terceiro recurso nem decisão de fusão. R-A e R-B conservam as suas identidades. A ambiguidade não é ausência comprovada de correspondência; a fonte não determina aqui criar novo candidato nem escolher um dos recursos.

**Comportamento exigido e referências.** Preservar e sinalizar a contradição; identificadores fortes contraditórios impedem fusão automática e correspondência ambígua exige revisão autorizada. IP/hostname isolados não resolvem o conflito; nenhuma fonte vence universalmente. Decisões e eventuais correções de associações são auditáveis e conservam histórico (DAT-02A/B; DAT-02C regras 2–4 e 6–7; DAT-03B).

**UUID, proveniência e histórico.** Preservar UUID de R-A/R-B, origem/contexto/histórico dos dois identificadores, proveniência de O-1 e observações anteriores, evidência que fundamenta cada associação e rasto de decisões/correções. Não sobrescrever a evidência anterior pela observação mais recente (DAT-01B, DAT-02A/B/C; D2 B8-05/07).

**Conflitos, proteções e retenção.** O conflito permanece aberto enquanto não houver resolução sustentada; preservar a evidência necessária mesmo que se alcance o prazo nominal de 30 dias. Aplicam-se as proteções comuns da §2, incluindo holds e objetos mistos apenas quando pertinentes (DAT-07A regras 4/7; D2 B8-01/09, V03-06, V05).

**Resultado descritível / em aberto.** É possível descrever «ambiguidade sinalizada para revisão autorizada, sem fusão automática»; não é um novo código de estado. Associação final, eventual correção, critérios de força/contexto/equivalência, limiares e procedimento concreto de resolução permanecem abertos (L1/L2/L5). Não se declara qual UUID representa a realidade observada.

### P3-02 — Observação repetida com candidato já pendente

**Situação inicial e evidências disponíveis.** C-P está pendente com O-1 e respetiva proveniência; não existe recurso consolidado aprovado para esse candidato no cenário. O-2 repete a descoberta, sem informação substantiva diferente na premissa do exemplo. A evidência disponível inclui contexto de origem, identificadores e tempos que permitem comparar O-1/O-2; não se assume que igualdade de IP ou nome prove repetição.

**Observação, candidato e consolidado.** O-2 continua a ser observação; C-P continua candidato pendente, separado de qualquer R. O exemplo pressupõe a relação com C-P para examinar os seus efeitos; não fornece um algoritmo que a determine.

**Comportamento exigido e referências.** A reconciliação deve ser conservadora, auditável e idempotente; repetir observações não pode criar recursos duplicados. Repetição não aprova o candidato; aprovação continua manual por defeito, ambiguidades exigem revisão autorizada (DAT-02C regras 4/6/8; DAT-03A/B). A forma de evitar candidatos redundantes e associar observações ao candidato existente não está concretizada nas fontes e não é decidida aqui.

**UUID, proveniência e histórico.** Não atribuir UUID de recurso por mera repetição nem criar nova identidade consolidada por esse motivo. Preservar proveniência e história necessárias de O-1/O-2 e C-P, sem escolher se a representação física guarda duas linhas, uma referência ou outra forma; `first_seen_at`/`last_seen_at` são conceitos de proveniência, não regras de atualização aqui definidas (DAT-02A/B/C; D2 B8-07).

**Conflitos, proteções e retenção.** Preservar C-P até decisão válida, com revisão documentada. Ausência de conflito novo não elimina dependências existentes; se a comparação revelar contradição, aplicar P3-01. Repetição não reinicia automaticamente prazos de retenção; não se escolhe relógio Discovery nem se elimina evidência necessária (DAT-07A; D2 B2-03, B8-01/02/07/09; §2).

**Resultado descritível / em aberto.** «Candidato continua pendente; repetição não produz consolidação nem recurso duplicado» é suportado. Permanecem abertos equivalência/deduplicação, associação a C-P, representação do histórico, concorrência e revisão periódica (L1/L3/L5). Idempotência de reconciliação não autoriza retry C5, publicação ou execução operacional.

### P3-03 — Candidato rejeitado novamente observado

**Situação inicial e evidências disponíveis.** C-R foi rejeitado por decisão cujo histórico, fundamento e evidência permanecem disponíveis. Chega O-2 no mesmo contexto aparente. A relação com C-R e a relevância de qualquer diferença têm de ser justificadas; coincidência isolada de IP/hostname não as demonstra.

| Variante | Evidência disponível | Comportamento exigido e resultado descritível |
| --- | --- | --- |
| A — repetição sem fundamento novo | O-2 repete material já considerado; não é apresentada nova evidência relevante nem decisão autorizada que fundamente reconsideração. | Evitar recriação repetitiva; não recriar automaticamente candidato rejeitado apenas por nova chegada ou pelo decurso de 90 dias. Preservar rejeição e proveniência; não promover a recurso (DAT-07A regra 3; D2 B8-03/07/08; DAT-03B). |
| B — potencial nova evidência relevante | O-2 traz material adicional, por exemplo contexto de identificador antes ausente que pode afetar o fundamento da rejeição. O exemplo não declara esse material suficiente ou verdadeiro. | Documentar a diferença e o seu vínculo ao fundamento anterior para avaliação. B8-08 admite a distinção entre repetição e nova evidência relevante ou decisão autorizada; não obriga nem autoriza, por si só, recriar/reabrir ou aprovar automaticamente. Se relevância ou identidade forem ambíguas, há revisão autorizada (DAT-02B/C, DAT-03B; D2 B8-08). |

**Observação, candidato e consolidado.** Nas duas variantes O-2 é observação e C-R é candidato historicamente rejeitado, não recurso consolidado. A variante B não decide entre reconsiderar o mesmo candidato ou originar outro percurso documental; não se cria transição nova. Se existir R relacionado, a sua identidade terá de ser avaliada pelas regras DAT, sem fusão implícita.

**UUID, proveniência e histórico.** Preservar decisão e fundamento da rejeição, evidência anterior e nova, contextos/fontes/tempos, associações e eventual decisão posterior, sem apagar a rejeição inicial. Não se atribui novo UUID consolidado para contornar histórico ou se substitui UUID de eventual R por identificador externo (DAT-01B, DAT-02A/B/C, DAT-03B; D2 B8-05/06/07).

**Conflitos, proteções e retenção.** Os 90 dias após rejeição não autorizam apagar evidência ainda necessária nem «esquecem» a rejeição para permitir recriação; o mecanismo que conserva informação suficiente após esse período continua por definir. Nova chegada não reinicia automaticamente retenção, e não se escolhe referência ainda TBD. Se surgir conflito, aplicar B8-09; holds, dependências e proteção R2 pertinente continuam cumulativos (§2; D2 B2, B8-01/03/07–10).

**Resultado descritível / em aberto.** Pode distinguir-se repetição sem fundamento novo de material novo apresentado para avaliar relevância; não se pode declarar aceite o segundo só por ser diferente. Definição verificável de relevância, critérios de correlação com rejeição anterior, percurso de reconsideração, responsável/competência concreta e preservação suficiente para evitar recriação após retenção nominal permanecem abertos (L1/L4/L5). A aprovação de eventual candidato mantém DAT-03B; não se seleciona política automática.

### P3-04 — Observação relacionada com recurso arquivado

**Situação inicial e evidências disponíveis.** R-H está `archived` com UUID, referências de identificadores, relações, decisão de arquivo e histórico disponíveis. O-N apresenta elementos potencialmente relacionados com R-H. A relação pode ser sustentada no contexto do exemplo ou permanecer ambígua; mera coincidência de hostname/IP não comprova identidade.

**Observação, candidato e consolidado.** O-N é observação; R-H já é recurso consolidado arquivado. Não se trata o arquivo como ausência de R-H nem como candidato novo. Se a identidade for ambígua, a fonte exige revisão; este caso não determina criar candidato, fundir ou associar definitivamente. Se for sustentada a identidade com R-H, não criar recurso duplicado apenas pela redescoberta (DAT-02C, DAT-03A).

**Comportamento exigido e referências.** Novas descobertas não reativam automaticamente arquivados. Consulta, recuperação e reativação são atos distintos; `archived -> active` requer recuperação manual autorizada, RBAC e auditoria, conservando UUID. D2 exige que os âmbitos de recuperação e reativação sejam expressamente abrangidos, sem presumir um pelo outro. Nenhum é executado aqui (DAT-03A/B; D2 V04-06, B5-08, B7-06/07/08; P1-10/17 e P2-10/11 como índices derivados).

**UUID, proveniência e histórico.** Preservar UUID original de R-H, decisão de arquivo, último estado conhecido, relações/contexto histórico, identificadores contextualizados e proveniência de O-N. Sinalizar eventual contradição sem reescrever o passado; identidade nova não se presume de uma mudança de IP/nome (DAT-01B, DAT-02A/B/C, DAT-03A/B; D2 B4, B5-03/04, B8-05/07).

**Conflitos, proteções e retenção.** Arquivo não é eliminação nem levantamento de hold; inventário/configuração seguem vida do recurso + arquivo, cuja duração/disposição permanece TBD. Relações com configurações partilhadas não desaparecem pelo arquivo. Aplicam-se B8 aos objetos Discovery, V03-06 aos holds/dependências e V05 quando pertinente; não se usa prazo de observação para eliminar R-H ou histórico (D2 V04-04/05, B5-05/07, B6, B7, B8-09/10; §2).

**Resultado descritível / em aberto.** «Observação relacionada, ou relação ambígua para revisão; R-H permanece arquivado sem reativação automática» é descritível. Associação definitiva, tratamento técnico de nova evidência em contexto arquivado e eventual procedimento de recuperação/reativação continuam sujeitos a critérios/autorizações próprios (L1/L5/L6). O caso não infere estado operacional nem altera o último estado por mera observação.

## 4. Lacunas e decisões preservadas

| ID editorial | Questão não determinada pelas fontes consultadas | Limite nesta proposta |
| --- | --- | --- |
| L1 | Critérios concretos de correspondência, equivalência/colisão, força contextual e limiares de confiança (DAT-02C; §12). | Não escolher associação/fusão, prioridade universal ou limiar. Ambiguidade exige revisão autorizada. |
| L2 | Procedimento concreto para resolver/corrigir contradições e repartir evidência entre identidades. | Preservar histórico e revisão; não adotar algoritmo ou política de fusão. |
| L3 | Deduplicação de observações/candidatos, correlação com pendente e representação de repetições/concorrência (DAT §3/§12). | Repetição não duplica recursos; nenhuma chave, constraint, esquema ou política de execução é definida. |
| L4 | Critérios de nova evidência relevante e percurso de reconsideração de rejeitado; informação suficiente contra recriação repetitiva após o prazo nominal. | Não fixar reabertura/recriação, novo estado, marcador permanente ou retenção adicional por conveniência. |
| L5 | Revisão periódica/responsáveis Discovery; métodos/autoridades temporais e de holds; referências temporais ainda TBD, incluindo início dos 180 dias (D2 B2/B8/reservas). | Não escolher responsável/role, periodicidade, prazo de hold ou início de contagem. A incerteza não autoriza disposição destrutiva. |
| L6 | Procedimentos técnicos e âmbito concreto de autorização para tratar nova observação de arquivado, recuperar e reativar; duração/disposição do arquivo (D2 B6/B7). | Preservar regras já aprovadas; não inferir efeitos automáticos, autorizações ou prazo. |

L1–L6 são localizadores desta proposta, não novos gates, lacunas normativas numeradas do projeto ou decisões tomadas. As reservas comuns R2/continuidade mantêm-se nas fontes; não se procura resolvê-las com estes casos.

## 5. Critérios de revisão humana e limites

A revisão pode aceitar documentalmente os quatro casos verificando a rastreabilidade das exigências, a separação observação/candidato/consolidado, a preservação do UUID/proveniência/histórico e o registo explícito dos resultados não determinados. Na variante P3-03B, verificar especialmente que evidência diferente não foi equiparada a relevância comprovada ou aprovação.

Nenhuma lacuna precisa de ser preenchida por suposição para rever esta candidata. A aceitação documental futura não autoriza implementação: critérios técnicos materiais e eventual âmbito de código requerem decisão própria. Não se implementam adaptadores, persistência, schema, testes operacionais, TTL, limpeza ou política de execução; não se alteram fontes/contratos aprovados, gates ou bloqueadores. Idempotência Discovery e eventual retry Outbox não autorizam retry C5. I-04/clone gravável, GAP-001/002, AUTH-03/F02/G2/G4 e restantes estados do índice ficam preservados. Sem commits, pushes ou merges.

**Recomendação:** revisão humana no ChatGPT desta candidata 0.1 e das lacunas L1–L6, sem reabrir P1/P2, DAT/D2 ou C4/B-L e sem exigir agora escolhas de implementação.
