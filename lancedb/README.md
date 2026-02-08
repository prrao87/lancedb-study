# LanceDB

LanceDB workflow for ingesting wine reviews, indexing, and running reproducible benchmarks.

## Prerequisites

From repo root:

```sh
cp lancedb/.env.example lancedb/.env
```

Data and indexes are stored under `lancedb/winemag`.

## Ingest data

Ingest validated rows and precompute embeddings into the `wines` table:

```sh
uv run lancedb/ingest.py --overwrite
```

Optional quick-run flags:

```sh
uv run lancedb/ingest.py --limit 1000 --chunksize 1000
```

## Build indexes

Build FTS + IVF_PQ using LanceDB async `create_index`:

```sh
uv run lancedb/index.py
```

Defaults:

- `num_partitions = 16`
- `num_sub_vectors = 64`

Override defaults:

```sh
uv run lancedb/index.py --num-partitions 8 --num-sub-vectors 64 --replace
```

FTS is built on `description` (aligned with Elasticsearch).

## Direct benchmark (engine only)

`bench.py` uses direct LanceDB async client calls (no FastAPI/HTTP overhead):

```sh
uv run lancedb/bench.py
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
uv run uvicorn lancedb.app:app --host 0.0.0.0 --port 8000
```

Then run benchmark:

```sh
uv run lancedb/bench_api.py
```

Extra flags for API benchmark:

- `--api-url`
- `--api-port`

## Inspect sample search results

```sh
uv run lancedb/query.py
```
