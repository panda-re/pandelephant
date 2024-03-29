from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import Pool
from typing import List, Union, Dict, Tuple
from . import _db_models
from . import _models
import uuid

class SessionTransactionWrapper:
        def __init__(self, session):
                self.session = session
                
        def __enter__(self):
                return self.session

        def __exit__(self, exc_type, exc_value, exc_traceback):
                if exc_type is not None:
                        print("Rolling Back")
                        self.session.rollback()
                else:
                        self.session.commit()
                self.session.close()

def determine_db_type_val(arg: Dict[str, Union[str, int, bool]]) -> Tuple[_db_models.ArgType, str]:
    """
    Given an argument dict with fields name, type, and value - identify the correct _db_models
    type and translate it into that type to be stored.

    Returns a tuple of the db_type and value that can be stored stored
    """
    db_type = None
    db_val = str(arg['value']) # actual data that gets stored in DB - overloaded just for bytes

    if arg['type'] == 'string':
        db_type = _db_models.ArgType.STRING
    elif arg['type'] == 'pointer':
        db_type = _db_models.ArgType.POINTER
    elif arg['type'] == 'unsigned64':
        db_type = _db_models.ArgType.UNSIGNED_64
    elif arg['type'] == 'signed64':
        db_type = _db_models.ArgType.SIGNED_64
    elif arg['type'] == 'unsigned32':
        db_type = _db_models.ArgType.UNSIGNED_32
    elif arg['type'] == 'signed32':
        db_type = _db_models.ArgType.SIGNED_32
    elif arg['type'] == 'unsigned16':
        db_type = _db_models.ArgType.UNSIGNED_16
    elif arg['type'] == 'signed16':
        db_type = _db_models.ArgType.SIGNED_16
    elif arg['type'] == 'bytes':
        # Bytes is a bit of a pain - we can't store non-null terminated strings in
        # the database, so we repr it and drop the leading 'b"' and the trailing '"'
        db_type = _db_models.ArgType.BYTES
        db_val = repr(arg['value'])[2:-1] # turn b"\x00foo\x00" into \x00foo\x00
    else:
        raise Exception("Unrecognized Argument Type: " + str(arg['type']))

    return db_type, db_val

class PandaDatastore:
    def __init__(self, url:str, debug:bool = False, pool:Pool = None):
        engine = create_engine(url, echo=debug, poolclass=pool)
        self.session_maker = sessionmaker(bind=engine)
        _db_models.Base.metadata.create_all(engine)

    def new_execution(self, name: str, description: str = None) -> _models.Execution:
        with SessionTransactionWrapper(self.session_maker()) as s:
            e = _db_models.Execution(name=name, description=description)
            s.add(e)
            s.commit()
            return _models.Execution._from_db(e)

    def get_executions(self) -> List[_models.Execution]:
        with SessionTransactionWrapper(self.session_maker()) as s:
            executions = s.query(_db_models.Execution).all()
            ret = []
            for e in executions:
                ret.append(_models.Execution._from_db(e))
            if len(ret) > 0:
                return ret
            return None

    def get_execution_by_uuid(self, execution_uuid: uuid.UUID) -> _models.Execution:
        with SessionTransactionWrapper(self.session_maker()) as s:
            e = s.query(_db_models.Execution).filter(_db_models.Execution.execution_id == execution_uuid).one_or_none()
            if e:
                return _models.Execution._from_db(e)
            return None

    def get_execution_by_name(self, name: str) -> _models.Execution:
        with SessionTransactionWrapper(self.session_maker()) as s:
            e = s.query(_db_models.Execution).filter(_db_models.Execution.name == name).one_or_none()
            if e:
                return _models.Execution._from_db(e)
            return None

    def new_recording(self, name: str, prefix: str, instruction_count: int, log_hash: List[bytes], snapshot_hash: List[bytes], description: str = None, qcow_hash: List[bytes] = None):
        with SessionTransactionWrapper(self.session_maker()) as s:
            r = _db_models.Recording(name=name, description=description, prefix=prefix, instruction_count=instruction_count, log_hash=log_hash, snapshot_hash=snapshot_hash, qcow_hash=qcow_hash)
            s.add(r)
            s.commit()
            return _models.Recording._from_db(r)

    def get_recordings(self) -> List[_models.Execution]:
        with SessionTransactionWrapper(self.session_maker()) as s:
            recordings = s.query(_db_models.Recording).all()
            ret = []
            for e in recordings:
                ret.append(_models.Recording._from_db(e))

            if len(ret) > 0:
                return ret
            return None

    def get_recording_by_uuid(self, recording_uuid: uuid.UUID) -> _models.Recording:
        with SessionTransactionWrapper(self.session_maker()) as s:
            r = s.query(_db_models.Recording).filter(_db_models.Recording.recording_id == recording_uuid).one_or_none()
            if r:
                return _models.Recording._from_db(r)
            return None

    def new_process(self, execution: _models.Execution, create_time: int, pid: int, ppid: int) -> _models.Process:
        with SessionTransactionWrapper(self.session_maker()) as s:
            p = _db_models.Process(execution_id=execution.uuid(), create_time=create_time, pid=pid, ppid=ppid)
            s.add(p)
            s.commit()
            return _models.Process._from_db(p)

    def new_thread(self, process: _models.Process, create_time: int, tid: int, names: List[str]) -> _models.Thread:
        with SessionTransactionWrapper(self.session_maker()) as s:
            db_names = []
            for n in names:
                db_names.append(_db_models.ThreadName(name=n))
            t = _db_models.Thread(process_id=process.uuid(), create_time=create_time, tid=tid, names=db_names)
            s.add(t)
            s.commit()
            return _models.Thread._from_db(t)

    def new_mapping(self, process: _models.Process, name: str, path: str, asid: int, address: int, execution_offset: int, size: int, first_seen_execution_offset: int, last_seen_execution_offset: int) -> _models.Mapping:
        with SessionTransactionWrapper(self.session_maker()) as s:
            base_addr = _db_models.VirtualAddress(execution_id=process.execution_uuid(), asid=asid, address=address, execution_offset=execution_offset)
            s.add(base_addr)
            mapping = _db_models.Mapping(process_id=process.uuid(), name=name, path=path, base=base_addr, size=size, first_seen_execution_offset=first_seen_execution_offset, last_seen_execution_offset=last_seen_execution_offset)
            s.add(mapping)
            s.commit()
            return _models.Mapping._from_db(mapping)
    
    def new_taintflow(self, is_store: bool, source_thread: _models.Thread, source_mapping: _models.Mapping, source_offset: int, source_execution_offset: int, sink_thread: _models.Thread, sink_mapping: _models.Mapping, sink_offset: int, sink_execution_offset: int) -> _models.TaintFlow:
        with SessionTransactionWrapper(self.session_maker()) as s:
            src = _db_models.CodePoint(mapping_id=source_mapping.uuid(), offset=source_offset)
            s.add(src)
            sink = _db_models.CodePoint(mapping_id=sink_mapping.uuid(), offset=sink_offset)
            s.add(sink)
            taintflow = _db_models.TaintFlow(source_is_store=is_store, source=src, source_thread_id=source_thread.uuid(), sink=sink, sink_thread_id=sink_thread.uuid(), source_execution_offset=source_execution_offset, sink_execution_offset=sink_execution_offset)
            s.add(taintflow)
            s.commit()
            return _models.TaintFlow._from_db(taintflow)

    def new_threadslice(self, thread: _models.Thread, start_execution_offset: int, end_execution_offset: int) -> _models.ThreadSlice:
        with SessionTransactionWrapper(self.session_maker()) as s:
            ts = _db_models.ThreadSlice(thread_id=thread.uuid(), start_execution_offset=start_execution_offset, end_execution_offset=end_execution_offset)
            s.add(ts)
            s.commit()
            return _models.ThreadSlice._from_db(ts)

    def new_syscall_collection(self, syscalls: List[Tuple[_models.Thread, str, int, List[Dict[str, Union[str, int, bool]]], int, int]]) -> None:
        '''
        Bulk insert a bunch of syscalls. Significantly faster than inserting one at a time in a loop, but doesn't return the db object
        '''
        syscalls_to_insert = []
        for (thread, name, retval, args, execution_offset, pc) in syscalls:
            db_args = []
            for idx, arg in enumerate(args):
                db_type, db_val = determine_db_type_val(arg)
                db_args.append(_db_models.SyscallArgument(name=arg['name'], position=idx, argument_type=db_type, value=db_val))

            syscall = _db_models.Syscall(thread_id=thread.uuid(), name=name, retval=retval, arguments=db_args, execution_offset=execution_offset, pc=pc)
            syscalls_to_insert.append(syscall)

        with SessionTransactionWrapper(self.session_maker()) as s:
            #s.bulk_save_objects(syscalls_to_insert) # XXX: Wish we could use this, but then the inserts will (silently!) drop the arguments
            s.add_all(syscalls_to_insert) # This is about 2-4x slower than bulk_save_bojects, but it actually does insert the args

    def new_syscall(self, thread: _models.Thread, name: str, retval: int, args: List[Dict[str, Union[str, int, bool]]], execution_offset: int, pc: int) -> _models.Syscall:
        with SessionTransactionWrapper(self.session_maker()) as s:
            db_args = []
            for idx, arg in enumerate(args):
                db_type, db_val = determine_db_type_val(arg)
                
                db_args.append(_db_models.SyscallArgument(name=arg['name'], position=idx, argument_type=db_type, value=db_val))
            syscall = _db_models.Syscall(thread_id=thread.uuid(), name=name, retval=retval, arguments=db_args, execution_offset=execution_offset, pc=pc)
            s.add(syscall)
            s.commit()
            return _models.Syscall._from_db(syscall)
