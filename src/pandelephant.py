from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, LargeBinary, ARRAY, BigInteger, DateTime, Table, ForeignKey, create_engine, Enum
from sqlalchemy.orm import relationship, sessionmaker
import enum

Base = declarative_base()

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
    threads = relationship("Thread", back_populates="process")
    mappings = relationship("Mapping", back_populates="process")

class Thread(Base):
    __tablename__ = 'threads'
    thread_id = Column(Integer, primary_key=True)
    process_id = Column(Integer, ForeignKey('processes.process_id'), nullable=False)
    names = Column(ARRAY(String))
    tid = Column(BigInteger)
    create_time = Column(BigInteger, nullable=False)
    end_time = Column(DateTime(timezone=True))
    process = relationship("Process", back_populates="threads")

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

class CodePoint(Base):
    __tablename__ = 'codepoints'
    code_point_id = Column(Integer, primary_key=True)
    mapping_id = Column(Integer, ForeignKey('mappings.mapping_id'), nullable=False)
    offset = Column(BigInteger, nullable=False)
    mapping = relationship("Mapping", back_populates="codepoints", uselist=False)


class WriteReadFlow(Base):
    __tablename__ = 'writeread_flows'
    writeread_flow_id = Column(Integer, primary_key=True)

    # the code points (module/offset) for write and read
    write_id = Column(Integer, ForeignKey('codepoints.code_point_id'), nullable=False)
    write = relationship('CodePoint', foreign_keys=[write_id], uselist=False)
    read_id = Column(Integer, ForeignKey('codepoints.code_point_id'), nullable=False)
    read = relationship('CodePoint', foreign_keys=[read_id], uselist=False)

    # the thread that did the write
    write_thread_id = Column(Integer, ForeignKey('threads.thread_id'), nullable=False)
    write_thread = relationship('Thread', foreign_keys=[write_thread_id], uselist=False)

    # the thread that did the read
    read_thread_id = Column(Integer, ForeignKey('threads.thread_id'), nullable=False)
    read_thread = relationship('Thread', foreign_keys=[read_thread_id], uselist=False)

    # execution offsets (replay instr count) for write and read
    write_execution_offset = Column(BigInteger, nullable=False) 
    read_execution_offset = Column(BigInteger, nullable=False) # This is an offset in the exection by 


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

def create_session(url, debug=False):
    engine = create_engine(url, echo=debug)
    Session = sessionmaker(bind=engine)
    return Session()

def init(url, debug=False):
    engine = create_engine(url, echo=debug)
    Base.metadata.create_all(engine)
