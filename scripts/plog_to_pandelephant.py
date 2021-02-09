#!/usr/bin/python3
from datetime import datetime, timedelta
import argparse
import sys
import time

# Assumes you've installed pandelephant package with setup.py
import pandelephant.pandelephant as pe

"""
USAGE: plog_to_pandelephant.py db_url plog
"""

debug = True

#NN = 2000000
NN = 20000000000


# HasField will raise an exception if that isnt a possible field name
# so this version translates that into a False
def hasfield(msg, field_name):
    try:
        if msg.HasField(field_name):
            return True
        else:
            return False
    except:
        return False


class Process:

    def __init__(self, pid, create_time, names, asids, tids):
        self.pid = al.pid
        self.create_time = create_time
        self.names = names
        self.asids = asids
        self.tids = tids

    def __repr__(self):
        return ("Process(names=[%s],pid=%d,asid=0x%x,create_time=%s)" % (self.names, self.pid, self.asid, str(self.create_time)))

    def __hash__(self):
        return (hash(self.__repr__()))

    def __cmp__(self, other):
        return(cmp(self.__repr__(), other.__repr__()))


def plog_to_pe(pandalog,  db_url, exec_name, exec_start=None, exec_end=None, PLogReader=None):

    if not PLogReader:
        # This is a terrible hack. If the caller has a plog object, we need to use
        # it instead of re-importing to avoid a segfault :(
        # Otherwise we import it either from pandare package or scripts directory
        # I'm sorry -af.

        # PLogReader from pandare package is easiest to import,
        # but if it's unavailable, fallback to searching PYTHONPATH
        # which users should add panda/panda/scripts to
        try:
#            from pandare.plog_reader import PLogReader
            sys.path.append("/home/tleek/git/panda-leet/panda/scripts")
            from plog_reader import PLogReader
        except ImportError:
            import PLogReader

    start_time = time.time()
    pe.init(db_url)
#    pe.init(db_url)

    s = pe.Session()

    execution_start_datetime = datetime.now()
    dbq = s.query(pe.Execution).filter(pe.Execution.name == exec_name)
    if dbq.count() == 0:
        try:
            db_execution = pe.Execution(name=exec_name, start_time=execution_start_datetime) # int(exec_start), end_time=int(exec_end))
            s.add(db_execution)
        except Exception as e:
            print(str(e))
    else:
        assert (dbq.count() == 1)
        db_execution = dbq.one()

    procs = {}

    pts = set([])

    # 1st pass over plog to get set of threads and processes.
    #
    # Why don't we just gather these on the fly? 
    # Because there are multiple sources for this information
    # and they have to be reconciled. 
    # It's oddly tricky to get a consistent view out of a replay
    # of the set of threads and processes and their names.
    # One could check at every basic block (by invoking Osi) 
    # but that would be very slow.  So we check at a few std
    # temporal points (syscall, every 100 bb, asid_info logging points)
    # and reconcile.
    # Better would be if we had callback on after-scheduler-changes-proc
    #  s.t. we could obtain proc/thread. 

    # thread is (pid, ppid, tid, create_time)
    threads = set([])
    # process is (pid, ppid)
    processes = set([])
    def collect_thread(pid, ppid, tid, create_time):
        thread = (pid, ppid, tid, create_time)
        threads.add(thread)
        process = (pid, ppid)
        processes.add(process)

    def collect_thread1(msg):
        collect_thread(msg.pid, msg.ppid, msg.tid, msg.create_time)

    print("First pass over plog...")
    t1 = time.time()
    nal = 0
    nalb = 0
    with PLogReader(pandalog) as plr:
        ii = 0
        for i, msg in enumerate(plr):
            ii += 1
            if (ii == NN):
                print("early exit..")
                break
            # asid_libraries and asid_info are required
            if msg.HasField("asid_libraries"):
                nal += 1
                al = msg.asid_libraries
                try:
                    collect_thread1(al)
                except:
                    nalb += 1
                    pass
            if msg.HasField("asid_info"):
                ai = msg.asid_info
                for tid in ai.tids:
                    collect_thread(ai.pid, ai.ppid, tid, ai.create_time)
            # these two fields are not required
            if hasfield(msg, "taint_flow"):
                collect_thread1(msg.taint_flow.source.cp.thread)
                collect_thread1(msg.taint_flow.sink.cp.thread)
            if hasfield(msg, "syscall"):
                collect_thread1(msg.syscall)


    print ("nal = %d nalb = %d" % (nal, nalb))
    t2 = time.time()
    print ("%.2f sec for 1st pass" % (t2-t1))

    # associate threads and procs
    thread2proc = {} # Key: thread (tid, create_time). Value: process (pid, ppid)
    proc2threads = {} # Key: (pid, ppid). Value: set((tid, create_time), ...)
    newthreads = set([]) # All threads observed
    for thread in threads:
        (pid, ppid, tid, create_time) = thread
        proc = (pid, ppid)
        if not (proc in proc2threads):
            proc2threads[proc] = set([])
        th = (tid,create_time)
        newthreads.add(th)
        proc2threads[proc].add(th)
        if th in thread2proc:
            #assert proc == thread2proc[th]
            if proc != thread2proc[th]:
                print("WARNING two processes for the same thread:", proc, thread2proc[th])
        thread2proc[th] = proc
    threads = newthreads

    for th in thread2proc.keys():
        print ("thread: (tid=%d, create_time=%d)" % th)
        print (" -- proc (pid=%d, ppid=%d)" % thread2proc[th])

    for proc in proc2threads.keys():
        print ("proc (pid=%d, ppid=%d)" % proc)
        for th in proc2threads[proc]:
            print (" -- thread: (tid=%d, create_time=%d)" % th)


    # 2nd pass over plog 
    # 
    # This time to get mappings for processes 
    # and names for each tid

    # Note. mappings[process] is sequence of mappings we saw for that process
    # each element in this array is a triple (instrcount, asid, m)
    # where m is the array of mappings observed at that instruction count
    mappings = {}

    tid_names = {}
    tids = {}
    num_discard = 0
    num_keep = 0
    num_mappings = 0
    num_no_mappings = 0
    xmllint = set([])
    libxml = set([])
    print("2nd pass over plog...")
    t1 = time.time()
    with PLogReader(pandalog) as plr:
        ii = 0 
        for i, msg in enumerate(plr):
            ii += 1
            if (ii == NN): break
            # this msg is the output of loaded_libs plugin
            if msg.HasField("asid_libraries") and (len(msg.asid_libraries.ListFields()) > 0):
                al = msg.asid_libraries
                if (al.pid == 0) or (al.ppid == 0) or (al.tid == 0):
                    these_mappings = None
                    num_no_mappings += 1
                    continue
                thread = (al.tid, al.create_time)
                process = (al.pid, al.ppid)
                # mappings in this plog entry
                these_mappings = []
                for mapping in al.modules:
                    mp = (mapping.name, mapping.file, mapping.base_addr, mapping.size)
                    if "xmllint" in mapping.name:
                        xmllint.add(mp)
                    if "libxml" in mapping.name:
                        libxml.add(mp)
                    these_mappings.append(mp)
                num_mappings += 1
                # collect mappings for this process, which
                # are bundled with instr count and asid
                # which we need to interpret base_addr
                if not (process in mappings):
                    mappings[process] = [(msg.instr, msg.asid, these_mappings)]
                else:
                    (x,last_asid,last_mappings) = mappings[process][-1]
                    if these_mappings == last_mappings and msg.asid == last_asid:
                        num_discard += 1
                    else:
                        mappings[process].append((msg.instr,msg.asid,these_mappings))
                        num_keep += 1
                thread2proc[thread] = process
                # there might be several names for a tid
                if not (thread in tid_names):
                    tid_names[thread] = set([])
                if not (process in tids):
                    tids[process] = set([])
                tid_names[thread].add(al.proc_name)
                tids[process].add(al.tid)

            if msg.HasField("asid_info"):
                ai = msg.asid_info
                process = (ai.pid, ai.ppid)
                if not (process in tids):
                    tids[process] = set([])
                for tid in ai.tids:
                    tids[process].add(tid)
                    thread = (tid, ai.create_time)
                    if not (thread in tid_names):
                        tid_names[thread] = set([])
                    for name in ai.names:
                        tid_names[thread].add(name)

#   import pdb; pdb.set_trace()

    t2 = time.time()
    print ("%.2f sec for 2nd pass" % (t2-t1))

    # NB: mappings is keyed on process. For each process, it provides a list of 
    # the mappings observed at some instr count we can use this later when we 
    # need a mapping for that process to find the one that makes sense
    # temporally (since its instr count is just before that of the thing we 
    # want to resolve).

    print("Num mappings = %d" % num_mappings)
    print("Num no_mappings = %d" % num_no_mappings)
    print("Kept %d of %d mappings)" % (num_keep, (num_keep+num_discard)))
    print("%d processes" % (len(processes)))
    for process in processes:
        print("proc %d %d" % process)        
        for thread in proc2threads[process]:
            (tid,create_time) = thread
            tname = str(tid_names[thread]) if thread in tid_names else ""
            print("  -- thread %d %d [%s]" % (tid, create_time, tname))
        if process in mappings:
            print("  -- %d mappings" % (len(mappings[process])))
            for (instr,b,m) in mappings[process]:
                print("    @ instr %d, %d mappings" % (instr, len(m)))
#            for mpn in m:
#                print ("  -- %s" % (str(mpn)))


    print("Constructing db objects for thread, process, and mapping")
    # construct db process, and for each,
    # create associated threads and mappings and connect them up
    db_sav_procs = {}
    db_sav_threads = {}
    db_sav_mappings = {}
    for process in processes:
#    for process in mappings.keys():
        (pid,ppid) = process
        if debug:
            print("Creating db process pid-%d ppid=%d for execution" % process)
        # why doesn't proc have a create_time?
        # bc all its threads do and the thread with earliest
        # create_time is create time of process, I think.
        db_proc = pe.Process(pid=pid, ppid=ppid, execution=db_execution)
        db_threads = []
        for thread in proc2threads[process]:
            (tid, thread_create_time) = thread
            tnames = list(tid_names[thread]) if thread in tid_names else []
            db_thread = pe.Thread(names=tnames, tid=tid, \
                                  create_time = thread_create_time)
            db_threads.append(db_thread)
            db_sav_threads[thread] = db_thread
            if debug:
                print("** Creating thread for that process names=[%s] tid=%d create_time=%d" % \
                       (tnames, tid, thread_create_time))
        db_proc.threads = db_threads
        if (process in mappings):
            db_proc.mappings = []
#            db_mappings = []
            for (instr,asid,one_mappings) in mappings[process]: # mapping_list:
                for mapping in one_mappings:
                    (m_name, m_file, m_base, m_size) = mapping
                    db_va = pe.VirtualAddress(asid=asid, execution_offset=instr, address=m_base, execution=db_execution)
                    if debug:
                        print("** Creating virtual addr for base for module in that process asid=%x base=%x instr=%d" % \
                               (asid, m_base, instr))
                    db_mapping = pe.Mapping(name=m_name, path=m_file, base=db_va, size=m_size)
                    if debug:
                        print("** Creating mapping for that process name=%s path=%s base=that virtual addr size=%d" % \
                               (m_name, m_file, m_size))
                    db_proc.mappings.append(db_mapping)
#            db_proc.mappings = db_mappings
        db_sav_procs[process] = db_proc
        s.add(db_proc)

    s.commit()
    print ("committed")


    # find mapping that corresponds best to this code point
    # at this instr count
    # that is, we have a temporal sequence of mappings for the process this thread is part of.
    # we want the mapping that makes most sense given this srcsink which also has an instruction count
    # so we search for mappings for that process that is most immediately prior to instr count
    # for the srcsink
    def get_module_offset(srcsink):
        cp = srcsink.cp
        thread = (cp.thread.tid, cp.thread.create_time)
        if not (thread in thread2proc):
            return None
        process = thread2proc[thread]
        retv = None
        for db_mapping in db_sav_procs[process].mappings:
            #  db_mapping = pe.Mapping(name=m_name, path=m_file, base=db_va, size=m_size)
            instr = db_mapping.base.execution_offset
            if instr <= srcsink.instr:
                base = db_mapping.base.address
                size = db_mapping.size 
                if cp.pc >= base and cp.pc <= (base+size-1):
                    retv = (db_mapping, cp.pc - base)
        return retv
                    


    # find db rows for process and thread indicated, if its there.
    def get_db_process_thread(db_execution, thr):
        thread = (thr.tid, thr.create_time)
        if not (thread in db_sav_threads):
            return None
        db_thread = db_sav_threads[thread]
        if not (thread in thread2proc):
            return None
        process = thread2proc[thread]
        if not (process in db_sav_procs):
            return None
        return (db_sav_procs[process], db_thread)


    def get_db_mapping(execution, db_process, asid, instr, mapping):
        (name, filename, base, size) = mapping
        # since instr is of a read/write, we need to *create* this va
        # as there's no reason to expect it will already be in the db
        db_va = pe.VirtualAddress(asid=asid, execution_offset=instr, address=base, execution=execution)
        # ditto since this mapping uses a virt address indexed to an instr,
        # we dont imagine it will already be there. so create.
        db_mapping = pe.Mapping(name=name, path=filename, base=db_va, size=size)
        # and we need to make sure mapping is assocated with our process, right?
        db_proc.mappings.append(db_mapping)
        return db_mapping



    print("3rd pass over plog -- reading flows and syscalls")
    # another pass over the plog to
    # read Flows from tsm and transform them
    # into module/offset
    instr_inc = 10000
    next_instr = instr_inc
    num_taint_flows = 0
    code_points = set([])
    t1 = time.time()
    with PLogReader(pandalog) as plr:
        ii = 0 
        for i, msg in enumerate(plr):
            ii += 1
            if (ii == NN): break
            if msg.instr > next_instr:
                print("time=%.2f sec: Hit instr=%d" % (time.time() - start_time, next_instr))
                if num_taint_flows > 0:
                    print ("num_taint_flow=%d " % num_taint_flows)
                next_instr += instr_inc

            if msg.HasField("asid_info"):
                ai = msg.asid_info
                for tid in ai.tids:
                    thread = (tid, ai.create_time)
                    assert (thread in db_sav_threads)
                    db_thread = db_sav_threads[thread]
                    db_thread_slice \
                        = pe.ThreadSlice(thread=db_thread, \
                                         start_execution_offset=ai.start_instr, \
                                         end_execution_offset=ai.end_instr)
                    s.add(db_thread_slice)

            # syscall field not *required* 
            if hasfield(msg, "syscall"):

                def syscall_value(a, scarg):
                    if scarg.HasField("str"):
                        a.argument_type = pe.ArgType.STRING
                        a.value = ("%s" % scarg.str)
                        return
                    if scarg.HasField("ptr"):
                        a.argument_type = pe.ArgType.POINTER
                        a.value = ("%x" % scarg.ptr)
                        return
                    if scarg.HasField("u64"):
                        a.argument_type = pe.ArgType.UNSIGNED_64
                        a.value = ("%d" % scarg.u64)
                        return
                    if scarg.HasField("u32"):
                        a.argument_type = pe.ArgType.UNSIGNED_32
                        a.value = ("%d" % scarg.u32)
                        return
                    if scarg.HasField("u16"):
                        a.argument_type = pe.ArgType.UNSIGNED_16
                        a.value = ("%d" % scarg.u16)
                        return
                    if scarg.HasField("i64"):
                        a.argument_type = pe.ArgType.SIGNED_64
                        a.value = ("%d" % scarg.i64)
                        return
                    if scarg.HasField("i32"):
                        a.argument_type = pe.ArgType.SIGNED_32
                        a.value = ("%d" % scarg.i32)
                        return
                    if scarg.HasField("i16"):
                        a.argument_type = pe.ArgType.SIGNED_16
                        a.value = ("%d" % scarg.i16)
                        return

                sc = msg.syscall
                thread = (sc.tid, sc.create_time)
                assert (thread in db_sav_threads)
                db_thread = db_sav_threads[thread]


                db_syscall = pe.Syscall(name=sc.call_name, thread=db_thread, execution_offset=msg.instr)
                s.add(db_syscall)
                i = 1
                for sc_arg in sc.args:
                    a = pe.SyscallArgument(syscall=db_syscall, position=i)
                    syscall_value(a, sc_arg)
                    s.add(a)
                    i += 1


            if hasfield(msg, "taint_flow"):

                tf = msg.taint_flow

                pt = get_db_process_thread(db_execution, tf.source.cp.thread)
                if pt is None:
                    continue
                (db_source_process, db_source_thread) = pt
                pt = get_db_process_thread(db_execution, tf.sink.cp.thread)
                if pt is None:
                    continue
                (db_sink_process, db_sink_thread) = pt



                source_mo = get_module_offset(tf.source)
                sink_mo = get_module_offset(tf.sink)
                if (source_mo is None) or (sink_mo is None):
                    continue



                (db_source_mapping, source_offset) = source_mo
                (db_sink_mapping, sink_offset) = sink_mo


#                db_source_mapping = get_db_mapping(db_execution, db_source_process, msg.asid, source_mapping_instr, source_mapping)
#                db_sink_mapping = get_db_mapping(db_execution, db_sink_process, msg.asid, sink_mapping_instr, sink_mapping)
                
#                p_source = (db_source_mapping, source_offset)
#                p_sink = (db_sink_mapping, sink_offset)
                                
                db_source_code_point = pe.CodePoint(mapping=db_source_mapping, offset=source_offset)
                db_sink_code_point = pe.CodePoint(mapping=db_sink_mapping, offset=sink_offset)
                
 #               code_points.add(p_source)
#                code_points.add(p_sink)
                
                db_taint_flow = pe.TaintFlow(
                    source_is_store = tf.source.is_store, \
                    source = db_source_code_point, \
                    source_thread = db_source_thread, \
                    source_execution_offset = tf.source.instr, \
                    sink = db_sink_code_point, \
                    sink_thread = db_sink_thread, \
                    sink_execution_offset = tf.sink.instr)
                
                s.add(db_taint_flow)
                num_taint_flows += 1

    print("db commit...")
    t_pre_commit = time.time()
    s.commit()
    t2 = time.time()
    print ("time to commit: %.2f sec" % (t2 - t_pre_commit))

    print("final time: %.2f sec" % (time.time() - start_time))


    
    print ("%.2f sec for 3rd pass" % (t2-t1))

    print ("num_taint_flows = %d" % num_taint_flows)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ingest pandalog and tranfer results to pandelephant")
    parser.add_argument("-db_url", help="db url", action="store", required=True)
    parser.add_argument("-pandalog", help="pandalog", action="store", required=True)
    parser.add_argument("-exec_start", "--exec-start", help="Start time for execution", action="store", default=None)
    parser.add_argument("-exec_end", "--exec-end", help="End time for execution", action="store", default=None)

    # must have this
    parser.add_argument("-exec_name", "--exec-name", help="A name for the execution", action="store", required=True)

    args = parser.parse_args()

##    db_url = "postgres://tleek:tleek123@localhost/pandelephant1"
##    if database_exists(db_url):
##        drop_database(db_url)
##    create_database(db_url)
##    pe.init("postgres://tleek:tleek123@localhost/pandelephant1")
##    db = pe.create_session("postgres://tleek:tleek123@localhost/pandelephant1")

#    exec_name="lots" 
#    db_url="postgres://tleek:tleek123@localhost/pandelephant1"
#    pandalog="/home/tleek/git/panda-leet/tsm/slash-tsm.plog-tcn-100"
#    pandalog="/home/tleek/toy/_home_tleek_toy_toy_debug.plog"

    print("%s %s" % (args.db_url, args.exec_name))
    plog_to_pe(args.pandalog, args.db_url, args.exec_name, args.exec_start, args.exec_end)

#    plog_to_pe(pandalog, db_url, exec_name, None, None)


#PYTHONPATH=/home/tleek/git/panda/panda/scripts python3 ./scripts/plog_to_pandelephant.py -pandalog ~/git/panda/build/foo.plog -exec_name test -db_url postgres://tleek:tleek123@localhost/pandelephant
