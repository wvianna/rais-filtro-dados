# RAIS · Filtro de Dados

> Sistema de consulta e análise da base RAIS (vínculos) — implementação de
> referência conforme [`docs/realtoriotecnico.txt`](docs/realtoriotecnico.txt).

**Versão** `1.0.0` · **Requisitos** Python 3.10+ · **Dependências** apenas a biblioteca padrão (stdlib).

---

## 1. Visão geral

O sistema processa arquivos da base RAIS de vínculos e, usando os layouts
oficiais (`layout/`), identifica para uma combinação de **município + subclasse
CNAE 2.0**:

- número de **estabelecimentos (empresas)** do ramo no município;
- número de **funcionários por empresa**;
- número **total de funcionários (vínculos)**;
- **estatística do grau de escolaridade**, com os valores "Ignorados"
  (`-1` / `{ñ class}`) separados em categoria própria.

### Decisões de arquitetura atendidas (`docs/realtoriotecnico.txt`, item 2)

- **Processamento streaming** — arquivos de 5 GB+ são lidos linha a linha,
  nunca carregados integralmente em memória.
- **Seleção dinâmica do arquivo-base** — o arquivo parcial (KB) serve para
  desenvolvimento/CI e o completo (5 GB+) para produção.
- **Indexação persistente (SQLite)** dos campos de alta cardinalidade
  (município e subclasse) para consultas repetidas performáticas.
- **Tipagem das variáveis como STRING** (preserva zeros à esquerda).
- **Tratamento explícito** de `-1`, `{ñ class}` e `{ñclass}` como "Ignorado".

---

## 2. Entregáveis

| Item | Descrição |
|---|---|
| `src/rais/` | Pacote Python (motor de dados + API + CLI) |
| `web/` | Frontend web (HTML/CSS/JS, sem build) |
| `scripts/` | Scripts utilitários (`run_server.py`, `make_sample.py`, `start.sh`, `stop.sh`) |
| `tests/` | Suíte de testes automatizados (43 testes) |
| `docs/` | Especificação técnica e manual de uso |
| `README.md` | Este documento |
| `.gitignore` | Arquivos ignorados pelo controle de versão |
| `Makefile` | Atalhos (`files`, `sample`, `analyze`, `index`, `start`, `stop`, `serve`, `test`) |
| `requirements.txt` | Dependências (nenhuma obrigatória) |

### Resultado do caso de uso de referência (validação automatizada)

- Filtros: município `330100` (Campos dos Goytacazes/RJ) · subclasse `2342702`
  (fabricação de artefatos de cerâmica e barro cozidos, exceto azulejos e pisos).
- Resultado na amostra: **3 estabelecimentos** (10, 5 e 3 funcionários) e
  **19 vínculos** (detalhes em [`docs/manual.md`](docs/manual.md)).

---

## 3. Estrutura do projeto

```text
dados/                              Arquivos de entrada (CSV)
  RAIS_VINC_PUB_MG_ES_RJ_parcial.csv                (~66 KB  · dev/CI)
  RAIS_VINC_PUB_MG_ES_RJ.csv-chunking-*.csv         (~4,7 GB · produção)
  amostra_com_identificador.csv                     (gerado por make sample)
layout/                             Taxonomias oficiais (municípios, CNAE 2.0,
                                    escolaridade, causas, natureza jurídica…)
src/rais/
  config.py     Configuração (caminhos, codificação, nomes lógicos)
  schema.py     Normalização de cabeçalho e detecção de separador
  domains.py    Taxonomias e tratamento de valores "Ignorado"
  reader.py     Leitura streaming (linha a linha) e leitura por offsets
  analyzer.py   Motor de análise (filtros + agregações + exceções)
  index.py      Índice persistente SQLite (município + subclasse)
  files.py      Descoberta e metadados dos arquivos de dados
  server.py     Servidor HTTP (API JSON + frontend)
  cli.py        Interface de linha de comando
  sample.py     Gerador de amostra determinística com Identificad
web/                                Frontend (index.html, styles.css, app.js)
scripts/                            run_server.py, make_sample.py, start.sh, stop.sh
tests/                              Suíte de testes (unittest, stdlib)
run/                                (gerado) pidfile e log do servidor
```

---

## 4. Como executar

### 4.1 Interface web (recomendada)

```bash
make start                 # inicia em segundo plano (pid em run/server.pid)
# ou: ./scripts/start.sh   # opções: --port 9000 --host 0.0.0.0 --foreground
```

Acesse <http://127.0.0.1:8000/>. Selecione o arquivo de base, informe
município e/ou subclasse (há autocompletar) e clique em **Analisar**.

```bash
make stop                  # encerra o serviço
# ou: ./scripts/stop.sh
```

> Alternativa em primeiro plano (Ctrl+C para parar):
> `make serve` ou `python3 scripts/run_server.py --port 8000`.

### 4.2 Linha de comando

```bash
export PYTHONPATH=src
python3 -m rais files                                   # lista arquivos
python3 -m rais analyze --file dados/RAIS_VINC_PUB_MG_ES_RJ_parcial.csv \
        --municipio 330100 --subclasse 2342702          # análise
python3 -m rais analyze --file dados/amostra_com_identificador.csv --json
python3 -m rais index --file dados/amostra_com_identificador.csv  # índice
python3 -m rais layouts --tipo escolaridade             # taxonomias
```

### 4.3 Amostra de validação (com coluna de identificação)

```bash
make sample    # cria dados/amostra_com_identificador.csv
```

---

## 5. Caso de uso de referência (2342702 em 330100)

```bash
make analyze
# python3 -m rais analyze --file dados/amostra_com_identificador.csv \
#        --municipio 330100 --subclasse 2342702
```

Resultado esperado na amostra:

| Métrica | Valor |
|---|---|
| Empresas/estabelecimentos | 3 (`01000000000100` [10], `02000000000200` [5], `03000000000300` [3]) |
| Vínculos totais | 19 |
| Vínculos considerados (TIPO ESTBL válido) | 18 |
| Distribuição de escolaridade | 11 níveis (1..11) + "Informação Não Disponível/Ignorada" |

> **Importante — contagem de empresas na base fornecida:** os arquivos RAIS
> fornecidos (parcial e completo) **não** contêm a coluna de identificação do
> estabelecimento (`IDENTIFICAD`/CNPJ). Sem ela é impossível distinguir
> estabelecimentos; o sistema reporta "indisponível" com aviso claro, mantendo
> corretas as métricas de vínculos e escolaridade. Para validar a contagem,
> use `make sample` ou a base RAIS oficial completa (o sistema detecta a
> coluna automaticamente quando presente).

---

## 6. Testes

```bash
make test
# PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Suíte com **43 testes** usando apenas `unittest` (stdlib). Cobertura:
normalização de colunas, detecção de separador, taxonomias, leitura streaming,
motor de análise (caso de referência + arquivo parcial), índice SQLite e API
do servidor. Os testes criam amostras em diretório temporário e não alteram os
dados originais. A suíte também roda sob `pytest` (caso instalado).

### CI/CD

O arquivo **parcial** (KB) deve ser a fonte dos testes e da integração
contínua; o arquivo **completo** (5 GB+) é reservado ao ambiente de produção
(`docs/realtoriotecnico.txt`, item 2).

---

## 7. Limites e boas práticas

- A leitura é **streaming** (memória constante). Evite abrir o arquivo completo
  em planilhas.
- Para consultas repetidas sobre a base de 5 GB, construa o índice
  ("Construir índice" na web ou `python3 -m rais index --file ...`); a análise
  passa a ler somente as linhas candidatas via `seek`.
- Variáveis de código (município, CNAE, escolaridade) são tratadas como
  **STRING** — nunca converta para inteiro (perde zeros à esquerda).
- `-1`, `{ñ class}`, `{ñclass}` e vazios são tratados como "Ignorado" e
  segregados da base de cálculo dos níveis definidos.

---

## 8. Documentação adicional

| Documento | Conteúdo |
|---|---|
| [`docs/especificacao.md`](docs/especificacao.md) | Especificação técnica (requisitos, arquitetura, mapeamento, decisões) |
| [`docs/manual.md`](docs/manual.md) | Manual de uso (CLI, web, amostra, índice, exemplos) |
| [`handsoff.md`](handsoff.md) | Handoff para o próximo agente (continuação do desenvolvimento) |
| [`docs/realtoriotecnico.txt`](docs/realtoriotecnico.txt) | Dicionário técnico de dados RAIS (fonte dos requisitos) |
| [`docs/textoinicial.txt`](docs/textoinicial.txt) | Enunciado original do problema |

---

*RAIS · Filtro de Dados — implementação de referência conforme
`docs/realtoriotecnico.txt` · stdlib-only · 2026.*

