"""Benchmark LanceDB search endpoints over HTTP."""

import argparse
import asyncio
import random
from pathlib import Path
from time import perf_counter

import aiohttp
from aiohttp.client_exceptions import ContentTypeError

QUERY_FILES = {
    "fts": "keyword_terms.txt",
    "vector": "vector_terms.txt",
}
SEARCH_TYPES = ("fts", "vector")
NUM_QUERIES = 1000
NUM_TRIALS = 3
DEFAULT_SEED = 37


def get_query_terms(search_type: str) -> list[str]:
    query_dir = Path(__file__).resolve().parents[1] / "bench_queries"
    query_terms_file = query_dir / QUERY_FILES[search_type]
    with open(query_terms_file, "r", encoding="utf-8") as f:
        queries = [line.strip() for line in f.readlines() if line.strip()]
    if not queries:
        raise ValueError(f"No benchmark queries found in {query_terms_file}")
    return queries


async def fetch_query(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    endpoint: str,
    query: str,
) -> tuple[dict | list | None, float]:
    async with semaphore:
        start = perf_counter()
        async with session.get(endpoint, params={"query": query}) as response:
            elapsed_ms = (perf_counter() - start) * 1000
            if response.status != 200:
                return None, elapsed_ms
            try:
                return await response.json(), elapsed_ms
            except ContentTypeError:
                return None, elapsed_ms


async def run_batch(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    endpoint: str,
    queries: list[str],
) -> list[tuple[dict | list | None, float]]:
    tasks = [
        asyncio.create_task(fetch_query(session, semaphore, endpoint, term))
        for term in queries
    ]
    return await asyncio.gather(*tasks)


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (p / 100.0) * (len(sorted_values) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    weight = rank - low
    return sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight


async def run_single_trial(
    endpoint: str,
    sampled_queries: list[str],
    warmup_queries: list[str],
    max_concurrency: int,
) -> dict[str, float]:
    semaphore = asyncio.Semaphore(max_concurrency)
    connector = aiohttp.TCPConnector(limit=max_concurrency)

    async with aiohttp.ClientSession(connector=connector) as session:
        if warmup_queries:
            await run_batch(session, semaphore, endpoint, warmup_queries)

        start = perf_counter()
        responses = await run_batch(session, semaphore, endpoint, sampled_queries)
        elapsed = perf_counter() - start

    latencies_ms = [latency for _, latency in responses]
    successes = sum(1 for response, _ in responses if response is not None)
    qps = NUM_QUERIES / elapsed if elapsed > 0 else float("inf")

    return {
        "success": float(successes),
        "elapsed_s": elapsed,
        "qps": qps,
        "p50_ms": percentile(latencies_ms, 50),
        "p95_ms": percentile(latencies_ms, 95),
        "p99_ms": percentile(latencies_ms, 99),
    }


def average_metrics(metrics_list: list[dict[str, float]]) -> dict[str, float]:
    keys = metrics_list[0].keys()
    return {
        key: sum(metrics[key] for metrics in metrics_list) / len(metrics_list)
        for key in keys
    }


async def run_benchmark(args: argparse.Namespace) -> None:
    print(
        f"Average metrics over {NUM_TRIALS} runs "
        f"for {NUM_QUERIES} queries per search type (fts, vector)."
    )

    print(
        "| search | queries | runs | success_avg | elapsed_s_avg | qps_avg | "
        "p50_ms_avg | p95_ms_avg | p99_ms_avg | max_concurrency | seed | warmup_queries |"
    )
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for i, search_type in enumerate(SEARCH_TYPES):
        endpoint = f"http://{args.api_url}:{args.api_port}/{search_type}_search"
        terms = get_query_terms(search_type)

        rng = random.Random(args.seed + i)
        sampled_queries = rng.choices(terms, k=NUM_QUERIES)
        warmup_queries = [terms[j % len(terms)] for j in range(args.warmup_queries)]

        all_trial_metrics: list[dict[str, float]] = []
        for _ in range(NUM_TRIALS):
            all_trial_metrics.append(
                await run_single_trial(
                    endpoint=endpoint,
                    sampled_queries=sampled_queries,
                    warmup_queries=warmup_queries,
                    max_concurrency=args.max_concurrency,
                )
            )

        avg = average_metrics(all_trial_metrics)

        print(
            f"| {search_type} | {NUM_QUERIES} | {NUM_TRIALS} | {avg['success']:.2f} | "
            f"{avg['elapsed_s']:.4f} | {avg['qps']:.2f} | {avg['p50_ms']:.2f} | "
            f"{avg['p95_ms']:.2f} | {avg['p99_ms']:.2f} | {args.max_concurrency} | "
            f"{args.seed} | {args.warmup_queries} |"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Random seed used for deterministic query sampling",
    )
    parser.add_argument("--max-concurrency", type=int, default=16)
    parser.add_argument(
        "--warmup-queries",
        type=int,
        default=10,
        help="Number of warmup queries to run before each trial",
    )
    parser.add_argument("--api-url", type=str, default="localhost")
    parser.add_argument("--api-port", type=int, default=8000)
    parsed_args = parser.parse_args()

    if parsed_args.max_concurrency <= 0:
        raise ValueError("--max-concurrency must be a positive integer")
    if parsed_args.warmup_queries < 0:
        raise ValueError("--warmup-queries must be >= 0")

    asyncio.run(run_benchmark(parsed_args))
