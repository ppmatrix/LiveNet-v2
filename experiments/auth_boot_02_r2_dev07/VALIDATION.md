# R2-DEV-07 — suficiência dos critérios e condições de aceitação

Revisão documental de V01–V15; nenhum dos cenários abaixo foi executado nesta
etapa. Localizadores Vnn são os da matriz DEV-06; Fnn estão em
[FINDINGS.md](FINDINGS.md). «Aceitação» significa requisito para futura apreciação,
não aprovação por esta entrega.

## Crítica individual V01–V15

| Critério | Avaliação e lacuna | Complemento de prova/oráculo exigido | Rastreio |
| --- | --- | --- | --- |
| V01 | Necessário, insuficiente como lista de tentativas. Um resultado negativo por papel não prova inexistência de outro administrador ou caminho. | Matriz efetiva SQL/OS/hipervisor/storage/backup/CA, heranças e recuperação; mapa de dados/volumes/exportações; comprovar desativação de replicação, jobs, triggers, extensões e 2PC se excluídos. | F01/F02/F10 |
| V02 | Ataca as duas janelas corretas; falta especificar a barreira de corte e observar a persistência terminal do commit. | Reproduzir escalonamentos antes de SQL, após UPDATE e durante commit, perder também sessão/canal do observador; ordenar término durável e confirmação causalmente. Separar drain e abort. | F04/F08 |
| V03 | Decisivo e corretamente conta efeito no clone. Pode falhar legitimamente, refutando a candidatura ao critério forte. | Clone vivo tenta escrita no próprio meio após confirmação; ler payload independentemente. Se topologia impedir copiar B, demonstrar essa prevenção; simples rejeição do endpoint não passa o critério. Snapshot de memória/credenciais também exige caso próprio. | F01/F06/F11 |
| V04 | Reconhece clone de raiz externa como contraexemplo; não decide se esse poder está permitido. | Restaurar combinações A/B/F/W/CA, backup de configuração e estado de enrolamento; comparar com continuidade externa não restaurada. Não aprovar o caso só porque o sistema deteta uma divergência depois do efeito. | F01/F05 |
| V05 | Bom inventário de pendências, mas statement preparado e transação 2PC são distintos; filas fora de SQL ficam por identificar. | Enumerar cache, WAL, I/O, jobs, filas externas e 2PC habilitados; provar fim/aborto por recurso antes do corte ou exclusão verificável. Se fora de âmbito, o veredito limita-se à operação fixa comprovadamente isolada. | F04/F10 |
| V06 | UNKNOWN e ausência de retry são corretos, mas a linha reúne pontos com consequências distintas. | Casos separados antes/depois da confirmação durável de admissão, consumo, D09, fence e efeito. Ler estado sem emitir capacidade; medir consumo irreversível, iniciação e payload; falha de confirmação D09 bloqueia progressão dependente. | F03/F07/F08 |
| V07 | Abrange ligações principais, não falhas assimétricas/correlacionadas nem retorno de respostas antigas. | Partição unidirecional, perda seletiva/duplicação/reordenação, isolamento simultâneo de W e F, retorno tardio e múltiplos caminhos. Verificar C5 da tentativa original; negar confirmação global incerta não prova contenção física. | F04/F08/F09 |
| V08 | Crash por transição é necessário; «cada transição» depende de máquina de estados ainda ausente. | Enumerar pontos persistentes, flush/ack, recovery e versões; casos de queda de energia/storage separados de morte de processo. Exigir consumo/ordem/fence sem regressão ou quarentena, sem reativação automática. | F05/F10 |
| V09 | Testa persistência do corte e rotas alternativas; falta controlo de criação posterior de novo recurso/credencial. | Re-registo, re-enrolamento, expansão de topologia, restauro de ACL/CA e credenciais de recuperação; confirmar que poderes legítimos de manutenção não reabrem capacidades antigas sem processo aprovado. | F01/F02/F05 |
| V10 | Bindings/nonce são necessários; certificado copiado ou assinatura válida não comprovam atuação atual. | Atuar com hardware original por relay, encarnações no mesmo hardware, atestado antigo re-assinado com nonce novo, troca de canal/geração e rollback coerente. Observação atual autenticada com continuidade persistente; nenhuma consulta cria permissão. | F02/F05/F11/F12 |
| V11 | Oito concorrentes é uma carga de exemplo, não um limiar probatório. Uma reserva única pode coexistir com várias chamadas à função. | Barreiras determinísticas em aquisição/consumo/efeito/rollback, replays na mesma e noutras sessões e ramos; contador de iniciações independente de commits/ledger transacional. Chamada direta exige consumo vinculado e não reutilizável. | F03/F06/F10 |
| V12 | Preserva a semântica correta do prazo, mas locks podem deslocar A se este ponto não for explicitado. | Identificar avaliação final serializada, incluir revogações de aprovação/chave/autoridade/política, resposta tardia e limites exatos L=not_before, U=expires_at, duração 900 s; ordem desconhecida bloqueia novas admissões. Não exigir elegibilidade no commit por inferência. | F03/F08/F09 |
| V13 | Bom teste de conteúdo e independência; hash isolado não basta. Falta definir eventos críticos e o corte temporal de confirmação. | Recuperar conteúdo integral por acesso independente, detetar mesmo ID/bytes divergentes, perda/restauro e retenção; confirmar eventos pré-execução antes de disponibilizar capacidade, resultados após observação antes de progressão dependente. Arquivar F não demonstra atuação F. | F02/F07 |
| V14 | Identifica atraso e continuidade; «erro declarado» pode ser autoatribuído e incorreto. | Justificar limite externo de erro e custódio, autenticação, bootstrap TLS/UTC sem dependência circular, suspensão/holdover, amostra autenticada falsa, assimetria e perda de continuidade; incluir interseção vazia ou intervalo invertido. Nonce e monotónico local não fornecem UTC. | F09 |
| V15 | Correto em separar reconciliação e retoma; falta provar quem pode produzir a nova decisão. | Inspeção read-only sem segredo de escrita, preservação de consumos/resultados, invalidação efetiva de todas as capacidades antigas, decisão humana autenticada/auditada e nova aprovação vinculada. Estado UNKNOWN não passa a seguro por timeout. | F02/F08/F11/F12 |

V01–V15 constituem um bom índice de riscos, mas ainda não um plano executável
nem prova de suficiência. Cada caso futuro precisa de topologia, precondições,
estado inicial, capacidade adversarial, barreiras de escalonamento, injeção de
falha, observadores, resultado esperado, evidência conservada, critério de
refutação e limites. Repetições aleatórias complementam, não substituem,
interleavings construídos. Controlos que reproduzem uma falha contam como
validação do oráculo, nunca como sucesso da garantia violada.

Casos compostos em falta: resposta perdida mais crash de F; W atrasada mais
restauro de A; partição multipath mais re-registo; rotação de CA mais snapshot de
credenciais; primeiro recurso cortado reaberto antes do último; efeito direto
que não escreve ledger; efeito seguido de compensação. Nenhum destes casos é
declarado observado nesta revisão.

## Oráculos e limites de prova

Devem existir quatro observações distintas: admissão/consumo duráveis em A;
reserva e iniciação vinculadas; mutações e commit/abort no recurso; atuação e
persistência do corte. A cópia D09 conserva e confirma o conteúdo crítico e a
continuidade, sem ser automaticamente oráculo da verdade física de cada evento.

No bypass administrativo DEV-05, `value=1` coexiste com `effects=[]` e `claims=0`.
Assim, uma lista vazia não prova ausência de efeito. Payload final isolado também
não prova ausência de escrita transitória ou posteriormente revertida. Num
futuro UPDATE fixo, definir se o efeito contabilizado é a mutação física durante
a execução ou o resultado durável no commit; DEV-06 A:8–12 usa «mutação física» e
inclui commit posterior. A observação deve cobrir ambos os eventos relevantes,
sem mudar o critério para facilitar a aprovação. C4 exige observar iniciações,
mesmo quando o efeito/commit é zero.

A ordem causal deve demonstrar término antigo antes do corte eficaz e este antes
da confirmação. Timestamps entre máquinas, ausência de heartbeat, lista de
backends vazia, ack de API e assinatura do atuador são insuficientes isoladamente.
Uma janela finita sem efeito não prova impossibilidade futura: é necessária
análise de capacidades e persistência. Acessos independentes ao payload/storage,
captura de intervenções e controlos negativos devem evidenciar que o observador
deteta precisamente os efeitos que o controlador pode ocultar ou não registar.

## Custódia e ameaça a concretizar

| Responsabilidade | Prova documental e poder a segregar |
| --- | --- |
| Executor/aplicação e administrador de D | Listar snapshots, memória, dados, root, credenciais exportáveis, DNS e rotas que controla; provar ausência de poder transitivo sobre B/F/W/CA e backups externos. |
| A e continuidade autoritativa | Custódio nominal de consumo, ordem e recovery; provar que recuperar A não apaga admissões/revogações nem delega autorização a uma consulta. |
| B/storage e F | Quem pode escrever dados, confirmar corte, mudar firmware/configuração, reanexar volumes, re-registar, provisionar cópia e usar emergência; continuidade fora de D. |
| W/D09 e arquivo | Administração e identidade próprias, conteúdo recuperável, retenção, backups e acesso de auditor independentes; sem depender só do mesmo hipervisor ou conta global. |
| V/observação técnica | Quem aprova inventário e observa payload/atuador, credenciais read-only e recolha fora do poder de alteração do executor/controlador; explicitar restantes componentes confiados. |
| PKI/identidade/UTC | Custódios e recuperação das raízes, enrolamento, rotação/revogação e bootstrap temporal; matriz de quem consegue substituir confiança ou fonte de tempo. |
| Reentrada/incidente | Pessoa que reconcilia, pessoa que decide e identidade que aprova o novo pedido; independência humana não decorre de duas contas ou de revisão por agente. |

Nenhum nome, fornecedor, mecanismo ou pessoa é aqui inventado. Os custódios
continuam **não identificados nos artefactos revistos**. O modelo pode confiar em
B/F, mas tem de o dizer: observação de um componente confiado ajuda a verificar
falhas, não demonstra resistência ao compromisso arbitrário desse componente.
Compromisso/conivência global permanece fora da garantia candidata, sujeito a
aceitação humana explícita. Disponibilidade não é garantida: drain pode esperar
indefinidamente; abort pode consumir sem efeito; incerteza pode bloquear reentrada.

## Condições de aceitação e decisão seguinte

| ID | Condição necessária | Evidência/decisão e bloqueador |
| --- | --- | --- |
| AC01 | Fronteira física de efeito e domínio D explícitos, incluindo clones/backups/memória. | Decisão humana sobre alcance e poderes. Se uma cópia gravável arbitrária continuar permitida, o critério forte é inviável (F01). |
| AC02 | Uma topologia candidata concreta, com mapa de todos os meios e caminhos de escrita e poderes nominais. | Custódios, raízes, recuperação, manutenção e exclusões verificáveis; sem admin global coberto por inferência (F02). |
| AC03 | Máquina de estados de admissão, reserva irreversível e efeito vinculados à mesma tentativa/sessão/transação. | Crash e ack perdido em cada fronteira; função direta sem consumo impossível no modelo; zero libertação por rollback (F03). |
| AC04 | Mecanismo selecionado com ordem efeito terminal–corte–confirmação e exclusão persistente. | Drain/abort, filas/2PC, multipath e cortes por recurso; sem retorno favorável parcial ou timeout tratado como cessação (F04). |
| AC05 | Continuidade e recuperação externas ao conjunto copiável, sem regressão ou reabertura antiga. | Backups/ACL/enrolamento e capacidades de recuperação abrangidos; incerteza em quarentena (F05). |
| AC06 | Plano de oráculos que deteta iniciações, mutações diretas e efeitos sem ledger. | Recolha/credenciais/administração independentes, controlos negativos e ordem causal por recurso (F06). |
| AC07 | Protocolo D09 com conteúdo e corte de eventos claros, sem circularidade. | Confirmação anterior à capacidade executável, resultado posterior, divergência/retenção/recuperação e custódio independente (F07). |
| AC08 | UTC e bootstrap com origem, custódio e orçamento de erro justificáveis. | Aplicação das fórmulas apenas em A; frescura de atestado separada; erro desconhecido bloqueante (F09). |
| AC09 | Plano V01–V15 refinado e significado do atestado explicitamente decidido. | Casos compostos, exclusões, evidência terminal, política de partições/UNKNOWN e continuidade da tentativa original (F08/F10/F11). |
| AC10 | Pacote revisável com limites de ensaio, recursos próprios, impacto, limpeza e critérios de paragem. | Revisão técnica e decisão humana próprias; schema/bytes R2 e integração aprovados separadamente se necessários. Sem abertura automática de gates (F12). |

AC01–AC10 são condições para reapreciar a candidatura a um **ensaio delimitado**.
Não exigem que a resistência empírica futura já tenha sido demonstrada nesta
fase documental; exigem desenho e plano concretos que permitam autorizar e
interpretar essa demonstração. A eventual passagem dos ensaios seria evidência
limitada à topologia/ameaça, nunca aprovação automática de produção ou prova
universal. Aceitação operacional exigiria evidência real das propriedades
reivindicadas e decisões próprias posteriores.

Recomenda-se R2-DEV-08 documental para preencher essas condições, com decisão
explícita entre manter o requisito forte e impedir cópia gravável, ou reconhecer
a inviabilidade sob os poderes atuais. Nenhuma alteração de alcance, aprovação
arquitetural, ensaio, infraestrutura ou integração fica autorizada por esta recomendação.
