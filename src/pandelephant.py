from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, LargeBinary, ARRAY, BigInteger, DateTime, Table, ForeignKey, create_engine
from sqlalchemy.orm import relationship, sessionmaker


Base = declarative_base()

class Execution(Base):
    __tablename__ = 'executions'
    execution_id = Column(Integer, primary_key=True)
    name = Column(String)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True)) 
    processes = relationship("Process", back_populates="execution")
    recording = relationship("Recording", back_populates="execution", uselist=False)

class Recording(Base):
    __tablename__ = 'recordings'
    recording_id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey('executions.execution_id'))
    file_name = Column(String)
    log_hash = Column(LargeBinary)
    snapshot_hash = Column(LargeBinary)
    qcow_hash = Column(LargeBinary)
    execution = relationship("Execution", back_populates="recording", uselist=False)

process_modules = Table('process_modules', Base.metadata, Column('process_id', ForeignKey('processes.process_id'), primary_key=True), Column('module_id', ForeignKey('modules.module_id'), primary_key=True))

# I'm calling all units of execution processes
class Process(Base):
    __tablename__ = 'processes'
    process_id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey('executions.execution_id'))
    names = Column(ARRAY(String))
    asid = Column(BigInteger)
    pid = Column(BigInteger)
    ppid = Column(BigInteger)
    tids = Column(Array(BigInteger))
    create_time = Column(DateTime(timezone=True))
    execution = relationship("Execution", back_populates="processes")
    modules = relationship("Module", secondary=process_modules, back_populates="process")

class Module(Base):
    __tablename__ = 'modules'
    module_id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    base = Column(BigInteger)
    size = Column(BigInteger)
    process = relationship("Process", secondary=process_modules, back_populates="modules")

class CodePoint(Base):
    __table_name__ = 'codepoints'
    code_point_id = Column(Integer, primary_key=True)
    module = relationship("module", secondary=process_modules, back_populates="modules")
    offset = Column(BigInteger)

class TaintFlow(Base):
    __tablename__ = 'taint_flows'
    taint_flow_id = Column(Integer, primary_key=True)
    # this is the code location of the write (store)
    src = Column(CodePoint) this is module/offset which i guess means it also relates to a process (which is good)
    # this is the code location of the read (load)
    dest = Column(CodePoint) this is another module/offset
    # this is the number of times we observed this flow
    count = Column(BigInteger)
    # this is first instr count in the replay when we observed this flow
    min_instr = Column(BigInteger)
    # this is last instr count in the replay when we observed this flow
    max_instr = Column(BigInteger)


def create_session(url, debug=False):
    engine = create_engine(url, echo=debug)
    Session = sessionmaker(bind=engine)
    return Session()

def init_and_create_session(url, debug=False):
    engine = create_engine(url, echo=debug)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
