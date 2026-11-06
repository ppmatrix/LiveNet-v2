# CAND-1/2/3 — fontes, revisão e preservação

30/10/2026 · Europe/Lisbon · Revisão pelo autor; exclusivamente documentação e análise estática.

## Mandato, ambiente e documentos produzidos

Pedido humano atual «Registo de aprovação I-01–I-04 v0.1 e análise de viabilidade arquitetural»: fonte direta da aprovação documental em 30/10/2026 e da autorização de análise. Não se inventam ID de mensagem, assinatura ou aprovação arquitetural. [Ato próprio](../../decisions/bl-c4-i01-i04-v01-approval-20261030.md) identifica os bytes calculados: SHA-256 `dd307b7adde92cd4a3d2ea5ac17e59f5ca46010ae0598bb590bae8f18c8adfbb`.

Ambiente efetivamente acessível confirmado: `/home/paulo/projects/livenet-v2`, branch `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`. Quatro caminhos tracked modificados e untracked preexistentes. A listagem integral do estado Git antes/depois consta de PRESERVATION.json. Não se assume que HEAD contenha os documentos untracked nem se afirma acesso ao remoto GitHub ou igualdade com Windows.

[PROPOSAL.md](PROPOSAL.md) é candidata 0.1 nova: relatório executivo, análise por composição, matriz comparativa §8, comportamento perante falhas §7, critérios verificáveis §9 e alternativas para próxima decisão §10. Ato de aprovação I-01–I-04 não aprova este novo objeto. Não se escolheu uma CAND, fronteira, primitiva ou alteração normativa.

## Fontes e versões

Hashes anteriores à escrita. Fontes reutilizadas preservam os limites já recuperados nesta mesma conversa; não se reconstroem anexos/contratos ausentes, aprovações ou poderes atuais a partir de resumos. O índice anterior tem cópia literal em CONTINUITY.before.md.

| Fonte e alcance | SHA-256 |
| --- | --- |
| [I-01–I-04 v0.1; documento aprovado e composições, integral no contexto desta continuidade](../bl-c4-i01-i04-20261030/PROPOSAL.md) | `dd307b7adde92cd4a3d2ea5ac17e59f5ca46010ae0598bb590bae8f18c8adfbb` |
| [Revisão/fontes da entrega I-01–I-04; lida](../bl-c4-i01-i04-20261030/REVIEW.md) | `62487f60e6aa9c7356d4a4323134939ea196c21a548bc2200ec2ce560903ba81` |
| [C4 v0.2 aprovada; invariantes reutilizados](../bl-c4-consolidated-20261030/PROPOSAL.md) | `937bb32ab57fb0859d414e3ada9a11dbf963fdb19158d85a0e2c55cf019ff3ab` |
| [B-L v1.0 aprovada; limites e sete cenários reutilizados](../d09-06-bl-conditional-20261030/SPECIFICATION.md) | `e889171ffc1db17afe7e46b40a927f268ffafb70dfe8ceb9ef26aef3207f86a6` |
| [Contrato R2; C1–C7 relidos](../../auth-boot-02-r2.md) | `241f65858fdfcf8676a4fef4d251f1fdef95dfb2987d971b26cd2c993bfcbfc1` |
| [Contrato R1; D09/D10 §§11–12 relidos](../../auth-boot-02-r1.md) | `59c312d7dded14db9781d5e2a8e91acbce433b79a6d69427d3884f846e182eff` |
| [D2 aceite; V05-06 relido](../../../specifications/f0/dr07-retention-addendum.md) | `a996d78fff71002db47f2756836669fd3f096bff3074bae10c98c31afdaab818` |
| [DEV-05, relatório histórico 27/10/2026; integral relido](../../../../experiments/auth_boot_02_r2_dev05/REPORT.md) | `0143b1dcbe5155e8e3eb6f70946e87f7a692c9ee53174715b3ba63123212b490` |
| [Continuidade anterior; integral lido](../../../project/CONTINUITY.md) | `d13c3c9aaad9c4975474b1f202eaa03e77c1ce2c0912c8af81006b25b873923b` |

Os atos anteriores B-L/C4 e a revisão A–H são reutilizados com os seus estatutos históricos, sem reabertura. A decisão atual resolve apenas I-01–I-04 documental. Não se releram chats ou se executaram inventários/consultas Proxmox/Synology para esta análise.

DEV-05 é evidência histórica parcial: relata bypass de função/consumo, escrita administrativa, snapshot em dois ramos e clone vivo após corte local. Relata também contenção local em fixtures e dependências comuns de host/utilizador/administração. Esses resultados não são generalizados para uma instalação atual, não demonstram nova Q/T ou D09 e não foram repetidos. Uma expectativa de contraexemplo satisfeita por um teste histórico não prova a garantia de segurança.

As fontes públicas PostgreSQL citadas na I-01–I-04 v0.1 são contexto técnico da etapa anterior; não se fizeram novas alegações sobre capacidades atuais de produto nem nova seleção tecnológica. Esta entrega usa sobretudo os contratos internos, os contraexemplos documentados e dedução estática. Não se afirma capacidade instalada de uma extensão, primitiva, atuador ou hardware.

## Revisão de coerência e cobertura do mandato

| Pedido | Resposta e verificação documental |
| --- | --- |
| Registo e SHA-256 efetivo | Ato novo com caminho/versão/hash calculado, bytes aprovados intactos, aprovação exclusivamente documental. |
| Primeiro contraexemplo por CAND | CE-C comum tem prioridade; CE-1/CE-2/CE-2K/CE-3 explicitam via removível, poderes/ligação M, duplicação viva e restore conjunto. Não se confunde atacar realização incompleta com provar falsa uma obrigação ideal. |
| Poderes diretos/transitivos | Rotas condicionais de escrita, consola, reset, deploy, backup/restore e ativação; não se presume que leitura isolada execute o ataque ou que o executor tenha todas as credenciais. |
| Fronteira mínima/Q | Fronteira de todos os meios precede detalhar Q; passagem singular ligada K/L/J descrita como requisito de primitiva não demonstrada, sem algoritmo/código/API. |
| Falhas | Matriz §7 cobre concorrência, reentrada, rollback/savepoint, crash, restore, recovery e corte para cada CAND. |
| Observação independente | Distinção entre J e efeito sem ledger; diário/ack não observam bypass; poder sobre observador e ramos não observados impedem conclusão global. Sem segundo operador imposto. |
| D09/continuidade | Obrigação causal/contentual por CAND, sem confirmar eventos futuros ou usar recibo como efeito; R2 único e recovery sem rearmamento. |
| I-02/I-04 | CE-C refuta todas as localizações L perante clone gravável autónomo; corte terminal não é fecho de entrada ou morte de mediador. I-04 mantém bloqueio. |
| Classificação de viabilidade | Nenhuma viabilidade forte estabelecida no modelo completo; inviabilidade explícita quando capacidade CE-C subsiste; plausibilidade local é hipótese condicionada e não retirada silenciosa de ameaça. |
| Próxima decisão material | §10 delimita manutenção do bloqueio, eventual novo fundamento e eventual redução normativa de ameaça/efeito. Nenhuma adotada; recomendada fronteira obrigatória antes de CAND/Q. |

O argumento do clone é condicionado ao seu caráter integral, gravável e autónomo e à relevância do efeito no âmbito aprovado. Não constitui afirmação de que todo backup é atacável ou de que toda arquitetura futura é impossível. Em contrapartida, não basta desconhecer um clone para prometer ausência. A garantia universal não se obtém excluindo da análise um poder/meio que o modelo manda tratar.

Não se demonstra ausência global de bypass por logs locais ou por bloquear endpoint. A matriz separa R (requisito), H (hipótese), M (mecanismo possível) e D (demonstração efetiva no âmbito indicado). Nenhuma D nova de execução é alegada. A inviabilidade das composições sem fronteira adicional não autoriza um novo fundamento de confiança por omissão.

## Preservação, Git antes/depois e limites

Baseline temporária `/tmp/livenet-cand-feasibility-before.json`: hashes SHA-256 de ficheiros regulares Git enumerados por `git ls-files --cached --others --exclude-standard`, estado `--porcelain=v1 -uall`, HEAD/branch e digest de `git diff --binary HEAD` antes da escrita. Não é inventário operacional ou auditoria geral.

Único caminho anterior alterado: `docs/project/CONTINUITY.md`, índice não normativo, com registo da aprovação/última etapa e encaminhamento da análise. A cópia anterior é literal. Os restantes caminhos escritos são o ato novo e esta pasta nova. Propostas aprovadas, fontes, relatórios e manifestos anteriores ficam inalterados. HEAD/branch/diff tracked e todas as entradas anteriores do estado Git são comparados no fim.

[PRESERVATION.json](PRESERVATION.json) conserva os resultados e listagens antes/depois, hashes dos aprovados e da entrega. Comparação cobre ficheiros regulares Git enumerados; exclui ignorados, metadados/ACL, estado interno `.git`, recursos externos e snapshot atómico contra concorrência. Não é D09, V05-06, prova de backups ou de continuidade operacional.

Não foram encontradas instruções AGENTS.md aplicáveis na árvore ou ascendentes consultados. A falha inicial bwrap foi contornada por execução autorizada fora do sandbox para leituras locais e escrita documental. Nenhum acesso a serviços ou interfaces operacionais, SQL, runners, testes/ensaios, deploy, alteração de código/schema/API, VMs/containers, rede/storage/credenciais, commits, pushes ou merges. Validação de UTF-8/referências/hashes é conferência de entrega documental.

## Estado final

Aprovação I-01–I-04 v0.1 registada; proposta de viabilidade candidata. Nenhuma CAND escolhida, I/GAP/H encerrada, norma ou gate alterado. I-04 e clone gravável continuam bloqueadores até demonstração válida. D09, D10, V05-06, UNKNOWN/BLOCKED, C5, R2 único e estados anteriores preservados.

A análise reversível autorizada foi concluída antes de apresentar a decisão material. A adoção de uma composição para a garantia forte necessita de proposta humana própria sobre fronteira/poderes e exclusão dos meios antigos. A presente entrega não espera por aprovação editorial nem presume aprovação de arquitetura.
