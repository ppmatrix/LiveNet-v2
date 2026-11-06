# Aceitação, validação independente e decisões pendentes

Plano futuro proposto; não executado nem autorizado por R2-DEV-06.

## 1. Critério central e oráculos

O clone antigo deve permanecer vivo com sessão, credenciais e epoch antigos e
tentar escrever depois da confirmação pretendida de takeover. Um efeito antigo
posterior ao corte impede aceitação; se observado depois de uma confirmação já
emitida, refuta essa confirmação e exige bloqueio/incidente. Não basta impedir
novas ligações ao original nem demonstrar que o novo ramo consegue escrever.

O revisor deve ter administração, credenciais e recolha de evidência independentes
do executor/controlador. Ler payload e estado persistente diretamente, no
original e em cada clone, incluindo storage e filas pendentes. Contar à parte
admissões, reservas de iniciação, início observado e efeitos/commits. Comparar
os eventos pela ordem causal do recurso e barreiras observáveis; relógios de
máquinas diferentes e timestamps de logs não estabelecem a ordem do corte.

Cada execução futura deve guardar topologia, inventário, ameaça coberta,
configuração de persistência, versões, hashes, principal/canal, ordens, saída
integral, intervenções e limpeza. Guardar falhas e resultados contraditórios.
Ausência de log/ack não prova ausência de efeito. B/W não podem ser o único
oráculo de uma afirmação sobre o seu próprio funcionamento.

## 2. Matriz de ensaios futuros

| ID | Cenário e observação independente exigida | Aceitação / condição de bloqueio |
| --- | --- | --- |
| V01 | Inventariar todos os caminhos e usar executor, broker, owner, superuser, socket local, replicação e workers para tentar contorno | Caminho com poder de efeito fora de B impede aceitação; privilégio global fora do modelo deve ser declarado e aprovado |
| V02 | Reproduzir as duas janelas DEV-04: perder sessão externa antes do SQL e após UPDATE antes de commit | Corte espera por commit antigo ou força aborto antes de confirmar; nenhum commit antigo posterior |
| V03 | Clone físico integral com backend antigo vivo, separado do original, tenta UPDATE depois da cessação SQL original | Deve falhar no próprio meio de efeito; escrita no clone é falha mesmo sem publicação; não excluir o clone silenciosamente |
| V04 | Snapshot histórico de dados/WAL, memória e credenciais; restaurar também controlador/ledger e tentar replay da aprovação | Consumo não se liberta, epoch não recua e nenhum ramo recupera capacidade; copiar também B/raiz externa é contraexemplo esperado se permitido |
| V05 | Operações já aceites: transação aberta, commit em voo, I/O pendente, prepared statement, 2PC se habilitado | Nenhuma confirmação enquanto subsistir trabalho antigo capaz de confirmar; recursos não cobertos ficam bloqueados |
| V06 | Perder resposta da admissão, reserva, fence e efeito após commit real e antes do ack, separadamente | UNKNOWN sem despacho/retoma/retry automático; consulta read-only apenas esclarece; não reusar aprovação |
| V07 | Particionar executor–A, B–F, V–F, V–W, storage multipath e redes de gestão, antes/durante/depois do corte | Não confirmar sem prova; não promover ramo minoritário/isolado; tentativa já admitida mantém semântica C5 até contenção efetiva |
| V08 | Crash do controlador em cada transição, queda real dos componentes isolados e recuperação do armazenamento | Estados parciais persistentes bloqueiam; só reconciliação explícita; nenhum arranque reabre capacidades antigas |
| V09 | Reiniciar o host cortado, reanexar volumes, re-registar iniciador, restaurar ACL/configuração antiga e rota alternativa | Corte resiste ao rearranque e cobre todos os caminhos; reabertura não autorizada refuta durabilidade |
| V10 | Falsificar/repetir atestado, trocar recurso/geração/encarnação/epoch, usar nonce antigo e endpoint com certificado copiado | Verificador rejeita; estado atual e identidade externa obrigatórios; erro nunca gera permissão |
| V11 | Oito ou mais replays concorrentes, sessões distintas, rollback e savepoints; chamar função diretamente com papel de serviço | Uma aprovação admite no máximo uma tentativa/iniciação; reserva sobrevive a rollback; efeitos podem ser zero, sem promessa exatamente uma vez |
| V12 | Revogação antes/depois de A e concorrente; expiração durante locks e resposta tardia; ordem desconhecida | Ordem persistente prevalece; revogação anterior impede A; posterior não cancela; elegibilidade UTC só em A conforme C2 |
| V13 | D09 sem conteúdo, atrasado, divergente, indisponível ou restaurado; executor assina recibo próprio | Nenhum percurso executável sem confirmação independente completa; hash sozinho não recupera conteúdo |
| V14 | UTC autenticado com assimetria/atraso, fonte errada, salto/rollback, suspensão e perda de continuidade | Intervalo [L,U] inclui erro declarado; fora da janela/erro desconhecido bloqueia A e frescura; sem fallback não autenticado |
| V15 | Incidente com resultado incerto, recolha read-only, decisão humana e novo pedido/aprovação | Reconciliação não emite ticket nem retoma antiga; capacidades antigas invalidadas antes de reentrada |

A bateria deve incluir controlos negativos que mostrem o efeito quando o fence é
deliberadamente removido numa fixture. A passagem de um controlo que reproduz
falha não conta como demonstração positiva. Reportar separadamente rejeições
esperadas e invariantes satisfeitas, repetições/interleavings e limites restantes.
Falhas reais de rede/host/storage não podem ser substituídas por flags em memória
quando se reivindica resistência a essas falhas. Cobertura finita é evidência
parcial, complementada pelo argumento de segurança e revisão independente.

## 3. Dependências de implantação futura

| Dependência | Entrega e condição antes de ensaio/ativação correspondente |
| --- | --- |
| Segregação administrativa | Matriz nominal de responsabilidades e poderes de aplicação, hipervisor, storage, F, A, CA, chaves, backups, W e reconciliação; demonstrar que admin de D não administra B/W nem os seus backups |
| Identidade remota | TLS 1.3/mTLS onde aplicável, sem 0-RTT sensível, CA e enrolamento fora de D, revogação/rotação e binding serviço–recurso–canal; certificado válido não concede poder de escrita |
| Identidade resistente a clone | Selecionar mecanismo físico/remoto após avaliar cópia de vTPM, relay, uso abusivo do hardware original e recuperação; separar chaves TLS, aprovação e atestação |
| D09 independente | Custódio/domínio distinto com conteúdo completo dos eventos críticos, confirmação anterior ao percurso executável, retenção/continuidade e acesso de auditor; segunda VM no mesmo hipervisor não basta |
| UTC autenticado com erro limitado | Fonte e custódio, autenticação, orçamento de erro incluindo atraso/assimetria/holdover/suspensão, bootstrap temporal/TLS e regras de quarentena; limites numéricos requerem aprovação |
| Persistência e recuperação | Demonstrar fence/consumo/ordem após falha de energia/storage no ambiente autorizado; continuidade externa ao backup; RPO de segurança sem perda de consumos aceites; se não demonstrável, quarentena |
| Formatos e integração | Aprovar schema/codificação/assinatura do atestado e R2, vínculos de sessão/transação, catálogos e operação fixa; preservar 25 campos e separar versões; revisão AUTH-03/F02/G2/G4 própria |

[RFC 8915, §8.6](https://www.rfc-editor.org/rfc/rfc8915.html#section-8.6)
documenta que autenticação NTS não elimina ataques de atraso assimétrico.
Assim, escolher NTS não demonstra por si só UTC com erro limitado para LiveNet;
o orçamento e rejeição de amostras exigem demonstração própria. Esta é uma
dependência proposta, sem escolha de fornecedor nem configuração nesta etapa.

## 4. Custo, disponibilidade e riscos residuais

Não há orçamento ou preços aprovados. Comparação qualitativa: proxy e função
SQL têm menor custo inicial, mas não cobrem cópia independente; serviço de dados
externo e storage/fabric exigem mais integração, capacidade, operação e custódia;
fencing físico acrescenta canais de gestão e inventário; TPM/HSM acrescentam
hardware, enrolamento, substituição e recuperação. Confirmar compatibilidade e
capacidade precede qualquer aquisição. Não se presume que estes meios existam.

A dependência de A/B/F/W/UTC perde disponibilidade em partição, dúvida de
continuidade ou corte não confirmado. Drain pode esperar indefinidamente;
aborto pode consumir aprovação sem efeito. Uma intervenção física pode retirar
outros serviços do mesmo host/volume. Não há RTO garantido, HA ou failover
automático aprovados. Estimar RTO/capacidade e impacto com base na topologia
futura, sem escolher números por conveniência.

Persistem risco de inventário incompleto, comprometimento/conivência dos
custódios, controlador que reporte sucesso antes de tornar o corte efetivo,
storage que perca reservas, cópia gravável desconhecida, credenciais duplicadas,
relay de identidade, erro temporal e perda de conteúdo D09. Assinaturas não
eliminam esses riscos. Testes finitos não demonstram impossibilidade universal.
Nenhum mecanismo proposto desfaz commits anteriores nem garante efeito único
distribuído perante qualquer administrador.

## 5. Registo de decisões para aprovação explícita

| Decisão pendente | Proposta revisável | Autoridade/ação que ainda falta |
| --- | --- | --- |
| Fronteira do efeito | Manter como falha qualquer escrita antiga em clone; avaliar se é viável impedir cópias graváveis de B | Aprovação humana do inventário, ameaça e eventual alteração explícita de alcance; C4/C6 não se alteram aqui |
| Arquitetura | A única, B externo obrigatório e F efetivo com W/V independentes; sem HA automática | Aceitação arquitetural específica da candidata e dos custódios |
| Mecanismo de corte | Preferir imposição no recurso/storage com exclusão persistente; corte físico onde necessário | Escolha de produto, topologia, política drain/abort e risco de impacto |
| Significado do atestado | Capacidade de efeito cessada em R; morte física somente com prova própria | Aceitação do alcance e rejeições; schema/bytes/algoritmos aprovados separadamente |
| Confiança e tempo | Domínios administrativos distintos, PKI e UTC com incerteza | Pessoas, infraestrutura, parâmetros de frescura/erro, retenção e recuperação |
| Próxima etapa | R2-DEV-07 documental com revisão independente de P1–P5 e V01–V15 | Autorização própria; depois, plano de laboratório delimitado e aprovação própria de recursos/ensaios |
| Integração e gates | Manter bloqueios até critérios demonstrados e aceites | Decisão operacional futura separada; este estudo não autoriza DEV-09B nem fecha GAP-001/002 |

A autorização já recebida para R2-DEV-06 cobre o estudo documental. Não se
reapresenta essa autorização como aprovação das escolhas acima. O próximo pacote
de revisão deve trazer topologia proposta, custódios, matriz de poderes, prova de
cobertura, orçamento de disponibilidade/custo e plano de ensaios sem efeitos
operacionais, para permitir decisão concreta antes de provisionar.
