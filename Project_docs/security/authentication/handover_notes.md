2. Handover Notes Template
When starting a new chat, provide this structure:

```markdown
# Work in Progress Status

## Current Issue
- Working on: Authentication system tests
- Specific Error: PostgreSQL session variable handling
- File: test_auth_system.py

## Verified Working Components
- Database connections ✅
- Schema creation ✅
- Blueprint registration ✅
- Basic endpoints ✅

## Last Working Change
```python
# Last verified working code
@contextmanager
def user_context(session, user_id):
    # Show the last working version