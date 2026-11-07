# DEV09B-1 — autorização do segundo bloco offline: camadas e evidências

07/11/2026 · Europe/Lisbon

## Decisão e âmbito

Fonte primária: pedido humano nesta conversa «Implementar o segundo bloco
offline DEV09B aprovado nesta sessão», base main/HEAD `28cd77e`, confirmada com
árvore limpa. Aprova a implementação delimitada da proposta de schemas semantic,
physical, provenance, Evidence e tipos internos, referências cruzadas e comparação
estrita de catálogo/ledgers. Autoriza os testes offline pertinentes, este ato e
atualização sucinta de CONTINUITY.md. Não aprova antecipadamente os bytes da
implementação nem autoriza qualquer execução operacional.

Preserva o [desenho aprovado](dev09b-migration-design-approval-20261107.md) e o
[primeiro bloco offline](dev09b-offline-block-approval-20261107.md), sem alterar
os respetivos bytes. Operações continuam apenas application base→f066a01a7230 e
security base→b12b01a7230 após confirmação independente de f066, separadamente.

## Condições vinculativas

1. Tipos estritos: bool não equivale a int; sem coerções ou campos desconhecidos.
2. Matriz explícita de phase/execution_result/nulidade; combinações resolvidas
   pelos significados aprovados, sem inferir garantias novas.
3. Perfis versionados e vinculados às fontes exatas. Perfil incompleto resulta
   em Unsupported e nunca confirma base, sucesso ou rollback.
4. classification=OPERATIONAL é apenas uma alegação. Autenticidade e confirmação
   independente exigem interfaces próprias; doubles só produzem observações
   sintéticas, sem autenticidade operacional.

Expectativas são entradas previamente fixadas, separadas das observações;
igualdade de hashes não comprova aprovação prévia, proveniência ou independência.
Ledger ausente, presente vazio e revisão concreta são estados distintos.
Conjuntos ordenados/unívocos não se confundem com a sequência da cadeia.

## Matriz de fases implementada

| phase | execution_result admissível | IDs e session_binding |
| --- | --- | --- |
| BEFORE | NOT_STARTED | Todos presentes, ou os três IDs e sessão todos null na inspeção inicial |
| PRECOMMIT | UNCOMMITTED | Todos presentes |
| POSTCOMMIT | COMMIT_REPORTED ou UNKNOWN | Todos presentes |
| ROLLBACK_CHECK | ROLLBACK_REPORTED ou UNKNOWN | Todos presentes |

POSTCOMMIT designa observação posterior à tentativa de commit, não prova de
commit. ROLLBACK_REPORTED também não comprova rollback. Nenhum dos resultados
declarados resolve incerteza sem confirmação independente. Nulidades parciais e
outras combinações são recusadas. session_binding refere a execução observada;
o coletor tem identidade distinta. Comparar um par de observações exige vínculo
à mesma sessão/transação/encarnação, mas isso não demonstra independência.

## Concretizações mecânicas e suporte real

- Schemas fechados, UUID/hash/limites e JCS do perfil DEV09B-1 reutilizados.
  Referências a documentos fechados, estados esperados e cadeia usam SHA-256
  dos respetivos bytes JCS. Digests das três camadas conservam os domínios
  já definidos no primeiro bloco; sem novo formato de assinatura.
- ExpectationSnapshot guarda bytes imutáveis e revalida envelope/bindings/plano,
  fontes da cadeia/validadores e digests. Não recebe observações para gerar
  expectativas. A origem/aprovação histórica das entradas exige prova externa;
  o snapshot não a inventa.
- Evidência inicial pode ser a própria referência prerequisite_evidence do
  plano; observações posteriores referenciam essa evidência. A referência
  coincidente não autentica o documento nem confirma f066 independentemente.
- Perfis `auth03-base-inventory-v1`, `m12b-f066-inventory-v1`,
  `m12b-b12-inventory-v1` e `g2-f066-b12-d05-v1` fixam fontes por path/SHA-256.
  Reutilizam apenas predicados compatíveis de schemas/relações/ledgers.
  O inventário G2 inclui schemas de sistema, ao contrário da projeção M1.2B.
- A variante detailed_catalog permanece fechada com apenas o discriminador
  profile: marcador explícito de variante incompleta, não payload opaco aceite.
  Nenhum perfil detalhado foi declarado completo. A comparação de projeções
  devolve InventoryComparison, sem confirmação de base/sucesso/rollback ou
  permissão de executar. Pedidos de confirmação integral retornam Unsupported.
- Não se inventou catálogo inicial completo, extensões/defaults permitidos,
  ownership ou ACL por fase. O perfil final G2/D05 não é transplantado para a
  fase transacional do migrator nem apresentado como cobertura integral.
- Authenticity e Independence são interfaces; os doubles não autenticam claims
  operacionais e não confirmam independência. Não há coletores/transportes reais.

## Verificação e dependência seguinte

Testes locais cobrem ambas as operações, schemas fechados, tipos estritos,
matriz de fases/nulidade, ordem/unicidade, catálogo truncado/resíduos, ledgers,
fontes versionadas, referências divergentes, mutação/reconstrução de expectativas
e tentativas de promover evidência sintética. Não demonstram estado real,
autenticidade, independência, exclusividade ou recuperação operacional.

Dependência concreta seguinte: especificar/rever os perfis detalhados e suas
expectativas completas de catálogo inicial, extensões/defaults e ownership/ACL
por fase. Até lá não existe validação integral de nenhuma das duas migrações.
Sem novas decisões materiais de segurança/semântica adotadas neste bloco.

AUTH-03/F02/G2/G4 mantêm-se fechados; R1/R2/C4/I-04 e contratos anteriores
preservados. Sem instalações, rede, PostgreSQL, SQL/Alembic, serviços,
infraestrutura, staging, commits ou pushes. Progbox exclusivamente DEV;
STAGING/PROD em VMs Proxmox e acesso exclusivamente interno.
