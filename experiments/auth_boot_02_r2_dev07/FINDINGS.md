# R2-DEV-07 — análise adversarial e achados rastreáveis

Data editorial: 2026-10-27. Veredito e âmbito em [REPORT.md](REPORT.md).
Severidades: crítica = contradiz a garantia forte se o cenário for permitido;
alta = bloqueia demonstração/ensaio favorável; média = especificação ou cobertura
insuficiente que pode produzir falsa confiança. Nenhuma severidade é um CVSS ou
declaração de vulnerabilidade operacional nova.

## Fontes e interpretação

Referências `A:linha` e `V:linha` designam, respetivamente,
`../auth_boot_02_r2_dev06/ARCHITECTURE.md` e `VALIDATION.md`. `R2:Cn` designa
`../../docs/architecture/auth-boot-02-r2.md`, cláusula correspondente:
[contrato R2](../../docs/architecture/auth-boot-02-r2.md).

Os caminhos contratuais nesta revisão são relativos à raiz do repositório quando
escritos como `docs/...`; as referências de evidência DEV-n apontam para
`experiments/auth_boot_02_r2_devnn/evidence.json`. As chaves JSON abaixo são
localizadores exatos. Observações históricas não foram reproduzidas.

DEV-02/03/04 registam 36/37/63 testes; DEV-05 distingue 34 novos e dois DEV-04.
Todos os JSON finais conservam `executable=false` e UTC autenticado ausente.
DEV-04/05 conservam independência D09 não demonstrada. Passar testes que esperam
contraexemplos não demonstra segurança universal. Cópias DEV-02/03 são lógicas;
DEV-04/05 copiam dados físicos com o alvo parado e iniciam ramos depois. Não
constituem demonstração de snapshot de memória, VM ou hardware.

## Exame lógico de P1–P5

DEV-06 A:172–175 apresenta cinco premissas numa frase. A decomposição abaixo
é analítica; não acrescenta cláusulas ao contrato.

| Premissa | Teste adversarial e estatuto | Obrigação independente |
| --- | --- | --- |
| P1: cada efeito passa por B | Clone em disco independente, superuser, socket local, replicação, trigger, worker ou destino externo escapam. DEV-05 já refuta P1 para o domínio histórico integral; mover apenas o endpoint não corrige. | Inventário de meios, capacidades e percursos, incluindo backups e exportações; demonstrar mediação no ponto de efeito e controlo de criação de novos ramos. |
| P2: capacidade/identidade B não duplicável por D | Chave não exportável não impede usar o hardware original por relay, nem escrita local que dispense autenticação B. B/F/W copiados em conjunto podem responder coerentemente com histórico antigo. P2 isolada não implica P1. | Mapear D, administradores efetivos, enrolamento, raízes e recuperação; mostrar o mecanismo que impede obter o meio gravável, além da identidade. |
| P3: corte e efeitos ordenados até commit/I/O terminal | DEV-04 perde o lock externo e permite SQL/commit após fence. DEV-05 mostra exclusão transacional local, não em todos os meios. Um atuador que acusa receção com filas pendentes viola P3. | Transições e barreiras observáveis por recurso; operação antiga termina/aborta antes do corte eficaz, sem janela check–use; incluir commits em voo e 2PC ou provar exclusão destes. |
| P4: persistência não regride nem reabre | Restaurar ledger/fence/configuração ou re-registar iniciador reativa capacidade. Um recibo histórico autêntico permanece autêntico após rollback. Reinício WAL no mesmo host não cobre perda de energia/storage. | Âncora de continuidade fora de todos os backups adversariais; recuperação sem perda de consumos/ordem; arranque em quarentena quando a continuidade for desconhecida; poderes de reabertura segregados. |
| P5: V/W autenticados e independentes verificam inventário/continuidade | W arquiva declaração F; V lê W e conclui que F atuou: círculo probatório. Um inventário assinado pelo controlador não prova inexistência de outra cópia. | Separar quem determina a cobertura, impõe o corte, observa o efeito e conserva evidência; explicitar a base confiada e a origem independente de cada observação. |

Com P1–P4 efetivamente verdadeiras, um efeito antigo depois de um corte terminal
contradiz as premissas. Esse raciocínio é válido, mas P3 já exige ausência de
trabalho antigo capaz de confirmar após o corte, e P4 exige que a exclusão dure.
Substituir a demonstração dessas propriedades pela palavra «efetivo» seria
circular. P5 é necessária à justificação da confiança no atestado, não cria
fisicamente a exclusão que P3/P4 exigem.

Para vários recursos, definir cortes locais T_i e uma confirmação global que só
se emite depois de todos os cortes duráveis, com exclusão contínua desde cada
T_i. Não é necessário inventar um relógio global: uma barreira causal pode ordenar
a confirmação depois das terminações. Se um primeiro recurso reabrir enquanto o
último é cortado, observar cada um isoladamente não prova um intervalo global
seguro. Nenhum estado parcial permite takeover. Isso não exige nem presume
atomicidade distribuída entre A, B e W.

## Matriz de achados

| ID / severidade | Evidência rastreável | Consequência e contraexemplo | Mitigação / decisão pendente |
| --- | --- | --- | --- |
| F01 / crítica | A:36–41,109–112; DEV-05 `measurements.clone_survives_local_cessation_counterexample` e `historical_snapshot_counterexample`; R2:C4/C6 | Cópia integral gravável permite efeito depois do fence original e repetição em ramo histórico. Restringir o efeito ao endpoint oficial falsearia o critério adotado em DEV-06. | Decidir se é possível impedir essas cópias por mecanismo verificável. Se continuarem permitidas, declarar inviável a garantia forte; nenhuma aceitação por renomear o domínio. |
| F02 / alta | A:45–58; V:58–64; DEV-03 `measurements.administrative_segregation`; DEV-05 REPORT:59–65 | Domínios A/B/F/W/V/CA/backup sem pessoas e poderes concretos. Admin global pode reabrir escrita, trocar confiança e reescrever testemunhos. Duas contas ou VMs não estabelecem independência. | Matriz nominal de poderes diretos e transitivos, recuperação e emergência; declarar explicitamente confiança/conivência toleradas e excluídas. Aprovação humana do modelo; sem alegar tolerância bizantina. |
| F03 / alta | A:101–107; DEV-05 `measurements.external_consumption_still_trusted_broker` = claims 0, value 1; DEV-04 `measurements.privileged_bypass`; R2:C1/C4/C5 | Fence local não exige consumo externo. Uma função direta autorizada pode executar sem admissão, ou reaproveitar reserva como bearer token. Não há atomicidade presumida que feche esta janela. | Especificar a verificação obrigatória no ponto de efeito, consumo não libertável e ligação imutável à sessão/transação/encarnação. Estados de crash/ack perdido bloqueantes; proibir migração ou recriação de permissão por consulta. |
| F04 / alta | A:121–131,172–183; DEV-04 `measurements.counterexample_guard_loss_sql_begins_after_fence` e `counterexample_guard_loss_old_commit_after_fence`; V02/V05 | Corte antes do fim do commit/I/O aceita efeito antigo após confirmação. Prepared statement não equivale a prepared transaction. Locks numa autoridade externa podem desaparecer sem parar o alvo. | Selecionar atuador e definir pontos de linearização, drain/abort, filas/cache/2PC e prova terminal por recurso; vedar confirmação enquanto houver trabalho antigo capaz de efeito. |
| F05 / alta | A:157–168; V04/V08/V09; DEV-02 `measurements.split_brain_counterexample`; DEV-05 `measurements.historical_snapshot_counterexample` | B, F e ledger restaurados em conjunto podem concordar num estado obsoleto. Nonce fresco assinado pelo estado antigo não prova continuidade atual; restauração de ACL ou re-enrolamento pode reabrir escrita. | Raiz externa de continuidade identificada com política de recuperação, retenção e troca de administradores; invalidar capacidades antigas inclusive depois de recovery/re-registo. Se a raiz também puder ser copiada, F01 reaparece. |
| F06 / alta | V:13–24; DEV-05 `measurements.admin_bypass_counterexample` = value 1, effects [], claims 0 | Contar só ledger de efeitos/consumos produz falso zero. Ler payload na mesma base administrada por quem impõe o corte não garante independência. Um UPDATE que reponha o valor pode ocultar efeito transitório. | Observar payload e resultados terminais além de ledgers, com trilho de mutações/captura independente para a fixture; validar o oráculo por bypass e efeito apagado/compensado. Definir completude e acessos, não apenas «read-only». |
| F07 / alta | A:129–131; V13; R2:C6; R1 §11 D09 | W pode guardar apenas hashes ou a afirmação de F sem observar atuação. Exigir confirmação antecipada do resultado futuro cria ciclo impossível; dispensar a confirmação da admissão viola C6. | Definir cortes de eventos: conteúdo crítico já existente confirmado antes da capacidade executável; resultado/commit observado e confirmado posteriormente, antes de progressão que dele depende. W confirma conteúdo/continuidade; observação do atuador precisa de origem própria. |
| F08 / alta | V06/V07/V15; A:137–142,185–187; R2:C3/C5 | UNKNOWN pode coexistir com commit real ou tentativa original viva. «Bloquear ambos» como decisão não para fisicamente o ramo antigo. Consulta autenticada posterior não autoriza retoma nem transfere sessão. | Tabela por fase e por componente: o que bloqueia novas admissões, o que pode continuar por C5, o que exige contenção efetiva e reconciliação. Distinguir retransmissão documental de evento de repetição da operação. |
| F09 / alta | V12/V14 e V:62–69; R2:C2; DEV-02 `measurements.expiry`; todos os finais `authenticated_utc=false` | Autenticação temporal não limita atraso assimétrico; nonce não prova UTC. Bootstrap TLS dependente de UTC obtido por TLS pode ser circular. Revalidar prazo no commit mudaria C2. | Definir bootstrap e custódio UTC, orçamento de erro incluindo suspensão/holdover/assimetria, quarentena e testes de fronteira em A; separar política de frescura do atestado do prazo da aprovação. |
| F10 / média | V:30–44,46–52; A:28–34; DEV-05 README, fronteira experimental | «Oito ou mais» replays e lista genérica de cenários não definem cobertura de interleavings, sessões, falhas correlacionadas, topologia dinâmica ou caminhos efetivamente desativados. | Plano com precondição, barreiras, falha, observador, critério de refutação e evidência por caso; justificar exclusões verificáveis e integrar cenários compostos. Não transformar contagem em prova universal. |
| F11 / alta | A:146–162; DEV-05 `measurements.local_cessation_receipt`; R2:C4/C6 | Cessação de capacidade em R, fim de backends, morte de processo e morte de host são afirmações diferentes. Drenar permite commit antigo antes do corte, sem desfazer efeitos anteriores. | Aprovar significado e âmbito do atestado e exclusões; exigir atuador próprio para morte física. Reconciliar todos os efeitos anteriores; assinatura atribui declaração, não comprova o seu conteúdo. |
| F12 / média | A:193–199; R2:C7; DEV-02/03/04/05 `executable=false` | Ausência de schema/domínio e integração impede tratar recibos de fixture como permissões R2. Dados de revisão podem ser confundidos com autorização se exportados para integração. | Manter perfis, 25 campos, JCS/UTF-8 e Ed25519 puro; especificação/aprovação separada dos bytes, validação estrita, sem fallback R1. Nenhum documento atual autoriza execução. |

F01 é um contraexemplo material histórico e uma impossibilidade condicional ao
modelo. F03/F04/F06 têm contraexemplos ou medições históricas concretas. Os
restantes explicitam condições de prova não satisfeitas e possíveis falhas lógicas;
esta revisão não afirma ter observado uma nova falha operacional.

## Compatibilidade contratual C1–C7

| Contrato | Avaliação crítica da candidata | Achados / condição |
| --- | --- | --- |
| C1, linhas 24–32 | Separação da autoridade e ausência de atomicidade são preservadas no texto; falta protocolo que impeça disponibilizar capacidade antes de consumo/vínculos/ordem/evidência duráveis. | F03, F07; transições especificadas e confirmação D09 no corte correto. |
| C2, linhas 34–45 | Aplicação do prazo em A está correta; commit/efeito posterior não é por si falha R2. Fonte e limites UTC continuam pendentes. | F09; [L,U] inteiramente elegível e duração máxima 900 s, sem grace period. |
| C3, linhas 47–56 | Revogação posterior não cancela admissão; contenção pode impedir efeitos futuros sem desfazer admissão/consumo. | F04/F08; ordem autoritativa explícita e revogação pendente não apresentada como eficaz. |
| C4, linhas 58–64 | Reserva separada é necessária para rollback, mas insuficiente sem imposição e vínculos no alvo; clone mantém o bloqueador. Uma iniciação não se prova contando só efeitos confirmados. | F01/F03/F06; observar também iniciações abortadas e concorrentes. Sem promessa de exatamente uma vez. |
| C5, linhas 66–74 | UNKNOWN sem retoma é preservado; a frase de bloqueio não pode ser usada para afirmar que sessão antiga deixou de escrever. | F08/F11; continuidade da tentativa original e invalidação demonstrada antes de nova tentativa. |
| C6, linhas 76–80 | D09 antes da capacidade executável e histórico sem rollback são obrigações, ainda sem mecanismos ou custódios. | F02/F05/F07; conteúdo completo, confirmação independente, quarentena e reentrada humana. |
| C7, linhas 82–86 | Separação de versões conservada; a candidata não define novos bytes e não recebe aprovação por este parecer. | F12; formatos e integração dependem de decisão própria. |

A candidata merece revisão, não rejeição universal de qualquer arquitetura
externa: identifica o problema central e aceita perda de disponibilidade. Porém
esses méritos não resolvem F01 nem tornam demonstradas as condições de implantação.
