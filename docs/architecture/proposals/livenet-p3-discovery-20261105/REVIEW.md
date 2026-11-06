# P3 Discovery — verificação documental da candidata 0.1

05/11/2026 · Europe/Lisbon · Revisão do autor, para revisão humana; **não constitui aprovação ou validação operacional**.

## Consulta e precedência

Consultados o [índice de continuidade](../../../project/CONTINUITY.md), a [entrada P3 da matriz](../livenet-dependencies-20261031/DEPENDENCIES.md), a [aceitação P1/P2](../../decisions/p1-p2-acceptance-20261105.md), P1/P2 e revisão conjunta, além das secções DAT/D2 indicadas na [proposta](PROPOSAL.md). D2 foi lido no âmbito de proteção, arquivo, Discovery e reservas; P4-B4 já consultado nesta sessão fundamenta a aceitação dos bytes D2. Não se repetiram auditorias, inventários ou revisão global das decisões. Nenhuma AGENTS.md aplicável foi encontrada no checkout ou nos diretórios ascendentes consultados.

SHA-256 conferidos dos ficheiros consultados:

| Objeto | SHA-256 | Comparação |
| --- | --- | --- |
| P1_INVENTORY.md | `e555833332087903817dab814e9a95d66c6d651370cf223bd9de9a917070eb58` | Coincide com o registo de aceitação P1/P2. |
| P2_RETENTION.md | `f13c9c7a35ea42575fb3530d5e853695d97f26620765d443b5d6ad2643900b40` | Coincide com o registo de aceitação P1/P2. |
| REVIEW.md de P1/P2 | `7e649304a1997dc286a8c789dad5c7ef584031987d591cecb19ae7d6dd7178ab` | Coincide com o registo de aceitação P1/P2. |
| D2 | `a996d78fff71002db47f2756836669fd3f096bff3074bae10c98c31afdaab818` | Coincide com o aceite em P4-B4. |

A comparação identifica bytes locais; não amplia a revisão declarada no ato de aceitação P1/P2. Referências derivadas aceites não substituem DAT/D2; cabeçalhos históricos de candidatura mantêm-se intactos.

## Coerência e ausência de escolhas novas

| Caso | Obrigações conferidas | Reserva preservada |
| --- | --- | --- |
| P3-01 | DAT-02A/B/C: contradição forte impede fusão automática; ambiguidade exige revisão; B8-09 preserva evidência. | Sem escolher recurso, candidato novo ou fonte vencedora. |
| P3-02 | DAT-02C/03B: idempotência sem recursos duplicados, sem aprovação por repetição; B8-02 preserva pendente. | Deduplicação técnica de observações/candidatos e concorrência não determinadas. |
| P3-03 A/B | DAT-07A/B8-08: distinguir repetição de nova evidência relevante ou decisão autorizada; rejeição e proveniência preservadas. | Material diferente não comprova relevância; relevância não é aprovação nem política de reabertura/recriação. |
| P3-04 | DAT-03A/B e D2 V04-06/B7: UUID preservado, sem reativação por descoberta, autorizações de recuperação/reativação distintas. | Sem associação definitiva por IP/nome, recurso duplicado ou procedimento técnico escolhido. |

Os quatro casos distinguem observação/candidato/consolidado, descrevem premissas/evidências, referências, identidade/histórico, proteções e resultados em aberto. A §2 da proposta reúne regras cumulativas de retenção, aplicadas explicitamente em cada caso. Não fixa início dos 180 dias, responsáveis/periodicidade de revisão, duração de holds ou arquivo; não introduz campos, estados físicos, limiares, fusão, TTL ou limpeza. Nenhum caso é PASS operacional ou demonstração D09/V05-06. L1–L6 são lacunas localizadas, não decisões novas ou alterações de gates.

## Preservação e verificações locais

Checkout `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`, com quatro tracked modificados e untracked anteriores. Baseline limitada registada em `/tmp/livenet-p3-20261105-before.json`: HEAD/branch, estado Git completo, digest do diff tracked e hashes das fontes consultadas/ficheiros tracked já modificados. Não se guardou inventário global de hashes nem snapshot de serviços/dados. A baseline em /tmp é auxiliar temporária, não artefacto de custódia.

Verificação final: UTF-8 e destinos das referências locais dos dois novos Markdown e do índice; comparação dos hashes selecionados, HEAD/branch/diff tracked e entradas Git preexistentes, permitindo apenas a nova pasta e a atualização do índice. Esta verificação não prova conteúdo de todos os untracked, ignorados, metadados ou recursos externos e não é prova de continuidade/recuperação.

O sandbox falhou na configuração de loopback (`bwrap`); as chamadas shell necessárias prosseguiram por execução autorizada fora do sandbox, limitadas a leitura e auxiliares em /tmp. As alterações do projeto são exclusivamente os dois documentos desta pasta e o índice. Não houve código, testes operacionais, SQL, migrações, builds, serviços, infraestrutura, deployments ou operações de escrita Git.

**Recomendação:** submeter a candidata 0.1 ao ChatGPT para revisão humana documental dos quatro casos e L1–L6. Não é necessário resolver critérios técnicos residuais para aceitar os exemplos condicionados. Qualquer futura implementação exige âmbito/decisão próprios. P3 permanece candidata; fontes aprovadas, gates/bloqueadores, LiveNet interno, progbox DEV e deployments em VMs Proxmox preservados.
