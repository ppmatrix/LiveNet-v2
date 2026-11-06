# B-L/C4 — protocolo candidato de disponibilização e iniciação única

Revisão documental 0.1 · 30/10/2026 · Europe/Lisbon.
**ESPECIFICAÇÃO TÉCNICA CANDIDATA; SEM IMPLEMENTAÇÃO OU GARANTIA DEMONSTRADA.**

## 1. Autoridade e resultado deste aprofundamento

A [aprovação documental B-L v1.0](../../decisions/d09-06-bl-v1-approval-20261030.md) está concluída em 30/10/2026 e foi expressamente reiterada pelo operador humano. Não é solicitada de novo. [A versão aprovada](../d09-06-bl-conditional-20261030/SPECIFICATION.md) e o ato de aprovação permanecem inalterados. O presente trabalho é preparação técnica documental autorizada; não depende de uma nova aprovação daquela especificação.

Este documento aprofunda os passos K3–J da [proposta técnica anterior](../bl-c4-technical-20261030/PROPOSAL.md). Analisa como uma reserva durável pode estar ligada a uma única entrada no alvo sem que recovery, consulta ou rollback recriem um direito de iniciar. Não seleciona produto, algoritmo criptográfico, schema, extensão, arquitetura física ou mecanismo de armazenamento. ALT-C continua uma combinação candidata analisada, sem adoção arquitetural tácita.

Resultado principal: **o registo irrevogável e a exclusão no ponto de entrada são obrigações distintas**. Um registo único de consumo pode coexistir com dois despachos; uma entrada local única pode ser duplicada num clone do seu estado. A candidata precisa de provar as duas propriedades e a continuidade externa ao domínio copiável. Declarar uma flag «gasta» não resolve essa ligação.

## 2. Objetos e limites de confiança

R2 continua a única autoridade de admissão e ordem. W/D09 preserva e confirma conteúdo pertinente. M é a função candidata que conduz o fluxo confiado fora do executor comprometido. T é a imposição obrigatória no alvo. L designa a função candidata que conserva o uso irrevogável da oportunidade de início fora do rollback do efeito. L não é segunda autoridade de admissão e não recebe poder de criar aprovações ou alterar os vínculos de R2.

Os nomes seguintes são notação de análise, não campos ou objetos executáveis aprovados:

| Objeto conceptual | Significado e limitação |
| --- | --- |
| Aprovação e tentativa | Uma aprovação admite no máximo uma tentativa com todos os vínculos C4 imutáveis. |
| Contexto K | Continuação viva original, ligada a encarnação, recurso/geração e sessão/transação reais em T; não apenas um ID guardado pelo cliente. |
| Compromisso L | Memória durável de que aquela aprovação/tentativa/contexto já gastou a oportunidade; nunca é devolvida por abort, timeout, restart ou restore. |
| Entrada J | Primeira entrada aceite no corpo da operação protegida no alvo. Entrada seguida de erro/rollback conta. Pedidos recusados antes do corpo não são J. |
| Efeito e término | Mutação observada e commit/abort são factos distintos de J e da confirmação W. |

K tem de existir de forma inerte antes da avaliação final em R2, para que a admissão não autorize escolher posteriormente outro contexto. A representação, autenticidade e identidade real de K precisam de solução concreta. PID, certificado, identificador ou memória copiados não demonstram que duas execuções são a mesma continuação viva.

M/T/L e as raízes que os validam devem estar fora do alcance transitivo do executor comprometido no cenário coberto. Terem nomes diferentes não basta. Se o executor conseguir alterar o validador, escrever diretamente no payload, recuperar a credencial de M, reverter L ou restaurar um T gravável independente, a propriedade não está demonstrada.

Mantém-se um único operador humano. A exclusão do comprometimento total dos seus poderes e de toda a recuperação não dispensa provar o limite de uma credencial administrativa que se pretende cobrir. Não se impõe segundo operador, terceiro ou hardware novo.

## 3. Máquina de estados analítica

Os estados abaixo são posições de prova, não enums ou schema R2. Só a implementação futura selecionada poderia definir a sua representação.

| Posição | Facto conhecido | Pode entrar em J? | Consequência de perda de contexto |
| --- | --- | --- | --- |
| P0 contexto inerte | K ligado ao pedido, sem admissão executável. | Não. | Abandonar K; não tratar estado local como autorização. |
| P1 admitido duravelmente | R2 confirmou consumo, vínculos, ordem e evidência essencial. | Não, faltam os requisitos restantes. | Consumo indisponível; UNKNOWN/BLOCKED e reconciliação. |
| P2 compromisso irrevogável | L gastou a única oportunidade para o K exato. | Não só por existir P2. | Não reconstruir oportunidade a partir de L; pode haver gasto sem início. |
| P3 preservação prévia confirmada | W confirmou conteúdo crítico existente, incluindo a relação R2/L/K pertinente. | Ainda depende da exclusão e do fluxo original em T. | Obter depois uma cópia da confirmação não recria K nem autoriza retoma. |
| P4 entrada armada no fluxo original | M/T verificaram pré-requisitos, continuidade, contexto e gates; somente a continuação viva original pode atravessar a entrada uma vez. | Uma vez, se a proteção ainda estiver efetiva. | O armamento não é persistido como tarefa redispatchável. Sem continuação original, fica indisponível. |
| P5 J observado | T aceitou a primeira entrada; possibilidade de efeito já existe. | Nenhuma outra entrada para a mesma aprovação. | Resultado incerto sem retry/retoma; reconciliar. |
| P6 término observado | Commit/abort e pendências relevantes resolvidos no recurso. | Não novamente. | Preservar resultado e conteúdo; não libertar consumo ou L. |

Uma implementação candidata teria de assegurar P1 antes de P2, P2 e preservação pertinente antes de P4, e P4 antes de J. A ordem é causal, não uma comparação de timestamps. Se forem necessários outros eventos críticos prévios, devem estar confirmados antes da progressão que deles depende. Não se antecipa como facto um início ou resultado ainda inexistente.

P4 é o ponto que exige demonstração além de um ledger: a autorização não pode ser um bearer token recebido pelo executor, nem uma mensagem que qualquer nova sessão reapresente para obter outra entrada. A única passagem deve estar ligada ao controlo de entrada em T e ao fluxo original. Duplicação de transporte, callback reentrante e duas invocações no mesmo backend precisam de recusa antes do corpo. A escolha da primitiva que torna isto verdadeiro continua pendente.

## 4. Registo irrevogável e propriedade até término

L deve preservar, por aprovação/tentativa, a impossibilidade de atribuir uma segunda oportunidade. A associação inclui K e todos os vínculos confirmados por R2; não basta um contador global. Ler «já gasto» nunca concede despacho. Ler «não encontrado» depois de restore, perda de conteúdo ou continuidade desconhecida também não prova que a oportunidade esteja livre.

Persistir L antes de J permite consumir sem executar. É uma perda de disponibilidade deliberadamente admitida pela candidata, não execução exatamente uma vez. Em contrapartida, persistir apenas depois do efeito deixa a janela de replay; guardar L na transação revertida pelo payload deixa rollback/savepoint devolver o direito. Duas conexões ou um serviço com outro nome não demonstram durabilidade/independência automaticamente.

No recurso, a proteção de T precisa de impedir segunda entrada e manter a exclusão de capacidades antigas até commit/abort e término de trabalho pendente. A perda de um lock numa autoridade externa não pode liberar uma transação antiga no alvo para confirmar depois de um corte considerado terminal. O fecho de entrada não é prova de término de trabalho já aceite.

Savepoint exige duas análises separadas: a oportunidade L continua gasta mesmo se payload/estado local regressar; e uma operação que perdeu a proteção do recurso não pode voltar a atravessar J ou confirmar depois de corte terminal. Uma propriedade não é deduzida da outra. M, quando candidato a dono da sessão/transação, não pode delegar ao executor comandos que desmontem essa proteção.

Se T permitir SQL direto por owner/superuser, escrita raw, função alternativa, manutenção, extensão, réplica promovida ou sessão antiga fora desse percurso, a mediação não é completa. Os poderes que se pretendem cobrir precisam de ser efetivamente contidos; os poderes confiados precisam de ser declarados, sem excluir um adversário por conveniência.

## 5. Interleavings e respostas perdidas

Cada linha é cenário de análise para evidência futura. Nenhum foi executado nesta etapa.

| Fronteira / falha | Estado que pode ter persistido | Comportamento requerido e refutação |
| --- | --- | --- |
| Antes do commit R2 / resposta perdida depois dele | Não admitido ou consumo real sem resposta. | Sem confirmação durável/autenticada no fluxo original: não despachar. Consulta esclarece factos, não emite capacidade. |
| Depois de R2, antes de L | Consumo real, zero oportunidades disponíveis ao cliente. | Crash não liberta aprovação. Não reenviar automaticamente a tentativa. |
| Depois de L, antes de W | Oportunidade gasta, início ainda não permitido. | A falta de W bloqueia. Não confundir «reservado» com fila recuperável de tarefas. |
| W preservou, ack perdeu-se | Conteúdo pode estar recuperável sem confirmação conhecida pelo fluxo. | Antes da confirmação exigida, sem abertura. Consulta posterior não retoma K perdido. |
| Resposta original atrasada, fluxo ainda contínuo | Mesmo K, sem timeout/abandono declarado e sem perda de continuidade. | Só o fluxo original pode avaliar os requisitos restantes; a resposta tardia não cria novo contexto ou novo despacho. C2 continua em A, sem prazo inventado no commit. |
| Depois de W, antes de armar T | Consumo e conteúdo confirmados, nenhuma entrada ainda. | Crash/perda de K continua sem retoma automática; conteúdo confirmado não é direito transferível. |
| Entre armamento e J | L gasto; J pode não ter ocorrido. | Reinício não reconstitui armamento. Conserva-se a possibilidade de zero efeito. |
| Duas chamadas concorrentes / callback duplicado | Um L, dois pedidos de entrada. | T deve aceitar no máximo uma entrada no corpo. Um L e dois J refutam C4, mesmo que só um commit. |
| Depois de J, antes de mutação ou durante rollback | Início já conta, efeito pode ser zero. | Segunda entrada não é permitida. Ledger de efeito vazio não apaga J. |
| Mutação/commit real, resposta perdida | Efeito pode estar confirmado. | UNKNOWN, sem repetição idempotente ou compensação automática apresentada como retoma segura. |
| Corte pedido com transação antiga em voo | Trabalho antigo pode ainda confirmar. | Drain termina antes do corte terminal, ou abort/término são demonstrados. Ack de comando não prova a barreira. |
| Corte local confirmado, clone antigo vivo | Original pode estar excluído, clone ainda gravável. | Não emitir confirmação universal/reentrada correspondente. Escrita no clone refuta; rejeição de endpoint não salva o caso. |
| L/R2/W/T restaurados juntos | Podem concordar num passado coerente. | Continuidade externa ao conjunto restaurado ou quarentena. Nonce fresco assinado pelo estado antigo não demonstra atualidade. |
| Primeiro recurso cortado reabre antes do último | Cortes locais existiram, sem exclusão global contínua. | Não confirmar corte global. Deteção posterior ao efeito não satisfaz a propriedade. |

Retransmissão de um evento documental para W não equivale a repetir a operação. A futura interface deve distinguir esses percursos e recusar que a consulta/retransmissão devolva uma nova capacidade. Não se escolhe aqui protocolo ou política de retry de mensagens; a proibição de retry/retoma da operação permanece integral.

## 6. C5, contenção e reentrada

Depois de satisfeitas as confirmações prévias, uma partição posterior não revoga retroativamente a admissão. C5 permite apenas à tentativa original continuamente vinculada prosseguir. Não autoriza nova sessão, reconstrução de armamento, continuação depois de restart ou repetição com resultado incerto. Falta de informação para novas progressões não é prova de que uma operação antiga deixou fisicamente de existir.

Nova tentativa exige reconciliação independente no âmbito aplicável, invalidação demonstrada das capacidades antigas, novo pedido e nova aprovação humana, além dos gates e requisitos R2/D09. Isso é aprovação da tentativa futura, distinta da aprovação B-L v1.0 já concluída; o documento aprovado não é reapresentado ao humano.

O corte terminal por recurso sucede ao término/abort do trabalho antigo e à retirada persistente de todos os caminhos de efeito. Em vários recursos, a confirmação sucede a todos os cortes e à manutenção contínua dos anteriores. Timeout, epoch, nova chave, NOLOGIN, ausência de heartbeat ou declaração administrativa não substituem prova de alcance e término. O mecanismo concreto de corte continua uma decisão técnica/arquitetural própria, sem atuação nesta etapa.

## 7. Argumento condicionado e fronteira do clone

Para sustentar uma iniciação exclusiva seria necessário demonstrar cumulativamente: consumo R2 sem reutilização; L sem segunda oportunidade ou regressão; ligação de P4 a uma única continuação real; T mediando toda entrada e mantendo exclusão terminal; recuperação sem rearmar capacidades; conteúdo/confiança/observação suficientes fora das falhas cobertas.

Se duas entradas forem possíveis, ou houve duas atribuições/reativação em L, ou a mesma atribuição permitiu dois fluxos entrarem em T, ou existiu caminho/clone fora da mediação. Esta decomposição identifica onde procurar contraexemplo; não prova que as premissas existem. Em particular, «K é único» e «T não é duplicável pelo adversário» são obrigações que não podem ser substituídas por IDs.

**Se o adversário conservar clone integral gravável autónomo, a garantia forte permanece inviável com os pressupostos atuais.** L ou W externos podem negar uma nova admissão conforme, mas não apagam o poder de escrever no meio autónomo. Se a solução pretender impedir a cópia, deverá demonstrar a prevenção perante os poderes aprovados de leitura/exportação/backup/restore. A precondição não é satisfeita por omitir o clone da experiência.

Limitar o efeito ao serviço oficial, retirar um poder da ameaça ou aceitar um novo fundamento global de confiança seriam decisões materiais. Nenhuma é adotada para concluir este documento. O bloqueio do clone continua explícito, sem abertura de O3 ou fecho de GAP-001/002.

## 8. Recovery D10 e sete cenários preservados

| Cenário D09-03 | Estado/fundamento sobrevivente exigido | Controlos e reentrada |
| --- | --- | --- |
| 1. Falha de VM/serviço | R2, oportunidade gasta, conteúdo W e confiança pertinentes recuperáveis fora da falha, incluindo eventos após backup. | Componente reconstruído em quarentena; log de reserva não redispatcha. Se faltar continuidade, UNKNOWN/BLOCKED. |
| 2. SO LiveNet comprometido | R2/W/M/T/L e fundamentos necessários fora do alcance transitivo da VM. | T rejeita SQL alternativo e W falso; se a VM remover T ou escrever payload por outro meio, o cenário falha. |
| 3. Perda de nó Proxmox | Conteúdo e confiança suficientes fora do nó; nenhuma autoridade concorrente; capacidade antiga tratada no eventual regresso. | Recovery não rearma K. Nova aprovação só depois de invalidação efetiva; ausência do nó não prova cessação. |
| 4. Synology indisponível | B-L conserva preservação crítica/recuperação fora do NAS e de dependências indiretas obrigatórias. | Progressão só com pré-requisitos satisfeitos; original contínuo conserva C5. Não se promete disponibilidade perante dependências comuns. |
| 5. Storage partilhado corrompido/eliminado | Conteúdo integral e referências de continuidade sobreviventes fora do domínio de falha/eliminação. | Restore em quarentena, sem «não encontrado = livre». Digest isolado não recupera conteúdo. |
| 6. Credencial administrativa limitada comprometida | R2/W/T/L e recovery pertinentes fora do alcance completo da credencial, incluindo reset, consola e deploy. | Controlos não alcançados bloqueiam; não reclassificar perda de toda a separação pretendida como exclusão global por conveniência. |
| 7. Comprometimento transversal e de toda a recuperação | Nenhum fundamento independente pressuposto; cenário excluído da garantia aprovada. | Não prometer imposição técnica ou recuperação segura por componentes todos comprometidos. Sem confiança restabelecida, não há base para reentrada. |

W não se promove a autoridade R2 nem se presume suficiente, isoladamente, para reconstruir todas as funções. A reconciliação acrescenta evidência; não apaga consumos/inícios ou reescreve a ordem. RPO/RTO, retenção e mecanismos concretos permanecem por decidir no âmbito próprio.

## 9. Alternativas para o ponto P2–J, sem seleção material

| Família candidata | O que poderia oferecer | Obrigação que permanece |
| --- | --- | --- |
| L integrado no domínio autoritativo R2, com entrada imposta por M/T | Menos funções de recuperação distintas e relação direta com a admissão. | R2 não se torna controlo mágico do meio: precisa de vínculo singular e imposição em T; nova transição/evidência exige especificação e formatos próprios. |
| L num domínio confiado de mediação, com T obrigatório | M pode deter o fluxo e impedir redispatch pelo executor. | L precisa de continuidade durável fora do payload; crash de M não rearma; a base confiada e seus poderes precisam de aceitação específica. |
| L/controlo dentro do alvo por primitiva não reversível, com fronteira externa de continuidade | Verificação próxima de J e término, evitando guarda cooperante distante. | Não presumir que função/trigger/contador ou extensão existente fornece isso; provar savepoint, crash, privilégios, restauração e clone. |

Não se escolhe uma dessas famílias nem se define base de dados, conta, protocolo, software, hardware ou nova autoridade. Os requisitos P0–P6 são comparáveis entre famílias. ALT-C da análise anterior continua recomendação de aprofundamento, não decisão operacional já tomada.

O trabalho documental pode continuar a comparar provas e falhas sem intervenção humana. Escolher de facto uma família que altere base confiada, poderes ou garantia é o ponto material a submeter antes de adoção. Abrir um gate, implementar ou ensaiar exige autorização própria. A aprovação B-L v1.0 não volta a ser condição pendente.

## 10. Evidência verificável e estado de saída

Uma demonstração futura deve observar separadamente admissão/consumo, compromisso de início, entrada real J, mutações/commit/abort, atuação do corte e conteúdo/continuidade W. Deve detetar bypass sem ledger e iniciação com zero efeito. Cada interleaving da secção 5 precisa de barreira observável, contexto/geração e origem de evidência que não dependa só da afirmação do controlador verificado. Nenhum ensaio foi realizado aqui.

Refutações centrais: um L com dois J; J antes da confirmação prévia exigida; rollback/restore libertando oportunidade; consulta devolvendo capacidade; commit antigo depois do corte terminal; efeito em clone fora da cobertura. Bloqueio seguro sem confirmação universal é resultado honesto, mas não demonstra cessação universal.

D09 confirma preservação pertinente antes da disponibilização; V05-06 demonstra independentemente preservação/separação/continuidade no seu âmbito. Nenhum substitui o outro; COMPROVADO não autoriza destruição. C7, 25 nomes de campos, JCS/UTF-8 e Ed25519 puro mantêm-se; não há schemas/bytes executáveis aprovados por este texto.

Estabelecido: aprovação documental B-L v1.0, invariantes e âmbito humano. Candidato: protocolo analítico e famílias de implementação. Por demonstrar: as primitivas de início singular, continuidade, mediação, corte e recuperação, incluindo o bloqueador do clone. P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados/bloqueantes; H02–H12/GAP-001/002 bloqueantes; RG1–RG7/D09/V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial.

Sem implementação, SQL, ensaios operacionais, infraestrutura, atribuição física, commits ou pushes. A atividade autorizada avança na especificação e análise, mantendo pendentes apenas as decisões materiais próprias e as demonstrações técnicas — não a aprovação B-L v1.0.
