import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./nyaya_history.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ScanRecord(Base):
    __tablename__ = "scans"

    scan_id = Column(String, primary_key=True, index=True)
    contract_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="processing")  # processing, complete, failed
    risk_level = Column(String, nullable=True)  # high, medium, low, none
    clause_count = Column(Integer, default=0)
    scan_date = Column(DateTime, default=datetime.datetime.utcnow)
    results_json = Column(Text, nullable=True)  # stores serialized list of findings

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id = Column(String, primary_key=True, index=True)
    session_id = Column(String, index=True)
    role = Column(String, nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    citations_json = Column(Text, nullable=True)  # stores serialized list of citations
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
