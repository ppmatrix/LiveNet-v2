# H02 — proposta de perímetro para revisão humana

Estado: **PROPOSTA DOCUMENTAL; H02 PENDENTE**. Compatível com a direção de estudo O1 aprovada em H01 no pedido atual; O3 permanece complemento possível não aprovado.

## Domínio a descrever nominalmente

Conservar o efeito físico histórico de DEV-08: mutação do payload, incluindo mutação transitória/compensada, e commit de trabalho anterior são relevantes. Ausência de publicação, clientes, entrada no ledger ou acesso ao endpoint oficial não retira um ramo do âmbito. O UPDATE fixo de laboratório continua a primeira classe delimitada pelo contrato; Alembic, DDL e administração não passam a operações autorizadas.

Propor à validação H02 os seguintes conjuntos relacionados, sem afirmar que já estão fechados:

| Conjunto proposto | Elementos a identificar | Regra de inclusão a submeter |
| --- | --- | --- |
| Recursos de efeito B/R* | Original, ramos/cópias integrais graváveis, réplicas promovíveis e destinos reconstruídos capazes de executar a operação. | Qualquer ramo capaz de produzir o efeito conta, mesmo isolado e sem publicação. Não limitar B ao serviço oficial. |
| Meios de reconstrução | Discos/volumes, WAL/tablespaces/cache pertinentes, snapshots, backups, dumps/exportações, memória/credenciais/identidades quando suficientes. | Uma cópia dormente é capacidade de criar recurso: relacionar os leitores, meios e destinos que a tornam gravável. Não confundir arquivo inerte com efeito já observado. |
| Caminhos/principais | Todos os W01–W13 e capacidades diretas/herdadas/transitivas de escrita, criação de cópia, promoção, exportação ou reanexação. | Para cada elo recurso→meio→caminho→principal→administrador, registar fonte e confiança; NC mantém cobertura desconhecida. |
| Dependências de confiança/continuidade | A/F/W/V/P/K/T, hosts/hipervisores, storage, CA/ACL/IdP, enrolamento, tempo e recuperação associados. | Não renomear todos como payload B; incluir no mapa de dependências porque podem reabrir capacidade ou adulterar prova. Confiança e custódios dependem de H03. |
| Mudanças posteriores | Nova cópia, restore, exportação, promoção, migração, reanexação, rotação/re-enrolamento e alteração de administração. | Relacionar os poderes de criação futura, não só listar cópias presentes. Nova topologia/capacidade impede reutilizar uma alegação de cobertura anterior sem revisão. |

D deve ser descrito pelos seus poderes efetivos sobre dados/meios/recuperação, não apenas por uma lista de VMs. O1 exige estudar a retirada dos meios de cópia/escrita autónoma de B. Se D retiver leitura suficiente e um meio gravável independente, a restrição pode ser impraticável e a candidata continua bloqueada. Não excluir silenciosamente esse efeito, nem aceitar administrador global/conivência fora da ameaça por decisão do agente.

## Condições documentais de completude a propor

- Cada recurso/cópia/meio tem identificador contextual, geração/localização, fonte datada, custódio por confirmar/confirmado, relações, poderes e destinos de reconstrução.
- W01–W13 têm ligação nominal a recursos/principais ou justificação documentada para ausência/exclusão proposta; nenhuma lacuna é convertida em ausência operacional.
- Identificar poderes sobre hipervisor/OS/storage/backup/memória/identidade e recuperação de cada domínio; não provar independência com VMs ou contas separadas.
- Delimitar capacidades que H01/O1 manda estudar retirar; identificar mecanismo/evidência existente e o que continua por demonstrar. Não declarar capacidade externa instalada.
- Distinguir integridade do inventário, confiança administrativa, política de corte e observação: H02 não decide H03/H04/H05/H08.
- Aprovação eventual deve ser humana, identificável, vinculada à versão exata e recursos/poderes/exclusões; não inferida de «continuar».

Estes são critérios propostos de revisão documental, não novos contratos, schemas, enums ou controlos instalados. A evidência disponível não satisfaz o fecho nominal: [GAPS.md](GAPS.md) permanece toda pendente.

## Limites das decisões futuras

H02 aprovaria um inventário/ameaça física expressos; não aprovaria por si custódios/base confiada (H03), significado de atestado (H04), atuador/drain/abort (H05), protocolo (H06), continuidade (H07), D09/observação (H08), UTC (H09), impacto/disponibilidade (H10), formatos (H11) ou plano/ensaio (H12). Nenhuma dessas escolhas é tomada neste dossier.

Não há seleção de produto, corte de energia/storage, concessão de privilégios, implantação, ensaio, autorização R2-DEV-09-PLAN ou DEV-09B. O3 não é aplicado por esta proposta. Gates fechados, GAP-001/002 abertas e contratos/modelo de ameaça preservados.

