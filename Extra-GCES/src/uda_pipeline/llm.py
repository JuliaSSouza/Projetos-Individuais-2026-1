from __future__ import annotations

import json
import os

import httpx


SYSTEM_PROMPT = """
Você é um extrator de dados para relatórios de Relações com Investidores de incorporadoras brasileiras.
Responda somente JSON compatível com o schema solicitado.
Regras:
- Extraia valores absolutos divulgados no documento, não percentuais de variação.
- Se uma métrica estiver ausente, não invente; omita a métrica ou use null quando o campo existir.
- Preserve unidade e moeda quando aparecerem no texto.
- Cada métrica precisa conter evidência textual curta em source_excerpt.
- Não calcule números derivados sem evidência explícita no trecho.
"""


def extract_with_openai(schema: dict, user_prompt: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada")

    payload = {
        "model": os.getenv("UDA_OPENAI_MODEL", "gpt-4.1-mini"),
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "ExtractionResult",
                "schema": schema,
                "strict": True,
            }
        },
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = httpx.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=90)
    response.raise_for_status()
    data = response.json()
    text = data["output"][0]["content"][0]["text"]
    return json.loads(text)
