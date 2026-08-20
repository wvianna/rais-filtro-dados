"""Fixtures e utilitários compartilhados pelos testes.

Os testes não dependem de instalação de pacotes: usam apenas a stdlib
(``unittest``, ``tempfile``) e o pacote ``rais`` em ``src/``.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO_ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

DATA_DIR = os.path.join(REPO_ROOT, "dados")
PARTIAL = os.path.join(DATA_DIR, "RAIS_VINC_PUB_MG_ES_RJ_parcial.csv")


def make_sample_file(dirpath: str) -> str:
    """Cria uma amostra COM coluna Identificad dentro de ``dirpath``.

    Copia o arquivo parcial real (para servir de cabeçalho) e gera a amostra
    determinística com o caso de referência (330100 · 2342702).
    """
    shutil.copy(PARTIAL, os.path.join(dirpath, "RAIS_VINC_PUB_MG_ES_RJ_parcial.csv"))
    from rais import sample

    path = os.path.join(dirpath, "amostra_com_identificador.csv")
    meta = sample.write_sample_file(path, data_dir=dirpath)
    assert meta["tem_identificador"]
    return path


class TempSampleDir:
    """Context manager: diretório temporário com a amostra gerada."""

    def __init__(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="rais_test_")
        self.sample_path = make_sample_file(self.tmp)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.tmp, ignore_errors=True)
