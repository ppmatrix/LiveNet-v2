# R2-DEV-08 — protocolo candidato de admissão, corte e reentrada

Estado: PROPOSTA NÃO APROVADA. Especificação comportamental para revisão, sem código, SQL, nomes de campos novos, bytes de assinatura ou schemas aprovados. «A» abaixo designa o serviço autoritativo; o ponto lógico A do contrato é a sua avaliação final serializada.

## 1. Contexto e invariantes

A candidata tem A único de admissão, B externo como único mediador da operação fixa, F atuador do corte, W/D09 de conteúdo/continuidade e V observador independente. Só é aplicável se H01/H02 aprovarem o domínio e demonstrarem a exclusão de cópia integral gravável adversarial de B. Caso contrário, o protocolo continua insuficiente para a propriedade forte.

Cada tentativa liga imutavelmente aprovação, pedido, participantes, finalidade, operação/gate/ambiente, plano/digests, recurso/geração, executor/encarnação e sessão/transação protegidas. O contexto de sessão/transação é criado por B antes da avaliação em A: contexto ainda inerte, de uso único, dentro de uma execução viva de B, sem permissão de mutação. IDs escolhidos pelo cliente ou copiados não provam continuidade. B deve vincular a ligação real, encarnação de B e recurso ao contexto. Implementação e representação dessa ligação exigem prova e aprovação próprias.

Distinguem-se três factos duráveis: consumo da aprovação em A; reserva única de iniciação em B fora da transação do efeito; início/resultado realmente observado. Nenhum se deduz dos outros. A reserva não é bearer token e não pode migrar para outra conexão, processo, transação ou recurso. O executor não recebe SQL arbitrário nem capacidade reutilizável; B detém o contexto e executa a operação fixa apenas quando todos os pré-requisitos forem satisfeitos.

O registo de reserva/início em B não participa de rollback/savepoint do payload. A implementação deverá conservar o marcador antes de tentar iniciar, permitir no máximo uma invocação no contexto vivo original e nunca reconstruir esse direito após crash/reconexão. Se crash ocorrer entre marcador e início, pode haver consumo e reserva gastos sem efeito. Um marcador durável não prova sozinho que não houve segunda iniciação: o ensaio deve observar entradas reais na operação e tentativas diretas. Não se pressupõe atomicidade entre A, B e W, nem execução exatamente uma vez.

## 2. Transições normais e confirmação D09

Os rótulos P0–P7 são posições de análise, não novos estados contratuais.

| Posição / transição | Pré-condição, ato e persistência exigidos | Falha e progressão permitida |
| --- | --- | --- |
| P0 quarentena → contexto inerte | V verifica inventário/continuidade e identidades; B cria a sessão/transação protegida inerte e vínculo ao pedido. Nenhuma mutação protegida. | Continuidade, UTC, custódia ou cobertura desconhecidos: BLOCKED, sem admissão/capacidade. |
| P1 contexto → decisão em A | A adquire serialização com todas as revogações de aprovação/chave/autoridade/política, epochs e política. A avaliação final usa UTC confiável atual após esperas relevantes. | Falha ou ordem desconhecida: sem autorização executável. Pedido de revogação não confirmado é pendente. |
| P2 avaliação → admissão durável | A confirma conjuntamente decisão, consumo, todos os vínculos imutáveis, ordem e evidência essencial. Aprovação fica indisponível para qualquer outra tentativa, independentemente de rollback posterior. | Resposta perdida: UNKNOWN/BLOCKED; nem A nem consulta posterior reemitem permissão/despacho. Commit real pode existir e deve ser reconciliado. |
| P3 admissão confirmada → reserva única em B | Só a execução original que recebeu confirmação durável/autenticada pode continuar. B valida diretamente a autoridade/continuidade e correspondência integral dos vínculos com a sessão/transação já criada; conserva reserva única fora do rollback do efeito. | Chamada direta, sessão divergente ou contexto perdido: recusa. Perda de resposta/continuidade na reserva: UNKNOWN; não tentar reservar novamente, iniciar ou transferir contexto. |
| P4 reserva → confirmação W pré-execução | W recebe conteúdo crítico já existente: pedido/decisão, admissão/consumo/ordem/vínculos, reserva e política/continuidade relevantes. W confirma conteúdo integral e posição/continuidade por canal autenticado próprio. B verifica confirmação vinculada ao mesmo contexto. | Falta, atraso, conflito ou ack ambíguo: BLOCKED; não disponibilizar percurso executável. Cópia de hash sem conteúdo recuperável não satisfaz D09. |
| P5 pré-execução confirmada → iniciação única | B gasta duravelmente o direito de início naquele contexto; W confirma esse evento prévio de compromisso de iniciação antes de B entrar na operação. Somente o fluxo vivo original atravessa a barreira de início uma vez, sob exclusão do recurso mantida até término. | Crash/ack perdido entre compromisso, W e início: sem repetição. Pode não haver início nem efeito; consumo permanece. Evento de compromisso não se apresenta como início observado. |
| P6 execução → término local | B mantém proteção no próprio ponto de efeito até commit/abort e término de todo I/O relevante. Regista início observado, mutações/commit/abort e resultado real, sem fabricar ausência quando perdeu observação. | Commit ou resultado incerto: UNKNOWN; consulta read-only não repete operação. Transação abortada não liberta aprovação/reserva. |
| P7 término → evidência confirmada | W confirma os eventos de início/resultado existentes; V confronta observações de payload e término com admissão e reserva. Só há progressão dependente destes resultados depois da confirmação requerida. | Falta/divergência W bloqueia progressão dependente e qualquer reentrada. Não se exige confirmar antecipadamente um resultado futuro. |

P4/P5 explicitam os cortes de D09: eventos pré-execução confirmados antes da capacidade/entrada; início físico e resultado confirmados quando efetivamente observados. Retransmitir o mesmo conteúdo documental para W, pelo produtor responsável e com deduplicação/conflito, não é repetir SQL nem emitir autorização. Uma consulta de estado pelo cliente nunca atravessa P3–P6. Em falha que quebre contexto/continuidade, obter depois uma cópia da confirmação não retoma o fluxo antigo.

Uma partição posterior a P5, mantendo confirmação prévia e execução original continuamente vinculada, não revoga a admissão: a tentativa pode concluir segundo C5, até contenção efetiva. W ausente bloqueia progressão que dependa de novos eventos; não se afirma que a ausência de W desfez trabalho em curso. Qualquer nova iniciação exige o seu próprio percurso admissível, nunca reutilização da mesma aprovação.

## 3. Elegibilidade, ordem e UTC

Em A mantêm-se `issued_at <= not_before < expires_at`, `expires_at - issued_at <= 900 segundos`, `L >= not_before` e `U < expires_at`. O intervalo [L,U] deve ser válido e sustentado por erro limitado/continuidade; intervalo invertido, fonte não autenticada, suspensão sem limites ou erro desconhecido impedem admissão. A escolha da fonte, bootstrap, erro e holdover não está feita. Autenticação NTS não elimina atraso assimétrico; [RFC 8915 §8.6](https://www.rfc-editor.org/rfc/rfc8915.html#section-8.6).

A transação pode confirmar depois do prazo, e entrega, mutação ou commit do efeito podem ser posteriores: C2 limita a avaliação final em A. Não se transfere o prazo para o commit ou para o fence. Revogação anterior na ordem autoritativa impede admissão; posterior não a cancela. Timeout não transforma revogação pendente em eficaz. Ordem desconhecida impede novas admissões; contenção é caminho adicional e não altera consumo/ordem.

## 4. Contenção e fencing terminal

Fica selecionado apenas o comportamento candidato: **fechar admissões; retirar persistentemente capacidades antigas em todos os meios; drenar ou abortar trabalho em voo antes de confirmar o corte**. O produto/interface storage/fabric/físico e a prova de compatibilidade não estão selecionados. A falta de atuador verificado mantém a confirmação bloqueada. SQL local sozinho conserva apenas o alcance local demonstrado em DEV-05.

| Etapa | Ato e condição de término |
| --- | --- |
| Q0 pedido de contenção | V fixa caso, inventário/geração/política, capacidades antigas e desafio fresco. A regista bloqueio de novas admissões e intenção durável; não liberta consumos nem declara canceladas admissões anteriores. |
| Q1 fecho de entradas | B/F retiram a possibilidade de novas iniciações antigas, incluindo sessões abertas, principals alternativos, caminhos locais, re-registo e restore. Comando aceite ainda não é corte terminal. |
| Q2 tratamento de pendências | Por recurso, B/F identificam transações, commits, WAL/cache/I/O, filas e 2PC. Política humana H05 escolhe drain ou abort e impacto. Drain permite término antigo antes do corte e pode esperar indefinidamente; abort só termina quando aborto/rollback e fim das pendências forem demonstrados. Timeout mantém bloqueio. |
| Q3 corte local terminal T_i | F/B impõem retirada persistente de escrita antiga em todos os meios/canais do recurso, resolvem todas as pendências e observam a barreira terminal. T_i sucede causalmente ao último término antigo e ao fecho durável. Nenhuma mutação/commit antigo depois de T_i. Persistência inclui restart, reanexação, ACL e recovery. |
| Q4 confirmação conjunta | V verifica todos os T_i, cobertura do inventário e manutenção contínua dos cortes anteriores até esta confirmação. W confirma conteúdo/continuidade; o observador de atuação e efeito tem origem própria. Recurso inacessível só pode ser considerado cortado por prova externa do seu meio; silêncio não basta. |
| Q5 atestado limitado | V declara cessação da capacidade de efeito somente no alcance demonstrado, depois de Q4. A guarda como evidência. Não concede operação, não escolhe novo executor e não inicia reentrada. |

A ordem verificável é: término do trabalho antigo por recurso precede T_i; todos os T_i com exclusão contínua precedem a confirmação global. Recibos da API, relógios de hosts distintos, assinaturas, ausência de backends/heartbeat ou epoch isolado não substituem as barreiras. Não se presume transação distribuída entre A/B/F/W. Se um recurso reabrir enquanto outro é cortado, Q4 não pode confirmar. Se isso for descoberto depois da emissão, o atestado deixa de justificar uso futuro e há incidente, com novas admissões bloqueadas; não se oculta a confirmação inválida.

Um clone integral fora do poder de F que permaneça gravável impede Q3/Q4 para R*. Um componente pode declarar UNKNOWN/BLOCKED e continuar fisicamente a produzir efeitos antigos. O bloqueio administrativo não é prova de contenção: ambos os novos percursos ficam sem autorização, e o antigo requer atuação efetiva; a propriedade forte não é reivindicada enquanto ele puder escrever.

## 5. Conteúdo e semântica do atestado

O significado proposto é «capacidades antigas de efeito cessadas no conjunto inventariado, sob ameaça e confiança identificadas». Não declara morte de processo/VM/host. Morte física exigiria alcance e atuador próprios (H04). Devem estar ligados conceptualmente: caso e desafio, recurso/geração/meios, versão do inventário e política, tentativa/encarnações/principals/contextos, epochs e posições de ordem distintos, cortes e pendências resolvidas, atuador e observador, persistência/continuidade, confirmação D09, evidência recuperável e limites/exclusões. Não se definem campos nem bytes executáveis.

V verifica autenticidade/origem, desafio de uso único, vínculos completos, estado atual do atuador e continuidade fora de D. Nonce fresco não impede que estado restaurado assine uma mentira antiga; recibo autêntico histórico não prova estado presente. Frescura do atestado tem política própria por aprovar, não o prazo C2. Mudança de topologia, configuração, confiança, re-enrolamento ou continuidade exige nova apreciação; nenhum TTL concede retoma.

W confirma o conteúdo que recebeu e a sua continuidade. W não prova que F cortou só por ter arquivado a declaração de F. V precisa de observação independente da atuação e dos efeitos, sob base confiada explícita. Se essa independência não existir, o artefacto é declaração técnica local, incapaz de satisfazer o atestado independente candidato.

## 6. Incerteza por fase e componente

| Falha | A / B / F | W/V e ação permitida |
| --- | --- | --- |
| Antes do commit de admissão ou resposta perdida após ele | A pode estar consumido; B não despacha sem confirmação recebida no fluxo original. | UNKNOWN; leitura esclarece factos, não emite permissão. Reconciliação antes de qualquer nova tentativa. |
| Reserva, compromisso de início ou W pré-execução incertos | B conserva marcadores existentes e bloqueia entrada/repetição; A não liberta consumo. | Consultar conteúdo/continuidade; não converter ack recuperado em retoma após quebra de contexto. |
| Partição após início confirmado, contexto original contínuo | A bloqueia novas admissões se ordem desconhecida; B pode terminar a execução original segundo C5. | Falta de novos eventos bloqueia progressão dependente. V não declara cessação por silêncio. |
| Commit do efeito real com resposta perdida | B pode ter efeito confirmado; nenhuma repetição nem retorno a contexto anterior. | Observação read-only de payload/término e reconciliação; resultado incompleto continua UNKNOWN. |
| Corte aplicado com ack perdido/crash de F | A mantém bloqueio; F não reaplica automaticamente uma transição incerta como se fosse nova. | V pode observar alcance atual e registos de corte; leitura não promove executor nem reabre escrita. |
| Perda de continuidade/restauro de A/B/F/W/CA | Quarentena; impedir novas capacidades e preservar consumos/ordem; capacidade antiga em meio externo precisa de corte demonstrado. | Reconstrução controlada e decisão humana; snapshot coerente/incremento epoch não provam continuidade. |
| Recurso inacessível e nenhum atuador externo verificável | Sem confirmação Q3/Q4; antigo pode estar vivo/gravável. | BLOCKED, sem confirmação de takeover; perda de disponibilidade potencialmente indefinida. |

## 7. Reconciliação e reentrada humana

Abrir caso com preservação de todas as versões/evidências contraditórias; recolher com credenciais de leitura separadas registos de A, reserva/início B, payload/mutações/commit/abort, F/storage, W e continuidade. Distinguir factos conhecidos, ausência de observação e hipóteses. Não executar probes de escrita como «consulta» nem conceder privilégio de efeito ao reconciliador.

Reconciliação acrescenta evidência e conclusão, sem apagar consumo, revogação ou resultado antigo. Exige inventário novamente validado e invalidação demonstrada de todas as capacidades antigas pertinentes, incluindo clone/backup/restauração. Resultado anterior conhecido não basta se a capacidade antiga puder voltar. Ausência de continuidade mantém quarentena mesmo depois de nova chave/epoch.

V apresenta alcance/limites e W confirma o conteúdo crítico. Pessoa identificada toma decisão autenticada/auditada, aceita risco e plano revistos e exige novo pedido e **nova aprovação**, ligados a nova tentativa/encarnação/sessão/transação. A aprovação anterior permanece consumida/indisponível. A nova decisão não declara automaticamente elegibilidade: o novo pedido deve passar todos os requisitos de A, UTC, D09 e bindings. Não há retry, transferência de sessão, reemissão de ticket, HA, failover ou bypass de emergência automáticos. Sem invalidação de capacidades antigas, nem decisão humana transforma o meio antigo em contido.

## 8. Correspondência C1–C7 e obrigações em aberto

| Cláusula | Preservação específica | Prova/decisão por realizar |
| --- | --- | --- |
| C1 | P1/P2 serializam e confirmam consumo/vínculos/ordem/evidência; A independente. | Implementação, durabilidade e segregação; nenhuma atomicidade A–B–W presumida. |
| C2 | Avaliação final serializada em A com fórmulas intactas; nenhuma revalidação do prazo no commit. | Fonte/limites UTC e bootstrap aprovados e demonstrados. |
| C3 | Ordem única; posterior não cancela; Q0 é contenção, sem reescrever admissão. | Ordenação persistente de todas as classes de revogação. |
| C4 | Contexto inerte previamente vinculado, reserva não reversível, início único por B em todas as entradas. | P1/P2 da fronteira, registo independente do rollback e impossibilidade de segunda iniciação/replay. |
| C5 | UNKNOWN sem despacho; consulta apenas documental; original contínuo pode terminar; nova tentativa só após reconciliação. | Provar continuidade real do contexto e ausência de retoma automática em falhas. |
| C6 | W antes do percurso/início; confirmação posterior dos resultados; recovery em quarentena. | Conteúdo, custódios, retenção, âncora externa e invalidação efetiva. |
| C7 | R1 e seus parsers/executores intactos; 25 nomes, JCS/UTF-8 e Ed25519 puro preservados. | Perfil R2/domínio próprio/codificação/schemas precisam de aprovação específica; estes rótulos não são formatos aprovados. |

O argumento de segurança continua condicionado à mediação completa, não duplicação fora da fronteira, exclusão terminal persistente e observação independente. Não se usam essas premissas como prova de que existem. Os cenários de VALIDATION verificam obrigações delimitadas; nenhum resultado é antecipado nesta especificação.
