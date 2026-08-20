================================================================================
 RAIS · FILTRO DE DADOS
 Sistema de consulta e análise da base RAIS (vínculos)
--------------------------------------------------------------------------------
 Versão: 1.0.0
 Requisitos: Python 3.10+ (apenas biblioteca padrão — sem dependências externas)
================================================================================

1. VISÃO GERAL
--------------------------------------------------------------------------------
O sistema implementa o software de análise descrito em docs/realtoriotecnico.txt
e docs/textoinicial.txt: a partir de um arquivo da base RAIS de vínculos e dos
layouts oficiais (pasta layout/), ele identifica, para uma combinação de
município + subclasse CNAE 2.0:

  * número de estabelecimentos (empresas) do ramo no município;
  * número de funcionários por empresa;
  * número total de funcionários (vínculos);
  * estatística do grau de escolaridade dos funcionários, com os valores
    "Ignorados" (-1 / {ñ class}) separados em categoria própria.

Decisões de arquitetura atendidas (realtoriotecnico.txt, item 2):
  * Processamento STREAMING: arquivos de 5 GB+ são lidos linha a linha, nunca
    carregados integralmente em memória.
  * Seleção dinâmica do arquivo-base: o arquivo parcial (KB) serve para
    desenvolvimento/CI e o arquivo completo (5 GB+) para produção.
  * Indexação persistente (SQLite) dos campos de alta cardinalidade
    (município e subclasse) para consultas repetidas performáticas.
  * Tipagem das variáveis como STRING (preserva zeros à esquerda).
  * Tratamento explícito de "-1", "{ñ class}" e "{ñclass}" como "Ignorado".


2. ENTREGÁVEIS
--------------------------------------------------------------------------------
  [x] src/rais/             Pacote Python (motor de dados + API + CLI)
  [x] web/                  Frontend web (HTML/CSS/JS, sem build)
  [x] scripts/              Scripts utilitários (servidor, gerador de amostra)
  [x] tests/                Suíte de testes automatizados (43 testes)
  [x] docs/                 Especificação técnica e manual de uso
  [x] README.txt            Este documento
  [x] .gitignore            Arquivos ignorados pelo controle de versão
  [x] Makefile              Atalhos (files, sample, analyze, index, serve, test)
  [x] requirements.txt      Dependências (nenhuma obrigatória)

  Resultado do caso de uso de referência (validação automatizada):
    Filtros: município 330100 (Campos dos Goytacazes/RJ)
             subclasse 2342702 (Fabricação de artefatos de cerâmica e barro
             cozido para uso na construção, exceto azulejos e pisos)
    -> 3 estabelecimentos (10, 5 e 3 funcionários) e 19 vínculos na amostra
       de validação (detalhes em docs/manual.md).


3. ESTRUTURA DO PROJETO
--------------------------------------------------------------------------------
  dados/                            Arquivos de entrada (CSV)
    RAIS_VINC_PUB_MG_ES_RJ_parcial.csv                (~66 KB  · dev/CI)
    RAIS_VINC_PUB_MG_ES_RJ.csv-chunking-*.csv         (~4,7 GB · produção)
    amostra_com_identificador.csv                     (gerado por make sample)
  layout/                           Taxonomias oficiais (municípios, CNAE 2.0,
                                    escolaridade, causas, natureza jurídica...)
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
  web/                              Frontend (index.html, styles.css, app.js)
  scripts/                          run_server.py e make_sample.py
  tests/                            Suíte de testes (unittest, stdlib)


4. COMO EXECUTAR
--------------------------------------------------------------------------------
  Requisito: Python 3.10+ (sem instalação de pacotes; usa apenas a stdlib).

  4.1 Interface WEB (recomendada)
        make serve
        # ou: python3 scripts/run_server.py --port 8000
      Acesse http://127.0.0.1:8000/
      Selecione o arquivo de base, informe município e/ou subclasse (há
      autocompletar), e clique em "Analisar".

  4.2 Linha de comando
        python3 -m rais files                                   # lista arquivos
        python3 -m rais analyze --file dados/RAIS_VINC_PUB_MG_ES_RJ_parcial.csv \
                --municipio 330100 --subclasse 2342702          # análise
        python3 -m rais analyze --file ... --json               # saída JSON
        python3 -m rais index --file ...                        # constrói índice
        python3 -m rais layouts --tipo escolaridade             # taxonomias
      Para usar via linha de comando a partir da raiz do projeto, informe o
      caminho de src (ex.: PYTHONPATH=src python3 -m rais ...).

  4.3 Gerar a amostra de validação (com coluna de identificação)
        make sample    # cria dados/amostra_com_identificador.csv


5. CASO DE USO DE REFERÊNCIA (2342702 em 330100)
--------------------------------------------------------------------------------
  Execute a análise do caso de referência na amostra:

        make analyze
        # python3 -m rais analyze --file dados/amostra_com_identificador.csv \
        #        --municipio 330100 --subclasse 2342702

  Resultado esperado na amostra:
    Empresas/estabelecimentos ....... 3   (identificadores 01000000000100 [10],
                                            02000000000200 [5], 03000000000300 [3])
    Vínculos totais ................. 19
    Vínculos considerados (TIPO ESTBL válido) ..... 18
    Distribuição de escolaridade .... 11 níveis (1..11) + categoria
                                      "Informação Não Disponível/Ignorada".

  IMPORTANTE — contagem de empresas na base fornecida:
  Os arquivos RAIS fornecidos (parcial e completo) NÃO contêm a coluna de
  identificação do estabelecimento (IDENTIFICAD/CNPJ). Sem essa coluna é
  impossível distinguir estabelecimentos distintos; por isso o sistema
  reporta a contagem de empresas como "indisponível" para esses arquivos
  (exibindo aviso claro), enquanto mantém corretas as métricas de vínculos
  e escolaridade. Para validar a contagem de empresas ponta a ponta, gere a
  amostra com "make sample" ou utilize a base RAIS oficial completa (que
  possui a coluna Identificad). O sistema detecta automaticamente a coluna
  quando presente.


6. TESTES
--------------------------------------------------------------------------------
  Suíte completa (43 testes) usando apenas unittest (stdlib):

        make test
        # PYTHONPATH=src python3 -m unittest discover -s tests -v

  Cobertura: normalização de colunas, detecção de separador, taxonomias,
  leitura streaming, motor de análise (caso de referência + arquivo parcial),
  índice SQLite e API do servidor. Os testes criam amostras em diretório
  temporário e não alteram os dados originais.

  Observação: a suíte também roda sob pytest (caso instalado), pois usa
  classes unittest.

  6.1 Validação de CI/CD
        O arquivo parcial (KB) deve ser a fonte dos testes e da integração
        contínua; o arquivo completo (5 GB+) é reservado ao ambiente de
        produção (realtoriotecnico.txt, item 2).


7. LIMITES E BOAS PRÁTICAS
--------------------------------------------------------------------------------
  * A leitura é streaming (memória constante, independente do tamanho do
    arquivo). Evite carregar o arquivo completo em ferramentas de planilha.
  * Para consultas repetidas sobre a base de 5 GB, construa o índice
    ("Construir índice" na web, ou "python3 -m rais index --file ..."); a
    análise passa a ler somente as linhas candidatas via seek.
  * Variáveis de código (município, CNAE, escolaridade) são tratadas como
    STRING: nunca converta para inteiro, sob risco de perder zeros à esquerda.
  * Valores "-1", "{ñ class}", "{ñclass}" e vazios são tratados como
    "Ignorado" e segregados da base de cálculo dos níveis definidos.


8. DOCUMENTAÇÃO ADICIONAL
--------------------------------------------------------------------------------
  docs/especificacao.md   Especificação técnica da solução (requisitos,
                          arquitetura, mapeamento de variáveis e decisões).
  docs/manual.md          Manual de uso (CLI, web, amostra, índice, exemplos).
  docs/realtoriotecnico.txt  Dicionário técnico de dados RAIS (fonte dos
                             requisitos).
  docs/textoinicial.txt   Enunciado original do problema.

--------------------------------------------------------------------------------
 RAIS · Filtro de Dados — implementação de referência conforme
 docs/realtoriotecnico.txt · stdlib-only · 2026
================================================================================
