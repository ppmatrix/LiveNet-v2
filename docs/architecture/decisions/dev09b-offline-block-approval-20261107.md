# DEV09B-1 — aprovação da codificação e do primeiro bloco offline

07/11/2026 · Europe/Lisbon

## Decisão e fonte

Fonte primária: pedido humano expresso nesta conversa: «Implementar o primeiro
bloco offline DEV09B agora aprovado pelo utilizador». A base aprovada é a proposta
consolidada DEV09B-1 apresentada no chat imediatamente antes desse pedido, com
as quatro correções vinculativas reproduzidas abaixo. Este ato regista a decisão;
não atribui aprovação antecipada aos bytes de uma implementação ainda por rever.

O [ato de desenho](dev09b-migration-design-approval-20261107.md) mantém-se intacto.
As suas menções à codificação candidata descrevem o estado anterior, resolvido
por esta aprovação apenas no âmbito delimitado deste ato.

## Correções vinculativas

1. AVAILABLE não é terminal; CONSUMED, REVOKED e EXPIRED são terminais.
2. Camadas sem schemas completos permanecem explicitamente não suportadas.
   Hash coincidente não torna um documento opaco aceitável.
3. Continuidade exige indicação por interface independente. Epoch na mesma base
   restaurável não comprova continuidade; ausência/incerteza bloqueia consumo e
   progressão.
4. Se consumos/revogações anteriores não puderem ser integralmente reconciliados,
   as aprovações dessa continuidade ficam inutilizáveis, incluindo as ausentes
   dos registos restaurados.

Indisponibilidade da autoridade não impede tentar rollback/fechar a ligação.
Sem confirmação independente, o resultado mantém-se incerto. Aprovações não
voltam a AVAILABLE e não existe retry ou retoma automática.

## Codificação aprovada para este bloco

- Perfil literal `DEV09B-1`; envelope fechado `payload`/`signature_hex`, 25 campos
  definidos no contrato apresentado no chat; sem compatibilidade R1/R2/G4.
- Ed25519 puro sobre `ASCII("LiveNet/DEV09B/approval/v1") || NUL || UTF8(JCS(payload))`.
  Assinatura lowercase de 128 caracteres, payload até 16 KiB, envelope até 32 KiB,
  profundidade máxima 8; sem fallback criptográfico.
- JSON UTF-8, JCS no domínio restrito aprovado, inteiros seguros sem floats,
  sem normalização Unicode implícita, campos desconhecidos ou duplicados.
- Schemas fechados TargetBinding, ExecutorBinding e ExecutionPlan; digests
  SHA-256 com `ASCII("LiveNet/DEV09B-1/") || ASCII(tipo) || NUL || UTF8(JCS(objeto))`.
- Operações literais `application-base-to-f066a01a7230` e
  `security-base-to-b12b01a7230`; pedidos/aprovações/tentativas separados;
  confirmação independente de f066 antes de security. Verificar hashes não
  valida o conteúdo de uma evidência com schema incompleto.
- Checkpoints no consumo, antes do primeiro efeito e antes de COMMIT; validade
  máxima de 900 segundos e intervalo temporal confiável. Verificação anterior
  ao comando não garante elegibilidade no instante físico do efeito/commit.

## Implementação autorizada e limites

Autorizados envelope/validação, três schemas de binding/plano, canonicalização,
digests/verificação Ed25519, interfaces abstratas de autoridade/relógio/
continuidade/executor, máquina de estados e doubles exclusivamente offline,
testes locais pertinentes, este ato e atualização sucinta de CONTINUITY.md.

As camadas semantic/physical/provenance não têm schemas completos neste bloco:
a validação é explicitamente recusada. O digest do índice global apenas calcula
integridade; não confere suporte às camadas. SignatureObservation apenas observa
uma assinatura sob a chave fornecida; não comprova confiança, autorização ou
prontidão. Carregar uma fixture no double não é emitir uma aprovação real.

MemoryAuthority usa apenas memória e lock de threads para modelar consumo
concorrente num processo. Não demonstra persistência, concorrência PostgreSQL,
recuperação real, autenticidade da continuidade ou exclusividade operacional.
Reconciliation flags e amostras são evidência sintética. Nenhum double liga
signature observations, digests ou estados a permissões operacionais.

O modelo bloqueia perante perda da indicação independente de continuidade. Uma
reconciliação sintética incompleta exige indicação independente de nova
continuidade e inutiliza a geração anterior inteira; mudar epoch local sozinho
não desbloqueia o modelo. Este comportamento não implementa um serviço real de
continuidade, trust store, revogação ou recuperação.

Não autoriza serviço real de autoridade, PostgreSQL, rede, chaves operacionais,
Alembic/SQL, infraestrutura, adaptação de executores ou abertura de gates.
Não altera contratos anteriores, R1/R2/C4, I-04 ou lacunas históricas. Sem staging,
commits ou pushes. Progbox exclusivamente DEV; STAGING/PROD em VMs Proxmox;
LiveNet exclusivamente interno.

## Organização e verificação local

- [Módulo offline](../../../scripts/dedicated/dev09b/): codec/schemas,
  interfaces/modelo e doubles sem transporte ou emissão operacional.
- [Testes](../../../scripts/postgres/tests/test_dev09b_offline.py): parsing,
  vetores literais/JCS e Ed25519 RFC8032, adulteração/rejeição cruzada,
  tempo/revogação, consumo modelado concorrente, falhas, incerteza,
  contenção sem autoridade, continuidade e troca de sessão/transação/encarnação.
- `cryptography` disponível no Python do sistema (41.0.7), ausente no `.venv`.
  Sem instalações; a ausência provoca CryptoUnavailable, sem fallback. Os
  vetores criptográficos são executados no interpretador que tem a dependência;
  no venv esses dois testes ficam explicitamente ignorados.

Próxima dependência concreta: schemas completos das camadas/evidências para
validar um manifesto completo, sem aceitar hashes opacos como substituto. A
autoridade durável, continuidade independente e exclusividade reais permanecem
trabalho operacional separado, sem autorização por extensão deste bloco.
