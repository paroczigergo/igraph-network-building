# igraph network building
This exercise is about using igraph (a graph module) for building network of a (sub-)folder/files structure of the local drive with storing extra file informations with the vertices.

For the implementation the following libraries and tools were used with Python 3.6.4:
  - igraph (http://igraph.org/)
  - sqlite (https://docs.python.org/2/library/sqlite3.html)
  - redis (https://redis.io/)
  - flask (http://flask.pocoo.org/)
  - pycaire (https://github.com/pygobject/pycairo)
  - for testing: locust (https://locust.io/)
  - for deploying: docker (https://www.docker.com/)

---

## Storage concept

For storing the created igraph model, two approaching were used:
- SQLite as an SQL relational database
- Redis as a NoSQL database (with key-value management)

To access SQLite we are using usual SQL queries, but with the use of Redis, another concept needs to be use.
Key-values are really useful and fast for storing strings and numbers, but we have verteces and edges. The main contept is to use JSON objects for storing them in Redis and parsing them when reading from the database. The core Redis server not support JSON storing, but with the [ReJSON](http://rejson.io/) Redis module, the ECMA-404 JSON Data Interchange Standard is implemented as a native data type.

Now the JSON encoding can be used like this:
```sh
redis.execute_command('JSON.SET','edges','.',json.dumps(self.graph.get_edgelist()))
```
 
 And the JSON decoding can be used like this:
```sh
json.loads(cache.execute_command('JSON.GET', 'edges'))
```
 
---

## Installation
The project using Docker-compose to set up the required environment.
Docker could be download from [here](https://www.docker.com/community-edition) or for Debian based Linux, use:
```sh
$ sudo apt-get install docker docker-compose
```

## Running docker-conpose
To start the system, run the following command (with a running Docker server at the background):
```sh
$ docker-compose up
```

This will use the docker-compose.yml and Dockerfile files to set up the required parts of the project and run the servers.

---

## Endpoints
Specifications are next to the implementation
- GET /graph/create
- GET /graph/redis
- GET /graph/sqlite
- GET /search/sqlite/?key={part of the file path}
- GET /search/igraph/?key={full file path}

## Testing 
The endpoints are available on the host machine's port of 5000.
For example:
```sh
 http://localhost:5000/graph/create
```
### Performance testing
[Locust](https://locust.io/), a well designed testing tool available on the host mashine's port of 8089:
```sh
 http://localhost:8089
```
