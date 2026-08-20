#!/usr/bin/env python3
"""Inicia o servidor web do sistema RAIS.

Uso:
  python scripts/run_server.py [--host 127.0.0.1] [--port 8000]
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rais.server import create_server  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = create_server(host=args.host, port=args.port)
    url = f"http://{args.host}:{args.port}/"
    print(f"RAIS · Filtro de Dados — servidor em {url}  (Ctrl+C para parar)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
