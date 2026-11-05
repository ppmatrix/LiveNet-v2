# DEV-09-ATTEST03 — Reconciliação documental dos auxiliares

Ambiente: progbox. Repositório: LiveNet v2. Registo documental separado;
nenhuma autorização operacional é emitida por este ficheiro.

## Autoridade e decisões humanas

A instrução humana DEV-09-ATTEST03 confirma os quatro hashes abaixo como
aprovados e determina a consolidação das decisões ATTEST01 e ATTEST02.
O fundamento é essa instrução explícita na conversa, não a existência do código,
a passagem de testes ou uma recomendação técnica anterior. Este documento é um
resumo de rastreabilidade, não uma transcrição reconstruída de decisões originais,
uma assinatura ou uma autorização AUTH-BOOT-02.

- **ATTEST01:** revisão dos quatro auxiliares; recomendação favorável ao auxiliar
  FIX01 e aos testes, com restrição do uso do auxiliar histórico. Identificou a
  descoberta dinâmica de fontes e o gerador Compose com contexto raiz.
- **ATTEST02:** correção localizada de duas APIs históricas e dos testes
  diretamente associados; 170 testes offline passaram. A aprovação humana
  consolidada neste pedido vincula os novos hashes, sem aprovar versões anteriores
  desses dois ficheiros como se fossem equivalentes.
- **ATTEST03:** regista as aprovações de fonte e os seus limites; não executa
  builds, serviços, SQL, migrações ou alterações de código.

## Categorias que não são equivalentes

| Categoria | Significado neste registo |
| --- | --- |
| Fonte aprovada | Bytes identificados por SHA256, aceites humanamente apenas no âmbito indicado. |
| Ficheiro aplicado | Bytes efetivamente presentes na working tree; APP-01/02/03 foram aplicados na DEV-09-APPLY01-FIX02. |
| Componente validado offline | Comportamento observado em testes e verificações sem infraestrutura operacional. |
| Componente operacionalmente autorizado | Exigiria autorização específica posterior; **não concedida** por ATTEST01/02/03 nem pela aplicação das fontes. |

## Quatro fontes aprovadas e âmbitos individuais

| Ficheiro | SHA256 aprovado | Âmbito |
| --- | --- | --- |
| `scripts/dedicated/dev09fix01_packaging.py` | `0d525bbadc8533a94a9650220b8361bb06c983533383740c91c5a67212a0bc17` | Inventário vinculado por hashes, validação, materialização privada e geração de descritor de quarentena; sem runner de build ou deployment. |
| `backend/tests/test_dev09fix01_packaging.py` | `b623d6f138db6950f5c10f3e0d2bdfaf73a49b9a57846c32be90b22acf739a0f` | Testes offline adversariais em fixtures privadas; não constituem autoridade operacional. |
| `scripts/dedicated/dev09a2_packaging.py` | `36492ed081807b235d179a09cbf894b8ffd2d30ca403c83a9e8364a56fcb0e5c` | Formatação literal, matcher restrito, reprodução da proposta Dockerfile e recusa das APIs históricas de inventário/Compose. Nenhuma execução automática. |
| `backend/tests/test_dev09a2_integration.py` | `fe3d071f7e9d0d238d7e060a4ebaf33d4a21931fda7b408f49008ce22afb744c` | Diagnósticos e testes offline de recusas, inventário, propostas e recuperação sintética; sem demonstrar operação real. |

Os auxiliares não passam a integrar o manifesto AUTH-03 por constarem desta
tabela. Não se acrescenta qualquer mecanismo de autoridade aos gates.

## Empacotamento aplicado

Aplicação controlada concluída em DEV-09-APPLY01-FIX02, após ensaios de
recuperação parcial e backups privados. Os três destinos são ficheiros regulares,
com modo `0664`, UID `1000` e GID `1000`.

| Unidade | Destino aplicado | SHA256 final |
| --- | --- | --- |
| APP-01 | `compose.auth03-executor.yaml` | `4e2a634568b568bc9402a44f74d05221ee3d2f022fe221b0d9535f007bb49fa7` |
| APP-02 | `scripts/postgres/auth03_executor.Dockerfile` | `666da86b54e81f0b7196eef55fac8d54ddfaab31c9f98e6d99727bb78c30b7b0` |
| APP-03 | `scripts/postgres/auth03_executor.Dockerfile.dockerignore` | `6920490db9bcbfd0ee1c5710a10758187f45fa5b141d3c4d4842fa9a587d6794` |

São hashes de ficheiros completos, não de patches. As unidades isoladas estão em
`docs/operations/proposals/dev09applyprep/`. O agregado DEV-09A.2 não foi aplicado
e continua proibido como unidade de aplicação: inclui alterações Python não
autorizadas. A presença do Dockerfile aplicado não significa que exista imagem
construída ou aprovada para execução.

## Percurso FIX01 e separação das APIs

- `frozen_inventory()` vincula o candidato histórico pelo seu SHA256, verifica o
  manifesto e fixa **66 fontes = 52 fontes AUTH-03 + 13 complementares + manifesto**.
- Os dois controlos são o Dockerfile APP-02 e o Dockerignore APP-03, pelos hashes
  completos acima: **68 ficheiros no contexto materializado**.
- `materialize_context()` lê e confere todas as fontes antes de criar um destino
  novo, privado e exterior ao repositório. Não faz descoberta dinâmica de Python.
- `verify_context()` percorre fisicamente o destino e compara conjunto e hashes,
  independentemente do matcher e da cópia. Partilha o inventário esperado; não é
  uma segunda autoridade de aprovação.
- Symlinks, tipos irregulares e alterações dos bytes atestados são recusados;
  ficheiros não listados na origem são excluídos. Ficheiros adicionais ou hashes
  divergentes no destino são recusados.
- FIX01 importa do auxiliar histórico **exclusivamente `dockerignore()`**. O
  auxiliar histórico não importa FIX01; não existe ciclo entre ambos. Os testes
  podem importar ambos, além da ponte e dos modelos offline.
- `allowed_sources()` recusa sempre com
  `HISTORICAL_SOURCE_API_DISABLED_USE_FIX01`.
- `proposed_compose()` recusa sempre com
  `HISTORICAL_COMPOSE_API_DISABLED_USE_FIX01`.
- Não há delegação automática dessas APIs, descoberta alternativa ou fallback
  para a raiz. Os descritores antigos permanecem apenas nos arquivos históricos.
- O template Compose atual não tem imagem nem build e é inválido por defeito.
  A geração exige projeto explícito, imagem por digest e UID/GID decimais não
  zero, sem interpolação. O descritor validado conserva `network_mode: none`,
  ausência de portas/mounts/secrets operacionais e entrada `exit 78`.

A validação de parâmetros pertence ao auxiliar. O Compose não impõe
universalmente esse verificador a administradores que forneçam outros ficheiros
ou overrides. O CLI `check-context` elimina o contexto temporário após verificar;
não existe ainda ligação executável desse contexto a um Docker build.

## Evidência offline

ATTEST02: **170 passed, 2 deselected in 2.73s**, nos dois ficheiros de testes
indicados acima, numa cópia privada, com conexões e subprocessos bloqueados.
Foram verificadas recusas antes de I/O/migrações, rejeição do Compose histórico,
sentinela Python sem expansão das 66 fontes, materialização e verificação física,
preservação do formatador e template inválido com `exit 78`.

Log privado de referência:
`/tmp/livenet-dev09-attest02-e0yjrhn8/offline-tests.log`.
SHA256: `26d3a1c1f714c91dea60259f02d714042d2c6623df6a2c7c8e1ad3eec43402d6`.
O caminho temporário não é um arquivo durável nem uma dependência de runtime.

Os testes seguintes ficaram intactos e foram classificados como não aplicáveis
ao estado posterior à aplicação, porque exigem preimagens antigas:

- `backend/tests/test_dev09fix01_packaging.py::test_patch_files_have_one_protected_target_each`.
- `backend/tests/test_dev09a2_integration.py::test_patch_is_unapplied_and_exact`.

ATTEST03 não repete a suite; verifica hashes, integridade, código das recusas e
preservação do repositório. A análise estática anterior demonstrou COPY sobre as
66 fontes e lock de 14 distribuições. Instalação e imports dinâmicos de uma imagem
construída não foram demonstrados.

## Referências históricas preservadas

Não atualizar em lugar os seguintes artefactos congelados:

| Referência | SHA256 do artefacto histórico |
| --- | --- |
| `docs/operations/dev09a2-complementary.NOT-APPROVED.json` | `bc0982d34e74c3c7838742cee9d3385225ddb749491b6c906cc04b55761f4db5` |
| `docs/operations/dev09a2-evidence.json` | `7957d23e1c03aadbbf8a02e0da61c082c5d115673fc1cd69d84c44302b84833a` |
| `docs/operations/proposals/dev09a2/proposal-index.json` | `705d9ef378222060953e5fe00c3c65fa78c8749772b3382f97d353998881fe03` |
| `docs/operations/proposals/dev09a2/protected-changes.NOT-APPROVED.patch` | `ad2c67c2d9859e780e1c224610d19cc7345b170cbb8d24233a56e6334a0bbef5` |

O candidato, em `auxiliary_review_sources`, e a evidência DEV-09A.2 conservam:

| Fonte | Hash DEV-09A.2 | Hash intermédio ATTEST01, substituído por ATTEST02 |
| --- | --- | --- |
| `scripts/dedicated/dev09a2_packaging.py` | `993ed7930ab15a1074c8df7a79b5f0317d9079c4273ee354916b65d04841dccc` | `d61a253b8a92209145055526b92611da87acb9d0042da327ba040c5fdb9681bc` |
| `backend/tests/test_dev09a2_integration.py` | `a6c4b48cc2809ab5e5521976fef8b2be528f8b35874746f28e7723999a203ef0` | `b262dd71c25b3680fe93fd89c01c408660f33a8b38b08b949b69696f88aaee56` |

As preimagens e propostas antigas de APP-01/03 nesses registos não descrevem os
bytes FIX01 aplicados. O Dockerfile APP-02 proposto corresponde aos bytes finais,
mas a sua preimagem histórica já não é o ficheiro atual. O relatório
`docs/operations/dev09a2-integration-closure.md`, nomeadamente a afirmação antiga
de contexto fechado, deve ser lido com esta reconciliação e as correções FIX01.
Não promover globalmente o índice de seis propostas a "aplicado".

Este documento acrescenta a relação entre estados; não substitui hashes
históricos, não altera a vinculação do candidato consumido por FIX01 e não
regenera manifestos.

## Integridade, limitações e condições antes de build

Baseline ATTEST03: branch `main`, HEAD
`647179c928888adfeef0f69f582fd13c5fc17350`; índice SHA256
`50d32095da16e2c0e985226625971e890c33d406cbb9b97743a7198905b9541e`.
AUTH-03 válido **52/52**, manifesto ativo
`4819c697b7d12f7ab5cbb1fdfa9cf4c3fd0e98e93b53a60337296cc84036fc29`;
APP-04 **7/7**; F02/G2/G4 fechados. A divergência `f066`/`f067`, lacunas de
autoridade e contratos originais não localizados continuam abertas.

A baseline privada E01 permite comparar os ignorados antes/depois da operação;
não demonstra ausência de alterações desde APPLY-PREP. Fontes locais não
versionadas continuam a exigir preservação explícita: HEAD isoladamente não
reproduz todo o conjunto. Verificações por hashes não impedem um administrador
do host de substituir o processo ou os ficheiros depois da verificação.

Antes de qualquer build controlado, são ainda necessários:

1. Nova autorização humana limitada ao build e respetivos efeitos; nenhuma está
   implícita neste registo.
2. Revalidar fontes, controlos, auxiliares aprovados, base e lock pelos hashes
   fixados; preservar ou arquivar evidência para reprodução.
3. Preparar e rever a ligação exclusiva do contexto materializado/verificado ao
   builder, sem aceitar a raiz do repositório como alternativa.
4. Definir e rever permissões, acesso à rede/cache, aquisição das dependências,
   destino da imagem e limpeza restrita aos artefactos novos autorizados.
5. Inspecionar o contexto efetivamente enviado e validar a imagem resultante,
   instalação com hashes, dependências, utilizador e entrada inerte, sem a
   apresentar como autorizada para serviços ou migrações.

AUTH-BOOT-02 e DEV-09B continuam a exigir decisões e autorizações próprias.
ATTEST03 limita-se a este documento; não modifica contratos, fontes aprovadas,
artefactos históricos, índice ou ficheiros ignorados.
