# app/database/__init__.py

from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from contextlib import contextmanager
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800
        )
        self.Session = scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        )

    def create_tables(self):
        """Create all database tables and triggers"""
        from app.models.base import Base

        # Create tables
        Base.metadata.create_all(self.engine)

        # Create triggers
        try:
            sql_file = Path(__file__).parent / 'functions.sql'
            with open(sql_file, 'r') as f:
                sql = f.read()
                with self.engine.connect() as conn:
                    conn.execute(text(sql))
                    conn.execute(text("SELECT create_audit_triggers('public')"))
                    conn.commit()
            logger.info("Created database triggers for auditing")
        except Exception as e:
            logger.error(f"Error creating triggers: {str(e)}")
            raise

    @contextmanager
    def get_session(self):
        """Get a database session"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()

db_manager = None

def init_db(database_url: str) -> DatabaseManager:
    """Initialize the database manager"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager(database_url)
    return db_manager

def get_db() -> DatabaseManager:
    """Get the database manager instance"""
    if db_manager is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    return db_manager