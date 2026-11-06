# R2-DEV-08 — custódios e poderes administrativos

Estado: PROPOSTA NÃO APROVADA. Matriz funcional para preenchimento nominal. Nenhuma pessoa é designada custódio por inferência do acesso SSH, titularidade do projeto ou número de contas. Os nomes reais, substitutos e relações de administração permanecem **PENDENTES**.

## Domínios e privilégios necessários

Os símbolos identificam responsabilidades, não VMs ou pessoas já existentes. B/F podem pertencer à mesma base confiada de imposição se H03 o aprovar; isso não os torna observadores independentes entre si. A deve ser independente das bases LiveNet e executores por C1. W e V precisam de recolha/administração fora do poder de adulteração do executor/controlador sobre as afirmações que verificam. Não se propõe um número de VMs como prova de independência.

| Domínio / nome real | Poder necessário | Poder que não deve ter sobre outros domínios | Prova nominal pendente |
| --- | --- | --- | --- |
| D executor/aplicação / PENDENTE | Controlar cliente, memória e cópias permitidas; solicitar uma operação fixa. | Escrever em B fora do percurso; administrar A/F/W/V, CA, continuidade ou recuperar os seus backups. | Pessoas, root/sudo, grupos, tokens, deploy e acesso às consolas/segredos. |
| A admissão/ordem / PENDENTE | Serializar admissão/revogação, consumo e vínculos; preservar estado e evidência local. | Alterar payload de B, libertar consumos, criar aprovação humana ou editar W/V. | Admins, processo de recuperação e raiz que impede regressão. |
| B recurso/SQL / PENDENTE | Executar apenas operação vinculada; conservar início único fora do rollback; terminar trabalho antigo. | Emitir admissão, fabricar confirmação W ou decisão humana; reabrir capacidade antiga por conta própria. | Owner/superuser, membros/heranças, funções, contas OS e acesso raw. Admin B confiado explicitamente. |
| F/storage/fabric / PENDENTE | Impor corte em todos os caminhos e bloquear re-registo; preservar exclusão e reportar estado. | Autorizar operação ou atestar sozinho a própria atuação como prova independente. | Operadores storage/BMC, firmware, reservas, gestão fora de banda, recovery e fornecedores. |
| W/D09 / PENDENTE | Receber, conservar conteúdo crítico e confirmar continuidade; disponibilizar leitura independente. | Escrever payload, conceder admissão ou reentrada, alterar retrospectivamente eventos aceites. | Identidade própria, arquivo, retenção, administradores e backups fora do poder de D e controlador. |
| V observação/revisão / PENDENTE | Verificar inventário, iniciações, payload/commit, atuador e continuidade; declarar alcance limitado. | Invocar operação, substituir atestado por autorização, alterar fontes observadas ou administrar o corte que valida. | Credenciais read-only adequadas, captura independente e administração do coletor/arquivo. |
| P confiança/PKI/enrolamento / PENDENTE | Emitir/rotacionar/revogar identidades segundo política e aprovações próprias. | Substituir raízes/enrolar clone e reabrir capacidade sem revisão; personificar livremente W/V/A sem deteção. | Admins CA, chaves, trust stores, DNS, recovery e segregação dos poderes de emissão. |
| T tempo / PENDENTE | Fornecer origem UTC autenticada e orçamento de erro/continuidade justificável a A/V. | Autodeclarar erro zero ou usar o relógio de D como raiz de confiança. | Fonte, custódio, bootstrap, limites externos de atraso/holdover/suspensão. |
| K backup/continuidade / PENDENTE | Inventariar/preservar histórico, demonstrar eventos após backup e restaurar em quarentena. | Exportar/restaurar meios graváveis fora da fronteira; restaurar CA/ACL/fence antigos como atuais. | Leitores de plaintext, custodiante de chaves, destino, retenção, cópias offline e âncora externa. |
| H reconciliação/decisão humana / PENDENTE | Receber evidência, decidir risco, autenticar/auditar decisão e nova aprovação vinculada. | Declarar cessação sem prova ou reutilizar aprovação antiga; bypass de emergência. | Reconciliador, decisor e aprovador identificados; conflitos de interesse e substituição. |
| G hipervisor/host/rede/recuperação / PENDENTE | Manutenção dos recursos expressamente atribuídos. | Poder global não declarado sobre todos os domínios que se dizem independentes. | Hosts físicos, consolas, root, storage partilhado, plano de gestão, IdP, reset MFA e segredos de automação. |

## Teste de independência e confiança residual

Para cada par relevante, registar se um administrador consegue modificar executável/memória/disco do outro, ler a sua chave, redefinir credenciais/MFA, trocar CA ou fonte de tempo, restaurar backup, assumir consola, mudar routes ou re-enrolar iniciador. Considerar também recuperação de emergência e contas de serviço/CI, não apenas RBAC normal. Se alguma resposta for sim, há poder transitivo a declarar. A falta de resposta não conta como segregação.

| Separação requerida | Motivo | Condição que a invalida |
| --- | --- | --- |
| D ↔ A e continuidade | C1/C6: consumo e ordem não regressam com clone do executor. | Mesmo root/hipervisor/backup de D pode restaurar ou editar A. |
| D ↔ B/F e dados/backups | P1/P2: cliente não recria meio gravável independente. | Exportação integral ou poder sobre storage/OS de B permite a cópia histórica. |
| W ↔ D/A/B/F sobre conteúdo e retenção | C6/D09: confirmação independente não pode ser fabricada/apagada pelo produtor. | VM separada controlada pelo mesmo administrador adversarial ou CA recuperável por ele. |
| V ↔ executor/controlador sobre observação e arquivo | Evitar que ausência de ledger seja usada para esconder efeito. | Mesmo controlador fornece a única leitura de payload e pode editar a captura. |
| Recuperação ↔ domínio comprometido | Restauro não promove estado antigo nem substitui confiança sem prova. | Mesma credencial comprometida reconstitui raízes e declara continuidade. |
| Decisão humana ↔ relato automático | Reconciliação e reentrada exigem ato humano identificável. | Duas contas da mesma pessoa apresentadas como dupla supervisão independente. |

Conivência/compromisso arbitrário de toda a base confiada não é tolerado pela candidata. Em especial, confiar em B/F exclui alegar resistência à escrita deliberada pelo seu administrador global. H03 deve aceitar ou rejeitar nominalmente esta exclusão e indicar quais combinações de compromisso estão cobertas. Não há alegação de consenso bizantino, maioria independente ou resistência a um administrador omnipotente.

Controlo por duas pessoas continua recomendação a concretizar segundo R1-D10. A proposta exige identificar separadamente reconciliador e aprovador, mas não afirma que já existam pessoas independentes. Se só existir um administrador efetivo de todo o laboratório, a independência fica não demonstrada; o ambiente poderá servir para estudo funcional delimitado, sem satisfazer D09 nem o critério independente de segurança.

Cada nomeação futura deve indicar pessoa titular/substituta, identidade autenticada, domínio físico e lógico, poderes delegados e herdados, meios de recuperação, evidência de ausência de poderes proibidos e revisão de conflitos. Nenhum preenchimento desta matriz autoriza conceder os privilégios.
