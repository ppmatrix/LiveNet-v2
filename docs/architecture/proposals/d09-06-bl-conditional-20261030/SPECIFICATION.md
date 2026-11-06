# LiveNet v2 — D09-06 — especificação documental condicionada B-L

Versão de trabalho: 1.0 · 30/10/2026 · Europe/Lisbon.
Estado: **PROPOSTA PARA REVISÃO HUMANA FINAL; BYTES NÃO APROVADOS**.

## 1. Objeto e autoridade

B-L significa **preservação crítica distribuída fora do NAS**. A variante foi aprovada como preferência técnica condicionada no âmbito D09-06; D09-05 foi aprovado como desenho lógico conceptual condicionado. Esta especificação desenvolve essas decisões, sem repetir a seleção de variantes nem converter a sua aprovação em aprovação física, de implementação ou dos presentes bytes.

O mandato atual, «Continuidade Autónoma de Desenvolvimento», reafirma expressamente ambas as aprovações e autoriza esta preparação documental. Os textos integrais de D09-05 e da comparação D09-06 foram recuperados nos chats de origem e conservados como dados em [RECOVERED_SOURCES.json](RECOVERED_SOURCES.json). [SOURCES_AND_REVIEW.md](SOURCES_AND_REVIEW.md) identifica mensagens, limites, fontes normativas e verificações. Uma resposta antiga do agente é fonte do texto proposto, não ato humano por si mesma.

A arquitetura preserva autoridade R2 única, separação entre admissão e execução e domínio D09 distinto. O propósito é permitir que conteúdo crítico, confiança e continuidade suficientes sobrevivam às falhas cobertas sem dependência exclusiva do Synology. Não se promete disponibilidade durante incidentes nem recuperação enquanto faltar fundamento suficiente.

## 2. Âmbito, pressupostos e exclusões

São abrangidos o fluxo de admissão durável, preservação e confirmação independente, condição de disponibilização do percurso executável, fronteira C4 no alvo e recuperação D10. O comprometimento do executor é um cenário coberto pretendido: não pode remover o controlo no alvo, falsificar D09 ou alterar a autoridade. A capacidade real de impor essas condições continua por demonstrar.

Existe um único operador humano, que exerce poderes funcionalmente segregados. Não se exige segundo administrador, fornecedor externo, novo hardware ou serviço adicional. O comprometimento total dos poderes desse operador e de todos os fundamentos de recuperação permanece fora da garantia aprovada. Esta exclusão não permite esconder uma credencial aparentemente limitada que, por delegação ou recuperação, alcance todos os fundamentos de um cenário que se pretendia cobrir.

O alojamento pretendido distribui R2, execução e D09 por nós distintos, sem atribuir nós ou VMs concretos. O estado autoritativo R2 é independente das bases e storage do executor. D09 ocupa domínio de alojamento e armazenamento distinto de R2 e execução. Distinção nominal não demonstra separação física, administrativa ou de eliminação: dependências comuns precisam de ser avaliadas pelo seu alcance efetivo.

Synology pode conservar cópias complementares. A perda ou indisponibilidade do NAS não pode retirar o único conteúdo crítico, a única referência de confiança ou a única possibilidade de recuperação de que B-L depende. Uma dependência indireta obrigatória de boot, configuração, identidade ou recuperação no NAS também contradiz essa finalidade, ainda que o conteúdo ativo se encontre noutro disco.

Progbox é exclusivamente DEV. STAGING e PROD devem residir em VMs Proxmox. Todo o LiveNet permanece na rede interna do laboratório, sem exposição à Internet. Esta proposta não escolhe VMIDs, nós, volumes, IPs, contas, software, protocolos, chaves, schemas, retenções, RPO/RTO ou limites temporais novos. A preferência B-L não prova capacidade livre nem reserva recursos.

Permanece o limite histórico de DEV-08: **se um adversário conservar uma cópia integral gravável autónoma do recurso, a cessação universal nessa cópia é inviável com os pressupostos atuais**. B-L distribui preservação e confiança; não elimina esse contraexemplo nem prova C4 por separar D09. Não se aprova O3 nem se redefine o efeito como apenas publicação no endpoint oficial. O desenho concreto deve demonstrar a impossibilidade de contorno/segunda iniciação sob os poderes cobertos, ou declarar a garantia não satisfeita.

## 3. Funções e fronteiras de confiança

| Função lógica | Responsabilidade e fundamento | Limite |
| --- | --- | --- |
| Aplicação/executor | Apresentar pedido e manter a tentativa original vinculada à execução admitida. | Não admite, não confirma D09, não modifica confiança nem reconstrói permissão a partir de estado local. |
| Autoridade única R2 | Avaliar em A e serializar com revogações, epochs e política; confirmar conjuntamente consumo, vínculos, ordem e evidência essencial. | Não substitui confirmação independente por declaração própria; não escreve a preservação para apagar divergências. |
| Preservação/confirmação D09 | Conservar conteúdo crítico suficiente, recuperável e verificável; confirmar a sua relação com a admissão concreta e continuidade. | Não admite, não liberta consumos e não prova execução/commit por confirmar preservação. |
| Condição de disponibilização | Verificar cumulativamente admissão durável, confirmação D09 pertinente, vínculos, continuidade e demais requisitos aplicáveis antes do percurso executável. | Não pode ser removida pelo executor no cenário de comprometimento coberto; não cria nova autoridade. |
| Alvo/fronteira C4 | Impedir segunda iniciação e todos os percursos de contorno, mantendo destino/geração e sessão/transação protegidas. | Não aceita um recibo isolado como prova de exclusividade nem devolve aprovação por rollback. |
| Verificação/reconciliação | Confrontar estado, conteúdo, ordem, efeitos e capacidades anteriores através de fundamentos que sobrevivam ao incidente. | Ler estado não cria capacidade, não retoma e não reescreve histórico. Não se pressupõe uma nova pessoa ou VM para esta função. |
| Recuperação D10 | Reconstruir em quarentena com conteúdo, confiança e continuidade suficientes fora de cada falha coberta. | Não promove D09 a autoridade substituta nem cria R2 concorrente. |
| Operador único | Decidir reentrada autenticada/auditada e aprovar novo pedido quando todas as condições forem demonstradas. | A decisão humana não substitui evidência perdida nem torna segura uma capacidade antiga ainda ativa. |

Fluxo lógico, sem atribuição física:

```text
executor → R2 único: avaliação em A e confirmação durável conjunta
                     ↓ conteúdo crítico e continuidade
                 D09 independente, fora da dependência exclusiva do NAS
                     ↓ confirmação pertinente e verificável
             condição de disponibilização cumulativa
                     ↓ apenas no contexto original admissível
                 alvo com imposição efetiva C4
                     ↓ início / efeito / commit ou abort observados
           preservação dos resultados e reconciliação quando necessária

fundamentos sobreviventes → quarentena → continuidade e invalidação
                         → decisão humana → novo pedido e nova aprovação
```

As setas são dependências informacionais. Não representam delegação de administração, protocolo aprovado ou atomicidade distribuída. A função de disponibilização é uma obrigação de imposição; a sua localização e mecanismo continuam por especificar tecnicamente. Enquanto o executor puder simplesmente saltá-la, o cenário 2 não está coberto.

## 4. Poderes, privilégios e dependências transitivas

| Poder delimitado | Acesso funcional permitido no desenho | Alcance incompatível com a separação pretendida | Fundamento que deve sobreviver |
| --- | --- | --- | --- |
| Execução/aplicação | Pedir admissão, consultar factos e executar contexto original válido. | Alterar consumo/ordem, fabricar confirmação, trocar validador ou iniciar SQL por outra via. | R2, preservação/confiança D09 e imposição C4 fora do comprometimento. |
| Administração do SO da execução | Manter somente o domínio abrangido pelos seus poderes. | Ler segredos R2/D09, montar os seus meios, assumir consola ou remover a fronteira do alvo. | Componentes e confiança exteriores a todos esses poderes efetivos. |
| Função R2 | Acrescentar transições autoritativas e evidência local. | Apagar conteúdo D09, substituir a confiança do verificador ou apagar consumos por recovery. | Cópia crítica e referências de continuidade fora desse poder. |
| Função D09 | Preservar, verificar e confirmar conteúdo pertinente. | Emitir admissões, alterar vínculos decididos ou transformar uma cópia em permissão. | Estado autoritativo e verificações que detetem inconsistência ou confirmação falsa. |
| Administração de storage/cópias | Gerir apenas os meios atribuídos ao poder delimitado. | Apagar/corromper simultaneamente todos os conteúdos e raízes que se dizem independentes desse poder. | Conteúdo suficiente e confiança fora da falha e do poder de eliminação considerado. |
| Credencial de recuperação | Reconstruir em quarentena dentro do caso autorizado. | Redefinir confiança e reativar poderes antigos sem continuidade/invalidação. | Referências e conteúdo verificáveis fora da credencial comprometida. |
| Gestão de cluster/consola/deploy | Apenas alcance que venha a ser delimitado e aprovado. | Controlar execução, R2, D09 e recuperação enquanto se apresenta como credencial limitada isolada. | Controlos não alcançados; se não existirem, a cobertura pretendida não foi demonstrada. |
| Totalidade dos poderes do operador | Administração humana global. | Não se reivindica independência quando todos esses poderes e a recuperação estiverem comprometidos. | Nenhum fundamento independente é pressuposto nesse cenário excluído. |

O mesmo operador pode exercer os poderes. A segregação exige demonstrar o alcance de cada credencial/capacidade, não multiplicar pessoas ou contas como prova. Seguir delegações, elevação, consolas, reset de identidade, acesso a chaves, alteração de trust stores, montagens, backups, distribuição de software e recuperação até ao alcance transitivo completo. Uma credencial que chega à gestão global não permanece «limitada» apenas pelo seu nome.

| Dependência comum | Pergunta a resolver no desenho técnico | Consequência enquanto desconhecida |
| --- | --- | --- |
| Hipervisor/gestão/consola | Que funções e cópias consegue modificar o mesmo poder? | Nós distintos não provam independência administrativa. |
| Storage, caminhos físicos e cópias | Conteúdo ativo e recuperação partilham backend, controlador ou poder de eliminação? | Um caminho lógico diferente não demonstra sobrevivência. |
| Identidade, confiança e reset | Quem substitui validadores, raízes e acessos de todas as funções? | Autenticidade aparente não prova origem independente. |
| Configuração, boot e deploy | O mesmo mecanismo remove as guardas ou fornece toda a configuração de recovery? | Separação de dados pode ser anulada por dependência transitiva. |
| Rede, alimentação e gestão | Uma falha comum torna inacessíveis fundamentos que ainda existem? | Conteúdo preservado pode exigir bloqueio por indisponibilidade. |
| Tempo confiável | Que fonte/continuidade permite A e a verificação pertinente? | Tempo ou continuidade desconhecidos impedem admissão, sem fallback presumido. |
| Recuperação | Existem transições posteriores à última cópia e capacidades antigas ainda vivas? | Snapshot coerente não permite reentrada automática. |

Estas são questões de ligação à futura solução concreta. Não autorizam nova auditoria geral nem recolha operacional nesta etapa.

## 5. Admissão R2, preservação D09 e execução

### 5.1 Precedências obrigatórias

| Etapa | Facto e condição exigidos | Falha ou resposta ambígua |
| --- | --- | --- |
| S0 avaliação em A | Avaliação final serializada com revogações de aprovação, chave, autoridade e política, epochs e vínculos da tentativa concreta. | Ordem/tempo desconhecidos: não admitir. Revogação pendente não é eficaz. |
| S1 confirmação durável R2 | Uma transação confirma conjuntamente admissão, consumo, vínculos imutáveis, ordem e evidência essencial local. | Sem confirmação durável/autenticada recebida no percurso original: UNKNOWN/BLOCKED, sem despacho. Pode existir consumo real sem efeito. |
| S2 preservação D09 | Conteúdo crítico recuperável relacionado com S1 é conservado em domínio independente para as ameaças cobertas. | Existência parcial, só digest, conteúdo divergente ou continuidade incerta não bastam. |
| S3 confirmação independente | Confirmação autenticada/verificável da preservação e continuidade pertinente à mesma admissão, vínculos e destino/geração. | Ausência, resposta perdida, divergência, replay ou vínculo inadequado: percurso bloqueado; consumo não se liberta. |
| S4 disponibilização condicionada | Controlos ainda confiáveis validam S1–S3, contexto original, C4, continuidade e todos os gates aplicáveis. | Nenhum recibo dispensa outro requisito. Nesta etapa todos os gates operacionais continuam fechados, logo nenhum percurso real é habilitado. |
| S5 iniciação e resultado no alvo | Apenas a tentativa original admissível pode iniciar uma vez sob C4. Início, mutação, commit/abort e resposta são observações distintas. | Resultado desconhecido não autoriza repetição; zero commit não prova zero iniciação. |
| S6 preservação dos factos observados | Preservar início/resultado e transições pertinentes quando existirem; confirmação exigida antes da progressão que dependa desses factos. | Não fabricar eventos futuros nem exigir confirmação antecipada de um commit ainda inexistente. Falta bloqueia progressão dependente. |

Não existe atomicidade presumida entre R2, D09 e alvo. A anterioridade de S3 a S4 deve ser demonstrável causalmente, sem depender só de timestamps entre máquinas. D09 não cria segunda ordem de admissão/revogação nem reavalia elegibilidade como autoridade concorrente.

Conservam-se C2 e as fórmulas existentes: `issued_at <= not_before < expires_at`, duração máxima de 900 segundos, `L >= not_before` e `U < expires_at`, com UTC confiável em A. O prazo limita a avaliação em A; não se desloca para confirmação, entrega, primeiro efeito ou commit. Não se infere retenção R2 da janela de 900 segundos.

Por C3, revogação ordenada antes de A recusa a admissão; posterior não a cancela retroativamente nem desfaz efeitos. Contenção continua possível sem libertar aprovação ou falsificar a ordem histórica. Ordem ou confirmação desconhecidas bloqueiam novas admissões.

### 5.2 Objeto e limites da confirmação

A confirmação deve referir verificavelmente o conteúdo efetivamente preservado, a admissão durável, vínculos, ordem/continuidade e âmbito a que respeita. Estas são obrigações semânticas, sem novos campos ou schema. É necessário poder recuperar conteúdo suficiente e verificar a sua relação com a fonte: um hash, assinatura ou recibo isolado não reconstitui bytes perdidos nem demonstra completude.

Confirmação D09 não prova iniciação, efeito, commit, morte de processo, cessação de clone ou capacidade de reconstruir integralmente R2. Tampouco autoriza destruição. Uma consulta autenticada posterior pode esclarecer o registo existente; não emite permissão nem retoma uma execução interrompida. Retransmissão de conteúdo documental para preservação, quando prevista no futuro protocolo, distingue-se de retry da operação; não reabre o percurso executável.

Eventos críticos já existentes e necessários à disponibilização devem estar confirmados antes dela. Eventos de início e resultado apenas podem ser preservados como observações depois de ocorrerem. O catálogo e a codificação concretos precisam de trabalho próprio; não se transforma esta sequência em aprovação de formatos.

## 6. Proteção C4 fora do controlo do executor

Cada aprovação admite no máximo uma tentativa, ligada imutavelmente a pedido, participantes, finalidade, operação, gate, ambiente, plano/digests, destino/geração, executor/encarnação e sessão/transação protegidas. Timeout, rollback, savepoint, expiração, crash ou restart não libertam aprovação nem permitem segunda iniciação. Não há promessa de execução exatamente uma vez: consumo sem efeito é possível.

A solução concreta deve mediar todas as entradas capazes de produzir o efeito, incluindo função direta, SQL privilegiado dentro do modelo, sessão antiga, caminhos locais, trabalhos pendentes, restore e clones. A ligação entre consumo durável e contexto de iniciação tem de continuar obrigatória no alvo, mesmo quando o executor ignora o broker. Contar consumos ou commits não demonstra início único. Alterar o payload sem escrever ledger também tem de ser observável.

Se o SO comprometido administrar o alvo ou puder remover o controlo C4, a separação lógica de R2/D09 não contém esse ataque. O desenho técnico deve colocar o fundamento de imposição fora do alcance coberto e demonstrar a exclusão de caminhos alternativos; a relação física executor–alvo continua pendente. Um clone integral gravável que escape à imposição mantém o contraexemplo histórico. D09 não corrige esse problema por guardar um recibo do original.

Não são selecionados mecanismos de fencing ou de vínculo nesta fase. Qualquer alegação futura de invalidação deve cobrir trabalho antigo até término/commit ou abort e manter a exclusão antes de admitir reentrada. Silêncio, ausência de heartbeat, nova chave ou incremento de epoch não provam isso.

## 7. UNKNOWN/BLOCKED e continuidade da tentativa original

| Situação | Comportamento exigido |
| --- | --- |
| R2 confirmou, D09 não confirmou ou a resposta perdeu-se | Consumo preservado; sem disponibilização. Consulta não cria permissão. |
| D09 contém dados mas a ligação a admissão durável é incerta | Não usar esses dados como autorização. Preservar divergência e reconciliar. |
| Confirmação válida para outro destino/geração/contexto | Recusar; não adaptar ou transferir vínculos. |
| Partição depois de satisfeitas as condições prévias | C5 permite apenas à tentativa original continuamente vinculada prosseguir; a partição não revoga retroativamente a admissão. Isso não autoriza nova tentativa ou nova disponibilização. |
| Reconexão, restart, perda de contexto ou resposta de commit incerta | Sem retoma/retry automático. Consulta apenas factual; abrir reconciliação. |
| D09/estado/ordem/tempo deixam de sustentar uma nova progressão | Bloquear progressão dependente. Não afirmar por isso que uma execução antiga cessou fisicamente. |
| Continuidade após restore ou confiança desconhecida | Quarentena, sem reativar aprovação/capacidade antiga. |

Bloqueio seguro é recusa tecnicamente imposta por controlos que sobrevivam com confiança suficiente. Uma instrução ao operador ou uma flag na VM comprometida não demonstra imposição. Perder disponibilidade pode ser a única resposta segura enquanto persistir incerteza; não há prazo de desbloqueio presumido.

## 8. Fundamento sobrevivente nos sete cenários D09-03

Os sete cenários foram recuperados integralmente da resposta D09-03 e do respetivo pedido humano. A matriz descreve obrigações B-L, **não resultados de novos ensaios**.

| Cenário | Alcance e fundamento sobrevivente requerido | Quem impõe bloqueio | Recuperação e limite |
| --- | --- | --- | --- |
| 1. Falha de VM/serviço | Conteúdo/estado e confiança suficientes fora do componente perdido, incluindo transições posteriores a uma cópia antiga. | Condição de disponibilização e alvo sobreviventes recusam progressão sem requisitos; componente reconstruído entra em quarentena. | Recuperação controlada, sem retoma automática. Perda de serviço não prova perda de conteúdo nem suficiência de cópias. |
| 2. Comprometimento do SO da VM LiveNet | R2, D09, confiança, recuperação e imposição C4 fora de todos os poderes transitivos da VM. | R2 recusa pedido inválido; validação de disponibilização exige D09 autêntico; alvo impede contorno/segunda iniciação independentemente do executor. | Se o SO puder trocar validador, escrever a preservação ou remover C4, o cenário falha. Restauração só com confiança e capacidades anteriores tratadas. |
| 3. Perda de um nó Proxmox | Distribuição pretendida por nós distintos e fundamento suficiente fora do nó e dependências simultaneamente afetadas. | Controlos sobreviventes bloqueiam progressão afetada; não há promoção automática de autoridade. | Reconstruir R2 único sem concorrer com instância antiga. Nó inacessível pode recuperar capacidades: ausência de resposta não invalida o antigo. Cinco nós não provam capacidade ou recuperação. |
| 4. Indisponibilidade Synology | Conteúdo crítico, confiança e recuperação de B-L não exclusivamente dependentes do NAS. | Se faltar qualquer requisito, condição de disponibilização/R2 bloqueiam progressão dependente; conserva-se C5 para tentativa original válida. | Se todas as condições sobreviverem fora do NAS, a sua perda isolada não exige artificialmente parar tudo. Dependência indireta obrigatória descoberta exige bloqueio e revisão da suficiência B-L. |
| 5. Corrupção/eliminação do storage partilhado | Conteúdo recuperável e continuidade fora da corrupção e do poder de eliminação considerados, incluindo cópias/configuração necessárias. | Validadores sobreviventes recusam conteúdo divergente/insuficiente; recuperação em quarentena. | Recibo/digest isolado não recupera conteúdo. Cópia no mesmo domínio de eliminação não satisfaz sobrevivência. Sem fundamento suficiente, recuperação permanece bloqueada. |
| 6. Comprometimento de credencial administrativa limitada | Fundamentos necessários fora de todo o alcance efetivo da credencial: elevação, reset, consola, gestão, deploy e recovery incluídos. | Controlos não alcançados recusam alteração ilegítima, confirmação falsa e reentrada; operador contém o poder comprometido. | Demonstrar o limite, não presumir pelo nome da conta. Se alcançar todos os fundamentos pertinentes, a cobertura pretendida falhou; não a reclassificar silenciosamente como cenário 7. |
| 7. Comprometimento transversal do cluster e de toda a recuperação | Nenhum fundamento independente é pressuposto; cenário fora da garantia aprovada. | Não se garante imposição confiável por componentes todos comprometidos. | Sem restabelecer fundamento confiável, não há base para declarar recuperação segura ou reentrada. Não se exige infraestrutura externa para prometer uma garantia aqui excluída. |

Para cada cenário coberto, a futura demonstração deve ligar poder/falha → conteúdo/confiança sobreviventes → controlo ainda confiável → evidência de bloqueio/recuperação. Sobrevivência meramente provável ou não localizada permanece por demonstrar. Não se presume que D09 isoladamente reconstrua todas as funções.

## 9. Recuperação, invalidação e reentrada D10

1. Conservar o caso e o histórico conhecido, incluindo divergências e resultados incertos. Bloquear novas admissões/progressões afetadas e pôr componentes recuperados em quarentena; isso não declara fisicamente cessadas as capacidades antigas.
2. Identificar os fundamentos que realmente sobreviveram ao incidente e os poderes ainda confiáveis. Distinguir indisponibilidade de conteúdo, perda de conteúdo e compromisso de confiança.
3. Reconstruir estado e conteúdo suficientes sem reduzir epochs, apagar consumos/admissões/revogações, mudar vínculos ou promover cópia divergente a autoridade. Demonstrar transições posteriores ao backup; lacunas não resolvidas mantêm quarentena.
4. Reconciliar iniciações e resultados com observações do alvo. Ausência de ledger não demonstra ausência de efeito; consulta read-only não é probe de escrita nem autorização.
5. Demonstrar invalidação de instâncias, sessões, clones e capacidades antigas pertinentes, inclusive após restauro. Um snapshot assinado, incremento de epoch ou nova chave não demonstra exclusão do antigo. Se um ramo permanecer gravável fora do controlo, não confirmar invalidação universal.
6. Verificar continuidade, confiança, preservação D09 e autoridade única. Recuperação não é eleição, HA ou failover automático e não concede a D09 poder de admissão.
7. Apresentar evidência ao operador único para decisão humana autenticada/auditada. Nova tentativa exige novo pedido e nova aprovação vinculados ao contexto novo, preservando o consumo anterior. Todos os gates e requisitos de admissão continuam aplicáveis.

Não há bypass de emergência. A decisão humana não preenche ausência de prova nem autoriza retoma da aprovação antiga. RPO/RTO, retenção, mecanismos e procedimentos físicos serão matéria técnica posterior; não se fixam por conveniência ou pelo número de nós.

## 10. D09 e V05-06: obrigações distintas

D09 é confirmação independente da preservação pertinente antes da disponibilização do percurso executável. V05-06 é demonstração verificável independentemente de preservação, separação e continuidade no âmbito identificado, com resultados COMPROVADO, FALHA e INDETERMINADO. COMPROVADO não autoriza destruição; FALHA ou INDETERMINADO mantêm a destruição bloqueada.

Uma confirmação D09 não substitui a demonstração V05-06; COMPROVADO em V05-06 não vale como confirmação D09 de uma admissão. Ambas permanecem por demonstrar. Mantêm-se prazos e condição final de libertação R2 TBD quando assim definidos, sem inferir retenção eterna ou permissão de eliminação. Não se altera D1/D2/D3 nem NC-01.

## 11. Lacunas relevantes e condições de demonstração

Estes localizadores editoriais não criam nem renumeram os registos de lacunas existentes.

| Obrigação pendente | Evidência necessária na futura solução concreta | Bloqueio enquanto ausente |
| --- | --- | --- |
| Alojamento/storage B-L e suficiência | Mapa nominal de funções, meios e dependências de falha/poder, reutilizando inventário existente; disponibilidade/capacidade fundamentadas. | Nenhuma atribuição física ou prontidão declarada. |
| Independência perante poderes delimitados | Alcance transitivo e fundamento sobrevivente dos cenários 2/5/6, incluindo confiança, deploy e recovery. | Contas/nós distintos não bastam; sem confirmação favorável por inferência. |
| Conteúdo suficiente D09 | Relação verificável entre admissão durável, conteúdo integral recuperável, vínculos e continuidade; tratamento de divergências. | Sem disponibilização de percurso. |
| Anterioridade e imposição | Barreira demonstrável S3→S4 e controlo fora do executor comprometido. | Flag/recibo sem imposição não passam o cenário 2. |
| C4 e capacidades antigas | Exclusividade de iniciação, ligação ao consumo/contexto, todos os caminhos diretos e invalidação até término de trabalho antigo. | GAP-001/002 e gates permanecem bloqueantes; clone gravável não é ignorado. |
| Continuidade recuperável | Estado, eventos pós-backup, conteúdo e confiança suficientes; R2 único; recuperação em quarentena. | Snapshot/epoch não reabrem capacidades. |
| Tempo, confiança e formatos | Escolhas técnicas próprias e aprovações específicas de mecanismos/bytes quando necessárias, preservando C2/C7. | Não interpretar notação desta proposta como schema/permissão. |
| Retenção e V05-06 | Resolução futura dos TBD e demonstração independente no seu âmbito, separada de D09. | Sem eliminação automática ou destruição autorizada. |

Não existe evidência aqui para exigir novo hardware, terceiros ou segundo operador. Também não existe prova suficiente de que os recursos atuais bastem. Se o desenho técnico revelar uma insuficiência concreta, apresentar uma decisão material fundamentada nesse ponto, sem antecipar aquisição ou solução externa.

## 12. Aceitação documental e próximo trabalho condicionado

A revisão final pode aceitar estes bytes como especificação documental condicionada se confirmar: fidelidade à definição B-L e D09-05/06; sete cenários preservados; operador único e exclusão total corretamente delimitados; sequência R2 durável→D09→percurso→C4 sem atomicidade presumida; C5 intacta; recuperação com continuidade e invalidação; distinção D09/V05-06; lacunas explícitas e ausência de escolhas físicas/implementação tácitas.

Não se exige demonstrar operacionalmente todas essas obrigações para aprovar o documento. Exige-se conservar a diferença entre obrigação e prova: aprovação documental não transforma RG1–RG7, D09, V05-06 ou C4 em demonstrados.

Após revisão final favorável, a próxima etapa recomendada é **preparação técnica documental do mecanismo de disponibilização e imposição C4 da B-L**, ligada aos sete cenários e aos fundamentos de recuperação. Deve reutilizar fontes existentes, descrever quais controlos sobrevivem ao executor comprometido e quais evidências futuras os verificarão. Escolhas materiais de arquitetura física, recursos, confiança ou implementação regressam a decisão humana própria; esta proposta não as antecipa. Não iniciar ensaios ou nova recolha operacional por extensão da aprovação documental.

## 13. Estados preservados e decisão submetida

P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados e bloqueantes; H02–H12 e GAP-001/002 bloqueantes; RG1–RG7, D09 e V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial. Nenhum desses estados muda por esta especificação ou pelo índice de continuidade.

**Decisão humana única submetida:** aprovar ou solicitar revisão da especificação B-L v1.0 exclusivamente como documento condicionado, mantendo pendentes as demonstrações, a arquitetura física, atribuição de recursos e implementação. Até essa decisão, os presentes bytes permanecem proposta.
