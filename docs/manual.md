# RAIS · Filtro de Dados — Manual de Uso

Guia prático de operação do sistema (interface web, linha de comando e
utilitários). Para os detalhes de arquitetura, veja
[`especificacao.md`](./especificacao.md).

---

## 1. Pré-requisitos

- Python 3.10 ou superior.
- Nenhum pacote externo é necessário (apenas a biblioteca padrão).
- Pasta `dados/` com ao menos um arquivo CSV da RAIS (parcial para dev/CI,
  completo para produção).

---

## 2. Início rápido

```bash
# 1) Validar (executa os 43 testes)
make test

# 2) Gerar amostra com coluna de identificação (valida contagem de empresas)
make sample

# 3) Analisar o caso de referência (330100 · 2342702)
make analyze

# 4) Subir a interface web
make serve          # abre http://127.0.0.1:8000/
```

---

## 3. Interface web

Acesse `http://127.0.0.1:8000/` (padrão) após `make serve`.

1. **Arquivo de base** — selecione o arquivo desejado. A interface indica o
   tamanho, a classe (parcial/completa) e se o arquivo possui a coluna de
   identificação do estabelecimento (necessária para a contagem de empresas).
2. **Município** — digite o código IBGE (ex.: `330100`); há autocompletar com
   o nome do município vindo do layout.
3. **Subclasse CNAE 2.0** — digite o código (ex.: `2342702`); autocompletar
   com a descrição oficial.
4. **Índice** — marque "Usar índice persistente" para consultas sobre a base
   completa de 5 GB; use "Construir índice" para gerá-lo (uma única varredura).
5. **Analisar** — executa a consulta. O painel de resultados apresenta:
   - cards: Estabelecimentos, Vínculos e Vínculos considerados p/ empresas;
   - tabela "Funcionários por estabelecimento" (quando há coluna de
     identificação);
   - tabela "Distribuição de escolaridade" com barras proporcionais e a
     categoria "Informação Não Disponível/Ignorada" destacada;
   - rodapé com contexto do layout (nome do município e do ramo).

> Avisos: se o arquivo não possuir a coluna de identificação, o sistema
> exibe um banner explicando que a contagem de empresas fica indisponível
> (vínculos e escolaridade continuam corretos).

---

## 4. Linha de comando

A partir da raiz do projeto (para que o pacote `src/rais` seja encontrado):

```bash
export PYTHONPATH=src
python3 -m rais --help          # ajuda geral
```

### 4.1 `files`
Lista os arquivos de dados com tamanho e classe (parcial/completa).

### 4.2 `schema`
```bash
python3 -m rais schema --file dados/RAIS_VINC_PUB_MG_ES_RJ_parcial.csv
```
Mostra separador, codificação, colunas e os campos lógicos presentes/ausentes.

### 4.3 `analyze`
```bash
python3 -m rais analyze --file dados/RAIS_VINC_PUB_MG_ES_RJ_parcial.csv \
    --municipio 330100 --subclasse 2342702
python3 -m rais analyze --file dados/amostra_com_identificador.csv \
    --municipio 330100 --subclasse 2342702 --json
```
Filtros são opcionais: informe apenas `--municipio` ou apenas `--subclasse`
para análises mais amplas. `--use-index` usa o índice persistente quando
existir.

### 4.4 `index`
```bash
python3 -m rais index --file dados/RAIS_VINC_PUB_MG_ES_RJ_parcial.csv   # constrói
python3 -m rais index --status --file dados/RAIS_VINC_PUB_MG_ES_RJ_parcial.csv
```

### 4.5 `layouts`
```bash
python3 -m rais layouts --tipo escolaridade
python3 -m rais layouts --tipo subclasse --busca 2342702
python3 -m rais layouts --tipo municipio --busca campos
```

### 4.6 `serve`
```bash
python3 -m rais serve --host 127.0.0.1 --port 8000
# ou: python3 scripts/run_server.py --port 8000
```

---

## 5. Amostra de validação (coluna de identificação)

A base real fornecida **não** contém a coluna `Identificad` (CNPJ/CEI do
estabelecimento), necessária para distinguir empresas. Para validar a
contagem de empresas, o projeto gera uma amostra determinística:

```bash
make sample
# cria dados/amostra_com_identificador.csv (63 colunas = 62 do layout + Identificad)
```

A amostra contém o caso de referência: município `330100`, subclasse
`2342702`, com **3 estabelecimentos** (10, 5 e 3 funcionários) e 19 vínculos
(incluindo um vínculo com TIPO ESTBL `-1`, que não entra na contagem de
empresas). Os resultados esperados estão em `src/rais/sample.py::EXPECTED` e
são verificados pelos testes.

---

## 6. Produção com a base completa (5 GB+)

1. Copie o arquivo completo para `dados/` (ex.: `RAIS_VINC_PUB_MG_ES_RJ.csv-...`).
2. Construa o índice uma vez:
   ```bash
   python3 -m rais index --file dados/RAIS_VINC_PUB_MG_ES_RJ.csv-chunking-*.csv
   ```
3. Na interface web, selecione o arquivo completo, marque "Usar índice
   persistente" e execute a consulta. O sistema lê apenas as linhas
   candidatas (via `seek`), mantendo a memória constante.

> A primeira varredura (sem índice) de um arquivo de 5 GB leva alguns
> minutos; as consultas seguintes com índice são praticamente instantâneas
> para um par (município, subclasse).

---

## 7. Perguntas frequentes

**Por que a contagem de empresas aparece como "—" / indisponível?**
O arquivo selecionado não possui a coluna de identificação do estabelecimento
(`Identificad`/CNPJ). Essa coluna é indispensável para distinguir empresas
(ver item 5). Use a amostra (`make sample`) ou a base RAIS oficial.

**O sistema aguenta o arquivo de 5 GB?**
Sim. A leitura é streaming (memória constante) e o índice permite consultas
seletivas. Não abra o arquivo completo em planilhas.

**Por que os códigos são tratados como texto?**
Para preservar zeros à esquerda (ex.: municípios `033100`, subclasses) e
evitar falsas conversões; é uma exigência do dicionário técnico.

**Como os valores "Ignorado" são tratados?**
`-1`, `{ñ class}`, `{ñclass}` e vazios são segregados na categoria
"Informação Não Disponível/Ignorada", fora da base de cálculo dos níveis 1..11.

**Posso rodar os testes com pytest?**
Sim — as classes são `unittest` e funcionam sob pytest, mas `make test` já
roda sem instalar nada.

---

## 8. Solução de problemas

| Sintoma | Causa provável / solução |
|---|---|
| `Nenhum arquivo de dados encontrado` | Pasta `dados/` vazia ou sem `.csv` |
| `Arquivo sem coluna de município` | Arquivo com layout diferente; o mapeamento lógico está em `config.py` |
| Contagem de empresas indisponível | Faltam a coluna `Identificad`; use a amostra ou base oficial |
| Erro de transação/índice | Apague `.rais_index/` e reconstrua o índice |
| Porta em uso | Use `--port` diferente (ex.: `--port 8010`) |
