# DEV09B — aprovação do desenho de autorização de migrações DEV

07/11/2026 · Europe/Lisbon

## Fonte e estatuto

Fonte: declaração humana expressa nesta conversa: «O utilizador aprovou as
quatro escolhas do desenho DEV09B», acompanhada das duas clarificações abaixo.
Este ato regista a aprovação desse desenho; não declara aprovados por extensão
os bytes deste registo ou uma codificação executável. A codificação exata
preparada posteriormente no chat continua candidata para revisão e autorização
de um bloco de implementação.

Direção aprovada: opção B, contrato específico de migrações DEV, preservando
AUTH-03/DEV08B/M1.2B, sem extensão automática de R1/R2/C4. DEV09B-R2-v1 não
foi aprovado.

## Operações abrangidas

- Application: base → `f066a01a7230`.
- Security: base → `b12b01a7230`, após confirmação independente de f066 e
  confirmação de que a cadeia security ainda está em base.
- Pedido, aprovação, consumo e tentativa separados por operação.
- Sem `head`, `stamp`, downgrade, f067/authorization ou autorização implícita
  de criação do alvo, provisionamento, grants, readiness ou ativação da aplicação.

## Quatro escolhas aprovadas

1. **Temporalidade por pontos de controlo.** Verificar assinatura, confiança,
   revogação e validade no consumo, imediatamente antes do primeiro comando
   com efeitos e imediatamente antes de enviar COMMIT. Validade máxima inicial
   de 900 segundos; intervalo confiável [L,U], com L ≥ not_before e U < expires_at.
   Expiração, revogação, autoridade indisponível ou perda de confiança temporal
   antes de enviar COMMIT impedem novos comandos com efeitos e desencadeiam
   tentativa de rollback. Os pontos de controlo não garantem elegibilidade no
   instante físico do efeito/commit nem cancelamento instantâneo de SQL iniciado.
   Rollback só é confirmado após confirmação transacional e inspeção independente;
   depois de COMMIT enviado sem resposta conclusiva, o resultado é incerto.
2. **Consumo durável e atómico.** Serviço de autorização segregado com PostgreSQL
   próprio, fora da base LiveNet, sem credenciais administrativas no executor.
   Uma transação serializa elegibilidade/revogação e consumo, vincula pedido,
   aprovação, tentativa, executor/encarnação, destino, operação e digests e
   confirma duravelmente antes de devolver recibo autenticado. Unicidade por
   aprovação impede consumidores concorrentes. Não há atomicidade presumida
   entre autoridade e alvo. Consumo sem execução permanece gasto; consulta de
   estado não autoriza retoma. Nova tentativa exige reconciliação, encerramento
   da anterior, novo pedido e nova aprovação, sem libertação/retry automáticos.
3. **Exclusividade administrativamente controlada.** Cluster DEV dedicado e janela
   supervisionada: excluir clientes escritores, sessões/transações preparadas e
   mecanismos externos de escrita; restringir novas ligações; migrator temporário
   com poderes mínimos; runtime sem administração/DDL. Uma ligação/transação
   externa vinculada à tentativa é entregue ao Alembic, sem reconexão, troca de
   ligação ou commits internos. Supervisão até verificação final e fecho dos
   poderes temporários; advisory lock isolado é insuficiente. Recusar escritor
   não explicado, exclusão incompleta, bindings divergentes, escape transacional,
   perda de supervisão ou fecho não verificável. Administração PostgreSQL,
   host/hipervisor/storage e controlo de credenciais/admissão podem contornar o
   mecanismo: pressupõe-se administração confiável sem intervenção concorrente.
   Não se declara resistência a administradores adversariais ou satisfação C4.
4. **Adaptação versionada do envelope.** Reutilizar payload/signature_hex,
   Ed25519 puro, JCS/UTF-8 e os 25 campos existentes onde compatíveis, com perfil
   DEV09B explicitamente distinguido e separação criptográfica entre perfis.
   Não reutilizar versão 1 como equivalência R1 nem versão 2 como adoção R2.
   Discriminador, codificação, schemas, bindings e digests concretos continuam
   candidatos; a implementação não os pode escolher silenciosamente.

## Duas clarificações humanas integrantes da aprovação

> Indisponibilidade da autoridade não impede tentar rollback ou fechar a ligação.
> Sem confirmação independente, o resultado mantém-se incerto.

> Restauro/perda de continuidade da autoridade não pode revalidar aprovações
> antigas; novas admissões ficam bloqueadas até reconciliação.

Rollback e fecho são contenção permitida pelo desenho mesmo sem autoridade;
não constituem prova de ausência de efeitos. Continuidade desconhecida da
autoridade bloqueia novas admissões; restaurar uma cópia ou incrementar um
contador não restitui aprovações nem demonstra continuidade.

## Fontes reutilizadas e substituição delimitada

- [DEV-08B](../../specifications/f0/dev08b-persistence-contracts.md): identidade,
  isolamento, perfis, revisões/ledgers e fronteiras de privilégios.
- [AUTH-03, autorização futura](../../specifications/f0/auth03-alembic-executor.md):
  autoridade externa, transação única, consumo e reconciliação.
- [M1.2B P2B-D01–D05](../../specifications/f0/m12b-p2c2b-operational-preparation.md):
  escritores externos, coordenação e recuperação independente.
- H-AUDIT, anexo histórico `deb81a29-e48f-4bb4-a3a1-db597653dc5a/Pasted text.txt`,
  §2; H-I2, `aedd3ea8-5de5-433c-a5c9-bbbd8c3427ff/Pasted text.txt`, §§2–3:
  requisitos de manifesto, confiança, validade/consumo e ficheiros F03/F04/F17.
  Localizadores fora do checkout; instruções históricas de auditoria não
  constituem autorização para executar essas auditorias agora.

O desenho delimita um contrato próprio para as duas operações; não recupera o
original AUTH-BOOT-02 nem aprova equivalência com G4-WF1/F03/F04. Uma futura
codificação DEV09B poderá substituir apenas as partes ausentes necessárias a
este perfil após aprovação própria. Os contratos gerais e lacunas históricas
continuam pendentes para os restantes percursos.

[R1](../auth-boot-02-r1.md), [R2](../auth-boot-02-r2.md), C4, I-04 e documentos
aprovados anteriores permanecem preservados. Não há extensão ou dispensa
implícita, demonstração de garantias, encerramento de lacunas ou abertura de
AUTH-03/F02/G2/G4.

## Autorização desta etapa e dependências futuras

Autorizados apenas este registo, atualização mínima de CONTINUITY.md e proposta
de contrato exato no chat. Desenho aprovado não é aprovação da codificação nem
autorização de implementação ou operação. Tecnologia/administração concretas,
confiança/chaves, fonte temporal, continuidade/recuperação da autoridade,
identidade do alvo, privilégios, supervisão e adaptação dos executores exigem
concretização/revisão antes da execução. Não criar chaves ou recursos por
consequência deste ato.

LiveNet exclusivamente interno; progbox exclusivamente DEV; STAGING/PROD em VMs
Proxmox. Sem código, testes, instalações, SQL, serviços, infraestrutura, staging,
commits ou pushes nesta etapa documental.
