from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# IMPORTANTE:
# Este archivo debe existir (generado por tu script Modbus) en la raíz desde donde ejecutas uvicorn.
DATABASE_URL = "sqlite:///./plc_analog_log_test_5s_60s.sqlite3"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # necesario para SQLite + FastAPI
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()