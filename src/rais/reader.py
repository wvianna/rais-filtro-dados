"""Leitura *streaming* dos arquivos RAIS.

Requisito de arquitetura (docs/realtoriotecnico.txt, item 2): o motor **não
pode** carregar arquivos de 5 GB+ em memória.  Este módulo itera as linhas
uma a uma (o módulo ``csv`` lê o arquivo por buffer, nunca na íntegra) e
oferece também um modo com *offset* de bytes por linha, usado na construção
do índice para leituras seletivas via ``seek``.
"""

from __future__ import annotations

import csv
import os
from typing import Callable, Iterator, List, Optional, Sequence, Tuple

from . import config, schema

Row = List[str]


class CsvStreamError(Exception):
    """Erro de leitura/parse do arquivo CSV."""


def iter_rows(
    path: str,
    *,
    encoding: Optional[str] = None,
    delimiter: Optional[str] = None,
    skip_header: bool = True,
) -> Iterator[Tuple[int, Row]]:
    """Itera (numero_linha, campos) do arquivo sem carregá-lo em memória.

    O ``csv.reader`` consome o arquivo linha a linha por buffer interno; o
    número de linhas retornado é o índice de dados (0-based).
    """
    encoding = encoding or config.DEFAULT_DATA_ENCODING
    delimiter = delimiter or schema.detect_delimiter(path, encoding)
    with open(path, "r", encoding=encoding, newline="") as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        if skip_header:
            try:
                next(reader)
            except StopIteration:
                return
        for i, row in enumerate(reader):
            if row is None or (len(row) == 1 and row[0].strip() == ""):
                continue
            yield i, row


def iter_rows_with_offsets(
    path: str,
    *,
    encoding: Optional[str] = None,
    delimiter: Optional[str] = None,
    skip_header: bool = True,
    expected_columns: Optional[int] = None,
    progress: Optional[Callable[[int, int], None]] = None,
) -> Iterator[Tuple[int, int, Row]]:
    """Como ``iter_rows`` mas retorna (numero_linha, offset_bytes, campos).

    O offset é a posição em bytes do início da linha física — permite ``seek``
    direto para linhas candidatas quando há índice.  Pré-requisito: o arquivo
    não contém quebras de linha embutidas entre aspas (verificado nos dados).
    Se o nº de colunas de uma linha não bater com o cabeçalho, dispara
    ``CsvStreamError`` com orientação para usar o modo de varredura integral.
    """
    encoding = encoding or config.DEFAULT_DATA_ENCODING
    delimiter = delimiter or schema.detect_delimiter(path, encoding)

    def _parse(line: str) -> Optional[Row]:
        try:
            return next(csv.reader([line], delimiter=delimiter))
        except Exception:
            return None

    n_rows = 0
    with open(path, "r", encoding=encoding, newline="") as fh:
        offset = fh.tell()
        line = fh.readline()
        if skip_header:
            header_row = _parse(line)
            expected_columns = len(header_row) if header_row else expected_columns
            n_rows = 0
            offset = fh.tell()
            line = fh.readline()
        while line:
            fields = _parse(line)
            if fields is None:
                raise CsvStreamError(
                    "Linha sem parse válido (possível quebra de linha embutida). "
                    "Use o modo de varredura integral (use_index=False)."
                )
            if expected_columns is not None and len(fields) != expected_columns:
                raise CsvStreamError(
                    f"Linha {n_rows + 1} com {len(fields)} colunas; esperado {expected_columns}. "
                    "Use o modo de varredura integral (use_index=False)."
                )
            if progress is not None:
                progress(offset, n_rows + 1)
            yield n_rows, offset, fields
            n_rows += 1
            offset = fh.tell()
            line = fh.readline()


def count_rows(path: str, *, encoding: Optional[str] = None, delimiter: Optional[str] = None) -> int:
    """Conta registros (sem o cabeçalho) varrendo em streaming."""
    encoding = encoding or config.DEFAULT_DATA_ENCODING
    delimiter = delimiter or schema.detect_delimiter(path, encoding)
    with open(path, "r", encoding=encoding, newline="") as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def read_rows_at_offsets(
    path: str,
    offsets: Sequence[int],
    *,
    encoding: Optional[str] = None,
    delimiter: Optional[str] = None,
) -> Iterator[Row]:
    """Lê linhas em offsets específicos (para consulta via índice).

    Cada offset deve apontar para o início de uma linha física.
    """
    encoding = encoding or config.DEFAULT_DATA_ENCODING
    delimiter = delimiter or schema.detect_delimiter(path, encoding)
    with open(path, "rb") as fh:
        for off in offsets:
            fh.seek(off)
            raw = fh.readline()
            text = raw.decode(encoding, errors="replace")
            row = next(csv.reader([text], delimiter=delimiter))
            yield row
