# tests/test_security/test_database_triggers.py
# Run with: pytest tests/test_security/test_database_triggers.py

import pytest
import time
import uuid
from sqlalchemy import text
from datetime import datetime, timedelta

class TestDatabaseTriggers:
    """Test suite for database trigger functionality"""
    
    def test_timestamp_update_trigger(self, session, test_hospital):
        """Test that update_timestamp trigger automatically updates timestamps"""
        # Find a suitable table with updated_at column
        table_info = session.execute(text("""
            SELECT table_name FROM information_schema.columns 
            WHERE column_name = 'updated_at' 
            AND table_schema = 'public'
            LIMIT 1
        """)).fetchone()
        
        if not table_info:
            pytest.skip("No table with updated_at column found for testing")
        
        table_name = table_info[0]
        
        # Find the primary key for this table
        pk_info = session.execute(text(f"""
            SELECT kcu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_name = '{table_name}'
            LIMIT 1
        """)).fetchone()
        
        if not pk_info:
            pytest.skip(f"No primary key found for table {table_name}")
        
        pk_column = pk_info[0]
        
        # Find a record to test with
        record = session.execute(text(f"""
            SELECT {pk_column}, updated_at FROM {table_name} LIMIT 1
        """)).fetchone()
        
        if not record:
            pytest.skip(f"No records in table {table_name} to test with")
        
        pk_value = record[0]
        original_timestamp = record[1]
        
        # Find a suitable column to update (non-key, non-timestamp)
        update_col_info = session.execute(text(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            AND column_name NOT IN ('created_at', 'updated_at', '{pk_column}')
            AND (data_type LIKE '%char%' OR data_type = 'boolean')
            LIMIT 1
        """)).fetchone()
        
        if not update_col_info:
            pytest.skip(f"No suitable column found to update in {table_name}")
        
        update_column, data_type = update_col_info
        
        # Wait to ensure timestamp would change
        time.sleep(1)
        
        # Update the record
        if data_type == 'boolean':
            # Get current value and toggle it
            current_value = session.execute(text(f"""
                SELECT {update_column} FROM {table_name} WHERE {pk_column} = '{pk_value}'
            """)).scalar()
            
            new_value = 'FALSE' if current_value else 'TRUE'
        else:
            # For text/varchar columns, append a random string
            new_value = f"'test_update_{uuid.uuid4().hex[:8]}'"
        
        # Convert value for SQL if needed
        sql_value = new_value if isinstance(new_value, str) and new_value.startswith("'") else f"'{new_value}'"
        
        # Execute update
        session.execute(text(f"""
            UPDATE {table_name} 
            SET {update_column} = {sql_value}
            WHERE {pk_column} = '{pk_value}'
        """))
        session.commit()
        
        # Verify timestamp was updated
        new_record = session.execute(text(f"""
            SELECT updated_at FROM {table_name} WHERE {pk_column} = '{pk_value}'
        """)).fetchone()
        
        new_timestamp = new_record[0]
        
        # Assert the timestamp was updated
        assert new_timestamp > original_timestamp, f"Timestamp not updated in {table_name}"
        
        # Cleanup - restore original value if needed (optional)
    
    def test_password_hashing_trigger(self, session, test_hospital):
        """Test that password hashing trigger automatically hashes passwords"""
        # Check if the users table exists
        table_exists = session.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users')"
        )).scalar()
        
        if not table_exists:
            pytest.skip("Users table does not exist")
            
        # Check if the hash_password trigger exists
        trigger_exists = session.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.triggers WHERE trigger_schema = 'public' AND event_object_table = 'users' AND trigger_name = 'hash_password')"
        )).scalar()
        
        if not trigger_exists:
            pytest.skip("hash_password trigger does not exist on users table")
        
        # Determine the password column name
        password_column = 'password_hash' if session.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'password_hash')"
        )).scalar() else 'password'
        
        # Create a test user with a plain password
        test_user_id = f"test_{uuid.uuid4().hex[:8]}"
        plain_password = "secure_test_password_123"
        
        # Get required columns for users table
        columns = session.execute(text(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'users'"
        )).fetchall()
        
        # Prepare data for required columns
        column_data = {}
        for col in columns:
            col_name, data_type, is_nullable = col
            
            # Skip auto-generated columns
            if col_name in ('created_at', 'updated_at', 'id'):
                continue
                
            # Set values for required columns
            if col_name == 'user_id' or col_name == 'username':
                column_data[col_name] = test_user_id
            elif col_name == password_column:
                column_data[col_name] = plain_password
            elif col_name == 'hospital_id' and is_nullable == 'NO':
                column_data[col_name] = test_hospital.hospital_id
            elif col_name == 'entity_type' and is_nullable == 'NO':
                column_data[col_name] = 'test'
            elif col_name == 'entity_id' and is_nullable == 'NO':
                column_data[col_name] = str(uuid.uuid4())
            elif data_type == 'boolean' and is_nullable == 'NO':
                column_data[col_name] = False
            elif data_type.startswith('int') and is_nullable == 'NO':
                column_data[col_name] = 0
            elif is_nullable == 'NO':
                # For other non-nullable columns, use a generic test value
                if data_type.startswith('varchar') or data_type.startswith('text'):
                    column_data[col_name] = f'test_{col_name}'
                elif data_type.startswith('timestamp'):
                    column_data[col_name] = datetime.utcnow()
        
        # Build INSERT SQL
        columns_str = ', '.join(column_data.keys())
        placeholders = ', '.join([f':{col}' for col in column_data.keys()])
        
        try:
            # Insert the test user
            insert_sql = f"INSERT INTO users ({columns_str}) VALUES ({placeholders})"
            session.execute(text(insert_sql), column_data)
            session.commit()
            
            # Retrieve the stored password
            stored_password = session.execute(text(
                f"SELECT {password_column} FROM users WHERE user_id = :user_id"
            ), {'user_id': test_user_id}).scalar()
            
            # Verify the password was hashed
            assert stored_password != plain_password, "Password was not hashed"
            assert len(stored_password) > 20, "Password hash too short"
            
            # Verify it looks like a bcrypt hash
            assert stored_password.startswith('$2'), "Password not hashed with bcrypt"
        
        finally:
            # Cleanup - always delete the test user
            session.execute(text(
                "DELETE FROM users WHERE user_id = :user_id"
            ), {'user_id': test_user_id})
            session.commit()
    
    def test_user_tracking_trigger(self, session, test_hospital):
        """Test that user tracking trigger sets created_by and updated_by"""
        # Find a table with created_by and updated_by columns
        table_info = session.execute(text("""
            SELECT t.table_name
            FROM information_schema.columns t
            WHERE t.column_name = 'created_by'
            AND EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = t.table_name AND column_name = 'updated_by'
            )
            AND t.table_schema = 'public'
            LIMIT 1
        """)).fetchone()
        
        if not table_info:
            pytest.skip("No table with created_by/updated_by columns found")
        
        table_name = table_info[0]
        
        # Check if the track_user_changes trigger exists
        trigger_exists = session.execute(text(f"""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.triggers 
                WHERE trigger_schema = 'public' 
                AND event_object_table = '{table_name}' 
                AND trigger_name = 'track_user_changes'
            )
        """)).scalar()
        
        if not trigger_exists:
            pytest.skip(f"track_user_changes trigger does not exist on {table_name}")
        
        # Set the app.current_user session variable
        test_user = f"test_user_{uuid.uuid4().hex[:8]}"
        session.execute(text(f"SET app.current_user = '{test_user}'"))
        
        try:
            # Find primary key column
            pk_info = session.execute(text(f"""
                SELECT kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_name = '{table_name}'
                LIMIT 1
            """)).fetchone()
            
            if not pk_info:
                pytest.skip(f"No primary key found for table {table_name}")
            
            pk_column = pk_info[0]
            
            # Get column info for this table
            columns = session.execute(text(f"""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
            """)).fetchall()
            
            # Prepare data for required columns
            column_data = {}
            for col in columns:
                col_name, data_type, is_nullable = col
                
                # Skip tracked columns
                if col_name in ('created_at', 'updated_at', 'created_by', 'updated_by', 'id'):
                    continue
                
                # Set values for required columns
                if col_name == pk_column:
                    if data_type.startswith('varchar') or data_type == 'text':
                        column_data[col_name] = f'test_{uuid.uuid4().hex[:8]}'
                    elif data_type.startswith('int'):
                        # Try to get max ID and add 1
                        try:
                            max_id = session.execute(text(f"""
                                SELECT COALESCE(MAX({pk_column}), 0) FROM {table_name}
                            """)).scalar() or 0
                            column_data[col_name] = max_id + 1
                        except:
                            column_data[col_name] = 999999
                elif col_name == 'hospital_id' and is_nullable == 'NO':
                    column_data[col_name] = test_hospital.hospital_id
                elif data_type == 'boolean' and is_nullable == 'NO':
                    column_data[col_name] = False
                elif data_type.startswith('int') and is_nullable == 'NO':
                    column_data[col_name] = 0
                elif is_nullable == 'NO':
                    if data_type.startswith('varchar') or data_type.startswith('text'):
                        column_data[col_name] = f'test_{col_name}_{uuid.uuid4().hex[:4]}'
                    elif data_type.startswith('timestamp'):
                        column_data[col_name] = datetime.utcnow()
            
            # Build INSERT SQL
            columns_str = ', '.join(column_data.keys())
            placeholders = ', '.join([f':{col}' for col in column_data.keys()])
            
            # Insert test record
            insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
            session.execute(text(insert_sql), column_data)
            session.commit()
            
            # Get primary key value
            pk_value = column_data[pk_column]
            
            # Convert PK value for SQL if needed
            sql_pk_value = f"'{pk_value}'" if isinstance(pk_value, str) else str(pk_value)
            
            # Verify created_by and updated_by were set
            result = session.execute(text(f"""
                SELECT created_by, updated_by 
                FROM {table_name} 
                WHERE {pk_column} = {sql_pk_value}
            """)).fetchone()
            
            # Clean up test record
            session.execute(text(f"""
                DELETE FROM {table_name} WHERE {pk_column} = {sql_pk_value}
            """))
            session.commit()
            
            # Verify user tracking worked
            assert result is not None, f"Record not found in {table_name}"
            created_by, updated_by = result
            
            assert created_by == test_user, f"created_by not set correctly: expected '{test_user}', got '{created_by}'"
            assert updated_by == test_user, f"updated_by not set correctly: expected '{test_user}', got '{updated_by}'"
        
        finally:
            # Reset session variable
            session.execute(text("RESET app.current_user"))
    
    def test_account_lockout_trigger(self, session, test_hospital):
        """Test that account lockout trigger activates after failed attempts"""
        # Check if the users table exists with needed columns
        has_required_columns = session.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'users'
            ) AND EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'failed_login_attempts'
            )
        """)).scalar()
        
        # Also check for either account_status or locked_until column
        has_lockout_column = session.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'account_status'
            ) OR EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'locked_until'
            )
        """)).scalar()
        
        if not (has_required_columns and has_lockout_column):
            pytest.skip("Users table missing required columns for lockout test")
        
        # Check if the trigger exists
        trigger_exists = session.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.triggers 
                WHERE trigger_schema = 'public' 
                AND event_object_table = 'users' 
                AND trigger_name = 'check_account_lockout'
            )
        """)).scalar()
        
        if not trigger_exists:
            pytest.skip("check_account_lockout trigger does not exist on users table")
        
        # Create a test user
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # Get required columns for users table
        columns = session.execute(text(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'users'"
        )).fetchall()
        
        # Prepare data for required columns
        column_data = {}
        for col in columns:
            col_name, data_type, is_nullable = col
            
            # Skip auto-generated columns
            if col_name in ('created_at', 'updated_at', 'id'):
                continue
                
            # Set values for required columns
            if col_name == 'user_id' or col_name == 'username':
                column_data[col_name] = test_user_id
            elif col_name == 'password' or col_name == 'password_hash':
                column_data[col_name] = 'test_password'
            elif col_name == 'failed_login_attempts':
                column_data[col_name] = 0  # Start with 0 failures
            elif col_name == 'hospital_id' and is_nullable == 'NO':
                column_data[col_name] = test_hospital.hospital_id
            elif col_name == 'entity_type' and is_nullable == 'NO':
                column_data[col_name] = 'test'
            elif col_name == 'entity_id' and is_nullable == 'NO':
                column_data[col_name] = str(uuid.uuid4())
            elif col_name == 'account_status' and is_nullable == 'NO':
                column_data[col_name] = 'ACTIVE'
            elif data_type == 'boolean' and is_nullable == 'NO':
                column_data[col_name] = False
            elif data_type.startswith('int') and is_nullable == 'NO':
                column_data[col_name] = 0
            elif is_nullable == 'NO':
                if data_type.startswith('varchar') or data_type.startswith('text'):
                    column_data[col_name] = f'test_{col_name}'
                elif data_type.startswith('timestamp'):
                    column_data[col_name] = datetime.utcnow()
        
        # Build INSERT SQL
        columns_str = ', '.join(column_data.keys())
        placeholders = ', '.join([f':{col}' for col in column_data.keys()])
        
        try:
            # Insert the test user
            insert_sql = f"INSERT INTO users ({columns_str}) VALUES ({placeholders})"
            session.execute(text(insert_sql), column_data)
            session.commit()
            
            # Now simulate failed login attempts
            max_attempts = 5  # Should match your trigger configuration
            
            # Update the user's failed_login_attempts
            for i in range(1, max_attempts + 1):
                session.execute(text("""
                    UPDATE users 
                    SET failed_login_attempts = :attempts
                    WHERE user_id = :user_id
                """), {'attempts': i, 'user_id': test_user_id})
                session.commit()
            
            # Check if account was locked
            if session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'account_status'
                )
            """)).scalar():
                # Check account_status
                status = session.execute(text("""
                    SELECT account_status FROM users WHERE user_id = :user_id
                """), {'user_id': test_user_id}).scalar()
                
                assert status == 'LOCKED', f"Account not locked after {max_attempts} failed attempts"
            
            if session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'locked_until'
                )
            """)).scalar():
                # Check locked_until
                locked_until = session.execute(text("""
                    SELECT locked_until FROM users WHERE user_id = :user_id
                """), {'user_id': test_user_id}).scalar()
                
                assert locked_until is not None, "locked_until not set after failed attempts"
                assert locked_until > datetime.utcnow(), "locked_until not set to future time"
        
        finally:
            # Cleanup - always delete the test user
            session.execute(text(
                "DELETE FROM users WHERE user_id = :user_id"
            ), {'user_id': test_user_id})
            session.commit()