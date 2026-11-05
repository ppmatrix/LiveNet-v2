# AUTH-BOOT-02-R1 — Registo de lacunas

**Estado: CANDIDATO DOCUMENTAL PARA REVISÃO HUMANA — todas as lacunas ABERTA.**

Revisão: R1-GAPS-CONSOLIDATION-B-CANDIDATE-1.
Fontes: CONSOLIDAÇÃO-A, relatório da sessão e pedido humano
`51c3491c-5df2-493e-94aa-73be4ba3a6dd/Pasted text.txt`;
CONSOLIDAÇÃO-B,
`a80a6b23-f866-404e-83e1-120d9b1fbf06/Pasted text.txt`, §§1 e 6.
Não são transcrições fictícias de contratos originais.

Ver [consolidado](auth-boot-02-r1.md) e [rastreabilidade](auth-boot-02-r1-traceability.md).
A aprovação arquitetural e a produção desta lista não resolvem qualquer entrada.
Severidades são a classificação documental aprovada para o registo inicial,
não um cálculo operacional de risco. Dependências não constituem autorização.

| Categoria | Significado |
| --- | --- |
| A | Bloqueadores de ativação. |
| B | Decisões técnicas pendentes antes da implementação correspondente; inclui proveniência documental. |
| C | Parâmetros operacionais pendentes. |
| D | Melhorias futuras não bloqueantes para a arquitetura inicial. |

Os 20 IDs são locais a R1. Não substituem, fundem ou renumeram as 28 lacunas
históricas G4/L02, a sua lista original não localizada, L02-R01–R07 ou outras
lacunas preexistentes. Não encerrar nenhuma pela mera existência deste documento.
Implementação, ensaios, infraestrutura e operação exigem autorização própria.

## R1-GAP-001

- **Estado:** ABERTA.
- **Categoria:** A.
- **Severidade:** CRÍTICA.
- **Decisões relacionadas:** D04/D08/D10.
- **Descrição:** Exclusividade durável da iniciação.
- **Impacto:** Segunda iniciação da mesma tentativa após concorrência, replay, crash ou clone.
- **Critério de resolução:** Protocolo e oráculo independente demonstram no máximo uma iniciação, incluindo reinício e snapshot.
- **Dependências:** R1-GAP-003, R1-GAP-005, R1-GAP-010.
- **Fase aplicável:** Antes de ativação.
- **Aprovação humana necessária:** Sim: mecanismo, ensaios e ativação separados.

## R1-GAP-002

- **Estado:** ABERTA.
- **Categoria:** A.
- **Severidade:** CRÍTICA.
- **Decisões relacionadas:** D05/D08.
- **Descrição:** Ordenação de revogação/expiração com o primeiro efeito PostgreSQL.
- **Impacto:** Operação começar inelegível após a última consulta ou despacho.
- **Critério de resolução:** Fronteira efetiva definida e prova perante pausas, espera por locks, atraso e partições; consulta pré-SQL não basta.
- **Dependências:** R1-GAP-001, R1-GAP-006, R1-GAP-014.
- **Fase aplicável:** Antes de ativação.
- **Aprovação humana necessária:** Sim: protocolo e qualquer alteração normativa; nenhuma janela residual implicitamente aceite.

## R1-GAP-003

- **Estado:** ABERTA.
- **Categoria:** A.
- **Severidade:** CRÍTICA.
- **Decisões relacionadas:** D04/D05/D09/D10.
- **Descrição:** Continuidade e proteção contra rollback.
- **Impacto:** Restauro omitir consumos/revogações ou reativar autorizações.
- **Critério de resolução:** Backup antigo confrontado com referência independente atual; transições relevantes reconstruídas ou âmbito bloqueado, sem reset de epochs.
- **Dependências:** R1-GAP-004, R1-GAP-007, R1-GAP-010, R1-GAP-012.
- **Fase aplicável:** Antes de ativação e de reentrada.
- **Aprovação humana necessária:** Sim: mecanismo e evidência independente.

## R1-GAP-004

- **Estado:** ABERTA.
- **Categoria:** A.
- **Severidade:** CRÍTICA.
- **Decisões relacionadas:** D09.
- **Descrição:** Evidência crítica e confirmação independente.
- **Impacto:** Novos efeitos sem preservação verificável fora do domínio afetado.
- **Critério de resolução:** Provar durabilidade, independência, cópia dos eventos críticos e bloqueio perante atraso/falha/divergência antes de liberar efeitos.
- **Dependências:** R1-GAP-012, R1-GAP-016, R1-GAP-017.
- **Fase aplicável:** Antes de ativação.
- **Aprovação humana necessária:** Sim: protocolo, domínios e evidência.

## R1-GAP-005

- **Estado:** ABERTA.
- **Categoria:** A.
- **Severidade:** CRÍTICA.
- **Decisões relacionadas:** D08.
- **Descrição:** Integração protegida ainda não implementada.
- **Impacto:** Abrir executores por referência, configuração ou alteração não revista.
- **Critério de resolução:** Propostas individualizadas, revisão de contratos/fontes/manifestos e autorização específica; gates atuais continuam fechados até lá.
- **Dependências:** R1-GAP-001, R1-GAP-002, R1-GAP-008, R1-GAP-018.
- **Fase aplicável:** Integração futura, fora da CONSOLIDAÇÃO-B.
- **Aprovação humana necessária:** Sim: cada alteração protegida e ativação.

## R1-GAP-006

- **Estado:** ABERTA.
- **Categoria:** A.
- **Severidade:** ALTA.
- **Decisões relacionadas:** D03/D08.
- **Descrição:** Identidade, transporte, privilégios e observações reais.
- **Impacto:** Alvo errado, excesso de privilégios ou evidência sintética promovida a real.
- **Critério de resolução:** Validação autorizada de TLS/identidades, destino/geração, sessão/ligação, privilégios e evidência real, sem fallback.
- **Dependências:** R1-GAP-008, R1-GAP-011, R1-GAP-015.
- **Fase aplicável:** Antes de ativação.
- **Aprovação humana necessária:** Sim: ambiente, acesso, grants e validações reais.

## R1-GAP-007

- **Estado:** ABERTA.
- **Categoria:** A.
- **Severidade:** CRÍTICA.
- **Decisões relacionadas:** D06/D10.
- **Descrição:** Recuperação e reentrada independentes não demonstradas.
- **Impacto:** Perda de confiança, recuperação incompleta ou repetição de tentativa incerta.
- **Critério de resolução:** Ensaio independente de continuidade, confiança, instâncias antigas e resultados incertos; reentrada humana auditada.
- **Dependências:** R1-GAP-003, R1-GAP-004, R1-GAP-016, R1-GAP-017.
- **Fase aplicável:** Antes de ativação/reentrada.
- **Aprovação humana necessária:** Sim: ensaios, recuperação e reentrada.

## R1-GAP-008

- **Estado:** ABERTA.
- **Categoria:** B.
- **Severidade:** ALTA.
- **Decisões relacionadas:** D02/D08.
- **Descrição:** Schemas de destino/plano/digest global e relação com AUTH-03.
- **Impacto:** Binding incompleto ou ambiguidade dos bytes autorizados.
- **Critério de resolução:** Codificação fechada, relações entre digests e vetores aprovados, sem presumir schema histórico F03/F04.
- **Dependências:** R1-GAP-009, R1-GAP-018.
- **Fase aplicável:** Antes da implementação do verificador/binding.
- **Aprovação humana necessária:** Sim: especificação técnica.

## R1-GAP-009

- **Estado:** ABERTA.
- **Categoria:** B.
- **Severidade:** ALTA.
- **Decisões relacionadas:** D02.
- **Descrição:** Schema integral e interoperabilidade criptográfica.
- **Impacto:** Parsers divergirem ou formatos candidatos serem promovidos sem decisão.
- **Critério de resolução:** Tipos/limites individuais, regras de parsing/contagem e vetores independentes aprovados, preservando os 25 campos e parâmetros fixados.
- **Dependências:** R1-GAP-008.
- **Fase aplicável:** Antes da implementação do protocolo.
- **Aprovação humana necessária:** Sim: detalhes ainda candidatos, sem alterar o protocolo aprovado.

## R1-GAP-010

- **Estado:** ABERTA.
- **Categoria:** B.
- **Severidade:** ALTA.
- **Decisões relacionadas:** D04.
- **Descrição:** Persistência, localização, isolamento e interfaces de estado.
- **Impacto:** Ausência de unicidade, durabilidade ou separação administrativa.
- **Critério de resolução:** Escolha fundamentada, transições condicionais, ordenação concorrente e recuperação especificadas; produto não selecionado nesta fase.
- **Dependências:** R1-GAP-011, R1-GAP-012.
- **Fase aplicável:** Antes da implementação do estado autoritativo.
- **Aprovação humana necessária:** Sim: arquitetura técnica e tecnologia.

## R1-GAP-011

- **Estado:** ABERTA.
- **Categoria:** B.
- **Severidade:** ALTA.
- **Decisões relacionadas:** D01/D03/D07.
- **Descrição:** Gestão/distribuição da confiança e ciclo de chaves/certificados.
- **Impacto:** Autoconfiança, uso indevido ou recuperação com credencial antiga.
- **Critério de resolução:** Protocolos/cerimónias de geração, ativação, distribuição, corte, revogação, custódia e recuperação revistos.
- **Dependências:** R1-GAP-014, R1-GAP-015, R1-GAP-017.
- **Fase aplicável:** Antes da implementação da confiança/custódia.
- **Aprovação humana necessária:** Sim: mecanismos, custódia e escolhas tecnológicas.

## R1-GAP-012

- **Estado:** ABERTA.
- **Categoria:** B.
- **Severidade:** ALTA.
- **Decisões relacionadas:** D09/D10.
- **Descrição:** Protocolo/schema de auditoria e reconstrução.
- **Impacto:** Eventos incompletos ou recibos interpretados como prova de efeito.
- **Critério de resolução:** Definir correlação, sequências, causalidade, completude, recibos, cópias e posições recuperáveis; provas independentes.
- **Dependências:** R1-GAP-010, R1-GAP-016, R1-GAP-017.
- **Fase aplicável:** Antes da implementação da auditoria/recuperação.
- **Aprovação humana necessária:** Sim: especificação técnica.

## R1-GAP-013

- **Estado:** ABERTA.
- **Categoria:** B.
- **Severidade:** MÉDIA.
- **Decisões relacionadas:** D01–D10.
- **Descrição:** Proveniência documental reprodutível das aprovações.
- **Impacto:** Atribuição de datas, textos ou aprovação de bytes não demonstrados.
- **Critério de resolução:** Fontes, excertos/alcances e limitações ligados a cada decisão; validação humana da consolidação; não fabricar originais.
- **Dependências:** H-A/H-B e contextos disponíveis; matriz de rastreabilidade.
- **Fase aplicável:** Formalização e revisão da CONSOLIDAÇÃO-B.
- **Aprovação humana necessária:** Sim: revisão dos bytes; mantém-se aberta nesta entrega.

## R1-GAP-014

- **Estado:** ABERTA.
- **Categoria:** C.
- **Severidade:** ALTA.
- **Decisões relacionadas:** D05.
- **Descrição:** Fonte temporal e limites de incerteza/holdover.
- **Impacto:** Elegibilidade temporal não demonstrável.
- **Critério de resolução:** Fonte, parâmetros e deteção de saltos/recuos medidos e aprovados, sem grace period.
- **Dependências:** R1-GAP-011, R1-GAP-015.
- **Fase aplicável:** Antes de operação.
- **Aprovação humana necessária:** Sim: parâmetros e procedimento temporal.

## R1-GAP-015

- **Estado:** ABERTA.
- **Categoria:** C.
- **Severidade:** ALTA.
- **Decisões relacionadas:** D03/D10.
- **Descrição:** Rede, endpoints, CA e identidades reais.
- **Impacto:** Exposição indevida ou pares autenticados incorretos.
- **Critério de resolução:** Configuração concreta e prova LAN-only, TLS 1.3/mTLS, identidades/CA e acessos administrativos aprovados.
- **Dependências:** DEV-05A-D01, R1-GAP-011, R1-GAP-017.
- **Fase aplicável:** Preparação operacional autorizada.
- **Aprovação humana necessária:** Sim: infraestrutura e parâmetros concretos.

## R1-GAP-016

- **Estado:** ABERTA.
- **Categoria:** C.
- **Severidade:** ALTA.
- **Decisões relacionadas:** D09/D10.
- **Descrição:** Retenção, capacidade, RPO/RTO e periodicidade de ensaios.
- **Impacto:** Perda de evidência/continuidade ou indisponibilidade não planeada.
- **Critério de resolução:** Política fundamentada e ensaiável para logs, estado anti-replay, backups/testemunhos e recuperação; sem prazos inventados.
- **Dependências:** R1-GAP-012, R1-GAP-017.
- **Fase aplicável:** Antes de operação.
- **Aprovação humana necessária:** Sim: valores, custos, retenção e ensaios.

## R1-GAP-017

- **Estado:** ABERTA.
- **Categoria:** C.
- **Severidade:** ALTA.
- **Decisões relacionadas:** D01/D07/D10.
- **Descrição:** Custódios, responsabilidades e recuperação administrativa.
- **Impacto:** Concentração de poderes ou dependência do único administrador.
- **Critério de resolução:** Pessoas, poderes, canais e domínios definidos; recomendação de duas pessoas avaliada sem presumir equipa.
- **Dependências:** R1-GAP-011, R1-GAP-015, R1-GAP-016.
- **Fase aplicável:** Antes de operação.
- **Aprovação humana necessária:** Sim: responsabilidades e procedimentos.

## R1-GAP-018

- **Estado:** ABERTA.
- **Categoria:** B.
- **Severidade:** ALTA.
- **Decisões relacionadas:** D02/D08; contratos históricos relacionados.
- **Descrição:** Contratos históricos ausentes e compatibilidade F03/F04/G4.
- **Impacto:** Equivalência fictícia ou integração que contorne contratos preservados.
- **Critério de resolução:** Manter SOURCE_NOT_LOCATED; documentar relações novas e respetiva aprovação sem fabricar originais. R1 substituta pode ser consolidada sem declarar recuperação histórica.
- **Dependências:** Registo G4/L02, R1-GAP-008, R1-GAP-005.
- **Fase aplicável:** Antes da integração que dependa dessas relações.
- **Aprovação humana necessária:** Sim: qualquer substituição ou alteração contratual; não encerra as lacunas históricas.

## R1-GAP-019

- **Estado:** ABERTA.
- **Categoria:** D.
- **Severidade:** FUTURA.
- **Decisões relacionadas:** D10.
- **Descrição:** HA/failover e distribuição adicional.
- **Impacto:** Complexidade, split-brain e domínio de falha partilhado se introduzidos sem prova.
- **Critério de resolução:** Necessidade demonstrada e nova decisão sobre coordenação, fencing e recuperação; não requerida para a instância única inicial.
- **Dependências:** R1-GAP-001, R1-GAP-003, R1-GAP-007.
- **Fase aplicável:** Melhoria futura, sem ativação implícita.
- **Aprovação humana necessária:** Sim: nova arquitetura e operação.

## R1-GAP-020

- **Estado:** ABERTA.
- **Categoria:** D.
- **Severidade:** FUTURA.
- **Decisões relacionadas:** D06/D09.
- **Descrição:** SIEM e automação ampliada de diagnóstico.
- **Impacto:** Consumidor de logs assumir autoridade ou diagnóstico iniciar reparação.
- **Critério de resolução:** Integração consumidora, minimizada e read-only quando autorizada; sem reexecução, decisão técnica fictícia ou alteração do estado autoritativo.
- **Dependências:** R1-GAP-012 e política de acessos.
- **Fase aplicável:** Melhoria futura.
- **Aprovação humana necessária:** Sim: integração e diagnóstico automatizado específicos.

## Condição de fecho e preservação

Fecho futuro exige evidência identificável, cumprimento do critério, revisão
humana e atualização documental autorizada. Não há fecho automático por teste
verde, assinatura válida, escolha de produto ou decisão arquitetural.

R1-GAP-001 e R1-GAP-002 permanecem expressamente **BLOQUEADORES DE ATIVAÇÃO**.
Resolver uma especificação B não demonstra automaticamente a garantia A.
As dependências podem exigir revisão conjunta; não são uma ordem operacional
executável nem resolvem ciclos por pressuposto.

Nenhum teste, build, serviço, SQL ou restauro foi executado para esta entrega.
AUTH-03, F02, G2 e G4 permanecem fechados. DEV-09B não está autorizada.
