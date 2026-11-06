# LiveNet v2 — matriz de dependências para decisão de sequência

Candidata 0.1 · 31/10/2026 · Europe/Lisbon. Classificação documental, sem autorização de implementação.

## Regras da classificação

- **I — Independente de C4 e dos gates bloqueados:** entrega estritamente documental delimitada que usa fontes existentes sem executar/ativar percurso protegido, alterar contratos ou decidir matérias pendentes. Não significa que a futura funcionalidade esteja desbloqueada.
- **C — Condicionada:** a elaboração de opções/critério pode avançar documentalmente, mas a decisão final do contrato, prova ou arquitetura depende de matéria pendente. Não fecha essa dependência.
- **B — Bloqueada:** execução/ativação ou alegação de garantia impedida por C4/I-04 ou outro gate explícito. Aprovar documentos ou classificar I/C não ultrapassa B.

As classes descrevem o ato/entrega concreta, não o nome de todo um subsistema. Dependência de C4 só é atribuída quando sustentada pelas fontes; não se estende C4 automaticamente a todo POST ou consumidor do produto. Se uma operação não tiver âmbito/gates rastreáveis, permanece C para decisão de âmbito e B para execução não autorizada, sem inventar equivalências entre gates.

## Matriz de trabalho

| Trabalho/entrega concreta | Classe | Dependências e fundamento documental | Limite para futura execução |
| --- | --- | --- | --- |
| Critérios documentais de consulta inventory/UI, estados vazio/erro/sem acesso e paginação | I | Roadmap entrega 2; implementation-status «UI/Inventário»; DAT-01B/03A distinguem identidade/estado administrativo. Usar apenas contratos existentes. | Implementar/mudar UI ou validar contra serviços exige escopo próprio; não libera auth, ACL, dados ou readiness. |
| Exemplos exclusivamente documentais de identidade/proveniência | I | DAT-02A/B/C já aprovadas: UUID, contexto, contradições, sem fusão por IP/hostname isolados. | Exemplos não são adaptador, limiar aprovado ou autorização de persistir/mesclar recursos. |
| Decidir critérios concretos de correspondência/ambiguidade Discovery | C | DAT-02C reserva critérios/limiares; DAT-03B aprovação manual por defeito; roadmap entrega 3 e modelo §12. | Não escolher política nova como detalhe; contratos concretos, fontes/permissões, assíncrono e persistência precisam de decisão/evidência. |
| Traduzir retenção já aceite em critérios documentais de holds/proteção/saída | I | D2 V05 e P4-B4: preservação, separação, demonstrações e não eliminação automática; DAT-07A e reservas aplicáveis. | Não reabre prazos/bytes aceites; não implementa limpeza nem define TBD. |
| Resolver TBD de custódia/libertação R2 e esquemas físicos | C | D2 V05-05/06 e B10, roadmap 4/7; dependências específicas R2. | Decisão normativa/arquitetural própria quando material; C4/D09/V05-06 não demonstrados por resolver texto. |
| Desenhar RBAC grupo/recurso, JSONB, políticas e transições técnicas | C | Modelo §§2/6/12, DAT-09A/10A referenciados pelo estado; RBAC atual é parcial segundo implementation-status. | Âmbito, precedência e contratos concretos por rever; alteração de segurança não é autorizada. Sem afirmar que conceitos DAT estão por aprovar. |
| Monitorização/histórico, regras e canais: especificação concreta | C | Roadmap 4/5; tipos/unidades, semântica temporal/estados, políticas e assíncrono pendentes; D2 posterior prevalece no seu âmbito. | Checks reais, persistência e notificações exigem autorização e pré-requisitos próprios; não selecionar TSDB/filas/canais. |
| Outbox/SSE/workers/scheduler: contrato concreto e dependências | C | DAT-08A Outbox já aprovada conceptualmente; roadmap 3–5 exige contratos/coordenação, estado diz ausência funcional histórica. | Sem implementar/publicar eventos; retry Outbox não é retry da operação protegida C5. |
| Imagem/artefacto/CI: planeamento de aceitação e promoção | C | Roadmap 1/6/7 e evidências de embalagem/integração históricas; escopo/locks/segredos/critério STAGING e recovery necessários. | Não repetir empacotamento já validado como se ausente; builds/deploy/CI não autorizados e não abrem gates. |
| Persistência aplicacional, primeira conta, ACL e readiness positiva | B — outros gates | implementation-status atualizações DEV-06/07; AUTH-03/F02/G2/G4, f066/f067, permissões/recovery/HTTPS e continuidade nos respetivos âmbitos. | Validação histórica de transporte/UI não demonstra prontidão atual; sem migrations, escrita runtime ou checker habilitado. |
| Migrações aplicacionais/security e integração M1.2B/G4 | B — outros gates e requisitos de exclusividade aplicáveis | AUTH-03/F02/G2/G4 fechados; modelo adenda DAT-05A fixa alvos/ledgers e não autoriza migração. R2 não autoriza Alembic por extensão. | Não regenerar manifesto, executar DDL ou usar um gate para contornar outro; bloqueios C4 só no âmbito contratual aplicável. |
| Discovery real/reconciliação persistente, checks/alertas reais | B para execução nesta etapa; dependências C anteriores | Roadmap 3–5: fontes/alvos, contratos, segredos/rede, persistência, workers e aceitação; nenhuma implementação autorizada aqui. | Não classificar funcionalidade inteira como já desbloqueada por poder escrever especificação. Não presumir que todo caso depende diretamente de C4. |
| Execução protegida R2 → D09 → barreira → alvo e reentrada universal | B — C4/I-04 e gates aplicáveis | Fronteira C4 aprovada documentalmente: meio autónomo/privilegiado fora da imposição mantém inviabilidade; R2/D09/D10 e I-01–I-04. | Sem escolher F-A–F-E/CAND, sem garantir corte ou rearmar capacidades. |
| Limpeza destrutiva, libertação de proteção R2 e eliminação de cópias | B — retenção/autorizações; C4/I-04 quando capacidades antigas relevantes | D2 V05/B10: demonstração/decisão específicas e disposição destrutiva própria; COMPROVADO não autoriza destruição. | Não transformar expiry, backup ou classificação I em autorização de apagar. |
| Ativação STAGING/PROD, operação estável ou Kubernetes | B — gates de ativação e pré-requisitos do roadmap | Entregas 2/6/7/8: recovery, segurança, artefactos, evidências e autorizações por ambiente. | Rede interna/progbox DEV mantidos; K8S não substitui recovery ou resolve autoridade R2 única. |

## Três próximas atividades candidatas, todas documentais

Não executadas nesta entrega: são propostas de escopo para a decisão de sequência, sem criar tarefa nova ou iniciar implementação.

| Candidata | Entrega concreta e dependências | Risco principal | Critérios documentais de aceitação |
| --- | --- | --- | --- |
| P1 — critérios da consulta inventory | Grelha curta de lista/filtros/paginação/detalhe, vazio/erro/sem acesso e distinção administrativo/operacional; fontes UI/inventory atuais e DAT aprovadas. Classe I no âmbito documental. | Assumir campo/endpoint/comportamento não contratado ou confundir UX com ACL efetiva. | Cada critério tem fonte; dúvidas explicitadas; sem novas rotas/campos/ações de escrita; avaliação de evidência histórica sem novo teste; itens já cobertos não reapresentados como funcionalidade em falta. |
| P2 — critérios de retenção e proteção de observações | Derivação documental de D2 aceite/DAT-07A: conflitos/holds, objeto misto, histórico e condições de saída; classe I para rastreio, C para qualquer TBD. Não refazer a revisão normativa de retenção. | Reabrir D1/D2/D3, inventar prazo/libertação, misturar D09/V05-06 ou autorizar limpeza. | Remissões exatas aos requisitos aceites; TBD e decisão necessária isolados; nenhum prazo/estado normativo alterado; matriz de condições não gera ação operacional nem fecha demonstrações. |
| P3 — casos concretos de reconciliação Discovery | Pequeno catálogo de colisão de identificadores, observações contraditórias, candidato repetido e recurso arquivado; DAT-02A/B/C/03A/B e dependências de preservação P2. Classe I para exemplos fiéis, C para opções técnicas/limiares residuais. | Converter «idempotência de reconciliação» em retry C5; fusão/reativação automática implícita; ampliar persistência física. | Exemplos distinguem observação/candidato/recurso e conservam UUID/proveniência/histórico; ambiguidades para revisão; nenhuma fusão/limiar/entidade nova escolhida; lista curta das decisões concretas restantes, sem implementar adaptador/schema. |

## Sequência recomendada

**P1 e P2 podem ser preparados documentalmente sem esperar resolução C4; P3 usa os critérios de proteção de P2 e os contratos DAT existentes.** A ordem é de dependência/baixo risco, não escalonamento autorizado de código. Não é necessário esperar P1 para elaborar P2; P3 não depende de libertação de gates para descrever exemplos, mas qualquer escolha de critérios residuais conserva classe C.

Após revisão humana dessas entregas, decidir separadamente se há âmbito suficiente para eventual implementação delimitada e quais gates se aplicam. Esta classificação não fornece tal autorização. Execução protegida/reentrada continua B, sem nova análise de F-A–F-E/CAND ou redução da garantia. Nenhum critério editorial deve converter-se em pedido de aprovação arquitetural; só escolhas materiais reais ou autorização de implementação exigem decisão própria.
