# R2-DEV-07 — parecer documental crítico

Data: 2026-10-27, Europe/Lisbon; data editorial, sem atestado UTC.
Objeto: candidata R2-DEV-06 em `progbox:/home/paulo/projects/livenet-v2`.
HEAD observado: `647179c928888adfeef0f69f582fd13c5fc17350`.

**Veredito: necessita revisão arquitetural.** A candidata reconhece corretamente
os limites dos fences locais, mas ainda não define uma arquitetura cuja cobertura,
vinculação de iniciação e continuidade possam ser verificadas. Não está pronta
para receber o veredito «aceitável para ensaio delimitado».

Se os pressupostos atuais incluírem uma cópia integral gravável do recurso sob
controlo adversarial, o requisito forte de impedir qualquer efeito nessa cópia é
**inviável com pressupostos atuais**. Esta conclusão é condicional ao domínio de
cópia: não equivale a declarar impossível um futuro serviço externo com cobertura
demonstrada. A decisão de retirar recursos desse domínio continua pendente de
aprovação humana explícita; esta revisão não a toma.

O contraexemplo histórico decisivo está em DEV-05,
`measurements.clone_survives_local_cessation_counterexample`: original epoch 2,
payload zero, clone vivo epoch 1, payload um. Recusar o endpoint do clone ou
assinar o recibo do original não impede esse efeito. A existência de apenas uma
admissão também não basta: DEV-05 regista uma chamada direta com zero consumos e
um efeito; o bypass administrativo muda o payload sem entrada no ledger de efeitos.

Os bloqueadores são: domínio de efeito e custódia ainda por decidir; P1/P2 sem
cobertura verificável; protocolo reserva–sessão–transação por especificar;
ordem durável entre efeito terminal e corte ainda sem implementação selecionada;
oráculos e confirmação D09 sem independência administrativa demonstrada;
recuperação/UTC sem mecanismos e parâmetros aprovados. São obrigações pendentes,
algumas já reconhecidas em DEV-06, não falhas novas observadas em execução.

O argumento P1–P5 é coerente como implicação condicionada, mas P3/P4 incluem
grande parte da propriedade que se deseja provar. Não serve como demonstração
independente das suas premissas. A revisão identifica também o risco de um W que
apenas arquiva a declaração de F acabar usado para validar a mesma declaração.

Documentos da entrega:

- [FINDINGS.md](FINDINGS.md): premissas P1–P5, contraexemplos, matriz F01–F12 e compatibilidade C1–C7.
- [VALIDATION.md](VALIDATION.md): crítica individual V01–V15, oráculos, custódios e condições AC01–AC10.
- [PROVENANCE.md](PROVENANCE.md): fontes diretas, hashes, acesso, estado e preservação.

Próximo passo recomendado: **R2-DEV-08, especificação documental revisada**,
sujeita a autorização própria. Entregar topologia concreta e inventário fechado,
matriz nominal de poderes, transições de consumo/fence/D09/recuperação e plano de
observação independente. Deve decidir expressamente a viabilidade da cópia
gravável e o significado do atestado. Só depois haverá matéria concreta para
decidir se um plano de ensaio delimitado pode ser autorizado separadamente.

Esta é revisão técnica por agente com leitura direta de artefactos. Não é auditoria
externa nem demonstra independência administrativa ou humana real. Nenhum ensaio,
SQL, instalação ou alteração operacional foi executado. A arquitetura e a execução
permanecem por aprovar; AUTH-03/F02/G2/G4 fechados, GAP-001/002 abertas e DEV-09B
não autorizada. Sem commits ou push.
