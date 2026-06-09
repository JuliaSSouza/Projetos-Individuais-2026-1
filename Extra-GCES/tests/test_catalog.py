from pathlib import Path

from uda_pipeline.catalog import Catalog
from uda_pipeline.schemas import MetricName, MetricRecord


def test_catalog_idempotency_and_query(tmp_path: Path) -> None:
    catalog = Catalog(tmp_path / "test.db")
    doc_id = catalog.add_document("MRV", "https://example.com/a.pdf", "urlhash", "contenthash", "a.pdf", 2025, 3)
    assert catalog.find_document("urlhash", "other")["id"] == doc_id

    catalog.add_metrics(
        doc_id,
        [
            MetricRecord(
                company="MRV",
                year=2025,
                quarter=3,
                metric_name=MetricName.net_sales,
                raw_label="Vendas liquidas",
                value=123.0,
                unit="R$ milhões",
                currency="BRL",
                source_excerpt="Vendas liquidas R$ 123 milhoes",
                page=1,
                confidence=0.9,
            )
        ],
    )

    rows = catalog.query_metrics(empresa="MRV", ano=2025, trimestre=3)
    assert len(rows) == 1
    assert rows[0]["content_hash"] == "contenthash"
    catalog.close()
