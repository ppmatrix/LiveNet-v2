# R2-DEV-01 — Evidência e limitações

Data: 2026-10-27. Repositório verificado por SSH antes de qualquer escrita:
`progbox:/home/paulo/projects/livenet-v2`.
HEAD inicial e final: `647179c928888adfeef0f69f582fd13c5fc17350`.

Implementado o protótipo isolado em `experiments/auth_boot_02_r2_dev01/`, com
máquina de admissão persistente, testes e evidência reproduzível. O âmbito de
R2-DEV-01 fica concluído como demonstração experimental parcial de C1–C7;
os critérios mínimos operacionais da baseline não ficam satisfeitos.

## Resultado observado

Execução final em progbox: `PYTHONDONTWRITEBYTECODE=1 python3 run_tests.py`.
Python 3.12.3. **40 testes, 40 passaram, zero falhas/erros/skips, exit code 0**.
Tempo indicado pelo unittest: **5,386 segundos**.
IDs, saída integral, hashes dos fontes, runtime e instante UTC em `evidence.json`.

- 32 threads e 8 processos concorrentes obtiveram exatamente uma admissão por
  aprovação na mesma autoridade; todos os restantes foram recusados.
- As 16 corridas entre admissão e revogação respeitaram a ordem persistida.
  Os quatro âmbitos de revogação foram exercitados. Pedido pendente não é eficácia.
- Os testes cobrem [L,U], máximo de 900 s, expiração durante espera pelo lock,
  commit posterior à expiração, epochs/política, vínculos e conflitos de IDs.
- Crashes reais com `os._exit(73)` foram injetados antes do commit, após commit
  local e após a cópia. Consumo durável não foi libertado; incerteza bloqueou;
  consulta de estado nunca emitiu permissão nem autorizou retry/retoma.
- Restauro antigo contra testemunho atual, encarnação diferente, ack inválido,
  testemunho ausente, corrupção e continuidade temporal desconhecida bloquearam.
- Um teste de limitação confirmou duas admissões em cópias completas separadas
  com a mesma identidade, testemunho e chave. Esse teste passa por demonstrar o
  contraexemplo esperado; não é evidência de resistência a clones completos.

A primeira execução também passou os 40 testes, mas terminou com exit code 1
ao tentar guardar a evidência: a pasta copiada de Windows ficou sem escrita para
o proprietário. Corrigida apenas essa permissão na nova pasta experimental;
a execução final gravou `evidence.json` e terminou com exit code 0.

## Preservação do checkout

Antes da cópia foram registados hashes de **360 ficheiros existentes**, o estado
Git completo e o diff binário. Após os testes:

- `sha256sum --quiet --check` confirmou os 360 ficheiros, exit code 0.
- `cmp` confirmou o diff binário byte a byte, exit code 0.
- `cmp` confirmou o estado Git fora da pasta experimental byte a byte, exit code 0.
- HEAD permaneceu inalterado. A única nova entrada é a pasta deste laboratório.

Hashes das capturas iniciais em `/tmp/livenet-r2-dev01-01a17d15-before.*`:

| Captura | SHA256 |
| --- | --- |
| sha256 | `b72e62deeb02cb12549b7d032983253e7792bc2a6cf576cbbdd6e3a97b0ad36d` |
| status | `fe2432ba98c6994ce10431a0c1359118c98c550c7ffac34f2dae98958483c6fb` |
| diff | `21b7778033dde56d142558cdeac78808f35437cdbc8e03fead49ad288c445df2` |

As capturas temporárias não são um arquivo de auditoria independente. A evidência
de preservação limita-se aos ficheiros versionados e não ignorados presentes na
captura; não afirma integridade de serviços, bases externas ou ficheiros ignorados.

## Limites para decisão

SQLite, relógio injetado e HMAC de teste servem apenas o laboratório. A cópia
persistente está no mesmo host e sob o mesmo administrador: independência D09,
UTC autenticado, anti-clone externo e invalidação real de capacidades antigas
continuam por demonstrar. Os crashes de processo não provam resistência a falha
de energia ou recuperação física do armazenamento.

Não foram implementados domínio de assinatura R2, JCS/Ed25519, schema operacional,
parsers, executor, despacho ou efeitos PostgreSQL. A restrição interna à string
`2` demonstra separação de semântica no modelo; não aprova codificação C7.
O rollback/savepoint testado pertence a um chamador SQLite em memória, não ao
alvo PostgreSQL. Não demonstra exclusividade de iniciação nem bloqueio de SQL direto.

GAP-001/002 permanecem abertas. AUTH-03/F02/G2/G4 permanecem fechados.
DEV-09B continua não autorizada. Não houve commits, push, alterações de serviços,
contratos, parsers/executores operacionais ou infraestrutura. Não foi necessário
PostgreSQL descartável. A rastreabilidade detalhada e as condições do modelo
constam de `README.md`.
