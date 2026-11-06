# C4 consolidada — fontes e verificação da entrega

30/10/2026 · Europe/Lisbon · Revisão documental pelo agente.

## Contexto efetivamente acessível

Checkout `/home/paulo/projects/livenet-v2` em progbox; branch `main`; HEAD `647179c928888adfeef0f69f582fd13c5fc17350`; origin configurado `git@github.com:ppmatrix/LiveNet-v2.git`. Leitura local do Git, sem fetch, contacto ao remoto ou prova de acesso remoto GitHub. Há alterações tracked e untracked preexistentes, preservadas. Não foram encontradas instruções AGENTS.md no repositório nem nos seus diretórios ascendentes consultados.

O sandbox falhou intermitentemente ao iniciar com `bwrap: loopback: Failed RTM_NEWADDR`. Usou-se execução autorizada fora do sandbox para leituras locais, comparação de integridade e escrita documental neste checkout. Isso não implicou acesso à infraestrutura operacional.

## Recuperação e fontes consultadas

A última etapa foi recuperada do [índice de continuidade anterior](CONTINUITY.before.md), da [proposta técnica 0.1](../bl-c4-technical-20261030/PROPOSAL.md), do [protocolo candidato](../bl-c4-protocol-20261030/PROTOCOL.md) e dos seus relatórios de revisão. São suficientes para retomar a atividade; não se repetiu recuperação de chats históricos, auditoria geral, inventário ou ensaio. O arquivo literal do índice mantém os links com base no seu local original `docs/project/CONTINUITY.md`.

Foram consultados a [B-L v1.0](../d09-06-bl-conditional-20261030/SPECIFICATION.md), o [ato de aprovação](../../decisions/d09-06-bl-v1-approval-20261030.md), [R2 C1–C7](../../auth-boot-02-r2.md) e [R1 §§11–12](../../auth-boot-02-r1.md). O hash B-L foi comparado com o ato antes e depois da escrita. Não se pediu nova aprovação nem se reescreveu o cabeçalho histórico.

Os contraexemplos DEV-04/05/08 e a distinção D09/V05-06 são reutilizados conforme a análise e rastreabilidade documentais anteriores; não foram reproduzidos nesta etapa. Não se afirma nova consulta integral desses artefactos ou novas conclusões de produto. As fontes públicas confrontadas anteriormente não foram pesquisadas de novo: a consolidação não seleciona tecnologia nem acrescenta alegações de capacidades atuais.

## O que foi consolidado

[PROPOSAL.md](PROPOSAL.md) é uma candidata 0.2 exclusivamente documental. Unifica P0–P6, K e J, explicita o compromisso L anterior à entrada, reúne as obrigações de prova/refutação e mantém C5, sete cenários, corte e reentrada. As três localizações candidatas de L permanecem abertas; ALT-C permanece recomendação de aprofundamento. Não se declara arquitetura selecionada nem mecanismo realizável.

A conferência técnica verificou: anterioridade R2/D09 causal; ausência de evento futuro usado como autorização prévia; consumo sem efeito possível; entrada abortada conta como início; rollback não devolve direito; consulta não cria capacidade; proteção até término; continuidade desconhecida em quarentena; clone gravável conserva bloqueio forte; poder transitivo e operador único preservados; D09 e V05-06 distintos; C2/C3/C7 e todos os gates conservados. É revisão pelo autor, sem demonstração operacional ou certificação independente.

## Preservação e verificação

Antes da escrita guardou-se em `/tmp/livenet-c4-consolidated-before.json` o estado Git, HEAD/branch, digest do diff tracked e hashes SHA-256 dos ficheiros regulares existentes reportados por `git ls-files --cached --others --exclude-standard`. Essa comparação de integridade serve para preservar trabalho anterior; não é inventário de infraestrutura ou auditoria do projeto.

Única alteração deliberada num caminho anterior: acrescentar uma secção ao índice não normativo `docs/project/CONTINUITY.md`. Todos os seus bytes anteriores são conservados como prefixo e na cópia literal CONTINUITY.before.md. Os restantes caminhos escritos pertencem exclusivamente à nova pasta desta entrega. Não se substituíram propostas anteriores, registos, normas ou manifestos históricos.

[PRESERVATION.json](PRESERVATION.json) contém o resultado da comparação, hashes da entrega, validação de referências e verificação de branch/HEAD/diff tracked. A comparação cobre os ficheiros regulares Git enumerados, sem ficheiros ignorados, metadados, ACL, estado interno `.git`, conteúdo externo ou snapshot atómico contra concorrência. Não constitui D09, V05-06, prova de recuperação nem garantia de integridade operacional. Nenhuma igualdade com a cópia Windows é alegada nesta sessão.

Não se executaram testes da aplicação, SQL, runners ou ensaios: o trabalho é documental. Verificações limitaram-se a UTF-8, referências locais dos documentos ativos novos, preservação e estado Git. Nenhum commit, push, merge, deployment ou recurso operacional foi criado.

## Objeto da revisão final

Rever a proposta técnica C4 consolidada como documento condicionado. Aprovação B-L v1.0 concluída e preservada. Nenhuma escolha material ou mudança de gate foi adotada; qualquer futura proposta desse tipo exige decisão própria. Preparação documental reversível continua no âmbito já autorizado.

P4-B4 encerrada; D1/D2/D3 aceites; NC-01 intacto; V02/CF-02 abertas; AUTH-03/F02/G2/G4 fechados/bloqueantes; H02–H12 e GAP-001/002 pendentes/abertos e bloqueantes conforme os registos; RG1–RG7/D09/V05-06 por demonstrar; O3 não aprovado; DEV-09B não autorizado; F0 Working draft/baseline não oficial.
