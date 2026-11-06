# R2-DEV-08 — fronteira de recurso e caminhos de efeito

Estado: PROPOSTA NÃO APROVADA. Termos deste documento são notação analítica, não campos de schema, enums operacionais ou alterações contratuais.

## Propriedade e domínio explícitos

Para uma tentativa antiga q e conjunto de recursos R, a afirmação proposta é: depois do corte terminal de cada recurso, q não consegue iniciar mutação física nem confirmar trabalho anteriormente iniciado em qualquer recurso abrangido; a confirmação global sucede causalmente a todos esses cortes e à prova da sua manutenção contínua. Efeitos anteriores são reconciliados, nunca desfeitos por declaração. A exclusividade de iniciação C4 é verificada separadamente da contagem de commits e efeitos.

O efeito da primeira classe de laboratório continua a ser o UPDATE fixo sobre payload sintético identificado, incluindo mutação física durante a execução e resultado durável/commit. Mutação depois do corte, ainda que desfeita por rollback ou compensação, refuta a alegação de ausência de mutação; commit posterior de trabalho antigo refuta a alegação de término antes do corte. Ledgers não são a definição do efeito. Alterações de fence/ACL são intervenções de contenção registadas separadamente; não podem alterar payload disfarçando efeito protegido. Alembic, DDL, equipamentos e administração geral não são incluídos como operações autorizadas.

O domínio forte R* abrange original, réplicas promovíveis, ramos e cópias integrais capazes de realizar a operação, independentemente de serem publicados. Backups dormentes são capacidades de criar recursos: devem estar inventariados e a sua restauração não pode criar um novo meio de efeito fora da fronteira. A restauração para disco isolado e gravável passa a integrar R*. Uma simples exportação de dados com que o adversário possa reconstruir o payload e executar a operação também tem de ser avaliada; não é segura só por ser lógica.

D é o estado copiável/restaurável pelo adversário: aplicação/executor, memória, sessões, disco, WAL, roles, configuração, certificados exportáveis, chaves em software, ledger local e vTPM quando incluído. Se B, F, A ou W forem controláveis/restauráveis pelo mesmo adversário, entram igualmente em D; a fronteira externa deixa de estar demonstrada. Um nome, endereço, UUID, PID, certificado copiado ou system_identifier não prova encarnação única.

Uma fronteira exata exige a relação recurso físico → meios de persistência → caminhos de escrita → capacidade/principal → domínio administrativo → observador → barreira terminal. Sem qualquer elo, a cobertura é desconhecida. A versão do inventário e da política liga-se a cada pedido de contenção e atestado. Descoberta de novo meio não é adição automática ao alcance de um atestado antigo.

## Inventário efetivamente conhecido

| ID | Facto documental/observado | Alcance e limite |
| --- | --- | --- |
| K01 | SSH como paulo e checkout em `/home/paulo/projects/livenet-v2`, HEAD registado em PROVENANCE. | Acesso a ficheiros, não inventário operacional de bases, hipervisores ou storage. |
| K02 | DEV-04/05 descrevem PostgreSQL 16 em clusters descartáveis com sockets privados e cópias físicas dos dados com alvo parado. DEV-05 regista clone vivo gravável. | Recursos históricos removidos segundo a evidência; nomes temporários não são destinos atuais nem autorizados. Não demonstra snapshot de memória ou de VM. |
| K03 | DEV-05 tem fence transacional local, papéis SQL restritos e controlador administrativo confiado; todos os clusters partilham host/utilizador/administrador. | Não há segregação administrativa demonstrada, corte físico ou cobertura de clone independente. |
| K04 | R1-D10 exige autoridade única em VM Proxmox dedicada, separada da aplicação e VMs PostgreSQL. | Determinação arquitetural; VMID, host e custódio concretos não verificados. |
| K05 | environments.md e baseline F0 preveem DEV progbox, STAGING Proxmox, PROD VM; LAN-only vinculativo. | Não identifica deployment atual validado nem capacidade livre. VM exclusiva G4 sem NIC é outra fronteira. |
| K06 | DEV-02–05 mantêm executable=false, UTC autenticado ausente; DEV-04/05 mantêm D09 independente não demonstrado. | Evidência histórica de bloqueio, sem nova verificação dos serviços. |

Esta tabela não é inventário fechado de R*. A ausência documental de um caminho significa lacuna, não ausência operacional. R* não pode ser declarado integralmente conhecido com as fontes disponíveis.

## Catálogo de escrita a fechar antes de ensaio favorável

| Caminho | Evidência/estatuto atual | Controlo candidato e prova exigida | Responsável proposto |
| --- | --- | --- | --- |
| W01 API/broker, ligação SQL normal e sessão antiga já aberta | DEV-05 demonstra verificação local até término; não uma solução integrada C1–C7. | B medeia a operação fixa e vincula consumo/sessão/transação; corte inclui conexões existentes e trabalho em voo. | A/B/F |
| W02 chamada direta da função autorizada, replay e outra sessão | Contraexemplo DEV-05: claims=0/value=1. | Toda entrada, inclusive direta, exige a mesma reserva consumida e início único; retirar SQL arbitrário do executor não basta se outro principal contornar. | B |
| W03 owner, superuser, herança/SET ROLE, SECURITY DEFINER, DDL de função/trigger, extensões | Bypass administrativo histórico observado; enumeração real desconhecida. | Inventariar poderes efetivos e owners; administradores de B são base confiada explícita ou há mecanismo externo que lhes retira escrita. Não alegar resistência a superuser com ACL local. | Custódio SQL/B |
| W04 socket Unix, loopback, peer, credenciais de manutenção e emergência | Sockets/pin locais históricos; caminhos atuais não inspeccionados. | Cobrir acessos locais e administração; sem rota de emergência que reabra poder antigo. | OS/B/PKI |
| W05 transação aberta, statement preparado, prepared transaction/2PC, commit pendente | Janelas DEV-04 demonstradas; DEV-05 exclui 2PC na fixture histórica. | Término durável ou abort de cada pendência; comprovar 2PC desativado e ausência de transações preparadas se excluído. Statement preparado não demonstra 2PC. | B/F/V |
| W06 replicação física/lógica, promoção, réplicas, PITR, WAL arquivado e restore | Não há inventário operacional localizado. | Mapear cada destino e quem promove/restaura; impedir capacidade de escrita independente fora de B e continuidade. | Storage/backup/B |
| W07 jobs, workers, scheduler, triggers, notificações/outbox e efeitos externos | Classes previstas no runtime; capacidade real neste escopo desconhecida. | Para UPDATE mínimo, demonstrar ausência/desativação de efeitos laterais e destinos; caso contrário incluir cada destino/barreira ou bloquear. | B/aplicação/V |
| W08 escrita por root no filesystem/dispositivo, acesso raw, consola/debug/memória/DMA | Poder potencial do domínio administrativo; não demonstrado em execução atual. | Retirar esses poderes de D sobre B e seus dados; verificar dispositivos, montagem e memória. Se adversário os mantiver, propriedade não demonstrável. | OS/hipervisor/storage |
| W09 snapshot/clone de VM, disco, memória, credenciais, vTPM, migração/exportação | Clone físico de dados é facto histórico; snapshot de VM/memória não ensaiado. | Inventariar cópias e destinos. Clone integral gravável adversarial mantém inviabilidade; não substituí-lo por clone só do cliente e declarar V03 satisfeito. | Hipervisor/backup |
| W10 backups restauráveis, dumps, réplicas offline, imagens e cópias em media amovível | Restauração histórica revive epoch/ledger. Lista de backups atuais ausente. | Inventário de leitores/exportadores/restauradores, destino e retenção; restauração apenas em quarentena sob B/continuidade. Cifragem em repouso não elimina poder de quem restaura ou exporta plaintext. | Backup/continuidade |
| W11 storage local/partilhado, multipath, cache, WAL/data/tablespaces separados, fabric, reanexação e novo iniciador | Dispositivos e reservas persistentes não verificados. | Atuador em cada caminho e pendência; impedir re-registo/reanexação e rollback da configuração. Um disco independente escapa a reserva no original. | Storage/F |
| W12 rede alternativa, DNS/route, túnel, endpoint e ligação sobrevivente | Pin rejeita endpoint clonado nos ensaios; isso não impediu escrita autónoma DEV-05. | Inventariar caminhos LAN/gestão; controlar sessões existentes. Firewall ou mTLS de novas ligações não é prova de cessação no meio. | Rede/B/F |
| W13 recuperação de A/B/F/W/CA/ACL, rotação e re-enrolamento | Snapshot coerente pode restaurar permissões; mecanismos atuais pendentes. | Raiz de continuidade fora do conjunto restaurável por D; nenhuma recuperação apaga consumo ou revalida capacidade antiga. | Continuidade/PKI/backup |

Para cada Wnn, o inventário nominal futuro deve fornecer identificador e localização do meio, geração, leitores/escritores, heranças/poderes transitivos, cópias/exportações, componente de imposição, prova independente, recuperação e decisão de inclusão/exclusão. Não há exemplos inventados de endereços, pools, VMIDs ou contas. Cada célula não preenchida mantém o caminho UNKNOWN/BLOCKED.

## Condição para a candidata externa

Na opção de fronteira externa, D contém só executor/aplicação e credenciais sem poder autónomo sobre os dados; B e todos os meios que permitem reconstruir uma cópia gravável ficam sob custódia confiada fora de D. Não basta mover um endpoint: o adversário não pode obter o conjunto de dados/meios/privilégios que recria a operação protegida de forma autónoma. Limitar a capacidade de reconstrução pode ser impraticável quando o adversário tem leitura integral; isso é bloqueador a resolver, não hipótese gratuita de criptografia ou HSM.

Esta é uma alteração explícita dos poderes adversariais relativamente ao clone integral histórico e exige H01/H02. Se não puder ser demonstrada, a candidata externa não satisfaz o requisito forte. Uma alternativa que proteja apenas publicação/serviço oficial é uma garantia diferente, dependente de aprovação expressa e sem satisfação retroativa de C4/C6/GAP-001.
