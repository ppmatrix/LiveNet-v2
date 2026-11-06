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
| C4 consolidada v0.2 | **Aprovada documentalmente, de forma condicionada, em 30/10/2026**, por declaração humana expressa, SHA-256 `937bb32ab57fb0859d414e3ada9a11dbf963fdb19158d85a0e2c55cf019ff3ab`. [Ato próprio](../architecture/decisions/bl-c4-v02-approval-20261030.md). I-01–I-04 permanecem técnicas pendentes; I-04/clone gravável bloqueantes. |
| I-01–I-04 v0.1 | **Aprovada exclusivamente como documento condicionado em 30/10/2026**, SHA-256 `dd307b7adde92cd4a3d2ea5ac17e59f5ca46010ae0598bb590bae8f18c8adfbb`. [Ato próprio](../architecture/decisions/bl-c4-i01-i04-v01-approval-20261030.md). Não seleciona CAND-1/2/3 nem encerra lacunas/demonstra C4; I-04/clone gravável bloqueantes. |
| P4-B4 e D1/D2/D3 | Aceitação humana dos bytes finais e fecho documental registados em [P4-B4](../architecture/decisions/dr09a-p4-b4-acceptance-20261030.md). Cabeçalhos históricos de pendência nos documentos anteriores não anulam esse ato posterior. |
| NC-01 e retenção | NC-01 intacto; D1/D2/D3 aceites no âmbito P4-B4. [D2](../specifications/f0/dr07-retention-addendum.md), especialmente V05-06/B10, distingue a demonstração independente da confirmação D09. TBD residuais preservados. |

Os chats são localizadores de proveniência, não garantia de acesso futuro. Os textos recuperados e as mensagens identificadas constam de [RECOVERED_SOURCES.json](../architecture/proposals/d09-06-bl-conditional-20261030/RECOVERED_SOURCES.json), com limites em [SOURCES_AND_REVIEW.md](../architecture/proposals/d09-06-bl-conditional-20261030/SOURCES_AND_REVIEW.md). Esses textos e o manifesto da entrega anterior permanecem históricos. O registo posterior acima documenta a aprovação da especificação B-L v1.0; não reconstrói atos ausentes nem altera documentos normativos anteriores.

O operador humano reiterou expressamente nesta conversa a aprovação B-L v1.0 de 30/10/2026 e determinou que não seja solicitada novamente. A decisão já está resolvida e registada; não constitui dependência pendente para a preparação técnica documental autorizada. A reiteração conserva o mesmo objeto e todos os gates, sem criar uma segunda aprovação ou ampliar o seu âmbito.

## Última etapa e próxima atividade

Etapa atual de análise documental: [fronteira obrigatória de efeito e corte](../architecture/proposals/bl-c4-effect-boundary-20261030/PROPOSAL.md), candidata 0.1; [matriz de meios/poderes](../architecture/proposals/bl-c4-effect-boundary-20261030/MATRIX.md). O estudo e a viabilidade CAND anterior não são novas aprovações. A última aprovação concluída mantém-se abaixo.

Última aprovação concluída: [I-01–I-04 v0.1](../architecture/proposals/bl-c4-i01-i04-20261030/PROPOSAL.md), SHA-256 `dd307b7adde92cd4a3d2ea5ac17e59f5ca46010ae0598bb590bae8f18c8adfbb`, por [ato humano registado em 30/10/2026](../architecture/decisions/bl-c4-i01-i04-v01-approval-20261030.md), exclusivamente documental condicionada. C4 v0.2 e B-L v1.0 conservam aprovações e hashes anteriores. Documentos aprovados, relatórios e manifestos preservados, incluindo cabeçalhos históricos de candidatura.

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

As duas etapas seguintes conservam a narrativa histórica anterior à aprovação C4 v0.2; as suas menções de pendência foram resolvidas pelo ato posterior acima, sem reescrever as propostas ou revisões. A etapa atual consta no final deste índice.

## Consolidação técnica para revisão final — 30/10/2026

Retomada no checkout acessível de progbox, `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`, com alterações anteriores preservadas. O estado da última sessão foi recuperado deste índice e dos pacotes técnicos existentes, sem repetir auditorias ou inventários. B-L v1.0 mantém a aprovação documental já concluída.

[Proposta técnica C4 consolidada 0.2](../architecture/proposals/bl-c4-consolidated-20261030/PROPOSAL.md): entrada atual de revisão final desta etapa, reunindo a proposta 0.1 e o protocolo candidato, que permanecem históricos intactos. Distingue compromisso irrevogável, disponibilização e entrada real J; reúne obrigações de prova, falhas, sete cenários e decisões materiais. Continua candidata, sem adoção de arquitetura ou garantia demonstrada. Clone integral gravável mantém o bloqueador forte; todos os gates acima permanecem.

[Verificação documental](../architecture/proposals/bl-c4-consolidated-20261030/REVIEW.md) e [índice anterior preservado](../architecture/proposals/bl-c4-consolidated-20261030/CONTINUITY.before.md). Preparação documental reversível continua autorizada; intervenção humana apenas para decisão material ou mudança de gate. Sem implementação, alterações operacionais, commits ou pushes.

## Revisão documental C4 v0.2 — 30/10/2026

Concluída a [revisão documental A–H](../architecture/proposals/bl-c4-consolidated-20261030/REVIEW_DOCUMENTAL_V02.md): **PRONTA PARA APROVAÇÃO DOCUMENTAL**, exclusivamente condicionada. Não é aprovação humana: C4 v0.2 permanece candidata; B-L v1.0 mantém a aprovação concluída. Sem contradições críticas identificadas; quatro observações importantes sobre provas ainda ausentes e duas clarificações editoriais resolvidas no relatório, sem alterar a proposta original. Nenhuma correção obrigatória ou decisão arquitetural material indispensável para submissão documental.

Proposta v0.2, revisão anterior e normas preservadas. [Estado Git e preservação antes/depois](../architecture/proposals/bl-c4-consolidated-20261030/REVIEW_DOCUMENTAL_V02_STATE.json); [índice anterior](../architecture/proposals/bl-c4-consolidated-20261030/CONTINUITY.pre-review-v02.md). Próximo passo recomendado: revisão humana da C4 v0.2 com o relatório, sem reabrir B-L nem transformar pendências técnicas em garantias demonstradas. Clone gravável e todos os gates mantêm os estados anteriores. Sem implementação, testes/ensaios, alterações operacionais, commits, pushes ou merges.

## Aprovação C4 v0.2 e aprofundamento I-01–I-04 — 30/10/2026

Aprovação humana expressa C4 v0.2 registada em [ato próprio](../architecture/decisions/bl-c4-v02-approval-20261030.md), após confirmação do hash dos bytes. Não reabre B-L, não aprova mecanismos por extensão e não demonstra C4. Documentos aprovados e revisões/manifestos históricos preservados.

[Proposta de aprofundamento I-01–I-04, candidata 0.1](../architecture/proposals/bl-c4-i01-i04-20261030/PROPOSAL.md): prioridade P4–J e mediação completa; distingue atribuição durável, travessia local singular Q/J e exclusão de meios de efeito. Compara L no domínio R2, no diário M e em primitiva própria do alvo; nenhuma composição selecionada ou declarada exequível. Regista poderes/vias de contorno, contraexemplos, conteúdo/confiança D09, recuperação e condições de demonstração. I-01/I-02/I-03 permanecem abertas; **I-04 e clone integral gravável continuam bloqueadores técnicos**, sem alteração de garantia ou gate.

[Revisão/fontes/preservação](../architecture/proposals/bl-c4-i01-i04-20261030/REVIEW.md), [estado antes/depois](../architecture/proposals/bl-c4-i01-i04-20261030/PRESERVATION.json) e [índice anterior literal](../architecture/proposals/bl-c4-i01-i04-20261030/CONTINUITY.before.md). Próxima revisão: avaliar a análise candidata; continuar comparação documental de provas e limites sem nova aprovação C4 v0.2/B-L. Adoção de arquitetura material ou alteração normativa exige decisão humana própria; nenhuma adotada. Sem implementação, testes/ensaios, infraestrutura/serviços, commits ou pushes.

## Aprovação I-01–I-04 v0.1 e viabilidade CAND-1/2/3 — 30/10/2026

[Aprovação documental I-01–I-04 v0.1](../architecture/decisions/bl-c4-i01-i04-v01-approval-20261030.md) registada com SHA-256 calculado do objeto acessível. As menções de candidatura da etapa anterior descrevem o estado histórico, agora resolvido apenas quanto à aprovação documental. Nenhuma CAND selecionada, lacuna encerrada ou gate alterado.

[Análise de viabilidade e refutação, candidata 0.1](../architecture/proposals/bl-c4-cand-feasibility-20261030/PROPOSAL.md): relatório executivo, análise individual, matriz e critérios de refutação. **Nenhuma das três composições é viável como solução da garantia forte enquanto clone integral gravável autónomo ou escritor privilegiado fora da imposição permanecer admissível.** Plausibilidade local é condicionada e não demonstra viabilidade no modelo completo. Não se afirma topologia/poderes atuais nem impossibilidade de qualquer arquitetura futura.

Prioridade I-02/I-04: não aprofundar indefinidamente Q antes de justificar a fronteira de efeito perante privilégios, cópias e trabalho antigo. Próxima decisão humana recomendada: manter modelo/bloqueios e delimitar uma proposta de fronteira obrigatória para todos os meios e poderes cobertos antes de adotar CAND-1/2/3. Novo fundamento confiado ou redução de ameaça/efeito exigem decisão material própria, nenhuma adotada. I-04/clone e todos os gates preservados; UNKNOWN/BLOCKED, C5, R2 único, D09/D10/V05-06 mantidos.

[Fontes e revisão](../architecture/proposals/bl-c4-cand-feasibility-20261030/REVIEW.md), [Git/preservação antes e depois](../architecture/proposals/bl-c4-cand-feasibility-20261030/PRESERVATION.json) e [índice anterior literal](../architecture/proposals/bl-c4-cand-feasibility-20261030/CONTINUITY.before.md). Exclusivamente documentação/análise estática; sem implementação, ensaios/SQL, alterações operacionais, commits, pushes ou merges.

## Estudo da fronteira obrigatória de efeito e corte — 30/10/2026

[Proposta consolidada candidata 0.1](../architecture/proposals/bl-c4-effect-boundary-20261030/PROPOSAL.md) e [matriz ME-01–ME-18](../architecture/proposals/bl-c4-effect-boundary-20261030/MATRIX.md): definições por remissão ao âmbito aprovado, caminhos de efeito/poderes e quatro obrigações de corte separadas. Alternativas no alvo, storage, virtualização e fundamentos externos comparadas sem escolha de tecnologia/raiz/arquitetura. Inclui contraexemplos, confiança mínima, sete cenários simultâneos e condições de refutação.

**Resultado: fronteira definida por condições necessárias; existência/realização para o modelo completo não demonstradas. Com meio integral gravável autónomo fora da imposição efetiva, garantia forte inviável nesse subcaso.** Nenhuma família conceptual remove esse bloqueador por si. I-01/I-02/I-03 abertas; I-04 e clone gravável bloqueantes, sem alteração de garantia/gate ou aprovação anterior.

Recomendação: manter modelo/bloqueios; qualquer proposta de adoção terá de justificar cobertura de vias raw, capacidades antigas, meios criáveis/restauráveis e poder sobre as próprias guardas. Nova raiz/poderes ou redefinição do efeito são decisões materiais reservadas, não adotadas. Não foi indispensável decisão intermédia para concluir o estudo documental.

[Revisão e rastreabilidade](../architecture/proposals/bl-c4-effect-boundary-20261030/REVIEW.md), [Git/preservação antes e depois](../architecture/proposals/bl-c4-effect-boundary-20261030/PRESERVATION.json) e [índice anterior](../architecture/proposals/bl-c4-effect-boundary-20261030/CONTINUITY.before.md). Sem implementação, auditoria/inventário operacional, SQL, ensaios/testes, alterações de serviços/infraestrutura, commits, pushes ou merges.
