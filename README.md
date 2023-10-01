# LanceDB: Full-text and vector search

[LanceDB](https://github.com/lancedb/lancedb) is an embedded (serverless), zero management overhead, developer-friendly and open source vector DB that serves as an alternative to a host of client-server vector DBs currently in the market. Some key features about LanceDB that make it extremely interesting are listed below, among many others on their GitHub repo.

* Incredibly lightweight (no DB servers to manage), because it runs entirely in-process with your application
* Extremely scalable from development to production
* Ability to perform both full-text search (FTS), SQL search (via [DataFusion](https://github.com/apache/arrow-datafusion)) and ANN vector search
* Multi-modal data support (images, text, video, audio, point-clouds, etc)
* Zero-copy (via Arrow) with automatic versioning of data on its native [Lance](https://github.com/lancedb/lance) storage format

The aim of this repo is to go over the FTS and vector search features of LanceDB on a text dataset of Wine reviews, and also study some performance numbers on query performance.

## Dataset

The dataset used for this demo is the [Wine Reviews](https://www.kaggle.com/zynicide/wine-reviews) dataset from Kaggle, containing ~130k reviews on wines along with other metadata. The dataset is converted to a ZIP archive, and the code for this as well as the ZIP data is provided here for reference.


