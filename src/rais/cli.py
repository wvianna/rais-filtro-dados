"""Interface de linha de comando do sistema RAIS.

Comandos:
  files                      lista os arquivos de dados disponíveis
  schema --file X            mostra o esquema/colunas do arquivo
  analyze --file X [--municipio M] [--subclasse S] [--use-index] [--json]
  index   --file X           constrói o índice persistente do arquivo
  index   --status --file X  mostra o estado do índice
  layouts --tipo T [--busca B]   consulta as taxonomias (escolaridade,
                             subclasse, municipio)
  serve [--host H] [--port P]  inicia o servidor web

Exemplo (caso de uso de referência):
  python -m rais analyze --file dados/RAIS_VINC_PUB_MG_ES_RJ_parcial.csv \
      --municipio 330100 --subclasse 2342702
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import __version__, analyzer, config, domains, files, index, schema


def _resolve_data_path(raw: str) -> str:
    """Aceita nome de arquivo da pasta dados, caminho relativo ou absoluto."""
    df = files.find_file(raw)
    if df is not None:
        return df.path
    return raw


def cmd_files(args: argparse.Namespace) -> int:
    lista = files.list_data_files()
    if not lista:
        print("Nenhum arquivo de dados encontrado em", config.DEFAULT_DATA_DIR)
        return 1
    print(f"{'Arquivo':<60} {'Tamanho':>12}  {'Classe':<10}")
    print("-" * 88)
    for f in lista:
        print(f"{f.name:<60} {f.size_human:>12}  {f.classificacao:<10}")
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    path = _resolve_data_path(args.file)
    sch = schema.detect_schema(path)
    print(json.dumps(sch.as_dict(), ensure_ascii=False, indent=2))
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    path = _resolve_data_path(args.file)
    res = analyzer.analyze(
        path,
        municipio=args.municipio,
        subclasse=args.subclasse,
        use_index=args.use_index,
    )
    data = res.as_dict()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    print("=" * 72)
    print("RAIS · Filtro de Dados — Análise")
    print("=" * 72)
    print(f"Arquivo      : {data['arquivo']}")
    print(f"Modo         : {data['modo']}")
    print(f"Município    : {data['filtros']['municipio']}")
    print(f"Subclasse    : {data['filtros']['subclasse']}")
    print(f"Linhas totais: {data['total_linhas']}")
    print(f"Vínculos     : {data['vinculos']}")
    print("-" * 72)
    if data["estabelecimentos"]["disponivel"]:
        est = data["estabelecimentos"]
        print(f"Empresas/estabelecimentos: {est['quantidade']}")
        print("  Funcionários por estabelecimento:")
        for e in est["por_estabelecimento"]:
            print(f"    {e['identificador']:<20} tipo={e['tipo_estabelecimento'] or '-'}  vínculos={e['vinculos']}")
    else:
        print("Empresas/estabelecimentos: indisponível")
        print(f"  Motivo: {data['estabelecimentos']['motivo']}")
    print("-" * 72)
    print("Distribuição de escolaridade:")
    for e in data["escolaridade"]:
        barra = "#" * int(e["percentual"] / 2)
        print(f"  {e['codigo']:<4} {e['rotulo']:<35} {e['frequencia']:>6}  {e['percentual']:>5.1f}%  {barra}")
    ign = data["ignorados_escolaridade"]
    barra = "#" * int(ign["percentual"] / 2)
    print(f"  {'-1':<4} {ign['rotulo']:<35} {ign['frequencia']:>6}  {ign['percentual']:>5.1f}%  {barra}")
    if data["avisos"]:
        print("-" * 72)
        for aviso in data["avisos"]:
            print("[aviso]", aviso)
    print("=" * 72)
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    path = _resolve_data_path(args.file)
    if args.status:
        stats = index.index_stats(path)
        if stats is None:
            print("Índice não encontrado para", args.file)
            return 1
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0
    try:
        resultado = index.build_index(path)
    except ValueError as exc:
        print("Erro:", exc)
        return 1
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


def cmd_layouts(args: argparse.Namespace) -> int:
    dom = domains.Domains()
    if args.tipo == "escolaridade":
        itens = [{"codigo": n.codigo, "rotulo": n.rotulo} for n in dom.escolaridade]
    elif args.tipo == "subclasse":
        itens = [{"codigo": c, "rotulo": d} for c, d in dom.subclasses.items()]
    elif args.tipo == "municipio":
        itens = [{"codigo": c, "rotulo": d} for c, d in dom.municipios.items()]
    else:
        print("Tipo inválido; use escolaridade|subclasse|municipio")
        return 1
    if args.busca:
        b = args.busca.lower()
        itens = [i for i in itens if b in i["codigo"].lower() or b in i["rotulo"].lower()]
    for i in itens:
        print(f"{i['codigo']:<10} {i['rotulo']}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .server import create_server

    server = create_server(host=args.host, port=args.port)
    url = f"http://{args.host}:{args.port}/"
    print(f"RAIS · servidor web iniciado em {url} (Ctrl+C para parar)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor.")
    finally:
        server.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rais",
        description="RAIS · Filtro de Dados — consulta e análise da base RAIS (vínculos).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_files = sub.add_parser("files", help="lista os arquivos de dados")
    p_files.set_defaults(func=cmd_files)

    p_schema = sub.add_parser("schema", help="mostra o esquema do arquivo")
    p_schema.add_argument("--file", required=True)
    p_schema.set_defaults(func=cmd_schema)

    p_an = sub.add_parser("analyze", help="executa a análise (filtros + agregações)")
    p_an.add_argument("--file", required=True)
    p_an.add_argument("--municipio", default=None)
    p_an.add_argument("--subclasse", default=None)
    p_an.add_argument("--use-index", action="store_true")
    p_an.add_argument("--json", action="store_true")
    p_an.set_defaults(func=cmd_analyze)

    p_idx = sub.add_parser("index", help="constrói/consulta o índice persistente")
    p_idx.add_argument("--file", required=True)
    p_idx.add_argument("--status", action="store_true")
    p_idx.set_defaults(func=cmd_index)

    p_lay = sub.add_parser("layouts", help="consulta as taxonomias de layout")
    p_lay.add_argument("--tipo", required=True, choices=["escolaridade", "subclasse", "municipio"])
    p_lay.add_argument("--busca", default=None)
    p_lay.set_defaults(func=cmd_layouts)

    p_serve = sub.add_parser("serve", help="inicia o servidor web")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=cmd_serve)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"Erro: arquivo não encontrado — {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
