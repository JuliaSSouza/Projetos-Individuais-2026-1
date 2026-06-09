from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MetricName(str, Enum):
    launches = "lancamentos"
    gross_sales = "vendas_brutas"
    net_sales = "vendas_liquidas"
    cancellations = "distratos"
    inventory = "estoque"
    landbank = "banco_de_terrenos"
    units = "unidades"
    revenue = "receita"
    other = "outro"


class MetricRecord(BaseModel):
    company: str = Field(min_length=1)
    year: int = Field(ge=2000, le=2100)
    quarter: int = Field(ge=1, le=4)
    metric_name: MetricName
    raw_label: str = Field(min_length=1)
    value: Optional[float] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    source_excerpt: str = Field(min_length=1)
    page: Optional[int] = Field(default=None, ge=1)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("company", "raw_label", "source_excerpt")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return " ".join(value.split())


class ExtractionResult(BaseModel):
    document_company: str
    document_year: int
    document_quarter: int
    metrics: list[MetricRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DocumentRecord(BaseModel):
    id: int
    company: str
    source_url: str
    content_hash: str
    url_hash: str
    local_path: str
    year: Optional[int]
    quarter: Optional[int]
    status: str
    created_at: datetime
