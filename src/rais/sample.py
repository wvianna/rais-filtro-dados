"""Geração de amostra RAIS determinística COM coluna de identificação.

A base real fornecida (parcial e completa) **não** possui a coluna de
identificação do estabelecimento (`IDENTIFICAD`/CNPJ) — sem ela a contagem de
empresas é impossível.  Este módulo gera uma amostra representativa que inclui
essa coluna e contém o caso de uso de referência (município 330100, subclasse
2342702), permitindo validar ponta a ponta a contagem de estabelecimentos,
os vínculos por empresa e a distribuição de escolaridade.

Também serve de exemplo do "contrato de dados" esperado para a base completa.
"""

from __future__ import annotations

import csv
import os
from typing import Dict, List, Optional

from . import config, reader

# Resultados esperados da amostra (usados pelos testes).
EXPECTED = {
    "municipio": "330100",
    "subclasse": "2342702",
    "estabelecimentos": 3,
    "vinculos": 19,  # 3 estabelecimentos (18) + 1 vínculo com TIPO ESTBL ignorado
    "vinculos_considerados": 18,
}

# Plano dos estabelecimentos do caso de referência.
# (identificador, tipo, tipo_nome, lista_de_escolaridades)
PLANO_ESTABELECIMENTOS = [
    ("01000000000100", "1", "CNPJ", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
    ("02000000000200", "1", "CNPJ", [2, 2, 4, 6, -1]),
    ("03000000000300", "3", "CEI", [11, 11, -1]),
]


def build_row_template(header: List[str]) -> Dict[str, str]:
    """Cria um template de linha preenchido com valores neutros."""
    template: Dict[str, str] = {}
    for col in header:
        template[col] = ""
    return template


def make_vinculo(
    header: List[str],
    *,
    municipio: str,
    subclasse: str,
    escolaridade: str,
    tipo_estabelecimento: str,
    tipo_nome: str,
    identificador: str = "",
    cbo: str = "",
    ocupacao_extra: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Monta uma linha (dict) de vínculo preenchida conforme o cabeçalho."""
    row = build_row_template(header)
    row["Município - Código"] = municipio
    row["CNAE 2.0 Subclasse - Codigo"] = subclasse
    row["Escolaridade Após 2005 - Código"] = escolaridade
    row["Tipo Estabelecimento - Código"] = tipo_estabelecimento
    row["Tipo Estabelecimento - Nome"] = tipo_nome
    if identificador:
        row["Identificad"] = identificador
    if cbo:
        row["CBO 2002 Ocupação - Código"] = cbo
    if ocupacao_extra:
        for k, v in ocupacao_extra.items():
            row[k] = v
    return row


def build_sample_rows(header: List[str]) -> List[Dict[str, str]]:
    """Gera todas as linhas da amostra (caso de referência + ruído)."""
    rows: List[Dict[str, str]] = []

    # --- Estabelecimentos do caso de referência ---------------------------
    cbo_counter = 1000
    for identificador, tipo, tipo_nome, escolaridades in PLANO_ESTABELECIMENTOS:
        for esc in escolaridades:
            cbo_counter += 1
            rows.append(
                make_vinculo(
                    header,
                    municipio="330100",
                    subclasse="2342702",
                    escolaridade=str(esc),
                    tipo_estabelecimento=tipo,
                    tipo_nome=tipo_nome,
                    identificador=identificador,
                    cbo=str(cbo_counter),
                )
            )

    # --- Vínculo com TIPO ESTBL ignorado (conta como vínculo, não como emp.) -
    rows.append(
        make_vinculo(
            header,
            municipio="330100",
            subclasse="2342702",
            escolaridade="7",
            tipo_estabelecimento="-1",
            tipo_nome="IGNORADO",
            identificador="99999999999999",  # ignorado junto com o tipo
            cbo="2000",
        )
    )

    # --- Ruído: outros municípios/subclasses -------------------------------
    ruido = [
        ("310620", "8513900", "9", "1", "CNPJ", "00000000000099"),
        ("330455", "8411600", "7", "1", "CNPJ", "00000000000088"),
        ("330100", "{ñ class}", "5", "1", "CNPJ", "00000000000077"),  # subclasse ignorada
        ("330100", "4711302", "5", "5", "CAEPF", "00000000000066"),  # outro ramo (fora do filtro)
        ("320530", "4744005", "3", "1", "CNPJ", "00000000000055"),
    ]
    for mun, sub, esc, tipo, tipo_nome, ident in ruido:
        rows.append(
            make_vinculo(
                header,
                municipio=mun,
                subclasse=sub,
                escolaridade=esc,
                tipo_estabelecimento=tipo,
                tipo_nome=tipo_nome,
                identificador=ident,
                cbo="3000",
            )
        )
    return rows


def write_sample_file(
    path: str,
    *,
    data_dir: Optional[str] = None,
) -> Dict:
    """Gera o arquivo de amostra (CSV latin-1) e retorna metadados.

    O cabeçalho é lido do arquivo parcial real (mesmas 62 colunas) e a coluna
    ``Identificad`` é adicionada ao final.
    """
    data_dir = data_dir or config.DEFAULT_DATA_DIR
    fonte = os.path.join(data_dir, "RAIS_VINC_PUB_MG_ES_RJ_parcial.csv")
    if not os.path.exists(fonte):
        raise FileNotFoundError(
            f"Arquivo parcial não encontrado em {fonte}; gere a amostra informando "
            "um arquivo de referência ou copie o CSV parcial para dados/."
        )
    with open(fonte, "r", encoding=config.DEFAULT_DATA_ENCODING, newline="") as fh:
        header = next(csv.reader(fh, delimiter=","))
    header = [h.strip() for h in header]
    header = header + ["Identificad"]

    rows = build_sample_rows(header)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding=config.DEFAULT_DATA_ENCODING, newline="") as fh:
        writer = csv.writer(fh, delimiter=",")
        writer.writerow(header)
        for row in rows:
            writer.writerow([row.get(col, "") for col in header])

    return {
        "path": path,
        "colunas": len(header),
        "linhas": len(rows),
        "tem_identificador": True,
        "esperado": EXPECTED,
    }
