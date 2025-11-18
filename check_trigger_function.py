import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

with get_db_session() as session:
    func_def = session.execute(text("""
        SELECT pg_get_functiondef('update_payment_modification_tracking'::regproc)
    """)).scalar()

    print(func_def)
