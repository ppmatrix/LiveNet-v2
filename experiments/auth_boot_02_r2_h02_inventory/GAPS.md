# H02 — matriz de lacunas e perguntas para validação humana

Estado: todas as linhas PENDENTES. L01–L13 são IDs editoriais, sem renumeração de GAP ou H. Responder com documentação existente, fonte/data, identidade de quem confirma, confiança, ressalvas e recursos exatos. Nenhuma linha autoriza consultas ao ambiente.

| Lacuna | Pergunta concreta | Evidência nominal necessária / relação | Responsabilidade funcional a identificar |
| --- | --- | --- | --- |
| L01 Recursos/VMs | Quais hosts/VMs/containers alojam aplicação, PostgreSQL, A e os componentes candidatos B/F/W/V? Quais existem e quais são apenas previstos? | Identificador/namespace, geração, ambiente, host físico, localização e relação de alojamento; I01–I05/I13; W08/W09. | Projeto e custódio de host/hipervisor; nomes NC. |
| L02 Persistência | Onde estão dados, WAL, tablespaces, volumes, caches e todos os caminhos de escrita? Existem meios locais ou partilhados e reanexação? | Relação recurso→meio→caminhos/iniciadores→administrador, incluindo montagens e destinos documentados; I09/I14; W08/W11. | SQL/OS/storage, NC. |
| L03 Snapshots e criação posterior | Que snapshots/clones existem, incluindo disco/memória/identidades quando aplicável? Quem os pode criar depois do inventário e para onde? | Catálogo datado de cópias, dependências e poderes/destinos de criação, exportação/migração; I07/I08/I11/I12; W09. | Hipervisor/backup/confiança, NC. |
| L04 Backups/restore | Que backups/dumps/réplicas offline/media/arquivos WAL existem? Quem lê plaintext, possui chaves ou restaura em disco independente? | Catálogo e destinos, retenção, leitores/exportadores/restauradores e procedimento de quarentena/continuidade; I10; W06/W10/W13. | Backup/continuidade, NC. |
| L05 Poder autónomo de D | D consegue obter dados suficientes para reconstruir B, inclusive por leitura normal, exportação lógica, memória ou combinação de cópias? Que poderes O1 pretende retirar e por que mecanismo documentado? | Matriz capacidade→dados/meios→destino gravável→restrição demonstrável. Ausência de mecanismo mantém bloqueio; I12/P05; W02/W08–W11. | Responsável pelo estudo O1 e custódios, NC. |
| L06 Entradas SQL e privilégios | Quem escreve diretamente, por função, owner/superuser, herança/SET ROLE, DDL/extensões, socket local ou manutenção? | Principais e poderes diretos/transitivos; função de efeito e percursos de contorno; P02/P03; W01–W04. Sem credenciais em claro. | SQL/OS/PKI, NC. |
| L07 Trabalho pendente | Há transações, commits/I/O pendentes, statements preparados ou prepared transactions/2PC relevantes? | Política e evidência documental de capacidades/configuração; ausência não inferida da fixture; W05/W11. Escolha drain/abort reservada a H05. | Recurso/atuador, NC. |
| L08 Réplicas/efeitos laterais | Que réplicas/promotores, jobs/workers/triggers/outbox/serviços externos podem produzir efeito ou novo ramo? | Mapa de destinos e poderes de promoção/efeito; exclusões justificadas por fonte; W06/W07. | Aplicação/SQL/backup, NC. |
| L09 Administração transitiva | Quem administra OS, hipervisor, storage, consolas, CA, IdP/reset, CI/contas de serviço e recuperação? Existe administrador global comum? | Pessoas, substitutos, delegações/heranças/emergência e pares de domínios controláveis; P04–P06; W03/W08/W09/W13. Confiança/conivência decididas em H03. | Titulares humanos por nomear. |
| L10 Rede/gestão | Quais percursos LAN, gestão, DNS/rotas, túneis e sessões sobreviventes estão documentados e aprovados? | Mapa nominal de percursos e domínios administrativos; W04/W12. LAN-only não certifica isolamento de dados. | Rede/host/PKI, NC. |
| L11 Continuidade das raízes | Quem pode restaurar A/B/F/W/CA/ACL ou re-enrolar identidade e reabrir capacidade? Qual raiz fica fora de D e de backups regressivos? | Dependências/recuperação, eventos posteriores ao backup, consumos/epochs e invalidação; W13. Decisões H06/H07/H09 próprias. | Continuidade/PKI/tempo, NC. |
| L12 Cobertura/observação | Quem determina que o inventário está completo e quem pode observar escrita/iniciação/corte sem depender só do ledger/controlador? | Origem independente por afirmação, acesso ao payload/meio e arquivo, limites de observação; S08 F02/F06/F07; H04/H08 próprias. | W/V e responsável humano, NC. |
| L13 Perímetro nominal | Qual versão exata de recursos/ramos/meios, poderes, cópias futuras e dependências deve ser submetida à decisão H02? Que lacunas impedem fechá-la? | Fichas nominais, W01–W13 preenchidos, inclusões/exclusões justificadas e condições de invalidação; [PERIMETER.md](PERIMETER.md). | Decisor humano H02, não designado por este dossier. |

## Ordem proposta para as confirmações

1. Preencher L01–L04 com documentação nominal de ativos e cópias.
2. Relacionar L05/L06/L09 com meios de B e poderes de reconstrução/escrita, inclusive recuperação.
3. Completar W01–W13 com L07/L08/L10/L11/L12 e assinalar cada NC remanescente.
4. Rever uma versão nominal do perímetro em L13; uma aprovação H02 deve identificar exatamente essa versão e lacunas aceites/recusadas, sem aprovar por arrasto H03–H12.

Se a documentação não existir, registar «não confirmável com as fontes atuais». Nova recolha precisa de âmbito e autorização próprios; esta matriz não contém comandos nem pedido implícito de executar inspeções, cortes, SQL ou testes.

