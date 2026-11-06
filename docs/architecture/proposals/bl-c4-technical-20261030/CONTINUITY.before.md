# LiveNet v2 — índice de continuidade

30/10/2026 · Europe/Lisbon · **PROPOSTA DE ÍNDICE; NÃO É FONTE NORMATIVA NEM BASELINE OFICIAL**.

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
| P4-B4 e D1/D2/D3 | Aceitação humana dos bytes finais e fecho documental registados em [P4-B4](../architecture/decisions/dr09a-p4-b4-acceptance-20261030.md). Cabeçalhos históricos de pendência nos documentos anteriores não anulam esse ato posterior. |
| NC-01 e retenção | NC-01 intacto; D1/D2/D3 aceites no âmbito P4-B4. [D2](../specifications/f0/dr07-retention-addendum.md), especialmente V05-06/B10, distingue a demonstração independente da confirmação D09. TBD residuais preservados. |

Os chats são localizadores de proveniência, não garantia de acesso futuro. Os textos recuperados e as mensagens identificadas constam de [RECOVERED_SOURCES.json](../architecture/proposals/d09-06-bl-conditional-20261030/RECOVERED_SOURCES.json), com limites em [SOURCES_AND_REVIEW.md](../architecture/proposals/d09-06-bl-conditional-20261030/SOURCES_AND_REVIEW.md). As aprovações D09-05/06 ainda não tinham registo dedicado localizado no repositório; esta proposta indexa a sua fonte humana sem se promover a novo ato normativo.

## Última etapa e próxima atividade

Última etapa documental produzida: [especificação condicionada B-L v1.0](../architecture/proposals/d09-06-bl-conditional-20261030/SPECIFICATION.md), com funções, poderes transitivos, sequência de disponibilização, C4, sete cenários, recuperação e critérios de demonstração. **Bytes da especificação pendentes de revisão humana final.** D09-05/06 aprovados conceptualmente não equivalem a aceitar esta nova redação.

Atividade autorizada pelo mandato atual: concluir/verificar a proposta e apresentá-la para uma única revisão final. Consultar fontes existentes e corrigir apenas problemas editoriais de documentos de trabalho não aprovados, sem alterar significado normativo. Não há autorização implícita para implementar, testar falhas ou recolher novamente o inventário operacional.

Próxima etapa recomendada após revisão favorável: preparação técnica documental da disponibilização e imposição C4, ligada aos cenários D09-03 e recuperação, reutilizando evidências. Arquitetura física, recursos, mecanismos de confiança ou alterações de garantia materiais exigem decisão própria. Não iniciar implantação ou ensaios por inferência.

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

Sem alteração de documentos normativos aprovados, VMs, Proxmox, Synology, rede, serviços, bases, credenciais, storage, deployments, reserva física, commits, pushes ou merges. Este índice permanece proposta até revisão; não é autorização duradoura para trabalho operacional futuro.
