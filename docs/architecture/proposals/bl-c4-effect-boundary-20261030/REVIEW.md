# Fronteira obrigatória C4 — revisão, rastreabilidade e preservação

30/10/2026 · Europe/Lisbon · Revisão documental pelo autor, sem revisor independente ou prova operacional.

## Mandato e estado dos documentos

Fonte humana direta: pedido atual «Estudo documental da fronteira obrigatória de efeito e corte (C4 / I-02 / I-04)». Autoriza análise estática autónoma, proposta/matriz/revisão/preservação e índice não normativo necessário. Não autoriza arquitetura, nova raiz, redução da ameaça, implementação ou ensaios.

B-L v1.0, C4 v0.2 e I-01–I-04 v0.1 foram identificadas por caminho/versão e hashes, comparados com os atos existentes. Todos coincidem. Cabeçalhos históricos de pendência não reabrem aprovações. A análise de viabilidade CAND é candidata anterior, não declarada aprovada pelo presente mandato. Não foi criado ato de aprovação novo nesta etapa.

[PROPOSAL.md](PROPOSAL.md) e [MATRIX.md](MATRIX.md) são candidatos 0.1 novos. A primeira define termos e quatro obrigações separadas de corte, analisa cinco famílias conceptuais e dez contraexemplos, cruza sete cenários e reserva decisões materiais. A matriz abrange 18 classes de meios/habilitadores, poderes e pontos de imposição relativos a cada via. Não é inventário real ou prova de completude de uma arquitetura.

## Ambiente e fontes identificadas

Repositório efetivamente acessível `/home/paulo/projects/livenet-v2`, branch `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`. Quatro tracked modificados e untracked preexistentes. HEAD é contexto, não declaração de que os documentos de trabalho estão nesse commit. Nenhum fetch/acesso remoto GitHub, comparação Windows ou consulta de infraestrutura efetuados.

Hashes antes da escrita; as fontes reutilizadas foram recuperadas nesta mesma conversa, mantendo limites de proveniência. O índice antigo tem cópia literal nesta pasta. As leituras normativas incidiram nas secções indicadas, sem nova auditoria integral de todos os contratos.

| Fonte, versão/estatuto e alcance | SHA-256 antes |
| --- | --- |
| [B-L v1.0 aprovada; §§2/3/6 relidas, sete cenários/invariantes reutilizados](../d09-06-bl-conditional-20261030/SPECIFICATION.md) | `e889171ffc1db17afe7e46b40a927f268ffafb70dfe8ceb9ef26aef3207f86a6` |
| [Ato B-L, aprovação de 30/10/2026; reutilizado](../../decisions/d09-06-bl-v1-approval-20261030.md) | `36713930a8c503d4dad049bd6f2831f6477393e4c2e4062b7b9fc1bcce5e1146` |
| [C4 v0.2 aprovada; semântica/vínculos reutilizados](../bl-c4-consolidated-20261030/PROPOSAL.md) | `937bb32ab57fb0859d414e3ada9a11dbf963fdb19158d85a0e2c55cf019ff3ab` |
| [Ato C4 v0.2; relido](../../decisions/bl-c4-v02-approval-20261030.md) | `1fa8e1c97c93d79c9fd6779665965a8cd941676f5618fa2e413b21c9deaadbab` |
| [I-01–I-04 v0.1 aprovada; hipóteses/limites reutilizados](../bl-c4-i01-i04-20261030/PROPOSAL.md) | `dd307b7adde92cd4a3d2ea5ac17e59f5ca46010ae0598bb590bae8f18c8adfbb` |
| [Ato I-01–I-04 v0.1; relido](../../decisions/bl-c4-i01-i04-v01-approval-20261030.md) | `d01360c16b63fb76ea940eeaa99822184926de8036727bb6a8f510cfdad901e3` |
| [Viabilidade CAND-1/2/3, candidata 0.1; consultada/reutilizada](../bl-c4-cand-feasibility-20261030/PROPOSAL.md) | `a8ff491e9d66a84668da01744fa453f6240eb24e59ada40644dea622f28e838e` |
| [R2-CONSOLIDATION-1; C1–C7 relidos](../../auth-boot-02-r2.md) | `241f65858fdfcf8676a4fef4d251f1fdef95dfb2987d971b26cd2c993bfcbfc1` |
| [R1 consolidado; D09/D10 §§11–12 relidos](../../auth-boot-02-r1.md) | `59c312d7dded14db9781d5e2a8e91acbce433b79a6d69427d3884f846e182eff` |
| [D2 aceite; V05-06 relido, restantes reservas reutilizadas](../../../specifications/f0/dr07-retention-addendum.md) | `a996d78fff71002db47f2756836669fd3f096bff3074bae10c98c31afdaab818` |
| [DEV-05 histórico de 27/10/2026; resultados/alcance relidos](../../../../experiments/auth_boot_02_r2_dev05/REPORT.md) | `0143b1dcbe5155e8e3eb6f70946e87f7a692c9ee53174715b3ba63123212b490` |
| [Continuidade anterior; consultada e preservada](../../../project/CONTINUITY.md) | `5d54cd281ed174602f59116a72533a5c14c090f45ef05f4a269c3186fe768a6a` |

DEV-05 fornece evidência histórica limitada a laboratório/fixtures, incluindo bypass, clone vivo e efeito após corte local. Não demonstra controlo atual das VMs, impossibilidade de clone, raiz não copiável ou fronteira nova. As falhas que os ensaios históricos esperavam observar não são garantias positivas. Nenhum runner/SQL/teste foi repetido. Anexos/chats históricos não foram recuperados de novo e fontes assinaladas como ausentes não foram reconstruídas.

Não foram necessários factos novos de produto ou bibliografia externa para estas deduções conceptuais; não se escolheram tecnologia ou implementação. As alternativas são hipóteses do agente confrontadas com requisitos e limites já documentados, sem alegação de propriedade nativa instalada ou atualidade de inventário histórico.

## Rastreabilidade aos requisitos aprovados

| Fonte/requisito | Resposta nesta entrega | Limite preservado |
| --- | --- | --- |
| R2 C4; B-L §6; C4 §§3–6 | Proposta §§3–7 e matriz ME-01–ME-08: efeito/início separados, todas as vias e singularidade sem contorno. | Definições analíticas não criam nova classe de operação; UPDATE fixo e todos os vínculos mantidos. |
| I-02/I-04 e I-01–I-04 §§5/8 | Proposta §§4–7, matriz de meios/poderes e fecho de capacidades/cópias. | Q, L e endpoint não resolvem meio autónomo. Nenhuma CAND selecionada. |
| R2 C1/C3/C5 | Proposta §§2/5/9: R2 único, ordem, original contínuo, corte distinto de revogação retroativa, consulta factual sem retry/retoma. | Nenhum novo lease, timeout seguro, cancelamento retroativo ou despacho por recovery. |
| D09/C6 | Proposta §9: confirmação pertinente causal anterior ao percurso, conteúdo/confiança e observação adequados. | Recibo não prova efeito/término nem verdade física da afirmação arquivada. |
| D10/C6 | Proposta §§5/8/9 e ME-09–ME-17: quarentena, transições pós-backup, invalidação persistente e reentrada humana. | Estado coerente/epoch não prova atualidade; sem D09 como autoridade/HA/failover. |
| V05-06/D2 | Proposta §§3/9: preservação distinta de retirada de capacidade; demonstrações cumulativas; sem destruição autorizada. | COMPROVADO não autoriza eliminação; prazo/condição R2 TBD conservados. |
| B-L §§2/4/8 | Proposta §8: sete cenários, dependências comuns, poderes transitivos, NAS não exclusivo e operador único. | Sem independência administrativa absoluta; cenário 6 não convertido silenciosamente em exclusão 7. |
| C2/C7 e âmbito DEV | Proposta §§2/9/11: prazo em A, versões, 25 nomes/JCS/UTF-8/Ed25519, rede interna/progbox DEV/Proxmox STAGING-PROD. | Não há bytes/schema/runtime/VM/software escolhidos. |

## Cobertura dos dez pontos do mandato

| Ponto | Local e resultado da revisão |
| --- | --- |
| 1. Git/documentos/preservação | Ambiente confirmado; hashes aprovados coincidem; comparação final e estados antes/depois em PRESERVATION.json. |
| 2. Definições | Proposta §3 distingue efeito, início, meio, capacidade, conteúdo inerte e confirmação terminal; ressalvas contra ampliação/redução normativa. |
| 3. Meios/poderes | MATRIX.md inclui SQL/alternativas, raw/filesystem/storage, trabalho antigo, cópias/clones, hipervisor/deploy/identidade/recovery e fecho transitivo. |
| 4. Último ponto | Coluna específica por via; camada nominal não é último ponto se houver escritor/caminho que a dispensa. |
| 5. Quatro obrigações | Proposta §5 e quatro verificações da matriz: novas entradas, trabalho aceite, persistência e autonomia analisados separadamente. |
| 6. Alternativas | Proposta §6, F-A–F-E alvo/storage/virtualização/evidência externa/dependência obrigatória, sem escolha tecnológica. |
| 7. Adversário | Proposta §§6/7/9: primeiro contorno, confiança mínima, prova necessária e contraexemplos verificáveis. |
| 8. Sete cenários simultâneos | Proposta §8: compatibilidade condicional, confiança sobrevivente e resultado não demonstrado para o conjunto. Exclusão 7 intacta. |
| 9. Estatutos | Proposta §10: requisito, hipótese, mecanismo, demonstração e impossibilidade/bloqueador separados. |
| 10. Decisões materiais | Proposta §10: nova raiz, poderes, prevenção de autonomia e redefinição do efeito explicitamente reservados, nenhuma adotada. |

## Achados e limites do parecer

Não foi identificada necessidade de alterar norma para descrever os requisitos e contraexemplos. A definição de efeito remete ao recurso/operação aprovados e não equivale a todo bit gravado ou toda corrupção; incerteza de classificação não é usada para declarar cobertura. Uma cópia só participa no ataque se existir capacidade alcançável para o efeito abrangido, mas identidade nominal diferente não elimina um clone suficiente do âmbito histórico.

A condição de intersetar todos os caminhos inclui administração do próprio controlo e meios futuros alcançáveis por restore/delegação. Isso é condição de completude por provar, não suposição de que a matriz enumerou o universo. Uma composição com pressupostos não provados continua candidata.

A confirmação terminal não promete apagar efeitos anteriores; exige que trabalho/capacidade antiga não produza efeitos depois do corte declarado. Preservar cópias e impedir a sua ativação são obrigações diferentes. Não se propõe destruição de backup ou rotação como apagamento de conhecimento já copiado.

**Conclusão da revisão:** entrega documental completa para o mandato, com fronteira conceptual definida por condições e limites; viabilidade realizável para o modelo completo não demonstrada. Com meio autónomo suficiente fora da imposição, garantia forte inviável nesse subcaso. O estudo não aprova uma alternativa nem resolve I-04. Não é parecer independente ou prova universal.

## Preservação e conferência documental

Antes da escrita guardou-se `/tmp/livenet-effect-boundary-before.json`: estado Git `--porcelain=v1 -uall`, HEAD/branch, digest do diff tracked e hashes dos ficheiros regulares enumerados por `git ls-files --cached --others --exclude-standard`. Destina-se a preservar trabalho anterior, não é auditoria/inventário operacional.

Só a pasta nova deste estudo e uma atualização no índice não normativo foram escritas. O índice anterior está em [CONTINUITY.before.md](CONTINUITY.before.md); os links dessa cópia conservam como base o local original docs/project/CONTINUITY.md. Normas, documentos aprovados, decisões, fontes e manifestos anteriores permanecem intactos. A análise CAND anterior não foi reescrita.

[PRESERVATION.json](PRESERVATION.json) contém a comparação final e o estado Git antes/depois. Fora do índice autorizado, os ficheiros regulares anteriores abrangidos mantêm os bytes; HEAD/branch/diff tracked e entradas anteriores do estado são preservados. Verificação de UTF-8 e referências locais dos documentos ativos novos, sem ensaios da aplicação. Limites: sem ignorados, metadados/ACL, estado interno Git, recursos externos ou snapshot atómico contra concorrência; não é D09/V05-06 ou prova de recovery.

Não foram encontradas AGENTS.md aplicáveis nos locais consultados. A falha inicial de bwrap foi contornada por execução autorizada fora do sandbox para leitura local e entrega documental. Não houve acesso operacional, código/schema/API, SQL, runners, testes/ensaios, alterações de serviços, containers, VMs, Proxmox/Synology, rede/storage/credenciais, deploy, commits, pushes ou merges.

## Saída

Proposta/matriz candidatas para revisão. Nenhuma decisão humana intermédia foi indispensável para terminar o estudo; qualquer adoção de nova raiz, poderes ou redefinição do efeito é decisão material própria antes de prosseguir nesse ponto. Recomenda-se manter modelo e bloqueios até proposta sustentada de fronteira obrigatória para todos os meios/poderes relevantes.

Aprovações anteriores e gates intactos; I-01/I-02/I-03 abertas, I-04/clone bloqueantes; autoridade R2 única, UNKNOWN/BLOCKED, C5, D09/D10/V05-06 preservados. Estados completos mantidos em PROPOSAL.md §11 e na continuidade.
