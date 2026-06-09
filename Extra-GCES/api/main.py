from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Query

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uda_pipeline.catalog import Catalog


app = FastAPI(title="API de Conjuntura Habitacional", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/conjuntura")
def conjuntura(
    empresa: str | None = Query(default=None),
    ano: int | None = Query(default=None, ge=2000, le=2100),
    trimestre: int | None = Query(default=None, ge=1, le=4),
) -> dict:
    catalog = Catalog()
    try:
        data = catalog.query_metrics(empresa=empresa, ano=ano, trimestre=trimestre)
        return {"count": len(data), "data": data}
    finally:
        catalog.close()


@app.get("/api/documentos")
def documentos() -> dict:
    catalog = Catalog()
    try:
        data = catalog.list_documents()
        return {"count": len(data), "data": data}
    finally:
        catalog.close()
