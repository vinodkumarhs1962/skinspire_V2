# scripts/verify_test_db.py
import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment
os.environ['FLASK_ENV'] = 'testing'

from app import create_app
from app.services.database_service import get_database_url, get_db_session
import sqlalchemy as sa

def check_test_database():
    """Verify the test database connection and tables"""
    app = create_app()
    
    # Get the database URL
    db_url = get_database_url()
    print(f"Using database URL: {db_url}")
    
    try:
        # Create a direct engine connection to bypass SQLAlchemy ORM
        engine = sa.create_engine(db_url)
        
        # Check if we can connect
        connection = engine.connect()
        print("Successfully connected to the database")
        
        # Check for tables
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        result = connection.execute(sa.text(query))
        tables = [row[0] for row in result]
        
        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
            
        # Specifically check if 'users' exists and what it contains
        if 'users' in tables:
            print("\nChecking 'users' table structure:")
            column_query = """
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND table_schema = 'public'
                ORDER BY ordinal_position
            """
            columns = connection.execute(sa.text(column_query))
            for column in columns:
                print(f"  - {column[0]}: {column[1]} (Nullable: {column[2]})")
            
            # Check if there are any rows in the table
            row_count = connection.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
            print(f"\nTotal rows in users table: {row_count}")
            
            # Try to fetch one row to verify structure
            if row_count > 0:
                sample_row = connection.execute(sa.text("SELECT * FROM users LIMIT 1")).first()
                print(f"Sample user_id: {sample_row[0] if sample_row else 'None'}")
        else:
            print("\nWARNING: 'users' table was not found!")
            
        connection.close()
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        print("Detailed traceback:")
        import traceback
        traceback.print_exc()
    
    # Now try using the database service approach
    print("\nTesting database service connection:")
    try:
        with get_db_session() as session:
            # Check connection with a simple query
            result = session.execute(sa.text("SELECT 1")).scalar()
            print(f"Test query result: {result}")
            
            # Try to query the users table
            result = session.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
            print(f"Users count via session: {result}")
    except Exception as e:
        print(f"ERROR with database service: {type(e).__name__}: {str(e)}")
        print("Detailed traceback:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_test_database()