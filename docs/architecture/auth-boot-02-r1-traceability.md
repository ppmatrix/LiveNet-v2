# AUTH-BOOT-02-R1 — Matriz de rastreabilidade

**Estado: CANDIDATO DOCUMENTAL PARA REVISÃO HUMANA — não é evidência operacional.**

Revisão: R1-TRACE-CONSOLIDATION-B-CANDIDATE-1.
A fonte normativa candidata é o [consolidado](auth-boot-02-r1.md).
O [registo de lacunas](auth-boot-02-r1-gaps.md) mantém 20 entradas ABERTA.
Esta matriz referencia requisitos, sem duplicar integralmente o texto normativo.

## 1. Fontes e limites de proveniência

| Ref. | Fonte | Alcance |
| --- | --- | --- |
| H-B | Pedido CONSOLIDAÇÃO-B, `/home/paulo/.codex/attachments/a80a6b23-f866-404e-83e1-120d9b1fbf06/Pasted text.txt`, §§1, 5–8 | Autoriza só quatro caminhos; explicita o conteúdo das dez decisões, todas arquiteturalmente aprovadas, e exige candidato de bytes ainda não aprovados. |
| H-A | Pedido CONSOLIDAÇÃO-A, `/home/paulo/.codex/attachments/51c3491c-5df2-493e-94aa-73be4ba3a6dd/Pasted text.txt`, §§2–10 | Declara 10/10 aprovações e fixa os requisitos de preservação. |
| H-D03 | Aprovação humana R1-D03 e contexto do pedido D04, `/home/paulo/.codex/attachments/e611751b-9d4e-4ed7-b5ca-bba0f03d4f78/Pasted text.txt`, linhas 5–9 e 61–63 | Confirma HTTPS/TLS 1.3, mTLS entre serviços e proibição de TLS 0-RTT nas interfaces sensíveis. |
| H-D | Pedido CONSOLIDAÇÃO-D, `/home/paulo/.codex/attachments/7796e9b1-153f-461d-b730-28244f760ec2/Pasted text.txt`, §5 | Clarifica D06: rollback transacional anterior ao commit preservado; recuperação automática de operações incertas proibida. |
| H-REV | Contextos humanos de D07, aprovação D07/pedido D08, D09 e D10 disponíveis na sessão; IDs dos anexos no consolidado §1 | Corroboram o alcance; não constituem dez atos integrais de aprovação transcritos nesta entrega. |
| H-I2 | I2-PREFLIGHT, anexo `aedd3ea8-5de5-433c-a5c9-bbbd8c3427ff/Pasted text.txt`, linhas 65–87 | I2-D02/D03 recuperados. SHA256 documental `795ef6000745493a6c5a91f6b1116ff6170b9e7eecf200385165a199cabd830b`; sem equivalência histórica demonstrada com AUTH-BOOT-02. |
| P-R1 | [R1-DRAFT-1](proposals/auth-boot-02-r1.NOT-APPROVED.md), secções B–L | Proposta histórica preservada: SHA256 `ec4e3afa6a6a1be5f1caaac18ec800442dfb8daddd64244f07cf4b6e32b4a4b6`. Os seus PENDENTE não são reescritos. |
| C-REG | [Registo](decision-register.md), DEV-05A-D01 e adenda DEV-08B | Rede interna e perfis/cadeias aprovados; estados históricos preservados e contextualizados pela nova adenda. |
| C-AUTH | [Especificação AUTH-03](../specifications/f0/auth03-alembic-executor.md), linhas 147–166; [executor](../../scripts/postgres/auth03_alembic_executor.py), linhas 56–59 e 136–151 | Gate bloqueado, verificador futuro externo, consumo e reconciliação; hash de fontes não é autorização. |
| C-F02 | [F02/G4](../../scripts/postgres/g4/contracts.py), linhas 207–211, 427–502 | Referências não autenticadas, estados UNVERIFIED/BLOCKED e recusa de execução. |
| C-G2 | [Adaptador G2](../../backend/app/readiness_postgres/adapter.py), linhas 23–33 e 122–125 | Execução real desativada e evidência sintética; não é readiness operacional. |
| C-SEC | [Executor security](../../scripts/postgres/m12b_security_migration.py), linhas 51–62 e 206–218 | Execução desativada, transação e reconciliação próprias. |
| C-08B | [Contratos DEV-08B](../specifications/f0/dev08b-persistence-contracts.md), §§Autoridade, D01, D02 e fronteiras | Isolamento/verify-full, MVP f066/b12 e AUTH-03 isolado f067; aprovação documental não implementa perfis. |
| E-08D | [DEV-08D](../operations/dev08d-auth03-application.md), §§Aprovação, Preflight e SHA256 | Aplicação aprovada do manifesto 31→52. Não autoriza autoridade ou operação PostgreSQL. |
| E-09A1 | [DEV-09A.1](../operations/dev09a1-executor-attestation-recovery.md), linhas 46–72 | Evidência histórica sintética e limites de commit incerto/restauro; não repetida aqui. |
| E-09A2 | [DEV-09A.2](../operations/dev09a2-integration-closure.md), linhas 103–115 | Recuperação sintética no mesmo host, sem demonstração off-host/autoridade real; não repetida aqui. |
| E-ATTEST | [ATTEST03](../operations/dev09-attest03-reconciliation.md), §§Categorias, Evidência e Referências históricas | Fonte aprovada ≠ ficheiro aplicado ≠ validação offline ≠ autorização operacional; propostas congeladas permanecem intactas. |

Os anexos não fazem parte do checkout. As datas e transcrições individuais de
aprovação não estão integralmente recuperadas: proveniência parcial nesse sentido,
sem reduzir a declaração explícita atual de aprovação 10/10 em H-A/H-B.
Não atribuir data de redação ou commit à aprovação humana. R1-GAP-013 permanece
ABERTA até revisão documental; nenhum digest torna um pedido numa autorização
criptográfica de execução.

## 2. Decisões e critérios

Em todas as linhas, aprovação significa arquitetural; os bytes consolidados
aguardam revisão. “Não implementado” refere o percurso R1 correspondente, não
nega as fundações isoladas existentes. Os critérios são futuros, não resultados.

| Decisão / referência no consolidado | Requisito/invariante | Fonte documental | Proveniência humana | Contratos relacionados | Lacunas associadas | Estado de especificação | Estado de implementação | Condição de aceitação futura |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1-D01 / §3 | Confiança independente, versionada, âmbitos e política; sem autoconfiança | P-R1 D e L:375 | H-B §5 D01; H-A §2; H-REV | C-REG, C-F02, H-I2 | 011, 013, 017 | Arquitetura fixada; distribuição/administração concretas pendentes | Percurso R1 não implementado; objetos F02 são referências | Demonstrar emissor/aplicação sem administração unilateral da confiança |
| R1-D02 / §4 | Envelope fechado, 25 campos, JCS/UTF-8, domínio/Ed25519 puro e parâmetros fixados | P-R1 E.2/E.3 e L:376 | H-B §5 D02; H-A §6 | C-AUTH, C-F02, H-I2 | 008, 009, 018 | Parâmetros fixados; tipos, catálogos, bindings e vetores pendentes | Parser/verificador R1 não implementado | Comparação exata dos 25 nomes/parâmetros e vetores independentes; nenhum campo extra/fallback |
| R1-D03 / §5 | HTTPS/TLS 1.3/mTLS, sem TLS 0-RTT nas interfaces sensíveis, identidades separadas, humano forte, autorização contextual e LAN-only | P-R1 C/I e L:377 | H-B §5 D03; H-D03 | C-REG, C-08B, C-AUTH | 006, 011, 015 | Princípios fixados; PKI/endpoints/certificados pendentes | Transporte R1 não implementado; não inferir da factory ou de URL | Evidência de HTTPS, recusa de TLS 0-RTT, autenticação/autorização e isolamento real sem fallback |
| R1-D04 / §6 | Estado independente, ISSUED→CLAIMED→CONSUMED_FOR_ATTEMPT, transições atómicas e consumo antes de efeitos | P-R1 F/G e L:378 | H-B §5 D04; H-A §2; H-REV | C-AUTH, C-SEC, H-I2 | 001, 003, 010 | Invariantes fixadas; persistência/interfaces pendentes | Estado autoritativo R1 não implementado; modelos em memória não o substituem | Um vencedor por transição, persistência recuperável e nenhuma reutilização/transferência |
| R1-D05 / §7 | 900 segundos, fórmulas temporais, incerteza, epochs estritos e revogação fresca | P-R1 E/F/G e L:379 | H-B §5 D05; H-A §7 | C-AUTH, C-F02, H-I2 | 002, 003, 014 | Fórmulas fixadas; fonte temporal e ordenação efetiva pendentes | Enforcement temporal/revogação R1 não implementado | Recusar tempo/estado antigo e demonstrar ordenação com primeiro efeito; bloqueador D08 |
| R1-D06 / §8 | Resultado verificado ou UNKNOWN/BLOCKED, reconciliação independente e nova autorização; rollback transacional anterior ao commit preservado, sem recuperação automática de operação incerta | P-R1 F/G e L:380 | H-B §5 D06; H-A §2; H-REV; H-D §5 | C-AUTH, C-F02, C-SEC, E-09A1 | 007, 012, 020 | Classificações fixadas; procedimento/diagnóstico concreto pendente | Reconciliação durável R1 não implementada; ensaios históricos sintéticos | Evidência suficiente/atribuível e decisão humana; nenhuma recuperação automática da aprovação |
| R1-D07 / §9 | Segregação, custódia, corte explícito, novo key_id e revogação | P-R1 D/I e L:381 | H-B §5 D07; H-REV inclui aprovação D07 | C-REG, C-AUTH | 011, 017 | Princípios fixados; hardware/cerimónias/backups privados pendentes | Custódia/rotação R1 não implementadas por esta entrega | Provar isolamento e compatibilidade, preservar histórico e recusar chave antiga |
| R1-D08 / §10 | Verificador externo, executor mínimo, binding e exclusividade durável até ao início efetivo | P-R1 B/F/H/J e L:382 | H-B §5 D08; H-A §8 | C-AUTH, C-F02, C-G2, C-SEC | 001, 002, 005, 006, 008 | Invariantes fixadas; dois mecanismos BLOQUEADORES DE ATIVAÇÃO | Integração não implementada; gates atuais recusam | Provar uma iniciação e revogação/expiração até primeiro efeito; pré-consulta SQL insuficiente |
| R1-D09 / §11 | Evidência essencial atómica local, cópia/continuidade independentes e confirmação antes de efeitos | P-R1 F/G/I e L:383 | H-B §5 D09; H-A §9 | C-AUTH, C-G2, E-ATTEST | 004, 012, 016, 017 | Invariantes fixadas; protocolos/armazenamento/retenção pendentes | Auditoria R1 independente não implementada; audit aplicacional é fundação distinta | Falha/divergência bloqueia; cópia recuperável e causalidade sem segredos nem apagamento de consumo |
| R1-D10 / §12 | VM única, reconstrução, continuidade, invalidação de instâncias e reentrada humana | P-R1 C/D/G/I/J/K e L:384 | H-B §5 D10; H-A §10; H-REV | C-REG, C-08B, C-SEC, E-09A1, E-09A2 | 003, 007, 016, 017, 019 | Princípios fixados; RPO/RTO/custódios/procedimentos pendentes | Recuperação operacional da autoridade não demonstrada/implementada | Restauro antigo/clone não reativa poderes; prova independente e decisão auditada antes de reentrada |

## 3. Divergências temporais e fronteiras

- P-R1 E/L ainda diz PENDENTE; I:302–304 chama mTLS candidato. H-A/H-B e a
  consolidação documentam a decisão posterior, sem alterar a proposta histórica.
- P-R1 documenta 25 campos e payload 16 KiB/profundidade 8; H-B fixa também
  envelope 32 KiB e `protocol_version="1"`. Não promover formatos individuais
  candidatos apenas porque a aprovação arquitetural existe.
- P-R1 F usa SUCCEEDED; D06 consolidada exige SUCCEEDED_VERIFIED. Não modificar
  os enums F02 nem equiparar um estado conceptual a resultado operacional.
- C-REG DEV-08B e C-AUTH conservam referências a 31 fontes/divergências.
  E-08D documenta a aplicação e E-ATTEST a baseline posterior 52/52; a adenda
  acrescenta precedência temporal sem apagar estados anteriores.
- C-08B distingue f066/b12 no MVP e f067 no AUTH-03 isolado. A implementação de
  perfis continua pendente: sem resolver automaticamente f066/f067.
- Originais AUTH-BOOT-02, F03/F04 e enumeração das 28 lacunas G4/L02 não são
  reconstruídos. Aprovar R1 substituta não demonstra equivalência histórica.
- DEV-09B continua dependente de autorizações próprias. Não aplicar o patch
  agregado DEV-09A.2 ou regenerar manifestos.

## 4. Auditoria futura deste candidato

Conferir cada linha com H-B/H-A, os contextos disponíveis e a localização
histórica indicada. Distinguir declaração humana, documentação, código,
ensaio offline e prova operacional. Todas as condições de aceitação permanecem
por demonstrar no percurso R1; nenhuma é satisfeita pela existência desta matriz.

Revisão documental futura: dez decisões sem perda de requisitos, parâmetros D02
e fórmulas D05 exatos, GAP-001/002 bloqueantes, confirmação independente D09,
continuidade D10, vinte lacunas abertas e contratos/gates intactos.
