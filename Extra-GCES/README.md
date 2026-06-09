# Pipeline de UDA para Boletim de Conjuntura Habitacional

Projeto prático para coletar, processar e servir dados estruturados extraídos de relatórios e prévias operacionais em PDF publicados nos portais de RI de incorporadoras.

## O que a solução entrega

- Observação contínua de fontes de RI por polling configurável.
- Idempotência por SHA-256 de URL e conteúdo do PDF antes de processar.
- Parsing de PDF com PyMuPDF e chunking semântico por páginas, títulos e termos de negócio.
- Contrato semântico com Pydantic para bloquear alucinações e normalizar valores ausentes como `NULL`.
- Extração por LLM com saída JSON estruturada, com fallback determinístico para demonstração local.
- Catálogo SQLite com linhagem: cada métrica fica vinculada ao documento, URL, hash, empresa, ano, trimestre e trecho-fonte.
- API REST/JSON para consulta por empresa e período.

## Arquitetura

```text
Fontes RI -> watcher/polling -> catálogo de documentos -> parser/chunking
          -> contrato semântico -> extrator LLM/fallback -> SQLite -> API REST
```

As camadas obrigatórias do desafio estão refletidas no código:

- `src/uda_pipeline/ingestion.py`: coleta, hash e idempotência.
- `src/uda_pipeline/pdf_parser.py` e `src/uda_pipeline/extractor.py`: parsing, chunking e extração.
- `src/uda_pipeline/schemas.py`: contrato semântico dos dados.
- `src/uda_pipeline/catalog.py`: catálogo, métricas e linhagem.
- `api/main.py`: serviço REST.

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Para usar extração semântica real por LLM, copie o arquivo de exemplo e preencha sua chave:

```bash
cp .env.example .env
```

Depois edite `.env`:

```env
UDA_LLM_PROVIDER=openai
OPENAI_API_KEY=sua-chave-aqui
UDA_OPENAI_MODEL=gpt-4.1-mini
```

Com essa configuração, os PDFs são enviados ao LLM usando JSON Schema e validados pelo contrato Pydantic. Sem chave, o pipeline usa um extrator local simples apenas para demonstração e testes sem custo.

## Configuração das fontes

Edite `sources.example.yml` com URLs de PDF ou páginas de resultados:

```yaml
sources:
  - company: MRV
    url: https://ri.mrv.com.br/
    kind: results_page
  - company: EXEMPLO
    url: file:///caminho/para/previa-operacional.pdf
    kind: pdf
```

Para reduzir carga nos sites de RI, rode no máximo algumas vezes ao dia em produção. O arquivo `scripts/watch_once.py` executa uma rodada de coleta; o agendamento deve ser feito por cron, GitHub Actions, Airflow ou outro orquestrador.

## Uso

Rodar ingestão de um PDF local:

```bash
python scripts/ingest_pdf.py \
  --company "EXEMPLO" \
  --pdf "/Users/juliasantanna/Downloads/exemplo_Boletim_Conjuntura_2025_3T (1).pdf" \
  --source-url "file:///Users/juliasantanna/Downloads/exemplo_Boletim_Conjuntura_2025_3T%20(1).pdf" \
  --year 2025 \
  --quarter 3
```

Rodar uma rodada de observação:

```bash
python scripts/watch_once.py --config sources.example.yml
```

Subir API:

```bash
uvicorn api.main:app --reload
```

Exemplo de consulta:

```bash
curl "http://127.0.0.1:8000/api/conjuntura?empresa=MRV&ano=2025&trimestre=3"
```

## Endpoints

- `GET /health`: status do serviço.
- `GET /api/conjuntura?empresa=MRV&ano=2025&trimestre=3`: métricas filtradas.
- `GET /api/documentos`: documentos processados e hashes.

## Contrato semântico

O prompt instrui o LLM a:

- Extrair valores absolutos, não percentuais de variação.
- Retornar `null` para dados ausentes.
- Preservar unidade, período, empresa e evidência textual.
- Não inferir números sem evidência explícita.
- Responder apenas JSON compatível com `ExtractionResult`.

## Modo de extração

A entrega principal usa uma solução nativa em Python:

- PyMuPDF para parsing do PDF.
- Chunking semântico por blocos e termos do setor habitacional.
- OpenAI Responses API para extração semântica quando `UDA_LLM_PROVIDER=openai`.
- Pydantic/JSON Schema como contrato de validação.

O fallback local existe somente para permitir que os testes rodem sem chave externa.

## Testes

```bash
pytest
```
