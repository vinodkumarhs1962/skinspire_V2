# test_imports.py
print("Testing imports...")

try:
    import app.db
    print(f"app.db is: {type(app.db)}")
except Exception as e:
    print(f"Error importing app.db: {str(e)}")

try:
    from app import flask_db
    print(f"from app import flask_db gives: {type(flask_db)}")
except Exception as e:
    print(f"Error importing flask_db: {str(e)}")

print("Import test complete")