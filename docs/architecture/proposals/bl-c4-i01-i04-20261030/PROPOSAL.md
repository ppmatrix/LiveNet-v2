# LiveNet v2 — aprofundamento documental I-01 a I-04

Versão candidata 0.1 · 30/10/2026 · Europe/Lisbon.
Estado: **PROPOSTA PARA A PRÓXIMA REVISÃO; SEM SELEÇÃO MATERIAL, IMPLEMENTAÇÃO OU DEMONSTRAÇÃO OPERACIONAL**.

## 1. Base aprovada e resultado deste aprofundamento

A [C4 consolidada v0.2](../bl-c4-consolidated-20261030/PROPOSAL.md), SHA-256 `937bb32ab57fb0859d414e3ada9a11dbf963fdb19158d85a0e2c55cf019ff3ab`, foi aprovada documentalmente em 30/10/2026, conforme [ato próprio](../../decisions/bl-c4-v02-approval-20261030.md). A B-L v1.0 conserva a sua aprovação. Não se editam esses documentos ou os relatórios históricos para simular aprovação anterior.

Esta proposta aprofunda as lacunas I-01–I-04 da [revisão A–H](../bl-c4-consolidated-20261030/REVIEW_DOCUMENTAL_V02.md), sem repetir inventário, auditoria ou seleção B-L. Resultado novo: distinguir **atribuição irrevogável da oportunidade**, **travessia local singular** e **exclusão de todos os meios de efeito**, comparar três composições concretas e explicitar as condições sob as quais o argumento poderia funcionar.

A classificação permanece: C4 v0.2 aprovada documentalmente; presente aprofundamento candidato; mecanismos, alcance de poderes e demonstrações por resolver. I-01/I-02/I-03 não são encerradas. **I-04 e o clone integral gravável permanecem bloqueadores técnicos.** Nenhuma composição abaixo satisfaz a garantia forte perante um clone autónomo fora da mediação.

## 2. Invariantes e vocabulário de análise

[R2 C1–C7](../../auth-boot-02-r2.md), [D09/D10](../../auth-boot-02-r1.md) e [B-L v1.0](../d09-06-bl-conditional-20261030/SPECIFICATION.md) regem a análise. Autoridade R2 única; operador humano único; domínios R2/execução/D09 distintos, com independência perante poderes delimitados por demonstrar. Comprometimento total dos poderes do operador e de toda a recuperação permanece excluído; credencial limitada não recebe essa exclusão se alcançar transitivamente todos os fundamentos pertinentes.

Conservam-se os rótulos P0–P6, K, L, M, T, W/D09, V e J da C4 v0.2. K é a continuação viva original ligada ao alvo/geração, executor/encarnação e sessão/transação reais. L é a memória durável de uso, sem autoridade para aprovar. J é a entrada aceite no corpo da operação fixa, incluindo início abortado/sem efeito. M conduz a execução; T impõe no alvo; W preserva/confirma; V observa. Q, usado abaixo, designa apenas o passo local candidato de retirar a possibilidade de uma segunda travessia. Não é novo campo, evento normativo, gate ou protocolo aprovado.

Os vínculos C4 completos são pedido, participantes, finalidade, operação, gate, ambiente, plano, digests, destino/geração, executor/encarnação e sessão/transação protegidas. K não substitui essa lista. Identificadores, certificados e nonces copiados não provam a identidade real ou singularidade da continuação.

Primeira classe: UPDATE fixo de laboratório, sem extensão a DDL/Alembic, comandos administrativos, filas ou efeitos externos. Progbox apenas DEV; STAGING/PROD em VMs Proxmox; LiveNet interno ao laboratório. Não se escolhem nós/VMs, contas, produtos, formatos, chaves, retenção ou RPO/RTO. Não se exige hardware novo, terceiro ou segundo operador.

## 3. I-01 — decomposição da ligação singular P4–J

### 3.1. Três obrigações diferentes

| Obrigação | Onde atua na candidata | Contraexemplo que a obrigação isolada não evita |
| --- | --- | --- |
| Atribuir no máximo uma oportunidade por aprovação/tentativa | P2, em L, com vínculo a K e consumo R2 preservado. | Um único registo «gasto» pode ser lido por dois workers que ambos despacham. |
| Usar essa oportunidade numa única entrada real | Entre P4 e J, no controlo vivo de T. | Dois K copiados ou duas entradas na mesma sessão podem usar o mesmo recibo. |
| Impedir efeito por todos os meios pertinentes | T e fronteira efetiva de dados/execução/recuperação, até término e corte. | SQL direto, raw ou clone pode escrever sem passar por J ou produzir ledger. |

Não basta tornar o UPDATE idempotente ou obter um só commit. O contrato limita iniciação e contorno. Um cenário com dois J e payload final único refuta a propriedade; uma escrita raw sem J refuta mediação, mesmo com zero entradas registadas.

### 3.2. Regra local candidata Q, sem implementação

Uma composição possível prepara, em P0, um contexto inerte **interno ao componente confiado T**. A relação com a sessão/transação real é estabelecida por T e incluída no vínculo admitido por R2; não é aceite como parâmetro escolhido livremente pelo cliente. Só a continuação original pode levar esse contexto através de P1/P2/P3 até P4. Slots/contextos duplicados para a mesma oportunidade têm de ser impossíveis ou recusados, não apenas ter nomes diferentes.

No limite P4–J, um controlo local de uso único realizaria uma transição indivisível de «passagem ainda não usada» para «passagem indisponível», Q. Apenas a invocação original que efetua essa transição pode continuar para J. Uma chamada concorrente ou reentrante encontra passagem indisponível e é recusada antes do corpo. Ler o estado indisponível nunca devolve direito de continuar. Q não é aquisição de lock reentrante e não é um recibo que se possa reenviar.

Essa indivisibilidade é uma **primitiva candidata a demonstrar**: por exemplo, uma troca condicional de estado interno de um runtime confiado, fora das alterações revertidas pela transação SQL. Não se afirma que uma função SQL, extensão, variável de sessão ou PostgreSQL instalado já forneça essa semântica. O runtime, o seu estado e os caminhos que o invocam passam a integrar uma base confiada proposta, cuja adoção seria decisão material.

Q precede J e pode gastar a passagem sem entrada. Não há exigência de atomicidade entre Q e o efeito: qualquer crash/perda de K nesse intervalo termina sem retoma, conservando consumo e L. Uma exceção, abort ou savepoint não podem reconstruir a passagem. Não pode existir um handler de recuperação que leia Q/L e volte a chamar a operação.

Não se persiste um armamento recuperável para redispatch. Depois da morte do contexto, a memória durável serve para negar reatribuição, não para reconstruir K. Restart de serviço cria contexto novo sem direito da aprovação antiga. Snapshot de VM com memória ou clone do runtime pode duplicar a própria continuação; a regra local não o contém sem fundamento externo efetivo. Esta fronteira integra I-04 e impede apresentar a memória local como solução universal.

Se o catálogo futuro classificar uma transição adicional pré-J como evento crítico a confirmar, a sua preservação/confirmação D09 terá de anteceder a progressão dependente, **sem rearmar Q ou duplicar a continuação**. Não se classifica unilateralmente Q como evento dispensado de D09. A sequência aprovada exige os conteúdos críticos existentes antes da disponibilização; início/commit futuros só se preservam quando observados. Esta análise não aprova catálogo ou schema.

### 3.3. Argumento condicionado de início único

Premissas a demonstrar cumulativamente:

1. R2 admite uma única tentativa com todos os vínculos; L compromete uma única oportunidade para o K exato e não a devolve por rollback, crash ou recovery.
2. Não há dois contextos reais capazes de usar essa oportunidade; o vínculo K deriva do controlo confiado e não de identidade copiável apresentada pelo cliente.
3. T efetua Q uma única vez, fora do rollback do efeito, e só o percurso original vencedor pode seguir a J; nenhum retorno, callback, comando ou consulta o recria.
4. Toda entrada capaz de efeito atravessa a imposição, sem escritor alternativo sob poderes cobertos, e a continuidade relevante não é revertida/copiada pelo adversário.
5. Trabalho aceite permanece contido até término; recuperação não rearma capacidades e o corte cobre todos os meios pertinentes.

Se existirem dois J, ou houve duas oportunidades/contextos (falha de 1/2), ou a mesma oportunidade atravessou duas vezes (falha de 3), ou houve entrada fora da cobertura/continuidade (falha de 4/5). Isto é argumento de desenho condicionado, **não prova das premissas**. Em particular, a premissa 2 não pode ser resolvida escrevendo «K é não copiável». Qualquer cenário que permita copiar runtime ou meio gravável conserva o bloqueador.

## 4. Três composições concretas, sem adoção

Os identificadores CAND-1/2/3 são editoriais. Todas conservam P1 → P2 → P3 → P4 → J → término e admitem consumo sem execução. As diferenças são de localização de L e propriedade do fluxo; todas precisam de T obrigatório, Q ou equivalente demonstrado, e continuidade fora das falhas cobertas.

### CAND-1 — compromisso no domínio R2, contexto de entrada no backend protegido

**Composição:** M detém a ligação e a transação PostgreSQL da operação fixa; o executor não detém a credencial de escrita nem comanda a transação. T teria um controlo interno obrigatório associado àquela encarnação real do backend e a K. Após P1, uma transição durável adicional no domínio R2 registaria a oportunidade L para o mesmo K. W confirma o conteúdo pertinente de P1/P2. Só o fluxo original com essas confirmações pode armar a passagem local de T e atravessar Q/J uma vez.

**Limites de confiança:** R2 continua única autoridade; L não reavalia elegibilidade nem cria segunda aprovação. Novas transições/interfaces no domínio R2 exigem especificação e aprovação próprias. M, T, configuração, código privilegiado e recovery precisam de estar fora do alcance do executor. Nenhum ID de backend fornecido pelo cliente é prova suficiente. A ligação não pode ser trocada pelo mediador depois da admissão.

**Crash:** se R2/L confirmaram e a resposta se perde ou K morre, não se reconsulta para obter autorização de despacho. W/ledger permitem reconciliar, sem recriar backend/armamento. Se a ligação antiga apenas perdeu comunicação, não se presume terminada; C5 e I-04 continuam aplicáveis.

**Limite:** R2 durável não prova que o backend não foi duplicado, que T cobre SQL privilegiado/raw ou que o administrador do alvo não removeu a guarda. Um controlo no backend é nova superfície a propor, não capacidade nativa demonstrada. Aumenta-se a especificação do domínio R2 sem resolver o clone.

### CAND-2 — compromisso num mediador confiado sem recuperação de tarefas

**Composição:** M tem um diário durável próprio, separado da transação do payload e do domínio do executor. L é acrescentado uma única vez para a admissão/K originais, antes de W confirmar a preservação correspondente. M mantém um único dono vivo da tentativa e da ligação protegida; T conserva a imposição de entrada singular no alvo. O diário não é outbox de execução: «reservado» ou «gasto» não gera tarefa ao arrancar.

**Limites de confiança:** introduz-se estado confiado de mediação e o seu recovery, além de R2 e W. A verificação de L por T precisa de origem e vínculo demonstráveis sem token reutilizável pelo executor. Recuperação do diário não concede despacho; ausência de registo após restore não prova oportunidade livre. M não pode aceitar comandos que alterem destino, transação ou payload admitidos.

**Crash:** depois de L e antes de J, perde-se disponibilidade da tentativa, sem worker substituto. O retorno de um M antigo e uma cópia do diário não podem concorrer; é preciso fundamento para excluir capacidades anteriores. Dois workers que leem a mesma entrada já comprometida são o contraexemplo direto: nenhum pode transformar essa leitura em continuação original.

**Limite:** um único worker, mutex de M ou fila com deduplicação não prova a entrada singular em T nem a mediação completa. Se a mesma mensagem chegar duas vezes à mesma sessão, T ainda precisa de recusa pré-J. A base confiada adicional e as suas credenciais podem aumentar o alcance de um comprometimento. Não resolve clone do alvo ou snapshot vivo de M/T.

### CAND-3 — compromisso persistente no alvo, fora do rollback do payload

**Composição:** T teria uma primitiva de registo L persistente por aprovação/K, num domínio de persistência separado da transação do efeito. O contexto K é preparado antes de A; o registo de oportunidade só é confirmado após P1 e antes de W/P4. O mesmo controlo de T associa a oportunidade à entrada Q/J. M pode conduzir o fluxo, mas o executor não escolhe outro backend para reutilizar a confirmação.

**Limites de confiança:** a primitiva precisa de durabilidade, ordenação e tratamento de crash próprios, sem tornar o alvo autoridade de admissão ou misturar o estado autoritativo R2 com as bases LiveNet. Uma tabela na mesma transação do UPDATE não satisfaz isso; uma segunda conexão também não garante, por si, continuidade ou vínculo singular. Restore do alvo não pode apagar o uso e permitir nova atribuição.

**Crash:** uma gravação incerta bloqueia; nunca se interpreta ausência pós-restore como livre. Recuperação em quarentena compara fundamentos externos suficientes (R2, W e referências sobreviventes), sem reconstruir continuação viva a partir do registo. Não se exige confirmar J inexistente para confirmar L.

**Limite:** proximidade do controlo ao efeito reduz uma distância lógica, mas não impede que o poder sobre os discos/runtime reverta ambos. Persistência local não constitui continuidade externa. Qualquer extensão, journal ou ligação externa específica seria mecanismo novo por aprovar, sem instalação nesta etapa. O alvo copiável continua sujeito a I-04.

### Comparação para revisão

| Tema | CAND-1 | CAND-2 | CAND-3 |
| --- | --- | --- | --- |
| Memória L | Domínio R2, em transição própria depois da admissão. | Diário confiado M, sem redispatch de entradas. | Persistência própria do alvo, fora do rollback do payload. |
| Principal ponto de prova I-01 | Vínculo causal R2/L ↔ contexto real T e Q. | Dono vivo M não duplicado ↔ entrada única T. | Durabilidade própria L ↔ uso local singular e continuidade externa. |
| Base confiada a declarar | R2 ampliado, M, T e recovery pertinente. | M/diário/recovery adicionais, T, interfaces com R2/W. | Primitiva privilegiada/persistência T, M e validação externa de recovery. |
| Perda após P2 | Consumo sem execução, sem nova autorização por consulta. | Nenhum worker de recuperação de tarefa. | Nenhum rearmamento por journal/restore. |
| Desvantagem dominante | Alterações no domínio autoritativo e vínculo distribuído. | Novo estado/poder de mediação e risco de transformar log em fila. | Estado copiável no alvo e semântica de persistência/crash própria. |
| I-02/I-04 | Exigem cobertura integral de escritores, administração e clones. | Idem; M exclusivo não substitui T. | Idem; proximidade não contém root/storage adversarial. |

Nenhuma é selecionada ou declarada exequível com os recursos atuais. Compará-las não adota novo fundamento de confiança. Prosseguir documentalmente deve procurar refutações e necessidades de confiança de cada composição, não concluir «ALT-C aprovada» a partir da aprovação C4 v0.2.

## 5. I-02 — mediação completa por via de efeito e poder

O ponto de confiança é o **último controlo que qualquer poder coberto precisa de atravessar antes de produzir efeito**, não o primeiro proxy do percurso esperado. A observação de bypass deve abranger payload/efeito, mesmo sem consumo ou ledger. ACL e restrições de clientes podem contribuir para um modelo limitado, sem conter automaticamente administração privilegiada.

| Via/poder | Obrigação candidata de mediação | Contraexemplo analítico | Condição de demonstração |
| --- | --- | --- | --- |
| Cliente/executor e SQL direto | Só operação fixa com vínculos reais; nenhum escritor alternativo, conexão livre ou alteração do payload admitido. | Função chamada diretamente altera dados com zero consumos externos. | Mostrar que o controlo recusa antes do corpo e observar payload por fonte independente. |
| Owner/superuser e alteração de catálogo | Poder coberto não remove T, troca função, atribui escritor ou muda validadores. | Administrador remove guarda e faz UPDATE fora do fluxo. | Delimitar poder transitivo e mostrar fronteira efetiva fora dele; não presumir ACL suficiente. |
| SO, filesystem, hipervisor e deploy | Executor/poder delimitado não lê credenciais M/R2/W, modifica runtime/dados, consola ou recovery pertinente. | Root na VM do alvo escreve raw ou substitui binário T. | Fronteira concreta ainda por propor; se o poder coberto a alcança, a candidata falha nesse cenário. |
| Sessões/transações antigas | Nenhum contexto migra; proteger trabalho até término; antigo não volta a escrever após corte terminal. | Nova chave bloqueia logins, mas transação antiga confirma depois. | Evidência de término ou exclusão do efeito em todos os contextos antigos, não só de novos acessos. |
| Mesma sessão/callback/concorrência | Q ou equivalente nega segunda entrada mesmo dentro do mesmo backend. | Lock reentrante aceita duas chamadas; só um commit mascara dois inícios. | Observar J separado de commit e provar transição não reentrante. |
| Rollback/savepoint/exceção | Consumo/L/Q não regressam com payload; comandos de transação do executor não desmontam a proteção. | Rollback do marcador ou libertação da guarda permite segunda chamada. | Análise de todas as saídas de erro e recursos adquiridos antes/depois de savepoint. |
| Trabalho preparado, assíncrono ou delegado | Resolver ou impedir pendências capazes de efeito no âmbito; não ampliar a operação sem especificação. | Não há backend ativo, mas trabalho delegado ainda produz efeito. | Distinguir instrução preparada, transação preparada e outros trabalhos; nenhum efeito oculto fora da cobertura. |
| Réplica promovida, manutenção, restore e clone | Nenhum ramo executável recupera uso/capacidade antiga. | Cópia antiga conserva credencial e estado armado, escrevendo autonomamente. | Continuidade/exclusão externas ao conjunto copiável; sem isso I-04 bloqueia. |

Uma separação executor–M não prova separação executor–T; uma credencial pode atravessar ambos por consola, reset ou deploy. A exclusão do comprometimento global não autoriza retirar o superuser/root de um cenário em que foi incluído. Se a única alternativa funcionar com esse poder confiado, a mudança de ameaça/base confiada deve ser explicitada antes de adoção.

### 5.1. Primitivas isoladas insuficientes e fontes primárias

As referências são PostgreSQL 16, versão histórica dos laboratórios, **sem verificar versão instalada ou configuração atual**. Não se presume que documentação de produto prove arquitetura LiveNet.

- Locks adquiridos após savepoint podem ser libertados pelo rollback correspondente; advisory locks são cooperantes e podem ser readquiridos pelo seu dono. Inferência: não são, isoladamente, memória irrevogável ou passagem de uso único. [Explicit Locking](https://www.postgresql.org/docs/16/explicit-locking.html).
- Superuser contorna verificações de permissões, salvo LOGIN. Inferência: ACL/função não contém esse poder quando incluído na ameaça. [Role Attributes](https://www.postgresql.org/docs/16/role-attributes.html).
- `nextval` não devolve valor por abort, mas a documentação distingue persistência após crash e utilização externa. Inferência: uma sequência não fornece, sozinha, vínculo por aprovação/K, entrada única e continuidade de recovery. [Sequence Manipulation](https://www.postgresql.org/docs/16/functions-sequence.html).

Uma restrição única transacional, broker, sequência, assinatura, epoch ou nonce também não demonstra toda a cadeia. Nenhuma afirmação acima recomenda instalação, extensão ou produto; Q é primitiva hipotética cujas semânticas faltam provar.

## 6. Falhas prioritárias entre confirmação e entrada

As linhas são contraexemplos/condições de evidência futura, não testes realizados ou autorizados.

| Interleaving | Resultado exigido | Refutação observável |
| --- | --- | --- |
| P1 confirmou, ack R2 perdeu-se | UNKNOWN/BLOCKED sem despacho; consumo pode existir. | Consulta devolve nova permissão ou reenvio inicia operação. |
| P2 confirmou, ack L perdeu-se | Não repetir reserva/reatribuir oportunidade; reconciliar factos. | Leitura posterior de L «gasto» cria worker autorizado. |
| W preservou, confirmação ainda desconhecida | Antes de P4, sem disponibilização. | J só com recibo local ou afirmação do executor. |
| Duas chamadas com mesmo vínculo depois de P3 | Apenas o contexto original pode satisfazer P4 e uma travessia Q. | Dois J, mesmo em sessão única ou com zero commits. |
| Q retirou passagem, antes de J ocorre crash | Aprovação/L continuam indisponíveis; zero início admissível. | Recovery interpreta «sem resultado» como tarefa por executar. |
| Erro depois de J e rollback a savepoint | Nenhuma segunda iniciação. | Retorno ao estado de passagem livre. |
| Comunicação M–T perde-se depois de J | Resultado incerto, sem substituição de ligação/retoma automática. | M novo recebe estado e volta a executar. |
| K permanece vivo e resposta original chega tarde | Só continuação original ainda íntegra avalia requisitos restantes. | Resposta atrasada é aceita por novo contexto; prazo de A é deslocado para commit. |
| Snapshot com memória de P4/Q é retomado duas vezes | Não alegar singularidade sem prova de exclusão externa das cópias. | Duas continuações locais consideradas originais. |
| Corte pedido durante trabalho já aceite | Não confirmar terminal antes de término/exclusão demonstrados. | Commit antigo posterior à confirmação terminal. |
| Restore simultâneo de R2/L/W/T | Quarentena se não houver fundamento sobrevivente suficiente. | Estado coerente antigo, assinado de novo, rearma aprovação. |

C5 permanece intacta: depois das condições prévias, partição posterior não revoga retroativamente a admissão e só o original continuamente vinculado pode prosseguir. Informação em falta bloqueia a progressão dependente; não demonstra morte do original. Nenhuma nova política de timeout, lease, retry ou reconexão segura é introduzida. Nova tentativa exige reconciliação, invalidação antiga demonstrada, novo pedido e nova aprovação humana, com gates aplicáveis.

## 7. I-03 — conteúdo e confiança suficientes sem novos schemas

Esta secção propõe obrigações semânticas para comparação, não um catálogo fechado ou codificação aprovada.

| Conjunto a preservar/verificar | Conteúdo suficiente pretendido | Insuficiente ou proibido |
| --- | --- | --- |
| Admissão R2 | Relação recuperável entre pedido/decisão humana, admissão durável, consumo, todos os vínculos C4, ordem com revogação/epochs/política e evidência essencial. | Digest/ID isolado, declaração do executor, assumir commit pela existência de pedido. |
| Compromisso L | Relação irrevogável com admissão/K/contexto real e fundamento para negar reatribuição. | Marcador «reservado» convertido em direito recuperável de despacho. |
| Confirmação W | Conteúdo efetivamente preservado, proveniência, pertinência exata e referências de continuidade verificáveis fora do poder coberto. | Assinatura sem conteúdo recuperável ou confirmação válida para outro contexto. |
| Factos de execução | J, mutações, commit/abort, resultado conhecido/incerto e término observados por fontes adequadas quando ocorrerem. | W arquivar alegação de M/T tomado como prova física independente; ausência de ledger como zero efeito. |
| Recovery/corte | Histórico suficiente incluindo transições pós-backup, divergências, alcance do corte, capacidades antigas e evidência de invalidação. | Snapshot coerente ou epoch maior tomado como atualidade/exclusão universal. |

A suficiência é relativa à reconstrução das relações e às falhas/poderes cobertos, não à quantidade de recibos. O fundamento de confiança precisa de sobreviver fora da falha e do alcance de eliminação/modificação considerado. O mesmo operador pode administrar os domínios; isso não cria independência administrativa absoluta.

Divergência, conteúdo incompleto, mesma identidade com bytes diferentes, confirmação para outro contexto ou continuidade incerta mantêm UNKNOWN/BLOCKED e quarentena. Reconciliação acrescenta evidência, sem reescrever consumo/ordem/vínculos. Nenhuma consulta, exportação ou retransmissão documental devolve capacidade.

D09 continua confirmação independente pertinente antes do percurso executável. [V05-06](../../../specifications/f0/dr07-retention-addendum.md) é demonstração independente de preservação/separação/continuidade no seu âmbito: cumulativa, sem substituir D09 ou ser dispensada por ele. COMPROVADO não autoriza destruição. Retenção R2/condição final TBD conservadas; 900 segundos limitam elegibilidade em A, não retenção, início ou commit. C3/C7 conservados, sem novo schema, campo ou bytes de assinatura.

## 8. I-04 — corte terminal e limite que nenhuma composição remove

Três objetos diferentes devem ser considerados: impedir nova entrada, terminar/excluir trabalho já aceite e impedir efeito em cada meio autónomo pertinente. Q pode servir o primeiro dentro de um runtime; não prova os outros dois.

Alternativas de contenção a comparar, sem escolher atuador:

| Família | O que poderia sustentar | Limite que permanece |
| --- | --- | --- |
| Drenar sob T mantendo exclusão | Esperar término do trabalho já aceite antes de declarar corte terminal. | Não há prazo garantido; precisa de cobertura de todas as pendências e nenhum caminho alternativo. |
| Abort/término imposto por controlo confiado | Retirar capacidade do contexto antigo e demonstrar resolução do trabalho pendente. | Ack do comando não prova término; controlador precisa de estar fora do poder coberto. |
| Retirar capacidade do meio de efeito | Complementar com controlo persistente no recurso/storage/fabric quando houver proposta concreta. | Não apaga efeitos anteriores, não cria início único e não alcança automaticamente cópias noutros meios. |

Em múltiplos recursos, a confirmação global só é justificável depois de todos os cortes e da manutenção contínua dos anteriores. Um recurso reaberto antes do último destrói essa conclusão. Nova chave, epoch, NOLOGIN, ausência de heartbeat ou rede desligada não substituem demonstração de alcance e término.

**Clone integral gravável autónomo adversarial:** pode conservar o payload, o runtime armado ou uma via raw. Negar admissão R2 ou confirmar W do original não retira o poder de efeito no clone. Não existe neste documento resolução dessa capacidade. Sem prevenção demonstrada da criação/escrita sob os poderes aprovados ou exclusão efetiva de todos os meios relevantes, a garantia forte e a reentrada correspondente continuam bloqueadas.

Restringir o efeito ao endpoint oficial, retirar poder de leitura/exportação/backup/restore ou confiar num novo fundamento global mudaria o problema. Essas alternativas não são adotadas nem se exige ao humano escolher uma agora para permitir a análise. Se forem propostas para adoção, exigem decisão material explícita com consequências. O3 não aprovado, DEV-09B não autorizado; não se altera requisito para declarar I-04 fechada.

## 9. Sete cenários, evidência sobrevivente e cobertura desta análise

| Cenário B-L | Aplicação a CAND-1/2/3 e bloqueio requerido |
| --- | --- |
| 1. Falha VM/serviço | R2/L/W e confiança suficientes fora da falha respetiva. K morto não se reconstrói de diário/backup. Quarentena e reconciliação sem redispatch. |
| 2. SO LiveNet comprometido | R2/W/M/T/L e recovery pertinentes fora de todo o alcance transitivo do executor; vias da §5 precisam de mediação. Se remover T/escrever raw, a candidata falha. |
| 3. Perda de nó Proxmox | Conteúdo/confiança suficientes fora do nó e dependências comuns; sem autoridade concorrente. Tratar capacidade antiga no regresso antes de reentrada. |
| 4. Synology indisponível | Preservação crítica e recovery sem dependência exclusiva direta/indireta do NAS. Bloquear progressões afetadas; C5 preservada para original contínuo. |
| 5. Storage partilhado corrompido/eliminado | Conteúdo recuperável e referências fora do domínio/poder de eliminação; ausência de L após perda não significa livre. |
| 6. Credencial administrativa limitada comprometida | Incluir reset, delegação, consola, deploy, chaves e recovery; separação nominal de M/L/T não basta. Controlos não alcançados impõem bloqueio. |
| 7. Comprometimento transversal e de toda a recuperação | Fora da garantia; nenhum controlo confiável pressuposto, sem promessa de recuperação segura por componentes todos comprometidos. |

Sem HA/failover automático ou D09 como autoridade substituta. Recuperação D10: conservar caso/divergências; reconstruir em quarentena com conteúdo/confiança/continuidade suficientes; reconciliar efeitos; invalidar capacidades antigas; verificar R2 único/D09; decisão humana autenticada/auditada; novo pedido e nova aprovação para nova tentativa. Não se salta I-04 por aceitar o documento.

## 10. Condições de demonstração e resultado revisto

Não se autorizam ensaios por enumerá-los. Cada linha define o que uma futura proposta/realização precisaria de sustentar, com observação independente do controlador verificado e sem inferir zero efeito de um ledger vazio.

| Lacuna | Demonstração futura necessária | Refutação suficiente | Estado após este documento |
| --- | --- | --- | --- |
| I-01 | Relação real K/admissão/L; uma atribuição e uma travessia Q/J; comportamento de erros, concorrência e morte do contexto sem rearmamento. | Dois J por aprovação, incluindo mesma sessão/zero commit; diário recria trabalho. | Aberta, prioritária; decomposição e três composições analisadas. |
| I-02 | Todas as vias/poderes da §5 ligados à fronteira que realmente impede efeito; observar bypass sem ledger. | Qualquer efeito por caminho coberto que evita T ou remove a guarda. | Aberta, prioritária; mapa de obrigações sem topologia verificada. |
| I-03 | Conteúdo recuperável e confiança suficientes, anterioridade causal, completude e continuidade pós-backup fora das falhas/poderes cobertos. | Ack sem conteúdo suficiente; estado antigo coerente aceito como atual; consulta emite capacidade. | Aberta; obrigações semânticas explicitadas, sem schema/retenção escolhidos. |
| I-04 | Corte terminal/persistente de trabalho antigo e todos os meios, sem reabertura; clones contidos dentro da ameaça aprovada. | Commit antigo após corte; qualquer escrita autónoma em clone não excluído. | **Bloqueadora; clone integral gravável não resolvido.** |

As condições não renumeram RG1–RG7, GAP/H existentes ou gates. Ensaios finitos futuros seriam evidência de âmbito limitado e não aprovação universal; esta etapa não realizou nenhum. Se a observação não cobre iniciação ou bypass, a conclusão permanece indeterminada, sem declarar a garantia satisfeita.

## 11. Próxima revisão e decisões materiais reservadas

Objeto proposto para revisão: adequação da decomposição Q/J, comparação CAND-1/2/3, cobertura de poderes/vias, conteúdo/confiança e critérios de refutação. Uma aceitação desta análise seria documental condicionada; não escolheria composição, runtime, extensão, persistência ou corte.

Não é indispensável decisão humana intermédia para elaborar/comparar estas hipóteses. Antes de adotar uma delas, deve ser apresentado: qual primitiva fornece Q; onde L reside e como recupera continuidade; quem controla M/T, dados e recovery; como são mediadas as vias privilegiadas e antigos contextos; qual capacidade de clone subsiste. Qualquer alteração material de poderes/base confiada/garantia ou normativa regressa ao humano nesse ponto. Nenhuma escolha é feita nesta entrega.

Continuação documental recomendada: procurar contraexemplos às premissas de §3.3 para cada composição e explicitar o mínimo de confiança exigido, com prioridade I-01/I-02 e mantendo o impedimento I-04. A análise pode avançar no âmbito autorizado sem voltar a aprovar C4 v0.2 ou B-L v1.0.

P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados/bloqueantes; H02–H12 e GAP-001/002 pendentes/abertos e bloqueantes conforme os registos; RG1–RG7, R2 D09 e V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial. C4 v0.2 aprovada documentalmente, presente proposta candidata e I-01–I-04 sem fecho técnico.

[Fontes, preservação e revisão desta entrega](REVIEW.md). Sem código, SQL executado, testes/ensaios, alteração operacional, infraestrutura/serviços, commits, pushes ou merges.
