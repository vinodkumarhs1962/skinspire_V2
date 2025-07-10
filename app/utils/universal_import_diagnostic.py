# =============================================================================
# File: app/utils/universal_import_diagnostic.py
# Diagnostic to identify exactly which import is failing in universal_views.py
# =============================================================================

# python app/utils/universal_import_diagnostic.py -v

"""
Targeted diagnostic to identify the specific import causing universal_views 
blueprint registration to fail silently.
"""

import sys
import traceback
from typing import Dict, List, Any

def diagnose_universal_imports() -> Dict[str, Any]:
    """
    Test each import from universal_views.py individually to identify failures
    """
    print("🔍 UNIVERSAL VIEWS IMPORT DIAGNOSTIC")
    print("=" * 60)
    
    report = {
        'timestamp': str(__import__('datetime').datetime.now()),
        'import_results': [],
        'failed_imports': [],
        'critical_failures': [],
        'recommendations': []
    }
    
    # List of imports from universal_views.py in order
    imports_to_test = [
        # Core Flask imports
        ('flask', 'from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, g, make_response'),
        ('flask_login', 'from flask_login import login_required, current_user'),
        ('datetime', 'from datetime import datetime'),
        ('uuid', 'import uuid'),
        ('typing', 'from typing import Dict, Any, Optional, List'),
        
        # Security imports
        ('security.decorators', 'from app.security.authorization.decorators import require_web_branch_permission, require_web_cross_branch_permission'),
        ('database_service', 'from app.services.database_service import get_db_session'),
        
        # Entity configuration imports  
        ('entity_configurations', 'from app.config.entity_configurations import get_entity_config, is_valid_entity_type, list_entity_types'),
        
        # Engine imports
        ('data_assembler', 'from app.engine.data_assembler import EnhancedUniversalDataAssembler'),
        ('universal_services', 'from app.engine.universal_services import get_universal_service'),
        
        # Context helpers
        ('context_helpers', 'from app.utils.context_helpers import ensure_request_context, get_user_branch_context, get_branch_uuid_from_context_or_request'),
        
        # Logging
        ('unicode_logging', 'from app.utils.unicode_logging import get_unicode_safe_logger')
    ]
    
    for import_name, import_statement in imports_to_test:
        result = test_import(import_name, import_statement)
        report['import_results'].append(result)
        
        if result['status'] == 'FAIL':
            report['failed_imports'].append(result)
            if result['critical']:
                report['critical_failures'].append(result)
    
    # Generate recommendations
    generate_recommendations(report)
    
    # Print results
    print_import_results(report)
    
    return report

def test_import(import_name: str, import_statement: str) -> Dict[str, Any]:
    """Test a single import and return detailed results"""
    
    print(f"Testing: {import_name}...", end=" ")
    
    result = {
        'name': import_name,
        'statement': import_statement,
        'status': 'UNKNOWN',
        'error': None,
        'error_type': None,
        'critical': False
    }
    
    # Determine if this import is critical for blueprint registration
    critical_imports = [
        'flask', 'flask_login', 'security.decorators', 
        'entity_configurations', 'universal_services'
    ]
    result['critical'] = import_name in critical_imports
    
    try:
        # Try to execute the import
        exec(import_statement)
        result['status'] = 'PASS'
        print("✅ PASS")
        
    except ImportError as e:
        result['status'] = 'FAIL'
        result['error'] = str(e)
        result['error_type'] = 'ImportError'
        print(f"❌ FAIL - ImportError: {e}")
        
    except ModuleNotFoundError as e:
        result['status'] = 'FAIL'
        result['error'] = str(e)
        result['error_type'] = 'ModuleNotFoundError'
        print(f"❌ FAIL - ModuleNotFoundError: {e}")
        
    except Exception as e:
        result['status'] = 'ERROR'
        result['error'] = str(e)
        result['error_type'] = type(e).__name__
        print(f"💥 ERROR - {type(e).__name__}: {e}")
    
    return result

def generate_recommendations(report: Dict[str, Any]) -> None:
    """Generate specific recommendations based on import failures"""
    
    failed_imports = report['failed_imports']
    critical_failures = report['critical_failures']
    
    if not failed_imports:
        report['recommendations'].append("✅ All imports successful - issue may be elsewhere")
        return
    
    # Check for specific failure patterns
    for failure in failed_imports:
        import_name = failure['name']
        error = failure['error']
        
        if import_name == 'entity_configurations':
            report['recommendations'].append(
                "🔧 Create missing entity_configurations module or implement fallback functions"
            )
        
        elif import_name == 'universal_services':
            report['recommendations'].append(
                "🔧 Create missing universal_services module or implement service adapter"
            )
        
        elif import_name == 'data_assembler':
            report['recommendations'].append(
                "🔧 Create missing data_assembler module or implement basic assembler"
            )
        
        elif import_name == 'context_helpers':
            report['recommendations'].append(
                "🔧 Create missing context_helpers module with required functions"
            )
        
        elif 'circular import' in error.lower():
            report['recommendations'].append(
                f"🔄 Fix circular import in {import_name} - consider lazy imports"
            )
    
    # Critical failure recommendations
    if critical_failures:
        report['recommendations'].append(
            "🚨 CRITICAL: Fix critical import failures before blueprint can register"
        )
        report['recommendations'].append(
            "💡 Consider implementing minimal fallback versions of missing modules"
        )

def print_import_results(report: Dict[str, Any]) -> None:
    """Print formatted results"""
    
    print("\n" + "=" * 60)
    print("📊 IMPORT DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    total_imports = len(report['import_results'])
    failed_count = len(report['failed_imports'])
    critical_failed = len(report['critical_failures'])
    
    print(f"\n📈 Statistics:")
    print(f"  Total Imports Tested: {total_imports}")
    print(f"  Failed Imports: {failed_count}")
    print(f"  Critical Failures: {critical_failed}")
    
    if report['failed_imports']:
        print(f"\n❌ Failed Imports ({failed_count}):")
        for failure in report['failed_imports']:
            critical_marker = "🚨 CRITICAL" if failure['critical'] else "⚠️"
            print(f"  {critical_marker} {failure['name']}: {failure['error_type']} - {failure['error']}")
    
    if report['recommendations']:
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"  {i}. {rec}")
    
    print("\n" + "=" * 60)

def test_blueprint_registration():
    """Test if the blueprint can be registered after fixing imports"""
    
    print("\n🧪 TESTING BLUEPRINT REGISTRATION")
    print("-" * 40)
    
    try:
        # Try to import the blueprint
        from app.views.universal_views import universal_bp
        print("✅ Blueprint import successful")
        
        # Try to access blueprint properties
        print(f"✅ Blueprint name: {universal_bp.name}")
        print(f"✅ Blueprint prefix: {universal_bp.url_prefix}")
        
        # Try to register with current app
        from flask import current_app
        if 'universal_views' in current_app.blueprints:
            print("✅ Blueprint already registered")
        else:
            # Try registration
            current_app.register_blueprint(universal_bp)
            print("✅ Blueprint registration successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Blueprint registration failed: {e}")
        traceback.print_exc()
        return False

def quick_fix_test():
    """Test a quick fix approach with minimal imports"""
    
    print("\n🔧 TESTING QUICK FIX APPROACH")
    print("-" * 40)
    
    # Test if we can create a minimal universal_views module
    minimal_code = '''
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

# Create blueprint
universal_bp = Blueprint('universal_views', __name__, url_prefix='/universal')

@universal_bp.route('/<entity_type>/list')
@login_required  
def universal_list_view(entity_type):
    """Minimal universal list view for testing"""
    flash(f"Universal list view accessed for {entity_type}", 'info')
    return redirect(url_for('auth_views.dashboard'))
'''
    
    try:
        # Try to execute minimal code
        exec(minimal_code, globals())
        print("✅ Minimal universal_views code works")
        return True
        
    except Exception as e:
        print(f"❌ Even minimal code fails: {e}")
        return False

if __name__ == "__main__":
    # Run full diagnostic
    report = diagnose_universal_imports()
    
    # Test blueprint registration
    test_blueprint_registration()
    
    # Test quick fix
    quick_fix_test()