# R1-PROTO-01 — núcleo estrutural offline

Implementa apenas parsing e validação estrutural. Não está ligado a Flask,
PostgreSQL, credenciais, transporte, autoridade ou executores. Não faz I/O.
Uma instância `ParsedCandidateEnvelope`, mesmo construída diretamente, é apenas
dados: nunca é uma capacidade ou aprovação. Não integrar em gates.

## Contrato preservado

Fonte: `docs/architecture/auth-boot-02-r1.md`, §§4 e 7, após CONSOLIDAÇÃO-D.
Envelope fechado (`payload`, `signature_hex`), exatamente os 25 campos,
`protocol_version="1"`, assinatura hexadecimal minúscula de 128 caracteres,
16 KiB de payload, 32 KiB de envelope e profundidade máxima oito.
Parsing sem duplicados (incluindo nomes equivalentes por escapes), constantes
não JSON, UTF-8 inválido, surrogates isolados ou conteúdo adicional.
As relações temporais aprovadas são verificadas sem consultar relógio.

## Perfil candidato — NÃO APROVADO

`R1-PROTO-01-CANDIDATE-1` fixa escolhas locais ainda sujeitas a revisão:

| Campo/regra | Escolha candidata |
| --- | --- |
| Tipos | Todos os 25 valores são strings. |
| `signature_algorithm` | Literal `Ed25519`. Não há negociação nem fallback. |
| Três campos `*_sha256` | 64 caracteres hexadecimais minúsculos. Só representação; não verifica conteúdo ou relações entre digests. |
| `trust_policy_version`, epochs | Decimal sem sinal nem zeros iniciais, 1–20 algarismos; zero permitido. |
| Três instantes | Segundos inteiros desde Unix epoch em UTC, na mesma representação decimal. Sem frações. |
| Outros identificadores/catálogos | 1–128 caracteres ASCII visíveis, sem espaço. Sem presumir UUID, catálogo de operações ou equivalência F03/F04. |
| Contagem de bytes | Envelope: todos os bytes recebidos, incluindo whitespace. Payload: bytes originais do seu valor JSON, incluindo whitespace interno e escapes; exclui separadores externos. Não usa reserialização. |
| Profundidade | Objetos/arrays; raiz do envelope = 1 e objeto payload = 2. Strings/escapes não aumentam profundidade. |
| Entrada | Apenas `bytes` UTF-8; BOM recusado. JSON não canónico pode passar a estrutura. |

Os limites de bytes são limites do contrato; esta forma concreta de contagem
continua candidata. O perfil não define schemas de destino/plano, composição do
digest global, fonte temporal, frescura, monotonicidade ou valores autoritativos
de epochs. Validação estrutural não prova unicidade de IDs ou de tentativa.
GAP-008/009/018 continuam abertas; não se recuperaram contratos históricos.

Não implementa JCS RFC 8785, Ed25519, verificação de assinatura ou construção de
bytes assinados. `SIGNING_DOMAIN` conserva apenas o prefixo aprovado, incluindo
NUL. `json.dumps(sort_keys=True)` não é apresentado como JCS. Sem geração de
chaves. O exemplo tem assinatura fictícia e não é um vetor criptográfico.

## Utilização e testes

Na raiz do repositório:

```python
from protocols.auth_boot_r1 import parse_candidate_envelope
parsed = parse_candidate_envelope(wire_bytes)
```

```sh
python3 -B -m unittest discover -s protocols/auth_boot_r1/tests -v
```

Testes usam apenas a biblioteca padrão e dados locais. Não consultam serviços,
não escrevem ficheiros e não verificam gates operacionais.
