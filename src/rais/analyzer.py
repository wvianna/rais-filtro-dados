"""Motor de análise dos vínculos RAIS.

Implementa o algoritmo do caso de uso de referência (realtoriotecnico.txt,
item 5):

1. Filtragem de registros por município e subclasse CNAE 2.0;
2. Contagem de estabelecimentos únicos via coluna de identificação,
   filtrada por TIPO ESTBL (valores ignorados descartados);
3. Cálculo de vínculos e distribuição de escolaridade;
4. Tratamento de exceções: GR INSTRUCAO == -1 e subclasse {ñ class} vão para
   a categoria "Informação Não Disponível/Ignorada".

A análise é **streaming**: varre o arquivo linha a linha (ou usa o índice
persistente para ler apenas as linhas candidatas via ``seek``), mantendo a
memória constante mesmo na base completa de 5 GB+.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import config, domains, index, reader, schema


# ---------------------------------------------------------------------------
# Normalização de valores
# ---------------------------------------------------------------------------

def _clean(value: Optional[str]) -> str:
    if value is None:
        return ""
    return value.strip()


def _norm_code(value: Optional[str]) -> Optional[str]:
    """Código normalizado: remove espaços; vazio vira None."""
    s = _clean(value)
    return s if s else None


# ---------------------------------------------------------------------------
# Estruturas de resultado
# ---------------------------------------------------------------------------

@dataclass
class EscolaridadeContagem:
    codigo: str
    rotulo: str
    frequencia: int = 0
    percentual: float = 0.0


@dataclass
class EstabelecimentoResumo:
    identificador: str
    tipo_estabelecimento: str
    vinculos: int = 0


@dataclass
class AnaliseResultado:
    arquivo: str = ""
    filtros: Dict = field(default_factory=dict)
    modo: str = "varredura_integral"          # ou "indice"
    total_linhas: int = 0
    linhas_analisadas: int = 0
    vinculos: int = 0
    escolaridade: List[EscolaridadeContagem] = field(default_factory=list)
    ignorados_escolaridade: Dict = field(default_factory=dict)
    estabelecimentos: Optional[Dict] = None
    coluna_identificacao: Optional[str] = None
    avisos: List[str] = field(default_factory=list)
    elapsed_s: float = 0.0

    def as_dict(self) -> Dict:
        return {
            "arquivo": self.arquivo,
            "filtros": self.filtros,
            "modo": self.modo,
            "total_linhas": self.total_linhas,
            "linhas_analisadas": self.linhas_analisadas,
            "vinculos": self.vinculos,
            "escolaridade": [
                {"codigo": e.codigo, "rotulo": e.rotulo, "frequencia": e.frequencia, "percentual": e.percentual}
                for e in self.escolaridade
            ],
            "ignorados_escolaridade": self.ignorados_escolaridade,
            "estabelecimentos": self.estabelecimentos,
            "coluna_identificacao": self.coluna_identificacao,
            "avisos": self.avisos,
            "elapsed_s": round(self.elapsed_s, 3),
        }


# ---------------------------------------------------------------------------
# Análise
# ---------------------------------------------------------------------------

def _matches(
    fields: Sequence[str],
    sch: schema.Schema,
    municipio: Optional[str],
    subclasse: Optional[str],
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Retorna (casou, municipio_norm, subclasse_norm)."""
    col_mun = sch.column_of("municipio")
    col_sub = sch.column_of("subclasse_cnae20")

    mun = None
    if col_mun is not None and col_mun < len(fields):
        mun = _norm_code(fields[col_mun])
    sub = None
    if col_sub is not None and col_sub < len(fields):
        sub = _norm_code(fields[col_sub])

    if municipio is not None and mun != municipio.strip():
        return False, mun, sub
    if subclasse is not None and sub != subclasse.strip():
        return False, mun, sub
    return True, mun, sub


def _composite_empresa_key(fields: Sequence[str], sch: schema.Schema) -> Tuple[str, ...]:
    """Chave composta de atributos de nível-empresa para ESTIMATIVA de empresas.

    Usada quando o arquivo não possui a coluna de identificação: a estimativa
    conta as combinações distintas destes campos (aproximação rotulada na
    interface).  Valores "Ignorado" são colapsados em "" para não fragmentar
    a chave.
    """
    partes: List[str] = []
    for logical in config.ESTIMATIVA_EMPRESA_FIELDS:
        idx = sch.column_of(logical)
        if idx is None or idx >= len(fields):
            partes.append("")
            continue
        valor = _clean(fields[idx])
        if domains.is_ignored(valor):
            partes.append("")
        else:
            partes.append(valor)
    return tuple(partes)


def _aggregate_row(
    fields: Sequence[str],
    sch: schema.Schema,
    dom: domains.Domains,
    contadores_esc: Dict[str, int],
    est_exato: Optional[set],
    est_exato_contagem: Optional[Dict[str, EstabelecimentoResumo]],
    est_estimado: set,
    est_estimado_contagem: Dict[Tuple[str, ...], int],
) -> None:
    """Acumula escolaridade e estabelecimentos (exatos ou estimativa)."""
    # --- Escolaridade -------------------------------------------------------
    col_esc = sch.column_of("escolaridade")
    codigo_esc = None
    if col_esc is not None and col_esc < len(fields):
        codigo_esc = _norm_code(fields[col_esc])

    if codigo_esc is None or domains.is_ignored(codigo_esc) or not codigo_esc.isdigit():
        contadores_esc["__ignorado__"] = contadores_esc.get("__ignorado__", 0) + 1
    else:
        num = int(codigo_esc)
        if config.ESCOLARIDADE_MIN <= num <= config.ESCOLARIDADE_MAX:
            contadores_esc[codigo_esc] = contadores_esc.get(codigo_esc, 0) + 1
        else:
            contadores_esc["__ignorado__"] = contadores_esc.get("__ignorado__", 0) + 1

    # --- TIPO ESTBL: registros com tipo ignorado não entram na contagem de
    #     estabelecimentos (realtoriotecnico.txt, item 5.2).
    col_tipo = sch.column_of("tipo_estabelecimento")
    tipo = None
    if col_tipo is not None and col_tipo < len(fields):
        tipo = _norm_code(fields[col_tipo])
    if tipo is not None and domains.is_ignored(tipo):
        return

    # --- Estimativa por chave composta (sempre acumulada) -------------------
    chave = _composite_empresa_key(fields, sch)
    est_estimado.add(chave)
    est_estimado_contagem[chave] = est_estimado_contagem.get(chave, 0) + 1

    # --- Contagem exata (somente com coluna de identificação) ---------------
    if est_exato is None or est_exato_contagem is None:
        return
    col_id = sch.column_of("identificador_estabelecimento")
    if col_id is None or col_id >= len(fields):
        return
    identificador = _norm_code(fields[col_id])
    if identificador is None or domains.is_ignored(identificador):
        return
    est_exato.add(identificador)
    resumo = est_exato_contagem.setdefault(identificador, EstabelecimentoResumo(
        identificador=identificador,
        tipo_estabelecimento=tipo or "",
    ))
    resumo.vinculos += 1


def analyze(
    path: str,
    *,
    municipio: Optional[str] = None,
    subclasse: Optional[str] = None,
    use_index: bool = False,
    index_dir: Optional[str] = None,
    encoding: Optional[str] = None,
    domains_obj: Optional[domains.Domains] = None,
) -> AnaliseResultado:
    """Executa a análise sobre um arquivo RAIS, em streaming.

    Parâmetros
    ----------
    path : caminho do arquivo CSV (parcial p/ dev ou completo 5 GB+ p/ prod).
    municipio : código IBGE (ex.: "330100").
    subclasse : subclasse CNAE 2.0 (ex.: "2342702").
    use_index : usa o índice persistente quando disponível.
    """
    started = time.monotonic()
    dom = domains_obj or domains.Domains()
    sch = schema.detect_schema(path, encoding)

    resultado = AnaliseResultado(
        arquivo=os.path.basename(path),
        filtros={
            "municipio": municipio.strip() if municipio else None,
            "subclasse": subclasse.strip() if subclasse else None,
        },
        coluna_identificacao=(
            sch.column_of(config.DEFAULT_ESTABELECIMENTO_ID) is not None
        ),
    )

    if not sch.present("municipio"):
        resultado.avisos.append(
            "Arquivo sem coluna de município; a filtragem geográfica fica inativa."
        )
    if not sch.present("escolaridade"):
        resultado.avisos.append(
            "Arquivo sem coluna de escolaridade; distribuição indisponível."
        )

    # Estabelecimentos: contagem exata quando há coluna de identificação;
    # caso contrário, ESTIMATIVA por chave composta (rotulada na interface).
    if sch.present(config.DEFAULT_ESTABELECIMENTO_ID):
        est_set: set = set()
        est_contagem: Dict[str, EstabelecimentoResumo] = {}
    else:
        est_set = None
        est_contagem = None
        resultado.avisos.append(
            "Arquivo sem coluna de identificação do estabelecimento (IDENTIFICAD/CNPJ). "
            "A contagem de empresas é uma ESTIMATIVA por chave composta (aproximada); "
            "use um arquivo com essa coluna para contagem exata."
        )

    # Estimativa por chave composta (sempre acumulada como apoio/fallback).
    est_estimado: set = set()
    est_estimado_contagem: Dict[Tuple[str, ...], int] = {}

    contadores_esc: Dict[str, int] = {}

    # ------------------------------------------------------------------ modo
    used_index = False
    if use_index and index.index_exists(path, index_dir):
        offs = index.lookup_offsets(
            path,
            municipio=resultado.filtros["municipio"],
            subclasse=resultado.filtros["subclasse"],
            index_dir=index_dir,
        )
        if offs:
            used_index = True
            resultado.modo = "indice"
            resultado.total_linhas = offs  # corrigido abaixo
            for fields in reader.read_rows_at_offsets(path, offs, encoding=encoding, delimiter=sch.delimiter):
                casou, _, _ = _matches(fields, sch, municipio, subclasse)
                if not casou:
                    continue
                resultado.linhas_analisadas += 1
                resultado.vinculos += 1
                _aggregate_row(fields, sch, dom, contadores_esc, est_set, est_contagem, est_estimado, est_estimado_contagem)

    if not used_index:
        resultado.modo = "varredura_integral"
        for _row_no, fields in reader.iter_rows(path, encoding=encoding, delimiter=sch.delimiter):
            resultado.total_linhas += 1
            casou, _, _ = _matches(fields, sch, municipio, subclasse)
            if not casou:
                continue
            resultado.linhas_analisadas += 1
            resultado.vinculos += 1
            _aggregate_row(fields, sch, dom, contadores_esc, est_set, est_contagem, est_estimado, est_estimado_contagem)

    # ----------------------------------------------------- pós-processamento
    total_validos = resultado.vinculos - contadores_esc.get("__ignorado__", 0)
    niveis = dom.escolaridade
    for nivel in niveis:
        if nivel.codigo == "-1":
            continue
        freq = contadores_esc.get(nivel.codigo, 0)
        pct = (freq / resultado.vinculos * 100.0) if resultado.vinculos else 0.0
        resultado.escolaridade.append(
            EscolaridadeContagem(codigo=nivel.codigo, rotulo=nivel.rotulo, frequencia=freq, percentual=pct)
        )
    # Ordena por código numérico (1..11).
    resultado.escolaridade.sort(key=lambda e: int(e.codigo))

    freq_ign = contadores_esc.get("__ignorado__", 0)
    pct_ign = (freq_ign / resultado.vinculos * 100.0) if resultado.vinculos else 0.0
    resultado.ignorados_escolaridade = {
        "rotulo": domains.ROTULO_ESCOLARIDADE,
        "frequencia": freq_ign,
        "percentual": pct_ign,
    }

    # Estabelecimentos: exato (coluna de identificação) ou estimativa.
    if est_set is not None and est_contagem is not None:
        por_est = sorted(
            (
                {
                    "identificador": r.identificador,
                    "tipo_estabelecimento": r.tipo_estabelecimento or None,
                    "vinculos": r.vinculos,
                }
                for r in est_contagem.values()
            ),
            key=lambda e: (-e["vinculos"], e["identificador"]),
        )
        resultado.estabelecimentos = {
            "disponivel": True,
            "estimado": False,
            "modo": "exato (coluna de identificação)",
            "quantidade": len(por_est),
            "por_estabelecimento": por_est,
            "total_vinculos_considerados": sum(e["vinculos"] for e in por_est),
        }
    else:
        resultado.estabelecimentos = {
            "disponivel": True,
            "estimado": True,
            "modo": "estimativa (chave composta · sem coluna de identificação)",
            "quantidade": len(est_estimado),
            "por_estabelecimento": [],
            "total_vinculos_considerados": sum(est_estimado_contagem.values()),
            "motivo": "arquivo sem coluna de identificação; contagem aproximada por chave composta",
        }

    resultado.elapsed_s = time.monotonic() - started
    return resultado
