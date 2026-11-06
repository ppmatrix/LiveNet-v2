# H02 — preparação documental de inventário e ameaça física

Data editorial: 2026-10-27, Europe/Lisbon; sem atestado UTC.
Repositório: `progbox:/home/paulo/projects/livenet-v2`.
HEAD de referência: `647179c928888adfeef0f69f582fd13c5fc17350`.
Estado: **H02 PENDENTE — NÃO APROVADA; inventário aberto**.

## Autoridade e alcance

O pedido humano desta sessão aprova H01 com O1 apenas para estudar uma fronteira externa que retire poderes de cópia/escrita autónoma do recurso protegido. O3 pode complementar, mas não foi aprovado. Essa escolha orienta a preparação; não demonstra que os poderes já foram retirados. H02–H12 continuam PENDENTES.

O estado histórico de DEV-08, que declarava H01–H12 pendentes, é preservado. O pedido atual é a fonte da atualização de H01 neste dossier; não se atribui uma assinatura executável, data do ato original ou alteração ao registo contratual. O seguimento «continua» autoriza concluir esta preparação, sem decidir as restantes linhas.

A leitura incidiu exclusivamente sobre ficheiros/evidências existentes no repositório e estado Git. Não foram consultados hipervisores, VMs, storage ou serviços; não houve comandos administrativos, testes, SQL, scans ou provisionamento.

## Resultado revisável

| Documento | Conteúdo |
| --- | --- |
| [INVENTORY.md](INVENTORY.md) | Recursos conhecidos, classes documentadas, privilégios e meios por identificar; fonte, confiança e aplicabilidade atual. |
| [WRITE_PATHS.md](WRITE_PATHS.md) | W01–W13 de DEV-08, evidência e lacunas de cobertura. |
| [GAPS.md](GAPS.md) | Perguntas e evidências requeridas à validação humana, sem recolha operacional autorizada. |
| [PERIMETER.md](PERIMETER.md) | Proposta de perímetro H02 compatível com o estudo O1 e critérios de completude. |
| [PROVENANCE.md](PROVENANCE.md) | Fontes, alcance das leituras e método/limites da preservação. |
| [preservation.baseline.json](preservation.baseline.json) | Baseline de conteúdo/modo/tamanho, estado Git, HEAD e hashes das fontes. |
| [preservation.json](preservation.json) | Comparação posterior e verificações documentais. |

Há evidência documental de um clone físico de dados PostgreSQL que escreveu após cessação local no original. Há uma determinação arquitetural de A único em VM Proxmox dedicada e ambientes DEV/STAGING/PROD previstos. Não há, nas fontes consultadas, inventário nominal fechado de VMs, volumes, backups, exportações ou administradores efetivos. O modelo físico de Inventory é uma especificação de dados, não uma lista de ativos instalados.

A inferência central continua condicional: O1 exige retirar a D todos os meios que permitam reconstruir e escrever uma cópia autónoma de B. Leitura integral, exportações, memória, backups e poderes administrativos transitivos precisam de classificação; mover o endpoint para outra VM não demonstra essa restrição. Não se declara independência administrativa por separação de VMs.

## Estado preservado e próximas confirmações

AUTH-03/F02/G2/G4 fechados; GAP-001/002 abertas; DEV-09B não autorizada. R1/R2, C1–C7, modelo de ameaça e contratos existentes permanecem inalterados. Sem commits/push ou alteração operacional.

A validação humana precisa primeiro de identificar recursos e custódios nominais, todas as cópias e destinos de restore/exportação, capacidades de leitura/escrita de D e poderes transitivos. Depois poderá rever uma versão concreta do perímetro e decidir H02 separadamente. H03–H12 conservam as suas decisões próprias. Esta entrega não autoriza consultas ao ambiente, plano de ensaio, laboratório ou integração.

