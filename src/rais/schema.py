"""Esquema de colunas: normalização de cabeçalho, detecção de separador e
mapeamento entre o cabeçalho físico do arquivo e as variáveis lógicas do
contrato RAIS (docs/realtoriotecnico.txt).

A normalização é tolerante a acentos, caixa e separadores ("Município -
Código" == "MUNICIPIO"), permitindo que o mesmo motor processe arquivos com
variações do layout oficial sem configuração manual.
"""

from __future__ import annotations

import csv
import io
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from . import config


def normalize_token(text: str) -> str:
    """Remove acentos, caixa e separadores de um nome de coluna.

    Separadores que costumam compor códigos ("2.0", "31/12", "1-0") são
    removidos sem espaço; os demais viram espaço simples.
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    out = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in ".-_,/":
            continue
        else:
            out.append(" ")
    return " ".join("".join(out).split())


def detect_delimiter(path: str, encoding: Optional[str] = None) -> str:
    """Detecta o separador real do arquivo entre os candidatos do layout.

    Estratégia robusta: conta a ocorrência de cada candidato na primeira linha
    e escolhe o de maior frequência (fora de aspas).  O layout oficial cita
    ";" mas os arquivos fornecidos usam ",".
    """
    encoding = encoding or config.DEFAULT_DATA_ENCODING
    candidates = config.DELIMITER_CANDIDATES
    counts = {c: 0 for c in candidates}
    with open(path, "r", encoding=encoding, newline="") as fh:
        line = fh.readline()
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
        elif not in_quotes and ch in counts:
            counts[ch] += 1
    best = max(candidates, key=lambda c: counts[c])
    if counts[best] == 0:
        # Sem separador: tenta o Sniffer antes de desistir.
        try:
            dialect = csv.Sniffer().sniff(line, delimiters="".join(candidates))
            return dialect.delimiter
        except Exception:
            return best
    return best


@dataclass
class Schema:
    """Mapeamento entre o cabeçalho físico e as variáveis lógicas."""

    header: List[str]
    delimiter: str
    encoding: str
    index_by_logical: Dict[str, int]
    missing: List[str]

    @property
    def columns(self) -> int:
        return len(self.header)

    def column_of(self, logical: str) -> Optional[int]:
        return self.index_by_logical.get(logical)

    def present(self, logical: str) -> bool:
        return logical in self.index_by_logical

    def as_dict(self) -> Dict:
        return {
            "delimiter": self.delimiter,
            "encoding": self.encoding,
            "columns": self.columns,
            "header": self.header,
            "present": sorted(self.index_by_logical.keys()),
            "missing": sorted(self.missing),
        }


def _build_alias_index() -> Dict[str, str]:
    """Mapeia cada nome normalizado de alias -> variável lógica."""
    index: Dict[str, str] = {}
    for logical, field in config.LOGICAL_FIELDS.items():
        for alias in (logical,) + field.aliases:
            index[normalize_token(alias)] = logical
    return index


_ALIAS_INDEX = _build_alias_index()


def resolve_logical(name: str) -> Optional[str]:
    """Retorna a variável lógica correspondente a um nome de coluna (ou None)."""
    return _ALIAS_INDEX.get(normalize_token(name))


def detect_schema(path: str, encoding: Optional[str] = None) -> Schema:
    """Lê o cabeçalho do arquivo e constrói o Schema com o mapeamento lógico."""
    encoding = encoding or config.DEFAULT_DATA_ENCODING
    delimiter = detect_delimiter(path, encoding)
    with open(path, "r", encoding=encoding, newline="") as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        header = next(reader)

    header = [h.strip() for h in header]
    index_by_logical: Dict[str, int] = {}
    for idx, name in enumerate(header):
        logical = resolve_logical(name)
        if logical is not None and logical not in index_by_logical:
            index_by_logical[logical] = idx

    missing = [name for name in config.LOGICAL_FIELDS if name not in index_by_logical]
    return Schema(
        header=header,
        delimiter=delimiter,
        encoding=encoding,
        index_by_logical=index_by_logical,
        missing=missing,
    )


def read_header_only(path: str, encoding: Optional[str] = None) -> List[str]:
    """Retorna apenas a lista de nomes de colunas do arquivo."""
    schema = detect_schema(path, encoding)
    return schema.header
