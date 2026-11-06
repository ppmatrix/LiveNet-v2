# LiveNet v2 — proposta técnica C4 consolidada

Versão candidata 0.2 · 30/10/2026 · Europe/Lisbon.
Estado: **CONSOLIDADA PARA REVISÃO FINAL; NÃO APROVADA, NÃO IMPLEMENTADA E SEM GARANTIA DEMONSTRADA**.

## 1. Objeto e conclusão técnica

Consolidar a disponibilização **R2 → D09 → barreira → alvo**, incorporando a [proposta técnica 0.1](../bl-c4-technical-20261030/PROPOSAL.md) e o [protocolo candidato 0.1](../bl-c4-protocol-20261030/PROTOCOL.md). Esta é a entrada de revisão consolidada desta etapa; os dois documentos anteriores conservam os seus bytes e a análise detalhada histórica. Não é nova baseline normativa.

A [B-L v1.0](../d09-06-bl-conditional-20261030/SPECIFICATION.md) já está aprovada documentalmente em 30/10/2026 pelo [ato posterior](../../decisions/d09-06-bl-v1-approval-20261030.md). O cabeçalho histórico de pendência não reabre essa aprovação. Os bytes aprovados conservam SHA-256 `e889171ffc1db17afe7e46b40a927f268ffafb70dfe8ceb9ef26aef3207f86a6`.

**Conclusão:** a admissão durável R2 e a confirmação independente D09 são necessárias, mas não bastam para C4. A solução candidata precisa também de memória de uso irrevogável, vínculo a uma única continuação real e mediação obrigatória no alvo até término. Um consumo único pode acompanhar duas entradas; um controlo local pode ser duplicado num clone. Nenhuma dessas lacunas é resolvida por redigir o requisito.

Mantém-se a recomendação de aprofundar documentalmente ALT-C: mediação confiada M, barreira obrigatória T e memória de uso L. Não se adota a sua arquitetura, localização ou primitiva. O clone integral gravável autónomo adversarial mantém inviável a garantia forte nos pressupostos atuais. Aprovar esta proposta documental não elimina esse bloqueador nem demonstra C4.

## 2. Autoridade, âmbito e fronteiras

Requisitos estabelecidos: [R2 C1–C7](../../auth-boot-02-r2.md), [R1 D09/D10](../../auth-boot-02-r1.md), B-L v1.0 e gates existentes. O pedido humano autoriza preparação documental autónoma; decisões arquiteturais materiais e alterações de gates requerem intervenção própria. Não se pede nova aprovação B-L.

A primeira classe analisada permanece o UPDATE fixo de laboratório indicado na proposta anterior. Não se generaliza a DDL, Alembic, administração ou efeitos externos. R2 é autoridade única, independente das bases e storage do executor. D09 ocupa domínio distinto de R2 e execução. B-L exige conteúdo crítico, confiança e recuperação suficientes fora da dependência exclusiva do NAS, incluindo dependências indiretas de boot, identidade e configuração.

Um operador humano, com poderes funcionalmente segregados. O comprometimento total dos seus poderes e de toda a recuperação está fora da garantia. Uma credencial limitada que alcança consolas, reset, deploy, storage ou recuperação de todos os componentes não pode ser reclassificada silenciosamente nessa exclusão. Não se exige segundo operador, hardware novo ou terceiro.

Progbox é exclusivamente DEV; STAGING/PROD em VMs Proxmox; LiveNet apenas interno ao laboratório. Nenhuma atribuição de nós, VMIDs, volumes, contas, IPs, produtos, protocolos, chaves, schemas, RPO/RTO ou retenções é feita nesta etapa. Não se pressupõe suficiência dos recursos existentes.

## 3. Funções e poderes candidatos

| Função | Responsabilidade | Limite de confiança a demonstrar |
| --- | --- | --- |
| R2 | Avaliar em A e confirmar conjuntamente consumo, vínculos, ordem e evidência essencial local. | Executor não altera autoridade, política, estado, confiança ou recuperação. Sem autoridade concorrente. |
| W/D09 | Preservar conteúdo suficiente e confirmar pertinência/continuidade independentemente. | Não admite, não devolve consumos, não prova início ou commit. Origem e conteúdo não falsificáveis pelo executor. |
| M | Conduzir o fluxo original e deter a sessão/transação protegida da operação fixa. | Fora de todos os poderes transitivos do executor comprometido; não aceita SQL arbitrário nem decide elegibilidade. |
| T | Mediar toda entrada capaz de efeito no alvo e conservar exclusão até término relevante. | Executor não remove a guarda, assume escritor alternativo ou escreve raw. Verificar não cria nova ordem de admissão. |
| L | Conservar o compromisso irrevogável de uso ligado à admissão e contexto exatos. | Fora do rollback/savepoint do efeito e da regressão por restore coberto. Não cria aprovação ou fila redispatchável. |
| V | Observar início real, mutações, término e atuação do corte. | Evidência não depende apenas da alegação do componente verificado; observa também efeito sem ledger. |

M/T/L são funções de análise, não serviços ou VMs criados. Podem vir a coexistir ou ser separados se a solução demonstrar as propriedades. A sua base confiada e a atribuição de poderes continuam decisão material. Contas, conexões ou nós diferentes não provam independência perante poder transitivo comum.

## 4. Semântica consolidada e notação

K é a continuação viva original ligada ao recurso/geração, executor/encarnação e sessão/transação reais. É preparada de forma inerte antes da decisão R2, para a admissão confirmar vínculos já determinados. Um ID, PID, certificado ou nonce copiável não demonstra singularidade de K. A preparação não inicia o corpo da operação protegida.

J é a primeira entrada aceite no corpo dessa operação no alvo; entrada seguida de erro ou rollback conta. Chamadas recusadas antes do corpo não são J. Mutação, commit/abort e resposta são factos diferentes. O compromisso L gasta a oportunidade antes de J; J não volta a consumir nem devolve a aprovação. Distinguir estes dois pontos elimina a ambiguidade entre «reservar» e «iniciar».

P0–P6 abaixo reutilizam a notação analítica do protocolo anterior. Não são enums, campos ou estados de API aprovados. O intervalo UTC de C2 é referido como `[L_UTC,U_UTC]` apenas nesta exposição, para não o confundir com a função L; não se altera a notação contratual nem os 25 nomes de campos.

## 5. Sequência causal e condições de disponibilização

| Posição | Facto e controlo exigidos | Consequência de falha |
| --- | --- | --- |
| P0 — contexto inerte | M/T ligam K ao pedido sem capacidade de efeito. | K perdido é abandonado; não se reconstrói permissão de estado local. |
| P1 — admissão R2 | Em A, avaliação serializada com revogações, epochs e política; commit conjunto de consumo, vínculos, ordem e evidência. | Sem confirmação durável/autenticada no percurso original: UNKNOWN/BLOCKED. Pode existir consumo real sem resposta. |
| P2 — compromisso L | A única oportunidade fica irrevogavelmente associada à admissão/K exatos. | Não basta para iniciar; reserva incerta não autoriza repetição ou recuperação de tarefa. |
| P3 — D09 confirmado | W preserva conteúdo crítico já existente de P1/P2 e confirma relação, completude pertinente e continuidade. | Conteúdo parcial, digest isolado, ack ausente/perdido, divergência ou vínculo errado bloqueiam disponibilização. |
| P4 — barreira satisfeita | M/T verificam cumulativamente P1–P3, K vivo original, vínculos reais, continuidade, exclusão e gates aplicáveis. | Armamento não é token entregue ao executor nem trabalho persistido para redispatch. Perda de K deixa a oportunidade gasta. |
| P5 — J | T aceita no máximo uma entrada do fluxo original no corpo protegido. | Replay, concorrência e reentrada, inclusive na mesma sessão, recusados antes do corpo. Zero efeito não devolve direito. |
| P6 — término | T/M mantêm proteção até commit/abort e término de trabalho relevante; factos observados são preservados. | Commit/resposta incertos: sem retry, retoma ou compensação automática usada como substituto da reconciliação. |

Dependência candidata: `P1 → P2 → P3 → P4 → J → término`. K precede a decisão final que o vincula. A precedência deve ser causalmente demonstrável; timestamps entre máquinas não a provam. Não há atomicidade presumida entre R2, L, W e alvo. Todos os gates operacionais atuais permanecem bloqueantes; esta sequência não habilita execução real.

A condição documental de abertura é a conjunção de admissão confirmada, compromisso único, confirmação D09 pertinente, continuidade original, mediação efetiva e gates satisfeitos. Não basta apresentar a conjunção como valores fornecidos pelo cliente: o controlo confiado precisa de verificá-la no percurso real. Também deve impedir que a mesma verificação seja usada por duas continuações entre P4 e J. Essa ligação permanece obrigação de prova, sem primitiva selecionada.

D09 confirma conteúdo prévio antes da disponibilização. Início e resultado são preservados depois de observados, com confirmação antes de qualquer progressão que dependa desses novos factos. Não se exige confirmar antecipadamente um commit futuro, nem se dispensa a preservação prévia por ainda não existir resultado. Consulta ou retransmissão documental não pode emitir capacidade de execução.

C2 mantém `issued_at <= not_before < expires_at`, `expires_at - issued_at <= 900 segundos`, e elegibilidade em A apenas com `L_UTC >= not_before` e `U_UTC < expires_at`. Tempo/continuidade desconhecidos impedem admissão. O prazo não passa para entrega, início ou commit. C3 conserva ordem autoritativa única: revogação anterior a A recusa; posterior não cancela retroativamente admissão; pendente não é eficaz; ordem desconhecida bloqueia novas admissões.

## 6. Obrigações de prova e critérios de refutação

Estes localizadores editoriais não criam gates ou substituem RG1–RG7/GAP existentes. São uma decomposição verificável da candidata, sem resultados de ensaios.

| Obrigação | Evidência futura necessária | Contraexemplo que a refuta |
| --- | --- | --- |
| Consumo/vínculos únicos | Estado R2 durável, concorrência e ordem com revogação, continuidade após incidente. | Aprovação reutilizada, vínculos trocados ou estado restaurado tratado como livre. |
| Anterioridade independente | Relação causal R2/L/W/K e conteúdo recuperável correspondente antes de P4/J. | J sem confirmação prévia pertinente; assinatura válida de conteúdo/contexto diferente aceite. |
| Compromisso irreversível | Uso por aprovação/K fora do rollback do payload, com continuidade recuperável. | Abort/savepoint/crash/restore devolve oportunidade; leitura de «gasto» concede despacho. |
| Ligação singular P4–J | Controlo real que não duplica o fluxo, mesmo sob duplicação de transporte, callbacks ou chamadas na mesma sessão. | Um compromisso L e duas entradas J, mesmo com um só commit ou nenhum efeito. |
| Mediação completa | Cobertura de SQL direto, funções alternativas, privilégios cobertos, raw, sessões antigas e pendências. | Mutação fora de T, incluindo escrita sem ledger. |
| Exclusão terminal | Término/drain ou abort demonstrados e retirada persistente dos caminhos antigos até reentrada. | Commit antigo depois de corte declarado terminal; recurso cortado reabre antes de concluir o corte global. |
| Continuidade externa | Fundamento suficiente fora do domínio restaurado/copiável e dos poderes cobertos. | R2/L/W/T antigos concordam e um nonce novo permite reativação. |
| Observação suficiente | Distinguir admissão, L, J, mutação, commit/abort, resposta e corte, com origem confiável. | Ausência de recibo usada como prova de ausência de efeito, ou oráculo incapaz de observar bypass. |

Argumento condicionado: se houver dois J para uma aprovação, houve segunda atribuição/reativação da oportunidade, duplicação do uso da mesma oportunidade, ou entrada por caminho/clone fora da mediação. As obrigações acima procuram excluir cada classe. A decomposição não prova que as primitivas necessárias existem nem que observações finitas demonstram a garantia universal.

## 7. Falhas, C5 e continuidade original

| Fronteira | Resposta exigida |
| --- | --- |
| Commit R2 possível, resposta desconhecida | UNKNOWN/BLOCKED, sem despacho. Consulta factual não concede capacidade. |
| Depois de P1 e antes de P2 | Consumo preservado; crash/perda de K não autoriza nova tentativa. |
| Depois de P2 e antes de P3 | Oportunidade gasta, sem início; falta de D09 bloqueia. |
| W preservou e ack perdeu-se | Preservação pode existir; sem confirmação exigida conhecida pelo fluxo original, não abrir. Consulta não ressuscita K. |
| Resposta original tardia, K ainda vivo | Só o percurso original ainda contínuo avalia requisitos restantes; não cria nova tentativa. Não se inventa prazo posterior a A. |
| Depois de P3/P4 e antes de J | Perda de contexto não rearma a entrada. É admissível consumo sem início. |
| J seguido de rollback/savepoint | L e consumo mantêm-se; nenhuma segunda entrada. Proteção do recurso não pode ser desmontada pelo executor. |
| Commit possível, resposta perdida | Reconciliar factos, sem repetir a operação. |
| Partição depois das condições prévias | C5 permite apenas à tentativa original continuamente vinculada prosseguir. Não há cancelamento retroativo nem nova disponibilização por reconexão. |
| Restore/restart ou confiança desconhecida | Quarentena; nenhum log ou ack antigo reconstrói K ou o armamento. |

Falta de requisitos para uma nova progressão não demonstra cessação física de trabalho antigo. Reconexão, reinício, perda de contexto, timeout ou resultado incerto não autorizam retoma automática. Não se promete exatamente uma vez: gastar a aprovação sem efeito é um resultado permitido.

## 8. Corte, clones e reentrada D10

Uma confirmação de corte terminal requer término/abort do trabalho antigo e retirada persistente de todos os percursos de efeito relevantes. Fechar uma entrada não prova término de transações já aceites. Em múltiplos recursos, a confirmação global exige todos os cortes e manutenção contínua dos anteriores. Ack de comando, silêncio, nova chave ou epoch não bastam.

Se subsistir clone integral gravável autónomo adversarial, o controlo no original e a preservação D09 não impedem o seu efeito. A garantia forte continua bloqueada. Provar impossibilidade de criar/escrever tal clone exige cobertura efetiva dos poderes de leitura, exportação, backup e restore; omiti-lo de um ensaio não é essa prova. Restringir a garantia ao endpoint oficial, retirar poderes cobertos ou adotar novo fundamento de confiança são decisões materiais, não adotadas.

Reentrada: preservar caso e divergências; colocar recuperação em quarentena; recuperar conteúdo/estado/confiança suficientes, incluindo transições posteriores ao backup; reconciliar início/efeito; demonstrar invalidação de capacidades antigas; verificar R2 único e D09; submeter evidência à decisão humana autenticada/auditada. Nova tentativa exige novo pedido e nova aprovação, sem reutilizar a antiga. O humano não substitui evidência ausente. Sem failover automático, autoridade substituta D09 ou bypass de emergência.

## 9. Sete cenários B-L preservados

| Cenário | Fundamento sobrevivente e controlo exigidos |
| --- | --- |
| 1. Falha de VM/serviço | Conteúdo, estado e confiança fora da falha, incluindo eventos pós-backup. Controlos sobreviventes bloqueiam; reconstrução em quarentena sem redispatch. |
| 2. SO LiveNet comprometido | R2/W/M/T/L e recuperação pertinentes fora de todo o alcance transitivo do executor. Se puder remover T, falsificar W ou escrever payload por outra via, a cobertura falha. |
| 3. Perda de nó Proxmox | Fundamentos suficientes fora do nó/dependências afetadas. R2 único, sem promoção automática; regresso do antigo tratado por invalidação demonstrada. |
| 4. Synology indisponível | Conteúdo crítico, confiança e recuperação sem dependência exclusiva direta ou indireta do NAS. Bloqueio das progressões afetadas, preservando C5; sem promessa de disponibilidade. |
| 5. Storage partilhado corrompido/eliminado | Conteúdo recuperável e continuidade fora do domínio de corrupção/eliminação. Digest isolado não recupera bytes; cópia no mesmo domínio não prova sobrevivência. |
| 6. Credencial administrativa limitada comprometida | Fundamentos e controlos fora de todo o seu alcance, incluindo elevação, reset, consola, deploy e recovery. Não confundir separação nominal com independência. |
| 7. Comprometimento transversal e de toda a recuperação | Fora da garantia aprovada. Nenhuma imposição ou recuperação segura é prometida por componentes todos comprometidos. |

Não se presume que W isoladamente reconstrua R2 ou todas as funções. Para cada cenário coberto, ligar falha/poder → conteúdo/confiança sobreviventes → controlo confiável → evidência de bloqueio e recuperação. Essa demonstração permanece pendente, sem inventário repetido.

## 10. Alternativas e decisões materiais delimitadas

A comparação histórica ALT-A/B/C/D é reutilizada: broker isolado não basta; guarda no alvo continua candidata condicionada; ALT-C combina mediação e imposição; corte físico é apenas complemento condicionado. Não se repete seleção de variantes B-L.

| Decisão material futura | Opções documentais ainda abertas | Condição antes de adoção |
| --- | --- | --- |
| Base confiada M/T/L | Funções integradas ou separadas, com poderes mínimos explícitos. | Explicar mudança de confiança/poderes e submeter escolha concreta ao humano. |
| Localização de L e ligação a J | No domínio R2, na mediação, ou em primitiva não reversível do alvo com continuidade externa. | Provar uso único, não reversão e vínculo real; nenhuma família resolve automaticamente clone. |
| Exclusão das capacidades antigas | Mecanismo de corte e cobertura terminal/persistente ainda não escolhidos. | Apresentar alcance, pendências, impacto e critérios de confirmação, sem atuar. |
| Clones e poderes | Manter a garantia forte e o bloqueador existente. | Qualquer redução de ameaça/efeito ou novo fundamento confiado requer decisão humana expressa. |

Recomenda-se continuar a análise documental de ALT-C contra as obrigações da secção 6. Essa recomendação já estava nos documentos anteriores; não adota uma família nem pede autorização genérica para continuar trabalho reversível já autorizado. Não há decisão material tomada nesta consolidação ou alteração de gate a ratificar.

## 11. Rastreabilidade e critérios da revisão final

| Fonte | Resultado consolidado |
| --- | --- |
| R2 C1/C2/C3 | P1, tempo em A, ordem única e consumo durável; secção 5. |
| R2 C4 | Vínculos, uso irrevogável, uma entrada J e mediação completa; secções 3–6. |
| R2 C5/C6; D09/D10 | UNKNOWN/BLOCKED, original contínuo, preservação prévia, recuperação e reentrada; secções 5, 7–9. |
| R2 C7 | 25 nomes de campos, JCS/UTF-8 e Ed25519 puro preservados; perfil/domínio e schemas concretos exigem aprovação própria. Sem bytes executáveis novos ou fallback R1. |
| B-L v1.0 | Separação, preservação fora do NAS, operador único, sete cenários e limite do clone. |
| Proposta e protocolo anteriores | Sequência, falhas e alternativas reunidas sem transformar hipóteses em mecanismos aprovados. |

D09 continua confirmação pertinente à admissão antes do percurso executável. V05-06 continua demonstração independente de preservação/separação/continuidade no seu âmbito. Nenhuma substitui a outra; COMPROVADO não autoriza destruição. Prazos/condições de retenção TBD mantêm-se; 900 segundos não definem retenção R2.

A revisão final incide exclusivamente nesta proposta técnica documental condicionada: coerência da sequência, semântica de J, resposta às falhas, C5, sete cenários, obrigações de prova e limites materiais. Uma aceitação documental não demonstra mecanismos, não seleciona arquitetura física e não abre gates. O objeto B-L v1.0 já aprovado não é reapresentado.

Estados preservados: P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados/bloqueantes; H02–H12 e GAP-001/002 pendentes/abertos e bloqueantes conforme os seus registos; RG1–RG7/D09/V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial.

Sem implementação, SQL, ensaios operacionais, alterações de infraestrutura, atribuição física, commits ou pushes. A [verificação desta entrega](REVIEW.md) identifica preservação e limites; não constitui confirmação D09 ou auditoria independente.
