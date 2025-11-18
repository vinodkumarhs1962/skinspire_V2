"""
Run Enhanced Audit Trigger Migration
Executes SQL migration in steps with proper error handling
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

print('='  * 80)
print('ENHANCED AUDIT TRIGGER MIGRATION')
print('=' * 80)

with get_db_session() as session:
    # Step 1: Create enhanced track_user_changes function
    print('\n1. Creating enhanced track_user_changes() function...')
    session.execute(text("""
        CREATE OR REPLACE FUNCTION track_user_changes()
        RETURNS trigger AS $$
        DECLARE
            current_user_value text;
        BEGIN
            BEGIN
                current_user_value := current_setting('app.current_user', TRUE);
                IF current_user_value IS NULL OR current_user_value = '' THEN
                    current_user_value := session_user;
                END IF;
            EXCEPTION
                WHEN OTHERS THEN
                    current_user_value := session_user;
            END;

            IF TG_OP = 'INSERT' THEN
                IF NEW.created_by IS NULL OR NEW.created_by = '' THEN
                    NEW.created_by := current_user_value;
                END IF;
                IF NEW.updated_by IS NULL OR NEW.updated_by = '' THEN
                    NEW.updated_by := current_user_value;
                END IF;

            ELSIF TG_OP = 'UPDATE' THEN
                NEW.updated_by := current_user_value;
                NEW.created_by := OLD.created_by;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """))
    print('✓ track_user_changes() function created/updated')

    # Step 2: Create update_timestamp function (if not exists)
    print('\n2. Creating update_timestamp() function...')
    session.execute(text("""
        CREATE OR REPLACE FUNCTION update_timestamp()
        RETURNS trigger AS $$
        BEGIN
            NEW.updated_at := CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """))
    print('✓ update_timestamp() function created/updated')

    session.commit()
    print('\n✓ Trigger functions successfully created!')

print('\n' + '=' * 80)
print('MIGRATION COMPLETED SUCCESSFULLY')
print('=' * 80)
print('\nNext steps:')
print('1. Triggers are already applied to tables (existing triggers)')
print('2. Add SQLAlchemy Event Listeners to TimestampMixin')
print('3. Test the complete solution')
