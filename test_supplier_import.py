# test_supplier_import.py
try:
    from app.views.supplier_views import supplier_views_bp
    print("Import successful!")
    print(f"Blueprint name: {supplier_views_bp.name}")
    print(f"URL prefix: {supplier_views_bp.url_prefix}")
except Exception as e:
    print(f"Import failed: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()