# AUTH-BOOT-02-R2 — Rastreabilidade e acompanhamento das lacunas

**Estado: CONSOLIDAÇÃO DOCUMENTAL da baseline candidata C1–C7 aprovada documentalmente; sem evidência operacional nova.**

Revisão: R2-TRACE-CONSOLIDATION-1. Data de consolidação: 2026-10-27.
Fonte contratual candidata: [AUTH-BOOT-02-R2](auth-boot-02-r2.md).
Registo histórico preservado: [lacunas R1](auth-boot-02-r1-gaps.md).

## 1. Fontes verificadas e limites

| Referência | Fonte | Alcance demonstrado |
| --- | --- | --- |
| H-R2-TEXT | Conversa `6adfbb17-6350-83ed-9daa-650bf8ad109a`, mensagem humana `408b84ef-5a83-4255-9bca-3bb79ae7ae58` | Texto integral R1-CONTRACT-REV-01: C1–C7, matriz de alterações, critérios mínimos, riscos e limites |
| H-R2-APPROVAL | Mesma conversa, mensagem humana `9daf5fec-5456-4d05-b296-483b9a1b3260` | Aprovação documental como baseline candidata AUTH-BOOT-02-R2, incluindo riscos e separação de versão; proibição expressa de implementação, alteração operacional, abertura de gates e fecho de GAP-001/002 |
| H-R2-CONSOLIDATION | Pedido atual de consolidação no repositório LiveNet v2 | Autoriza apenas documentação, com verificação prévia do repositório; preserva R1/histórico, lacunas abertas, gates fechados e DEV-09B não autorizada; sem commits ou push |
| R1 | [Consolidado R1](auth-boot-02-r1.md), §§6–8 e §§10–12 | Fronteira temporal anterior, exclusividade, reconciliação, confirmação independente e continuidade; texto preservado |
| R1-GAPS | [Registo R1](auth-boot-02-r1-gaps.md), GAP-001 a GAP-020 | Critérios e estados históricos mantidos; GAP-001/002 ABERTAS e bloqueantes |
| R1-TRACE | [Rastreabilidade R1](auth-boot-02-r1-traceability.md) | Proveniência e relações históricas; sem reclassificação dos resultados anteriores |

O texto C1–C7 foi recuperado da mensagem humana integral. As mensagens do assistente na conversa referenciada foram devolvidas apenas como referências de conteúdo; não foram usadas para preencher lacunas. Não se atribuem datas individuais de aprovação, assinaturas, schemas ou conteúdo ausente. A data acima identifica a consolidação atual.

O repositório foi verificado em `progbox:/home/paulo/projects/livenet-v2`. A pasta local inicialmente disponível estava vazia e não era um checkout Git. O estado remoto incluía alterações pré-existentes; esta consolidação limita-se aos dois documentos R2 e a uma adenda no registo de decisões.

## 2. Cláusulas, diferenças e demonstração pendente

| Cláusula | Relação com R1 e contratos | Conteúdo documental aprovado | Demonstração ou aprovação ainda necessária |
| --- | --- | --- | --- |
| C1 | R1-D04/D08/D09 | Decisão final em `A`, serializada com revogação/epochs/política; admissão condicionada a confirmação durável conjunta; estado independente | Transições, persistência, isolamento e prova de uma admissão durável; sem atomicidade presumida com o alvo |
| C2 | R1-D05/D08 | Fórmulas e máximo de 900 segundos mantidos; prazo aplicado à avaliação em `A`, com confirmação/efeito potencialmente posteriores | Fonte UTC/incerteza, continuidade temporal e avaliação atribuível a `A` |
| C3 | R1-D05/D08 | Ordem autoritativa única; revogação anterior recusa; posterior não retira admissão; pendência não é eficácia | Prova persistente da ordem e de bloqueio quando ordem/confirmação são desconhecidas |
| C4 | R1-D04/D08/D10 | Uma tentativa por aprovação, vínculos imutáveis, sem transferência/libertação; segunda iniciação e caminhos SQL de contorno impedidos | Exclusividade aplicada no alvo, incluindo replay, savepoint, rollback, concorrência e recuperação; admissão única não basta |
| C5 | R1-D06/D08 | Confirmação ausente implica UNKNOWN/BLOCKED; consulta não autoriza retoma; continuidade da tentativa original; ausência de retry automático | Reconciliação independente, invalidação de capacidades antigas e tratamento de respostas perdidas/partições |
| C6 | R1-D09/D10 | Confirmação independente antes do percurso executável; recuperação preserva admissões/consumos/revogações/ordem/epochs/vínculos | Independência, continuidade, quarentena e invalidação de instâncias anteriores demonstradas |
| C7 | R1-D02, F02/G4 e integrações | Separação explícita; perfil R2 recomendado com protocol_version="2", domínio próprio, 25 nomes de campos, JCS/UTF-8 e Ed25519 puro | Aprovação específica da codificação e dos schemas de evidência; domínio concreto não definido; sem fallback entre versões; parsers/executores inalterados |

## 3. Acompanhamento R2 sem alteração do registo R1

As linhas abaixo referenciam os IDs R1 existentes. Não criam novos IDs, não substituem critérios históricos e não encerram entradas. Os critérios R2 provêm da matriz e dos critérios mínimos de H-R2-TEXT.

| Lacuna existente | Estado mantido | Critério histórico preservado | Acompanhamento da baseline R2 |
| --- | --- | --- | --- |
| R1-GAP-001 | ABERTA — BLOQUEADOR DE ATIVAÇÃO | No máximo uma iniciação, com protocolo e oráculo independente, incluindo reinício e snapshot | Demonstrar exclusividade no alvo contra replay, savepoint, rollback, concorrência e caminho direto; continuidade/invalidação; admissão única durável não encerra a lacuna |
| R1-GAP-002 | ABERTA — BLOQUEADOR DE ATIVAÇÃO | Ordenação de revogação/expiração com primeiro efeito PostgreSQL; pré-consulta SQL insuficiente | Revisão expressa para avaliação temporal em A e ordem autoritativa com admissão; confirmação durável, revogação anterior impeditiva e incerteza bloqueante ainda por demonstrar; requisito histórico não declarado satisfeito |
| R1-GAP-003/007 | ABERTAS | Continuidade, proteção contra rollback, resultado incerto e invalidação antes de nova tentativa | Preservar ordem/admissões e impedir reativação por restauro/clone; reconciliação e reentrada humana |
| R1-GAP-004/012 | ABERTAS | Independência, auditoria e reconstrução | Confirmação D09 antes do percurso executável; distinguir admissão, início observado e resultado |
| R1-GAP-005/006 | ABERTAS | Integração e fronteira efetiva do executor | Preservar transação protegida única, mesma ligação, rollback e reconciliação; referências atuais não autorizam execução |
| R1-GAP-008/009 | ABERTAS | Schemas, codificações, limites e interoperabilidade | Separar R2 de R1; aprovar codificação e schemas de evidência sem inventar campos ou bytes de assinatura |
| R1-GAP-010 | ABERTA | Persistência, isolamento e interfaces de estado | Admissão/consumo/vínculos/ordem/evidência essencial locais confirmados duravelmente |
| R1-GAP-011/014–017 | ABERTAS | Confiança, tempo, rede, retenção e responsabilidades | Manter requisitos pertinentes de confiança, UTC/incerteza e continuidade; escolhas concretas pendentes |
| R1-GAP-013 | ABERTA | Proveniência e revisão documental dos bytes | Fontes atuais identificadas; não presume encerramento da proveniência histórica nem aprovação final dos bytes consolidados |
| R1-GAP-018 | ABERTA | SOURCE_NOT_LOCATED para contratos históricos ausentes | Sem reconstrução ou equivalência histórica presumida; relações novas exigem aprovação própria |
| R1-GAP-019/020 | ABERTAS | Melhorias futuras HA/failover e SIEM/diagnóstico | Nenhuma ativação, ampliação ou autorização implícita |

Os vinte estados ABERTA do registo R1 permanecem. As 28 lacunas G4/L02 e a ausência da sua enumeração original continuam preservadas, sem correspondência inventada com os IDs R1.

## 4. Preservação e verificação documental

Hashes SHA256 lidos antes da consolidação em progbox; identificam os documentos históricos, não demonstram autorização de execução:

| Documento preservado | SHA256 |
| --- | --- |
| auth-boot-02-r1.md | `59c312d7dded14db9781d5e2a8e91acbce433b79a6d69427d3884f846e182eff` |
| auth-boot-02-r1-gaps.md | `d86570e878c97aa86a96099aa95701587d7df0d5c7e62b8145daeec05d507edf` |
| auth-boot-02-r1-traceability.md | `9becfd88ff071f3d0b99e25662de7bb6ce07f3e0394e3ffef85180336fb1be8c` |
| proposals/auth-boot-02-r1.NOT-APPROVED.md | `ec4e3afa6a6a1be5f1caaac18ec800442dfb8daddd64244f07cf4b6e32b4a4b6` |

O registo de decisões anterior à adenda tinha SHA256 `3f4eaa13eabf7739dfc8e4ee451361c1b7b89cb2f58f871f638de46f8f234c15`. A adenda R2 é acrescentada depois do conteúdo existente; os seus estados históricos não são reescritos.

Verificação desta entrega limitada a texto, referências, hashes e âmbito das alterações. Sem ensaios aplicacionais ou de laboratório, builds, SQL, migrações, serviços, infraestrutura, commits ou push. AUTH-03/F02/G2/G4 fechados; DEV-09B não autorizada; GAP-001/002 abertas.
