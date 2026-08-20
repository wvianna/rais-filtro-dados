"""Configuração central do sistema RAIS.

Reúne caminhos padrão, codificações, nomes lógicos de colunas e o contrato
de dados exigido em docs/realtoriotecnico.txt.  O objetivo é que todas as
decisões de "mapeamento" fiquem em um único lugar, permitindo interoperar
com variações do layout oficial (acentos, maiúsculas, " - Código" etc.).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Caminhos padrão (relativos ao repositório)
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEFAULT_DATA_DIR = os.path.join(REPO_ROOT, "dados")
DEFAULT_LAYOUT_DIR = os.path.join(REPO_ROOT, "layout")
DEFAULT_WEB_DIR = os.path.join(REPO_ROOT, "web")
DEFAULT_INDEX_DIR = os.path.join(REPO_ROOT, ".rais_index")

# ---------------------------------------------------------------------------
# Leitura de arquivos
# ---------------------------------------------------------------------------

# Os arquivos de dados RAIS distribuídos vêm em latin-1/CP1252 (acentos como
# "Código" foram verificados).  Os arquivos de layout são UTF-8.
DEFAULT_DATA_ENCODING = "latin-1"
LAYOUT_ENCODING = "utf-8"

# Separadores candidatos a detecção automática.  O layout oficial cita ";" mas
# os arquivos efetivamente fornecidos usam ",".
DELIMITER_CANDIDATES: List[str] = [",", ";", "\t", "|"]

# Valores que o layout oficial manda considerar como "Ignorado".
# "-1" e "{ñ class}" são citados em docs/realtoriotecnico.txt.
IGNORED_TOKENS: List[str] = [
    "",
    "-1",
    "{ñ class}",
    "{ñclass}",
    "{n class}",
    "{nclass}",
    "não classificado",
    "nao classificado",
]


@dataclass(frozen=True)
class LogicalField:
    """Uma variável lógica do contrato RAIS e os nomes que pode ter no arquivo."""

    name: str
    aliases: tuple = field(default_factory=tuple)


# Colunas lógicas relevantes para o caso de uso (município + subclasse +
# escolaridade + tipo/identificação do estabelecimento).  O sistema aceita
# qualquer um dos nomes por alias, ignorando acentos/caixa/separadores.
LOGICAL_FIELDS: Dict[str, LogicalField] = {
    "municipio": LogicalField(
        "municipio",
        ("Município - Código", "Municipio - Codigo", "MUNICIPIO", "Município"),
    ),
    "municipio_trab": LogicalField(
        "municipio_trab",
        ("Município Trab - Código", "Municipio Trab - Codigo", "MUNICIPIO TRAB"),
    ),
    "subclasse_cnae20": LogicalField(
        "subclasse_cnae20",
        (
            "CNAE 2.0 Subclasse - Codigo",
            "CNAE 2.0 Subclasse - Código",
            "SB CLAS 20",
            "Subclasse CNAE 2.0",
        ),
    ),
    "classe_cnae20": LogicalField(
        "classe_cnae20",
        ("CNAE 2.0 Classe - Código", "CNAE 2.0 Classe - Codigo", "CLAS CNAE 20"),
    ),
    "classe_cnae95": LogicalField(
        "classe_cnae95",
        ("CNAE 95 Classe - Código", "CNAE 95 Classe - Codigo", "CLAS CNAE 95"),
    ),
    "escolaridade": LogicalField(
        "escolaridade",
        (
            "Escolaridade Após 2005 - Código",
            "Escolaridade Apos 2005 - Codigo",
            "GR INSTRUCAO",
            "Escolaridade",
        ),
    ),
    "tipo_estabelecimento": LogicalField(
        "tipo_estabelecimento",
        ("Tipo Estabelecimento - Código", "Tipo Estabelecimento - Codigo", "TIPO ESTBL"),
    ),
    "tipo_estabelecimento_nome": LogicalField(
        "tipo_estabelecimento_nome",
        ("Tipo Estabelecimento - Nome", "TIPO ESTBL NOME"),
    ),
    "natureza_juridica": LogicalField(
        "natureza_juridica",
        ("Natureza Jurídica - Código", "Natureza Juridica - Codigo", "NAT JURIDICA"),
    ),
    "tamanho_estabelecimento": LogicalField(
        "tamanho_estabelecimento",
        ("Tamanho Estabelecimento - Código", "Tamanho Estabelecimento - Codigo", "TAM ESTAB"),
    ),
    "ind_estabelecimento_simples": LogicalField(
        "ind_estabelecimento_simples",
        (
            "Ind Estabelecimento Participante SIMPLES - Código",
            "Ind Estabelecimento Participante SIMPLES - Codigo",
            "IND ESTAB SIMPLES",
        ),
    ),
    "ibge_subsetor": LogicalField(
        "ibge_subsetor",
        ("IBGE Subsetor - Código", "IBGE Subsetor - Codigo", "IBGE SUBSETOR"),
    ),
    "identificador_estabelecimento": LogicalField(
        "identificador_estabelecimento",
        (
            "Identificad",
            "IDENTIFICAD",
            "Identificador",
            "CNPJ/CEI",
            "CNPJ CEI",
            "CNPJ",
            "CEI",
            "CNPJ ou CEI",
        ),
    ),
}

# Coluna usada, por padrão, como identificador do estabelecimento
# ("coluna de identificação" citada em realtoriotecnico.txt, item 5.2).
DEFAULT_ESTABELECIMENTO_ID = "identificador_estabelecimento"

# Campos de nível-empresa usados para a ESTIMATIVA de empresas quando o arquivo
# não possui a coluna de identificação.  A estimativa conta as combinações
# distintas desses atributos (chave composta) — aproximação claramente
# rotulada na interface, pois sem Identificad/CNPJ não há identificador único.
ESTIMATIVA_EMPRESA_FIELDS: List[str] = [
    "municipio",
    "subclasse_cnae20",
    "classe_cnae20",
    "classe_cnae95",
    "tipo_estabelecimento",
    "tipo_estabelecimento_nome",
    "natureza_juridica",
    "tamanho_estabelecimento",
    "ind_estabelecimento_simples",
    "ibge_subsetor",
]

# Domínios válidos de escolaridade (1..11) conforme layout oficial.
ESCOLARIDADE_MIN = 1
ESCOLARIDADE_MAX = 11

# Tamanhos de leitura (buffers) para o processamento streaming.
READ_CHUNK_BYTES = 1024 * 1024  # 1 MiB

# Código do caso de uso de referência (município Campos dos Goytacazes/RJ e
# subclasse CNAE 2.0 de fabricação de artefatos de cerâmica e barro cozidos).
REFERENCIA_MUNICIPIO = "330100"
REFERENCIA_SUBCLASSE = "2342702"
