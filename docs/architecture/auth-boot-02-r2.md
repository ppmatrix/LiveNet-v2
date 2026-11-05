# AUTH-BOOT-02-R2 — Baseline candidata de admissão lógica

**Estado: BASELINE CANDIDATA APROVADA DOCUMENTALMENTE quanto a C1–C7, riscos e separação de versão; consolidação documental para revisão dos bytes.**

Identificador: AUTH-BOOT-02-R2. Revisão documental: R2-CONSOLIDATION-1.
Data desta consolidação: 2026-10-27. Esta data não é atribuída à aprovação original.

## 1. Autoridade, proveniência e alcance

Fonte: conversa [Planeamento das lacunas](chatgpt-conversation://6adfbb17-6350-83ed-9daa-650bf8ad109a), texto humano integral R1-CONTRACT-REV-01, mensagem `408b84ef-5a83-4255-9bca-3bb79ae7ae58`, e aprovação humana `9daf5fec-5456-4d05-b296-483b9a1b3260`:

> Aprovo documentalmente C1–C7 como baseline candidata AUTH-BOOT-02-R2, incluindo expressamente os riscos identificados e a separação de versão. Não autorizo implementação, alteração operacional, abertura de gates ou encerramento de GAP-001/002.

O pedido atual autoriza consolidar essa baseline no repositório, preservando R1 e o histórico. O texto integral C1–C7 e as tabelas/riscos abaixo foram recuperados da mensagem humana, não reconstruídos a partir de resumos. As respostas anteriores do assistente só estavam disponíveis como referências de conteúdo; não lhes é atribuído conteúdo contratual. A aprovação é documental e não é uma aprovação assinada executável nem aprovação antecipada dos bytes desta consolidação.

Esta revisão altera expressamente a fronteira de segurança de R1-D04/D05/D08: a elegibilidade condiciona a admissão lógica em `A`, deixando de garantir elegibilidade no primeiro efeito físico PostgreSQL. Não constitui interpretação retroativa de R1. O [consolidado R1](auth-boot-02-r1.md), a [proposta histórica](proposals/auth-boot-02-r1.NOT-APPROVED.md), o [registo R1 de lacunas](auth-boot-02-r1-gaps.md) e a [rastreabilidade R1](auth-boot-02-r1-traceability.md) mantêm os seus textos e estados históricos.

AUTH-03, F02, G2 e G4 permanecem fechados. DEV-09B continua não autorizada. R1-GAP-001/002 permanecem ABERTAS e bloqueantes; as restantes lacunas não são encerradas. Não há autorização de implementação, laboratório, infraestrutura ou operação nesta baseline.

## 2. Cláusulas C1–C7

O texto desta secção reproduz as cláusulas fornecidas na fonte humana, conservando o caráter de recomendação do perfil concreto em C7.

### C1 — Admissão lógica e durabilidade

A admissão é uma decisão autoritativa exclusiva para uma aprovação e tentativa concretas.

O ponto lógico de admissão, `A`, corresponde à avaliação decisória final de elegibilidade, dentro de uma transação que serialize essa decisão com as alterações relevantes de revogação, epochs e política.

A decisão só constitui uma admissão se a transação confirmar duravelmente, registando conjuntamente consumo, vínculos, ordem autoritativa e evidência essencial local. Antes dessa confirmação, não pode ser disponibilizada autorização executável.

O estado autoritativo permanece independente das bases LiveNet e dos executores, sob administração segregada. Não existe atomicidade presumida entre esse estado e PostgreSQL alvo.

### C2 — Expiração

Mantêm-se:
```
issued_at <= not_before < expires_at
expires_at - issued_at <= 900 segundos
Elegibilidade em A apenas quando L >= not_before e U < expires_at
```

`[L,U]` é o intervalo UTC confiável associado à avaliação em `A`. Tempo não confiável ou continuidade temporal desconhecida impedem admissão.

**O prazo limita a avaliação lógica em `A`, não o commit posterior dessa decisão, a entrega da resposta, o primeiro efeito físico ou o commit da operação.** Não há grace period acrescentado à avaliação; há uma mudança expressa do evento ao qual o prazo se aplica.

### C3 — Revogação

Admissão e revogação devem integrar uma ordem autoritativa única, incluindo revogações de aprovação, chave, autoridade e política. Timestamps isolados não estabelecem essa ordem.

- Revogação ordenada antes de `A`: admissão recusada.
- Admissão ordenada antes da revogação: a tentativa admitida não perde retroativamente a sua admissão por essa revogação.
- Pedido de revogação ainda não confirmado: deve aparecer como pendente, nunca como eficaz.
- Ordem ou confirmação desconhecidas: bloquear novas admissões.

Revogação posterior não promete interromper execução, cancelar um despacho já entregue ou desfazer efeitos. Medidas de contenção continuam possíveis, sem reutilizar ou libertar a aprovação.

### C4 — Exclusividade e vinculação

Cada aprovação admite, no máximo, uma tentativa. A tentativa admitida vincula imutavelmente pedido, participantes, finalidade, operação, gate, ambiente, plano, digests, destino/geração, executor/encarnação e sessão/transação protegidas.

A admissão não é transferível nem reutilizável. Expiração, timeout, rollback, savepoint, crash ou reinício não libertam a aprovação.

O alvo deve impedir segunda iniciação e caminhos de SQL que contornem essa fronteira. Um recibo, marcador ou objeto de autorização, isoladamente, não demonstra essa garantia. Não se promete execução exatamente uma vez.

### C5 — Respostas perdidas, partições e incerteza

Antes de existir confirmação durável e autenticada da admissão, indisponibilidade ou resposta perdida implica `UNKNOWN/BLOCKED`, sem despacho automático.

Consultas de estado podem esclarecer o registo existente; não emitem nova permissão, não autorizam retoma e não repetem a operação.

Depois de confirmada, apenas a tentativa original, continuamente vinculada à mesma execução, pode prosseguir. Uma partição posterior não revoga retroativamente essa admissão. Reconexão, reinício, perda de contexto ou resultado incerto não autorizam retoma automática.

Nova tentativa exige reconciliação, invalidação demonstrada de capacidades antigas, novo pedido e nova aprovação. Mantém-se a ausência de retry automático.

### C6 — Evidência e recuperação

A confirmação independente exigida por D09 continua obrigatória antes de disponibilizar o percurso executável. Não se presume atomicidade entre registo autoritativo, cópia independente e alvo; confirmação ausente ou ambígua bloqueia a progressão.

Recuperação deve preservar admissões, consumos, revogações, ordem, epochs e vínculos. Snapshot, clone ou incremento de epoch não demonstram continuidade. Continuidade desconhecida implica quarentena e reentrada humana, sem reativação automática de admissões antigas.

### C7 — Separação de versões

Esta semântica não pode ser aceite silenciosamente como protocolo R1 versão 1.

Recomenda-se um perfil **R2**, com `protocol_version="2"` e domínio de assinatura próprio, preservando os 25 nomes de campos, JCS/UTF-8 e Ed25519 puro. A codificação concreta e os schemas da evidência de admissão exigem aprovação específica; os parsers e executores atuais permanecem inalterados.

## 3. Matriz de alterações propostas

| Área | Alteração concreta |
| --- | --- |
| R1-D04/D05/D08 | Introduzir admissão exclusiva; ordenar revogação com admissão; substituir a exigência temporal no primeiro efeito |
| D02 | Separar criptograficamente a nova semântica; sem fallback entre versões |
| D06/D09/D10 | Preservar bloqueio de incerteza, confirmação independente e continuidade; distinguir admissão de início observado e resultado |
| AUTH-03/security | Rever a integração do controlo autoritativo separado. Preservar transação única da operação protegida, mesma ligação, rollback e reconciliação |
| F02/G4 | Rever futuramente vínculos e evidências verificáveis; referências atuais continuam sem conferir autoridade |
| G2 | Alterar apenas se houver novos objetos ou requisitos de catálogo; readiness não passa a autorizar execução |
| GAP-001 | Mantém a obrigação de demonstrar exclusividade no alvo e continuidade; não é resolvida pela admissão única |
| GAP-002 | Propor critério de ordenação com admissão, preservando o requisito original no histórico; permanece aberta |
| Dependências | Continuam necessárias 003–018 conforme aplicável, sobretudo continuidade, evidência, integração, schemas, persistência e confiança |

Esta matriz descreve consequências documentais e trabalho futuro. Não modifica contratos operacionais, schemas, parsers, executores, manifestos ou gates. O domínio de assinatura concreto R2, a codificação e os schemas de evidência permanecem por especificar e aprovar. Não se inventam bytes de domínio, eventos ou novos campos.

## 4. Critérios mínimos de demonstração

| Critério | Evidência mínima exigida |
| --- | --- |
| Admissão única e durável | Concorrência, confirmação perdida e recuperação sem duplicação ou libertação |
| Ordenação com revogação | Ordem atribuível e persistente; revogação anterior impede admissão; incerteza bloqueia |
| Exclusividade no alvo | Sem segunda iniciação por replay, savepoint, rollback, sessão concorrente ou caminho direto |
| Continuidade | Restauro antigo e clone não reativam poderes; instâncias anteriores efetivamente invalidadas |
| Resultados incertos | Sem retry/retoma automática; reconciliação independente e decisão humana |
| Evidência independente | Confirmação D09 anterior ao percurso executável, sem confundir recibo com efeito ou commit |

Os laboratórios existentes constituem evidência parcial, não satisfação destes critérios. Não foram repetidos ou ampliados nesta consolidação. Nenhum critério passa a demonstrado pela aprovação documental.

## 5. Riscos expressamente abrangidos pela aprovação documental

- Efeito físico depois da expiração ou revogação, incluindo durante partição posterior à admissão.
- Ausência de limite temporal garantido entre decisão lógica, confirmação durável e efeito.
- Possibilidade de aprovação consumida sem qualquer execução.
- Incapacidade de garantir cancelamento de uma tentativa admitida.
- Dependência de continuidade e invalidação de instâncias; falhas históricas ou clones continuam perigosos.

A aprovação humana citada em §1 inclui expressamente os riscos identificados e a separação de versão. Isto abrange a mudança de fronteira para `A`, a ausência de invalidação retroativa por revogação posterior e a possibilidade de confirmação durável e efeito posteriores ao prazo. Não confere autorização operacional.

## 6. Lacunas e limites da consolidação

R1-GAP-001 mantém o critério original de exclusividade durável da iniciação. R1-GAP-002 conserva no registo R1 a exigência histórica de ordenação com o primeiro efeito PostgreSQL; R2 documenta a revisão expressa para admissão lógica, com critérios ainda por demonstrar. Não se declara satisfeito o requisito histórico nem se fecha a lacuna por mudança de semântica. O acompanhamento R2 e as dependências constam da [rastreabilidade R2](auth-boot-02-r2-traceability.md).

Os 20 IDs R1 permanecem no registo existente. As lacunas históricas G4/L02 não são fundidas, renumeradas ou encerradas. AUTH-BOOT-02 original e contratos históricos não recuperados mantêm `SOURCE_NOT_LOCATED`; não se presume equivalência com R1, R2, I2, G4-WF1 ou F03/F04.

A fonte limita a primeira classe de implementação ao UPDATE fixo de laboratório. Esta indicação delimita eventual trabalho posterior, que continua sem autorização; Alembic, DDL e operações administrativas não ficam automaticamente abrangidos.

Não foram alterados código executável, infraestrutura, manifestos ou evidências congeladas. Não há abertura de gates, encerramento de lacunas ou autorização de DEV-09B. Implementação, ensaios e ativação exigem decisões próprias posteriores.
