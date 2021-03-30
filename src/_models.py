from __future__ import annotations
from typing import Union, Dict, List, Optional
import uuid
from datetime import datetime
from . import models_pb2 as pb
from sqlalchemy.ext.declarative.api import as_declarative
from . import _db_models
from abc import ABC, abstractmethod

class BaseModel(ABC):

    def __init__(self, uuid: uuid.UUID):
        self._uuid = uuid

    @abstractmethod
    def _from_db(db_object):
        raise NotImplementedError

    def uuid(self) -> uuid.UUID:
        return self._uuid

    @abstractmethod
    def to_pb(self):
        raise NotImplementedError

def _set_of_uuid_to_list_of_string(s: set[uuid.UUID]) -> List[str]:
    ret = []
    for e in s:
        ret.append(str(e))
    return ret

class Execution(BaseModel):
    def __init__(self, uuid: uuid.UUID, name: str, process_uuids: set[uuid.UUID], description: str = None):
        super().__init__(uuid)
        self._name = name
        self._process_uuids = process_uuids
        self._description = description
    
    def _from_db(db_object: _db_models.Execution) -> Execution:
        processes = set([])
        for p in db_object.processes:
            processes.add(p.process_id)
        return Execution(db_object.execution_id, db_object.name, processes, description=db_object.description)
    
    def name(self) -> str:
        return self._name

    def description(self) -> Optional[str]:
        return self._description

    def process_uuids(self) -> set[uuid.UUID]:
        return self._process_uuids

    def to_pb(self):
        return pb.Execution(uuid=str(self.uuid()), name=self.name(), process_uuids=_set_of_uuid_to_list_of_string(self.process_uuids()), description=self.description())

class Recording(Execution):
    def __init__(self, uuid: uuid.UUID, name: str, process_uuids: set[uuid.UUID], prefix: str, instruction_count: int, log_hash: List[bytes], snapshot_hash: List[bytes], description: str = None, qcow_hash: List[bytes] = None):
        self._prefix = prefix
        self._instruction_count = instruction_count
        self._log_hash = log_hash
        self._snapshot_hash = snapshot_hash
        self._qcow_hash = qcow_hash
        super().__init__(uuid, name, process_uuids, description=description)

    def _from_db(db_object: _db_models.Recording) -> Recording:
        processes = set([])
        for p in db_object.processes:
            processes.add(p.process_id)
        return Recording(db_object.recording_id, db_object.name, processes, db_object.prefix, db_object.instruction_count, db_object.log_hash, db_object.snapshot_hash, description=db_object.description, qcow_hash=db_object.qcow_hash)

    def prefix(self) -> str:
        return self._prefix

    def instruction_count(self) -> int:
        return self._instruction_count

    def log_hash(self) -> List[bytes]:
        return self._log_hash

    def snapshop_hash(self) -> List[bytes]:
        return self._snapshot_hash
    
    def qcow_hash(self) -> Optional[List[bytes]]:
        return self._qcow_hash

    def to_pb(self):
        e = super().to_pb()
        return pb.Recording(execution=e, prefix=self.prefix(), instruction_count=self.instruction_count(), log_hash=self.log_hash(), snapshot_hash=self.snapshop_hash(), qcow_hash=self.qcow_hash())
    
class Process(BaseModel):
    def __init__(self, uuid: uuid.UUID, execution_uuid: uuid.UUID, create_time: int, pid: int, ppid: int, thread_uuids: set[uuid.UUID], mapping_uuids: set[uuid.UUID]):
        super().__init__(uuid)
        self._execution_uuid = execution_uuid
        self._create_time = create_time
        self._pid = pid
        self._ppid = ppid
        self._thread_uuids = thread_uuids
        self._mapping_uuids = mapping_uuids
    
    def _from_db(db_object: _db_models.Process) -> Process:
        threads = set([])
        mappings = set([])
        for t in db_object.threads:
            threads.add(t.thread_id)
        for m in db_object.mappings:
            mappings.add(m.mapping_id)
        return Process(db_object.process_id, db_object.execution_id, db_object.create_time, db_object.pid, db_object.ppid, threads, mappings)

    def execution_uuid(self) -> uuid.UUID:
        return self._execution_uuid

    def create_time(self) -> int:
        return self._create_time
    
    def pid(self) -> int:
        return self._pid

    def ppid(self) -> int:
        return self._ppid

    def thread_uuids(self) -> set[uuid.UUID]:
        return self._thread_uuids

    def mapping_uuids(self) -> set[uuid.UUID]:
        return self._mapping_uuids
    
    def to_pb(self):
        return pb.Process(uuid=str(self.uuid()), execution_uuid=str(self.execution_uuid()), create_time=self.create_time(), pid=self.pid(), ppid=self.ppid(), thread_uuids=_set_of_uuid_to_list_of_string(self.thread_uuids()), mapping_uuids=_set_of_uuid_to_list_of_string(self.mapping_uuids()))

class Thread(BaseModel):
    def __init__(self, uuid: uuid.UUID, process_uuid: uuid.UUID, create_time: int, tid: int,  names: set[str]):
        super().__init__(uuid)
        self._process_uuid = process_uuid
        self._tid = tid
        self._create_time = create_time
        self._names = names
    
    def _from_db(db_object: _db_models.Thread) -> Thread:
        names = set([])
        for n in db_object.names:
            names.add(n.name)
        return Thread(db_object.thread_id, db_object.process_id, db_object.tid, db_object.create_time, names)

    def process_uuid(self) -> uuid.UUID:
        return self._process_uuid

    def tid(self) -> int:
        return self._tid

    def create_time(self) -> int:
        return self._create_time

    def names(self) -> set[str]:
        return self._names

    def to_pb(self):
        return pb.Thread(uuid=str(self.uuid()), process_uuid=str(self.process_uuid()), create_time=self.create_time(), names=list(self.names()))
        
class Mapping(BaseModel):
    def __init__(self, uuid: uuid.UUID, process_uuid: uuid.UUID, name: str, path: str, base_uuid: uuid.UUID, size: int, first_seen_execution_offset: int, last_seen_execution_offset: int):
        super().__init__(uuid)
        self._process_uuid = process_uuid
        self._name = name
        self._path = path
        self._base_uuid = base_uuid
        self._size = size
        self._first = first_seen_execution_offset
        self._last = last_seen_execution_offset
    
    def _from_db(db_object: _db_models.Mapping) -> Mapping:
        return Mapping(db_object.mapping_id, db_object.process_id, db_object.name, db_object.path, db_object.base_id, db_object.size, db_object.first_seen_execution_offset, db_object.last_seen_execution_offset)

    def process_uuid(self) -> uuid.UUID:
        return self._process_uuid

    def name(self) -> str:
        return self._name

    def path(self) -> str:
        return self._path
    
    def base_uuid(self) -> uuid.UUID:
        return self._base_uuid
    
    def size(self) -> int:
        return self._size

    def first_seen_execution_offset(self) -> int:
        return self._first
    
    def last_seen_execution_offset(self) -> int:
        return self._last

    def to_pb(self):
        return pb.Mapping(uuid=str(self.uuid()), process_uuid=str(self.process_uuid()), name=self.name(), path=self.path(), base_uuid=str(self.base_uuid()), size=self.size(), first_seen_execution_offset=self.first_seen_execution_offset(), last_seen_execution_offset=self.last_seen_execution_offset()) 

class VirtualAddress(BaseModel):
    def __init__(self, uuid: uuid.UUID, execution_uuid: uuid.UUID, asid: int, execution_offset: int, address: int):
        super().__init__(uuid)
        self._execution_uuid = execution_uuid
        self._asid = asid
        self._execution_offset = execution_offset
        self._address = address

    def _from_db(db_object: _db_models.VirtualAddress):
        return VirtualAddress(db_object.address_id, db_object.execution_id, db_object.asid, db_object.execution_offset, db_object.address)

    def execution_uuid(self) -> uuid.UUID:
        return self._execution_uuid
    
    def asid(self) -> int:
        return self._asid
    
    def execution_offset(self) -> int:
        return self._execution_offset

    def address(self) -> int:
        return self._address

    def to_pb(self):
        return pb.VirtualAddress(uuid=str(self.uuid()), execution_uuid=str(self.execution_uuid(), asid=self.asid(), execution_offset=self.execution_offset(), address=self.address()))

class CodePoint(BaseModel):
    def __init__(self, uuid: uuid.UUID, mapping_uuid: uuid.UUID, offset: int):
        super().__init__(uuid)
        self._mapping_uuid = mapping_uuid
        self._offset = offset

    def _from_db(db_object: _db_models.CodePoint) -> CodePoint:
        return CodePoint(db_object.code_point_id, db_object.mapping_id, db_object.offset)

    def mapping_uuid(self) -> uuid.UUID:
        return self._mapping_uuid

    def offset(self) -> int:
        return self._offset

    def to_pb(self):
        return pb.CodePoint(uuid=str(self.uuid()), mapping_uuid=str(self.mapping_uuid()), offset=self.offset())


class TaintFlow(BaseModel):
    def __init__(self, uuid: uuid.UUID, is_store: bool, source_code_point_uuid: uuid.UUID, source_thread_uuid: uuid.UUID, source_execution_offset: int, sink_code_point_uuid: uuid.UUID, sink_thread_uuid: uuid.UUID, sink_execution_offset: int):
        super().__init__(uuid)
        self._is_store = is_store
        self._source_code_point_uuid = source_code_point_uuid
        self._source_thread_uuid = source_thread_uuid
        self._source_execution_offset = source_execution_offset
        self._sink_code_point_uuid = sink_code_point_uuid
        self._sink_thread_uuid = sink_thread_uuid
        self._sink_execution_offset = sink_execution_offset
    
    def _from_db(db_object: _db_models.TaintFlow) -> TaintFlow:
        return TaintFlow(db_object.taint_flow_id, db_object.source_is_store, db_object.source_id, db_object.source_thread_id, db_object.source_execution_offset, db_object.sink_id, db_object.sink_thread_id, db_object.sink_execution_offset)

    def is_store(self) -> bool:
        return self._is_store
    
    def source_code_point_uuid(self) -> uuid.UUID:
        return self._source_code_point_uuid

    def source_thread_uuid(self) -> uuid.UUID:
        return self._source_thread_uuid

    def source_execution_offset(self) -> int:
        return self._source_execution_offset

    def sink_code_point_uuid(self) -> uuid.UUID:
        return self._sink_code_point_uuid

    def sink_thread_uuid(self) -> uuid.UUID:
        return self._sink_thread_uuid

    def sink_execution_offset(self) -> int:
        return self._sink_execution_offset
    
    def to_pb(self):
        return pb.TaintFlow(uuid=str(self.uuid()), is_store=self.is_store(), source_code_point_uuid=str(self.source_code_point_uuid()), source_thread_uuid=str(self.source_thread_uuid()), source_execution_offset=self.source_execution_offset(), sink_code_point_uuid=str(self.sink_code_point_uuid()), sink_thread_uuid=str(self.sink_thread_uuid()), sink_execution_offset=self.sink_execution_offset())


class ThreadSlice(BaseModel):
    def __init__(self, uuid: uuid.UUID, thread_uuid: uuid.UUID, start_execution_offset: int, end_execution_offset: int):
        super().__init__(uuid)
        self._thread_uuid = thread_uuid
        self._start_execution_offset = start_execution_offset
        self._end_execution_offset = end_execution_offset

    def _from_db(db_object: _db_models.ThreadSlice) -> ThreadSlice:
        return ThreadSlice(db_object.threadslice_id, db_object.thread_id, db_object.start_execution_offset, db_object.end_execution_offset)
    
    def thread_uuid(self) -> uuid.UUID:
        return self._thread_uuid

    def start_execution_offset(self) -> int:
        return self._start_execution_offset

    def end_execution_offset(self) -> int:
        return self._end_execution_offset

    def to_pb(self):
        return pb.ThreadSlice(uuid=str(self.uuid()), thread_uuid=str(self.thread_uuid()), start_execution_offset=self.start_execution_offset(), end_execution_offset=self.end_execution_offset())

class Syscall(BaseModel):
    def __init__(self, uuid: uuid.UUID, thread_uuid: uuid.UUID, name: str, arguments: List[Dict[str, Union[str, int, bool]]], execution_offset: int):
        super().__init__(uuid)
        self._thread_uuid = thread_uuid
        self._name = name
        self._arguments = arguments
        self._execution_offset = execution_offset

    def _from_db(db_object: _db_models.Syscall) -> Syscall:
        arguments = []
        for a in db_object.arguments:
            arg = {'name': a.name}
            if a.argument_type == _db_models.ArgType.STRING:
                arg['value'] = a.value
                arg['type'] = 'string'
            else:
                arg['value'] = int(a.value)
                
            if a.argument_type == _db_models.ArgType.POINTER:
                arg['pointer'] = True
                arg['type'] = 'pointer'
            else:
                arg['pointer'] = False

            if a.argument_type == _db_models.ArgType.UNSIGNED_64:
                arg['type'] = 'unsigned64'
            elif a.argument_type == _db_models.ArgType.SIGNED_64:
                arg['type'] = 'signed64'
            elif a.argument_type == _db_models.ArgType.UNSIGNED_32:
                arg['type'] = 'unsigned32'
            elif a.argument_type == _db_models.ArgType.SIGNED_32:
                arg['type'] = 'signed32'
            elif a.argument_type == _db_models.ArgType.UNSIGNED_16:
                arg['type'] = 'unsigned16'
            elif a.argument_type == _db_models.ArgType.SIGNED_16:
                arg['type'] = 'signed16'                                                                

            arguments.append(arg)
        
        return Syscall(db_object.syscall_id, db_object.thread_id, db_object.name, arguments, db_object.execution_offset)
    
    def thread_uuid(self) -> uuid.UUID:
        return self._thread_uuid

    def name(self) -> str:
        return self._name
    
    def arguments(self) -> List[Dict[str, Union[str, int, bool]]]:
        return self._arguments

    def execution_offset(self) -> int:
        return self._execution_offset

    def to_pb(self):
        pb_args = []
        for a in self.arguments():
            if a['type'] == 'string':
                pb_args.append(pb.SyscallArgument(name=a['name'], type=pb.ArgumentType.STRING, string_value=a['value']))
            else:
                pb_type = None
                if a['type'] == 'pointer':
                    pb_type = pb.ArgumentType.POINTER
                elif a['type'] == 'unsigned64':
                    pb_type = pb.ArgumentType.UNSIGNED_64
                elif a['type'] == 'signed64':
                    pb_type = pb.ArgumentType.SIGNED_64
                elif a['type'] == 'unsigned32':
                    pb_type = pb.ArgumentType.UNSIGNED_32
                elif a['type'] == 'signed32':
                    pb_type = pb.ArgumentType.SIGNED_32
                elif a['type'] == 'unsigned16':
                    pb_type = pb.ArgumentType.UNSIGNED_16
                elif a['type'] == 'signed16':
                    pb_type = pb.ArgumentType.SIGNED_16
                pb_args.append(pb.SyscallArgument(name=a['name'], type=pb_type, number_value=a['value']))                                                                                      
        return pb.Syscall(uuid=str(self.uuid()), name=self.name(), arguments=pb_args, thread_uuid=str(self.thread_uuid()), execution_offset=self.execution_offset())