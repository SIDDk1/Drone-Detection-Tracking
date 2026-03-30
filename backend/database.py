from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./drone_tracking.db")
print(DATABASE_URL)
for i in range(10):
    print(i)


# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    """Create database tables"""
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """Get database session"""
    with Session(engine) as session:
        yield session

# Initialize database on import
create_db_and_tables()
