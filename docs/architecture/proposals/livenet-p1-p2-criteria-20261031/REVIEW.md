# P1 Inventory / P2 Retenção — revisão conjunta

31/10/2026 · Europe/Lisbon · Documentos candidatos 0.1 para revisão humana.

## Entrega e conclusão

[P1_INVENTORY.md](P1_INVENTORY.md): 18 critérios verificáveis, com origem em contrato DAT aprovado, comportamento UI documentado ou consequência derivada; seis dúvidas explícitas. Pesquisa textual e ordenação personalizada estão expressamente ausentes na UI documentada: não foram transformadas em requisito implementável ou parâmetro novo. Sem fonte para ordem padrão, composição de filtros ou tratamento de página inválida, preserva-se a lacuna.

[P2_RETENTION.md](P2_RETENTION.md): matriz de prazos Discovery e 18 condições cumulativas de proteção/saída, com distinção entre aprovado e TBD. Mantém holds, conflitos, identidade/histórico, objetos mistos, arquivo, cópias e R2; não altera prazos, D09/V05-06 ou eliminação. P4-B4 resolve a aprovação dos bytes D2, sem apagar cabeçalhos históricos.

**Conclusão: entregas documentais preparadas para revisão, com dúvidas delimitadas; nenhuma validação executável realizada ou alegada.** Não há decisão material indispensável para concluir estes critérios condicionados. Aceitação humana dos novos documentos permanece pendente; as fontes aprovadas não são reabertas.

## Rastreabilidade e alcance das consultas

| Fonte | Secções usadas / limite |
| --- | --- |
| [Matriz de dependências](../livenet-dependencies-20261031/DEPENDENCIES.md) | P1/P2/P3, escopo documental e ausência de autorização de implementação. |
| [frontend README](../../../../frontend/README.md) | Integral: endpoints/Resource/parâmetros/paginação/sessão/RBAC e limitações. É documentação de implementação; não ato de aprovação normativa. |
| [DAT](../../../specifications/f0/data-model.md) | DAT-01A/B, DAT-02A/B/C, DAT-03A/B, DAT-07A/08A: identidade, estados, reconciliação e observações/Outbox; contratos já aprovados. |
| [Implementation-status](../../../specifications/f0/implementation-status.md) e [DEV-07](../../../operations/dev07-react-integration.md) | Contexto histórico UI/readiness/persistência reutilizado; limites/resultados DEV-07 consultados, não repetidos nem generalizados para dados reais atuais. |
| [D2](../../../specifications/f0/dr07-retention-addendum.md) | Classes, V03/V04/V05 e B1–B10/reservas pertinentes: regras de proteção/saída; leitura por secções, sem nova auditoria normativa. |
| [D1](../dr07-retention-decisions.md) | Proveniência/precedência V03–V05 e reservas/índice; não se reconstrói ato histórico ausente. |
| [P4-B4](../../decisions/dr09a-p4-b4-acceptance-20261030.md) | Integral; aceitação D1/D2/D3 em 30/10/2026, com hashes D1/D2 conferidos. D3/NC-01 Windows não reabertos. |

Nenhum código, API real, base, serviço, browser ou dado operacional foi consultado. Não se fez auditoria de implementação. A ausência de requisito nas fontes consultadas é registada como lacuna documental, não prova de que uma função não exista noutro contrato. Os hashes das versões consultadas constam de PRESERVATION.json.

## Dúvidas materiais e critérios de aceitação

| Tema | Reserva / ponto de decisão futura | Critério de aceitação desta entrega |
| --- | --- | --- |
| Pesquisa/ordenação e filtros/paginação residuais | Funcionalidade futura precisa de escopo/contrato, sem decidir endpoints/campos/políticas aqui. Não é necessária decisão intermédia para registar ausência. | P1 separa comportamento documentado, derivação e não definido; não promete pesquisa, ordem padrão ou normalização sem fonte. |
| Permissões e estado operacional | Novos âmbitos RBAC, uso de informação operacional ou mudança de exposição seriam decisões próprias; não inferidos de active/disabled. | Preservar 401/403/404 indistinto, papéis leitores atuais e administrativo separado de operacional; sem telemetria/role nova. |
| Holds/tempo/Discovery | Métodos/autoridades, revisão/responsáveis e referências temporais TBD não preenchidos. | P2 não escolhe início dos 180 dias de reconciliação, revisão automática, prazo de hold ou mecanismo de levantamento. |
| Arquivo/custódia/libertação | Detalhes/períodos e condições R2 pendentes exigem decisões próprias quando materiais. B5 A e B6/B7/B9/B10 C não são reabertos. | Preservação, separação, levantamento, libertação, recuperação/reativação e eliminação separados; nenhum se torna autorização do seguinte. |
| D09/V05-06 e execução | Demonstrações continuam independentes nos seus âmbitos e cumulativas; sem resultado operacional novo. | COMPROVADO não é permissão de apagar nem confirmação D09; nada fecha lacunas ou gates. |

Revisão do autor conferiu referências, prazos/unidades, semântica de saída e ausência de novos campos/endpoints/regras de fusão. Critérios que dependem de observar UI/API/dados só podem ser verificados operacionalmente em etapa autorizada. Não se apresentam como PASS por constarem desta grelha.

## P3 Discovery

**Há base suficiente para começar P3 exclusivamente como preparação documental de exemplos condicionados**, usando DAT/D2 aprovados e a grelha P2 candidata como índice auxiliar. Pode descrever contradição de identificadores, candidato repetido/rejeitado e recurso arquivado, conservando UUID/proveniência/histórico/proteções e referências TBD.

Não selecionar limiares, prioridade universal entre fontes, regras concretas de fusão, reativação automática, schema, TTL/limpeza ou política de execução. P2 não precisa de eliminar os seus TBD para isso, mas não se trata o novo documento como já aprovado. **P3 não foi executado nesta tarefa.** Conclusão de prontidão não autoriza adaptador, persistência ou teste operacional.

## Git, preservação e limites

Checkout confirmado: `/home/paulo/projects/livenet-v2`, branch `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`. Quatro tracked modificados e untracked anteriores preservados; frontend README e data-model consultados não foram editados. Baseline em `/tmp/livenet-p1-p2-before.json`: hashes dos ficheiros regulares Git enumerados, estado `--porcelain=v1 -uall`, HEAD/branch e digest do diff tracked.

[PRESERVATION.json](PRESERVATION.json) regista comparação/estados/hashes antes/depois e validação UTF-8/referências locais. Só se acrescentam esta pasta e a notícia necessária no índice não normativo, cujo original fica em [CONTINUITY.before.md](CONTINUITY.before.md); links dessa cópia conservam a base original docs/project/CONTINUITY.md. Sem alteração de contratos/normas/decisões aprovados. Comparação exclui ignorados, metadados/ACL, estado interno Git, recursos externos e snapshot atómico contra concorrência; não é D09, V05-06 ou prova de recuperação.

Nenhuma AGENTS.md aplicável foi encontrada nos locais consultados. A falha inicial bwrap foi contornada por execução autorizada fora do sandbox para leitura/escrita documental. Sem código, ensaios/testes operacionais, SQL/migrations, infraestrutura/serviços, gates, commits, pushes ou merges. C4/B-L e estudos aprovados não reabertos; I-04/clone e demais gates mantidos. LiveNet interno; progbox DEV; STAGING/PROD em VMs Proxmox.
