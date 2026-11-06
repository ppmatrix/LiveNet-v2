# LiveNet v2 — aprovação da Fronteira C4 e sequência por dependências

Relatório documental candidato 0.1 · 31/10/2026 · Europe/Lisbon.

## Resultado executivo

A aprovação humana da Fronteira C4 v0.1, declarada em **30/10/2026**, foi registada em **31/10/2026** em [ato próprio](../../decisions/bl-c4-effect-boundary-v01-approval-20261031.md), com os hashes calculados de PROPOSAL.md e MATRIX.md. Ambos permanecem intactos. Não seleciona F-A–F-E/CAND-1/2/3 nem resolve a fronteira ou I-04.

Há preparação documental que pode avançar independentemente da resolução C4. A [matriz de dependências](DEPENDENCIES.md) separa essa preparação de contratos residuais condicionados e de execução/ativação bloqueadas. «Não depende de C4» não equivale a «pode implementar»: persistência, readiness positiva, migrações e ativação mantêm os gates próprios.

Recomendação para decisão humana de sequência: **P1 — critérios de consulta inventory e P2 — critérios documentais de proteção/retenção; depois P3 — casos de reconciliação Discovery**, usando P2. São três escopos pequenos propostos, com riscos/aceitação na matriz. Não foram iniciadas essas entregas nem qualquer implementação; a presente execução limita-se a classificá-las e recomendá-las.

## Fontes mínimas e precedência

| Fonte consultada | Uso/limite |
| --- | --- |
| Pedido humano atual | Declara aprovação de dois objetos em 30/10/2026 e autoriza registo/classificação documental. Sem aprovação de arquitetura/implementação. |
| [Continuidade](../../../project/CONTINUITY.md) e [cópia anterior](CONTINUITY.before.md) | Aprovações/gates atuais, retomada sem recuperar inventários. O arquivo literal conserva links com base no local original. |
| [Roadmap DEV-03B, 25/10/2026](../../../roadmap/platform-roadmap.md) | Entregas 0–8 e dependências propostas; não é plano novo aprovado nem estado operacional de 31/10. |
| [Implementation-status](../../../specifications/f0/implementation-status.md), atualizações DEV-05B/06/07 e consolidado até §bloqueios | Código/evidência/ativação distintos. Resultados de testes e ausência funcional ali descritos são históricos, não revalidados agora. |
| [Modelo de dados](../../../specifications/f0/data-model.md), §§1–10, DAT-02A–03B, DAT-07A/08A, §12 e adenda DAT-05A | Contratos conceptuais aprovados versus critérios físicos/técnicos residuais. DAT conceptual não volta a ser tratado como decisão por aprovar. |
| [D2](../../../specifications/f0/dr07-retention-addendum.md), V05 e reservas já conhecidas; [P4-B4](../../decisions/dr09a-p4-b4-acceptance-20261030.md) | Aceitação posterior de retenção prevalece no seu âmbito. Não reabrir D1/D2/D3 por menção histórica do roadmap; TBD e demonstrações continuam. |
| [Rastreabilidade R2](../../auth-boot-02-r2-traceability.md), §§2–3 | Exclusividade/continuidade e gates existentes, sem estender o UPDATE fixo a toda operação do produto ou a Alembic. |
| Fronteira C4 [proposta](../bl-c4-effect-boundary-20261030/PROPOSAL.md), [matriz](../bl-c4-effect-boundary-20261030/MATRIX.md), revisão da entrega | Objetos aprovados e limites reutilizados nesta mesma conversa; hashes medidos antes da escrita. Não se refaz o estudo. |

Conflitos temporais são tratados por âmbito: DAT-05A tem adenda posterior explícita; retenção tem P4-B4/D2; DEV-06/07 validaram transporte/UI em âmbito histórico sem desbloquear persistência/readiness. Não se volta a propor «resolver topologia», retenção conceptual ou empacotamento já documentados como se não existissem. Os textos antigos permanecem intactos. Onde faltam fontes/decisões, a classificação conserva a dependência e não reconstrói os originais D-01–D-52/28 lacunas por suposição.

Não foram consultados código, serviços, VMs, bases, inventários ou fontes externas. A pesquisa documental limitou-se aos caminhos/ secções acima; cabeçalhos/referências de DAT foram usados apenas para localizar as secções relevantes. Não se reavaliou a implementação inteira. Hashes das fontes em PRESERVATION.json.

## Revisão da classificação

- Independência é atribuída a uma entrega documental delimitada, sem novo comportamento executável ou decisão normativa; não a todo um módulo.
- As decisões DAT de identidade, reconciliação conservadora, candidato separado/aprovação manual e Outbox já aprovadas são pressupostos, não perguntas repetidas. Limiares, persistência e contratos concretos residuais são C.
- Outbox `at-least-once` e consumidores idempotentes não autorizam retry de operação protegida C5. A matriz mantém essa separação.
- Bloqueio por C4/I-04 aparece na execução protegida/reentrada e capacidades antigas pertinentes; AUTH-03/F02/G2/G4 e outros gates são explicitados separadamente. Não se inventam equivalências ou aplica C4 indiscriminadamente a todas as escritas.
- Falta de autorização de implementar mantém a execução fora do escopo, mesmo quando não haja dependência direta de C4. Nenhuma linha I/C é parecer de prontidão operacional.

Nenhuma alteração material foi necessária para concluir esta classificação. Nova raiz/poderes, alteração normativa ou autorização de implementar exige ato humano próprio; não se presume concedido por aprovar este relatório. Não há nova aprovação B-L/C4/estudos a solicitar.

## Git e preservação

Confirmados `/home/paulo/projects/livenet-v2`, `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`. Quatro tracked modificados anteriores: backend/migrations/env.py, docs/specifications/f0/data-model.md, docs/specifications/f0/implementation-status.md e frontend/README.md; além dos untracked. Preservados, incluindo os próprios documentos consultados que já tinham modificações.

[PRESERVATION.json](PRESERVATION.json) contém estado Git antes/depois, hashes das fontes/aprovados e comparação de ficheiros regulares Git enumerados. Só CONTINUITY.md muda entre os caminhos anteriores; a sua cópia literal está nesta pasta. Ato e restante pasta são novos. HEAD/branch/diff tracked e entradas anteriores do estado Git mantidos. Sem ignorados, metadados/ACL, estado interno Git, recursos externos ou snapshot atómico contra concorrência; esta conferência não é D09/V05-06 ou auditoria operacional.

A falha inicial bwrap foi contornada por execução autorizada fora do sandbox para leituras/escrita documental. Não foram encontradas AGENTS.md aplicáveis nos locais consultados. Conferidas referências locais/UTF-8 e integridade, sem testes/ensaios, SQL, código, serviços/infraestrutura, commits, pushes ou merges.

## Estados preservados

B-L v1.0, C4 v0.2, I-01–I-04 v0.1 e Fronteira C4 v0.1 aprovadas documentalmente nos seus objetos. I-01/I-02/I-03 abertas; I-04/clone integral gravável bloqueantes. Autoridade R2 única, UNKNOWN/BLOCKED, C5, D09/D10/V05-06 e operador único mantidos. P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados/bloqueantes; H02–H12 e GAP-001/002 conforme registos; RG1–RG7/D09/V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial. LiveNet interno; progbox DEV; STAGING/PROD em VMs Proxmox.
