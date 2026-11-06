# R2-DEV-08 — viabilidade documental no laboratório Proxmox

Estado: PROPOSTA NÃO APROVADA. Avaliação baseada em artefactos e acesso a ficheiros; nenhum acesso à API/consola Proxmox, sondagem de rede, inventário de hardware ou provisionamento foi efetuado.

## Recursos conhecidos versus capacidades por verificar

| Item | Facto da fonte ou observação nesta entrega | Requisito para a candidata / estatuto |
| --- | --- | --- |
| progbox | SSH como paulo ao checkout foi confirmado. DEV-05 evidencia Python 3.12.3, PostgreSQL 16.15 e psycopg 3.3.6 na execução histórica. | Não se assume versão atual, capacidade livre, isolamento ou que progbox seja host/VM Proxmox. |
| Ambiente Proxmox | F0/environment preveem STAGING em VM dedicada. R1-D10 determina A único em VM dedicada separada de aplicação/PostgreSQL. | Não foram localizados hosts/VMIDs concretos, CPU/RAM/discos disponíveis, versões, rede de gestão ou poderes nominais. Existência de requisito não prova disponibilidade. |
| Operação fixa | Clusters descartáveis e UPDATE sintético usados historicamente. | Podem fundamentar plano funcional futuro; recursos históricos limpos não estão reservados para DEV-08. |
| Storage e corte | DEV-05 comprova somente fence/cessação SQL local no laboratório passado. | Pools, multipath, dispositivos/reservas, cache, persistência, re-registo e atuador externo não verificados. Não se presume SAN, storage fencing, BMC/PDU ou Passthrough. |
| Identidade/chaves | Pin de socket/SO_PEERCRED histórico, mesmo administrador. | PKI remota, enrolamento, revogação e chaves fora de D pendentes. HSM/TPM físico não localizados; vTPM não é assumido não clonável. |
| Independência | Papéis SQL e VMs separadas são descrições lógicas, sem matriz nominal demonstrada. | Administração efetivamente separada para A, B/F, W/V e recuperação deve ser comprovada; host global comum invalida a alegação contra esse administrador. |
| D09 | DEV-04/05 registam independência não demonstrada. | W com conteúdo integral, confirmação e continuidade, retenção e acesso independente ainda não identificado. |
| UTC | authenticated_utc=false nas evidências finais históricas. | Fonte autenticada, erro limitado, bootstrap, atraso/holdover/suspensão e custódio não especificados operacionalmente. |
| Backups | Requisitos documentais de backups separados; snapshots históricos reativam estado antigo. | Inventário de todas as cópias/exportações e raiz de continuidade fora de D não demonstrados. |
| Política de acesso | DEV-05A-D01 impõe LAN-only a todos os ambientes. G4 exclusivo sem NIC é outra fronteira. | Topologia futura precisa de alcance interno aprovado e controlo de rotas/gestão; não publicar UI/API/ensaios nem reutilizar G4 por inferência. |

## Topologia candidata concreta, mas condicional

Esta é uma distribuição de responsabilidades proposta, sem quantificar VMs como se fossem recursos disponíveis:

| Zona proposta | Conteúdo e ligação permitida | Fronteira administrativa requerida |
| --- | --- | --- |
| ZD | Executor e ramo antigo/clonado; ligação interna autenticada apenas a A e operação fixa B. | Administrador adversarial de D não controla dados/backup nem administração das outras zonas. |
| ZA | A único, ledger de admissão/ordem/consumo e evidência local. | VM dedicada conforme determinação R1; host, backups, chaves e recuperação fora do poder de D. |
| ZB | Serviço de dados B, payload sintético, contexto protegido e registo de início não reversível pelo efeito. | Dados e todos os meios de reconstrução gravável fora de D; administradores confiados identificados. |
| ZF | F e plano de gestão do atuador em todos os meios de ZB; política de não reabertura. | Pode integrar a base confiada B/F, com poderes declarados; não pode ser o único observador independente. |
| ZW | W com cópia de conteúdo crítico/continuidade e arquivo recuperável. | Administração/recuperação independente dos produtores que verifica, sem root global adversarial comum. |
| ZV | V e captura de iniciações, mutações/commit, atuação e inventário; acesso de leitura próprio. | Sem segredo de efeito nem administração do controlador verificado; arquivo fora da sua adulteração. |
| ZK/ZP/ZT | Recuperação/continuidade, confiança/enrolamento e tempo autenticado. | Poderes transitivos identificados; nenhuma raiz pode ser restaurada por D para tornar permissões antigas atuais. |

Separar ZA/ZB/ZW em VMs no mesmo host pode servir um estudo funcional quando se confia no host. Não satisfaz por si a independência contra o seu administrador, nem cria um segundo domínio de falha físico. A escolha de hosts separados, controladores e custódios deve decorrer da matriz de poderes, não de contagem de VMs. Rede interna também não impede que root copie um disco.

Para o corte, a candidata exige exclusão na operação B até término e um atuador persistente em todos os meios onde capacidade antiga possa sobreviver. A opção concreta de dispositivo/fabric/energia permanece por selecionar após inventário. [A documentação Linux de reservas persistentes](https://docs.kernel.org/block/pr.html) descreve restrições por iniciador e preempção com aborto; isso não prova que o storage LiveNet as suporte, cubra todos os caminhos ou impeça cópia num disco independente. A seleção inclui quem pode limpar reservas, re-registar iniciadores e restaurar configuração.

## Veredito por objetivo

| Objetivo | Viabilidade nesta etapa | Condição para avançar |
| --- | --- | --- |
| Produzir especificação documental | Realizada no âmbito autorizado. | Revisão e decisão humana das opções. |
| Simulação funcional sob administrador único confiado | Potencialmente planeável com base histórica; capacidade atual não verificada. | Autorização própria de plano/recursos. Resultado explicitamente incapaz de provar independência real ou propriedade universal. |
| Ensaio independente da fronteira externa | **Prontidão não demonstrada; bloqueado para aprovação favorável.** | H01–H10 pertinentes, inventário fechado, custódios reais, mecanismo compatível, observadores e limites demonstráveis. |
| Cessação universal com clone integral gravável adversarial | **Inviável nos pressupostos atuais.** | Alteração explícita e demonstrada de poderes ou reconhecimento formal de inviabilidade. Mais VMs, PKI ou assinatura não eliminam o clone. |
| Integração/produção/gates | Não autorizada por este trabalho. | Decisões operacionais próprias, fora de DEV-08. |

Não se calculam capacidade, preço, RTO ou número de máquinas com valores inventados. Indisponibilidade por A/W/UTC inacessíveis, drain interminável ou corte incompleto pode durar indefinidamente. Aborto pode gastar aprovação sem efeito; corte físico pode afetar outros serviços do host/volume. Um orçamento futuro deve identificar esses serviços, janela, capacidade, responsáveis e processo humano; não oferecer HA ou failover automático como compensação tácita.

A consulta ao guia público Proxmox devolveu HTTP 403; não se tomou isso como prova de qualquer capacidade instalada. A avaliação específica acima baseia-se nas fontes internas identificadas em PROVENANCE, não em funcionalidades presumidas do produto.
