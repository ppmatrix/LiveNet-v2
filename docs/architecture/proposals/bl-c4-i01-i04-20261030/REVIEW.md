# C4 — aprovação v0.2 e aprofundamento I-01–I-04: revisão da entrega

30/10/2026 · Europe/Lisbon · Atividade exclusivamente documental.

## Atos e documentos distintos

O pedido humano atual «Continuação após aprovação humana C4 v0.2» declara a aprovação em 30/10/2026 e o hash exato. O [registo novo de decisão](../../decisions/bl-c4-v02-approval-20261030.md) fixa esse objeto, preserva os bytes e distingue a autorização de continuação documental. Não se deduz aprovação de um parecer do agente, não se inventa identificador de mensagem e não se solicita nova aprovação C4 ou B-L.

A [proposta nova I-01–I-04](PROPOSAL.md), candidata 0.1, não fica aprovada por esse ato. Concretiza três composições e o papel de Q antes de J, sem produzir código, schema, API, produto escolhido, autoridade concorrente ou recurso operacional. Os termos «indivisível», «irreversível» e «contexto real» designam propriedades cuja realização exige prova, não capacidades existentes.

## Fontes locais reutilizadas e consultadas

Os hashes abaixo são anteriores a qualquer escrita desta etapa. O índice foi depois atualizado e a sua [cópia anterior literal](CONTINUITY.before.md) conserva o hash de origem. A leitura B-L/sequências históricas beneficia do conteúdo já recuperado nesta mesma conversa; não se repete inventário nem recuperação de chats.

| Fonte e alcance | SHA-256 antes da escrita |
| --- | --- |
| [C4 v0.2, aprovada; §§1–11](../bl-c4-consolidated-20261030/PROPOSAL.md) | `937bb32ab57fb0859d414e3ada9a11dbf963fdb19158d85a0e2c55cf019ff3ab` |
| [Revisão A–H, I-01–I-04; integral](../bl-c4-consolidated-20261030/REVIEW_DOCUMENTAL_V02.md) | `ab18bc709de7b7350ab4186ac51c92691939bb038b3d83316a6277ef5bbb2473` |
| [B-L v1.0 aprovada, reutilizada; invariantes e sete cenários](../d09-06-bl-conditional-20261030/SPECIFICATION.md) | `e889171ffc1db17afe7e46b40a927f268ffafb70dfe8ceb9ef26aef3207f86a6` |
| [Ato B-L preservado; integral](../../decisions/d09-06-bl-v1-approval-20261030.md) | `36713930a8c503d4dad049bd6f2831f6477393e4c2e4062b7b9fc1bcce5e1146` |
| [R2 C1–C7 consultados; R2-CONSOLIDATION-1](../../auth-boot-02-r2.md) | `241f65858fdfcf8676a4fef4d251f1fdef95dfb2987d971b26cd2c993bfcbfc1` |
| [D09/D10 consultados; §§11–12](../../auth-boot-02-r1.md) | `59c312d7dded14db9781d5e2a8e91acbce433b79a6d69427d3884f846e182eff` |
| [D2 aceite, V05-01–06 consultados](../../../specifications/f0/dr07-retention-addendum.md) | `a996d78fff71002db47f2756836669fd3f096bff3074bae10c98c31afdaab818` |
| [Continuidade anterior; integral](../../../project/CONTINUITY.md) | `8bebe2747288e050c85635195415deac51e5705744030afad7b3ea4073104df7` |

A aprovação C4 coincide com o hash humano `937bb32ab57fb0859d414e3ada9a11dbf963fdb19158d85a0e2c55cf019ff3ab`; B-L conserva `e889171ffc1db17afe7e46b40a927f268ffafb70dfe8ceb9ef26aef3207f86a6`. Fontes históricas D09-05/06/03 e as limitações de proveniência são as da revisão A–H, sem novos atos reconstruídos. DEV-04/05/08 são contraexemplos históricos referidos no encadeamento aprovado; não foram executados ou revalidados agora.

## Fontes primárias públicas e limite das inferências

Consultadas nesta etapa para verificar limites de primitivas PostgreSQL 16, versão histórica de referência. Não se determina a versão/configuração instalada nem a exequibilidade dos recursos atuais.

| Fonte primária | Facto documental e uso limitado |
| --- | --- |
| [Explicit Locking, §§13.3.1 e 13.3.5](https://www.postgresql.org/docs/16/explicit-locking.html) | Semântica de savepoint, natureza cooperante dos advisory locks e reaquisição pelo dono. A inferência de desenho é que um lock isolado não fornece Q ou mediação completa. |
| [Role Attributes, §22.2](https://www.postgresql.org/docs/16/role-attributes.html) | Alcance do superuser perante permissões. A inferência é não declarar uma ACL como contenção desse poder coberto. |
| [Sequence Manipulation, §9.17](https://www.postgresql.org/docs/16/functions-sequence.html) | Distinção entre não devolução por abort e persistência/uso externo após crash. A inferência é não apresentar uma sequência como L/C4 completo. |

A página oficial Continuous Archiving também foi aberta como contexto geral de recuperação; não é utilizada para afirmar propriedades das composições. Não se descarregou software ou contactou interfaces de laboratório. Nenhuma das fontes afirma a existência da primitiva Q proposta ou aprova extensão. CAND-1/2/3 são hipóteses do agente para revisão, não factos de produto.

## Conferência de coerência e evolução técnica

| Tema | Resultado da revisão documental pelo autor |
| --- | --- |
| Aprovação | C4 v0.2 registada por ato sucessor, sem editar o aprovado ou revisão histórica. |
| I-01 | Atribuição L, passagem Q e J distinguidos. Q pode perder disponibilidade antes de J; não se promete atomicidade com efeito. Ligação singular real e impossibilidade de duplicar K continuam pendentes. |
| Três composições | L no domínio R2, diário M sem redispatch e persistência própria T comparados com fluxo, confiança, crash e limitações; nenhuma adotada. |
| I-02 | Matriz de vias/poderes inclui SQL privilegiado, raw, reentrada na mesma sessão, transação antiga, trabalho pendente, restore/clone e alcance transitivo. Não confunde dono único de M com mediação T. |
| D09 e eventos | Conteúdo crítico prévio confirmado antes de progressão; classificação/catálogo novos não aprovados. Se uma transição adicional exigir confirmação pré-J, a candidata terá de a satisfazer sem rearmar Q. Eventos futuros não fabricados. |
| C2/C3/C5 | Prazo em A, ordem única e não revogação retroativa; consultas factuais; só original contínuo; nenhuma retoma/retry automática. |
| I-03 | Suficiência de conteúdo, confiança sobrevivente e continuidade externas discriminadas sem schema/retenção. D09/V05-06 distintos e cumulativos no respetivo âmbito. |
| I-04 | Entrada fechada, término e exclusão de meios são coisas distintas. Corte terminal e clones permanecem bloqueadores, sem reduzir efeito ao endpoint ou excluir poderes. |
| Sete cenários | Conservados, com falha/poder, fundamento sobrevivente e bloqueio; operador único e exclusão total sem independência absoluta prometida. |
| Decisões materiais | Locais de L, primitiva Q, base confiada M/T e atuador de corte são propostas próprias antes de adoção; nenhuma foi necessária para terminar a comparação documental. |

Esta é revisão pelo autor, sem segundo revisor independente ou demonstração operacional. Nenhuma linha encerra RG/H/GAP/I ou muda gate. O progresso é análise verificável e comparação de falhas; não se declara I-01–I-04 resolvidas por escrever requisitos.

## Git, preservação e limites

Checkout confirmado em `/home/paulo/projects/livenet-v2`, branch `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`. Quatro tracked modificados e untracked anteriores preservados. O snapshot comparativo temporário `/tmp/livenet-c4-approved-followup-before.json` guarda hashes dos ficheiros regulares Git enumerados, estado `--porcelain=v1 -uall`, HEAD/branch e digest do diff tracked, antes de qualquer escrita.

Único caminho preexistente alterado: índice não normativo CONTINUITY.md, cuja cópia literal anterior está nesta entrega. Atualizaram-se o estado corrente/última aprovação e a referência à próxima atividade; a narrativa de etapas antigas é identificada como histórica. Ato de aprovação e pasta de análise são caminhos novos. Normas, propostas aprovadas, revisões e manifestos anteriores ficam inalterados.

[PRESERVATION.json](PRESERVATION.json) regista estado antes/depois, hashes e comparação: fora do índice, os ficheiros regulares anteriores abrangidos mantêm os bytes; diff tracked, branch e HEAD conservados. O âmbito exclui ignorados, metadados/ACL, conteúdo externo, estado interno `.git` e snapshot atómico contra concorrência. Não é D09 ou V05-06 e não compara Windows/remoto.

A execução local usou permissão fora do sandbox devido à falha de inicialização bwrap, para leituras e escrita documental autorizadas. Não se repetiram auditorias ou inventários. Sem implementação, SQL, ensaios/testes, serviços/containers, VM/Proxmox/Synology, rede/storage/credenciais, deploy, commits, pushes ou merges. Conferências de texto, referências e hashes não são ensaios da aplicação.

## Estado para a próxima revisão

C4 v0.2 aprovada documentalmente; nova proposta I-01–I-04 candidata para revisão. Recomenda-se rever a decomposição e as condições de refutação sem selecionar uma composição. A análise reversível continua autorizada; adoção material ou alteração normativa requer decisão específica antes de prosseguir nesse ponto. I-04/clone integral gravável continuam bloqueadores técnicos.

P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados/bloqueantes; H02–H12 e GAP-001/002 pendentes/abertos e bloqueantes conforme os registos; RG1–RG7, R2 D09 e V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial. Sem mudança de gate ou de qualquer aprovação anterior.
