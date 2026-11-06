# B-L — proposta técnica documental da disponibilização e imposição C4

Versão candidata: 0.1 · 30/10/2026 · Europe/Lisbon.
Estado: **PROPOSTA TÉCNICA PARA REVISÃO; NÃO APROVADA NEM IMPLEMENTADA**.

## 1. Resultado e classificação das afirmações

A [especificação B-L v1.0](../d09-06-bl-conditional-20261030/SPECIFICATION.md) está aprovada documentalmente de forma condicionada, conforme [ato posterior](../../decisions/d09-06-bl-v1-approval-20261030.md). Os seus bytes permanecem inalterados. A presente proposta aprofunda as obrigações técnicas sem selecionar arquitetura física, produto, protocolo ou formato executável.

**Estabelecido:** autoridade R2 única; consumo/vínculos/ordem/evidência local confirmados conjuntamente; D09 independente anterior ao percurso executável; imposição C4 que resista ao executor comprometido; C5 e D10; B-L sem dependência exclusiva do NAS; operador único e exclusão do comprometimento total dos seus poderes e de toda a recuperação.

**Candidato:** mediação confiada fora do executor, ligada à barreira no alvo, com registo de início não reversível pela transação do efeito e um único contexto vivo de execução. A recomendação para aprofundamento é a combinação ALT-C da secção 9. Não se declara essa combinação aprovada ou realizável com os recursos atuais.

**Por demonstrar:** implementação do vínculo efetivo, impossibilidade de segunda iniciação/contorno, durabilidade do registo e corte, alcance transitivo dos poderes, conteúdo e continuidade D09, recursos e recuperação. A existência de uma cópia integral gravável autónoma adversarial mantém bloqueada a garantia forte: um controlo no original não impede a escrita nesse meio.

Não se exige segundo operador, novo hardware ou serviço externo ao laboratório. R2, D09 e execução continuam funções distintas; as novas letras abaixo designam funções internas candidatas, não novas VMs ou autoridades. Escolhas materiais ficam explícitas para revisão, sem execução antecipada.

## 2. Propriedades a satisfazer separadamente

| Propriedade | Critério técnico | Insuficiente como prova |
| --- | --- | --- |
| Admissão única | Uma aprovação admite no máximo uma tentativa imutavelmente vinculada, com consumo durável em R2. | Um efeito final ou um recibo único. |
| Anterioridade D09 | Conteúdo crítico necessário à disponibilização está preservado e confirmado independentemente antes da abertura do percurso. | Ordem aparente de timestamps ou assinatura do executor. |
| Iniciação exclusiva | No máximo uma entrada aceite na operação protegida por aprovação, mesmo que aborte ou produza zero commits. | Unicidade numa tabela que reverte com payload; idempotência do resultado. |
| Mediação completa | Toda via capaz de produzir o efeito atravessa a mesma imposição, inclusive chamada direta e poderes cobertos. | Proxy acessível mas SQL alternativo, owner ou superuser não controlado. |
| Contexto não transferível | A capacidade só pode ser usada pelo fluxo original, no destino/geração, encarnação e sessão/transação vinculados. | Identificador/nonce/certificado copiável apresentado como bearer token. |
| Continuidade/invalidação | Consumo e início não regressam com restore; capacidades antigas deixam efetivamente de produzir efeitos antes da reentrada. | Nova chave, epoch maior, reinício, ausência de resposta ou recibo local. |

«Iniciação» nesta proposta é a primeira entrada aceite pelo controlo do alvo no corpo da operação fixa; chamadas recusadas antes dessa entrada são tentativas de contorno observadas, não novas iniciações protegidas. Uma entrada seguida de erro/rollback conta como iniciação. Mutação física, commit durável e resposta são factos separados; efeitos num clone contam mesmo sem publicação. Nenhuma destas definições estreita o requisito forte histórico.

A primeira classe continua o UPDATE fixo de laboratório. Não se estende a Alembic, DDL, operações administrativas, filas ou efeitos externos por inferência. Se uma operação tiver múltiplos efeitos laterais, a cobertura e os pontos de término de cada um precisam de especificação própria antes de alegar esta garantia.

## 3. Localização lógica e base confiada candidata

| Função | Localização lógica e obrigação | Poderes do executor a excluir e demonstrar |
| --- | --- | --- |
| R2 | Fora da execução e do seu storage; única autoridade de admissão/ordem. | Alterar consumo, políticas, revogações, confiança ou recuperação R2. |
| W/D09 | Domínio distinto de R2/execução, sem dependência exclusiva Synology. Preserva/confirma, sem admitir. | Fabricar ack, editar conteúdo preservado ou substituir o validador/raiz usada para aceitá-lo. |
| M mediador | Função confiada fora do SO comprometido do executor. Detém o fluxo vivo e conduz apenas operação fixa. Não decide elegibilidade. | SQL arbitrário, acesso à credencial de M, alteração do seu software, memória, configuração ou recuperação. |
| T barreira no alvo | Verifica a conjunção de requisitos no ponto de iniciação e mantém exclusão até término relevante. Não é uma guarda apenas na UI/broker. | Remover T, chamar outra entrada de efeito, assumir owner/superuser ou escrever raw no meio protegido. |
| L continuidade de início | Registo candidato do compromisso irrevogável de uma única iniciação, fora do rollback/savepoint do payload e fora de D copiável. | Apagar, restaurar ou reatribuir a entrada de início e a continuidade que a torna atual. |
| V observação | Verifica início real, efeito/commit, corte e continuidade por fundamentos não adulteráveis pelo executor/controlador observado. | Editar captura, fazer passar ausência de ledger por ausência de efeito ou obter poder de escrita através do observador. |

M/T/L podem ser funções de um mesmo serviço confiado ou de componentes separados, se a solução escolhida demonstrar as propriedades. Duas conexões, bases, processos ou VMs não garantem independência ou durabilidade por si. Não se pressupõe que L já exista nem que um ledger transacional comum o implemente. Uma nova base confiada ou mecanismo de persistência é decisão arquitetural material antes da sua adoção.

O comprometimento de todo o SO do executor não pode incluir, por montagem, consola, chave, deploy, reset ou restore, o poder de remover M/T/L, falsificar W ou alterar R2. Se executor e alvo partilharem o mesmo poder de administração que permite esses atos, a resistência pretendida não está demonstrada. Segregar papéis SQL não contém root adversarial desse mesmo domínio.

Uma validação exclusivamente no executor falha no cenário 2. Uma validação exclusivamente em M também falha se T aceitar outro escritor. A barreira completa tem duas obrigações: M não disponibiliza sem as provas e T não admite iniciação por qualquer via que as contorne. São obrigações cumulativas, não duas autoridades de admissão.

## 4. Sequência candidata e pontos persistentes

Os rótulos K/J abaixo são notação analítica. Não são campos, estados operacionais, APIs ou bytes de schema aprovados.

| Passo | Pré-condição e ato candidato | Persistência / efeito de falha |
| --- | --- | --- |
| K0 contexto inerte | M/T preparam contexto vivo sem capacidade de efeito; associam principal real, recurso/geração, encarnação e sessão/transação protegidas ao pedido. | O vínculo que R2 confirma já tem de identificar esse contexto; não se escolhe livremente uma sessão depois da admissão. Perda do contexto impede execução. |
| K1 avaliação em A | R2 avalia elegibilidade na ordem serializada com revogações, epochs e política. | C2 aplica-se aqui, depois das esperas relevantes, sem deslocar prazo para commit. |
| K2 admissão durável | R2 confirma conjuntamente consumo, vínculos imutáveis, ordem e evidência essencial. | Sem confirmação durável/autenticada no percurso original: UNKNOWN/BLOCKED. Consumo real pode existir mesmo sem resposta. |
| K3 reserva/compromisso de início | L associa irrevogavelmente uma única oportunidade ao contexto original já admitido; não autoriza SQL por si. | Fora do rollback do efeito; nunca devolvida por timeout, abort, crash ou restore. Reserva incerta não se repete. |
| K4 preservação prévia | W preserva conteúdo crítico existente de K2/K3 e confirma a sua pertinência e continuidade. M/T verificam origem, completude e vínculos exatos. | Falta/divergência/ack perdido impede disponibilização. Confirmação não prova iniciação futura. |
| K5 disponibilização restrita | M/T habilitam somente o fluxo vivo original para cruzar uma vez a entrada protegida, com K2–K4, vínculo, continuidade, exclusão atual e gates satisfeitos. | Nada é entregue ao executor como token transferível/reemitível. Todos os gates atuais continuam fechados: este passo não é executável nesta etapa. |
| J iniciação no alvo | T consome logicamente a oportunidade do fluxo original e aceita uma única entrada no corpo da operação fixa. | Nenhuma outra chamada, inclusive na mesma sessão, pode entrar. Crash na janela entre compromisso e entrada pode gastar a aprovação sem início/efeito. |
| K6 término | T/M conservam proteção no recurso até commit/abort e término de todo trabalho capaz de efeito. | Resultado ou commit desconhecidos não permitem repetir. Efeito pode existir sem resposta. |
| K7 preservação posterior | Preservam-se início realmente observado, mutações, término e resultado quando conhecidos. | W confirma antes de progressão que dependa desses novos factos; não se exige preservar antecipadamente um resultado futuro. |

L não concede uma nova admissão: conserva o uso único da admissão R2, com o mesmo conjunto de vínculos. W não emite a oportunidade de execução: confirma a preservação pertinente. O alvo verifica os pré-requisitos, sem criar uma segunda ordem decisória de elegibilidade/revogação.

O requisito mais difícil de K3–J é impedir que «reservado» se transforme em direito de voltar a despachar. Na candidata, só a continuação viva original pode atravessar J; após perda dessa continuação, o registo gasto permanece indisponível. Se houver dúvida sobre se J foi atravessado, não se tenta novamente. A futura implementação deve demonstrar a impossibilidade de duplicar o fluxo por concorrência, reentrada de função, reconexão ou restauração. Persistir uma flag e depois chamar SQL não é, por si, essa demonstração.

Não se presume atomicidade R2–L–W–alvo. Cada intervalo pode acabar em consumo sem efeito e bloqueio indefinido. Não se promete exatamente uma vez. A alternativa de recuperar automaticamente trabalho «reservado mas ainda não feito» seria uma alteração material incompatível com a proibição de retoma automática aqui preservada.

## 5. Vínculos, frescura e confirmação sem circularidade

O pacote semântico a verificar liga aprovação/tentativa, pedido/participantes/finalidade, operação/gate/ambiente/plano/digests, destino/geração, executor/encarnação, sessão/transação e continuidade de R2/L/W/T. O alvo não aceita parâmetros do cliente como prova da sessão real. PID, nome, endereço, system_identifier, certificado ou contexto copiados não demonstram continuidade singular.

Uma confirmação W para outro conteúdo/contexto, uma confirmação histórica após restore, ou um novo desafio respondido por estado obsoleto não estabelecem continuidade atual. A verificação exige origem e estado de continuidade confiáveis, não só autenticidade de assinatura. A fonte de confiança e mecanismo concreto são pendentes; não se introduz nesta proposta novo formato de aprovação ou atestado.

K4 confirma eventos já existentes necessários a K5. J e commit são observados depois de acontecerem e preservados em K7. Assim não se usa a futura execução para provar a sua própria autorização prévia, nem se dispensa D09 alegando que ainda não há resultado. W arquivar a afirmação de T/M não demonstra que a atuação ocorreu: V precisa de observação própria do início, payload, término e corte.

Preservam-se C2/C3: UTC confiável e fórmulas contratuais em A, com máximo de 900 segundos e limites estritos; commit/efeito posteriores não são por si falha de elegibilidade. Revogação anterior na ordem autoritativa impede admissão; posterior não a cancela. Contenção física pode impedir efeitos sem apagar a admissão ou libertar consumo.

## 6. Cobertura adversarial e resíduos

| Via | Condição da candidata | O que refuta ou mantém bloqueio |
| --- | --- | --- |
| SQL direto / função autorizada | Toda entrada no alvo exige R2, W, L e contexto único; executor não possui escritor alternativo. | DEV-05 já mostra função direta com zero consumos externos e efeito. Confiar no broker repete a lacuna. |
| Owner, superuser, root/raw, extensões | Poderes incluídos na ameaça têm de ser contidos por fronteira que não consigam remover; poderes confiados devem ser declarados. | ACL local não contém superuser. Excluir silenciosamente esse poder ou confiar num trigger removível não passa. |
| Replay / concorrência / mesma sessão | Uma entrada J por aprovação; chamar novamente é recusado antes do corpo, mesmo que o resultado anterior seja zero. | Duas iniciações com um só commit refutam C4; idempotência não corrige. |
| Rollback e savepoint | R2 e L não são revertidos com payload; M/T não deixam o executor recuperar o direito por controlo transacional. | Ledger do efeito que desaparece ou lock adquirido depois de savepoint e libertado sem impedir reentrada. |
| Sessão antiga / transação aberta | Contexto antigo não migra; barreira do recurso protege até término, incluindo commit em voo. | Perder ligação à âncora externa e ainda confirmar depois do corte repete DEV-04. |
| Prepared statement / 2PC / filas | Distinguir instrução preparada de transação preparada. Resolver pendências ou provar exclusão verificável. | Lista de backends vazia não basta perante trabalho/efeitos pendentes não inventariados. |
| Restore / snapshot coerente | R2/L/W/T preservam continuidade fora do conjunto restaurável pelo poder coberto; instâncias recuperadas ficam em quarentena. | Estado antigo coerente com nonce novo, ledger e epoch antigos pode reabrir poderes. |
| Clone integral gravável | Cada meio de efeito pertence à cobertura ou a criação/escrita autónoma é impedida de modo demonstrável e aprovado. | Clone vivo escreve depois do corte do original: falha, mesmo se endpoint oficial o rejeitar. Continua bloqueador forte. |
| Cópias/exportações e re-registo | Backups, dumps, réplicas promovíveis, memória, reanexação e recuperação de credenciais entram na análise de capacidades. | Só olhar para o recurso ativo ou afirmar que cifragem/TPM resolve todos os meios é insuficiente. |

As limitações de SQL são confrontadas com documentação PostgreSQL 16, não com instalação atual presumida: superuser contorna verificações de permissões; locks normais podem ser libertados por rollback a savepoint; advisory locks exigem cooperação; sequências que não devolvem valores após abort não constituem consumo por aprovação resistente a crash/restore. As fontes e a distinção entre factos do produto e inferências constam de [EVIDENCE_AND_REVIEW.md](EVIDENCE_AND_REVIEW.md).

## 7. Incerteza, C5 e corte antes de reentrada

| Ponto incerto | Novas capacidades / nova iniciação | Tentativa original |
| --- | --- | --- |
| Confirmação R2 ausente/ambígua | UNKNOWN/BLOCKED; consulta apenas esclarece o registo. | Não despachar sem as confirmações exigidas no fluxo original. |
| L reservado ou W prévio incerto | Conservar consumo/reserva; não repetir reserva nem emitir ticket recuperado. | Falta de pré-requisito não permite cruzar J. Resposta original tardia só pode ser tratada no fluxo original contínuo, sem recriar contexto; timeout/perda de contexto já declarados não autorizam retoma por consulta. |
| Partição posterior a todas as confirmações e à disponibilização válida | Bloquear progressão nova que dependa de informação indisponível; não criar outro fluxo. | C5 permite prosseguir apenas se a execução original continua vinculada. Partição não revoga retroativamente a admissão. |
| Início/commit real com ack perdido | Sem retry, mesmo idempotente; preservar UNKNOWN e reconciliar. | Pode existir efeito; consulta posterior não repete, não migra sessão nem volta a iniciar. |
| Corte/fence com ack perdido | Não confirmar reentrada ou reaplicar cegamente como nova transição. | Pode ainda existir capacidade antiga: observar/conter efetivamente, sem declarar cessação por bloqueio administrativo. |
| Restore/continuidade desconhecida | Quarentena e recuperação humana D10. | Aprovação antiga indisponível; nenhum arranque reconstrói a oportunidade viva. |

Para cada recurso, a confirmação de corte tem de suceder ao término/abort do trabalho antigo capaz de efeito e à retirada persistente das suas capacidades em todos os caminhos. Em vários recursos, todos os cortes devem manter-se continuamente até a confirmação global. Drain pode esperar indefinidamente; abort só permite confirmação depois de término demonstrado, não do simples pedido de cancelamento.

Reentrada exige reconciliação, inventário de meios pertinente, invalidação demonstrada de capacidades antigas, continuidade suficiente e decisão humana autenticada/auditada, seguida de novo pedido e nova aprovação. Consulta, nova chave, epoch, backup ou decisão humana desacompanhada de prova não invalidam clones. Sem atuador/continuidade suficientes, aceitar perda de disponibilidade e manter bloqueio.

## 8. D10 e os sete cenários D09-03

| Cenário preservado | Fundamento sobrevivente e controlo de bloqueio na candidata | Evidência necessária / limite |
| --- | --- | --- |
| 1. Falha de VM/serviço | R2/W/L e observações suficientes fora da falha; T/M sobreviventes recusam pré-requisitos ausentes; componente recuperado em quarentena. | Recuperar eventos após backup sem redispatch; zero novas iniciações por restart. Se L não sobreviver, não deduzir que a oportunidade estava livre. |
| 2. SO LiveNet comprometido | R2/W/M/T/L e confiança pertinente fora do alcance transitivo do executor; T impede SQL alternativo e valida W. | Demonstrar barreira removível por nenhum poder coberto da VM. Se o alvo estiver sob esse mesmo root, a alegação falha. |
| 3. Perda de nó Proxmox | Conteúdo e confiança suficientes fora do nó; exclusão persistente nos meios sobreviventes; sem autoridade concorrente. | Nó antigo pode regressar. Provar invalidação de M/T/L/encarnações antigas antes da nova admissão; nós distintos não bastam. |
| 4. Synology indisponível | B-L preserva fundamentos críticos fora do NAS. M/T/R2 bloqueiam só progressões cujos requisitos se tornem indisponíveis. | Nenhuma dependência obrigatória indireta oculta. Original contínuo mantém C5; não prometer disponibilidade se rede/tempo/gestão comuns faltarem. |
| 5. Storage partilhado corrompido/eliminado | Conteúdo integral e continuidade fora do incidente/poder de eliminação; validadores sobreviventes recusam estado divergente. | Restaurar apenas com fundamento suficiente e consumos/inícios conhecidos; hashes isolados ou cópia no mesmo domínio não recuperam o perdido. |
| 6. Credencial administrativa limitada comprometida | R2/W/T/L e recovery pertinentes fora do alcance completo da credencial; controlos não alcançados impõem bloqueio. | Incluir reset, deploy, chaves, consolas e restore. Se a credencial chega a todos os fundamentos, a cobertura falhou; não a converter silenciosamente na exclusão total. |
| 7. Comprometimento transversal e de toda a recuperação | Fora da garantia aprovada; nenhum fundamento confiável é pressuposto. | Não prometer bloqueio técnico por componentes todos comprometidos ou recuperação segura sem restabelecer confiança. Não impor terceiro/segundo operador para prometer outra garantia. |

Recuperação acrescenta evidência, sem reescrever consumo/ordem/vínculos. A reconstrução de R2 único depende de estado e transições suficientes; W não se promove a autoridade e não se presume suficiente para reconstruir todas as funções. A oportunidade viva em M/T não é reconstituída a partir do log; capacidades antigas precisam de invalidação efetiva. RPO/RTO, mecanismos físicos e retenção continuam por decidir no respetivo âmbito.

## 9. Alternativas técnicas plausíveis

Nenhuma alternativa está selecionada operacionalmente. A comparação mantém a preferência B-L de alojamento/preservação já aprovada; avalia apenas como cumprir as suas obrigações C4.

| Alternativa | Vantagem técnica possível | Limitação decisiva | Evidência / decisão pendente |
| --- | --- | --- | --- |
| ALT-A — broker/proxy externo como única guarda | Pode reter credenciais e negar SQL arbitrário do cliente; separa lógica do executor. | Se T tiver acesso alternativo ou M validar e perder a guarda antes de commit, permanece contorno/DEV-04. Não resolve clone nem consumo não reversível. | Cobertura de todas as entradas e vínculo terminal. **Insuficiente isoladamente.** |
| ALT-B — imposição no alvo por função restrita ou extensão, associada a R2/W/L | A entrada do efeito pode verificar contexto e manter exclusão local até término. | Função/trigger/ACL podem ser contornados por administração coberta; ledger comum reverte com payload. Extensão implica superfície privilegiada e semântica/durabilidade a provar; não é instalada nem aprovada. | Mecanismo de registo não reversível, verificação obrigatória de todas as entradas, crash/savepoint, privilégios e restore. **Candidata local condicionada.** |
| ALT-C — M confiado com posse da sessão/transação, T obrigatório e L não reversível | Reduz controlo transacional do executor e liga disponibilização à entrada real, combinando mediação com imposição no recurso. | Amplia explicitamente a base confiada; ligação entre L e J não é atomicidade gratuita. Crash pode consumir sem iniciar. Não impede escrita num clone independente fora da fronteira. | **Recomendação para aprofundamento documental**, dependente de decisão da arquitetura lógica concreta M/T/L e prova dos vínculos, sem escolher produto/local físico. |
| ALT-D — corte persistente de storage/fabric/energia como complemento | Pode retirar capacidade antiga de meios inventariados sem cooperação do processo. | Não cria admissão/início único, não apaga efeitos anteriores, não corta cópia noutro meio nem prova D09. Recursos/compatibilidade/atuador desconhecidos. | Política de corte, cobertura e impacto são decisões próprias. Não é O3 aprovada por outro nome. **Complemento condicionado, não solução C4 isolada.** |

A recomendação ALT-C é uma inferência de desenho sobre as obrigações e contraexemplos, não uma escolha humana tomada pelo agente. Não se adota automaticamente extensão PostgreSQL, serviço dedicado, HSM, PKI, storage fencing, HA ou arquitetura física.

Se a única maneira de uma candidata parecer satisfazer C4 for retirar da ameaça um poder antes incluído, isso é alteração material de garantia e deve ser submetido expressamente. O mesmo vale para limitar efeitos ao endpoint oficial ou dispensar o clone. Nenhuma dessas decisões é executada nesta proposta.

## 10. Plano de evidência necessário, sem ensaios nesta etapa

| Evidência futura | Observação exigida | Refutação / resultado honesto |
| --- | --- | --- |
| Ordem de disponibilização | R2 durável e conteúdo W confirmado antes de K5/J, com vínculos e continuidade exatos. | Início antes da confirmação ou confirmação para outro contexto refuta. Confirmação ausente deve bloquear. |
| Consumo vs início vs efeito | Observar separadamente R2, L, entrada J, mutações e commit/abort, incluindo bypass sem ledger. | Um consumo e dois inícios refutam C4 mesmo sem segundo commit. Oráculo incapaz de ver mutação torna resultado indeterminado. |
| Replay e transação | Barreiras determinísticas em reserva, W, J, rollback/savepoint e chamada direta, na mesma e noutras sessões. | Libertar direito após rollback ou permitir função direta sem consumo refuta. |
| Perda de guarda/commit | Reutilizar os dois contraexemplos DEV-04 como requisitos de cenário, sem repetir agora: antes do SQL e depois da mutação antes de commit. | Confirmação de corte anterior a efeito antigo refuta; drain/abort precisam de término real. |
| Crash/ack perdido | Falhas distintas antes/depois de R2, L, W, J e término. | Nenhum recovery/consulta redispatcha; consumo sem efeito é resultado admissível, sem alegar exatamente uma vez. |
| Clone antigo vivo gravável | Sessão/contexto antigo permanece vivo; tenta escrita no seu próprio meio depois de confirmação de corte pretendida. | Qualquer efeito nesse clone refuta a garantia forte. Recusar confirmar é bloqueio seguro, não demonstra cessação universal. |
| Impossibilidade de clone, se alegada | Provar perante os poderes aprovados de leitura/exportação/backup/restore que não se cria meio autónomo gravável. | «Não há clone no teste» não prova prevenção. Reduzir ameaça requer decisão humana; não reclassificar o contraexemplo histórico como sucesso. |
| Recuperação e sete cenários | Conteúdo, confiança e controlo sobreviventes por cenário, eventos após backup e invalidação do antigo. | Ausência de continuidade/fundamento: UNKNOWN/BLOCKED. Assinatura/epoch isolados não passam. |

Cadeia de evidência e retenção devem permitir reconstruir o que foi observado, com fontes independentes da alegação que se verifica. W confirma conteúdo, não verdade física automática de M/T. Ensaios finitos produziriam evidência limitada ao seu âmbito, nunca aprovação universal ou abertura automática de gates.

D09 e V05-06 continuam distintos. V05-06 classifica demonstração independente em COMPROVADO/FALHA/INDETERMINADO; COMPROVADO não autoriza destruição nem substitui confirmação D09. Retenção R2 e condições de libertação TBD não se inferem dos 900 segundos ou da existência de backups.

## 11. Decisões materiais e próximos passos documentais

| Decisão pendente | Recomendação para revisão, sem adoção | Motivo de não ser decidida pelo agente |
| --- | --- | --- |
| Forma lógica M/T/L e base confiada | Aprofundar ALT-C, com funções mínimas e poderes explícitos. | Escolher mecanismo/novo fundamento de persistência ou confiança é material; nenhuma atribuição física aqui. |
| Proteção de K3–J | Demonstrar início não reversível e continuidade singular sem recuperação automática. | A propriedade não resulta de declarar um marcador durável; implementação/prova precisam de proposta específica. |
| Cobertura de clones/poderes | Manter bloqueador integral e exigir demonstração de exclusão de efeito ou prevenção de cópia dentro da ameaça aprovada. | Retirar meios/poderes ou mudar domínio do efeito alteraria a garantia. |
| Corte e recuperação | Requisitos terminal/persistente e invalidação antes de nova aprovação, sem mecanismo presumido. | Escolher atuador, impacto físico, regras de reabertura ou garantias de disponibilidade exige decisão própria. |
| Formatos e integração | Especificar separadamente quando o mecanismo candidato permitir proposta concreta. | C7 mantém 25 nomes, JCS/UTF-8 e Ed25519 puro; domínio R2 e schemas exigem aprovação específica, sem fallback R1. |

A análise editorial e a comparação reversível foram concluídas sem intervenção intermédia. Não se tomou decisão arquitetural material nem se abriu gate. O próximo passo recomendado é rever esta proposta e autorizar, se aceite, o aprofundamento documental de ALT-C que resolva a ligação K3–J e a cobertura de clone, antes de selecionar recursos ou implementar. Se esse aprofundamento exigir mudar ameaça/garantia, interromper nesse ponto com decisão concreta; não esconder a mudança como detalhe de implementação.

## 12. Estados e alcance final

B-L v1.0 aprovada documentalmente; esta proposta técnica 0.1 permanece candidata. P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados/bloqueantes; H02–H12 e GAP-001/002 bloqueantes; RG1–RG7/D09/V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial.

Sem implementação, SQL, ensaios operacionais, instalação, infraestrutura, atribuição física, commits ou pushes. Nenhuma variante desta comparação demonstra por si a garantia C4. Enquanto persistir clone integral gravável adversarial sem controlo suficiente, a garantia forte permanece inviável nos pressupostos atuais e a reentrada correspondente bloqueada.
