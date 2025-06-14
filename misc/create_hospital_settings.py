# create_hospital_settings.py
import os
import sys
import subprocess

# Set environment variables directly
os.environ['FLASK_APP'] = 'app:create_app'

# Run Flask in simplified mode
try:
    # Check if table exists using the correct inspect API
    print("Checking if hospital_settings table exists...")
    result = subprocess.run(
        [sys.executable, '-c', 
         "from app import create_app, db; from sqlalchemy import inspect; " +
         "app=create_app(); app.app_context().push(); " +
         "print('Table exists' if inspect(db.engine).has_table('hospital_settings') else 'Table does not exist')"],
        capture_output=True,
        text=True,
        check=True
    )
    
    print(result.stdout)
    
    # Check if we need to create the table
    if "Table does not exist" in result.stdout:
        print("Creating hospital_settings table...")
        # Create the table using SQL directly with explicit transaction
        result = subprocess.run(
            [sys.executable, '-c', 
             """
from app import create_app, db
from sqlalchemy import text
app = create_app()
app.app_context().push()

sql_command = '''
CREATE TABLE hospital_settings (
    setting_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    category VARCHAR(50) NOT NULL,
    settings JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by VARCHAR(50),
    updated_by VARCHAR(50)
);
'''

with db.engine.begin() as conn:
    conn.execute(text(sql_command))
    print("SQL executed successfully")
             """
            ],
            capture_output=True,
            text=True
        )
        
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
    else:
        print("Table already exists.")
    
    print("Script completed successfully.")
        
except subprocess.CalledProcessError as e:
    print(f"Error executing command:")
    print(f"STDOUT: {e.stdout}")
    print(f"STDERR: {e.stderr}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)