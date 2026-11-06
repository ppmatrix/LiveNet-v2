# R2-DEV-08 — resumo executivo da proposta documental

Estado: **PROPOSTA NÃO APROVADA**. Data editorial: 2026-10-27, Europe/Lisbon; sem atestado UTC.
Origem: `progbox:/home/paulo/projects/livenet-v2`. HEAD observado: `647179c928888adfeef0f69f582fd13c5fc17350`.

A autorização humana para executar R2-DEV-08 permite preparar este pacote documental. Não aprova a arquitetura, a alteração do modelo de ameaça, os schemas, infraestrutura ou ensaios futuros. C1–C7 conservam a aprovação documental e os limites registados no contrato existente.

## Resultado que exige decisão humana

**Mantendo uma cópia integral gravável sob controlo adversarial, a cessação universal é inviável com os pressupostos atuais.** O efeito no clone continua a contar, mesmo sem publicação, clientes ou acesso ao endpoint oficial. Esta proposta não retira silenciosamente o clone do domínio protegido.

DEV-05 documenta original em epoch 2/payload 0 e clone vivo em epoch 1/payload 1 depois da cessação SQL local. Documenta também efeito por chamada direta sem consumo externo e escrita administrativa sem entrada no ledger de efeitos. São factos dos artefactos históricos, não observações repetidas por DEV-08. A consequência arquitetural é uma inferência: admissão única, recibo, identidade ou fence no original não controlam esse meio independente.

Há três decisões distintas possíveis: manter a ameaça integral e reconhecer o bloqueio; manter a propriedade forte alterando explicitamente os poderes de cópia/escrita e demonstrando a sua restrição; ou aprovar uma garantia mais estreita, que não satisfará a propriedade forte histórica. A matriz [DECISIONS.md](DECISIONS.md) torna estas alternativas e o seu custo em disponibilidade expressos. Nenhuma está selecionada pelo utilizador nesta entrega.

## Entrega concreta

| Documento | Resultado revisável |
| --- | --- |
| [BOUNDARY.md](BOUNDARY.md) | Predicado de efeito, domínio de cópia, inventário conhecido e catálogo de caminhos por fechar, incluindo superuser, meios independentes, backups e restauração. |
| [CUSTODY.md](CUSTODY.md) | Poderes diretos/transitivos e separações administrativas necessárias; pessoas e domínios físicos não comprovados permanecem por identificar. |
| [PROTOCOL.md](PROTOCOL.md) | Admissão, reserva não reutilizável, sessão/transação, contenção, corte terminal, atestado, incerteza, reconciliação e nova aprovação humana, preservando C1–C7. |
| [LAB_FEASIBILITY.md](LAB_FEASIBILITY.md) | Topologia candidata condicional para Proxmox e confronto entre recursos documentados e requisitos não verificados. |
| [DECISIONS.md](DECISIONS.md) | Opções e registo individual de decisões pendentes para aprovação humana. |
| [VALIDATION.md](VALIDATION.md) | Critérios e cenários futuros com barreiras, observadores, refutação e caso decisivo de clone antigo vivo e gravável. |
| [PROVENANCE.md](PROVENANCE.md) | Fontes, limites de independência, acesso, HEAD e método de preservação; JSON de baseline/comparação acompanham o pacote. |

O protocolo escolhe, como especificação candidata, consumo durável em A e uma única iniciação ligada previamente a contexto vivo em B, sem token transferível, com registo de iniciação fora do rollback do efeito. O corte só pode ser confirmado depois do término de todo o trabalho antigo e da exclusão persistente em todos os meios abrangidos. São obrigações de desenho para implementação e prova futuras; nenhuma destas capacidades foi instalada ou demonstrada aqui.

Não existe inventário físico fechado nem matriz nominal de custódios demonstrados. A VM dedicada de autoridade é determinação documental; STAGING Proxmox é ambiente previsto. Não foram localizados números de hosts, VMIDs, capacidade CPU/RAM, storage, BMC/PDU, HSM, PKI operacional, UTC autenticado com erro limitado ou W/D09 independente que permitam declarar o laboratório pronto. Acesso SSH ao progbox não demonstra acesso ou poderes sobre Proxmox.

## Próximo passo proposto

Realizar **R2-DEV-09-PLAN, apenas documental**, após decisão humana explícita nas linhas H01–H04 de DECISIONS: escolher domínio/ameaça e significado do atestado, nomear custódios e autorizar a recolha documental do inventário concreto. A designação é uma proposta de trabalho, sem relação autorizativa com DEV-09B. A entrega seguinte seria inventário nominal de recursos e caminhos, matriz assinável de poderes, mecanismo de corte selecionado com documentação de compatibilidade, parâmetros de continuidade/tempo/D09 e plano de ensaio com impacto e limpeza delimitados. Se H01 mantiver cópia integral gravável adversarial, produzir registo de inviabilidade/bloqueio; não preparar um ensaio com veredito positivo impossível.

Ensaios, provisionamento e eventual aprovação de schemas/bytes seriam decisões posteriores próprias. A candidata não recebe o veredito «pronta para ensaio independente» enquanto os bloqueadores assinalados persistirem.

Foram criados apenas documentos e evidências de preservação na pasta nova, com cópia local. Sem testes, SQL, instalação, provisionamento, código operacional, alteração a ficheiros anteriores ou contratos, commits ou push. AUTH-03/F02/G2/G4 fechados; GAP-001/002 abertas; DEV-09B não autorizada.
