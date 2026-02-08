# Elasticsearch

Elasticsearch workflow for indexing wine reviews and running reproducible benchmarks.

## Prerequisites

From repo root:

```sh
cp elasticsearch/.env.example elasticsearch/.env
```

Review `elasticsearch/.env` and set values appropriate for your local Docker setup.

## Start Elasticsearch + Kibana

```sh
cd elasticsearch && docker compose up --build
```

## Index configuration

Mappings are defined in `elasticsearch/mapping/mapping.json`.

Vector field:

- `dense_vector`
- `dims: 256`
- `similarity: cosine`

## Ingest data

```sh
uv run elasticsearch/index.py
```

If mappings/dims changed and indexing fails, rebuild the existing alias/index first:

```sh
uv run elasticsearch/index.py --recreate-index
```

Optional quick-run flags:

```sh
uv run elasticsearch/index.py --limit 1000 --chunksize 1000
```

## Direct benchmark (engine only)

`bench.py` uses direct Elasticsearch async client calls (no FastAPI/HTTP overhead):

```sh
uv run elasticsearch/bench.py
```

Protocol:

- fixed `1000` queries per search type (`fts`, `vector`) per trial
- `3` trials per search type
- reports averaged metrics across trials
- uses shared queries from `bench_queries/`

Flags:

- `--max-concurrency` (default `16`)
- `--warmup-queries` (default `10`)
- `--seed` (default `37`)

## API benchmark (optional)

`bench_api.py` is end-to-end benchmarking through FastAPI endpoints.

Run API server first:

```sh
uv run uvicorn elasticsearch.app:app --host 0.0.0.0 --port 8000
```

Then run benchmark:

```sh
uv run elasticsearch/bench_api.py
```

Extra flags for API benchmark:

- `--api-url`
- `--api-port`

## Inspect sample search results

```sh
uv run elasticsearch/query.py
```
