# PANDelephant

PANDelephant is a SQLAlchemy-based data store for collecting information gathered during analyses of PANDA executions or recordings.
The scripts in this repo describe the ORM (database schema) and support ingesting data from PANDAlog (plog) files that were created using PANDA's `asidstory` and `syscalls_logger` plugins.

These scripts are known to work with SQLite and Postgres.

## SETUP

### Docker
After cloning the repo, build an image based off the PANDA container with PANDelephant configured.
```
$ docker build . -t pe
$ docker run --rm -it pe
```

## Linux

After cloning the repo, install PANDelephant with
```
$ pip install -e .
```

Install dependencies:
```
sudo apt install postgresql postgresql-contrib libpq-dev postgresql-client-common postgresql-client-10
pip3 install -r requirements.txt
```

Unless you're starting from a previously collected plog file, you'll probably want to build and install PANDA plus the Python interface
```
git clone git@github.com:panda-re/panda.git

mkdir panda/build && cd panda/build
../build.sh x86_64-softmmu
make

pip install -e ../panda/python/core
```

## USAGE
### Note: Database URLs
Here `DB_URL` should be a SQLAlchemy database url (see [here](https://docs.sqlalchemy.org/en/14/core/engines.html#database-urls) for SQLAlchemy documentation).
For example, `sqlite:///foo.db` will be a sqlite3 database named foo.db in the local directoy (a 4th slash would indicate an absolute path).
Alternatively, for postgres you can encode credentials, database host and table: `postgres://tleek:tleek123@localhost/pandelephant`

### Generate Plog and Analyze (Example)
If you do not already have a plog, you can create one and then ingest it into a database named `test.db` by running `./generate_and_analyze.py`.
This script runs a guest under PANDA with the necessary plugins loaded (`asidstory`, `syscalls_logger`) which record data to a plog, then analyzes the plog to populate the sqlite database.

### Analyze Existing Plog
If you have already collected a plog with the required information, you can convert it into a PANDelephant database with
```
python3 -m pandelephant.parser  -db_url [DB_URL] -pandalog [PANDALOG]
```

### Programatic Ingesting Plogs
A python script can consume a plog and convert it to a PANDelephant database with
```py
from pandelephant import parser
parser.consume_plog("path_to_plog", "DB_URL", "execution_name")
```

Danger: if you have imported PANDA into the python script calling this function, you *must* pass the pandare.plog.PLogReader object to this function.
```py
from pandare import Panda, plog
from pandelephant import parser
# ...
parser.consume_plog("path_to_plog", "DB_URL", "execution_name", PLogReader=plog.PLogReader)
```

### ORM Interactions
Once data has been translated into a PANDelephant datastore, it can be analyzed through Python.

To connect to the ORM, use
```py
from pandelephant import db
ds = db.DataStore(DB_URL)
```

After creating this connection, the functions described in `pandelephant/db/db.py` can be used to query information:

```py
for ex in ds.get_executions():
  print("Execution", ex)
```

Queries can also be issued directly using the `ds.Session` object. For example, to join the processe and thread tables for the execution with ID 1: 
```
s = ds.Session()
print(s.query(Process).join(Thread).filter(Process.execution_id == 1).all())
```


### ADVANCED USAGE: ORM Inheritance
It may be advantageous to inherit the ORM and expand it with additional tables, and analysis functions.

For example a file called `CustomDataStore.py` could be created with:
```py
from pandelephant import db

class NewTable(db.Base):
    __tablename__ = 'new_table'
    iid = Column(Integer, primary_key=True)
    data = Column(String, nullable=False)

class CustomDataStore(db.DataStore):
    def get_experiments(self):
        s = self.Session()
        return s.query(NewTable).all()
```

Then this can be used in a script:
```
from CustomDataStore import CustomDataStore
ds = CustomDataStore("DB_URL")
...
```

Note custom tables will not automatically be filled in by the PANDelephant parser - you'll need to either populate your custom tables separately or extend that to add additional information while parsing plog files.

## ORM Documentation

Here's a brief overview of the tables in the ORM

Executions:  Executions of a whole system, described by unique names.

Recordings:  A PANDA recording that maps back to an execution.

threads:     threads observed during the execution 

processes:   processes observed during execution

threadslice: start/end execution offset indicate time range over which a thread was observed

Syscall:          system call observed at some point in execution connects to 0 or more SyscallArgument rows
SyscallArgument:  An argument to a syscall. Includes position, value, type, and (optionally) argument name.

mapping:     (unknown)

CodePoint:     (unknown)

WriteReadFlow:     (unknown)

ThreadSlice:     (unknown)


    sqlite3 ./test.db
    sqlite> .headers on
    sqlite> select * from threads;
     thread_id | process_id |       names        | tid  |  create_time  | end_time 
    -----------+------------+--------------------+------+---------------+----------
             1 |          1 | {systemd}          |  864 |  437773461293 |
             2 |          2 | {systemd-logind}   |  557 |   98196905969 |
             3 |          3 | {readlink,sh}      | 1366 | 1282742163157 |
             4 |          4 | {systemd-journal}  |  350 |   43258233692 |
             5 |          5 | {systemd-udevd}    | 1355 | 1282113265248 |
             6 |          6 | {systemd-udevd}    | 1358 | 1282365197925 |
             7 |          7 | {sh,(spawn)}       | 1370 | 1283854115705 |
             8 |          8 | {sh,ln}            | 1371 | 1283871341208 |
             9 |          9 | {systemd-udevd}    | 1360 | 1282385457457 |
            10 |         10 | {bash,xmllint}     | 1373 | 1284753708476 |
            11 |         11 | {sh}               | 1364 | 1282650172422 |
            12 |         12 | {systemd-udevd}    |  368 |   49617139506 |
            13 |         13 | {sleep,bash}       | 1367 | 1283505857743 |
            14 |         14 | {bash}             |  884 |  440329393298 |
            15 |         15 | {cdrom_id,(spawn)} | 1368 | 1283620952196 |
            16 |         16 | {ata_id,(spawn)}   | 1369 | 1283790580956 |
            17 |         17 | {readlink,sh}      | 1372 | 1283883670309 |
            18 |         18 | {systemd}          |    1 |    1072000000 |
            19 |         19 | {dbus-daemon}      |  562 |   98746614715 |
    (19 rows)
