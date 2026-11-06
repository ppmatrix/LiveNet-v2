# LiveNet v2 — índice de continuidade

30/10/2026 · Europe/Lisbon · **ÍNDICE DOCUMENTAL ATUALIZADO SOB AUTORIZAÇÃO HUMANA; NÃO É FONTE NORMATIVA NEM BASELINE OFICIAL**.

Este índice facilita retomar o trabalho. Remete para fontes e atos; não duplica o Plano Técnico, não aprova decisões, não substitui documentos arquiteturais e não concede autorização operacional. Em conflito, consultar a fonte e o seu ato de aprovação, preservando o âmbito temporal do histórico.

## Ambiente e origem do estado

Repositório de desenvolvimento confirmado por leitura: `progbox:/home/paulo/projects/livenet-v2`, branch `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`. Checkout com modificações preexistentes, preservadas. A pasta Windows LiveNet é uma cópia documental, não um checkout Git declarado.

Progbox é exclusivamente DEV. STAGING/PROD devem residir em VMs Proxmox. LiveNet é exclusivamente interno ao laboratório, sem exposição Internet. O inventário histórico identifica cinco nós pve01–pve05 e VM105/progbox em pve04 com scsi0/ide2 em local-lvm; isso não atribui recursos a R2/D09 nem prova capacidade livre. SynologyShared NFS com Backup permitido não prova cópias existentes ou recuperáveis. Não repetir inventário/auditoria geral para retomar a especificação.

## Decisões e fontes de autoridade

| Objeto | Estado atual e fonte |
| --- | --- |
| R2 C1–C7 | Baseline candidata aprovada documentalmente no seu âmbito; [contrato](../architecture/auth-boot-02-r2.md) e [rastreabilidade](../architecture/auth-boot-02-r2-traceability.md). Schemas/bytes executáveis não aprovados por extensão. |
| D09/D10 | [R1 §§11–12](../architecture/auth-boot-02-r1.md): preservação/confirmação independente, continuidade, recuperação controlada, autoridade única e sem failover automático. A recomendação histórica de duas pessoas não é convertida em requisito novo contra o modelo de operador único reafirmado pelo mandato atual. |
| D09-05 | Desenho lógico conceptual condicionado da Alternativa B aprovado, conforme reafirmação humana atual. Texto integral recuperado no chat `01a18cf5-a5d2-7711-98b8-5292296ea673`. Não aprova implementação. |
| D09-06 B-L | Preferência técnica condicionada aprovada: preservação crítica distribuída fora do NAS, R2/execução/D09 separados e recuperação suficiente fora de cada falha coberta. Comparação e resposta humana «sim» recuperadas no chat `01a18d4c-843c-7652-905b-e9141ee7f1ca`; mandato atual reafirma a aprovação. |
| B-L v1.0 — especificação integral | **Aprovada documentalmente, de forma condicionada, em 30/10/2026**, por declaração humana expressa no pedido de continuidade seguinte. [Registo do ato e hash dos bytes preservados](../architecture/decisions/d09-06-bl-v1-approval-20261030.md). Não aprova implementação nem demonstra garantias. |
| P4-B4 e D1/D2/D3 | Aceitação humana dos bytes finais e fecho documental registados em [P4-B4](../architecture/decisions/dr09a-p4-b4-acceptance-20261030.md). Cabeçalhos históricos de pendência nos documentos anteriores não anulam esse ato posterior. |
| NC-01 e retenção | NC-01 intacto; D1/D2/D3 aceites no âmbito P4-B4. [D2](../specifications/f0/dr07-retention-addendum.md), especialmente V05-06/B10, distingue a demonstração independente da confirmação D09. TBD residuais preservados. |

Os chats são localizadores de proveniência, não garantia de acesso futuro. Os textos recuperados e as mensagens identificadas constam de [RECOVERED_SOURCES.json](../architecture/proposals/d09-06-bl-conditional-20261030/RECOVERED_SOURCES.json), com limites em [SOURCES_AND_REVIEW.md](../architecture/proposals/d09-06-bl-conditional-20261030/SOURCES_AND_REVIEW.md). Esses textos e o manifesto da entrega anterior permanecem históricos. O registo posterior acima documenta a aprovação da especificação B-L v1.0; não reconstrói atos ausentes nem altera documentos normativos anteriores.

O operador humano reiterou expressamente nesta conversa a aprovação B-L v1.0 de 30/10/2026 e determinou que não seja solicitada novamente. A decisão já está resolvida e registada; não constitui dependência pendente para a preparação técnica documental autorizada. A reiteração conserva o mesmo objeto e todos os gates, sem criar uma segunda aprovação ou ampliar o seu âmbito.

## Última etapa e próxima atividade

Última aprovação concluída: [especificação condicionada B-L v1.0](../architecture/proposals/d09-06-bl-conditional-20261030/SPECIFICATION.md), SHA-256 `e889171ffc1db17afe7e46b40a927f268ffafb70dfe8ceb9ef26aef3207f86a6`, preservada integralmente. As menções internas à aprovação pendente descrevem a preparação; o ato posterior de 30/10/2026 resolve esse estado documental.

Atividade autorizada pelo pedido atual: registar a aprovação e atualizar este índice; preparar autonomamente a especificação técnica documental da disponibilização e imposição C4, analisar alternativas e entregar proposta consolidada. [Proposta técnica C4](../architecture/proposals/bl-c4-technical-20261030/PROPOSAL.md): **preparada para revisão humana; não aprovada**. [Fontes e verificação](../architecture/proposals/bl-c4-technical-20261030/EVIDENCE_AND_REVIEW.md). Nenhuma análise de alternativa constitui escolha arquitetural material aprovada.

Continuação documental produzida sob a reiteração humana: [protocolo candidato de disponibilização e iniciação única](../architecture/proposals/bl-c4-protocol-20261030/PROTOCOL.md), com máquina de estados analítica, falhas entre reserva e entrada real, C5, corte, sete cenários e famílias técnicas sem seleção material. [Rastreabilidade e preservação](../architecture/proposals/bl-c4-protocol-20261030/REVIEW.md). Não se confunde este novo aprofundamento candidato com a especificação B-L v1.0 já aprovada.

Atividade seguinte autorizada: continuar a análise documental reversível das condições de prova e dos mecanismos candidatos, reutilizando fontes, sem voltar a pedir aprovação B-L v1.0. A adoção de uma arquitetura que altere base confiada, poderes ou garantias, ou a alteração de gate, constitui decisão material própria. Implementação, ensaios operacionais, atribuição física e infraestrutura continuam sem autorização.

## Gates, lacunas e limites permanentes

| Conjunto | Estado preservado |
| --- | --- |
| P4-B4; D1/D2/D3; NC-01 | Etapa documental encerrada; bytes aceites; NC-01 intacto. |
| V02/CF-02 | Abertas. |
| AUTH-03/F02/G2/G4 | Fechados e bloqueantes. |
| H02–H12; GAP-001/002 | Pendentes/abertos e bloqueantes conforme os seus registos. |
| RG1–RG7; R2 D09; V05-06 | Por demonstrar; demonstrações distintas. |
| O3; DEV-09B | Não aprovado; não autorizado. |
| F0 | Working draft; baseline não oficial. |

Autoridade R2 única; sem atomicidade distribuída presumida; UNKNOWN/BLOCKED; sem retry/retoma automática. C5 permite apenas a tentativa original continuamente vinculada depois de satisfeitas as condições prévias. Reentrada exige continuidade, invalidação demonstrada, decisão humana, novo pedido e nova aprovação.

Um único operador humano; comprometimento total dos seus poderes e de toda a recuperação fora da garantia. Separação de VMs/nós/contas não prova independência perante poder transitivo comum. Clone integral gravável adversarial mantém o bloqueador forte histórico; B-L não o resolve por preservar recibos.

Sem alteração de documentos normativos aprovados, VMs, Proxmox, Synology, rede, serviços, bases, credenciais, storage, deployments, reserva física, commits, pushes ou merges. Este índice é navegação documental atualizada, sem autoridade normativa ou autorização duradoura para trabalho operacional futuro. A versão imediatamente anterior foi preservada em [CONTINUITY.before.md](../architecture/proposals/bl-c4-protocol-20261030/CONTINUITY.before.md); a versão anterior ao registo de aprovação conserva-se no [arquivo da etapa precedente](../architecture/proposals/bl-c4-technical-20261030/CONTINUITY.before.md).
