# R2-DEV-08 — fontes, acesso e preservação

Estado: PROPOSTA NÃO APROVADA. Data editorial: 2026-10-27, Europe/Lisbon; não é atestado UTC. A autorização procede do pedido humano explícito nesta sessão para executar R2-DEV-08 exclusivamente documental em progbox e do seguimento «Prossegue». Não há aprovação humana das escolhas H01–H12 por inferência dessa autorização.

## Fontes e estatuto de cada afirmação

As afirmações históricas são factos **dos relatórios/JSON**, sem reprodução dos ensaios. As consequências de impossibilidade condicional, o protocolo P/Q, zonas e critérios E são **inferências e propostas DEV-08**. Nomes de custódios, recursos não localizados, alteração de domínio/ameaça, mecanismo de corte, parâmetros e formatos são **decisões ou verificações pendentes**. Uma fonte declarar sucesso de um teste não torna verdadeira a propriedade universal.

| Referência | Leitura realizada e uso |
| --- | --- |
| [DEV-07 REPORT](../auth_boot_02_r2_dev07/REPORT.md), [FINDINGS](../auth_boot_02_r2_dev07/FINDINGS.md), [VALIDATION](../auth_boot_02_r2_dev07/VALIDATION.md), [PROVENANCE](../auth_boot_02_r2_dev07/PROVENANCE.md) | Quatro documentos lidos diretamente no remoto. F01–F12, crítica V01–V15 e AC01–AC10 orientam a especificação; veredito histórico mantido. |
| [DEV-06 ARCHITECTURE](../auth_boot_02_r2_dev06/ARCHITECTURE.md), [VALIDATION](../auth_boot_02_r2_dev06/VALIDATION.md) | Definição de efeito físico, domínio de clone, P1–P5, candidata externa, C1–C7 e critérios prévios. Leitura direta remota. |
| [Contrato R2](../../docs/architecture/auth-boot-02-r2.md), [rastreabilidade](../../docs/architecture/auth-boot-02-r2-traceability.md) | Texto C1–C7 e autoridade/limites da aprovação documental lidos; nenhuma alteração. Aprovação de baseline não aprova schemas/bytes/implantação DEV-08. |
| [R1](../../docs/architecture/auth-boot-02-r1.md), §§11–12 | D09: conteúdo/continuidade/confirmação independente; D10: A único Proxmox, recuperação/segregação e ausência de HA automática. Secções lidas diretamente; hash fixa o ficheiro inteiro, sem alegar releitura integral de todo R1. |
| [DEV-05 REPORT](../auth_boot_02_r2_dev05/REPORT.md), [README](../auth_boot_02_r2_dev05/README.md), [evidence](../auth_boot_02_r2_dev05/evidence.json) | Relatório e limites lidos; JSON analisado como dados, especialmente measurements e flags. Clone/snapshot físicos de dados, não snapshot VM/memória demonstrado. |
| [DEV-02 evidence](../auth_boot_02_r2_dev02/evidence.json), [DEV-03 evidence](../auth_boot_02_r2_dev03/evidence.json), [DEV-04 evidence](../auth_boot_02_r2_dev04/evidence.json) | Inspeção direta das chaves, flags e medições pertinentes. Não foram importados módulos, executados runners ou interpretadas saídas antigas como ensaios novos. |
| [Ambientes](../../docs/architecture/environments.md), [runtime](../../docs/architecture/platform-runtime.md), [F0](../../docs/specifications/f0/f0-baseline.md) | Política LAN-only, Proxmox como ambiente previsto, dependências de runtime/backup. Pesquisa documental de referências a Proxmox/hardware em docs; sem inventário operacional. |

[sources.json](sources.json) contém caminhos e SHA-256 de 18 fontes, confrontados com a baseline antes da entrega. Os hashes fixam bytes; não certificam veracidade operacional, aprovação, independência ou completude. Os links para fontes no repositório resolvem no remoto; a cópia local de leitura pode não conter todo R1/runtime/F0. Links entre os oito documentos DEV-08 resolvem nos dois destinos.

Localizadores JSON decisivos: DEV-02 `measurements.split_brain_counterexample` (duas admissões com referência copiada) e `target_counterexample` (uma admissão/dois UPDATE diretos); DEV-03 `full_clone_counterexample`, `privileged_bypass`, `administrative_segregation`; DEV-04 `counterexample_guard_loss_sql_begins_after_fence` e `counterexample_guard_loss_old_commit_after_fence`; DEV-05 `clone_survives_local_cessation_counterexample`, `historical_snapshot_counterexample`, `external_consumption_still_trusted_broker`, `admin_bypass_counterexample` e `local_cessation_receipt`.

Em DEV-05, original epoch 2/value 0 e clone epoch 1/value 1 coexistem com `distributed_fencing=false`; chamada direta tem claims 0/value 1; bypass administrativo tem value 1/effects vazios/claims 0. O recibo local regista zero backends antigos naquele recurso, com process_cessation_proven e distributed_takeover_confirmed falsos. Os JSON finais DEV-02–05 têm executable=false e authenticated_utc=false; DEV-04/05 têm d09_independence_demonstrated=false. Estas flags não foram alteradas nem verificadas por nova execução.

A conversa `6adfbb17-6350-83ed-9daa-650bf8ad109a` foi consultada por read_thread, dez turnos solicitados. O serviço devolveu cinco turnos disponíveis, sem cursor adicional: inclui «Autorizo R2-DEV-08» e relatos DEV-06/07, mas respostas do assistente continuam como referências de conteúdo. Não se reconstruiu conteúdo ausente nem se trataram anexos/resumos como ordens adicionais. O pedido atual define o âmbito suficiente. Não foram recuperadas capacidades físicas concretas dessa leitura.

Consulta pública em 2026-10-27: [Linux kernel — reservas persistentes](https://docs.kernel.org/block/pr.html), para semântica genérica de restrição por iniciador e preempção com aborto; [RFC 8915 §8.6](https://www.rfc-editor.org/rfc/rfc8915.html#section-8.6), para limite da autenticação perante atraso assimétrico. Nenhuma fonte prova configuração LiveNet. Consulta ao guia Proxmox em `https://pve.proxmox.com/pve-docs/pve-admin-guide.html` devolveu HTTP 403 e não foi usada como prova de funcionalidade instalada. Não houve escolha/aquisição de produto.

## Acesso, instruções e baseline

SSH autenticado como paulo. HEAD inicial: `647179c928888adfeef0f69f582fd13c5fc17350`. O checkout já tinha quatro tracked modificados (`backend/migrations/env.py`, dois documentos F0 e `frontend/README.md`) e numerosos untracked, incluindo experiências anteriores. Não foi feito reset, limpeza, branch, commit ou push.

Não foram encontrados AGENTS.md na árvore remota nem nos ancestrais `/`, `/home`, `/home/paulo`, `/home/paulo/projects`. Na árvore local não foram encontrados AGENTS.md; verificações dos ancestrais até `C:/` também não encontraram instruções aplicáveis. A pasta remota DEV-08 não existia; a pasta local foi criada nova pelos patches de documentação.

A primeira tentativa SSH no ambiente restrito não resolveu progbox; a repetição com acesso autorizado funcionou. A inicialização de PowerShell demorou e registou erro do fornecedor de filesystem; os processos terminaram, e as operações de ficheiros/SSH prosseguiram por cmd. Algumas tentativas iniciais de codificação/quoting de leitura falharam antes de qualquer escrita remota. Não foram usadas para inferir propriedades da arquitetura. Não ficaram serviços ou processos de laboratório criados por DEV-08.

Antes de criar DEV-08, uma captura por leitura inventariou **9.140 ficheiros regulares/symlinks**, incluindo ignorados. A diferença face aos 9.136 registados antes de DEV-07 inclui os quatro Markdown DEV-07 agora preexistentes; a baseline atual, não o contador histórico, rege esta comparação.

- Inventário SHA-256: `81d00cf2ca39dbefcefa2978179d6dadc32e67a0bd5183d2a6a14b4e7149fdd3`.
- Diff binário face a HEAD SHA-256: `21b7778033dde56d142558cdeac78808f35437cdbc8e03fead49ad288c445df2`.
- [preservation.baseline.json](preservation.baseline.json): mapa completo dos caminhos com modo lstat, tamanho e SHA-256, HEAD, estado Git detalhado e digest do diff.

A captura percorre sem seguir diretórios symlink; inclui o destino textual dos symlinks como bytes de comparação; exclui diretórios `.git`. Serializa o mapa com JSON sort_keys e separadores compactos para o agregado. Só depois da captura se criou a nova pasta e se gravou a baseline. Nenhum script operacional ou ficheiro Python foi acrescentado ao projeto; os utilitários de leitura/hashing/transferência funcionaram apenas como comandos de entrega documental.

## Verificação final e alcance

A comparação final volta a inventariar o repositório com o mesmo método, excluindo apenas a nova pasta DEV-08 e `.git`. Compara todos os caminhos, modos, tamanhos e hashes, deteta adições externas, e confronta HEAD, estado Git porcelain v1 com -uall filtrando exclusivamente DEV-08, e diff binário face a HEAD. [preservation.json](preservation.json) conserva o resultado dessa verificação, juntamente com integridade UTF-8, referências internas e hashes da entrega.

A preservação não cobre `.git` interno, atime, diretórios vazios, ACL/xattrs, metadados de diretórios, serviços, bases ou meios externos não acedidos. Não é snapshot atómico contra atividade concorrente nem confirmação D09 independente. O checkout remoto é o âmbito da baseline; a pasta local é cópia de leitura, não declarada checkout Git. A entrega local/remota é comparada por hashes.

Recursos próprios desta etapa: nova pasta documental e processos transitórios de leitura/transferência/verificação. Os documentos e manifestos são a entrega preservada; nenhum cluster, VM, volume, conta, chave ou serviço foi criado. Não se apagaram recursos históricos ou ficheiros preexistentes. Não houve testes, SQL, instalação, provisionamento, alteração operacional, código operacional ou alterações aos contratos R1/R2.

Esta é especificação/revisão técnica pelo mesmo agente e acesso da entrega; não é auditoria externa nem demonstra independência humana/administrativa. H01–H12 permanecem pendentes. AUTH-03/F02/G2/G4 fechados; GAP-001/002 abertas; DEV-09B não autorizada.

## Resultado da comparação após entrega

A captura posterior à transferência confirmou as **9.140 entradas preexistentes idênticas**: zero caminhos removidos, zero alterações de conteúdo/modo/tamanho e zero adições fora de DEV-08. HEAD, estado Git anterior e diff binário permaneceram iguais; o digest agregado do inventário conserva o valor da baseline. Esta atualização do novo documento é seguida de outra comparação pelo mesmo método, registada em preservation.json.

Os oito Markdown passaram verificação de leitura UTF-8, ausência de caracteres de substituição e referências relativas existentes no remoto. Os 18 hashes das fontes coincidiram com a baseline. Estas verificações avaliam a entrega documental, sem testes da arquitetura. A transferência final dos manifestos para a cópia local é acompanhada de comparação dos hashes locais/remotos de todos os ficheiros da entrega.
