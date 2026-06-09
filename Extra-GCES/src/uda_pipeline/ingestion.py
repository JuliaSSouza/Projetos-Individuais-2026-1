from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from .catalog import Catalog
from .config import PDF_DIR, ensure_data_dirs
from .extractor import extract_metrics
from .pdf_parser import parse_pdf


@dataclass(frozen=True)
class Source:
    company: str
    url: str
    kind: str = "pdf"
    year: int | None = None
    quarter: int | None = None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_pdf(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path)).read_bytes()
    response = httpx.get(url, timeout=45, follow_redirects=True)
    response.raise_for_status()
    return response.content


def discover_pdf_links(page_url: str) -> list[str]:
    response = httpx.get(page_url, timeout=45, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        label = anchor.get_text(" ", strip=True).lower()
        if ".pdf" not in href.lower():
            continue
        if any(term in label for term in ("prévia", "previa", "operacional", "resultados", "release")):
            links.append(str(httpx.URL(page_url).join(href)))
    return sorted(set(links))


def ingest_pdf(
    company: str,
    source_url: str,
    year: int,
    quarter: int,
    catalog: Catalog | None = None,
) -> dict:
    ensure_data_dirs()
    owns_catalog = catalog is None
    catalog = catalog or Catalog()
    try:
        content = fetch_pdf(source_url)
        content_hash = sha256_bytes(content)
        url_hash = sha256_text(source_url)
        existing = catalog.find_document(url_hash, content_hash)
        if existing:
            return {"status": "skipped", "reason": "documento já processado", "document_id": existing["id"]}

        filename = f"{company}_{year}T{quarter}_{content_hash[:12]}.pdf".replace(" ", "_")
        local_path = PDF_DIR / filename
        local_path.write_bytes(content)

        document_id = catalog.add_document(
            company=company,
            source_url=source_url,
            url_hash=url_hash,
            content_hash=content_hash,
            local_path=str(local_path),
            year=year,
            quarter=quarter,
        )
        try:
            chunks = parse_pdf(local_path)
            result = extract_metrics(company, year, quarter, chunks)
            catalog.add_metrics(document_id, result.metrics)
            catalog.set_document_status(document_id, "processed")
            return {"status": "processed", "document_id": document_id, "metrics": len(result.metrics), "warnings": result.warnings}
        except Exception:
            catalog.set_document_status(document_id, "failed")
            raise
    finally:
        if owns_catalog:
            catalog.close()


def ingest_local_copy(company: str, pdf_path: Path, source_url: str, year: int, quarter: int) -> dict:
    ensure_data_dirs()
    if not source_url:
        source_url = pdf_path.resolve().as_uri()
    return ingest_pdf(company, source_url, year, quarter)


def copy_example_pdf(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
