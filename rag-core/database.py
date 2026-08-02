from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://raguser:ragpassword@localhost:5432/ragdb"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db_session():
    return SessionLocal()

def setup_database():
    """Creates the pgvector extension and the chunks table if they don't exist yet."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chunks (
                id SERIAL PRIMARY KEY,
                source_file TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding vector(384)
            );
        """))
        conn.commit()
    print("Database setup complete: extension and table are ready.")