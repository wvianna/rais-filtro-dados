"""Índice persistente (SQLite) para consultas performáticas.

Requisito de arquitetura (realtoriotecnico.txt, item 2): indexar campos de alta
cardinalidade (município e subclasse de atividade econômica) para que filtros e
agregações sejam eficientes mesmo na base completa de 5 GB+.

O índice mapeia (municipio, subclasse) -> offsets de bytes das linhas.  Uma
consulta filtra primeiro o índice (leitura pequena) e depois faz ``seek``
apenas nas linhas candidatas — sem varrer os 5 GB a cada execução.
"""

from __future__ import annotations

import os
import sqlite3
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import config, reader, schema

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS rais_index (
    file      TEXT NOT NULL,
    municipio TEXT,
    subclasse TEXT,
    row_no    INTEGER,
    offset    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rais_file_mun_sub
    ON rais_index(file, municipio, subclasse);
"""


def _db_path(index_dir: str, file_key: str) -> str:
    return os.path.join(index_dir, file_key.replace(os.sep, "__") + ".sqlite")


def build_index(
    path: str,
    *,
    index_dir: Optional[str] = None,
    encoding: Optional[str] = None,
    progress: Optional[Callable[[int, int], None]] = None,
) -> Dict:
    """Constrói (ou reconstrói) o índice do arquivo em uma varredura única."""
    index_dir = index_dir or config.DEFAULT_INDEX_DIR
    os.makedirs(index_dir, exist_ok=True)
    sch = schema.detect_schema(path, encoding)
    col_mun = sch.column_of("municipio")
    col_sub = sch.column_of("subclasse_cnae20")
    if col_mun is None:
        raise ValueError("O arquivo não possui coluna de município; índice não pode ser construído.")

    file_key = os.path.abspath(path)
    db = _db_path(index_dir, file_key)

    started = time.monotonic()
    rows_scanned = 0
    # isolation_level=None => autocommit; transação explícita apenas no loop.
    with sqlite3.connect(db, isolation_level=None) as conn:
        conn.executescript(_SCHEMA_SQL)
        conn.execute("DELETE FROM rais_index WHERE file = ?", (file_key,))
        conn.execute("BEGIN")
        batch: List[Tuple] = []
        for row_no, offset, fields in reader.iter_rows_with_offsets(
            path, encoding=encoding, delimiter=sch.delimiter, skip_header=True,
            expected_columns=sch.columns, progress=progress,
        ):
            mun = fields[col_mun].strip() if col_mun < len(fields) else ""
            sub = fields[col_sub].strip() if col_sub is not None and col_sub < len(fields) else ""
            if mun == "":
                mun = None
            if sub == "":
                sub = None
            batch.append((file_key, mun, sub, row_no, offset))
            rows_scanned += 1
            if len(batch) >= 5000:
                conn.executemany(
                    "INSERT INTO rais_index(file, municipio, subclasse, row_no, offset) "
                    "VALUES (?,?,?,?,?)",
                    batch,
                )
                batch.clear()
        if batch:
            conn.executemany(
                "INSERT INTO rais_index(file, municipio, subclasse, row_no, offset) "
                "VALUES (?,?,?,?,?)",
                batch,
            )
        conn.commit()

    elapsed = time.monotonic() - started
    return {
        "file": os.path.basename(path),
        "indexed_rows": rows_scanned,
        "elapsed_s": round(elapsed, 3),
        "db": db,
    }


def index_exists(path: str, index_dir: Optional[str] = None) -> bool:
    index_dir = index_dir or config.DEFAULT_INDEX_DIR
    file_key = os.path.abspath(path)
    db = _db_path(index_dir, file_key)
    if not os.path.exists(db):
        return False
    try:
        with sqlite3.connect(db) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM rais_index WHERE file = ?", (file_key,))
            return cur.fetchone()[0] > 0
    except sqlite3.Error:
        return False


def lookup_offsets(
    path: str,
    *,
    municipio: Optional[str] = None,
    subclasse: Optional[str] = None,
    index_dir: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[int]:
    """Retorna offsets das linhas que casam com os filtros informados."""
    index_dir = index_dir or config.DEFAULT_INDEX_DIR
    file_key = os.path.abspath(path)
    db = _db_path(index_dir, file_key)
    if not os.path.exists(db):
        return []

    where = ["file = ?"]
    params: List = [file_key]
    if municipio is not None:
        where.append("municipio = ?")
        params.append(municipio.strip())
    if subclasse is not None:
        where.append("subclasse = ?")
        params.append(subclasse.strip())

    sql = f"SELECT offset FROM rais_index WHERE {' AND '.join(where)} ORDER BY offset"
    if limit:
        sql += f" LIMIT {int(limit)}"

    try:
        with sqlite3.connect(db) as conn:
            cur = conn.execute(sql, params)
            return [r[0] for r in cur.fetchall()]
    except sqlite3.Error:
        return []


def index_stats(path: str, index_dir: Optional[str] = None) -> Optional[Dict]:
    index_dir = index_dir or config.DEFAULT_INDEX_DIR
    file_key = os.path.abspath(path)
    db = _db_path(index_dir, file_key)
    if not os.path.exists(db):
        return None
    try:
        with sqlite3.connect(db) as conn:
            cur = conn.execute(
                "SELECT COUNT(*), COUNT(DISTINCT municipio), COUNT(DISTINCT subclasse) "
                "FROM rais_index WHERE file = ?",
                (file_key,),
            )
            total, distinct_mun, distinct_sub = cur.fetchone()
            return {
                "exists": True,
                "rows": total,
                "distinct_municipios": distinct_mun,
                "distinct_subclasses": distinct_sub,
            }
    except sqlite3.Error:
        return None
