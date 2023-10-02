# LanceDB: A study on full-text, SQL and vector search performance

[LanceDB](https://github.com/lancedb/lancedb) is an embedded (serverless), developer-friendly and open source vector DB that serves as an alternative to a host of client-server vector DBs currently in the market. Some key features about LanceDB that make it extremely interesting are listed below, among many others listed on their GitHub repo.

* Incredibly lightweight (no DB servers to manage), because it runs entirely in-process with the application
* Extremely scalable from development to production
* Ability to perform full-text search (FTS), SQL search (via [DataFusion](https://github.com/apache/arrow-datafusion)) *and* ANN vector search
* Multi-modal data support (images, text, video, audio, point-clouds, etc.)
* Zero-copy (via [Arrow](https://github.com/apache/arrow-rs)) with automatic versioning of data on its native [Lance](https://github.com/lancedb/lance) storage format

The aim of this repo is to go over the full-text, SQL and vector search features of LanceDB on a text dataset of Wine reviews, and also to study query performance and throughput.

## Dataset

The dataset used for this demo is the [Wine Reviews](https://www.kaggle.com/zynicide/wine-reviews) dataset from Kaggle, containing ~130k reviews on wines along with other metadata. The dataset is converted to a ZIP archive, and the code for this as well as the ZIP data is provided here for reference.

## Setup

Install the dependencies in virtual environment via `requirements.txt`.

```sh
# Setup the environment for the first time
python -m venv .venv  # python -> python 3.10+

# Activate the environment (for subsequent runs)
source .venv/bin/activate

python -m pip install -r requirements.txt
```