# Elasticsearch

[Elasticsearch](https://www.elastic.co/what-is/elasticsearch) is a distributed search and analytics engine for semi-structured and unstructured data. It has been the primary tool of choice for handling full-text search (FTS) on huge text datasets, and is the backbone of many search engines in production today. Recently, Elasticsearch has added support for vector search (powered by Lucene), but a large number of use cases rely on a well-designed FTS index.

## Setup Elasticsearch in a container

Use the provided `docker-compose.yml` to initiate containers that run Elasticsearch and its dashboard utility, Kibana.

```
docker compose up --build
```

This compose file starts a persistent-volume Elasticsearch database and Kibana environment with the credentials specified in `.env` (make sure it's filled out with the requisite version numbers first). The services can be stopped and restarted at any time for maintenance and updates.

```
# Tear down the container but retain the persistent volume and its associated data
docker compose down

# Restart the container with persistent volume
docker compose up
```

## Ingest the data

The first step is to ingest the wine reviews dataset into Elasticsearch. Data is asynchronously ingested into the Elasticsearch database through the scripts in the `scripts` directory.

```sh
python index.py
```

* This script first checks the database for a mapping (that tells Elasticsearch what fields to analyze and how to index them). Each index is attached to an alias, "wines", which is used to reference all the operations downstream
  * If no existing index or alias is found, new ones are created
* The script then validates the input JSON data via [Pydantic](https://docs.pydantic.dev) and asynchronously indexes them into the database using the [`AsyncElasticsearch` client](https://elasticsearch-py.readthedocs.io/en/v8.7.0/async.html) for fastest performance
