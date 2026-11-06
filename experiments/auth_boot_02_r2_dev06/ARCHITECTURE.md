# Fronteira externa de efeito — candidata R2-DEV-06

Estado: proposta técnica para revisão; nenhuma escolha de produto ou alteração
contratual aprovada. Ler com [REPORT](REPORT.md) e [VALIDATION](VALIDATION.md).

## 1. Efeito, recurso e domínio de cópia

Um efeito protegido é a mutação física da operação aprovada num recurso
identificado, incluindo commit posterior de trabalho iniciado anteriormente.
Início, consumo e efeito são observações distintas. O domínio inclui os ramos
clonados que possam executar a operação; o efeito DEV-05 no clone conta como
contraexemplo, mesmo sem tráfego de clientes ou publicação do resultado.

Designa-se por D o conjunto de estados que o adversário pode copiar/restaurar:
discos e WAL PostgreSQL, roles, certificados exportáveis, memória, sessões,
estado do executor, controlador e vTPM quando incluído no snapshot. Nomes,
`system_identifier`, `vm_generation_id`, PID e certificados copiados não distinguem
de forma suficiente duas encarnações. Um endpoint fixado identifica uma ligação
aceite, mas não impede uma ligação antiga noutra cópia.

Uma fronteira externa B tem de mediar cada caminho capaz de produzir efeito e
conservar fora de D o poder de autorizar/revogar a escrita. A sua identidade e
estado de continuidade não podem ser reassociados ou revertidos pelo administrador
de D. Separar portas, bases ou VMs no mesmo administrador de hipervisor não
estabelece esta propriedade. B inclui o atuador efetivo, não apenas o broker que
lhe pede para atuar.

Inventário necessário para provar cobertura: recursos primários, réplicas com
capacidade de promoção, backups restauráveis, volumes locais, discos partilhados,
snapshots de VM/memória, SQL privilegiado, replicação, jobs, triggers, funções,
extensões, prepared transactions/2PC, workers e destinos externos. No primeiro
laboratório futuro propõe-se apenas UPDATE fixo; tudo o resto deve ser desativado
de modo verificável ou tratado como caminho pendente. Não se estende a Alembic,
DDL ou administração por inferência.

Limite fundamental: dois ramos isolados com cópia completa de dados, credenciais
e controlo local podem executar autonomamente o mesmo UPDATE. Uma autoridade
externa pode negar novas admissões conformes; não pode apagar o poder de um
administrador escrever numa cópia independente. Para o critério forte ser viável,
é preciso impedir que essa cópia gravável exista no domínio adversarial ou atuar
efetivamente em cada meio de escrita. Um inventário incompleto impede a prova.

## 2. Modelo de ameaça e confiança

| Ator ou falha | Poder considerado | Garantia condicionada / limite |
| --- | --- | --- |
| Executor antigo/clonado | Preserva memória, sessão, credenciais antigas; ignora cooperação; tenta replay, SQL e reconexão | B tem de negar os efeitos após o corte, mesmo com processo vivo |
| Administrador de aplicação/VM clonável | Restaura disco/memória, muda relógio/DNS/roteamento, possui root/superuser nesse domínio | Só é coberto se não puder administrar B nem obter outro meio gravável do recurso protegido |
| Rede adversarial | Particiona, atrasa, duplica e perde respostas; reconecta sessões | Não pode forjar as identidades de B; incerteza bloqueia novas admissões/takeover |
| Armazenamento e controlador | Crash, resposta perdida, cache, restauro antigo ou comandos pendentes | Exigir persistência do fence, drenagem/aborto e continuidade verificável; não inferir da resposta de API |
| Custódios de B, confiança e persistência externa | Administram identidade, fence e estado único | São parte da base confiada; compromisso conivente permite violar a garantia |
| Custódio D09 e revisor | Confirmam conteúdo crítico e continuidade fora dos outros domínios | Devem ter acesso/identidade próprios; assinatura do executor não os substitui |
| Administrador global | Controla B, dados, chaves, auditoria e cópias | Fora da garantia candidata; nenhuma assinatura ou epoch recupera independência nesse cenário |

O desenho não tolera comportamento bizantino arbitrário da base confiada.
Dividir funções e exigir revisão humana reduz risco; não prova honestidade de
todos os custódios. Uma futura tolerância a compromisso de B exigiria outro
modelo e aprovação, sem introduzir consenso/HA silenciosamente.

## 3. Alternativas concretas

| Alternativa | Fronteira efetiva | Partição e confirmação perdida | Clone integral, rollback e administrador | Custo/disponibilidade e avaliação |
| --- | --- | --- | --- | --- |
| Broker/proxy obrigatório de SQL, mTLS, sem login direto | Todas as ligações ao recurso passam por um serviço externo; só esse serviço possui escrita | Perda antes de confirmação bloqueia; uma ligação SQL antiga que sobreviva ao proxy pode ainda confirmar | Superuser/socket local/replicação ou cópia com credenciais contorna o proxy; mTLS não cancela sessão existente | Custo moderado e dependência do proxy; necessário como controlo, insuficiente isoladamente |
| Fence transacional no próprio PostgreSQL, função restrita e epoch ligado ao principal | Verificação e exclusão duram até commit no mesmo recurso | Pode drenar indefinidamente; corte só confirma depois do commit/aborto antigo | DEV-05 demonstra proteção local e falha perante clone e superuser; ledger/fence restaurados regressam | Custo baixo/moderado; componente local útil, sem prova distribuída |
| Storage externo com reservas persistentes SCSI e preempção/aborto | O dispositivo recusa escrita de iniciadores antigos em todos os caminhos | Só confirmar com leitura autenticada do estado e comandos antigos terminados; incerteza bloqueia promoção | Exige controlar registo/re-registo e identidades dos iniciadores; chaves copiadas não bastam; clone em outro disco contorna | Custo elevado de storage/fabric e ensaio; candidata quando todos os dados persistentes dependem desse meio [S1] |
| Isolamento físico por BMC/PDU, com bloqueio de rearranque | Retira energia/capacidade de execução dos hosts inventariados por canal externo | Falha do canal ou estado incerto impede takeover; timeout não prova off | Desligar uma VM/host não desliga cópia noutro host; administrador de BMC/hipervisor ou cópia desconhecida invalida cobertura | Custo elevado, indisponibilidade e inventário rigoroso; complemento para recursos conhecidos [S2] |
| Isolamento lógico por SAN/fabric e rede de gestão separada | Revoga acesso a todos os volumes/canais de efeito, incluindo ligações existentes | ACL aplicada só a novas conexões é insuficiente; aguardar/abortar I/O já aceite | Não bloqueia disco local nem rota alternativa; rollback do controlador pode reabrir caminho | Custo moderado/elevado; aceitável só com cobertura e persistência demonstradas [S2] |
| Identidade em TPM físico/HSM não exportável, enrolamento externo e desafios | Dificulta copiar a capacidade de autenticar como um recurso | Sem serviço de validação/frescura, bloquear; assinatura antiga não é corte | Dispositivo original pode continuar a assinar, acesso remoto pode ser retransmitido e vTPM pode integrar D; identidade não controla SQL | Custo de hardware, custódia e recuperação; defesa complementar, nunca prova de cessação [S3] |
| Lease/token com epoch externo sem imposição no recurso | Somente clientes cooperantes verificam validade | Suspensão/atraso entre verificação e efeito reabre DEV-04; lease depende de limites temporais demonstrados | Clone com token ou administrador ignora verificação; cópia da autoridade restaura permissões | Custo baixo; rejeitada como solução suficiente |

As reservas de storage têm tipos que permitem vários registados; não selecionar
um modo apenas pelo nome. A candidata exige exclusão efetiva dos antigos,
prevenção de re-registo, persistência e cobertura multipath. São requisitos de
validação do produto/configuração, não capacidades demonstradas neste repositório.
Mesmo storage perfeitamente isolado não impede escrita num volume independente.

Identidade não clonável significa, nesta proposta, uma capacidade cuja duplicação
para D não permite autenticar nova instância perante B: chave fora de D,
enrolamento aprovado, desafio fresco e vinculação ao recurso/canal. A chave sozinha
não distingue dois processos no mesmo hardware. Atestação mede propriedades num
instante; não prova execução futura honesta nem cessação de todos os processos.
Algoritmo de identidade/atestação não substitui Ed25519 puro das aprovações R1/R2.

## 4. Arquitetura candidata condicionada

Propõe-se separar quatro responsabilidades: autoridade A de admissão/ordem;
serviço B de dados e imposição de escrita; controlador F do atuador persistente;
testemunha W/D09 e verificador V independentes. B/F e seus dados não pertencem ao
snapshot do executor e não são administrados pelo seu custódio. A inicialmente
continua única, sem eleição, HA ou failover automático. W não autoriza SQL.

```text
Executor clonável -> A: admissão exclusiva, vínculos e consumo duráveis
                 -> B: operação fixa, sessão/transação vinculadas
V/F externo      -> B/storage: corte persistente e drenagem/aborto
A, B, F          -> W/D09: conteúdo crítico e continuidade confirmados
V                -> operador: atestado limitado e decisão de reentrada pendente
```

B rejeita instruções arbitrárias e poderes administrativos do executor, mantém
fence até ao término da transação e depende de armazenamento/atuador fora de D.
A reserva de iniciação é durável fora da transação de efeito, para rollback ou
savepoint não libertarem a aprovação. Chamada direta à função por um principal
autorizado também tem de exigir essa reserva, corrigindo a dependência do broker
demonstrada em DEV-05. O protocolo concreto para vincular reserva e sessão ainda
carece de especificação; uma reserva externa não torna o UPDATE atómico com A.

Mover o PostgreSQL protegido para B reduz o conjunto clonável, mas altera uma
premissa de implantação e necessita de aprovação. Se houver cópia gravável de B
fora do seu controlo, a candidata volta ao contraexemplo. Não satisfaz o requisito
universal de qualquer cópia física arbitrária; não se aprova essa restrição aqui.

### Sequência proposta para contenção e takeover

1. V verifica continuidade de A/B/F/W, identidades e inventário fechado de
   recursos; cria desafio fresco para um pedido de contenção identificado.
2. A bloqueia novas admissões no âmbito e regista duravelmente a intenção de
   corte, sem apagar admissões, consumos ou revogações. Não se declara cancelada
   retroativamente uma tentativa já admitida por C3.
3. F impõe no recurso/storage a retirada persistente das capacidades antigas,
   incluindo sessões, conexões e caminhos alternativos. O corte lógico local
   pode drenar ou abortar conforme política explicitamente aprovada. Todos os
   efeitos antigos já confirmados continuam parte do resultado a reconciliar.
4. Para cada recurso, F/B demonstram que I/O/transações antigos terminaram antes
   do ponto de corte T e que capacidades antigas não voltam a escrever, mesmo
   após reinício. Epoch novo só é publicado como eficaz após esse estado durável.
   Durante transição, estados parciais são bloqueantes, nunca sucesso global.
5. W confirma o conteúdo crítico e a continuidade do corte; V confronta
   evidências autenticadas do atuador com inventário, desafio e ordem atual.
   Um comando aceite, ausência de heartbeat ou lista SQL vazia não basta.
6. V emite um atestado de alcance explícito. A guarda-o como evidência de
   contenção; não emite autorização de efeito. Reentrada exige reconciliação,
   decisão humana autenticada/auditada, novo pedido e nova aprovação; não retoma
   admissão antiga nem transfere a tentativa para sessão nova.

Se um recurso estiver inacessível mas o seu meio de escrita puder ser cortado
externamente com prova, o corte pode ser comprovado sem cooperação do host.
Se nem isso for verificável, V não confirma. O percurso novo fica bloqueado; o
sistema procura conter o antigo, mas não afirma conseguir fazê-lo só por política.
Uma tentativa antiga continuamente vinculada e já confirmada pode continuar
segundo C5 até contenção efetiva; partição posterior não revoga a sua admissão.

## 5. Atestado de cessação: significado e obrigações

O termo proposto é cessação da capacidade de efeito no conjunto de recursos R.
Não equivale a provar morte do processo/host. Se o requisito exigir morte física,
é necessária prova própria do atuador e cobertura de todos os hosts/cópias; não
se infere isso do atestado de capacidade. A aceitação desse alcance é pendente.

Conteúdo conceptual necessário, sem definir nomes de campos, bytes ou schema R2:

| Vínculo | Evidência a exigir |
| --- | --- |
| Recurso | Identidade autenticada externa, geração de dados/storage, inventário e digest da política de cobertura; não apenas nome/IP/system_identifier |
| Encarnação antiga e nova | Principais e capacidades retiradas, identidade de arranque/enrolamento e associação verificável às sessões/transações; nova identidade não libera aprovação antiga |
| Epoch e ordem | Epoch anterior/novo, posição durável autoritativa e posição do corte no recurso; epochs de recurso e autoridade não são confundidos nem renomeiam campos existentes |
| Frescura | Desafio imprevisível de V para esta operação, resposta ligada ao canal e estado atual; consulta de continuidade e intervalo UTC com erro limitado; recibo em cache insuficiente |
| Cessação efetiva | Atuador, caminhos cortados, destino autenticado, drenagem/aborto e operações pendentes resolvidas; alcance e exclusões explícitos |
| Durabilidade | Referência ao registo persistente do fence, política que impede rollback/reabertura e confirmação independente de conteúdo crítico; fsync configurado não prova hardware |
| Proveniência | Identidades distintas de quem pediu, atuou, observou e verificou; chaves/políticas válidas e referências D09; assinatura atribui declaração, não torna a declaração verdadeira |
| Limites | Resultado incerto, recursos não cobertos e validade perante mudança de topologia; qualquer lacuna relevante proíbe confirmação distribuída |

Frescura não é um TTL que permita retoma. Um nonce evita aceitar resposta antiga
para um pedido novo, mas não assegura que o fence continue aplicado; V consulta
estado atual e continuidade e B mantém a exclusão persistentemente. Alterar
topologia, reativar caminho ou perder continuidade invalida a utilização futura
do atestado. A autorização operacional continua a exigir os restantes gates.

### Argumento de segurança condicionado

Premissas P1–P5: cada efeito passa por B; identidade/capacidade de B não é
duplicável por D; B/F ordenam corte e efeitos com exclusão até commit/I/O terminal;
o estado persistente não regride nem permite reativar capacidade antiga; V/W são
autenticados, independentes e verificam inventário completo e continuidade.

Para um efeito antigo posterior a T existir, ou atravessou B depois de retirado o
poder, contradizendo P3/P4, ou usou outro caminho/recurso, contradizendo P1/P2.
Uma operação antiga aceite antes de T tem de estar terminada/abortada antes de
confirmar T; se continuar pendente, T não pode ser confirmado. Essa é a obrigação
que fecha a janela DEV-04. DEV-05 satisfaz parte de P3 num recurso, mas refuta
P1/P2 para o clone. As premissas não estão demonstradas; este argumento não é
prova empírica nem permite confirmar takeover hoje.

Não há atomicidade global: A pode consumir sem efeito; B pode confirmar sem
resposta ao cliente; W pode ficar atrasada. Qualquer intervalo ambíguo conserva
consumo e bloqueio. Nenhum estado observado read-only concede retoma.

## 6. Compatibilidade C1–C7

| Cláusula | Preservação na proposta e pendência |
| --- | --- |
| C1 | A decide e confirma duravelmente consumo/vínculos/ordem/evidência; B não inventa admissão; independência de A e ausência de atomicidade com B mantidas |
| C2 | UTC confiável em A: issued_at <= not_before < expires_at, duração <=900 s, L>=not_before e U<expires_at; prazo não se desloca para commit/efeito |
| C3 | Revogação ordenada antes de A recusa; posterior não cancela admissão; contenção é medida adicional, sem prometer desfazer efeitos |
| C4 | Uma tentativa imutável; reserva externa não libertada por rollback; cobertura de SQL e clones continua obrigação pendente |
| C5 | UNKNOWN/BLOCKED sem despacho automático antes de confirmação; consulta não retoma; partição posterior não revoga tentativa original continuamente vinculada |
| C6 | W/D09 antes de percurso executável, recuperação preserva histórico e invalida capacidades; incremento de epoch sozinho não prova continuidade |
| C7 | Sem alterar 25 campos, parsers, assinaturas ou domínio R1; perfil R2 e atestado precisam de schemas/codificação e aprovação próprios |

## 7. Fundamentação externa

As conclusões específicas LiveNet são inferências dos relatórios/evidências
locais, não garantias dos produtos abaixo. Fontes primárias consultadas em
2026-10-27; produtos/configurações não foram instalados nem avaliados.

- S1: [Linux kernel — Persistent Reservations](https://docs.kernel.org/block/pr.html).
  Documenta restrição por iniciador, tipos, persistência/multipath esperados e
  preempção com aborto. A cobertura de clones independentes é análise deste estudo.
- S2: [ClusterLabs — Pacemaker fencing, §§8.1–8.3](https://clusterlabs.org/projects/pacemaker/doc/3.0/Pacemaker_Explained/html/fencing.html).
  Descreve corte de energia/fabric e dependências externas ao nó/rede afetados.
  Não se adota Pacemaker nem os seus retries como política LiveNet.
- S3: [tpm2-tools — tpm2_create](https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_create.1/).
  Expõe atributos fixedTPM/fixedParent e políticas de criação; não demonstra
  não clonabilidade da infraestrutura LiveNet, do vTPM ou cessação de processos.
