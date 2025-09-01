You're right that a consistent approach will be essential when migrating existing code to use the database_service strategy. Let me help you with a brief synopsis for new chats and identify the key files you should attach.

## New Chat Background Text

```
I'm working on implementing a unified database access strategy for our Skinspire hospital management system. We've created a centralized database_service.py that serves as the single point of entry for all database operations.

Key points about our approach:
1. All database access should use get_db_session() from database_service.py
2. This service automatically detects whether to use Flask-SQLAlchemy or direct SQLAlchemy
3. All transaction management is handled via context managers
4. We're now migrating all existing code to use this pattern

I need help updating the following files to use this approach:
[list files here]

The migration requires changing direct SQLAlchemy usage, Flask-SQLAlchemy access, and any custom database access patterns to use the centralized database_service approach.

Please find following files in Project knowledge for reference.
database_service.py
Developer Guide-Using database_service.py.md
project structure 13.03.2.25
database models :  base.py, master.py, transaction.py
```

## Key Files to Attach

When starting a new chat for migration help, you should attach these files:

1. **database_service.py** - The core service implementing the unified approach
2. **Developer Guide: Using database_service.py** - The guide I provided 
3. **Files to be migrated** - The specific files you need help updating
4. **Related model files** - Any model definitions related to the files being migrated

## Migration Checklist

Here's a checklist of patterns to look for when migrating code:

1. **Direct db.session usage**:
   - Before: `user = db.session.query(User).first()`
   - After: `with get_db_session() as session: user = session.query(User).first()`

2. **Direct SQLAlchemy Session usage**:
   - Before: `session = Session(); try: ...; finally: session.close()`
   - After: `with get_db_session() as session: ...`

3. **Manual transaction management**:
   - Before: `try: ...; session.commit(); except: session.rollback(); raise`
   - After: `with get_db_session() as session: ...` (commit/rollback handled automatically)

4. **Database manager usage**:
   - Before: `db_manager = get_db(); with db_manager.get_session() as session: ...`
   - After: `with get_db_session() as session: ...`

5. **Flask application contexts**:
   - Before: `with app.app_context(): user = User.query.first()`
   - After: `with get_db_session() as session: user = session.query(User).first()`

This systematic approach will help ensure that all your code is consistently using the database_service for database access.