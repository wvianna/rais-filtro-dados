"""Descoberta dos arquivos de dados disponíveis.

O frontend deve permitir selecionar dinamicamente o arquivo base
(realtoriotecnico.txt, item 2): o arquivo parcial (KB) para desenvolvimento e
CI, e a base completa (5 GB+) para produção.  Este módulo lista os arquivos da
pasta de dados com metadados úteis (tamanho, classificação parcial/completa).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from . import config

# Arquivos acima deste limite são tratados como "base completa" (produção).
FULL_FILE_MIN_BYTES = 500 * 1024 * 1024  # 500 MiB


@dataclass
class DataFile:
    name: str
    path: str
    size_bytes: int
    mtime: float
    classificacao: str  # "parcial" | "completa"

    @property
    def size_human(self) -> str:
        n = self.size_bytes
        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if n < 1024 or unit == "TiB":
                return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
            n /= 1024
        return f"{n:.1f} TiB"

    def as_dict(self) -> Dict:
        return {
            "name": self.name,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "size_human": self.size_human,
            "classificacao": self.classificacao,
        }


def list_data_files(data_dir: Optional[str] = None) -> List[DataFile]:
    data_dir = data_dir or config.DEFAULT_DATA_DIR
    result: List[DataFile] = []
    if not os.path.isdir(data_dir):
        return result
    for name in sorted(os.listdir(data_dir)):
        full = os.path.join(data_dir, name)
        if not os.path.isfile(full):
            continue
        if not (name.endswith(".csv") or ".csv" in name):
            continue
        st = os.stat(full)
        classificacao = "completa" if st.st_size >= FULL_FILE_MIN_BYTES else "parcial"
        result.append(
            DataFile(
                name=name,
                path=full,
                size_bytes=st.st_size,
                mtime=st.st_mtime,
                classificacao=classificacao,
            )
        )
    return result


def find_file(name: str, data_dir: Optional[str] = None) -> Optional[DataFile]:
    """Localiza um arquivo pelo nome (ou caminho relativo/absoluto)."""
    data_dir = data_dir or config.DEFAULT_DATA_DIR
    for df in list_data_files(data_dir):
        if df.name == name:
            return df
    # Aceita também caminhos absolutos ou relativos.
    if os.path.isfile(name):
        st = os.stat(name)
        return DataFile(
            name=os.path.basename(name),
            path=name,
            size_bytes=st.st_size,
            mtime=st.st_mtime,
            classificacao="completa" if st.st_size >= FULL_FILE_MIN_BYTES else "parcial",
        )
    return None
