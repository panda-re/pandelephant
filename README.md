# PANDelephant

A Python3 + Postgres system for storing data about PANDA executions and recordings.

## Linux install / setup
Note that you'll need `sudo` for the pip/python commands if you're installing
outside of a virtual environment.

Clone repo:

    $ git clone git@github.com:panda-re/pandelephant.git
    $ cd pandelephant

Install dependencies:

    $ sudo apt install postgresql postgresql-contrib libpq-dev postgresql-client-common postgresql-client-10
    $ pip3 install -r requirements.txt

Create a database:

    $ sudo -su postgres createdb pandelephant

Create a user account:

    $ sudo -su postgres createuser --createdb tleek
    $ sudo -su postgres psql -c "ALTER USER tleek WITH PASSWORD 'tleek123'"

Install pandelephant:

    $ python3 ./setup.py  install

Make sure that worked by running the following in python3
```python
import pandelephant.pandelephant as pe
db_url = "postgres://tleek:tleek123@localhost/pandelephant") # Customize for your credentials
pe.init(db_url)
db = pe.create_session(db_url)
```

## Generate pandalog for ingest

Obtain panda.

    git clone git@github.com:panda-re/panda.git
    cd panda

Check out the pandelephant rose-hulman version of panda.

    git checkout pe-rh 

Compile panda.

    mkdir build
    cd build
    ../build.sh x86_64-softmmu
    make

Run panda on a replay with all the necessary plugins

    x86_64-softmmu/panda-system-x86_64 -m 1G -replay slashdot.xml-replay  -os linux-64-ubuntu:4.15.0-72-generic-noaslr-nokaslr -pandalog pe.plog  -panda syscalls_logger -panda asidstory

This will write a pandalog with stuff that can be read into pandelephant.  instruction count ranges over which threads/processes exit. System calls plus args. 

## Feed pandalog into postgres

Make sure you blow away pandelephant db first.

    sudo -su postgres dropdb pandelephant;
    sudo -su postgres createdb pandelephant

Python ingest into postgres

    PYTHONPATH=/home/tleek/git/panda/panda/scripts python3 ./scripts/plog_to_pandelephant.py -pandalog ~/git/panda/build/foo.plog -exec_name test -db_url postgres://tleek:tleek123@localhost/pandelephant

Output will look like the following:

    ...
    time=0.58 sec: Hit instr=44000000
    time=0.58 sec: Hit instr=45000000
    time=0.58 sec: Hit instr=46000000
    time=0.58 sec: Hit instr=47000000
    db commit...
    final time: 2.20 sec

At this point, you should have a postgres db!

Here's a look at four tables and some inner joins to connect things.

threads:     threads observed during the execution 

processes:   processes observed during ...

threadslice: start/end execution offset indicate time range over which a thread was observed

syscall:     system call (and args) observed at some point in execution


    psql -U tleek pandelephant
    
    psql (10.14 (Ubuntu 10.14-0ubuntu0.18.04.1))                                          
    Type "help" for help.                                                                 
                                                                                          
    pandelephant=> select * from threads                                                  
    pandelephant-> ;                                                                      
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

    pandelephant=> select * from processes;       
     process_id | execution_id | pid  | ppid      
    ------------+--------------+------+------     
              1 |            1 |  864 |    1      
              2 |            1 |  557 |    1      
              3 |            1 | 1366 | 1364      
              4 |            1 |  350 |    1      
              5 |            1 | 1355 |  368      
              6 |            1 | 1358 |  368      
              7 |            1 | 1370 | 1358      
              8 |            1 | 1371 | 1370      
              9 |            1 | 1360 |  368      
             10 |            1 | 1373 |  884      
             11 |            1 | 1364 | 1355      
             12 |            1 |  368 |    1      
             13 |            1 | 1367 |  884      
             14 |            1 |  884 |  647      
             15 |            1 | 1368 | 1358      
             16 |            1 | 1369 | 1358      
             17 |            1 | 1372 | 1370      
             18 |            1 |    1 |    0      
             19 |            1 |  562 |    1      
    (19 rows)                                     

    pandelephant=> select * from threadslice limit 20;                                                                                                                        
     threadslice_id | slice_thread_id | start_execution_offset | end_execution_offset                                                                                         
    ----------------+-----------------+------------------------+----------------------                                                                                        
                  1 |              14 |                      0 |                75147                                                                                         
                  2 |               4 |                  75504 |                94094                                                                                         
                  3 |               3 |                  94451 |               118029                                                                                         
                  4 |              19 |                 118386 |               134644                                                                                         
                  5 |              19 |                 134744 |               134905                                                                                         
                  6 |               4 |                 135005 |               147655                                                                                         
                  7 |               4 |                 147755 |               147916                                                                                         
                  8 |              19 |                 148016 |               173070                                                                                         
                  9 |              19 |                 173170 |               173331                                                                                         
                 10 |               3 |                 173431 |               191694                                                                                         
                 11 |               3 |                 191794 |               191955                                                                                         
                 12 |               4 |                 192055 |               205208                                                                                         
                 13 |               4 |                 205308 |               205469                                                                                         
                 14 |              19 |                 205569 |               300315                                                                                         
                 15 |              19 |                 300415 |               300575                                                                                         
                 16 |               2 |                 300675 |               329799                                                                                         
                 17 |               2 |                 329899 |               330060                                                                                         
                 18 |               4 |                 330160 |               351132                                                                                         
                 19 |               4 |                 351232 |               351393                                                                                         
                 20 |               3 |                 351493 |               395477                                                                                         
    (20 rows)                                                                                                                                                                 
                                                                                                                                                                              
    pandelephant=> select * from syscall limit 20;                                                                                                                            
     syscall_id |        name         |             arg1             |       arg2       |       arg3       |  arg4  | arg5 | arg6 | syscall_thread_id | execution_offset      
    ------------+---------------------+------------------------------+------------------+------------------+--------+------+------+-------------------+------------------     
              1 | sys_clock_gettime   | u32=7                        | ptr=7fffffffe4e0 |                  |        |      |      |                 4 |           136899      
              2 | sys_read            | u32=16                       | ptr=7fffffffe500 | u32=8            |        |      |      |                 4 |           138820      
              3 | sys_clock_gettime   | u32=7                        | ptr=7fffffffe850 |                  |        |      |      |                 2 |           303146      
              4 | sys_recvmsg         | i32=12                       | ptr=7fffffffd7d0 | u32=1073758272   |        |      |      |                 2 |           306633      
              5 | sys_recvmsg         | i32=12                       | ptr=7fffffffd7d0 | u32=1073758272   |        |      |      |                 2 |           316672      
              6 | sys_close           | u32=3                        |                  |                  |        |      |      |                 3 |           387353      
              7 | sys_sendmsg         | i32=12                       | ptr=7fffffffe370 | u32=16384        |        |      |      |                19 |           396003      
              8 | sys_sendmsg         | i32=12                       | ptr=7fffffffe370 | u32=16384        |        |      |      |                19 |           508146      
              9 | sys_sendmsg         | i32=12                       | ptr=7fffffffe370 | u32=16384        |        |      |      |                19 |           605068      
             10 | sys_sendmsg         | i32=12                       | ptr=7fffffffe370 | u32=16384        |        |      |      |                19 |           703722      
             11 | sys_dup2            | u32=4                        | u32=1            |                  |        |      |      |                 3 |           716314      
             12 | sys_close           | u32=4                        |                  |                  |        |      |      |                 3 |           717326      
             13 | sys_newstat         | str=/usr/local/sbin/readlink | ptr=7fffffffe060 |                  |        |      |      |                 3 |           747019      
             14 | sys_newstat         | str=/usr/local/bin/readlink  | ptr=7fffffffe060 |                  |        |      |      |                 3 |           750589      
             15 | sys_newstat         | str=/usr/sbin/readlink       | ptr=7fffffffe060 |                  |        |      |      |                 3 |           753726      
             16 | sys_newstat         | str=/usr/bin/readlink        | ptr=7fffffffe060 |                  |        |      |      |                 3 |           756859      
             17 | sys_newstat         | str=/sbin/readlink           | ptr=7fffffffe060 |                  |        |      |      |                 3 |           759560      
             18 | sys_ftruncate       | u32=22                       | u64=8388608      |                  |        |      |      |                 4 |           801687      
             19 | sys_timerfd_settime | i32=16                       | i32=1            | ptr=7fffffffe6f0 | ptr=0  |      |      |                 4 |           804651      
             20 | sys_epoll_wait      | i32=4                        | ptr=7fffffffe460 | i32=64           | i32=-1 |      |      |                19 |           818862      
    (20 rows)                                                                                                                                                                 


    pandelephant=> select names,tid,execution_offset,name,arg1,arg2 from syscall inner join threads on threads.thread_id = syscall.syscall_thread_id limit 20;        
           names       | tid  | execution_offset |        name         |             arg1             |       arg2                                                    
    -------------------+------+------------------+---------------------+------------------------------+------------------                                             
     {systemd-journal} |  350 |           136899 | sys_clock_gettime   | u32=7                        | ptr=7fffffffe4e0                                              
     {systemd-journal} |  350 |           138820 | sys_read            | u32=16                       | ptr=7fffffffe500                                              
     {systemd-logind}  |  557 |           303146 | sys_clock_gettime   | u32=7                        | ptr=7fffffffe850                                              
     {systemd-logind}  |  557 |           306633 | sys_recvmsg         | i32=12                       | ptr=7fffffffd7d0                                              
     {systemd-logind}  |  557 |           316672 | sys_recvmsg         | i32=12                       | ptr=7fffffffd7d0                                              
     {readlink,sh}     | 1366 |           387353 | sys_close           | u32=3                        |                                                               
     {dbus-daemon}     |  562 |           396003 | sys_sendmsg         | i32=12                       | ptr=7fffffffe370                                              
     {dbus-daemon}     |  562 |           508146 | sys_sendmsg         | i32=12                       | ptr=7fffffffe370                                              
     {dbus-daemon}     |  562 |           605068 | sys_sendmsg         | i32=12                       | ptr=7fffffffe370                                              
     {dbus-daemon}     |  562 |           703722 | sys_sendmsg         | i32=12                       | ptr=7fffffffe370                                              
     {readlink,sh}     | 1366 |           716314 | sys_dup2            | u32=4                        | u32=1                                                         
     {readlink,sh}     | 1366 |           717326 | sys_close           | u32=4                        |                                                               
     {readlink,sh}     | 1366 |           747019 | sys_newstat         | str=/usr/local/sbin/readlink | ptr=7fffffffe060                                              
     {readlink,sh}     | 1366 |           750589 | sys_newstat         | str=/usr/local/bin/readlink  | ptr=7fffffffe060                                              
     {readlink,sh}     | 1366 |           753726 | sys_newstat         | str=/usr/sbin/readlink       | ptr=7fffffffe060                                              
     {readlink,sh}     | 1366 |           756859 | sys_newstat         | str=/usr/bin/readlink        | ptr=7fffffffe060                                              
     {readlink,sh}     | 1366 |           759560 | sys_newstat         | str=/sbin/readlink           | ptr=7fffffffe060                                              
     {systemd-journal} |  350 |           801687 | sys_ftruncate       | u32=22                       | u64=8388608                                                   
     {systemd-journal} |  350 |           804651 | sys_timerfd_settime | i32=16                       | i32=1                                                         
     {dbus-daemon}     |  562 |           818862 | sys_epoll_wait      | i32=4                        | ptr=7fffffffe460                                              
