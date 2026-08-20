# Estatística do Código — RAIS · Filtro de Dados

> Métricas da base de código do projeto, coletadas em **20/08/2026**.
> Contagem de linhas: código (exclui linhas em branco e comentários),
> total (todas as linhas físicas).

---

## 1. Visão geral

| Métrica | Valor |
|---|---|
| Arquivos considerados | **35** |
| Linhas totais | **4.886** |
| Linhas de código | **3.887** |
| Linhas em branco | **740** |
| Funções (Python) | **135** |
| Classes (Python) | **25** |
| Testes automatizados | **45** (todos passando) |

```
Distribuição por tipo de código:
┌──────────────────────────────────────────────────────┐
│ Backend (src/rais)      ████████████  1.532 (39%)    │
│ Frontend (web)          █████████████  1.189 (31%)   │
│ Docs e raiz             ██████           563 (15%)   │
│ Testes (tests)          ████            350  (9%)    │
│ Scripts (scripts)       ███             253  (7%)    │
└──────────────────────────────────────────────────────┘
```

---

## 2. Backend — `src/rais/` (12 arquivos, 1.532 linhas de código)

| Módulo | Linhas | Código | Funções | Classes | Responsabilidade |
|---|---:|---:|---:|---:|---|
| `analyzer.py` | 355 | 286 | 7 | 3 | Motor de análise (filtros, empresas, escolaridade) |
| `server.py` | 248 | 208 | 18 | 3 | Servidor HTTP (API JSON + estáticos) |
| `cli.py` | 207 | 173 | 9 | 0 | Interface de linha de comando |
| `domains.py` | 183 | 130 | 12 | 2 | Taxonomias e valores "Ignorado" |
| `config.py` | 173 | 128 | 0 | 1 | Configuração (caminhos, colunas lógicas) |
| `index.py` | 172 | 147 | 5 | 0 | Índice persistente SQLite |
| `sample.py` | 172 | 143 | 4 | 0 | Gerador de amostra com `Identificad` |
| `schema.py` | 145 | 115 | 10 | 1 | Normalização de colunas e separador |
| `reader.py` | 140 | 117 | 5 | 1 | Leitura streaming e por offsets |
| `files.py` | 89 | 74 | 4 | 1 | Descoberta de arquivos de dados |
| `__init__.py` | 8 | 6 | 0 | 0 | Metadados do pacote |
| `__main__.py` | 8 | 5 | 0 | 0 | Entrypoint (`python -m rais`) |

---

## 3. Testes — `tests/` (8 arquivos, 350 linhas de código, 45 testes)

| Arquivo | Linhas | Código | Testes | Cobre |
|---|---:|---:|---:|---|
| `test_analyzer.py` | 94 | 68 | 12 | Motor de análise (referência + parcial + estimativa) |
| `test_server.py` | 95 | 74 | 9 | API HTTP (health, files, layouts, schema, analyze, index) |
| `test_domains.py` | 68 | 47 | 9 | Taxonomias e valores "Ignorado" |
| `test_schema.py` | 50 | 34 | 6 | Normalização, separador, mapeamento |
| `test_index.py` | 70 | 57 | 5 | Índice SQLite e equivalência índice×varredura |
| `test_reader.py` | 46 | 34 | 4 | Leitura streaming e offsets |
| `support.py` | 49 | 35 | — | Fixtures (amostra temporária) |
| `__init__.py` | 1 | 1 | — | — |

**Execução:** `make test` → `Ran 45 tests ... OK` (apenas `unittest`, stdlib; também roda sob `pytest`).

---

## 4. Frontend — `web/` (3 arquivos, 1.189 linhas de código)

| Arquivo | Linhas | Código | Conteúdo |
|---|---:|---:|---|
| `styles.css` | 643 | 581 | Temas (claro/escuro), tooltips, spinner, pizza, layout |
| `app.js` | 505 | 444 | Lógica: análise, índice, pizza, legenda interativa, exportação CSV |
| `index.html` | 182 | 164 | Estrutura da interface |

---

## 5. Scripts — `scripts/` (6 arquivos, 253 linhas de código)

| Arquivo | Linhas | Código | Finalidade |
|---|---:|---:|---|
| `start.sh` | 122 | 81 | Inicia serviço (Linux/macOS); instala o ambiente |
| `start.bat` | 69 | 61 | Inicia serviço (Windows) |
| `stop.sh` | 48 | 30 | Encerra serviço (Linux/macOS) |
| `stop.bat` | 35 | 30 | Encerra serviço (Windows) |
| `run_server.py` | 38 | 27 | Servidor em primeiro plano |
| `make_sample.py` | 36 | 24 | Gera a amostra de validação |

---

## 6. Documentação e raiz (6 arquivos, 563 linhas de código)

| Arquivo | Linhas | Código | Conteúdo |
|---|---:|---:|---|
| `README.md` | 228 | 150 | Documentação principal (com índice/TOC) |
| `docs/especificacao.md` | 201 | 145 | Especificação técnica |
| `docs/manual.md` | 182 | 112 | Manual de uso |
| `handsoff.md` | 168 | 120 | Handoff para o próximo agente |
| `Makefile` | 48 | 36 | Atalhos de build/teste |
| `requirements.txt` | 8 | 0 | Dependências (stdlib — nenhuma obrigatória) |

---

## 7. Complexidade por módulo (funções + classes — Python)

| Módulo | Funções | Classes | Total |
|---|---:|---:|---:|
| `server.py` | 18 | 3 | 21 |
| `analyzer.py` | 7 | 3 | 10 |
| `domains.py` | 12 | 2 | 14 |
| `schema.py` | 10 | 1 | 11 |
| `cli.py` | 9 | 0 | 9 |
| `index.py` | 5 | 0 | 5 |
| `reader.py` | 5 | 1 | 6 |
| `sample.py` | 4 | 0 | 4 |
| `files.py` | 4 | 1 | 5 |
| `config.py` | 0 | 1 | 1 |
| **Total (src)** | **74** | **12** | **86** |
| **Total (tests)** | **61** | **13** | **74** |

---

## 8. Observações

- O sistema é **100% stdlib** (Python): sem dependências externas de runtime.
- Arquivos de dados (`dados/`, incluindo a base de ~5 GB) **não** entram nesta
  contagem — são dados de entrada, não código.
- A contagem de "código" desconsidera linhas em branco e comentários;
  a de "linhas" considera todas as linhas físicas.
- Métricas de funções/classes usam a **AST** do Python (análise precisa, não
  regex).
