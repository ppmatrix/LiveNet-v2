# H02 — inventário documental aberto

Estado: preparação documental; H02 PENDENTE. IDs I e P são localizadores editoriais deste dossier, não novos recursos ou decisões contratuais.

## Como ler a confiança

FD = facto documentado: a fonte declara o dado, incluindo requisitos/propostas e observações históricas devidamente qualificadas.
IN = inferência explicitamente condicional.
NC = dado não confirmado/não localizado nas fontes consultadas.
Confiança alta significa fidelidade ao conteúdo identificado, não validação operacional. Para qualquer recurso atual, a existência, localização, geração, capacidades e custódia continuam NC salvo a leitura do checkout. Não se atribuem probabilidades numéricas.

As fontes S01–S20 e os seus hashes estão em [PROVENANCE.md](PROVENANCE.md) e na baseline.

## Recursos, cópias e persistência

| ID | Recurso ou classe / dado conhecido | Estatuto, fonte e confiança | Relação potencial com B e lacuna atual |
| --- | --- | --- | --- |
| I01 | Checkout `/home/paulo/projects/livenet-v2` acessível por SSH no destino progbox. | FD atual limitado a ficheiros/estado Git; alta. S01/S05 também documentam esse acesso histórico. | Ferramenta de preparação; não se conhece se progbox é VM ou host Proxmox, nem se contém B atual. Não inferir privilégios de hipervisor a partir de SSH. |
| I02 | DEV progbox, STAGING VM Proxmox, PROD-VM Compose e PROD-K8S previsto; política LAN-only. | FD de política/topologia prevista; alta, S16/S17/S19. | Nenhum deployment atual é validado por essa previsão. Hosts, VMIDs, gerações, redes e administradores NC. |
| I03 | Autoridade A inicialmente única em VM Proxmox dedicada, separada da aplicação e VMs PostgreSQL, sem HA/failover automático. | FD de determinação arquitetural; alta, S13 §12. | A não é automaticamente payload B, mas a sua restauração pode reativar poderes. VMID, host, discos e recuperação NC. |
| I04 | VMs de aplicação e PostgreSQL mencionadas na separação de R1-D10. | FD de arquitetura; alta, S13 §12. Existência atual NC. | PostgreSQL e persistência do payload são candidatos ao âmbito B; quantidade e localização não documentadas nas fontes lidas. |
| I05 | G4 exige VM Proxmox exclusiva e ensaios sem NIC; criação planeada, não autorizada. | FD de registo, alta, S18 linha G4D-01. | Fronteira distinta de STAGING/PROD; não reservar, reutilizar ou incluir como recurso disponível. |
| I06 | DEV-04/05 descrevem clusters PostgreSQL 16 descartáveis, dados copiados com alvo parado e ramos iniciados depois. DEV-05 declara limpeza. | FD histórico; alta, S03/S08/S11/S12. | Original/clone são demonstrações do problema B. Não são destinos atuais. Snapshot de VM/memória não foi demonstrado. |
| I07 | Clone DEV-05: original epoch 2/value 0; clone epoch 1/value 1 após cessação SQL local. | FD histórico; alta, S12 `measurements.clone_survives_local_cessation_counterexample`. | Mostra meio gravável autónomo no domínio histórico; não prova existência de clone atual. `distributed_fencing=false`. |
| I08 | Snapshot físico histórico DEV-05: um efeito em cada ramo com a mesma aprovação; roles, WAL e estado local são copiáveis no ensaio. | FD histórico; alta, S11 e S12 `measurements.historical_snapshot_counterexample`. | Mecanismo histórico de restauração de estado antigo, sem inventário atual de snapshots nem capacidade de VM demonstrada. |
| I09 | Volumes, pools, dispositivos, data/WAL/tablespaces, cache, storage partilhado/local, fabric e multipath. | NC quanto a recursos concretos; S03 W11/S05 enumeram classes por verificar. | Potencialmente B ou meio de o reconstruir; não afirmar existência de SAN, reservas persistentes ou atuador. Identificadores/montagens/iniciadores NC. |
| I10 | Backups, dumps, imagens, réplicas offline, media amovível, arquivos WAL e PITR. | FD como classes de ameaça/requisitos, S03 W06/W10 e S13 §12; catálogo atual NC. | Cada cópia restaurável/exportação suficiente para recriar payload pode criar B autónomo (IN, condicionada à capacidade). Destinos, retenção, leitores e restauradores NC. |
| I11 | Snapshots/clones de VM, disco, memória, migração/exportação, credenciais e vTPM. | FD como catálogo W09, S03; suporte e uso atuais NC. | Avaliar meios de reconstrução e cópias posteriores; não atribuir snapshots de memória, vTPM, migração ou exportação à infraestrutura sem evidência nominal. |
| I12 | D pode abranger aplicação/executor, memória, sessões, discos, WAL, roles, configuração, certificados/chaves exportáveis, ledger local e vTPM quando incluído. | FD da definição analítica DEV-08, S03; não inventário instalado. | IN: se D puder copiar/administrar A/B/F/W ou recuperar as suas raízes, a fronteira externa não fica demonstrada. Conteúdo efetivo de D NC. |
| I13 | B serviço de dados/payload/contexto e início; F imposição/corte; W/D09 arquivo; V observação; P/K/T confiança/continuidade/tempo. | FD de responsabilidades candidatas, S04/S05/S10. Não equivalem a VMs existentes. | B e seus meios de reconstrução candidatos; F/A/W/P/K/T são dependências de integridade/continuidade. Pessoas, máquinas, chaves e meios NC. |
| I14 | Runtime descreve Compose com volumes separados e redes lógicas; workers/scheduler/Redis/Outbox/SSE previstos ou ausentes conforme baseline. | FD documental, S17 tabelas de estado/runtime; atualidade operacional NC. | Volumes descritos não provam isolamento físico; jobs/efeitos laterais continuam W07 por esclarecer. Não assumir serviços ativos. |
| I15 | Modelo Inventory suporta tipos physical_host, virtual_machine, storage_device, service/cluster, identificadores VMID/UUID, relações e proveniência/confiança. | FD de especificação, S20 §§1–4; alta. | Não contém catálogo nominal de B; UUID/VMID não é prova de encarnação única. Esquema não preenche inventário nem autoriza SQL. |

Não foram localizados nas fontes consultadas valores nominais de VMIDs/hosts/storage, catálogo fechado de volumes/snapshots/backups, capacidades livres ou inventário de meios amovíveis. A ausência de documentação não permite declarar esses recursos inexistentes.

## Privilégios e domínios administrativos

| ID | Poder ou domínio conhecido na documentação | Estatuto / fonte / confiança | Confirmação necessária |
| --- | --- | --- | --- |
| P01 | Acesso SSH ao checkout como paulo, documentado historicamente e utilizado nesta preparação. | FD de acesso a ficheiros; alta, S01/S06. | Não demonstra root/sudo, consola, storage ou hipervisor. Identidades efetivas e alcance além do checkout NC. |
| P02 | DEV-05: todos os clusters sob mesmo host, utilizador OS e administrador; SO_PEERCRED/pin de socket; controlador SQL confiado. | FD histórico; alta, S11. | Nenhuma segregação administrativa demonstrada; não transportar esta configuração como facto do ambiente atual. |
| P03 | Papel SQL antigo, novo papel e função SECURITY DEFINER/fence local no ensaio; superuser contorna a função; chamada direta contorna consumo externo. | FD histórico; alta, S11/S12. | Owners, superusers, heranças/SET ROLE, DDL/extensões e credenciais locais atuais NC; W02–W04. |
| P04 | D executor; A admissão; B recurso/SQL; F storage/fabric; W/D09; V revisão; P confiança; T tempo; K backup; H humano; G host/hipervisor/rede. | FD de matriz funcional proposta; alta, S04. | Titulares, substitutos, contas de serviço, delegação, emergência, reset de credenciais e poderes transitivos NC. Nenhuma pessoa nomeada por inferência. |
| P05 | Hipervisor/root/storage/backup/CA/IdP e recuperação podem conferir poder transitivo sobre domínios ditos separados. | IN condicionada aos poderes reais, fundada em S04 e S08 F02/F05. | Identificar quem lê discos/chaves/memória, troca executáveis/trust stores, restaura, reanexa, promove ou reinscreve. VMs separadas não provam independência. |
| P06 | Controlo por duas pessoas recomendado; recuperação independente e segregação são requisitos. | FD de requisito, S13 §§11–12. | Duas contas da mesma pessoa não comprovam dupla supervisão; conivência/admin global exigem decisão H03. |
| P07 | HSM/TPM físico, BMC/PDU, SAN/fencing, UTC autenticado e W/D09 independente não foram localizados/demonstrados nas fontes pertinentes. | FD de limite do estudo anterior, S05; estado atual NC. | Não adquirir/selecionar/atribuir essas capacidades. Pedir evidência existente e autorização própria se for necessária nova recolha. |

## Ficha nominal a completar por validação humana

Para cada recurso/meio: identificador e namespace; host/localização física; ambiente e geração; estado atual e data da evidência; discos/volumes/WAL/tablespaces/memória; snapshots/backups/exportações e destinos; leitores/escritores; privilégios diretos/herdados/transitivos; custódio e recuperação; mecanismos de clone/restore/exportação/criação posterior; W associados; inclusão proposta em B ou dependência; observador/barreira documentados; fonte, confiança e incertezas.

Todos os campos ainda sem evidência permanecem NC. Nenhuma ficha é considerada recurso aprovado, ausência verificada, exclusão de ameaça ou capacidade instalada.

