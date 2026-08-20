# RAIS · Filtro de Dados — atalhos comuns
PYTHON ?= python3
PYTHONPATH := src

.PHONY: help files schema analyze sample index serve test lint clean

help:
	@echo "Alvos disponíveis:"
	@echo "  make files    - lista os arquivos de dados"
	@echo "  make sample   - gera amostra com coluna Identificad"
	@echo "  make analyze  - análise do caso de referência (amostra)"
	@echo "  make index    - constrói índice da amostra"
	@echo "  make serve    - inicia o servidor web (porta 8000)"
	@echo "  make test     - executa a suíte de testes"
	@echo "  make clean    - remove índices e caches"

files:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m rais files

sample:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/make_sample.py

analyze: sample
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m rais analyze \
		--file dados/amostra_com_identificador.csv \
		--municipio 330100 --subclasse 2342702

index: sample
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m rais index \
		--file dados/amostra_com_identificador.csv

serve:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/run_server.py

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

clean:
	rm -rf .rais_index .pytest_cache __pycache__ src/rais/__pycache__ \
		tests/__pycache__
