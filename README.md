# PANDelephant
PANDelephant is a Python 3 library for storing and querying data captured during dynamic analysis in a database. It was built for [PANDA](https://github.com/panda-re/panda), but we tried to make it generic enough to work with other dynamic analysis tools. It also includes the ability to serialize results as protocol buffers.

## Installation
```bash
python3 setup.py generate_py_protobufs
python3 setup.py install
```

## Setup / Usage
PANDelephant is developed using [PostgreSQL](https://www.postgresql.org) as its database backend, but [SQLite](https://sqlite.org) may work as well. To use the library, you can either use the `PandaDatastore` object / API locate in `src/api.py` or extend that object with your own methods. Those APIs should return model objects that are defined in `src/_models.py`. If you'd like to see the database tables they are described in `src/_db_models.py` which can be extended to add new tables.

To initialize a `PandaDatastore` you just need to pass the constructor a database url as described [here](https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls).

## Using with PANDA
PANDelephant was built with [PANDA](https://github.com/panda-re/panda) in mind and [PANDA](https://github.com/panda-re/panda) ships with a script that imports a plog into PANDelephant located at `panda/scripts/plog_to_pandelephant.py` in the [PANDA](https://github.com/panda-re/panda) repository.