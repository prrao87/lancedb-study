# LanceDB vs Elasticsearch benchmark

Reproducible benchmark project comparing full-text search (FTS) and vector search between LanceDB and Elasticsearch on the Wine Reviews dataset.

## Setup

Run from repo root:

```sh
uv sync
```

Create env files:

```sh
cp lancedb/.env.example lancedb/.env
cp elasticsearch/.env.example elasticsearch/.env
```

- LanceDB defaults work out of the box if you keep `lancedb/.env.example` values.
- Elasticsearch requires a valid DB password set up in `elasticsearch/.env` for your local container setup.

## Shared benchmark queries

A set of keyword-based queries (for full-text search) and vector search queries are present in the following two files. These are sampled at random, 1000 times (with repetition) to create the query suites for the benchmarks.

- `bench_queries/keyword_terms.txt`
- `bench_queries/vector_terms.txt`

## Benchmark protocol

The benchmark is run in two modes: a) using the async Python clients directly in LanceDB and Elasticsearch, and b) via a FastAPI REST server that calls the respective query endpoint for LanceDB and Elasticsearch.

Both modes use the same run protocol, averaged over 3 runs, per the following criteria:

- Fixed query count: `1000` queries per search type (`fts`, `vector`) per trial
- Fixed trial count: `3` trials per search type
- Results containing QPS, P50/P95/P99 latencies

## Embedding model

The `nomic-ai/modernbert-embed-base` embedding model [on Hugging Face](https://huggingface.co/nomic-ai/modernbert-embed-base), with 256 dimensions, is used for generating embeddings on the text fields.

## LanceDB workflow

Run the following steps to ingest the data with embeddings, create and index
and run the benchmarks for LanceDB.

```bash
cd lancedb
```

### 1. Ingest data + embeddings:

```sh
uv run ingest.py --overwrite
```

### 2. Build indexes (FTS + IVF_PQ):

```sh
uv run index.py
```

### 3. Run direct-client benchmark (no FastAPI overhead):

```sh
uv run bench.py
```

### 4. End-to-end API benchmark:

```sh
uv run uvicorn app:app --host 0.0.0.0 --port 8000
uv run bench_api.py
```

## Elasticsearch workflow

Run the following steps to ingest the data with embeddings, create and index
and run the benchmarks for Elasticsearch.

### 1. Start Elasticsearch + Kibana:

```sh
cd elasticsearch && docker compose up --build
```

2. Ingest data + embeddings:

```sh
uv run elasticsearch/index.py
```

If you changed vector dims or mappings and hit indexing errors, rebuild the alias/index:

```sh
uv run elasticsearch/index.py --recreate-index
```

3. Run direct-client benchmark (no FastAPI overhead):

```sh
uv run elasticsearch/bench.py
```

4. Optional end-to-end API benchmark:

```sh
uv run uvicorn elasticsearch.app:app --host 0.0.0.0 --port 8000
uv run elasticsearch/bench_api.py
```

## Result #1: Direct Async Client

This benchmark mode runs direct async client calls against LanceDB / Elasticsearch. It isolates search-engine + embedding/runtime behavior without FastAPI overhead.

### LanceDB

Averaged metrics over best-of-3 direct-client runs for 1000 queries per search type (fts, vector).
| search | queries | runs | success_avg | elapsed_s_avg | qps_avg | p50_ms_avg | p95_ms_avg | p99_ms_avg | max_concurrency | seed | warmup_queries |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fts | 1000 | 3 | 1000.00 | 0.6522 | 1534.34 | 10.18 | 14.28 | 15.92 | 16 | 37 | 10 |
| vector | 1000 | 3 | 1000.00 | 10.3106 | 96.99 | 134.55 | 170.47 | 181.94 | 16 | 37 | 10 |

### Elasticsearch

Averaged metrics over best-of-3 direct-client runs for 1000 queries per search type (fts, vector).
| search | queries | runs | success_avg | elapsed_s_avg | qps_avg | p50_ms_avg | p95_ms_avg | p99_ms_avg | max_concurrency | seed | warmup_queries |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fts | 1000 | 3 | 1000.00 | 0.1681 | 5948.88 | 2.59 | 4.07 | 5.25 | 16 | 37 | 10 |
| vector | 1000 | 3 | 1000.00 | 10.1893 | 98.14 | 110.37 | 212.83 | 222.35 | 16 | 37 | 10 |

## Result #2: Through FastAPI Endpoints

This benchmark mode runs requests through FastAPI endpoints over HTTP, mimicking a scenario in the real world where we would typically integrate the search engine as part of a larger stack. In such cases, it makes more sense to measure end-to-end service behavior, even if it introduces a small additional overhead due to the REST API.

### LanceDB

Averaged metrics over best-of-3 runs for 1000 queries per search type (fts, vector).
| search | queries | runs | success_avg | elapsed_s_avg | qps_avg | p50_ms_avg | p95_ms_avg | p99_ms_avg | max_concurrency | seed | warmup_queries |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fts | 1000 | 3 | 1000.00 | 0.7470 | 1338.69 | 11.49 | 16.29 | 18.40 | 16 | 37 | 10 |
| vector | 1000 | 3 | 1000.00 | 10.4593 | 95.61 | 158.97 | 219.66 | 235.47 | 16 | 37 | 10 |

### Elasticsearch

Averaged metrics over best-of-3 runs for 1000 queries per search type (fts, vector).
| search | queries | runs | success_avg | elapsed_s_avg | qps_avg | p50_ms_avg | p95_ms_avg | p99_ms_avg | max_concurrency | seed | warmup_queries |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fts | 1000 | 3 | 1000.00 | 0.2899 | 3452.31 | 4.33 | 6.05 | 7.70 | 16 | 37 | 10 |
| vector | 1000 | 3 | 1000.00 | 10.6418 | 93.97 | 203.52 | 224.66 | 256.44 | 16 | 37 | 10 |

## Takeaways

- This benchmark gives a quick sense of query performance, but there are many tunable components in both systems. Depending on your use case and how each solution is tuned, results may vary.
- Benchmark numbers are a combination of multiple factors (index strategy, embedding/runtime cost, client stack, API overhead, deployment shape). End-to-end benchmarks in realistic environments are often the most meaningful.
- For many practical use cases, the difference between a 10 ms response time and a 20 ms response time is not user-visible. Reliability, operability, and total system complexity often matter just as much as raw latency.
