# R2-DEV-08 — critérios verificáveis de ensaio futuro

Estado: **PLANO PROPOSTO, NÃO APROVADO E NÃO EXECUTADO**. Nenhum cenário abaixo é resultado DEV-08. Aprovação futura do plano não equivale a aprovação de produção, schemas ou abertura de gates.

## Pré-condições e observação

Exigir antes de um ensaio com pretensão independente: H01–H10 pertinentes decididas; H11 quando se usarem formatos executáveis; inventário nominal fechado e seu digest; custódios reais com poderes transitivos verificados; recursos sintéticos próprios e impacto aprovado; atuador/mecanismo selecionado; observadores e recolha realmente independentes; plano de barreiras/falhas e limites documentados. Recursos não disponíveis ou caminhos não demonstrados produzem BLOCKED/NOT_DEMONSTRATED, não SKIP convertido em sucesso. Um estudo funcional no mesmo administrador deve ser classificado como tal.

| Oráculo | Facto que deve observar | Limite e validação exigida |
| --- | --- | --- |
| OA | Ordem, avaliação UTC, consumo e vínculos duráveis em A. | Não conta efeitos nem demonstra que B iniciou. Ler por acesso independente do executor. |
| OB | Reserva/compromisso de início e entradas reais na operação, ligadas à sessão/transação/encarnação. | Contar inícios abortados e concorrentes; ledger transacional não prova início único. |
| OE | Mutações no payload/meio e resultados terminais commit/abort em cada ramo. | Captura independente que detete bypass sem ledger, mutação transitória e efeito compensado. Se não os detetar, o oráculo falha e o caso é inconclusivo. |
| OF | Atuação real e persistência do corte em cada meio, incluindo pendências e caminhos alternativos. | Ack/assinatura de F não bastam; observação independente de estado do atuador e barreira terminal. |
| OW | Conteúdo integral/continuidade W e confirmação antes da capacidade; resultados posteriores. | Não usa arquivo de declaração de F como prova física de F. Testar ausência/divergência/restauro. |

Cada execução futura deve conservar versões, hashes/fontes, topologia, recursos/gerações, principals/canais, políticas, pressupostos, ordem/barreiras, início/efeito/corte observados, falhas e intervenções, resultados contraditórios, stdout/stderr pertinentes, conteúdo D09 recuperável e limpeza. Redigir método e completude da captura de mutações antes de testar; não escolher só o payload final por ser mais fácil. Timestamps entre máquinas não estabelecem ordem causal. Uma janela finita sem efeito não prova impossibilidade futura: é necessária análise de capacidades e persistência.

## Caso decisivo E03: clone antigo vivo e gravável

Precondição: original e clone integral em meio independente, dados/roles/WAL/credenciais e estado antigo documentados, processo e sessão antigos vivos no clone. O adversário tem os poderes de escrita que H01 diz cobrir. Documentar separadamente cópia física de dados com alvo parado e snapshot de VM/memória; o primeiro não prova o segundo. O observador OE tem acesso independente ao próprio meio do clone e valida que deteta uma mutação sem ledger.

Barreiras: primeiro comprovar em fixture autorizada que o clone pode escrever antes do corte, sem consumir a aprovação que será usada no caso principal; depois manter sessão/contexto antigo vivo, pedir contenção do conjunto, observar os cortes locais e a eventual confirmação global. Só após receber causalmente essa confirmação, libertar a tentativa antiga no clone para a operação fixa, incluindo chamada direta e, se dentro do modelo, SQL privilegiado. Observar mutação e commit/abort no clone e original. Não desligar o clone, não remover a sua credencial e não trocar por cliente sem dados para fabricar sucesso.

Critério: qualquer efeito antigo no clone depois do corte refuta a propriedade; se houve confirmação global, refuta também essa confirmação. Rejeição do endpoint oficial, zero clientes no clone, novo ramo saudável ou ledger vazio não são aprovação. Se o sistema recusar confirmar porque não controla o clone, isso é comportamento seguro de bloqueio, mas **não é demonstração de cessação universal**.

Se O1 impedir a criação do clone de B, o ensaio deve demonstrar a prevenção perante os poderes administrativos/backup/exportação efetivamente aprovados, com observação independente. Declarar a precondição impossível sem essa prova não passa E03. Conservar em separado o contraexemplo histórico integral, classificar a mudança explícita de poderes e ensaiar clones do executor com sessões antigas contra B. Estes casos não substituem nem reclassificam o contraexemplo histórico. Mantendo a cópia gravável adversarial, o resultado honesto é a inviabilidade/bloqueio já identificada.

## Matriz de casos e refutação

Cada linha herda as pré-condições/arquivo acima; a execução só será especificada após topologia nominal. Os passos são desenhos de experiência, sem comandos operacionais.

| ID / rastreio | Precondição, barreira e falha a construir | Observadores e condição verificável / refutação |
| --- | --- | --- |
| E01 V01 / F01–03 | Para cada W01–W13, inventariar principal/capacidade; tentar operação pela entrada direta, socket local, owner/superuser e recuperação dentro da ameaça aprovada. | OB/OE/OF: nenhum caminho de efeito fora de B. Caminho desconhecido bloqueia; um sucesso refuta cobertura, ainda que sem admissão. Poder confiado excluído deve ter aprovação H03. |
| E02 V02 / F04 | Pausar antes do SQL, depois da mutação e durante commit; perder realmente o canal de guarda externo. Exercitar drain e abort separados. | OE/OF: cada término antigo precede T_i e confirmação. Commit/mutação antigos posteriores refutam. Não aceitar lock externo como barreira do recurso. |
| E03 V03 / F01,F06 | Clone integral vivo e gravável, conforme descrição detalhada anterior; tentativa libertada depois da confirmação. | OE no meio do clone; efeito é falha. Recusa de confirmação é bloqueio seguro, sem prova de cessação. |
| E04 V04 / F05 | Restaurar combinações antigas A/B/F/W/CA/configuração, dados/WAL, backups e memória quando permitida; preservar âncora externa separada para comparação. | OA/OB/OW/OF: consumos/ordem não regressam e poderes antigos não reabrem. Rollback coerente com nonce novo não passa; falta de continuidade exige quarentena. |
| E05 V05 / F04 | Criar pendências em transação, prepared statement, 2PC se habilitado, WAL/cache/I/O e fila externa; cortar com pendência deliberada. | OE/OF: término ou abort demonstrado antes de T_i. Se excluídos, prova verificável de desativação/ausência; qualquer pendência por resolver impede confirmação. |
| E06 V06 / F03,F08 | Em cada P2–P7 perder resposta antes/após persistência real, incluindo admissão, reserva, W pré-início, início e commit. | OA/OB/OE/OW: nenhum despacho sem confirmação, nenhuma repetição por consulta, aprovação sempre indisponível após consumo. Efeito real com resultado UNKNOWN é permitido como incerteza, nunca repetido. |
| E07 V07 / F08 | Partições direcionais/seletivas em executor–A/B, B–F, V–W e multipath; construir antes e depois da confirmação/início contínuo. | Todos: novos percursos bloqueados quando exigido; original confirmado/contínuo conserva C5 até corte. Silêncio nunca conta como cessação; não promover ramo isolado. |
| E08 V08 / F05 | Para cada transição P/Q, crash antes/depois de escrita durável e ack; separar morte de processo, VM, host e perda de energia/storage. | OA/OB/OF/OW: consumo/ordem/corte preservados ou quarentena. Nenhum arranque executa automaticamente; flags simuladas não sustentam alegações de falha física real. |
| E09 V09 / F02,F05 | Após corte, restart de host/controlador, reanexação, registo de iniciador novo, rota alternativa, restauro de ACL/CA e enrolamento. | OF/OE: capacidade antiga continua excluída em todos os caminhos. Reabertura sem processo aprovado refuta persistência; deteção posterior ao efeito não salva o caso. |
| E10 V10 / F05,F11 | Repetir atestado, usar nonce fresco com estado antigo, trocar geração/canal/encarnação, copiar certificado e usar hardware original por relay. | V/OF/OW: rejeitar vínculo/continuidade inválidos. Assinatura autêntica não prova atuação. Consulta de verificação não cria permissão. |
| E11 V11 / F03,F06 | Barreiras determinísticas antes/depois de admissão, reserva, compromisso, entrada, rollback/savepoint; concorrência mesma sessão, sessões e ramos distintos. | OA/OB/OE: no máximo uma tentativa e uma iniciação por aprovação; contar inícios com zero commits. Uma reserva com dois inícios refuta C4. Repetição não é aceite só por ser idempotente no payload. |
| E12 V12 / F09 | Serializar revogações de aprovação/chave/autoridade/política antes/depois de A; expirar durante lock e atrasar commit/resposta. Limites L=not_before, U=expires_at, duração=900 e superior. | OA: fórmulas C2 estritas, sem grace period; revogação anterior impede A; posterior não cancela. Commit posterior ao prazo não é falha C2. Ordem desconhecida bloqueia. |
| E13 V13 / F07 | W sem conteúdo, só hash, ack perdido, bytes divergentes para mesmo ID, retenção/perda/restauro; atrasar confirmação pré-início e de resultado. | OW/OB/OE: nenhuma capacidade/início antes de confirmação prévia; sem progressão dependente antes de resultado confirmado. Recuperar conteúdo integral; detectar conflito sem reescrever histórico. |
| E14 V14 / F09 | Origem UTC errada/autenticada, atraso assimétrico, suspensão, holdover, salto, bootstrap TLS/tempo, intervalo invertido/interseção vazia. | OA/V: provar limite de erro externo ou recusar admissão/frescura. Nonce/monotónico/NTS sozinhos não justificam UTC limitado; nunca erro zero presumido. |
| E15 V15 / F08,F11 | Resultado incerto; reconciliador só leitura; capacidades antigas deliberadamente sobreviventes; depois corte completo, ato humano e novo pedido/aprovação. | OA/OB/OF/OW: sem retoma/transferência; primeiro estado bloqueia. Novo fluxo só com invalidação demonstrada e aprovação nova; antigo consumo permanece. |
| E16 F04,F05 | Dois recursos: cortar primeiro, reabri-lo enquanto segundo ainda corta; combinar perda de ack com crash de F. | OF/OE/V: Q4 não confirma sem exclusão contínua de ambos; confirmação emitida refuta protocolo. Ordem causal, não aproximação de timestamps. |
| E17 F02,F05,F07 | W atrasada mais restore de A; multipath particionado mais re-registo; rotação CA mais snapshot de credenciais. | Todos: falha composta não promove estado coerente obsoleto; sem efeito/capacidade nova antes de continuidade e confirmação. Cada combinação fica registada separadamente. |
| E18 F06 | Controlos negativos: remover fence só na fixture, fazer escrita administrativa sem ledger, efetuar mutação seguida de compensação/rollback e observar iniciação abortada. | OB/OE devem detetar todos os eventos relevantes; falha do oráculo torna casos negativos inconclusivos. Reproduzir contraexemplo valida observador, não segurança. |

Casos com efeitos permitidos antes de T_i não são contabilizados como falha de cessação; devem ser reconciliados. Já a segunda iniciação da mesma aprovação viola C4 mesmo sem efeito. O julgamento separa propriedades satisfeitas, contraexemplos reproduzidos, bloqueios seguros e lacunas não demonstradas; não usa «N/N passaram» para transformar contraexemplo em prova universal.

## Cobertura de DEV-07 AC01–AC10

| Condição | Concretização DEV-08 | Obrigação ainda pendente |
| --- | --- | --- |
| AC01 | BOUNDARY e opções O0–O3 preservam o clone. | H01/H02 e possibilidade real de impedir cópia. |
| AC02 | CUSTODY e zonas propostas relacionam poderes e meios. | Nomes, recursos físicos e inventário fechado; não satisfeita por tabela funcional. |
| AC03 | P0–P7 especificam contexto, reserva e início. | Implementação do vínculo/registro não reversível e prova E01/E06/E11. |
| AC04 | Q0–Q5 definem ordem terminal e persistência. | Atuador real/compatibilidade, H05 e prova E02/E05/E16. |
| AC05 | Quarentena e recovery sem reativação definidos. | Âncora externa nominal e E04/E08/E09. |
| AC06 | OA–OW e controlos E18 distinguem iniciações/efeitos. | Captura real/completude/independência. |
| AC07 | Cortes D09 pré-execução e pós-resultado definidos. | Custódio, conteúdo, retenção e prova E13. |
| AC08 | Fórmulas/recusas C2 preservadas. | Bootstrap/fonte/orçamento UTC e E14. |
| AC09 | Significado de atestado e E01–E18/casos compostos propostos. | H04, topologia/parametrização e execução independente autorizada. |
| AC10 | Dossier e decisões/próxima etapa delimitados. | Recursos/impacto, autorizações e formatos se necessários. |

Não se declara AC01–AC10 satisfeitas integralmente. DEV-08 torna o desenho revisável e deixa os bloqueadores localizáveis; a seleção do mecanismo e a identificação dos custódios não podem ser inventadas para concluir prontidão.

## Paragem, preservação e limpeza de um futuro ensaio

Parar progressão e preservar evidência ao primeiro efeito fora de cobertura, confirmação falsa, segunda iniciação, perda de continuidade/oráculo, recurso desconhecido ou impacto fora do aprovado. Parar também criação de recursos ao exceder limites previamente aprovados. Não apagar o contraexemplo nem reexecutar para substituir falha por sucesso.

O plano autorizado futuro deve listar exatamente VMs/volumes/credenciais/processos sintéticos próprios, seus proprietários e dependências; fixar baseline antes da criação e comparação depois. Limpeza só por identidade/caminho/propriedade comprovados, nunca nomes genéricos ou glob de recursos preexistentes. Evidência fica preservada antes da remoção. Qualquer recurso próprio não removido deve ser declarado com motivo/risco/responsável. DEV-08 não criou esses recursos; apenas documentos e manifestos de preservação.
