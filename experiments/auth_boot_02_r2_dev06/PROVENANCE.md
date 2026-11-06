# Proveniência e verificação documental R2-DEV-06

Data de elaboração: 2026-10-27. Autorização: pedido humano nesta sessão para
executar R2-DEV-06 exclusivamente como estudo arquitetural/documental em progbox.
Conversa referenciada: Planeamento das lacunas, ID
`6adfbb17-6350-83ed-9daa-650bf8ad109a`; consultada por leitura.
A mensagem humana «Autorizo R2-DEV-06» confirma o âmbito documental descrito no
pedido atual; referências de conteúdo do assistente não foram reconstruídas.

## Acesso, instruções e estado antes de escrever

Acesso SSH verificado como utilizador paulo ao caminho
`/home/paulo/projects/livenet-v2`. O estado inicial continha alterações tracked,
untracked e ficheiros ignorados; não era um checkout limpo.
HEAD: `647179c928888adfeef0f69f582fd13c5fc17350`.

Foram procurados AGENTS.md no repositório e nos ancestrais
`/`, `/home`, `/home/paulo` e `/home/paulo/projects`.
Nenhum aplicável foi encontrado. A pesquisa em projetos irmãos encontrou
instruções fora do âmbito LiveNet; não foram aplicadas.

A primeira tentativa SSH dentro do acesso restrito não resolveu progbox;
a repetição com acesso autorizado confirmou o repositório. Uma leitura inicial
falhou por quoting antes de ler/escrever; foi refeita. Uma tentativa de capturar
o inventário integral excedeu o limite de saída, sem escrita remota; foi substituída
pela impressão digital agregada abaixo. Estas ocorrências não executaram testes.

## Fontes locais primárias

Foram lidos C1–C7 e rastreabilidade R2, o consolidado R1 (incluindo D08–D10),
REPORT/README e as evidências JSON finais DEV-02 a DEV-05.
A leitura dos JSON inspecionou contagens, flags, measurements, saídas históricas
e pressupostos. Não executou os módulos Python dos laboratórios.

| Caminho relativo ao repositório | SHA-256 antes da entrega |
| --- | --- |
| `docs/architecture/auth-boot-02-r1.md` | `59c312d7dded14db9781d5e2a8e91acbce433b79a6d69427d3884f846e182eff` |
| `docs/architecture/auth-boot-02-r2-traceability.md` | `6c239c812e0fc125fff10a1d5712a380f653adc021586ecca2d3910ec6d3d1f2` |
| `docs/architecture/auth-boot-02-r2.md` | `241f65858fdfcf8676a4fef4d251f1fdef95dfb2987d971b26cd2c993bfcbfc1` |
| `experiments/auth_boot_02_r2_dev02/README.md` | `6efac690b59d55ee14ab0be7f87ae847c0dd6ee5bab7000b4eee47b2c6dd1433` |
| `experiments/auth_boot_02_r2_dev02/REPORT.md` | `6e1e80e4f5a9f7745f6cad5a97c0216e5855a78b3748d68542cafa3ae84f0a50` |
| `experiments/auth_boot_02_r2_dev02/evidence.json` | `97ff5371dbbee0c4f61ee618e7afe78753b1f262228c9fac31371c681e8182c0` |
| `experiments/auth_boot_02_r2_dev03/README.md` | `169392abcfe5e1fc06313ad26792e650b054926cafa8fd289c0c29d7fdd67f6e` |
| `experiments/auth_boot_02_r2_dev03/REPORT.md` | `4a97611db342d718bbfab0339d253ee3ce6b04276ee757b06faa2a541fb02aeb` |
| `experiments/auth_boot_02_r2_dev03/evidence.json` | `2e9d3f79168c22c9ab0ce5f3d55b267b905f6e89100c0e5407ae6a880776d5b8` |
| `experiments/auth_boot_02_r2_dev04/README.md` | `9145d9bd4dd79c6fdbbb16524979aabfcea8f4c1e9cbbab7a22937371ab8716e` |
| `experiments/auth_boot_02_r2_dev04/REPORT.md` | `6d26a20af3a54ea3b7547956233b2965c3434fe14c66cc75668ada66c91728e3` |
| `experiments/auth_boot_02_r2_dev04/evidence.json` | `588dae06c03aedd04a24152adc88ece248c3eb88f9218322a150cb08fc701f81` |
| `experiments/auth_boot_02_r2_dev05/README.md` | `13a39f932bfa99645eea0abfdcfd4fe5ed03c014a4a9099b62d0a682b319bfe2` |
| `experiments/auth_boot_02_r2_dev05/REPORT.md` | `0143b1dcbe5155e8e3eb6f70946e87f7a692c9ee53174715b3ba63123212b490` |
| `experiments/auth_boot_02_r2_dev05/evidence.json` | `b586f80075259ac09fe61e85442913dee07e7acc5bbc7b3e12c2b420049f7647` |

Os hashes fixam os bytes lidos, não aprovam esses bytes nem provam os resultados
operacionais. Evidências DEV-02/03/04 mantêm 36/37/63 testes respetivamente.
DEV-05 contém 34 novos e dois da baseline DEV-04. Todos são resultados históricos.
`evidence.initial.json` e outros intermediários ficam preservados, sem os
promover a resultados finais nem somar contagens entre execuções.

Referências decisivas no JSON DEV-05:
`measurements.clone_survives_local_cessation_counterexample`,
`measurements.historical_snapshot_counterexample`,
`measurements.anchor_loss_before_sql_fixed_locally`,
`measurements.anchor_loss_before_commit_drained`,
`measurements.local_cessation_receipt`,
`measurements.admin_bypass_counterexample` e
`measurements.external_consumption_still_trusted_broker`.
Estas observações fundamentam a distinção entre fence local, capacidade
distribuída, consumo e efeito usada no estudo.

## Fontes externas e estatuto das conclusões

Fontes primárias públicas, lidas em 2026-10-27, estão ligadas junto das afirmações
em ARCHITECTURE S1–S3 e VALIDATION §3: Linux kernel, ClusterLabs, tpm2-tools e
RFC 8915. Não se testaram produtos, versões ou capacidades de hardware.
A comparação e a arquitetura candidata são análise/recomendação R2-DEV-06;
não são decisões herdadas desses projetos nem escolhas previamente aprovadas.

## Baseline de preservação

Capturada antes de criar a pasta remota DEV-06, cuja ausência foi verificada.
Inventário: **9132 ficheiros regulares/symlinks**, incluindo ignorados.
Para cada caminho relativo, recolheu-se modo lstat, tamanho e SHA-256 do
conteúdo, ou do destino textual para symlink, sem seguir diretórios symlink.
O mapa foi serializado por Python JSON com sort_keys=True e separators=(',',':')
e reduzido a SHA-256; uma segunda captura usa o mesmo procedimento e exclui
apenas a pasta nova e diretórios .git.

- Inventário SHA-256: `e69f719a1ed5555849641f577bf8c64e36266d22e0a1c5feb40bda8f4d55d82f`.
- Estado Git detalhado, sem DEV-06: `df5e6016029a22df9b563bfc15183af08105585baea60f470d907bf8cafcf4ef`.
- Diff binário face a HEAD: `21b7778033dde56d142558cdeac78808f35437cdbc8e03fead49ad288c445df2`.
- HEAD: `647179c928888adfeef0f69f582fd13c5fc17350`.

A impressão agregada deteta diferenças no conjunto inventariado, mas não conserva
a lista integral de hashes nem permite localizar uma diferença a partir do digest.
Não é evidência D09 independente. Exclui conteúdo interno de .git, atime,
metadados de diretórios, diretórios vazios, ACL/xattrs, recursos externos e bases
operacionais não acedidos. Leituras podem atualizar atime. Nenhum inventário
do repositório demonstra preservação universal de recursos fora desse âmbito.

## Âmbito da entrega

Apenas REPORT.md, ARCHITECTURE.md, VALIDATION.md e este PROVENANCE.md na pasta
nova `experiments/auth_boot_02_r2_dev06/`, com cópia local de entrega no workspace
LiveNet. A cópia local não é declarada checkout Git nem origem autoritativa.
Nenhuma escrita em artefactos anteriores é necessária.
Verificações limitam-se a conteúdo/referências, integridade e âmbito documental.
Não são testes de segurança nem validação da arquitetura candidata.

## Resultado da comparação final

Após a criação dos quatro documentos no remoto, a segunda captura confirmou
**9.132 entradas preexistentes com impressão digital idêntica**, incluindo
conteúdo/modo/tamanho e conjunto de caminhos. HEAD, estado Git fora de DEV-06 e
diff binário face a HEAD conservaram os valores acima. Não foram observadas
alterações nem adições fora da pasta nova no âmbito inventariado.

O conjunto novo contém exatamente os quatro Markdown indicados. Codificação
UTF-8 e referências relativas entre documentos foram verificadas sem erros.
Esta comparação é verificação do agente no mesmo domínio de acesso; não é
validação independente da candidata nem atestado de cessação operacional.

AUTH-03/F02/G2/G4 fechados; GAP-001/002 abertas. Sem testes novos, SQL,
provisionamento, instalações, alteração de contratos/código operacional,
commits, push ou DEV-09B. A proposta R2-DEV-07 e todas as decisões técnicas
pendentes continuam recomendações, sem autorização implícita.

