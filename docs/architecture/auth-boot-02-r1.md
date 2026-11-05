# AUTH-BOOT-02-R1 — Consolidação arquitetural

**Estado: CANDIDATO DOCUMENTAL PARA REVISÃO HUMANA — bytes não aprovados.**

Identificador: AUTH-BOOT-02-R1. Revisão documental: R1-CONSOLIDATION-B-CANDIDATE-1.
Preparação documental em progbox. Não é implementação, autorização operacional,
aprovação assinada nem formato atualmente aceite pelos executores.

## 1. Autoridade, proveniência e precedência

O responsável humano declara R1-D01 a R1-D10 aprovadas arquiteturalmente nesta
conversa. CONSOLIDAÇÃO-B autoriza exclusivamente três documentos novos e uma
adenda ao registo. A autorização não aprova antecipadamente estes bytes.

| Fonte | Conteúdo demonstrado e limite |
| --- | --- |
| H-B | Pedido CONSOLIDAÇÃO-B, anexo `a80a6b23-f866-404e-83e1-120d9b1fbf06/Pasted text.txt`, §§1–8: autoriza a organização modular, explicita os requisitos das dez decisões e manda manter as 20 lacunas abertas. |
| H-A | Pedido CONSOLIDAÇÃO-A, anexo `51c3491c-5df2-493e-94aa-73be4ba3a6dd/Pasted text.txt`, §§2–10: declara 10/10 aprovações arquiteturais e os requisitos a preservar. |
| H-D03 | Aprovação humana R1-D03 e contexto do pedido D04, anexo `e611751b-9d4e-4ed7-b5ca-bba0f03d4f78/Pasted text.txt`, linhas 5–9 e 61–63: HTTPS/TLS 1.3, mTLS entre serviços e proibição de TLS 0-RTT nas interfaces sensíveis. |
| H-D | Pedido CONSOLIDAÇÃO-D, anexo `7796e9b1-153f-461d-b730-28244f760ec2/Pasted text.txt`, §5: clarifica D06, preservando o rollback transacional anterior ao commit previsto nos contratos e proibindo recuperação automática de operações incertas. |
| H-REV | Contextos humanos das revisões disponíveis nesta sessão: D07, anexo `df953164-d216-437a-8a11-4be3914ae13f`; aprovação D07 e pedido D08, `586f2ae9-999f-42d3-bcee-a1793be436ff`; D09, `726df3bd-359d-47b4-acdc-1e0abd985b34` e repetição `fb654ff8-0e75-456c-a5f0-f495d70cc42d`; D10, `10a6ad0e-3c63-4b5d-bf3c-dc617a04936b`. A aprovação global é expressa em H-A/H-B; estes contextos não são dez transcrições individuais integrais de aprovação. |
| P-R1 | [Proposta histórica R1-DRAFT-1](proposals/auth-boot-02-r1.NOT-APPROVED.md), SHA256 `ec4e3afa6a6a1be5f1caaac18ec800442dfb8daddd64244f07cf4b6e32b4a4b6`; permanece byte-identical e com o seu estado original. |
| H-I2 | Pedido I2-PREFLIGHT, anexo `aedd3ea8-5de5-433c-a5c9-bbbd8c3427ff/Pasted text.txt`, linhas 65–87: requisitos I2-D02/D03 recuperados; não prova equivalência com AUTH-BOOT-02. |

Os anexos estão sob `/home/paulo/.codex/attachments/`, fora do checkout.
A proveniência das aprovações é parcial quanto aos textos integrais e datas
individuais: não se inventam transcrições, datas ou assinaturas. As formulações
seguintes são consolidação dos requisitos efetivamente fornecidos, não citações
literais de dez atos humanos originais. Ver [rastreabilidade](auth-boot-02-r1-traceability.md).

Precedência de interpretação: decisões humanas explicitamente fornecidas;
contratos aprovados preservados no repositório; proposta histórica; recomendações
novas, identificadas como tal. O presente candidato procura documentar essa
precedência; a sua exatidão continua sujeita a revisão humana.

O original AUTH-BOOT-02 continua não localizado. R1 é especificação substituta,
não recuperação do original, nem equivalência demonstrada com I2, G4-WF1 ou
schemas F03/F04. Alternativas históricas não são automaticamente aprovadas.

## 2. Estados, âmbito e fronteiras

| Classificação | Significado nesta consolidação |
| --- | --- |
| Aprovado arquiteturalmente | Invariantes e parâmetros explicitados por H-A/H-B e pelos contextos humanos disponíveis. |
| Ainda não especificado | Produtos, schemas, protocolos e parâmetros identificados nas lacunas. |
| Ainda não demonstrado | Exclusividade de início, ordenação com primeiro efeito, independência, recuperação e demais provas operacionais. |
| Ainda não implementado | Percurso integrado de autoridade/verificador/estado/admissão descrito por R1; fundações existentes não equivalem a esse percurso. |
| Não autorizado operacionalmente | Nenhuma implementação, infraestrutura, serviço, build ou operação PostgreSQL é autorizada por este documento. |

A autoridade reside conceptualmente numa VM Proxmox dedicada, separada da aplicação
LiveNet e das VMs PostgreSQL. Separar avaliação/emissão, verificação, estado
autoritativo e execução. Separação lógica não obriga a uma VM adicional por função;
localização e mecanismos concretos permanecem pendentes.

A autoridade não executa migrações nem recebe administração das bases LiveNet.
A aplicação não aprova os próprios pedidos; o executor não emite aprovações,
administra confiança/revogação ou escreve livremente no estado autoritativo.
Credencial SQL, assinatura, ficheiro, digest, nome de operador, recibo ou teste
offline positivo nunca são autorização suficiente.

## 3. R1-D01 — Registo independente de confiança

**Aprovado arquiteturalmente.** Registo independente, versionado e administrado
separadamente de autoridades, chaves públicas, âmbitos e políticas previamente
autorizados. O emissor não administra sozinho a confiança que o legitima.
Identidade, permissões, política e contexto são verificados com comportamento
fail-closed. Revogação e alterações de confiança exigem canais e proveniência
independentes, autenticados e auditáveis.

Não aceitar TOFU, confiança autodeclarada, chave incorporada na própria aprovação
como raiz, URL arbitrário ou DNS isolado como prova de confiança.
A credencial da aplicação não administra o registo.

**Pendente:** tecnologia, distribuição, protocolo de atualização, responsabilidades
e eventual raiz administrativa offline. Dependências D07/D09/D10;
R1-GAP-011, R1-GAP-013 e R1-GAP-017.

## 4. R1-D02 — Envelope, canonicalização e assinatura

**Parâmetros fixados.** Envelope JSON fechado com apenas `payload` e
`signature_hex`. O payload contém exatamente 25 campos obrigatórios:

1. `protocol_version`
2. `signature_algorithm`
3. `issuer_id`
4. `key_id`
5. `trust_policy_version`
6. `approval_id`
7. `request_id`
8. `attempt_id`
9. `approver_id`
10. `requester_id`
11. `executor_id`
12. `audience`
13. `environment`
14. `vm_generation_id`
15. `target_binding_sha256`
16. `global_digest_sha256`
17. `operation`
18. `gate`
19. `purpose`
20. `execution_plan_sha256`
21. `issued_at`
22. `not_before`
23. `expires_at`
24. `authority_epoch`
25. `revocation_epoch`

`protocol_version="1"`. Canonicalização JCS RFC 8785, UTF-8 e Ed25519 puro.
Bytes assinados, exatamente:

```text
ASCII("LiveNet/AUTH-BOOT-02-R1/approval/v1") || 0x00 || UTF8(JCS(payload))
```

Não usar Ed25519ctx/Ed25519ph nem substituir a mensagem por um digest externo.
Assinatura hexadecimal lowercase de 128 caracteres. Payload máximo 16 KiB;
envelope máximo 32 KiB; profundidade máxima 8. Parser estrito, sem campos
desconhecidos, duplicados, Unicode inválido ou fallback criptográfico.
JCS não se reduz a ordenar chaves num serializador JSON comum.

**Ainda não especificado:** formatos individuais não expressamente fixados,
limites por campo, catálogos, schemas/codificação dos bindings e dos digests,
relação entre digest global e bundle AUTH-03 e vetores de interoperabilidade.
As sugestões UUID/ASCII/strings decimais da proposta não são promovidas
automaticamente a requisitos aprovados. Não reconstruir schemas F03/F04 por
inferência. Dependências D01/D05/D08; R1-GAP-008, R1-GAP-009 e R1-GAP-018.

## 5. R1-D03 — Transporte e autenticação

**Aprovado arquiteturalmente.** HTTPS nas interfaces de serviço aplicáveis ao
protocolo R1, com TLS 1.3 e mTLS nas interfaces de rede entre
serviços; autenticação humana forte e autorização contextual por serviço,
operação, ambiente e finalidade. Identidades e material TLS, Ed25519 e humanos
são distintos. Certificado válido não concede poderes de emissão/administração.
TLS 0-RTT é proibido nas interfaces sensíveis (H-D03).
Não há fallback autorizador offline.

Comunicação exclusivamente interna sob DEV-05A-D01: sem exposição pública,
IP público, port forwarding de entrada Internet ou túneis equivalentes.
Saídas e acesso administrativo exigem âmbito próprio. Rede privada ou DNS
interno não demonstram isolamento. Eventual IPC local autenticado exige revisão;
não transforma separação lógica em aprovação de transporte concreto.

**Pendente:** CA, endpoints, emissão/renovação/revogação de certificados,
mapeamento das identidades e parâmetros de rede. PKI e certificados não estão
implementados por esta formalização. Dependências D01/D07/D10;
R1-GAP-006, R1-GAP-011 e R1-GAP-015.

## 6. R1-D04 — Estado autoritativo, claim e consumo

**Aprovado arquiteturalmente.** Fonte autoritativa transacional e durável,
independente das bases LiveNet. Vínculos imutáveis de pedido, aprovação,
tentativa, participantes e contexto. Ciclo:

```text
ISSUED → CLAIMED → CONSUMED_FOR_ATTEMPT
```

Claim exclusivo, condicional e atómico; consumo durável antes de efeitos.
Revogação, política, tempo e vínculos são revalidados nas transições pertinentes.
Estado anterior e unicidade integram a transação, não uma leitura seguida de
escrita desprotegida. Duas instâncias não podem ganhar a mesma transição.

Sem libertação, transferência ou reutilização, incluindo timeout, lease expirada,
crash ou reinício. Consulta/reenvio pode informar estado já persistido, mas não
concede segunda permissão. IDs iguais com conteúdo diferente são conflito.
Consumo único não demonstra exclusividade de iniciação: esta pertence a D08.

Não existe atomicidade distribuída presumida com PostgreSQL nem garantia de
execução exatamente uma vez. Consumo sem execução inutiliza a aprovação;
execução sem resultado confirmado exige bloqueio/reconciliação.

**Pendente:** produto, localização, schema, isolamento e provas de durabilidade.
Nenhuma alternativa SQLite/PostgreSQL/ledger da proposta foi selecionada.
Dependências D05/D08/D09/D10; R1-GAP-001, R1-GAP-003 e R1-GAP-010.

## 7. R1-D05 — Tempo, epochs e revogação

**Parâmetros fixados:**

```text
issued_at <= not_before < expires_at
expires_at - issued_at <= 900 segundos
UTC confiável: [L,U]
Elegibilidade apenas quando L >= not_before e U < expires_at
```

UTC autenticado com incerteza explícita; monotónico local não prova UTC.
Sem grace period. Revalidar no claim, consumo e antes dos efeitos.
Relógio não confiável, rollback ou continuidade desconhecida bloqueiam.

Revogação autoritativa de aprovações, chaves, autoridades e políticas;
`authority_epoch` e `revocation_epoch` monotónicos, com igualdade estrita
inicial face ao estado autoritativo atual. Sem autorização por informação antiga.
Revogação deve ter ordenação definida com claim/consumo. Aumento de epoch não
recupera consumos perdidos nem resolve resultado incerto.

Expirar/revogar não apaga consumo ou desfaz efeitos já iniciados. Não se promete
paragem instantânea ou rollback de commit. **A ordenação de expiração/revogação
com o primeiro efeito PostgreSQL continua não demonstrada: bloqueador D08.**

**Pendente:** fonte temporal, limites de incerteza, protocolos de frescura,
semântica operacional das mudanças de epochs e tratamento de saltos.
Dependências D03/D04/D08/D10; R1-GAP-002, R1-GAP-003 e R1-GAP-014.

## 8. R1-D06 — Resultados incertos e reconciliação

**Aprovado arquiteturalmente.** Separar utilização da aprovação, elegibilidade,
resultado da execução e estado de reconciliação. Classificações conceptuais,
sem alteração de enums F02:

| Classificação | Condição |
| --- | --- |
| `SUCCEEDED_VERIFIED` | Evidência suficiente e atribuível à tentativa/destino de commit e efeitos esperados, sem contradições relevantes abertas. |
| `FAILED_VERIFIED` | Falha terminal comprovada e efeitos caracterizados; não significa necessariamente ausência de efeitos parciais. |
| `UNKNOWN/BLOCKED` | Evidência incompleta, contraditória, desatualizada ou não atribuível. |
| `RECONCILED` | Esclarecimento técnico e classificação preservados com decisão humana autenticada e auditada; não é nova autorização. |

Reconciliação assistida por operador e inspeção independente read-only do destino
atestado. Ausência de logs, recibo, resposta ou marcador não prova ausência de
efeito. Assinatura ou recibo do executor não é prova independente de commit.
Revisão Alembic isolada não atribui uma execução à tentativa.

O rollback transacional PostgreSQL previsto nos contratos AUTH-03 e security,
perante falha antes do commit, não é proibido por D06 (clarificação H-D §5).
Não autoriza repetir a operação ou reutilizar a aprovação, nem permite presumir
que efeitos externos ou já confirmados foram revertidos. Os contratos existentes
permanecem preservados, sem introdução de novos mecanismos transacionais.

Continuam proibidos rollback compensatório automático de operações com resultado
incerto, retry, reparação ou reabilitação automática, reutilização ou libertação
de aprovação consumida e bypass de bloqueio ou reconciliação humana. Rollback
local não garante ausência de efeitos externos.

Encerramento administrativo sem prova não converte UNKNOWN em sucesso.
Nova tentativa exige
novo pedido, plano aprovado para o estado atual, novo attempt e nova aprovação
humana, após resolução das condições relevantes e da capacidade de continuação
antiga.

Diagnóstico automatizado read-only exige autorização específica posterior.
Dependências D08/D09/D10; R1-GAP-007, R1-GAP-012 e R1-GAP-020.

## 9. R1-D07 — Custódia, rotação e comprometimento

**Aprovado arquiteturalmente.** Separar chaves Ed25519, TLS/mTLS, identidades
humanas, administração da confiança e eventuais chaves de auditoria/backup.
Chave de emissão fora da aplicação, verificador e executor. Custódia e
administração independentes da emissão; privilégios mínimos.

Preferir chave não exportável quando compatibilidade Ed25519 puro, isolamento e
recuperação forem demonstrados. Não selecionar HSM, TPM, software protegido,
fornecedor ou hardware por inferência. Não exportabilidade não impede por si
assinaturas abusivas por um serviço comprometido.

Geração, registo/ativação, utilização, suspensão, rotação, revogação e destruição
exigem procedimentos próprios. Rotação inicial por corte explícito e novo
`key_id`; IDs não são reassociados a material diferente. Sem fallback para chave
antiga/desconhecida. Igualdade estrita de epochs mantém-se durante o corte.

Preservar chaves públicas, políticas e revogações para história, sem lhes conferir
elegibilidade atual. Assinatura histórica após compromisso não prova decisão
humana legítima ou momento anterior ao incidente. Suspeita/comprometimento,
divergência de confiança ou perda de continuidade bloqueiam o âmbito afetado.
Substituição da autoridade exige decisão e confiança independentes, sem apagar
consumos ou incertezas.

**Pendente:** mecanismo de custódia, cerimónias, backups privados e destruição
verificável de cópias. Dependências D01/D03/D05/D09/D10;
R1-GAP-011 e R1-GAP-017.

## 10. R1-D08 — Executor, binding e gates

**Aprovado arquiteturalmente.** Verificador externo ao processo executor,
estado autoritativo independente e fronteira executora mínima. Identidades e
privilégios segregados. Executor não recebe emissão, administração de confiança
ou escrita administrativa do estado de consumo/revogação.

Vincular integralmente os 25 campos, contexto aprovado, executor lógico,
encarnação concreta, sessão, ligação/transação PostgreSQL, destino e geração.
Identidade declarada, PID, lock local, memória ou lease não demonstram
exclusividade durável. O `vm_generation_id` não é silenciosamente reutilizado
como identidade da encarnação executora.

Distinguir assinatura válida, elegibilidade atual, consumo autoritativo e
admissão operacional. `CONSUMED_FOR_ATTEMPT` não abre o executor.
Prevenir segunda iniciação após concorrência, replay de envelope/recibo,
timeout, crash, reinício, transferência, clone, rollback ou continuação antiga.
Uma consulta de estado não permite retomar. Mesma ligação, plano/artefactos
efetivos e origem/destino aprovados devem ser preservados.

### BLOQUEADORES DE ATIVAÇÃO

- **R1-GAP-001 — Exclusividade durável da iniciação: ainda não demonstrada.**
- **R1-GAP-002 — Ordenação de revogação/expiração com o primeiro efeito
  PostgreSQL: ainda não demonstrada.**

Revalidar imediatamente antes do envio SQL reduz uma janela, mas não demonstra
elegibilidade no primeiro efeito: podem ocorrer suspensão, rede ou espera por
locks. Recibo, advisory lock ou fencing não aplicado no recurso não fecham a
janela. O mecanismo concreto e a fronteira efetiva precisam de especificação,
prova e aprovação próprias; não se redefine implicitamente o início para
enfraquecer D05. Não se promete exatamente-uma-vez distribuído.

Integração não implementada nem ativada por este candidato. Dependências
D01–D07/D09/D10 e R1-GAP-005, R1-GAP-006, R1-GAP-008.

## 11. R1-D09 — Auditoria, evidência e retenção

**Aprovado arquiteturalmente.** Registo estruturado/versionado, separado de
diagnóstico e do estado anti-replay. Transição autoritativa e evidência essencial
atómicas no respetivo domínio, sem presumir atomicidade com PostgreSQL ou cópia
externa. Cópia independente dos eventos críticos e referências verificáveis de
continuidade. **Confirmação independente obrigatória antes de novos efeitos
protegidos.** Falha/divergência bloqueia a progressão dependente.

Cobrir pedido, avaliação/decisão humana, emissão/entrega, verificação,
elegibilidade, claim, consumo, admissão, início observado, resultado, expiração,
revogação, rotação, confiança, epochs, bloqueio, incidente, reconciliação,
backup/restauro e validação de continuidade. Não fabricar eventos não observados.
Um evento não prova automaticamente efeito PostgreSQL.

Correlacionar IDs, atores, instância, destino, geração, plano/digests, gate,
operação, política/epochs, resultado e caso de reconciliação. Mesmo ID com bytes
divergentes é conflito. Sequências, referências causais, UTC/incerteza e receção
tardia são distintos; timestamps entre máquinas não estabelecem ordem total.

Hash chaining local não resiste sozinho ao administrador de todo o histórico;
testemunho de hashes não recupera conteúdo perdido. Segunda VM no mesmo
hipervisor não prova independência contra o seu administrador.

Sem segredos, credenciais ou envelopes integrais em logs gerais. Minimização,
schema de eventos fechado, acessos/exportações controlados e administração
segregada. Eventual arquivo restrito do objeto assinado exige política específica;
hash isolado não permite reconstruí-lo para prova histórica.

Retenção distinta para logs, consumos/revogações, execução, reconciliações,
incidentes, chaves públicas, backups e testemunhos. Rotação/eliminação não pode
apagar estados necessários à não reutilização. Reconciliação acrescenta evidência
sem reescrever o histórico. Futuro SIEM não é fonte autoritativa R1 por pressuposto.
Sem fallback volátil. Retransmissão de evento não autoriza retry da operação.

**Pendente:** protocolos, schemas, armazenamento, retenção, completude,
custódios e independência efetiva. Dependências D04/D06–D08/D10;
R1-GAP-004, R1-GAP-012, R1-GAP-016 e R1-GAP-017.

## 12. R1-D10 — Operação e recuperação

**Aprovado arquiteturalmente.** Autoridade inicialmente única em VM Proxmox
dedicada, separada da aplicação e VMs PostgreSQL. Sem HA ou failover automático
nesta decisão. Recuperação por reconstrução controlada, com estado e evidência
independentes do domínio de falha/comprometimento.

Preservar epochs, IDs, claims, consumos, admissões exclusivas, revogações,
chaves/políticas, auditoria e reconciliações. Nunca reduzir epochs, apagar consumo,
reutilizar IDs ou reativar aprovação antiga. Demonstrar transições posteriores
ao backup e invalidar capacidade de instâncias/executores antigos, não apenas
constatar ausência de resposta.

Snapshot assinado, backup internamente consistente, nova chave ou incremento de
epoch não demonstram continuidade. Clones podem conservar IDs/certificados.
Perante rollback, clonagem, split-brain, corrupção ou continuidade desconhecida,
bloquear. Substituição de autoridade não contorna histórico perdido nem resultados
incertos. Recuperação de confiança é independente das credenciais comprometidas.

Backups com integridade, cifragem, inventário, retenção e custódia separados.
Arranque, paragem, atualização, rotação, recuperação e revalidação precisam de
procedimentos. Reentrada apenas após validação independente e decisão humana
autenticada/auditada. Rollback de software não pode rebaixar políticas, epochs
ou histórico, nem permitir execução sobre schema incompatível. Sem bypass de emergência.

Responsabilidades segregadas para autoridade, Proxmox, confiança, chaves,
backups, auditoria, aprovação, reconciliação e incidente. Controlo por duas
pessoas é recomendação operacional ainda não concretizada; duas contas da mesma
pessoa não provam dupla supervisão.

**Pendente:** custódios, mecanismos, procedimentos, RPO/RTO, retenção, capacidade
e ensaios concretos. Não se fixam valores pelo número de recursos. Dependências
D01/D04–D09; R1-GAP-003, R1-GAP-007, R1-GAP-016, R1-GAP-017 e R1-GAP-019.

## 13. Contratos e evidência existentes

| Contrato/fonte | Relação e limite preservado |
| --- | --- |
| [Registo de decisões](decision-register.md) | DEV-05A-D01 vinculativa; adenda R1 separada do texto histórico; 28 lacunas G4/L02 continuam abertas. |
| [AUTH-03](../specifications/f0/auth03-alembic-executor.md) | Mutações recusadas por `operation_gate()`; autorização externa futura não é configuração nem simples ficheiro. Commit incerto exige inspeção e reconciliação. |
| [F02/G4](../../scripts/postgres/g4/contracts.py) | Referências não autenticadas e objetos UNVERIFIED/BLOCKED não são capacidades; `execution_boundary()` só recusa. Não alterar enums. |
| [G2](../../backend/app/readiness_postgres/adapter.py) | Executor real desativado; evidência sintética não é REAL. Readiness não é autorização de migração. |
| [Security](../../scripts/postgres/m12b_security_migration.py) | Execução desativada, transação/ligação e reconciliação próprias; não ativar por booleano. |
| [DEV-08B](../specifications/f0/dev08b-persistence-contracts.md) | MVP f066 + security b12; AUTH-03 isolado f067; ledgers separados. Implementação de perfis não se reconcilia por esta formalização. |
| [DEV-08D](../operations/dev08d-auth03-application.md) | Documenta aplicação aprovada de 31 para 52 fontes. Não regenera nem altera o manifesto nesta tarefa. |
| [DEV-09A.1](../operations/dev09a1-executor-attestation-recovery.md) | Mecânicas/estados sintéticos e limites de commit incerto, sem autoridade operacional. |
| [DEV-09A.2](../operations/dev09a2-integration-closure.md) | 35 verificações históricas de recuperação sintética, mesmo host, sem prova off-host; não foram repetidas aqui. |
| [ATTEST03](../operations/dev09-attest03-reconciliation.md) | Separa fonte aprovada, ficheiro aplicado, validação offline e autorização operacional; preserva artefactos congelados DEV-09A.2. |

Persistem diferenças f066/f067 e requisitos de implementação por perfil. Não usar
head/stamp, fundir cadeias ou abrir gates. O patch agregado DEV-09A.2 não é aplicado.
Aprovações R1 não demonstram operação atual, recuperação integral ou privilégios.

## 14. Lacunas e condições de aceitação

O [registo R1-GAP-001–020](auth-boot-02-r1-gaps.md) mantém todas as entradas
**ABERTA**; a [matriz](auth-boot-02-r1-traceability.md) liga fontes, requisitos,
contratos e critérios. Não substituem originais ou lacunas G4/L02.

Antes da implementação correspondente: especificar schemas/bindings, confiança,
tempo, persistência, interfaces, custódia, auditoria e recuperação; rever
compatibilidade com contratos existentes e obter autorização específica.
Uma lacuna não é resolvida pela mera escolha de um produto.

Antes de ativação: demonstrar exclusividade e ordenação D08, durabilidade e
continuidade, transporte/identidades/privilégios reais, confirmação independente
D09 e recuperação D10. Ensaios futuros devem cobrir vetores criptográficos,
corrupção de campos, concorrência, replay, crash, perda de confirmação,
revogação/expiração, partições, rollback/clone, recuperação, rotação e atualização.
Exigir oráculos independentes e aceitação humana; nenhum ensaio foi executado
nesta consolidação.

## 15. Restrições e revisão documental

Esta entrega autoriza zero operações: sem implementação, provisionamento, chaves,
coletores, schemas, Docker, builds, serviços, SQL, migrações, backup/restauro,
commits ou DEV-09B. AUTH-03, F02, G2 e G4 permanecem fechados.

Para aceitar os bytes: verificar dez decisões, 25 campos e parâmetros D02,
fórmulas D05, dois bloqueadores D08, confirmação independente D09 e continuidade
D10; todas as lacunas abertas, fontes e links corretos, proposta/manifesto e
ficheiros preexistentes preservados, adenda exclusivamente acrescentada.
A aprovação arquitetural não torna estes bytes automaticamente aprovados.
