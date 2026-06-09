from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


KEY_TERMS = (
    "lançamento",
    "lancamento",
    "vendas",
    "vso",
    "distrato",
    "estoque",
    "landbank",
    "banco de terrenos",
    "unidades",
    "receita",
    "valor geral",
    "vpl",
    "vgv",
)


@dataclass(frozen=True)
class TextChunk:
    text: str
    page: int
    score: int


def parse_pdf(path: Path) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    with fitz.open(path) as doc:
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if not text:
                continue
            chunks.extend(chunk_page(text, index))
    return chunks


def chunk_page(text: str, page: int, max_chars: int = 2800) -> list[TextChunk]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not paragraphs:
        paragraphs = [text]

    chunks: list[TextChunk] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 > max_chars and current:
            chunks.append(TextChunk(current, page, score_chunk(current)))
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}".strip()
    if current:
        chunks.append(TextChunk(current, page, score_chunk(current)))
    return chunks


def score_chunk(text: str) -> int:
    lowered = text.lower()
    return sum(1 for term in KEY_TERMS if term in lowered)


def select_relevant_chunks(chunks: list[TextChunk], limit: int = 8) -> list[TextChunk]:
    ranked = sorted(chunks, key=lambda chunk: (chunk.score, len(chunk.text)), reverse=True)
    return [chunk for chunk in ranked[:limit] if chunk.score > 0] or ranked[: min(limit, len(ranked))]
