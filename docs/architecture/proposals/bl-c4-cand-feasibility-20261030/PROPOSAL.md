# LiveNet v2 — viabilidade e refutação CAND-1, CAND-2 e CAND-3

Versão documental candidata 0.1 · 30/10/2026 · Europe/Lisbon.
Estado: **ANÁLISE ESTÁTICA CONSOLIDADA PARA REVISÃO; NENHUMA COMPOSIÇÃO SELECIONADA OU VIABILIDADE FORTE DEMONSTRADA**.

## 1. Relatório executivo

A [I-01–I-04 v0.1](../bl-c4-i01-i04-20261030/PROPOSAL.md) está aprovada exclusivamente como documento condicionado, pelo [ato próprio](../../decisions/bl-c4-i01-i04-v01-approval-20261030.md). CAND-1/2/3, Q e fronteiras de confiança não foram selecionadas/aprovadas por extensão; I-01–I-04 não foram encerradas.

**Resultado: nenhuma das três composições, tal como descritas, é viável como solução da garantia forte enquanto um adversário coberto puder conservar um clone integral gravável autónomo ou uma via privilegiada de efeito fora da imposição.** Trocar L entre R2, M e alvo não altera essa conclusão. Não existe neste conjunto uma composição pronta para adoção dentro de toda a ameaça aprovada.

O resultado não é uma prova de impossibilidade de qualquer arquitetura futura nem uma constatação operacional de que determinado administrador do laboratório controla todas as VMs. É uma refutação condicionada a capacidades adversariais que o modelo obriga a tratar, e que as três composições ainda não retiram por mecanismos demonstrados. A presença de um contraexemplo admissível basta para impedir uma garantia universal; desconhecer a sua presença atual não prova exclusão.

As três conservam plausibilidade **local condicionada**, se a fronteira real impedir todos esses percursos e a singularidade Q/K for demonstrada. Essas premissas não estão estabelecidas; afirmá-las como verdade exigiria prova e, quando implicasse nova base confiada ou alteração de poderes, decisão arquitetural material. A análise não as concede tacitamente.

Recomendação para a próxima decisão humana: tratar primeiro a fronteira de efeito perante poderes privilegiados e cópias; não escolher a localização de L ou continuar a detalhar Q como se isso resolvesse I-02/I-04. Manter a garantia atual bloqueada e preparar uma proposta delimitada de fronteira obrigatória para todos os meios relevantes é a linha recomendada, sem adoção de mecanismo ou autorização operacional. As alternativas materiais e consequências estão na §10.

## 2. Fontes, requisitos e método de refutação

Base: [R2 C1–C7](../../auth-boot-02-r2.md), [D09/D10](../../auth-boot-02-r1.md), [B-L v1.0](../d09-06-bl-conditional-20261030/SPECIFICATION.md), [C4 v0.2](../bl-c4-consolidated-20261030/PROPOSAL.md), [revisão A–H](../bl-c4-consolidated-20261030/REVIEW_DOCUMENTAL_V02.md) e I-01–I-04 v0.1. Fontes/versões/hashes e limites constam de [REVIEW.md](REVIEW.md).

Notação preservada: R2 admite/ordena; W/D09 preserva/confirma; M conduz o fluxo; T impõe no alvo; L conserva oportunidade irrevogável; K é a continuação viva original; Q seria a retirada singular da passagem antes de J; J é entrada real no corpo protegido, incluindo início abortado. Q não é nova autoridade, gate, campo ou schema aprovado. Efeito por bypass pode ocorrer sem J instrumentado; isso refuta I-02, não deve ser escondido redefinindo J.

Invariantes: uma aprovação admite no máximo uma tentativa com todos os vínculos C4 imutáveis; consumo sem efeito é admissível; não se promete exatamente uma vez. R2 → L → confirmação D09 pertinente → P4 → eventual Q/J → término é dependência causal candidata, sem atomicidade distribuída. Se uma transição pré-J exigir confirmação adicional como evento crítico, não é dispensada nesta análise. Início e resultado futuros não são inventados para obter autorização prévia.

Ordem da avaliação: (1) procurar escritor/clone que evite toda a cadeia; (2) procurar poder que remova o controlo; (3) só no subcaso em que essas vias sejam excluídas, avaliar singularidade Q/K, transação e recovery. Não se constrói um algoritmo para Q nesta etapa. As composições descrevem obrigações; um ataque a uma realização que não cumpre uma dessas obrigações refuta a realização, não o texto ideal por este proibir o ataque. A questão de viabilidade é precisamente se a obrigação pode ser sustentada perante os poderes cobertos.

Os contraexemplos abaixo são sequências de factos a verificar numa futura demonstração autorizada, **não comandos, ensaios executados ou nova autorização de ensaio**. Distinguem-se inferência estática, evidência histórica e topologia atual desconhecida.

## 3. Contraexemplo prioritário comum: interação I-02/I-04

### CE-C — meio autónomo fora da mediação

1. Subsiste uma cópia integral gravável ou via raw capaz de alterar o recurso relevante, sob poderes incluídos no cenário coberto. O meio não depende de uma fronteira de efeito que o original consiga retirar efetivamente.
2. R2 mantém consumo e ordem corretos; L não concede segunda oportunidade; W preserva conteúdo correto; Q no original aceita no máximo uma passagem.
3. O original bloqueia novas entradas ou é declarado localmente cortado. O adversário conserva no outro meio runtime/sessão antigos ou um escritor que não necessita de T.
4. O meio autónomo produz efeito. A recusa do endpoint oficial e a ausência de novo consumo/L/J do original não impedem esse efeito.

Conclusão: I-02 falha no meio omitido; uma alegação de corte universal I-04 também falha. Não é necessário derrotar criptografia, forjar W, reverter R2 ou produzir segundo J no original. Se for usada a mesma aprovação em dois ramos para iniciar a operação, há também refutação I-01; para refutar mediação basta um efeito fora da fronteira.

**Poder direto mínimo:** capacidade de escrita/execução autónoma no meio pertinente. **Obtenção transitiva possível:** exportação/leitura/backup mais restore e escrita; snapshot com memória mais capacidade de retomar duas instâncias; administração do alvo/storage; ou credencial que alcance esses poderes por consola, reset, delegação/deploy. São rotas alternativas condicionais, não uma afirmação de que um único poder é suficiente para todas. Leitura isolada ou posse de backup sem capacidade de o tornar executável/gravável não são automaticamente o ataque completo.

**Fronteira mínima necessária:** todo meio capaz desse efeito e o controlo sobre a sua criação/ativação teriam de depender de imposição confiável que o poder coberto não removesse ou copiasse para uso autónomo. Colocar mais um verificador antes do SQL no original não satisfaz isso. Se o adversário já conserva conteúdo integral utilizável e escritor autónomo, um novo controlo no original não o recupera retroativamente.

**Evidência histórica reutilizada:** [DEV-05](../../../../experiments/auth_boot_02_r2_dev05/REPORT.md) relata clone com sessão antiga viva e efeito após cessação local do original, snapshot com efeito em ambos os ramos, função direta sem consumo externo e bypass administrativo. Esse laboratório tinha host/utilizador/administrador comuns, fixtures e observação local; não prova poderes atuais sobre o laboratório nem valida T/Q novos. Não foi repetido.

**Condição de paragem analítica:** enquanto CE-C for admissível e não houver proposta concreta que o exclua dentro da ameaça aprovada, não se aprofunda a implementação de Q para declarar uma candidata viável. O restante documento avalia apenas limites e condições, sem ignorar esse bloqueio.

## 4. CAND-1 — L no domínio R2, T no backend protegido

### 4.1. Primeiro contraexemplo, poderes e fronteira mínima

Primeiro contraexemplo global: CE-C, mesmo com R2/L intactos. Primeiro contraexemplo específico numa realização com T removível: **CE-1** — um poder coberto alcança o catálogo/runtime ou um escritor do alvo, desvia a operação fixa de T e altera payload sem nova oportunidade R2/L. Não precisa de reentrar em Q. É ataque I-02, não uma segunda admissão.

Poder direto necessário: remover/substituir a guarda ou invocar uma via de escrita não mediada. Poder transitivo: executor → credencial administrativa recuperável/gestão/deploy → controlo do alvo; ou administração delimitada do alvo/storage. Esta cadeia precisa de ser demonstrada ou excluída concretamente; não se atribui ao executor por suposição. A exclusão de comprometimento total de todos os poderes não pode absorver uma credencial limitada que já quebra esta fronteira.

Fronteira mínima: T e todos os caminhos de efeito, configuração, credenciais, código e recovery têm de ficar fora desse alcance coberto. Independência R2/W não basta quando o payload continua gravável por outro poder. Se para funcionar se pretender confiar o administrador do alvo antes coberto como adversário, essa é uma mudança material explícita, não propriedade demonstrada da CAND-1.

### 4.2. Q/L/K/J, observação e continuidade

Só após excluídos CE-C/CE-1: L em R2 pode negar uma segunda atribuição, mas Q precisa de retirar uma única passagem no contexto real T, de forma indivisível e não reversível com rollback do payload. A associação a K deve ser autenticada pelo componente que conhece a sessão/transação real; ID ou certificado vindo de M não prova que não há dois contextos. Só a continuação original vencedora segue para J; ler «gasto» em R2 não reautoriza o backend. Não se presume que a primitiva exista.

Observação independente: é necessário observar J no alvo, inclusive entrada abortada, e payload/efeito por vias que não produzam ledger, relacionando-os com admissão/L e contexto real. Log de M ou ack R2 não observa o bypass CE-1. Se o poder remove T e a instrumentação correspondente, a instrumentação local deixa de ser independente desse ataque; exige fundamento exterior ao poder e cobertura suficiente. Não há capacidade independente completa demonstrada nesta candidata.

D09: confirmação pertinente de admissão e compromisso L precede P4; não se deduz dela execução. Continuidade R2/L deve sobreviver às falhas cobertas e à cópia/restore do alvo; o seu estado externo pode bloquear reatribuição, mas não retira um escritor autónomo. D10 exige também invalidação de contexto antigo, não apenas reconstruir R2. I-04 impõe término/exclusão efetivos antes de reentrada.

**Classificação:** inviável para a garantia forte com CE-C ou CE-1 admissíveis; plausibilidade local condicionada à fronteira e Q demonstrados. Uma nova fronteira concreta ou mudança de poderes confiados depende de decisão material. Nenhuma seleção da CAND-1 é fundamentada só por L estar em R2.

## 5. CAND-2 — L no diário do mediador M, sem recuperação de tarefas

### 5.1. Primeiro contraexemplo, poderes e fronteira mínima

Primeiro contraexemplo global: CE-C. Primeiro específico para a mediação: **CE-2** — poder coberto obtém a credencial de escrita/configuração de M, ou assume controlo da ligação protegida, e chama uma via que T não medeia obrigatoriamente. O diário mantém uma oportunidade e o broker aparenta execução única, mas há efeito direto no alvo. É I-02; exigir M honesto não prova que os seus poderes sejam inacessíveis.

Poder direto: usar credencial/capacidade de escrita fora de T ou alterar a mediação. Poder transitivo: executor → reset, montagem, consola, deploy ou recovery de M → segredo/ligação ao alvo; alternativamente acesso administrativo direto ao alvo. Obter só uma credencial limitada que T rejeite não completa o contraexemplo. Se toda utilização dessa credencial atravessar T real e singular, este ataque fica impedido e o próximo exame é I-01.

Contraexemplo I-01 específico nesse subcaso: **CE-2K** — snapshot vivo de M/T duplica o dono da tentativa e contexto armado; ambos prosseguem como continuação original sem que o diário conceda nova oportunidade. Um Q local em cada runtime aceita uma vez. Copiar apenas um diário morto não deveria causar execução: redispatch por leitura é proibido e seria defeito de realização, não comportamento permitido pela composição. Este contraste separa recuperação documental de clonagem de capacidade viva.

Fronteira mínima: poderes de M, diário, ligações, T e recovery não podem ser apropriados pelo poder coberto; T medeia todas as entradas mesmo se M for contornado. Além disso, capacidade viva duplicada precisa de exclusão efetiva, externa ao conjunto copiável. Mutex ou dono único escrito num registo só sustentam exclusividade dentro do domínio que o adversário não consiga duplicar.

### 5.2. Q/L/K/J, observação e continuidade

L no diário não é outbox nem fila de execução recuperável. Q continua obrigatório no alvo e deve impedir duas entradas na mesma sessão, não apenas dois workers no M original. A continuação real K liga M e T, sem transferência para worker substituto. Se um novo worker recebe o registo e continua J, C5 foi violada; se o snapshot duplica todo o fluxo, I-04/continuidade continuam por resolver.

Observação independente: o diário só prova o que registou; não demonstra J, ausência de escrita direta ou morte do M antigo. Exige-se fonte de observação de entrada e payload exterior ao poder que possa adulterar M/T e relação verificável com W. Um clone que escreve fora da observação impede concluir «zero bypass» ou «corte universal», mesmo com diário externo íntegro. Capacidade independente suficiente não demonstrada.

D09: preservar conteúdo crítico R2/diário e confirmar vínculos/continuidade antes de disponibilização. Há novo estado confiado de mediação, com cadeia de custódia/recovery própria e fundamento suficiente fora da sua falha. Consultar W/diário não gera tarefa. Reiniciar M não prova término da ligação ou transação antiga; I-04 bloqueia substituição sem invalidação demonstrada.

**Classificação:** inviável para garantia forte com CE-C/CE-2/CE-2K admissíveis. Plausibilidade local condicionada à contenção de poderes, mediação T e exclusão de duplicação viva, não à unicidade de worker. Adoção do estado/poderes de M e fronteira externa é decisão material, sem seleção nesta análise.

## 6. CAND-3 — L persistente no alvo, fora da transação do efeito

### 6.1. Primeiro contraexemplo, poderes e fronteira mínima

Primeiro contraexemplo global: CE-C. Primeiro específico de continuidade: **CE-3** — um poder coberto restaura ou copia alvo, L, T e respetivas referências locais de verificação, fazendo reaparecer estado anterior a uso/corte; permite que o ramo antigo produza efeito sem obter nova admissão. Se o runtime puder ser retomado armado, dispensa até reconstruir K. Um diário local não revertido por rollback SQL pode ainda assim ser revertido por restore do seu meio.

Poder direto: copiar/repor estado e tornar o ramo gravável/ativo; ou alterar a primitiva/diário T. Poder transitivo: backup/storage/consola ou recuperação/deploy do alvo → controlo do estado e do escritor. A capacidade de restaurar só o payload, mantendo L e imposição externa atuais e obrigatórios, não basta para este ataque; daí a necessidade de identificar o conjunto realmente copiável em cada proposta.

Primeiro contraexemplo I-02 ainda mais curto, se esse poder existir: escrever raw ou remover T; não exige restore e toma precedência sobre CE-3. Não há pressuposto de que o adversário precise de quebrar o journal para contornar o efeito.

Fronteira mínima: persistência e imposição de T não podem ser alteradas/removidas pelo poder coberto, e a atualidade/invalidação precisam de fundamento fora do conjunto restaurável. Esse fundamento deve governar o efeito real em todos os meios; apenas notar a divergência posteriormente em W não impediu o efeito. Colocar o mesmo journal noutra pasta/disco sob o mesmo poder não demonstra separação.

### 6.2. Q/L/K/J, observação e continuidade

No subcaso sem esses bypasses, Q precisaria de passagem singular ligada ao K real, com L confirmado fora da transação do payload e sem reabertura por crash/recovery. Q e L próximos do recurso não tornam a atribuição e a entrada atomicamente duráveis por definição. Perda entre compromisso e J permite zero início; «sem resultado» não é trabalho por retomar. Uma segunda conexão não prova separação de persistência ou vínculo.

Observação independente: journal T no mesmo domínio comprometido não demonstra a sua própria não regressão ou ausência de raw. Exige-se observação de J/efeito com confiança e continuidade sobreviventes, não apenas cópia W de afirmação local. Sem acesso a um ramo autónomo, a cobertura global permanece não demonstrada; a observação do original não o substitui.

D09: W confirma conteúdo pertinente existente, mas não promove um L restaurado a atual. Recovery requer relações R2/L/vínculos/ordem suficientes, transições pós-backup e quarentena. R2 continua independente das bases executor/alvo e única autoridade: L local não passa a aprovar ou reavaliar elegibilidade. Fundamento externo para continuidade não é automaticamente mecanismo de exclusão do clone. Corte terminal deve cobrir o ramo restaurado e pendências antigas.

**Classificação:** inviável para garantia forte com CE-C/CE-3 ou raw admissíveis. Plausibilidade local depende de persistência própria, fronteira não removível e continuidade externa efetiva, todas por demonstrar. Definir esse fundamento é decisão material; não é uma propriedade existente inferida da posição de L.

## 7. Matriz de comportamento perante falhas

São requisitos/hipóteses de realização a confrontar, não comportamentos já testados ou demonstrados. Em todas as colunas pressupõe-se, apenas para esta análise local, que os contraexemplos de mediação global foram excluídos; isso não sucede por escrever a tabela.

| Situação | CAND-1 | CAND-2 | CAND-3 | Critério comum de refutação |
| --- | --- | --- | --- | --- |
| Concorrência | L único R2 não pode originar dois K/T; Q limita entrada real. | Diário e dono M não substituem Q no alvo. | L local serializado não basta se houver dois contextos/ramificações. | Dois J por aprovação, mesmo com um/zero commits. |
| Reentrada na mesma sessão | Q não é lock reentrante nem chamada repetível após erro. | Mesmo M/ligação não pode emitir segunda entrada aceite. | Primitiva T não aceita novamente o mesmo uso confirmado. | Segunda entrada após erro/retorno ou callback duplicado. |
| Rollback/savepoint | Consumo/L externos ao payload; Q não regressa nem se perde proteção do recurso. | Diário gasto não volta a fila; controlo T permanece indisponível. | L/Q fora do rollback SQL; segundo domínio de persistência precisa de prova. | Marcador/guarda revertido permite nova entrada. |
| Crash antes de J | R2/L mantêm oportunidade indisponível; K perdido não se reconstitui. | Nenhum worker de recuperação reexecuta entrada do diário. | Gravação incerta bloqueia; replay do journal não rearma contexto. | «Reservado sem resultado» tratado como tarefa. |
| Crash depois de J/ack perdido | Resultado incerto sem repetir; observar/reconciliar. | Novo M não assume continuação antiga. | Não inferir ausência de efeito de L/J local incompleto. | Retry em contexto novo ou mesmo contexto sem continuidade. |
| Restore/snapshot vivo | R2 atual pode negar nova atribuição, mas não impede T/clone autónomo. | Duplica dono vivo; registo de dono/diário não invalida cópia. | Pode reverter conjuntamente L/T; exige fundamento externo e mediação obrigatória. | Ramo antigo escreve ou K copiado é tratado como original único. |
| Recuperação D10 | Reconstruir autoridade única e continuidade, sem reativar tentativa. | Reconstruir M/diário em quarentena sem despachar. | Reconciliar L local com fundamentos sobreviventes sem o promover a autoridade. | Aprovação antiga reativada por recovery/consulta. |
| Corte terminal | Não confundir L externo com término de backend antigo. | Não confundir morte de M com término de transação no alvo. | Não confundir journal/corte local com exclusão de todos os meios. | Commit antigo após confirmação terminal ou recurso reaberto prematuramente. |

C5 preservada: partição posterior às condições prévias não revoga retroativamente admissão e só o original continuamente vinculado pode prosseguir. Informação desconhecida bloqueia progressão dependente; não prova morte do original. Não há novo lease, prazo, política de retry ou retoma. Nova tentativa exige reconciliação, invalidação demonstrada, novo pedido e nova aprovação humana com gates aplicáveis.

## 8. Matriz comparativa de viabilidade e estatuto das afirmações

R = requisito aprovado; H = hipótese ainda não demonstrada; M = mecanismo possível não adotado; D = propriedade efetivamente demonstrada no âmbito indicado. Estas letras são editoriais, não estados de gate.

| Dimensão | CAND-1 | CAND-2 | CAND-3 |
| --- | --- | --- | --- |
| R: fronteira e oportunidade | R2 único, D09 prévio, vínculos C4, uso não reutilizável e T obrigatório. | Iguais; diário não é nova autoridade. | Iguais; L alvo não aprova. |
| H: confiança mínima | M/T, todas as vias de efeito e recovery fora dos poderes cobertos. | Idem, mais diário e posse viva M; nenhuma cópia executável concorrente. | T/L e atualidade fora do poder de reversão, mais exclusão de todas as vias de efeito. |
| M: posição de L | Transição durável própria no domínio R2. | Diário confiado M sem redispatch. | Persistência própria no alvo fora da transação payload. |
| M: Q requerido | Passagem indivisível ligada ao K real T, não desfeita com payload. | Mesma passagem T; dono M único não é substituto. | Passagem T com persistência/continuidade próprias; proximidade não basta. |
| Primeiro refutador global | CE-C: efeito em meio autónomo ou escritor não mediado. | CE-C, sem depender do diário. | CE-C, sem depender de L local. |
| Refutador específico prioritário | CE-1: remover T/escritor alternativo. | CE-2: poder de M usado fora de T; CE-2K se cópia viva contorna singularidade. | Raw se disponível; CE-3: restore/cópia conjunto L/T e escritor. |
| Observação independente D | Nenhuma cobertura completa de J e bypass demonstrada para esta composição. | Nenhuma; diário M não observa o alvo/clone autonomamente. | Nenhuma; journal local não atesta a própria integridade contra o seu administrador. |
| D09/continuidade D | Nenhuma demonstração nova; integridade documental não é D09. | Idem, com novo estado M por justificar. | Idem, com risco de continuidade comum alvo/L. |
| I-04/clone | Não resolvido; L externo não retira escritor autónomo. | Não resolvido; dono copiado e alvo autónomo. | Não resolvido; L/T e meio podem ser copiados/restaurados juntos. |
| Plausibilidade local | Condicionada a H, Q e término demonstrados. | Condicionada a H, Q e exclusão do dono antigo. | Condicionada a H, Q e continuidade fora do meio copiável. |
| Viabilidade para toda a garantia atual | **Inviável com CE-C admissível; não estabelecida dentro de toda a ameaça aprovada.** | **Inviável com CE-C admissível; não estabelecida dentro de toda a ameaça aprovada.** | **Inviável com CE-C admissível; não estabelecida dentro de toda a ameaça aprovada.** |
| Dependência material | Fronteira/poderes T, alterações R2/L e primitiva Q antes de adoção. | Fronteira/poderes T/M/diário e continuidade antes de adoção. | Fronteira/persistência T/L e fundamento externo antes de adoção. |

**D históricas efetivamente disponíveis:** o relatório DEV-05 documenta efeitos de contorno e clone, e contenção local em fixtures específicas. Não demonstra as três composições novas, impossibilidade de bypass privilegiado, observação global independente ou continuidade D09. «Testes passaram» nesse relatório inclui testes que esperavam contraexemplos. A demonstração de um limite histórico não é demonstração da segurança pretendida.

**D desta etapa:** identidade/hash dos documentos aprovados e comparação de preservação de ficheiros Git no âmbito declarado em REVIEW.md. Nenhuma propriedade executável Q/L/T, capacidade de recursos ou segurança operacional foi demonstrada por esta análise estática.

## 9. Critérios de refutação verificáveis e condições de saída

Os localizadores CE/F abaixo não substituem RG/H/GAP/I ou criam gates. São critérios de evidência futura; nenhum ensaio está autorizado ou foi executado.

| Localizador | Factos que a observação deve distinguir | Refutação suficiente | Se não houver cobertura suficiente |
| --- | --- | --- | --- |
| F-01 — mediação | Poder exercido, via de escrita, contexto/geração, estado R2/L e payload observado. | Efeito por poder coberto fora de T, ainda que não exista novo J/ledger. | Não afirmar mediação completa. |
| F-02 — singularidade | Uma aprovação/L, K real e cada entrada no corpo, inclusive as que abortam. | Dois J para a mesma aprovação, na mesma sessão ou em ramos distintos. | Não deduzir início único de commit/resultado único. |
| F-03 — não rearmamento | Estado antes/depois de erro, savepoint, crash e leitura de diário/autoridade. | Aprovação ou passagem recuperada dá direito a reentrada/retoma. | UNKNOWN/BLOCKED, sem tarefa de recuperação. |
| F-04 — D09/continuidade | Conteúdo recuperável e origem, vínculos, ordem/continuidade e causalidade anterior a disponibilização. | J sem confirmação prévia pertinente; W falso/de outro contexto aceite; restore antigo tratado como atual. | Quarentena; assinatura/digest/nonce não completam a prova. |
| F-05 — corte | Trabalho antigo até término, todos os meios e manutenção contínua das exclusões. | Commit antigo após confirmação terminal ou qualquer efeito em clone não invalidado. | Não confirmar corte universal/reentrada correspondente. |
| F-06 — observador | Alcance dos poderes sobre evidência e capacidade de ver J, efeito sem ledger e meios autónomos. | Controlador pode esconder o bypass ou um ramo fica fora da observação usada para concluir ausência global. | Resultado indeterminado para a garantia; não fabricar «zero efeito». |

Bloquear sem confirmar corte universal é comportamento seguro requerido, mas não prova cessação universal. D09 confirma preservação pertinente; V05-06 demonstra preservação/separação/continuidade no seu âmbito e é cumulativa, sem substituição. COMPROVADO não autoriza destruição. RPO/RTO, retenção e libertação TBD não são fixados.

Condições antes de qualificar qualquer composição como viável para o modelo completo: fronteira real contra F-01/F-05 em todos os poderes/meios cobertos; singularidade real contra F-02/F-03; D09/continuidade contra F-04; observação suficiente contra F-06. A mera promessa destas condições numa especificação não as satisfaz.

## 10. Próxima decisão humana: fronteira da garantia antes da localização de L

A análise autorizada fica concluída sem escolher arquitetura. **Para passar desta comparação para a adoção de uma composição que reclame a garantia forte, a fronteira I-02/I-04 é decisão material indispensável.** Não se assume uma solução para continuar indefinidamente Q.

| Alternativa para decisão própria | Consequência | Estatuto nesta entrega |
| --- | --- | --- |
| A — Manter a garantia e manter bloqueio até haver proposta de fronteira obrigatória que cubra poderes/meios, criação de cópias e término antigo | Preserva a ameaça; pode revelar impossibilidade de excluir capacidades já concedidas ou necessidade de novo fundamento. Exige justificação de confiança/recuperação antes de adotar mecanismo. Não implica recurso novo por si. | **Recomendação de continuidade documental**, sem mecanismo escolhido ou I-04 resolvida. |
| B — Propor novo fundamento confiado fora do domínio adversarial copiável, com poder efetivo sobre todos os meios pertinentes | Pode procurar sustentar A, mas altera base confiada/poderes/recuperação e exige decisão concreta. Não se afirma existência, disponibilidade, suficiência ou capacidade de controlar cópia autónoma já em posse do adversário. | Não adotada; não seleciona hardware, serviço, atuador ou topologia. |
| C — Redefinir expressamente ameaça/domínio do efeito ou poderes excluídos | Pode tornar um problema local mais tratável, mas reduz/altera a garantia aprovada; efeitos no endpoint oficial não são equivalentes a ausência de efeito no clone. Exige alteração normativa humana explícita. | Não recomendada como ajuste implícito; não adotada. |

A e B não são soluções independentes comprovadas: B seria uma possível proposta material para tentar concretizar A. Se o meio já é integralmente autónomo e gravável, não se pode prometer torná-lo dependente apenas por instalar controlo noutro local. Também não se retira ao adversário um poder por o declarar agora confiado.

Recomendação concreta: **manter o modelo e os bloqueios; orientar a próxima decisão para o âmbito de uma fronteira obrigatória de efeito e os poderes que teria de resistir, antes de decidir CAND-1/2/3**. O dossier dessa decisão deve responder: que meios podem existir; qual poder limita criação/ativação/escrita em cada um; qual controlo não pode ser removido/copiado no alcance coberto; como termina trabalho antigo; que evidência independente permite confirmá-lo. Identificar obrigação não autoriza inventário novo ou infraestrutura; reutilizar o já documentado e assinalar desconhecidos.

Se não existir proposta que responda a isso sem retirar poderes/efeitos cobertos, o resultado mantém-se **nenhuma composição viável para a garantia forte nos pressupostos atuais**. Só então uma eventual revisão normativa deve ser apresentada com a perda de garantia explícita; não é adotada pelo agente.

## 11. Continuidade, cenários e limites preservados

Sete cenários B-L: falha VM/serviço, SO executor comprometido, perda de nó Proxmox, Synology indisponível, storage corrompido/eliminado, credencial limitada comprometida e comprometimento transversal com toda a recuperação. As linhas de ataque tratam sobretudo cenários 2/5/6 e capacidades antigas do 1/3; o 4 continua a exigir preservação crítica fora da dependência exclusiva direta/indireta do NAS; o 7 conserva a exclusão aprovada. Não se confunde 6 com 7 para descartar um ataque delimitado. Dependências comuns de gestão, identidade/reset, storage/cópias, deploy/boot, rede/alimentação, tempo e recovery continuam a avaliar pelo alcance efetivo, não por nomes de contas/VMs/nós.

D10 preservado: conteúdo/confiança e transições suficientes fora da falha/poder; reconstrução em quarentena, ordem/consumo/vínculos intactos; reconciliação; invalidação antiga demonstrada; decisão humana autenticada/auditada; novo pedido e nova aprovação para nova tentativa. D09 não se torna autoridade alternativa. Sem HA/failover automático ou bypass de emergência. Operador único, sem independência administrativa absoluta perante todos os seus poderes.

C2/C3/C7 preservados: tempo confiável e elegibilidade em A, máximo de 900 segundos sem prazo inventado para commit; ordem autoritativa única e sem revogação retroativa de admissão anterior; sem fallback R1 ou formatos/assinaturas novos, preservando 25 nomes/JCS/UTF-8/Ed25519. Nenhuma destas propriedades remove o clone.

LiveNet interno ao laboratório, progbox DEV, STAGING/PROD em VMs Proxmox. P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados/bloqueantes; H02–H12 e GAP-001/002 pendentes/abertos e bloqueantes conforme os registos; RG1–RG7, R2 D09 e V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial. I-01–I-04 abertas; I-04/clone bloqueantes.

Esta proposta é candidata para revisão, não decisão arquitetural tomada. Sem implementação, mecanismos/schemas/APIs, SQL, testes/ensaios, alteração de infraestrutura/serviços/credenciais, commits, pushes ou merges.
