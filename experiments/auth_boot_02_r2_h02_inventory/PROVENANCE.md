# H02 — fontes e preservação

Data editorial: 2026-10-27, Europe/Lisbon, sem atestado UTC.
Âmbito: preparação documental no repositório `progbox:/home/paulo/projects/livenet-v2`.

## Fonte humana e fontes do repositório

A fonte autorizativa é o pedido explícito desta sessão: H01 aprovada com O1 para estudo; O3 pode complementar sem aprovação; H02–H12 pendentes. Não foi necessário recuperar conteúdo adicional da conversa referenciada: o pedido atual fixa integralmente o âmbito. O preview limitado é contexto, não prova de dados físicos ou instruções adicionais.

| Fonte | Caminho relativo à raiz do repositório | Localizador e alcance de leitura/uso |
| --- | --- | --- |
| S01 | experiments/auth_boot_02_r2_dev08/DECISIONS.md | Leitura integral; H01/H02/H03–H12 e O0–O4; estados históricos preservados. |
| S02 | experiments/auth_boot_02_r2_dev08/REPORT.md | Leitura integral; inventário não fechado e limites da proposta. |
| S03 | experiments/auth_boot_02_r2_dev08/BOUNDARY.md | Leitura integral; K01–K06, domínio D/R*, W01–W13 e candidata externa. |
| S04 | experiments/auth_boot_02_r2_dev08/CUSTODY.md | Leitura integral; domínios funcionais e poderes transitivos; nomes pendentes. |
| S05 | experiments/auth_boot_02_r2_dev08/LAB_FEASIBILITY.md | Tabelas de recursos/zonas e condições lidas; capacidades não verificadas e ausência de prontidão. |
| S06 | experiments/auth_boot_02_r2_dev08/PROVENANCE.md | Secções de fontes, acesso e preservação lidas; relatos de etapas anteriores não são verificações atuais. |
| S07 | experiments/auth_boot_02_r2_dev07/REPORT.md | Leitura integral; veredito e bloqueadores. |
| S08 | experiments/auth_boot_02_r2_dev07/FINDINGS.md | Leitura integral; P1–P5/F01–F12, natureza de cópias e independência. |
| S09 | experiments/auth_boot_02_r2_dev06/REPORT.md | Leitura integral; consequências dos contraexemplos e candidata condicional. |
| S10 | experiments/auth_boot_02_r2_dev06/ARCHITECTURE.md | Alternativas, candidata, domínio e obrigações de prova lidos; saída conjunta parcialmente truncada, sem alegação de releitura integral. Nenhuma URL ali citada foi aberta. |
| S11 | experiments/auth_boot_02_r2_dev05/REPORT.md | Leitura integral; clusters/clone/roles, limpeza histórica e limites. |
| S12 | experiments/auth_boot_02_r2_dev05/evidence.json | Leitura seletiva como JSON: flags e cinco medições clone/snapshot/chamada direta/bypass/recibo, sem execução/import de código do projeto. |
| S13 | docs/architecture/auth-boot-02-r1.md | Pesquisa e leitura §§11–12 (linhas 310–380); D09/D10, VM de A, independência/recuperação. |
| S14 | docs/architecture/auth-boot-02-r2.md | Leitura integral; C1–C7 e limites da primeira classe UPDATE. |
| S15 | docs/architecture/auth-boot-02-r2-traceability.md | Leitura inicial até linha 75; GAP-001/002 abertas e limites. |
| S16 | docs/architecture/environments.md | Política/tabelas iniciais e pesquisa de backup/ambientes; leitura parcial, sem alegação de catálogo operacional. |
| S17 | docs/architecture/platform-runtime.md | Tabelas de implementação/runtime e propostas lidas; leitura documental, não estado de serviços. |
| S18 | docs/architecture/decision-register.md | Pesquisa seletiva; G4D-01 (VM exclusiva sem NIC) e referências de ambientes. |
| S19 | docs/specifications/f0/f0-baseline.md | Pesquisa seletiva; STAGING Proxmox previsto. |
| S20 | docs/specifications/f0/inventory-physical-model.md | Secções iniciais §§1–4 lidas: tipos, identificadores/relações/proveniência. Ficheiro extenso com saída truncada; não se reivindica leitura integral. É especificação, não catálogo de ativos. |

Os SHA-256 integrais das 20 fontes constam de `preservation.baseline.json:sources`. Hash integral fixa bytes, não significa leitura semântica integral. Apenas estas fontes lidas/focalizadas sustentam o inventário; pesquisa de nomes em docs/infra não certifica inexistência de inventário noutro local. Não se leram novas fontes externas, URLs, hipervisores ou bases.

FD significa declaração documental, não comprovação atual. Inferências e propostas são identificadas; lacunas são NC. Não existe auditoria humana/administrativa independente realizada por este agente.

## Acesso e preservação

Não foram encontrados AGENTS.md na pesquisa da árvore remota nem nos ancestrais `/`, `/home`, `/home/paulo`, `/home/paulo/projects` e raiz do repositório. Na árvore local de preparação e ancestrais consultados também não foram encontrados. A nova pasta remota não existia na baseline; não se sobrepõem ficheiros.

O checkout já apresentava quatro tracked modificados e numerosos untracked. A baseline desta preparação contém **9.151 ficheiros regulares/symlinks**, incluindo ignorados e excluindo diretórios `.git`. O valor é desta captura, não reaproveita contagens DEV-08. HEAD: `647179c928888adfeef0f69f582fd13c5fc17350`.

Método: percurso de ficheiros sem seguir diretórios symlink; para ficheiros regulares SHA-256 dos bytes; para symlinks hash do destino textual; por entrada guardar em memória caminho relativo POSIX, modo lstat, tamanho e hash. Digest agregado do mapa com JSON `sort_keys=True`, separadores compactos, UTF-8. Guardar contagem/digest, HEAD, SHA-256 do estado Git porcelain v1 `-uall`, SHA-256 de `git diff --binary HEAD` e hashes das fontes. A baseline persistida é compacta, não contém o mapa integral por caminho.

A comparação final usa o mesmo método, excluindo apenas a pasta nova desta entrega e `.git`; filtra exclusivamente os novos caminhos da pasta no estado Git. Igualdade do agregado confirma preservação de caminhos/modos/tamanhos/bytes no âmbito comparado, sem atribuir qual ficheiro mudou em caso de divergência. Comparar também fontes, HEAD e diff. `preservation.json` regista o resultado e hashes da entrega; os Markdown são verificados como UTF-8 e links relativos no repositório remoto, sem ensaios do projeto.

Limites: não cobre `.git` interno, atime/mtime, ACL/xattrs, diretórios vazios, serviços ou recursos externos. Não é snapshot atómico nem prova D09; atividade concorrente pode exigir investigação se houver divergência. Os manifestos não se autoatestam nem demonstram independência administrativa.

A documentação é criada por patches numa nova pasta local e transferida com criação exclusiva para a mesma pasta relativa do remoto. Apenas documentos/JSON de evidência de preservação são acrescentados. A cópia local é de consulta e não é declarada checkout Git; alguns links a fontes históricas só resolvem no remoto.

A primeira tentativa SSH restrita não resolveu progbox; acesso autorizado permitiu a leitura. Uma pesquisa inicial sofreu erro de quoting e foi corrigida; uma primeira captura de saída foi truncada e não serve de baseline, tendo sido repetida em formato compacto. Nenhuma dessas ocorrências alterou fontes ou foi usada para inferir capacidade do ambiente.

Sem comandos administrativos, consultas a hipervisores/VMs/storage, testes, SQL, scans, provisionamento, alterações operacionais, commits ou push. Sem alteração a ficheiros existentes/contratos/modelo de ameaça. H02–H12 pendentes; O3 não aprovado; AUTH-03/F02/G2/G4 fechados; GAP-001/002 abertas; DEV-09B não autorizada.

