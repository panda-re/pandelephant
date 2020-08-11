from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, LargeBinary, ARRAY, BigInteger, DateTime, Table, ForeignKey, create_engine
from sqlalchemy.orm import relationship, sessionmaker


Base = declarative_base()

class Execution(Base):
    __tablename__ = 'executions'
    execution_id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True)) 
    processes = relationship("Process", back_populates="execution")
    recording = relationship("Recording", back_populates="execution", uselist=False)

class Recording(Base):
    __tablename__ = 'recordings'
    recording_id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey('executions.execution_id'), nullable=False)
    file_name = Column(String)
    log_hash = Column(LargeBinary, unique=True, nullable=False)
    snapshot_hash = Column(LargeBinary, unique=True, nullable=False)
    qcow_hash = Column(LargeBinary)
    execution = relationship("Execution", back_populates="recording", uselist=False)

class Process(Base):
    __tablename__ = 'processes'
    process_id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey('executions.execution_id'), nullable=False)
    pid = Column(BigInteger, nullable=False)
    ppid = Column(BigInteger)
    execution = relationship("Execution", back_populates="processes")
    threads = relationship("Thread", back_populates="process")
    modules = relationship("Module", back_populates="process")

class Thread(Base):
    __tablename__ = 'threads'
    thread_id = Column(Integer, primary_key=True)
    process_id = Column(Integer, ForeignKey('processes.process_id'), nullable=False)
    names = Column(ARRAY(String))
    tid = Column(BigInteger)
    create_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    process = relationship("Process", back_populates="threads")

class Module(Base):
    __tablename__ = 'modules'
    module_id = Column(Integer, primary_key=True)
    process_id = Column(Integer, ForeignKey('processes.process_id'), nullable=False)
    name = Column(String)
    path = Column(String)
    base_id = Column(Integer, ForeignKey('virtual_addresses.address_id'), nullable=False)
    base = relationship("VirtualAddress", uselist=False)
    size = Column(BigInteger, nullable=False)
    process = relationship("Process", back_populates="modules")
    codepoints = relationship("CodePoint", back_populates="module")

class VirtualAddress(Base):
    __tablename__ = 'virtual_addresses'
    address_id = Column(Integer, primary_key=True)
    asid = Column(BigInteger, nullable=False)  # bases are virtual addresses so we need an ASID
    execution_offset = Column(BigInteger, nullable=False)  # We're using an ASID so we need a "time". We're using instruction count indexed by execution start (execution starts at 0).
    address = Column(BigInteger, nullable=False)

class CodePoint(Base):
    __tablename__ = 'codepoints'
    code_point_id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey('modules.module_id'), nullable=False)
    offset = Column(BigInteger, nullable=False)
    module = relationship("Module", back_populates="codepoints", uselist=False)


class WriteReadFlow(Base):
    __tablename__ = 'writeread_flows'
    writeread_flow_id = Column(Integer, primary_key=True)
    # this is the code location of the write (store)
    write_id = Column(Integer, ForeignKey('codepoints.code_point_id'), nullable=False)
    write_thread_id = Column(Integer, ForeignKey('threads.thread_id'), nullable=False)

    # this is the code location of the read (load)
    read_id = Column(Integer, ForeignKey('codepoints.code_point_id'), nullable=False)
    read_thread_id = Column(Integer, ForeignKey('threads.thread_id'), nullable=False)

    execution_offset = Column(BigInteger, nullable=False) # This is an offset in the exection by 
    write = relationship('CodePoint', foreign_keys=[write_id], uselist=False)
    write_thread = relationship('Thread', foreign_keys=[write_thread_id], uselist=False)
    read = relationship('CodePoint', foreign_keys=[read_id], uselist=False)
    read_thread = relationship('Thread', foreign_keys=[read_thread_id], uselist=False)

def create_session(url, debug=False):
    engine = create_engine(url, echo=debug)
    Session = sessionmaker(bind=engine)
    return Session()

def init_and_create_session(url, debug=False):
    engine = create_engine(url, echo=debug)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
