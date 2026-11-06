# LiveNet v2 — fronteira obrigatória de efeito e corte

Proposta documental candidata 0.1 · 30/10/2026 · Europe/Lisbon.
Estado: **ESTUDO ESTÁTICO CONCLUÍDO; FRONTEIRA NÃO SELECIONADA, NÃO EXISTENTE POR PRESSUPOSTO E NÃO DEMONSTRADA**.

## 1. Conclusão executiva

É possível especificar rigorosamente as condições que uma fronteira obrigatória teria de satisfazer. **Não foi identificada, nos fundamentos e mecanismos documentados, uma fronteira realizável demonstrada que satisfaça a garantia forte para todos os meios e poderes cobertos.** As alternativas no alvo, storage e virtualização são fronteiras parciais se subsistirem vias inferiores, paralelas ou meios autónomos. Fundamento externo de evidência não é, por si, controlo do efeito.

**Se um adversário coberto já conserva um meio integral, gravável e autónomo capaz do efeito protegido, controlos apenas no original ou em serviços que esse meio dispensa não podem impedir o efeito nesse ramo.** É o bloqueador I-04, não uma lacuna corrigível por mais recibos, Q ou nova localização de L. I-02 mantém prioridade quando o poder pode remover a imposição e escrever diretamente.

Uma composição conceptual de controlos só seria suficiente se cobrisse todos os caminhos de efeito e de criação/reativação de meios, resistisse aos poderes cobertos, mantivesse a exclusão até e depois do corte e dispusesse de observação/continuidade suficientes. Nenhuma dessas premissas é concedida por esta redação. Não se prova impossibilidade de toda arquitetura futura nem se afirma topologia/poderes atuais do laboratório; afirma-se a inviabilidade no caso de autonomia gravável admitida e a ausência de demonstração para o modelo completo.

A matriz de meios/poderes e pontos finais de imposição está em [MATRIX.md](MATRIX.md). Esta proposta reúne definições, alternativas, contraexemplos, sete cenários e decisões reservadas. Não seleciona CAND-1/2/3 nem adota nova raiz confiada. I-01/I-02/I-03 continuam abertas; I-04 e clone gravável continuam bloqueadores.

## 2. Autoridade e âmbito preservados

Base aprovada: [B-L v1.0](../d09-06-bl-conditional-20261030/SPECIFICATION.md), [C4 v0.2](../bl-c4-consolidated-20261030/PROPOSAL.md) e [I-01–I-04 v0.1](../bl-c4-i01-i04-20261030/PROPOSAL.md), com os atos de aprovação identificados em [REVIEW.md](REVIEW.md). A [análise de viabilidade CAND-1/2/3](../bl-c4-cand-feasibility-20261030/PROPOSAL.md) é proposta histórica reutilizada; este mandato não declara a sua aprovação.

[R2 C1–C7](../../auth-boot-02-r2.md) e [D09/D10](../../auth-boot-02-r1.md) mantidos. Primeira classe analisada: UPDATE fixo de laboratório, vínculos imutáveis de pedido, participantes, finalidade, operação, gate, ambiente, plano, digests, destino/geração, executor/encarnação e sessão/transação protegidas. Não se generaliza a DDL/Alembic, administração ou qualquer efeito externo por inferência.

As definições seguintes são precisões analíticas por remissão às fontes aprovadas. Não criam uma nova classe normativa de efeitos, não deslocam a fronteira temporal para commit e não redefinem clones como irrelevantes pelo nome ou endpoint. Se a classificação de uma transformação concreta não puder ser determinada com essas fontes, permanece desconhecida para alegar cobertura, e eventual redefinição normativa exige decisão própria.

Autoridade R2 única; D09 preserva/confirma e não admite. Operador único, segregação funcional sem independência administrativa absoluta perante todos os seus poderes. Exclusão do comprometimento total dos poderes e de toda a recuperação não absorve uma credencial delimitada que alcance vários domínios. Progbox DEV; STAGING/PROD em VMs Proxmox; LiveNet interno. Sem recursos, tecnologia, topologia, chaves, contas, retenção ou RPO/RTO escolhidos.

## 3. Definições rigorosas para a análise

| Termo | Definição analítica e limite |
| --- | --- |
| Efeito protegido | Mutação/atuação sobre o recurso/payload abrangido pela operação e relações protegidas existentes, incluindo alteração por via que contorne o percurso autorizado. Deve relacionar-se com o âmbito aprovado, não apenas com publicação no endpoint oficial. Mutação observada e commit durável são factos distintos; não se exige commit para reconhecer que houve início ou mutação. |
| Início J | Entrada real aceite no corpo da operação protegida; entrada que aborte conta. Efeito por SQL alternativo/raw pode evitar o J instrumentado e continua contraexemplo de mediação. Início sem mutação não se transforma em segundo direito de iniciar. |
| Meio capaz de efeito | Recurso ou combinação de conteúdo, runtime, processo/escritor e acessos que permite produzir o efeito abrangido, agora ou após ativação/restore alcançável pelo poder coberto. Não se limita à VM oficial ou à instância PostgreSQL conhecida. |
| Conteúdo inerte | Cópia/backup que, isoladamente e no alcance considerado, não dispõe de percurso para se tornar meio gravável/ativo. Conservar bytes não é automaticamente executar um ataque; se o poder puder acrescentar escritor/ambiente, a composição alcançável tem de entrar na análise. |
| Capacidade de escrita | Poder efetivo para iniciar, alterar, confirmar ou permitir a alteração relevante: credencial, ligação viva, transação pendente, acesso a dados/volumes, controlo de runtime/configuração, delegação ou recovery que alcance esses atos. Capacidade pode existir sem novo login, sem recibo ou sem consumo adicional. |
| Poder coberto e alcance transitivo | Poder adversarial delimitado cuja resistência é exigida pelo cenário aprovado, incluindo o que consegue obter por delegação, reset, consola, deploy, chaves, storage e recuperação. Não se presume que todo executor tenha todos os poderes; uma via plausível não é topologia verificada. |
| Fronteira obrigatória | Conjunto conceptual de controlos pelos quais passa todo caminho relevante de capacidade até efeito, incluindo caminhos que criam/restauram meios ou alteram os próprios controlos. Não tem de ser uma única máquina ou camada; cada controlo necessário deve permanecer confiável perante o poder/falha em que é usado como fundamento. |
| Último ponto confiável | Em cada caminho concreto, ponto de imposição que ainda consegue impedir o efeito antes de ele ocorrer e que o poder coberto não consegue evitar/remover. É relativo à via; um ponto SQL não é último numa via raw que o dispensa. Observação posterior não é esse ponto. |
| Confirmação de corte terminal | Afirmação verificável, de âmbito e contexto/geração explícitos, de que novas entradas antigas estão impedidas, trabalho anteriormente aceite terminou ou ficou incapaz de efeito, e capacidades/meios antigos pertinentes não voltam a produzir efeito por restart/restore/delegação. Exige exclusão persistente e continuidade desde os cortes até à confirmação e depois dela; não é ack de comando ou timeout. |

A definição de efeito não transforma qualquer escrita num backup ou corrupção de qualquer ficheiro em operação protegida nova. Uma alteração raw só é contraexemplo se afetar o recurso/efeito abrangido ou permitir concretizá-lo. Cópia que conserva essa capacidade não deixa de contar por receber outra identidade aparente. Se a equivalência semântica com o efeito aprovado não for verificável, não se conclui segurança por omissão.

A confirmação terminal não desfaz efeitos anteriores nem declara inválida a admissão histórica. Pode haver commit antigo **antes** do corte terminal demonstrado; não pode haver efeito antigo posterior ao corte que se confirmou como terminal. Uma tentativa futura legitimamente aprovada é novo contexto, não reativação das capacidades antigas. Não se exige apagar backups protegidos ou destruir dados para afirmar corte; demonstrar incapacidade de efeito é obrigação distinta e destruição continua sem autorização.

## 4. Modelo de cobertura: caminhos, poderes e tempo

Considere-se, apenas como notação analítica, uma relação de alcançabilidade entre poder coberto → capacidade → meio → efeito. Incluir as relações indiretas que permitam substituir o controlo, obter o seu segredo, reconstruir capacidade ou criar outro meio. Uma fronteira adequada tem de intersetar obrigatoriamente **cada** caminho relevante através de imposição que sobreviva ao poder/falha considerado. Não basta intersetar o percurso esperado executor → M → T → PostgreSQL.

Exemplo de refutação estática: poder → snapshot/exportação → meio gravável autónomo → efeito não passa no T do original; logo T não corta essa via. Outro: poder → deploy do verificador → remoção do controlo → efeito. O caminho de administração sobre a guarda é parte do problema de mediação, não detalhe externo à arquitetura.

Há dois fechos necessários a demonstrar: (a) sobre todos os meios existentes e pendências; (b) sobre os meios/capacidades que o poder ainda consegue criar ou reativar a partir de cópias, configuração e recovery. Lista de VMs ligadas só trata uma parte de (a); lista de backups só não prova (b). Esta é exigência de completude da demonstração, não um inventário operacional agora executado ou uma enumeração completa já obtida.

Além da cobertura espacial, a imposição tem de durar. Validar em P4 e perder a guarda antes da mutação/commit não basta. Cortes em recursos diferentes só sustentam uma confirmação global quando todos estiverem efetivos e os anteriores não tiverem reaberto. A comparação de timestamps entre máquinas não substitui dependência causal e evidência de término.

Este modelo define uma condição necessária de fronteira e um argumento condicionado de suficiência **se** cobertura, resistência, continuidade, término e observação forem realmente demonstrados. Não demonstra que essas premissas são realizáveis. Se a obtenção de completude depender de presumir que não há cópias desconhecidas, a conclusão global permanece não estabelecida.

## 5. Quatro obrigações separadas de corte

| Obrigação | Facto que seria necessário | O que não prova esse facto |
| --- | --- | --- |
| Prevenir novas entradas | Todos os percursos de nova entrada antiga ou inválida recusados antes do corpo/efeito, com singularidade C4 quando aplicável. | Bloquear UI/broker/login, mantendo SQL alternativo, ligação viva ou raw. |
| Terminar ou excluir trabalho aceite | Cada processo/sessão/transação/trabalho pendente abrangido terminou, abortou ou ficou incapaz de produzir efeito; inclusão de trabalho delegado e ramos antigos. | Lista local vazia, ack de término, morte de M, rede desligada, ausência de heartbeat. |
| Retirar persistentemente capacidade antiga | O poder não recupera a capacidade por restart, nova configuração, reset, delegação ou restore; controlo e histórico suficientes sobrevivem. | Chave/epoch novas só no original, revogação apenas de futuras ligações, marcador reversível. |
| Excluir meios autónomos | Nenhum meio relevante fora da fronteira conserva ou obtém capacidade de efeito, incluindo cópia já ativada ou ativável pelo poder coberto. | Corte de uma VM/LUN, pin do endpoint, recusa de R2 ou recibo D09 do original. |

Sem a quarta obrigação, a confirmação só pode ter âmbito local demonstrado; não se rotula como universal. Não se impõe ordem física de comandos ou mecanismo novo. As quatro obrigações são cumulativas para a alegação terminal no âmbito aprovado; ausência/ambiguidade de qualquer fundamento impede essa confirmação e a reentrada correspondente.

C5: uma partição posterior à confirmação prévia não revoga retroativamente admissão. Só a tentativa original continuamente vinculada pode prosseguir. Contenção física é ato diferente de revogação lógica; não pode ser deduzida da revogação posterior ou do silêncio. Esperar drenagem preserva os efeitos anteriores ao término, sem prazo garantido; forçar término requer poder de contenção confiável e demonstração de resultado. Nenhuma destas alternativas autoriza retry/retoma automática.

## 6. Alternativas conceptuais e primeiro poder de contorno

As alternativas F-A–F-E são editoriais, não arquitetura escolhida. Cada uma responde a um conjunto de caminhos e não substitui as outras obrigações por mudar o nível de imposição.

| Alternativa conceptual | Capacidade pretendida | Primeiro contorno adversarial | Confiança mínima/evidência necessária | Conclusão de viabilidade |
| --- | --- | --- | --- | --- |
| F-A — imposição no alvo | Entrada singular e mediação de toda via SQL; exclusão até término no recurso. | Poder que modifica/remove T, invoca escritor alternativo, escreve raw ou ativa clone. | Código/configuração/dados e vias alternativas fora do poder coberto; prova de início, payload, término e não reentrada. | Plausível localmente condicionada; insuficiente isoladamente para todos os meios/poderes. |
| F-B — imposição no storage/caminho de escrita | Retirar capacidade de escrita nos suportes abrangidos, inclusive a processos que ignorem SQL. | Poder que reconfigura o controlo, muda o suporte, escreve por outro caminho ou usa exportação já autónoma. | Todos os percursos ao suporte realmente mediados; administração/recovery do controlo não alcançadas; resolver operações aceites/em voo e efeitos pendentes. | Não prova início único e não cobre automaticamente cópias fora do suporte; suficiência global não demonstrada. |
| F-C — imposição na virtualização/execução | Suspender/terminar contextos e impedir reativação dos domínios abrangidos. | Gestão/consola/deploy que reativa/duplica runtime ou exporta dados para execução noutro meio. | Poder de criação, memória, dispositivos e recovery contido; evidência de fim/exclusão de trabalho antigo e de todos os ramos pertinentes. | Limite conceptual do domínio controlado, não do universo de cópias; não contém o seu próprio administrador adversarial por definição. |
| F-D — fundamento externo de continuidade/atestação | Manter referências não revertidas com o alvo e evidência de atualidade/corte. | Meio autónomo que produz efeito sem consultar esse fundamento; ou poder que substitui raízes/observações. | Raiz/evidência sobreviventes e âmbito verificável; distinguir informação correta de atuação obrigatória. | Pode apoiar demonstração; testemunho externo isolado não impõe efeito/corte. |
| F-E — dependência externa obrigatória de capacidade de efeito | Hipótese de todo meio necessitar de um recurso/capacidade que o poder não copie, substitua ou utilize após corte. | Cópia integral com tudo o necessário; cache/segredo exportável ou capacidade pré-concedida que dispensa a dependência; escritor raw relevante. | Provar necessidade real para o efeito aprovado, não só para o endpoint, e impossibilidade de obter autonomia sob poderes cobertos; término de capacidades já entregues. | Nova base confiada potencial, não demonstrada; incapaz de revogar retroativamente autonomia já concedida apenas mudando o original. |

F-E não é seleção de criptografia, serviço, hardware ou tecnologia. Cifrar/verificar acesso não prova retirada de capacidade se o poder já conservar conteúdo utilizável, chaves ou escritor autónomo; destruir/rodar uma chave no original não apaga conhecimento copiado. Também não se redefine efeito como «aceitação pelo validador externo»: o conteúdo/efeito protegido continua o aprovado. Só uma proposta concreta poderia mostrar se tal dependência existe sem reduzir o modelo.

Uma composição de F-A/B/C/D/E teria de resistir aos caminhos administrativos e de recovery que atravessam várias camadas. Não se deduz independência de múltiplos nomes. Um fundamento externo não tem de ser terceiro fora do laboratório; «externo» significa fora do domínio de falha/poder/cópia em análise, com alcance efetivo por demonstrar. Não se exige fornecedor, segundo operador ou hardware novo.

## 7. Contraexemplos adversariais e alcance da impossibilidade

| Ref. | Sequência analítica | Poder necessário | Refutação |
| --- | --- | --- | --- |
| CE-01 | R2/L/W corretos; SQL alternativo ou guarda substituída altera payload sem nova autorização. | Escritor não mediado ou administração que remova T. | I-02; fronteira só no percurso nominal não é obrigatória. |
| CE-02 | Processo ignora PostgreSQL/M/T e modifica estado protegido por acesso raw relevante. | Acesso efetivo ao meio e capacidade de produzir a mutação abrangida, não só leitura. | F-A insuficiente; é necessário controlo no caminho efetivo de efeito. |
| CE-03 | Novos logins impedidos, mas transação antiga confirma depois de um corte alegadamente terminal. | Capacidade já aceite ainda ativa; nenhum novo privilégio ou login necessário. | Obrigação de término/exclusão falhou, mesmo sem novas entradas. |
| CE-04 | Corte do suporte original; cópia exportada gravável produz efeito noutro suporte. | Cópia utilizável mais ativação/escrita fora do caminho cortado. | F-B não cobre meios autónomos; I-04 continua. |
| CE-05 | VM parada; snapshot com memória é retomado duas vezes, preservando K/Q e capacidade local. | Snapshot/restore/execução nos ramos e meio pertinente gravável. | K/Q local não é singular global; F-C parcial. |
| CE-06 | Estado e verificação restaurados juntos; histórico coerente antigo aparenta atualidade e reativa capacidade. | Recovery sobre o conjunto de estado/raízes; caminho de efeito ainda disponível. | Sem fundamento sobrevivente obrigatório, continuidade e não rearmamento não demonstradas. |
| CE-07 | Chave/epoch ou permissão externa retirada; capacidade antiga em cache ou conteúdo integral já copiado continua utilizável. | Capacidade previamente adquirida que dispensa nova consulta. | F-D não impõe; F-E só seria obrigatória se essa autonomia fosse efetivamente impossível. |
| CE-08 | Credencial limitada alcança reset/deploy/consola do controlador e do observador; efeito e evidência são alterados. | Cadeia transitiva de administração específica, não comprometimento global presumido. | Não há independência perante esse poder; não pode ser descartado como cenário 7 por conveniência. |
| CE-09 | Recurso A cortado reabre enquanto se corta B; são somados recibos locais em instantes diferentes. | Reativação ou recovery de A antes de confirmação global. | Não existiu exclusão global contínua, ainda que cada recibo local fosse correto. |
| CE-10 | Logs locais e ledger vazios; ramo autónomo não observado altera payload. | Meio de efeito fora da observação; não é necessário falsificar W. | Ausência de observação não demonstra ausência global de efeito; confirmação indevida. |

**Argumento de impossibilidade no subcaso autónomo:** se (i) o efeito continua abrangido, (ii) o adversário coberto controla um meio gravável suficiente e (iii) a produção do efeito nesse meio não depende de controlos alcançáveis pelo corte proposto, existe uma execução em que o meio produz efeito apesar do corte. A fronteira proposta não pode garantir a exclusão nesse subcaso. Trocar o local de L, assinar recibos, incrementar epochs ou acrescentar observadores sem poder de imposição não remove (ii)/(iii).

A conclusão é limitada e explícita: enquanto esse subcaso for admissível, garantia forte inviável para essa fronteira. Não se infere que toda cópia é suficiente, que o laboratório atual tem essas permissões, ou que uma arquitetura que realmente previna autonomia seria impossível. Por outro lado, declarar «não há clone» sem excluir os caminhos de criação/ativação não demonstra prevenção.

## 8. Verificação simultânea dos sete cenários B-L

Não são sete aprovações independentes: uma mesma proposta de fronteira precisa de conservar as suas premissas em todos os cenários cobertos. A evidência que sustenta um deles não pode depender exclusivamente do componente perdido ou poder comprometido noutro.

| Cenário | Fronteira/controlo e evidência sobreviventes exigidos | Estado desta análise |
| --- | --- | --- |
| 1. Falha VM/serviço | Guardas e conteúdo/confiança suficientes fora da falha; processos pendentes e capacidades restauráveis tratados. Reconstituição não rearma aprovação antiga. | Condição definida, sobrevivência concreta não demonstrada. |
| 2. SO LiveNet comprometido | Fronteira real de efeito e observação fora de todo alcance transitivo do SO, incluindo credenciais, montagens, deploy e vias raw. | F-A sozinha não basta se SO remover T/escrever meio. Exequibilidade não demonstrada. |
| 3. Perda nó Proxmox | Conteúdo/confiança suficientes fora do nó e dependências comuns; bloquear progressão afetada; tratar nó antigo se regressar; sem autoridade concorrente. | F-C local não prova exclusão no regresso ou noutro ramo. |
| 4. Synology indisponível | Preservação crítica B-L, confiança e recovery sem dependência exclusiva direta/indireta do NAS; controlo seguro quando requisitos faltam. | Fronteira proposta que dependa exclusivamente do NAS não satisfaz B-L. Sem promessa de disponibilidade; C5 mantida. |
| 5. Storage corrompido/eliminado | Conteúdo recuperável, continuidade e controlos confiáveis fora do domínio de falha/eliminação. Recuperar não devolve capacidade antiga. | F-B pode perder os seus próprios fundamentos; cópia suficiente externa por demonstrar. |
| 6. Credencial administrativa limitada comprometida | Resistência ao alcance completo, incluindo reset, consola, chaves, deploy, storage e recovery. Pelo menos os fundamentos necessários a esse cenário ficam fora dele. | Independência é relativa ao poder; várias contas/nós não a provam. Lacuna material, sem exclusão silenciosa. |
| 7. Comprometimento transversal e de toda a recuperação | Nenhum fundamento confiável pressuposto; não garantir imposição por componentes comprometidos nem reentrada segura sem confiança restabelecida. | Exclusão aprovada preservada; não ampliada para descartar cenário 6. |

**Resultado simultâneo:** nenhuma alternativa demonstrou essa composição de sobrevivência/imposição para todos os cenários cobertos. A distribuição B-L não é contradita pela exigência de fronteira; também não a fornece automaticamente. Um controlador global pode criar dependência comum e poder transversal que precisa de decisão/prova, não alega-se independência administrativa absoluta. Operador único mantido.

## 9. Evidência, critérios de refutação e confirmação terminal

Esta secção descreve semântica de evidência futura, não novo schema/atestado ou ensaio autorizado. Uma confirmação terminal teria de identificar verificavelmente: contexto/capacidades antigas abrangidos; meios e percursos incluídos; fundamento para completude e não criação/reativação de ramos; término/exclusão de pendências; atuação persistente dos controlos; origem/continuidade da observação e limitações conhecidas. Campos e bytes não são definidos.

| Obrigação | Evidência futura necessária | Refutação verificável |
| --- | --- | --- |
| Cobertura de meios/poderes | Relação completa pertinente entre poder, capacidade, meio e efeito, incluindo administração e recovery da guarda. | Um caminho coberto produz efeito sem controlo obrigatório. |
| Início único C4 | Observação de J inclusive abortado, ligada a uma aprovação/K/L reais; Q não reversível ou duplicável no âmbito coberto. | Dois J por aprovação ou Q rearmado por erro/restore. |
| Efeito/bypass | Observação de payload e vias raw/alternativas que não dependa apenas do ledger/controlador verificado. | Efeito sem ledger fica invisível enquanto se conclui «zero efeito». |
| Término | Estado final de todo trabalho aceite ou demonstração de incapacidade de efeito, sem assumir morte por silêncio. | Efeito/commit antigo depois da confirmação terminal. |
| Persistência e meios futuros | Demonstração de que restart/restore/delegação não recriam capacidade antiga; todas as cópias ativáveis relevantes cobertas. | Ramo reaparece gravável, ou corte antigo reabre antes/depois da confirmação. |
| Confiança da prova | Conteúdo/raízes/observação fora da falha/poder considerado, com continuidade suficiente. | Mesmo poder remove guarda e falsifica o fundamento usado para a validar. |

A instrumentação pode ser próxima do efeito sem ser independente do poder que a consegue alterar. W preservar uma afirmação de T não demonstra verdade física de início, término ou ausência de bypass. Uma amostra finita de meios não prova completude global. Se a observação não cobre um ramo ou não sobrevive ao poder considerado, o resultado é insuficiente/indeterminado para confirmar, não prova de segurança.

D09 confirma conteúdo crítico pertinente antes da disponibilização, sem antecipar início/resultado futuros. Ausência/ambiguidade bloqueia progressão dependente. V05-06 é demonstração independente de preservação/separação/continuidade no seu âmbito, cumulativa e distinta; COMPROVADO não autoriza destruição. D10 exige conteúdo/estado/confiança suficientes, quarentena, continuidade pós-backup, reconciliação, invalidação antiga e reentrada humana autenticada/auditada. Não promove D09 a R2 nem cria failover automático.

C2/C3/C5/C7 mantidos: tempo confiável e prazo em A, sem grace period ou prazo de corte inventado; revogação única ordenada sem cancelamento retroativo; consultas factuais não emitem capacidade e não há retry/retoma automática; separação R2/R1, 25 nomes/JCS/UTF-8/Ed25519 sem novos formatos. Consumo/recibos corretos não provam uma fronteira universal.

## 10. Estatuto das afirmações e decisões materiais reservadas

| Estatuto | O que se afirma nesta entrega |
| --- | --- |
| Propriedade exigida | C4, mediação, confirmação D09, continuidade e invalidação antigas, ausência de retoma e garantia forte mantidas pelas fontes aprovadas. |
| Hipótese conceptual | Cobertura de todos os caminhos/meios e imposição que sobreviva ao poder/falha, incluindo fecho sobre criação/reativação. Premissas não demonstradas. |
| Mecanismo candidato | Famílias F-A–F-E ou composição, sem tecnologia, produto, runtime, atuador, localização física ou raiz escolhidos. |
| Propriedade demonstrada | Nesta etapa apenas leitura/hashes/preservação documental no âmbito descrito em REVIEW.md. Evidência DEV-05 histórica, parcial e não repetida, não demonstra fronteira nova. |
| Impossibilidade/bloqueador | Autonomia gravável suficiente fora da imposição torna a garantia inviável nesse subcaso; I-04 não resolvida. Fora dele, realizabilidade da fronteira para todos os cenários não estabelecida. |

A análise pode ser concluída sem decisão material intermédia. Para adotar uma fronteira ou alegar garantia realizável, é necessário apresentar ao operador alternativas concretas:

| Decisão reservada | Alternativas e consequências |
| --- | --- |
| Nova raiz/base de confiança | Propor fundamento fora do domínio adversarial relevante, com poder de imposição sobre todos os meios, e especificar quem o administra/recupera. Pode procurar preservar a garantia; não resolve conteúdo/capacidade autónomos já concedidos só por existir noutro local. Não se seleciona nem exige hardware/terceiro. |
| Poderes e delegações | Propor fronteira que resista ao poder coberto, preservando a ameaça; ou propor explicitamente alteração do poder confiado/excluído, que mudaria o modelo e exige decisão normativa/material própria. Retirar transitivamente um poder por declaração não é prova de resistência. |
| Prevenção de autonomia | Demonstrar que cópias/restores não podem tornar-se meios autónomos sob os poderes aprovados, incluindo estado e capacidades já existentes; ou manter bloqueio quando isso não é possível. Novo mecanismo/gestão de cópias precisa de proposta própria, sem destruição autorizada. |
| Redefinição de efeito | Qualquer limite ao endpoint, aceitação externa ou apenas dados oficiais alteraria a garantia. Só pode ser submetido como redução/mudança explícita; não é adotado para fechar I-04. |
| Manutenção do modelo sem mecanismo suficiente | Manter garantia e bloqueio, admitindo perda de disponibilidade, sem reclamar corte universal. É a recomendação enquanto a fronteira não for sustentada. |

**Recomendação:** manter o modelo e os bloqueios; usar a matriz como dossier de requisitos/refutação para uma futura proposta material de fronteira, começando pelas vias raw, capacidades antigas e cópias autónomas. Não escolher CAND-1/2/3 nem aprofundar Q como solução do bypass global. Se nenhuma proposta resistir a esses poderes sem reduzir a garantia, declarar inviabilidade mantida e submeter eventual revisão de pressupostos ao humano, nunca fazê-la implicitamente.

## 11. Resultado final e limites de execução

**Viabilidade da fronteira obrigatória: condições definidas; existência e realização para o modelo completo não demonstradas; garantia forte inviável enquanto subsistir meio integral gravável autónomo fora de qualquer imposição efetiva.** Nenhuma alternativa estudada remove esse caso. Esta conclusão não aprova nova raiz nem altera normas/gates.

P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados/bloqueantes; H02–H12 e GAP-001/002 pendentes/abertos e bloqueantes conforme os registos; RG1–RG7, R2 D09 e V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial. I-01/I-02/I-03 abertas; I-04/clone gravável bloqueantes.

Sem implementação, SQL, schemas/APIs/mecanismos executáveis, ensaios ou testes operacionais, acesso a VMs/Proxmox/Synology/serviços, alterações de rede/storage/credenciais, commits, pushes ou merges. Somente proposta nova e índice não normativo necessário; documentos aprovados e alterações anteriores preservados.
