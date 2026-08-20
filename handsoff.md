# Handoff · RAIS Filtro de Dados

> Documento de passagem de bastão para o **próximo agente** dar continuidade ao
> desenvolvimento **sem precisar ler todo o código**. Leia este arquivo
> primeiro; depois consulte [`docs/especificacao.md`](docs/especificacao.md) e
> [`docs/manual.md`](docs/manual.md) para detalhes.

---

## 1. O que é este projeto

Sistema **web + CLI** para consulta/análise da base **RAIS (vínculos)**.
Dado um arquivo CSV da RAIS e os layouts oficiais (`layout/`), responde a
perguntas do tipo:

- quantas **empresas** de uma subclasse CNAE 2.0 existem em um **município**;
- **funcionários por empresa** e **total de vínculos**;
- **distribuição de escolaridade** (com valores `-1`/`{ñ class}` segregados).

**Stack:** Python 3.10+ **stdlib only** (csv, sqlite3, http.server, unittest,
json). Frontend vanilla JS/HTML/CSS **sem build**. Sem dependências externas.

---

## 2. Como rodar (resumo)

```bash
make test        # 43 testes (unittest, stdlib) — deve passar
make sample      # gera dados/amostra_com_identificador.csv
make analyze     # caso de referência 330100 · 2342702
make start       # inicia servidor web em 2º plano (PID em run/server.pid)
make stop        # encerra
make serve       # servidor em 1º plano (Ctrl+C)
```

> `start.sh` **instala o ambiente automaticamente**: cria `.venv/` (se ausente)
> e instala `requirements.txt` antes de iniciar (`--skip-install` pula).
> Windows: `scripts/start.bat` / `scripts/stop.bat` (mesmo comportamento).

- CLI direta: `export PYTHONPATH=src && python3 -m rais ...`
  (`files`, `schema`, `analyze`, `index`, `layouts`, `serve`).
- Web: <http://127.0.0.1:8000/> — seleciona arquivo-base, autocompleta
  município/subclasse, botão "Analisar", tema claro/escuro no cabeçalho.

---

## 3. Mapa do código

| Arquivo | Responsabilidade | Pontos de atenção |
|---|---|---|
| `src/rais/config.py` | Caminhos, codificações, **nomes lógicos das colunas** (aliases) | Coluna de empresa = `identificador_estabelecimento` (alias `Identificad`/`IDENTIFICAD`/`CNPJ/CEI`) |
| `src/rais/schema.py` | Normalização de cabeçalho, detecção de separador, mapeamento lógico | `normalize_token` remove acentos/caixa e **junta** "2.0"→"20" |
| `src/rais/domains.py` | Taxonomias (município, CNAE 2.0, escolaridade) e `is_ignored()` | `is_ignored` trata `-1`, `{ñ class}`, `{ñclass}`, vazio |
| `src/rais/reader.py` | Leitura **streaming** + leitura por offsets (`seek`) | Nunca carrega o arquivo inteiro na RAM |
| `src/rais/analyzer.py` | Motor: filtros, vínculos, empresas, escolaridade | **Lógica central do caso de uso** (item 5 do dicionário); estimativa por chave composta quando não há `Identificad` |
| `src/rais/index.py` | Índice persistente SQLite `(file,municipio,subclasse,offset)` | Consulta via índice lê só linhas candidatas |
| `src/rais/files.py` | Lista arquivos de `dados/` (parcial/completa) | Limiar "completa" = 500 MiB |
| `src/rais/server.py` | API JSON + estáticos (http.server) | Endpoints na seção 5 |
| `src/rais/cli.py` | CLI (`python -m rais`) | — |
| `src/rais/sample.py` | Gera amostra determinística **com coluna `Identificad`** | `EXPECTED` contém os números esperados |
| `web/` | `index.html`, `styles.css`, `app.js` | Tema claro/escuro via `data-theme`; spinner de processamento (`#processing`); pizza em canvas com legenda interativa (hover destaca a fatia); estimativa `≈` no card |
| `scripts/start.sh` / `stop.sh` | Subir/derrubar serviço (PID/log em `run/`) | `run/` é gitignorado |
| `scripts/make_sample.py`, `run_server.py` | Utilitários | — |

---

## 4. Fatos críticos sobre os dados (NÃO pular)

1. **Separador real é vírgula `,`** — o layout cita `;`, mas os arquivos
   fornecidos usam `,`. O sistema detecta automaticamente.
2. **Encoding**: dados RAIS = **latin-1**; layouts (`layout/`) = **UTF-8**.
   `config.py` define os padrões.
3. **Nenhum dos arquivos fornecidos tem coluna de identificação do
   estabelecimento** (`Identificad`/CNPJ) — verificado: 62 colunas no parcial
   e no completo (5 GB). Consequência: sem essa coluna a contagem de empresas
   passa a ser uma **ESTIMATIVA (≈) por chave composta** (decisão do usuário),
   agrupando os atributos de nível-empresa listados em
   `config.py::ESTIMATIVA_EMPRESA_FIELDS` e rotulando o resultado como
   aproximado na interface. Com a coluna presente, a contagem é **exata**.
   Vínculos e escolaridade são sempre exatos.
4. Para validar a contagem **exata** de empresas, use **`make sample`**
   (`dados/amostra_com_identificador.csv`, 63 colunas = 62 + `Identificad`).
   O sistema detecta a coluna automaticamente quando presente.
5. Códigos (município, CNAE, escolaridade) são **STRING** — nunca converter
   para inteiro (perde zeros à esquerda).
6. Arquivo parcial = 299 linhas (66 KB) → **usar em dev/CI**. Arquivo completo
   (`RAIS_VINC_PUB_MG_ES_RJ.csv-chunking-*.csv`, ~4,7 GB) → **produção**.

### Caso de referência (esperado na amostra)

Filtros `municipio=330100` · `subclasse=2342702`:

- **3 estabelecimentos**: `01000000000100` [10], `02000000000200` [5],
  `03000000000300` [3];
- **19 vínculos** (18 considerados para empresas — o 19º tem TIPO ESTBL `-1`);
- Escolaridade: 11 níveis + 2 ignorados (`-1`).

---

## 5. API do servidor

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/health` | status + versão |
| GET | `/api/files` | lista de arquivos de dados |
| GET | `/api/layouts?tipo=&busca=&limit=` | taxonomias (escolaridade/subclasse/municipio) |
| GET | `/api/schema?file=` | colunas + campos lógicos presentes/ausentes |
| GET | `/api/index?file=` | status do índice |
| POST | `/api/index` `{file}` | constrói índice |
| POST | `/api/analyze` `{file,municipio,subclasse,use_index}` | análise |

Respostas JSON UTF-8, CORS liberado. Estáticos: `/`, `/styles.css`, `/app.js`.

---

## 6. Convenções do projeto

- Documentação e comentários em **pt-BR**; identificadores em inglês.
- **Só stdlib** — não adicionar dependências sem necessidade real.
- Testes com **`unittest`** em `tests/` (também rodam sob pytest).
  - Fixtures em `tests/support.py` (`TempSampleDir` cria amostra temporária).
- Builds/scripts em `scripts/`; atalhos no `Makefile`.
- Arquivos gerados ignorados: `.rais_index/`, `run/`, `dados/amostra_*.csv`,
  `.venv/`, `*.log`.
- O repositório já está em Git (`main`) com remoto no GitHub
  (wvianna/rais-filtro-dados).

---

## 7. Limitações conhecidas e armadilhas

- **Contagem de empresas exige coluna `Identificad`** (ver seção 4).
- Índice: construído por `(file, municipio, subclasse)`. Se o arquivo não tiver
  coluna de município, `build_index` falha com erro claro (use varredura).
- `reader.iter_rows_with_offsets` pressupõe **sem quebras de linha embutidas**
  (verificado nos dados). Se aparecerem, o modo de índice deve desativar
  (erro orienta a usar `use_index=False`).
- A 1ª varredura da base de 5 GB (sem índice) leva alguns minutos; com índice,
  consultas por (município, subclasse) são rápidas.
- O `stop.sh` lê `run/server.pid`; se o processo foi morto externamente, ele
  apenas remove o pidfile.

---

## 8. Próximos passos sugeridos (TODO)

- [ ] **Produção real**: validar contagem de empresas na base RAIS oficial
  completa (que possui a coluna `Identificad`) — hoje a base fornecida não tem.
- [ ] Endpoint/página de **exportação CSV/JSON** dos resultados da análise.
- [ ] **Testes de carga/benchmark** da varredura do arquivo de 5 GB
  (medir tempo e pico de memória).
- [ ] Barra de **progresso** para varreduras longas (callback já existe no
  reader, falta expor via API/SSE).
- [ ] `robots.txt`/`favicon` (o servidor já responde 404 para `/favicon.ico`).
- [ ] CI (GitHub Actions): `make test` no push; usar o arquivo **parcial**.
- [ ] Autenticação simples antes de expor em rede (`--host 0.0.0.0` hoje é
  aberto).
- [ ] Cobertura de testes para `start.sh`/`stop.sh` (script de integração).

---

## 9. Contatos / referências

- Especificação técnica: [`docs/especificacao.md`](docs/especificacao.md)
- Manual de uso: [`docs/manual.md`](docs/manual.md)
- Dicionário técnico RAIS (fonte dos requisitos):
  [`docs/realtoriotecnico.txt`](docs/realtoriotecnico.txt)
- Enunciado original: [`docs/textoinicial.txt`](docs/textoinicial.txt)
