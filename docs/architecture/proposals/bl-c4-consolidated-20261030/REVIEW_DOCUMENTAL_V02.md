# LiveNet v2 — revisão documental, técnica e arquitetural C4 v0.2

Revisão 1 · 30/10/2026 · Europe/Lisbon.
Objeto exato: PROPOSAL.md, versão candidata 0.2, SHA-256 `937bb32ab57fb0859d414e3ada9a11dbf963fdb19158d85a0e2c55cf019ff3ab`.

## 1. Conclusão e âmbito da decisão

**PRONTA PARA APROVAÇÃO DOCUMENTAL.**

A proposta v0.2 é coerente com os requisitos e decisões consultados, no seu âmbito expressamente condicionado. Não foi identificada contradição normativa nem autorização documental de contorno das barreiras. A sequência R2 → D09 → barreira C4 → alvo PostgreSQL, os vínculos, C5, D10, os sete cenários e a distinção D09/V05-06 estão conservados.

Esta conclusão significa que o documento pode ser submetido ao utilizador para aprovação documental. Não aprova C4 v0.2, não seleciona ALT-C/M/T/L, não demonstra início único ou independência e não abre gates. A aprovação B-L v1.0 já concluída não é objeto de nova decisão.

Identificam-se quatro observações IMPORTANTES sobre demonstrações ainda em falta, já declaradas pela proposta, e duas observações EDITORIAIS esclarecidas neste relatório. Não há achados CRÍTICOS nem correções obrigatórias à v0.2 para esta finalidade documental. As lacunas importantes impedem afirmar a garantia técnica; não impedem aprovar um documento que as identifica como pendentes. O bloqueador do clone integral gravável mantém-se integralmente.

Não existe decisão arquitetural material indispensável para concluir esta revisão ou submeter o documento. A escolha futura dos mecanismos exige proposta concreta e decisão própria. Nenhuma foi antecipada para obter esta conclusão.

## 2. Mandato, método e preservação

Mandato: anexo humano «LiveNet v2 — Revisão documental C4 v0.2 / Continuação autónoma — sem implementação», recebido nesta conversa, caminho `/home/paulo/.codex/attachments/c955e256-c782-414a-997f-abb25eba4e8c/Pasted text.txt`. Autoriza revisão A–H e relatório separado; proíbe alterar a proposta original nesta fase, normas aprovadas, gates e sistemas operacionais.

A revisão confrontou os textos existentes e os respetivos estatutos, sem reconstruir decisões por suposição. Distinguem-se: requisito aprovado, obrigação de prova, mecanismo candidato e demonstração executada. As tabelas de falhas e cenários da proposta são especificação de comportamento/evidência futura, não relatórios de ensaios. Não foram executados testes, ensaios, SQL, acessos a serviços ou nova auditoria operacional.

Repositório confirmado: `/home/paulo/projects/livenet-v2`, branch `main`, HEAD `647179c928888adfeef0f69f582fd13c5fc17350`. Estado anterior: quatro caminhos tracked modificados e ficheiros untracked preexistentes. São eles `backend/migrations/env.py`, `docs/specifications/f0/data-model.md`, `docs/specifications/f0/implementation-status.md` e `frontend/README.md`. A listagem completa de estado antes/depois está no [registo da revisão](REVIEW_DOCUMENTAL_V02_STATE.json), sem interpretar untracked como trabalho desta revisão.

Antes da escrita capturaram-se hashes dos ficheiros regulares enumerados por `git ls-files --cached --others --exclude-standard`, estado Git com `-uall`, branch/HEAD e digest do diff tracked. A proposta original, REVIEW.md, PRESERVATION.json histórico, B-L e normas permanecem intactos. O índice foi preservado literalmente em [CONTINUITY.pre-review-v02.md](CONTINUITY.pre-review-v02.md), antes de acrescentar apenas a notícia desta revisão.

O registo JSON documenta o estado antes/depois e a comparação final. Só se acrescentam este relatório, esse registo, a cópia anterior do índice e uma secção no índice não normativo. O diff tracked, HEAD/branch e as entradas Git anteriores mantêm-se. A comparação abrange ficheiros regulares Git enumerados; não abrange ignorados, metadados, ACL, recursos externos ou snapshot atómico contra concorrência. Não é confirmação D09 ou demonstração V05-06.

Não foram encontradas instruções AGENTS.md aplicáveis na árvore e nos ascendentes consultados. A falha intermitente `bwrap: loopback: Failed RTM_NEWADDR` foi contornada por execução autorizada fora do sandbox para leituras locais e documentos desta revisão. Não houve contacto com Proxmox, Synology ou bases de dados.

## 3. Fontes e versões efetivamente consultadas

S03 identifica os bytes do índice antes desta revisão; a cópia preservada tem esse mesmo hash. Os restantes hashes identificam os ficheiros consultados, incluindo quando só as secções explicitadas foram lidas. HEAD é contexto do checkout, não commit que contenha os documentos untracked.

| Ref. | Fonte, versão e alcance de leitura | SHA-256 |
| --- | --- | --- |
| S01 | [PROPOSAL.md](PROPOSAL.md) — C4 candidata 0.2, 30/10/2026; integral | `937bb32ab57fb0859d414e3ada9a11dbf963fdb19158d85a0e2c55cf019ff3ab` |
| S02 | [REVIEW.md](REVIEW.md) — Revisão da entrega 0.2, 30/10/2026; integral | `dd54c4b4833fffca67022cf32e72d5edaadd365b6bca51e439fac46b5a355d02` |
| S03 | [CONTINUITY.md](../../../project/CONTINUITY.md) — Índice não normativo anterior à presente revisão; integral | `5177c25dc4e4136702b82ba2fadda233cf2dadd99c1d480150feb140473585ad` |
| S04 | [SPECIFICATION.md](../d09-06-bl-conditional-20261030/SPECIFICATION.md) — B-L v1.0, 30/10/2026; integral, aprovada pelo ato S05 | `e889171ffc1db17afe7e46b40a927f268ffafb70dfe8ceb9ef26aef3207f86a6` |
| S05 | [d09-06-bl-v1-approval-20261030.md](../../decisions/d09-06-bl-v1-approval-20261030.md) — D09-06-BL-V1-ACCEPTANCE-20261030; integral | `36713930a8c503d4dad049bd6f2831f6477393e4c2e4062b7b9fc1bcce5e1146` |
| S06 | [auth-boot-02-r2.md](../../auth-boot-02-r2.md) — R2-CONSOLIDATION-1, 27/10/2026; integral | `241f65858fdfcf8676a4fef4d251f1fdef95dfb2987d971b26cd2c993bfcbfc1` |
| S07 | [auth-boot-02-r2-traceability.md](../../auth-boot-02-r2-traceability.md) — R2-TRACE-CONSOLIDATION-1, 27/10/2026; integral | `6c239c812e0fc125fff10a1d5712a380f653adc021586ecca2d3910ec6d3d1f2` |
| S08 | [auth-boot-02-r1.md](../../auth-boot-02-r1.md) — R1 consolidado; consultadas §§11–12 D09/D10 | `59c312d7dded14db9781d5e2a8e91acbce433b79a6d69427d3884f846e182eff` |
| S09 | [dr07-retention-addendum.md](../../../specifications/f0/dr07-retention-addendum.md) — D2 aceite em P4-B4; consultados V05-01–06, B10 e reservas transversais | `a996d78fff71002db47f2756836669fd3f096bff3074bae10c98c31afdaab818` |
| S10 | [dr09a-p4-b4-acceptance-20261030.md](../../decisions/dr09a-p4-b4-acceptance-20261030.md) — P4-B4, 30/10/2026; integral | `2c92d079f92d11f6c0d7c401316cbe43cf09f133e88586d22b2d73c28881ba49` |
| S11 | [RECOVERED_SOURCES.json](../d09-06-bl-conditional-20261030/RECOVERED_SOURCES.json) — Arquivo de 30/10/2026; entradas D09-05, D09-06 e D09-03 | `aef768ddb611479ddf00f386178c00eb033a8db5d30de41a6ad968d718785d68` |
| S12 | [SOURCES_AND_REVIEW.md](../d09-06-bl-conditional-20261030/SOURCES_AND_REVIEW.md) — Proveniência da entrega B-L, 30/10/2026; integral | `dd1215a4ef54920b9f6907bf837dcd2e9a4eec489ca0e8b1c9472f908fd736a3` |

S04 coincide com o hash aprovado em S05. S09 coincide com D2 aceite em S10: `a996d78fff71002db47f2756836669fd3f096bff3074bae10c98c31afdaab818`. Cabeçalhos históricos de pendência não anulam os atos posteriores de aprovação. A presente revisão não regenera manifestos históricos nem certifica os atos por medir hashes.

### 3.1. Recuperação D09-05, D09-06 e D09-03

Foram reutilizadas as entradas efetivamente disponíveis em S11:

| Objeto | Localizador de proveniência | Conteúdo e estatuto recuperados |
| --- | --- | --- |
| D09-05 | Chat `01a18cf5-a5d2-7711-98b8-5292296ea673`, mensagem `msg_0d1aafcd4bf7cdf0016ae499692f34819196e508884ea8d572` | Desenho conceptual com três fronteiras, poderes transitivos, recuperação e sete cenários. Texto do agente; aprovação conceptual reafirmada pela continuidade e incorporada na B-L aprovada. |
| D09-06 — comparação | Chat `01a18d4c-843c-7652-905b-e9141ee7f1ca`, mensagem `msg_052ca9cf3623bc46016ae4b043e2f48191b91353021a3ea1fc` | Comparação B-L/B-N; B-L distribuída fora do NAS, alojamento pretendido em nós distintos, suficiência e independência por demonstrar. |
| D09-06 — ato em contexto | Mesmo chat, mensagem humana `01a18d52-505c-7ef2-824c-a93667421cc3` | Resposta «sim» à pergunta sobre preferência técnica condicionada B-L, com arquitetura física e implementação ainda por aprovar. A resposta subsequente do agente não é tomada como ato humano autónomo. |
| D09-03 | Chat `01a18cb1-b26d-7512-852f-d6c69f4ff8c2`, mensagem `msg_0992fa4c248ee9c7016ae488ad20b08191a3f07e8067bdb70c` | Matriz dos sete cenários e limites da evidência histórica. Observações operacionais antigas não são revalidadas nem reproduzidas nesta revisão. |

Limitações precisas: S11 não contém uma mensagem humana autónoma de aprovação D09-05; não se inventa tal mensagem. A aprovação conceptual é a documentada/reafirmada nas fontes de continuidade e na especificação B-L posteriormente aprovada. Os anexos originais Windows D09/D09-02 e o ficheiro original da declaração de continuidade histórica não foram usados como textos primários nesta revisão; as suas referências estão em S12. Não se alega identidade byte a byte com anexos antigos, custódia certificada, nova leitura dos chats ou disponibilidade futura destes. S11 contém os textos recuperados necessários para a comparação, com os limites indicados.

D3/NC-01 e pacotes Windows P4-B3 não foram reabertos; o alcance P4-B4 é o registado em S10. Não se faz nova auditoria de retenção nem se altera NC-01. Os contratos históricos assinalados como SOURCE_NOT_LOCATED em S06/S07 não são reconstruídos ou equiparados a R2. Nenhuma destas limitações impede a revisão condicionada A–H com as fontes disponíveis.

## 4. Matriz de conformidade A–H

«Conforme documentalmente» significa especificação coerente com as fontes no âmbito candidato; nunca garantia operacional comprovada.

| Ponto | Fontes e secções da v0.2 | Avaliação e fundamento | Reserva |
| --- | --- | --- | --- |
| A — Sequência | S06 C1/C6, S08 D09; S04 §5; v0.2 §§4–6 | **Conforme documentalmente.** P0 é preparação inerte; P1 confirma R2; P2 compromete uso; P3 confirma preservação pertinente; P4 verifica cumulativamente; J só depois. Ordem causal, sem atomicidade distribuída presumida ou eventos futuros fabricados. | Imposição física P4–J e origem/continuidade da confirmação por demonstrar; I-01/I-03. |
| B — Imposição C4 | S06 C4; S04 §§4/6; v0.2 §§3/5/6/8/10 | **Conforme como requisitos e candidata.** SQL direto/privilegiado, funções alternativas, raw, sessões antigas, replay, rollback/savepoint, crash/restart/restore e clones abrangidos. T deve mediar toda via e sobreviver ao executor comprometido. | Não há mecanismo selecionado ou demonstração de impossibilidade de bypass; I-01/I-02/I-04. |
| C — Iniciação única | S06 C4; v0.2 §§4–7 | **Conforme documentalmente.** Uma aprovação/tentativa, vínculos imutáveis, compromisso L não devolvido, no máximo um J inclusive na mesma sessão. Entrada abortada conta; consumo, início e commit distintos. | Identidade K não pode ser só um ID; prova de singularidade ainda ausente; I-01. |
| D — UNKNOWN/BLOCKED e C5 | S06 C5/C6; S04 §7; v0.2 §§5/7/8 | **Conforme.** Sem confirmação adequada, sem despacho; consulta factual não concede capacidade; sem retry/retoma automática. Só original continuamente vinculada prossegue após pré-condições. Nova tentativa requer reconciliação, invalidação, novo pedido e nova aprovação. | Uma partição posterior não revoga retroativamente nem prova cessação; ausência de informação bloqueia progressão dependente. |
| E — Recuperação D10 | S06 C6; S08 D10; S04 §9; v0.2 §§6–9 | **Conforme documentalmente.** Quarentena, eventos pós-backup, preservação de consumo/ordem/vínculos, invalidação antiga e decisão humana autenticada/auditada. Restore não rearma K, nem D09 vira autoridade. | Corte terminal, continuidade e recuperação suficientes por demonstrar; I-03/I-04. |
| F — Sete cenários | S11 D09-03/05/06; S04 §§4/8; v0.2 §§2/3/9 | **Conforme por remissão e síntese.** Sete cenários conservados; conteúdo/confiança sobreviventes e controlo exigidos; dependências comuns e alcance transitivo reconhecidos. | Mapa concreto e suficiência não demonstrados. A síntese §9 não substitui os detalhes da B-L aprovada; ver §5 deste relatório. |
| G — D09 versus V05-06 | S09 V05/B10; S04 §10; v0.2 §11 | **Conforme.** Obrigações distintas e cumulativas nos respetivos âmbitos, sem substituição recíproca. COMPROVADO não autoriza destruição; 900 segundos não são retenção. | Não se inventa um resultado V05-06 por admissão nem um gate novo de execução; preservam-se os requisitos existentes. |
| H — Limites B-L | S04 §§2/4/8/9; S11 D09-05/06; v0.2 §§1–3/8–11 | **Conforme.** Operador único; autoridade única, sem failover automático; recuperação controlada; exclusão total delimitada; clone gravável bloqueante; sem independência administrativa absoluta presumida. | Novos poderes confiados, redução de ameaça ou seleção de arquitetura continuam decisões materiais próprias. |

Verificação transversal C2/C3/C7: prazo em A, sem grace period novo ou cancelamento retroativo; intervalo UTC renomeado só na notação expositiva; revogação na ordem única; sem schemas/bytes executáveis novos, fallback R1 ou alteração dos 25 nomes/JCS/UTF-8/Ed25519. A classe UPDATE fixo é coerente com S06 §6 e não amplia o âmbito para DDL/Alembic.

## 5. Conferência individual dos sete cenários

A tabela detalha a avaliação F sem inventário operacional. Dependências de hipervisor/consola, storage/cópias, identidade/reset, boot/deploy, rede/alimentação, tempo e recuperação são as de S04 §4/S11, não recursos agora verificados.

| Cenário D09-03 | Dependência/poder a preservar na análise | Evidência e controlo que devem sobreviver | Resultado da revisão |
| --- | --- | --- | --- |
| 1. Falha de VM/serviço | Discos, host, rede e gestão comuns; restart pode recuperar identidade antiga. | Estado/conteúdo/confiança fora da falha, incluindo pós-backup; disponibilização/T bloqueiam sem fundamento; reconstrução em quarentena. | Contemplado; sobrevivência concreta pendente. |
| 2. SO LiveNet comprometido | Segredos, montagens, consola, deploy e vias de escrita alcançáveis pelo SO. | R2/D09 e imposição C4 fora do alcance transitivo; rejeitar confirmação falsa e escrita alternativa. | Contemplado; se o SO remover T, o cenário falha e não passa à exclusão total por conveniência. |
| 3. Perda de nó Proxmox | VMs/discos e dependências comuns; nó antigo pode regressar. | Fundamentos fora do nó; controlo sobrevivente bloqueia; R2 único sem promoção automática; invalidação do antigo. | Contemplado; número de nós não prova capacidade/continuidade. |
| 4. Synology indisponível | NFS e dependências indiretas de boot, confiança, configuração ou recuperação. | B-L conserva conteúdo crítico/confiança suficientes fora do NAS; bloqueia progressões sem requisitos; ressalva C5 preservada. | Contemplado; conteúdo sobrevivente não garante disponibilidade de rede, tempo ou gestão. |
| 5. Storage partilhado corrompido/eliminado | Backends e cópias no mesmo domínio/poder de eliminação. | Conteúdo integral recuperável e continuidade fora do domínio afetado; validadores recusam divergência; quarentena. | Contemplado; digest isolado não recupera bytes. |
| 6. Credencial administrativa limitada comprometida | Elevação, delegação, reset, deploy, consola e recovery ampliam alcance nominal. | Fundamentos pertinentes fora desse alcance e controlos não alcançados impõem bloqueio. | Contemplado; contas/nós distintos não estabelecem independência absoluta. |
| 7. Comprometimento transversal e de toda a recuperação | Poder conjunto sobre todos os fundamentos. | Nenhum fundamento confiável pressuposto; não prometer imposição por componentes comprometidos ou reentrada segura sem confiança. | Exclusão preservada, sem a estender ao cenário 6. |

## 6. Achados classificados e tratamento

A severidade classifica a consequência técnica, não cria um novo gate. As observações IMPORTANTES são lacunas residuais reconhecidas na proposta; não são descobertas apresentadas como mecanismo já aprovado ou como contradições novas.

### I-01 — IMPORTANTE — Singularidade K/L/P4–J ainda sem primitiva demonstrada

Referências: v0.2 §§3–6, em especial P2/P4/P5 e obrigação «Ligação singular P4–J»; S06 C4/C5. Persistir um compromisso por aprovação não impede dois fluxos de atravessar J. IDs copiados, replay, callback duplicado e reentrada na mesma sessão não demonstram a mesma continuação viva. Rollback do efeito não pode devolver a oportunidade.

Tratamento: a proposta já exige estas propriedades e declara a prova pendente. Recomenda-se aprofundar o argumento de vínculo real, irreversibilidade e uma única travessia, incluindo perda de contexto em cada intervalo, antes de alegar C4 demonstrada. Sem correção normativa necessária, mecanismo escolhido ou pedido humano nesta etapa. Não bloqueia aprovação documental condicionada; impede declarar a garantia satisfeita.

### I-02 — IMPORTANTE — Mediação e limite dos poderes privilegiados por demonstrar

Referências: v0.2 §§2/3/6/9/10; S04 §§4/6; S11 D09-06. A obrigação é cobrir SQL direto/privilegiado, escritor alternativo, raw e poderes administrativos incluídos na ameaça. Se algum desses poderes remove T, altera validadores ou alcança R2/D09/recovery, separação lógica não contém o ataque. Acesso administrativo ao alvo não pode ser excluído tacitamente por conveniência.

Tratamento: a proposta reconhece o problema. A solução futura deve explicitar base confiada, alcance transitivo e observação de efeito sem ledger. Recomenda-se documentação de poderes e percursos concretos quando houver candidata, reutilizando evidência existente; não se ordena inventário agora. Não bloqueia aprovação documental; impede afirmar resistência ao executor/poder coberto sem prova.

### I-03 — IMPORTANTE — Conteúdo/confiança D09 e continuidade de recuperação ainda não concretizados

Referências: v0.2 §§3/5/6/8/9; S08 D09/D10; S09 V05-02–06; S04 §§5/9/11. Falta uma realização concreta que sustente completude pertinente, autenticidade, anterioridade causal e recuperação dos consumos/ordem/vínculos/transições pós-backup. R2/L/W/T restaurados juntos podem concordar num passado coerente; assinatura/epoch/nonce não demonstram atualidade.

Tratamento: pendência expressa, sem schema ou retenção selecionados. Recomenda-se identificar futuramente conteúdo suficiente, fundamentos de confiança sobreviventes e regras de divergência, distinguindo confirmação factual de capacidade executável. Não bloqueia aprovação documental; impede alegar D09, V05-06 ou recovery demonstrados. Não se converte V05-06 num substituto de D09.

### I-04 — IMPORTANTE — Corte terminal e clone mantêm bloqueio técnico forte

Referências: v0.2 §§1/6/8/10; S04 §§2/6/9; S11 D09-05/06. Fechar a entrada não termina trabalho aceite. Confirmação terminal depende de término/abort e retirada persistente dos percursos antigos, globalmente se houver vários recursos. Clone integral gravável autónomo fora da mediação conserva capacidade de efeito.

Tratamento: a v0.2 declara expressamente a inviabilidade da garantia forte nesse pressuposto. Recomenda-se manter essa conclusão e procurar prova dentro da ameaça aprovada. Se uma solução só avançar reduzindo domínio/poderes ou acrescentando fundamento de confiança, apresentar alternativas e consequências numa decisão material própria. Não é necessário tomar essa decisão para aprovar o documento condicionado, e não se solicita agora. Não bloqueia aprovação documental; bloqueia a declaração de garantia/reentrada correspondente enquanto a capacidade subsistir.

### E-01 — EDITORIAL — Terminologia e vínculos explicitados na revisão

Referências: v0.2 §§1/4/5 e S06 C4. Neste relatório, «barreira» designa a condição confiada de disponibilização e a imposição obrigatória em T; «alvo» é PostgreSQL, embora K possa ser preparado de forma inerte antes da admissão. As setas exprimem dependências de autorização, não proibição de preparar contexto nem uma transação distribuída. L é compromisso de uso; J é início real, que não volta a consumir a aprovação.

Resolução autónoma neste relatório, sem editar o original: os vínculos C4 referidos são pedido, participantes, finalidade, operação, gate, ambiente, plano, digests, destino/geração, executor/encarnação e sessão/transação protegidas, todos imutáveis. A enumeração contratual permanece em S06; a v0.2 remete para ela e não a reduz ao conjunto citado na definição de K. Nenhuma decisão humana é necessária para esta clarificação.

### E-02 — EDITORIAL — Conformidade documental e atos de aprovação separados

Referências: v0.2 §§1/10/11; S02; S05/S10/S12. O relatório anterior REVIEW.md é revisão da entrega pelo autor, sem matriz A–H. Este novo relatório fornece a revisão solicitada e não substitui aquele registo histórico. «Pronta» não quer dizer «aprovada», e os cabeçalhos históricos da B-L não anulam S05.

Resolução autónoma: fonte, versão, hash, limites de proveniência e objeto da eventual aprovação estão identificados neste relatório. Não se altera a proposta, normas ou registos existentes. Não se pede nova aprovação B-L. Sem correção obrigatória ao original; qualquer melhoria editorial futura deve preservar os bytes 0.2 e originar revisão identificada.

## 7. Correções e decisões humanas

**Correções obrigatórias para submissão documental: nenhuma.** As clarificações E-01/E-02 ficam resolvidas neste relatório, respeitando a proibição de alterar a proposta original. Recomendações I-01–I-04 são trabalho de demonstração/especificação concreta, não licença para implementar ou ensaiar.

**Decisões arquiteturais ou normativas indispensáveis para esta revisão: nenhuma.** A decisão do utilizador, quando pretender, incide apenas na aprovação documental condicionada da proposta C4 v0.2 identificada por hash. Este relatório não regista tal aprovação e não altera o seu estado pendente.

Decisões futuras já isoladas em v0.2 §10:

| Questão futura | Alternativas sem escolha nesta revisão | Consequência a submeter antes de adoção |
| --- | --- | --- |
| Base confiada e L | L no domínio R2; na mediação; ou primitiva não reversível no alvo com continuidade externa. Funções integradas ou separadas. | Cada opção altera poderes, continuidade e recuperação de forma própria; nenhuma demonstra automaticamente P4–J ou clone. |
| Corte das capacidades antigas | Mecanismo terminal/persistente ainda não escolhido; complemento físico continua apenas candidato. | Cobertura de todos os meios e trabalho pendente, impacto e reabertura precisam de fundamentação; não se adota atuador por inferência. |
| Limite do clone | Manter a garantia forte e provar contenção/prevenção dentro dos poderes aprovados; qualquer proposta de reduzir ameaça/efeito ou confiar noutro fundamento é distinta. | A primeira mantém o bloqueio enquanto não demonstrada; as restantes mudariam a garantia/base confiada e exigiriam decisão humana expressa. |

Não há motivo para interromper a revisão com perguntas editoriais ou de implementação. A ausência dessas decisões futuras não impede avaliar a coerência dos requisitos e pendências agora apresentados.

## 8. Estado de saída e próximo passo concreto

Submeter C4 v0.2, SHA-256 `937bb32ab57fb0859d414e3ada9a11dbf963fdb19158d85a0e2c55cf019ff3ab`, acompanhada deste relatório, para aprovação documental condicionada. Conclusão inequívoca: **PRONTA PARA APROVAÇÃO DOCUMENTAL**. A decisão de aprovação pertence ao utilizador e permanece pendente.

A análise documental reversível pode continuar no âmbito já autorizado, concentrada nas condições de prova I-01–I-04, sem adoção de arquitetura. Implementação, ensaios, infraestrutura e seleção material não são autorizados por este relatório ou pela eventual aprovação documental.

Gates/estados preservados: P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados/bloqueantes; H02–H12 pendentes/bloqueantes e GAP-001/002 abertas/bloqueantes conforme os registos; RG1–RG7, R2 D09 e V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial. Sem independência administrativa absoluta prometida, HA/failover automático ou autorização de destruição.

Nenhum código, norma aprovada, base, serviço, container, VM, rede, storage ou credencial foi alterado. Sem testes, ensaios, deployment, commits, pushes ou merges. Proposta C4 v0.2 e respetiva revisão de entrega preservadas integralmente.
