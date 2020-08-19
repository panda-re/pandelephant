# pandelephant

I assume you are on a Linux system

Here is what you will need to install.

% pip install sqlalchemy
% sudo apt install postgresql postgresql-contrib


Create a db:

% sudo createdb pandelephant1

You'll also need a user/role that can create databases
 
% sudo -i -u postgres
ostgres@ubuntu:~$ psql
psql (10.12 (Ubuntu 10.12-0ubuntu0.18.04.1))
Type "help" for help.

postgres=# create user tleek with password 'tleek123';
CREATE ROLE
postgres=# alter role tleek createdb;


Install pandelephant system wide

% cd pandelephant
% sudo python ./setup.py  install

python

>>> import pandelephant.pandelephant as pe
>>> db = pe.init_and_create_session("postgres://postgres:postgres123@localhost/pandelephant1", debug=True)
