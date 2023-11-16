# LanceDB benchmark: Full-text and vector search performance

[LanceDB](https://github.com/lancedb/lancedb) is an open source, embedded and developer-friendly vector database. Some key features about LanceDB that make it extremely valuable are listed below, among many others listed on their GitHub repo.

* Incredibly lightweight (no DB servers to manage), because it runs entirely in-process with the application
* Extremely scalable from development to production
* Ability to perform full-text search (FTS), SQL search (via [DataFusion](https://github.com/apache/arrow-datafusion)) *and* ANN vector search
* Multi-modal data support (images, text, video, audio, point-clouds, etc.)
* Zero-copy (via [Arrow](https://github.com/apache/arrow-rs)) with automatic versioning of data on its native [Lance](https://github.com/lancedb/lance) storage format

The aim of this repo is to demonstrate the full-text and vector search features of LanceDB via an end-to-end benchmark, in which we carefully study query results and throughput.

## Dataset

The dataset used for this demo is the [Wine Reviews](https://www.kaggle.com/zynicide/wine-reviews) dataset from Kaggle, containing ~130k reviews on wines along with other metadata. The dataset is converted to a ZIP archive, and the code for this as well as the ZIP data is provided here for reference.

## Comparison

Studying the performance of any tool in isolation is a challenge, so for the sake of comparison, an Elasticsearch workflow is provided in this repo. [Elasticsearch](https://github.com/elastic/elasticsearch) is a popular Lucene-based full-text and vector search engine whose use is regularly justified for full-text (and these days, vector search), so this makes it a meaningful tool to compare LanceDB against.

## Setup

Install the dependencies in virtual environment via `requirements.txt`.

```sh
# Setup the environment for the first time
python -m venv .venv  # python -> python 3.11+

# Activate the environment (for subsequent runs)
source .venv/bin/activate

python -m pip install -r requirements.txt
```

## Embedding model

The Hugging Face [model hub](https://huggingface.co/models) is a good starting point to learn which embedding models are available, including their names and how to access them. For ease of use, the `sentence-transformers` library is used in this repo to expose the embedding models to LanceDB and generating the embeddings.

The following open source embedding models for English are exposed through the `sentence-transformers` library (in order of their performance on the [MTEB leaderboard](https://huggingface.co/spaces/mteb/leaderboard)):

| Model class | Model name | Dimensions | Sequence length
|:---:|:---|:---:|:---:
BAAI General (Flag) Embedding | `BAAI/bge-large-en-v1.5` | 1024 | 512
BAAI General (Flag) Embedding | `BAAI/bge-base-en-v1.5` | 768 | 512
Alibaba General Text Embeddings | `thenlper/gte-large` | 1024 | 512
Alibaba General Text Embeddings | `thenlper/gte-base` | 768 | 512
BAAI General (Flag) Embedding | `BAAI/bge-small-en-v1.5` | 384 | 512
Alibaba General Text Embeddings | `thenlper/gte-small` | 384 | 512
SentenceBERT | `sentence-transformers/all-MiniLM-L12-v2` | 384 | 256
SentenceBERT | `sentence-transformers/all-MiniLM-L6-v2` | 384 | 256

For this study, the `BAAI/bge-small-en-v1.5` model with 384 dimensions is used.

## Benchmark results

LanceDB is clearly the fastest in terms of query throughput for the vector search use case, and is also faster than Elasticsearch for the full-text search use case when using multiple threads concurrently. In the future, if an async (non-blocking) Python client is available for LanceDB, the throughput for LanceDB for FTS is expected to be even higher.

> [!NOTE]
> * The search space comprises 129,971 wine review descriptions in either LanceDB or Elasticsearch
> * The vector dimensionality is 384
> * The benchmark is run on a 2022 M2 Macbook Pro with 16GB RAM and 8-core CPU
> * The run times reported are an average over 3 runs

### Serial Benchmark

#### Full-text search (FTS)

Queries | Elasticsearch (sec)| Elasticsearch (QPS) | LanceDB (sec) | LanceDB (QPS)
:---:|:---:|:---:|:---:|:---:
10 | 0.0516 | **193.8** | 0.0518 | 193.0
100 | 0.2589 | 386.3 | 0.2383 | **419.7**
1000 | 2.5748 | 388.6 | 2.1759 | **459.3**
10000 | 25.0318 | 399.8 | 21.3196 | **468.9**

#### Vector search

Queries | Elasticsearch (sec)| Elasticsearch (QPS) | LanceDB (sec) | LanceDB (QPS)
:---:|:---:|:---:|:---:|:---:
10 | 0.8087 | 12.4 | 0.2158 | **46.3**
100 | 7.6020 | 13.1 | 1.6803 | **59.5**
1000 | 84.0086 | 11.9 | 16.7948 | **59.5**
10000 | 842.9494 | 11.9 | 185.0582 | **54.0**

### Concurrent Benchmark

#### Full-text search (FTS)

Queries | Elasticsearch (sec)| Elasticsearch (QPS) | LanceDB (sec) | LanceDB (QPS)
:---:|:---:|:---:|:---:|:---:
10 | 0.0350 | 285.7 | 0.0284 | **351.4**
100 | 0.1243 | **804.1** | 0.2049 | 487.8
1000 | 0.6972 | **1434.5** | 1.8980 | 526.8
10000 | 6.4948 | **1539.0** | 18.9136 | 528.9

#### Vector search

Queries | Elasticsearch (sec)| Elasticsearch (QPS) | LanceDB (sec) | LanceDB (QPS)
:---:|:---:|:---:|:---:|:---:
10 | 0.2896 | 34.5 | 0.1409 | **71.0**
100 | 2.5275 | 39.6 | 1.3367 | **74.8**
1000 | 20.4268 | 48.9 | 13.3158 | **75.1**
10000 | 197.2314 | 50.7 | 139.6330 | **71.6**
