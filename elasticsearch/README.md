# Elasticsearch

[Elasticsearch](https://www.elastic.co/what-is/elasticsearch) is a distributed search and analytics engine for semi-structured and unstructured data. It has been the primary tool of choice for handling full-text search (FTS) on huge text datasets, and is the backbone of many search engines in production today. Recently, Elasticsearch has added support for vector search (powered by Lucene), but a large number of use cases rely on a well-designed FTS index.

## Set up Elasticsearch container

Use the provided `docker-compose.yml` to initiate containers that run Elasticsearch and its dashboard utility, Kibana.

```sh
docker compose up --build
```

This compose file starts a persistent-volume Elasticsearch database and Kibana environment with the credentials specified in `.env` (make sure it's filled out with the requisite version numbers first). The services can be stopped and restarted at any time for maintenance and updates.

```sh
# Tear down the container but retain the persistent volume and its associated data
docker compose down

# Restart the container with persistent volume
docker compose up
```

## Ingest the data

The first step is to ingest the wine reviews dataset into Elasticsearch. Data is asynchronously ingested into the Elasticsearch database through the scripts in the `scripts` directory.

```sh
$ python index.py

python index.py
Found index wines in db, skipping index creation...

Finished indexing ID range 1-10000
Finished indexing ID range 10001-20000
Finished indexing ID range 20001-30000
Finished indexing ID range 30001-40000
Finished indexing ID range 40001-50000
Finished indexing ID range 50001-60000
Finished indexing ID range 60001-70000
Finished indexing ID range 70001-80000
Finished indexing ID range 80001-90000
Finished indexing ID range 90001-100000
Finished indexing ID range 100001-110000
Finished indexing ID range 110001-120000
Finished indexing ID range 120001-129971
Indexed data in 7.0413 sec
```

* Ingesting ~130K records into Elasticsearch via its async API takes ~7 seconds (M2 Macbook Pro)
* The script first checks the database for a mapping (that tells Elasticsearch what fields to analyze and how to index them). Each index is attached to an alias, `wines`, which is used to reference all the operations downstream
  * If no existing index or alias is found, a new one is created
* The script then validates the input JSON data via [Pydantic](https://docs.pydantic.dev) and asynchronously indexes them into the database using the [`AsyncElasticsearch` client](https://elasticsearch-py.readthedocs.io/en/v8.7.0/async.html) for fastest performance

### Run sample FTS query

```sh
python query.py
```

The full text search (via BM25 keyword matches) for the terms `tropical fruit` produce the following results.

```
Full-text search result
shape: (10, 5)
┌────────┬────────┬───────────────────────────────────┬───────────────────────────────────┬────────┐
│ id     ┆ points ┆ title                             ┆ description                       ┆ price  │
│ ---    ┆ ---    ┆ ---                               ┆ ---                               ┆ ---    │
│ i64    ┆ i64    ┆ str                               ┆ str                               ┆ f64    │
╞════════╪════════╪═══════════════════════════════════╪═══════════════════════════════════╪════════╡
│ 118060 ┆ 99     ┆ Failla 2010 Estate Vineyard Char… ┆ Shows classic, full-throttle not… ┆ 44.0   │
│ 82818  ┆ 97     ┆ Kracher 2013 Grande Cuvée Trocke… ┆ The heady, pure perfume of fig r… ┆ 95.0   │
│ 122943 ┆ 97     ┆ Château Smith Haut Lafitte 2014 … ┆ Dense and beautifully ripe, this… ┆ 95.0   │
│ 1572   ┆ 96     ┆ Château Haut-Brion 2009  Pessac-… ┆ Solid, very structured, packed w… ┆ 1200.0 │
│ …      ┆ …      ┆ …                                 ┆ …                                 ┆ …      │
│ 21080  ┆ 96     ┆ Château Lafite Rothschild 2011  … ┆ The wine shows the power typical… ┆ 685.0  │
│ 23440  ┆ 96     ┆ Bouchard Père & Fils 2011  Cheva… ┆ Initially, this is a richly ripe… ┆ 315.0  │
│ 47438  ┆ 96     ┆ Williams Selyem 2010 Drake Estat… ┆ Winemaker Bob Cabral's three 201… ┆ 65.0   │
│ 47439  ┆ 96     ┆ Williams Selyem 2010 Heintz Vine… ┆ The acidity really makes this Ch… ┆ 50.0   │
└────────┴────────┴───────────────────────────────────┴───────────────────────────────────┴────────┘
```