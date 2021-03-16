from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Boolean, Integer, String, LargeBinary, BigInteger, DateTime, Table, ForeignKey, create_engine, Enum, Text
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import Sequence
from sqlalchemy.types import TypeDecorator

# XXX: Isn't htis postgres specific - need general error handling
from psycopg2 import OperationalError

import enum
from time import sleep

# from pandelephant.db import *

Base = declarative_base()

class DataStore():
    def __init__(self, url, debug=False, retries=3):
        # Helper to get a DB Session and store it in our (global) Session object
        # example:
        # from pandelephant import db
        # ds = db.DataStore("sqlite:///foo.sqlite")
        # print(ds.get_executions())

        if debug:
            print(f"Creating connection to {url}")
        engine = create_engine(url, echo=debug, poolclass=StaticPool)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)

        # Attempt to connect up to `retries` times
        success = False
        while not success and retries>0:
            try:
                Base.metadata.create_all(engine)
                success = True
            except OperationalError as e:
                from time import sleep
                # DB potentially overloaded "too many connections for role"
                if retries > 0:
                    print("Warning couldn't connect to DB. Retrying in 60s")
                    sleep(60)
                    retries -= 1
                else:
                    print("Error couldn't connect to DB!")
                    raise e
        if not success:
            raise RuntimeError("Couldn't connect to DB")

    def get_executions(self):
        '''
        Return a list of executions
        '''
        s = self.Session()
        return s.query(Execution).all()

    def get_proc_threads(self, exe_id):
        '''
        Given an execution_id get all processes + threads
        '''
        s = self.Session()
        return s.query(Process).join(Thread).filter(Process.execution_id == exe_id).all()

    def get_syscalls(self, thread_id):
        '''
        return all syscalls for a given thread
        '''
        s = self.Session()
        return s.query(Syscall) \
                    .outerjoin(SyscallArgument) \
                    .filter(thread_id == thread_id) \
                    .order_by(Syscall.execution_offset, SyscallArgument.position).all()

class Execution(Base):
    __tablename__ = 'executions'
    execution_id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False) # a short, user supplied name
    description = Column(String) # a longer, human description of the execution
    start_time = Column(DateTime(timezone=True)) # guest time
    end_time = Column(DateTime(timezone=True)) # guest time
    processes = relationship("Process", back_populates="execution")
    recording = relationship("Recording", back_populates="execution", uselist=False)

class Recording(Base):
    __tablename__ = 'recordings'
    recording_id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey('executions.execution_id'), nullable=False)
    file_name = Column(String, nullable=False)
    log_hash = Column(LargeBinary, unique=True, nullable=False)
    snapshot_hash = Column(LargeBinary, unique=True, nullable=False)
    qcow_hash = Column(LargeBinary) # hash of the QCOW used to make the recording taken before the recording
    execution = relationship("Execution", back_populates="recording", uselist=False)

# Note: every process must have at least one associated thread
class Process(Base):
    __tablename__ = 'processes'
    process_id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey('executions.execution_id'), nullable=False)
    pid = Column(BigInteger, nullable=False)
    ppid = Column(BigInteger)
    execution = relationship("Execution", back_populates="processes")
    threads = relationship("Thread", back_populates="process", lazy='joined')
    mappings = relationship("Mapping", back_populates="process")

class ThreadName(Base):
    __tablename__ = 'thread_names'
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey('threads.thread_id'), nullable=False)
    name = Column(String)
    thread = relationship("Thread", back_populates="names")

class Thread(Base):
    __tablename__ = 'threads'
    thread_id = Column(Integer, primary_key=True)
    process_id = Column(Integer, ForeignKey('processes.process_id'), nullable=False)
    tid = Column(BigInteger)
    create_time = Column(BigInteger, nullable=False)
    end_time = Column(DateTime(timezone=True))
    process = relationship("Process", back_populates="threads")
    names = relationship("ThreadName", back_populates="thread", lazy='joined')

class Mapping(Base):
    __tablename__ = 'mappings'
    mapping_id = Column(Integer, primary_key=True)
    process_id = Column(Integer, ForeignKey('processes.process_id'), nullable=False)
    name = Column(String)
    path = Column(String)
    base_id = Column(Integer, ForeignKey('virtual_addresses.address_id'), nullable=False)
    base = relationship("VirtualAddress", uselist=False)
    size = Column(BigInteger, nullable=False)
    process = relationship("Process", back_populates="mappings")
    codepoints = relationship("CodePoint", back_populates="mapping")

# Any time you want to use a virtual address, it needs to be a reference to this table.
class VirtualAddress(Base):
    __tablename__ = 'virtual_addresses'
    address_id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey('executions.execution_id'), nullable=False)
    asid = Column(BigInteger, nullable=False)  # We need an ASID to know address space to query
    execution_offset = Column(BigInteger, nullable=False)  # We're using an ASID so we need a "time". We're using instruction count indexed by execution start (execution starts at 0).
    address = Column(BigInteger, nullable=False)
    execution = relationship("Execution", uselist=False)

# an offset within a code module
class CodePoint(Base):
    __tablename__ = 'codepoints'
    code_point_id = Column(Integer, primary_key=True)
    mapping_id = Column(Integer, ForeignKey('mappings.mapping_id'), nullable=False)
    offset = Column(BigInteger, nullable=False)
    mapping = relationship("Mapping", back_populates="codepoints", uselist=False)


class TaintFlow(Base):
    __tablename__ = 'taint_flows'
    taint_flow_id = Column(Integer, primary_key=True)

    source_is_store = Column(Boolean, nullable=False)

    # the code points (module/offset) for src and sink of flow
    source_id = Column(Integer, ForeignKey('codepoints.code_point_id'), nullable=False)
    source = relationship('CodePoint', foreign_keys=[source_id], uselist=False)
    sink_id = Column(Integer, ForeignKey('codepoints.code_point_id'), nullable=False)
    sink = relationship('CodePoint', foreign_keys=[sink_id], uselist=False)

    # the thread that did the source
    source_thread_id = Column(Integer, ForeignKey('threads.thread_id'), nullable=False)
    source_thread = relationship('Thread', foreign_keys=[source_thread_id], uselist=False)

    # the thread that did the sink
    sink_thread_id = Column(Integer, ForeignKey('threads.thread_id'), nullable=False)
    sink_thread = relationship('Thread', foreign_keys=[sink_thread_id], uselist=False)

    # execution offsets (replay instr count) for source and sink
    source_execution_offset = Column(BigInteger, nullable=False) 
    sink_execution_offset = Column(BigInteger, nullable=False) 


# Used to indicate that a thread was observed to be executing between two points in time
class ThreadSlice(Base):
    __tablename__ = "threadslice"
    threadslice_id = Column(Integer, primary_key=True)

    # this is the thread 
    thread_id = Column(Integer, ForeignKey('threads.thread_id'), nullable=False)
    thread = relationship('Thread', foreign_keys=[thread_id], uselist=False)

    # start and end execution offsets
    start_execution_offset = Column(BigInteger, nullable=False) 
    end_execution_offset = Column(BigInteger, nullable=False) 



# A system call observed for some thread
class Syscall(Base):
    __tablename__ = "syscalls"
    syscall_id = Column(Integer, primary_key=True)
    
    name = Column(String)
    arguments = relationship("SyscallArgument", back_populates="syscall", order_by="SyscallArgument.position")  

    # this is the thread that made the call
    thread_id = Column(Integer, ForeignKey('threads.thread_id'), nullable=False)
    thread = relationship('Thread', foreign_keys=[thread_id], uselist=False)

    # and this is when it happened
    execution_offset = Column(BigInteger, nullable=False)

class ArgType(enum.Enum):
    STRING = 1
    POINTER = 2
    UNSIGNED_64 = 3
    SIGNED_64 = 4
    UNSIGNED_32 = 5
    SIGNED_32 = 6
    UNSIGNED_16 = 7
    SIGNED_16 = 8

class SyscallArgument(Base):
    __tablename__ = "syscall_arguments"
    syscall_argument_id = Column(Integer, primary_key=True)
    syscall_id = Column(Integer, ForeignKey("syscalls.syscall_id"), nullable=False)
    syscall = relationship("Syscall", back_populates="arguments", uselist=False)
    name = Column(String)
    position = Column(Integer, nullable=False)
    argument_type = Column(Enum(ArgType))
    value = Column(String)
