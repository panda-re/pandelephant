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
    tid = Column(BigInteger)
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

def create_session(url, debug=False):
    engine = create_engine(url, echo=debug)
    Session = sessionmaker(bind=engine)
    return Session()

def init_and_create_session(url, debug=False):
    engine = create_engine(url, echo=debug)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()