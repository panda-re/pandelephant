from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Boolean, Integer, String, LargeBinary, BigInteger, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
import uuid
from .utils import sys_cat.SyscallCategory
Base = declarative_base()

# GUID class taken from https://docs.sqlalchemy.org/en/13/core/custom_types.html#backend-agnostic-guid-type
class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    """
    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                # hexstring
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value

class Execution(Base):
    __tablename__ = 'executions'
    execution_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(String(20))
    name = Column(String, unique=True, nullable=False) # a short, user supplied name
    description = Column(String) # a longer, human description of the execution
    processes = relationship("Process", back_populates="execution")

    __mapper_args__ = {
            'polymorphic_identity': 'Execution',
            'polymorphic_on':type
    }

class Recording(Execution):
    __tablename__ = 'recordings'
    recording_id = Column(GUID, ForeignKey('executions.execution_id'), primary_key=True)
    prefix = Column(String, nullable=False)
    instruction_count = Column(BigInteger, nullable=False)
    log_hash = Column(LargeBinary, unique=True, nullable=False)
    snapshot_hash = Column(LargeBinary, unique=True, nullable=False)
    qcow_hash = Column(LargeBinary) # hash of the QCOW used to make the recording taken before the recording
    __mapper_args__ = {
            'polymorphic_identity': 'Recording'
    }

class Process(Base):
    __tablename__ = 'processes'
    process_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(String(20))
    execution_id = Column(GUID, ForeignKey('executions.execution_id'), nullable=False)
    create_time = Column(BigInteger, nullable=False)
    pid = Column(BigInteger, nullable=False)
    ppid = Column(BigInteger)
    execution = relationship("Execution", back_populates="processes")
    threads = relationship("Thread", back_populates="process")
    mappings = relationship("Mapping", back_populates="process")

    __mapper_args__ = {
            'polymorphic_identity': 'Process',
            'polymorphic_on':type
    }

class ThreadName(Base):
    __tablename__ = 'thread_names'
    id = Column(Integer, primary_key=True)
    thread_id = Column(GUID, ForeignKey('threads.thread_id'), nullable=False)
    name = Column(String)
    thread = relationship("Thread", back_populates="names")

class Thread(Base):
    __tablename__ = 'threads'
    thread_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(String(20))
    process_id = Column(GUID, ForeignKey('processes.process_id'), nullable=False)
    tid = Column(BigInteger)
    create_time = Column(BigInteger, nullable=False)
    process = relationship("Process", back_populates="threads")
    names = relationship("ThreadName", back_populates="thread")

    __mapper_args__ = {
            'polymorphic_identity': 'Thread',
            'polymorphic_on':type
    }


class Mapping(Base):
    __tablename__ = 'mappings'
    mapping_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(String(20))
    process_id = Column(GUID, ForeignKey('processes.process_id'), nullable=False)
    name = Column(String)
    path = Column(String)
    base_id = Column(GUID, ForeignKey('virtual_addresses.address_id'), nullable=False)
    base = relationship("VirtualAddress", uselist=False)
    size = Column(BigInteger, nullable=False)
    first_seen_execution_offset = Column(BigInteger, nullable=False)
    last_seen_execution_offset = Column(BigInteger, nullable=False)

    process = relationship("Process", back_populates="mappings")
    codepoints = relationship("CodePoint", back_populates="mapping")

    __mapper_args__ = {
            'polymorphic_identity': 'Mapping',
            'polymorphic_on':type
    }

class VirtualAddress(Base):
    __tablename__ = 'virtual_addresses'
    address_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(String(20))
    execution_id = Column(GUID, ForeignKey('executions.execution_id'), nullable=False)
    asid = Column(BigInteger, nullable=False)  # We need an ASID to know address space to query
    execution_offset = Column(BigInteger, nullable=False)  # We're using an ASID so we need a "time". We're using instruction count indexed by execution start (execution starts at 0).
    address = Column(BigInteger, nullable=False)
    execution = relationship("Execution", uselist=False)

    __mapper_args__ = {
            'polymorphic_identity': 'VirtualAddress',
            'polymorphic_on':type
    }

# an offset within a code module
class CodePoint(Base):
    __tablename__ = 'code_points'
    code_point_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(String(20))
    mapping_id = Column(GUID, ForeignKey('mappings.mapping_id'), nullable=False)
    offset = Column(BigInteger, nullable=False)
    mapping = relationship("Mapping", back_populates="codepoints", uselist=False)

    __mapper_args__ = {
            'polymorphic_identity': 'CodePoint',
            'polymorphic_on':type
    }

class TaintFlow(Base):
    __tablename__ = 'taint_flows'
    taint_flow_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(String(20))

    source_is_store = Column(Boolean, nullable=False)

    # the code points (module/offset) for src and sink of flow
    source_id = Column(GUID, ForeignKey('code_points.code_point_id'), nullable=False)
    source = relationship('CodePoint', foreign_keys=[source_id], uselist=False)
    sink_id = Column(GUID, ForeignKey('code_points.code_point_id'), nullable=False)
    sink = relationship('CodePoint', foreign_keys=[sink_id], uselist=False)

    # the thread that did the source
    source_thread_id = Column(GUID, ForeignKey('threads.thread_id'), nullable=False)
    source_thread = relationship('Thread', foreign_keys=[source_thread_id], uselist=False)

    # the thread that did the sink
    sink_thread_id = Column(GUID, ForeignKey('threads.thread_id'), nullable=False)
    sink_thread = relationship('Thread', foreign_keys=[sink_thread_id], uselist=False)

    # execution offsets (replay instr count) for source and sink
    source_execution_offset = Column(BigInteger, nullable=False)
    sink_execution_offset = Column(BigInteger, nullable=False)

    __mapper_args__ = {
            'polymorphic_identity': 'TaintFlow',
            'polymorphic_on':type
    }


# Used to indicate that a thread was observed to be executing between two points in time

class ThreadSlice(Base):
    __tablename__ = "threadslice"
    threadslice_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(String(20))

    # this is the thread
    thread_id = Column(GUID, ForeignKey('threads.thread_id'), nullable=False)
    thread = relationship('Thread', foreign_keys=[thread_id], uselist=False)

    # start and end execution offsets
    start_execution_offset = Column(BigInteger, nullable=False)
    end_execution_offset = Column(BigInteger, nullable=False)

    __mapper_args__ = {
            'polymorphic_identity': 'ThreadSlice',
            'polymorphic_on':type
    }

# A system call observed for some thread
class Syscall(Base):
    __tablename__ = "syscalls"
    syscall_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(String(20))

    name = Column(String)
    arguments = relationship("SyscallArgument", back_populates="syscall", order_by="SyscallArgument.position")

    # this is the thread that made the call
    thread_id = Column(GUID, ForeignKey('threads.thread_id'), nullable=False)
    thread = relationship('Thread', foreign_keys=[thread_id], uselist=False)

    # and this is when it happened
    execution_offset = Column(BigInteger, nullable=False)

    __mapper_args__ = {
            'polymorphic_identity': 'Syscall',
            'polymorphic_on':type
    }

# TODO: is this subclassing OK? Verify with Andy
class SyscallDWARF(Syscall):

    '''
    A system call with 2 additional pieces of semantic information:
        1. Field granular data for struct arguments (TODO: configurable recursion depth)
        2. A functional category (non-exhaustive)
    '''

    __tablename__ = "syscallsDWARF"
    syscallDWARF_id = Column(GUID, ForeignKey('syscalls.syscall_id'), primary_key=True)
    # type -> Inherited from parent
    # name -> Inherited from parent
    arguments = relationship("SyscallDWARFArgument", back_populates="syscallDWARF", order_by="SyscallDWARFArgument.position")
    # thread_id -> Inherited from parent
    # thread -> Inherited from parent
    # execution -> Inherited from parent
    category = Column(Enum(SyscallCategory))

    __mapper_args__ = {
            'polymorphic_identity': 'SyscallDWARF',
            'polymorphic_on':type
    }

class ArgType(enum.Enum):
    STRING = 1
    POINTER = 2
    UNSIGNED_64 = 3
    SIGNED_64 = 4
    UNSIGNED_32 = 5
    SIGNED_32 = 6
    UNSIGNED_16 = 7
    SIGNED_16 = 8

# TODO: is this OK? Verify with Andy
class StructMember(Base):
    __tablename__ = "struct_members"
    struct_member_id = Column(Integer, primary_key=True)
    syscall_id = Column(GUID, ForeignKey("syscalls.syscall_id"), nullable=False)
    syscall_dwarf_argument = relationship("SyscallDWARFArgument", back_populates="members", uselist=False)
    struct_member_name = Column(String)
    struct_member_type = Column(Enum(ArgType))
    struct_member_value = Column(String)
    position = Column(Integer, nullable=False)

class SyscallArgument(Base):
    __tablename__ = "syscall_arguments"
    syscall_argument_id = Column(Integer, primary_key=True)
    syscall_id = Column(GUID, ForeignKey("syscalls.syscall_id"), nullable=False)
    syscall = relationship("Syscall", back_populates="arguments", uselist=False)
    name = Column(String)
    position = Column(Integer, nullable=False)
    argument_type = Column(Enum(ArgType))
    value = Column(String)

# TODO: is this subclassing OK? Verify with Andy
class SyscallDWARFArgument(SyscallArgument):
    __tablename__ = "syscallDWARF_arguments"
    # syscall_argument_id -> Inherited from parent
    # syscall_id -> Inherited from parent
    syscall = relationship("SyscallDWARF", back_populates="arguments", uselist=False)
    # name -> Inherited from parent
    # position -> Inherited from parent
    argument_type = Column(String) # String name of struct type, NOT primitive enum
    members = relationship("StructMember", back_populates="syscallDWARF", order_by="StructMember.position")