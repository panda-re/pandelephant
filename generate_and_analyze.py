#!/usr/bin/env python3
import os
from pandare import Panda, plog

# Settings
rr_name   = "test"
plog_name = "test.plog"
db_name   = "test.db"
execution_name = "test_exec"

reset = False
if reset:
    print("0) Deleting old files")
    for f in [rr_name +"-rr-snp", rr_name +"-rr-nondet.log", plog_name, db_name]:
        if os.path.isfile(f):
            os.remove(f)
    

# Step 1: create recording of a few commands running
panda = Panda(generic="x86_64")

if os.path.isfile(rr_name + "-rr-snp") and os.path.isfile(rr_name + "-rr-nondet.log"):
    print(f"\n1) Using existing recording: {rr_name}")
else:
    print(f"\n1) Generating recording {rr_name}")

    @panda.queue_blocking
    def drive():
        panda.record_cmd("whoami; ls; find /etc | grep foo", recording_name=rr_name)
        panda.end_analysis()

    panda.run()


# Step 2: replay the recording with plugins required for pandelephant data collection
if os.path.isfile(plog_name):
    print(f"\n2) Using existing PANDALOG: {plog_name}")
else:
    print(f"\n2) Generating PANDALOG {plog_name}")

    # Load required plugins and set PLOG
    panda.load_plugin("syscalls_logger")
    panda.load_plugin("asidstory")
    panda.set_pandalog(plog_name)

    # Analyze replay to populate PLOG
    panda.run_replay(rr_name)


# Step 3: Convert to PLOG to a DB
db_str = "sqlite:///"+db_name

if os.path.isfile(db_name):
    print(f"\n3) Using existing DB: {db_name}")
else:
    print(f"\n3) Translating PLOG into DB: {db_name}")
    from pandelephant import parser
    parser.consume_plog(plog_name, db_str, execution_name, PLogReader=plog.PLogReader)

# Step 4 analyze DB
print("\n4) Analyzing PANDelephant DB")
from pandelephant import db
ds = db.Connection(db_str)

print("\n4a) All syscalls for a single process")
# Glue together results from helper function
for ex in ds.get_executions():
    threads = ds.get_proc_threads(ex.execution_id)
    procs = [] # (name, pid, ppid)
    for thread in threads:
        proc_names = thread.threads[0].names
        if len(proc_names) > 1 and "bash" in proc_names:
            proc_names.remove("bash")
        procs.append((", ".join(proc_names), thread.pid, thread.ppid))

    for (proc_name, pid, ppid) in procs:
        print(f"{proc_name}: {pid} (parent {ppid})")

        for syscall in ds.get_syscalls(pid):
            args = ", ".join([arg.value for arg in syscall.arguments])
            print(f"{syscall.name} ({args})")
        break

print("\n4a) Filenames opened per process")
from sqlalchemy import func
# Custom query
for ex in ds.get_executions():
    processes = ds.get_proc_threads(ex.execution_id)
    procs = [] # (name, pid, ppid)
    for process in processes:
        for thread in process.threads:
            if len(thread.names) > 1 and "bash" in thread.names:
                thread.names.remove("bash")
            print(f"{', '.join(thread.names)} pid {process.pid}, tid {thread.tid}, created at {thread.create_time}")

            s = ds.Session()
            counts = s.query(db.Syscall, func.count(db.Syscall.name)) \
                    .filter(db.Syscall.thread_id == thread.thread_id) \
                    .group_by(db.Syscall.name).all()
            for (syscall, cnt) in sorted(counts, key=lambda x: -x[1]):
                print(syscall.name, cnt)
            print()
