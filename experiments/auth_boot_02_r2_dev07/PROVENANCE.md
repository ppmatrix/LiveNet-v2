# R2-DEV-07 — proveniência e preservação

Data editorial: 2026-10-27 (Europe/Lisbon), sem atestado UTC. Autorização:
pedido humano explícito nesta conversa para executar revisão documental
crítica/adversarial da candidata DEV-06 em progbox. A referência à conversa
6adfbb17-6350-83ed-9daa-650bf8ad109a foi tratada como contexto; o pedido atual
fornece âmbito suficiente e não foi necessário reconstruir respostas ausentes.

## Acesso, instruções e baseline anterior à escrita

SSH autenticado como paulo para /home/paulo/projects/livenet-v2. A primeira
tentativa no ambiente restrito não resolveu progbox; a repetição com acesso
autorizado funcionou. Nenhuma falha de acesso foi interpretada como prova
sobre a arquitetura. As leituras remotas foram feitas diretamente nos ficheiros.

Não foram encontrados AGENTS.md no repositório nem nos ancestrais /, /home,
/home/paulo e /home/paulo/projects. Não foram encontradas instruções AGENTS.md
na árvore local usada para a entrega. HEAD: 647179c928888adfeef0f69f582fd13c5fc17350.
O checkout remoto já continha quatro ficheiros tracked modificados e numerosos
untracked, incluindo experiências anteriores. Não foi limpo, revertido ou criado
outro checkout. A ausência remota de experiments/auth_boot_02_r2_dev07 foi
verificada antes da escrita. A pasta local de entrega também era nova.

Baseline remota capturada antes de qualquer escrita DEV-07:

- 9136 entradas regulares/symlinks, incluindo ignorados.
- SHA-256 do inventário: 3e0bf94fae92a4cb415db9e8b62065e7e7f77893ac005efe6bf276377b2b53cc.
- SHA-256 do diff binário face a HEAD: 21b7778033dde56d142558cdeac78808f35437cdbc8e03fead49ad288c445df2.

Procedimento: percorrer sem seguir diretórios symlink, excluir diretórios .git;
por caminho relativo guardar modo lstat, tamanho e SHA-256 dos bytes, ou dos bytes
do destino textual do symlink. Serializar o mapa por Python JSON com sort_keys=True
e separators=(',',':'), depois calcular SHA-256. A segunda captura exclui apenas a
nova pasta DEV-07. Conservar e comparar também HEAD, estado Git porcelain v1 com
-uall (filtrando somente a pasta nova) e diff binário face a HEAD. A baseline Git
foi conservada em memória durante a revisão; não é um novo registo autoritativo.

Uma primeira tentativa de codificar o comando em JavaScript falhou antes da
chamada remota por função ausente. Uma leitura do mapa integral excedeu o limite
de saída e não pôde ser interpretada; foi repetida como agregado. Ambas as
ocorrências foram somente de recolha, sem escrita remota e sem ensaios.

## Fontes primárias diretamente lidas

Foram lidos integralmente os quatro Markdown DEV-06; C1–C7 e rastreabilidade R2;
as secções D09/D10 de R1; REPORT/README DEV-02 a DEV-05 e os JSON finais,
inspecionando chaves de estado, contagens, flags, measurements, hashes de fontes
e saídas históricas dos testes. O stdout/stderr dos dois testes DEV-04 preservados
em baseline_dev04 no JSON DEV-05 também foi lido. Não se executaram nem importaram
módulos dos laboratórios. Saídas antigas não são novas observações operacionais.

| Caminho relativo ao repositório | SHA-256 dos bytes lidos |
| --- | --- |
| docs/architecture/auth-boot-02-r1.md | 59c312d7dded14db9781d5e2a8e91acbce433b79a6d69427d3884f846e182eff |
| docs/architecture/auth-boot-02-r2.md | 241f65858fdfcf8676a4fef4d251f1fdef95dfb2987d971b26cd2c993bfcbfc1 |
| docs/architecture/auth-boot-02-r2-traceability.md | 6c239c812e0fc125fff10a1d5712a380f653adc021586ecca2d3910ec6d3d1f2 |
| experiments/auth_boot_02_r2_dev06/ARCHITECTURE.md | 74a969798ca05797efebe0c976f67090da6edd3f277d7baf3089a38b876ce69a |
| experiments/auth_boot_02_r2_dev06/VALIDATION.md | 1385c773a17acc76d6b57cf9686df9257a18fa7cef045b9e99a5e5097f7348f5 |
| experiments/auth_boot_02_r2_dev06/REPORT.md | 33e9d06dbe4f386724407e7b40bdcbdda469804751132743a7bb34e2856016e2 |
| experiments/auth_boot_02_r2_dev06/PROVENANCE.md | acf08dbd3e88ae6c7d1aca5d92421aead7e754d0b96634f6d815f64f7e201242 |
| experiments/auth_boot_02_r2_dev02/REPORT.md | 6e1e80e4f5a9f7745f6cad5a97c0216e5855a78b3748d68542cafa3ae84f0a50 |
| experiments/auth_boot_02_r2_dev02/README.md | 6efac690b59d55ee14ab0be7f87ae847c0dd6ee5bab7000b4eee47b2c6dd1433 |
| experiments/auth_boot_02_r2_dev02/evidence.json | 97ff5371dbbee0c4f61ee618e7afe78753b1f262228c9fac31371c681e8182c0 |
| experiments/auth_boot_02_r2_dev03/REPORT.md | 4a97611db342d718bbfab0339d253ee3ce6b04276ee757b06faa2a541fb02aeb |
| experiments/auth_boot_02_r2_dev03/README.md | 169392abcfe5e1fc06313ad26792e650b054926cafa8fd289c0c29d7fdd67f6e |
| experiments/auth_boot_02_r2_dev03/evidence.json | 2e9d3f79168c22c9ab0ce5f3d55b267b905f6e89100c0e5407ae6a880776d5b8 |
| experiments/auth_boot_02_r2_dev04/REPORT.md | 6d26a20af3a54ea3b7547956233b2965c3434fe14c66cc75668ada66c91728e3 |
| experiments/auth_boot_02_r2_dev04/README.md | 9145d9bd4dd79c6fdbbb16524979aabfcea8f4c1e9cbbab7a22937371ab8716e |
| experiments/auth_boot_02_r2_dev04/evidence.json | 588dae06c03aedd04a24152adc88ece248c3eb88f9218322a150cb08fc701f81 |
| experiments/auth_boot_02_r2_dev05/REPORT.md | 0143b1dcbe5155e8e3eb6f70946e87f7a692c9ee53174715b3ba63123212b490 |
| experiments/auth_boot_02_r2_dev05/README.md | 13a39f932bfa99645eea0abfdcfd4fe5ed03c014a4a9099b62d0a682b319bfe2 |
| experiments/auth_boot_02_r2_dev05/evidence.json | b586f80075259ac09fe61e85442913dee07e7acc5bbc7b3e12c2b420049f7647 |

Os hashes históricos DEV-02 a DEV-05 e contratos coincidem com os que DEV-06
registou para essas fontes. Isso fixa bytes, não certifica veracidade operacional,
autorização ou independência D09. Intermediários evidence.initial.json e outros
artefactos anteriores permanecem preservados e não foram promovidos a finais.

Referências centrais verificadas: DEV-02 measurements.split_brain_counterexample
e target_counterexample; DEV-03 full_clone_counterexample e privileged_bypass;
DEV-04 counterexample_guard_loss_sql_begins_after_fence e
counterexample_guard_loss_old_commit_after_fence; DEV-05
clone_survives_local_cessation_counterexample, historical_snapshot_counterexample,
external_consumption_still_trusted_broker, admin_bypass_counterexample,
anchor_loss_before_sql_fixed_locally, anchor_loss_before_commit_drained e
local_cessation_receipt (todos dentro de measurements).

## Fontes externas confrontadas documentalmente

Consultadas em 2026-10-27, apenas para verificar a fundamentação genérica de
DEV-06; sem escolha de produto ou validação de configuração LiveNet:

- [Linux kernel — Persistent Reservations](https://docs.kernel.org/block/pr.html): distingue modos de reserva por iniciador e preempção com aborto. Isto não demonstra cobertura de disco independente; essa limitação é inferência da revisão.
- [ClusterLabs — Fencing, §§8.1–8.3](https://clusterlabs.org/projects/pacemaker/doc/3.0/Pacemaker_Explained/html/fencing.html): descreve corte de energia/fabric e dependências de canal/energia. Não prova inventário LiveNet nem independência de custódios.
- [tpm2-tools — tpm2_create](https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_create.1/): documenta atributos/políticas de criação de objetos. Não é prova de que o ambiente LiveNet possui hardware não clonável ou impede relay.
- [RFC 8915, §8.6](https://www.rfc-editor.org/rfc/rfc8915.html#section-8.6): autenticação NTS não elimina ataques de atraso. Orçamento UTC e bootstrap continuam obrigações específicas por justificar.

As conclusões F01–F12 são análise técnica deste agente sobre fontes e premissas,
não conclusões atribuídas a esses projetos externos.

## Âmbito e independência

Entrega nova: REPORT.md, FINDINGS.md, VALIDATION.md e PROVENANCE.md em
experiments/auth_boot_02_r2_dev07/, com cópia local para leitura. O remoto é a
origem da revisão; a cópia local não é declarada checkout Git. Os links para
contratos e experiências anteriores resolvem no repositório remoto; a cópia
local pode não conter todas as fontes. Links entre os quatro documentos da
entrega resolvem em ambos os locais.

Trata-se de revisão técnica por agente, no mesmo acesso concedido para leitura e
entrega. Não houve auditor humano independente, auditoria externa, segregação
administrativa nova ou atestado independente dos resultados. A palavra
independente nos critérios futuros designa uma obrigação por cumprir.

A preservação compara conjunto de caminhos, conteúdo, modo e tamanho no âmbito
inventariado. Exclui .git interno, atime, metadados/ACL/xattrs, diretórios vazios,
recursos externos e bases operacionais não acedidas. Leituras podem atualizar
atime. Não se reivindica preservação universal nem uma captura atomicamente
consistente com atividade concorrente. O agregado não permite localizar uma
alteração sem outro inventário; é verificação do agente, não D09.

Só se criaram documentos; as verificações de texto, hashes e âmbito não são
ensaios da arquitetura. Sem testes, SQL, serviços, instalações, infraestrutura,
alterações a código/contratos/artefactos anteriores, commits ou push. Mantêm-se
AUTH-03/F02/G2/G4 fechados, GAP-001/002 abertas e DEV-09B não autorizada.

## Comparação após entrega

A segunda captura remota confirmou as **9.136 entradas preexistentes idênticas**,
com o mesmo agregado de conteúdo/modo/tamanho/conjunto de caminhos. HEAD,
estado Git fora de DEV-07 e diff binário face a HEAD permaneceram iguais à
baseline. Não foram detetadas alterações ou adições fora da nova pasta no
âmbito inventariado.

A pasta DEV-07 contém exatamente os quatro Markdown indicados. A leitura UTF-8,
a ausência de caracteres de substituição e a resolução das referências relativas
foram verificadas no remoto. Esta secção foi acrescentada apenas ao novo
PROVENANCE.md; a transferência final é seguida de nova comparação de preservação
e de hashes locais/remotos dos quatro documentos. As verificações são de entrega
documental, sem execução dos ensaios descritos nos documentos.

