#!/usr/bin/env python3
"""Gera a amostra determinística COM coluna de identificação.

Uso:
  python scripts/make_sample.py [--saida dados/amostra_com_identificador.csv]

A amostra inclui o caso de uso de referência (município 330100, subclasse
2342702) e permite validar a contagem de empresas, vínculos por empresa e a
distribuição de escolaridade.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rais import config, sample  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", default=os.path.join(config.DEFAULT_DATA_DIR, "amostra_com_identificador.csv"))
    args = parser.parse_args()

    meta = sample.write_sample_file(args.saida)
    print("Amostra gerada:")
    for k, v in meta.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
