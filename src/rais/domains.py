"""Taxonomias e domínios de valor do layout RAIS.

Carrega os arquivos de referência de `layout/` (municípios, subclasses CNAE 2.0,
escolaridade) e centraliza o tratamento de valores "Ignorado" definido no
dicionário técnico.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from . import config


# ---------------------------------------------------------------------------
# Valores "Ignorado"
# ---------------------------------------------------------------------------

def normalize_token_like(text: str) -> str:
    """Normaliza um valor para comparação de tokens (ñ -> n, caixa baixa)."""
    return text.strip().lower().replace("ñ", "n").replace("\u00e3", "a")


def is_ignored(value: Optional[str]) -> bool:
    """True quando o valor deve ser tratado como "Ignorado" (layout oficial).

    O dicionário técnico manda tratar "-1", "{ñ class}" ou "{ñclass}" como
    ignorado; aqui também cobre vazio, "não classificado" e variações.
    """
    if value is None:
        return True
    tok = normalize_token_like(value)
    if tok == "":
        return True
    ignored = {normalize_token_like(t) for t in config.IGNORED_TOKENS}
    return tok in ignored


# ---------------------------------------------------------------------------
# Escolaridade
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NivelInstrucao:
    codigo: str
    rotulo: str


def load_escolaridade(path: Optional[str] = None) -> List[NivelInstrucao]:
    """Lê layout/RAIS_vinculos_layout_escolaridadeOUinstrucao.csv.

    Formato: "ANALFABETO,,1" ... "DOUTORADO,,11", "IGNORADO,,-1".
    """
    path = path or os.path.join(config.DEFAULT_LAYOUT_DIR, "RAIS_vinculos_layout_escolaridadeOUinstrucao.csv")
    niveis: List[NivelInstrucao] = []
    with open(path, "r", encoding=config.LAYOUT_ENCODING, newline="") as fh:
        reader = csv.reader(fh, delimiter=",")
        for row in reader:
            if not row or not row[0].strip():
                continue
            if len(row) < 3 or not row[2].strip():
                continue
            rotulo = row[0].strip()
            codigo = row[2].strip()
            if rotulo.lower().startswith("grau"):
                continue  # linha de cabeçalho
            niveis.append(NivelInstrucao(codigo=codigo, rotulo=rotulo))
    # Ordena códigos numéricos primeiro e "-1" (Ignorado) por último.
    niveis.sort(key=lambda n: (n.codigo == "-1", int(n.codigo) if n.codigo.lstrip("-").isdigit() else 10**9))
    return niveis


ROTULO_ESCOLARIDADE = "Informação Não Disponível/Ignorada"


def rotulo_escolaridade(codigo: Optional[str], niveis: Optional[List[NivelInstrucao]] = None) -> str:
    """Retorna o rótulo oficial de um código de escolaridade (1..11).

    Para valores ignorados ou fora do domínio, retorna a categoria separada
    definida em realtoriotecnico.txt (item 5.4).
    """
    if niveis is None:
        niveis = load_escolaridade()
    if is_ignored(codigo):
        return ROTULO_ESCOLARIDADE
    code = (codigo or "").strip()
    for nivel in niveis:
        if nivel.codigo == code:
            return nivel.rotulo
    return ROTULO_ESCOLARIDADE


# ---------------------------------------------------------------------------
# Subclasse CNAE 2.0
# ---------------------------------------------------------------------------

def load_subclasses(path: Optional[str] = None) -> Dict[str, str]:
    """Lê layout/RAIS_vinculos_layout_subclasse2-0.csv -> {codigo: descricao}.

    Formato: "2342702:Fabricação de ..." (linha pode vir entre aspas porque a
    descrição contém vírgula).
    """
    path = path or os.path.join(config.DEFAULT_LAYOUT_DIR, "RAIS_vinculos_layout_subclasse2-0.csv")
    subclasses: Dict[str, str] = {}
    with open(path, "r", encoding=config.LAYOUT_ENCODING, newline="") as fh:
        for raw in fh:
            line = raw.strip().strip('"').strip()
            if not line or line.lower().startswith("cnae"):
                continue
            if ":" in line:
                code, _, desc = line.partition(":")
                subclasses[code.strip()] = desc.strip()
    return subclasses


# ---------------------------------------------------------------------------
# Municípios
# ---------------------------------------------------------------------------

def load_municipios(path: Optional[str] = None) -> Dict[str, str]:
    """Lê layout/RAIS_vinculos_layout_municipio.csv -> {codigo: nome}."""
    path = path or os.path.join(config.DEFAULT_LAYOUT_DIR, "RAIS_vinculos_layout_municipio.csv")
    municipios: Dict[str, str] = {}
    with open(path, "r", encoding=config.LAYOUT_ENCODING, newline="") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.lower().startswith("municipio"):
                continue
            if ":" in line:
                code, _, nome = line.partition(":")
                municipios[code.strip()] = nome.strip()
    return municipios


# ---------------------------------------------------------------------------
# Acesso consolidado
# ---------------------------------------------------------------------------

class Domains:
    """Coleção carregada (com cache) das taxonomias do projeto."""

    def __init__(self, layout_dir: Optional[str] = None) -> None:
        self.layout_dir = layout_dir or config.DEFAULT_LAYOUT_DIR
        self._escolaridade: Optional[List[NivelInstrucao]] = None
        self._subclasses: Optional[Dict[str, str]] = None
        self._municipios: Optional[Dict[str, str]] = None

    @property
    def escolaridade(self) -> List[NivelInstrucao]:
        if self._escolaridade is None:
            self._escolaridade = load_escolaridade(
                os.path.join(self.layout_dir, "RAIS_vinculos_layout_escolaridadeOUinstrucao.csv")
            )
        return self._escolaridade

    @property
    def subclasses(self) -> Dict[str, str]:
        if self._subclasses is None:
            self._subclasses = load_subclasses(
                os.path.join(self.layout_dir, "RAIS_vinculos_layout_subclasse2-0.csv")
            )
        return self._subclasses

    @property
    def municipios(self) -> Dict[str, str]:
        if self._municipios is None:
            self._municipios = load_municipios(
                os.path.join(self.layout_dir, "RAIS_vinculos_layout_municipio.csv")
            )
        return self._municipios

    def descricao_subclasse(self, codigo: Optional[str]) -> Optional[str]:
        if codigo is None:
            return None
        return self.subclasses.get(codigo.strip())

    def nome_municipio(self, codigo: Optional[str]) -> Optional[str]:
        if codigo is None:
            return None
        return self.municipios.get(codigo.strip())
