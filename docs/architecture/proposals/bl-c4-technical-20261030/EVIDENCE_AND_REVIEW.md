# B-L/C4 — fontes, decisões e verificação documental

30/10/2026 · Europe/Lisbon · Revisão técnica documental pelo agente; não é auditoria independente, atestado UTC ou demonstração operacional.

## Entrega e estatutos

| Resultado | Estatuto e alcance |
| --- | --- |
| [Registo da aprovação B-L v1.0](../../decisions/d09-06-bl-v1-approval-20261030.md) | Ato documental autorizado pelo pedido humano atual; identifica a versão aprovada por hash sem a editar. |
| [Índice de continuidade](../../../project/CONTINUITY.md) | Atualizado sob autorização expressa; continua navegação não normativa. A [versão anterior](CONTINUITY.before.md) conserva os bytes anteriores. |
| [Proposta técnica C4 0.1](PROPOSAL.md) | Candidata para revisão: mediação/barreira/contexto/início, falhas, alternativas, recuperação e evidência necessária. Não aprovada nem implementada. |
| [Preservação](PRESERVATION.json) | Comparação específica dos documentos anteriores, mudanças autorizadas, estado Git e integridade da entrega; não prova a arquitetura. |

O pedido humano atual fornece expressamente a aprovação documental B-L v1.0 em 30/10/2026 e autoriza o seu registo, a atualização do índice e esta preparação técnica. Não se procurou novamente um «sim», não se reabriu a preferência B-L e não se confundiu aprovação de documento com evidência técnica ou autorização executável assinada.

A aprovação resolve a pendência documental da especificação anterior por ato sucessor. O ficheiro aprovado conserva SHA-256 `e889171ffc1db17afe7e46b40a927f268ffafb70dfe8ceb9ef26aef3207f86a6`, incluindo o cabeçalho histórico «bytes não aprovados». Esse cabeçalho é temporalmente anterior à decisão; não é removido ou reescrito. Os manifestos, fontes e relatórios da entrega original continuam íntegros como evidência do seu momento.

## Fontes reutilizadas e efetivamente consultadas

| Fonte | Utilização e limite |
| --- | --- |
| Pedido humano atual nesta conversa | Aprovação e autorização diretas, data e âmbito: registo documental, índice e proposta técnica; sem implementação/ensaios/infraestrutura. Não se inventa ID de mensagem ou assinatura. |
| `docs/architecture/proposals/d09-06-bl-conditional-20261030/SPECIFICATION.md` | Versão aprovada, lida/identificada por hash antes de escrever; funções, cenários, C4/C5/D10 e limites. Cópias local/remota coincidentes. |
| `docs/project/CONTINUITY.md` anterior; `SOURCES_AND_REVIEW.md` da entrega B-L | Recuperação do estado e referências; antiga pendência resolvida por novo ato, sem alterar o relatório antigo. |
| `RECOVERED_SOURCES.json` do pacote B-L | Textos D09-05/06 e sete cenários D09-03 recuperados na etapa precedente, já conservados. Reutilizados sem reler chats ou tentar anexos temporários novamente. |
| `docs/architecture/auth-boot-02-r2.md`, C1–C7; R1 §§11–12; D2 V05-06 | Fontes normativas já lidas na etapa imediatamente anterior e reutilizadas com os mesmos hashes documentais. Não se afirma nova auditoria integral nem se alteram esses documentos. |
| `experiments/auth_boot_02_r2_dev05/REPORT.md` | Relido o resultado histórico: fence local, função direta sem consumo externo, bypass administrativo, clone vivo gravável, resposta perdida e limites. Não se repetiram testes. |
| DEV-04/05 JSON e DEV-08 PROTOCOL/BOUNDARY/VALIDATION da continuidade existente | Evidência/análise anteriormente consultadas para janelas de perda da guarda, consumo irreversível e clone. Não são ensaios novos nem mecanismos aprovados por esta referência. |
| Pesquisa documental RG1–RG7 em docs/experiments | Confirmadas referências aos estados por demonstrar. A pesquisa não fornece aqui enumeração normativa autónoma completa; não se inventam definições, novas equivalências ou renumeração. Os critérios desta proposta não se apresentam como fecho individual RG. |

DEV-05 distingue 34 ensaios novos de dois contraexemplos DEV-04 históricos. Passar um teste que espera um contraexemplo não demonstra segurança universal. A chamada direta produziu efeito sem consumo externo; a escrita administrativa produziu payload sem ledger; o clone manteve epoch antigo e escrita depois do corte do original. Isto fundamenta a necessidade de observar iniciação/efeito e impor todos os caminhos, não apenas contar recibos. Os factos são dos relatórios/artefactos, sem reprodução nesta etapa.

## Fontes primárias públicas confrontadas

Consultadas em 30/10/2026 para limitar as afirmações genéricas sobre opções PostgreSQL 16, versão histórica dos laboratórios. Não identificam a versão instalada atual nem validam configuração LiveNet.

| Fonte primária | Facto documental e inferência de desenho |
| --- | --- |
| [PostgreSQL 16 — Role Attributes](https://www.postgresql.org/docs/16/role-attributes.html) | Superuser contorna controlos de permissões, salvo LOGIN. Inferência: uma fronteira baseada apenas em ACL/função não contém esse administrador se ele fizer parte da ameaça. Não se atribui ao produto promessa de conter root/storage adversarial. |
| [PostgreSQL 16 — Explicit Locking](https://www.postgresql.org/docs/16/explicit-locking.html) | Locks normais podem ser libertados por rollback a savepoint; advisory locks dependem do uso cooperante e têm semânticas distintas por sessão/transação. Inferência: lock isolado não é registo de início irreversível nem mediação universal. O detalhe de savepoint precisa de cenário próprio, sem tratar «lock até commit» como frase universal. |
| [PostgreSQL 16 — Sequence Manipulation](https://www.postgresql.org/docs/16/functions-sequence.html) | Obter número de sequência não o devolve por abort; isso não fornece por si mapeamento de consumo por aprovação, proteção de continuidade ou garantia de estado externo após crash. Inferência: uma sequência não deve ser apresentada como solução completa L/C4. |

Estas fontes não selecionam implementação SQL/extension, mecanismo de fencing ou storage. Não houve SQL executado, instalação de extensão, experimento ou recomendação de aquisição. ALT-C é inferência candidata do agente sobre as obrigações e limites, não facto de produto ou decisão já aprovada.

## Coerência e decisões materiais ainda abertas

| Aspeto | Concretização na proposta | Ainda pendente |
| --- | --- | --- |
| R2 → W → barreira → início | K0–K7 distinguem contexto inerte, admissão, oportunidade irrevogável, preservação prévia, disponibilização e J observado. | Mecanismo real de vínculo, persistência e início único sem redispatch, incluindo crash. |
| Executor comprometido | M/T/L e confiança fora do alcance transitivo coberto; entrada no alvo obrigatória. | Localização lógica concreta/base confiada e impossibilidade de contorno administrativo. |
| SQL/replay/rollback/savepoint | Cobertura por via, incluindo contagem de iniciações abortadas e a mesma sessão. | Prova de mediação, marcador não reversível e observador completo. |
| C5/UNKNOWN | Pré-requisito ausente bloqueia; original contínuo pode prosseguir após condições satisfeitas; consulta não retoma. | Implementação que demonstre continuidade singular, sem bearer token ou recriação do contexto. |
| Recovery e sete cenários | Fundamento sobrevivente e controlo que bloqueia identificados por cenário, com operador único. | Conteúdo/continuidade suficientes, invalidação antiga e solução material concreta. |
| Clone integral | Efeito no clone continua falha; impossibilidade de copiar, se alegada, exige demonstração perante poderes aprovados. | Bloqueador forte não resolvido. Não se aprovou redução do domínio nem O3. |
| Alternativas | ALT-A/B/C/D comparadas; ALT-C recomendada apenas para aprofundamento documental. | Adoção da arquitetura M/T/L, mecanismo de continuidade/corte e qualquer alteração de garantia são decisões próprias. |

As lacunas não são ocultadas por uma declaração de «fencing eficaz». A propriedade K3–J contém uma obrigação importante ainda sem mecanismo selecionado. Esta proposta torna-a revisável, não prova que a obrigação está satisfeita. Não se alegam exatamente uma vez, HA automática, autoridade D09 alternativa ou cancelamento retroativo por revogação.

## Verificação, âmbito e preservação

Checkout real confirmado em progbox, branch main, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`, com alterações tracked/untracked anteriores. A pasta Windows é cópia documental. Não se encontraram instruções AGENTS.md aplicáveis nos locais pesquisados. Antes da edição, os hashes locais/remotos da especificação aprovada e do índice coincidiram.

Capturaram-se os hashes dos Markdown/JSON existentes em docs/experiments e o estado Git remoto para comparação documental específica. Só CONTINUITY.md é uma mudança autorizada num caminho anterior; a sua cópia anterior é comparada com o hash de origem. A decisão de aprovação e a pasta desta proposta são novas. Não se altera norma, fonte, relatório ou manifesto histórico. A comparação final detalhada em PRESERVATION.json exclui apenas estes novos caminhos e a atualização autorizada do índice, verificando separadamente o original aprovado, HEAD/branch, estado Git e diff tracked.

O âmbito não inclui todos os ficheiros do projeto, `.git` interno, ACL, modos, atime, recursos externos ou uma captura atómica contra concorrência. É verificação de entrega pelo agente, não D09 independente. Links relativos/UTF-8 e integridade local/remota da entrega são conferidos sem ensaiar a arquitetura.

CONTINUITY.before.md é cópia literal arquivada: as suas referências relativas conservam como base o local original docs/project/CONTINUITY.md. Não se alteram esses links para tornar o arquivo navegável à custa dos bytes preservados; a conferência do arquivo usa essa base de origem.

Não se repetiu inventário do laboratório, não se contactaram interfaces Proxmox/Synology ou bases e não houve scanner. SSH serviu apenas leitura documental/estado Git e entrega no repositório de desenvolvimento. Não foram criados recursos físicos, serviços, contas ou processos de laboratório. Não há recursos de terceiros a limpar; preservam-se documentos e processos transitórios terminados normalmente.

## Resumo para revisão

A primeira tarefa fica concretizada por ato sucessor com hash e atualização autorizada do índice, conservando B-L v1.0. A segunda entrega proposta técnica consolidada 0.1, com alternativa preferida para análise e decisões ainda abertas. Nenhuma decisão material foi tomada para conseguir encerrar a redação; por isso não foi necessária intervenção intermédia.

Revisão humana seguinte: avaliar se ALT-C e as obrigações K3–J oferecem base suficiente para aprofundamento documental, mantendo a garantia forte e o bloqueador do clone. Se for necessário retirar poder de cópia/escrita ou mudar a base confiada para avançar, apresentar essa decisão material expressamente antes de a adotar. A preparação documental não autoriza implementação ou ensaios posteriores.

P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados/bloqueantes; H02–H12/GAP-001/002 bloqueantes; RG1–RG7/D09/V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial. Sem commits, pushes, implantação ou atribuição física.
