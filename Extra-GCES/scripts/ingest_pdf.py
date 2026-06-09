#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uda_pipeline.ingestion import ingest_local_copy


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingere um PDF local no catálogo UDA.")
    parser.add_argument("--company", required=True)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--source-url", default="")
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--quarter", required=True, type=int, choices=[1, 2, 3, 4])
    args = parser.parse_args()

    result = ingest_local_copy(args.company, args.pdf, args.source_url, args.year, args.quarter)
    print(result)


if __name__ == "__main__":
    main()
