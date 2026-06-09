from __future__ import annotations

import json
import os
import re

from .llm import extract_with_openai
from .pdf_parser import TextChunk, select_relevant_chunks
from .schemas import ExtractionResult, MetricName, MetricRecord


LABEL_MAP = {
    "lan": MetricName.launches,
    "vendas brutas": MetricName.gross_sales,
    "venda bruta": MetricName.gross_sales,
    "vendas líquidas": MetricName.net_sales,
    "vendas liquidas": MetricName.net_sales,
    "distrato": MetricName.cancellations,
    "estoque": MetricName.inventory,
    "banco de terrenos": MetricName.landbank,
    "landbank": MetricName.landbank,
    "receita": MetricName.revenue,
    "unidades": MetricName.units,
}


def build_extraction_prompt(company: str, year: int, quarter: int, chunks: list[TextChunk]) -> str:
    source = "\n\n".join(f"[pagina {chunk.page}]\n{chunk.text}" for chunk in chunks)
    schema = json.dumps(ExtractionResult.model_json_schema(), ensure_ascii=False)
    return f"""
Empresa: {company}
Ano: {year}
Trimestre: {quarter}

Schema JSON:
{schema}

Trechos selecionados do PDF:
{source}
"""


def extract_metrics(company: str, year: int, quarter: int, chunks: list[TextChunk]) -> ExtractionResult:
    relevant = select_relevant_chunks(chunks)
    provider = os.getenv("UDA_LLM_PROVIDER", "fallback").lower()
    if provider == "openai":
        prompt = build_extraction_prompt(company, year, quarter, relevant)
        result = extract_with_openai(ExtractionResult.model_json_schema(), prompt)
        return ExtractionResult.model_validate(result)
    return fallback_extract(company, year, quarter, relevant)


def fallback_extract(company: str, year: int, quarter: int, chunks: list[TextChunk]) -> ExtractionResult:
    metrics: list[MetricRecord] = []
    for chunk in chunks:
        for line in chunk.text.splitlines():
            normalized = " ".join(line.split())
            metric_name = classify_label(normalized)
            if metric_name is None:
                continue
            value = first_numeric_value(normalized)
            if value is None:
                continue
            metrics.append(
                MetricRecord(
                    company=company,
                    year=year,
                    quarter=quarter,
                    metric_name=metric_name,
                    raw_label=normalized[:120],
                    value=value,
                    unit=detect_unit(normalized),
                    currency="BRL" if "r$" in normalized.lower() else None,
                    source_excerpt=normalized[:260],
                    page=chunk.page,
                    confidence=0.55,
                )
            )
    return ExtractionResult(
        document_company=company,
        document_year=year,
        document_quarter=quarter,
        metrics=dedupe_metrics(metrics),
        warnings=["Extração local de demonstração usada; configure UDA_LLM_PROVIDER=openai para extração semântica por LLM."],
    )


def classify_label(text: str) -> MetricName | None:
    lowered = text.lower()
    if "%" in lowered and not any(token in lowered for token in ("r$", "mil", "unidade", "vgv")):
        return None
    for needle, metric in LABEL_MAP.items():
        if needle in lowered:
            return metric
    return None


def first_numeric_value(text: str) -> float | None:
    match = re.search(r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)", text)
    if not match:
        return None
    raw = match.group(1).replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def detect_unit(text: str) -> str | None:
    lowered = text.lower()
    if "r$" in lowered and ("milh" in lowered or "mm" in lowered):
        return "R$ milhões"
    if "unidade" in lowered or " unidades" in lowered:
        return "unidades"
    if "mil m" in lowered or "m²" in lowered:
        return "m²"
    return None


def dedupe_metrics(metrics: list[MetricRecord]) -> list[MetricRecord]:
    seen: set[tuple[str, str, float | None]] = set()
    unique: list[MetricRecord] = []
    for metric in metrics:
        key = (metric.metric_name.value, metric.raw_label, metric.value)
        if key in seen:
            continue
        seen.add(key)
        unique.append(metric)
    return unique
