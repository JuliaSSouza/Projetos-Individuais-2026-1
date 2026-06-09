from uda_pipeline.extractor import fallback_extract
from uda_pipeline.pdf_parser import TextChunk


def test_fallback_ignores_standalone_percentages() -> None:
    result = fallback_extract(
        "MRV",
        2025,
        3,
        [
            TextChunk("Vendas líquidas R$ 123 milhões\nCrescimento 40%", page=1, score=1),
        ],
    )
    assert result.metrics
    assert result.metrics[0].value == 123.0
    assert result.metrics[0].metric_name.value == "vendas_liquidas"
