# B-L/C4 — continuidade e revisão do aprofundamento de protocolo

30/10/2026 · Europe/Lisbon · Etapa exclusivamente documental.

## Aprovação resolvida e trabalho produzido

A aprovação documental condicionada B-L v1.0 de 30/10/2026 já tem [registo próprio](../../decisions/d09-06-bl-v1-approval-20261030.md). O pedido humano atual reitera-a e determina «Não voltes a solicitar esta aprovação». O índice foi atualizado para que a aprovação não reapareça como dependência pendente. Não se cria novo ato, não se altera o registo existente e não se confunde a reiteração com aprovação de implementação ou de outro objeto.

A [especificação aprovada](../d09-06-bl-conditional-20261030/SPECIFICATION.md) conserva SHA-256 `e889171ffc1db17afe7e46b40a927f268ffafb70dfe8ceb9ef26aef3207f86a6`. As menções históricas internas à pendência continuam contextualizadas pelo ato posterior, sem reescrita dos bytes.

O [protocolo candidato](PROTOCOL.md) aprofunda a [proposta técnica anterior](../bl-c4-technical-20261030/PROPOSAL.md) através de estados analíticos, oportunidade irrevogável, entrada real no alvo e falhas entre esses pontos. Explicita por que um ledger único não prova um despacho único e por que exclusão local não contém um clone integral gravável. Não seleciona uma implementação ou nova base confiada.

## Fontes reutilizadas e alcance

| Fonte | Uso nesta etapa |
| --- | --- |
| Pedido humano atual nesta conversa | Autoriza continuação documental autónoma, confirma aprovação resolvida e preserva gates; intervenção apenas para decisão material ou alteração de gate. |
| Registo B-L v1.0 e CONTINUITY.md atuais | Recuperação do estado já documentado, sem procura de uma aprovação nova nem repetição de auditoria histórica. |
| B-L v1.0 e fontes recuperadas do seu pacote | Invariantes, operador único, B-L fora de dependência exclusiva NAS e sete cenários. Textos já disponíveis e preservados; sem voltar a depender de anexos temporários. |
| Proposta técnica C4 anterior e EVIDENCE_AND_REVIEW.md | Passos K3–J, mediação M/T/L, limites de savepoint/rollback, fontes primárias já confrontadas e alternativas. Não se refaz comparação geral. |
| C1–C7, D09/D10, D2 V05-06 e DEV-04/05 previamente consultados | Obrigações e contraexemplos históricos reutilizados. Nenhum runner, SQL, teste ou leitura operacional repetidos. |

O texto novo é análise técnica do agente. «Irrevogável», «continuação viva» e «mediação completa» são requisitos a demonstrar, não propriedades cuja existência seja declarada pela redação. Os estados P0–P6 são notação de prova, sem novos campos, enums ou schema executável. Nenhuma conclusão nova de produto ou de capacidade do laboratório é inferida.

## Conferência de coerência

| Tema | Resultado documental |
| --- | --- |
| Anterioridade | R2 durável e preservação independente pertinente precedem disponibilização/entrada; evento futuro não confirma a sua própria autorização. |
| Início único | Compromisso L, armamento do fluxo e entrada J distinguidos; gasto sem efeito é possível, sem exatamente uma vez. |
| C5 | Original continuamente vinculado pode prosseguir depois das confirmações; consulta, restart, reconexão ou resultado incerto não recriam capacidade. |
| Falhas | Interleavings explícitos antes/depois de R2, L, W, armamento, entrada e término; nenhuma tabela é relatório de ensaios executados. |
| SQL e rollback | Toda entrada precisa de imposição; consumo fora de rollback não dispensa exclusão no recurso até término. |
| Restore e clone | Continuidade externa e invalidação antigas exigidas; meio autónomo gravável mantém bloqueador forte. |
| Recovery | Sete cenários conservados, com fundamento sobrevivente, controlo de bloqueio e operador único. |
| Alternativas | Três famílias para P2–J mantidas como candidatas; nenhuma adoção material, produto ou atribuição física. |
| D09 / V05-06 | Demonstrações distintas; confirmação não prova commit e COMPROVADO não autoriza destruição. |

O que avança é a precisão do problema e do protocolo candidato. O que não avança sem evidência é a classificação de C4, independência, continuidade recuperável, suficiência de recursos ou garantias contra clone. Se uma futura opção exigir reduzir poderes/efeitos cobertos ou adotar novo fundamento de confiança, essa decisão material deve ser explicitada antes da adoção. Isso não reabre a aprovação documental B-L v1.0.

## Preservação e limites da verificação

Repositório real em `progbox:/home/paulo/projects/livenet-v2`, branch main, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`. A pasta Windows é cópia documental. Foram guardados hashes de comparação dos Markdown/JSON preexistentes em docs/experiments e estado Git remoto, sem inventário de infraestrutura ou auditoria geral.

Só se acrescenta esta pasta e se atualiza o índice não normativo sob autorização. A [cópia imediatamente anterior do índice](CONTINUITY.before.md) conserva os seus bytes; os links dessa cópia usam a base original docs/project/CONTINUITY.md. Documentos anteriores, incluindo versão B-L aprovada, registo da decisão, proposta técnica e manifestos históricos, permanecem inalterados.

[PRESERVATION.json](PRESERVATION.json) regista comparação e hashes, excluindo apenas os caminhos novos e a atualização autorizada do índice; a aprovação resolvida é verificada como objeto preservado, não submetida novamente. A verificação inclui UTF-8, referências remotas e igualdade local/remota da entrega. Não cobre todos os ficheiros, metadados, ACL, `.git` interno, recursos operacionais ou snapshot atómico contra concorrência; não é D09 ou revisão externa.

Sem novas instalações, testes, SQL, VM, rede, storage, conta, serviço, reserva física, commit ou push. SSH limitou-se a documentação/estado Git e entrega; não houve contacto com interfaces Proxmox/Synology. Os documentos são recursos próprios preservados da entrega; nenhum recurso operacional foi criado ou removido.

## Continuação autorizada

A preparação documental reversível pode continuar a comparar condições de prova das famílias candidatas, reutilizando fontes. Não se estabelece espera por nova aprovação B-L v1.0. A intervenção humana fica reservada à adoção de decisão arquitetural material, alteração de garantia ou gate; implementar/ensaiar exige autorização própria.

P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados/bloqueantes; H02–H12/GAP-001/002 bloqueantes; RG1–RG7/D09/V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial. Aprovação B-L v1.0 concluída e preservada; este protocolo permanece candidato.
