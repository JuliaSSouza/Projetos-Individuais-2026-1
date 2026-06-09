#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uda_pipeline.catalog import Catalog
from uda_pipeline.ingestion import Source, discover_pdf_links, ingest_pdf


def load_sources(path: str) -> list[Source]:
    with open(path, "r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}
    return [Source(**item) for item in raw.get("sources", [])]


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa uma rodada de observação das fontes de RI.")
    parser.add_argument("--config", default="sources.example.yml")
    args = parser.parse_args()

    catalog = Catalog()
    try:
        for source in load_sources(args.config):
            urls = [source.url] if source.kind == "pdf" else discover_pdf_links(source.url)
            for url in urls:
                if source.year is None or source.quarter is None:
                    print({"status": "ignored", "reason": "ano/trimestre não configurados", "url": url})
                    continue
                print(ingest_pdf(source.company, url, source.year, source.quarter, catalog))
    finally:
        catalog.close()


if __name__ == "__main__":
    main()
