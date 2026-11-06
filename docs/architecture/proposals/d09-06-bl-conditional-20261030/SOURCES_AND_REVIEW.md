# D09-06 B-L — fontes, revisão e resumo executivo

30/10/2026 · Europe/Lisbon · Proposta documental; não é atestado UTC ou aprovação humana dos presentes bytes.

## Resultado

Foi preparada a [especificação B-L v1.0](SPECIFICATION.md) para a revisão humana final solicitada. Desenvolve a variante técnica preferida já aprovada condicionalmente, sem refazer a comparação/seleção, e acrescenta o [índice de continuidade](../../../project/CONTINUITY.md) como proposta não normativa. O arquivo [RECOVERED_SOURCES.json](RECOVERED_SOURCES.json) evita depender novamente de resumos ou de anexos temporários para recuperar os textos D09-05/06 e os sete cenários.

As aprovações conceptuais D09-05/06 foram identificadas como decisões ainda sem registo dedicado localizado no repositório. A especificação e o índice remetem para a autoridade humana atual e para as fontes recuperadas. Não se criou um novo ato de aprovação, não se atribuiu ao agente a decisão e não se promoveu a proposta a norma. P4-B4 já tinha registo remoto próprio e não foi repetido.

Não há bloqueio documental material que impeça apresentar a especificação: as fontes antes ausentes foram recuperadas em chats acessíveis. Permanecem bloqueadores técnicos de implementação e demonstração, sobretudo C4 perante executor comprometido, independência transitiva, conteúdo/continuidade recuperáveis, suficiência de recursos e invalidação de capacidades antigas. Nenhum deles justifica declarar que B-L já está demonstrada ou repetir agora uma auditoria de infraestrutura.

## Fontes efetivamente consultadas

| Ref. | Fonte / localizador | Uso e limite |
| --- | --- | --- |
| H-ACTUAL | Anexo humano `C:/Users/Paulo/.codex/attachments/74ea19b1-5bf6-463b-8390-e116ea05e26a/Pasted text.txt`, «Continuidade Autónoma de Desenvolvimento». | Autoriza a etapa documental e reafirma D09-05/06, operador único, estados e restrições. É a fonte humana direta desta execução. |
| S05 | Chat `01a18cf5-a5d2-7711-98b8-5292296ea673`, título «Desenhar conceptualmente a Alternalt», resposta `msg_0d1aafcd4bf7cdf0016ae499692f34819196e508884ea8d572`. | Texto integral D09-05 recuperado, incluindo funções, dependências, sete cenários e recuperação. Resposta do agente é fonte do desenho; a aprovação conceptual procede do mandato humano e da continuidade posterior. |
| S06 | Chat `01a18d4c-843c-7652-905b-e9141ee7f1ca`, título «Preparar proposta técnica D09-06», proposta `msg_052ca9cf3623bc46016ae4b043e2f48191b91353021a3ea1fc`. | Comparação integral B-L/B-N recuperada, com definição original B-L. Não foi reconstruída por suposição nem foi necessário escolher novamente a variante. |
| H06 | Mesmo chat, mensagem humana `01a18d52-505c-7ef2-824c-a93667421cc3`, «sim», e resposta subsequente identificadas no arquivo. | Aprovação da preferência condicionada em contexto; o mandato humano atual reafirma expressamente esse objeto. Não aprova esta especificação, recursos ou implementação. |
| S03 | Chat `01a18cb1-b26d-7512-852f-d6c69f4ff8c2`, «Mapear dependências reais do D09», resposta `msg_0992fa4c248ee9c7016ae488ad20b08191a3f07e8067bdb70c` e pedido humano dessa tarefa. | Recuperados os sete cenários exatos e os limites da evidência histórica. Não se repetiram os seus acessos operacionais ou tentativas de autenticação. |
| R2 | Remoto `docs/architecture/auth-boot-02-r2.md`; rastreabilidade conhecida nesta continuidade. | C1–C7 relidos no contrato: admissão, prazo em A, ordem, exclusividade, incerteza, evidência/recuperação e separação de versões. Não alterados. |
| R1 | Remoto `docs/architecture/auth-boot-02-r1.md`, §§11–12. | D09/D10 relidos: conteúdo, confirmação independente, continuidade e recuperação. Recomendação histórica de duas pessoas não foi imposta contra o modelo humano atual. |
| P4 | Remoto `docs/architecture/decisions/dr09a-p4-b4-acceptance-20261030.md`. | Ato posterior aceita bytes D1/D2/D3 e encerra apenas a etapa documental. Evita reabrir pendência histórica já resolvida. |
| D2 | Remoto `docs/specifications/f0/dr07-retention-addendum.md`, V05-02–V05-06. | Distinção D09/V05-06, conteúdo recuperável, retenção R2 e resultados COMPROVADO/FALHA/INDETERMINADO. Não se escolheu retenção. |
| Q/H02 | Locais `experiments/auth_boot_02_r2_h02_inventory/CONSOLIDATION_Q01_Q05.md` e `docs/reviews/production_h02_20261028/MATRICES.md`. | Reutilizados inventário histórico parcial e progbox exclusivamente DEV. A consolidação Q não existe no caminho remoto tentado; foi consultada na cópia local, sem inferir perda ou necessidade de nova recolha. |
| D3 | Local `docs/reviews/release_1_0_consolidation_20261028/dr07_retention_successor/ADDENDUM.md`. | Síntese e remissões existentes, com cabeçalhos históricos preservados; o ato P4-B4 resolve posteriormente a aceitação final dos bytes. |
| CONTEXTO | Chats «Planeamento das lacunas» e «Especificar variante B-L D09-06». | Confirmam dificuldade anterior de acesso aos anexos; não foram tomados como fonte do texto ausente. Nesta etapa os desenhos foram recuperados nos chats autores. |

Os textos exportados são cópia do conteúdo devolvido pelo serviço de leitura de chats, com IDs, título e turno. Não se afirma identidade byte a byte com os antigos ficheiros anexos `Pasted text(20261030-145145).txt`/`Pasted text(20261030-154604).txt` nem certificação da sua custódia. Os textos integrais dos desenhos estão disponíveis; essa reserva de identidade do anexo não impede a proposta autorizada. Não se usaram respostas representadas apenas por referências de conteúdo para inventar texto.

Os factos SynologyShared NFS e Backup permitido são recuperados da comparação D09-06/reconciliação. Q05 tinha deliberadamente limitado a transcrição formal a local-lvm; não se apresenta Q05 como tendo inventariado o NAS ou demonstrado backups. Cinco nós e discos da VM105 são observações históricas, sem nova verificação de atualidade, capacidade livre ou suficiência.

## Coerência verificada na redação

| Pedido | Local de resposta na especificação |
| --- | --- |
| Objetivo, âmbito, pressupostos e exclusões | §§1–2. |
| Funções e fronteiras de confiança | §3. |
| Poderes e dependências transitivas | §4, com operador único e exclusão total delimitada. |
| Admissão durável → D09 → disponibilização | §5, sem atomicidade distribuída e sem confundir confirmação com commit. |
| C4 no alvo e comprometimento do executor | §6, incluindo contorno direto e limite do clone gravável. |
| Recuperação e reentrada humana | §§7 e 9, sem retry/retoma e com C5 preservada. |
| Sete cenários D09-03 | §8, com fundamento sobrevivente, controlo de bloqueio e limite por cenário. |
| Demonstrações de independência/recuperação/bloqueio | §§8 e 11. |
| Lacunas efetivamente pendentes | §11, sem renumerar RG/H/GAP nem inventar fecho. |
| Aceitação e próximos passos condicionados | §§12–13. |
| D09 distinto de V05-06 | §10, por remissão a D2 aceite. |

Não se executou demonstração técnica ou auditoria independente. A verificação de redação confirma cobertura/coerência do documento, não segurança operacional. A insuficiência de recursos não foi provada; a suficiência também não. Mantêm-se por demonstrar independência perante poderes delimitados, continuidade recuperável, D09, V05-06 e imposição C4. O compromisso transversal total continua excluído; uma credencial limitada não recebe essa exclusão por conveniência.

## Âmbito da execução e preservação

Confirmados por leitura do repositório: branch main, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`, quatro tracked modificados e untracked preexistentes. Não se encontrou AGENTS.md na árvore remota ou ancestrais pesquisados nem na árvore local. Não foram executados comandos Proxmox/Synology, consultas a serviços/bases, inventários operacionais, scans ou ensaios. SSH foi usado exclusivamente para ler documentação/estado Git de progbox e entregar estas propostas novas, sem acesso a interfaces da infraestrutura.

Foi guardada comparação documental prévia de Markdown/JSON já existentes em docs e experiments nos dois destinos e do estado Git remoto. Não é auditoria geral da infraestrutura nem snapshot universal do filesystem. A verificação final confronta esses mesmos bytes, procura adições fora dos novos caminhos autorizados, e compara HEAD/branch/status/diff, filtrando exclusivamente esta entrega. [PRESERVATION.json](PRESERVATION.json) regista os resultados e hashes da entrega; os seus próprios bytes são comparados separadamente entre cópias, sem hash autorreferente.

Os hashes remotos de D1 e D2 consultados continuam respetivamente `0c561312e96096e64b342b14e1023037481e55076c204720cc834565c4b65a82` e `a996d78fff71002db47f2756836669fd3f096bff3074bae10c98c31afdaab818`, iguais aos aceites em P4-B4. Isso fixa bytes, não constitui nova aceitação. NC-01 e D3 não são editados. A comparação documental local abrange D3; não se alega uma nova auditoria do conteúdo integral de NC-01.

Só se acrescentam a pasta isolada desta proposta e docs/project/CONTINUITY.md, ambos de trabalho não aprovado. Fontes recuperadas são dados documentais, não código operacional. Diretórios e documentos da entrega permanecem como resultado; nenhum recurso de laboratório, conta ou serviço foi criado, reservado ou removido. Os processos transitórios de leitura e transferência terminam sem limpeza de recursos preexistentes.

## Revisão final e próxima etapa

Solicita-se apenas a revisão final dos bytes da especificação B-L v1.0 como documento condicionado; o índice permanece proposta auxiliar, sem autoridade normativa. Não é preciso voltar a aprovar a preferência B-L já decidida. Uma revisão favorável não autoriza implementação nem arquitetura física.

Próxima etapa recomendada: preparação técnica documental do mecanismo de disponibilização e imposição C4, com fundamento sobrevivente por cenário e recuperação. Reutilizar fontes existentes. Apenas escolhas materiais que alterem arquitetura, garantias, recursos ou gates exigem nova decisão específica. Até à revisão final, a atividade autorizada permanece a preparação e conferência desta proposta.

P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados/bloqueantes; H02–H12/GAP-001/002 bloqueantes; RG1–RG7, D09 e V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial. Sem commits, push, merge, código operacional, SQL, instalações, deployments ou atribuição física.
