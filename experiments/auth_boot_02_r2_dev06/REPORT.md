# R2-DEV-06 — estudo arquitetural e documental

Data de elaboração: 2026-10-27 (Europe/Lisbon; não é atestado UTC).
Estado: estudo entregue; recomendações pendentes de aprovação e demonstração.
Repositório: `progbox:/home/paulo/projects/livenet-v2`.
HEAD observado: `647179c928888adfeef0f69f582fd13c5fc17350`.

## Resultado e decisão recomendada

A cessação SQL no original não retira a capacidade de escrita de uma cópia do
recurso. DEV-05 conserva o contraexemplo decisivo: original em epoch 2, zero
efeitos; clone vivo em epoch 1, um efeito antigo depois da cessação local.
`distributed_cessation_proven=false`. Um recibo assinado dessa operação local
continuaria a provar apenas o seu alcance local.

Recomenda-se estudar uma fronteira obrigatória no serviço de dados e nos seus
meios de persistência, fora do domínio de cópia dos executores, com controlo
externo de todas as escritas, identidade autenticada, continuidade protegida e
segregação administrativa. A combinação candidata usa esse recurso externo,
admissão/consumo independentes e fencing imposto pelo recurso ou pelo seu
armazenamento; identidade não exportável é defesa complementar.

Esta recomendação é condicional: se o adversário puder copiar integralmente o
recurso e continuar a escrever num disco independente, nenhum fence no original
impede esse efeito físico. Não se redefine esse efeito como irrelevante para
declarar satisfeitos C4/C6. O critério forte de DEV-05 permanece pendente; qualquer
restrição do domínio de efeito necessita de aprovação explícita. Sem cobertura
comprovada, confirmação de takeover e reentrada continuam bloqueadas.

## Documentos

- [Arquitetura e alternativas](ARCHITECTURE.md): fronteira, ameaça/confiança,
  comparação, candidata, obrigações de prova e atestado conceptual de cessação.
- [Aceitação e validação independente](VALIDATION.md): critérios, oráculos,
  cenários futuros, dependências, custos e decisões a aprovar.
- [Fontes e preservação](PROVENANCE.md): acesso/instruções, proveniência dos
  resultados históricos, hashes, âmbito e verificação documental desta entrega.

## Base factual e limites

| Fonte lida | Resultado histórico relevante | Consequência arquitetural |
| --- | --- | --- |
| DEV-02, REPORT/evidence | 36 testes; cópia da referência permite duas admissões; SQL direto permite dois UPDATE | Estado autoritativo único não controla sozinho os efeitos |
| DEV-03, REPORT/evidence | 37 testes; copiar autoridade/referência/alvo produz um efeito em cada ramo; serviço privilegiado contorna broker | O controlo tem de cobrir todos os recursos e caminhos |
| DEV-04, REPORT/evidence | 63 testes; perda real do backend da âncora permite SQL/commit antigo depois do fence | Uma verificação ou lock externo separado do efeito deixa uma janela |
| DEV-05, REPORT/evidence | 2 contraexemplos DEV-04 mais 34 testes novos; fence transacional local fecha essas janelas; clone continua a escrever | Cessação local não prova cessação distribuída |

Contagens pertencem às execuções anteriores; testes de contraexemplo passam
quando observam a falha esperada. Nenhum teste foi executado nesta etapa.
DEV-05 regista `tests=34` na bateria nova e `baseline_dev04.tests=2` separadamente;
o total histórico é 36, sem somar execuções iniciais ou relatórios anteriores.
D09 independente, UTC autenticado e fencing incondicional permanecem ausentes.

## Autoridade e próximo passo proposto

A autorização atual cobre a produção deste estudo documental isolado. C1–C7
continuam baseline candidata aprovada documentalmente; a candidata aqui descrita,
o seu schema, produtos, custódios, parâmetros e implantação não estão aprovados.
AUTH-03/F02/G2/G4 permanecem fechados; GAP-001/002 abertas; DEV-09B não autorizada.

Propõe-se R2-DEV-07 como revisão independente documental: decidir a fronteira
exata do efeito, inventário de recursos/cópias, adversário administrativo e
custódios, e rever as obrigações de prova. Só depois, mediante autorização
específica, preparar um laboratório separado que mantenha o clone antigo vivo
tentando escrever após takeover. Esta proposta não autoriza esse laboratório,
infraestrutura, integração, HA ou abertura de gates.

Foram criados apenas documentos nesta pasta. Sem testes novos, instalações,
provisionamento, SQL, alterações operacionais, contratos alterados, commits ou push.
